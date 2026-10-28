"""Thin wrapper around the Gemini API. Anything callable as llm(system, prompt) -> str works,
which is how the tests substitute a fake."""
from __future__ import annotations

import os
import time

# A named, stable model rather than the "-latest" alias: the alias moves to preview models whose free daily quota is tiny
# (20 requests a day was seen), so a few runs exhaust it.
DEFAULT_MODEL = "gemini-2.5-flash"
# If the chosen model is busy (503 high demand, 504 deadline, 429 quota), try these in turn. Checked live against the API.
FALLBACK_MODELS = ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3-flash-preview"]
TIMEOUT_MS = 120_000


def is_busy(error: Exception) -> bool:
    """A temporary capacity problem on Google's side, worth retrying or moving to another model."""
    t = str(error)
    return any(k in t for k in ("503", "504", "429", "UNAVAILABLE", "DEADLINE", "RESOURCE_EXHAUSTED", "overloaded", "high demand"))


def daily_quota_spent(error: Exception) -> bool:
    """The free-tier requests-per-day limit of this model is used up: waiting seconds will not help, so move on at once."""
    t = str(error)
    return "429" in t and "PerDay" in t


def models_to_try(model: str) -> list:
    return [model] + [m for m in FALLBACK_MODELS if m != model]


def generate_with_fallback(client, model: str, contents: str, config, attempts: int = 2, pause=time.sleep):
    """(text, model used). Each model is tried `attempts` times when busy, then the next; any other error is raised at once."""
    last = None
    for name in models_to_try(model):
        for attempt in range(attempts):
            try:
                return client.models.generate_content(model=name, contents=contents, config=config).text or "", name
            except Exception as e:  # noqa: BLE001
                last = e
                if not is_busy(e):
                    raise
                if daily_quota_spent(e):
                    break                      # this model is finished for the day; try the next one
                pause(2 * (attempt + 1))
    raise last


class LLMError(RuntimeError):
    pass


class GeminiLLM:
    def __init__(self, api_key: str | None = None, model: str | None = None, retries: int = 3):
        key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not key:
            raise LLMError("No Gemini API key. Set GEMINI_API_KEY in .env or pass it in.")
        from google import genai
        from google.genai import types
        self._client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=TIMEOUT_MS))
        self.model = model or os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
        self.retries = retries

    def __call__(self, system: str, prompt: str) -> str:
        from google.genai import types
        cfg = types.GenerateContentConfig(system_instruction=system, temperature=0.2, response_mime_type="application/json")
        try:
            text, used = generate_with_fallback(self._client, self.model, prompt, cfg, self.retries)
        except Exception as e:  # network, quota, safety: report
            raise LLMError(f"Gemini request failed: {e}") from e
        self.model_used = used
        return text
