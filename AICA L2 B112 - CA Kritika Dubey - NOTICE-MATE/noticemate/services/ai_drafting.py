"""V3.2 — AI writes the issue-wise reply, inside the normal "Write the reply" flow.

For each notice query the model receives only what is relevant (retrieval): the exact query wording, the
best-matching passages from the uploaded records (each with its document and location, numbered E1, E2 …),
the CA's record-availability marks, the CA's position and explanation, contradictions found between records,
any CA-verified legal points, and the list of documents selected for enclosure.

Its answer is checked on this computer before it is used:
* every amount, date and identifier must appear in the notice or the supplied material; anything else is
  kept but marked [CA TO CONFIRM: …] at that sentence;
* no mention of software/AI; no "enclosed" unless a document was selected for enclosure; no section, case
  or circular that was not supplied (marked for the CA);
* each paragraph keeps the evidence numbers it relied on, so every statement can be traced to its source.

Engines
* local  — a model on this computer (LM Studio / Ollama). Nothing leaves the computer; no approval step.
* cloud  — Anthropic / Gemini through the existing AI gateway: redacted locally, exact payload shown,
           explicit approval, then the answer becomes a new draft version automatically.
If no engine is ready, the reply is still written from the records, and is labelled as such.
"""
from __future__ import annotations

import json
import re

from ..core import audit
from ..core.db import dumps, ro, row_to_dict, tx, utcnow
from ..core.errors import NotFound, ValidationError
from ..core.security import sha256_text
from . import authorities, cases, issues as issues_svc, mapping, reply_writer
from .ai_providers import CLOUD_PROVIDERS, get_provider, local_readiness, provider_error

SYSTEM = """You draft replies to Indian income-tax notices for a Chartered Accountant, written in the assessee's own voice.
Rules — follow every one:
1. Write as the assessee addressing the income-tax authority: "we", "our", "us". Never refer to "the assessee" in the third person.
2. Never mention software, AI, a model, prompts, or that the text was drafted by anyone.
3. Use ONLY facts in the MATERIAL: the notice query, the evidence extracts (E1, E2 …), the CA's position and explanation,
   the record-availability list and the verified legal points. Never invent amounts, dates, names, PANs, UTRs, invoice numbers,
   sources of funds, lender capacity, confirmations, payment modes, ledger entries, annexure numbers or legal conclusions.
4. Answer every material request in the query, in the notice's order, in connected professional paragraphs. Do not answer with a
   bare one-liner. For a record the CA marks "available with us (not uploaded)", say it is available and can be produced for
   verification — do not describe its contents. For "not available", say so and add [CA TO CONFIRM: reason]. For anything
   material that is missing or unclear, write a short specific placeholder: [CA TO CONFIRM: …].
5. Say a document is "enclosed" or give it an annexure number ONLY if it appears in ENCLOSURES. Otherwise say "available for
   production" or simply refer to it as part of our records.
6. Cite a section, rule, circular or judgment ONLY if it appears in VERIFIED LEGAL POINTS. Do not add legal conclusions.
7. Keep every [CA REVIEW: …] and [CA TO CONFIRM: …] marker from FACT SUMMARY exactly where it applies.
8. Respectful, composed tone. No stock phrases such as "fully proved" or "beyond doubt". No headings, no greeting, no sign-off.
Return ONLY JSON: {"paragraphs":[{"text":"…","sources":["E1","E3"]}]} — "sources" lists the evidence numbers each paragraph relies on."""

_FORBIDDEN = re.compile(r"(?i)\b(artificial intelligence|language model|chatgpt|notice-?mate|software|as an ai|the ai\b|this tool|"
                        r"prompt|generated)\b")
