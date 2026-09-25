"""Persistent client and matter management with complete change history."""
from __future__ import annotations

import json
import re
import sqlite3
import uuid
from dataclasses import dataclass
from typing import Any

from app.core.errors import StorageError, ValidationError
from app.core.time import Clock, SystemClock, to_utc_iso
from app.db.connection import transaction
from app.security import aead
from app.security.audit import AuditService
from app.security.kdf import derive_subkey

CLIENT_EDITABLE = {
    "name", "corporate_debtor", "cin", "pan", "gst", "registered_office",
    "industry", "primary_email", "primary_phone", "notes", "custom_fields",
}
MATTER_DATE_FIELDS = {
    "date_of_default", "demand_notice_date", "filing_date", "admission_date",
    "insolvency_commencement_date",
}
MATTER_EDITABLE = {
    "title", "matter_type", "case_number", "nclt_bench", "applicant",
    "initiating_provision", *MATTER_DATE_FIELDS, "irp", "rp", "liquidator",
    "advisor", "notes", "custom_fields", "status",
}


def _clean_optional(value: Any, limit: int = 5000) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    if not result:
        return None
    if len(result) > limit:
        raise ValidationError(f"Value is longer than the permitted {limit} characters.")
    return result


def _validate_email(value: str | None) -> str | None:
    value = _clean_optional(value, 320)
    if value and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        raise ValidationError("Email address is not valid.")
    return value


def _canonical_custom(value: Any) -> str:
    if value in (None, ""):
        return "{}"
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValidationError("Custom fields must contain valid JSON.") from exc
    if not isinstance(value, dict):
        raise ValidationError("Custom fields must be an object of field names and values.")
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    if len(encoded) > 100_000:
        raise ValidationError("Custom fields are too large.")
    return encoded


def _mask_pan(value: str | None) -> str | None:
    if not value:
        return None
    return "*" * max(0, len(value) - 4) + value[-4:]


