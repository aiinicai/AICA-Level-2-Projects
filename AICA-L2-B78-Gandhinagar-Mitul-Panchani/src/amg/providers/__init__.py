"""Provider registry with offline enforcement, caching, budgets, and honest reporting."""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel

from amg.config import Settings, get_settings
from amg.models import (
    AssertionType,
    CandidateFact,
    CheckerVerdict,
    EntailmentVerdict,
    ServedBy,
    SourceType,
)
from amg.providers.budget import (
    BudgetExceeded,
    record_live_call,
    record_tokens,
)
from amg.providers.cache import ResponseCache
from amg.providers.embed_base import EmbeddingProvider
from amg.providers.embed_local import LocalEmbeddingProvider
from amg.providers.embed_voyage import VoyageEmbeddingProvider
from amg.providers.llm_base import LLMProvider, ProviderCallResult, ProviderUnavailable
from amg.providers.llm_gemini import GeminiProvider
from amg.providers.llm_stub import StubProvider


logger = logging.getLogger(__name__)
_Result = TypeVar("_Result")
_LAST_REPORT: dict[str, ProviderCallResult] = {}
_LLM_CACHE: tuple[tuple[object, ...], LLMProvider] | None = None
_EMBED_CACHE: tuple[tuple[object, ...], EmbeddingProvider] | None = None
_WORKING_GEMINI_MODEL: str | None = None


@dataclass(frozen=True, slots=True)
class _CallMetadata:
    provider_name: str
    model: str
    served_by: ServedBy


def _record(
    operation: str,
    provider_name: str,
    model: str,
    served_by: ServedBy,
    was_fallback: bool,
) -> None:
    report = ProviderCallResult(
        provider_name=provider_name,
        model=model,
        served_by=served_by,
        was_fallback=was_fallback,
    )
    _LAST_REPORT[operation] = report
    family = "embedding" if operation.startswith("embedding_") else "llm"
    _LAST_REPORT[family] = report


def _json_value(result: object) -> object:
    if isinstance(result, BaseModel):
        return result.model_dump(mode="json")
    if isinstance(result, list):
        return [_json_value(item) for item in result]
    return result


def _gemini_model_chain(configured_model: str) -> tuple[str, ...]:
    candidates = (
        configured_model,
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
    )
    models: list[str] = []
    for model in candidates:
        # These known-ineligible/retired models must never consume another probe.
        if model == "gemini-3.7-flash" or model.startswith("gemini-2.5-"):
            logger.warning("Skipping unsupported/free-tier-ineligible Gemini model %s", model)
            continue
        if model and model not in models:
            models.append(model)
    return tuple(models)


