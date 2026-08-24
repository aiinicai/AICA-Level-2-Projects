"""Inspectable disk cache for successful responses from real providers only."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from amg.config import writable_app_path


CACHE_DIR = writable_app_path(".amg_cache")
logger = logging.getLogger(__name__)
_READ_MODES = frozenset({"read_write", "read_only"})
_WRITE_MODES = frozenset({"live_first", "read_write", "refresh"})
_ENTRIES_WRITTEN = 0


def canonical_json(value: object) -> str:
    """Return the stable JSON representation used in cache identities."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def cache_key(provider: str, model: str, method: str, inputs: object) -> str:
    """Hash exactly the provider, model, method, and canonicalized inputs."""

    material = "|".join((provider, model, method, canonical_json(inputs)))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class ResponseCache:
    """One atomic, human-inspectable JSON file per successful live response."""

    def __init__(self, mode: str, directory: Path | None = None) -> None:
        self.mode = mode
        self.directory = directory if directory is not None else CACHE_DIR

    def get(
        self, provider: str, model: str, method: str, inputs: object
    ) -> Any | None:
        """Return a verified real-provider cache entry when reads are enabled."""

        if self.mode not in _READ_MODES:
            return None
        return self._read_verified(provider, model, method, inputs)

    def _read_verified(
        self, provider: str, model: str, method: str, inputs: object
    ) -> Any | None:
        key = cache_key(provider, model, method, inputs)
        path = self.directory / f"{key}.json"
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return None
        if (
            entry.get("key") != key
            or entry.get("provider") != provider
            or entry.get("model") != model
            or entry.get("method") != method
            or entry.get("served_by") != "live"
        ):
            return None
        return entry.get("response")

    def get_fallback(
        self, provider: str, model: str, method: str, inputs: object
    ) -> Any | None:
        """Read a pre-warmed response only after a live-first attempt failed."""

        if self.mode != "live_first":
            return None
        return self._read_verified(provider, model, method, inputs)

    def put(
        self,
        provider: str,
        model: str,
        method: str,
        inputs: object,
        response: object,
        *,
        served_by: str,
    ) -> None:
        """Persist only genuine live responses; failed and stub calls never arrive here."""

        if self.mode not in _WRITE_MODES:
            return
        if served_by != "live":
            raise ValueError("Only genuine live provider responses may be cached")
        global _ENTRIES_WRITTEN
        key = cache_key(provider, model, method, inputs)
        entry = {
            "key": key,
            "provider": provider,
            "model": model,
            "method": method,
            "inputs": inputs,
            "served_by": served_by,
            "created_at": datetime.now(UTC).isoformat(),
            "response": response,
        }
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            handle = tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.directory,
                prefix=f".{key}.",
                suffix=".tmp",
                delete=False,
            )
            temporary_path = Path(handle.name)
            try:
                with handle:
                    json.dump(entry, handle, sort_keys=True, indent=2, ensure_ascii=False)
                    handle.write("\n")
                os.replace(temporary_path, self.directory / f"{key}.json")
                _ENTRIES_WRITTEN += 1
            finally:
                if temporary_path.exists():
                    temporary_path.unlink()
        except OSError as exc:
            # Cache persistence is a quota optimization, never a reason to lose
            # an otherwise valid live response or crash the demo.
            logger.warning("Could not persist provider cache entry: %s", exc)


def cache_entry_count(directory: Path | None = None) -> int:
    """Count inspectable cache entries without creating the cache directory."""

    target = directory if directory is not None else CACHE_DIR
    if not target.is_dir():
        return 0
    return sum(1 for path in target.glob("*.json") if path.is_file())


def cache_write_count() -> int:
    """Return successful cache-file writes made by this process."""

    return _ENTRIES_WRITTEN
