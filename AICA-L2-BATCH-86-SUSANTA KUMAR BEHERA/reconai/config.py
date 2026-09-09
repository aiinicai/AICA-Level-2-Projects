import json
import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


def get_app_base_dir() -> Path:
    """
    Get the absolute directory where the application binary or main project resides.
    If running as a packaged PyInstaller executable, returns the directory of the .exe.
    If running in development/source mode, returns the root project directory.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def get_default_config_path() -> Path:
    return get_app_base_dir() / "config.json"


def get_default_db_path() -> str:
    return str(get_app_base_dir() / "reconai.db")


CONFIG_FILE_PATH = get_default_config_path()


class ReconciliationConfig(BaseModel):
    """Configuration parameters for reconciliation rules and tolerances."""
    date_tolerance_days: int = Field(default=3, ge=0, le=30, description="Allowed date difference in days for matches")
    amount_tolerance: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), description="Allowed amount discrepancy tolerance")
    fuzzy_narration_threshold: float = Field(default=75.0, ge=0.0, le=100.0, description="Minimum similarity ratio (0-100) for fuzzy matching")
    enable_ai_matcher: bool = Field(default=True, description="Enable AI fallback for complex narration matching")
    ai_model: str = Field(default="gemini-2.5-flash", description="AI model name (Claude or Gemini)")
    api_key: Optional[str] = Field(default=None, description="API Key for AI analysis")

    # Backward-compatible property aliases
    @property
    def gemini_api_key(self) -> Optional[str]:
        return self.api_key

    @gemini_api_key.setter
    def gemini_api_key(self, val: Optional[str]):
        self.api_key = val


class AuditConfig(BaseModel):
    """Configuration parameters for expense audit rules."""
    duplicate_date_window_days: int = Field(default=3, ge=0, le=30, description="Date window to flag potential duplicate entries")
    round_amount_threshold: Decimal = Field(default=Decimal("25000.00"), ge=Decimal("0.00"), description="Flag round amounts greater than or equal to this threshold")
    high_value_approval_threshold: Decimal = Field(default=Decimal("50000.00"), ge=Decimal("0.00"), description="Expenses above this require an approver reference")
    flag_weekend_transactions: bool = Field(default=True, description="Flag expenses incurred on Saturday or Sunday")
    enable_gst_tds_compliance: bool = Field(default=True, description="Enable GSTIN format and TDS section validation (India-specific)")
    approved_vendors: list[str] = Field(default_factory=list, description="Approved vendor list for supplier compliance")
    enable_ai_audit: bool = Field(default=True, description="Enable AI semantic anomaly analysis for narrations")


class AppConfig(BaseModel):
    """Master application configuration."""
    reconciliation: ReconciliationConfig = Field(default_factory=ReconciliationConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    theme: str = Field(default="dark", description="'dark' or 'light'")
    db_path: str = Field(default="reconai.db", description="Path to local SQLite database")

    def get_resolved_db_path(self) -> str:
        """Resolve db_path to an absolute, reliable path based on the app's base directory."""
        p = Path(self.db_path)
        if not p.is_absolute():
            return str(get_app_base_dir() / p)
        return str(p)

    def save_to_file(self, file_path: Optional[Path] = None):
        target = file_path or get_default_config_path()
        try:
            with open(target, "w", encoding="utf-8") as f:
                f.write(self.model_dump_json(indent=2))
        except Exception:
            pass

    @classmethod
    def load_from_env(cls, file_path: Optional[Path] = None) -> "AppConfig":
        target = file_path or get_default_config_path()
        config = cls()
        # Load from persisted config.json if present
        if target.exists():
            try:
                with open(target, "r", encoding="utf-8") as f:
                    data = json.load(f)
                config = cls.model_validate(data)
            except Exception:
                pass

        # Environment variables take precedence if set
        env_key = (
            os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or os.environ.get("AI_API_KEY")
            or os.environ.get("ANTHROPIC_API_KEY")
        )
        if env_key:
            config.reconciliation.api_key = env_key

        return config
