"""AI provider adapters (stdlib HTTP — no vendor SDKs required).

Providers
* anthropic     — Anthropic Messages API (unchanged from v1; ANTHROPIC_API_KEY).
* gemini        — Google Gemini generateContent API (optional; GEMINI_API_KEY).
* offline-echo  — test-only, no network.

Only the AI gateway may call send(). Keys come from the environment only and
are sent as HTTP headers — never placed in the request body, logs or DB.

Optional live web research (off by default):
* Anthropic server-side web search tool  (NOTICEMATE_ANTHROPIC_WEB_SEARCH=true)
* Gemini Google Search grounding          (NOTICEMATE_GEMINI_GROUNDING=true)
These must also be enabled on the provider account and are billed by the
provider. They were not exercised against the live APIs in the build
environment; if the provider rejects the tool, the error is shown to the user.
"""
from __future__ import annotations

import json
import re
import socket
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from ..core.config import get_settings
from ..core.errors import ProviderError


@dataclass
class ProviderResult:
    text: str
    input_tokens: int | None
    output_tokens: int | None
    model: str
    citations: list[dict] = field(default_factory=list)  # [{"url":..., "title":...}]


def provider_error(kind: str, msg: str) -> ProviderError:
    e = ProviderError(msg, details={"kind": kind})
    e.kind = kind  # type: ignore[attr-defined]
    return e


def _http_json(url: str, body: dict, headers: dict, timeout: int, provider: str) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={**headers, "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            j = json.loads(e.read().decode("utf-8"))
            detail = (j.get("error") or {}).get("message", "") if isinstance(j.get("error"), dict) else str(j.get("error", ""))
        except Exception:
            pass
        detail = detail[:300]
        retry = e.headers.get("retry-after") if e.headers else None
        if e.code in (401, 403):
            raise provider_error("AUTH", f"{provider}: authentication/permission failed (HTTP {e.code}). Check the API key. "
                                         f"Note: a Claude Pro subscription does not include API usage. {detail}")
        if e.code == 402:
            raise provider_error("BILLING", f"{provider}: billing/credit problem (HTTP 402). {detail}")
        if e.code == 429:
            raise provider_error("RATE_LIMIT", f"{provider}: rate limit or quota exceeded (HTTP 429)."
                                               + (f" Retry after {retry} s." if retry else " Wait and retry.") + f" {detail}")
        if e.code in (400, 404, 413, 422):
            raise provider_error("BAD_REQUEST", f"{provider}: request rejected (HTTP {e.code}) — check model name / options. {detail}")
        if e.code >= 500:
            raise provider_error("SERVER", f"{provider}: provider server error (HTTP {e.code}); try again later. {detail}")
        raise provider_error("HTTP", f"{provider}: HTTP {e.code}. {detail}")
    except (socket.timeout, TimeoutError):
        raise provider_error("TIMEOUT", f"{provider}: request timed out after {timeout} s.")
    except urllib.error.URLError as e:
        if isinstance(getattr(e, "reason", None), (socket.timeout, TimeoutError)):
            raise provider_error("TIMEOUT", f"{provider}: request timed out after {timeout} s.")
        raise provider_error("NETWORK", f"{provider}: could not reach the API ({type(getattr(e, 'reason', e)).__name__}). Check internet/proxy.")
    except json.JSONDecodeError:
        raise provider_error("SERVER", f"{provider}: response was not valid JSON.")


class AnthropicProvider:
    name = "anthropic"
    API_VERSION = "2023-06-01"

    def __init__(self):
        s = get_settings()
        if not s.anthropic_api_key:
            raise provider_error("NOT_CONFIGURED", "ANTHROPIC_API_KEY is not set in the environment.")
        self._key = s.anthropic_api_key
        self.model = s.anthropic_model
        self.base = s.anthropic_base_url.rstrip("/")
        self.timeout = s.ai_timeout_s
        self.max_tokens = s.ai_max_tokens
        self.web_search_available = s.anthropic_web_search

    @property
    def endpoint(self) -> str:
        return f"{self.base}/v1/messages"

    def build_body(self, system: str, user_content: str, *, web_search: bool = False) -> dict:
        body = {"model": self.model, "max_tokens": self.max_tokens, "system": system,
                "messages": [{"role": "user", "content": user_content}]}
        if web_search and self.web_search_available:
            body["tools"] = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}]
        return body

    def send(self, body: dict) -> ProviderResult:
        data = _http_json(self.endpoint, body, {"x-api-key": self._key, "anthropic-version": self.API_VERSION},
                          self.timeout, "Anthropic")
        texts, cites = [], []
        for b in data.get("content", []):
            if b.get("type") == "text":
                texts.append(b.get("text", ""))
                for c in b.get("citations") or []:
                    if c.get("url"):
                        cites.append({"url": c["url"], "title": c.get("title", "")})
        u = data.get("usage", {})
        return ProviderResult("".join(texts), u.get("input_tokens"), u.get("output_tokens"), data.get("model", self.model),
                              _dedupe(cites))


