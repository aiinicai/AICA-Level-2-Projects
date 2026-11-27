"""
Statement detector: decides whether a sheet / page is a Profit & Loss account
or a Balance Sheet, finds the financial year(s) it relates to, and parses
Indian-format amounts (1,23,456.00 / (12,345) / 12,345 Dr).
"""
import datetime as dt
import re

from config.constants import PL_MARKERS, BS_MARKERS

_AMT = re.compile(r"^\(?-?₹?\s*[\d,]+(\.\d+)?\)?(\s*(dr|cr))?$", re.I)


def parse_amount(value):
    """Return float or None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace("₹", "").replace("Rs.", "").replace("Rs", "").strip()
    if s in ("", "-", "--", "nil", "Nil", "NIL"):
        return None
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg, s = True, s[1:-1]
    low = s.lower()
    if low.endswith(" cr") or low.endswith("cr"):
        s = s[:-2].strip()
    elif low.endswith(" dr") or low.endswith("dr"):
        s = s[:-2].strip()
    if s.startswith("-"):
        neg, s = True, s[1:]
    s = s.replace(",", "").replace(" ", "")
    if not re.fullmatch(r"\d+(\.\d+)?", s):
        return None
    v = float(s)
    return -v if neg else v


def is_amount_token(tok):
    t = str(tok).strip()
    if not t or not _AMT.match(t):
        return False
    digits = re.sub(r"\D", "", t)
    return len(digits) >= 1


def looks_like_year_or_note(v, header=""):
    """Small integers in a 'Note' column or bare years are not amounts."""
    if v is None:
        return True
    if "note" in str(header).lower() or "sch" in str(header).lower():
        return True
    return False


def classify_text(text):
    """Return 'PL', 'BS' or '' from the words on a sheet / page."""
    t = (text or "").lower()
    pl = sum(t.count(m) for m in PL_MARKERS)
    bs = sum(t.count(m) for m in BS_MARKERS)
    if "balance sheet" in t and "profit" not in t[:200]:
        bs += 5
    if "profit and loss" in t[:300] or "profit & loss" in t[:300] or "trading" in t[:300] \
            or "income and expenditure" in t[:300]:
        pl += 5
    if pl == bs == 0:
        return ""
    return "PL" if pl > bs else "BS"


_FY_PATTERNS = [
    re.compile(r"(?:f\.?y\.?\s*)?(20\d{2})\s*[-–/]\s*(\d{2}|20\d{2})(?!\d)", re.I),
    re.compile(r"31(?:st)?[\s\.\-/]*(?:03|march|mar)[\s\.\-/,]*(20\d{2})", re.I),
    re.compile(r"(?:march|mar)\s*31(?:st)?[\s,]*(20\d{2})", re.I),
]


def detect_years(text):
    """Return a list of FY end years mentioned (in order of first appearance, unique)."""
    out = []
    t = text or ""
    for m in _FY_PATTERNS[0].finditer(t):
        a, b = int(m.group(1)), m.group(2)
        bb = int(b) if len(b) == 4 else (a // 100) * 100 + int(b)
        if bb == a + 1:
            out.append((m.start(), bb))
    for pat in _FY_PATTERNS[1:]:
        for m in pat.finditer(t):
            out.append((m.start(), int(m.group(1))))
    out.sort()
    seen, res = set(), []
    for _, y in out:
        if y not in seen and 2000 < y < 2100:
            seen.add(y)
            res.append(y)
    return res


def year_from_header(cell):
    """FY end year from a column header such as 'FY 2025-26', '31.03.2026', '2025-2026'."""
    if isinstance(cell, (dt.date, dt.datetime)):
        return cell.year + (1 if cell.month >= 4 else 0)
    ys = detect_years(str(cell or ""))
    return ys[0] if len(ys) == 1 else None
