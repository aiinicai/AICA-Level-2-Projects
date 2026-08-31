"""Provider boundary for stored-document and retrieval-query embeddings."""

from __future__ import annotations

from abc import ABC, abstractmethod

from amg.providers.llm_base import ProviderUnavailable

__all__ = ["EmbeddingProvider", "ProviderUnavailable"]


class EmbeddingProvider(ABC):
    """Common contract implemented by live and deterministic embeddings."""

    @property
    @abstractmethod
    def model_version(self) -> str:
        """Return the model identifier stored beside each vector."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the exact vector width produced by this provider."""

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed stored memory content, batching where supported."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed one contextual-retrieval query."""
