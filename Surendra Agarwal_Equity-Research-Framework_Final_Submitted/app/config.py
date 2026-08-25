"""Centralized application configuration.

Loads from environment variables / a `.env` file via pydantic-settings.
No secrets are ever hard-coded here — see .env.example for the full list
of supported variables. Import `get_settings()` (cached) rather than
constructing `Settings()` directly, so the whole app shares one instance.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.exceptions import ConfigurationError

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ScoreWeights(BaseSettings):
    """Module 9 investment-score component weights.

    Loaded as part of Settings; validated to sum to 1.0 (within floating
    point tolerance) so a misconfigured .env fails fast at startup rather
    than silently producing a distorted score.
    """

    fundamentals: float = 0.30
    cashflow_quality: float = 0.15
    business_management: float = 0.15
    valuation: float = 0.20
    technical: float = 0.10
    risk_governance: float = 0.10

    def as_dict(self) -> dict[str, float]:
        return {
            "fundamentals": self.fundamentals,
            "cashflow_quality": self.cashflow_quality,
            "business_management": self.business_management,
            "valuation": self.valuation,
            "technical": self.technical,
            "risk_governance": self.risk_governance,
        }


class Settings(BaseSettings):
    """Application-wide settings, sourced from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---
    app_env: str = "development"
    log_level: str = "INFO"
    log_dir: Path = _PROJECT_ROOT / "logs"

    # --- Directories ---
    data_raw_dir: Path = _PROJECT_ROOT / "data" / "raw"
    data_processed_dir: Path = _PROJECT_ROOT / "data" / "processed"
    data_sample_dir: Path = _PROJECT_ROOT / "data" / "sample"
    reports_dir: Path = _PROJECT_ROOT / "reports"

    # --- AI provider (OpenAI / ChatGPT) ---
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"
    # Deliberate pacing delay (seconds) between sequential batch LLM
    # calls (e.g. per-page document analysis). Reduces how often a real
    # OpenAI account's rate limit gets hit in the first place — see
    # app/ai/rate_limiting.py's module docstring for the real incident
    # that motivated this. Increase via LLM_REQUEST_DELAY_SECONDS in
    # .env if you're on a lower-tier account and still see frequent
    # retries; decrease (even to 0) on a high-tier account for speed.
    llm_request_delay_seconds: float = 0.5
    openai_max_tokens: int = 4096

    # --- AI provider (Google Gemini) ---
    # Added so a capstone submission can run entirely on Gemini's free
    # tier (Flash/Flash-Lite models — public-document analysis only,
    # since free-tier content is used by Google to improve their
    # products, per Gemini API's own terms) without requiring the
    # evaluator to use or be billed against the project owner's own
    # OpenAI key. Gemini is tried first when both keys are configured;
    # OpenAI is an automatic fallback if a live Gemini call fails (see
    # get_default_llm_client() in app/ai/llm_client.py) — never the
    # reverse, and never used to choose "whichever is cheaper" or any
    # other criterion beyond "did the primary call actually fail."
    google_api_key: str | None = None
    # Google retires/restricts specific Gemini model IDs for new API
    # keys surprisingly fast — "gemini-2.5-flash-lite" (this project's
    # original default) returned a live 404 "no longer available to new
    # users" within about a month of being set. If you hit a similar
    # 404, check the CURRENT free-tier model list at
    # https://ai.google.dev/gemini-api/docs/pricing before assuming
    # anything else is broken, and override via GEMINI_MODEL in .env
    # rather than editing this default (which may itself go stale).
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_max_tokens: int = 4096

    # --- Market data ---
    market_data_provider: str = "csv"
    csv_price_history_path: Path | None = None

    # --- Score weights ---
    weight_fundamentals: float = 0.30
    weight_cashflow_quality: float = 0.15
    weight_business_management: float = 0.15
    weight_valuation: float = 0.20
    weight_technical: float = 0.10
    weight_risk_governance: float = 0.10

    @model_validator(mode="after")
    def _weights_sum_to_one(self) -> "Settings":
        total = (
            self.weight_fundamentals
            + self.weight_cashflow_quality
            + self.weight_business_management
            + self.weight_valuation
            + self.weight_technical
            + self.weight_risk_governance
        )
        if abs(total - 1.0) > 1e-6:
            raise ConfigurationError(
                f"Investment score weights must sum to 1.0, got {total:.4f}. "
                "Check WEIGHT_* variables in your .env file."
            )
        return self

    @property
    def score_weights(self) -> dict[str, float]:
        return {
            "fundamentals": self.weight_fundamentals,
            "cashflow_quality": self.weight_cashflow_quality,
            "business_management": self.weight_business_management,
            "valuation": self.weight_valuation,
            "technical": self.weight_technical,
            "risk_governance": self.weight_risk_governance,
        }

    def require_openai_key(self) -> str:
        """Call this from the AI layer (never from Layers 1-4) before
        making a live API call. Raises a clear, fatal ConfigurationError
        rather than letting a downstream SDK call fail with an opaque
        401."""
        if not self.openai_api_key:
            raise ConfigurationError(
                "OPENAI_API_KEY is not set. Add it to your .env file "
                "(see .env.example) before running AI-interpretation steps. "
                "The deterministic analysis layers do not require this key."
            )
        return self.openai_api_key

    def require_google_key(self) -> str:
        """Same contract as require_openai_key(), for the Gemini provider."""
        if not self.google_api_key:
            raise ConfigurationError(
                "GOOGLE_API_KEY is not set. Add it to your .env file "
                "(see .env.example) before running AI-interpretation steps. "
                "The deterministic analysis layers do not require this key."
            )
        return self.google_api_key

    def require_any_llm_key(self) -> None:
        """Call this from the UI layer before offering an AI-assisted
        action, instead of require_openai_key()/require_google_key()
        directly — since either provider being configured is sufficient
        (Gemini first if both are set; see get_default_llm_client()).
        Raises a clear, fatal ConfigurationError only if NEITHER key is set."""
        if not self.google_api_key and not self.openai_api_key:
            raise ConfigurationError(
                "Neither GOOGLE_API_KEY nor OPENAI_API_KEY is set. Add at "
                "least one to your .env file (see .env.example) before "
                "running AI-interpretation steps. The deterministic "
                "analysis layers do not require either key."
            )

    def ensure_directories(self) -> None:
        """Create all configured working directories if they don't exist."""
        for d in (
            self.log_dir,
            self.data_raw_dir,
            self.data_processed_dir,
            self.data_sample_dir,
            self.reports_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor. Use this everywhere instead of
    instantiating Settings() directly, so the whole process shares one
    validated configuration object."""
    return Settings()
