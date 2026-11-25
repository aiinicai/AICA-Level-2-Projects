"""Module 1 & 12 — local case workspaces, membership-based access, history."""
from __future__ import annotations

import json
import re

from ..core import audit
from ..core.db import dumps, ro, row_to_dict, tx, utcnow
from ..core.errors import NotFound, PermissionDenied, ValidationError
from ..core.pii import mask_pan
from .auth import require_role

CATEGORIES = ("INDIVIDUAL", "HUF", "FIRM", "LLP", "COMPANY_DOMESTIC", "AOP_BOI", "OTHER")
_AY = re.compile(r"^\d{4}-\d{2}$")
_PAN = re.compile(r"^[A-Z]{5}\d{4}[A-Z]$")


def _validate(assessee_name: str, category: str, pan: str | None, ay: str | None) -> None:
    if not assessee_name or len(assessee_name) > 200:
        raise ValidationError("Assessee name is required (max 200 chars).")
    if category not in CATEGORIES:
        raise ValidationError(f"Assessee category must be one of {CATEGORIES}.")
    if pan and not _PAN.match(pan):
        raise ValidationError("PAN format is invalid (use a FICTITIOUS PAN for testing).")
    if ay:
        if not _AY.match(ay) or (int(ay[:4]) + 1) % 100 != int(ay[5:7]):
            raise ValidationError("Assessment/Tax year must look like 2026-27.")


def create_case(user: dict, *, case_ref: str, assessee_name: str, assessee_category: str, pan: str | None = None,
                assessment_year: str | None = None, party_names: list[str] | None = None) -> dict:
    pan = (pan or "").strip().upper() or None
    _validate(assessee_name, assessee_category, pan, assessment_year)
    if not case_ref or not re.match(r"^[A-Za-z0-9_\-/]{1,60}$", case_ref):
        raise ValidationError("Case reference: 1-60 chars, letters/digits/-/_// only.")
    names = sorted({assessee_name.strip(), *[n.strip() for n in (party_names or []) if n.strip()]})
    now = utcnow()
    with tx() as conn:
        cur = conn.execute(
            "INSERT INTO cases(case_ref,assessee_name,assessee_category,pan,assessment_year,party_names,created_by,created_at,updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (case_ref, assessee_name.strip(), assessee_category, pan, assessment_year, dumps(names), user["id"], now, now),
        )
        cid = cur.lastrowid
        conn.execute("INSERT INTO case_members(case_id,user_id) VALUES (?,?)", (cid, user["id"]))
        audit.log_event(conn, "CASE_CREATED", user_id=user["id"], case_id=cid, meta={"category": assessee_category, "ay": assessment_year})
    return get_case(user, cid)


def check_access(user: dict, case_id: int) -> None:
    if user["role"] == "ADMIN":
        return
    with ro() as conn:
        ok = conn.execute("SELECT 1 FROM case_members WHERE case_id=? AND user_id=?", (case_id, user["id"])).fetchone()
        exists = ok or conn.execute("SELECT 1 FROM cases WHERE id=?", (case_id,)).fetchone()
    if not exists:
        raise NotFound("Case not found — it may have been deleted.")
    if not ok:
        raise PermissionDenied("You do not have access to this case.")


def get_case(user: dict, case_id: int, *, include_pan: bool = False) -> dict:
    check_access(user, case_id)
    with ro() as conn:
        r = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    if not r:
        raise NotFound("Case not found.")
    d = row_to_dict(r, ("party_names",))
    d["pan_masked"] = mask_pan(d.get("pan"))
    if not include_pan:
        d.pop("pan", None)
    return d


def list_cases(user: dict) -> list[dict]:
    with ro() as conn:
        if user["role"] == "ADMIN":
            rows = conn.execute("SELECT * FROM cases ORDER BY updated_at DESC").fetchall()
        else:
            rows = conn.execute(
                "SELECT c.* FROM cases c JOIN case_members m ON m.case_id=c.id WHERE m.user_id=? ORDER BY c.updated_at DESC",
                (user["id"],),
            ).fetchall()
    out = []
    for r in rows:
        d = row_to_dict(r, ("party_names",))
        d["pan_masked"] = mask_pan(d.pop("pan", None))
        out.append(d)
    return out


def update_party_names(user: dict, case_id: int, names: list[str]) -> dict:
    case = get_case(user, case_id)
    clean = sorted({case["assessee_name"], *[n.strip() for n in names if n and n.strip()]})
    if any(len(n) > 200 for n in clean):
        raise ValidationError("Each redaction term must be ≤ 200 chars.")
    with tx() as conn:
        conn.execute("UPDATE cases SET party_names=?, updated_at=? WHERE id=?", (dumps(clean), utcnow(), case_id))
        audit.log_event(conn, "REDACTION_TERMS_UPDATED", user_id=user["id"], case_id=case_id, meta={"n_terms": len(clean)})
    return get_case(user, case_id)


def add_member(user: dict, case_id: int, member_user_id: int) -> None:
    check_access(user, case_id)
    if user["role"] not in ("ADMIN", "CA"):
        raise PermissionDenied("Only ADMIN or CA can add case members.")
    with tx() as conn:
        conn.execute("INSERT OR IGNORE INTO case_members(case_id,user_id) VALUES (?,?)", (case_id, member_user_id))
        audit.log_event(conn, "CASE_MEMBER_ADDED", user_id=user["id"], case_id=case_id, meta={"member_user_id": member_user_id})


