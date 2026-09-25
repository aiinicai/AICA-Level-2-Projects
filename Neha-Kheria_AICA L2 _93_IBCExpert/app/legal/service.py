"""Generic legal database import, versioning, verification and FTS5 search."""
from __future__ import annotations

import json
import re
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.errors import ValidationError
from app.core.time import Clock, SystemClock, to_utc_iso
from app.db.connection import transaction
from app.security.audit import AuditService

VERIFICATION_STATES = {"VERIFIED", "UNVERIFIED", "REVIEW_REQUIRED", "SUPERSEDED"}
LEGAL_ENTITY_TYPES = {"provision", "judgment", "circular", "notification"}


def _required(value: Any, label: str, limit: int = 1000) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValidationError(f"{label} is required.")
    if len(text) > limit:
        raise ValidationError(f"{label} is too long.")
    return text


def _optional(value: Any, limit: int = 5000) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) > limit:
        raise ValidationError("Legal metadata value is too long.")
    return text


def _verification(value: str | None) -> str:
    value = value or "REVIEW_REQUIRED"
    if value not in VERIFICATION_STATES:
        raise ValidationError("Legal verification status is invalid.")
    return value


def _fts_query(query: str, exact_phrase: bool) -> str:
    query = query.strip()
    if not query:
        raise ValidationError("Enter text to search.")
    if exact_phrase:
        return '"' + query.replace('"', '""') + '"'
    tokens = re.findall(r"[\w§.-]+", query, flags=re.UNICODE)
    if not tokens:
        raise ValidationError("Search contains no searchable terms.")
    return " AND ".join('"' + token.replace('"', '""') + '"' for token in tokens[:20])


