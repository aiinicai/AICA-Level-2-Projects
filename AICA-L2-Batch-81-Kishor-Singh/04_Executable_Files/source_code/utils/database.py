"""SQLite persistence for signature templates, recent jobs and the audit log.

Only metadata is ever stored -- never PDF/Word file contents, never
passwords. The database lives alongside settings.json in the per-user app
data directory (see :mod:`utils.config_manager`).
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from models.signature_template import SignatureTemplate

_SCHEMA = """
CREATE TABLE IF NOT EXISTS templates (
    template_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    data_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recent_jobs (
    job_id TEXT PRIMARY KEY,
    operation TEXT NOT NULL,
    source_name TEXT,
    output_name TEXT,
    status TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    operator TEXT,
    operation TEXT,
    source_document TEXT,
    output_document TEXT,
    pages_processed TEXT,
    template_used TEXT,
    result TEXT
);

-- Local integrity registry for QR-stamped documents (core.integrity_engine).
-- Records only a document ID, the final file's SHA-256 hash, and metadata --
-- never the document content itself. This registry lives on ONE computer;
-- it proves nothing to a third party unless they can query this same
-- database (see the README's note on local-only vs. web verification).
CREATE TABLE IF NOT EXISTS integrity_registry (
    document_id TEXT PRIMARY KEY,
    sha256 TEXT NOT NULL,
    filename TEXT,
    operator TEXT,
    registered_at TEXT NOT NULL
);
"""


@dataclass
class AuditEntry:
    timestamp: str
    operator: str
    operation: str
    source_document: str
    output_document: str
    pages_processed: str
    template_used: str
    result: str


class Database:
    """Thin, dependency-free SQLite wrapper. Not thread-shared: each worker
    thread should open its own :class:`Database` instance pointing at the
    same file (sqlite3 connections are not safe to share across threads).
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    # ---------------------------------------------------------------- templates
    def save_template(self, template: SignatureTemplate) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO templates (template_id, name, data_json, updated_at) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(template_id) DO UPDATE SET name=excluded.name, "
                "data_json=excluded.data_json, updated_at=excluded.updated_at",
                (template.template_id, template.name, json.dumps(template.to_dict()), datetime.now().isoformat()),
            )
            conn.commit()

    def delete_template(self, template_id: str) -> None:
        with closing(self._connect()) as conn:
            conn.execute("DELETE FROM templates WHERE template_id = ?", (template_id,))
            conn.commit()

    def list_templates(self) -> list[SignatureTemplate]:
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT data_json FROM templates ORDER BY updated_at DESC").fetchall()
        return [SignatureTemplate.from_dict(json.loads(r[0])) for r in rows]

    def get_template(self, template_id: str) -> SignatureTemplate | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT data_json FROM templates WHERE template_id = ?", (template_id,)
            ).fetchone()
        return SignatureTemplate.from_dict(json.loads(row[0])) if row else None

    # -------------------------------------------------------------- recent jobs
    def add_recent_job(self, job_id: str, operation: str, source_name: str, output_name: str, status: str) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO recent_jobs (job_id, operation, source_name, output_name, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (job_id, operation, source_name, output_name, status, datetime.now().isoformat()),
            )
            conn.commit()

    def list_recent_jobs(self, limit: int = 50) -> list[sqlite3.Row]:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(
                "SELECT * FROM recent_jobs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()

    # ---------------------------------------------------------------- audit log
    def add_audit_entry(self, entry: AuditEntry) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO audit_log (timestamp, operator, operation, source_document, "
                "output_document, pages_processed, template_used, result) VALUES (?,?,?,?,?,?,?,?)",
                (
                    entry.timestamp,
                    entry.operator,
                    entry.operation,
                    entry.source_document,
                    entry.output_document,
                    entry.pages_processed,
                    entry.template_used,
                    entry.result,
                ),
            )
            conn.commit()

    def list_audit_entries(self, limit: int = 500) -> list[sqlite3.Row]:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(
                "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()

    # ----------------------------------------------------------- integrity registry
    def register_integrity_record(self, document_id: str, sha256: str, filename: str, operator: str) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO integrity_registry (document_id, sha256, filename, operator, registered_at) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(document_id) DO UPDATE SET sha256=excluded.sha256, filename=excluded.filename, "
                "operator=excluded.operator, registered_at=excluded.registered_at",
                (document_id, sha256, filename, operator, datetime.now().isoformat()),
            )
            conn.commit()

    def get_integrity_record(self, document_id: str) -> sqlite3.Row | None:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(
                "SELECT * FROM integrity_registry WHERE document_id = ?", (document_id,)
            ).fetchone()

    def list_integrity_records(self, limit: int = 500) -> list[sqlite3.Row]:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(
                "SELECT * FROM integrity_registry ORDER BY registered_at DESC LIMIT ?", (limit,)
            ).fetchall()
