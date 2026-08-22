"""LLM client abstraction — Layer 5 foundation.

Everything in app/ai/* talks to an LLMClient, never to a concrete SDK
directly. This is what makes the provider swap (Anthropic -> OpenAI,
per the person's decision) a one-file change, and what makes automated
testing possible without live API calls or costs — every test in this
codebase uses FakeLLMClient, never OpenAIClient.

HONEST STATUS: this sandbox's network egress is restricted to package
registries (PyPI/npm/GitHub) and does not include api.openai.com, so
OpenAIClient below is verified for import correctness, error handling
shape, and prompt/response plumbing, but has NOT been exercised against
a live API call in this environment. Its first live test will need to
happen on the person's machine with a real OPENAI_API_KEY.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from pydantic import BaseModel

from app.config import get_settings
from app.core.exceptions import LLMProviderError

logger = logging.getLogger(__name__)


class LLMResponse(BaseModel):
    text: str
    model: str
    finish_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class LLMClient(ABC):
    """Interface every LLM provider implementation must satisfy."""

    @abstractmethod
    def complete(
        self, *, system: str, user: str, max_tokens: int | None = None, temperature: float = 0.2,
    ) -> LLMResponse:
        """Single-turn completion. `system` carries the task instructions;
        `user` carries the actual request, which may itself embed
        clearly-delimited document data (see app/ai/prompts.py) — this
        method does no prompt construction itself, it only sends what
        it's given and returns what comes back."""


class OpenAIClient(LLMClient):
    """Provider using the OpenAI Python SDK (ChatGPT models)."""

    def __init__(self, model: str | None = None, max_tokens: int | None = None) -> None:
        settings = get_settings()
        settings.require_openai_key()  # fails fast with a clear message if unset
        self._model = model or settings.openai_model
        self._max_tokens = max_tokens or settings.openai_max_tokens

    def complete(
        self, *, system: str, user: str, max_tokens: int | None = None, temperature: float = 0.2,
    ) -> LLMResponse:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMProviderError(
                "openai package is not installed. Run: pip install openai"
            ) from exc

        settings = get_settings()
        client = OpenAI(api_key=settings.require_openai_key())

        try:
            response = client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens or self._max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except Exception as exc:  # network, rate limit, auth, malformed response — all recoverable
            raise LLMProviderError(f"OpenAI API call failed: {exc}") from exc

        choice = response.choices[0]
        text = choice.message.content or ""
        prompt_tokens = response.usage.prompt_tokens if response.usage else None
        completion_tokens = response.usage.completion_tokens if response.usage else None
        return LLMResponse(
            text=text, model=response.model, finish_reason=choice.finish_reason,
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
        )


