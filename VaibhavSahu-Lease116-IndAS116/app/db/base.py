from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .. import config


class Base(DeclarativeBase):
    pass


_engine = None
SessionLocal = sessionmaker(autoflush=False, expire_on_commit=False)


def get_engine():
    global _engine
    if _engine is None:
        config.ensure_dirs()
        url = config.db_url()
        kw = {}
        if url.startswith("sqlite"):
            kw["connect_args"] = {"check_same_thread": False, "timeout": 30}
        _engine = create_engine(url, future=True, **kw)
        if url.startswith("sqlite"):
            @event.listens_for(_engine, "connect")
            def _pragmas(dbapi_conn, _):  # pragma: no cover
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA foreign_keys=ON")
                cur.execute("PRAGMA journal_mode=WAL")
                cur.execute("PRAGMA synchronous=NORMAL")
                cur.close()
        SessionLocal.configure(bind=_engine)
    return _engine


def reset_engine(url: str | None = None):
    """Used by tests to point the app at a temporary database."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None
    if url:
        import os
        os.environ["LEASE116_DB_URL"] = url
    get_engine()


# columns added after the first release: (table, column, DDL type) — applied to existing databases on start-up
_ADDED_COLUMNS = [("leases", "inputs_changed_at", "DATETIME")]


def _ensure_columns(engine):
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    with engine.begin() as conn:
        for table, col, ddl in _ADDED_COLUMNS:
            if table in tables and col not in {c["name"] for c in insp.get_columns(table)}:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))


def init_db():
    from . import models  # noqa: F401
    eng = get_engine()
    Base.metadata.create_all(eng)
    _ensure_columns(eng)


@contextmanager
def session_scope():
    get_engine()
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def get_db():
    get_engine()
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()
