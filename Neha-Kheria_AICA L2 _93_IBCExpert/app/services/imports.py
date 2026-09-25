"""Explicit user-initiated local import orchestration.

This module intentionally contains no web client, downloader, scheduler, or remote update code.
Every import starts from a local file the user selected.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from app.core.errors import DocumentError, ValidationError
from app.core.time import SystemClock, to_utc_iso
from app.db.connection import transaction
from app.documents.vault import DocumentVault
from app.plugins.manager import EventBus

class LocalImportService:
    def __init__(self, connection: sqlite3.Connection, vault: DocumentVault, events: EventBus):
        self.connection = connection
        self.vault = vault
        self.events = events
        self.clock = SystemClock()

    def _start(self, source: Path, import_type: str) -> int:
        now = to_utc_iso(self.clock.now())
        digest = hashlib.sha256(source.read_bytes()).hexdigest() if source.is_file() else None
        cur = self.connection.execute(
            """INSERT INTO imports(import_uuid,import_type,source_name,source_hash,status,total_items,imported_items,rejected_items,started_at)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (str(uuid.uuid4()), import_type, source.name, digest, "RUNNING", 1, 0, 0, now),
        )
        self.connection.commit()
        return int(cur.lastrowid)

    def _finish(self, import_id: int, *, status: str, imported: int, rejected: int, error_log: str | None = None, total: int | None = None) -> None:
        self.connection.execute(
            """UPDATE imports SET status=?,total_items=COALESCE(?,total_items),imported_items=?,rejected_items=?,error_log=?,completed_at=? WHERE id=?""",
            (status, total, imported, rejected, error_log, to_utc_iso(self.clock.now()), import_id),
        )
        self.connection.commit()

    def import_file(self, source: Path | str, *, client_id: int | None = None, matter_id: int | None = None,
                    category: str | None = None, tags: list[str] | None = None, user_id: int | None = None) -> dict[str, Any]:
        path = Path(source)
        if not path.is_file():
            raise ValidationError("Selected import source is not a local file.")
        import_id = self._start(path, "LOCAL_USER_SELECTED")
        try:
            if path.suffix.lower() == ".zip":
                result = self.vault.import_zip(path, client_id=client_id, matter_id=matter_id, category=category, tags=tags, user_id=user_id)
                imported = len(result["imported_document_ids"])
                duplicates = len(result["duplicate_document_ids"])
                rejected = len(result["rejected"])
                total = imported + duplicates + rejected
                status = "COMPLETE" if rejected == 0 else "PARTIAL"
                self._finish(import_id, status=status, imported=imported + duplicates, rejected=rejected,
                             error_log=json.dumps(result["rejected"], ensure_ascii=False) if rejected else None, total=total)
                output = {"import_id": import_id, **result}
            else:
                duplicate_id = self.vault.find_duplicate(path, client_id=client_id, matter_id=matter_id)
                document_id = self.vault.ingest(path, client_id=client_id, matter_id=matter_id, category=category,
                                                tags=tags, source_label="User-selected local import", user_id=user_id)
                self._finish(import_id, status="COMPLETE", imported=1, rejected=0)
                output = {"import_id": import_id, "document_id": document_id, "duplicate": duplicate_id is not None}
            self.events.publish("local_import.completed", {"import_id": import_id, "source_name": path.name})
            return output
        except Exception as exc:
            self._finish(import_id, status="FAILED", imported=0, rejected=1, error_log=str(exc))
            self.events.publish("local_import.failed", {"import_id": import_id, "source_name": path.name})
            raise

    def history(self, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 500:
            raise ValidationError("Import history limit is invalid.")
        return [dict(row) for row in self.connection.execute(
            "SELECT * FROM imports ORDER BY started_at DESC,id DESC LIMIT ?", (limit,)
        ).fetchall()]
