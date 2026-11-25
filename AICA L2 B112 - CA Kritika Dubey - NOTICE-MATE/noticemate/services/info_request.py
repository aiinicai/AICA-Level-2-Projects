"""Module 9 — evidence-gap analysis and client information request generator.

Requests are issue-wise, plain-language, and exclude requirements already
assessed SUFFICIENT. Documents already on file are listed so the client is not
asked for them again."""
from __future__ import annotations

from ..core import audit
from ..core.db import dumps, ro, row_to_dict, tx, utcnow
from . import cases, evidence, issues

_WHY = {
    "NOT_PROVIDED": "not yet received",
    "INSUFFICIENT": "received, but does not adequately support the explanation",
    "PARTIALLY_SUFFICIENT": "received, but incomplete",
    "CONTRADICTORY": "received, but conflicts with other records — please clarify",
    "REQUIRES_VERIFICATION": "on file, but needs to be checked — please confirm it is the complete and final version",
}


def generate(user: dict, case_id: int, *, include_requires_verification: bool = False, save: bool = True,
             require_assessment: bool = False) -> dict:
    case = cases.get_case(user, case_id)
    mat = evidence.matrix(user, case_id)
    iss = {i["id"]: i for i in issues.list_issues(user, case_id)}
    sections = []
    for iid, i in iss.items():
        position = i["analysis_json"].get("concern_position")
        held_by_ca = set(i["analysis_json"].get("available_records") or [])
        if require_assessment and not position:
            from ..core.errors import ValidationError
            raise ValidationError(f"Record a CA factual assessment for Q{i['seq']} before generating its document request.")
        rows = [m for m in mat if m["issue_id"] == iid]
        req, have = [], []
        for m in rows:
            if m["requirement"] in held_by_ca:
                have.append(f"{m['requirement_label']} — confirmed available with CA")
                continue
            if m["document_name"] and m["status"] != "CONTRADICTORY":
                have.append(f"{m['requirement_label']} — {m['document_name']}")
            if m["status"] == "SUFFICIENT":
                continue
            if m["status"] == "REQUIRES_VERIFICATION" and not include_requires_verification:
                continue
            q = m["client_question"] or f"Please provide: {m['requirement_label']}."
            extra = f" Note: {m['inconsistency']}" if m.get("inconsistency") else ""
            req.append({"evidence_id": m["id"], "request": q + extra, "status": m["status"], "why": _WHY.get(m["status"], "")})
        if req:
            request_basis = {
                "TRUE": "To quantify and support the concern accepted on the records reviewed, please provide:",
                "PARTLY_TRUE": "To identify the accepted portion and support the explanation for the balance, please provide:",
                "FALSE": "To support the position that the concern is factually incorrect, please provide:",
                "NEED_CLIENT_INFO": "To assess and respond to this concern, please provide:",
            }.get(position, "To respond to this concern, please provide:")
            sections.append({"issue_seq": i["seq"], "issue_summary": i["query_text"][:200], "category": i["category"],
                             "concern_position": position, "request_basis": request_basis,
                             "requests": req, "already_on_file": have})
    content = {
        "case_ref": case["case_ref"], "assessee": case["assessee_name"],
        "intro": ("To enable us to respond to the Income-tax notice, please provide the following. Where a document does not "
                  "exist, please tell us so in writing rather than preparing a new one. Please do not send originals; clear copies are sufficient."),
        "sections": sections,
        "closing": "Please share documents through the agreed secure channel. Do not send PAN/Aadhaar/bank details by unencrypted e-mail.",
        "generated_at": utcnow(),
    }
    if save:
        with tx() as conn:
            cur = conn.execute("INSERT INTO info_requests(case_id,content_json,created_by,created_at) VALUES (?,?,?,?)",
                               (case_id, dumps(content), user["id"], utcnow()))
            content["id"] = cur.lastrowid
            audit.log_event(conn, "CLIENT_REQUEST_GENERATED", user_id=user["id"], case_id=case_id,
                            meta={"request_id": cur.lastrowid, "n_items": sum(len(s["requests"]) for s in sections)})
    return content


def as_text(content: dict) -> str:
    lines = [f"Information request — {content['assessee']} (Ref: {content['case_ref']})", "", content["intro"], ""]
    for s in content["sections"]:
        lines.append(f"Query {s['issue_seq']}: {s['issue_summary']}")
        lines.append(s.get("request_basis", "Please provide the following:"))
        for n, r in enumerate(s["requests"], 1):
            lines.append(f"  {n}. {r['request']}  [{r['why']}]")
        if s["already_on_file"]:
            lines.append("  Already received (no need to resend): " + "; ".join(s["already_on_file"]))
        lines.append("")
    lines.append(content["closing"])
    return "\n".join(lines)


def list_requests(user: dict, case_id: int) -> list[dict]:
    cases.check_access(user, case_id)
    with ro() as conn:
        rows = conn.execute("SELECT * FROM info_requests WHERE case_id=? ORDER BY id DESC", (case_id,)).fetchall()
    return [row_to_dict(r, ("content_json",)) for r in rows]
