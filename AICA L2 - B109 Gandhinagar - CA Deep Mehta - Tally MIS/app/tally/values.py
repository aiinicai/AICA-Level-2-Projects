"""Parsers for Tally's text formats (amounts, dates, quantities).

All money maths is exact: text -> whole paise, never floating point. Tally's XML sign is
negative = debit; our model is debit-positive, so `canonical_paise` flips the sign once, here.
Ported from the Node project's connectors/tally/values.ts so both produce identical numbers.
"""
from __future__ import annotations

import re
from datetime import date

_MONTHS = {m: i + 1 for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}
_DEC = re.compile(r"^([+-])?(\d*)(?:\.(\d*))?$")


def scale_decimal(text: str | None, scale: int) -> int | None:
    """'12.345' scaled by 10**scale -> int, rounding half away from zero. None when blank/unparseable."""
    if text is None:
        return None
    m = _DEC.match(text.strip())
    if not m or (m.group(2) == "" and (m.group(3) or "") == ""):
        return None
    neg = m.group(1) == "-"
    frac = (m.group(3) or "").ljust(scale + 1, "0")
    n = int((m.group(2) or "0") + frac[:scale])
    if int(frac[scale]) >= 5:
        n += 1
    return -n if neg and n != 0 else n


_NUM = re.compile(r"\d+(?:\.\d+)?|\.\d+")


def extract_number(raw: str | None) -> str | None:
    """Numeric part of a Tally amount string, with '-' prefix when it is a debit."""
    if not raw:
        return None
    s = raw
    if "=" in s:  # forex: base-currency value follows '='
        s = s[s.rindex("=") + 1:]
    s = s.replace(",", "").strip()
    m = _NUM.search(s)
    if not m:
        return None
    before = s[: m.start()]
    neg = "-" in before or "(" in before
    if re.search(r"\bDr\.?$", s, re.I):
        neg = True
    elif re.search(r"\bCr\.?$", s, re.I):
        neg = False
    return ("-" if neg else "") + m.group(0)


_SIMPLE = re.compile(r"^(-?)(\d+)(?:\.(\d{1,2}))?$")


def tally_paise(raw: str | None) -> int | None:
    """Tally amount -> paise in Tally's own sign (negative = debit)."""
    if raw:  # fast path for the overwhelmingly common plain form "-11800.00"
        m = _SIMPLE.match(raw)
        if m:
            n = int(m[2]) * 100 + int((m[3] or "").ljust(2, "0"))
            return -n if m[1] and n else n
    return scale_decimal(extract_number(raw), 2)


def canonical_paise(raw: str | None) -> int:
    """Tally amount -> debit-positive paise. Blank -> 0."""
    p = tally_paise(raw)
    return 0 if p is None or p == 0 else -p


def parse_qty(raw: str | None) -> tuple[int, str | None] | None:
    """' 100.500 Nos' -> (1005000, 'Nos') (quantity x 10^4)."""
    if not raw or not raw.strip():
        return None
    s = raw.strip()
    if "=" in s:
        s = s[: s.index("=")].strip()
    m = re.match(r"^(-)?\s*(\d*\.?\d+)\s*(.*)$", s.replace(",", ""))
    if not m:
        return None
    q = scale_decimal((m.group(1) or "") + m.group(2), 4)
    if q is None:
        return None
    unit = (m.group(3) or "").strip().split()
    return q, (unit[0] if unit else None)


def parse_rate(raw: str | None) -> int | None:
    if not raw:
        return None
    p = tally_paise(raw.split("/")[0])
    return None if p is None else abs(p)


def _valid(y: int, m: int, d: int) -> str | None:
    if m < 1 or m > 12 or d < 1 or d > 31 or y < 1900 or y > 2200:
        return None
    try:
        date(y, m, d)
    except ValueError:
        return None
    return f"{y:04d}-{m:02d}-{d:02d}"


_D1 = re.compile(r"^(\d{4})(\d{2})(\d{2})$")
_D2 = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
_D3 = re.compile(r"^(\d{1,2})[-\s/]([A-Za-z]{3})[A-Za-z]*[-\s/](\d{2,4})$")
_D4 = re.compile(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$")


def parse_tally_date(raw: str | None) -> str | None:
    """'20240415' | '2024-04-15' | '15-Apr-2024' | '1-Apr-24' | '15-04-2024' -> '2024-04-15'."""
    if not raw:
        return None
    s = raw.strip()
    m = _D1.match(s)
    if m:
        return _valid(int(m[1]), int(m[2]), int(m[3]))
    m = _D2.match(s)
    if m:
        return _valid(int(m[1]), int(m[2]), int(m[3]))
    m = _D3.match(s)
    if m:
        mon = _MONTHS.get(m[2].lower())
        y = int(m[3])
        if y < 100:
            y += 2000
        return _valid(y, mon, int(m[1])) if mon else None
    m = _D4.match(s)
    if m:
        return _valid(int(m[3]), int(m[2]), int(m[1]))
    return None


def parse_bool(raw: str | None) -> bool:
    return (raw or "").strip().lower() == "yes"


def parse_credit_period(raw: str | None) -> dict:
    if not raw or not raw.strip():
        return {}
    s = raw.strip()
    m = re.match(r"^(\d+)\s*(days?)?$", s, re.I)
    if m:
        return {"days": int(m[1])}
    m = re.match(r"^(\d+)\s*weeks?$", s, re.I)
    if m:
        return {"days": int(m[1]) * 7}
    m = re.match(r"^(\d+)\s*months?$", s, re.I)
    if m:
        return {"days": int(m[1]) * 30}
    due = parse_tally_date(s)
    return {"due_date": due} if due else {}


def clean_text(raw: str | None) -> str:
    return " ".join(raw.split()) if raw else ""
