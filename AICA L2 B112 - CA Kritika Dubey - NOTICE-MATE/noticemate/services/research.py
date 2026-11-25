"""Phase 4 — legal research workspace.

A research note separates:
  statutory   — provisions from the registry (with Act, type, effective date, source, status)
  judicial    — judgments from the registry (only those a user has entered)
  practical   — practical suggestions (evidence to gather, procedural points) — not law
  ai_propositions — optional AI-suggested propositions; ALWAYS 'UNVERIFIED' until a CA
                    verifies each against a source, or promotes it to the registry.

Live research disclosure: unless the provider's web-search tool is enabled AND was
used, AI propositions come from model training data, which may be outdated and
must never be treated as current law. NOTICE-MATE has no built-in legal database.
"""
from __future__ import annotations

import json
import re

from ..core import audit
from ..core.config import get_settings
from ..core.db import dumps, ro, row_to_dict, tx, utcnow
from ..core.errors import NotFound, ValidationError
from . import ai_gateway, cases, issues, taxlaw
from .analysis import _extract_json
from .auth import require_role

NO_LIVE = ("LIVE LEGAL RESEARCH NOT USED: AI output (if any) is based on the model's training data, which may be outdated or wrong. "
           "It is not current law. Every proposition must be verified against the official text, notification, circular or judgment.")
LIVE = ("Provider web search was requested. Returned links are shown as received; they have NOT been checked by NOTICE-MATE. "
        "Verify each source and its date before relying on it.")
_KEYWORDS = {
    "cash": ["IT1961_S68", "IT1961_S69A", "IT1961_S269ST", "IT1961_S115BBE"],
    "loan": ["IT1961_S68", "IT1961_S269SS", "IT1961_S115BBE"],
    "capital": ["IT1961_S68", "IT1961_S269SS"],
    "penalty": ["IT1961_S270A", "IT1961_S271AAC"],
    "reassess": ["IT1961_S148"],
    "scrutiny": ["IT1961_S143_2", "IT1961_S143_3", "IT1961_S144B"],
    "expense": ["IT1961_S69C", "IT1961_S40A3"],
    "interest": ["IT1961_S234ABC"],
    "transition": ["IT2025_COMMENCEMENT", "IT2025_SAVINGS"],
    "2025": ["IT2025_COMMENCEMENT", "IT2025_SAVINGS"],
}


def _ref_view(r: dict) -> dict:
    return {"ref_key": r["ref_key"], "act": r["act"], "provision": r["provision"], "title": r["title"], "summary": r["summary"],
            "ref_type": r.get("ref_type") or "STATUTE", "effective_from": r.get("effective_from") or "REQUIRES VERIFICATION",
            "applies_to": r.get("applies_to"), "source_url": r.get("source_url") or "NOT PROVIDED", "status": r["status"]}


def create(user: dict, case_id: int, question: str, issue_id: int | None = None) -> dict:
    case = cases.get_case(user, case_id)
    if not question or len(question) > 3000:
        raise ValidationError("Question required (≤3000 chars).")
    keys: list[str] = []
    issue = None
    if issue_id:
        issue = issues.get_issue(user, issue_id)
        keys += issue["analysis_json"].get("candidate_provisions_to_examine") or []
        keys += issue["analysis_json"].get("legal_refs_selected") or []
    ql = question.lower()
    for kw, ks in _KEYWORDS.items():
        if kw in ql:
            keys += ks
    keys = list(dict.fromkeys(keys))
    refs = {r["ref_key"]: r for r in taxlaw.list_refs()}
    statutory = [_ref_view(refs[k]) for k in keys if k in refs and (refs[k].get("ref_type") or "STATUTE") != "JUDGMENT"]
    judicial = [_ref_view(r) for r in refs.values() if (r.get("ref_type") == "JUDGMENT")
                and (r["ref_key"] in keys or any(w in (r["title"] + r["summary"]).lower() for w in re.findall(r"[a-z]{5,}", ql)[:8]))]
    practical = []
    if issue:
        a = issue["analysis_json"]
        practical.append({"text": "Evidence to gather: " + "; ".join(a["information_required"]), "type": "PRACTICAL"})
        practical.append({"text": "Issue perspectives (orientation only): " + a["perspectives"]["balanced"], "type": "PRACTICAL"})
    law = None
    if case.get("assessment_year"):
        try:
            law = taxlaw.determine_applicable_law(case["assessment_year"], "AY")
        except ValidationError:
            law = None
    content = {"question": question, "applicable_law": law, "statutory": statutory, "judicial": judicial,
               "judicial_note": ("No judgments are bundled with NOTICE-MATE. Only judgments a user has entered in the registry appear here; "
                                 "they must be VERIFIED before use." if not judicial else "Judgments shown are from the registry; check status."),
               "practical": practical, "ai_propositions": [], "disclosures": [NO_LIVE]}
    now = utcnow()
    with tx() as conn:
        cur = conn.execute("INSERT INTO research_notes(case_id,issue_id,question,content_json,created_by,created_at,updated_at) "
                           "VALUES (?,?,?,?,?,?,?)", (case_id, issue_id, question, dumps(content), user["id"], now, now))
        nid = cur.lastrowid
        audit.log_event(conn, "RESEARCH_NOTE_CREATED", user_id=user["id"], case_id=case_id, meta={"note_id": nid, "n_refs": len(statutory)})
    return get(user, nid)


