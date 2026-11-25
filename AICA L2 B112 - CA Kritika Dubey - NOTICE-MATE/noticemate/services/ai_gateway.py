"""AI gateway — the ONLY path by which any data can leave the machine.

Workflow: prepare() → user reviews exact payload → approve_and_send().
* Content is redacted locally (core.pii) with case-specific terms (assessee,
  parties, PAN). Redaction is re-verified; any residual hit → BLOCKED.
* Original documents are never attached; only the text the user selected.
* The exact JSON body to be transmitted is stored as `pending_payload` and its
  SHA-256 is shown. Sending requires that hash, explicit confirm=True and a
  user with access to the case.
* Audit log stores hash, size, PII counts, provider, model, token counts —
  never content. Pending payload is wiped after sending unless retention is
  enabled by NOTICEMATE_RETAIN_AI_PAYLOADS.
* AI output is stored as a labelled suggestion and never auto-merged.
"""
from __future__ import annotations

import json

from ..core import audit
from ..core.config import GEMINI_DISCLOSURE, SUBSCRIPTION_DISCLOSURE, get_settings
from ..core.db import dumps, ro, row_to_dict, tx, utcnow
from ..core.errors import NotFound, PermissionDenied, PrivacyBlocked, ValidationError
from ..core.pii import redact
from ..core.security import sha256_text
from . import cases
from .ai_providers import PROVIDERS, get_provider, outgoing_text

AI_LABEL = "AI SUGGESTION — GENERATED FROM REDACTED INPUT — NOT A PROFESSIONAL OPINION — VERIFY EVERY FACT, FIGURE AND LEGAL REFERENCE"

SYSTEM_PROMPT = """You are assisting an Indian Chartered Accountant with an income-tax notice. Rules:
1. Never invent facts, figures, documents, annexures, section numbers, circulars or case law. If unsure, say "REQUIRES VERIFICATION".
2. Do not assume the notice allegation or the assessee's explanation is correct. Distinguish verified facts, client explanations, assumptions and opinions.
3. Missing evidence is not proof of taxable income.
4. Give both assessee-favourable and Revenue-favourable views where relevant.
5. For AY 2026-27 and earlier, the Income-tax Act, 1961 generally applies via the savings provisions of the Income-tax Act, 2025; from Tax Year 2026-27 the 2025 Act applies. Flag any transition question for CA verification. Do not map 1961 sections to 2025 sections unless certain; otherwise mark REQUIRES VERIFICATION.
6. Bracketed tokens like [PAN_1] or [PARTY_NAME_2] are redacted identifiers; keep them as-is.
7. Your output is a draft for CA review, not a final opinion."""

