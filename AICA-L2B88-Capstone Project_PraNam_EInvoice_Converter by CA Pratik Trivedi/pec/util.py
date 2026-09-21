"""Defensive parsing helpers. None of these functions guess: when a value cannot be
interpreted they return None and the caller raises a validation issue."""
from __future__ import annotations

import datetime as dt
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

_WS = re.compile(r"\s+")


_CID = re.compile(r"\(cid:\d+\)")


def clean_text(v) -> str:
    """Collapse whitespace; treat None, '-' and blank as empty. PDF glyphs that carry no
    Unicode mapping (the rupee sign in some fonts) arrive as '(cid:31)' and are dropped."""
    if v is None:
        return ""
    s = _WS.sub(" ", _CID.sub(" ", str(v))).strip()
    return "" if s in {"-", "--", "NIL", "N/A"} else s


def split_block_lines(v) -> list[str]:
    """A merged block cell often holds several address lines separated by line breaks
    or long runs of spaces. Split on either."""
    if v is None:
        return []
    parts = re.split(r"\r?\n|\s{3,}", str(v))
    return [clean_text(p).strip(" ,") for p in parts if clean_text(p).strip(" ,")]


_NUM_JUNK = re.compile(r"(?i)(₹|rs\.?|rupees?|inr|usd|us\$|\$|euros?|eur|€|gbp|pounds?|£|aed|aud|cad|sgd|chf|jpy)")


def to_decimal(v) -> Decimal | None:
    """Numbers, numbers-as-text, '1,234.50', '(12.5)', 'USD 12', '18%'. Returns None if not a number."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        try:
            return Decimal(repr(v)) if isinstance(v, float) else Decimal(v)
        except InvalidOperation:
            return None
    if isinstance(v, Decimal):
        return v
    s = _CID.sub("", str(v)).strip()
    if not s:
        return None
    neg = s.startswith("(") and s.endswith(")")
    s = _NUM_JUNK.sub("", s.strip("()")).replace(",", "").replace("%", "").replace("\u20b9", "").strip()
    if not re.fullmatch(r"[-+]?\d+(\.\d+)?|[-+]?\.\d+", s):
        return None
    d = Decimal(s)
    return -d if neg else d


def first_number(v) -> Decimal | None:
    """Lenient: first numeric token in text such as '200 GMS'."""
    d = to_decimal(v)
    if d is not None:
        return d
    m = re.search(r"\d+(?:\.\d+)?", str(v or "").replace(",", ""))
    return Decimal(m.group(0)) if m else None


def q(d: Decimal, places: int) -> Decimal:
    return d.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def fmt(d: Decimal | None, places: int) -> str:
    """Round half-up and render without superfluous trailing zeros ('349', '38.78')."""
    if d is None:
        return ""
    s = format(q(d, places), "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in {"-0", ""} else s


_MONTHS = {m: i for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}


def parse_date(v, dayfirst: bool = True) -> tuple[dt.date | None, bool]:
    """Returns (date, ambiguous). 'ambiguous' is True when day and month could be swapped."""
    if v is None:
        return None, False
    if isinstance(v, dt.datetime):
        return v.date(), False
    if isinstance(v, dt.date):
        return v, False
    s = clean_text(v).upper()
    m = re.fullmatch(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})", s)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        y = y + 2000 if y < 100 else y
        d, mo = (a, b) if dayfirst else (b, a)
        try:
            return dt.date(y, mo, d), (a <= 12 and b <= 12 and a != b)
        except ValueError:
            return None, False
    m = re.fullmatch(r"(\d{1,2})[\-\s]([A-Z]{3})[A-Z]*[\-\s,]*(\d{2,4})", s)
    if m and m.group(2) in _MONTHS:
        y = int(m.group(3))
        y = y + 2000 if y < 100 else y
        try:
            return dt.date(y, _MONTHS[m.group(2)], int(m.group(1))), False
        except ValueError:
            return None, False
    return None, False


# ---------------------------------------------------------------- GSTIN
_GSTIN_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z][0-9A-Z][0-9A-Z]$")


def gstin_check(g: str) -> tuple[bool, str]:
    """Structure + check-digit test of a 15-character GSTIN."""
    g = (g or "").strip().upper()
    if not g:
        return False, "GSTIN is blank"
    if len(g) != 15:
        return False, f"GSTIN must be 15 characters (found {len(g)})"
    if not _GSTIN_RE.match(g):
        return False, "GSTIN structure is not valid (2-digit state code + 10-character PAN + entity code + 2 characters)"
    total = 0
    for i, ch in enumerate(g[:14]):
        p = _GSTIN_CHARS.index(ch) * (1 if i % 2 == 0 else 2)
        total += p // 36 + p % 36
    expected = _GSTIN_CHARS[(36 - total % 36) % 36]
    if expected != g[14]:
        return False, "GSTIN check digit does not match - please re-check the GSTIN"
    return True, ""


def safe_filename(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\-]+", "_", s).strip("_") or "invoice"


def xml_escape(s: str) -> str:
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def col_letter(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def col_index(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n
