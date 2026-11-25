"""Module 11 — CA quality-review checklist, approval and final export.

* Checklist = Project Instructions §12; every item is mandatory.
* Approval: role CA only; all items checked; no unresolved placeholders;
  compliance deadline verified; bound to the draft's content hash.
* Export: only the approved version, only while the approval is valid
  (not revoked, hash unchanged). Unapproved preview carries a draft banner.
"""
from __future__ import annotations

from ..core import audit
from ..core.config import get_settings
from ..core.db import ro, row_to_dict, tx, utcnow
from ..core.errors import Conflict, PermissionDenied, ValidationError
from ..core.pii import mask_pan
from ..core.security import safe_join, sha256_bytes
from . import authorities, cases, drafting, notices
from .auth import require_role

CHECKLIST = [
    ("assessee_details", "Correct assessee and assessment details"),
    ("notice_section", "Correct notice section"),
    ("deadline", "Compliance deadline verified"),
    ("all_queries", "All notice queries addressed"),
    ("facts_consistent", "Facts consistent with supporting documents"),
    ("legal_verified", "Legal references verified"),
    ("applicable_law", "Applicable legislation confirmed (1961 / 2025 Act and transition)"),
    ("gaps_disclosed", "Contradictions and evidence gaps disclosed / addressed"),
    ("tax_calcs", "Tax calculations checked"),
    ("annexures", "Annexures properly referenced and actually enclosed"),
    ("no_admission", "No unsupported admission or concession"),
    ("no_invention", "No invented facts or citations"),
]
DECLARATION = ("I have independently reviewed this draft, the underlying records and the legal references. I take professional "
               "responsibility for its content. Software-generated material has not been relied upon without verification.")

_CITATION_RX = __import__("re").compile(
    r"(?P<rep>[\(\[]\d{4}[\)\]]\s*\d+\s*(?:taxmann\.com|ITR|SCC|ITD|TTJ|CTR|DTR|Taxman|SOT|TM)(?:\s*\d+)?)"
    r"|(?P<ita>\bITA\s*No\.?\s*\d+/[A-Za-z]+/\d{4})"
    r"|(?:\b(?:Circular|Notification|Instruction)\s*No\.?\s*(?P<num>[\w\-]+(?:/[\w\-]+)*))", __import__("re").IGNORECASE)


def citation_problems(user: dict, content: dict) -> list[str]:
    """Cited propositions must still be verified, and any citation-like text in the reply
    must belong to a CA-verified source. Returns a list of plain-language problems."""
    import re as _re

    problems = []
    for c in drafting.cited_propositions(content):
        try:
            pv = authorities.proposition_view(user, c["id"])
        except Exception:
            problems.append(f"Cited proposition #{c['id']} no longer exists. Rebuild the draft.")
            continue
        if pv["effective_status"] != "VERIFIED" or pv.get("verified_hash") != c.get("verified_hash"):
            problems.append(f"Cited proposition #{c['id']} is no longer verified or has changed. Re-verify it and rebuild the draft.")
    verified = [_re.sub(r"\s+", " ", (s.get("citation") or "") + " " + (s.get("document_number") or "")).lower()
                for s in authorities.list_sources(status="VERIFIED")]
    text = drafting.render_text(content, approved=True)
    for m in _CITATION_RX.finditer(text):
        key = _re.sub(r"\s+", " ", (m.group("rep") or m.group("ita") or m.group("num") or "")).strip().lower()
        if key and not any(key in v for v in verified):
            problems.append(f"Citation-like text not matched to a CA-verified source: '{m.group(0).strip()[:60]}'.")
    return list(dict.fromkeys(problems))


def checklist(user: dict, draft_id: int) -> list[dict]:
    d = drafting.get_draft(user, draft_id)
    items = list(CHECKLIST)
    if d["content_json"].get("_meta", {}).get("reflect_reconciliation"):
        items.insert(6, ("reconciliation_reflected", "Selected reconciliation findings reviewed and addressed"))
    with ro() as conn:
        rows = {r["item_key"]: dict(r) for r in conn.execute("SELECT * FROM review_checklists WHERE draft_id=?", (draft_id,))}
    return [{"item_key": k, "label": lbl, "checked": bool(rows.get(k, {}).get("checked")), "note": rows.get(k, {}).get("note"),
             "checked_by": rows.get(k, {}).get("checked_by"), "draft_version": d["version"]} for k, lbl in items]


