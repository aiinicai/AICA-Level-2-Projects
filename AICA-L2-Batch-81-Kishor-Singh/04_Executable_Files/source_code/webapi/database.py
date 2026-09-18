"""SQLAlchemy engine/session setup.

Defaults to a local SQLite file so the API runs with zero external
dependencies out of the box (development, testing, and small single-office
deployments). Point ``DATABASE_URL`` at a PostgreSQL connection string for
a real multi-user "Team Deployment" -- see the README. Using SQLite as a
*shared network* database for real concurrent multi-user access is
explicitly unsupported (SQLite has no real concurrent-writer story over a
network share); PostgreSQL is the supported path for that.
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


def _default_sqlite_url() -> str:
    data_dir = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "CADocuFlowAI"
    data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{data_dir / 'webapi.db'}"


DATABASE_URL = os.environ.get("DATABASE_URL", _default_sqlite_url())

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Real deployments should use Alembic migrations
    instead (see webapi/alembic/) -- this is a convenience for local/dev/test."""
    from webapi import models  # noqa: F401 - ensures models are registered on Base.metadata

    Base.metadata.create_all(bind=engine)
