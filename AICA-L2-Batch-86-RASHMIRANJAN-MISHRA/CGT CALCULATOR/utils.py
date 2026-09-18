"""
CAPITAL GAINS TAX COMPARISON CALCULATOR (12.5% vs 20%)
Utility Functions & Indian Currency Formatter
Author: Senior Python Developer & Tax-Audit Software Architect
"""

import math
from typing import Union, Optional


def format_inr(val: Union[float, int, str, None], show_paise: bool = False, show_symbol: bool = True) -> str:
    """
    Formats a numeric value into the Indian numbering system:
    Example:
      10000000 -> ₹1,00,00,000 (or 1,00,00,000 without symbol)
      1234567.89 -> ₹12,34,567.89 (with show_paise=True)
      -50000 -> -₹50,000
    """
    if val is None or val == "":
        return "₹0" if show_symbol else "0"

    try:
        num = float(val)
    except (ValueError, TypeError):
        return str(val)

    is_negative = num < 0
    num = abs(num)

    if show_paise:
        integer_part = int(math.floor(num))
        paise_part = f"{round((num - integer_part) * 100):02d}"
    else:
        integer_part = int(round(num))
        paise_part = None

    s = str(integer_part)
    if len(s) <= 3:
        formatted = s
    else:
        last3 = s[-3:]
        rest = s[:-3]
        # Group rest into groups of 2 from right to left
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        formatted = ",".join(groups) + "," + last3

    if show_paise:
        formatted += f".{paise_part}"

    prefix = ""
    if is_negative:
        prefix = "-"
    if show_symbol:
        prefix += "₹"

    return f"{prefix}{formatted}"


def parse_inr(s: Union[str, float, int, None]) -> float:
    """Parses a string formatted as currency or plain text into a float."""
    if s is None:
        return 0.0
    if isinstance(s, (int, float)):
        return float(s)
    clean = str(s).replace("₹", "").replace(",", "").replace(" ", "").strip()
    try:
        return float(clean)
    except ValueError:
        return 0.0
