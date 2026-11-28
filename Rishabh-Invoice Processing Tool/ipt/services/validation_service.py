"""GST & accounting validation engine.

Every rule returns findings; nothing here changes invoice values. Severity:
- error   : must be fixed (or overridden by an admin with a remark) before approval
- warning : should be checked by the reviewer
"""
from __future__ import annotations

import re

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from ipt.core.gstin import validate_gstin
from ipt.core.states import STATES
from ipt.db.models import Company, FinancialYear, Invoice, ValidationResult

GST_REFORM_DATE = date(2025, 9, 22)  # GST rate rationalisation (5% / 18% / 40% structure)
STANDARD_RATES = {Decimal(x) for x in ("0", "0.1", "0.25", "1", "1.5", "3", "5", "6", "7.5", "12", "18", "28", "40")}
ZERO = Decimal("0")


@dataclass
class Finding:
    code: str
    severity: str
    message: str
    field: str = ""
    expected: str = ""
    found: str = ""


def _d(v) -> Decimal:
    return v if isinstance(v, Decimal) else (Decimal(str(v)) if v is not None else ZERO)


def _s(v) -> str:
    return "" if v is None else str(v)


def validate_invoice(inv: Invoice, company: Company, fy: FinancialYear, tolerance: Decimal,
                     duplicates: list[Invoice] | None = None, today: date | None = None) -> list[Finding]:
    f: list[Finding] = []
    today = today or date.today()
    tol = tolerance
    is_note = inv.doc_type in ("credit_note", "debit_note")

    # ---------------- parties
    if not inv.supplier_gstin:
        sev = "warning" if inv.doc_type == "bill_of_supply" else "error"
        f.append(Finding("SUPPLIER_GSTIN_MISSING", sev, "Supplier GSTIN not found. ITC cannot be claimed without it.",
                         "supplier_gstin"))
    else:
        r = validate_gstin(inv.supplier_gstin)
        if not r.valid:
            f.append(Finding("SUPPLIER_GSTIN_INVALID", "error", f"Supplier GSTIN is not valid: {r.message}",
                             "supplier_gstin", found=inv.supplier_gstin))
        elif inv.supplier_state_code and inv.supplier_state_code != inv.supplier_gstin[:2]:
            f.append(Finding("SUPPLIER_STATE_MISMATCH", "error", "Supplier state code does not match the GSTIN",
                             "supplier_state_code", inv.supplier_gstin[:2], inv.supplier_state_code))
    if company.gstin and inv.supplier_gstin and inv.supplier_gstin == company.gstin:
        f.append(Finding("SUPPLIER_IS_COMPANY", "error",
                         "Supplier GSTIN is your own GSTIN – this looks like a sales invoice", "supplier_gstin"))
    if inv.buyer_gstin:
        r = validate_gstin(inv.buyer_gstin)
        if not r.valid:
            f.append(Finding("BUYER_GSTIN_INVALID", "error", f"Buyer GSTIN is not valid: {r.message}",
                             "buyer_gstin", found=inv.buyer_gstin))
        elif company.gstin and inv.buyer_gstin != company.gstin:
            f.append(Finding("BUYER_NOT_COMPANY", "warning", "Invoice is addressed to a different GSTIN than this "
                             "company's", "buyer_gstin", company.gstin, inv.buyer_gstin))
    elif company.gstin:
        f.append(Finding("BUYER_GSTIN_MISSING", "warning", "Your GSTIN is not printed on the invoice "
                         "(B2C invoice – ITC will not appear in GSTR-2B)", "buyer_gstin", company.gstin))

    # ---------------- header
    if not inv.invoice_no:
        f.append(Finding("INVOICE_NO_MISSING", "error", "Invoice number not found", "invoice_no"))
    if not inv.invoice_date:
        f.append(Finding("INVOICE_DATE_MISSING", "error", "Invoice date not found", "invoice_date"))
    else:
        if inv.invoice_date > today:
            f.append(Finding("INVOICE_DATE_FUTURE", "error", "Invoice date is in the future", "invoice_date",
                             found=inv.invoice_date.strftime("%d-%m-%Y")))
        if not (fy.start_date <= inv.invoice_date <= fy.end_date):
            f.append(Finding("INVOICE_DATE_OUTSIDE_FY", "error",
                             f"Invoice date is outside FY {fy.label}. Switch FY or correct the date.",
                             "invoice_date", f"{fy.start_date:%d-%m-%Y} to {fy.end_date:%d-%m-%Y}",
                             inv.invoice_date.strftime("%d-%m-%Y")))
    if is_note and not inv.original_invoice_ref:
        f.append(Finding("NOTE_REF_MISSING", "warning", "Credit/debit note without original invoice reference",
                         "original_invoice_ref"))
    if (inv.currency or "INR") != "INR" and not inv.exchange_rate:
        f.append(Finding("FX_RATE_MISSING", "error", f"Invoice is in {inv.currency}; enter the exchange rate "
                         "to get INR values", "exchange_rate"))

    # ---------------- tax type: intra-state vs inter-state
    cg, sg, ig = _d(inv.cgst), _d(inv.sgst), _d(inv.igst)
    supplier_state = inv.supplier_state_code or (inv.supplier_gstin or "")[:2] or None
    pos = inv.place_of_supply
    if not pos:
        f.append(Finding("POS_MISSING", "warning", "Place of supply not found; intra/inter-state could not be "
                         "verified", "place_of_supply"))
    elif pos not in STATES:
        f.append(Finding("POS_INVALID", "error", "Place of supply is not a valid state code", "place_of_supply",
                         found=pos))
    elif supplier_state:
        if supplier_state == pos:
            if ig > tol:
                f.append(Finding("IGST_ON_INTRA", "error", "Supplier and place of supply are in the same state, "
                                 "but IGST is charged (expected CGST + SGST/UTGST)", "igst", "0.00", _s(inv.igst)))
        elif cg > tol or sg > tol:
            f.append(Finding("CGST_ON_INTER", "error", "Inter-state supply, but CGST/SGST is charged "
                             "(expected IGST)", "cgst", "0.00", f"{cg}/{sg}"))
    if abs(cg - sg) > tol:
        f.append(Finding("CGST_SGST_UNEQUAL", "error", "CGST and SGST should be equal", "sgst", _s(inv.cgst),
                         _s(inv.sgst)))

    # ---------------- line items
    items = list(inv.items)
    if not items:
        f.append(Finding("NO_ITEMS", "warning", "No line items were read. Add them in the Items tab ('Add row' below the table) – or, if you do not enter this supplier item-wise, book it to a ledger in Master Mapping (no items needed)", "items"))
    for it in items:
        label = f"Line {it.line_no}"
        if it.gst_rate is not None:
            rate = _d(it.gst_rate).normalize()
            if rate not in STANDARD_RATES:
                f.append(Finding("RATE_UNUSUAL", "warning", f"{label}: GST rate {rate}% is not a standard rate",
                                 "items", found=f"{rate}%"))
            if inv.invoice_date and rate == 40 and inv.invoice_date < GST_REFORM_DATE:
                f.append(Finding("RATE_NOT_EFFECTIVE", "warning", f"{label}: 40% applies only from 22-09-2025",
                                 "items", found="40%"))
            if inv.invoice_date and inv.invoice_date >= GST_REFORM_DATE and rate in (12, 28):
                f.append(Finding("RATE_CHECK_REFORM", "warning", f"{label}: {rate}% slab was largely replaced from "
                                 "22-09-2025 – confirm the rate for this HSN", "items", found=f"{rate}%"))
            if it.taxable_value is not None:
                expected_tax = (_d(it.taxable_value) * rate / 100).quantize(Decimal("0.01"))
                item_tax = _d(it.cgst) + _d(it.sgst) + _d(it.igst)
                if item_tax and abs(item_tax - expected_tax) > tol:
                    f.append(Finding("ITEM_TAX_MISMATCH", "warning", f"{label}: tax does not equal taxable × rate",
                                     "items", str(expected_tax), str(item_tax)))
        if it.hsn_sac:
            if not (it.hsn_sac.isdigit() and len(it.hsn_sac) in (4, 6, 8)):
                f.append(Finding("HSN_FORMAT", "warning", f"{label}: HSN/SAC should be 4, 6 or 8 digits", "items",
                                 found=it.hsn_sac))
        for name in ("qty", "rate", "taxable_value", "total"):
            if getattr(it, name) is not None and _d(getattr(it, name)) < 0:
                f.append(Finding("NEGATIVE_VALUE", "error", f"{label}: {name} is negative", "items",
                                 found=_s(getattr(it, name))))
        if it.taxable_value is None or not _d(it.taxable_value):
            f.append(Finding("ITEM_NO_AMOUNT", "error", f"{label}: no amount – probably a stray row read from the bill "
                             "(e.g. a column heading). Delete it in the Items tab, or enter its amount", "items",
                             found=(it.description or "")[:40]))
        if len(re.sub(r"[^A-Za-z]", "", it.description or "")) < 3:
            f.append(Finding("ITEM_DESC_MISSING", "warning", f"{label}: item name is missing or unreadable "
                             f"('{it.description or ''}') – Tally needs it to choose the stock item", "items",
                             found=it.description or ""))
        if it.qty is None or not _d(it.qty):
            f.append(Finding("ITEM_QTY_MISSING", "warning", f"{label}: quantity is missing – needed to import "
                             "item-wise into Tally (or book this supplier to a ledger in Master Mapping)", "items"))
        if it.qty is not None and it.rate is not None and it.taxable_value is not None:
            gross = (_d(it.qty) * _d(it.rate) - _d(it.discount)).quantize(Decimal("0.01"))
            if abs(gross - _d(it.taxable_value)) > tol:
                f.append(Finding("ITEM_AMOUNT_MISMATCH", "warning", f"{label}: qty × rate − discount does not equal "
                                 "taxable value", "items", str(gross), _s(it.taxable_value)))

    # ---------------- totals
    for name in ("taxable_total", "cgst", "sgst", "igst", "cess", "invoice_total"):
        v = getattr(inv, name)
        if v is not None and _d(v) < 0:
            f.append(Finding("NEGATIVE_VALUE", "error", f"{name.replace('_', ' ').title()} is negative", name,
                             found=_s(v)))
    if inv.invoice_total is None:
        f.append(Finding("TOTAL_MISSING", "error", "Invoice total not found", "invoice_total"))
    if inv.taxable_total is None:
        f.append(Finding("TAXABLE_MISSING", "error", "Taxable value not found", "taxable_total"))
    if items and inv.taxable_total is not None and all(i.taxable_value is not None for i in items):
        s_items = sum(_d(i.taxable_value) for i in items)
        if abs(s_items - _d(inv.taxable_total)) > tol:
            f.append(Finding("ITEMS_VS_TAXABLE", "error", "Sum of line items does not match the taxable total",
                             "taxable_total", str(s_items), _s(inv.taxable_total)))
    if inv.invoice_total is not None and inv.taxable_total is not None:
        computed = (_d(inv.taxable_total) + cg + sg + ig + _d(inv.cess) + _d(inv.freight) + _d(inv.packing)
                    + _d(inv.other_charges) + _d(inv.tcs) + _d(inv.round_off))
        diff = _d(inv.invoice_total) - computed
        if abs(diff) > tol:
            f.append(Finding("TOTAL_MISMATCH", "error", "Invoice total does not equal taxable + taxes + charges",
                             "invoice_total", str(computed), _s(inv.invoice_total)))
        elif diff != 0 and inv.round_off is None:
            f.append(Finding("ROUND_OFF", "warning", f"Difference of {diff} – probably round-off; enter it in "
                             "Round off", "round_off", str(diff), "0"))
        if _d(inv.invoice_total) == 0:
            f.append(Finding("ZERO_VALUE", "warning", "Invoice value is zero", "invoice_total"))

    # ---------------- duplicates
    for d in duplicates or []:
        f.append(Finding("DUPLICATE_INVOICE", "error",
                         f"Same supplier GSTIN, invoice number and type already exists (invoice #{d.id}, "
                         f"status {d.status})", "invoice_no", found=inv.invoice_no or ""))
    return f


def find_duplicates(session, inv: Invoice) -> list[Invoice]:
    if not inv.invoice_no_normalized:
        return []
    q = select(Invoice).where(Invoice.company_id == inv.company_id, Invoice.id != inv.id,
                              Invoice.invoice_no_normalized == inv.invoice_no_normalized,
                              Invoice.doc_type == inv.doc_type, Invoice.status != "rejected")
    q = q.where(Invoice.supplier_gstin == inv.supplier_gstin) if inv.supplier_gstin else \
        q.where(Invoice.supplier_gstin.is_(None), Invoice.supplier_name == inv.supplier_name)
    return list(session.scalars(q))


def store_findings(session, invoice_id: int, findings: list[Finding]) -> None:
    for old in session.scalars(select(ValidationResult).where(ValidationResult.invoice_id == invoice_id)):
        session.delete(old)
    for x in findings:
        session.add(ValidationResult(invoice_id=invoice_id, check_code=x.code, severity=x.severity, field=x.field,
                                     message=x.message, expected=x.expected[:60], found=x.found[:60]))
