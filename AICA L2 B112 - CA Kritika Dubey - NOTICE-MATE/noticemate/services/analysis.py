"""Structured 13-section notice analysis (Phase 3).

Two sources, one format:
* LOCAL — built deterministically from application data (no network). Always available.
* AI    — produced by an approved, redacted AI submission and parsed from JSON.

Every finding carries a `basis` tag so the CA can see what kind of statement it is:
  ESTABLISHED_FACT        — supported by evidence a user assessed SUFFICIENT
  DOCUMENT_AVAILABLE      — taken from a document on file (e.g. notice text) but not independently verified
  MANAGEMENT_EXPLANATION  — client / management explanation, not yet confirmed
  ASSUMPTION              — assumption used for analysis
  UNRESOLVED              — open point; needs information or CA judgement
  SYSTEM_DERIVED          — computed by NOTICE-MATE from the above (e.g. risk score)

Analyses are versioned, editable, and must be ACCEPTED or REJECTED by a CA.
An accepted analysis is still not a professional opinion.
"""
from __future__ import annotations

import io
import json
import re

from ..core import audit
from ..core.db import dumps, ro, row_to_dict, tx, utcnow
from ..core.errors import NotFound, ValidationError
from . import ai_gateway, cases, evidence, info_request, issues, notices, review
from .auth import require_role
from .notice_parser import NP

BASIS = ("ESTABLISHED_FACT", "DOCUMENT_AVAILABLE", "MANAGEMENT_EXPLANATION", "ASSUMPTION", "UNRESOLVED", "SYSTEM_DERIVED")
SECTIONS = [
    ("summary", "1. Notice summary"),
    ("notice_type_provision", "2. Notice type and statutory provision"),
    ("period", "3. Assessment year and relevant tax period"),
    ("deadline", "4. Response deadline"),
    ("issues", "5. Issue-wise analysis"),
    ("information_requested", "6. Information and documents requested"),
    ("tax_implications", "7. Potential tax implications"),
    ("evidence_available", "8. Evidence available"),
    ("evidence_gaps", "9. Evidence gaps"),
    ("risk_assessment", "10. Risk assessment"),
    ("strategy", "11. Recommended response strategy"),
    ("client_request", "12. Client information request"),
    ("ca_checklist", "13. CA review checklist"),
]
LABEL = "DRAFT ANALYSIS — NOT A PROFESSIONAL OPINION — REQUIRES CA REVIEW"
HIGH_RISK_CATEGORIES = {"CASH_DEPOSITS", "UNSECURED_LOAN", "CAPITAL_CONTRIBUTION", "BANK_CREDITS"}


def _item(text: str, basis: str, **extra) -> dict:
    assert basis in BASIS
    return {"text": text, "basis": basis, **extra}


def _pval(p: dict, k: str) -> str:
    return (p.get(k) or {}).get("value") or NP


def risk_for_issue(issue: dict, ev: list[dict]) -> dict:
    """Transparent rule-based risk score (0-100). Reasons are listed; CA may override."""
    score, reasons = 0, []
    if issue["category"] in HIGH_RISK_CATEGORIES:
        score += 25
        reasons.append(f"Category {issue['category']} commonly leads to additions if source/nature is not explained.")
    amt = issue.get("amount") or 0
    if amt >= 1_000_000:
        score += 25
        reasons.append(f"Amount mentioned ₹{amt:,.0f} is material (≥ ₹10 lakh).")
    elif amt >= 200_000:
        score += 15
        reasons.append(f"Amount mentioned ₹{amt:,.0f} (≥ ₹2 lakh).")
    st = [e["status"] for e in ev]
    if "CONTRADICTORY" in st:
        score += 30
        reasons.append("Contradictory evidence on record.")
    n_gap = sum(s in ("NOT_PROVIDED", "INSUFFICIENT") for s in st)
    if n_gap:
        score += min(30, 8 * n_gap)
        reasons.append(f"{n_gap} evidence requirement(s) not provided or insufficient.")
    n_rv = st.count("REQUIRES_VERIFICATION") + st.count("PARTIALLY_SUFFICIENT")
    if n_rv:
        score += min(15, 3 * n_rv)
        reasons.append(f"{n_rv} requirement(s) only partly supported or awaiting verification.")
    if st and all(s == "SUFFICIENT" for s in st):
        score = max(0, score - 30)
        reasons.append("All mapped requirements assessed SUFFICIENT by a user.")
    score = min(100, score)
    level = "HIGH" if score >= 60 else "MEDIUM" if score >= 30 else "LOW"
    return {"score": score, "level": level, "reasons": reasons or ["No risk factors identified from recorded data."]}


