"""Stable, offline character n-gram embeddings for the demo fallback."""

from __future__ import annotations

import hashlib
import math
import re

from amg.providers.embed_base import EmbeddingProvider


class LocalEmbeddingProvider(EmbeddingProvider):
    """Deterministic hashed character n-grams with no network dependency."""

    _DIMENSIONS = 256

    @property
    def model_version(self) -> str:
        return "local-hash-v1"

    @property
    def dimensions(self) -> int:
        return self._DIMENSIONS

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        normalized = re.sub(r"\s+", " ", text.casefold()).strip()
        padded = f"  {normalized}  "
        vector = [0.0] * self.dimensions

        for width in (3, 4, 5):
            for start in range(max(0, len(padded) - width + 1)):
                ngram = padded[start : start + width].encode("utf-8")
                digest = hashlib.sha256(ngram).digest()
                index = int.from_bytes(digest[:4], "big") % self.dimensions
                sign = 1.0 if digest[4] & 1 else -1.0
                vector[index] += sign

        magnitude = math.sqrt(sum(component * component for component in vector))
        if magnitude == 0.0:
            return vector
        return [component / magnitude for component in vector]