def set_status(user: dict, case_id: int, status: str) -> None:
    if status not in ("OPEN", "AWAITING_CLIENT", "UNDER_REVIEW", "APPROVED", "SUBMITTED", "CLOSED"):
        raise ValidationError("Invalid status.")
    check_access(user, case_id)
    with tx() as conn:
        conn.execute("UPDATE cases SET status=?, updated_at=? WHERE id=?", (status, utcnow(), case_id))
        audit.log_event(conn, "CASE_STATUS", user_id=user["id"], case_id=case_id, meta={"status": status})


def touch(conn, case_id: int) -> None:
    conn.execute("UPDATE cases SET updated_at=? WHERE id=?", (utcnow(), case_id))


def party_terms(case_id: int) -> list[str]:
    with ro() as conn:
        r = conn.execute("SELECT party_names, pan FROM cases WHERE id=?", (case_id,)).fetchone()
    if not r:
        return []
    terms = json.loads(r["party_names"] or "[]")
    if r["pan"]:
        terms.append(r["pan"])
    return terms


def history(user: dict, case_id: int) -> list[dict]:
    check_access(user, case_id)
    return audit.case_history(case_id)


# ---------------------------------------------------------------- permanent deletion
def deletion_preview(user: dict, case_id: int) -> dict:
    """What a permanent deletion would remove (counts only), for the confirmation message."""
    require_role(user, "CA", "ADMIN")
    case = get_case(user, case_id)
    with ro() as conn:
        def n(sql: str) -> int:
            return conn.execute(sql, (case_id,)).fetchone()[0]
        out = {"case_id": case_id, "case_ref": case["case_ref"], "assessee_name": case["assessee_name"], "status": case["status"],
               "documents": n("SELECT COUNT(*) FROM documents WHERE case_id=?"),
               "issues": n("SELECT COUNT(*) FROM issues WHERE case_id=?"),
               "drafts": n("SELECT COUNT(*) FROM drafts WHERE case_id=?"),
               "approvals": n("SELECT COUNT(*) FROM approvals WHERE draft_id IN (SELECT id FROM drafts WHERE case_id=?)"),
               "history_entries": n("SELECT COUNT(*) FROM audit_log WHERE case_id=?")}
    return out


def _case_tables(conn) -> list[str]:
    out = []
    for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
        if name in ("cases", "audit_log", "verification_log") or name.startswith("sqlite_"):
            continue
        if any(c[1] == "case_id" for c in conn.execute(f"PRAGMA table_info({name})").fetchall()):
            out.append(name)
    return out


def delete_case(user: dict, case_id: int, confirm_case_ref: str) -> dict:
    """Permanently delete one case and its whole workflow: notice and supporting files, extracted text,
    issues, evidence, document mappings, reconciliations, research, drafts and versions, approvals,
    AI-request records and the case's own history. Nothing is sent anywhere.

    `confirm_case_ref` must equal this case's reference, so a confirmation opened for one case can
    never delete another. CLOSED is a status, not deletion — use set_status for that."""
    import shutil

    from ..core.config import get_settings
    from ..core.security import safe_join

    require_role(user, "CA", "ADMIN")
    case = get_case(user, case_id)
    if (confirm_case_ref or "").strip() != case["case_ref"]:
        raise ValidationError("The confirmation does not match this case. Nothing was deleted — open the case list and try again.")
    s = get_settings()
    with ro() as conn:
        exports = []
        for r in conn.execute("SELECT meta_json FROM audit_log WHERE case_id=? AND event='FINAL_EXPORTED'", (case_id,)):
            f = (json.loads(r["meta_json"] or "{}") or {}).get("file")
            if f:
                exports.append(f)
    preview = deletion_preview(user, case_id)
    with tx() as conn:
        if not conn.execute("SELECT 1 FROM cases WHERE id=? AND case_ref=?", (case_id, case["case_ref"])).fetchone():
            raise NotFound("Case not found — it may already have been deleted.")
        leftovers = {}
        conn.execute("DELETE FROM cases WHERE id=?", (case_id,))  # ON DELETE CASCADE removes the dependent rows
        for t in _case_tables(conn):  # defensive: anything not covered by a cascade
            cur = conn.execute(f"DELETE FROM {t} WHERE case_id=?", (case_id,))
            if cur.rowcount:
                leftovers[t] = cur.rowcount
        purge = audit.purge_case_history(conn, case_id)
        audit.log_event(conn, "CASE_DELETED", user_id=user["id"], case_id=None,
                        meta={"deleted_case_id": case_id, "documents": preview["documents"], "issues": preview["issues"],
                              "drafts": preview["drafts"], "approvals": preview["approvals"], **purge,
                              "rows_removed_without_cascade": sum(leftovers.values())})
    # Files go only after the database change has committed.
    not_removed = []
    folder = s.docs_dir / f"case_{int(case_id)}"
    if folder.exists() and folder.resolve().parent == s.docs_dir.resolve():
        shutil.rmtree(folder, ignore_errors=True)
        if folder.exists():
            not_removed.append(str(folder))
    for f in exports:
        try:
            p = safe_join(s.exports_dir, f)
            if p.exists():
                p.unlink()
        except Exception:
            not_removed.append(f)
    return {"deleted": True, "case_id": case_id, "case_ref": case["case_ref"], "removed": preview,
            "files_not_removed": not_removed}
