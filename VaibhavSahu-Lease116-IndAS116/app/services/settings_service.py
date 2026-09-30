"""Company-level settings: accounting policies, controls, AI engine and display preferences."""
from __future__ import annotations

import copy
import platform
import sys
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from ..db.models import Company
from ..engine.models import Framework, Policy
from ..engine.rates import DayCount, RateConvention

DEFAULT_SETTINGS: dict[str, Any] = {
    "policies": {
        "daycount": "ACT/365F",
        "rate_convention": "EFFECTIVE_ANNUAL",
        "commencement_payment_paid": True,
        "depreciation_method": "DAILY",
        "current_split_method": "PRINCIPAL_12M",
        "rounding_method": "BALANCE",
        "currency_decimals": 2,
        "maturity_buckets": [1, 2, 3, 4, 5],
        "low_value_threshold": None,          # entity policy — deliberately not assumed
        "deposit_difference_as_prepaid_rent": True,
        "lessor_income_method": "MONTHLY_EQUAL",   # lessor operating-lease income: MONTHLY_EQUAL | DAILY (both straight-line, para 81)
        "gst_non_creditable_policy": "Exclude (creditable GST not a lease payment)",
    },
    "controls": {
        "segregation_of_duties": True,        # preparer cannot approve own work
        "two_step_review": False,             # require reviewer before approver
        "materiality_deposit": "1000000",     # deposits above this are flagged for Ind AS 109 analysis
    },
    "ai": {
        "mode": "local",                      # rules | local | claude
        "allow_cloud": False,                 # entity-level permission for Claude API
        "local": {"kind": "ollama", "base_url": "http://localhost:11434", "model": "", "vision_model": ""},
        "claude": {"api_key": "", "model": ""},
        "ocr_engine": "auto",
    },
    "display": {"number_format": "INDIAN", "units": "ABSOLUTE", "date_format": "DD-MMM-YYYY"},
    "journal": {"payment_credit_role": "LESSOR_PAYABLE", "tally_company": "", "summarise": False},
    "tax": {"tax_rate_pct": "25.168", "rou_tax_base": "0", "liability_tax_base": "0", "dta_recoverable": True, "offset_permitted": True},
}


def deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def get_settings(company: Company) -> dict:
    return deep_merge(DEFAULT_SETTINGS, company.settings or {})


def public_settings(company: Company) -> dict:
    s = get_settings(company)
    s = copy.deepcopy(s)
    key = s["ai"]["claude"].get("api_key") or ""
    s["ai"]["claude"]["api_key"] = ("•" * 8 + key[-4:]) if key else ""
    s["ai"]["claude"]["has_key"] = bool(key)
    return s


def build_policy(company: Company, overrides: dict | None = None) -> Policy:
    p = get_settings(company)["policies"]
    if overrides:
        p = {**p, **{k: v for k, v in overrides.items() if v not in (None, "")}}
    return Policy(framework=Framework(company.framework or "IND_AS_116"), daycount=DayCount(p["daycount"]),
                  rate_convention=RateConvention(p["rate_convention"]),
                  commencement_payment_paid=bool(p["commencement_payment_paid"]),
                  depreciation_method=p["depreciation_method"], current_split_method=p["current_split_method"],
                  rounding_method=p["rounding_method"], currency_decimals=int(p["currency_decimals"]),
                  fy_start_month=company.fy_start_month or 4, maturity_buckets=tuple(p.get("maturity_buckets") or (1, 2, 3, 4, 5)),
                  lessor_income_method=p.get("lessor_income_method") or "MONTHLY_EQUAL")


def build_llm(company: Company, allow_cloud_for_doc: bool = False, mode_override: str | None = None):
    """Return (provider, name) for the configured AI mode, or (None, '') for rules-only."""
    from ..docintel.llm import ClaudeLLM, LocalLLM

    ai = get_settings(company)["ai"]
    mode = mode_override or ai.get("mode", "local")
    if mode == "claude":
        if not ai.get("allow_cloud"):
            raise PermissionError("Cloud AI is not allowed for this company (Settings → AI engine).")
        if not allow_cloud_for_doc:
            raise PermissionError("Please confirm that this document may be sent to the Claude API.")
        key = ai["claude"].get("api_key")
        if not key:
            raise ValueError("Claude API key is not configured (Settings → AI engine).")
        return ClaudeLLM(api_key=key, model=ai["claude"].get("model") or ""), "claude"
    if mode == "local":
        loc = ai.get("local", {})
        if not loc.get("model"):
            return None, ""
        return LocalLLM(base_url=loc.get("base_url") or "http://localhost:11434", kind=loc.get("kind") or "ollama",
                        model=loc["model"], vision_model=loc.get("vision_model") or ""), "local"
    return None, ""


def capabilities() -> dict:
    from ..docintel import ocr as ocrmod
    from ..docintel.ingest import HAS_FITZ
    from ..docintel.llm import LocalLLM
    from ..docintel.vision import HAS_CV2

    try:
        import anthropic  # noqa: F401
        has_anthropic = True
    except Exception:
        has_anthropic = False
    return {
        "python": sys.version.split()[0], "platform": platform.platform(), "machine": platform.machine(),
        "pdf_engine": "PyMuPDF" if HAS_FITZ else "pypdf + pypdfium2",
        "computer_vision": "OpenCV" if HAS_CV2 else "Pillow (basic)",
        "ocr_engines": ocrmod.available_engines(),
        "local_llm_servers": LocalLLM.detect(),
        "claude_sdk": has_anthropic,
    }