def build_local(user: dict, case_id: int, notice_id: int | None = None, *, save: bool = True) -> dict:
    case = cases.get_case(user, case_id)
    ns = notices.list_notices(user, case_id)
    n = next((x for x in ns if x["id"] == notice_id), None) if notice_id else (ns[-1] if ns else None)
    if notice_id and not n:
        raise NotFound("Notice not found in this case.")
    p = n["particulars_json"] if n else {}
    law = (n or {}).get("applicable_law_json") or {}
    iss = issues.list_issues(user, case_id)
    mat = evidence.matrix(user, case_id)
    by_issue: dict[int, list] = {}
    for m in mat:
        by_issue.setdefault(m["issue_id"], []).append(m)

    c: dict = {"_label": LABEL, "case_ref": case["case_ref"], "assessee": case["assessee_name"], "source": "LOCAL"}
    sec = _pval(p, "section")
    c["summary"] = [
        _item(f"Notice under section {sec} ({_pval(p, 'nature')}) for AY {_pval(p, 'assessment_year')}, issued by "
              f"{_pval(p, 'issuing_authority')} on {_pval(p, 'date_of_issue')}.", "DOCUMENT_AVAILABLE"),
        _item(f"{len(iss)} issue(s) identified from the notice text.", "SYSTEM_DERIVED"),
    ] if n else [_item("No notice parsed for this case yet.", "UNRESOLVED")]
    if n and _pval(p, "scrutiny_scope") == "LIMITED":
        c["summary"].append(_item("Limited scrutiny — the response should stay within the issues identified; other matters are flagged separately for CA review.", "DOCUMENT_AVAILABLE"))
    c["notice_type_provision"] = [
        _item(f"Section: {sec}; nature: {_pval(p, 'nature')}.", "DOCUMENT_AVAILABLE"),
        _item(f"Applicable law: {law.get('substantive_law', NP)} — {law.get('basis', 'not determined')}", "SYSTEM_DERIVED"),
        *[_item(f, "UNRESOLVED") for f in law.get("flags", [])],
    ]
    c["period"] = [_item(f"Assessment Year {_pval(p, 'assessment_year')}; previous year {_pval(p, 'previous_year')}.", "DOCUMENT_AVAILABLE")]
    if law.get("relevant_period"):
        rp = law["relevant_period"]
        c["period"].append(_item(f"Relevant period {rp['from']} to {rp['to']}.", "SYSTEM_DERIVED"))
    if n and n["deadline_verified"]:
        c["deadline"] = [_item(f"Verified deadline: {n['deadline_value']}.", "ESTABLISHED_FACT")]
    else:
        c["deadline"] = [_item(f"Extracted deadline: {_pval(p, 'compliance_deadline')} — NOT VERIFIED; confirm on the e-proceedings portal.", "UNRESOLVED")]

    c["issues"], c["risk_assessment"], c["strategy"], c["tax_implications"] = [], [], [], []
    for i in iss:
        a = i["analysis_json"]
        ev = by_issue.get(i["id"], [])
        c["issues"].append({
            "seq": i["seq"], "issue_id": i["id"], "category": i["category"], "query": i["query_text"],
            "amount": i["amount"],
            "findings": [
                _item(f"Department's query: {i['query_text']}", "DOCUMENT_AVAILABLE"),
                *([_item(f"Relevant transaction: {a['relevant_transaction']}", "UNRESOLVED")]
                  if str(a.get("relevant_transaction", "")).startswith("[") else
                  [_item(f"Relevant transaction: {a['relevant_transaction']}", "DOCUMENT_AVAILABLE")]),
                *([_item(f"Client explanation: {a['client_explanation']}", "MANAGEMENT_EXPLANATION")] if a.get("client_explanation") else []),
                _item("Assessee view: " + a["perspectives"]["assessee"], "ASSUMPTION"),
                _item("Revenue view: " + a["perspectives"]["revenue"], "ASSUMPTION"),
                _item("Balanced: " + a["perspectives"]["balanced"], "ASSUMPTION"),
                *([_item(f"CA conclusion: {a['ca_conclusion']}", "ESTABLISHED_FACT")] if a.get("ca_conclusion") else []),
            ],
        })
        r = risk_for_issue(i, ev)
        c["risk_assessment"].append({"seq": i["seq"], "issue_id": i["id"], **r, "basis": "SYSTEM_DERIVED"})
        sug = issues.suggest_strategy(user, i["id"])
        c["strategy"].append({"seq": i["seq"], "issue_id": i["id"],
                              "strategy": issues.STRATEGIES.get(i["strategy"] or sug["strategy"]),
                              "reason": i["strategy_reason"] or sug["reason"],
                              "basis": "ESTABLISHED_FACT" if i["strategy"] else "SYSTEM_DERIVED",
                              "note": "Set by user" if i["strategy"] else "System suggestion — not yet decided"})
        provs = a.get("candidate_provisions_to_examine") or []
        if provs:
            c["tax_implications"].append(_item(f"Q{i['seq']}: provisions to examine (not conclusions): {', '.join(provs)}.", "ASSUMPTION"))
    with ro() as conn:
        tc = conn.execute("SELECT result_json FROM tax_computations WHERE case_id=? ORDER BY id DESC LIMIT 1", (case_id,)).fetchone()
    if tc:
        res = json.loads(tc["result_json"])
        for s in res["scenarios"]:
            c["tax_implications"].append(_item(f"Illustrative scenario {s['key']} — {s['title']}: incremental tax ₹{s['incremental_tax']:,.0f} "
                                               f"on proposed additions of ₹{res['total_proposed_additions']:,.0f}.", "SYSTEM_DERIVED"))
        c["tax_implications"].append(_item(res["label"], "ASSUMPTION"))
    else:
        c["tax_implications"].append(_item("No tax simulation run yet — exposure NOT DETERMINED.", "UNRESOLVED"))

    c["information_requested"] = [_item(f"Q{i['seq']}: {i['query_text']}", "DOCUMENT_AVAILABLE") for i in iss]
    c["evidence_available"] = [
        _item(f"Q{m['seq']} — {m['requirement_label']}: {m['document_name']} [{m['status']}]"
              + (f" — establishes: {m['establishes']}" if m.get("establishes") else ""),
              "ESTABLISHED_FACT" if m["status"] == "SUFFICIENT" else "DOCUMENT_AVAILABLE")
        for m in mat if m.get("document_name")]
    c["evidence_gaps"] = [_item(f"Q{m['seq']} — {m['requirement_label']}: {m['status']}"
                                + (f" ({m['inconsistency']})" if m.get("inconsistency") else ""), "UNRESOLVED")
                          for m in mat if m["status"] in ("NOT_PROVIDED", "INSUFFICIENT", "CONTRADICTORY", "PARTIALLY_SUFFICIENT")]
    req = info_request.generate(user, case_id, save=False)
    c["client_request"] = [{"seq": s["issue_seq"], "requests": [r["request"] for r in s["requests"]], "basis": "UNRESOLVED"}
                           for s in req["sections"]]
    latest = None
    from . import drafting
    latest = drafting.latest_draft(user, case_id)
    cl = review.checklist(user, latest["id"]) if latest else [{"label": lbl, "checked": False} for _, lbl in review.CHECKLIST]
    c["ca_checklist"] = [{"item": x["label"], "done": x["checked"], "basis": "UNRESOLVED" if not x["checked"] else "ESTABLISHED_FACT"} for x in cl]
    if save:
        return _save(user, case_id, n["id"] if n else None, "LOCAL", c, None)
    return c


