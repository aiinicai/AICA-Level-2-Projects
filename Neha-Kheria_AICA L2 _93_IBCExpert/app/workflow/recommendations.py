"""Deterministic explainable recommendation engine with citation enforcement."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from app.core.errors import ValidationError
from app.core.time import Clock, SystemClock, to_utc_iso
from app.db.connection import transaction
from app.security.audit import AuditService


@dataclass
class RecommendationEngine:
    connection: sqlite3.Connection
    audit: AuditService
    clock: Clock = SystemClock()

    def persist(self, *, matter_id: int, rule_key: str, priority: str, title: str, action: str, reason: str, citation_id: int | None, process_stage_id: int | None = None, applicable_due_date: str | None = None, related_case_law: list[int] | None = None) -> int:
        if citation_id is None:
            raise ValidationError("No legal recommendation may be created without an associated citation.")
        citation = self.connection.execute("SELECT * FROM citations WHERE id=?", (citation_id,)).fetchone()
        if citation is None:
            raise ValidationError("Recommendation citation was not found.")
        if priority not in {"LOW", "NORMAL", "HIGH", "CRITICAL"}:
            raise ValidationError("Recommendation priority is invalid.")
        now = to_utc_iso(self.clock.now())
        cursor = self.connection.execute(
            """INSERT INTO recommendations(
                matter_id,process_stage_id,priority,title,action_text,reason,citation_id,
                source_document_id,source_page,applicable_due_date,related_case_law_json,
                verification_status,rule_key,dismissed,generated_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,0,?,?)
            ON CONFLICT(matter_id,rule_key,applicable_due_date) DO UPDATE SET
                process_stage_id=excluded.process_stage_id,priority=excluded.priority,title=excluded.title,
                action_text=excluded.action_text,reason=excluded.reason,citation_id=excluded.citation_id,
                source_document_id=excluded.source_document_id,source_page=excluded.source_page,
                related_case_law_json=excluded.related_case_law_json,
                verification_status=excluded.verification_status,dismissed=0,updated_at=excluded.updated_at""",
            (
                matter_id, process_stage_id, priority, title.strip(), action.strip(), reason.strip(),
                citation_id, citation["source_document_id"], citation["source_page"], applicable_due_date,
                json.dumps(related_case_law or []), citation["verification_status"], rule_key, now, now,
            ),
        )
        if cursor.lastrowid:
            return int(cursor.lastrowid)
        row = self.connection.execute("SELECT id FROM recommendations WHERE matter_id=? AND rule_key=? AND applicable_due_date IS ?", (matter_id, rule_key, applicable_due_date)).fetchone()
        return int(row[0])

    def generate_for_matter(self, matter_id: int) -> list[dict[str, Any]]:
        matter = self.connection.execute("SELECT * FROM matters WHERE id=?", (matter_id,)).fetchone()
        if matter is None:
            raise ValidationError("Matter was not found.")
        today = self.clock.now().date()
        generated: list[int] = []
        with transaction(self.connection):
            stages = self.connection.execute(
                """SELECT ps.*,sd.stage_key,sd.stage_name,sd.citation_id,sd.required_documents_json,
                          sd.verification_status,c.citation_text
                   FROM process_stages ps
                   JOIN process_stage_definitions sd ON sd.id=ps.stage_definition_id
                   LEFT JOIN citations c ON c.id=sd.citation_id
                   JOIN process_instances pi ON pi.id=ps.process_instance_id
                   WHERE pi.matter_id=? AND pi.status='ACTIVE'""", (matter_id,)
            ).fetchall()
            for stage in stages:
                if stage["citation_id"] is None:
                    # This is intentionally not a recommendation: citation enforcement
                    # blocks legal advice from uncited workflow data.
                    continue
                due = date.fromisoformat(stage["computed_due_date"]) if stage["computed_due_date"] else None
                if due and stage["status"] not in {"DONE", "NOT_APPLICABLE"}:
                    if due < today:
                        generated.append(self.persist(
                            matter_id=matter_id, process_stage_id=stage["id"],
                            rule_key=f"overdue:{stage['stage_key']}", priority="CRITICAL",
                            title=f"Overdue: {stage['stage_name']}",
                            action=f"Review and complete {stage['stage_name']} immediately.",
                            reason=f"The stored workflow due date {due.isoformat()} has passed.",
                            citation_id=stage["citation_id"], applicable_due_date=due.isoformat(),
                        ))
                    elif due <= today + timedelta(days=7):
                        generated.append(self.persist(
                            matter_id=matter_id, process_stage_id=stage["id"],
                            rule_key=f"upcoming:{stage['stage_key']}", priority="HIGH",
                            title=f"Upcoming: {stage['stage_name']}",
                            action=f"Prepare and complete {stage['stage_name']} by the stored due date.",
                            reason=f"The stored workflow due date is {due.isoformat()}.",
                            citation_id=stage["citation_id"], applicable_due_date=due.isoformat(),
                        ))
                required = json.loads(stage["required_documents_json"])
                if required:
                    attached = self.connection.execute("SELECT d.category,d.original_filename FROM process_stage_documents psd JOIN documents d ON d.id=psd.document_id WHERE psd.process_stage_id=?", (stage["id"],)).fetchall()
                    haystack = " ".join((row["category"] or "") + " " + row["original_filename"] for row in attached).lower()
                    missing = [item for item in required if str(item).lower() not in haystack]
                    if missing:
                        generated.append(self.persist(
                            matter_id=matter_id, process_stage_id=stage["id"],
                            rule_key=f"missing-documents:{stage['stage_key']}", priority="HIGH",
                            title=f"Missing documents: {stage['stage_name']}",
                            action="Obtain and attach: " + ", ".join(map(str, missing)),
                            reason="The stage definition requires documents not presently attached.",
                            citation_id=stage["citation_id"], applicable_due_date=stage["computed_due_date"],
                        ))
            self.audit.append("RECOMMENDATIONS_GENERATED", f"Generated or refreshed {len(generated)} recommendation(s).", entity_type="matter", entity_id=matter_id, details={"count": len(generated)})
        return [dict(row) for row in self.connection.execute(
            """SELECT r.*,c.citation_text FROM recommendations r JOIN citations c ON c.id=r.citation_id
               WHERE r.matter_id=? AND r.dismissed=0 ORDER BY
               CASE r.priority WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'NORMAL' THEN 3 ELSE 4 END,
               r.applicable_due_date""", (matter_id,)
        ).fetchall()]
