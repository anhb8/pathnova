import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()  # loads backend/.env

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

# Engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,    # drops dead connections cleanly
    echo=True, 
    future=True
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Dependency to get a DB session per-request in FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
