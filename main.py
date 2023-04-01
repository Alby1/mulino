import random
import string
import time
import uvicorn
import datetime

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, FileResponse, Response

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Boolean, desc
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from sqlalchemy.ext.declarative import DeclarativeMeta

import requests

from pydantic import BaseModel

import json

from starlette.requests import Request as StarletteRequest
from starlette.responses import StreamingResponse
from starlette.background import BackgroundTask

import httpx


class AlchemyEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj.__class__, DeclarativeMeta):
            # an SQLAlchemy class
            fields = {}
            for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
                data = obj.__getattribute__(field)
                try:
                    # this will fail on non-encodable values, like other classes
                    json.dumps(data)
                    fields[field] = data
                except TypeError:
                    fields[field] = None
            # a json-encodable dict
            return fields

        return json.JSONEncoder.default(self, obj)


class API():
    class Product(BaseModel):
        id: int
        nome: str
        quantita: int
        prezzo: int
        registry: str | None
    class Login(BaseModel):
        user: str
        password: str

    class User(BaseModel):
        id: int
        user: str
        password: str
        admin: bool
        registry: str | None
    class Token(BaseModel):
        token: str

    class Fattura(BaseModel):
        id: int
        user: str
        indirizzo: str

    class FatturaProdotto(BaseModel):
        id: int
        fattura: int
        prodotto: int
        quantita: int
        unitario: int
        where: int = None


    def is_user_admin(db, token):
        if(token == "null"): return False
        user = db.get_user_by_token(token)
        if(user is not None):
            return user.admin
        return False


