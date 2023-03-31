import uvicorn

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

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

    class User(BaseModel):
        id: int
        user: str
        password: str
        admin: bool
        registry: str | None

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

        venditore_ = relationship("Seller", back_populates="prodotti_")
        fattureprodotti_ = relationship(
            "FatturaProdotto", back_populates="prodotto_")

    class Utente(Base):
        __tablename__ = 'utenti'
        id = Column(Integer, primary_key=True,
                    nullable=False, autoincrement=True)
        user = Column(String(45), unique=True, nullable=False)
        password = Column(String(45), nullable=False)
        admin = Column(Boolean())
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
        user = Column(Integer, ForeignKey("utenti.id"), nullable=False)
        indirizzo = Column(String(40), nullable=False)
        where = Column(Integer, ForeignKey("venditori.id"))

        venditore_ = relationship("Seller", back_populates="fatture_")
        utente_ = relationship("Utente", back_populates="fatture_")
        fattureprodotti_ = relationship(
            "FatturaProdotto", back_populates="fattura_")

    class FatturaProdotto(Base):
        __tablename__ = 'fatture_prodotti'
        id = Column(Integer, primary_key=True,
                    nullable=False, autoincrement=True)
        fattura = Column(Integer, ForeignKey("fatture.id"))
        prodotto = Column(Integer, ForeignKey("prodotti.id"))
        quantita = Column(Integer, nullable=False)
        unitario = Column(Integer, nullable=False)
        where = Column(Integer, ForeignKey("venditori.id"))

        fattura_ = relationship("Fattura", back_populates="fattureprodotti_")
        prodotto_ = relationship("Prodotto", back_populates="fattureprodotti_")

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
                nome=p.nome, quantita=p.quantita, prezzo=p.prezzo, where=w)

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

    def fatture_prodotti_s(self, fatture: list[FatturaProdotto]):
        s = self.session()
        try:
            s.add_all(fatture)
            s.commit()
        except Exception as e:
            print(e)
        finally:
            s.close()

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
        f.append(DB_Service.Fattura(
            user=p.user, indirizzo=p.indirizzo, where=where))
    db.fatture_s(f)


@app.post("/fatture_prodotti_s")
def fa_p_fatture_prodotti_s(fatture: list[API.FatturaProdotto], seller: str):
    global db
    f = []
    where = db.get_venditore_by_name(seller).id
    for p in fatture:

        f.append(DB_Service.FatturaProdotto(fattura=p.fattura, prodotto=p.prodotto,
                 quantita=p.quantita, unitario=p.unitario, where=where))
    db.fatture_prodotti_s(f)


@app.get("/")
def index(request: Request):
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

    if (path.__len__() == 0):
        return RedirectResponse(request.url.__str__() + "/")

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