@dataclass
class LegalService:
    connection: sqlite3.Connection
    audit: AuditService
    clock: Clock = SystemClock()

    def add_statute(self, data: dict[str, Any], user_id: int | None = None) -> int:
        now = to_utc_iso(self.clock.now())
        title = _required(data.get("title"), "Statute title", 500)
        status = _verification(data.get("verification_status"))
        with transaction(self.connection):
            cursor = self.connection.execute(
                """INSERT INTO statutes(
                    statute_uuid,title,short_title,statute_type,jurisdiction,enactment_date,
                    commencement_date,identifier,verification_status,source_document_id,
                    created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(uuid.uuid4()), title, _optional(data.get("short_title"), 200),
                    _required(data.get("statute_type"), "Statute type", 100),
                    _optional(data.get("jurisdiction"), 100) or "India",
                    _optional(data.get("enactment_date"), 30),
                    _optional(data.get("commencement_date"), 30),
                    _optional(data.get("identifier"), 200), status,
                    data.get("source_document_id"), now, now,
                ),
            )
            statute_id = int(cursor.lastrowid)
            self.audit.append(
                "STATUTE_ADDED", f"Added legal source '{title}'.", entity_type="statute",
                entity_id=statute_id, user_id=user_id, details={"verification_status": status},
            )
            return statute_id

    def update_statute(self, statute_id: int, data: dict[str, Any], user_id: int | None = None) -> None:
        allowed = {"title", "short_title", "statute_type", "jurisdiction", "enactment_date", "commencement_date", "identifier", "verification_status", "source_document_id"}
        unknown = set(data) - allowed
        if unknown:
            raise ValidationError(f"Unknown statute field(s): {', '.join(sorted(unknown))}")
        row = self.connection.execute("SELECT * FROM statutes WHERE id=?", (statute_id,)).fetchone()
        if row is None:
            raise ValidationError("Legal source was not found.")
        values: dict[str, Any] = {}
        for field, value in data.items():
            if field in {"title", "statute_type"}:
                values[field] = _required(value, field.replace("_", " ").title(), 500)
            elif field == "verification_status":
                values[field] = _verification(value)
            elif field == "source_document_id":
                values[field] = value
            else:
                values[field] = _optional(value, 500)
        if not values:
            return
        with transaction(self.connection):
            self.connection.execute(
                f"UPDATE statutes SET {','.join(field+'=?' for field in values)},updated_at=? WHERE id=?",
                [*values.values(), to_utc_iso(self.clock.now()), statute_id],
            )
            self.audit.append("STATUTE_UPDATED", "Updated legal-source metadata.", entity_type="statute", entity_id=statute_id, user_id=user_id, details={"fields": sorted(values)})

    def add_provision(self, statute_id: int, data: dict[str, Any], user_id: int | None = None) -> int:
        statute = self.connection.execute("SELECT * FROM statutes WHERE id=?", (statute_id,)).fetchone()
        if statute is None:
            raise ValidationError("Statute was not found.")
        now = to_utc_iso(self.clock.now())
        text = _required(data.get("text_content"), "Provision text", 2_000_000)
        status = _verification(data.get("verification_status"))
        provision_uuid = data.get("provision_uuid") or str(uuid.uuid4())
        with transaction(self.connection):
            cursor = self.connection.execute(
                """INSERT INTO legal_provisions(
                    provision_uuid,statute_id,parent_id,provision_type,number_label,heading,
                    text_content,effective_from,effective_to,source_document_id,source_page,
                    amendment_identifier,verification_status,supersedes_id,imported_at,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    provision_uuid, statute_id, data.get("parent_id"),
                    _required(data.get("provision_type"), "Provision type", 100),
                    _optional(data.get("number_label"), 100), _optional(data.get("heading"), 1000),
                    text, _optional(data.get("effective_from"), 30), _optional(data.get("effective_to"), 30),
                    data.get("source_document_id"), data.get("source_page"),
                    _optional(data.get("amendment_identifier"), 300), status,
                    data.get("supersedes_id"), now, now,
                ),
            )
            provision_id = int(cursor.lastrowid)
            citation = f"{statute['short_title'] or statute['title']} {data.get('provision_type','')} {data.get('number_label') or ''}".strip()
            self.connection.execute(
                "INSERT INTO search_index(entity_type,entity_id,title,body,citation,verification_status) VALUES(?,?,?,?,?,?)",
                ("provision", str(provision_id), data.get("heading") or citation, text, citation, status),
            )
            self.audit.append("LEGAL_PROVISION_ADDED", f"Added {citation}.", entity_type="legal_provision", entity_id=provision_id, user_id=user_id, details={"verification_status": status})
            return provision_id

    def version_provision(self, prior_id: int, effective_from: str, new_text: str, amendment_identifier: str, source_document_id: int | None = None, source_page: int | None = None, verification_status: str = "REVIEW_REQUIRED", user_id: int | None = None) -> int:
        prior = self.connection.execute("SELECT * FROM legal_provisions WHERE id=?", (prior_id,)).fetchone()
        if prior is None:
            raise ValidationError("Provision version was not found.")
        if prior["effective_from"] and effective_from <= prior["effective_from"]:
            raise ValidationError("New version must start after the previous version.")
        with transaction(self.connection):
            self.connection.execute(
                "UPDATE legal_provisions SET effective_to=?,verification_status=CASE WHEN verification_status='VERIFIED' THEN 'SUPERSEDED' ELSE verification_status END WHERE id=?",
                (effective_from, prior_id),
            )
            self.connection.execute(
                "UPDATE search_index SET verification_status='SUPERSEDED' WHERE entity_type='provision' AND entity_id=?",
                (str(prior_id),),
            )
            new_id = self.add_provision(prior["statute_id"], {
                "provision_uuid": prior["provision_uuid"], "parent_id": prior["parent_id"],
                "provision_type": prior["provision_type"], "number_label": prior["number_label"],
                "heading": prior["heading"], "text_content": new_text,
                "effective_from": effective_from, "source_document_id": source_document_id,
                "source_page": source_page, "amendment_identifier": amendment_identifier,
                "verification_status": verification_status, "supersedes_id": prior_id,
            }, user_id=user_id)
            self.audit.append("LEGAL_PROVISION_VERSIONED", "Created an amended point-in-time legal provision version.", entity_type="legal_provision", entity_id=new_id, user_id=user_id, details={"supersedes_id": prior_id, "effective_from": effective_from})
            return new_id

    def provision_at(self, provision_uuid: str, on_date: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            """SELECT p.*,s.title AS statute_title,s.short_title FROM legal_provisions p
               JOIN statutes s ON s.id=p.statute_id
               WHERE p.provision_uuid=?
                 AND (p.effective_from IS NULL OR p.effective_from<=?)
                 AND (p.effective_to IS NULL OR p.effective_to>?)
               ORDER BY COALESCE(p.effective_from,'0000-00-00') DESC LIMIT 1""",
            (provision_uuid, on_date, on_date),
        ).fetchone()
        return dict(row) if row else None

    def add_judgment(self, data: dict[str, Any], user_id: int | None = None) -> int:
        now = to_utc_iso(self.clock.now())
        title = _required(data.get("title"), "Judgment title", 1000)
        text = _required(data.get("text_content"), "Judgment text", 5_000_000)
        court = _required(data.get("court"), "Court/tribunal", 300)
        status = _verification(data.get("verification_status"))
        with transaction(self.connection):
            cursor = self.connection.execute(
                """INSERT INTO judgments(
                    judgment_uuid,title,neutral_citation,reported_citation,court,bench,judgment_date,
                    case_number,parties,text_content,holding_summary,source_document_id,source_page,
                    verification_status,imported_at,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(uuid.uuid4()), title, _optional(data.get("neutral_citation"), 300),
                    _optional(data.get("reported_citation"), 300), court, _optional(data.get("bench"), 500),
                    _optional(data.get("judgment_date"), 30), _optional(data.get("case_number"), 300),
                    _optional(data.get("parties"), 2000), text, _optional(data.get("holding_summary"), 20_000),
                    data.get("source_document_id"), data.get("source_page"), status, now, now,
                ),
            )
            judgment_id = int(cursor.lastrowid)
            citation = data.get("neutral_citation") or data.get("reported_citation") or data.get("case_number") or title
            self.connection.execute(
                "INSERT INTO search_index(entity_type,entity_id,title,body,citation,verification_status) VALUES(?,?,?,?,?,?)",
                ("judgment", str(judgment_id), title, text, citation, status),
            )
            self.audit.append("JUDGMENT_ADDED", f"Added judgment '{title}'.", entity_type="judgment", entity_id=judgment_id, user_id=user_id, details={"verification_status": status})
            return judgment_id

    def add_citation(self, citation_text: str, *, statute_id: int | None = None, provision_id: int | None = None, judgment_id: int | None = None, source_document_id: int | None = None, source_page: int | None = None, verification_status: str = "REVIEW_REQUIRED") -> int:
        if not any((statute_id, provision_id, judgment_id, source_document_id)):
            raise ValidationError("Citation must refer to an imported legal source.")
        cursor = self.connection.execute(
            """INSERT INTO citations(citation_text,statute_id,provision_id,judgment_id,source_document_id,source_page,verification_status,created_at)
               VALUES(?,?,?,?,?,?,?,?)""",
            (_required(citation_text, "Citation", 1000), statute_id, provision_id, judgment_id, source_document_id, source_page, _verification(verification_status), to_utc_iso(self.clock.now())),
        )
        return int(cursor.lastrowid)

    def search(self, query: str, *, exact_phrase: bool = False, entity_type: str | None = None, verification_status: str | None = None, statute_id: int | None = None, limit: int = 50) -> list[dict[str, Any]]:
        if not 1 <= limit <= 200:
            raise ValidationError("Legal search limit is invalid.")
        if entity_type and entity_type not in LEGAL_ENTITY_TYPES | {"document"}:
            raise ValidationError("Legal search entity filter is invalid.")
        if verification_status:
            _verification(verification_status)
        clauses = ["search_index MATCH ?"]
        params: list[Any] = [_fts_query(query, exact_phrase)]
        if entity_type:
            clauses.append("entity_type=?")
            params.append(entity_type)
        if verification_status:
            clauses.append("verification_status=?")
            params.append(verification_status)
        params.append(limit * 3 if statute_id else limit)
        rows = self.connection.execute(
            f"""SELECT rowid,entity_type,entity_id,title,
                       snippet(search_index,3,'<mark>','</mark>',' … ',24) AS snippet,
                       citation,verification_status,bm25(search_index,2.0,1.0,2.0) AS rank
                FROM search_index WHERE {' AND '.join(clauses)} ORDER BY rank LIMIT ?""",
            params,
        ).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["source_document_id"] = None
            item["source_page"] = None
            if row["entity_type"] == "provision":
                detail = self.connection.execute("SELECT statute_id,source_document_id,source_page,provision_type,number_label,effective_from,effective_to FROM legal_provisions WHERE id=?", (row["entity_id"],)).fetchone()
                if not detail or (statute_id is not None and int(detail["statute_id"]) != statute_id):
                    continue
                item.update(dict(detail))
            elif row["entity_type"] == "judgment":
                detail = self.connection.execute("SELECT source_document_id,source_page,court,judgment_date,neutral_citation,reported_citation FROM judgments WHERE id=?", (row["entity_id"],)).fetchone()
                if detail:
                    item.update(dict(detail))
            elif statute_id is not None:
                continue
            results.append(item)
            if len(results) >= limit:
                break
        return results

    def import_json_package(self, package_path: Path | str, user_id: int | None = None) -> dict[str, int]:
        try:
            package = json.loads(Path(package_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValidationError("Legal import package is unreadable or invalid JSON.") from exc
        if package.get("format") != "IBC-EXPERT-LEGAL-1" or not isinstance(package.get("statutes"), list):
            raise ValidationError("Legal import package format is not supported.")
        counts = {"statutes": 0, "provisions": 0, "judgments": 0}
        with transaction(self.connection):
            for statute_data in package["statutes"]:
                provisions = statute_data.pop("provisions", [])
                statute_id = self.add_statute(statute_data, user_id)
                counts["statutes"] += 1
                for provision in provisions:
                    self.add_provision(statute_id, provision, user_id)
                    counts["provisions"] += 1
            for judgment in package.get("judgments", []):
                self.add_judgment(judgment, user_id)
                counts["judgments"] += 1
            self.audit.append("LEGAL_PACKAGE_IMPORTED", "Imported legal knowledge package.", entity_type="legal_import", user_id=user_id, details=counts)
        return counts

    def list_statutes(self, *, verification_status: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
        if verification_status:
            _verification(verification_status)
        clauses = []
        params: list[Any] = []
        if verification_status:
            clauses.append("verification_status=?")
            params.append(verification_status)
        params.append(limit)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.connection.execute(
            f"""SELECT s.*, d.original_filename AS source_filename,
                       (SELECT COUNT(*) FROM legal_provisions p WHERE p.statute_id=s.id) AS provision_count
                FROM statutes s LEFT JOIN documents d ON d.id=s.source_document_id
                {where} ORDER BY s.title COLLATE NOCASE LIMIT ?""", params
        ).fetchall()
        return [dict(row) for row in rows]

    def statute_detail(self, statute_id: int) -> dict[str, Any]:
        row = self.connection.execute(
            """SELECT s.*,d.original_filename AS source_filename FROM statutes s
               LEFT JOIN documents d ON d.id=s.source_document_id WHERE s.id=?""", (statute_id,)
        ).fetchone()
        if row is None:
            raise ValidationError("Legal source was not found.")
        item = dict(row)
        item["provisions"] = [dict(r) for r in self.connection.execute(
            """SELECT p.*,d.original_filename AS source_filename FROM legal_provisions p
               LEFT JOIN documents d ON d.id=p.source_document_id
               WHERE p.statute_id=? ORDER BY COALESCE(p.number_label,''),COALESCE(p.effective_from,'') DESC,p.id""", (statute_id,)
        ).fetchall()]
        item["amendments"] = [dict(r) for r in self.connection.execute(
            "SELECT * FROM amendments WHERE statute_id=? ORDER BY COALESCE(effective_date,'') DESC,id DESC", (statute_id,)
        ).fetchall()]
        return item

    def provision_detail(self, provision_id: int) -> dict[str, Any]:
        row = self.connection.execute(
            """SELECT p.*,s.title AS statute_title,s.short_title,d.original_filename AS source_filename
               FROM legal_provisions p JOIN statutes s ON s.id=p.statute_id
               LEFT JOIN documents d ON d.id=p.source_document_id WHERE p.id=?""", (provision_id,)
        ).fetchone()
        if row is None:
            raise ValidationError("Legal provision was not found.")
        item = dict(row)
        item["versions"] = [dict(r) for r in self.connection.execute(
            """SELECT id,effective_from,effective_to,amendment_identifier,verification_status,source_page
               FROM legal_provisions WHERE provision_uuid=? ORDER BY COALESCE(effective_from,'0000-00-00') DESC,id DESC""",
            (row["provision_uuid"],),
        ).fetchall()]
        return item

    def list_judgments(self, *, verification_status: str | None = None, court: str | None = None, limit: int = 250) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if verification_status:
            _verification(verification_status); clauses.append("j.verification_status=?"); params.append(verification_status)
        if court:
            clauses.append("j.court LIKE ?"); params.append(f"%{court.strip()}%")
        params.append(limit)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.connection.execute(
            f"""SELECT j.*,d.original_filename AS source_filename FROM judgments j
                LEFT JOIN documents d ON d.id=j.source_document_id {where}
                ORDER BY COALESCE(j.judgment_date,'') DESC,j.title COLLATE NOCASE LIMIT ?""", params
        ).fetchall()
        return [dict(r) for r in rows]

    def judgment_detail(self, judgment_id: int) -> dict[str, Any]:
        row = self.connection.execute(
            """SELECT j.*,d.original_filename AS source_filename FROM judgments j
               LEFT JOIN documents d ON d.id=j.source_document_id WHERE j.id=?""", (judgment_id,)
        ).fetchone()
        if row is None:
            raise ValidationError("Judgment was not found.")
        return dict(row)

    def set_verification_status(self, entity_type: str, entity_id: int, status: str, user_id: int | None = None) -> None:
        status = _verification(status)
        mapping = {"statute": ("statutes", "id"), "provision": ("legal_provisions", "id"), "judgment": ("judgments", "id")}
        if entity_type not in mapping:
            raise ValidationError("Unsupported legal entity type.")
        table, key = mapping[entity_type]
        row = self.connection.execute(f"SELECT {key} FROM {table} WHERE {key}=?", (entity_id,)).fetchone()
        if row is None:
            raise ValidationError("Legal item was not found.")
        with transaction(self.connection):
            self.connection.execute(f"UPDATE {table} SET verification_status=? WHERE {key}=?", (status, entity_id))
            if entity_type in {"provision", "judgment"}:
                self.connection.execute("UPDATE search_index SET verification_status=? WHERE entity_type=? AND entity_id=?", (status, entity_type, str(entity_id)))
            self.audit.append("LEGAL_VERIFICATION_UPDATED", f"Set {entity_type} verification status to {status}.", entity_type=entity_type, entity_id=entity_id, user_id=user_id, details={"verification_status": status})
