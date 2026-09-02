"""Plain-text recipient settings stored outside the frozen application bundle.

This capstone deliberately does not pretend to be a credential manager. The
web UI makes the plain-text limitation visible before a recipient saves keys.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"


@dataclass(frozen=True, slots=True)
class StoredProviderSettings:
    """The small, versioned settings document written by the recipient."""

    gemini_api_key: str | None
    voyage_api_key: str | None
    gemini_model: str = DEFAULT_GEMINI_MODEL
    offline: bool = True


def _clean_secret(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def load_provider_settings(path: Path) -> StoredProviderSettings | None:
    """Load a settings override, returning ``None`` when none was saved."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        # An unreadable credential file must fail closed to deterministic mode.
        return StoredProviderSettings(None, None, offline=True)
    if not isinstance(value, dict):
        return StoredProviderSettings(None, None, offline=True)
    gemini_key = _clean_secret(value.get("gemini_api_key"))
    voyage_key = _clean_secret(value.get("voyage_api_key"))
    raw_model = value.get("gemini_model")
    model = (
        raw_model.strip()
        if isinstance(raw_model, str) and raw_model.strip()
        else DEFAULT_GEMINI_MODEL
    )
    return StoredProviderSettings(
        gemini_api_key=gemini_key,
        voyage_api_key=voyage_key,
        gemini_model=model,
        # A hand-edited file with no usable keys must never claim live mode.
        offline=(
            not bool(gemini_key or voyage_key)
            or bool(value.get("offline", False))
        ),
    )


def save_provider_settings(
    path: Path,
    *,
    gemini_api_key: str | None,
    voyage_api_key: str | None,
    gemini_model: str = DEFAULT_GEMINI_MODEL,
) -> StoredProviderSettings:
    """Atomically persist recipient-owned keys in the external data directory."""

    gemini_key = _clean_secret(gemini_api_key)
    voyage_key = _clean_secret(voyage_api_key)
    model = gemini_model.strip() or DEFAULT_GEMINI_MODEL
    stored = StoredProviderSettings(
        gemini_api_key=gemini_key,
        voyage_api_key=voyage_key,
        gemini_model=model,
        offline=not bool(gemini_key or voyage_key),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    temporary_path = Path(handle.name)
    try:
        with handle:
            json.dump(
                {
                    "version": 1,
                    "offline": stored.offline,
                    "gemini_api_key": stored.gemini_api_key,
                    "voyage_api_key": stored.voyage_api_key,
                    "gemini_model": stored.gemini_model,
                },
                handle,
                sort_keys=True,
                indent=2,
            )
            handle.write("\n")
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return stored


def clear_provider_settings(path: Path) -> StoredProviderSettings:
    """Remove both keys while retaining an explicit offline override."""

    return save_provider_settings(
        path,
        gemini_api_key=None,
        voyage_api_key=None,
        gemini_model=DEFAULT_GEMINI_MODEL,
    )
