"""Number helpers and Indian-style formatting.

Convention used across the package:
    * Money is held in rupees (float). Display converts to Rs crore (1 crore = 1e7).
    * Percentages are held as percent numbers (12.5 means 12.5 percent), never fractions.
    * Missing values are None. NaN and infinity are converted to None by `num`.
"""

from __future__ import annotations

import math
import numbers
from typing import Any, Iterable

CRORE = 1e7


def num(x: Any) -> float | None:
    """Return x as a finite float, or None."""
    if x is None or isinstance(x, bool):
        return None
    if isinstance(x, numbers.Real):
        f = float(x)
        return f if math.isfinite(f) else None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def pct_from_fraction(x: Any) -> float | None:
    v = num(x)
    return None if v is None else v * 100.0


def safe_div(a: Any, b: Any) -> float | None:
    a, b = num(a), num(b)
    if a is None or b is None or b == 0:
        return None
    return a / b


def median(values: Iterable[Any]) -> float | None:
    vals = sorted(v for v in (num(x) for x in values) if v is not None)
    if not vals:
        return None
    mid = len(vals) // 2
    return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def cagr(first: Any, last: Any, years: float) -> float | None:
    """Compound annual growth rate in percent. None if either end is not positive."""
    first, last = num(first), num(last)
    if first is None or last is None or first <= 0 or last <= 0 or years <= 0:
        return None
    return ((last / first) ** (1.0 / years) - 1.0) * 100.0


def _group_indian(int_part: str) -> str:
    """Group digits the Indian way: 12,34,56,789."""
    if len(int_part) <= 3:
        return int_part
    head, tail = int_part[:-3], int_part[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups) + "," + tail


def fmt_num(x: Any, dp: int = 0, paren: bool = True, dash: str = "-") -> str:
    """Indian-grouped number. Negatives in brackets (research-note style) when paren=True."""
    v = num(x)
    if v is None:
        return dash
    s = f"{abs(v):.{dp}f}"
    int_part, _, dec = s.partition(".")
    body = _group_indian(int_part) + (("." + dec) if dec else "")
    if v < 0 and float(s) != 0:
        return f"({body})" if paren else f"-{body}"
    return body


def fmt_cr(x: Any, dp: int | None = None, paren: bool = True) -> str:
    """Rupees to Rs crore. Uses 1 decimal below Rs 1,000 crore unless dp is given."""
    v = num(x)
    if v is None:
        return "-"
    c = v / CRORE
    if dp is None:
        dp = 1 if abs(c) < 1000 else 0
    return fmt_num(c, dp, paren)


def fmt_pct(x: Any, dp: int = 1, signed: bool = False, paren: bool = True) -> str:
    v = num(x)
    if v is None:
        return "-"
    if signed and v > 0:
        return "+" + fmt_num(v, dp) + "%"
    return fmt_num(v, dp, paren) + "%"


def fmt_x(x: Any, dp: int = 1) -> str:
    v = num(x)
    return "-" if v is None else fmt_num(v, dp) + "x"


def fmt_rs(x: Any, dp: int | None = None) -> str:
    v = num(x)
    if v is None:
        return "-"
    if dp is None:
        dp = 2 if abs(v) < 100 else (1 if abs(v) < 1000 else 0)
    return "Rs " + fmt_num(v, dp, paren=False)


def fy_label(ts: Any) -> str:
    """Fiscal-year label. A period ending in March 2026 is FY26; other year ends use the month."""
    try:
        month, year = ts.month, ts.year
    except AttributeError:
        return str(ts)
    if month == 3:
        return f"FY{year % 100:02d}"
    return f"{ts.strftime('%b')}{year % 100:02d}"


def q_label(ts: Any) -> str:
    """Indian fiscal quarter label. June 2026 quarter is Q1FY27."""
    try:
        month, year = ts.month, ts.year
    except AttributeError:
        return str(ts)
    fy = year + 1 if month >= 4 else year
    q = {6: 1, 9: 2, 12: 3, 3: 4}.get(month)
    if q is None:
        return ts.strftime("%b%y")
    return f"Q{q}FY{fy % 100:02d}"


def clean(obj: Any) -> Any:
    """Recursively convert NaN/inf to None and numpy scalars to Python types, for JSON."""
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, bool) or obj is None or isinstance(obj, str):
        return obj
    if isinstance(obj, numbers.Integral):
        return int(obj)
    if isinstance(obj, numbers.Real):
        return num(obj)
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)
