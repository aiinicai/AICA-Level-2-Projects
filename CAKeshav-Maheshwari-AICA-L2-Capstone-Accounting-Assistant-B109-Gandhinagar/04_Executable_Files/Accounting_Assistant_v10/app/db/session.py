"""Engines and sessions.

Local SQLite is the working DB on every PC. Writes to SYNCED tables automatically
queue an Outbox row (via a before_flush hook) so they can be pushed to the LAN master.
"""
from __future__ import annotations

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import SYNCED_MODELS, Base, Outbox

_SYNCED_TABLES = {m.__tablename__ for m in SYNCED_MODELS}


def auto_migrate(eng: Engine) -> None:
    """Create new tables and add new columns to existing ones (additive changes only)."""
    Base.metadata.create_all(eng)
    insp = inspect(eng)
    with eng.begin() as conn:
        for table in Base.metadata.sorted_tables:
            have = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name not in have:
                    ddl = col.type.compile(dialect=eng.dialect)
                    conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {ddl}'))


def make_local_engine(url: str) -> Engine:
    eng = create_engine(url, future=True)

    @event.listens_for(eng, "connect")
    def _pragmas(dbapi_conn, _):  # WAL = safe concurrent reads on one PC
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    auto_migrate(eng)
    return eng


def make_remote_engine(url: str, password: str | None = None, connect_timeout: int = 3) -> Engine:
    if password and "@" in url and ":" not in url.split("//", 1)[1].split("@", 1)[0]:
        scheme, rest = url.split("//", 1)
        user, host = rest.split("@", 1)
        url = f"{scheme}//{user}:{password}@{host}"
    if url.startswith("postgresql+pg8000"):
        args = {"timeout": connect_timeout}
    elif url.startswith("postgresql"):
        args = {"connect_timeout": connect_timeout}
    else:
        args = {}
    eng = create_engine(url, future=True, pool_pre_ping=True, connect_args=args)
    auto_migrate(eng)
    return eng


def is_reachable(engine: Engine | None) -> bool:
    if engine is None:
        return False
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def local_sessionmaker(engine: Engine, actor: str) -> sessionmaker:
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    @event.listens_for(factory, "before_flush")
    def _queue_outbox(session: Session, *_):
        if session.info.get("syncing"):
            return
        for obj in list(session.new) + list(session.dirty):
            table = getattr(obj, "__tablename__", None)
            if table in _SYNCED_TABLES:
                if not getattr(obj, "updated_by", None):
                    obj.updated_by = actor
                if obj.id is None:
                    from .models import new_id
                    obj.id = new_id()
                session.add(Outbox(table=table, row_id=obj.id))

    return factory
