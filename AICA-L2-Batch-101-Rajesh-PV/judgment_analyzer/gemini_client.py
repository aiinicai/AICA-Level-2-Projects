"""Thin wrapper around the official Google Gen AI SDK (``google-genai``).

Responsibilities:
* create the client from a user-supplied key (never hard-coded),
* translate SDK / network exceptions into friendly ``GeminiError`` subclasses,
* retry transient failures (rate limits, 5xx, timeouts) with exponential backoff
  while remaining responsive to user cancellation.
"""

from __future__ import annotations

import logging
import random
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from .pdf_processor import CancelledError

log = logging.getLogger(__name__)

StatusFn = Callable[[str], None]


# ---------------------------------------------------------------- errors ---
class GeminiError(Exception):
    """Base class; ``str(exc)`` is a user-friendly message."""

    retryable = False


class InvalidApiKeyError(GeminiError):
    pass


class PermissionDeniedError(GeminiError):
    pass


class ModelNotFoundError(GeminiError):
    pass


class RateLimitError(GeminiError):
    """429 / RESOURCE_EXHAUSTED. ``kind`` is 'minute', 'daily', 'no_free_quota' or 'unknown'.
    Only per-minute (and unknown) limits are worth retrying."""

    def __init__(self, message: str, kind: str = "unknown", retry_after: float | None = None):
        super().__init__(message)
        self.kind = kind
        self.retry_after = retry_after
        self.retryable = kind in ("minute", "unknown")


class TokenLimitError(GeminiError):
    pass


class ServiceUnavailableError(GeminiError):
    retryable = True


class NetworkError(GeminiError):
    retryable = True


class ContentBlockedError(GeminiError):
    pass


class EmptyResponseError(GeminiError):
    retryable = True


class BadRequestError(GeminiError):
    pass


def translate_exception(exc: BaseException, model: str = "") -> GeminiError:
    """Map SDK / transport exceptions to friendly ``GeminiError`` instances."""
    if isinstance(exc, GeminiError):
        return exc

    try:
        from google.genai import errors as genai_errors
    except ImportError:  # pragma: no cover
        genai_errors = None

    if genai_errors is not None and isinstance(exc, genai_errors.APIError):
        code = getattr(exc, "code", 0) or 0
        status = (getattr(exc, "status", "") or "").upper()
        message = str(getattr(exc, "message", "") or exc)
        low = message.lower()
        if "api key" in low or "api_key" in low or status == "UNAUTHENTICATED" or code == 401:
            return InvalidApiKeyError(
                "Gemini rejected the API key. Check that it was copied correctly and is active in Google AI Studio."
            )
        if code == 403 or status == "PERMISSION_DENIED":
            return PermissionDeniedError(
                "This API key does not have permission to use the Gemini API or this model. "
                "Check the key's project and API restrictions in Google AI Studio / Cloud Console."
            )
        if code == 404 or status == "NOT_FOUND":
            return ModelNotFoundError(
                f"The model '{model}' was not found or is not available to this key. "
                "Choose another model in Settings or click 'Refresh models'."
            )
        if code == 429 or status == "RESOURCE_EXHAUSTED":
            return rate_limit_error(getattr(exc, "details", None), message, model)
        if code == 400 and ("token" in low and ("exceed" in low or "too long" in low or "limit" in low)):
            return TokenLimitError(
                "The document is too large for a single request to this model. "
                "It will be processed in smaller sections."
            )
        if code == 400 and ("safety" in low or "blocked" in low):
            return ContentBlockedError("Gemini declined to process this content under its safety policy.")
        if code >= 500 or status in {"UNAVAILABLE", "INTERNAL", "DEADLINE_EXCEEDED"}:
            return ServiceUnavailableError(
                "The Gemini service is temporarily unavailable or overloaded. Retrying may help."
            )
        return BadRequestError(f"Gemini API error ({code} {status}): {message[:300]}")

    # Transport-level errors (httpx is used by the SDK).
    try:
        import httpx

        if isinstance(exc, httpx.TimeoutException):
            return NetworkError("The request to Gemini timed out. Check your connection; the app will retry.")
        if isinstance(exc, httpx.TransportError):
            return NetworkError("Could not reach the Gemini API. Check your internet connection or proxy settings.")
    except ImportError:  # pragma: no cover
        pass
    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        return NetworkError("Could not reach the Gemini API. Check your internet connection or proxy settings.")
    return GeminiError(f"Unexpected error while contacting Gemini: {exc}")


