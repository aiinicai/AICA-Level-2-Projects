"""Hardened SQLite connection and transaction helpers."""
from __future__ import annotations

import contextlib
import sqlite3
import uuid
from pathlib import Path
from typing import Iterator

from app.core.errors import StorageError


def connect(database_path: Path | str) -> sqlite3.Connection:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        connection = sqlite3.connect(
            str(path), timeout=30.0, isolation_level=None, check_same_thread=False
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA trusted_schema = OFF")
        connection.execute("PRAGMA secure_delete = ON")
        connection.execute("PRAGMA temp_store = MEMORY")
        if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            raise StorageError("SQLite foreign-key enforcement could not be enabled.")
        return connection
    except sqlite3.Error as exc:
        raise StorageError("The local database could not be opened.") from exc


@contextlib.contextmanager
def transaction(connection: sqlite3.Connection, immediate: bool = True) -> Iterator[sqlite3.Connection]:
    """Atomic transaction with rollback on every exception.

    Nested transactions use SAVEPOINTs so services remain composable.
    """
    nested = connection.in_transaction
    savepoint = f"ibc_nested_{uuid.uuid4().hex}" if nested else None
    try:
        if nested:
            connection.execute(f"SAVEPOINT {savepoint}")
        else:
            connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
        yield connection
        if nested:
            connection.execute(f"RELEASE SAVEPOINT {savepoint}")
        else:
            connection.commit()
    except Exception:
        if nested:
            connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
            connection.execute(f"RELEASE SAVEPOINT {savepoint}")
        else:
            connection.rollback()
        raise


def integrity_check(connection: sqlite3.Connection) -> tuple[bool, str]:
    row = connection.execute("PRAGMA integrity_check").fetchone()
    result = str(row[0]) if row else "no result"
    return result.lower() == "ok", result
