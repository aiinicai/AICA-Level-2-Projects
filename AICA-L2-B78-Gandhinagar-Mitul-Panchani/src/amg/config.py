"""Environment-driven configuration for the governance layer."""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final

from dotenv import load_dotenv


MAX_CONTEXTUAL_TOP_K: Final[int] = 6
REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
_VALID_CHECKER_STRICTNESS: Final[frozenset[str]] = frozenset(
    {"lenient", "balanced", "strict"}
)
_VALID_CACHE_MODES: Final[frozenset[str]] = frozenset(
    {"live_first", "read_write", "read_only", "off", "refresh"}
)
logger = logging.getLogger(__name__)


def is_frozen() -> bool:
    """Return whether PyInstaller is currently hosting the process."""

    return bool(getattr(sys, "frozen", False))


def user_data_dir() -> Path:
    """Return the durable writable root without changing source-mode paths."""

    if not is_frozen():
        return REPO_ROOT
    local_app_data = os.getenv("LOCALAPPDATA")
    base = (
        Path(local_app_data)
        if local_app_data and local_app_data.strip()
        else Path.home() / "AppData" / "Local"
    )
    directory = base / "AIMemoryGovernance"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def bundled_src_dir() -> Path:
    """Resolve read-only package resources in source and one-file modes."""

    if is_frozen():
        bundle_root = getattr(sys, "_MEIPASS", None)
        if bundle_root:
            return Path(bundle_root)
    return REPO_ROOT / "src"


def settings_file_path() -> Path:
    """Return the external recipient settings file location."""

    return user_data_dir() / "settings.json"


def writable_app_path(filename: str) -> Path:
    """Keep a named application artifact durable when running frozen."""

    return user_data_dir() / filename


def _load_environment() -> None:
    """Load a local .env when present without replacing process variables."""

    # A frozen application must never discover or depend on a bundled .env.
    if is_frozen():
        return
    dotenv_path = REPO_ROOT / ".env"
    if dotenv_path.is_file():
        load_dotenv(dotenv_path=dotenv_path, override=False)


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    return value.strip()


def _int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().casefold()
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    raise ValueError(f"{name} must be one of: 1, true, yes, 0, false, no")


def _float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated settings loaded from environment variables."""

    offline: bool = True
    llm_provider: str = "gemini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash"
    embed_provider: str = "voyage"
    voyage_api_key: str | None = None
    voyage_model: str = "voyage-4-lite"
    contextual_top_k: int = MAX_CONTEXTUAL_TOP_K
    contradiction_min_confidence: float = 0.70
    checker_strictness: str = "balanced"
    export_passphrase: str = "capstone-demo-2026"
    db_path: str = "amg_memory.db"
    cache_mode: str = "live_first"
    daily_live_call_cap: int = 100

    def __post_init__(self) -> None:
        if self.llm_provider not in {"gemini", "stub"}:
            raise ValueError("llm_provider must be 'gemini' or 'stub'")
        if self.embed_provider not in {"voyage", "local"}:
            raise ValueError("embed_provider must be 'voyage' or 'local'")
        # P0 rule 4 is a boundary, not a tunable high-water mark.
        if not 1 <= self.contextual_top_k <= MAX_CONTEXTUAL_TOP_K:
            raise ValueError(
                f"contextual_top_k must be between 1 and {MAX_CONTEXTUAL_TOP_K}"
            )
        if not 0.0 <= self.contradiction_min_confidence <= 1.0:
            raise ValueError("contradiction_min_confidence must be between 0 and 1")
        if self.checker_strictness not in _VALID_CHECKER_STRICTNESS:
            raise ValueError(
                "checker_strictness must be one of: lenient, balanced, strict"
            )
        if self.cache_mode not in _VALID_CACHE_MODES:
            raise ValueError(
                "cache_mode must be one of: live_first, read_write, read_only, off, refresh"
            )
        if self.daily_live_call_cap < 0:
            raise ValueError("daily_live_call_cap must be zero or greater")

    def resolved_llm_provider(self) -> str:
        """Return the provider that can actually serve an LLM request."""

        if self.offline:
            return "stub"
        if self.llm_provider == "gemini" and not self.gemini_api_key:
            return "stub"
        return self.llm_provider

    def resolved_embed_provider(self) -> str:
        """Return the provider that can actually serve an embedding request."""

        if self.offline:
            return "local"
        if self.embed_provider == "voyage" and not self.voyage_api_key:
            return "local"
        return self.embed_provider


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache validated application settings."""

    _load_environment()
    from amg.settings_store import load_provider_settings

    saved = load_provider_settings(settings_file_path())
    environment_gemini_key = _optional_env("GEMINI_API_KEY")
    environment_voyage_key = _optional_env("VOYAGE_API_KEY")
    environment_model = os.getenv("AMG_GEMINI_MODEL", "gemini-3.5-flash").strip()
    offline_env_is_explicit = os.getenv("AMG_OFFLINE") is not None
    environment_offline = _bool_env("AMG_OFFLINE", True)
    offline = environment_offline
    gemini_key = environment_gemini_key
    voyage_key = environment_voyage_key
    gemini_model = environment_model
    if saved is not None:
        # An explicit AMG_OFFLINE=true remains a process-wide network kill switch.
        offline = (
            True
            if offline_env_is_explicit and environment_offline
            else saved.offline
        )
        gemini_key = saved.gemini_api_key
        voyage_key = saved.voyage_api_key
        gemini_model = saved.gemini_model

    db_value = os.getenv("AMG_DB_PATH", "amg_memory.db")
    db_path = str(writable_app_path(Path(db_value).name)) if is_frozen() else db_value
    settings = Settings(
        offline=offline,
        llm_provider=os.getenv("AMG_LLM_PROVIDER", "gemini").strip().lower(),
        gemini_api_key=gemini_key,
        gemini_model=gemini_model,
        embed_provider=os.getenv("AMG_EMBED_PROVIDER", "voyage").strip().lower(),
        voyage_api_key=voyage_key,
        voyage_model=os.getenv("AMG_VOYAGE_MODEL", "voyage-4-lite").strip(),
        contextual_top_k=_int_env("AMG_CONTEXTUAL_TOP_K", MAX_CONTEXTUAL_TOP_K),
        contradiction_min_confidence=_float_env(
            "AMG_CONTRADICTION_MIN_CONFIDENCE", 0.70
        ),
        checker_strictness=os.getenv(
            "AMG_CHECKER_STRICTNESS", "balanced"
        ).strip().lower(),
        export_passphrase=os.getenv(
            "AMG_EXPORT_PASSPHRASE", "capstone-demo-2026"
        ),
        db_path=db_path,
        cache_mode=os.getenv("AMG_CACHE_MODE", "live_first").strip().lower(),
        daily_live_call_cap=_int_env("AMG_DAILY_LIVE_CALL_CAP", 100),
    )
    logger.info(
        "AMG provider mode: %s (LLM=%s, embeddings=%s, cache=%s)",
        "offline" if settings.offline else "live-enabled",
        settings.resolved_llm_provider(),
        settings.resolved_embed_provider(),
        settings.cache_mode,
    )
    return settings
