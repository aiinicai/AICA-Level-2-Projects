from contextvars import ContextVar
from pathlib import Path
from typing import Dict, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from starlette.requests import Request

from app.core.config import settings

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False, "timeout": 30} if _is_sqlite else {}
_engine_kwargs = {"connect_args": connect_args, "echo": False}
if _is_sqlite:
    _engine_kwargs["poolclass"] = NullPool

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

_active_client_slug: ContextVar[str] = ContextVar("active_client_slug", default="")
_engine_cache: Dict[str, Engine] = {}


def set_active_client_slug(slug: str):
    return _active_client_slug.set(slug or "")


def reset_active_client_slug(token) -> None:
    _active_client_slug.reset(token)


def get_active_client_slug() -> str:
    return _active_client_slug.get() or ""


def dispose_sqlite_engine(db_path: Path) -> None:
    key = str(db_path.resolve())
    cached = _engine_cache.pop(key, None)
    if cached is None:
        return
    try:
        with cached.connect() as conn:
            conn.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)")
    except Exception:
        pass
    cached.dispose()


def dispose_all_sqlite_engines() -> None:
    engines = list(_engine_cache.values())
    _engine_cache.clear()
    for cached in engines:
        try:
            with cached.connect() as conn:
                conn.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass
        try:
            cached.dispose()
        except Exception:
            pass


def engine_for_sqlite(db_path: Path) -> Engine:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    key = str(db_path.resolve())
    cached = _engine_cache.get(key)
    if cached is not None:
        return cached
    url = URL.create(drivername="sqlite", database=str(db_path.resolve()))
    created = create_engine(
        url,
        connect_args={"check_same_thread": False, "timeout": 30},
        poolclass=NullPool,
        echo=False,
    )
    _engine_cache[key] = created
    return created


def current_engine(preferred: str = "") -> Engine:
    from app.services.client_store import get_client, is_testing, list_clients, resolve_active_slug

    if is_testing() or not list_clients():
        return engine
    slug = resolve_active_slug(preferred or get_active_client_slug())
    client = get_client(slug)
    if not client:
        return engine
    from app.services.client_store import client_db_path
    return engine_for_sqlite(client_db_path(client))


def get_db(request: Request):
    slug = getattr(request.state, "client_slug", "") or get_active_client_slug()
    Session = sessionmaker(autocommit=False, autoflush=False, bind=current_engine(slug))
    db = Session()
    try:
        yield db
    finally:
        db.close()
