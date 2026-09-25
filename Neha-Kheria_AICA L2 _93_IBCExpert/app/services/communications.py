"""Offline professional communication drafts and TXT/EML exports."""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

from app.core.errors import ValidationError
from app.core.time import Clock, SystemClock, to_utc_iso
from app.security.audit import AuditService


@dataclass
class CommunicationService:
    connection: sqlite3.Connection
    audit: AuditService
    clock: Clock = SystemClock()

    def create(self, matter_id: int, draft_type: str, subject: str, body: str, recipient: str | None = None, process_stage_id: int | None = None) -> int:
        if not subject.strip() or not body.strip():
            raise ValidationError("Communication subject and body are required.")
        if self.connection.execute("SELECT 1 FROM matters WHERE id=?", (matter_id,)).fetchone() is None:
            raise ValidationError("Matter was not found.")
        now = to_utc_iso(self.clock.now())
        cursor = self.connection.execute(
            """INSERT INTO communication_drafts(
               matter_id,process_stage_id,draft_type,recipient,subject,body,version,status,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,1,'DRAFT',?,?)""",
            (matter_id, process_stage_id, draft_type, recipient, subject.strip(), body, now, now),
        )
        draft_id = int(cursor.lastrowid)
        self.audit.append("COMMUNICATION_DRAFT_CREATED", "Created offline communication draft.", entity_type="communication_draft", entity_id=draft_id)
        return draft_id

    def update(self, draft_id: int, *, recipient: str | None, subject: str, body: str, status: str = "DRAFT") -> None:
        if status not in {"DRAFT", "FINAL", "ARCHIVED"}:
            raise ValidationError("Communication status is invalid.")
        cursor = self.connection.execute(
            """UPDATE communication_drafts SET recipient=?,subject=?,body=?,status=?,
               version=version+1,updated_at=? WHERE id=?""",
            (recipient, subject.strip(), body, status, to_utc_iso(self.clock.now()), draft_id),
        )
        if cursor.rowcount != 1:
            raise ValidationError("Communication draft was not found.")
        self.audit.append("COMMUNICATION_DRAFT_UPDATED", "Updated offline communication draft.", entity_type="communication_draft", entity_id=draft_id)

    def export(self, draft_id: int, destination: Path, output_type: str) -> Path:
        row = self.connection.execute("SELECT * FROM communication_drafts WHERE id=?", (draft_id,)).fetchone()
        if row is None:
            raise ValidationError("Communication draft was not found.")
        output_type = output_type.upper()
        if output_type not in {"TXT", "EML"}:
            raise ValidationError("Communication export supports TXT or EML.")
        destination.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^A-Za-z0-9._ -]", "_", row["subject"])[:100].strip() or "communication"
        target = destination / f"{safe}-v{row['version']}.{output_type.lower()}"
        if output_type == "TXT":
            target.write_text(f"To: {row['recipient'] or ''}\nSubject: {row['subject']}\n\n{row['body']}", encoding="utf-8")
        else:
            message = EmailMessage()
            if row["recipient"]: message["To"] = row["recipient"]
            message["Subject"] = row["subject"]
            message.set_content(row["body"])
            target.write_bytes(message.as_bytes())
        self.audit.append("COMMUNICATION_EXPORTED", f"Exported communication as {output_type}; no email was sent.", entity_type="communication_draft", entity_id=draft_id)
        return target