TASKS = {
    "ISSUE_ANALYSIS": "Analyse the following notice query issue-wise: department's question, information required, evidence required, potential legal/factual issues (with provisions to examine, marked for verification), assessee and Revenue perspectives, and recommended next action.",
    "SUMMARISE_NOTICE": "Summarise the following notice: nature, issues raised, information requested, consequences mentioned. Do not guess dates.",
    "DRAFT_IMPROVE": "Improve the language of the following draft reply paragraph in formal Indian tax-practice style without adding any new facts, figures or legal references. Keep all bracketed placeholders.",
    "DRAFT_REPLY": "Prepare a courteous, natural, professionally reasoned reply to the notice, written in the assessee's own voice from the assessee to the assessing authority. The CA drafts and edits it on the assessee's behalf, but the reply must not refer to the assessee in the third person or mention a client relationship. Use first-person plural ('we', 'our', 'us') consistently, including in issue responses, explanations, and the prayer/conclusion. Use the supplied draft, CA factual position, and per-issue available-record confirmations. A record type marked available by the CA is confirmed to be held and to support that issue; the file itself may not be uploaded into this app. Refer to such records as records relied upon, but do not say they are attached/enclosed unless the supplied material identifies an actual annexure. Use only stated notice facts and CA-confirmed explanation; never invent details, amounts, dates, transaction paths, documents, annexures or legal references. If a material fact is not supplied, insert one concise [CA TO CONFIRM: ...] placeholder. Do not mention AI, software, prompts, or drafting tools in the reply. Do not add generic analysis or legal authorities that are not verified and supplied. Preserve the supplied issue IDs and return ONLY valid JSON in this exact shape: {\"issues\":[{\"issue_id\":123,\"paragraphs\":[\"draft paragraph\"],\"records_assessment\":\"CA-confirmed records available / records not marked available / further facts needed\",\"gaps\":[\"item\"]}]}. Include each supplied issue ID exactly once. This remains an internal suggestion for Admin CA review.",
    "EVIDENCE_REVIEW": "Review the following description of evidence against the query and state what it establishes, what it does not establish, and what additional documents may be needed.",
    "ISSUE_DRAFTING": "",               # full instructions supplied by services.ai_drafting
    "NOTICE_ANALYSIS_STRUCTURED": "",   # full instructions supplied by services.analysis
    "LEGAL_RESEARCH": "",               # full instructions supplied by services.research
    "CUSTOM": "",
}
_NEEDS_INSTRUCTIONS = {"CUSTOM", "NOTICE_ANALYSIS_STRUCTURED", "LEGAL_RESEARCH", "ISSUE_DRAFTING"}
_OWN_SYSTEM = {"ISSUE_DRAFTING"}  # the instructions ARE the system prompt (reply drafting has its own rules)
KEY_ENV = {"anthropic": "ANTHROPIC_API_KEY", "gemini": "GEMINI_API_KEY", "offline-echo": None, "local": None}


def _key_configured(provider: str) -> bool:
    s = get_settings()
    if provider == "local":
        from .ai_providers import local_settings

        return local_settings()["enabled"]
    return {"anthropic": bool(s.anthropic_api_key), "gemini": bool(s.gemini_api_key), "offline-echo": True}.get(provider, False)


def prepare(user: dict, case_id: int, task: str, content: str, extra_instructions: str = "", *,
            provider: str | None = None, purpose: str = "GENERAL", related_id: int | None = None,
            web_search: bool = False, extra_terms: list[str] | None = None) -> dict:
    """Redact locally and stage the exact payload for approval. Nothing is sent here."""
    cases.check_access(user, case_id)
    s = get_settings()
    if task not in TASKS:
        raise ValidationError(f"Task must be one of {sorted(TASKS)}.")
    if not content or not content.strip():
        raise ValidationError("Nothing to send.")
    if task in _NEEDS_INSTRUCTIONS and not extra_instructions.strip():
        raise ValidationError(f"{task} task needs instructions.")
    provider = provider or s.ai_provider
    if provider not in PROVIDERS:
        raise ValidationError(f"Provider must be one of {sorted(PROVIDERS)}.")
    terms = cases.party_terms(case_id) + [t for t in (extra_terms or []) if t]
    res_c = redact(content, terms)
    res_i = redact(extra_instructions or "", terms)
    provider_name = provider
    status, reason, pending, body = "PENDING_APPROVAL", None, None, None
    if not res_c.ok or not res_i.ok:
        status = "BLOCKED"
        reason = "Redaction verification failed — residual identifiers detected or redaction error. Nothing will be transmitted."
    else:
        label = "Instructions" if task in _NEEDS_INSTRUCTIONS and task != "CUSTOM" else "Additional instructions"
        system = res_i.redacted_text if task in _OWN_SYSTEM else SYSTEM_PROMPT
        user_content = (TASKS[task] + "\n\n" if TASKS[task] else "") + \
            (f"{label}: {res_i.redacted_text}\n\n" if res_i.redacted_text and task not in _OWN_SYSTEM else "") + \
            "--- BEGIN REDACTED MATERIAL ---\n" + res_c.redacted_text + "\n--- END REDACTED MATERIAL ---"
        try:
            prov = get_provider(provider_name)
            body = prov.build_body(system, user_content, web_search=web_search)
        except Exception:
            # Provider not configured yet: still show the user exactly what would be sent.
            body = {"model": s.gemini_model if provider_name == "gemini" else s.anthropic_model,
                    "max_tokens": s.ai_max_tokens, "system": system,
                    "messages": [{"role": "user", "content": user_content}],
                    "_note": "Provider not configured — final body will be built in the provider's format at send time from this same text."}
        pending = dumps(body)
        if len(pending) > s.ai_max_payload_chars:
            status, reason, pending = "BLOCKED", f"Payload exceeds {s.ai_max_payload_chars} characters; send a smaller extract.", None
    model = (body or {}).get("model", s.anthropic_model)
    phash = sha256_text(pending) if pending else sha256_text(content)
    summary = {"content": res_c.summary, "instructions": res_i.summary}
    with tx() as conn:
        cur = conn.execute(
            "INSERT INTO ai_submissions(case_id,task,status,provider,model,payload_hash,payload_chars,pii_summary_json,block_reason,"
            "pending_payload,prepared_by,created_at,purpose,related_id,restore_map_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (case_id, task, status, provider_name, model, phash, len(pending or ""), dumps(summary), reason, pending, user["id"], utcnow(),
             purpose, related_id, dumps({**res_i.restore, **res_c.restore}) if purpose == "AI_DRAFTING" and pending else None))
        sid = cur.lastrowid
        audit.log_event(conn, "AI_SUBMISSION_PREPARED" if status != "BLOCKED" else "AI_SUBMISSION_BLOCKED", user_id=user["id"],
                        case_id=case_id, meta={"submission_id": sid, "task": task, "purpose": purpose, "provider": provider_name, "payload_hash": phash,
                                               "chars": len(pending or ""), "pii_counts": res_c.counts, "residual": res_c.residual})
    return get_submission(user, sid)


