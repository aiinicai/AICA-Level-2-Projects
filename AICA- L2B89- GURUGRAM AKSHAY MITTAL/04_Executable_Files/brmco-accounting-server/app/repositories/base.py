"""Repository interfaces.

Services depend on these abstract classes only. Phase 1 ships an in-memory
implementation; Phase 5 adds a MongoDB implementation behind the same interface,
selected by the REPOSITORY_BACKEND environment variable.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DocumentRepository(ABC):
    """Minimal document-store contract that maps naturally onto a MongoDB collection."""

    @abstractmethod
    def get(self, doc_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def list(self, filters: dict[str, Any] | None = None, limit: int = 100) -> list[dict[str, Any]]: ...

    @abstractmethod
    def upsert(self, doc_id: str, document: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def delete(self, doc_id: str) -> bool: ...
