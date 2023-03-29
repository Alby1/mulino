from fastapi import FastAPI, status, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Boolean
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




app = FastAPI()

origins = ["*"]

app.add_middleware(CORSMiddleware, allow_origins=origins)


@app.get("/api/products/")
async def api_products(response: Response, id : int = None):
    global db
    if(id is None):
        return db.get_products()
    
    return db.get_product_by_id(id)


@app.get("/api/products/add")
async def api_products_add(nome : str, prezzo: int, response : Response, quantita: int = None):

    if(nome is None or prezzo is None):
        response.status_code = status.HTTP_400_BAD_REQUEST
    
    global db
    return db.add_product(DB_Service.Prodotto(nome=nome, prezzo=prezzo, quantita=quantita))

@app.get("/location")
async def location():
    return argv[1]

@app.get("/api/users/login")
def api_users_login(user: str, password: str):
    if(user is None or password is None): return False

    global db
    if(db.login(user, password)):
        return {"status" : "ok"}
    return {"status" : "bad"}


@app.on_event("startup")
async def startup():
    global db
    db = DB_Service()
    global th
    th = threading.Thread(target=sync_thread)
    th.start()


@app.get("/")
async def index():
    return FileResponse("www/index.html")

app.mount("/", StaticFiles(directory="www"), name="static")

@app.get("/status")
async def service_status():
    return True


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
        token = Column(String(20))

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
        
    def get_users(self):
        s = self.session()
        
        q = s.query(self.Utente)
        s.close()
        
        return q.all()
    
    def add_user(self, user, password, admin):
        s = self.session()
        u = self.Utente(user = user, password = password, admin = admin)
        s.add(u)
        s.commit()
        i = u.id
        s.close()
        return i
    
    def login(self, user, password):
        s = self.session()

        letters = string.ascii_lowercase
        result_str = ''.join(random.choice(letters) for i in range(20))

        w = s.query(self.Utente).filter(self.Utente.user == user).filter(self.Utente.password == password)

        u = w.first()

        u.token = result_str

        ret = False

        if(w.count() != 0):
            return True
        
        return result_str
        


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
    except:
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
    