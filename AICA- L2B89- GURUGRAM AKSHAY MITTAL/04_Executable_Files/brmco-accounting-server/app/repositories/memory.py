"""In-memory repository used in Phase 1 and in tests."""
from __future__ import annotations

import copy
import threading
from typing import Any

from app.repositories.base import DocumentRepository


class InMemoryRepository(DocumentRepository):
    def __init__(self) -> None:
        self._docs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get(self, doc_id: str) -> dict[str, Any] | None:
        with self._lock:
            doc = self._docs.get(doc_id)
            return copy.deepcopy(doc) if doc is not None else None

    def list(self, filters: dict[str, Any] | None = None, limit: int = 100) -> list[dict[str, Any]]:
        filters = filters or {}
        with self._lock:
            matches = [
                copy.deepcopy(d) for d in self._docs.values()
                if all(d.get(k) == v for k, v in filters.items())
            ]
        return matches[:limit]

    def upsert(self, doc_id: str, document: dict[str, Any]) -> dict[str, Any]:
        stored = {**copy.deepcopy(document), "_id": doc_id}
        with self._lock:
            self._docs[doc_id] = stored
        return copy.deepcopy(stored)

    def delete(self, doc_id: str) -> bool:
        with self._lock:
            return self._docs.pop(doc_id, None) is not None
