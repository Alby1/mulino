import uvicorn

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Boolean, desc
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from sqlalchemy.ext.declarative import DeclarativeMeta


from pydantic import BaseModel

import json

import requests

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
    class Product(BaseModel):
        id: int
        nome : str
        quantita : int
        prezzo : int
        registry: str | None

    class User(BaseModel):
        id: int
        user: str
        password: str
        admin: bool
        registry: str | None

class DB_Service():
    Base = declarative_base()
    
    class Prodotto(Base):
        __tablename__ = 'prodotti'
        id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
        nome = Column(String(45), nullable=False, unique=True)
        prezzo = Column(INTEGER(unsigned=True), nullable=False)
        quantita = Column(INTEGER(unsigned=True), nullable=False)
        where = Column(Integer, ForeignKey("venditori.id"))

        venditore_ = relationship("Seller", back_populates="prodotti_")

    class Utente(Base):
        __tablename__ = 'utenti'
        id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
        user = Column(String(45), unique=True, nullable=False)
        password = Column(String(45), nullable=False)
        admin = Column(Boolean())
        where = Column(Integer, ForeignKey("venditori.id"))

        venditore_ = relationship("Seller", back_populates="utenti_")


    class Seller(Base):
        __tablename__ = 'venditori'
        id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
        nome = Column(String(20), nullable=False, unique=True)
        port = Column(Integer, unique=True, nullable=False)

        prodotti_ = relationship("Prodotto", back_populates="venditore_")
        utenti_ = relationship("Utente", back_populates="venditore_")


    def __init__(self):
        self.protocol = "mysql+pymysql"
        self.host = "localhost"
        self.port = 3306
        self.user = "mulino"
        self.password = "mulino"
        self.name = f"mulino_main"
        if not database_exists(f"{self.protocol}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"):
            create_database(f"{self.protocol}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}")
        
            self.engine = create_engine(f"{self.protocol}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}", echo=False, pool_size=10, max_overflow=20)
                
            self.Base.metadata.create_all(self.engine)

            self.add_user("admin", "admin", True)

            return

        self.engine = create_engine(f"{self.protocol}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}", echo=False, pool_size=10, max_overflow=20)
            
        self.Base.metadata.create_all(self.engine)

    def session(self) -> Session:
        return sessionmaker(bind=self.engine)()
    
    def get_port(self, seller):
        s = self.session()

        q = s.query(self.Seller)

        if(q.count() != 0): return q.filter(self.Seller.nome == seller).first().port
        
        a = s.query(self.Seller).order_by(desc(self.Seller.port))
        p = 9000
        
        if(a.count() != 0): p = int(a.first().port)
        p += 1
        sl = self.Seller(nome=seller, port = p )
        s.add(sl)
        s.commit()
        s.close()

        return p
    
    def prodotto_s(self, p : API.Product, seller : str):
        s = self.session()

        w = s.query(self.Seller).filter(self.Seller.nome == seller).first().id
        try:
            q = s.query(self.Prodotto).filter(self.Prodotto.where == w).filter(self.Prodotto.nome == p.nome)
            m = q.first()
            m.prezzo = p.prezzo
            m.quantita = p.quantita
            s.commit()

        except:
            pa = self.Prodotto(nome = p.nome, quantita=p.quantita, prezzo=p.prezzo, where = w)

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
            q = s.query(self.Utente).filter(self.Utente.where == w).filter(self.Utente.user == p.user)
            if(q.count != 0): 
                m = q.first()
                m.user = p.user
                m.password = p.password
                m.admin = p.admin

                s.commit()
                i = m.id
                s.close()

        except:
            try:
                ua = self.Utente(user = p.user, password = p.password, admin = p.admin, where = w)

                s.add(ua)
                s.commit()
                i = ua.id
                s.close()
            except: pass

        return i
        
    def get_users(self):
        s = self.session()

        q = s.query(self.Utente)

        s.close()

        return q.all()
    
    def add_user(self, username, password, admin = None, where = None):
        s = self.session()

        u = self.Utente(user = username, password = password, admin = admin, where = where)
        
        s.add(u)
        s.commit()
        i = u.id
        s.close()
        return i
    

    def get_sellers(self):
        s = self.session()

        ss = s.query(self.Seller)

        return ss.all()
        

app = FastAPI()

origins = ["*"]

app.add_middleware(CORSMiddleware, allow_origins=origins)

@app.on_event("startup")
async def startup():
    global db
    db = DB_Service()
    global templates
    templates = Jinja2Templates(directory="www")


@app.get("/port")
def fa_port(seller: str = None):
    if(seller is None): return "no seller provided"
    global db
    return db.get_port(seller)


@app.post("/products")
def fa_p_products(products: list[API.Product], seller : str | None = None):
    if(seller is None): return False
    global db
    for p in products:
        db.prodotto_s(p, seller)

@app.post("/users_s")
def fa_p_users(users: list[API.User], seller : str | None = None):
    if(seller is None): return False
    global db
    for u in users:
        db.user_s(u, seller)


@app.post("/users_r")
def fa_p_users_r():
    global db
    return json.dumps(db.get_users(), cls=AlchemyEncoder)


@app.get("/")
def index(request: Request):
    global db
    sellers = db.get_sellers()
    sr = []
    for s in sellers:
        try:
            requests.get(f"http://localhost:{s.port}/status")
            sr.append(s)
        except:
            pass
    global templates
    return templates.TemplateResponse("status.html", {"request" : request, "sellers" : sr})


app.mount("/static", StaticFiles(directory="www"), name="www")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=9000, log_level="info", reload=True)
    