def tick(user: dict, draft_id: int, item_key: str, checked: bool, note: str = "") -> list[dict]:
    require_role(user, "CA")
    d = drafting.get_draft(user, draft_id)
    allowed = dict(CHECKLIST)
    if d["content_json"].get("_meta", {}).get("reflect_reconciliation"):
        allowed["reconciliation_reflected"] = "Selected reconciliation findings reviewed and addressed"
    if item_key not in allowed:
        raise ValidationError("Unknown checklist item.")
    with tx() as conn:
        conn.execute("INSERT INTO review_checklists(draft_id,item_key,checked,note,checked_by,checked_at) VALUES (?,?,?,?,?,?) "
                     "ON CONFLICT(draft_id,item_key) DO UPDATE SET checked=excluded.checked, note=excluded.note, "
                     "checked_by=excluded.checked_by, checked_at=excluded.checked_at",
                     (draft_id, item_key, int(checked), (note or "")[:1000], user["id"], utcnow()))
        audit.log_event(conn, "CHECKLIST_ITEM", user_id=user["id"], case_id=d["case_id"],
                        meta={"draft_id": draft_id, "item": item_key, "checked": checked})
    return checklist(user, draft_id)


def tick_all(user: dict, draft_id: int, note: str = "Confirmed in the final CA review") -> list[dict]:
    """One-click final review: the CA confirms every checklist line for this exact draft version."""
    for c in checklist(user, draft_id):
        if not c["checked"]:
            tick(user, draft_id, c["item_key"], True, note)
    return checklist(user, draft_id)


def approve(user: dict, draft_id: int, *, declaration_accepted: bool) -> dict:
    require_role(user, "CA")
    d = drafting.get_draft(user, draft_id)
    latest = drafting.latest_draft(user, d["case_id"])
    if latest["id"] != draft_id:
        raise Conflict("Only the latest draft version can be approved.")
    if not declaration_accepted:
        raise ValidationError("The CA declaration must be accepted.")
    missing = [c["label"] for c in checklist(user, draft_id) if not c["checked"]]
    if missing:
        raise ValidationError("Checklist incomplete.", details={"unchecked": missing})
    if d["unresolved_placeholders"]:
        raise ValidationError("Draft contains unresolved placeholders.", details={"placeholders": d["unresolved_placeholders"][:20]})
    nid = d["content_json"].get("_meta", {}).get("notice_id")
    if nid and not notices.get_notice(user, nid)["deadline_verified"]:
        raise ValidationError("Compliance deadline has not been verified.")
    open_c = [c for c in list_comments(user, d["case_id"]) if c["status"] == "OPEN"]
    if open_c:
        raise ValidationError("Resolve all open reviewer comments before approval.", details={"open_comments": len(open_c)})
    cp = citation_problems(user, d["content_json"])
    if cp:
        raise ValidationError("Legal citations in this draft are not all verified.", details={"problems": cp})
    with tx() as conn:
        prev = conn.execute("SELECT id FROM approvals WHERE revoked=0 AND draft_id IN (SELECT id FROM drafts WHERE case_id=?)",
                            (d["case_id"],)).fetchall()
        conn.execute("UPDATE approvals SET revoked=1 WHERE draft_id IN (SELECT id FROM drafts WHERE case_id=?)", (d["case_id"],))
        if prev:
            audit.log_event(conn, "APPROVAL_SUPERSEDED", user_id=user["id"], case_id=d["case_id"],
                            meta={"superseded_approval_ids": [r["id"] for r in prev]})
        conn.execute("INSERT INTO draft_reviews(draft_id,decision,comment,content_hash,reviewer_id,created_at) VALUES (?,?,?,?,?,?)",
                     (draft_id, "APPROVED", None, d["content_hash"], user["id"], utcnow()))
        cur = conn.execute("INSERT INTO approvals(draft_id,content_hash,approved_by,approver_membership_no,declaration,approved_at,"
                           "draft_version) VALUES (?,?,?,?,?,?,?)",
                           (draft_id, d["content_hash"], user["id"], user.get("membership_no"), DECLARATION, utcnow(), d["version"]))
        audit.log_event(conn, "DRAFT_APPROVED", user_id=user["id"], case_id=d["case_id"],
                        meta={"draft_id": draft_id, "version": d["version"], "content_hash": d["content_hash"], "approval_id": cur.lastrowid})
    return approval_status(user, d["case_id"])


