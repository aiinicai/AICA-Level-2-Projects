"""Tally's reserved voucher types and how each affects the books (ported from voucher-types.ts)."""
from __future__ import annotations

import re

RESERVED: dict[str, tuple[bool, bool]] = {  # name -> (affects accounts, affects inventory)
    "Sales": (True, True), "Purchase": (True, True), "Receipt": (True, False), "Payment": (True, False),
    "Journal": (True, True), "Contra": (True, False), "Credit Note": (True, True), "Debit Note": (True, True),
    "Payroll": (True, False), "Delivery Note": (False, True), "Receipt Note": (False, True),
    "Rejections In": (False, True), "Rejections Out": (False, True), "Stock Journal": (False, True),
    "Manufacturing Journal": (False, True), "Material In": (False, True), "Material Out": (False, True),
    "Physical Stock": (False, False), "Sales Order": (False, False), "Purchase Order": (False, False),
    "Job Work In Order": (False, False), "Job Work Out Order": (False, False), "Memorandum": (False, False),
    "Reversing Journal": (False, False), "Attendance": (False, False),
}

_ALIASES = [(re.compile(p, re.I), b) for p, b in [
    (r"credit\s*note|sales\s*return", "Credit Note"), (r"debit\s*note|purchase\s*return", "Debit Note"),
    (r"delivery", "Delivery Note"), (r"receipt\s*note|grn", "Receipt Note"), (r"sales\s*order", "Sales Order"),
    (r"purchase\s*order", "Purchase Order"), (r"stock\s*journal", "Stock Journal"),
    (r"manufactur", "Manufacturing Journal"), (r"physical", "Physical Stock"), (r"memo", "Memorandum"),
    (r"reversing", "Reversing Journal"), (r"payroll", "Payroll"), (r"contra", "Contra"), (r"receipt", "Receipt"),
    (r"payment", "Payment"), (r"journal", "Journal"), (r"sales|invoice", "Sales"), (r"purchase", "Purchase"),
]]


def resolve_base_type(name: str, parent_of: dict[str, str | None]) -> tuple[str, bool]:
    """Reserved base via the parent chain; falls back to name heuristics (then 'known' is False)."""
    cur, seen = name, set()
    while cur and cur not in seen:
        if cur in RESERVED:
            return cur, True
        seen.add(cur)
        cur = parent_of.get(cur)
    for rx, base in _ALIASES:
        if rx.search(name):
            return base, False
    return "Unknown", False


def default_effects(base: str) -> tuple[bool, bool]:
    return RESERVED.get(base, (True, False))