def _walk(obj):
    """Yield every dict nested anywhere inside ``obj``."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def _parse_seconds(value) -> float | None:
    try:
        return float(str(value).strip().rstrip("s"))
    except (TypeError, ValueError):
        return None


def rate_limit_error(details, message: str = "", model: str = "") -> RateLimitError:
    """Classify a 429 using Google's QuotaFailure / RetryInfo details when present."""
    quota_ids: list[str] = []
    zero_quota = False
    retry_after = None
    for d in _walk(details):
        qid = d.get("quotaId") or d.get("quota_id") or d.get("quotaMetric") or ""
        if qid:
            quota_ids.append(str(qid))
            if str(d.get("quotaValue", d.get("quota_value", ""))).strip() == "0":
                zero_quota = True
        if "retryDelay" in d:
            retry_after = _parse_seconds(d["retryDelay"])
    text = (" ".join(quota_ids) + " " + (message or "")).lower()
    free = "freetier" in text.replace("_", "").replace("-", "")
    tier = "free-tier " if free else ""
    name = f"'{model}'" if model else "this model"

    if zero_quota or "limit: 0" in text:
        return RateLimitError(
            f"Your API key has no {tier}quota for {name}. Choose another model (for example "
            "'gemini-3.5-flash-lite' or 'gemini-2.5-flash') with the ↻ button, or enable billing on the "
            "key's Google Cloud project.", kind="no_free_quota")
    if "perday" in text or "per_day" in text or "per day" in text:
        return RateLimitError(
            f"The daily {tier}request limit for {name} has been used up. It resets at midnight Pacific time "
            "(early afternoon IST). Try another model now, or enable billing for higher limits.",
            kind="daily")
    if "perminute" in text or "per_minute" in text or "per minute" in text:
        what = "tokens" if "token" in text else "requests"
        hint = (" A large judgment can exceed the per-minute token allowance on its own - turn on "
                "'Always process section by section'." if what == "tokens" else "")
        return RateLimitError(
            f"Per-minute {tier}{what} limit reached for {name}; waiting and retrying automatically.{hint}",
            kind="minute", retry_after=retry_after)
    return RateLimitError(
        f"Gemini rate limit or quota reached for {name}; retrying automatically. If this keeps happening, "
        "check your limits in Google AI Studio or choose another model.", kind="unknown", retry_after=retry_after)


# ---------------------------------------------------------------- client ---
@dataclass
class GenerationResult:
    text: str
    truncated: bool = False
    input_tokens: int | None = None
    output_tokens: int | None = None
    sources: list = None  # [(title, uri)] when Google Search grounding was used


