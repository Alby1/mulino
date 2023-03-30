from fastapi import FastAPI, status, Response, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from starlette.requests import Request as StarletteRequest

from pydantic import BaseModel

from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import sessionmaker, declarative_base
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

    def is_user_admin(db, token):
        user = db.get_user_by_token(token)
        if(user is not None):
            if(user.admin is False):
                return False
        return True




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

    class Utente(Base):
        __tablename__ = 'utenti'
        id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
        user = Column(String(45), unique=True, nullable=False)
        password = Column(String(45), nullable=False)
        admin = Column(Boolean())
        token = Column(String(20), unique=True)

        def __repr__(self):
            return f"{self.user} {self.admin}"

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

        q = session.query(self.Prodotto)

        session.close()
        return q.all()
    
    def get_product_by_id(self, id):
        session = self.session()

        q = session.query(self.Prodotto).filter(self.Prodotto.id == id)

        return q.first()
    
    def add_product(self, product: Prodotto):
        session = self.session()
        try:
            session.add(product)
            session.commit()
            session.close()
            return "ok"
        except IntegrityError as e:
            return "product already exists"
        
    def update_product(self, id, nome = None, costo = None, quantita = None):
        s = self.session()
        q = s.query(self.Prodotto).filter(self.Prodotto.id == id).first()

        if nome is not None: q.nome = nome
        if costo is not None: q.prezzo = costo
        if quantita is not None: q.quantita = quantita

        s.commit()
        s.close()

        return "ok"

        
    def get_users(self):
        s = self.session()
        
        q = s.query(self.Utente)
        s.close()
        
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
        except: return False
            

    def user_exists(self, user):
        s = self.session()
        ret = False
        try:
            u = s.query(self.Utente).filter(self.Utente.user == user)
            if(u.count() != 0): ret = True
        except: ret = False
        try:
            s.close()
        except: pass

        return ret
    
    def get_user_by_token(self, token):
        s = self.session()
        q = s.query(self.Utente).filter(self.Utente.token == token)
        if(q.count() == 0): return None
        return q.first()
    
    def login(self, user, password):
        s = self.session()

        letters = string.ascii_lowercase
        result_str = ''.join(random.choice(letters) for i in range(20))

        w = s.query(self.Utente).filter(self.Utente.user == user).filter(self.Utente.password == password)

        u = w.first()

        if(w.count() == 0):
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

        s.close()

        
        return result_str, admin
    
    def check_session(self, token: str):
        if(token is None): return False
        s = self.session()

        q = s.query(self.Utente).filter(self.Utente.token == token)

        if(q.count() != 0):
            return True
        return False
        


def get_port():
    p = requests.get(f'http://localhost:9000/port?seller={argv[1]}')
    return int(p.text)

def sync_main():
    try:
        global db
        ps = db.get_products()
        data = json.dumps(ps, cls=AlchemyEncoder)

        r = requests.post(f"http://localhost:9000/products?seller={argv[1]}", data=data)

        us = db.get_users()
        data = json.dumps(us, cls=AlchemyEncoder)

        r = requests.post(f"http://localhost:9000/users_s?seller={argv[1]}", data=data)


        r = requests.post(f"http://localhost:9000/users_r", data=data)

        for u in json.loads(r.json()):
            try:
                db.add_user(u['user'], u['password'], u['admin'])
            except Exception as e:
                # print(e)
                pass
    except Exception as es:
        # print(es)
        print("can't sync")


def sync_thread():
    try:
        while True:
            sync_main()
            time.sleep(10)
    except KeyboardInterrupt:
        return
    


if __name__ == "__main__":
    port = get_port()
    uvicorn.run("seller:app", host="0.0.0.0", port=port, log_level="info", reload=True)
    