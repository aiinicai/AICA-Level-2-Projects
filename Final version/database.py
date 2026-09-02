"""
database.py - R K Muley & Co | Tax Notice Litigation Assistant v9.0 beta

Default backend: local SQLite in WAL mode.
Optional backend: SQLAlchemy URL from Streamlit secrets or environment for hosted
PostgreSQL deployments.

Accepted connection settings:
  - DATABASE_URL
  - SQLALCHEMY_DATABASE_URI
  - [database].url in .streamlit/secrets.toml
"""

from __future__ import annotations

import hashlib
import json
import logging
import logging.handlers as _log_handlers
import os
import sqlite3
import sys as _sys
from datetime import datetime
from pathlib import Path
from typing import Any

_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DB_PATH, LOG_PATH

SCHEMA_VER = 9

_log_fmt = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s [%(funcName)s:%(lineno)d] - %(message)s"
)
_sh = logging.StreamHandler()
_sh.setFormatter(_log_fmt)
_fh = _log_handlers.RotatingFileHandler(
    str(LOG_PATH), maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
_fh.setFormatter(_log_fmt)
logging.basicConfig(level=logging.INFO, handlers=[_sh, _fh], force=True)
logger = logging.getLogger("RKMuley.DB.v9")


class DatabaseError(Exception):
    """Base exception for all database-layer errors."""


try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import SQLAlchemyError

    SQLALCHEMY_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    create_engine = None
    text = None
    SQLAlchemyError = Exception
    SQLALCHEMY_AVAILABLE = False


def _secret_database_url() -> str:
    for key in ("DATABASE_URL", "SQLALCHEMY_DATABASE_URI"):
        if os.getenv(key):
            return os.environ[key].strip()
    try:
        import streamlit as st

        for key in ("DATABASE_URL", "SQLALCHEMY_DATABASE_URI"):
            value = st.secrets.get(key)
            if value:
                return str(value).strip()
        database_block = st.secrets.get("database", {})
        if database_block and database_block.get("url"):
            return str(database_block["url"]).strip()
    except Exception:
        pass
    return ""


DATABASE_URL = _secret_database_url()
USE_SQLALCHEMY = bool(DATABASE_URL)
_ENGINE = None
if USE_SQLALCHEMY and SQLALCHEMY_AVAILABLE:
    _ENGINE = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
elif USE_SQLALCHEMY:
    logger.error("DATABASE_URL configured but SQLAlchemy is not installed.")


def database_backend() -> str:
    if not USE_SQLALCHEMY:
        return "sqlite"
    if _ENGINE is None:
        return "sqlalchemy-unavailable"
    return f"sqlalchemy:{_ENGINE.dialect.name}"


def _sqlite_connect(timeout: int = 10) -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, timeout=timeout)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def _exec_sqlite(sql: str, params: tuple = (), fetch: str | None = None) -> Any:
    with _sqlite_connect() as con:
        cur = con.execute(sql, params)
        if fetch == "one":
            return cur.fetchone()
        if fetch == "all":
            return cur.fetchall()
        con.commit()
        return cur.lastrowid


def _exec_sqla(sql: str, params: tuple = (), fetch: str | None = None) -> Any:
    if _ENGINE is None or text is None:
        raise DatabaseError("SQLAlchemy backend requested but unavailable.")
    named: dict[str, Any] = {}
    converted = sql
    for idx, value in enumerate(params):
        marker = f":p{idx}"
        converted = converted.replace("?", marker, 1)
        named[f"p{idx}"] = value
    with _ENGINE.begin() as con:
        result = con.execute(text(converted), named)
        if fetch == "one":
            row = result.fetchone()
            return tuple(row) if row else None
        if fetch == "all":
            return [tuple(row) for row in result.fetchall()]
        try:
            return result.lastrowid
        except Exception:
            return -1


def _exec(sql: str, params: tuple = (), fetch: str | None = None) -> Any:
    if USE_SQLALCHEMY:
        return _exec_sqla(sql, params, fetch)
    return _exec_sqlite(sql, params, fetch)


def execute_query(sql: str, params: tuple = (), fetch: str | None = None) -> Any:
    """Public thin wrapper used by support modules that should honor the active backend."""
    return _exec(sql, params, fetch)


def query_dicts(sql: str, params: tuple = ()) -> list[dict]:
    if USE_SQLALCHEMY:
        if _ENGINE is None or text is None:
            raise DatabaseError("SQLAlchemy backend requested but unavailable.")
        named: dict[str, Any] = {}
        converted = sql
        for idx, value in enumerate(params):
            marker = f":p{idx}"
            converted = converted.replace("?", marker, 1)
            named[f"p{idx}"] = value
        with _ENGINE.begin() as con:
            return [dict(row) for row in con.execute(text(converted), named).mappings().all()]
    with _sqlite_connect() as con:
        con.row_factory = sqlite3.Row
        return [dict(row) for row in con.execute(sql, params).fetchall()]