class GeminiClient:
    """Synchronous Gemini client used from a worker thread."""

    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float | None = None,
        max_output_tokens: int = 32_768,
        timeout_s: int = 300,
        max_retries: int = 4,
        client: Any | None = None,
    ) -> None:
        if not api_key:
            raise InvalidApiKeyError("No Gemini API key has been provided.")
        self.model = model
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.max_retries = max_retries
        if client is not None:  # dependency injection for tests
            self._client = client
        else:
            from google import genai
            from google.genai import types

            self._client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=int(timeout_s * 1000)),  # milliseconds
            )

    # -- utilities -----------------------------------------------------------
    def test_connection(self) -> str:
        """Validate key + model with a lightweight metadata call. Returns a status message."""
        try:
            info = self._client.models.get(model=self.model)
        except Exception as exc:
            raise translate_exception(exc, self.model) from exc
        limit = getattr(info, "input_token_limit", None)
        extra = f" (input limit about {limit:,} tokens)" if isinstance(limit, int) else ""
        return f"API key is valid. Model '{self.model}' is available{extra}."

    def input_token_limit(self) -> int | None:
        try:
            limit = getattr(self._client.models.get(model=self.model), "input_token_limit", None)
            return limit if isinstance(limit, int) else None
        except Exception:
            return None

    def list_text_models(self) -> list[str]:
        """Return model IDs that support generateContent, newest-looking first."""
        try:
            names = []
            for m in self._client.models.list():
                actions = getattr(m, "supported_actions", None) or []
                name = (getattr(m, "name", "") or "").removeprefix("models/")
                if name.startswith("gemini") and (not actions or "generateContent" in actions):
                    if not any(t in name for t in ("tts", "image", "embedding", "live", "audio", "transcribe")):
                        names.append(name)
        except Exception as exc:
            raise translate_exception(exc, self.model) from exc
        return sorted(set(names), reverse=True)

    # -- generation ----------------------------------------------------------
    def generate(
        self,
        prompt: str,
        system_instruction: str,
        cancel_event: threading.Event | None = None,
        on_status: StatusFn | None = None,
        json_mode: bool = False,
        max_output_tokens: int | None = None,
        web_search: bool = False,
    ) -> GenerationResult:
        from google.genai import types

        options: dict[str, Any] = {
            "system_instruction": system_instruction,
            "max_output_tokens": max_output_tokens or self.max_output_tokens,
        }
        # None = use the model's own default temperature. Google recommends the default (1.0) for
        # Gemini 3 models; lower values can cause looping or degraded output on those models.
        if self.temperature is not None:
            options["temperature"] = self.temperature
        if json_mode:
            options["response_mime_type"] = "application/json"
        if web_search:  # Grounding with Google Search (used only for the optional citation lookup)
            options["tools"] = [types.Tool(google_search=types.GoogleSearch())]
        config = types.GenerateContentConfig(**options)
        attempt = 0
        while True:
            _check_cancel(cancel_event)
            try:
                response = self._client.models.generate_content(model=self.model, contents=prompt, config=config)
                return self._read_response(response)
            except Exception as exc:  # noqa: BLE001 - translated below
                error = translate_exception(exc, self.model)
                if not error.retryable or attempt >= self.max_retries:
                    log.error("Gemini request failed: %s", error)
                    raise error from exc
                attempt += 1
                delay = min(60.0, (2 ** attempt) * (3.0 if isinstance(error, RateLimitError) else 1.5))
                if isinstance(error, RateLimitError) and error.retry_after:
                    delay = min(90.0, error.retry_after + 1.0)  # honour Google's suggested wait
                delay += random.uniform(0, 1.0)
                log.warning("Transient Gemini error (%s). Retry %d/%d in %.0fs.",
                            type(error).__name__, attempt, self.max_retries, delay)
                if on_status:
                    on_status(f"{error} Next attempt in {delay:.0f}s ({attempt}/{self.max_retries}).")
                _sleep_with_cancel(delay, cancel_event)

    @staticmethod
    def _read_response(response: Any) -> GenerationResult:
        feedback = getattr(response, "prompt_feedback", None)
        if feedback is not None and getattr(feedback, "block_reason", None):
            raise ContentBlockedError(
                f"Gemini blocked the request ({feedback.block_reason}). The document could not be analysed."
            )
        candidates = getattr(response, "candidates", None) or []
        finish = str(getattr(candidates[0], "finish_reason", "") or "") if candidates else ""
        try:
            text = response.text or ""
        except Exception:  # .text can raise when no text part exists
            text = ""
        if not text.strip():
            if "SAFETY" in finish or "PROHIBITED" in finish or "BLOCKLIST" in finish:
                raise ContentBlockedError("Gemini stopped the response under its safety policy.")
            raise EmptyResponseError("Gemini returned an empty response.")
        usage = getattr(response, "usage_metadata", None)
        sources = []
        try:
            meta = getattr(candidates[0], "grounding_metadata", None) if candidates else None
            for chunk in (getattr(meta, "grounding_chunks", None) or []):
                web = getattr(chunk, "web", None)
                if web is not None and getattr(web, "uri", None):
                    sources.append((getattr(web, "title", "") or getattr(web, "domain", "") or "", web.uri))
        except Exception:  # grounding metadata is optional
            pass
        return GenerationResult(
            sources=sources,
            text=text,
            truncated="MAX_TOKENS" in finish,
            input_tokens=getattr(usage, "prompt_token_count", None) if usage else None,
            output_tokens=getattr(usage, "candidates_token_count", None) if usage else None,
        )


def _check_cancel(cancel_event: threading.Event | None) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise CancelledError()


def _sleep_with_cancel(seconds: float, cancel_event: threading.Event | None) -> None:
    end = time.monotonic() + seconds
    while (remaining := end - time.monotonic()) > 0:
        _check_cancel(cancel_event)
        time.sleep(min(0.25, remaining))
