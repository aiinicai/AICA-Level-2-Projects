"""SQLite connection and schema management for the memory store."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection with row and foreign-key support enabled."""

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create the four tables and required indexes from architecture section 3.2."""

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS embeddings (
            id INTEGER PRIMARY KEY,
            vector TEXT NOT NULL,
            model_version TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY,
            content TEXT NOT NULL,
            subject_key TEXT NOT NULL,
            category TEXT NOT NULL,
            source_type TEXT NOT NULL CHECK (
                source_type IN ('user_stated', 'ai_inferred')
            ),
            confirmed_at TEXT,
            source_session_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_verified_at TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN ('active', 'flagged_conflict', 'superseded', 'deleted')
            ),
            supersedes_id INTEGER,
            embedding_id INTEGER NOT NULL,
            FOREIGN KEY (supersedes_id) REFERENCES memories(id),
            FOREIGN KEY (embedding_id) REFERENCES embeddings(id)
        );

        CREATE TABLE IF NOT EXISTS derived_from (
            memory_id INTEGER NOT NULL,
            parent_memory_id INTEGER NOT NULL,
            PRIMARY KEY (memory_id, parent_memory_id),
            FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE,
            FOREIGN KEY (parent_memory_id) REFERENCES memories(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY,
            event_type TEXT NOT NULL CHECK (
                event_type IN (
                    'write', 'write_rejected', 'contextual_read', 'full_export',
                    'update', 'delete', 'access_denied'
                )
            ),
            memory_id INTEGER,
            actor TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            detail TEXT NOT NULL,
            prev_row_hash TEXT NOT NULL,
            row_hash TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_memories_subject_key
            ON memories(subject_key);
        CREATE INDEX IF NOT EXISTS idx_memories_status
            ON memories(status);
        """
    )


def reset_db(db_path: str | Path) -> sqlite3.Connection:
    """Replace a database file with a newly initialized schema."""

    path = Path(db_path)
    if path.exists():
        path.unlink()
    conn = connect(path)
    init_schema(conn)
    return conn


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""

    return datetime.now(timezone.utc).isoformat()