def get(user: dict, note_id: int) -> dict:
    with ro() as conn:
        r = conn.execute("SELECT * FROM research_notes WHERE id=?", (note_id,)).fetchone()
    if not r:
        raise NotFound("Research note not found.")
    d = row_to_dict(r, ("content_json",))
    cases.check_access(user, d["case_id"])
    return d


def list_notes(user: dict, case_id: int) -> list[dict]:
    cases.check_access(user, case_id)
    with ro() as conn:
        ids = [r["id"] for r in conn.execute("SELECT id FROM research_notes WHERE case_id=? ORDER BY id DESC", (case_id,))]
    return [get(user, i) for i in ids]


AI_RESEARCH_INSTRUCTIONS = """Answer the research question for an Indian Chartered Accountant. Return ONE JSON object only:
{"statutory":[{"proposition":"...","act":"Income-tax Act, 1961|Income-tax Act, 2025|Rules|Other","provision":"...","effective_from":"YYYY-MM-DD or UNKNOWN","source_url":"... or NONE","confidence":"LOW|MEDIUM|HIGH"}],
 "judicial":[{"proposition":"...","case_name":"...","citation":"... or UNKNOWN","court":"...","year":"...","source_url":"... or NONE","confidence":"LOW|MEDIUM|HIGH"}],
 "practical":[{"suggestion":"..."}],
 "caveats":["..."]}
Rules: Separate statute, judicial interpretation and practical suggestions. Distinguish the Income-tax Act, 1961 from the Income-tax Act, 2025 and say which applies to the stated period.
NEVER invent a case name, citation, section, circular or notification. If you are not certain a judgment exists with that exact name and citation, omit it.
Use "UNKNOWN"/"NONE" rather than guessing. State if your knowledge may be outdated."""


def prepare_ai(user: dict, note_id: int, provider: str | None = None, live: bool = False) -> dict:
    n = get(user, note_id)
    c = n["content_json"]
    material = {"question": c["question"], "applicable_law_hint": c.get("applicable_law"),
                "registry_provisions": [{k: v for k, v in s.items() if k in ("act", "provision", "title", "status")} for s in c["statutory"]]}
    sub = ai_gateway.prepare(user, n["case_id"], "LEGAL_RESEARCH", json.dumps(material, ensure_ascii=False, indent=1),
                             AI_RESEARCH_INSTRUCTIONS, provider=provider, purpose="RESEARCH", related_id=note_id, web_search=live)
    if live and not sub.get("web_search_requested"):
        sub["warning"] = ("Live web search was requested but is not enabled for this provider (set NOTICEMATE_ANTHROPIC_WEB_SEARCH or "
                          "NOTICEMATE_GEMINI_GROUNDING). The request will use model knowledge only.")
    return sub