def revoke(user: dict, case_id: int, reason: str) -> dict:
    require_role(user, "CA")
    cases.check_access(user, case_id)
    with tx() as conn:
        conn.execute("UPDATE approvals SET revoked=1 WHERE draft_id IN (SELECT id FROM drafts WHERE case_id=?)", (case_id,))
        audit.log_event(conn, "APPROVAL_REVOKED", user_id=user["id"], case_id=case_id, meta={"reason": (reason or "")[:300]})
    return approval_status(user, case_id)


def approval_status(user: dict, case_id: int) -> dict:
    latest = drafting.latest_draft(user, case_id)
    if not latest:
        return {"approved": False, "reason": "No draft."}
    with ro() as conn:
        a = conn.execute("SELECT a.*, u.full_name, u.username FROM approvals a JOIN users u ON u.id=a.approved_by "
                         "WHERE a.draft_id=? AND a.revoked=0 ORDER BY a.id DESC LIMIT 1", (latest["id"],)).fetchone()
    if not a:
        with ro() as conn:
            dec = conn.execute("SELECT decision, comment FROM draft_reviews WHERE draft_id=? ORDER BY id DESC LIMIT 1",
                               (latest["id"],)).fetchone()
        reason = "Latest version not approved."
        if dec and dec["decision"] in ("REJECTED", "CHANGES_REQUESTED"):
            reason = f"Latest version {dec['decision'].replace('_', ' ').lower()} by CA: {dec['comment']}"
        return {"approved": False, "latest_draft_id": latest["id"], "version": latest["version"], "reason": reason,
                "state": dec["decision"] if dec else "AWAITING_REVIEW"}
    if a["content_hash"] != latest["content_hash"]:
        return {"approved": False, "latest_draft_id": latest["id"], "reason": "Draft changed after approval."}
    cp = citation_problems(user, latest["content_json"])
    if cp:
        return {"approved": False, "latest_draft_id": latest["id"], "reason": "A cited legal proposition or source is no longer verified.",
                "problems": cp}
    return {"approved": True, "latest_draft_id": latest["id"], "version": latest["version"], "approved_version": a["draft_version"],
            "approved_by": a["full_name"],
            "membership_no": a["approver_membership_no"], "approved_at": a["approved_at"], "content_hash": a["content_hash"]}


def preview(user: dict, draft_id: int) -> str:
    d = drafting.get_draft(user, draft_id)
    case = cases.get_case(user, d["case_id"], include_pan=True)
    return drafting.render_text(d["content_json"], approved=False, pan_value=mask_pan(case.get("pan")))


def working_docx(user: dict, draft_id: int) -> bytes:
    """Editable working copy; final export remains approval-gated."""
    require_role(user, "ADMIN", "CA")
    d = drafting.get_draft(user, draft_id)
    case = cases.get_case(user, d["case_id"], include_pan=True)
    pan = case.get("pan") or "[TO BE CONFIRMED: PAN]"
    # This is an editable CA working copy. Keep the content in ordinary letter
    # format; review/approval status is shown in the app and approval gate.
    return drafting.render_docx(d["content_json"], approved=False, pan_value=pan, include_draft_banner=False)