def get_submission(user: dict, sid: int) -> dict:
    with ro() as conn:
        r = conn.execute("SELECT * FROM ai_submissions WHERE id=?", (sid,)).fetchone()
    if not r:
        raise NotFound("Submission not found.")
    d = row_to_dict(r, ("pii_summary_json",))
    cases.check_access(user, d["case_id"])
    d["exact_payload_preview"] = json.loads(d["pending_payload"]) if d.get("pending_payload") else None
    d.pop("pending_payload", None)
    d.pop("restore_map_json", None)  # local only; never shown or sent
    s = get_settings()
    d["destination"] = {"anthropic": f"{s.anthropic_base_url}/v1/messages",
                        "gemini": f"{s.gemini_base_url}/v1beta/models/{d['model']}:generateContent"}.get(d["provider"], d["provider"])
    d["disclosure"] = SUBSCRIPTION_DISCLOSURE + (" " + GEMINI_DISCLOSURE if d["provider"] == "gemini" else "")
    d["web_search_requested"] = bool(d["exact_payload_preview"] and d["exact_payload_preview"].get("tools"))
    if d.get("response_text"):
        d["response_label"] = AI_LABEL
    return d


def approve_and_send(user: dict, sid: int, payload_hash: str, confirm: bool) -> dict:
    s = get_settings()
    with ro() as conn:
        r = conn.execute("SELECT * FROM ai_submissions WHERE id=?", (sid,)).fetchone()
    if not r:
        raise NotFound("Submission not found.")
    cases.check_access(user, r["case_id"])
    if r["status"] != "PENDING_APPROVAL":
        raise PrivacyBlocked(f"Submission is {r['status']}; it cannot be sent.")
    if not confirm:
        raise PrivacyBlocked("Explicit confirmation is required to transmit.")
    if payload_hash != r["payload_hash"] or sha256_text(r["pending_payload"] or "") != r["payload_hash"]:
        raise PrivacyBlocked("Payload hash mismatch — the payload you approved is not the payload on record. Re-prepare.")
    if r["provider"] == "local":
        if not _key_configured("local"):
            raise PermissionDenied("Local AI drafting is switched off (Settings → AI drafting).")
    elif r["provider"] != "offline-echo":
        if not s.ai_enabled:
            raise PermissionDenied("AI is disabled (set NOTICEMATE_AI_ENABLED=true). " + SUBSCRIPTION_DISCLOSURE)
        if not _key_configured(r["provider"]):
            raise PermissionDenied(f"{KEY_ENV.get(r['provider'])} is not configured. " + SUBSCRIPTION_DISCLOSURE)
    body = json.loads(r["pending_payload"])
    if "_note" in body:  # staged before the provider was configured → rebuild in provider format from the same text
        prov = get_provider(r["provider"])
        body = prov.build_body(body["system"], body["messages"][0]["content"])
    # Final defence: re-verify redaction on the exact outgoing text.
    from ..core.pii import verify_redaction

    outgoing = outgoing_text(body)
    if verify_redaction(outgoing, cases.party_terms(r["case_id"])):
        with tx() as conn:
            conn.execute("UPDATE ai_submissions SET status='BLOCKED', block_reason=?, pending_payload=NULL WHERE id=?",
                         ("Residual identifiers detected at send time.", sid))
            audit.log_event(conn, "AI_SUBMISSION_BLOCKED", user_id=user["id"], case_id=r["case_id"], meta={"submission_id": sid, "stage": "send"})
        raise PrivacyBlocked("Residual identifiers detected at send time; transmission blocked.")
    with tx() as conn:
        audit.log_event(conn, "AI_SUBMISSION_APPROVED", user_id=user["id"], case_id=r["case_id"],
                        meta={"submission_id": sid, "payload_hash": payload_hash, "provider": r["provider"], "model": r["model"]})
    try:
        result = get_provider(r["provider"]).send(body)
    except Exception as exc:
        kind = getattr(exc, "kind", type(exc).__name__)
        with tx() as conn:
            conn.execute("UPDATE ai_submissions SET status='FAILED', block_reason=?, error_kind=? WHERE id=?",
                         (str(getattr(exc, "message", exc))[:300], kind, sid))
            audit.log_event(conn, "AI_SUBMISSION_FAILED", user_id=user["id"], case_id=r["case_id"],
                            meta={"submission_id": sid, "error": kind})
        raise
    with tx() as conn:
        resp = result.text
        if result.citations:
            resp += "\n\n---\nSOURCES RETURNED BY PROVIDER WEB SEARCH (unverified):\n" + "\n".join(
                f"- {c['title'] or c['url']} — {c['url']}" for c in result.citations)
        conn.execute("UPDATE ai_submissions SET status='SENT', approved_by=?, sent_at=?, response_text=?, pending_payload=? WHERE id=?",
                     (user["id"], utcnow(), resp, r["pending_payload"] if s.retain_ai_payloads else None, sid))
        audit.log_event(conn, "AI_SUBMISSION_SENT", user_id=user["id"], case_id=r["case_id"],
                        meta={"submission_id": sid, "payload_hash": payload_hash, "model": result.model,
                              "input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
                              "n_citations": len(result.citations),
                              "payload_retained": s.retain_ai_payloads})
    out = get_submission(user, sid)
    if r["purpose"] == "AI_DRAFTING":  # the answer becomes a new draft version straight away — no separate "apply" step
        from . import ai_drafting

        try:
            out["drafting_result"] = ai_drafting.ingest_cloud(user, sid, json.loads(r["restore_map_json"] or "{}"), result.text)
        except Exception as exc:
            out["drafting_error"] = str(getattr(exc, "message", exc))[:300]
        with tx() as conn:
            conn.execute("UPDATE ai_submissions SET restore_map_json=NULL WHERE id=?", (sid,))
    return out