@dataclass
class ClientService:
    connection: sqlite3.Connection
    master_key: bytes
    audit: AuditService
    clock: Clock = SystemClock()

    def __post_init__(self) -> None:
        if len(self.master_key) != 32:
            raise ValueError("master key must contain 32 bytes")

    def _encrypt_pan(self, client_uuid: str, pan: str | None) -> bytes | None:
        pan = _clean_optional(pan, 20)
        if pan is None:
            return None
        key = derive_subkey(self.master_key, "client-pan", client_uuid)
        return aead.encrypt(key, pan.upper().encode("utf-8"), client_uuid.encode("ascii"))

    def _decrypt_pan(self, client_uuid: str, payload: bytes | None) -> str | None:
        if payload is None:
            return None
        key = derive_subkey(self.master_key, "client-pan", client_uuid)
        return aead.decrypt(key, payload, client_uuid.encode("ascii")).decode("utf-8")

    def create(self, data: dict[str, Any], user_id: int | None = None) -> int:
        name = _clean_optional(data.get("name"), 300)
        if not name:
            raise ValidationError("Client name is required.")
        client_uuid = str(uuid.uuid4())
        now = to_utc_iso(self.clock.now())
        pan = _clean_optional(data.get("pan"), 20)
        with transaction(self.connection):
            cursor = self.connection.execute(
                """
                INSERT INTO clients(
                    client_uuid,name,corporate_debtor,cin,pan_encrypted,gst,
                    registered_office,industry,primary_email,primary_phone,notes,
                    custom_fields_json,status,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    client_uuid, name, _clean_optional(data.get("corporate_debtor"), 300),
                    _clean_optional(data.get("cin"), 30), self._encrypt_pan(client_uuid, pan),
                    _clean_optional(data.get("gst"), 30),
                    _clean_optional(data.get("registered_office"), 3000),
                    _clean_optional(data.get("industry"), 200),
                    _validate_email(data.get("primary_email")),
                    _clean_optional(data.get("primary_phone"), 50),
                    _clean_optional(data.get("notes"), 50_000),
                    _canonical_custom(data.get("custom_fields")), "ACTIVE", now, now,
                ),
            )
            client_id = int(cursor.lastrowid)
            audit_id = self.audit.append(
                "CLIENT_CREATED", f"Created client '{name}'.", entity_type="client",
                entity_id=client_id, user_id=user_id, details={"client_uuid": client_uuid},
            )
            self.connection.execute(
                """INSERT INTO client_change_history(
                    client_id,field_name,previous_value,new_value,changed_at,user_id,audit_entry_id,change_group
                ) VALUES(?,?,?,?,?,?,?,?)""",
                (client_id, "__created__", None, name, now, user_id, audit_id, str(uuid.uuid4())),
            )
            return client_id

    def get(self, client_id: int, include_deleted: bool = False) -> dict[str, Any]:
        query = "SELECT * FROM clients WHERE id=?"
        params: list[Any] = [client_id]
        if not include_deleted:
            query += " AND status!='DELETED'"
        row = self.connection.execute(query, params).fetchone()
        if row is None:
            raise ValidationError("Client was not found.")
        result = dict(row)
        result["pan"] = self._decrypt_pan(row["client_uuid"], row["pan_encrypted"])
        result.pop("pan_encrypted", None)
        result["custom_fields"] = json.loads(result.pop("custom_fields_json"))
        return result

    def search(self, query: str = "", status: str | None = "ACTIVE", limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 500:
            raise ValidationError("Search result limit is invalid.")
        clauses: list[str] = []
        params: list[Any] = []
        if status:
            if status not in {"ACTIVE", "ARCHIVED", "DELETED"}:
                raise ValidationError("Client status filter is invalid.")
            clauses.append("status=?")
            params.append(status)
        if query.strip():
            escaped = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            clauses.append("(name LIKE ? ESCAPE '\\' OR corporate_debtor LIKE ? ESCAPE '\\' OR cin LIKE ? ESCAPE '\\' OR gst LIKE ? ESCAPE '\\')")
            params.extend([f"%{escaped}%"] * 4)
        sql = "SELECT id,client_uuid,name,corporate_debtor,cin,gst,industry,status,created_at,updated_at,row_version FROM clients"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY name COLLATE NOCASE LIMIT ?"
        params.append(limit)
        return [dict(row) for row in self.connection.execute(sql, params).fetchall()]

    def update(self, client_id: int, changes: dict[str, Any], expected_version: int, user_id: int | None = None) -> int:
        unknown = set(changes) - CLIENT_EDITABLE
        if unknown:
            raise ValidationError(f"Unknown client field(s): {', '.join(sorted(unknown))}")
        current = self.get(client_id, include_deleted=True)
        if current["status"] == "DELETED":
            raise ValidationError("Deleted client must be restored before editing.")
        if current["row_version"] != expected_version:
            raise StorageError("This client was changed elsewhere. Reload it before saving.")
        normalized: dict[str, Any] = {}
        for field, value in changes.items():
            if field == "name":
                value = _clean_optional(value, 300)
                if not value:
                    raise ValidationError("Client name is required.")
            elif field == "primary_email":
                value = _validate_email(value)
            elif field == "custom_fields":
                value = _canonical_custom(value)
            else:
                value = _clean_optional(value, 50_000 if field == "notes" else 3000)
            normalized[field] = value
        db_names = {"pan": "pan_encrypted", "custom_fields": "custom_fields_json"}
        group = str(uuid.uuid4())
        now = to_utc_iso(self.clock.now())
        actual: list[tuple[str, Any, Any, Any]] = []
        for field, value in normalized.items():
            previous = current[field]
            compare_value = json.dumps(previous, sort_keys=True) if field == "custom_fields" else previous
            if compare_value == value:
                continue
            db_value = self._encrypt_pan(current["client_uuid"], value) if field == "pan" else value
            history_old = _mask_pan(previous) if field == "pan" else (json.dumps(previous, sort_keys=True) if field == "custom_fields" else previous)
            history_new = _mask_pan(value) if field == "pan" else value
            actual.append((field, db_names.get(field, field), db_value, (history_old, history_new)))
        if not actual:
            return expected_version
        with transaction(self.connection):
            assignments = ",".join(f"{db_field}=?" for _, db_field, _, _ in actual)
            params = [db_value for _, _, db_value, _ in actual] + [now, client_id, expected_version]
            cursor = self.connection.execute(
                f"UPDATE clients SET {assignments},updated_at=?,row_version=row_version+1 WHERE id=? AND row_version=?",
                params,
            )
            if cursor.rowcount != 1:
                raise StorageError("This client was changed elsewhere. Reload it before saving.")
            audit_id = self.audit.append(
                "CLIENT_UPDATED", f"Updated {len(actual)} client field(s).",
                entity_type="client", entity_id=client_id, user_id=user_id,
                details={"fields": [item[0] for item in actual]},
            )
            self.connection.executemany(
                """INSERT INTO client_change_history(
                    client_id,field_name,previous_value,new_value,changed_at,user_id,audit_entry_id,change_group
                ) VALUES(?,?,?,?,?,?,?,?)""",
                [(client_id, field, pair[0], pair[1], now, user_id, audit_id, group) for field, _, _, pair in actual],
            )
        return expected_version + 1

    def _set_status(self, client_id: int, status: str, event: str, user_id: int | None) -> None:
        current = self.get(client_id, include_deleted=True)
        now = to_utc_iso(self.clock.now())
        archived_at = now if status == "ARCHIVED" else None
        deleted_at = now if status == "DELETED" else None
        with transaction(self.connection):
            self.connection.execute(
                "UPDATE clients SET status=?,archived_at=?,deleted_at=?,updated_at=?,row_version=row_version+1 WHERE id=?",
                (status, archived_at, deleted_at, now, client_id),
            )
            audit_id = self.audit.append(event, f"Client status changed to {status}.", entity_type="client", entity_id=client_id, user_id=user_id)
            self.connection.execute(
                """INSERT INTO client_change_history(
                    client_id,field_name,previous_value,new_value,changed_at,user_id,audit_entry_id,change_group
                ) VALUES(?,?,?,?,?,?,?,?)""",
                (client_id, "status", current["status"], status, now, user_id, audit_id, str(uuid.uuid4())),
            )

    def archive(self, client_id: int, user_id: int | None = None) -> None:
        self._set_status(client_id, "ARCHIVED", "CLIENT_ARCHIVED", user_id)

    def restore(self, client_id: int, user_id: int | None = None) -> None:
        self._set_status(client_id, "ACTIVE", "CLIENT_RESTORED", user_id)

    def soft_delete(self, client_id: int, user_id: int | None = None) -> None:
        self._set_status(client_id, "DELETED", "CLIENT_SOFT_DELETED", user_id)

    def permanent_delete(self, client_id: int, confirmation_name: str, user_id: int | None = None) -> None:
        current = self.get(client_id, include_deleted=True)
        if current["status"] != "DELETED":
            raise ValidationError("A client must be soft-deleted before permanent deletion.")
        if confirmation_name.strip() != current["name"]:
            raise ValidationError("Permanent-delete confirmation name does not match.")
        # Audit before deletion because related history will cascade.
        with transaction(self.connection):
            self.audit.append(
                "CLIENT_PERMANENTLY_DELETED", "Permanently deleted a client and related records.",
                entity_type="client", entity_id=client_id, user_id=user_id,
                details={"client_uuid": current["client_uuid"], "name": current["name"]},
            )
            self.connection.execute("DELETE FROM clients WHERE id=?", (client_id,))

    def history(self, client_id: int) -> list[dict[str, Any]]:
        return [dict(row) for row in self.connection.execute(
            "SELECT * FROM client_change_history WHERE client_id=? ORDER BY id DESC", (client_id,)
        ).fetchall()]

    def create_matter(self, client_id: int, data: dict[str, Any], user_id: int | None = None) -> int:
        self.get(client_id)
        title = _clean_optional(data.get("title"), 300)
        matter_type = _clean_optional(data.get("matter_type"), 100)
        if not title or not matter_type:
            raise ValidationError("Matter title and process type are required.")
        now = to_utc_iso(self.clock.now())
        matter_uuid = str(uuid.uuid4())
        fields = [
            "case_number", "nclt_bench", "applicant", "initiating_provision",
            "date_of_default", "demand_notice_date", "filing_date", "admission_date",
            "insolvency_commencement_date", "irp", "rp", "liquidator", "advisor", "notes",
        ]
        values = [_clean_optional(data.get(field), 50_000 if field == "notes" else 1000) for field in fields]
        with transaction(self.connection):
            cursor = self.connection.execute(
                f"""INSERT INTO matters(
                    matter_uuid,client_id,title,matter_type,{','.join(fields)},custom_fields_json,status,created_at,updated_at
                ) VALUES({','.join('?' for _ in range(4 + len(fields) + 4))})""",
                [matter_uuid, client_id, title, matter_type, *values,
                 _canonical_custom(data.get("custom_fields")), "OPEN", now, now],
            )
            matter_id = int(cursor.lastrowid)
            self.audit.append("MATTER_CREATED", f"Created matter '{title}'.", entity_type="matter", entity_id=matter_id, user_id=user_id, details={"client_id": client_id, "matter_uuid": matter_uuid})
            return matter_id
