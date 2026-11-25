"""Modules 2 & 3 — upload pipeline, document register, annexure marking, search."""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..core import audit, storage
from ..core.config import get_settings
from ..core.db import dumps, ro, row_to_dict, tx, utcnow
from ..core.errors import Conflict, NotFound, ValidationError
from ..core.security import sha256_bytes, validate_upload
from . import cases
from .classification import DOC_TYPES, classify, index_terms
from .extraction import extract

_DOC_FIELDS = ("id,case_id,original_name,extension,size_bytes,sha256,encrypted,doc_type,doc_type_confidence,doc_type_confirmed,"
               "extraction_status,extraction_notes,page_count,is_annexure,annexure_label,uploaded_at,extraction_pages_json")


def upload(user: dict, case_id: int, filename: str, data: bytes) -> dict:
    cases.check_access(user, case_id)
    safe = validate_upload(filename, data, get_settings().max_upload_mb)
    ext = Path(safe).suffix.lower()
    digest = sha256_bytes(data)
    with ro() as conn:
        dup = conn.execute("SELECT id FROM documents WHERE case_id=? AND sha256=?", (case_id, digest)).fetchone()
    if dup:
        raise Conflict("This exact file is already in the case.", details={"document_id": dup["id"]})

    ex = extract(ext, data)
    doc_type, conf, _ = classify(ex.text, safe)
    stored, encrypted = storage.save_document(case_id, ext, data)
    try:
        with tx() as conn:
            cur = conn.execute(
                "INSERT INTO documents(case_id,original_name,stored_name,extension,size_bytes,sha256,encrypted,doc_type,"
                "doc_type_confidence,extraction_status,extraction_notes,page_count,uploaded_by,uploaded_at,extraction_pages_json)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (case_id, safe, stored, ext, len(data), digest, int(encrypted), doc_type, conf, ex.status,
                 dumps(ex.notes), ex.page_count, user["id"], utcnow(), dumps(ex.pages)),
            )
            did = cur.lastrowid
            conn.execute("INSERT INTO doc_text(document_id,text,tables_json) VALUES (?,?,?)", (did, ex.text, dumps(ex.tables)))
            conn.executemany("INSERT INTO doc_index(document_id,term,freq) VALUES (?,?,?)",
                             [(did, t, f) for t, f in index_terms(ex.text)])
            cases.touch(conn, case_id)
            audit.log_event(conn, "DOCUMENT_UPLOADED", user_id=user["id"], case_id=case_id,
                            meta={"document_id": did, "sha256": digest, "ext": ext, "bytes": len(data),
                                  "extraction_status": ex.status, "suggested_type": doc_type, "encrypted": encrypted})
    except Exception:
        storage.delete_document(case_id, stored)
        raise
    _remap(user, case_id)
    return get_document(user, did)


def _remap(user: dict, case_id: int) -> None:
    """Re-read the case's records against its issues (no-op before issues exist). Never blocks an upload/delete."""
    try:
        with ro() as conn:
            has = conn.execute("SELECT 1 FROM issues WHERE case_id=? LIMIT 1", (case_id,)).fetchone()
        if has:
            from .mapping import map_case

            map_case(user, case_id)
    except Exception:  # mapping is advisory; the document itself is safely stored
        import logging

        logging.getLogger("noticemate").exception("Mapping after document change failed")


def get_document(user: dict, document_id: int) -> dict:
    with ro() as conn:
        r = conn.execute(f"SELECT {_DOC_FIELDS} FROM documents WHERE id=?", (document_id,)).fetchone()
    if not r:
        raise NotFound("Document not found.")
    d = row_to_dict(r, ("extraction_notes", "extraction_pages_json"))
    cases.check_access(user, d["case_id"])
    return d


def list_documents(user: dict, case_id: int) -> list[dict]:
    cases.check_access(user, case_id)
    with ro() as conn:
        rows = conn.execute(f"SELECT {_DOC_FIELDS} FROM documents WHERE case_id=? ORDER BY id", (case_id,)).fetchall()
    return [row_to_dict(r, ("extraction_notes", "extraction_pages_json")) for r in rows]


def get_text(user: dict, document_id: int) -> dict:
    d = get_document(user, document_id)
    with ro() as conn:
        r = conn.execute("SELECT text, tables_json FROM doc_text WHERE document_id=?", (document_id,)).fetchone()
    return {"document_id": document_id, "doc_type": d["doc_type"], "text": r["text"] if r else "",
            "tables": json.loads(r["tables_json"]) if r else []}


def get_original(user: dict, document_id: int) -> tuple[str, bytes]:
    d = get_document(user, document_id)
    with ro() as conn:
        r = conn.execute("SELECT stored_name, encrypted FROM documents WHERE id=?", (document_id,)).fetchone()
    data = storage.load_document(d["case_id"], r["stored_name"], bool(r["encrypted"]))
    with tx() as conn:
        audit.log_event(conn, "DOCUMENT_OPENED", user_id=user["id"], case_id=d["case_id"], meta={"document_id": document_id})
    return d["original_name"], data


