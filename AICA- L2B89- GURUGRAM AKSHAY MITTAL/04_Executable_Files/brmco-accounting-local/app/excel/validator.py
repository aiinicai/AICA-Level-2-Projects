"""Cell-level parsing and validation of Excel rows.

Converts raw cell values into typed Python values (date, Decimal, bool, canonical
state names...) and reports problems with the exact row and column. Business
rules (GST consistency, balancing, ledgers, duplicates) live in
``accounting.validation``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from openpyxl.utils.datetime import from_excel

from app.accounting.gst import CGST_RATES, IGST_RATES, gstin_error, normalise_state
from app.accounting.models import ValidationIssue
from app.excel.reader import RawRow
from app.excel.template_spec import Column, TemplateSpec

_DATE_FORMATS = ("%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d", "%d-%b-%Y", "%d-%b-%y", "%d %b %Y",
                 "%d-%m-%y", "%d/%m/%y")
_YES = {"yes", "y", "true", "1"}
_NO = {"no", "n", "false", "0"}


@dataclass
class ParsedRow:
    row: int
    values: dict[str, Any]
    raw: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        v = self.values.get(key)
        return default if v is None else v


class FieldError(ValueError):
    pass


def _blank(v: Any) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def parse_text(v: Any) -> str:
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, (datetime, date)):
        return v.strftime("%d-%m-%Y")
    return re.sub(r"\s+", " ", str(v)).strip()


def parse_date(v: Any) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if 20000 < v < 80000:  # Excel serial date stored as a number
            return from_excel(v).date()
        raise FieldError(f'"{v}" is not a valid date. Use DD-MM-YYYY.')
    text = str(v).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise FieldError(f'"{text}" is not a valid date. Use DD-MM-YYYY.')


def parse_decimal(v: Any) -> Decimal:
    if isinstance(v, bool):
        raise FieldError(f'"{v}" is not a number.')
    if isinstance(v, (int, Decimal)):
        return Decimal(v)
    if isinstance(v, float):
        return Decimal(repr(v)).quantize(Decimal("0.000001")).normalize()
    text = str(v).strip().replace(",", "").replace("₹", "").replace("Rs.", "").replace("%", "").strip()
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    try:
        d = Decimal(text)
    except InvalidOperation:
        raise FieldError(f'"{v}" is not a valid number.') from None
    if not d.is_finite():
        raise FieldError(f'"{v}" is not a valid number.')
    return -d if negative else d


def _parse(col: Column, v: Any) -> Any:
    t = col.type
    if t == "text":
        return parse_text(v)
    if t == "date":
        return parse_date(v)
    if t in ("amount", "qty", "rate", "gst_rate", "signed"):
        d = parse_decimal(v)
        if t != "signed" and d < 0:
            raise FieldError(f"{col.header} cannot be negative ({d}).")
        if t in ("amount", "signed") and d != d.quantize(Decimal("0.01")):
            if abs(d - d.quantize(Decimal("0.01"))) > Decimal("0.0000001"):
                raise FieldError(f"{col.header} has more than 2 decimal places ({d}).")
            d = d.quantize(Decimal("0.01"))
        if t == "gst_rate":
            allowed = CGST_RATES if col.key in ("cgst_rate", "sgst_rate") else IGST_RATES
            if d not in allowed:
                shown = ", ".join(format(r.normalize(), "f") for r in sorted(allowed))
                raise FieldError(f"{col.header} {d.normalize()}% is not a valid GST rate. Allowed: {shown}.")
        if t == "rate" and d > 500:
            raise FieldError(f"{col.header} {d}% looks wrong.")
        return d
    if t == "yesno":
        s = str(v).strip().lower()
        if s in _YES:
            return True
        if s in _NO:
            return False
        raise FieldError(f'{col.header} must be Yes or No (found "{v}").')
    if t == "gstin":
        g = str(v).strip().upper().replace(" ", "")
        problem = gstin_error(g)
        if problem:
            raise FieldError(problem)
        return g
    if t == "state":
        s = normalise_state(str(v))
        if not s:
            raise FieldError(f'"{v}" is not a recognised Indian state / UT. Pick one from the dropdown.')
        return s
    if t == "choice":
        s = str(v).strip().lower()
        for choice in col.choices:
            if choice.lower() == s:
                return choice
        raise FieldError(f'{col.header} must be one of: {", ".join(col.choices)} (found "{v}").')
    raise AssertionError(f"Unknown column type {t}")


def parse_rows(spec: TemplateSpec, rows: list[RawRow]) -> tuple[list[ParsedRow], list[ValidationIssue]]:
    """Parse every cell. Rows with cell errors are still returned (with the bad cell as None)
    so later checks can report further problems in the same pass."""
    parsed: list[ParsedRow] = []
    issues: list[ValidationIssue] = []
    for raw in rows:
        values: dict[str, Any] = {}
        for col in spec.columns:
            v = raw.values.get(col.key)
            if _blank(v):
                values[col.key] = None
                continue
            try:
                values[col.key] = _parse(col, v)
            except FieldError as exc:
                values[col.key] = None
                issues.append(ValidationIssue(severity="error", row=raw.row, column=col.header,
                                              message=str(exc), code=f"cell.{col.type}"))
        parsed.append(ParsedRow(raw.row, values, raw.values))
    return parsed, issues
