import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL Connection String from Environment Variable
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://fsbuilder_user:password@localhost:5432/fsbuilder"
)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def create_db_engine(url: str):
    if "sqlite" in url:
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(
        url,
        pool_size=10,
        max_overflow=20,
        pool_recycle=1800,
        pool_pre_ping=True,
        echo=False
    )

try:
    engine = create_db_engine(DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
except Exception:
    # Dev Fallback if local PostgreSQL service is not active
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    FALLBACK_URL = f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}"
    engine = create_db_engine(FALLBACK_URL)
    DATABASE_URL = FALLBACK_URL

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_health():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            db_type = "SQLite (Dev Fallback)" if "sqlite" in str(engine.url) else "PostgreSQL"
            return {
                "status": "healthy" if result == 1 else "unhealthy",
                "database": db_type,
                "engine": str(engine.url).split("@")[-1] if "@" in str(engine.url) else str(engine.url),
                "pool_status": {
                    "pool_size": getattr(engine.pool, 'size', lambda: 1)(),
                    "checkedin": getattr(engine.pool, 'checkedin', lambda: 1)(),
                    "overflow": getattr(engine.pool, 'overflow', lambda: 0)(),
                    "checkedout": getattr(engine.pool, 'checkedout', lambda: 0)()
                }
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "PostgreSQL",
            "error": str(e)
        }


