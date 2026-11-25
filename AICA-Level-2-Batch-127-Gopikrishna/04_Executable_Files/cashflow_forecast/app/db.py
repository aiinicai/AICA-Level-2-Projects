"""Database engine and session handling (SQLite via SQLAlchemy 2)."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def _sqlite_pragmas(dbapi_conn, _record) -> None:
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA journal_mode=WAL")   # readers do not block the writer (several users)
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA busy_timeout=5000")
    cur.close()


def _begin(conn) -> None:
    conn.exec_driver_sql("BEGIN")


def make_engine(url: str) -> Engine:
    eng = create_engine(url, connect_args={"check_same_thread": False}, future=True)
    event.listen(eng, "connect", _sqlite_pragmas)
    # pysqlite manages transactions itself, which breaks SAVEPOINT (used to roll back a rejected
    # import without losing its hash-log row). Documented SQLAlchemy workaround: let SQLAlchemy
    # emit BEGIN itself.
    event.listen(eng, "connect", lambda dbapi_conn, _r: setattr(dbapi_conn, "isolation_level", None))
    event.listen(eng, "begin", _begin)
    return eng


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        _engine = make_engine(get_settings().database_url)
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine


def reset_engine() -> None:
    """Used by tests to point at a fresh database."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def session_factory() -> sessionmaker:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


@contextmanager
def session_scope() -> Iterator[Session]:
    """Commit on success, roll back on error."""
    s = session_factory()()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency."""
    with session_scope() as s:
        yield s