class DB_Service():
    Base = declarative_base()

    class Prodotto(Base):
        __tablename__ = 'prodotti'
        id = Column(Integer, primary_key=True,
                    nullable=False, autoincrement=True)
        nome = Column(String(45), nullable=False)
        prezzo = Column(INTEGER(unsigned=True), nullable=False)
        quantita = Column(INTEGER(unsigned=True), nullable=False)
        where = Column(Integer, ForeignKey("venditori.id"))
        local_id = Column(Integer, nullable=False)

        venditore_ = relationship("Seller", back_populates="prodotti_")
        fattureprodotti_ = relationship(
            "FatturaProdotto", back_populates="prodotto_")
        
        def __repr__(self):
            return f"{self.id} {self.nome} {self.prezzo} {self.quantita} {self.where} {self.local_id}"

    class Utente(Base):
        __tablename__ = 'utenti'
        id = Column(Integer, primary_key=True,
                    nullable=False, autoincrement=True)
        user = Column(String(45), unique=True, nullable=False)
        password = Column(String(45), nullable=False)
        admin = Column(Boolean())
        token = Column(String(20), unique=True)
        where = Column(Integer, ForeignKey("venditori.id"))

        venditore_ = relationship("Seller", back_populates="utenti_")
        fatture_ = relationship("Fattura", back_populates="utente_")

    class Seller(Base):
        __tablename__ = 'venditori'
        id = Column(Integer, primary_key=True,
                    nullable=False, autoincrement=True)
        nome = Column(String(20), nullable=False, unique=True)
        port = Column(Integer, unique=True, nullable=False)

        prodotti_ = relationship("Prodotto", back_populates="venditore_")
        utenti_ = relationship("Utente", back_populates="venditore_")
        fatture_ = relationship("Fattura", back_populates="venditore_")

    class Fattura(Base):
        __tablename__ = 'fatture'
        id = Column(Integer, primary_key=True,
                    nullable=False, autoincrement=True)
        user = Column(String(45), ForeignKey("utenti.user"), nullable=False)
        indirizzo = Column(String(40), nullable=False)
        where = Column(Integer, ForeignKey("venditori.id"))
        local_id = Column(Integer, nullable=False)

        venditore_ = relationship("Seller", back_populates="fatture_")
        utente_ = relationship("Utente", back_populates="fatture_")
        fattureprodotti_ = relationship(
            "FatturaProdotto", back_populates="fattura_")
        
        def __repr__(self):
            return f"{self.user} {self.where} {self.local_id}"

    class FatturaProdotto(Base):
        __tablename__ = 'fatture_prodotti'
        id = Column(Integer, primary_key=True,
                    nullable=False, autoincrement=True)
        fattura = Column(Integer, ForeignKey("fatture.id"))
        prodotto = Column(Integer, ForeignKey("prodotti.id"))
        quantita = Column(Integer, nullable=False)
        unitario = Column(Integer, nullable=False)
        where = Column(Integer, ForeignKey("venditori.id"))
        local_id = Column(Integer, nullable=False)

        fattura_ = relationship("Fattura", back_populates="fattureprodotti_")
        prodotto_ = relationship("Prodotto", back_populates="fattureprodotti_")

        def __repr__(self) -> str:
            return f"{self.fattura} {self.prodotto} {self.quantita} {self.unitario} {self.where} {self.local_id}"

    def __init__(self):
        self.protocol = "mysql+pymysql"
        self.host = "localhost"
        self.port = 3306
        self.user = "mulino"
        self.password = "mulino"
        self.name = f"mulino_main"
        if not database_exists(f"{self.protocol}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"):
            create_database(
                f"{self.protocol}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}")

            self.engine = create_engine(
                f"{self.protocol}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}", echo=False, pool_size=10, max_overflow=20)

            self.Base.metadata.create_all(self.engine)

            self.add_user("admin", "admin", True)

            return

        self.engine = create_engine(
            f"{self.protocol}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}", echo=False, pool_size=10, max_overflow=20)

        self.Base.metadata.create_all(self.engine)

    def session(self) -> Session:
        return sessionmaker(bind=self.engine)()

    def get_port(self, seller):
        s = self.session()

        q = s.query(self.Seller)

        if (q.count() != 0):
            q = q.filter(self.Seller.nome == seller)
            if (q.count() != 0):
                return q.first().port

        a = s.query(self.Seller).order_by(desc(self.Seller.port))
        p = 9000

        if (a.count() != 0):
            p = int(a.first().port)
        p += 1
        sl = self.Seller(nome=seller, port=p)
        s.add(sl)
        s.commit()
        s.close()

        return p

    def prodotto_s(self, p: API.Product, seller: str):
        s = self.session()

        w = s.query(self.Seller).filter(self.Seller.nome == seller).first().id
        try:
            q = s.query(self.Prodotto).filter(self.Prodotto.where ==
                                              w).filter(self.Prodotto.nome == p.nome)
            m = q.first()
            m.prezzo = p.prezzo
            m.quantita = p.quantita
            s.commit()
            s.close()

        except:
            pa = self.Prodotto(
                nome=p.nome, quantita=p.quantita, prezzo=p.prezzo, where=w, local_id=p.id)

            s.add(pa)
            s.commit()
            i = pa.id
            s.close()
            return i

    def user_s(self, p: API.User, seller: str):
        s = self.session()

        w = s.query(self.Seller).filter(self.Seller.nome == seller).first().id

        i = -1

        try:
            q = s.query(self.Utente).filter(self.Utente.where ==
                                            w).filter(self.Utente.user == p.user)
            if (q.count != 0):
                m = q.first()
                m.user = p.user
                m.password = p.password
                m.admin = p.admin

                s.commit()
                i = m.id
                s.close()

        except:
            try:
                ua = self.Utente(
                    user=p.user, password=p.password, admin=p.admin, where=w)

                s.add(ua)
                s.commit()
                i = ua.id
                s.close()
            except:
                s.close()

        return i

    def get_users(self):
        s = self.session()

        q = s.query(self.Utente)

        s.close()

        return q.all()

    def add_user(self, username, password, admin=None, where=None):
        s = self.session()

        u = self.Utente(user=username, password=password,
                        admin=admin, where=where)

        s.add(u)
        s.commit()
        i = u.id
        s.close()
        return i

    def get_sellers(self) -> list[Seller]:
        s = self.session()

        ss = s.query(self.Seller)

        s.close()

        return ss.all()

    def fatture_s(self, fatture: list[Fattura]):
        s = self.session()
        try:
            s.add_all(fatture)
            s.commit()
        except Exception as e:
            print(e)
        finally:
            s.close()

    def get_fattura_by_local_id_and_where(self, id: int, where : int) -> Fattura | Boolean:
        s = self.session()
        q = False
        try:
            q = s.query(self.Fattura).filter(self.Fattura.local_id == id).filter(self.Fattura.where == where)
            ret = q.first()
        except: pass
        finally:
            s.close()
            return ret

    def fatture_prodotti_s(self, fatture: list[FatturaProdotto]):
        s = self.session()
        try:
            s.add_all(fatture)
            s.commit()
        except Exception as e:
            print(e)
        finally:
            s.close()

    def get_fattura_prodotto_by_local_id_and_where(self, id: int, where : int) -> FatturaProdotto | Boolean:
        s = self.session()
        q = False
        try:
            q = s.query(self.FatturaProdotto).filter(self.FatturaProdotto.local_id == id).filter(self.FatturaProdotto.where == where)
            ret = q.first()
        except: pass
        finally:
            s.close()
            return ret

    def get_venditore_by_name(self, name) -> Seller:
        s = self.session()
        ret = False
        try:
            q = s.query(self.Seller).filter(self.Seller.nome == name)
            
            ret = q.first()
        except: pass
        finally:
            s.close()
            return ret
        
    def get_user_by_token(self, token):
        s = self.session()
        try:
            q = s.query(self.Utente).filter(self.Utente.token == token)
        except Exception as e: print(e)
        finally: s.close()
        if(q.count() == 0): return None
        return q.first()
    
    def login(self, user, password):
        s = self.session()
        try:
            letters = string.ascii_lowercase
            result_str = ''.join(random.choice(letters) for i in range(20))

            w = s.query(self.Utente).filter(self.Utente.user == user).filter(self.Utente.password == password)

            u = w.first()

            if(w.count() == 0):
                s.close()
                return None

            admin = False

            cycles = 1
            while cycles > 0:
                try:
                    u.token = result_str
                    admin = u.admin

                    s.commit()

                    cycles = -1
                except Exception as e:
                    if(cycles >= 5):
                        print(e)
                        break
                    cycles += 1
                    time.sleep(0.1 * cycles)
        except: pass
        finally: s.close()
        
        return result_str, admin
    
    def get_fatture(self) -> list[Fattura]:
        s = self.session()
        f = s.query(self.Fattura)
        s.close()
        return f.all()
    
    def get_fatture_prodotti_by_fattura_id(self, id) -> list[FatturaProdotto]:
        s = self.session()
        ret = False
        try:
            q = s.query(self.FatturaProdotto).filter(self.FatturaProdotto.fattura == id)
            ret = q.all()
        except: pass
        finally: 
            s.close()
            return ret
        
    def get_product_by_id(self, id) -> Prodotto:
        session = self.session()
        try:
            q = session.query(self.Prodotto).filter(self.Prodotto.id == id)
        except:pass
        finally: session.close()

        return q.first()
    
    def get_product_by_local_id_and_where(self, id : int, where : int) -> Prodotto:
        session = self.session()
        ret = False
        try:
            q = session.query(self.Prodotto).filter(self.Prodotto.local_id == id).filter(self.Prodotto.where == where)
            ret = q.first()
        except:pass
        finally: session.close()

        return ret
    
    def get_user_by_id(self, id: int) -> Utente:
        s = self.session()
        ret = False
        try:
            q = s.query(self.Utente).filter(self.Utente.id == id)
            ret = q.first()
        except: pass
        finally:
            s.close()
            return ret
        
    
    def get_user_by_user(self, user: str) -> Utente:
        s = self.session()
        ret = False
        try:
            q = s.query(self.Utente).filter(self.Utente.user == user)
            ret = q.first()
        except: pass
        finally:
            s.close()
            return ret
        
    
    
    def check_session(self, token: str = None):
        if(token is None): return False
        s = self.session()
        try:
            q = s.query(self.Utente).filter(self.Utente.token == token)

            if(q.count() != 0):
                s.close()
                return True
        except: pass
        finally: s.close()
        return False
    
    def get_seller_by_id(self, id) -> Seller:
        s = self.session()
        ret = False
        try:
            q = s.query(self.Seller).filter(self.Seller.id == id)
            ret = q.first()
        except: pass
        finally:
            s.close()
            return ret

