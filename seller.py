from fastapi import FastAPI, status, Response, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from starlette.requests import Request as StarletteRequest

from pydantic import BaseModel

from sqlalchemy import ForeignKey, create_engine, Column, Integer, String, Boolean
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import DeclarativeMeta

from sys import argv

import uvicorn

import requests

import json

import threading

import time

import random

import string


class AlchemyEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj.__class__, DeclarativeMeta):
            # an SQLAlchemy class
            fields = {}
            for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
                data = obj.__getattribute__(field)
                try:
                    json.dumps(data) # this will fail on non-encodable values, like other classes
                    fields[field] = data
                except TypeError:
                    fields[field] = None
            # a json-encodable dict
            return fields

        return json.JSONEncoder.default(self, obj)


class API():
    class Login(BaseModel):
        user: str
        password: str

    class Token(BaseModel):
        token: str

    class Product(BaseModel):
        id: int = None
        nome: str = None
        costo: int = None 
        quantita: int = None

        token: str = None
        count: int = None
        address: str = None

    class Fattura(BaseModel):
        id: int = None
        user: str = None
        indirizzo: str = None

    

    def is_user_admin(db, token):
        if(token == "null"): return False
        user = db.get_user_by_token(token)
        if(user is not None):
            return user.admin
        return False




app = FastAPI()

origins = ["*"]

app.add_middleware(CORSMiddleware, allow_origins=origins)


@app.get("/api/products/")
async def api_products(response: Response, id : int = None): # type: ignore
    global db
    if(id is None):
        return db.get_products()
    
    return db.get_product_by_id(id)


@app.post("/api/products/add")
async def api_products_add(product : API.Product, response: Response):
    nome = product.nome
    prezzo = product.costo
    quantita = product.quantita
    token = product.token

    global db
    
    if(not API.is_user_admin(db, token)): response.status_code == status.HTTP_400_BAD_REQUEST

    if(nome is None or prezzo is None):
        response.status_code = status.HTTP_400_BAD_REQUEST
    
    return db.add_product(DB_Service.Prodotto(nome=nome, prezzo=prezzo, quantita=quantita))

@app.post("/api/products/update")
async def api_products_update(product : API.Product, response: Response):
    global db
    token = product.token
    
    if(not API.is_user_admin(db, token)): 
        response.status_code == status.HTTP_400_BAD_REQUEST
        return "user is not admin"
    
    nome = product.nome
    prezzo = product.costo
    quantita = product.quantita
    id = product.id

    return db.update_product(id, nome, prezzo, quantita)


@app.get("/api/products/delete")
async def api_products_delete(id: int, token: str = None):
    global db
    if(token == "undefined"):
        return "no token provided"
    if(API.is_user_admin(db, token)):
        return db.delete_product(id)
    return "user is not admin"

@app.get("/api/products/availability")
async def api_products_availability(id: int = None):
    global db
    if(id == None):
        return "no id provided"

    pr = db.get_product_by_id(id)
    return pr.quantita

@app.post("/api/products/buy")
async def api_products_buy(products: list[API.Product]):
    global db

    if products.__len__() == 0:
        return "product list is empty"
    
    if(not db.check_session(products[0].token)):
        return "token not valid"
    
    fattura = db.add_fattura(db.get_user_by_token(products[0].token).id, products[0].address )
    if fattura:
        for pr in products:
            prdb = db.get_product_by_id(pr.id)
            if(prdb.quantita - pr.count <= 0):
                return f"troppi {pr.nome}, massimo è {prdb.quantita}"
            
            db.add_fattura_prodotto(fattura, pr.id, pr.count, prdb.prezzo)
            prdb.quantita -= pr.count
            db.update_product(product=prdb)

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
        ret.append({"user" : f"{us.user} ({us.id})", "address": r.indirizzo, "oggetti": fpj})
    return json.dumps(ret)


@app.get("/location")
async def location():
    return argv[1]

@app.get("/api/users")
def all_users(token : str):
    global db
    if(API.is_user_admin(db, token)):
        return json.dumps(db.get_users(), cls=AlchemyEncoder) 
    return json.dumps([{"user" : "YOU ARE NOT", "admin" : True}])

@app.post("/api/users/login")
def api_users_login(login: API.Login):
    user = login.user
    password = login.password
    if(user is None or password is None): return False

    global db
    lg, ad = db.login(user, password)
    if(not lg):
        return {"status" : "bad", "message" : ad}
    return {"status" : "ok", "token" : lg, "admin" : ad}