class GeminiProvider:
    name = "gemini"

    def __init__(self):
        s = get_settings()
        if not s.gemini_api_key:
            raise provider_error("NOT_CONFIGURED", "GEMINI_API_KEY is not set in the environment.")
        self._key = s.gemini_api_key
        self.model = s.gemini_model
        self.base = s.gemini_base_url.rstrip("/")
        self.timeout = s.ai_timeout_s
        self.max_tokens = s.ai_max_tokens
        self.web_search_available = s.gemini_grounding

    @property
    def endpoint(self) -> str:
        return f"{self.base}/v1beta/models/{self.model}:generateContent"

    def build_body(self, system: str, user_content: str, *, web_search: bool = False) -> dict:
        body = {"model": self.model,  # informational; stripped before sending (model is in the URL)
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user_content}]}],
                "generationConfig": {"maxOutputTokens": self.max_tokens}}
        if web_search and self.web_search_available:
            body["tools"] = [{"google_search": {}}]
        return body

    def send(self, body: dict) -> ProviderResult:
        payload = {k: v for k, v in body.items() if k != "model"}
        data = _http_json(self.endpoint, payload, {"x-goog-api-key": self._key}, self.timeout, "Gemini")
        cands = data.get("candidates") or []
        if not cands:
            fb = (data.get("promptFeedback") or {}).get("blockReason")
            raise provider_error("BLOCKED_BY_PROVIDER", f"Gemini returned no answer{' (blocked: ' + fb + ')' if fb else ''}.")
        parts = (cands[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts)
        cites = []
        for ch in (cands[0].get("groundingMetadata") or {}).get("groundingChunks") or []:
            w = ch.get("web") or {}
            if w.get("uri"):
                cites.append({"url": w["uri"], "title": w.get("title", "")})
        u = data.get("usageMetadata", {})
        return ProviderResult(text, u.get("promptTokenCount"), u.get("candidatesTokenCount"), self.model, _dedupe(cites))


class OfflineEchoProvider:
    """For tests and demos only — performs no network call. Clearly labelled."""

    name = "offline-echo"
    model = "offline-echo"
    endpoint = "offline-echo (no network)"
    web_search_available = False

    def build_body(self, system: str, user_content: str, *, web_search: bool = False) -> dict:
        return {"model": self.model, "system": system, "messages": [{"role": "user", "content": user_content}]}

    def send(self, body: dict) -> ProviderResult:
        txt = body["messages"][0]["content"]
        canned = get_settings().offline_echo_response
        if canned:
            return ProviderResult(canned, None, None, self.model)
        return ProviderResult(f"[OFFLINE TEST PROVIDER — no AI call made]\nReceived {len(txt)} characters.", None, None, self.model)


LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def local_settings() -> dict:
    """Local-AI address and model: in-app settings (Settings → AI drafting) override the environment."""
    from . import appsettings

    s = get_settings()
    return {"url": (appsettings.get("local_ai_url") or s.local_ai_url).rstrip("/"),
            "model": appsettings.get("local_ai_model") or s.local_ai_model,
            "enabled": appsettings.get("local_ai_enabled") == "1"}


def check_loopback(url: str) -> None:
    from urllib.parse import urlparse

    u = urlparse(url)
    if u.scheme not in ("http", "https") or (u.hostname or "") not in LOOPBACK:
        raise provider_error("NOT_LOCAL", "The local AI address must be on this computer (http://127.0.0.1:…, localhost). "
                                          "Case text is never sent to another machine through the local option.")


def local_readiness(url: str | None = None, model: str | None = None, timeout: float = 4.0) -> dict:
    """Is a local model server (LM Studio / Ollama, OpenAI-compatible) running here, and which models does it offer?
    Read-only: asks the server for its model list; no case data is sent; nothing is downloaded."""
    cfg = local_settings()
    url = (url or cfg["url"]).rstrip("/")
    model = model if model is not None else cfg["model"]
    out = {"url": url, "enabled": cfg["enabled"], "reachable": False, "models": [], "model": None, "ready": False}
    try:
        check_loopback(url)
    except ProviderError as e:
        return {**out, "message": e.message}
    try:
        with urllib.request.urlopen(urllib.request.Request(url + "/models", method="GET"), timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:
        return {**out, "message": f"No local AI server is answering at {url}. Start LM Studio (Developer → Start server) "
                                  "or Ollama, load a model, then check again."}
    ids = [m.get("id") for m in data.get("data") or [] if m.get("id")]
    chat = [i for i in ids if "embed" not in i.lower()]
    out.update(reachable=True, models=chat)
    if not chat:
        return {**out, "message": "The local AI server is running but has no chat model available. Download and load a model "
                                  "in LM Studio (or `ollama pull` in Ollama), then check again."}
    chosen = model if model in chat else (chat[0] if not model else None)
    if not chosen:
        return {**out, "message": f"The chosen model '{model}' is not available on the local server. Pick one of: "
                                  + ", ".join(chat[:8])}
    out.update(model=chosen, ready=True,
               message=f"Local AI server found at {url}; model '{chosen}' will be used." +
                       ("" if cfg["enabled"] else " Local AI drafting is switched off — turn it on to use it."))
    return out


class LocalOpenAIProvider:
    """A model running on this computer behind an OpenAI-compatible server (LM Studio, Ollama).
    Requests go only to a loopback address, so case text does not leave the computer."""

    name = "local"
    web_search_available = False

    def __init__(self, model: str | None = None):
        s = get_settings()
        cfg = local_settings()
        self.base = cfg["url"]
        check_loopback(self.base)
        self.model = model or cfg["model"]
        if not self.model:
            r = local_readiness(self.base, "")
            if not r["ready"]:
                raise provider_error("NOT_CONFIGURED", r["message"])
            self.model = r["model"]
        self.timeout = s.local_ai_timeout_s
        self.max_tokens = s.local_ai_max_tokens

    @property
    def endpoint(self) -> str:
        return f"{self.base}/chat/completions"

    def build_body(self, system: str, user_content: str, *, web_search: bool = False) -> dict:
        return {"model": self.model, "temperature": 0.2, "max_tokens": self.max_tokens, "stream": False,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user_content}]}

    def send(self, body: dict) -> ProviderResult:
        try:
            data = _http_json(self.endpoint, body, {}, self.timeout, "Local AI")
        except ProviderError as e:
            if getattr(e, "kind", "") == "NETWORK":
                raise provider_error("NETWORK", f"The local AI server at {self.base} is not answering. Start LM Studio's server "
                                                "(or Ollama) and load the model, then try again.")
            raise
        ch = (data.get("choices") or [{}])[0]
        text = ((ch.get("message") or {}).get("content") or "")
        text = re.sub(r"(?s)<think>.*?</think>", "", text).strip()  # reasoning models: keep only the answer
        u = data.get("usage") or {}
        return ProviderResult(text, u.get("prompt_tokens"), u.get("completion_tokens"), data.get("model", self.model))


def _dedupe(c: list[dict]) -> list[dict]:
    seen, out = set(), []
    for x in c:
        if x["url"] not in seen:
            seen.add(x["url"])
            out.append(x)
    return out


PROVIDERS = {"anthropic": AnthropicProvider, "gemini": GeminiProvider, "offline-echo": OfflineEchoProvider,
             "local": LocalOpenAIProvider}
CLOUD_PROVIDERS = ("anthropic", "gemini")


def get_provider(name: str | None = None):
    name = name or get_settings().ai_provider
    cls = PROVIDERS.get(name)
    if not cls:
        raise provider_error("NOT_CONFIGURED", f"Unknown AI provider '{name}'.")
    return cls()


def outgoing_text(body: dict) -> str:
    """All human-readable text in a request body, for the final redaction check."""
    if "messages" in body:
        return (body.get("system") or "") + "\n" + "\n".join(
            m["content"] if isinstance(m["content"], str) else json.dumps(m["content"]) for m in body["messages"])
    sys_parts = (body.get("systemInstruction") or {}).get("parts") or []
    parts = [p.get("text", "") for p in sys_parts]
    for c in body.get("contents") or []:
        parts += [p.get("text", "") for p in c.get("parts") or []]
    return "\n".join(parts)
