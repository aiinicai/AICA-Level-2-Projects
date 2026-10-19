import os
import sys
from typing import Optional, Dict, Any
from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app import company_manager

if getattr(sys, 'frozen', False):
    WORKSPACE_DIR = os.path.dirname(sys.executable)
else:
    WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_DB_FILE = os.path.join(WORKSPACE_DIR, "erp_ledger.db")

Base = declarative_base()

_engine_cache: Dict[str, Any] = {}
_sessionmaker_cache: Dict[str, Any] = {}

def get_engine_for_path(db_path: str):
    abs_path = os.path.abspath(db_path)
    if abs_path not in _engine_cache:
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        db_url = f"sqlite:///{abs_path}"
        eng = create_engine(
            db_url,
            connect_args={"check_same_thread": False}
        )
        # Create tables if not exist
        Base.metadata.create_all(bind=eng)
        _engine_cache[abs_path] = eng
        _sessionmaker_cache[abs_path] = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    return _engine_cache[abs_path]

def get_sessionmaker_for_path(db_path: str):
    abs_path = os.path.abspath(db_path)
    if abs_path not in _sessionmaker_cache:
        get_engine_for_path(abs_path)
    return _sessionmaker_cache[abs_path]

# Default primary engine and sessionmaker for scripts/lifespan
engine = get_engine_for_path(DEFAULT_DB_FILE)
SessionLocal = get_sessionmaker_for_path(DEFAULT_DB_FILE)

def resolve_db_path(request: Optional[Request] = None) -> str:
    if request:
        cid = request.headers.get("X-Company-Id") or request.query_params.get("company_id")
        if cid:
            comp = company_manager.get_company_by_id(cid)
            if comp and comp.get("db_file"):
                return comp["db_file"]
    
    # Active company from registry
    try:
        active = company_manager.get_active_company()
        if active and active.get("db_file"):
            return active["db_file"]
    except Exception:
        pass
        
    return DEFAULT_DB_FILE

def get_db(request: Request):
    db_path = resolve_db_path(request)
    sm = get_sessionmaker_for_path(db_path)
    db: Session = sm()
    try:
        yield db
    finally:
        db.close()
