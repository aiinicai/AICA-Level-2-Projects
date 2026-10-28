"""Number and date formatting for statements: whole rupees, Indian digit grouping, negatives in
brackets, nil shown as a dash, dates as dd/mm/yyyy."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal


def rnd(x: float, step: int = 1) -> int:
    """Round to the nearest multiple of `step` rupees, halves away from zero (step 1 = whole rupees)."""
    q = Decimal(str(round(float(x), 6))) / Decimal(step)
    return int(q.quantize(Decimal("1"), rounding=ROUND_HALF_UP)) * step


def group_indian(n: int) -> str:
    s = str(abs(n))
    head, tail = s[:-3], s[-3:]
    if not head:
        return tail
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts) + "," + tail


def inr(n: int | None) -> str:
    """12,34,567 ; (12,34,567) for negatives ; '-' for nil or not available."""
    if n is None or n == 0:
        return "-"
    return f"({group_indian(n)})" if n < 0 else group_indian(n)


def dmy(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def rs(x: float, decimals: int = 0) -> str:
    """'Rs 24,89,416' (or with paise) for use inside sentences."""
    neg = x < 0
    x = abs(x)
    whole = int(x)
    out = group_indian(whole)
    if decimals:
        out += f".{round((x - whole) * 100):02d}" if round((x - whole) * 100) < 100 else ".00"
    return f"Rs ({out})" if neg else f"Rs {out}"


# ---- presentation units ------------------------------------------------------------------------------------
# Schedule III (Division I) makes rounding off compulsory (ICAI Guidance Note, para 6.15): total income under
# Rs 100 crore is rounded to hundreds, thousands, lakhs or millions (or decimals of these); Rs 100 crore or more
# to lakhs, millions or crores. Full figures are no longer permitted. `step` is the rupee granularity a figure is
# rounded to, so every amount stays a whole multiple of it and all totals still foot exactly.
CRORE = 10_000_000


@dataclass(frozen=True)
class Unit:
    key: str
    label: str          # for a heading, for example "Rs in lakhs"
    scale: int          # rupees in one displayed unit
    decimals: int
    step: int           # amounts are rounded to a multiple of this many rupees

    def value(self, rupees: float) -> float:
        """The number to show or store: rupees expressed in this unit."""
        q = Decimal(str(round(float(rupees), 6))) / Decimal(self.scale)
        return float(q.quantize(Decimal(1).scaleb(-self.decimals), rounding=ROUND_HALF_UP))

    def fmt(self, rupees: float | None) -> str:
        """Indian grouping, brackets for negatives, '-' for nil or not available."""
        if rupees is None or abs(rupees) < self.step / 2 and self.step > 1 or rupees == 0:
            return "-"
        v = self.value(rupees)
        if v == 0:
            return "-"
        whole, frac = f"{abs(v):.{self.decimals}f}".partition(".")[::2]
        text = group_indian(int(whole)) + (f".{frac}" if self.decimals else "")
        return f"({text})" if v < 0 else text

    @property
    def number_format(self) -> str:
        body = "#,##0" + ("." + "0" * self.decimals if self.decimals else "")
        return f'{body}_);({body});"-"_)'

    @property
    def heading(self) -> str:
        return ("All amounts in Indian Rupees (Rs) unless otherwise stated" if self.key == "rupees"
                else f"{self.label}, rounded off as required by Schedule III")


UNITS = {u.key: u for u in (
    Unit("rupees", "Rs", 1, 0, 1),
    Unit("hundreds", "Rs in hundreds", 100, 0, 100),
    Unit("thousands", "Rs in thousands", 1_000, 0, 1_000),
    Unit("lakhs", "Rs in lakhs", 100_000, 2, 1_000),
    Unit("millions", "Rs in millions", 1_000_000, 2, 10_000),
    Unit("crores", "Rs in crores", CRORE, 2, 100_000),
)}


def allowed_units(total_income: float) -> list[Unit]:
    """The units Schedule III permits for a company with this total income (full rupees are not among them)."""
    keys = ["hundreds", "thousands", "lakhs", "millions"] if total_income < 100 * CRORE else ["lakhs", "millions", "crores"]
    return [UNITS[k] for k in keys]


def choose_unit(total_income: float) -> Unit:
    """A sensible permitted default: lakhs for a company under Rs 100 crore, crores above."""
    return UNITS["lakhs"] if total_income < 100 * CRORE else UNITS["crores"]


def as_unit(unit) -> Unit:
    return unit if isinstance(unit, Unit) else UNITS[unit or "rupees"]