_ENCLOSE = re.compile(r"(?i)\b(enclosed|annexed|attached herewith|attached hereto|annexure\s+[A-Z0-9\-]+)\b")
_SECTION = re.compile(r"(?i)\bsections?\s+(\d+[A-Z]{0,3}(?:\(\w+\))*)")
_CASE = re.compile(r"(?:\b[A-Z][A-Za-z.&]+(?:\s+[A-Z][A-Za-z.&]+){0,5}\s+v(?:s)?\.?\s+[A-Z][A-Za-z.&]+)|(?:\(\d{4}\)\s*\d+\s*(?:ITR|Taxman|SCC|ITD|TTJ|CTR|DTR))")
_IDENT = re.compile(r"\b(?=[A-Z0-9/\-]*\d)(?=[A-Z0-9/\-]*[A-Z])[A-Z0-9][A-Z0-9/\-]{5,}\b")
EVIDENCE_CHARS = 7000
PASSAGE_CHARS = 700


# ------------------------------------------------------------------ engine status
def engine_status() -> dict:
    """What can write the reply right now — shown before the user reaches drafting."""
    from ..core.config import get_settings

    s = get_settings()
    local = local_readiness()
    cloud = {p: {"key_configured": bool(s.anthropic_api_key if p == "anthropic" else s.gemini_api_key),
                 "model": s.anthropic_model if p == "anthropic" else s.gemini_model} for p in CLOUD_PROVIDERS}
    cloud_ready = [p for p, v in cloud.items() if s.ai_enabled and v["key_configured"]]
    if local["enabled"] and local["ready"]:
        best, msg = "local", f"AI drafting is ready on this computer (model: {local['model']}). Nothing leaves this computer."
    elif cloud_ready:
        best, msg = cloud_ready[0], (f"Cloud AI ({cloud_ready[0]}) is configured. Each request is redacted, shown to you and sent only "
                                     "after your approval; the provider may charge for usage.")
    else:
        best = None
        msg = ("AI drafting is not set up. The reply will be written from your records without AI (a basic template where no "
               "record relates to a query). To use AI on this computer: Settings → AI drafting.")
        if local["enabled"] and not local["ready"]:
            msg = "Local AI is switched on but not ready: " + local["message"]
    return {"best": best, "message": msg, "local": local, "cloud": cloud, "cloud_ai_enabled": s.ai_enabled,
            "cloud_ready": cloud_ready}


# ------------------------------------------------------------------ material for one query
def _fy(case: dict):
    return mapping._fy_start(case.get("assessment_year"))


