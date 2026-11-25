"""Cell parsers. Each returns the parsed value or raises CellError with a readable message.

Dates are day-first (Oman convention): 05/12/2026 is 5 December 2026.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from app.core.money import round_money, to_decimal
from app.importers.specs import BD_TYPES, normalise_header


class CellError(ValueError):
    pass


EXCEL_EPOCH = date(1899, 12, 30)
DATE_FORMATS = ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%d-%b-%Y", "%d %b %Y", "%d-%B-%Y",
                "%d %B %Y", "%d/%m/%y", "%d-%m-%y", "%d-%b-%y", "%Y/%m/%d")


def is_blank(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def parse_str(v) -> str:
    if is_blank(v):
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))               # cheque numbers read as numbers
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m-%d")
    return " ".join(str(v).split())


def parse_date(v) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if 20000 < v < 80000:            # Excel serial number (1954-2119)
            return EXCEL_EPOCH + timedelta(days=int(v))
        raise CellError(f"'{v}' is not a date")
    text = parse_str(v)
    if not text:
        raise CellError("date is missing")
    if " " in text and ":" in text:      # '2026-12-05 00:00:00'
        text = text.split(" ")[0]
    for fmt in DATE_FORMATS:
        try:
            d = datetime.strptime(text, fmt).date()
            if 1990 <= d.year <= 2100:
                return d
        except ValueError:
            continue
    raise CellError(f"'{text}' is not a date (use dd/mm/yyyy)")


def parse_amount(v) -> tuple[Decimal, str | None]:
    """Return (amount rounded to 3 dp, warning or None)."""
    if is_blank(v):
        raise CellError("amount is missing")
    if isinstance(v, bool):
        raise CellError("amount is not a number")
    try:
        d = to_decimal(v)
    except ValueError as exc:
        raise CellError(f"'{v}' is not an amount") from exc
    r = round_money(d)
    warn = None
    if abs(d - r) > Decimal("0.0000001"):
        warn = f"{d} rounded to {r} (3 decimals)"
    return r, warn


def parse_rate(v) -> Decimal:
    if is_blank(v):
        raise CellError("rate is missing")
    try:
        d = to_decimal(v)
    except ValueError as exc:
        raise CellError(f"'{v}' is not a rate") from exc
    if d <= 0:
        raise CellError("rate must be greater than 0")
    return d.quantize(Decimal("0.000001")).normalize()


def parse_int(v) -> int:
    if is_blank(v):
        raise CellError("number is missing")
    try:
        d = to_decimal(v)
    except ValueError as exc:
        raise CellError(f"'{v}' is not a whole number") from exc
    if d != d.to_integral_value():
        raise CellError(f"'{v}' is not a whole number")
    return int(d)


_TRUE = {"y", "yes", "true", "1", "x", "t"}
_FALSE = {"n", "no", "false", "0", "f", ""}


def parse_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    s = normalise_header(parse_str(v))
    if s in _TRUE:
        return True
    if s in _FALSE:
        return False
    raise CellError(f"'{v}' should be Y or N")


def parse_direction(v) -> str:
    s = normalise_header(parse_str(v))
    if s in ("inflow", "in", "receipt", "receipts", "income", "cr"):
        return "inflow"
    if s in ("outflow", "out", "payment", "payments", "expense", "dr"):
        return "outflow"
    raise CellError(f"'{v}' should be Inflow or Outflow")


def parse_treatment(v) -> str:
    s = normalise_header(parse_str(v))
    if s in ("fixed", "f", "non deferrable"):
        return "fixed"
    if s in ("deferrable", "d", "flexible", "deferable"):
        return "deferrable"
    raise CellError(f"'{v}' should be Fixed or Deferrable")


_BD_ALIASES = {"proceeds": "discount proceeds", "discount proceed": "discount proceeds",
               "bill discount proceeds": "discount proceeds", "new discounting": "discount proceeds",
               "lc": "lc maturity", "lc payment": "lc maturity", "lc maturity": "lc maturity",
               "bd maturity": "discount maturity", "bill discount maturity": "discount maturity",
               "discount repayment": "discount maturity"}


def parse_bd_type(v) -> str:
    s = normalise_header(parse_str(v))
    s = _BD_ALIASES.get(s, s)
    if s in BD_TYPES:
        return s
    raise CellError(f"'{v}' should be Discount proceeds, Discount maturity or LC maturity")


PARSERS = {"str": parse_str, "date": parse_date, "rate": parse_rate, "int": parse_int, "bool": parse_bool,
           "direction": parse_direction, "treatment": parse_treatment, "bd_type": parse_bd_type}