app = FastAPI()

origins = ["*"]

app.add_middleware(CORSMiddleware, allow_origins=origins)


@app.on_event("startup")
async def startup():
    global db
    db = DB_Service()
    global templates
    templates = Jinja2Templates(directory="www")

    global clients
    clients = []


@app.get("/port")
def fa_port(seller: str = None):
    if (seller is None):
        return "no seller provided"
    global db
    return db.get_port(seller)


@app.post("/products")
def fa_p_products(products: list[API.Product], seller: str | None = None):
    if (seller is None):
        return False
    global db
    for p in products:
        db.prodotto_s(p, seller)


@app.post("/users_s")
def fa_p_users(users: list[API.User], seller: str | None = None):
    if (seller is None):
        return False
    global db
    for u in users:
        db.user_s(u, seller)


@app.post("/users_r")
def fa_p_users_r():
    global db
    return json.dumps(db.get_users(), cls=AlchemyEncoder)


# TODO: (errore) ogni volta che invia dati crea una nuova riga.

@app.post("/fatture_s")
def fa_p_fatture_s(fatture: list[API.Fattura], seller: str):
    global db
    f = []
    where = db.get_venditore_by_name(seller).id
    for p in fatture:
        old = db.get_fattura_by_local_id_and_where(p.id, where)
        if(old):
            if(old.local_id == p.id and old.where == where):
                continue
        f.append(DB_Service.Fattura(
        user=p.user, indirizzo=p.indirizzo, where=where, local_id=p.id))
    db.fatture_s(f)


