import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

MODULE_DIR = Path(__file__).resolve().parent
DB_PATH = MODULE_DIR / "wp_data.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)

    # Perform table schema migration check
    with engine.connect() as conn:
        try:
            res = conn.execute(text("PRAGMA table_info(fd_records)"))
            cols = [row[1] for row in res.fetchall()]
            if cols and "is_roll_forward" not in cols:
                print("[Working Papers DB] Migration: dropping outdated fd_records schema...")
                conn.execute(text("DROP TABLE fd_records"))
                conn.commit()
                Base.metadata.create_all(bind=engine)

            res2 = conn.execute(text("PRAGMA table_info(as26_entries)"))
            cols2 = [row[1] for row in res2.fetchall()]
            if not cols2:
                print("[Working Papers DB] Creating as26_entries table...")
                Base.metadata.create_all(bind=engine)

            res3 = conn.execute(text("PRAGMA table_info(wp_entities)"))
            cols3 = [row[1] for row in res3.fetchall()]
            if not cols3:
                print("[Working Papers DB] Creating wp_entities table...")
                Base.metadata.create_all(bind=engine)
        except Exception as e:
            print(f"[Working Papers DB] Migration check exception: {e}")