def cancel(user: dict, sid: int) -> dict:
    d = get_submission(user, sid)
    if d["status"] != "PENDING_APPROVAL":
        raise ValidationError("Only pending submissions can be cancelled.")
    with tx() as conn:
        conn.execute("UPDATE ai_submissions SET status='CANCELLED', pending_payload=NULL WHERE id=?", (sid,))
        audit.log_event(conn, "AI_SUBMISSION_CANCELLED", user_id=user["id"], case_id=d["case_id"], meta={"submission_id": sid})
    return get_submission(user, sid)


def list_submissions(user: dict, case_id: int) -> list[dict]:
    cases.check_access(user, case_id)
    with ro() as conn:
        ids = [r["id"] for r in conn.execute("SELECT id FROM ai_submissions WHERE case_id=? ORDER BY id DESC", (case_id,))]
    return [get_submission(user, i) for i in ids]


def status() -> dict:
    s = get_settings()
    providers = {
        "anthropic": {"model": s.anthropic_model, "key_env": "ANTHROPIC_API_KEY", "api_key_configured": bool(s.anthropic_api_key),
                      "live_web_search_enabled": s.anthropic_web_search, "endpoint": f"{s.anthropic_base_url}/v1/messages"},
        "gemini": {"model": s.gemini_model, "key_env": "GEMINI_API_KEY", "api_key_configured": bool(s.gemini_api_key),
                   "live_web_search_enabled": s.gemini_grounding,
                   "endpoint": f"{s.gemini_base_url}/v1beta/models/{s.gemini_model}:generateContent"},
    }
    if s.ai_provider == "offline-echo":
        providers["offline-echo"] = {"model": "offline-echo", "key_env": None, "api_key_configured": True,
                                     "live_web_search_enabled": False, "endpoint": "none (test provider)"}
    return {"ai_enabled": s.ai_enabled, "provider": s.ai_provider, "default_provider": s.ai_provider,
            "model": providers.get(s.ai_provider, {}).get("model", s.anthropic_model),
            "api_key_configured": _key_configured(s.ai_provider), "providers": providers,
            "disclosure": SUBSCRIPTION_DISCLOSURE, "gemini_disclosure": GEMINI_DISCLOSURE,
            "retain_payloads": s.retain_ai_payloads,
            "live_research_note": ("Live legal research requires a provider web-search tool to be enabled; otherwise AI answers come from "
                                   "the model's training data, which may be outdated and are never current law.")}