def export(user: dict, case_id: int, fmt: str = "docx") -> tuple[str, bytes]:
    if fmt not in ("docx", "pdf"):
        raise ValidationError("format must be docx or pdf.")
    st = approval_status(user, case_id)
    if not st["approved"]:
        with tx() as conn:
            audit.log_event(conn, "EXPORT_REFUSED", user_id=user["id"], case_id=case_id, meta={"reason": st["reason"]})
        raise PermissionDenied(f"Export blocked: {st['reason']} CA approval is mandatory before final export.")
    d = drafting.get_draft(user, st["latest_draft_id"])
    case = cases.get_case(user, case_id, include_pan=True)
    pan = case.get("pan") or "[TO BE CONFIRMED: PAN]"
    if fmt == "pdf":
        data = drafting.render_pdf(d["content_json"], approved=True, pan_value=pan)
    else:
        data = drafting.render_docx(d["content_json"], approved=True, pan_value=pan)
    fname = f"{case['case_ref'].replace('/', '_')}_reply_v{d['version']}.{fmt}"
    path = safe_join(get_settings().exports_dir, fname)
    path.write_bytes(data)
    with tx() as conn:
        audit.log_event(conn, "FINAL_EXPORTED", user_id=user["id"], case_id=case_id,
                        meta={"draft_id": d["id"], "version": d["version"], "file_sha256": sha256_bytes(data), "file": fname, "format": fmt})
    return fname, data


def review_memo(user: dict, case_id: int) -> str:
    """Internal (not for submission) record of the approval and open notes."""
    st = approval_status(user, case_id)
    latest = drafting.latest_draft(user, case_id)
    case = cases.get_case(user, case_id)
    if st.get("approved"):
        appr = f"APPROVED — version {st['version']} by {st['approved_by']} (M.No. {st.get('membership_no') or 'NOT PROVIDED'}) at {st['approved_at']}"
    else:
        appr = f"NOT APPROVED — {st.get('reason')}"
    lines = ["INTERNAL REVIEW MEMO — NOT FOR SUBMISSION", f"Case: {case['case_ref']} — {case['assessee_name']}", f"Approval: {appr}", ""]
    if latest:
        for b in latest["content_json"]["issues"]:
            lines.append(b["heading"][:120])
            lines += [f"  - {x}" for x in b["internal_notes"]] or ["  - no internal notes"]
        lines += ["", "Reviewer comments:"]
        lines += [f"  [{c['status']}] v{c['draft_version']} {c['section']}: {c['comment']}" + (f" → {c['resolution']}" if c.get("resolution") else "")
                  for c in list_comments(user, case_id)] or ["  none"]
        lines += ["", "Review decisions:"]
        lines += [f"  v{r['version']} {r['decision']} by {r['reviewer']} at {r['created_at']}" + (f" — {r['comment']}" if r["comment"] else "")
                  for r in history(user, case_id)["reviews"]] or ["  none"]
        lines += ["", "Checklist:"]
        lines += [f"  [{'x' if c['checked'] else ' '}] {c['label']}" + (f" — {c['note']}" if c["note"] else "")
                  for c in checklist(user, latest["id"])]
    return "\n".join(lines)


# ---------------- reviewer comments & decisions ----------------
def add_comment(user: dict, draft_id: int, section: str, comment: str) -> dict:
    d = drafting.get_draft(user, draft_id)
    if not comment or len(comment.strip()) < 3 or len(comment) > 3000:
        raise ValidationError("Comment must be 3–3000 characters.")
    if not section or len(section) > 100:
        raise ValidationError("Section is required (≤100 chars).")
    with tx() as conn:
        cur = conn.execute("INSERT INTO draft_comments(case_id,draft_id,section,comment,created_by,created_at) VALUES (?,?,?,?,?,?)",
                           (d["case_id"], draft_id, section, comment.strip(), user["id"], utcnow()))
        audit.log_event(conn, "REVIEW_COMMENT_ADDED", user_id=user["id"], case_id=d["case_id"],
                        meta={"draft_id": draft_id, "comment_id": cur.lastrowid, "section": section})
    return {"id": cur.lastrowid}


