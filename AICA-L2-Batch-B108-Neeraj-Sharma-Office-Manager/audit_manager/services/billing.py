"""Invoice maths, numbering and the invoice PDF."""
import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle

from ..models import FirmSetting, Invoice, InvoiceItem, db
from . import letterhead, pdfutil
from .pdfutil import P, money, styles

TAX_MODES = {"cgst_sgst": "Intra-State (CGST + SGST)", "igst": "Inter-State (IGST)", "exempt": "Tax Exempt / No GST"}
PAYMENT_MODES = {"bank": "Bank Transfer", "upi": "UPI", "cash": "Cash", "cheque": "Cheque", "card": "Card", "other": "Other"}


DEFAULT_SERVICES = [
    ("Statutory Audit Fee", "998221", 0), ("Tax Audit Fee (Sec. 44AB)", "998221", 0), ("Income Tax Return Filing", "998231", 0),
    ("GST Return Filing (Monthly)", "998231", 0), ("GST Return Filing (Quarterly)", "998231", 0), ("GST Annual Return (GSTR-9/9C)", "998231", 0),
    ("TDS Return Filing (Quarterly)", "998231", 0), ("Accounting & Book-keeping", "998222", 0), ("GST Registration", "998231", 0),
    ("ROC / Company Law Compliance", "998399", 0), ("Certification Charges", "998221", 0), ("Project Report / CMA Data", "998311", 0),
    ("Consultancy Charges", "998311", 0), ("Out of Pocket Expenses", "998221", 0),
]


def seed_services() -> None:
    from ..models import ServiceItem

    if ServiceItem.query.count() == 0:
        for name, sac, rate in DEFAULT_SERVICES:
            db.session.add(ServiceItem(name=name, sac_code=sac, default_rate=rate))


def invoice_message(inv, firm: str) -> str:
    """A WhatsApp-ready summary of an invoice (the PDF itself has to be attached by hand or sent by email)."""
    due = f"\nDue date: *{inv.due_date:%d-%b-%Y}*" if inv.due_date else ""
    paid = f"\nReceived: Rs. {inv.paid_amount:,.2f}\nBalance payable: *Rs. {inv.balance:,.2f}*" if inv.paid_amount else ""
    return (f"Dear {inv.client.name},\n\nGreetings from {firm}.\n\nPlease find the details of our invoice:\n\n"
            f"Invoice No.: *{inv.invoice_number}*\nDate: {inv.invoice_date:%d-%b-%Y}\nAmount: *Rs. {inv.total_amount:,.2f}*{due}{paid}\n\n"
            f"Kindly arrange the payment at your earliest convenience.\n\nRegards,\n{firm}")


def save_pdf_copy(inv):
    """Save the invoice PDF into the folder chosen in Settings (for example a Google Drive folder). Returns the path, or None."""
    import os
    from pathlib import Path

    folder = (FirmSetting.get("invoice_pdf_folder") or "").strip()
    if not folder:
        return None
    try:
        path = Path(os.path.expandvars(os.path.expanduser(folder)))
        path.mkdir(parents=True, exist_ok=True)
        target = path / (inv.invoice_number.replace("/", "-") + ".pdf")
        target.write_bytes(invoice_pdf(inv))
        return target
    except OSError:
        return None


def default_rate(key: str, fallback: float) -> float:
    try:
        return float(FirmSetting.get(key, fallback))
    except (TypeError, ValueError):
        return fallback


def compute_totals(items: list[dict], discount: float, tax_mode: str, cgst: float, sgst: float, igst: float) -> dict:
    subtotal = round(sum(i["quantity"] * i["rate"] for i in items), 2)
    discount = min(max(discount, 0.0), subtotal)
    taxable = round(subtotal - discount, 2)
    c = s = g = 0.0
    if tax_mode == "cgst_sgst":
        c, s = round(taxable * cgst / 100, 2), round(taxable * sgst / 100, 2)
    elif tax_mode == "igst":
        g = round(taxable * igst / 100, 2)
    else:
        cgst = sgst = igst = 0.0
    return {
        "subtotal": subtotal, "discount_amount": discount, "taxable_amount": taxable,
        "cgst_rate": cgst if tax_mode == "cgst_sgst" else 0, "cgst_amount": c,
        "sgst_rate": sgst if tax_mode == "cgst_sgst" else 0, "sgst_amount": s,
        "igst_rate": igst if tax_mode == "igst" else 0, "igst_amount": g,
        "total_amount": round(taxable + c + s + g, 2),
    }


def financial_year_label(d: date) -> str:
    start = d.year if d.month >= 4 else d.year - 1
    return f"{start}-{str(start + 1)[2:]}"


