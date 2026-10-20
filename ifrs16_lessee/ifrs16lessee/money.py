"""Decimal helpers: explicit rounding policy and date arithmetic. Floats are never used for ledger amounts."""
from __future__ import annotations

import calendar
import datetime as dt
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, ROUND_DOWN, ROUND_UP, Decimal, getcontext

getcontext().prec = 40          # working precision for discount factors; ledger amounts are quantised explicitly

D = Decimal
ZERO = D(0)
MODES = {'ROUND_HALF_UP': ROUND_HALF_UP, 'ROUND_HALF_EVEN': ROUND_HALF_EVEN, 'ROUND_DOWN': ROUND_DOWN, 'ROUND_UP': ROUND_UP}


def dec(v) -> Decimal:
    """Convert user/DB input to Decimal without passing through binary floating point."""
    if isinstance(v, Decimal):
        return v
    if isinstance(v, float):
        return Decimal(repr(v))
    if v is None or v == '':
        return ZERO
    return Decimal(str(v).replace(',', '').strip())


@dataclass(frozen=True)
class RoundingPolicy:
    """Every ledger amount is rounded to `decimals` places using `mode` at the moment it is produced."""
    decimals: int = 2
    mode: str = 'ROUND_HALF_UP'

    def q(self, x) -> Decimal:
        return dec(x).quantize(Decimal(1).scaleb(-self.decimals), rounding=MODES[self.mode])

    def to_dict(self):
        return {'decimals': self.decimals, 'mode': self.mode}

    @staticmethod
    def from_dict(d):
        return RoundingPolicy(int(d.get('decimals', 2)), d.get('mode', 'ROUND_HALF_UP'))


# ------------------------------------------------------------------ dates
def parse_date(v) -> dt.date:
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    s = str(v).strip()
    for f in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d %b %Y', '%d-%b-%Y'):
        try:
            return dt.datetime.strptime(s, f).date()
        except ValueError:
            pass
    raise ValueError(f"Cannot read date '{v}'. Use YYYY-MM-DD.")


def add_months(d: dt.date, n: int, anchor_day: int | None = None) -> dt.date:
    """Add months keeping the anchor day, clamped to month end (31 Jan + 1 month = 28/29 Feb)."""
    y, m = divmod(d.year * 12 + (d.month - 1) + n, 12)
    m += 1
    day = min(anchor_day or d.day, calendar.monthrange(y, m)[1])
    return dt.date(y, m, day)


def days_between(a: dt.date, b: dt.date) -> int:
    return (b - a).days


FREQ_MONTHS = {'monthly': 1, 'quarterly': 3, 'semi-annual': 6, 'annual': 12}


# ------------------------------------------------------------------ discounting
DAY_COUNTS = ('ACT/365', 'ACT/360', '30E/360')
COMPOUNDING = {'annual': 1, 'semi-annual': 2, 'quarterly': 4, 'monthly': 12}


def year_fraction(a: dt.date, b: dt.date, convention: str) -> Decimal:
    if b == a:
        return ZERO
    if convention == 'ACT/365':
        return D((b - a).days) / D(365)
    if convention == 'ACT/360':
        return D((b - a).days) / D(360)
    if convention == '30E/360':
        d1, d2 = min(a.day, 30), min(b.day, 30)
        return D(360 * (b.year - a.year) + 30 * (b.month - a.month) + (d2 - d1)) / D(360)
    raise ValueError(f'Unknown day-count convention {convention}')


def growth_factor(a: dt.date, b: dt.date, rate: Decimal, day_count: str, compounding: str) -> Decimal:
    """(1 + r/m)^(m*t): value at b of 1 unit held from a. `rate` is the annual rate as a fraction (0.05 = 5%)."""
    if b == a:
        return D(1)
    m = D(COMPOUNDING[compounding])
    t = year_fraction(a, b, day_count)
    base = D(1) + rate / m
    return base ** (m * t)