def test_connection(user: dict, provider: str) -> dict:
    """Explicit user action: sends a fixed, client-free prompt to check key/model/connectivity."""
    s = get_settings()
    if provider not in PROVIDERS:
        raise ValidationError(f"Provider must be one of {sorted(PROVIDERS)}.")
    if provider == "local":
        if not _key_configured("local"):
            raise PermissionDenied("Local AI drafting is switched off (Settings → AI drafting).")
    elif provider != "offline-echo":
        if not s.ai_enabled:
            raise PermissionDenied("AI is disabled (NOTICEMATE_AI_ENABLED=false).")
        if not _key_configured(provider):
            raise PermissionDenied(f"{KEY_ENV[provider]} is not configured.")
    prov = get_provider(provider)
    body = prov.build_body("Connectivity test. No client data.", "Reply with the single word: OK")
    if "max_tokens" in body:
        body["max_tokens"] = 10
    ok, err, kind, model = False, None, None, getattr(prov, "model", "")
    try:
        res = prov.send(body)
        ok, model = True, res.model
    except Exception as exc:
        err, kind = str(getattr(exc, "message", exc))[:300], getattr(exc, "kind", type(exc).__name__)
    with tx() as conn:
        audit.log_event(conn, "AI_CONNECTION_TEST", user_id=user["id"],
                        meta={"provider": provider, "model": model, "ok": ok, "error_kind": kind})
    return {"provider": provider, "model": model, "ok": ok, "error": err, "error_kind": kind,
            "note": "A fixed test prompt with no client data was sent."}
