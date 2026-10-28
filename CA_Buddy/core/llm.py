"""Minimal clients for Claude (Anthropic), OpenAI and Gemini over plain HTTPS.
The API key is used for the request and never stored by the server."""
from __future__ import annotations

import os

import httpx

from .pdf_tools import ToolError

PROVIDERS = {
    "anthropic": {
        "label": "Claude (Anthropic)",
        "default": "claude-sonnet-5-5",
        "suggested": ["claude-sonnet-5-5", "claude-opus-5-5", "claude-haiku-5-5"],
        "key_hint": "sk-ant-…",
        "key_url": "https://console.anthropic.com/settings/keys",
    },
    "openai": {
        "label": "OpenAI",
        "default": "gpt-5.5",
        "suggested": ["gpt-5.5", "gpt-5.4-mini"],
        "key_hint": "sk-…",
        "key_url": "https://platform.openai.com/api-keys",
    },
    "gemini": {
        "label": "Google Gemini",
        "default": "gemini-flash-latest",
        "suggested": ["gemini-flash-latest", "gemini-3.1-pro-preview", "gemini-3.5-flash"],
        "key_hint": "AIza…",
        "key_url": "https://aistudio.google.com/apikey",
    },
}

TIMEOUT = httpx.Timeout(connect=20, read=300, write=60, pool=20)


def _client() -> httpx.AsyncClient:
    # honour corporate proxies / custom CA bundles if configured
    verify = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE") or True
    return httpx.AsyncClient(timeout=TIMEOUT, verify=verify, trust_env=True)


def _friendly(provider: str, resp: httpx.Response) -> ToolError:
    name = PROVIDERS[provider]["label"]
    try:
        body = resp.json()
        detail = (body.get("error") or {}).get("message") if isinstance(body.get("error"), dict) \
            else body.get("error") or body.get("message") or ""
    except Exception:  # noqa: BLE001
        detail = resp.text[:300]
    code = resp.status_code
    if code in (401, 403) or "API key not valid" in str(detail):
        msg = f"{name} rejected the API key. Check that it's correct and active."
    elif code == 404 or "not found" in str(detail).lower() and "model" in str(detail).lower():
        msg = f"{name} doesn't recognise that model name. Click “Load models” to pick one your key can use."
    elif code == 429:
        msg = f"{name} says you've hit a rate or credit limit. Wait a minute, or check billing on your account."
    elif code == 400 and "credit" in str(detail).lower():
        msg = f"{name} says the account has no credit left. Add credit and try again."
    elif code >= 500:
        msg = f"{name} is having trouble right now (error {code}). Try again shortly."
    else:
        msg = f"{name} returned an error ({code})."
    if detail:
        msg += f" Details: {str(detail)[:300]}"
    return ToolError(msg)


async def complete(provider: str, model: str, api_key: str, system: str,
                   messages: list[dict], max_tokens: int = 12000) -> str:
    """messages: [{'role': 'user'|'assistant', 'content': str}, ...]"""
    if provider not in PROVIDERS:
        raise ToolError("Choose an AI provider.")
    if not api_key.strip():
        raise ToolError("Paste your API key to continue.")
    model = model.strip() or PROVIDERS[provider]["default"]
    if os.environ.get("CAWB_FAKE_LLM"):
        return _fake(messages)
    try:
        async with _client() as c:
            if provider == "anthropic":
                r = await c.post("https://api.anthropic.com/v1/messages", headers={
                    "x-api-key": api_key.strip(), "anthropic-version": "2023-06-01",
                    "content-type": "application/json"},
                    json={"model": model, "max_tokens": max_tokens, "system": system,
                          "messages": messages})
                if r.status_code != 200:
                    raise _friendly(provider, r)
                data = r.json()
                text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
                if data.get("stop_reason") == "max_tokens":
                    text += "\n\n*(The answer was cut off because it hit the length limit. Ask for a shorter version or continue.)*"
                return text
            if provider == "openai":
                r = await c.post("https://api.openai.com/v1/chat/completions", headers={
                    "Authorization": f"Bearer {api_key.strip()}"},
                    json={"model": model,
                          "messages": [{"role": "system", "content": system}] + messages})
                if r.status_code != 200:
                    raise _friendly(provider, r)
                choice = r.json()["choices"][0]
                text = choice["message"].get("content") or ""
                if choice.get("finish_reason") == "length":
                    text += "\n\n*(The answer was cut off at the length limit.)*"
                return text
            # gemini
            contents = [{"role": "model" if m["role"] == "assistant" else "user",
                         "parts": [{"text": m["content"]}]} for m in messages]
            r = await c.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": api_key.strip()},
                json={"systemInstruction": {"parts": [{"text": system}]}, "contents": contents,
                      "generationConfig": {"maxOutputTokens": max(max_tokens, 16000)}})
            if r.status_code != 200:
                raise _friendly(provider, r)
            data = r.json()
            cands = data.get("candidates") or []
            if not cands:
                reason = (data.get("promptFeedback") or {}).get("blockReason", "no answer")
                raise ToolError(f"Gemini didn't return an answer ({reason}).")
            parts = (cands[0].get("content") or {}).get("parts") or []
            text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
            if cands[0].get("finishReason") == "MAX_TOKENS":
                text += "\n\n*(The answer was cut off at the length limit.)*"
            return text
    except httpx.ConnectError as exc:
        raise ToolError("Couldn't reach the AI service. Check your internet connection or office proxy.") from exc
    except httpx.TimeoutException as exc:
        raise ToolError("The AI service took too long to answer. Try again, or use a faster model.") from exc