@app.post("/api/users/check_session")
def api_users_check_session(token: API.Token):
    token = token.token
    if(token is None): return {"status" : "no token"}
    
    global db
    if(db.check_session(token)):
        return {"status" : "ok"}
    return {"status" : "bad"}

@app.post("/api/users/register")
def api_users_register(register : API.Login):
    global db
    ok = db.add_user(register.user, register.password, False)
    if ok : return {"status" : "ok"}
    return {"status" : "bad"}

@app.get("/api/users/already_exists")
def api_users_already_exists(user: str):
    global db
    return db.user_exists(user)



@app.get("/status")
def service_status():
    return True


@app.on_event("startup")
async def startup():
    global db
    db = DB_Service()
    global th
    th = threading.Thread(target=sync_thread)
    th.start()
    global templates
    templates = Jinja2Templates(directory="www")


@app.get("/")
async def index():
    return FileResponse("www/index.html")


@app.exception_handler(FileNotFoundError)
async def file_not_found(request: Request, exc):
    return FileResponse("www/404.html")

@app.get("/{path:path}", response_class=FileResponse)
async def index_(request: Request):
    global templates
    path = request.url.path.replace("/", "", 1)
    if(path == "api.js"):
        return templates.TemplateResponse(path, {"request" : request, "venditore" : argv[1]})
    return FileResponse(f"www/{path}")




class DB_Service():
    Base = declarative_base()

    class Prodotto(Base):
        __tablename__ = 'prodotti'
        id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
        nome = Column(String(45), nullable=False, unique=True)
        prezzo = Column(INTEGER(unsigned=True), nullable=False)
        quantita = Column(INTEGER(unsigned=True), nullable=False)

        fattureprodotti_ = relationship("FatturaProdotto", back_populates="prodotto_")

    class Utente(Base):
        __tablename__ = 'utenti'
        id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
        user = Column(String(45), unique=True, nullable=False)
        password = Column(String(45), nullable=False)
        admin = Column(Boolean())
        token = Column(String(20), unique=True)

        fatture_ = relationship("Fattura", back_populates="utente_")

        def __repr__(self):
            return f"{self.user} {self.admin}"
        
    class Fattura(Base):
        __tablename__ = 'fatture'
        id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
        user = Column(String(45), ForeignKey("utenti.user"), nullable=False)
        indirizzo = Column(String(40), nullable=False)

        utente_ = relationship("Utente", back_populates="fatture_")
        fattureprodotti_ = relationship("FatturaProdotto", back_populates="fattura_")

    class FatturaProdotto(Base):
        __tablename__ = 'fatture_prodotti'
        id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
        fattura = Column(Integer, ForeignKey("fatture.id"))
        prodotto = Column(Integer, ForeignKey("prodotti.id"))
        quantita = Column(Integer, nullable=False)
        unitario = Column(Integer, nullable=False)

        fattura_ = relationship("Fattura", back_populates="fattureprodotti_")
        prodotto_ = relationship("Prodotto", back_populates="fattureprodotti_")

    def __init__(self):
        self.protocol = "mysql+pymysql"
        self.host = "localhost"
        self.port = 3306
        self.user = "mulino"
        self.password = "mulino"
        self.name = f"mulino_{argv[1]}"
        if not database_exists(f"{self.protocol}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"):
            create_database(f"{self.protocol}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}")
        
        self.engine = create_engine(f"{self.protocol}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}", echo=False, pool_size=10, max_overflow=20)
            
        self.Base.metadata.create_all(self.engine)

    def session(self):
        return sessionmaker(bind=self.engine)()

    def get_products(self):
        session = self.session()

        try:
            q = session.query(self.Prodotto)
        except: pass
        finally: session.close()

        return q.all()
    
    def get_product_by_id(self, id) -> Prodotto:
        session = self.session()
        try:
            q = session.query(self.Prodotto).filter(self.Prodotto.id == id)
        except:pass
        finally: session.close()

        return q.first()
    
    def add_product(self, product: Prodotto):
        session = self.session()
        try:
            session.add(product)
            session.commit()
            return "ok"
        except IntegrityError as e: return "product already exists"
        finally: session.close()
        
    def update_product(self, id: int = None, nome : str = None, costo : int = None, quantita : int = None, product : API.Product = None):
        s = self.session()
        try:
            if product is not None:
                id = product.id
            q = s.query(self.Prodotto).filter(self.Prodotto.id == id).first()

            if product is not None:
                q.nome = product.nome
                q.prezzo = product.prezzo
                q.quantita = product.quantita

            if nome is not None: q.nome = nome
            if costo is not None: q.prezzo = costo
            if quantita is not None: q.quantita = quantita

            s.commit()
        except: pass
        finally: s.close()

        return "ok"
    
    def delete_product(self, id):
        s = self.session()
        try:
            u = s.query(self.Prodotto).filter(self.Prodotto.id == id).first()
            s.merge(u)
            s.delete(u)
            s.commit()
        except Exception as e: print(e)
        finally: s.close()
        return "ok"
    


    def add_fattura(self, user : int = None, indirizzo : str = None, fattura : Fattura = None) -> int:
        s = self.session()
        
        i = False
        try:
            if user is not None:
                
                f = self.Fattura(user=db.get_user_by_id(user).user, indirizzo=indirizzo)
                s.add(f)
                s.commit()
                i = f.id
        
            if fattura is None:
                return "no data"
            
            s.add(fattura)
            s.commit()
            i = fattura.id
        except: pass
        finally: 
            s.close()
            return i
        
    def add_fattura_prodotto(self, fattura: int, prodotto: int, quantita: int, unitario: int):
        s = self.session()

        i = False
        try:
            fp = self.FatturaProdotto(fattura=fattura, prodotto=prodotto, quantita=quantita, unitario=unitario)
            s.add(fp)
            s.commit()
            i = fp.id
        except Exception as e: pass
        finally:
            s.close()
            return i
        
    def get_fatture(self) -> list[Fattura]:
        s = self.session()
        f = s.query(self.Fattura)
        s.close()
        return f.all()
    
    def get_fatture_prodotti(self) -> list[FatturaProdotto]:
        s = self.session()
        f = s.query(self.FatturaProdotto)
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
    

        
    def get_users(self):
        s = self.session()
        try:
            q = s.query(self.Utente)
        except: pass
        finally: s.close()
        
        return q.all()
    
    def add_user(self, user, password, admin):
        try:
            s = self.session()
            u = self.Utente(user = user, password = password, admin = admin)
            s.add(u)
            s.commit()
            i = u.id
            s.close()
            return i
        except: 
            s.close()
            return False
            

    def user_exists(self, user):
        s = self.session()
        ret = False
        try:
            u = s.query(self.Utente).filter(self.Utente.user == user)
            if(u.count() != 0): ret = True
        except: ret = False
        finally: s.close()

        return ret
    
    def get_user_by_token(self, token):
        s = self.session()
        try:
            q = s.query(self.Utente).filter(self.Utente.token == token)
        except: pass
        finally: s.close()
        if(q.count() == 0): return None
        return q.first()
    
    def login(self, user: str, password: str):
        s = self.session()
        if(user.__len__() == 0): return False, "Nome utente vuoto"
        if(password.__len__() == 0): return False, "Password vuota"
        if(not db.user_exists(user)): return False, "Utente inesistente"
        try:
            letters = string.ascii_lowercase
            result_str = ''.join(random.choice(letters) for i in range(20))

            w = s.query(self.Utente).filter(self.Utente.user == user).filter(self.Utente.password == password)

            u = w.first()

            if(w.count() == 0):
                s.close()
                return False, "Password incorretta"

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


