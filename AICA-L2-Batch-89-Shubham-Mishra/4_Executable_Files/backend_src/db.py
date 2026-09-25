"""
Database connection. Uses the real Postgres instance in production (Render
sets DATABASE_URL); falls back to a local SQLite file for development when
DATABASE_URL isn't set, so this can be built/tested before the Postgres
instance exists.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ca_practiceos_dev.db")

# Render's internal Postgres URLs start with postgres:// - SQLAlchemy 2.x
# requires the postgresql:// scheme.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
