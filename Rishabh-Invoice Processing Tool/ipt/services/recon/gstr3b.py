"""GSTR-3B Table 4 (ITC) working for one return period, from GSTR-2B and the books (purchase register).

This is a WORKING for the professional who files the return, not a filing and not a legal conclusion:
- 4(A) is what GSTR-2B of the month carries (the portal auto-fills 3B from it), with RCM tax from the books.
- Adjustments the user should look at are listed bill by bill: in 2B but not in the books, in the books but not
  in 2B yet (not claimable yet, carried forward), ITC the 2B marks not available / Sec 16(4), and the user's own
  ITC Analysis decisions (blocked / ineligible / deferred).
Credit notes reduce ITC. Every figure is head-wise (IGST, CGST, SGST, Cess).
"""
from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from ipt.db.models import (Gstr2bRecord, Gstr2bUpload, ItcAnalysis, PurchaseRegisterRecord, PurchaseRegisterUpload,
                           ReconRow, ReconRun)

HEADS = ("igst", "cgst", "sgst", "cess")
Z = Decimal("0")
DISCLAIMER = ("Working only – prepared from GSTR-2B and your books for review. It is not a filing and does not "
              "decide eligibility (Sec 16 / 17 conditions, receipt of goods, payment within 180 days). "
              "Check every adjustment before filing GSTR-3B.")


def _amt(rec, sign=1) -> dict[str, Decimal]:
    return {h: sign * (getattr(rec, h) or Z) for h in HEADS}


def _add(a: dict, b: dict) -> None:
    for h in HEADS:
        a[h] = a.get(h, Z) + b.get(h, Z)


def _zero() -> dict[str, Decimal]:
    return {h: Z for h in HEADS}


def _total(a: dict) -> Decimal:
    return sum((a.get(h, Z) for h in HEADS), Z)


@dataclass
class Line:
    code: str              # '4(A)(5)'
    label: str
    amounts: dict = field(default_factory=_zero)
    note: str = ""


@dataclass
class Bill:
    group: str             # which list this belongs to
    supplier: str
    gstin: str
    doc_no: str
    doc_date: date | None
    doc_type: str
    amounts: dict
    note: str = ""


@dataclass
class Working:
    period: str
    lines: list[Line]
    bills: list[Bill]
    books_itc: dict
    warnings: list[str]


GROUPS = {
    "not_in_books": "In GSTR-2B of this month, not found in your books",
    "not_in_2b": "In your books, not in any GSTR-2B up to this month (not claimable yet – carry forward)",
    "not_available": "GSTR-2B says ITC not available / time-barred (Sec 16(4)) – keep out of 4(A)",
    "late": "Earlier-month bills reported by the supplier in this GSTR-2B (included in 4(A))",
    "blocked": "Marked blocked / ineligible in your ITC review – reverse in 4(B)(1)",
    "deferred": "Marked deferred / reversed in your ITC review – reverse in 4(B)(2)",
    "rcm": "Reverse charge entries in your books this month – 4(A)(3)",
}


def _month(period: str) -> tuple[date, date]:
    if not re.fullmatch(r"\d{4}-\d{2}", period or "") or not 1 <= int(period[5:]) <= 12:
        raise ValueError("Period must be YYYY-MM")
    y, m = int(period[:4]), int(period[5:])
    return date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])


