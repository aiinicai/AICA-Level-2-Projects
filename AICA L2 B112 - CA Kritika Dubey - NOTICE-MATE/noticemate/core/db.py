"""SQLite access (stdlib sqlite3). One connection per call-site context; WAL mode."""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .config import get_settings

SCHEMA_VERSION = 1
_init_lock = threading.Lock()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=30, detect_types=0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db() -> dict:
    """Create missing v1 tables (CREATE IF NOT EXISTS — never drops), then apply
    additive migrations. An existing database is backed up before migrating."""
    from .migrations import apply_migrations

    s = get_settings()
    existed = s.db_path.exists() and s.db_path.stat().st_size > 0
    with _init_lock:
        conn = _connect(s.db_path)
        try:
            schema = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
            conn.executescript(schema)
            row = conn.execute("SELECT version FROM schema_version").fetchone()
            if row is None:
                conn.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,))
        finally:
            conn.close()
        result = apply_migrations(s.db_path, s.data_dir / "backups", existed_before=existed)
    try:
        import os

        os.chmod(s.db_path, 0o600)
    except OSError:  # pragma: no cover
        pass
    return result


@contextmanager
def tx() -> Iterator[sqlite3.Connection]:
    """Transaction context: commits on success, rolls back on error."""
    conn = _connect(get_settings().db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


@contextmanager
def ro() -> Iterator[sqlite3.Connection]:
    conn = _connect(get_settings().db_path)
    try:
        yield conn
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row | None, json_fields: tuple[str, ...] = ()) -> dict[str, Any] | None:
    if row is None:
        return None
    d = dict(row)
    for f in json_fields:
        if f in d and isinstance(d[f], str):
            try:
                d[f] = json.loads(d[f])
            except json.JSONDecodeError:
                pass
    return d


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str, sort_keys=True)
