"""Central configuration. All secrets come from the environment (or a local .env
file that must never be committed). Nothing sensitive is hard-coded here."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# NOTICEMATE_NO_DOTENV=1 (set by scripts/test_workspace.py) keeps the real .env — and any keys in it —
# out of the isolated fictional test instance.
if os.getenv("NOTICEMATE_NO_DOTENV") != "1":
    try:  # python-dotenv is optional
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:  # pragma: no cover
        pass


def _bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


PACKAGE_DIR = Path(__file__).resolve().parent.parent
STATIC_DATA_DIR = PACKAGE_DIR / "data"

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".xlsm", ".csv", ".txt", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}


@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("NOTICEMATE_DATA_DIR", "./workspace")).resolve())
    max_upload_mb: int = field(default_factory=lambda: _int("NOTICEMATE_MAX_UPLOAD_MB", 25))
    session_hours: int = field(default_factory=lambda: _int("NOTICEMATE_SESSION_HOURS", 8))
    max_failed_logins: int = field(default_factory=lambda: _int("NOTICEMATE_MAX_FAILED_LOGINS", 5))
    encryption_key: str | None = field(default_factory=lambda: os.getenv("NOTICEMATE_ENCRYPTION_KEY") or None)

    # AI provider — disabled unless explicitly enabled AND a key is present
    ai_enabled: bool = field(default_factory=lambda: _bool("NOTICEMATE_AI_ENABLED", False))
    ai_provider: str = field(default_factory=lambda: os.getenv("NOTICEMATE_AI_PROVIDER", "anthropic"))
    anthropic_api_key: str | None = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY") or None)
    anthropic_model: str = field(default_factory=lambda: os.getenv("NOTICEMATE_ANTHROPIC_MODEL", "claude-sonnet-5-5"))
    anthropic_base_url: str = field(default_factory=lambda: os.getenv("NOTICEMATE_ANTHROPIC_BASE_URL", "https://api.anthropic.com"))
    ai_max_tokens: int = field(default_factory=lambda: _int("NOTICEMATE_AI_MAX_TOKENS", 4000))
    ai_timeout_s: int = field(default_factory=lambda: _int("NOTICEMATE_AI_TIMEOUT_S", 120))
    ai_max_payload_chars: int = field(default_factory=lambda: _int("NOTICEMATE_AI_MAX_PAYLOAD_CHARS", 60000))
    anthropic_web_search: bool = field(default_factory=lambda: _bool("NOTICEMATE_ANTHROPIC_WEB_SEARCH", False))
    gemini_api_key: str | None = field(default_factory=lambda: os.getenv("GEMINI_API_KEY") or None)
    gemini_model: str = field(default_factory=lambda: os.getenv("NOTICEMATE_GEMINI_MODEL", "gemini-3.8-flash"))
    gemini_base_url: str = field(default_factory=lambda: os.getenv("NOTICEMATE_GEMINI_BASE_URL", "https://generativelanguage.googleapis.com"))
    gemini_grounding: bool = field(default_factory=lambda: _bool("NOTICEMATE_GEMINI_GROUNDING", False))
    offline_echo_response: str | None = None  # tests only
    # Local AI (LM Studio / Ollama on this computer). Off until the CA turns it on in Settings.
    local_ai_url: str = field(default_factory=lambda: os.getenv("NOTICEMATE_LOCAL_AI_URL", "http://127.0.0.1:1234/v1"))
    local_ai_model: str = field(default_factory=lambda: os.getenv("NOTICEMATE_LOCAL_AI_MODEL", ""))
    local_ai_timeout_s: int = field(default_factory=lambda: _int("NOTICEMATE_LOCAL_AI_TIMEOUT_S", 600))
    local_ai_max_tokens: int = field(default_factory=lambda: _int("NOTICEMATE_LOCAL_AI_MAX_TOKENS", 2500))
    retain_ai_payloads: bool = field(default_factory=lambda: _bool("NOTICEMATE_RETAIN_AI_PAYLOADS", False))

    api_host: str = field(default_factory=lambda: os.getenv("NOTICEMATE_API_HOST", "127.0.0.1"))
    api_port: int = field(default_factory=lambda: _int("NOTICEMATE_API_PORT", 8000))
    ui_origin: str = field(default_factory=lambda: os.getenv("NOTICEMATE_UI_ORIGIN", "http://localhost:8501"))
    log_level: str = field(default_factory=lambda: os.getenv("NOTICEMATE_LOG_LEVEL", "INFO"))

    @property
    def db_path(self) -> Path:
        return self.data_dir / "noticemate.db"

    @property
    def docs_dir(self) -> Path:
        return self.data_dir / "documents"

    @property
    def exports_dir(self) -> Path:
        return self.data_dir / "exports"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.docs_dir, self.exports_dir, self.logs_dir):
            d.mkdir(parents=True, exist_ok=True)
            try:
                os.chmod(d, 0o700)
            except OSError:  # pragma: no cover (Windows)
                pass


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.ensure_dirs()
    return _settings


def reset_settings(**overrides) -> Settings:
    """Used by tests and scripts to rebuild settings (e.g. new data dir)."""
    global _settings
    _settings = Settings(**overrides)
    _settings.ensure_dirs()
    return _settings


GEMINI_DISCLOSURE = (
    "Gemini (optional) uses the Google Gemini API with a separate GEMINI_API_KEY from Google AI Studio / Google Cloud; "
    "API usage, quotas and data-handling terms are governed by Google's API terms, not by any consumer subscription."
)

SUBSCRIPTION_DISCLOSURE = (
    "IMPORTANT: A Claude Pro (or Max/Team) subscription does NOT include Anthropic API usage. "
    "AI features in NOTICE-MATE use the Anthropic API, which requires a separate API account and key "
    "from the Anthropic Console and is billed separately per token. NOTICE-MATE works fully offline "
    "(without AI) if no API key is configured."
)
