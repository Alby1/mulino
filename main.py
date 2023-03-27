import uvicorn

from fastapi import FastAPI, status, Response, Body
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse


from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Boolean, desc
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from sqlalchemy.exc import IntegrityError

from typing import Annotated

from pydantic import BaseModel


class API():
    class Product(BaseModel):
        id: int
        nome : str
        quantita : int
        prezzo : int
        registry: str | None

class DB_Service():
    Base = declarative_base()
    
    class Prodotto(Base):
        __tablename__ = 'prodotti'
        id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
        nome = Column(String(45), nullable=False, unique=True)
        prezzo = Column(INTEGER(unsigned=True), nullable=False)
        quantita = Column(INTEGER(unsigned=True), nullable=False)
        where = Column(Integer, ForeignKey("venditori.id"), nullable=False)

        venditore_ = relationship("Seller", back_populates="prodotti_")

    class Utente(Base):
        __tablename__ = 'utenti'
        id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
        user = Column(String(45), unique=True, nullable=False)
        password = Column(String(45), nullable=False)
        admin = Column(Boolean())

    class Seller(Base):
        __tablename__ = 'venditori'
        id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
        nome = Column(String(20), nullable=False, unique=True)
        port = Column(Integer, unique=True, nullable=False)

        prodotti_ = relationship("Prodotto", back_populates="venditore_")


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

    def session(self) -> Session:
        return sessionmaker(bind=self.engine)()
    
    def get_port(self, seller):
        s = self.session()

        q = s.query(self.Seller)

        if(q.count() != 0): return q.filter(self.Seller.nome == seller).first().port
        
        a = s.query(self.Seller).order_by(desc(self.Seller.port))
        p = 9001
        print(a.count())
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
        

app = FastAPI()

origins = ["*"]

app.add_middleware(CORSMiddleware, allow_origins=origins)

@app.on_event("startup")
async def startup():
    global db
    db = DB_Service()


@app.get("/port")
def fa_port(seller: str = None):
    if(seller is None): return "no seller provided"
    global db
    return db.get_port(seller)


@app.post("/products")
def fa_p_products(products: list[API.Product], seller : str | None = None):
    global db
    for p in products:
        db.prodotto_s(p, seller)



if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=9000, log_level="info", reload=True)
    