def ingest_ai(user: dict, submission_id: int) -> dict:
    sub = ai_gateway.get_submission(user, submission_id)
    if sub.get("purpose") != "RESEARCH" or sub["status"] != "SENT":
        raise ValidationError("Not a sent research submission.")
    n = get(user, sub["related_id"])
    c = n["content_json"]
    text = sub["response_text"] or ""
    body_text = text.split("\n\n---\nSOURCES RETURNED BY PROVIDER WEB SEARCH")[0]
    data = _extract_json(body_text) or {}
    live_used = "SOURCES RETURNED BY PROVIDER WEB SEARCH" in text
    props = []
    for kind in ("statutory", "judicial", "practical"):
        for x in data.get(kind, []) if isinstance(data.get(kind), list) else []:
            if isinstance(x, dict):
                props.append({"kind": kind.upper(), **{k: str(v)[:1000] for k, v in x.items()}, "status": "UNVERIFIED",
                              "submission_id": submission_id})
    if not data:
        props.append({"kind": "RAW", "proposition": body_text[:6000], "status": "UNVERIFIED", "submission_id": submission_id,
                      "note": "Response was not valid JSON."})
    sources = re.findall(r"- (.*?) — (https?://\S+)", text)
    c["ai_propositions"] += props
    c["provider_sources"] = c.get("provider_sources", []) + [{"title": t, "url": u, "status": "UNVERIFIED"} for t, u in sources]
    c["caveats"] = data.get("caveats", []) if isinstance(data.get("caveats"), list) else []
    c["disclosures"] = [LIVE if live_used else NO_LIVE]
    with tx() as conn:
        conn.execute("UPDATE research_notes SET content_json=?, submission_id=?, live_research=?, updated_at=? WHERE id=?",
                     (dumps(c), submission_id, int(live_used), utcnow(), n["id"]))
        audit.log_event(conn, "RESEARCH_AI_INGESTED", user_id=user["id"], case_id=n["case_id"],
                        meta={"note_id": n["id"], "n_props": len(props), "live": live_used})
    return get(user, n["id"])


def set_proposition_status(user: dict, note_id: int, index: int, status: str, source_url: str | None = None, note: str = "") -> dict:
    require_role(user, "CA")
    if status not in ("VERIFIED", "DISCARDED", "UNVERIFIED"):
        raise ValidationError("status must be VERIFIED, DISCARDED or UNVERIFIED.")
    n = get(user, note_id)
    c = n["content_json"]
    if not 0 <= index < len(c["ai_propositions"]):
        raise ValidationError("Invalid proposition index.")
    if status == "VERIFIED" and not (source_url and re.match(r"^https?://", source_url)):
        raise ValidationError("Verification requires the source URL you checked.")
    p = c["ai_propositions"][index]
    p.update({"status": status, "verified_source": source_url, "ca_note": note[:500], "reviewed_by": user["username"]})
    statuses = {x["status"] for x in c["ai_propositions"] if x["status"] != "DISCARDED"}
    overall = "VERIFIED" if statuses == {"VERIFIED"} else "PARTLY_VERIFIED" if "VERIFIED" in statuses else "UNVERIFIED"
    with tx() as conn:
        conn.execute("UPDATE research_notes SET content_json=?, status=?, updated_at=? WHERE id=?", (dumps(c), overall, utcnow(), note_id))
        audit.log_event(conn, "RESEARCH_PROPOSITION_REVIEWED", user_id=user["id"], case_id=n["case_id"],
                        meta={"note_id": note_id, "index": index, "status": status})
    return get(user, note_id)


def promote_to_registry(user: dict, note_id: int, index: int, ref_key: str) -> dict:
    """Copy an AI proposition into the legal registry as REQUIRES_VERIFICATION (it still needs CA verification)."""
    n = get(user, note_id)
    p = n["content_json"]["ai_propositions"][index] if 0 <= index < len(n["content_json"]["ai_propositions"]) else None
    if not p:
        raise ValidationError("Invalid proposition index.")
    judgment = p["kind"] == "JUDICIAL"
    url = p.get("source_url")
    url = url if url and url.startswith("http") else None
    ef = p.get("effective_from")
    ef = ef if ef and re.match(r"^\d{4}-\d{2}-\d{2}$", ef) else None
    return taxlaw.add_ref(user, ref_key=ref_key, act=(p.get("court") if judgment else p.get("act")) or "UNKNOWN",
                          provision=(p.get("citation") if judgment else p.get("provision")) or "UNKNOWN",
                          title=(p.get("case_name") if judgment else (p.get("provision") or "AI proposition")) or "UNKNOWN",
                          summary=("AI-suggested (unverified): " + (p.get("proposition") or p.get("suggestion") or ""))[:2000],
                          source_url=url, ref_type="JUDGMENT" if judgment else "STATUTE", effective_from=None if judgment else ef)


def live_status() -> dict:
    s = get_settings()
    return {"anthropic_web_search": s.anthropic_web_search, "gemini_grounding": s.gemini_grounding,
            "disclosure": NO_LIVE if not (s.anthropic_web_search or s.gemini_grounding) else LIVE}
