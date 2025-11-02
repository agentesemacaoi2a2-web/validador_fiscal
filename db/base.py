import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


DB_URL = os.getenv('DB_URL', 'sqlite:///./data/validador.db')
connect_args = {"check_same_thread": False} if DB_URL.startswith('sqlite') else {}
engine = create_engine(DB_URL, echo=False, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
Base = declarative_base()


# Cria pasta data se não existir
os.makedirs('data', exist_ok=True)