def issue_material(user: dict, case_id: int, issue: dict, *, docs: dict | None = None, contra: list | None = None) -> dict:
    """Everything the model may use for one query, and nothing else (retrieval by relevance and size)."""
    case = cases.get_case(user, case_id)
    fy = _fy(case)
    links = mapping.links_for_issue(user, issue["id"])
    if contra is None:
        contra = mapping.contradictions(user, case_id)
    my_contra = [c for c in contra if c.get("issue_id") == issue["id"]]
    recs = mapping.record_status(issue, links, my_contra)
    if docs is None:
        with ro() as conn:
            docs = {r["id"]: row_to_dict(r) for r in conn.execute(
                "SELECT d.id, d.original_name, d.annexure_label, d.is_annexure, d.doc_type, t.text FROM documents d "
                "LEFT JOIN doc_text t ON t.document_id=d.id WHERE d.case_id=?", (case_id,))}
    from .drafting import _doc_title

    good = [l for l in links if l["status"] != "REJECTED" and (l["certainty"] == "STRONG" or l["status"] == "ACCEPTED")]
    good.sort(key=lambda l: (l["status"] != "ACCEPTED", -l["score"]))
    evidence, used = [], 0
    for l in good:
        txt = re.sub(r"(?i)\bfictional\s+", "", l["passage"])[:PASSAGE_CHARS]
        if used + len(txt) > EVIDENCE_CHARS:
            continue
        used += len(txt)
        d = docs.get(l["document_id"]) or {}
        evidence.append({"ref": f"E{len(evidence) + 1}", "link_id": l["id"], "document_id": l["document_id"],
                         "document": _doc_title(d) if d else l["document_name"], "file": l["document_name"],
                         "location": l.get("location") or "", "text": txt})
    facts = reply_writer.write_issue(issue, links, docs, fy, {}, contra, recs)
    a = issue.get("analysis_json") or {}
    verified_legal = []
    for pid in [r["id"] for r in _props(issue["id"])]:
        pv = authorities.proposition_view(user, pid)
        if pv["effective_status"] == "VERIFIED":
            cites = [(s.get("citation") or s["title"]) for s in pv["sources"]
                     if s["stance"] == "SUPPORTS" and s["source_class"] == "PRIMARY" and s["effective_status"] == "VERIFIED"]
            verified_legal.append(pv["text"].rstrip(".") + (f" ({'; '.join(cites)})" if cites else ""))
    enclosures = [f"Annexure {d['annexure_label']}: {_doc_title(d)}" for d in docs.values() if d.get("is_annexure") and d.get("annexure_label")]
    return {
        "issue_id": issue["id"], "query_no": issue["seq"], "title": issue.get("title") or "",
        "query": issue["query_text"],
        "evidence": evidence,
        "fact_summary": facts["paragraphs"] if facts["drafted_by"] == "RECORDS" else [],
        "records": [{"item": r["short"], "asked_in_notice": r["asked"], "state": r["state_label"]} for r in recs],
        "contradictions": [c["text"] for c in my_contra],
        "ca_position": a.get("concern_position") or "",
        "ca_basis": a.get("concern_position_basis") or "",
        "ca_explanation": (a.get("client_explanation") or "") if a.get("client_explanation_confirmed") else "",
        "unconfirmed_client_explanation": "" if a.get("client_explanation_confirmed") else (a.get("client_explanation") or ""),
        "verified_legal_points": verified_legal,
        "enclosures": enclosures,
        "_fy": fy,
    }


def _props(issue_id: int) -> list:
    with ro() as conn:
        return [row_to_dict(r) for r in conn.execute("SELECT id FROM propositions WHERE issue_id=? ORDER BY id", (issue_id,))]


def material_text(m: dict) -> str:
    """The material as the model sees it (also the reference text for the fact check)."""
    out = [f"QUERY NO. {m['query_no']}{' — ' + m['title'] if m['title'] else ''}", f"NOTICE QUERY (exact wording):\n{m['query']}", ""]
    out.append("EVIDENCE EXTRACTS FROM OUR UPLOADED RECORDS:")
    out += [f"{e['ref']} [{e['document']}{', ' + e['location'] if e['location'] else ''}]: {e['text']}" for e in m["evidence"]] or ["(none)"]
    if m["fact_summary"]:
        out += ["", "FACT SUMMARY (prepared from the same extracts; keep any [CA REVIEW …] markers):"] + m["fact_summary"]
    out += ["", "RECORDS THE NOTICE ASKS FOR / WE HOLD:"]
    out += [f"- {r['item']}: {r['state']}{' (asked in the notice)' if r['asked_in_notice'] else ''}" for r in m["records"]] or ["(none)"]
    if m["contradictions"]:
        out += ["", "CONTRADICTIONS BETWEEN OUR RECORDS (do not resolve; keep a [CA REVIEW: …] marker):"] + [f"- {c}" for c in m["contradictions"]]
    out += ["", f"CA'S FACTUAL POSITION: {m['ca_position'] or 'not recorded'}"]
    if m["ca_basis"]:
        out.append(f"CA'S BASIS: {m['ca_basis']}")
    if m["ca_explanation"]:
        out.append(f"CA-CONFIRMED EXPLANATION: {m['ca_explanation']}")
    if m["unconfirmed_client_explanation"]:
        out.append(f"CLIENT EXPLANATION NOT YET CONFIRMED (use only inside [CA TO CONFIRM: …]): {m['unconfirmed_client_explanation']}")
    out += ["", "VERIFIED LEGAL POINTS:"] + ([f"- {x}" for x in m["verified_legal_points"]] or ["(none — do not cite any law)"])
    out += ["", "ENCLOSURES:"] + ([f"- {x}" for x in m["enclosures"]] or ["(none — do not say anything is enclosed)"])
    return "\n".join(out)