def next_invoice_number(invoice_date: date) -> str:
    prefix = FirmSetting.get("invoice_prefix", "INV") or "INV"
    base = f"{prefix}/{financial_year_label(invoice_date)}/"
    count = Invoice.query.filter(Invoice.invoice_number.like(base + "%")).count()
    while True:
        count += 1
        number = f"{base}{count:04d}"
        if not Invoice.query.filter_by(invoice_number=number).first():
            return number


def create_invoice(client_id: int, invoice_date: date, due_date: date | None, tax_mode: str, items: list[dict],
                   discount: float, notes: str, user_id: int) -> Invoice:
    totals = compute_totals(items, discount, tax_mode, default_rate("default_cgst_rate", 9),
                            default_rate("default_sgst_rate", 9), default_rate("default_igst_rate", 18))
    inv = Invoice(invoice_number=next_invoice_number(invoice_date), client_id=client_id, invoice_date=invoice_date,
                  due_date=due_date, tax_mode=tax_mode, notes=notes or None, created_by_id=user_id, **totals)
    for it in items:
        inv.items.append(InvoiceItem(description=it["description"], sac_code=it.get("sac_code") or "998221",
                                     quantity=it["quantity"], rate=it["rate"], amount=round(it["quantity"] * it["rate"], 2)))
    inv.balance = inv.total_amount
    db.session.add(inv)
    db.session.flush()
    inv.sync_payments()
    return inv


def invoice_pdf(inv: Invoice) -> bytes:
    st = styles()
    regular, bold, _ = pdfutil.fonts()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=14 * mm,
                            bottomMargin=14 * mm, title=inv.invoice_number)
    width = A4[0] - 30 * mm
    prof = letterhead.profile()
    right = f"Invoice: {inv.invoice_number}\nDate: {inv.invoice_date:%d %b %Y}\n" + \
            (f"Due: {inv.due_date:%d %b %Y}\n" if inv.due_date else "") + f"Status: {inv.status.replace('_', ' ').title()}"
    story = pdfutil.letterhead_block(prof, width, "TAX INVOICE", right)

    c = inv.client
    billed = [P("Billed To", st["th"]), P(c.name, st["bodyb"]),
              P(", ".join(x for x in (c.address, c.city, c.state, c.pincode) if x), st["body"]),
              P(f"PAN: {c.pan or '—'}   GSTIN: {c.gstin or 'Unregistered'}", st["body"])]
    t = Table([[billed]], colWidths=[width])
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                           ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")), ("PADDING", (0, 0), (-1, -1), 6)]))
    story += [t, Spacer(1, 8)]

    rows = [[P(h, st["th"]) for h in ("#", "Service Description", "SAC", "Qty", "Rate", "Amount")]]
    for n, it in enumerate(inv.items, start=1):
        rows.append([P(n, st["body"]), P(it.description, st["body"]), P(it.sac_code, st["body"]),
                     P(f"{it.quantity:g}", st["right"]), P(money(it.rate), st["right"]), P(money(it.amount), st["right"])])
    items = Table(rows, colWidths=[8 * mm, width - 8 * mm - 20 * mm - 14 * mm - 30 * mm - 32 * mm, 20 * mm, 14 * mm, 30 * mm, 32 * mm],
                  repeatRows=1)
    items.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), pdfutil.LIGHT), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 4)]))
    story += [items, Spacer(1, 8)]

    tot = [("Subtotal", inv.subtotal)]
    if inv.discount_amount:
        tot.append(("Discount", -inv.discount_amount))
    tot.append(("Taxable value", inv.taxable_amount))
    if inv.cgst_amount or inv.tax_mode == "cgst_sgst":
        tot += [(f"CGST @ {inv.cgst_rate:g}%", inv.cgst_amount), (f"SGST @ {inv.sgst_rate:g}%", inv.sgst_amount)]
    if inv.tax_mode == "igst":
        tot.append((f"IGST @ {inv.igst_rate:g}%", inv.igst_amount))
    tot += [("Total", inv.total_amount), ("Paid", inv.paid_amount), ("Balance due", inv.balance)]
    trows = [[P(k, st["bodyb"] if k in ("Total", "Balance due") else st["body"]), P(money(v), st["right"])] for k, v in tot]
    totals = Table(trows, colWidths=[40 * mm, 34 * mm], hAlign="RIGHT")
    totals.setStyle(TableStyle([("LINEABOVE", (0, -3), (-1, -3), 1, pdfutil.NAVY), ("PADDING", (0, 0), (-1, -1), 3)]))
    story.append(totals)
    if inv.notes:
        story += [Spacer(1, 8), P("Notes: " + inv.notes, st["body"])]
    doc.build(story)
    return buf.getvalue()
