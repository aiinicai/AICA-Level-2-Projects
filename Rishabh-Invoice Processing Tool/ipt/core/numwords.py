"""Indian 'amount in words' -> number ('Ninety One Thousand Eight Hundred Seventy Nine Rupees
and Fifty Paise Only' -> 91879.50). Returns None unless every word is understood."""
from __future__ import annotations

import re
from decimal import Decimal

UNITS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
    "sixteen seventeen eighteen nineteen".split())}
TENS = {w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
SCALES = {"hundred": 100, "thousand": 1000, "lakh": 100000, "lakhs": 100000, "lac": 100000, "lacs": 100000,
          "crore": 10000000, "crores": 10000000, "million": 1000000}
SKIP = {"and", "only", "rupees", "rupee", "inr", "rs", "indian", "rupee.", "amount", "chargeable", "in", "words",
        "total", "tax", "of", "a"}


def _number(words: list[str]) -> int | None:
    total, current, seen = 0, 0, False
    for w in words:
        if w in UNITS:
            current += UNITS[w]
        elif w in TENS:
            current += TENS[w]
        elif w == "hundred":
            current = (current or 1) * 100
        elif w in SCALES:
            total += (current or 1) * SCALES[w]
            current = 0
        else:
            return None
        seen = True
    return total + current if seen else None


def words_to_amount(text: str) -> Decimal | None:
    t = re.sub(r"[^a-z ]", " ", (text or "").lower())
    t = re.sub(r"\bfourty\b", "forty", t)
    parts = re.split(r"\bpaise\b|\bpaisa\b", t)
    main = t.split()
    paise = 0
    m = re.search(r"\band\b((?:\s+\w+){1,3})\s+paise", t)
    if m:
        p = _number([w for w in m.group(1).split() if w not in SKIP])
        if p is None or p >= 100:
            return None
        paise = p
        main = t[:m.start()].split()
    elif len(parts) > 1:
        return None
    words = [w for w in main if w not in SKIP]
    rupees = _number(words)
    if rupees is None or rupees == 0:
        return None
    return Decimal(rupees) + Decimal(paise) / 100
