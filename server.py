from fastapi import FastAPI, status, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Boolean
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.exc import IntegrityError

from sys import argv

import uvicorn




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


@app.on_event("startup")
async def startup():
    global db
    db = DB_Service()


@app.get("/")
async def index():
    return FileResponse("www/index.html")

app.mount("/", StaticFiles(directory="www"), name="static")

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
        

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, log_level="info", reload=True)