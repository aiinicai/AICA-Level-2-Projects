"""Central configuration for GXVAN.

Everything that a user (or a release manager) might want to change lives here:
branding, colours, tolerances, statutory cut-offs and folder paths.
Statutory values carry a ``# VERIFY against current law before release`` marker.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Branding
# ---------------------------------------------------------------------------
APP_NAME = "GXVAN"  # change to "GXPVAN" here and everything follows
APP_TAGLINE = "a product of Vantage"
APP_VERSION = "1.0.0"
FIRM_NAME = "Vantage Tax Consulting LLP"
FOOTER_TEXT = "© 2026 Vantage Tax Consulting LLP"

# ---------------------------------------------------------------------------
# Paths (never depend on cwd)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
# In a PyInstaller build the code folder may be read-only - keep user data in the home folder.
DATA_DIR = (Path.home() / "GXVAN_Data") if getattr(sys, "frozen", False) else BASE_DIR
ASSETS_DIR = BASE_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "vantage_logo.png"
LOG_DIR = DATA_DIR / "logs"
LOG_FILE = LOG_DIR / "gxvan.log"
DUMMY_DIR = BASE_DIR / "dummy_data"
DUMMY_OUT_DIR = DATA_DIR / "dummy_data" / "output" if DATA_DIR != BASE_DIR else DUMMY_DIR / "output"
TEMPLATE_DIR = DATA_DIR / "templates"          # column-mapping templates (JSON)
SETTINGS_FILE = DATA_DIR / "settings.json"      # user-editable overrides
RECO_COLUMN_MAP_FILE = DATA_DIR / "reco_column_map.json"

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
NAVY = "#1F2A5C"
GOLD_1 = "#E0A526"
GOLD_2 = "#F2C14E"
CANVAS = "#F4F5F9"
ACCENTS = {
    "home": "#1F2A5C",
    "pr": "#0FA3A3",       # PR Builder - teal
    "reco": "#6C4AB6",     # Reconciliation - violet
    "pdf": "#F06A4D",      # PDF tools - coral
    "pro": "#E0A526",      # Pro tools - amber
    "gst": "#0FA3A3",
    "dummy": "#2EAD6B",    # Dummy data - green
    "settings": "#55607A",
}
STATUS_COLOURS = {
    "Matched": "#2EAD6B",
    "Matched within tolerance": "#58C08A",
    "Probable": "#E0A526",
    "Mismatch": "#E0A526",
    "Missing": "#E5484D",
    "Ineligible": "#8A94A6",
    "RCM": "#6C4AB6",
    "Timing": "#3B82F6",
    "Duplicate": "#B5476B",
    "Info": "#55607A",
}

# ---------------------------------------------------------------------------
# Tolerances / matching parameters (user-editable in Settings)
# ---------------------------------------------------------------------------
DEFAULTS: dict = {
    "amount_tolerance_abs": 1.0,       # Rs per head
    "amount_tolerance_pct": 0.0,       # optional %; 0 = disabled
    "fuzzy_invoice_threshold": 85,     # rapidfuzz ratio
    "date_window_days": 3,
    "name_match_threshold": 80,
    # Sec 16(4) CGST Act: ITC for FY X can be claimed till 30 Nov of FY X+1.
    # VERIFY against current law before release
    "sec16_4_cutoff_month_day": "11-30",
    # Rule 37 CGST Rules: payment within 180 days of invoice date.
    # VERIFY against current law before release
    "rule37_days": 180,
    "einvoice_aato_threshold_cr": 5,   # VERIFY against current law before release
    "invoice_no_max_len": 16,          # Rule 46(b) CGST Rules - VERIFY
    "fx_tolerance_pct": 2.0,           # PR FX vs reference rate
    # Reference FX (INR per unit) for GST valuation checks - user maintained.
    # Rule 34 CGST Rules / CBIC notified rates. VERIFY against current law before release
    "reference_fx": {"USD": 88.0, "EUR": 95.0, "GBP": 112.0, "AED": 24.0, "SGD": 68.0, "NOK": 8.2},
    # IGST rate applied to import of services under RCM (user-confirmable per record).
    # VERIFY against current law before release
    "rcm_default_rate": 18.0,
    "sec17_5_keywords": {},            # empty = use gst_rules.SEC_17_5_KEYWORDS
    "theme": "light",
    "reviewer": "Reviewer",
    "recent_projects": [],
}


def load_settings() -> dict:
    """Return defaults overlaid with any saved user settings."""
    s = dict(DEFAULTS)
    try:
        if SETTINGS_FILE.exists():
            s.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return s


def save_settings(s: dict) -> None:
    """Persist user settings to settings.json."""
    SETTINGS_FILE.write_text(json.dumps(s, indent=2, default=str), encoding="utf-8")


def sec16_4_cutoff(fy_start_year: int, settings: dict | None = None) -> date:
    """Cut-off date for claiming ITC on invoices of FY starting ``fy_start_year``."""
    s = settings or load_settings()
    mm, dd = (int(x) for x in s["sec16_4_cutoff_month_day"].split("-"))
    return date(fy_start_year + 1, mm, dd)


# Single source for the pip line shown in README / Help dialog.
# Must match GXVAN.PACKAGES (checked by tests/test_packaging.py).
PIP_PACKAGES = [
    "PyQt6", "pandas", "numpy", "openpyxl", "xlsxwriter", "PyMuPDF", "reportlab", "Pillow",
    "rapidfuzz", "python-dateutil", "qrcode", "rapidocr-onnxruntime",
]
PIP_LINE = "pip install " + " ".join(PIP_PACKAGES)
