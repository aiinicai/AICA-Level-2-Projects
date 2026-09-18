import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Org-chart traversal (manager -> junior chains) and the prompt-engine's
# recursive-descent date/intent parsing can nest deeper than Python's
# default limit on a large org tree - raise it up front.
sys.setrecursionlimit(10000)

# When packaged with PyInstaller, __file__ lives inside the temp extraction
# folder (sys._MEIPASS), which is wiped between runs - persistent data
# (database, backups, session secret) must live next to the .exe instead.
if getattr(sys, "frozen", False):
    APP_ROOT = os.path.dirname(sys.executable)
else:
    APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(APP_ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "company_os.db")

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
