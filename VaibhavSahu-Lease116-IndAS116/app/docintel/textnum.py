"""Parsing of amounts, numbers-in-words (Indian and international systems), percentages,
durations and dates as they appear in Indian lease / leave-and-licence agreements.

Examples handled
  Rs. 1,50,000/- (Rupees One Lakh Fifty Thousand Only)   -> 150000, INR
  INR 2.5 lakh per month                                  -> 250000
  ₹1.25 crore                                             -> 12500000
  USD 10,000                                              -> 10000, USD
  sixty (60) months / 5 (five) years / 11 months          -> 60 / 60 / 11
  5% (five percent) / 15 per cent                         -> 5 / 15
  1st April, 2025 / 01/04/2025 / 01.04.2025 / April 1, 2025 / 15th day of March 2025
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional

UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fourty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
        "ninety": 90}
SCALES = {"hundred": 100, "thousand": 1000, "lakh": 100000, "lakhs": 100000, "lac": 100000, "lacs": 100000,
          "crore": 10000000, "crores": 10000000, "million": 1000000, "billion": 1000000000}
ORDINAL_WORDS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8,
                 "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12}

MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                        "september", "october", "november", "december"], start=1)}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())})
MONTHS["sept"] = 9

NUMBER_WORD_RE = r"(?:" + "|".join(sorted(list(UNITS) + list(TENS) + list(SCALES) + ["and"], key=len, reverse=True)) + r")"


def words_to_number(text: str) -> Optional[Decimal]:
    """'One Lakh Fifty Thousand' -> 150000 ; 'sixty' -> 60 ; returns None if no number words."""
    tokens = re.findall(r"[a-zA-Z]+", text.lower().replace("-", " "))
    total = 0
    current = 0
    seen = False
    for tok in tokens:
        if tok in ("and", "only", "rupees", "rupee", "rs", "inr", "paise", "the", "sum", "of"):
            continue
        if tok in UNITS:
            current += UNITS[tok]
            seen = True
        elif tok in TENS:
            current += TENS[tok]
            seen = True
        elif tok == "hundred":
            current = (current or 1) * 100
            seen = True
        elif tok in SCALES:
            scale = SCALES[tok]
            current = (current or 1) * scale
            total += current
            current = 0
            seen = True
        else:
            if seen:
                break
    if not seen:
        return None
    return Decimal(total + current)


@dataclass
class Amount:
    value: Decimal
    currency: str
    start: int
    end: int
    raw: str
    words_value: Optional[Decimal] = None

    @property
    def words_match(self) -> Optional[bool]:
        if self.words_value is None:
            return None
        return self.words_value == self.value


_CUR = r"(?P<cur>Rs\.?|Rs|INR|₹|Rupees|USD|US\$|\$|EUR|€|GBP|£|AED|SGD)"
_NUM = r"(?P<num>\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
_SCALE = r"(?:\s*(?P<scale>lakhs?|lacs?|crores?|million|mn|cr\.?|k)\b)?"
AMOUNT_RE = re.compile(_CUR + r"\s*" + _NUM + r"\s*(?:/-)?" + _SCALE, re.IGNORECASE)
AMOUNT_WORDS_RE = re.compile(r"\((?:\s*(?:Rupees|INR|Rs\.?|US\s*Dollars|Dollars|USD))?\s*(?P<words>[A-Za-z][A-Za-z\s\-,]+?)\s*(?:only)?\s*\)",
                             re.IGNORECASE)

CURRENCY_MAP = {"rs": "INR", "rs.": "INR", "inr": "INR", "₹": "INR", "rupees": "INR", "usd": "USD", "us$": "USD", "$": "USD",
                "eur": "EUR", "€": "EUR", "gbp": "GBP", "£": "GBP", "aed": "AED", "sgd": "SGD"}


def _scale_mult(s: Optional[str]) -> int:
    if not s:
        return 1
    s = s.lower().rstrip(".")
    if s.startswith("lakh") or s.startswith("lac"):
        return 100000
    if s.startswith("crore") or s == "cr":
        return 10000000
    if s in ("million", "mn"):
        return 1000000
    if s == "k":
        return 1000
    return 1


def find_amounts(text: str) -> list[Amount]:
    out = []
    for m in AMOUNT_RE.finditer(text):
        num = m.group("num").replace(",", "")
        try:
            val = Decimal(num) * _scale_mult(m.group("scale"))
        except InvalidOperation:
            continue
        cur = CURRENCY_MAP.get(m.group("cur").lower().strip(), "INR")
        # words in brackets immediately following
        tail = text[m.end(): m.end() + 160]
        wv = None
        wm = AMOUNT_WORDS_RE.match(tail.lstrip()) if tail.lstrip().startswith("(") else None
        end = m.end()
        if wm:
            wv = words_to_number(wm.group("words"))
            end = m.end() + (len(tail) - len(tail.lstrip())) + wm.end()
        out.append(Amount(val, cur, m.start(), end, text[m.start():end], wv))
    return out


PERCENT_RE = re.compile(r"(?P<num>\d+(?:\.\d+)?)\s*(?:%|per\s*cent|percent|p\.?c\.?)", re.IGNORECASE)


def find_percents(text: str) -> list[tuple[Decimal, int, int]]:
    return [(Decimal(m.group("num")), m.start(), m.end()) for m in PERCENT_RE.finditer(text)]


DURATION_RE = re.compile(
    r"(?:(?P<num>\d+(?:\.\d+)?)\s*(?:\((?P<w1>[a-z\s\-]+)\)\s*)?|(?P<words>(?:" + NUMBER_WORD_RE + r"[\s\-]*){1,4})\s*(?:\((?P<n2>\d+)\)\s*)?)"
    r"(?P<unit>calendar\s+months?|months?|years?|yrs?|days?)\b", re.IGNORECASE)


def find_durations(text: str) -> list[tuple[int, int, int, str]]:
    """Return (value_in_months (days kept as negative days), start, end, unit)."""
    out = []
    for m in DURATION_RE.finditer(text):
        if m.group("num"):
            v = Decimal(m.group("num"))
        elif m.group("n2"):
            v = Decimal(m.group("n2"))
        else:
            w = words_to_number(m.group("words") or "")
            if w is None:
                continue
            v = w
        unit = m.group("unit").lower()
        if unit.startswith("year") or unit.startswith("yr"):
            months = int(v * 12)
            out.append((months, m.start(), m.end(), "months"))
        elif "month" in unit:
            out.append((int(v), m.start(), m.end(), "months"))
        else:
            out.append((-int(v), m.start(), m.end(), "days"))
    return out


# ---------------------------------------------------------------------------- dates
_ORD = r"(?P<d>\d{1,2})(?:st|nd|rd|th)?"
_MON = r"(?P<m>jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_YEAR = r"(?P<y>\d{4})"
DATE_PATTERNS = [
    re.compile(_ORD + r"\s+day\s+of\s+" + _MON + r"\.?,?\s*(?:in\s+the\s+year\s+)?" + _YEAR, re.I),
    re.compile(_ORD + r"[\s\-\.]*" + _MON + r"\.?[\s,\-\.]*" + _YEAR, re.I),
    re.compile(_MON + r"\.?\s+" + _ORD + r",?\s*" + _YEAR, re.I),
    re.compile(r"(?P<y>\d{4})-(?P<mm>\d{1,2})-(?P<d>\d{1,2})"),
    re.compile(r"(?<![\d/.\-])(?P<d>\d{1,2})[/.\-](?P<mm>\d{1,2})[/.\-](?P<y>\d{4})(?![\d])"),
]


@dataclass
class FoundDate:
    value: date
    start: int
    end: int
    raw: str


def find_dates(text: str) -> list[FoundDate]:
    found: list[FoundDate] = []
    taken: list[tuple[int, int]] = []
    for pat in DATE_PATTERNS:
        for m in pat.finditer(text):
            if any(not (m.end() <= a or m.start() >= b) for a, b in taken):
                continue
            try:
                d = int(m.group("d"))
                y = int(m.group("y"))
                if m.groupdict().get("m"):
                    key = m.group("m").lower().rstrip(".")
                    mon = MONTHS.get(key) or MONTHS[key[:3]]
                else:
                    mon = int(m.group("mm"))
                dt = date(y, mon, d)
            except (ValueError, KeyError, IndexError):
                continue
            if not (1950 <= dt.year <= 2100):
                continue
            found.append(FoundDate(dt, m.start(), m.end(), m.group(0)))
            taken.append((m.start(), m.end()))
    return sorted(found, key=lambda f: f.start)


def ordinal_day_number(token: str) -> Optional[int]:
    token = token.lower().strip()
    m = re.match(r"(\d{1,2})(st|nd|rd|th)?$", token)
    if m:
        return int(m.group(1))
    return ORDINAL_WORDS.get(token)


def normalise(text: str) -> str:
    """Normalise for fuzzy matching: unify quotes/dashes, collapse whitespace, lower-case."""
    t = (text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
         .replace("–", "-").replace("—", "-").replace(" ", " ").replace("₹", "rs "))
    t = re.sub(r"\s+", " ", t)
    return t.strip().lower()
