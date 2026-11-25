"""Application settings.

Two layers:

1. ``Settings`` - deployment settings read from environment variables (prefix ``CFF_``)
   or a ``.env`` file. These cover host/port, TLS, paths, secrets and limits.
   No secret is ever written in code: if a secret is not supplied it is generated
   once into the ``instance/`` folder, which is git-ignored.

2. ``BusinessDefaults`` - forecast rules (lot scheme, horizon, currency, approver switch).
   These are only *seed* values. From Phase 2 on they are stored in the database
   ``app_setting`` table and edited by an Admin on screen.
"""
from __future__ import annotations

import ipaddress
import secrets
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]

LotScheme = Literal["month_thirds", "fixed_days"]


class BusinessDefaults(BaseSettings):
    """Seed values for business rules (overridable via env, then editable in the DB)."""

    model_config = SettingsConfigDict(
        env_prefix="CFF_", env_file=PROJECT_ROOT / ".env", extra="ignore"
    )

    base_currency: str = "OMR"
    currency_decimals: int = Field(3, ge=0, le=4)
    # month_thirds: days 1-10, 11-20, 21-month end.  fixed_days: rolling lots of lot_length_days.
    lot_scheme: LotScheme = "month_thirds"
    lot_length_days: int = Field(10, ge=1, le=31)
    # Optional anchor date (YYYY-MM-DD; blank = the 1st of the month).
    #   month_thirds: its DAY starts every period, e.g. 2026-01-05 -> periods 5 Nov-4 Dec, lots 5-14, 15-24, 25-4.
    #   fixed_days:   lots run every lot_length_days from this exact date, e.g. 2026-11-05 -> 5-14 Nov, 15-24 Nov ...
    lot_anchor_date: str = ""
    # month_thirds: horizon = current month + (horizon_months - 1) following months, to month end.
    #               2 -> e.g. 21-30 Nov .. 31 Dec;  3 -> .. 31 Jan.  Change any time in Settings.
    horizon_months: int = Field(3, ge=1, le=12)
    # fixed_days: horizon is a number of lots instead.
    horizon_lots: int = Field(3, ge=1, le=36)
    show_month_totals: bool = True         # a month-total column after each month's lots
    # current_lot: grid starts at the lot holding the as-of date (rolling view).
    # month_start: grid starts at lot 1 of the as-of month; earlier lots show as locked actuals.
    grid_start: Literal["current_lot", "month_start"] = "current_lot"
    max_bank_accounts_base_currency: int = Field(3, ge=1, le=20)
    funding_alert_threshold: float = 0.0   # commentary warns when funding position falls below this
    # --- cheque holds ---
    hold_default_days: int = Field(10, ge=1, le=180)     # suggested next honouring date = cheque date + N
    cheque_validity_days: int = Field(180, ge=30, le=365)  # warn if honouring date makes the cheque stale
                                                           # (confirm the period your banks apply)
    approver_enabled: bool = False

    @field_validator("base_currency")
    @classmethod
    def _upper(cls, v: str) -> str:
        v = v.strip().upper()
        if len(v) != 3 or not v.isalpha():
            raise ValueError("base_currency must be a 3-letter ISO code")
        return v

    @field_validator("lot_anchor_date", mode="before")
    @classmethod
    def _anchor(cls, v) -> str:
        if v is None:
            return ""
        if isinstance(v, date):
            return v.isoformat()
        v = str(v).strip()
        if not v:
            return ""
        try:
            return date.fromisoformat(v).isoformat()
        except ValueError:
            raise ValueError("lot_anchor_date must be a date as YYYY-MM-DD, or blank") from None

    @model_validator(mode="after")
    def _anchor_day(self):
        if self.lot_anchor_date and self.lot_scheme == "month_thirds" and self.anchor.day > 28:
            raise ValueError("With month_thirds the anchor day must be 1-28 (every month has that day).")
        return self

    @property
    def anchor(self) -> date | None:
        return date.fromisoformat(self.lot_anchor_date) if self.lot_anchor_date else None


