"""Reads an 'AMOUNT IN WORDS' line so it can be cross-checked against the figures.
Only used for a warning - never to populate any NIC field."""
from __future__ import annotations
import re
from decimal import Decimal

_UNITS = {"ZERO": 0, "ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5, "SIX": 6, "SEVEN": 7,
          "EIGHT": 8, "NINE": 9, "TEN": 10, "ELEVEN": 11, "TWELVE": 12, "THIRTEEN": 13,
          "FOURTEEN": 14, "FIFTEEN": 15, "SIXTEEN": 16, "SEVENTEEN": 17, "EIGHTEEN": 18,
          "NINETEEN": 19, "TWENTY": 20, "THIRTY": 30, "FORTY": 40, "FIFTY": 50, "SIXTY": 60,
          "SEVENTY": 70, "EIGHTY": 80, "NINETY": 90}
_SPELLING = {"NINTY": "NINETY", "NINTEEN": "NINETEEN", "RUPPES": "RUPEES", "RUPPEES": "RUPEES", "RUPES": "RUPEES", "FOURTY": "FORTY", "FORTEEN": "FOURTEEN", "EIGHTTEEN": "EIGHTEEN",
             "TWELVETH": "TWELVE", "THOUSANDS": "THOUSAND", "HUNDREDS": "HUNDRED", "LAKHS": "LAKH",
             "LACS": "LAKH", "LAC": "LAKH", "CRORES": "CRORE", "MILLIONS": "MILLION"}
_SCALES = {"THOUSAND": 1_000, "LAKH": 100_000, "MILLION": 1_000_000, "CRORE": 10_000_000,
           "BILLION": 1_000_000_000}
_MINOR = {"CENT", "CENTS", "PAISE", "PAISA", "FILS"}
_MAJOR = {"USD", "DOLLAR", "DOLLARS", "RUPEE", "RUPEES", "INR", "EURO", "EUROS", "EUR", "AED",
          "DIRHAM", "DIRHAMS", "POUND", "POUNDS", "GBP"}
_SKIP = {"ONLY", "US", "RS", "OF"}


def _group(tokens: list[str]) -> int | None:
    total, current, seen = 0, 0, False
    for t in tokens:
        if t in _UNITS:
            current += _UNITS[t]; seen = True
        elif t == "HUNDRED":
            current = (current or 1) * 100; seen = True
        elif t in _SCALES:
            total += (current or 1) * _SCALES[t]; current = 0; seen = True
        elif t in _SKIP or t in _MAJOR:
            continue
        else:
            return None
    return total + current if seen else None


_AND_AS_POINT = False


def words_to_amount(text: str) -> Decimal | None:
    """'THREE THOUSAND FOUR HUNDRED NINTY SIX USD THIRTY SEVEN CENT ONLY' -> 3496.37.
    Returns None when the wording cannot be read with confidence."""
    if not text:
        return None
    toks = [_SPELLING.get(t, t) for t in re.findall(r"[A-Z]+", text.upper())]
    toks = [t for t in toks if t not in {"AMOUNT", "IN", "WORDS"}]
    seq: list[tuple[str, object]] = []        # ("run", [tokens]) or ("major"/"minor", tok)
    run: list[str] = []
    for t in toks:
        if t in _UNITS or t == "HUNDRED" or t in _SCALES:
            run.append(t)
            continue
        if t in _SKIP or (t == "AND" and not (_AND_AS_POINT and run)):
            continue
        if t == "AND":
            seq.append(("run", run)); run = []
            seq.append(("point", t))
            continue
        if run:
            seq.append(("run", run)); run = []
        if t == "POINT":
            seq.append(("point", t))
        elif t in _MINOR:
            seq.append(("minor", t))
        elif t in _MAJOR:
            seq.append(("major", t))
        else:
            return None
    if run:
        seq.append(("run", run))
    major_val = minor_val = None
    for i, (kind, val) in enumerate(seq):
        if kind != "run":
            continue
        prev = seq[i - 1][0] if i > 0 else None
        nxt = seq[i + 1][0] if i + 1 < len(seq) else None
        v = _group(val)
        if v is None:
            return None
        if nxt == "point":
            target = "major"
        elif prev == "point":
            target = "minor"
        elif nxt == "minor" and (prev != "major" or major_val is not None):
            target = "minor"
        elif prev == "minor":
            target = "minor"
        else:
            target = "major"
        if target == "major":
            if major_val is not None:
                return None
            major_val = v
        else:
            if minor_val is not None:
                return None
            minor_val = v
    if major_val is None and minor_val is None:
        return None
    return Decimal(major_val or 0) + Decimal(minor_val or 0) / 100


def words_to_amounts(text: str) -> list[Decimal]:
    """All plausible readings. 'NINE HUNDRED ZERO TWO AND SIXTY SIX RUPEES' may mean ...902.66 (Indian
    invoices) or ...968; both are offered and the caller keeps the one matching the invoice figure."""
    global _AND_AS_POINT
    out = []
    for flag in (False, True):
        _AND_AS_POINT = flag
        try:
            v = words_to_amount(text)
        finally:
            _AND_AS_POINT = False
        if v is not None and v not in out:
            out.append(v)
    return out
