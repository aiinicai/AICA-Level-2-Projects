"""Arithmetic and statutory checks on an extracted invoice. Produces issues + a traffic-light."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal

from ..tally.parsers import gstin_valid
from .schema import Invoice

TOL = Decimal("1.00")
KEY_FIELDS = ("supplier_gstin", "invoice_no", "invoice_date", "grand_total")


@dataclass
class Issue:
    level: str        # error | warn | info
    field: str
    message: str


@dataclass
class Validation:
    issues: list[Issue]
    confidence: float
    status: str       # green | amber | red

    @property
    def errors(self):
        return [i for i in self.issues if i.level == "error"]

    def to_json(self) -> dict:
        return {"issues": [asdict(i) for i in self.issues], "confidence": self.confidence, "status": self.status}


def itc_deadline(inv_date: date) -> date:
    """s.16(4): 30 November following the end of the FY of the invoice."""
    fy_end_year = inv_date.year + 1 if inv_date.month >= 4 else inv_date.year
    return date(fy_end_year, 11, 30)


def validate(inv: Invoice, company_gstin: str = "", company_state: str = "", today: date | None = None) -> Validation:
    today = today or date.today()
    issues: list[Issue] = []
    add = lambda lvl, f, m: issues.append(Issue(lvl, f, m))

    # ---- identity
    if not inv.supplier_gstin:
        add("warn", "supplier_gstin", "No supplier GSTIN found (unregistered vendor? RCM may apply)")
    elif not gstin_valid(inv.supplier_gstin):
        add("error", "supplier_gstin", f"Supplier GSTIN {inv.supplier_gstin} fails checksum")
    if company_gstin and inv.buyer_gstin and inv.buyer_gstin != company_gstin:
        add("error", "buyer_gstin", f"Invoice is billed to {inv.buyer_gstin}, not this company ({company_gstin})")
    if company_gstin and not inv.buyer_gstin and inv.tax_total:
        add("warn", "buyer_gstin", "Company GSTIN not printed on invoice; ITC needs it (Rule 46)")
    if not inv.invoice_no:
        add("error", "invoice_no", "Invoice number not found")
    elif len(inv.invoice_no) > 16:
        add("warn", "invoice_no", "Invoice number longer than 16 characters (Rule 46)")

    # ---- date
    d = None
    if not inv.invoice_date:
        add("error", "invoice_date", "Invoice date not found")
    else:
        try:
            d = datetime.strptime(inv.invoice_date, "%Y%m%d").date()
        except ValueError:
            add("error", "invoice_date", f"Bad date {inv.invoice_date}")
    if d:
        if d > today:
            add("error", "invoice_date", f"Invoice date {d:%d-%m-%Y} is in the future")
        if inv.tax_total and not inv.reverse_charge:
            dl = itc_deadline(d)
            if today > dl:
                add("error", "invoice_date", f"ITC time-barred u/s 16(4): deadline was {dl:%d-%m-%Y}")
            elif (dl - today).days <= 30:
                add("warn", "invoice_date", f"ITC window closes {dl:%d-%m-%Y} (s.16(4))")

    # ---- tax type vs place of supply
    sup_state = inv.supplier_gstin[:2] if inv.supplier_gstin else ""
    pos = inv.place_of_supply or (company_gstin[:2] if company_gstin else "") or company_state
    if sup_state and pos and (inv.igst_total or inv.cgst_total or inv.sgst_total):
        intra = sup_state == pos
        if intra and inv.igst_total and not (inv.cgst_total or inv.sgst_total):
            add("error", "igst_total", f"IGST charged on an intra-state supply (supplier {sup_state}, POS {pos})")
        if not intra and (inv.cgst_total or inv.sgst_total) and not inv.igst_total:
            add("error", "cgst_total", f"CGST/SGST charged on an inter-state supply (supplier {sup_state}, POS {pos})")
    own = company_gstin[:2] if company_gstin else ""
    if own and inv.place_of_supply and inv.place_of_supply != own and inv.tax_total and not inv.reverse_charge:
        add("warn", "place_of_supply",
            f"Place of supply is state {inv.place_of_supply}, not {own}: ITC is not available in this GSTIN "
            f"(e.g. hotel stay u/s 12(3) IGST Act). Book the GST as part of the expense (tick 'ITC blocked').")
    if inv.document_type == "credit_note":
        add("info", "document_type", "Supplier credit note: will be posted as a Debit Note in your books"
            + (f" against invoice {inv.original_invoice_no}" if inv.original_invoice_no else ""))
    if abs(inv.cgst_total - inv.sgst_total) > TOL:
        add("error", "sgst_total", f"CGST {inv.cgst_total} and SGST {inv.sgst_total} differ")

    # ---- arithmetic
    if inv.grand_total:
        computed = inv.taxable_total + inv.tax_total + inv.tcs + inv.round_off
        diff = inv.grand_total - computed
        if abs(diff) > TOL:
            add("error", "grand_total", f"Taxable {inv.taxable_total} + tax {inv.tax_total} + TCS {inv.tcs} + "
                f"round-off {inv.round_off} = {computed}, but total is {inv.grand_total} (diff {diff})")
    else:
        add("error", "grand_total", "Invoice total not found")
    if abs(inv.round_off) > TOL:
        add("error", "round_off", f"Round-off {inv.round_off} exceeds Rs 1")
    for r in inv.taxes:
        expected = r.taxable * r.rate / 100
        actual = r.igst + r.cgst + r.sgst
        if r.taxable and abs(expected - actual) > max(TOL, expected * Decimal("0.005")):
            big = abs(expected - actual) > max(Decimal("5"), expected * Decimal("0.02"))
            add("error" if big else "warn", "taxable_total",
                f"{r.rate}% slab: tax {actual} vs expected {expected:.2f} on {r.taxable}")
    gst = inv.igst_total + inv.cgst_total + inv.sgst_total
    if inv.taxable_total > 0 and gst > 0:
        eff = gst * 100 / inv.taxable_total
        rates = [Decimal(x) for x in ("0.1", "0.25", "1", "1.5", "3", "5", "6", "7.5", "12", "18", "28", "40")]
        if len(inv.taxes) <= 1 and min(abs(eff - r) / r for r in rates) > Decimal("0.04"):
            add("error", "taxable_total", f"GST is {eff:.2f}% of the taxable value {inv.taxable_total}, which is not "
                f"a GST rate - taxable value or tax is probably misread")
    if inv.lines:
        lt = sum((l.taxable for l in inv.lines), Decimal(0))
        if inv.taxable_total and abs(lt - inv.taxable_total) > TOL:
            add("warn", "lines", f"Line items add to {lt}, taxable total is {inv.taxable_total}")
        for l in inv.lines:
            if l.hsn and len(l.hsn) not in (4, 6, 8):
                add("warn", "lines", f"HSN/SAC '{l.hsn}' should be 4, 6 or 8 digits")

    # ---- score
    confs = [inv.field_confidence.get(f, 0.0) for f in KEY_FIELDS]
    conf = min(confs) if confs else 0.0
    n_err = sum(1 for i in issues if i.level == "error")
    n_warn = sum(1 for i in issues if i.level == "warn")
    score = round(max(0.0, conf - 0.25 * n_err - 0.05 * n_warn), 2)
    status = "red" if n_err else ("green" if score >= 0.8 and n_warn == 0 else "amber")
    return Validation(issues, score, status)
