# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Database engine, session factory and ``init_db()`` for LeaseIQ Pro.

The default database is the SQLite file ``leaseiq.db`` in the project root.
Set ``LEASEIQ_DB_URL`` (e.g. in ``.env``) to point somewhere else; tests pass an
explicit ``db_url`` so they never touch the real database.

No Streamlit imports belong in this module.
"""
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from db.models import Base

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "leaseiq.db"

_engines: dict = {}


def get_database_url() -> str:
    """Return the configured database URL (env override, else local SQLite file)."""
    load_dotenv()
    return os.getenv("LEASEIQ_DB_URL") or "sqlite:///{}".format(DEFAULT_DB_PATH.as_posix())


def get_engine(db_url: Optional[str] = None) -> Engine:
    """Return a cached Engine for ``db_url`` (default: the configured database)."""
    url = db_url or get_database_url()
    if url not in _engines:
        connect_args = {}
        if url.startswith("sqlite"):
            # Streamlit runs scripts on multiple threads.
            connect_args["check_same_thread"] = False
        engine = create_engine(url, connect_args=connect_args)

        if engine.dialect.name == "sqlite":
            @event.listens_for(engine, "connect")
            def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        _engines[url] = engine
    return _engines[url]


def init_db(db_url: Optional[str] = None) -> Engine:
    """Create every table (idempotent) and return the Engine.

    With no argument this creates/opens ``leaseiq.db`` in the project root.
    """
    engine = get_engine(db_url)
    Base.metadata.create_all(engine)
    add_missing_columns(engine)
    return engine


# Columns added after a table was first created: ``create_all`` never alters an existing table, so an
# existing database gets them here. Each is a plain nullable column, which SQLite adds safely in place.
COLUMN_ADDITIONS = (
    ("lease_cases", "rejection_reason", "TEXT"),
    ("user_preferences", "theme", "VARCHAR(10) NOT NULL DEFAULT 'light'"),
    ("user_preferences", "dashboard_layout", "VARCHAR(20) NOT NULL DEFAULT 'classic'"),
    ("audit_logs", "lease_ref", "VARCHAR(50)"),
    ("users", "workspace_id", "INTEGER REFERENCES users(user_id)"),
    ("users", "access_level", "VARCHAR(20)"),
    ("users", "created_by", "INTEGER REFERENCES users(user_id)"),
    ("users", "must_change_password", "BOOLEAN NOT NULL DEFAULT 0"),
)


def add_missing_columns(engine: Engine) -> list:
    """Add any column in COLUMN_ADDITIONS that the database does not have yet. Returns what was added."""
    added = []
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    for table, column, sql_type in COLUMN_ADDITIONS:
        if table in tables and column not in {c["name"] for c in inspector.get_columns(table)}:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE {} ADD COLUMN {} {}".format(table, column, sql_type)))
            added.append("{}.{}".format(table, column))
    return added


def get_session(engine: Optional[Engine] = None) -> Session:
    """Return a new Session. Use as a context manager: ``with get_session() as s:``."""
    return Session(engine or get_engine(), expire_on_commit=False)