async def list_models(provider: str, api_key: str) -> list[str]:
    if not api_key.strip():
        raise ToolError("Paste your API key first.")
    if os.environ.get("CAWB_FAKE_LLM"):
        return PROVIDERS[provider]["suggested"]
    async with _client() as c:
        try:
            if provider == "anthropic":
                r = await c.get("https://api.anthropic.com/v1/models?limit=100", headers={
                    "x-api-key": api_key.strip(), "anthropic-version": "2023-06-01"})
                if r.status_code != 200:
                    raise _friendly(provider, r)
                return [m["id"] for m in r.json().get("data", [])]
            if provider == "openai":
                r = await c.get("https://api.openai.com/v1/models",
                                headers={"Authorization": f"Bearer {api_key.strip()}"})
                if r.status_code != 200:
                    raise _friendly(provider, r)
                ids = [m["id"] for m in r.json().get("data", [])]
                skip = ("embedding", "whisper", "tts", "dall-e", "image", "audio", "realtime",
                        "transcribe", "moderation", "search", "babbage", "davinci")
                ids = [i for i in ids if i.startswith(("gpt", "o", "chatgpt")) and not any(s in i for s in skip)]
                return sorted(ids, reverse=True)
            r = await c.get("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200",
                            headers={"x-goog-api-key": api_key.strip()})
            if r.status_code != 200:
                raise _friendly(provider, r)
            return [m["name"].removeprefix("models/") for m in r.json().get("models", [])
                    if "generateContent" in m.get("supportedGenerationMethods", [])
                    and "gemini" in m["name"] and not any(s in m["name"] for s in ("tts", "image", "embedding", "live"))]
        except httpx.HTTPError as exc:
            raise ToolError("Couldn't reach the AI service to list models.") from exc


def _fake(messages: list[dict]) -> str:
    """Offline stand-in used for testing (CAWB_FAKE_LLM=1)."""
    last = messages[-1]["content"]
    import re
    tokens = sorted(set(re.findall(r"\[[A-Z]+_\d+\]", last)))
    if "Draft a formal reply" in last:
        return ("[[Firm / taxpayer letterhead]]\n\nDate: [[date]]\n\nTo,\nThe Proper Officer\n\n"
                f"**Subject:** Reply to notice issued to {tokens[0] if tokens else '[NAME_1]'}\n\n"
                "## Preliminary submissions\n\n1. The notice is barred by limitation **(verify)**.\n"
                "2. No DRC-01A was issued.\n\n## Point-wise reply\n\n### 1. ITC mismatch\n\n"
                "The difference of ₹ 1,23,456 is explained in Annexure A.\n\n"
                "| Item | Amount |\n|---|---|\n| As per books | [[amount]] |\n| As per GSTR-2B | ₹ 4,56,789 |\n\n"
                "## Prayer\n\nIt is prayed that the proceedings be dropped.\n\nFor " + " ".join(tokens) + "\n")
    if "Revise your previous answer" in last:
        return "## Revised\n\nThis is the revised version for " + " ".join(tokens) + "."
    return ("## At a glance\n\n| Field | Detail |\n|---|---|\n"
            f"| Taxpayer | {tokens[0] if tokens else '-'} |\n| Reply due | 30 days |\n\n"
            "## What the department is alleging\n\n- *Excess ITC* claimed of **₹ 1,23,456**.\n\n"
            "Tokens seen: " + ", ".join(tokens))
