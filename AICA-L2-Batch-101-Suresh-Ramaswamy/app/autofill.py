"""Automatic completion of invoice data, so staff only have to supply the bare minimum.

* Place of supply  - taken from the first two digits (state code) of the recipient GSTIN.
                     Unregistered customers: exports -> 96 (Other Country), otherwise the supplier's own state
                     (flagged for confirmation - the real place of supply is where the goods are delivered).
* Tax amounts      - IGST / CGST / SGST are calculated as taxable value x rate:
                     inter-state, SEZ, deemed export, export with payment  -> IGST
                     intra-state                                           -> CGST + SGST (half each)
                     reverse charge, export / SEZ without payment of tax   -> no tax
All functions are pure (no UI, no database) so they are used by the Excel/PDF import, the review screen
and the Master Template reader alike.
"""
from decimal import Decimal
from typing import Iterable, List, Tuple

from .gstin import is_valid_structure, state_of
from .models import Line
from .utils import D, q2, parse_rates, snap_rate, ZERO

IGST_INVOICE_TYPES = ("sez supplies with payment", "sez supplies without payment", "deemed exp",
                      "intra-state supplies attracting igst")
EXPORT_POS = "96"


def flag(settings: dict, key: str, default: str = "1") -> bool:
    return str((settings or {}).get(key, default)).strip().lower() in ("1", "true", "yes", "y")


def pos_from_gstin(gstin: str) -> str:
    """State code of a (structurally valid) GSTIN, else ''."""
    g = (gstin or "").strip().upper()
    return state_of(g) if g and is_valid_structure(g) else ""


def default_pos(gstin: str, own_state: str, is_export: bool = False) -> Tuple[str, str]:
    """-> (pos, how) where how is 'gstin' | 'export' | 'supplier' | ''."""
    p = pos_from_gstin(gstin)
    if p:
        return p, "gstin"
    if is_export:
        return EXPORT_POS, "export"
    return (own_state, "supplier") if own_state else ("", "")


def tax_split(taxable: Decimal, rate: Decimal, interstate: bool) -> Tuple[Decimal, Decimal, Decimal]:
    """(igst, cgst, sgst) for taxable x rate."""
    if not taxable or not rate:
        return ZERO, ZERO, ZERO
    if interstate:
        return q2(taxable * rate / 100), ZERO, ZERO
    half = q2(taxable * rate / 200)
    return ZERO, half, half


def _is_export(l: Line) -> bool:
    return (l.invoice_type or "").lower().startswith("export") or bool(l.export_type) or l.pos == EXPORT_POS


def _no_tax(l: Line) -> bool:
    return (l.reverse_charge == "Y" or l.export_type == "WOPAY"
            or (l.invoice_type or "").lower() == "sez supplies without payment")


def _interstate(l: Line, own_state: str) -> bool:
    if (l.invoice_type or "").lower() in IGST_INVOICE_TYPES or _is_export(l):
        return True
    return bool(l.pos and own_state and l.pos != own_state)


def _note(l: Line, text: str) -> None:
    if text not in (l.note or ""):
        l.note = (l.note + "; " if l.note else "") + text


def autofill_line(l: Line, own_state: str, settings: dict, tol: Decimal = None, tax: bool = True) -> List[str]:
    """Complete place of supply and tax amounts of one line in place. Returns what was changed."""
    changes: List[str] = []
    tol = tol if tol is not None else D((settings or {}).get("rounding_tolerance", "1.00"))
    # ---- place of supply
    if flag(settings, "auto_pos") and not l.pos:
        p, how = default_pos(l.recipient_gstin, own_state, _is_export(l))
        if p:
            l.pos = p
            changes.append(f"place of supply {p} ({how})")
            if how == "supplier":
                _note(l, "Place of supply assumed = supplier's state (unregistered customer) - confirm")
    # ---- rate from tax amounts when no rate was given
    if tax and l.taxable and not l.rate and l.tax_total:
        l.rate = snap_rate(l.taxable, l.tax_total, parse_rates((settings or {}).get("valid_rates", "")))
        changes.append(f"rate {l.rate} inferred from tax amounts")
    # ---- tax = taxable x rate
    if tax and l.taxable and l.rate is not None:
        if _no_tax(l):
            new = (ZERO, ZERO, ZERO)
        else:
            new = tax_split(l.taxable, l.rate, _interstate(l, own_state))
        cur = (l.igst, l.cgst, l.sgst)
        if flag(settings, "auto_tax"):
            if new != cur:
                if l.tax_total and abs(sum(new, ZERO) - l.tax_total) > tol:
                    _note(l, f"Tax in source ({q2(l.tax_total)}) replaced by taxable x rate ({q2(sum(new, ZERO))})")
                l.igst, l.cgst, l.sgst = new
                changes.append(f"tax {q2(sum(new, ZERO))} = taxable x {l.rate}%")
    return changes


def autofill_lines(lines: Iterable[Line], own_state: str, settings: dict) -> int:
    """Run autofill_line over many lines; returns how many lines changed."""
    n = 0
    for l in lines:
        if autofill_line(l, own_state, settings):
            n += 1
    return n
