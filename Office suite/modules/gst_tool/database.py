import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

MODULE_DIR = Path(__file__).resolve().parent
DB_PATH = MODULE_DIR / "gst_data.db"
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
    # Check if database tables need schema upgrade for expanded columns
    if DB_PATH.exists():
        try:
            with engine.connect() as conn:
                gst_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(gst_records)")).fetchall()]
                client_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(clients)")).fetchall()]
                
                if (gst_cols and "b2b_supplies" not in gst_cols) or (client_cols and "trade_name" not in client_cols):
                    print("[GST Tool DB] Upgrading database schema for expanded GSTR-1 and GSTR-3B columns...")
                    conn.execute(text("DROP TABLE IF EXISTS gst_records"))
                    conn.execute(text("DROP TABLE IF EXISTS ledger_records"))
                    conn.execute(text("DROP TABLE IF EXISTS clients"))
                    conn.commit()
        except Exception as e:
            print(f"[GST Tool DB] Migration check error: {e}")

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        try:
            from .models import Client
        except ImportError:
            from models import Client

        existing_client = db.query(Client).first()
        if not existing_client:
            default_client = Client(
                name="Acme Enterprises Private Limited",
                trade_name="Acme Solutions",
                gstin="27AAAAA0000A1Z5",
                status="Active",
                constitution="Private Limited Company",
                address="Plot No 42, Industrial Area Phase 1, Mumbai, Maharashtra 400001",
                registration_date="2017-07-01"
            )
            db.add(default_client)
            db.commit()
            db.refresh(default_client)
            print(f"[GST Tool DB] Created default client: ID {default_client.id} ({default_client.name})")
    except Exception as e:
        print(f"[GST Tool DB] Client seed info: {e}")
        db.rollback()
    finally:
        db.close()
