"""Optional AI helpers. The app works fully without them.

Works with a key from any of three providers: Claude (Anthropic), ChatGPT
(OpenAI) or Gemini (Google). The provider is recognised from the key, and the
list of models is read from the provider so the user can pick one.

The API key is supplied by the user at run time (Settings box or an
environment variable). It is never written to disk.

Privacy: the client's name is NOT sent. The explanation call sends only
rounded figures; the ledger call sends only ledger and group names that the
rule-based classifier could not place.
"""
from __future__ import annotations

import json
import os
import re

PROVIDERS = {"anthropic": "Claude (Anthropic)", "openai": "ChatGPT (OpenAI)", "gemini": "Gemini (Google)"}
ENV_KEYS = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY"}
# Used only when the provider's model list cannot be read; the user can type any other name.
FALLBACK_MODELS = {"anthropic": "claude-sonnet-5-5", "openai": "gpt-4o", "gemini": "gemini-2.5-flash"}
DEFAULT_MODEL = FALLBACK_MODELS["anthropic"]
TIMEOUT = 60

_OPENAI_CHAT = re.compile(r"^(gpt-|chatgpt-|o\d)")
_OPENAI_SKIP = ("audio", "realtime", "tts", "transcribe", "whisper", "image", "embedding", "moderation",
                "search", "instruct", "codex", "computer-use", "deep-research")
_GEMINI_SKIP = ("embedding", "image", "tts", "audio", "vision", "aqa", "live", "robotics", "computer-use")


class AIError(RuntimeError):
    """A problem talking to the AI provider, with a message fit to show on screen."""


# ------------------------------------------------------------------ provider
def detect_provider(api_key: str) -> str | None:
    """Recognise the provider from the shape of the key. None when it cannot be told."""
    key = (api_key or "").strip()
    if key.startswith("sk-ant-"):
        return "anthropic"
    if key.startswith("sk-"):
        return "openai"
    if key.startswith("AIza"):
        return "gemini"
    return None


def key_from_environment() -> tuple[str, str | None]:
    """(key, provider) from the first environment variable that is set, else ("", None)."""
    for provider, var in ENV_KEYS.items():
        if os.environ.get(var):
            return os.environ[var], provider
    return "", None


def _provider(api_key: str, provider: str | None) -> str:
    chosen = provider or detect_provider(api_key)
    if chosen not in PROVIDERS:
        raise AIError("Could not tell which AI provider this key belongs to. Choose the provider in Settings.")
    return chosen


