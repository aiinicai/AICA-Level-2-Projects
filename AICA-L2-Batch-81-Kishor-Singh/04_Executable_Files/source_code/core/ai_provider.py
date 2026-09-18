"""Provider-agnostic AI adapter for document intelligence features.

Every AI Assistant feature (classification, summarization, structured
extraction, Ask Document) goes through this one module, which supports
four backends behind a single interface:

* Anthropic (Claude)  -- cloud
* OpenAI (GPT)         -- cloud
* Google Gemini        -- cloud
* Ollama               -- local, fully offline

Design choices, deliberately:

* Plain HTTP via ``requests`` rather than each vendor's SDK. This keeps the
  dependency footprint small, avoids SDK version churn, and means the same
  thin adapter pattern works for every provider.
* **No network call happens anywhere in this codebase unless a caller
  explicitly invokes** :meth:`AIProvider.complete`. Nothing here runs in the
  background, on a timer, or as a side effect of opening a document.
* API keys are never written to ``settings.json`` or logged. They are
  stored via the OS credential store (``keyring`` -> Windows Credential
  Manager on this platform) and read back only for the duration of a call.
* A provider/model combination is either configured (key present) or not;
  every caller must handle "not configured" as a first-class state, not an
  exception to work around.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import requests

from utils.logging_utils import get_logger
from utils.validation import ValidationError

logger = get_logger("ai_provider")

KEYRING_SERVICE = "CADocuFlowAI"
_REQUEST_TIMEOUT_SECONDS = 60


class AIProviderKind(str, Enum):
    ANTHROPIC = "Anthropic (Claude)"
    OPENAI = "OpenAI (GPT)"
    GEMINI = "Google Gemini"
    OLLAMA = "Ollama (Local, Offline)"


#: Sensible starting defaults, all user-editable in Settings -> AI Assistant.
#: Provider model catalogs change over time -- always confirm the current
#: model name against the provider's own documentation before relying on it.
DEFAULT_MODELS: dict[AIProviderKind, str] = {
    AIProviderKind.ANTHROPIC: "claude-sonnet-5",
    AIProviderKind.OPENAI: "gpt-4o-mini",
    AIProviderKind.GEMINI: "gemini-2.0-flash",
    AIProviderKind.OLLAMA: "llama3",
}

#: Ollama runs entirely on the user's machine -- no API key or internet
#: connection required, which is why it is the only provider usable in a
#: fully offline / confidentiality-sensitive setup.
CLOUD_PROVIDERS = {AIProviderKind.ANTHROPIC, AIProviderKind.OPENAI, AIProviderKind.GEMINI}


class AIProviderError(ValidationError):
    """Raised for any AI-call failure: missing key, network error, bad response."""


@dataclass
class AIRequest:
    system_prompt: str
    user_prompt: str
    max_tokens: int = 4000
    temperature: float = 0.0  # deterministic by default -- extraction should not be creative


@dataclass
class AIResponse:
    text: str
    provider: AIProviderKind
    model: str


# ------------------------------------------------------------- key storage
def save_api_key(provider: AIProviderKind, api_key: str) -> None:
    import keyring

    keyring.set_password(KEYRING_SERVICE, provider.value, api_key)
    logger.info("API key saved for provider %s", provider.value)


def get_api_key(provider: AIProviderKind) -> str | None:
    import keyring

    try:
        return keyring.get_password(KEYRING_SERVICE, provider.value)
    except Exception:  # noqa: BLE001 - keyring backend issues shouldn't crash the app
        logger.warning("Could not read API key from OS credential store for %s", provider.value)
        return None


def delete_api_key(provider: AIProviderKind) -> None:
    import keyring

    try:
        keyring.delete_password(KEYRING_SERVICE, provider.value)
    except Exception:  # noqa: BLE001
        pass


def is_configured(provider: AIProviderKind) -> bool:
    if provider == AIProviderKind.OLLAMA:
        return True  # no key needed; availability is checked via a live ping instead
    return bool(get_api_key(provider))


def ping_ollama(base_url: str = "http://localhost:11434") -> bool:
    """Check whether a local Ollama server is reachable (does not prove a model is pulled)."""
    try:
        resp = requests.get(f"{base_url}/api/tags", timeout=3)
        return resp.status_code == 200
    except requests.RequestException:
        return False


# ------------------------------------------------------------- the adapter
class AIProvider:
    """Facade used by every AI Assistant feature. One instance per call is fine -- stateless."""

    def __init__(self, kind: AIProviderKind, model: str | None = None, ollama_base_url: str = "http://localhost:11434"):
        self.kind = kind
        self.model = model or DEFAULT_MODELS[kind]
        self.ollama_base_url = ollama_base_url

    def complete(self, request: AIRequest) -> AIResponse:
        if self.kind in CLOUD_PROVIDERS and not is_configured(self.kind):
            raise AIProviderError(
                f"{self.kind.value} is not configured. Add an API key in "
                "Settings -> AI Assistant before using this feature."
            )
        try:
            if self.kind == AIProviderKind.ANTHROPIC:
                return self._call_anthropic(request)
            if self.kind == AIProviderKind.OPENAI:
                return self._call_openai(request)
            if self.kind == AIProviderKind.GEMINI:
                return self._call_gemini(request)
            return self._call_ollama(request)
        except requests.Timeout as exc:
            raise AIProviderError(f"{self.kind.value} did not respond in time. Please try again.") from exc
        except requests.ConnectionError as exc:
            hint = " Is Ollama running (`ollama serve`)?" if self.kind == AIProviderKind.OLLAMA else " Check your internet connection."
            raise AIProviderError(f"Could not reach {self.kind.value}.{hint}") from exc

    # ---------------------------------------------------------- Anthropic
    def _call_anthropic(self, request: AIRequest) -> AIResponse:
        api_key = get_api_key(self.kind)
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "system": request.system_prompt,
                "messages": [{"role": "user", "content": request.user_prompt}],
            },
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        self._raise_for_status(resp)
        data = resp.json()
        text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
        return AIResponse(text=text, provider=self.kind, model=self.model)

    # ------------------------------------------------------------ OpenAI
    def _call_openai(self, request: AIRequest) -> AIResponse:
        api_key = get_api_key(self.kind)
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
            json={
                "model": self.model,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "messages": [
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.user_prompt},
                ],
            },
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        self._raise_for_status(resp)
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        return AIResponse(text=text, provider=self.kind, model=self.model)

    # ------------------------------------------------------------ Gemini
    def _call_gemini(self, request: AIRequest) -> AIResponse:
        api_key = get_api_key(self.kind)
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            params={"key": api_key},
            headers={"content-type": "application/json"},
            json={
                "system_instruction": {"parts": [{"text": request.system_prompt}]},
                "contents": [{"parts": [{"text": request.user_prompt}]}],
                "generationConfig": {"temperature": request.temperature, "maxOutputTokens": request.max_tokens},
            },
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        self._raise_for_status(resp)
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return AIResponse(text=text, provider=self.kind, model=self.model)

    # ------------------------------------------------------------ Ollama
    def _call_ollama(self, request: AIRequest) -> AIResponse:
        resp = requests.post(
            f"{self.ollama_base_url}/api/generate",
            json={
                "model": self.model,
                "system": request.system_prompt,
                "prompt": request.user_prompt,
                "stream": False,
                "options": {"temperature": request.temperature},
            },
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        self._raise_for_status(resp)
        data = resp.json()
        return AIResponse(text=data.get("response", ""), provider=self.kind, model=self.model)

    @staticmethod
    def _raise_for_status(resp: requests.Response) -> None:
        if resp.ok:
            return
        try:
            detail = resp.json()
        except ValueError:
            detail = resp.text[:300]
        raise AIProviderError(f"AI provider returned an error (HTTP {resp.status_code}): {detail}")
