"""Periods, financial years and file names."""
import calendar
import re
from datetime import date

MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH_FULL = ["January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"]
QUARTER_MONTHS = {1: (4, 5, 6), 2: (7, 8, 9), 3: (10, 11, 12), 4: (1, 2, 3)}

FORM_LABELS = {"GSTR1": "GSTR-1", "GSTR2B": "GSTR-2B", "GSTR3B": "GSTR-3B"}


def fy_start(year: int, month: int) -> int:
    return year if month >= 4 else year - 1


def fy_label(year: int, month: int) -> str:
    s = fy_start(year, month)
    return f"{s}-{str(s + 1)[-2:]}"


def fy_months(fy_start_year: int):
    """(year, month) for Apr..Mar of the FY."""
    return [(fy_start_year, m) for m in range(4, 13)] + [(fy_start_year + 1, m) for m in range(1, 4)]


def quarter_no(month: int) -> int:
    return ((month - 4) % 12) // 3 + 1


def quarter_end_month(month: int) -> int:
    return QUARTER_MONTHS[quarter_no(month)][2]


def period_label(year: int, month: int) -> str:
    return f"{MONTH_ABBR[month - 1]} {year}"


def quarter_label(year: int, month: int) -> str:
    q = quarter_no(month)
    a, _, c = QUARTER_MONTHS[q]
    return f"Q{q} {MONTH_ABBR[a - 1]}-{MONTH_ABBR[c - 1]} {year}"


_INVALID = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
_MS = re.compile(r"^\s*m\s*/\s*s\.?\s+", re.IGNORECASE)


def clean_name(name: str) -> str:
    """Make a client name safe for a Windows file/folder name."""
    s = _MS.sub("", str(name or ""))
    s = _INVALID.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip().rstrip(". ")
    return (s[:80].rstrip(". ") or "Client")


def build_filename(trade_name: str, form: str, label: str, ext: str) -> str:
    ext = ext.lstrip(".").lower()
    return f"{clean_name(trade_name)} {form} {label}.{ext}"


def send_by_date(year: int, month: int, day: int) -> date:
    """`day` of the month after the period (clamped to month length)."""
    ny, nm = (year + 1, 1) if month == 12 else (year, month + 1)
    last = calendar.monthrange(ny, nm)[1]
    return date(ny, nm, max(1, min(int(day), last)))


def fmt_date(d: date) -> str:
    return d.strftime("%d-%b-%Y")


def is_period_available(year: int, month: int, today: date | None = None) -> bool:
    """A month can be downloaded only after it has ended."""
    today = today or date.today()
    return (year, month) < (today.year, today.month)
