"""High-precision decimal helpers used by the accounting engine.

All balances are held as :class:`decimal.Decimal`. Binary floating point is never
used for accounting amounts (spec section 32). Intermediate values are carried at
40 significant digits; amounts are rounded to the configured currency decimals only
when they are presented or booked.
"""
from __future__ import annotations

from decimal import Decimal, Context, localcontext, ROUND_HALF_UP, ROUND_HALF_EVEN, InvalidOperation
from functools import wraps
from typing import Any

ENGINE_PRECISION = 40
ENGINE_CONTEXT = Context(prec=ENGINE_PRECISION, rounding=ROUND_HALF_EVEN)

ZERO = Decimal(0)
ONE = Decimal(1)
HUNDRED = Decimal(100)


def D(value: Any, default: Decimal | None = None) -> Decimal:
    """Convert *value* to Decimal without passing through binary float artefacts."""
    if value is None or value == "":
        if default is not None:
            return default
        return ZERO
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return Decimal(int(value))
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        # repr() gives the shortest round-tripping decimal representation
        return Decimal(repr(value))
    text = str(value).strip().replace(",", "").replace("₹", "")
    if text.lower().startswith("rs"):
        text = text[2:].lstrip(". ")
    try:
        return Decimal(text)
    except InvalidOperation as exc:  # pragma: no cover - defensive
        raise ValueError(f"Not a valid number: {value!r}") from exc


def q(value: Any, places: int = 2) -> Decimal:
    """Round half-up to *places* decimals (accounting rounding)."""
    exp = Decimal(1).scaleb(-places)
    res = D(value).quantize(exp, rounding=ROUND_HALF_UP)
    return res if res != 0 else abs(res)   # never return negative zero


def pct(rate_percent: Any) -> Decimal:
    """9.5 -> 0.095"""
    return D(rate_percent) / HUNDRED


def dpow(base: Decimal, exponent: Decimal) -> Decimal:
    """base ** exponent at engine precision (supports fractional exponents)."""
    with localcontext(ENGINE_CONTEXT):
        if exponent == ZERO:
            return ONE
        if base == ONE:
            return ONE
        return base ** exponent


def engine_context(func):
    """Decorator: run the function under the engine's 40-digit decimal context."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        with localcontext(ENGINE_CONTEXT):
            return func(*args, **kwargs)

    return wrapper


def fmt_money(value: Any, places: int = 2, indian: bool = True, symbol: str = "") -> str:
    """Format a number with Indian (12,34,567.00) or international grouping."""
    v = q(value, places)
    neg = v < 0
    v = abs(v)
    s = f"{v:.{places}f}"
    whole, _, frac = s.partition(".")
    if indian and len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    elif not indian:
        whole = f"{int(whole):,}"
    out = whole + ("." + frac if places else "")
    out = symbol + out
    return f"({out})" if neg else out


def to_jsonable(value: Any) -> Any:
    """Recursively convert Decimals/dates for JSON output (Decimals as strings)."""
    from datetime import date, datetime
    from dataclasses import is_dataclass, asdict
    from enum import Enum

    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {k: to_jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(v) for v in value]
    return value