def resolve_comment(user: dict, comment_id: int, resolution: str) -> dict:
    with ro() as conn:
        r = conn.execute("SELECT * FROM draft_comments WHERE id=?", (comment_id,)).fetchone()
    if not r:
        from ..core.errors import NotFound

        raise NotFound("Comment not found.")
    cases.check_access(user, r["case_id"])
    if not resolution or len(resolution.strip()) < 3:
        raise ValidationError("Describe how the comment was resolved.")
    with tx() as conn:
        conn.execute("UPDATE draft_comments SET status='RESOLVED', resolved_by=?, resolved_at=?, resolution=? WHERE id=?",
                     (user["id"], utcnow(), resolution.strip()[:2000], comment_id))
        audit.log_event(conn, "REVIEW_COMMENT_RESOLVED", user_id=user["id"], case_id=r["case_id"], meta={"comment_id": comment_id})
    return {"ok": True}


def list_comments(user: dict, case_id: int) -> list[dict]:
    cases.check_access(user, case_id)
    with ro() as conn:
        rows = conn.execute("SELECT c.*, d.version AS draft_version, u.full_name AS author, r.full_name AS resolver "
                            "FROM draft_comments c JOIN drafts d ON d.id=c.draft_id JOIN users u ON u.id=c.created_by "
                            "LEFT JOIN users r ON r.id=c.resolved_by WHERE c.case_id=? ORDER BY c.id", (case_id,)).fetchall()
    return [dict(r) for r in rows]


def reject(user: dict, draft_id: int, comment: str, decision: str = "REJECTED") -> dict:
    require_role(user, "CA")
    if decision not in ("REJECTED", "CHANGES_REQUESTED"):
        raise ValidationError("decision must be REJECTED or CHANGES_REQUESTED.")
    if not comment or len(comment.strip()) < 5:
        raise ValidationError("A reason is required.")
    d = drafting.get_draft(user, draft_id)
    with tx() as conn:
        conn.execute("INSERT INTO draft_reviews(draft_id,decision,comment,content_hash,reviewer_id,created_at) VALUES (?,?,?,?,?,?)",
                     (draft_id, decision, comment.strip()[:3000], d["content_hash"], user["id"], utcnow()))
        conn.execute("UPDATE approvals SET revoked=1 WHERE draft_id=?", (draft_id,))
        conn.execute("UPDATE cases SET status='OPEN', updated_at=? WHERE id=?", (utcnow(), d["case_id"]))
        audit.log_event(conn, f"DRAFT_{decision}", user_id=user["id"], case_id=d["case_id"],
                        meta={"draft_id": draft_id, "version": d["version"]})
    return approval_status(user, d["case_id"])


def history(user: dict, case_id: int) -> dict:
    """Version history with review decisions and comment counts."""
    cases.check_access(user, case_id)
    with ro() as conn:
        versions = conn.execute("SELECT d.id, d.version, d.content_hash, d.created_at, u.full_name AS author FROM drafts d "
                                "JOIN users u ON u.id=d.created_by WHERE d.case_id=? ORDER BY d.version DESC", (case_id,)).fetchall()
        reviews = conn.execute("SELECT r.*, d.version, u.full_name AS reviewer FROM draft_reviews r JOIN drafts d ON d.id=r.draft_id "
                               "JOIN users u ON u.id=r.reviewer_id WHERE d.case_id=? ORDER BY r.id DESC", (case_id,)).fetchall()
        ncom = {r["draft_id"]: r["n"] for r in conn.execute(
            "SELECT draft_id, COUNT(*) n FROM draft_comments WHERE case_id=? GROUP BY draft_id", (case_id,))}
    rv = [dict(r) for r in reviews]
    out = []
    for v in versions:
        dec = next((r for r in rv if r["draft_id"] == v["id"]), None)
        out.append({**dict(v), "latest_decision": dec["decision"] if dec else None, "comments": ncom.get(v["id"], 0)})
    return {"versions": out, "reviews": rv, "approval": approval_status(user, case_id)}
