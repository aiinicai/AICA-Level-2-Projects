"""Excel-compatible rounding (ROUND half away from zero, not banker's rounding)."""
import math


def xround(x, digits=0):
    if x is None:
        return 0
    f = 10 ** digits
    v = abs(x) * f
    r = math.floor(v + 0.5 + 1e-9) / f
    r = r if x >= 0 else -r
    return int(r) if digits == 0 else r


def safe_div(a, b, default=0.0):
    try:
        return a / b if b else default
    except (TypeError, ZeroDivisionError):
        return default
