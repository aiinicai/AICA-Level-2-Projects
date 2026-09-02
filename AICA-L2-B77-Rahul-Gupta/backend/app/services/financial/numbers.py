"""Indian financial number parsing and formatting.

Handles: ₹/INR symbols, Indian comma grouping (1,25,00,000), lakh/crore units,
parenthesised negatives, thousands/millions, and display formatting back to
Indian units. All values normalise to absolute numeric INR.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

LAKH = 100_000.0
CRORE = 10_000_000.0

_UNIT_MULTIPLIERS: dict[str, float] = {
    "crore": CRORE, "crores": CRORE, "cr": CRORE, "cr.": CRORE,
    "lakh": LAKH, "lakhs": LAKH, "lac": LAKH, "lacs": LAKH,
    "thousand": 1_000.0, "thousands": 1_000.0, "'000": 1_000.0, "000s": 1_000.0,
    "million": 1_000_000.0, "millions": 1_000_000.0, "mn": 1_000_000.0,
    "billion": 1_000_000_000.0, "bn": 1_000_000_000.0,
    "inr": 1.0, "rs": 1.0, "rs.": 1.0, "rupees": 1.0, "": 1.0,
}

_NUM_RE = re.compile(r"[-+]?[\d,]*\.?\d+")


@dataclass
class ParsedAmount:
    original: str
    value: float  # absolute INR
    unit: str  # unit detected/applied


def detect_unit_multiplier(text: str) -> tuple[float, str]:
    """Detect a unit word inside free text; returns (multiplier, unit_name)."""
    t = text.lower()
    for token, mult in _UNIT_MULTIPLIERS.items():
        if token and re.search(rf"(?<![a-z]){re.escape(token)}(?![a-z])", t):
            if token in ("inr", "rs", "rs.", "rupees"):
                continue
            return mult, token
    return 1.0, ""


def parse_amount(raw: str | float | int | None, default_unit_multiplier: float = 1.0) -> float | None:
    """Parse a displayed amount into absolute INR.

    ``default_unit_multiplier`` applies when the string itself carries no unit
    (e.g. a statement column headed "₹ in Lakhs" → pass 1e5).
    Returns None when no number can be found.
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw) * default_unit_multiplier
    s = str(raw).strip()
    if not s or s in {"-", "--", "—", "NA", "N.A.", "nil", "Nil", "NIL"}:
        return None

    negative = False
    if re.search(r"\(\s*[\d,.]+\s*\)", s):
        negative = True
    if s.lstrip().startswith("-"):
        negative = True

    cleaned = s.replace("₹", " ").replace("Rs.", " ").replace("Rs", " ").replace("INR", " ")
    inline_mult, unit = detect_unit_multiplier(cleaned)
    m = _NUM_RE.search(cleaned.replace("(", " ").replace(")", " "))
    if not m:
        return None
    num_str = m.group(0).replace(",", "")
    try:
        value = float(num_str)
    except ValueError:
        return None
    value = abs(value)
    mult = inline_mult if unit else default_unit_multiplier
    value = round(value * mult, 2)  # kill float dust from unit multiplication
    return -value if negative else value


def to_crore(value_inr: float | None) -> float | None:
    return None if value_inr is None else value_inr / CRORE


def to_lakh(value_inr: float | None) -> float | None:
    return None if value_inr is None else value_inr / LAKH


def format_indian(value: float) -> str:
    """Format an absolute number with Indian comma grouping (12,34,56,789)."""
    neg = value < 0
    value = abs(value)
    whole = int(round(value))
    s = str(whole)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return f"-{s}" if neg else s


def format_inr(value_inr: float | None, unit: str = "crore", decimals: int = 2, symbol: bool = True) -> str:
    """Format absolute INR into a display string like ``₹ 2.11 Cr``."""
    if value_inr is None:
        return "—"
    sym = "₹ " if symbol else ""
    if unit == "crore":
        return f"{sym}{value_inr / CRORE:,.{decimals}f} Cr"
    if unit == "lakh":
        return f"{sym}{value_inr / LAKH:,.{decimals}f} L"
    return f"{sym}{format_indian(value_inr)}"