# --------------------------------------------------------------------- http
def _request(method: str, url: str, headers: dict, body: dict | None = None) -> dict:
    import requests  # imported lazily so the app starts even if the package is missing

    try:
        resp = requests.request(method, url, headers=headers, json=body, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise AIError(f"Could not reach the AI provider: {exc.__class__.__name__}. Check the internet connection.") from exc
    try:
        data = resp.json()
    except ValueError:
        data = {}
    if resp.status_code >= 400:
        err = data.get("error") if isinstance(data, dict) else None
        detail = err.get("message") if isinstance(err, dict) else (err if isinstance(err, str) else "")
        if resp.status_code in (401, 403):
            hint = "The key was not accepted. Check the key and the provider."
        elif resp.status_code == 404:
            hint = "The model was not found. Pick another model."
        elif resp.status_code == 429:
            hint = "The provider's usage limit was reached, or the account has no credit."
        else:
            hint = "The provider returned an error."
        raise AIError(f"{hint} ({resp.status_code}{': ' + str(detail)[:200] if detail else ''})")
    return data if isinstance(data, dict) else {}


def _headers(provider: str, api_key: str) -> dict:
    key = api_key.strip()
    if provider == "anthropic":
        return {"x-api-key": key, "anthropic-version": "2023-06-01"}
    if provider == "openai":
        return {"Authorization": f"Bearer {key}"}
    return {"x-goog-api-key": key}


# ------------------------------------------------------------------- models
def list_models(api_key: str, provider: str | None = None) -> list[dict]:
    """Text models the key can use, best guess first: [{"id": ..., "label": ...}]."""
    p = _provider(api_key, provider)
    h = _headers(p, api_key)
    if p == "anthropic":
        data = _request("GET", "https://api.anthropic.com/v1/models?limit=1000", h)
        rows = sorted(data.get("data", []), key=lambda m: str(m.get("created_at", "")), reverse=True)
        return [{"id": m["id"], "label": m.get("display_name") or m["id"]} for m in rows if m.get("id")]
    if p == "openai":
        data = _request("GET", "https://api.openai.com/v1/models", h)
        rows = [m for m in data.get("data", [])
                if _OPENAI_CHAT.match(str(m.get("id", ""))) and not any(x in m["id"] for x in _OPENAI_SKIP)]
        rows.sort(key=lambda m: m.get("created", 0), reverse=True)
        return [{"id": m["id"], "label": m["id"]} for m in rows]
    data = _request("GET", "https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000", h)
    out = []
    for m in data.get("models", []):
        mid = str(m.get("name", "")).removeprefix("models/")
        if (mid.startswith("gemini") and "generateContent" in m.get("supportedGenerationMethods", [])
                and not any(x in mid for x in _GEMINI_SKIP)):
            out.append({"id": mid, "label": m.get("displayName") or mid})
    return sorted(out, key=lambda m: m["id"], reverse=True)


def suggested_model(models: list[dict], provider: str) -> str:
    """A sensible everyday model from the list: capable but not the costliest."""
    ids = [m["id"] for m in models]
    hints = {"anthropic": ("sonnet",), "openai": ("mini",), "gemini": ("flash",)}[provider]
    for mid in ids:
        if any(hint in mid for hint in hints) and "preview" not in mid and "exp" not in mid:
            return mid
    return ids[0] if ids else FALLBACK_MODELS[provider]


# --------------------------------------------------------------------- chat
def ask(prompt: str, api_key: str, model: str, provider: str | None = None, max_tokens: int = 600) -> str:
    """Send one prompt and return the text of the reply."""
    p = _provider(api_key, provider)
    h = _headers(p, api_key)
    if p == "anthropic":
        data = _request("POST", "https://api.anthropic.com/v1/messages", h,
                        {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]})
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    elif p == "openai":
        data = _request("POST", "https://api.openai.com/v1/chat/completions", h,
                        {"model": model, "messages": [{"role": "user", "content": prompt}]})
        choices = data.get("choices") or [{}]
        text = (choices[0].get("message") or {}).get("content") or ""
    else:
        data = _request("POST", f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", h,
                        {"contents": [{"role": "user", "parts": [{"text": prompt}]}]})
        cands = data.get("candidates") or [{}]
        text = "".join(part.get("text", "") for part in (cands[0].get("content") or {}).get("parts", []))
    text = text.strip()
    if not text:
        raise AIError("The AI returned an empty reply. Try again or pick another model.")
    return text


# -------------------------------------------------------------------- tasks
def explain_for_client(summary: dict, api_key: str, model: str = DEFAULT_MODEL, language: str = "English",
                       provider: str | None = None) -> str:
    """A short, plain-language explanation of the advance tax position."""
    prompt = (
        "You are assisting an Indian Chartered Accountant's office. Write a short explanation (max 110 words) "
        f"in simple {language} for a business owner about the advance tax position below. "
        "Use only the figures given. Do not add tax advice, section numbers or new numbers. "
        "Say what to pay, by when, why, and what happens if it is late. No greeting or sign-off.\n\n"
        f"Figures (rupees):\n{json.dumps(summary, indent=2, default=str)}"
    )
    return ask(prompt, api_key, model, provider, max_tokens=600)


def flag_unusual_items(ledgers: list[dict], api_key: str, model: str = DEFAULT_MODEL,
                       provider: str | None = None) -> str:
    """Point out ledgers that may distort a straight-line projection."""
    prompt = (
        "Below are profit and loss ledgers with year-to-date amounts from an Indian business. "
        "List up to 5 items that look one-off, seasonal or unusual and so should not be simply annualised "
        "when projecting full-year profit. One line each with the reason. If nothing stands out, say so.\n\n"
        f"{json.dumps(ledgers, indent=1)}"
    )
    return ask(prompt, api_key, model, provider, max_tokens=600)


def classify_ledgers(items: list[dict], api_key: str, model: str = DEFAULT_MODEL,
                     provider: str | None = None) -> dict:
    """Classify ledgers the rules could not place. Returns {ledger: type}."""
    prompt = (
        "Classify each trial balance ledger of an Indian business as exactly one of: "
        '"Income", "Expense", "Opening Stock", "Ignore". Use "Ignore" for balance-sheet items '
        "(assets, liabilities, capital, taxes, parties, bank, cash). "
        "Reply with only a JSON object mapping the ledger name to the type.\n\n"
        f"{json.dumps(items, indent=1)}"
    )
    raw = ask(prompt, api_key, model, provider, max_tokens=3000)
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    allowed = {"Income", "Expense", "Opening Stock", "Ignore"}
    return {k: v for k, v in data.items() if v in allowed}