# ------------------------------------------------------------------ answer parsing and checking
def parse_answer(text: str) -> list[dict]:
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    m = re.search(r"\{.*\}", t, re.S)
    if not m:
        raise ValidationError("The AI answer was not in the expected format.")
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        raise ValidationError("The AI answer was not valid JSON.")
    paras = data.get("paragraphs") if isinstance(data, dict) else None
    out = []
    for p in paras or []:
        if isinstance(p, str):
            out.append({"text": p.strip(), "sources": []})
        elif isinstance(p, dict) and isinstance(p.get("text"), str):
            out.append({"text": p["text"].strip(), "sources": [str(x) for x in p.get("sources") or []]})
    out = [p for p in out if p["text"]]
    if not out:
        raise ValidationError("The AI answer contained no paragraphs.")
    return out


def _sentences(text: str) -> list[str]:
    return re.split(r"(?<=[.;])\s+(?=[A-Z(\[])", text)


def check_paragraphs(paras: list[dict], m: dict) -> tuple[list[str], list[list[str]], list[dict]]:
    """Fact-check the model's paragraphs against the material. Returns (paragraphs, sources, checks)."""
    ref_text = material_text(m)
    ref_up = ref_text.upper()
    fy = m.get("_fy")
    amts, dts = mapping.amounts_in(ref_text), mapping.dates_in(ref_text, fy)
    known_refs = {e["ref"] for e in m["evidence"]}
    checks, out_p, out_s = [], [], []
    for p in paras:
        sents = []
        for sent in _sentences(p["text"]):
            if _FORBIDDEN.search(sent):
                checks.append({"kind": "REMOVED", "message": f"Removed a sentence that referred to software or drafting: “{sent[:120]}”"})
                continue
            marks = []
            plain = re.sub(r"\[(?:CA TO CONFIRM|CA REVIEW)[^\]]*\]", " ", sent)
            bad_a = [mapping.inr(a) for a in mapping.amounts_in(plain) - amts]
            bad_d = [mapping.fmt_date(d) for d in mapping.dates_in(plain, fy) - dts]
            bad_i = [t for t in _IDENT.findall(plain.upper()) if t not in ref_up and not re.fullmatch(r"\d{4}-\d{2}", t)]
            if bad_a or bad_d or bad_i:
                what = ", ".join(bad_a + bad_d + bad_i)
                marks.append(f"[CA TO CONFIRM: {what} — not found in the notice or the records]")
                checks.append({"kind": "UNSUPPORTED_FACT", "message": f"Query {m['query_no']}: {what} is not in the notice or the records."})
            if _ENCLOSE.search(plain) and not m["enclosures"]:
                marks.append("[CA TO CONFIRM: no document has been selected for enclosure]")
                checks.append({"kind": "ENCLOSURE", "message": f"Query {m['query_no']}: the text says a document is enclosed, but none is selected."})
            for sec in _SECTION.findall(plain):
                if not re.search(rf"(?i)section\s+{re.escape(sec)}\b", ref_text) and not re.search(rf"\b{re.escape(sec)}\b", m["query"]):
                    marks.append(f"[CA TO CONFIRM: section {sec} — legal reference not verified]")
                    checks.append({"kind": "LEGAL", "message": f"Query {m['query_no']}: section {sec} was not among the verified legal points."})
            for cs in _CASE.findall(plain):
                if cs.upper() not in ref_up:
                    marks.append("[CA TO CONFIRM: judgment not verified]")
                    checks.append({"kind": "LEGAL", "message": f"Query {m['query_no']}: an unverified judgment was cited ({cs[:60]})."})
            if re.search(r"(?i)\bthe assessee\b", plain):
                checks.append({"kind": "VOICE", "message": f"Query {m['query_no']}: rephrase “the assessee” in the first person."})
            sents.append(sent if not marks else sent.rstrip() + " " + " ".join(dict.fromkeys(marks)))
        if sents:
            out_p.append(" ".join(sents))
            out_s.append([r for r in p["sources"] if r in known_refs])
    words = len(" ".join(out_p).split())
    if words < 40:
        raise ValidationError(f"The AI answer for query {m['query_no']} was too short to use ({words} words).")
    return out_p, out_s, checks