def _save(user, case_id, notice_id, source, content, submission_id) -> dict:
    with tx() as conn:
        ver = conn.execute("SELECT COALESCE(MAX(version),0)+1 FROM ai_analyses WHERE case_id=?", (case_id,)).fetchone()[0]
        cur = conn.execute("INSERT INTO ai_analyses(case_id,notice_id,submission_id,source,version,content_json,created_by,created_at) "
                           "VALUES (?,?,?,?,?,?,?,?)", (case_id, notice_id, submission_id, source, ver, dumps(content), user["id"], utcnow()))
        aid = cur.lastrowid
        audit.log_event(conn, "ANALYSIS_SAVED", user_id=user["id"], case_id=case_id, meta={"analysis_id": aid, "source": source, "version": ver})
    return get(user, aid)


def get(user: dict, analysis_id: int) -> dict:
    with ro() as conn:
        r = conn.execute("SELECT * FROM ai_analyses WHERE id=?", (analysis_id,)).fetchone()
    if not r:
        raise NotFound("Analysis not found.")
    d = row_to_dict(r, ("content_json",))
    cases.check_access(user, d["case_id"])
    return d


def list_for_case(user: dict, case_id: int) -> list[dict]:
    cases.check_access(user, case_id)
    with ro() as conn:
        rows = conn.execute("SELECT id, source, version, status, created_at, reviewed_at, review_comment, submission_id "
                            "FROM ai_analyses WHERE case_id=? ORDER BY version DESC", (case_id,)).fetchall()
    return [dict(r) for r in rows]


