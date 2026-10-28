"""Helper functions: decimals, dates, states, rates."""
import datetime as dt
import hashlib
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from .config import STATE_CODES

ZERO = Decimal("0")


def D(v, default: Decimal = ZERO) -> Decimal:
    if v is None:
        return default
    if isinstance(v, Decimal):
        return v
    if isinstance(v, bool):
        return default
    if isinstance(v, int):
        return Decimal(v)
    if isinstance(v, float):
        if v != v:
            return default
        return Decimal(str(v))
    s = str(v).strip().replace(",", "").replace("₹", "").replace("Rs.", "").replace("%", "").strip()
    if s in ("", "-", "nan", "None", "NaT"):
        return default
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try:
        d = Decimal(s)
    except InvalidOperation:
        return default
    return -d if neg else d


def q2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), ROUND_HALF_UP)


_DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y", "%d.%m.%y",
    "%Y-%m-%d", "%Y/%m/%d", "%d-%b-%Y", "%d-%b-%y", "%d %b %Y", "%d %B %Y",
    "%d-%B-%Y", "%b %d, %Y", "%d/%b/%Y", "%d %b, %Y", "%d-%b/%Y",
]


def parse_date(v) -> str:
    """Return ISO date string (YYYY-MM-DD) or '' if it cannot be parsed."""
    if v is None:
        return ""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if v == v and 20000 < float(v) < 80000:  # Excel serial date
            return (dt.date(1899, 12, 30) + dt.timedelta(days=int(v))).isoformat()
        return ""
    if hasattr(v, "strftime"):
        try:
            return v.strftime("%Y-%m-%d")
        except ValueError:
            return ""
    s = str(v).strip()
    if not s or s.lower() in ("nan", "nat", "none"):
        return ""
    s = re.sub(r"\s+\d{1,2}:\d{2}(:\d{2})?.*$", "", s)
    for f in _DATE_FORMATS:
        try:
            return dt.datetime.strptime(s, f).date().isoformat()
        except ValueError:
            continue
    return ""


def state_from_text(t) -> str:
    """Place of supply text ('27-Maharashtra', 'Maharashtra', '27') -> 2-digit code."""
    if not t:
        return ""
    s = str(t).strip()
    m = re.match(r"^(\d{2})\b", s)
    if m and m.group(1) in STATE_CODES:
        return m.group(1)
    low = s.lower().replace("&", "and")
    best = ""
    for code, name in STATE_CODES.items():
        if name.lower() in low and len(name) > len(STATE_CODES.get(best, "")):
            best = code
    if not best and "orissa" in low:
        best = "21"
    if not best and "pondicherry" in low:
        best = "34"
    return best


def pos_label(code: str) -> str:
    return f"{code}-{STATE_CODES[code]}" if code in STATE_CODES else code


def parse_rates(text: str):
    out = []
    for p in str(text).split(","):
        d = D(p, None)
        if d is not None:
            out.append(d)
    return out


def snap_rate(taxable: Decimal, tax: Decimal, rates) -> Decimal:
    """Infer GST rate from tax/taxable, snapping to nearest valid slab within 0.15."""
    if taxable == 0:
        return ZERO
    raw = tax / taxable * 100
    best = None
    for r in rates:
        if best is None or abs(r - raw) < abs(best - raw):
            best = r
    if best is not None and abs(best - raw) <= Decimal("0.15"):
        return best
    return q2(raw)


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_invoice_no(s: str) -> str:
    return re.sub(r"\s+", "", str(s or "")).upper()


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fmt_date(iso: str, style: str = "DD-Mon-YY") -> str:
    if not iso:
        return ""
    try:
        d = dt.date.fromisoformat(iso)
    except ValueError:
        return iso
    return (style.replace("YYYY", f"{d.year:04d}").replace("YY", f"{d.year % 100:02d}")
            .replace("DD", f"{d.day:02d}").replace("Mon", MONTHS[d.month - 1])
            .replace("MM", f"{d.month:02d}"))


def fin_year(month: int, year: int) -> str:
    start = year if month >= 4 else year - 1
    return f"{start}-{str(start + 1)[-2:]}"