def _upsert_schema_version(ver: int = SCHEMA_VER) -> None:
    _exec(
        "INSERT INTO schema_version (version, applied_at) VALUES (?,?) "
        "ON CONFLICT(version) DO UPDATE SET applied_at=excluded.applied_at",
        (ver, datetime.now().isoformat()),
    )


def _schema_sql(dialect: str) -> list[str]:
    pk = "INTEGER PRIMARY KEY AUTOINCREMENT" if dialect == "sqlite" else "INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY"
    return [
        f"""
        CREATE TABLE IF NOT EXISTS generation_log (
            id {pk},
            timestamp TEXT NOT NULL,
            model TEXT NOT NULL,
            step TEXT NOT NULL,
            prompt_hash TEXT NOT NULL,
            output_hash TEXT NOT NULL,
            char_count INTEGER,
            username TEXT,
            notes TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS session_store (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            ts TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS ca_vault (
            id {pk},
            ts_added TEXT NOT NULL,
            assessee TEXT,
            ay TEXT,
            notice_type TEXT,
            sections TEXT,
            issue_type TEXT NOT NULL,
            quantum_lakh REAL DEFAULT 0,
            outcome TEXT DEFAULT 'Pending',
            strategy TEXT,
            lessons TEXT,
            forum TEXT DEFAULT 'AO Level',
            tags TEXT,
            ao_ward TEXT,
            assessee_type TEXT,
            notes TEXT,
            created_by TEXT,
            updated_at TEXT
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS audit_trail (
            id {pk},
            timestamp TEXT NOT NULL,
            username TEXT,
            action TEXT NOT NULL,
            resource TEXT,
            details TEXT
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS notice_store (
            id {pk},
            created_at TEXT NOT NULL,
            username TEXT,
            pan TEXT,
            ay TEXT,
            notice_type TEXT,
            extraction_json TEXT,
            draft_text TEXT,
            cover_note TEXT,
            proc_flags_json TEXT,
            risk_score INTEGER,
            success_score INTEGER,
            status TEXT DEFAULT 'Draft'
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS users (
            id {pk},
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'article',
            display_name TEXT,
            created_at TEXT NOT NULL,
            last_login TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS deadline_tracker (
            id {pk},
            notice_store_id INTEGER,
            pan TEXT,
            ay TEXT,
            response_due TEXT,
            matter_ref TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TEXT NOT NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_vault_sections ON ca_vault(sections)",
        "CREATE INDEX IF NOT EXISTS idx_vault_outcome ON ca_vault(outcome)",
        "CREATE INDEX IF NOT EXISTS idx_vault_ay ON ca_vault(ay)",
        "CREATE INDEX IF NOT EXISTS idx_log_step ON generation_log(step)",
        "CREATE INDEX IF NOT EXISTS idx_log_ts ON generation_log(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_notice_pan ON notice_store(pan)",
        "CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_trail(username)",
    ]


class DatabaseMigrationEngine:
    """Single schema manager for SQLite and opt-in SQLAlchemy backends."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db = db_path

    def _connect(self) -> sqlite3.Connection:
        return _sqlite_connect()

    def current_version(self) -> int:
        try:
            if USE_SQLALCHEMY:
                row = _exec("SELECT MAX(version) FROM schema_version", fetch="one")
            else:
                tbl = _exec(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'",
                    fetch="one",
                )
                if not tbl:
                    return 0
                row = _exec("SELECT MAX(version) FROM schema_version", fetch="one")
            return int(row[0]) if row and row[0] else 0
        except Exception:
            return 0

    def run(self) -> list[int]:
        current = self.current_version()
        applied: list[int] = []
        if current >= SCHEMA_VER:
            return applied
        try:
            dialect = "sqlite"
            if USE_SQLALCHEMY:
                if _ENGINE is None:
                    raise DatabaseError("SQLAlchemy engine unavailable.")
                dialect = _ENGINE.dialect.name
            for stmt in _schema_sql(dialect):
                _exec(stmt)
            _upsert_schema_version(SCHEMA_VER)
            applied.append(SCHEMA_VER)
            logger.info("DB schema v%d ready on %s.", SCHEMA_VER, database_backend())
        except Exception as exc:
            logger.error("Migration failed: %s", exc)
        return applied

    def health(self) -> dict:
        try:
            if USE_SQLALCHEMY:
                tables = [
                    r[0] for r in _exec(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema='public' ORDER BY table_name",
                        fetch="all",
                    )
                ]
            else:
                tables = [
                    r[0] for r in _exec(
                        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
                        fetch="all",
                    )
                ]
            vault_n = _exec("SELECT COUNT(*) FROM ca_vault", fetch="one")[0] if "ca_vault" in tables else 0
            log_n = _exec("SELECT COUNT(*) FROM generation_log", fetch="one")[0] if "generation_log" in tables else 0
            notice_n = _exec("SELECT COUNT(*) FROM notice_store", fetch="one")[0] if "notice_store" in tables else 0
            return {
                "status": "healthy",
                "backend": database_backend(),
                "schema_version": self.current_version(),
                "tables": tables,
                "vault_records": vault_n,
                "log_entries": log_n,
                "notice_records": notice_n,
                "db_path": str(self._db) if not USE_SQLALCHEMY else "SQLAlchemy URL configured",
                "db_size_kb": round(self._db.stat().st_size / 1024, 1) if (not USE_SQLALCHEMY and self._db.exists()) else None,
            }
        except Exception as exc:
            return {"status": "error", "backend": database_backend(), "error": str(exc)}


def log_generation(
    model: str,
    step: str,
    prompt: str,
    output: str,
    username: str = "system",
    notes: str = "",
) -> None:
    try:
        p_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        o_hash = hashlib.sha256(output.encode()).hexdigest()[:16]
        _exec(
            "INSERT INTO generation_log "
            "(timestamp, model, step, prompt_hash, output_hash, char_count, username, notes) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (datetime.now().isoformat(timespec="seconds"), model, step, p_hash, o_hash, len(output), username, notes),
        )
    except Exception as exc:
        logger.warning("generation_log write failed (non-fatal): %s", exc)


def write_audit_trail(
    action: str,
    resource: str = "",
    details: str = "",
    username: str = "anonymous",
) -> None:
    try:
        _exec(
            "INSERT INTO audit_trail (timestamp, username, action, resource, details) VALUES (?,?,?,?,?)",
            (datetime.now().isoformat(), username, action, resource, str(details)[:500]),
        )
    except Exception as exc:
        logger.warning("audit_trail write failed (non-fatal): %s", exc)


def save_session(key: str, value: Any) -> None:
    try:
        _exec(
            "INSERT INTO session_store (key, value, ts) VALUES (?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, ts=excluded.ts",
            (key, json.dumps(value), datetime.now().isoformat()),
        )
    except (Exception, TypeError) as exc:
        logger.warning("Session save failed for key '%s': %s", key, exc)


def load_session(key: str, default: Any = None) -> Any:
    try:
        row = _exec("SELECT value FROM session_store WHERE key=?", (key,), fetch="one")
        return json.loads(row[0]) if row else default
    except Exception as exc:
        logger.warning("Session load failed for key '%s': %s", key, exc)
        return default


def clear_all_sessions() -> None:
    try:
        _exec("DELETE FROM session_store")
    except Exception as exc:
        logger.warning("Session clear failed: %s", exc)


def persist_notice_store(
    pan: str,
    ay: str,
    notice_type: str,
    extraction: str,
    draft: str,
    cover: str,
    proc_flags: list,
    risk_score: int,
    success_score: int,
    username: str = "",
) -> int:
    try:
        row_id = _exec(
            "INSERT INTO notice_store "
            "(created_at, username, pan, ay, notice_type, extraction_json, "
            "draft_text, cover_note, proc_flags_json, risk_score, success_score, status) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                datetime.now().isoformat(),
                username,
                pan,
                ay,
                notice_type,
                extraction[:50000],
                draft[:50000],
                cover[:5000],
                json.dumps(proc_flags),
                risk_score,
                success_score,
                "Draft",
            ),
        )
        return int(row_id or -1)
    except Exception as exc:
        logger.error("persist_notice_store failed: %s", exc)
        return -1