class _CachedBudgetGeminiProvider(LLMProvider):
    """Live Gemini calls with cache lookup and a cap check before every probe."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._models = _gemini_model_chain(settings.gemini_model)
        self._cache = ResponseCache(settings.cache_mode)
        self.last_call: _CallMetadata | None = None

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def model_version(self) -> str:
        if self.last_call is not None:
            return self.last_call.model
        return self._ordered_models()[0]

    def extract_candidates(self, user_text: str) -> list[CandidateFact]:
        result = self._serve(
            "maker",
            {"user_text": user_text},
            lambda provider: provider.extract_candidates(user_text),
            lambda value: [CandidateFact.model_validate(item) for item in value],
        )
        return result

    def check_candidate(
        self,
        content: str,
        assertion_type: AssertionType,
        source_type: SourceType,
    ) -> CheckerVerdict:
        result = self._serve(
            "checker",
            {
                "content": content,
                "assertion_type": assertion_type.value,
                "source_type": source_type.value,
            },
            lambda provider: provider.check_candidate(
                content, assertion_type, source_type
            ),
            CheckerVerdict.model_validate,
        )
        return result

    def check_entailment(
        self, new_fact: str, existing_fact: str
    ) -> EntailmentVerdict:
        result = self._serve(
            "entailment",
            {"new_fact": new_fact, "existing_fact": existing_fact},
            lambda provider: provider.check_entailment(new_fact, existing_fact),
            EntailmentVerdict.model_validate,
        )
        return result

    def _ordered_models(self) -> tuple[str, ...]:
        if _WORKING_GEMINI_MODEL in self._models:
            assert _WORKING_GEMINI_MODEL is not None
            return (_WORKING_GEMINI_MODEL,) + tuple(
                model for model in self._models if model != _WORKING_GEMINI_MODEL
            )
        return self._models

    def _serve(
        self,
        method: str,
        inputs: object,
        call: Callable[[GeminiProvider], _Result],
        decode: Callable[[Any], _Result],
    ) -> _Result:
        global _WORKING_GEMINI_MODEL
        models = self._ordered_models()
        if not models:
            raise ProviderUnavailable("No eligible Gemini models are configured")

        for model in models:
            cached = self._cache.get("gemini", model, method, inputs)
            if cached is not None:
                self.last_call = _CallMetadata("gemini", model, "cache")
                _WORKING_GEMINI_MODEL = model
                return decode(cached)

        if not self._settings.gemini_api_key:
            raise ProviderUnavailable("GEMINI_API_KEY is not configured")

        last_error: ProviderUnavailable | None = None
        for model in models:
            try:
                provider = GeminiProvider(
                    model=model,
                    api_key=self._settings.gemini_api_key,
                    checker_strictness=self._settings.checker_strictness,
                    offline=False,
                )
                record_live_call("gemini", model, self._settings.daily_live_call_cap)
                result = call(provider)
            except ProviderUnavailable as exc:
                last_error = exc
                status_code = getattr(exc, "status_code", None)
                if status_code in {404, 429}:
                    logger.warning(
                        "Gemini model %s returned %s; trying the next eligible model",
                        model,
                        status_code,
                    )
                    continue
                break
            self._cache.put(
                "gemini",
                model,
                method,
                inputs,
                _json_value(result),
                served_by="live",
            )
            self.last_call = _CallMetadata("gemini", model, "live")
            _WORKING_GEMINI_MODEL = model
            return result

        for model in models:
            cached = self._cache.get_fallback("gemini", model, method, inputs)
            if cached is not None:
                logger.warning("Gemini live call failed; serving a pre-warmed real response")
                self.last_call = _CallMetadata("gemini", model, "cache_after_error")
                _WORKING_GEMINI_MODEL = model
                return decode(cached)
        raise ProviderUnavailable("All eligible Gemini models were unavailable") from last_error


class _CachedBudgetVoyageProvider(EmbeddingProvider):
    """Live Voyage calls with the same cache and budget boundary as Gemini."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cache = ResponseCache(settings.cache_mode)
        self.last_call: _CallMetadata | None = None

    @property
    def model_version(self) -> str:
        return self._settings.voyage_model

    @property
    def dimensions(self) -> int:
        return 1024

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            self.last_call = _CallMetadata("local", "no-op", "stub")
            return []
        return self._serve(
            "embedding_documents",
            {"texts": texts, "input_type": "document"},
            lambda provider: provider.embed_documents(texts),
        )

    def embed_query(self, text: str) -> list[float]:
        vectors = self._serve(
            "embedding_query",
            {"texts": [text], "input_type": "query"},
            lambda provider: [provider.embed_query(text)],
        )
        return vectors[0]

    def _serve(
        self,
        method: str,
        inputs: object,
        call: Callable[[VoyageEmbeddingProvider], list[list[float]]],
    ) -> list[list[float]]:
        model = self._settings.voyage_model
        cached = self._cache.get("voyage", model, method, inputs)
        if cached is not None:
            vectors = [[float(value) for value in vector] for vector in cached]
            self.last_call = _CallMetadata("voyage", model, "cache")
            return vectors
        if not self._settings.voyage_api_key:
            raise ProviderUnavailable("VOYAGE_API_KEY is not configured")

        provider = VoyageEmbeddingProvider(
            model=model,
            api_key=self._settings.voyage_api_key,
            offline=False,
        )
        try:
            record_live_call("voyage", model, self._settings.daily_live_call_cap)
            vectors = call(provider)
        except ProviderUnavailable:
            cached = self._cache.get_fallback("voyage", model, method, inputs)
            if cached is None:
                raise
            logger.warning("Voyage live call failed; serving a pre-warmed real response")
            vectors = [[float(value) for value in vector] for vector in cached]
            self.last_call = _CallMetadata("voyage", model, "cache_after_error")
            return vectors
        record_tokens("voyage", model, provider.last_total_tokens)
        self._cache.put(
            "voyage",
            model,
            method,
            inputs,
            vectors,
            served_by="live",
        )
        self.last_call = _CallMetadata("voyage", model, "live")
        return vectors


