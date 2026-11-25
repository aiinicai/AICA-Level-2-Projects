"""V3 — notice-first intake and guided workflow status.

The user starts by uploading the notice. A provisional case is created, the
file is stored and read, and the notice is parsed if its text is complete.
Anything found in the notice text (assessee name, PAN, AY) is only a
SUGGESTION until the user confirms it on the confirmation screen.
"""
from __future__ import annotations

import re
import json
from datetime import datetime

from ..core import audit
from ..core.db import dumps, ro, tx, utcnow
from ..core.errors import ValidationError
from . import cases, documents, notices
from .notice_parser import NP

PROVISIONAL_NAME = "[TO BE CONFIRMED FROM NOTICE]"
_PAN = re.compile(r"\b([A-Z]{5}\d{4}[A-Z])\b")


def _suggest(text: str, particulars: dict | None) -> dict:
    """Plain suggestions from the notice text, each with the line it came from."""
    out: dict = {}
    m = _PAN.search(text or "")
    if m:
        out["pan"] = {"value": m.group(1), "source": "PAN pattern found in notice text"}
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    # Prefer an explicit assessee label. DOCX intake also turns a two-column
    # cover table such as `To | Aarav Stationery` into a text line.
    name_patterns = (
        re.compile(r"(?i)^\s*(?:name\s+of\s+assessee|assessee(?:'s)?\s+name)\s*[:|]\s*(.+?)\s*$"),
        re.compile(r"(?i)^\s*to\s*\|\s*(?!the\s+income[- ]tax|income[- ]tax|assessing\s+officer|the\s+assessee)(.+?)\s*$"),
        re.compile(r"(?i)^\s*assessee\s*[:|]\s*(.+?)\s*$"),
        re.compile(r"(?i)^\s*to\s*[:]\s*(?:the\s+assessee\s*,\s*)?(?!the\s+income[- ]tax|income[- ]tax|assessing\s+officer)(.+?)\s*$"),
    )
    for ln in lines:
        for pattern in name_patterns:
            match = pattern.match(ln)
            if match:
                name = re.split(r"\s+\|\s+(?:PAN|assessment year|previous year|notice reference)\b", match.group(1), flags=re.I)[0].strip(" \t|:")
                if name:
                    out["assessee_name"] = {"value": name[:200], "source": f"Assessee field found in notice: {ln[:80]}"}
                    break
        if "assessee_name" in out:
            break
    if "assessee_name" not in out:
        for i, ln in enumerate(lines):
            if re.fullmatch(r"(?i)to[,]?", ln) and i + 1 < len(lines):
                out["assessee_name"] = {"value": lines[i + 1][:200], "source": f"Line after 'To,': {lines[i + 1][:80]}"}
                break
    ay = ((particulars or {}).get("assessment_year") or {}).get("value")
    if ay and ay != NP:
        out["assessment_year"] = {"value": ay, "source": "Assessment year field parsed from notice"}
    return out


def start_from_notice(user: dict, filename: str, data: bytes) -> dict:
    ref = f"NOTICE-{datetime.now():%Y%m%d-%H%M%S}"
    with ro() as conn:
        n = 1
        while conn.execute("SELECT 1 FROM cases WHERE case_ref=?", (ref if n == 1 else f"{ref}-{n}",)).fetchone():
            n += 1
    ref = ref if n == 1 else f"{ref}-{n}"
    case = cases.create_case(user, case_ref=ref, assessee_name=PROVISIONAL_NAME, assessee_category="OTHER")
    doc = documents.upload(user, case["id"], filename, data)
    documents.set_type(user, doc["id"], "NOTICE")
    result = {"case": cases.get_case(user, case["id"]), "document": documents.get_document(user, doc["id"]),
              "notice": None, "suggestions": {}, "next_step": "CONFIRM_DETAILS", "message": ""}
    st = doc["extraction_status"]
    if st == "FAILED":
        result.update(next_step="FIX_OCR",
                      message="No text could be read from this file. Run the OCR check (Settings → System check), then upload a clearer scan.")
        return result
    if st == "PARTIAL":
        result.update(next_step="ACKNOWLEDGE_PARTIAL",
                      message="Only part of this notice could be read. Confirm you will check the unreadable pages against the original.")
        return result
    return _parse_and_suggest(user, result, doc["id"], acknowledge_partial=False)


def acknowledge_and_parse(user: dict, document_id: int) -> dict:
    doc = documents.get_document(user, document_id)
    result = {"case": cases.get_case(user, doc["case_id"]), "document": doc, "notice": None, "suggestions": {},
              "next_step": "CONFIRM_DETAILS", "message": ""}
    return _parse_and_suggest(user, result, document_id, acknowledge_partial=True)


def _parse_and_suggest(user: dict, result: dict, document_id: int, *, acknowledge_partial: bool) -> dict:
    n = notices.create_from_document(user, document_id, acknowledge_partial=acknowledge_partial)
    text = documents.get_text(user, document_id)["text"]
    result["notice"] = n
    result["suggestions"] = _suggest(text, n["particulars_json"])
    result["message"] = "Check every field against the notice. Nothing is treated as confirmed until you confirm it."
    return result