@app.post("/fatture_prodotti_s")
def fa_p_fatture_prodotti_s(fatture: list[API.FatturaProdotto], seller: str):
    global db
    f = []
    where = db.get_venditore_by_name(seller).id
    for p in fatture:
        old = db.get_fattura_prodotto_by_local_id_and_where(p.id, where)
        ft = db.get_fattura_by_local_id_and_where(p.fattura, where)
        pr = db.get_product_by_local_id_and_where(p.prodotto, where)
        if(old):
            if(old.local_id == p.id and old.where == where):
                continue
        f.append(DB_Service.FatturaProdotto(fattura=ft.id, prodotto=pr.id,
                quantita=p.quantita, unitario=p.unitario, where=where, local_id=p.id))
    db.fatture_prodotti_s(f)


@app.get("/")
async def index(request: Request):
    global templates
    active_sellers = []
    for sl in db.get_sellers():
        try:
            r = requests.get(f"http://localhost:{sl.port}/status")
            if (r is None):
                continue
            active_sellers.append(sl)
        except:
            continue

    return templates.TemplateResponse("status.html", {"request": request, "sellers": active_sellers})

@app.get("/admin")
async def admin():
    return FileResponse("www/main-admin.html")

@app.get("/admin/")
async def admin():
    return FileResponse("www/main-admin.html")

@app.get("/admin/login")
async def admin():
    return FileResponse("www/login.html")

@app.get("/api/fatture")
async def all_fatture(token):
    global db
    if(not API.is_user_admin(db, token)):
        return json.dumps([{"user" : "YOU ARE NOT", "oggetti": [{"nome": "", "count" : 0, "unitario" : 0}], "address" : "ADMIN"}])

    fatture = db.get_fatture()
    ret = []
    for r in fatture:
        fp = db.get_fatture_prodotti_by_fattura_id(r.id)
        fpj = []
        for g in fp:
            p = db.get_product_by_id(g.prodotto)
            fpj.append({"nome" : p.nome, "count" : g.quantita, "unitario" : g.unitario})
            us = db.get_user_by_user(r.user)
            sl = db.get_seller_by_id(r.where)
        ret.append({"user" : f"{us.user} ({us.id})", "address": r.indirizzo, "oggetti": fpj, "dove" : sl.nome})
        if(ret.__len__() > 9): break
    return json.dumps(ret)

@app.post("/api/users/login")
def api_users_login(login: API.Login):
    user = login.user
    password = login.password
    if(user is None or password is None): return False

    global db
    lg, ad = db.login(user, password)
    if(lg is None):
        return {"status" : "bad"}
    return {"status" : "ok", "token" : lg, "admin" : ad}

@app.post("/api/users/check_session")
def api_users_check_session(token: API.Token):
    token = token.token
    if(token is None): return {"status" : "no token"}
    
    global db
    if(db.check_session(token)):
        return {"status" : "ok"}
    return {"status" : "bad"}


app.mount("/static", StaticFiles(directory="www"), name="www")


class SellerClient():
    nome: str
    port: int
    client: httpx.AsyncClient = None

    def __init__(self, nome, port, client=None) -> None:
        self.nome = nome
        self.port = port
        self.client = client

    def __repr__(self) -> str:
        return f"{self.nome} @ {self.port}"


async def _reverse_proxy(request: StarletteRequest):
    global clients
    global db
    nome = request.url.path.split("/")[1]
    path = request.url.path.replace(f"/{nome}", "", 1)

    url = httpx.URL(path=path,
                    query=request.url.query.encode("utf-8"))
    
    if(nome == "favicon.ico"):
        return FileResponse("www/favicon.png")

    if (path.__len__() == 0):
        if(nome.endswith(".js") or nome.endswith(".html") or nome.endswith(".css")):
            return FileResponse(f"www/{nome}")
        return RedirectResponse(request.url.__str__() + "/")
    
    if (nome == "admin"):
        if(path.endswith(".js") or path.endswith(".html") or path.endswith(".css")):
            return FileResponse(f"www{path}")

    client = None
    for c in clients:
        if (c.nome == nome):
            client = c.client

    if (client is None):
        port = db.get_port(nome)
        try:
            client = httpx.AsyncClient(base_url=f"http://localhost:{port}/")
        except:
            return
        clients.append(SellerClient(nome, port, client))

    rp_req = client.build_request(request.method, url,
                                  headers=request.headers.raw,
                                  content=request.stream())

    rp_resp = await client.send(rp_req, stream=True)
    return StreamingResponse(
        rp_resp.aiter_raw(),
        status_code=rp_resp.status_code,
        headers=rp_resp.headers,
        background=BackgroundTask(rp_resp.aclose),
    )

app.add_route("/{path:path}",
              _reverse_proxy, ["GET", "POST"])


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=9000,
                log_level="info", reload=True)