class _FallbackLLMProvider(LLMProvider):
    def __init__(
        self,
        primary: LLMProvider,
        fallback: StubProvider,
        fallback_enabled: bool,
        default_service: str,
        default_was_fallback: bool,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._fallback_enabled = fallback_enabled
        self._default_service = default_service
        self._default_was_fallback = default_was_fallback
        self._active_name = fallback.name if default_was_fallback else primary.name

    @property
    def name(self) -> str:
        return self._active_name

    def extract_candidates(self, user_text: str) -> list[CandidateFact]:
        return self._serve(
            "maker",
            lambda: self._primary.extract_candidates(user_text),
            lambda: self._fallback.extract_candidates(user_text),
        )

    def check_candidate(
        self,
        content: str,
        assertion_type: AssertionType,
        source_type: SourceType,
    ) -> CheckerVerdict:
        return self._serve(
            "checker",
            lambda: self._primary.check_candidate(content, assertion_type, source_type),
            lambda: self._fallback.check_candidate(content, assertion_type, source_type),
        )

    def check_entailment(
        self, new_fact: str, existing_fact: str
    ) -> EntailmentVerdict:
        return self._serve(
            "entailment",
            lambda: self._primary.check_entailment(new_fact, existing_fact),
            lambda: self._fallback.check_entailment(new_fact, existing_fact),
        )

    def _serve(
        self,
        operation: str,
        primary_call: Callable[[], _Result],
        fallback_call: Callable[[], _Result],
    ) -> _Result:
        try:
            result = primary_call()
            self._active_name = self._primary.name
            metadata = getattr(self._primary, "last_call", None)
            if metadata is None:
                model = "stub-rule-v1"
                service = self._default_service
            else:
                model = metadata.model
                service = metadata.served_by
            _record(
                operation,
                self._primary.name,
                model,
                service,
                self._default_was_fallback,
            )
            return result
        except BudgetExceeded as exc:
            if not self._fallback_enabled:
                raise
            logger.warning(
                "Live-call cap blocked %s for %s; using deterministic stub: %s",
                self._primary.name,
                operation,
                exc,
            )
            result = fallback_call()
            self._active_name = self._fallback.name
            _record(operation, "stub", "stub-rule-v1", "blocked_by_cap", True)
            return result
        except ProviderUnavailable as exc:
            if not self._fallback_enabled:
                raise
            logger.warning(
                "%s unavailable for %s; using deterministic stub: %s",
                self._primary.name,
                operation,
                exc,
            )
            result = fallback_call()
            self._active_name = self._fallback.name
            _record(operation, "stub", "stub-rule-v1", "fallback_after_error", True)
            return result


class _FallbackEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        primary: EmbeddingProvider,
        fallback: LocalEmbeddingProvider,
        fallback_enabled: bool,
        default_service: str,
        default_was_fallback: bool,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._fallback_enabled = fallback_enabled
        self._default_service = default_service
        self._default_was_fallback = default_was_fallback
        self._using_fallback = default_was_fallback

    @property
    def model_version(self) -> str:
        if self._using_fallback:
            return self._fallback.model_version
        return self._primary.model_version

    @property
    def dimensions(self) -> int:
        if self._using_fallback:
            return self._fallback.dimensions
        return self._primary.dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._serve(
            "embedding_documents",
            lambda: self._primary.embed_documents(texts),
            lambda: self._fallback.embed_documents(texts),
        )

    def embed_query(self, text: str) -> list[float]:
        return self._serve(
            "embedding_query",
            lambda: self._primary.embed_query(text),
            lambda: self._fallback.embed_query(text),
        )

    def _serve(
        self,
        operation: str,
        primary_call: Callable[[], _Result],
        fallback_call: Callable[[], _Result],
    ) -> _Result:
        try:
            result = primary_call()
            self._using_fallback = False
            metadata = getattr(self._primary, "last_call", None)
            if metadata is None:
                model = self._primary.model_version
                service = self._default_service
                provider_name = (
                    "local" if self._primary is self._fallback else "voyage"
                )
            else:
                model = metadata.model
                service = metadata.served_by
                provider_name = metadata.provider_name
            _record(
                operation,
                provider_name,
                model,
                service,
                self._default_was_fallback,
            )
            return result
        except BudgetExceeded as exc:
            if not self._fallback_enabled:
                raise
            logger.warning(
                "Live-call cap blocked embeddings for %s; using local embeddings: %s",
                operation,
                exc,
            )
            result = fallback_call()
            self._using_fallback = True
            _record(
                operation,
                "local",
                self._fallback.model_version,
                "blocked_by_cap",
                True,
            )
            return result
        except ProviderUnavailable as exc:
            if not self._fallback_enabled:
                raise
            logger.warning(
                "Embedding provider unavailable for %s; using local embeddings: %s",
                operation,
                exc,
            )
            result = fallback_call()
            self._using_fallback = True
            _record(
                operation,
                "local",
                self._fallback.model_version,
                "fallback_after_error",
                True,
            )
            return result


def _llm_key(settings: Settings) -> tuple[object, ...]:
    return (
        settings.offline,
        settings.llm_provider,
        settings.gemini_api_key,
        settings.gemini_model,
        settings.checker_strictness,
        settings.cache_mode,
        settings.daily_live_call_cap,
    )


def _embed_key(settings: Settings) -> tuple[object, ...]:
    return (
        settings.offline,
        settings.embed_provider,
        settings.voyage_api_key,
        settings.voyage_model,
        settings.cache_mode,
        settings.daily_live_call_cap,
    )


def get_llm_provider() -> LLMProvider:
    """Return an LLM provider without constructing a live backend while offline."""

    global _LLM_CACHE
    settings = get_settings()
    key = _llm_key(settings)
    if _LLM_CACHE is not None and _LLM_CACHE[0] == key:
        return _LLM_CACHE[1]

    stub = StubProvider(settings.checker_strictness)
    if settings.offline:
        blocked = settings.llm_provider == "gemini"
        provider: LLMProvider = _FallbackLLMProvider(
            stub,
            stub,
            False,
            "blocked_offline" if blocked else "stub",
            blocked,
        )
    elif settings.resolved_llm_provider() == "stub":
        provider = _FallbackLLMProvider(stub, stub, False, "stub", False)
    else:
        provider = _FallbackLLMProvider(
            _CachedBudgetGeminiProvider(settings),
            stub,
            True,
            "live",
            False,
        )
    _LLM_CACHE = (key, provider)
    return provider


def get_embedding_provider() -> EmbeddingProvider:
    """Return embeddings without constructing Voyage while offline."""

    global _EMBED_CACHE
    settings = get_settings()
    key = _embed_key(settings)
    if _EMBED_CACHE is not None and _EMBED_CACHE[0] == key:
        return _EMBED_CACHE[1]

    local = LocalEmbeddingProvider()
    if settings.offline:
        blocked = settings.embed_provider == "voyage"
        provider: EmbeddingProvider = _FallbackEmbeddingProvider(
            local,
            local,
            False,
            "blocked_offline" if blocked else "stub",
            blocked,
        )
    elif settings.resolved_embed_provider() == "local":
        provider = _FallbackEmbeddingProvider(local, local, False, "stub", False)
    else:
        provider = _FallbackEmbeddingProvider(
            _CachedBudgetVoyageProvider(settings),
            local,
            True,
            "live",
            False,
        )
    _EMBED_CACHE = (key, provider)
    return provider


def last_provider_report() -> dict[str, dict[str, object]]:
    """Return a copy of per-operation reports for honest UI display."""

    return {
        operation: report.model_dump(mode="json")
        for operation, report in _LAST_REPORT.items()
    }


def reset_provider_state(*, clear_working_model: bool = False) -> None:
    """Clear process-local registries; tests use this to prevent state leakage."""

    global _LLM_CACHE, _EMBED_CACHE, _WORKING_GEMINI_MODEL
    _LLM_CACHE = None
    _EMBED_CACHE = None
    _LAST_REPORT.clear()
    if clear_working_model:
        _WORKING_GEMINI_MODEL = None


def test_provider_connections() -> dict[str, dict[str, object]]:
    """Make at most one small, budgeted live request per configured provider."""

    settings = get_settings()
    results: dict[str, dict[str, object]] = {}
    if not settings.gemini_api_key:
        results["gemini"] = {
            "configured": False,
            "attempted": False,
            "success": False,
            "message": "Not configured; no call was made.",
        }
    else:
        try:
            provider = GeminiProvider(
                model=settings.gemini_model,
                api_key=settings.gemini_api_key,
                checker_strictness=settings.checker_strictness,
                offline=False,
            )
            record_live_call(
                "gemini", settings.gemini_model, settings.daily_live_call_cap
            )
            provider.check_entailment(
                "The connection test is active.",
                "The connection test is active.",
            )
            results["gemini"] = {
                "configured": True,
                "attempted": True,
                "success": True,
                "model": settings.gemini_model,
                "message": "Gemini connection succeeded.",
            }
        except BudgetExceeded as exc:
            results["gemini"] = {
                "configured": True,
                "attempted": False,
                "success": False,
                "model": settings.gemini_model,
                "message": f"Gemini test blocked by the daily budget cap: {exc}",
            }
        except ProviderUnavailable as exc:
            results["gemini"] = {
                "configured": True,
                "attempted": True,
                "success": False,
                "model": settings.gemini_model,
                "message": f"Gemini connection failed: {exc}",
            }

    if not settings.voyage_api_key:
        results["voyage"] = {
            "configured": False,
            "attempted": False,
            "success": False,
            "message": "Not configured; no call was made.",
        }
    else:
        try:
            provider = VoyageEmbeddingProvider(
                model=settings.voyage_model,
                api_key=settings.voyage_api_key,
                offline=False,
            )
            record_live_call(
                "voyage", settings.voyage_model, settings.daily_live_call_cap
            )
            provider.embed_query("AI Memory Governance connection test")
            record_tokens("voyage", settings.voyage_model, provider.last_total_tokens)
            results["voyage"] = {
                "configured": True,
                "attempted": True,
                "success": True,
                "model": settings.voyage_model,
                "message": "Voyage connection succeeded.",
            }
        except BudgetExceeded as exc:
            results["voyage"] = {
                "configured": True,
                "attempted": False,
                "success": False,
                "model": settings.voyage_model,
                "message": f"Voyage test blocked by the daily budget cap: {exc}",
            }
        except ProviderUnavailable as exc:
            results["voyage"] = {
                "configured": True,
                "attempted": True,
                "success": False,
                "model": settings.voyage_model,
                "message": f"Voyage connection failed: {exc}",
            }
    return results


def cosine(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity in plain Python so retrieval math stays visible."""

    if len(a) != len(b):
        raise ValueError("cosine vectors must have the same dimensions")
    dot_product = sum(left * right for left, right in zip(a, b, strict=True))
    magnitude_a = math.sqrt(sum(value * value for value in a))
    magnitude_b = math.sqrt(sum(value * value for value in b))
    if magnitude_a == 0.0 or magnitude_b == 0.0:
        return 0.0
    return dot_product / (magnitude_a * magnitude_b)


__all__ = [
    "ProviderCallResult",
    "ProviderUnavailable",
    "cosine",
    "get_embedding_provider",
    "get_llm_provider",
    "last_provider_report",
    "reset_provider_state",
    "test_provider_connections",
]