def build(s, company_id: int, fy_id: int, period: str) -> Working:
    start, end = _month(period)
    warnings: list[str] = []
    ups = list(s.scalars(select(Gstr2bUpload).where(Gstr2bUpload.company_id == company_id,
                                                    Gstr2bUpload.fy_id == fy_id, Gstr2bUpload.is_current.is_(True))))
    this_up = [u.id for u in ups if u.period == period]
    upto_up = [u.id for u in ups if u.period <= period]
    if not this_up:
        warnings.append(f"No GSTR-2B loaded for {period[5:]}-{period[:4]} – 4(A) cannot be worked out.")
    cur_pr = [u.id for u in s.scalars(select(PurchaseRegisterUpload).where(
        PurchaseRegisterUpload.company_id == company_id, PurchaseRegisterUpload.fy_id == fy_id,
        PurchaseRegisterUpload.is_current.is_(True)))]
    if not cur_pr:
        warnings.append("No purchase register loaded – books-side checks (not in 2B, not in books, RCM) are empty.")
    b2_this = list(s.scalars(select(Gstr2bRecord).where(Gstr2bRecord.upload_id.in_(this_up)))) if this_up else []
    b2_upto = list(s.scalars(select(Gstr2bRecord).where(Gstr2bRecord.upload_id.in_(upto_up)))) if upto_up else []
    books = list(s.scalars(select(PurchaseRegisterRecord).where(PurchaseRegisterRecord.upload_id.in_(cur_pr)))) \
        if cur_pr else []

    # links the reconciliation already made (fuzzy and manual matches count too)
    run = s.scalar(select(ReconRun).where(ReconRun.company_id == company_id, ReconRun.fy_id == fy_id,
                                          ReconRun.is_latest.is_(True)).order_by(ReconRun.id.desc()))
    linked_pr, linked_2b = set(), set()
    if run is not None:
        for r in s.scalars(select(ReconRow).where(ReconRow.run_id == run.id)):
            if r.pr_record_id and r.gstr2b_record_id:
                linked_pr.add(r.pr_record_id)
                linked_2b.add(r.gstr2b_record_id)

    def key(gstin, norm, doc_type):
        return (gstin or "", norm or "", doc_type or "INV")

    book_keys = {key(p.supplier_gstin, p.invoice_no_normalized, p.doc_type) for p in books
                 if not (p.narration or "").startswith("[RCM]")}
    b2_keys = {key(g.supplier_gstin, g.doc_no_normalized, g.doc_type) for g in b2_upto}

    reviews = {(a.supplier_gstin, a.doc_no_normalized, a.doc_type): a.eligibility for a in s.scalars(
        select(ItcAnalysis).where(ItcAnalysis.company_id == company_id, ItcAnalysis.fy_id == fy_id))}

    l_imp = Line("4(A)(1)", "Import of goods")
    l_rcm = Line("4(A)(3)", "Inward supplies liable to reverse charge (from books)")
    l_isd = Line("4(A)(4)", "Inward supplies from ISD")
    l_oth = Line("4(A)(5)", "All other ITC (GSTR-2B: B2B, amendments, debit / credit notes)")
    l_b1 = Line("4(B)(1)", "Reversed – Rule 38, 42, 43 and Sec 17(5) (from your ITC review)")
    l_b2 = Line("4(B)(2)", "Reversed – others (deferred in your review; in 2B but not in books)")
    l_d2 = Line("4(D)(2)", "Ineligible ITC u/s 16(4) and PoS rules (2B: ITC not available) – not in 4(A)")
    bills: list[Bill] = []

    for g in b2_this:
        k = key(g.supplier_gstin, g.doc_no_normalized, g.doc_type)
        sign = -1 if g.doc_type == "CRN" else 1
        a = _amt(g, sign)
        name = g.supplier_name or ""
        if g.reverse_charge:
            continue                                  # RCM tax is paid by us: taken from the books in 4(A)(3)
        reason = g.itc_reason or ""
        if (g.itc_available or "").lower().startswith("n") or re.search(r"16\s*\(\s*4\s*\)", reason):
            _add(l_d2.amounts, a)
            bills.append(Bill("not_available", name, g.supplier_gstin, g.doc_no, g.doc_date, g.doc_type, a, reason))
            continue
        if g.doc_type == "BOE" or g.section in ("IMPG", "IMPGSEZ"):
            _add(l_imp.amounts, a)
            continue
        if g.doc_type == "ISD" or g.section in ("ISD", "ISDA"):
            _add(l_isd.amounts, a)
            continue
        _add(l_oth.amounts, a)
        if g.doc_date and g.doc_date < start:
            bills.append(Bill("late", name, g.supplier_gstin, g.doc_no, g.doc_date, g.doc_type, a,
                              f"invoice of {g.doc_date:%b-%y}"))
        rv = reviews.get(k, "")
        if rv in ("Ineligible", "Blocked (Sec 17(5))"):
            _add(l_b1.amounts, a)
            bills.append(Bill("blocked", name, g.supplier_gstin, g.doc_no, g.doc_date, g.doc_type, a, rv))
        elif rv in ("Deferred", "Reversed"):
            _add(l_b2.amounts, a)
            bills.append(Bill("deferred", name, g.supplier_gstin, g.doc_no, g.doc_date, g.doc_type, a, rv))
        elif books and k not in book_keys and g.id not in linked_2b:
            _add(l_b2.amounts, a)
            bills.append(Bill("not_in_books", name, g.supplier_gstin, g.doc_no, g.doc_date, g.doc_type, a,
                              "check receipt of goods / book the bill, else reverse"))

    books_itc = _zero()
    for p in books:
        d = p.voucher_date or p.supplier_invoice_date
        sign = -1 if p.doc_type == "CRN" else 1
        a = _amt(p, sign)
        rcm = (p.narration or "").startswith("[RCM]")
        if d and start <= d <= end:
            if rcm:
                _add(l_rcm.amounts, a)
                bills.append(Bill("rcm", p.party_name, p.supplier_gstin, p.supplier_invoice_no or p.voucher_no,
                                  d, p.doc_type, a, p.voucher_type))
            else:
                _add(books_itc, a)
        if rcm or d is None or d > end:
            continue
        k = key(p.supplier_gstin, p.invoice_no_normalized, p.doc_type)
        if k not in b2_keys and p.id not in linked_pr and _total(a) != 0:
            bills.append(Bill("not_in_2b", p.party_name, p.supplier_gstin, p.supplier_invoice_no or p.voucher_no,
                              p.supplier_invoice_date or d, p.doc_type, a, f"booked {d:%d-%m-%Y}"))

    l_a = Line("4(A)", "ITC available (total of 4(A)(1) to 4(A)(5))")
    for ln in (l_imp, l_rcm, l_isd, l_oth):
        _add(l_a.amounts, ln.amounts)
    l_b = Line("4(B)", "ITC reversed (total)")
    _add(l_b.amounts, l_b1.amounts)
    _add(l_b.amounts, l_b2.amounts)
    l_c = Line("4(C)", "Net ITC available (4(A) – 4(B)) – suggested")
    _add(l_c.amounts, l_a.amounts)
    _add(l_c.amounts, {h: -v for h, v in l_b.amounts.items()})
    if any(v < 0 for v in l_oth.amounts.values()):
        warnings.append("Credit notes exceed invoices in a tax head of 4(A)(5): the portal shows the negative part "
                        "in 4(B)(2) – check before filing.")
    lines = [l_imp, Line("4(A)(2)", "Import of services (not in GSTR-2B – add from your books if any)"),
             l_rcm, l_isd, l_oth, l_a, l_b1, l_b2, l_b, l_c, l_d2]
    order = list(GROUPS)
    bills.sort(key=lambda b: (order.index(b.group), b.supplier or "", b.doc_date or date.min))
    return Working(period, lines, bills, books_itc, warnings)