AI_INSTRUCTIONS = """Produce a structured income-tax notice analysis as ONE JSON object and nothing else (no markdown fences).
Keys (all required): summary, notice_type_provision, period, deadline, issues, information_requested, tax_implications,
evidence_available, evidence_gaps, risk_assessment, strategy, client_request, ca_checklist.
- Every list item must be an object {"text": "...", "basis": one of ESTABLISHED_FACT | DOCUMENT_AVAILABLE | MANAGEMENT_EXPLANATION | ASSUMPTION | UNRESOLVED}.
- "issues": list of {"seq": n, "query": "...", "findings": [items]}; "risk_assessment": list of {"seq": n, "level": "LOW|MEDIUM|HIGH", "reasons": ["..."]};
  "strategy": list of {"seq": n, "strategy": "...", "reason": "..."}; "client_request": list of {"seq": n, "requests": ["..."]}.
- Use ESTABLISHED_FACT only where the material says evidence was assessed SUFFICIENT. Treat client statements as MANAGEMENT_EXPLANATION.
- Do NOT state any deadline that is not in the material. Do NOT cite case law. Mark any statutory reference you are not certain of with "(REQUIRES VERIFICATION)".
- Keep bracketed tokens such as [PARTY_NAME_1] unchanged."""


def material_for_ai(user: dict, case_id: int, notice_id: int | None) -> str:
    local = build_local(user, case_id, notice_id, save=False)
    ns = notices.list_notices(user, case_id)
    n = next((x for x in ns if x["id"] == notice_id), None) if notice_id else (ns[-1] if ns else None)
    notice_text = ""
    if n and n.get("document_id"):
        from .documents import get_text

        notice_text = get_text(user, n["document_id"])["text"][:15000]
    slim = {k: local[k] for k, _ in SECTIONS if k not in ("ca_checklist", "client_request")}
    return ("NOTICE TEXT (extracted, may contain OCR errors):\n" + notice_text +
            "\n\nCASE RECORD PREPARED BY NOTICE-MATE (with basis tags):\n" + json.dumps(slim, ensure_ascii=False, indent=1))


def prepare_ai(user: dict, case_id: int, notice_id: int | None = None, provider: str | None = None) -> dict:
    content = material_for_ai(user, case_id, notice_id)
    return ai_gateway.prepare(user, case_id, "NOTICE_ANALYSIS_STRUCTURED", content, AI_INSTRUCTIONS,
                              provider=provider, purpose="NOTICE_ANALYSIS", related_id=notice_id)


