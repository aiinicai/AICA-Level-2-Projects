"""Persistent data-driven workflow definitions, deadlines and checklists."""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from app.core.errors import ValidationError
from app.core.time import Clock, SystemClock, to_utc_iso
from app.db.connection import transaction
from app.security.audit import AuditService

ALLOWED_TRIGGER_FIELDS = {
    "date_of_default", "demand_notice_date", "filing_date", "admission_date",
    "insolvency_commencement_date",
}
STAGE_STATUSES = {"NOT_STARTED", "IN_PROGRESS", "DONE", "NOT_APPLICABLE", "OVERDUE"}


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError as exc:
        raise ValidationError(f"Invalid ISO date: {value}") from exc


def add_business_days(start: date, days: int) -> date:
    if days < 0:
        raise ValidationError("Negative workflow offsets are not supported.")
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


@dataclass
class WorkflowService:
    connection: sqlite3.Connection
    audit: AuditService
    clock: Clock = SystemClock()

    def create_definition(self, name: str, process_type: str, version: int, stages: list[dict[str, Any]], verification_status: str = "REVIEW_REQUIRED", user_id: int | None = None) -> int:
        if not name.strip() or not process_type.strip() or version < 1:
            raise ValidationError("Workflow name, type and positive version are required.")
        if not stages:
            raise ValidationError("Workflow must contain at least one stage.")
        now = to_utc_iso(self.clock.now())
        with transaction(self.connection):
            cursor = self.connection.execute(
                """INSERT INTO process_definitions(
                    definition_uuid,name,process_type,version,verification_status,active,created_at
                ) VALUES(?,?,?,?,?,1,?)""",
                (str(uuid.uuid4()), name.strip(), process_type.strip(), version, verification_status, now),
            )
            definition_id = int(cursor.lastrowid)
            seen: set[str] = set()
            for sequence, stage in enumerate(stages, start=1):
                key = str(stage.get("stage_key") or "").strip()
                title = str(stage.get("stage_name") or "").strip()
                if not key or key in seen or not title:
                    raise ValidationError("Every workflow stage needs a unique key and a name.")
                seen.add(key)
                trigger = stage.get("trigger_field")
                if trigger is not None and trigger not in ALLOWED_TRIGGER_FIELDS:
                    raise ValidationError(f"Unsupported workflow trigger field: {trigger}")
                offset = stage.get("due_offset_days")
                if offset is not None and (not isinstance(offset, int) or offset < 0 or offset > 3650):
                    raise ValidationError("Workflow due-day offset is invalid.")
                if offset is not None and not stage.get("citation_id"):
                    raise ValidationError("A stage with a legal due date must have an associated citation.")
                checklist = stage.get("checklist") or []
                if not isinstance(checklist, list) or any(not str(item).strip() for item in checklist):
                    raise ValidationError("Workflow checklist must be a list of non-empty labels.")
                self.connection.execute(
                    """INSERT INTO process_stage_definitions(
                        process_definition_id,stage_key,sequence_number,stage_name,statutory_basis,
                        citation_id,trigger_field,due_offset_days,due_calendar_type,due_rule_json,
                        required_documents_json,checklist_template_json,verification_status
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        definition_id, key, sequence, title, stage.get("statutory_basis"),
                        stage.get("citation_id"), trigger, offset,
                        stage.get("due_calendar_type", "CALENDAR"),
                        json.dumps(stage.get("due_rule") or {}, separators=(",", ":"), sort_keys=True),
                        json.dumps(stage.get("required_documents") or [], ensure_ascii=False),
                        json.dumps(checklist, ensure_ascii=False),
                        stage.get("verification_status", verification_status),
                    ),
                )
            self.audit.append("WORKFLOW_DEFINITION_CREATED", f"Created workflow definition '{name}'.", entity_type="process_definition", entity_id=definition_id, user_id=user_id, details={"stage_count": len(stages), "version": version})
            return definition_id

    def instantiate(self, matter_id: int, definition_id: int, user_id: int | None = None) -> int:
        matter = self.connection.execute("SELECT * FROM matters WHERE id=?", (matter_id,)).fetchone()
        definition = self.connection.execute("SELECT * FROM process_definitions WHERE id=? AND active=1", (definition_id,)).fetchone()
        if matter is None or definition is None:
            raise ValidationError("Matter or active workflow definition was not found.")
        now = to_utc_iso(self.clock.now())
        with transaction(self.connection):
            cursor = self.connection.execute(
                """INSERT INTO process_instances(
                    instance_uuid,matter_id,process_definition_id,started_at,status,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?)""",
                (str(uuid.uuid4()), matter_id, definition_id, now, "ACTIVE", now, now),
            )
            instance_id = int(cursor.lastrowid)
            definitions = self.connection.execute(
                "SELECT * FROM process_stage_definitions WHERE process_definition_id=? ORDER BY sequence_number",
                (definition_id,),
            ).fetchall()
            for stage_def in definitions:
                stage_cursor = self.connection.execute(
                    """INSERT INTO process_stages(
                        process_instance_id,stage_definition_id,status,created_at,updated_at
                    ) VALUES(?,?,'NOT_STARTED',?,?)""",
                    (instance_id, stage_def["id"], now, now),
                )
                stage_id = int(stage_cursor.lastrowid)
                for index, label in enumerate(json.loads(stage_def["checklist_template_json"])):
                    self.connection.execute(
                        "INSERT INTO checklists(process_stage_id,item_key,label,sequence_number) VALUES(?,?,?,?)",
                        (stage_id, f"item-{index+1}", str(label), index + 1),
                    )
            self.audit.append("WORKFLOW_STARTED", f"Started workflow '{definition['name']}'.", entity_type="process_instance", entity_id=instance_id, user_id=user_id, details={"matter_id": matter_id})
            self.recalculate(instance_id, reason="Workflow instantiated", user_id=user_id)
            return instance_id

    def _compute_due(self, trigger: date, offset: int, calendar_type: str) -> date:
        return add_business_days(trigger, offset) if calendar_type == "BUSINESS" else trigger + timedelta(days=offset)

    def recalculate(self, instance_id: int, reason: str, user_id: int | None = None) -> int:
        rows = self.connection.execute(
            """SELECT ps.*,sd.stage_name,sd.trigger_field,sd.due_offset_days,sd.due_calendar_type,
                      sd.citation_id,sd.verification_status,pi.matter_id,m.*
               FROM process_stages ps
               JOIN process_stage_definitions sd ON sd.id=ps.stage_definition_id
               JOIN process_instances pi ON pi.id=ps.process_instance_id
               JOIN matters m ON m.id=pi.matter_id
               WHERE ps.process_instance_id=?""",
            (instance_id,),
        ).fetchall()
        if not rows:
            raise ValidationError("Workflow instance was not found.")
        today = self.clock.now().date()
        now = to_utc_iso(self.clock.now())
        changed = 0
        with transaction(self.connection):
            for row in rows:
                trigger_value = row[row["trigger_field"]] if row["trigger_field"] else None
                trigger = _parse_date(trigger_value)
                due = None
                if trigger is not None and row["due_offset_days"] is not None:
                    due = self._compute_due(trigger, int(row["due_offset_days"]), row["due_calendar_type"])
                due_text = due.isoformat() if due else None
                old_due = row["computed_due_date"]
                status = row["status"]
                if status not in {"DONE", "NOT_APPLICABLE"}:
                    status = "OVERDUE" if due and due < today else ("NOT_STARTED" if status == "OVERDUE" else status)
                if old_due != due_text or row["trigger_date"] != trigger_value or status != row["status"]:
                    changed += 1
                    self.connection.execute(
                        """UPDATE process_stages SET trigger_date=?,computed_due_date=?,status=?,last_recalculated_at=?,updated_at=? WHERE id=?""",
                        (trigger_value, due_text, status, now, now, row["id"]),
                    )
                    self.connection.execute(
                        """INSERT INTO deadline_recalculation_history(
                            process_stage_id,previous_trigger_date,new_trigger_date,previous_due_date,new_due_date,reason,recalculated_at
                        ) VALUES(?,?,?,?,?,?,?)""",
                        (row["id"], row["trigger_date"], trigger_value, old_due, due_text, reason, now),
                    )
                if due_text:
                    deadline_status = "OVERDUE" if due < today else ("DUE_TODAY" if due == today else "UPCOMING")
                    if status == "DONE":
                        deadline_status = "COMPLETED"
                    self.connection.execute(
                        """INSERT INTO deadlines(
                            matter_id,process_stage_id,title,trigger_date,due_date,citation_id,
                            verification_status,status,completed_at,created_at,updated_at
                        ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                        ON CONFLICT(process_stage_id) DO UPDATE SET
                            title=excluded.title,trigger_date=excluded.trigger_date,due_date=excluded.due_date,
                            citation_id=excluded.citation_id,verification_status=excluded.verification_status,
                            status=excluded.status,completed_at=excluded.completed_at,updated_at=excluded.updated_at""",
                        (row["matter_id"], row["id"], row["stage_name"], trigger_value, due_text,
                         row["citation_id"], row["verification_status"], deadline_status,
                         row["completion_date"], now, now),
                    )
            if changed:
                self.audit.append("WORKFLOW_RECALCULATED", f"Recalculated {changed} workflow stage(s).", entity_type="process_instance", entity_id=instance_id, user_id=user_id, details={"reason": reason})
        return changed

    def update_matter_dates(self, matter_id: int, dates: dict[str, str | None], user_id: int | None = None) -> None:
        unknown = set(dates) - ALLOWED_TRIGGER_FIELDS
        if unknown:
            raise ValidationError(f"Unsupported matter date(s): {', '.join(sorted(unknown))}")
        normalized = {field: (_parse_date(value).isoformat() if value else None) for field, value in dates.items()}
        now = to_utc_iso(self.clock.now())
        with transaction(self.connection):
            cursor = self.connection.execute(
                f"UPDATE matters SET {','.join(field+'=?' for field in normalized)},updated_at=?,row_version=row_version+1 WHERE id=?",
                [*normalized.values(), now, matter_id],
            )
            if cursor.rowcount != 1:
                raise ValidationError("Matter was not found.")
            instances = self.connection.execute("SELECT id FROM process_instances WHERE matter_id=? AND status='ACTIVE'", (matter_id,)).fetchall()
            for instance in instances:
                self.recalculate(int(instance[0]), reason="Matter trigger date changed", user_id=user_id)
            self.audit.append("MATTER_DATES_UPDATED", "Updated matter dates and recalculated affected workflows.", entity_type="matter", entity_id=matter_id, user_id=user_id, details={"fields": sorted(normalized)})

    def set_stage_status(self, stage_id: int, status: str, notes: str | None = None, user_id: int | None = None) -> None:
        if status not in STAGE_STATUSES:
            raise ValidationError("Workflow stage status is invalid.")
        row = self.connection.execute("SELECT * FROM process_stages WHERE id=?", (stage_id,)).fetchone()
        if row is None:
            raise ValidationError("Workflow stage was not found.")
        now = to_utc_iso(self.clock.now())
        completion = now if status == "DONE" else None
        with transaction(self.connection):
            self.connection.execute("UPDATE process_stages SET status=?,completion_date=?,notes=?,updated_at=? WHERE id=?", (status, completion, notes, now, stage_id))
            deadline_status = "COMPLETED" if status == "DONE" else ("WAIVED" if status == "NOT_APPLICABLE" else None)
            if deadline_status:
                self.connection.execute("UPDATE deadlines SET status=?,completed_at=?,updated_at=? WHERE process_stage_id=?", (deadline_status, completion, now, stage_id))
            self.audit.append("WORKFLOW_STAGE_STATUS_CHANGED", f"Workflow stage status changed to {status}.", entity_type="process_stage", entity_id=stage_id, user_id=user_id)

    def complete_checklist_item(self, item_id: int, completed: bool, notes: str | None = None, user_id: int | None = None) -> None:
        now = to_utc_iso(self.clock.now())
        cursor = self.connection.execute("UPDATE checklists SET completed=?,completed_at=?,notes=? WHERE id=?", (1 if completed else 0, now if completed else None, notes, item_id))
        if cursor.rowcount != 1:
            raise ValidationError("Checklist item was not found.")
        self.audit.append("CHECKLIST_UPDATED", "Workflow checklist item updated.", entity_type="checklist", entity_id=item_id, user_id=user_id, details={"completed": completed})

    def attach_document(self, stage_id: int, document_id: int) -> None:
        now = to_utc_iso(self.clock.now())
        try:
            self.connection.execute("INSERT OR IGNORE INTO process_stage_documents(process_stage_id,document_id,attached_at) VALUES(?,?,?)", (stage_id, document_id, now))
        except sqlite3.IntegrityError as exc:
            raise ValidationError("Workflow stage or document was not found.") from exc

    def stages(self, instance_id: int) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """SELECT ps.*,sd.stage_key,sd.stage_name,sd.sequence_number,sd.statutory_basis,
                      sd.citation_id,sd.required_documents_json,sd.verification_status
               FROM process_stages ps JOIN process_stage_definitions sd ON sd.id=ps.stage_definition_id
               WHERE ps.process_instance_id=? ORDER BY sd.sequence_number""", (instance_id,)
        ).fetchall()
        return [dict(row) for row in rows]