def export_xlsx(w: Working, company_name: str, target: Path) -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = "3B Table 4 working"
    mon = f"{calendar.month_name[int(w.period[5:])]} {w.period[:4]}"
    ws.append([f"{company_name} – GSTR-3B ITC working for {mon}"])
    ws["A1"].font = Font(bold=True, size=13)
    ws.append([DISCLAIMER])
    ws["A2"].alignment = Alignment(wrap_text=True)
    ws.merge_cells("A2:G2")
    ws.row_dimensions[2].height = 45
    for msg in w.warnings:
        ws.append(["⚠ " + msg])
    ws.append([])
    ws.append(["Table", "Details", "IGST", "CGST", "SGST/UTGST", "Cess", "Total"])
    head_row = ws.max_row
    for c in ws[head_row]:
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor="E5E7EB")
    for ln in w.lines:
        ws.append([ln.code, ln.label] + [float(ln.amounts[h]) for h in HEADS] + [float(_total(ln.amounts))])
        if ln.code in ("4(A)", "4(B)", "4(C)"):
            for c in ws[ws.max_row]:
                c.font = Font(bold=True)
    ws.append([])
    ws.append(["", "For comparison: ITC in your books this month (non-RCM)"] +
              [float(w.books_itc[h]) for h in HEADS] + [float(_total(w.books_itc))])
    for row in ws.iter_rows(min_row=head_row + 1, min_col=3, max_col=7):
        for c in row:
            c.number_format = "#,##0.00"
    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 70
    for col in "CDEFG":
        ws.column_dimensions[col].width = 15

    det = wb.create_sheet("Bills to check")
    det.append(["List", "Supplier", "GSTIN", "Document", "Date", "Type", "IGST", "CGST", "SGST", "Cess", "Total",
                "Note"])
    for c in det[1]:
        c.font = Font(bold=True)
    for b in w.bills:
        det.append([GROUPS[b.group], b.supplier, b.gstin, b.doc_no, b.doc_date, b.doc_type] +
                   [float(b.amounts[h]) for h in HEADS] + [float(_total(b.amounts)), b.note])
    for row in det.iter_rows(min_row=2, min_col=7, max_col=11):
        for c in row:
            c.number_format = "#,##0.00"
    for row in det.iter_rows(min_row=2, min_col=5, max_col=5):
        for c in row:
            c.number_format = "DD-MM-YYYY"
    for col, wd in zip("ABCDEFGHIJKL", (60, 32, 17, 18, 12, 6, 12, 12, 12, 10, 13, 40)):
        det.column_dimensions[col].width = wd
    wb.save(target)
    return target
