"""SQLAlchemy 2.x setup. Identical models on SQLite and PostgreSQL (§1)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import USER_DATA_ROOT, get_settings


class Base(DeclarativeBase):
    """Declarative base. Alembic autogenerate targets this metadata."""


def _engine_kwargs(url: str) -> dict[str, Any]:
    if url.startswith("sqlite"):
        # check_same_thread=False is required because FastAPI serves requests
        # from a thread pool; each request still gets its own Session.
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}


def _fix_pysqlite_transactions(target: Engine) -> None:
    """Make SQLite transactions real.

    The pysqlite driver manages transactions itself and does not emit BEGIN
    for DML, so statements effectively autocommit and SAVEPOINT never nests
    inside anything. That matters here: versioning a client profile closes
    one row and inserts another, and a failure between the two must roll
    back both. Without this, it would leave the old profile closed and no
    current profile at all.

    The recipe is SQLAlchemy's documented one — disable the driver's implicit
    BEGIN, then emit it ourselves.
    """
    if target.dialect.name != "sqlite":
        return

    @event.listens_for(target, "connect")
    def _no_implicit_begin(dbapi_connection: Any, _record: Any) -> None:
        dbapi_connection.isolation_level = None

    @event.listens_for(target, "begin")
    def _explicit_begin(conn: Any) -> None:
        conn.exec_driver_sql("BEGIN")


def build_engine(url: str | None = None) -> Engine:
    settings = get_settings()
    resolved = url or settings.database_url
    if resolved.startswith("sqlite:///") and "memory" not in resolved:
        # Resolve the SQLite file relative to the project root, not the cwd,
        # so `python run.py` and `pytest` reach the same database.
        rel = Path(resolved.removeprefix("sqlite:///"))
        settings.data_path.mkdir(parents=True, exist_ok=True)
        resolved = f"sqlite:///{rel if rel.is_absolute() else (USER_DATA_ROOT / rel).resolve()}"
    built = create_engine(resolved, future=True, **_engine_kwargs(resolved))
    _fix_pysqlite_transactions(built)
    return built


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_connection: Any, _record: Any) -> None:
    """SQLite does not enforce foreign keys unless asked.

    Without this the 'PostgreSQL-compatible models' claim decays quietly:
    referential integrity bugs stay invisible in development and surface only
    after migration. Decision log item 2.

    The dialect is detected from the connection being opened, not from the
    module-level engine — tests and scripts build their own engines, and
    those need the pragma just as much.
    """
    if not type(dbapi_connection).__module__.startswith("sqlite3"):
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def get_session() -> Iterator[Session]:
    """FastAPI dependency. One session per request, always closed."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
