"""Choose the invoice totals by arithmetic when OCR / layout rules are unsure.

Every number printed on the invoice is a candidate. A combination is accepted only if

    taxable × GST slab rate ≈ tax          (CGST = SGST = half rate, or IGST = full rate)
    taxable + tax (+ round off ≤ ₹1) ≈ invoice total

and **exactly one** combination fits. Nothing is invented: all three numbers must be printed on
the page. OCR often reads the rupee sign '₹' as '7', '2', 'z' or '%' ('₹91,879' -> '791,879'), so a
number that starts with such a character is also tried without it; arithmetic decides.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

# CGST/SGST half rates (%) in use before and after the 22-09-2025 rate change
HALF_RATES = [Decimal(x) for x in ("0.125", "0.75", "1.5", "2.5", "3", "6", "9", "14", "20")]
TAX_TOLERANCE = Decimal("0.06")       # rounding of tax per line / per item
MAX_ROUND_OFF = Decimal("1.00")
MIN_TAXABLE = Decimal("50")
NUM_RE = re.compile(r"(?<![\w.,/-])([₹7z2%F]?)(\d{1,3}(?:,\d{2,3})+(?:\.\d{1,2})?|\d+\.\d{1,2}|\d{1,7})(?![\w/-]|[.,]\d)")


@dataclass
class Solution:
    taxable: Decimal
    cgst: Decimal | None
    sgst: Decimal | None
    igst: Decimal | None
    total: Decimal

    @property
    def round_off(self) -> Decimal:
        return self.total - self.taxable - (self.cgst or 0) - (self.sgst or 0) - (self.igst or 0)


def _dec(s: str) -> Decimal | None:
    try:
        return Decimal(s.replace(",", "")).quantize(Decimal("0.01"))
    except ArithmeticError:
        return None


# OCR often breaks the decimal point of a printed amount into a space ('24,898 25') or reads the thousands
# comma as a dot ('1.244 92', '1.056.24'). These readings are added as extra candidates; arithmetic decides.
SPACED_RE = re.compile(r"(?<![\d.,])(\d{1,3}(?:[.,]\d{3})*)[ .](\d{2})(?![\d%]|[.,]\d)")


def candidates(texts: list[str], extended: bool = False) -> set[Decimal]:
    out: set[Decimal] = set()
    for t in texts:
        for m in (SPACED_RE.finditer(t) if extended else ()):
            whole = m.group(1).replace(",", "").replace(".", "")
            if len(whole) >= 3:
                d = _dec(f"{whole}.{m.group(2)}")
                if d is not None and d > 0:
                    out.add(d)
        for m in NUM_RE.finditer(t):
            prefix, body = m.group(1), m.group(2)
            d = _dec(body)
            if d is None or d <= 0 or d > Decimal("100000000"):
                continue
            if prefix in ("₹", "") :
                out.add(d)
            else:
                out.add(d)                         # '₹' misread as a separate leading character
                whole = _dec(prefix + body) if prefix.isdigit() else None
                if whole is not None:
                    out.add(whole)                 # ...or a genuine leading digit
    return out


def solve(texts: list[str], intra: bool | None) -> Solution | None:
    """The unique (taxable, tax, total) combination printed on the invoice, else None. Broken decimal
    points ('24,898 25') are tried only when the clean readings give no answer."""
    return _solve(texts, intra, False) or _solve(texts, intra, True)


def _solve(texts: list[str], intra: bool | None, extended: bool) -> Solution | None:
    nums = sorted(candidates(texts, extended))
    pool = set(nums)
    found: dict[tuple, Solution] = {}
    fit: dict[tuple, Decimal] = {}
    for t in nums:
        if t < MIN_TAXABLE:
            continue          # tiny numbers (quantities, dates) make accidental combinations
        for half in HALF_RATES:
            for split in ((True, False) if intra is None else ((intra,))):
                rate = half if split else half * 2
                expected = (t * rate / 100).quantize(Decimal("0.01"))
                taxes = [x for x in (expected + d for d in _steps(TAX_TOLERANCE)) if x in pool and x > 0]
                for tax in taxes:
                    gross = t + (tax * 2 if split else tax)
                    for total in _near(gross, pool):
                        if total == t or total == tax:
                            continue
                        sol = Solution(t, tax if split else None, tax if split else None,
                                       None if split else tax, total)
                        found[(t, tax, split, total)] = sol
                        fit[(t, tax, split)] = min(fit.get((t, tax, split), Decimal(9)), abs(t * rate / 100 - tax))
    if not found:
        return None
    # the same tax split may round to two totals (e.g. 91,879.08 printed as 91,879 and also 91,879.07);
    # prefer a whole-rupee total, then the smallest round off
    by_base: dict[tuple, list[Solution]] = {}
    for (t, tax, split, _), sol in found.items():
        by_base.setdefault((t, tax, split), []).append(sol)
    if len(by_base) != 1:
        # two readings of the same taxable value ('21,124.80' and a broken '21124') give the same tax and
        # total: the one whose tax matches to the paisa wins - only if every candidate shares that tax
        if len({(tax, split) for (_, tax, split) in by_base}) != 1:
            return None
        ranked = sorted(by_base, key=lambda k: fit[k])
        if not (fit[ranked[0]] <= Decimal("0.005") and fit[ranked[1]] >= Decimal("0.01")):
            return None
        by_base = {ranked[0]: by_base[ranked[0]]}
    sols = sorted(next(iter(by_base.values())),
                  key=lambda s: (s.total != s.total.to_integral_value(), abs(s.round_off)))
    return sols[0]


def _steps(tol: Decimal):
    n = int(tol / Decimal("0.01"))
    return [Decimal(k) / 100 for k in range(-n, n + 1)]


def _near(value: Decimal, pool: set[Decimal]) -> list[Decimal]:
    lo, hi = value - MAX_ROUND_OFF, value + MAX_ROUND_OFF
    return [p for p in pool if lo <= p <= hi]
