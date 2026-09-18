"""
Agentic reasoning layer (Module 2/10 — AI Agents, Agentic AI).

Dynamically detects online :free models directly from OpenRouter's live catalog,
ensuring zero cost ($0.00) and preventing 404 'Model Not Found' errors.
"""

import os
import json
import time
import re
import urllib.request
import urllib.error
from dotenv import load_dotenv
from reconciliation import InvoiceReconciliation

# Load environment variables
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

SYSTEM_PROMPT = """You are assisting a Chartered Accountant who has just run an automated
reconciliation of intercompany invoices against a master intercompany agreement.

You will be given the OUTPUT OF A DETERMINISTIC RECONCILIATION ENGINE — every finding,
severity, and specific figure has already been computed and verified by code. Your job is
ONLY to:
1. Write a short batch-level executive summary (max 150 words) of what was found across
   all invoices reviewed.
2. Prioritise the invoices/findings that need attention first (CRITICAL before FLAG before
   REVIEW), in a short ordered list.
3. Suggest 3-5 concrete next steps for the CA reviewing this batch.

STRICT RULES:
- Do NOT invent, restate with altered figures, or "correct" any amount, date, currency, or
  entity name. Use only what is given to you verbatim.
- Do NOT assert an invoice is correct or incorrect beyond what the findings already say.
- If extraction confidence was flagged as low for a document (OCR-sourced fields), reflect
  that uncertainty in your summary rather than treating the figures as certain.
- Return ONLY valid JSON.
"""


def _findings_to_text(reconciliations: list[InvoiceReconciliation]) -> str:
    lines = []
    for r in reconciliations:
        lines.append(
            f"\n--- {r.invoice.filename} (extraction method: {r.invoice.extraction_method}, "
            f"overall status: {r.status}) ---"
        )
        for f in r.findings:
            lines.append(f"  [{f.severity}] {f.check}: {f.detail}")
    return "\n".join(lines)


def _sanitize_json_output(text: str) -> str:
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if match:
        return match.group(1).strip()
    return cleaned


def _get_live_free_models() -> list[str]:
    """Fetches the list of currently active zero-cost models from OpenRouter."""
    url = "https://openrouter.ai/api/v1/models"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            free_models = []
            for m in data.get("data", []):
                model_id = m.get("id", "")
                pricing = m.get("pricing", {})
                # Strictly verify zero pricing ($0 prompt & $0 completion) or :free suffix
                if model_id.endswith(":free") or (
                    str(pricing.get("prompt")) == "0" and str(pricing.get("completion")) == "0"
                ):
                    free_models.append(model_id)
            if free_models:
                return free_models
    except Exception as err:
        print(f"[agent.py] Could not fetch live model list: {err}")

    # Fallback to standard free identifiers if catalog retrieval fails
    return [
        "meta-llama/llama-3.2-3b-instruct:free",
        "meta-llama/llama-3.1-8b-instruct:free",
        "mistralai/mistral-7b-instruct:free",
        "qwen/qwen-2.5-72b-instruct:free",
    ]


def _call_openrouter_api(model: str, user_prompt: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5002",
        "X-Title": "Invoice Consistency Checker",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 2048,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            return res_data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {e.code}: {error_body}")


def generate_batch_narrative(reconciliations: list[InvoiceReconciliation]) -> dict:
    findings_text = _findings_to_text(reconciliations)

    status_counts = {}
    for r in reconciliations:
        status_counts[r.status] = status_counts.get(r.status, 0) + 1

    user_prompt = f"""Batch summary: {len(reconciliations)} invoices reviewed against one master
intercompany agreement.

Status breakdown: {json.dumps(status_counts)}

Detailed findings per invoice:
{findings_text}

Respond ONLY in valid JSON format with keys:
"executive_summary" (string),
"prioritized_items" (list of strings, most urgent first referencing invoice filenames),
"recommended_next_steps" (list of strings).
No markdown formatting, no commentary outside the JSON.
"""

    models_to_try = _get_live_free_models()
    print(f"[agent.py] Found {len(models_to_try)} active free model(s) on OpenRouter.")

    response_text = None
    last_error = None

    for model_name in models_to_try[:5]:  # Try top verified free models
        try:
            print(f"[agent.py] Trying model: {model_name}...")
            response_text = _call_openrouter_api(model_name, user_prompt)
            if response_text:
                print(f"[agent.py] Succeeded with {model_name}")
                break
        except Exception as e:
            last_error = e
            print(f"[agent.py] Error on {model_name}: {e}")
            time.sleep(1)

    if response_text is None:
        return {
            "executive_summary": (
                f"[Narrative generation unavailable across free models: {last_error}] "
                f"Status breakdown: {json.dumps(status_counts)}. See detailed findings below."
            ),
            "prioritized_items": [
                f"{r.invoice.filename}: {r.status}"
                for r in reconciliations
                if r.status in ("CRITICAL", "FLAG")
            ],
            "recommended_next_steps": [
                "Verify OPENROUTER_API_KEY in .env.",
                "Review detailed findings directly in the meantime.",
            ],
        }

    cleaned = _sanitize_json_output(response_text)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "executive_summary": (
                "Narrative generated; please see detailed findings below for the full analysis."
            ),
            "prioritized_items": [
                f"{r.invoice.filename}: {r.status}"
                for r in reconciliations
                if r.status in ("CRITICAL", "FLAG")
            ],
            "recommended_next_steps": [
                "Review detailed findings directly.",
            ],
            "_raw_model_output": response_text,
        }