MAIN_PORT = 9400

def get_port():
    p = requests.get(f'http://localhost:{MAIN_PORT}/port?seller={argv[1]}')
    return int(p.text)

def sync_main():
    try:
        global db
        ps = db.get_products()
        data = json.dumps(ps, cls=AlchemyEncoder)
        r = requests.post(f"http://localhost:{MAIN_PORT}/products?seller={argv[1]}", data=data)

        us = db.get_users()
        data = json.dumps(us, cls=AlchemyEncoder)

        r = requests.post(f"http://localhost:{MAIN_PORT}/users_s?seller={argv[1]}", data=data)


        r = requests.post(f"http://localhost:{MAIN_PORT}/users_r", data=data)

        for u in json.loads(r.json()):
            try:
                db.add_user(u['user'], u['password'], u['admin'])
            except Exception as e:
                # print(e)
                pass

        data = json.dumps(db.get_fatture(), cls=AlchemyEncoder)
        r = requests.post(f"http://localhost:{MAIN_PORT}/fatture_s?seller={argv[1]}", data=data)

        data = json.dumps(db.get_fatture_prodotti(), cls=AlchemyEncoder)
        r = requests.post(f"http://localhost:{MAIN_PORT}/fatture_prodotti_s?seller={argv[1]}", data=data)
    except Exception as es:
        print(es)
        print("can't sync")


def sync_thread():
    try:
        while True:
            sync_main()
            time.sleep(5)
    except KeyboardInterrupt:
        return
    


if __name__ == "__main__":
    port = get_port()
    uvicorn.run("seller:app", host="0.0.0.0", port=port, log_level="info", reload=True)
    