def set_type(user: dict, document_id: int, doc_type: str) -> dict:
    if doc_type not in DOC_TYPES and doc_type != "OTHER":
        raise ValidationError(f"doc_type must be one of {sorted(DOC_TYPES) + ['OTHER']}.")
    d = get_document(user, document_id)
    with tx() as conn:
        conn.execute("UPDATE documents SET doc_type=?, doc_type_confirmed=1 WHERE id=?", (doc_type, document_id))
        audit.log_event(conn, "DOCUMENT_TYPE_CONFIRMED", user_id=user["id"], case_id=d["case_id"],
                        meta={"document_id": document_id, "doc_type": doc_type, "previous": d["doc_type"]})
    return get_document(user, document_id)


_LABEL = re.compile(r"^[A-Z]{1,2}(-\d{1,3})?$")


def set_annexure(user: dict, document_id: int, is_annexure: bool, label: str | None) -> dict:
    d = get_document(user, document_id)
    if is_annexure:
        if not label or not _LABEL.match(label):
            raise ValidationError("Annexure label must look like A, B, AA or A-1.")
        with ro() as conn:
            clash = conn.execute("SELECT id FROM documents WHERE case_id=? AND annexure_label=? AND id<>? AND is_annexure=1",
                                 (d["case_id"], label, document_id)).fetchone()
        if clash:
            raise Conflict(f"Annexure {label} is already used by document {clash['id']}.")
    with tx() as conn:
        conn.execute("UPDATE documents SET is_annexure=?, annexure_label=? WHERE id=?",
                     (int(is_annexure), label if is_annexure else None, document_id))
        audit.log_event(conn, "ANNEXURE_SET", user_id=user["id"], case_id=d["case_id"],
                        meta={"document_id": document_id, "is_annexure": is_annexure, "label": label})
    return get_document(user, document_id)


def search(user: dict, case_id: int, query: str) -> list[dict]:
    cases.check_access(user, case_id)
    terms = [t for t in re.findall(r"[a-z0-9()\-/]{3,}", (query or "").lower())][:10]
    if not terms:
        raise ValidationError("Enter at least one search term of 3+ characters.")
    q = ",".join("?" * len(terms))
    with ro() as conn:
        rows = conn.execute(
            f"SELECT d.id, d.original_name, d.doc_type, SUM(i.freq) AS score FROM doc_index i JOIN documents d ON d.id=i.document_id "
            f"WHERE d.case_id=? AND i.term IN ({q}) GROUP BY d.id ORDER BY score DESC LIMIT 50",
            (case_id, *terms),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_impact(user: dict, document_id: int) -> dict:
    """What deleting this file would remove — shown to the user before they confirm."""
    d = get_document(user, document_id)
    with ro() as conn:
        notice = conn.execute("SELECT COUNT(*) FROM notices WHERE document_id=?", (document_id,)).fetchone()[0]
        links = conn.execute("SELECT COUNT(*) FROM doc_links WHERE document_id=?", (document_id,)).fetchone()[0]
        ev = conn.execute("SELECT COUNT(*) FROM evidence_items WHERE document_id=?", (document_id,)).fetchone()[0]
        facts = conn.execute("SELECT COUNT(*) FROM proposition_facts WHERE document_id=?", (document_id,)).fetchone()[0]
    return {"document_id": document_id, "name": d["original_name"], "is_notice": bool(notice), "issue_links": links,
            "evidence_links": ev, "proposition_facts": facts, "is_annexure": bool(d.get("is_annexure"))}


def delete(user: dict, document_id: int) -> dict:
    d = get_document(user, document_id)
    if user["role"] not in ("ADMIN", "CA"):
        from ..core.errors import PermissionDenied

        raise PermissionDenied("Only ADMIN or CA can delete documents.")
    impact = delete_impact(user, document_id)
    if impact["is_notice"]:
        raise ValidationError("This file is the notice the case was built from. Delete the case instead, or upload the "
                              "corrected notice as a new case.")
    with ro() as conn:
        r = conn.execute("SELECT stored_name FROM documents WHERE id=?", (document_id,)).fetchone()
    with tx() as conn:
        # links to issues/evidence/propositions go with the file; evidence rows simply lose the document
        conn.execute("UPDATE evidence_items SET document_id=NULL, status=CASE WHEN source='SYSTEM' THEN 'NOT_PROVIDED' ELSE status END "
                     "WHERE document_id=?", (document_id,))
        conn.execute("DELETE FROM documents WHERE id=?", (document_id,))
        audit.log_event(conn, "DOCUMENT_DELETED", user_id=user["id"], case_id=d["case_id"],
                        meta={"document_id": document_id, "sha256": d["sha256"], "name": d["original_name"],
                              "issue_links_removed": impact["issue_links"], "evidence_links_cleared": impact["evidence_links"]})
    storage.delete_document(d["case_id"], r["stored_name"])
    _remap(user, d["case_id"])
    return impact


def docs_by_type(case_id: int) -> dict[str, list[dict]]:
    with ro() as conn:
        rows = conn.execute("SELECT id, original_name, doc_type, doc_type_confirmed, is_annexure, annexure_label "
                            "FROM documents WHERE case_id=?", (case_id,)).fetchall()
    out: dict[str, list[dict]] = {}
    for r in rows:
        out.setdefault(r["doc_type"], []).append(dict(r))
    return out
