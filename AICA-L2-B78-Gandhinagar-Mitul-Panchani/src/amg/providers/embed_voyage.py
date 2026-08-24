"""Voyage AI embeddings using the verified Phase 2 API shape."""

from __future__ import annotations

import os
from typing import Any

from amg.config import get_settings
from amg.providers.embed_base import EmbeddingProvider, ProviderUnavailable

try:
    import voyageai
except Exception:  # pragma: no cover - exercised only when an optional package is absent
    voyageai = None  # type: ignore[assignment]


class VoyageEmbeddingProvider(EmbeddingProvider):
    """Live Voyage backend; every provider failure is converted for fallback."""

    def __init__(
        self,
        model: str = "voyage-4-lite",
        api_key: str | None = None,
        dimensions: int = 1024,
        offline: bool | None = None,
    ) -> None:
        # The process-wide kill switch cannot be bypassed by a constructor arg.
        offline_mode = get_settings().offline or offline is True
        if offline_mode:
            raise ProviderUnavailable("Voyage construction blocked by AMG_OFFLINE")
        self._model = model
        self._dimensions = dimensions
        self._api_key = api_key or os.getenv("VOYAGE_API_KEY")
        self._client: Any | None = None
        self.last_total_tokens: int | None = None
        if self._api_key and voyageai is None:
            raise ProviderUnavailable("voyageai is not installed")
        if self._api_key:
            try:
                # Recipient keys live in settings.json rather than process env.
                self._client = voyageai.Client(api_key=self._api_key)
            except Exception as exc:
                raise ProviderUnavailable("Voyage client initialization failed") from exc

    @property
    def model_version(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._embed(texts, input_type="document")

    def embed_query(self, text: str) -> list[float]:
        vectors = self._embed([text], input_type="query")
        return vectors[0]

    def _embed(self, texts: list[str], input_type: str) -> list[list[float]]:
        if not self._api_key:
            raise ProviderUnavailable("VOYAGE_API_KEY is not configured")
        if self._client is None:
            raise ProviderUnavailable("Voyage client is unavailable")
        try:
            result = self._client.embed(
                texts,
                model=self._model,
                input_type=input_type,
            )
            total_tokens = getattr(result, "total_tokens", None)
            self.last_total_tokens = (
                int(total_tokens) if isinstance(total_tokens, (int, float)) else None
            )
            vectors = [[float(value) for value in vector] for vector in result.embeddings]
            if len(vectors) != len(texts):
                raise ValueError("Voyage returned an unexpected number of vectors")
            if any(len(vector) != self.dimensions for vector in vectors):
                raise ValueError("Voyage returned an unexpected vector width")
            return vectors
        except ProviderUnavailable:
            raise
        except Exception as exc:
            raise ProviderUnavailable("Voyage embedding request failed") from exc
