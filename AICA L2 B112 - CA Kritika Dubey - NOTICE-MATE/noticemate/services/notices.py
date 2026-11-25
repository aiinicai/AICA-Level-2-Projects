"""Module 4 — notice records: particulars extraction, manual correction,
deadline verification and applicable-law determination."""
from __future__ import annotations

import json
import re
from datetime import date

from ..core import audit
from ..core.db import dumps, ro, row_to_dict, tx, utcnow
from ..core.errors import NotFound, ValidationError
from . import cases, documents
from .notice_parser import NP, extract_particulars
from .taxlaw import determine_applicable_law

CORE_FIELDS = ["issuing_authority", "section", "notice_type", "din", "assessment_year", "date_of_issue", "date_of_service",
               "compliance_deadline", "nature"]
EDITABLE = {"notice_type", "section", "din", "notice_number", "assessment_year", "tax_year", "previous_year", "issuing_authority",
            "date_of_issue", "date_of_service", "nature", "scrutiny_scope", "non_compliance_consequences"}


def _law_for(p: dict) -> dict | None:
    ay = p.get("assessment_year", {}).get("value")
    ty = p.get("tax_year", {}).get("value")
    nd = p.get("date_of_issue", {}).get("value")
    nd = nd if nd and nd != NP else None
    try:
        if ay and ay != NP and re.match(r"^\d{4}-\d{2}$", ay):
            return determine_applicable_law(ay, "AY", nd)
        if ty and ty != NP and re.match(r"^\d{4}-\d{2}$", ty):
            return determine_applicable_law(ty, "TAX_YEAR", nd)
    except ValidationError:
        return None
    return None


def create_from_document(user: dict, document_id: int, *, acknowledge_partial: bool = False) -> dict:
    t = documents.get_text(user, document_id)
    d = documents.get_document(user, document_id)
    if d.get("extraction_status") == "FAILED" or not t["text"].strip():
        raise ValidationError("No text could be read from this document, so it cannot be parsed. "
                              "Run the OCR check and re-upload a clearer scan.",
                              details={"extraction_status": d.get("extraction_status")})
    if d.get("extraction_status") == "PARTIAL" and not acknowledge_partial:
        bad = [p["page"] for p in (d.get("extraction_pages_json") or []) if p.get("status") in ("BLANK", "FAILED")]
        raise ValidationError("Only part of this document could be read (page(s) %s). Confirm that you will check the "
                              "missing pages against the original before parsing." % (bad or "unknown"),
                              details={"extraction_status": "PARTIAL", "unreadable_pages": bad, "needs_acknowledgement": True})
    p = extract_particulars(t["text"])
    law = _law_for(p)
    now = utcnow()
    with tx() as conn:
        cur = conn.execute(
            "INSERT INTO notices(case_id,document_id,particulars_json,applicable_law_json,created_at,updated_at) VALUES (?,?,?,?,?,?)",
            (d["case_id"], document_id, dumps(p), dumps(law) if law else None, now, now))
        nid = cur.lastrowid
        cases.touch(conn, d["case_id"])
        audit.log_event(conn, "NOTICE_PARSED", user_id=user["id"], case_id=d["case_id"],
                        meta={"notice_id": nid, "document_id": document_id, "extraction_status": d.get("extraction_status"),
                              "partial_acknowledged": bool(acknowledge_partial),
                              "fields_found": sum(1 for v in p.values() if v["status"] != NP)})
    return get_notice(user, nid)


def get_notice(user: dict, notice_id: int) -> dict:
    with ro() as conn:
        r = conn.execute("SELECT * FROM notices WHERE id=?", (notice_id,)).fetchone()
    if not r:
        raise NotFound("Notice not found.")
    d = row_to_dict(r, ("particulars_json", "applicable_law_json"))
    cases.check_access(user, d["case_id"])
    d["deadline_banner"] = (f"VERIFIED DEADLINE: {d['deadline_value']}" if d["deadline_verified"]
                            else "COMPLIANCE DEADLINE NOT VERIFIED — check the e-proceedings portal before relying on any date.")
    d["completeness"] = completeness(d)
    return d