def _extract_json(text: str) -> dict | None:
    t = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start = t.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(t)):
        if t[i] == "{":
            depth += 1
        elif t[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(t[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def _normalise_items(v) -> list:
    out = []
    for x in v if isinstance(v, list) else [v]:
        if isinstance(x, dict):
            if "basis" in x and x["basis"] not in BASIS:
                x["basis"] = "UNRESOLVED"
            elif "text" in x and "basis" not in x:
                x["basis"] = "UNRESOLVED"
            out.append(x)
        elif x not in (None, ""):
            out.append({"text": str(x), "basis": "UNRESOLVED"})
    return out


def ingest_ai(user: dict, submission_id: int) -> dict:
    sub = ai_gateway.get_submission(user, submission_id)
    if sub["status"] != "SENT" or not sub.get("response_text"):
        raise ValidationError("Submission has not been sent or has no response.")
    if sub.get("purpose") != "NOTICE_ANALYSIS":
        raise ValidationError("Submission is not a notice-analysis request.")
    data = _extract_json(sub["response_text"])
    content: dict = {"_label": LABEL, "source": "AI", "provider": sub["provider"], "model": sub["model"],
                     "_ai_notice": "Generated by AI from REDACTED input. Bracketed tokens are redacted identifiers. Verify every statement."}
    if not data:
        content["parse_error"] = "AI response was not valid JSON; raw text kept for manual review."
        content["raw_text"] = sub["response_text"]
        for k, _ in SECTIONS:
            content[k] = []
    else:
        for k, _ in SECTIONS:
            content[k] = _normalise_items(data.get(k, []))
            if k not in data:
                content.setdefault("missing_sections", []).append(k)
    return _save(user, sub["case_id"], sub.get("related_id"), "AI", content, submission_id)


def edit(user: dict, analysis_id: int, content: dict) -> dict:
    a = get(user, analysis_id)
    if not isinstance(content, dict):
        raise ValidationError("content must be an object.")
    bad = set(content) - {k for k, _ in SECTIONS} - {"_label", "source", "case_ref", "assessee", "provider", "model", "_ai_notice",
                                                     "parse_error", "raw_text", "missing_sections", "edited_from"}
    if bad:
        raise ValidationError(f"Unknown sections: {sorted(bad)}")
    for k, _ in SECTIONS:
        if k in content:
            content[k] = _normalise_items(content[k]) if k not in ("risk_assessment", "strategy", "client_request", "issues", "ca_checklist") \
                else content[k]
    merged = {**a["content_json"], **content, "edited_from": a["id"], "_label": LABEL}
    return _save(user, a["case_id"], a["notice_id"], "MERGED" if a["source"] != "LOCAL" else "LOCAL", merged, a["submission_id"])


def review_decision(user: dict, analysis_id: int, decision: str, comment: str) -> dict:
    require_role(user, "CA")
    if decision not in ("ACCEPTED", "REJECTED"):
        raise ValidationError("decision must be ACCEPTED or REJECTED.")
    if decision == "REJECTED" and len((comment or "").strip()) < 5:
        raise ValidationError("A reason is required to reject.")
    a = get(user, analysis_id)
    with tx() as conn:
        conn.execute("UPDATE ai_analyses SET status=?, review_comment=?, reviewed_by=?, reviewed_at=? WHERE id=?",
                     (decision, (comment or "")[:2000], user["id"], utcnow(), analysis_id))
        audit.log_event(conn, f"ANALYSIS_{decision}", user_id=user["id"], case_id=a["case_id"], meta={"analysis_id": analysis_id})
    return get(user, analysis_id)


def render_text(content: dict) -> str:
    out = [content.get("_label", LABEL), f"Case: {content.get('case_ref', '')}  Source: {content.get('source')}", ""]
    if content.get("parse_error"):
        out += [content["parse_error"], content.get("raw_text", ""), ""]
    for k, title in SECTIONS:
        out.append(title)
        for x in content.get(k, []):
            if not isinstance(x, dict):
                out.append(f"  - {x}")
            elif "findings" in x:
                out.append(f"  Q{x.get('seq')}: {x.get('query', '')}")
                out += [f"     • [{f.get('basis')}] {f.get('text')}" for f in x["findings"]]
            elif "level" in x:
                out.append(f"  Q{x.get('seq')}: {x.get('level')} ({x.get('score', '-')}) — " + "; ".join(x.get("reasons", [])))
            elif "strategy" in x:
                out.append(f"  Q{x.get('seq')}: {x.get('strategy')} — {x.get('reason')}")
            elif "requests" in x:
                out.append(f"  Q{x.get('seq')}:")
                out += [f"     • {r}" for r in x["requests"]]
            elif "item" in x:
                out.append(f"  [{'x' if x.get('done') else ' '}] {x['item']}")
            else:
                out.append(f"  - [{x.get('basis')}] {x.get('text')}")
        out.append("")
    return "\n".join(out)


def render_docx(content: dict) -> bytes:
    import docx

    d = docx.Document()
    d.add_paragraph().add_run(content.get("_label", LABEL)).bold = True
    for line in render_text(content).splitlines()[1:]:
        if re.match(r"^\d+\. ", line):
            d.add_heading(line, level=2)
        else:
            d.add_paragraph(line)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()
