"""Local Host configuration.

Two layers:

* ``EnvSettings`` — process-level settings from environment variables / ``.env``
  (paths, log level, timeouts, first-run defaults). Read once at start-up.
* ``AppConfig`` — business settings the user edits in the Settings screen
  (company, financial year, Tally host/port, tax ledgers...). Stored in SQLite.

The Local Host holds NO provider secrets (AI keys, MongoDB credentials). Those
live on the Server Host only.
"""
from __future__ import annotations

import re
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_NAME = "BRMCo Accounting Hub"
APP_VERSION = "1.0.0"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    data_dir: Path = PROJECT_ROOT / "data"
    log_level: str = "INFO"
    max_upload_mb: int = 10

    tally_timeout_seconds: float = 30.0
    server_timeout_seconds: float = 10.0

    # First-run defaults (afterwards the values saved in Settings win)
    tally_host: str = "127.0.0.1"
    tally_port: int = 9000
    server_base_url: str = "http://127.0.0.1:8001"
    demo_mode: bool = True

    @property
    def db_path(self) -> Path:
        return self.data_dir / "brmco_local.db"

    @property
    def log_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def xml_dir(self) -> Path:
        return self.data_dir / "xml"

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.log_dir, self.xml_dir, self.upload_dir):
            d.mkdir(parents=True, exist_ok=True)


_FY_RE = re.compile(r"^(\d{4})-(\d{2})$")


class AppConfig(BaseModel):
    """User-editable settings, persisted in the ``app_settings`` table."""

    company_name: str = ""
    company_gstin: str = ""
    company_state: str = ""
    financial_year: str = "2026-27"

    tally_company_name: str = ""
    tally_host: str = "127.0.0.1"
    tally_port: int = Field(default=9000, ge=1, le=65535)

    server_base_url: str = "http://127.0.0.1:8001"
    demo_mode: bool = True

    # Ledgers the engine posts GST / round-off to. Must exist in Tally.
    output_cgst_ledger: str = "Output CGST"
    output_sgst_ledger: str = "Output SGST"
    output_igst_ledger: str = "Output IGST"
    output_cess_ledger: str = "Output Cess"
    input_cgst_ledger: str = "Input CGST"
    input_sgst_ledger: str = "Input SGST"
    input_igst_ledger: str = "Input IGST"
    input_cess_ledger: str = "Input Cess"
    round_off_ledger: str = "Round Off"
    cost_category: str = "Primary Cost Category"

    # Tally voucher type names (companies often rename these, e.g. "Sales GST")
    voucher_type_sales: str = "Sales"
    voucher_type_purchase: str = "Purchase"
    voucher_type_journal: str = "Journal"
    voucher_type_receipt: str = "Receipt"
    voucher_type_payment: str = "Payment"

    # Allowed difference between a tax amount in Excel and taxable x rate.
    tax_tolerance: Decimal = Decimal("1.00")
    # When True (and not in demo mode) ledgers must be verified against synced masters.
    require_master_sync: bool = True

    @field_validator("financial_year")
    @classmethod
    def _fy(cls, v: str) -> str:
        m = _FY_RE.match(v.strip())
        if not m or (int(m.group(1)) + 1) % 100 != int(m.group(2)):
            raise ValueError("Financial year must look like 2026-27")
        return v.strip()

    @field_validator("server_base_url")
    @classmethod
    def _url(cls, v: str) -> str:
        v = v.strip().rstrip("/")
        if v and not re.match(r"^https?://", v):
            raise ValueError("Server URL must start with http:// or https://")
        return v

    @field_validator("company_gstin")
    @classmethod
    def _gstin(cls, v: str) -> str:
        return v.strip().upper()

    def voucher_type_for(self, kind: str) -> str:
        return getattr(self, f"voucher_type_{getattr(kind, 'value', kind)}")

    @property
    def tally_url(self) -> str:
        return f"http://{self.tally_host}:{self.tally_port}"

    @property
    def fy_start_year(self) -> int:
        return int(self.financial_year[:4])

    @property
    def master_cache_key(self) -> str:
        """Masters are cached per Tally company; demo masters never mix with real ones."""
        if self.demo_mode:
            return "__DEMO__"
        return self.tally_company_name.strip() or "__ACTIVE__"


@lru_cache
def get_env_settings() -> EnvSettings:
    return EnvSettings()