def completeness(n: dict) -> dict:
    """Which core particulars are missing, which still need verification, and any
    extraction/OCR warnings from the source document — so nothing is silently assumed."""
    p = n["particulars_json"]
    if "notice_type" not in p:  # v1 records: derive display value from 'nature' without inventing
        nat = (p.get("nature") or {}).get("value")
        p["notice_type"] = {"value": nat.split(" — ")[0] if nat and nat != NP else NP,
                            "status": "DERIVED" if nat and nat != NP else NP, "source_snippet": "Derived from section mapping",
                            "needs_verification": True, "note": None}
    missing = [f for f in CORE_FIELDS if (p.get(f) or {}).get("value") in (None, "", NP)]
    verify = [f for f in CORE_FIELDS if f not in missing and (p.get(f) or {}).get("needs_verification")
              and (p.get(f) or {}).get("status") != "USER_ENTERED"]
    if n.get("deadline_verified") and "compliance_deadline" in verify:
        verify.remove("compliance_deadline")
    warnings: list[str] = []
    if n.get("document_id"):
        with ro() as conn:
            r = conn.execute("SELECT extraction_status, extraction_notes FROM documents WHERE id=?", (n["document_id"],)).fetchone()
        if r:
            if r["extraction_status"] != "OK":
                warnings.append(f"Source document extraction status: {r['extraction_status']}.")
            try:
                warnings += json.loads(r["extraction_notes"] or "[]")
            except ValueError:
                pass
    score = round(100 * (len(CORE_FIELDS) - len(missing)) / len(CORE_FIELDS))
    return {"missing": missing, "needs_verification": verify, "extraction_warnings": warnings, "completeness_pct": score}


def list_notices(user: dict, case_id: int) -> list[dict]:
    cases.check_access(user, case_id)
    with ro() as conn:
        ids = [r["id"] for r in conn.execute("SELECT id FROM notices WHERE case_id=? ORDER BY id", (case_id,))]
    return [get_notice(user, i) for i in ids]


def update_field(user: dict, notice_id: int, field: str, value: str) -> dict:
    if field not in EDITABLE:
        raise ValidationError(f"Editable fields: {sorted(EDITABLE)} (deadline uses verify_deadline).")
    if value is None or len(value) > 500:
        raise ValidationError("Value required (max 500 chars).")
    n = get_notice(user, notice_id)
    p = n["particulars_json"]
    p[field] = {"value": value.strip() or NP, "status": "USER_ENTERED" if value.strip() else NP,
                "source_snippet": "Entered by user", "needs_verification": False, "note": None}
    law = _law_for(p)
    with tx() as conn:
        conn.execute("UPDATE notices SET particulars_json=?, applicable_law_json=?, updated_at=? WHERE id=?",
                     (dumps(p), dumps(law) if law else None, utcnow(), notice_id))
        audit.log_event(conn, "NOTICE_FIELD_EDITED", user_id=user["id"], case_id=n["case_id"],
                        meta={"notice_id": notice_id, "field": field})
    return get_notice(user, notice_id)


def verify_deadline(user: dict, notice_id: int, deadline_iso: str, source: str) -> dict:
    try:
        dl = date.fromisoformat(deadline_iso)
    except ValueError:
        raise ValidationError("Deadline must be YYYY-MM-DD.")
    if not source or len(source) < 5:
        raise ValidationError("State where the deadline was verified (e.g., 'e-proceedings portal, viewed on …').")
    n = get_notice(user, notice_id)
    with tx() as conn:
        conn.execute("UPDATE notices SET deadline_verified=1, deadline_verified_by=?, deadline_value=?, updated_at=? WHERE id=?",
                     (user["id"], dl.isoformat(), utcnow(), notice_id))
        audit.log_event(conn, "DEADLINE_VERIFIED", user_id=user["id"], case_id=n["case_id"],
                        meta={"notice_id": notice_id, "deadline": dl.isoformat(), "source": source[:200]})
    return get_notice(user, notice_id)


def upcoming_deadlines(user: dict) -> list[dict]:
    out = []
    for c in cases.list_cases(user):
        for n in list_notices(user, c["id"]):
            p = n["particulars_json"]
            out.append({"case_id": c["id"], "case_ref": c["case_ref"], "notice_id": n["id"],
                        "section": p.get("section", {}).get("value"),
                        "deadline": n["deadline_value"] if n["deadline_verified"] else p.get("compliance_deadline", {}).get("value"),
                        "verified": bool(n["deadline_verified"])})
    return sorted(out, key=lambda x: (x["deadline"] or "9999"))