def _store(user: dict, case_id: int, issue_id: int, provider: str, model: str, paras: list[str], sources: list[list[str]],
           checks: list[dict], m: dict, submission_id: int | None = None) -> dict:
    ev = {e["ref"]: {k: e[k] for k in ("document", "file", "location", "text", "document_id", "link_id")} for e in m["evidence"]}
    src = [[{"ref": r, **ev[r]} for r in refs if r in ev] for refs in sources]
    ch = sha256_text(material_text(m))
    with tx() as conn:
        cur = conn.execute("INSERT INTO ai_issue_drafts(case_id,issue_id,provider,model,paragraphs_json,sources_json,checks_json,"
                           "context_hash,submission_id,created_by,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                           (case_id, issue_id, provider, model, dumps(paras), dumps(src), dumps(checks), ch, submission_id,
                            user["id"], utcnow()))
        rid = cur.lastrowid
        audit.log_event(conn, "AI_ISSUE_DRAFTED", user_id=user["id"], case_id=case_id,
                        meta={"ai_draft_id": rid, "issue_id": issue_id, "provider": provider, "model": model,
                              "material_hash": ch, "paragraphs": len(paras), "checks": len(checks)})
    return get_row(user, rid)


def get_row(user: dict, rid: int) -> dict:
    with ro() as conn:
        r = conn.execute("SELECT * FROM ai_issue_drafts WHERE id=?", (rid,)).fetchone()
    if not r:
        raise NotFound("AI draft not found.")
    d = row_to_dict(r)
    cases.check_access(user, d["case_id"])
    return {"id": d["id"], "case_id": d["case_id"], "issue_id": d["issue_id"], "provider": d["provider"], "model": d["model"],
            "paragraphs": json.loads(d["paragraphs_json"]), "sources": json.loads(d["sources_json"]),
            "checks": json.loads(d["checks_json"]), "created_at": d["created_at"]}


# ------------------------------------------------------------------ local engine
def draft_issue_local(user: dict, issue_id: int) -> dict:
    """Write one query's reply with the model on this computer (nothing leaves the computer)."""
    i = issues_svc.get_issue(user, issue_id) if hasattr(issues_svc, "get_issue") else _issue(user, issue_id)
    r = local_readiness()
    if not r["enabled"]:
        raise ValidationError("Local AI drafting is switched off. Turn it on in Settings → AI drafting.")
    if not r["ready"]:
        raise provider_error("NOT_CONFIGURED", r["message"])
    m = issue_material(user, i["case_id"], i)
    prov = get_provider("local")
    res = prov.send(prov.build_body(SYSTEM, material_text(m)))
    paras = parse_answer(res.text)
    p, s, checks = check_paragraphs(paras, m)
    return _store(user, i["case_id"], i["id"], "local", res.model, p, s, checks, m)


def _issue(user: dict, issue_id: int) -> dict:
    with ro() as conn:
        r = conn.execute("SELECT * FROM issues WHERE id=?", (issue_id,)).fetchone()
    if not r:
        raise NotFound("Issue not found.")
    cases.check_access(user, r["case_id"])
    return row_to_dict(r, ("analysis_json",))


def rows_for_build(user: dict, case_id: int, ai_draft_ids: list[int]) -> dict[int, dict]:
    out = {}
    for rid in ai_draft_ids or []:
        row = get_row(user, rid)
        if row["case_id"] != case_id:
            raise ValidationError("An AI draft does not belong to this case.")
        out[row["issue_id"]] = row
    return out