def confirm_case(user: dict, case_id: int, *, assessee_name: str, assessee_category: str, pan: str | None,
                 assessment_year: str | None, case_ref: str | None = None) -> dict:
    cases.check_access(user, case_id)
    pan = (pan or "").strip().upper() or None
    if not assessee_name or assessee_name.strip() == PROVISIONAL_NAME:
        raise ValidationError("Enter the assessee name as it appears in the notice.")
    cases._validate(assessee_name.strip(), assessee_category, pan, assessment_year)
    if case_ref and not re.match(r"^[A-Za-z0-9_\-/]{1,60}$", case_ref):
        raise ValidationError("Case reference: 1-60 chars, letters/digits/-/_// only.")
    with tx() as conn:
        if case_ref and conn.execute("SELECT 1 FROM cases WHERE case_ref=? AND id<>?", (case_ref, case_id)).fetchone():
            raise ValidationError("That case reference is already used.")
        old = conn.execute("SELECT party_names FROM cases WHERE id=?", (case_id,)).fetchone()
        import json as _json

        names = sorted({n for n in _json.loads(old["party_names"] or "[]") if n != PROVISIONAL_NAME} | {assessee_name.strip()})
        # pan=None keeps the PAN already stored (so re-confirming never wipes it)
        conn.execute("UPDATE cases SET assessee_name=?, assessee_category=?, pan=COALESCE(?, pan), assessment_year=?, party_names=?, "
                     "case_ref=COALESCE(?, case_ref), updated_at=? WHERE id=?",
                     (assessee_name.strip(), assessee_category, pan, assessment_year, dumps(names), case_ref, utcnow(), case_id))
        audit.log_event(conn, "CASE_DETAILS_CONFIRMED", user_id=user["id"], case_id=case_id,
                        meta={"category": assessee_category, "ay": assessment_year, "pan_present": bool(pan)})
    return cases.get_case(user, case_id)


def workflow_status(user: dict, case_id: int) -> dict:
    """Seven guided steps, each with done/blocked state and a one-line hint."""
    cases.check_access(user, case_id)
    with ro() as conn:
        c = conn.execute("SELECT assessee_name FROM cases WHERE id=?", (case_id,)).fetchone()
        n = conn.execute("SELECT id, deadline_verified FROM notices WHERE case_id=? ORDER BY id DESC LIMIT 1", (case_id,)).fetchone()
        docs = conn.execute("SELECT COUNT(*) AS k, SUM(extraction_status IN ('FAILED','PARTIAL')) AS bad FROM documents WHERE case_id=?",
                            (case_id,)).fetchone()
        n_iss = conn.execute("SELECT COUNT(*) FROM issues WHERE case_id=?", (case_id,)).fetchone()[0]
        issue_rows = conn.execute("SELECT analysis_json FROM issues WHERE case_id=?", (case_id,)).fetchall()
        positions_done = sum(bool(json.loads(r["analysis_json"] or "{}").get("concern_position")) for r in issue_rows)
        ev = conn.execute("SELECT COUNT(*) AS k, SUM(source='USER') AS done FROM evidence_items WHERE case_id=?", (case_id,)).fetchone()
        recon = conn.execute("SELECT COUNT(*) FROM recon_runs WHERE case_id=?", (case_id,)).fetchone()[0]
        props = conn.execute("SELECT COUNT(*) AS k, SUM(status IN ('VERIFIED','REJECTED')) AS done FROM propositions WHERE case_id=?",
                             (case_id,)).fetchone()
        drafts = conn.execute("SELECT COUNT(*) FROM drafts WHERE case_id=?", (case_id,)).fetchone()[0]
    from . import review

    appr = review.approval_status(user, case_id) if drafts else {"approved": False}
    details_ok = bool(c and c["assessee_name"] != PROVISIONAL_NAME and n and n["deadline_verified"])
    steps = [
        {"key": "upload", "label": "Upload notice", "done": bool(n),
         "hint": "Upload the notice PDF, scan or Word file." if not n else
         ("Some documents were only partly read." if (docs["bad"] or 0) else "Notice read.")},
        {"key": "confirm", "label": "Confirm details", "done": details_ok,
         "hint": "Confirm assessee, AY and verify the compliance deadline." if not details_ok else "Details and deadline confirmed."},
        {"key": "issues", "label": "Issues & evidence", "done": bool(n_iss) and positions_done == n_iss,
         "hint": f"{positions_done} of {n_iss} issue positions confirmed by CA." if n_iss else "Generate issues from the notice."},
        {"key": "reconcile", "label": "Reconcile", "done": recon > 0, "optional": True,
         "hint": "Bank / books / AIS / 26AS checks." if not recon else f"{recon} reconciliation run(s) saved."},
        {"key": "research", "label": "Law & sources", "done": not (props["k"] or 0) or (props["done"] or 0) == (props["k"] or 0),
         "optional": not (props["k"] or 0),
         "hint": f"{props['done'] or 0} of {props['k'] or 0} propositions decided by CA." if props["k"] else "Optional: add verified legal propositions when they are relevant; a draft can proceed without them."},
        {"key": "draft", "label": "Draft reply", "done": drafts > 0, "hint": "Build and edit the reply." if not drafts else f"{drafts} version(s)."},
        {"key": "approve", "label": "CA approval", "done": bool(appr.get("approved")),
         "hint": "Approved." if appr.get("approved") else (appr.get("reason") or "Awaiting CA review.")},
    ]
    nxt = next((s["key"] for s in steps if not s["done"] and not s.get("optional")), None)
    return {"case_id": case_id, "steps": steps, "next": nxt}
