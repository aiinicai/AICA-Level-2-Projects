"""GST maths, amount in words (Indian system) and invoice PDF (fpdf2)."""
from fpdf import FPDF

from . import db

# SAC codes under heading 9982 (legal & accounting services). Verify before real use.
SAC_OPTIONS = {
    "Tax consultancy & return filing": "998231",
    "Audit & assurance": "998221",
    "Accounting & bookkeeping": "998222",
}

FIRM_KEYS = {
    "firm_name": "Sample & Associates, Chartered Accountants",
    "firm_address": "Ahmedabad, Gujarat",
    "firm_gstin": "24AAAAA0000A1Z5",
    "firm_pan": "AAAAA0000A",
    "firm_state": "Gujarat",
    "firm_bank": "A/c: Sample & Associates | A/c No: XXXXXXXX | IFSC: XXXX0000000",
    "firm_email": "accounts@example.com",
}

NAVY = (11, 31, 58)
TEAL = (13, 148, 136)


def firm() -> dict:
    return {k: db.get_setting(k, v) for k, v in FIRM_KEYS.items()}


def compute_gst(taxable: float, rate: float, client_state: str, firm_state: str) -> dict:
    tax = round(taxable * rate / 100, 2)
    if (client_state or "").strip().lower() == (firm_state or "").strip().lower():
        cgst = round(tax / 2, 2)
        return {"cgst": cgst, "sgst": round(tax - cgst, 2), "igst": 0.0, "total": round(taxable + tax, 2)}
    return {"cgst": 0.0, "sgst": 0.0, "igst": tax, "total": round(taxable + tax, 2)}


def next_invoice_no(fy_lbl: str) -> str:
    n = db.scalar("SELECT COUNT(*) FROM invoices WHERE invoice_no LIKE :p", p=f"INV/{fy_lbl}/%")
    while True:
        n += 1
        no = f"INV/{fy_lbl}/{n:04d}"
        if not db.one("SELECT id FROM invoices WHERE invoice_no=:n", n=no):
            return no


_ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve",
         "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _lt1000(n):
    out = []
    if n >= 100:
        out.append(_ONES[n // 100] + " Hundred")
        n %= 100
    if n >= 20:
        out.append(_TENS[n // 10] + (" " + _ONES[n % 10] if n % 10 else ""))
    elif n:
        out.append(_ONES[n])
    return " ".join(out)


def amount_in_words(amount: float) -> str:
    rupees, paise = int(amount), round((amount - int(amount)) * 100)
    parts = []
    for div, name in ((10**7, "Crore"), (10**5, "Lakh"), (1000, "Thousand")):
        if rupees >= div:
            parts.append(_lt1000(rupees // div) + " " + name)
            rupees %= div
    if rupees:
        parts.append(_lt1000(rupees))
    words = "Rupees " + (" ".join(parts) or "Zero")
    return words + (f" and {_lt1000(paise)} Paise" if paise else "") + " Only"


def _money(x):
    return f"{x:,.2f}"


_SUBS = {"\u2014": "-", "\u2013": "-", "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
         "\u20b9": "Rs.", "\u2026": "...", "\u00a0": " "}


def _latin(s) -> str:
    s = str(s)
    for a, b in _SUBS.items():
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


class _PDF(FPDF):
    """Core PDF fonts only cover Latin-1, so clean up dashes, quotes and the rupee sign."""

    def cell(self, w=None, h=None, text="", *args, **kwargs):
        return super().cell(w, h, _latin(text), *args, **kwargs)

    def multi_cell(self, w, h=None, text="", *args, **kwargs):
        return super().multi_cell(w, h, _latin(text), *args, **kwargs)


def build_pdf(inv: dict, client: dict) -> bytes:
    f = firm()
    pdf = _PDF()
    pdf.add_page()
    pdf.set_auto_page_break(True, 15)

    # Header band
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, 210, 34, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(12, 8)
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(130, 8, f["firm_name"])
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(56, 8, "TAX INVOICE", align="R")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_xy(12, 17)
    pdf.cell(0, 5, f["firm_address"])
    pdf.set_xy(12, 22)
    pdf.cell(0, 5, f"GSTIN: {f['firm_gstin']}   |   PAN: {f['firm_pan']}   |   {f['firm_email']}")
    pdf.set_fill_color(*TEAL)
    pdf.rect(0, 34, 210, 1.5, "F")

    pdf.set_text_color(30, 41, 59)
    pdf.set_xy(12, 44)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(95, 5, "BILLED TO")
    pdf.cell(0, 5, "INVOICE DETAILS", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_x(12)
    pdf.cell(95, 6, client["name"][:45])
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, f"Invoice no:  {inv['invoice_no']}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(12)
    pdf.cell(95, 5, f"GSTIN: {client.get('gstin') or 'Unregistered'}")
    pdf.cell(0, 5, f"Invoice date:  {inv['invoice_date']}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(12)
    pdf.cell(95, 5, f"PAN: {client.get('pan') or '-'}")
    pdf.cell(0, 5, f"Due date:  {inv.get('due_date') or '-'}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(12)
    pdf.cell(95, 5, f"State: {client.get('state') or '-'}")
    pdf.cell(0, 5, f"Place of supply:  {client.get('state') or '-'}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # Items table
    pdf.set_x(12)
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(116, 8, "  Description of service", fill=True)
    pdf.cell(26, 8, "SAC", fill=True, align="C")
    pdf.cell(44, 8, "Amount (Rs.)  ", fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(30, 41, 59)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_x(12)
    pdf.cell(116, 9, "  " + (inv.get("description") or "Professional fees")[:62], border="B")
    pdf.cell(26, 9, inv.get("sac") or "", border="B", align="C")
    pdf.cell(44, 9, _money(inv["taxable_value"]) + "  ", border="B", align="R", new_x="LMARGIN", new_y="NEXT")

    def row(label, val, bold=False, fill=False):
        pdf.set_x(110)
        pdf.set_font("Helvetica", "B" if bold else "", 10)
        if fill:
            pdf.set_fill_color(240, 253, 250)
        pdf.cell(44, 8, label, align="R", fill=fill)
        pdf.cell(44, 8, _money(val) + "  ", align="R", fill=fill, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(2)
    row("Taxable value", inv["taxable_value"])
    half = inv["gst_rate"] / 2
    if inv["igst"]:
        row(f"IGST @ {inv['gst_rate']:g}%", inv["igst"])
    else:
        row(f"CGST @ {half:g}%", inv["cgst"])
        row(f"SGST @ {half:g}%", inv["sgst"])
    row("Total (Rs.)", inv["total"], bold=True, fill=True)

    pdf.ln(4)
    pdf.set_x(12)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(186, 5, amount_in_words(inv["total"]))
    pdf.ln(6)
    pdf.set_x(12)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, "Bank details", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(12)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(186, 5, f["firm_bank"])
    pdf.ln(14)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, f"For {f['firm_name']}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(12)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "Authorised signatory", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(-18)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 5, "This is a computer-generated invoice.", align="C")
    return bytes(pdf.output())