# ------------------------------------------------------------------ cloud engine (through the approval gateway)
CLOUD_TASK = ("Write the reply paragraphs for EACH query in the material below, following the system rules for each one. "
              "Return ONLY JSON: {\"issues\":[{\"issue_id\":<id>,\"paragraphs\":[{\"text\":\"…\",\"sources\":[\"E1\"]}]}]} — "
              "one entry per issue_id supplied. Evidence numbers are per query.")


def prepare_cloud(user: dict, case_id: int, provider: str) -> dict:
    from . import ai_gateway

    if provider not in CLOUD_PROVIDERS:
        raise ValidationError(f"Cloud provider must be one of {CLOUD_PROVIDERS}.")
    contra = mapping.contradictions(user, case_id)
    iss = issues_svc.list_issues(user, case_id)
    if not iss:
        raise ValidationError("No issues yet.")
    blocks, names = [], set()
    for i in iss:
        names |= mapping.names_in(f"{i.get('title') or ''} {i['query_text']}")
        m = issue_material(user, case_id, i, contra=contra)
        for e in m["evidence"]:
            names |= mapping.names_in(e["text"])
        blocks.append(f"=== ISSUE_ID {i['id']} ===\n" + material_text(m))
    material = "\n\n".join(blocks)
    sub = ai_gateway.prepare(user, case_id, "ISSUE_DRAFTING", material, SYSTEM_RULES_FOR_GATEWAY,
                             provider=provider, purpose="AI_DRAFTING", extra_terms=sorted(names))
    return sub


SYSTEM_RULES_FOR_GATEWAY = SYSTEM + "\n\n" + CLOUD_TASK


def ingest_cloud(user: dict, sid: int, restore: dict[str, str], response_text: str, options: dict | None = None) -> dict:
    """Turn an approved cloud answer into a new draft version: restore redacted identifiers locally, check each
    query's paragraphs against its material, store them, and build the draft."""
    from . import ai_gateway, drafting

    sub = ai_gateway.get_submission(user, sid)
    case_id = sub["case_id"]
    t = response_text or ""
    for ph, orig in sorted(restore.items(), key=lambda kv: -len(kv[0])):
        t = t.replace(ph, orig)
    m0 = re.search(r"\{.*\}", re.sub(r"^```(?:json)?\s*|\s*```$", "", t.strip()), re.S)
    try:
        data = json.loads(m0.group(0)) if m0 else {}
    except json.JSONDecodeError:
        data = {}
    items = {str(x.get("issue_id")): x for x in data.get("issues") or [] if isinstance(x, dict)}
    if not items:
        raise ValidationError("The provider's answer was not in the expected format, so the reply was not changed.")
    contra = mapping.contradictions(user, case_id)
    rows, problems = {}, []
    for i in issues_svc.list_issues(user, case_id):
        it = items.get(str(i["id"]))
        if not it:
            problems.append(f"Query {i['seq']}: no paragraphs returned — written from the records instead.")
            continue
        m = issue_material(user, case_id, i, contra=contra)
        try:
            paras = parse_answer(json.dumps({"paragraphs": it.get("paragraphs") or []}))
            p, s, checks = check_paragraphs(paras, m)
        except ValidationError as e:
            problems.append(f"Query {i['seq']}: {e.message} Written from the records instead.")
            continue
        rows[i["id"]] = _store(user, case_id, i["id"], sub["provider"], sub["model"], p, s, checks, m, submission_id=sid)
    d = drafting.build(user, case_id, ai_rows=rows, options=options,
                       drafting_info={"mode": "AI_CLOUD", "provider": sub["provider"], "model": sub["model"],
                                      "label": f"Issue paragraphs written with cloud AI ({sub['provider']}, {sub['model']}) "
                                               "and checked against your records", "problems": problems})
    return {"draft_id": d["id"], "version": d["version"], "ai_issues": len(rows), "problems": problems}
