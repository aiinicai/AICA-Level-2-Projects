"""
utils.py — Shared helpers for GST Notice Tracker
"""

import re
from datetime import datetime, date
import pandas as pd

# ─────────────────────────────────────────────
# GSTIN Validation
# ─────────────────────────────────────────────

GSTIN_REGEX = re.compile(
    r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
)


def validate_gstin(value: str) -> bool:
    """Return True if the value is a valid GSTIN."""
    if not isinstance(value, str):
        value = str(value).strip().upper()
    else:
        value = value.strip().upper()
    return bool(GSTIN_REGEX.match(value))


# ─────────────────────────────────────────────
# Date Parsing & Formatting
# ─────────────────────────────────────────────

_DATE_FORMATS = [
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%Y-%m-%d",
    "%d-%m-%y",
    "%d/%m/%y",
    "%Y/%m/%d",
    "%d.%m.%Y",
    "%d.%m.%y",
    "%m/%d/%Y",
    "%m-%d-%Y",
]

_EXCEL_EPOCH = datetime(1899, 12, 30)


def parse_date(value) -> datetime | None:
    """
    Accept any of: Python datetime, date, pandas Timestamp,
    Excel serial number (int/float), or date string.
    Returns a datetime object or None.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    # pandas NaT
    if isinstance(value, pd.NaT.__class__) and pd.isna(value):
        return None

    # Already a datetime / date
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)

    # pandas Timestamp
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.to_pydatetime()

    # Excel serial number
    if isinstance(value, (int, float)):
        try:
            return _EXCEL_EPOCH + pd.Timedelta(days=float(value))
        except Exception:
            return None

    # String
    s = str(value).strip()
    if not s or s.lower() in ("nan", "nat", "none", ""):
        return None

    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue

    return None


def format_date(value) -> str:
    """Return DD-MM-YYYY string or empty string."""
    dt = parse_date(value) if not isinstance(value, datetime) else value
    if dt is None:
        return ""
    return dt.strftime("%d-%m-%Y")


# ─────────────────────────────────────────────
# Urgency / Days Remaining  (always dynamic)
# ─────────────────────────────────────────────

def calc_days_remaining(due_date_value) -> int | None:
    """
    Return integer days remaining until due_date from today.
    Negative means overdue.  None if due_date is missing.
    """
    dt = parse_date(due_date_value)
    if dt is None:
        return None
    delta = dt.date() - date.today()
    return delta.days


def calc_urgency(due_date_value) -> str:
    """
    Dynamically calculate urgency label from today's date:
      GREEN  → > 10 days remaining
      AMBER  → 6–10 days remaining
      RED    → 0–5 days remaining
      OVERDUE→ past due date
    Returns empty string if due_date is missing.
    """
    days = calc_days_remaining(due_date_value)
    if days is None:
        return ""
    if days < 0:
        return "OVERDUE"
    elif days <= 5:
        return "RED"
    elif days <= 10:
        return "AMBER"
    else:
        return "GREEN"


URGENCY_COLORS = {
    "GREEN":   "#27ae60",
    "AMBER":   "#e67e22",
    "RED":     "#e74c3c",
    "OVERDUE": "#8e44ad",
    "":        "#95a5a6",
}

URGENCY_BG = {
    "GREEN":   "rgba(39,174,96,0.15)",
    "AMBER":   "rgba(230,126,34,0.15)",
    "RED":     "rgba(231,76,60,0.15)",
    "OVERDUE": "rgba(142,68,173,0.15)",
    "":        "rgba(149,165,166,0.10)",
}