class Settings(BaseSettings):
    """Deployment settings."""

    model_config = SettingsConfigDict(
        env_prefix="CFF_", env_file=PROJECT_ROOT / ".env", extra="ignore"
    )

    app_name: str = "Cash Flow Forecast"

    # --- server ---
    host: str = "127.0.0.1"
    port: int = Field(8000, ge=1, le=65535)
    ssl_certfile: Path | None = None
    ssl_keyfile: Path | None = None

    # --- paths ---
    instance_dir: Path = Path("instance")

    # --- secrets (empty -> generated into instance/) ---
    secret_key: str = ""
    backup_passphrase: str = ""

    # --- sessions ---
    session_max_age_minutes: int = Field(480, ge=5, le=24 * 60)

    # --- uploads ---
    upload_max_mb: int = Field(10, ge=1, le=200)
    upload_allowed_extensions: tuple[str, ...] = (".xlsx", ".csv")

    # --- backups: encrypted; one a day automatically while the app runs; newest N kept ---
    auto_backup: bool = True
    backup_keep: int = Field(30, ge=1, le=3650)
    backup_copy_dir: Path | None = None        # e.g. a network share or USB drive: each backup is copied there

    # --- display: times are stored in UTC and shown at this offset (Oman = +4, no daylight saving) ---
    utc_offset_hours: float = Field(4.0, ge=-12, le=14)

    # --- Excel export check (LibreOffice). Empty: look in the usual install folders and PATH ---
    soffice_path: Path | None = None
    recalc_timeout_seconds: int = Field(180, ge=10, le=1800)

    @field_validator("ssl_certfile", "ssl_keyfile", "soffice_path", "backup_copy_dir", mode="before")
    @classmethod
    def _blank_to_none(cls, v):
        return None if v in ("", None) else v

    @model_validator(mode="after")
    def _resolve(self) -> "Settings":
        if not self.instance_dir.is_absolute():
            self.instance_dir = (PROJECT_ROOT / self.instance_dir).resolve()
        for name in ("ssl_certfile", "ssl_keyfile"):
            p = getattr(self, name)
            if p is not None and not p.is_absolute():
                setattr(self, name, (PROJECT_ROOT / p).resolve())
        if bool(self.ssl_certfile) != bool(self.ssl_keyfile):
            raise ValueError("Set both CFF_SSL_CERTFILE and CFF_SSL_KEYFILE, or neither")
        return self

    # ---------- derived paths ----------
    @property
    def database_path(self) -> Path:
        return self.instance_dir / "cashflow.db"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path.as_posix()}"

    @property
    def uploads_dir(self) -> Path:
        return self.instance_dir / "uploads"

    @property
    def exports_dir(self) -> Path:
        return self.instance_dir / "exports"

    @property
    def backups_dir(self) -> Path:
        return self.instance_dir / "backups"

    @property
    def upload_max_bytes(self) -> int:
        return self.upload_max_mb * 1024 * 1024

    @property
    def https_enabled(self) -> bool:
        return self.ssl_certfile is not None

    @property
    def is_loopback(self) -> bool:
        if self.host == "localhost":
            return True
        try:
            return ipaddress.ip_address(self.host).is_loopback
        except ValueError:
            return False

    # ---------- setup ----------
    def ensure_dirs(self) -> None:
        for d in (self.instance_dir, self.uploads_dir, self.exports_dir, self.backups_dir):
            d.mkdir(parents=True, exist_ok=True)

    def _load_or_create_secret(self, filename: str) -> str:
        path = self.instance_dir / filename
        if path.exists():
            value = path.read_text(encoding="utf-8").strip()
            if value:
                return value
        value = secrets.token_urlsafe(48)
        path.write_text(value, encoding="utf-8")
        try:
            path.chmod(0o600)  # best effort; on Windows NTFS ACLs of instance/ apply
        except OSError:
            pass
        return value

    def resolve_secrets(self) -> None:
        """Fill secret_key / backup_passphrase from instance/ files when not supplied."""
        self.ensure_dirs()
        if not self.secret_key:
            self.secret_key = self._load_or_create_secret("secret.key")
        if not self.backup_passphrase:
            self.backup_passphrase = self._load_or_create_secret("backup.key")

    def check_network_safety(self) -> None:
        """HTTPS is mandatory whenever the app listens beyond this PC."""
        if not self.is_loopback and not self.https_enabled:
            raise RuntimeError(
                f"Refusing to listen on {self.host} without HTTPS. "
                "Set CFF_SSL_CERTFILE and CFF_SSL_KEYFILE, or use CFF_HOST=127.0.0.1."
            )


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.resolve_secrets()
    return s


@lru_cache
def get_business_defaults() -> BusinessDefaults:
    return BusinessDefaults()
