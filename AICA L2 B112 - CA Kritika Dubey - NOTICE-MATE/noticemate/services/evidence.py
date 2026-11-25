"""Module 6 — evidence mapping and assessment.

Auto-mapping links a requirement to a document of a plausible type, but only
ever sets REQUIRES_VERIFICATION (never SUFFICIENT). A user assessment must
explain what the document establishes and does not establish. Absence of
evidence is recorded as NOT_PROVIDED — it is never treated as proof of income."""
from __future__ import annotations

from ..core import audit
from ..core.db import ro, row_to_dict, tx, utcnow
from ..core.errors import NotFound, ValidationError
from . import cases
from .issues import _requirements

STATUSES = ("SUFFICIENT", "PARTIALLY_SUFFICIENT", "INSUFFICIENT", "NOT_PROVIDED", "CONTRADICTORY", "REQUIRES_VERIFICATION")


def auto_map(user: dict, case_id: int) -> int:
    cases.check_access(user, case_id)
    reqs = _requirements()
    with ro() as conn:
        issues = conn.execute("SELECT id, category FROM issues WHERE case_id=?", (case_id,)).fetchall()
        docs = conn.execute("SELECT id, doc_type FROM documents WHERE case_id=? ORDER BY doc_type_confirmed DESC, id", (case_id,)).fetchall()
        existing = {(r["issue_id"], r["requirement"]): r for r in
                    conn.execute("SELECT id, issue_id, requirement, document_id, source FROM evidence_items WHERE case_id=?", (case_id,))}
    by_type: dict[str, int] = {}
    for d in docs:
        by_type.setdefault(d["doc_type"], d["id"])
    created = 0
    now = utcnow()
    with tx() as conn:
        for iss in issues:
            for r in reqs[iss["category"]]["requirements"]:
                doc_id = next((by_type[t] for t in r["doc_types"] if t in by_type), None)
                ex = existing.get((iss["id"], r["key"]))
                if ex is None:
                    conn.execute(
                        "INSERT INTO evidence_items(case_id,issue_id,requirement,document_id,status,source,updated_at) VALUES (?,?,?,?,?,?,?)",
                        (case_id, iss["id"], r["key"], doc_id, "REQUIRES_VERIFICATION" if doc_id else "NOT_PROVIDED", "SYSTEM", now))
                    created += 1
                elif ex["source"] == "SYSTEM" and ex["document_id"] is None and doc_id:
                    conn.execute("UPDATE evidence_items SET document_id=?, status='REQUIRES_VERIFICATION', updated_at=? WHERE id=?",
                                 (doc_id, now, ex["id"]))
        audit.log_event(conn, "EVIDENCE_AUTOMAPPED", user_id=user["id"], case_id=case_id, meta={"created": created})
    return created


def assess(user: dict, evidence_id: int, *, status: str, establishes: str = "", does_not_establish: str = "",
           supports_explanation: str = "", inconsistency: str = "", document_id: int | None = None) -> dict:
    if status not in STATUSES:
        raise ValidationError(f"Status must be one of {STATUSES}.")
    e = get_item(user, evidence_id)
    doc = document_id if document_id is not None else e["document_id"]
    if status in ("SUFFICIENT", "PARTIALLY_SUFFICIENT") and not doc:
        raise ValidationError(f"{status} requires a linked document.")
    if status != "NOT_PROVIDED" and not (establishes or does_not_establish):
        raise ValidationError("Explain WHY: state what the evidence establishes and/or does not establish.")
    if status == "CONTRADICTORY" and not inconsistency:
        raise ValidationError("Describe the inconsistency.")
    if doc:
        with ro() as conn:
            ok = conn.execute("SELECT 1 FROM documents WHERE id=? AND case_id=?", (doc, e["case_id"])).fetchone()
        if not ok:
            raise ValidationError("Linked document must belong to the same case.")
    with tx() as conn:
        conn.execute(
            "UPDATE evidence_items SET status=?, establishes=?, does_not_establish=?, supports_explanation=?, inconsistency=?, "
            "document_id=?, source='USER', updated_by=?, updated_at=? WHERE id=?",
            (status, establishes[:2000], does_not_establish[:2000], supports_explanation[:1000], inconsistency[:2000],
             doc, user["id"], utcnow(), evidence_id))
        audit.log_event(conn, "EVIDENCE_ASSESSED", user_id=user["id"], case_id=e["case_id"],
                        meta={"evidence_id": evidence_id, "status": status, "document_id": doc})
    return get_item(user, evidence_id)


def get_item(user: dict, evidence_id: int) -> dict:
    with ro() as conn:
        r = conn.execute("SELECT * FROM evidence_items WHERE id=?", (evidence_id,)).fetchone()
    if not r:
        raise NotFound("Evidence item not found.")
    d = row_to_dict(r)
    cases.check_access(user, d["case_id"])
    return d


def list_for_issue(user: dict, issue_id: int) -> list[dict]:
    with ro() as conn:
        rows = conn.execute("SELECT e.*, d.original_name AS document_name FROM evidence_items e LEFT JOIN documents d ON d.id=e.document_id "
                            "WHERE e.issue_id=? ORDER BY e.id", (issue_id,)).fetchall()
    out = [row_to_dict(r) for r in rows]
    if out:
        cases.check_access(user, out[0]["case_id"])
    return out


def matrix(user: dict, case_id: int) -> list[dict]:
    cases.check_access(user, case_id)
    reqs = _requirements()
    with ro() as conn:
        rows = conn.execute(
            "SELECT e.*, i.seq, i.category, d.original_name AS document_name FROM evidence_items e JOIN issues i ON i.id=e.issue_id "
            "LEFT JOIN documents d ON d.id=e.document_id WHERE e.case_id=? ORDER BY i.seq, e.id", (case_id,)).fetchall()
    out = []
    for r in rows:
        d = row_to_dict(r)
        spec = next((x for x in reqs[d["category"]]["requirements"] if x["key"] == d["requirement"]), None)
        d["requirement_label"] = spec["label"] if spec else d["requirement"]
        d["client_question"] = spec["client_question"] if spec else None
        out.append(d)
    return out


def gaps(user: dict, case_id: int) -> list[dict]:
    return [m for m in matrix(user, case_id) if m["status"] in ("NOT_PROVIDED", "INSUFFICIENT", "PARTIALLY_SUFFICIENT",
                                                                  "CONTRADICTORY", "REQUIRES_VERIFICATION")]