class GeminiClient(LLMClient):
    """Provider using Google's `google-genai` SDK (Gemini models).

    Added so a capstone submission can be evaluated entirely on
    Gemini's free tier (Flash/Flash-Lite) without requiring the
    evaluator to use or be billed against the project owner's own
    OpenAI key. Uses the current GA `google-genai` package
    (`from google import genai`) — NOT the deprecated
    `google-generativeai` package, which Google's own PyPI listing
    explicitly marks as superseded.
    """

    def __init__(self, model: str | None = None, max_tokens: int | None = None) -> None:
        settings = get_settings()
        settings.require_google_key()
        self._model = model or settings.gemini_model
        self._max_tokens = max_tokens or settings.gemini_max_tokens

    def complete(
        self, *, system: str, user: str, max_tokens: int | None = None, temperature: float = 0.2,
    ) -> LLMResponse:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise LLMProviderError(
                "google-genai package is not installed. Run: pip install google-genai"
            ) from exc

        settings = get_settings()
        client = genai.Client(
            api_key=settings.require_google_key(),
            http_options=types.HttpOptions(
                # The google-genai SDK has its OWN internal retry-with-
                # backoff hidden inside generate_content() — up to 4
                # attempts by default, backoff capped at 60s EACH. On a
                # rate-limited free-tier account, this silently absorbed
                # up to ~3 minutes per call before ever raising an
                # exception back to our code — a real user hit this
                # exact scenario (consistent ~2m51s gaps between calls
                # in their logs). That defeated the whole point of
                # FallbackLLMClient: it can only fall back to OpenAI
                # AFTER Gemini's own internal retry loop gives up, so a
                # "fast fallback" took minutes instead of seconds.
                # attempts=1 disables the SDK's internal retry entirely
                # — a rate-limit or transient error now raises
                # immediately, letting THIS project's own pacing
                # (delay_seconds in the batch functions) and fallback
                # (FallbackLLMClient) logic — already built, tested, and
                # under our control — handle recovery instead, the way
                # they were actually designed to.
                retry_options=types.HttpRetryOptions(attempts=1),
                timeout=30_000,  # 30s per-call cap, milliseconds
            ),
        )

        try:
            response = client.models.generate_content(
                model=self._model,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=max_tokens or self._max_tokens,
                    temperature=temperature,
                ),
            )
        except Exception as exc:  # network, rate limit (common on free tier), auth, malformed response
            raise LLMProviderError(f"Gemini API call failed: {exc}") from exc

        text = response.text or ""
        finish_reason = None
        if response.candidates:
            finish_reason = getattr(response.candidates[0], "finish_reason", None)
            finish_reason = finish_reason.name if hasattr(finish_reason, "name") else finish_reason
        prompt_tokens = None
        completion_tokens = None
        if response.usage_metadata is not None:
            prompt_tokens = response.usage_metadata.prompt_token_count
            completion_tokens = response.usage_metadata.candidates_token_count
        return LLMResponse(
            text=text, model=self._model, finish_reason=finish_reason,
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
        )


def infer_provider_label(model: str | None) -> str:
    """Pure function: guess a human-readable provider name from a model
    string, for display purposes only (e.g. in a cost-tracking table) —
    not used anywhere that affects actual routing/fallback logic."""
    if model is None:
        return "Unknown"
    if model.startswith("gemini-"):
        return "Gemini"
    if model.startswith("gpt-") or model.startswith(("o1", "o3", "o4")):
        return "OpenAI"
    return "Unknown"


class UsageTrackingLLMClient(LLMClient):
    """Wraps another LLMClient, recording token usage and estimated
    cost for every call into a shared list the caller supplies —
    without this module (or any of app/ai/*) needing a Streamlit
    dependency. The UI layer wires the list into st.session_state;
    this class and app/ai/pricing.py stay fully framework-agnostic and
    independently testable.

    Provider is inferred from the ACTUAL model name in each response
    (via infer_provider_label), not a fixed label supplied at
    construction time — this matters specifically when wrapping a
    FallbackLLMClient, where which provider serves a given call is
    decided dynamically per-call, not once for the whole session.
    """

    def __init__(self, inner: LLMClient, usage_log: list[dict]) -> None:
        self._inner = inner
        self._usage_log = usage_log

    def complete(
        self, *, system: str, user: str, max_tokens: int | None = None, temperature: float = 0.2,
    ) -> LLMResponse:
        from datetime import datetime, timezone
        from app.ai.pricing import estimate_cost_usd

        response = self._inner.complete(
            system=system, user=user, max_tokens=max_tokens, temperature=temperature,
        )
        cost = estimate_cost_usd(response.model, response.prompt_tokens, response.completion_tokens)
        self._usage_log.append({
            "timestamp": datetime.now(timezone.utc),
            "provider": infer_provider_label(response.model),
            "model": response.model,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "estimated_cost_usd": cost,
        })
        return response