def get_system_health(db_engine: DatabaseMigrationEngine) -> dict:
    db_info = db_engine.health()
    try:
        recent_logs = _exec(
            "SELECT step, model, timestamp, char_count FROM generation_log ORDER BY id DESC LIMIT 5",
            fetch="all",
        )
        recent_audits = _exec(
            "SELECT username, action, timestamp FROM audit_trail ORDER BY id DESC LIMIT 5",
            fetch="all",
        )
    except Exception:
        recent_logs, recent_audits = [], []
    return {
        "app_version": "9.0.0-beta",
        "timestamp": datetime.now().isoformat(),
        "database": db_info,
        "recent_llm_calls": [
            {"step": r[0], "model": r[1], "ts": r[2], "chars": r[3]} for r in recent_logs
        ],
        "recent_audit": [
            {"user": r[0], "action": r[1], "ts": r[2]} for r in recent_audits
        ],
        "log_file": str(LOG_PATH),
    }


def smoke_test() -> dict[str, bool]:
    from config import DIN_PATTERN, PAN_PATTERN

    results: dict[str, bool] = {}
    try:
        if USE_SQLALCHEMY:
            _exec("SELECT 1", fetch="one")
        else:
            _exec("SELECT 1", fetch="one")
        results["db_connection"] = True
    except Exception:
        results["db_connection"] = False
    results["schema_current"] = DatabaseMigrationEngine().current_version() >= SCHEMA_VER
    results["din_regex"] = (
        bool(DIN_PATTERN.search("ITBA/NFAC/2024/1234567890"))
        and bool(DIN_PATTERN.search("ITBA/AST/F/143(3)(SCN)/2025-26/1086168255(1)"))
    )
    try:
        import streamlit  # noqa: F401

        results["streamlit_available"] = True
    except ImportError:
        results["streamlit_available"] = False
    try:
        import google.genai  # noqa: F401

        results["genai_available"] = True
    except ImportError:
        results["genai_available"] = False
    return results