class FallbackLLMClient(LLMClient):
    """Wraps a primary and secondary LLMClient: tries primary first,
    and ONLY on an LLMProviderError (the generic wrapper every provider
    in this module raises for any API failure — auth, rate limit,
    network, malformed response) falls back to secondary. Never the
    reverse, and never used to pick "whichever is cheaper" or any
    criterion other than "did the primary call actually fail."

    Built specifically for the Gemini-free-tier-primary,
    OpenAI-paid-backup arrangement (see get_default_llm_client()) — a
    capstone evaluator can run entirely on the free Gemini tier, with
    OpenAI only ever invoked (and only ever billed to the project
    owner) if Gemini's free-tier rate limit is hit or a call otherwise
    fails.
    """

    def __init__(self, primary: LLMClient, secondary: LLMClient) -> None:
        self._primary = primary
        self._secondary = secondary

    def complete(
        self, *, system: str, user: str, max_tokens: int | None = None, temperature: float = 0.2,
    ) -> LLMResponse:
        try:
            return self._primary.complete(
                system=system, user=user, max_tokens=max_tokens, temperature=temperature,
            )
        except LLMProviderError as exc:
            logger.warning(
                "Primary LLM provider (%s) failed, falling back to secondary (%s): %s",
                type(self._primary).__name__, type(self._secondary).__name__, exc,
            )
            return self._secondary.complete(
                system=system, user=user, max_tokens=max_tokens, temperature=temperature,
            )


class FakeLLMClient(LLMClient):
    """Deterministic test double. NEVER makes a network call.

    Two modes:
    - Fixed response: construct with `fixed_response=...` to always
      return the same text regardless of input.
    - Scripted responses: construct with `responses=[...]` to return
      each in order across successive calls (raises if exhausted).

    Every call is recorded in `.calls` (list of {"system", "user",
    "max_tokens", "temperature"}) so tests can assert on exactly what
    was sent to the "model" — including verifying document text was
    properly delimited as data, not concatenated into the system prompt.
    """

    def __init__(
        self, *, fixed_response: str | None = None, responses: list[str] | None = None,
        model_name: str = "fake-model",
        prompt_tokens: int | None = None, completion_tokens: int | None = None,
    ) -> None:
        if fixed_response is None and not responses:
            raise ValueError("FakeLLMClient requires either fixed_response or responses.")
        self._fixed_response = fixed_response
        self._responses = list(responses) if responses else None
        self._model_name = model_name
        self._prompt_tokens = prompt_tokens
        self._completion_tokens = completion_tokens
        self.calls: list[dict] = []

    def complete(
        self, *, system: str, user: str, max_tokens: int | None = None, temperature: float = 0.2,
    ) -> LLMResponse:
        self.calls.append({"system": system, "user": user, "max_tokens": max_tokens, "temperature": temperature})

        if self._fixed_response is not None:
            text = self._fixed_response
        else:
            if not self._responses:
                raise LLMProviderError("FakeLLMClient: scripted responses exhausted.")
            text = self._responses.pop(0)

        return LLMResponse(
            text=text, model=self._model_name, finish_reason="stop",
            prompt_tokens=self._prompt_tokens, completion_tokens=self._completion_tokens,
        )


def get_default_llm_client() -> LLMClient:
    """Provider selection: Gemini first (if GOOGLE_API_KEY is set),
    OpenAI as an automatic fallback (if OPENAI_API_KEY is also set) via
    FallbackLLMClient — never the reverse. If only one key is set, that
    provider is used alone. Raises ConfigurationError if neither is set
    (via the individual client constructors' require_*_key() calls).

    This ordering exists specifically so a capstone evaluator can run
    entirely on Gemini's free tier without needing (or being billed
    against) the project owner's own OpenAI key — OpenAI is only ever
    invoked if a live Gemini call actually fails.
    """
    settings = get_settings()
    has_google = bool(settings.google_api_key)
    has_openai = bool(settings.openai_api_key)

    if has_google and has_openai:
        return FallbackLLMClient(primary=GeminiClient(), secondary=OpenAIClient())
    if has_google:
        return GeminiClient()
    if has_openai:
        return OpenAIClient()
    # Neither configured — this always raises ConfigurationError
    # (google_api_key is None in this branch by construction above).
    settings.require_google_key()
