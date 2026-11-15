"""Practice reports and their four outputs (screen, CSV, Excel, PDF), all carrying the firm letterhead."""
import csv
import io
from datetime import date, datetime

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XlImage
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle

from ..access import visible_clients
from ..models import (
    Client, ComplianceDeadline, GstReturn, Invoice, ItrFiling, Payment, Task, TdsReturn, User, db,
)
from . import letterhead, pdfutil
from .pdfutil import P, styles

TYPES = {
    "client_compliance": "Client-wise Compliance Summary",
    "gst_status": "GST Filing Status Report",
    "itr_status": "ITR Filing Status Report",
    "tds_status": "TDS Return Status Report",
    "overdue_compliance": "Overdue Compliance Report",
    "employee_productivity": "Employee Productivity Report",
    "pending_tasks": "Pending Tasks Report",
    "outstanding_invoices": "Outstanding Invoices Report",
    "receivables_ageing": "Receivables Ageing Report",
    "monthly_revenue": "Monthly Revenue Report",
    "client_register": "Register - Clients (master list)",
    "gst_register": "Register - GST Returns Filed and Pending",
    "itr_register": "Register - Income Tax Returns",
    "tds_register": "Register - TDS Returns",
    "invoice_register": "Register - Invoices Raised (Sales Register)",
    "receipt_register": "Register - Receipts",
    "time_register": "Register - Time Sheet",
    "matter_register": "Register - Matters and Hearings (Cause List)",
    "own_gst_outward": "Own GST - Outward Supplies Register (GSTR-1 style)",
    "own_gst_summary": "Own GST - Monthly Tax Summary (GSTR-3B style)",
    "own_gst_sac": "Own GST - SAC-wise Summary",
}

MONEY = "money"  # column marker: values in these columns are rupee amounts


def _between(col, start: date | None, end: date | None):
    conds = []
    if start:
        conds.append(col >= start)
    if end:
        conds.append(col <= end)
    return conds


def _name(u) -> str:
    return u.name if u else "—"


def build(kind: str, user, start: date | None = None, end: date | None = None) -> dict:
    """Returns {'headers': [...], 'rows': [[native values]], 'money_cols': {indexes}}."""
    if kind not in TYPES:
        kind = "client_compliance"
    ids = [c.id for c in visible_clients(user).with_entities(Client.id).all()]
    return globals()["_" + kind](ids, start, end)


def _client_compliance(ids, start, end):
    rows = []
    today = date.today()
    for c in Client.query.filter(Client.id.in_(ids)).order_by(Client.name):
        pend_gst = sum(1 for r in c.gst_returns if r.status != "filed")
        pend_itr = sum(1 for r in c.itr_filings if r.status != "filed")
        pend_tds = sum(1 for r in c.tds_returns if r.status != "filed")
        overdue = sum(1 for d in c.deadlines if d.status != "completed" and d.due_date < today)
        rows.append([c.client_code, c.name, c.pan or "—", pend_gst, pend_itr, pend_tds, overdue, c.outstanding()])
    return {"headers": ["Code", "Client", "PAN", "GST Pending", "ITR Pending", "TDS Pending", "Overdue Deadlines", "Outstanding"],
            "rows": rows, "money_cols": {7}}


def _gst_status(ids, start, end):
    q = GstReturn.query.filter(GstReturn.client_id.in_(ids), *_between(GstReturn.due_date, start, end)).order_by(GstReturn.due_date)
    rows = [[r.client.name, r.return_type.name, r.period, r.due_date, r.status.replace("_", " ").title(), r.filed_date,
             r.arn or "—", _name(r.assigned_to)] for r in q]
    return {"headers": ["Client", "Return", "Period", "Due Date", "Status", "Filed On", "ARN", "Assigned To"], "rows": rows, "money_cols": set()}


def _itr_status(ids, start, end):
    q = ItrFiling.query.filter(ItrFiling.client_id.in_(ids), *_between(ItrFiling.due_date, start, end)).order_by(ItrFiling.due_date)
    rows = [[r.client.name, r.client.pan or "—", r.assessment_year, r.form_type, r.due_date, r.status.replace("_", " ").title(),
             r.filed_date, r.ack_number or "—", {"e_verified": "e-Verified", "itrv_sent": "ITR-V sent by post",
                                                 "itrv_received": "ITR-V received at CPC"}.get(r.verification_status or "", "Not verified" if r.status == "filed" else ""),
             r.verification_date, r.refund_amount or 0, _name(r.assigned_to)] for r in q]
    return {"headers": ["Client", "PAN", "AY", "Form", "Due Date", "Status", "Filed On", "Ack. No.", "Verification", "Verified On", "Refund", "Assigned To"],
            "rows": rows, "money_cols": {10}}


def _tds_status(ids, start, end):
    q = TdsReturn.query.filter(TdsReturn.client_id.in_(ids), *_between(TdsReturn.due_date, start, end)).order_by(TdsReturn.due_date)
    rows = [[r.client.name, r.client.tan or "—", r.financial_year, r.quarter, r.form_type, r.due_date, r.tds_deducted or 0,
             r.tds_deposited or 0, r.challan_number or "—", r.status.replace("_", " ").title(), r.filed_date, r.ack_number or "—",
             _name(r.assigned_to)] for r in q]
    return {"headers": ["Client", "TAN", "FY", "Qtr", "Form", "Due Date", "TDS Deducted", "TDS Deposited", "Challan", "Status", "Filed On", "Ack. No.",
                        "Assigned To"],
            "rows": rows, "money_cols": {6, 7}}


def _overdue_compliance(ids, start, end):
    today = date.today()
    out = []
    for d in ComplianceDeadline.query.filter(ComplianceDeadline.client_id.in_(ids), ComplianceDeadline.status != "completed",
                                             ComplianceDeadline.due_date < today, *_between(ComplianceDeadline.due_date, start, end)):
        out.append(["Deadline", d.client.name if d.client else "—", d.title, d.due_date, _name(d.assigned_to)])
    for r in GstReturn.query.filter(GstReturn.client_id.in_(ids), GstReturn.status != "filed", GstReturn.due_date < today,
                                    *_between(GstReturn.due_date, start, end)):
        out.append(["GST", r.client.name, f"{r.return_type.name} {r.period}", r.due_date, _name(r.assigned_to)])
    for r in ItrFiling.query.filter(ItrFiling.client_id.in_(ids), ItrFiling.status != "filed", ItrFiling.due_date < today,
                                    *_between(ItrFiling.due_date, start, end)):
        out.append(["ITR", r.client.name, f"{r.form_type} AY {r.assessment_year}", r.due_date, _name(r.assigned_to)])
    for r in TdsReturn.query.filter(TdsReturn.client_id.in_(ids), TdsReturn.status != "filed", TdsReturn.due_date < today,
                                    *_between(TdsReturn.due_date, start, end)):
        out.append(["TDS", r.client.name, f"{r.form_type} {r.financial_year} {r.quarter}", r.due_date, _name(r.assigned_to)])
    out.sort(key=lambda r: r[3])
    rows = [[r[0], r[1], r[2], r[3], (today - r[3]).days, r[4]] for r in out]
    return {"headers": ["Type", "Client", "Item", "Due Date", "Days Overdue", "Assigned To"], "rows": rows, "money_cols": set()}


def _employee_productivity(ids, start, end):
    rows = []
    for u in User.query.filter_by(is_active_user=True).order_by(User.name):
        tasks = Task.query.filter(Task.assigned_to_id == u.id)
        rows.append([
            u.name, u.role_label,
            Client.query.filter_by(assigned_to_id=u.id, archived=False).count(),
            tasks.filter(Task.status != "completed").count(),
            tasks.filter(Task.status == "completed").count(),
            sum(1 for t in tasks if t.is_overdue),
            sum(m.query.filter_by(assigned_to_id=u.id, status="filed").count() for m in (GstReturn, ItrFiling, TdsReturn)),
        ])
    return {"headers": ["Staff", "Role", "Clients", "Open Tasks", "Completed Tasks", "Overdue Tasks", "Returns Filed"], "rows": rows, "money_cols": set()}


def _pending_tasks(ids, start, end):
    q = Task.query.filter(Task.status != "completed", *_between(Task.due_date, start, end)).order_by(Task.due_date)
    rows = [[t.title, t.client.name if t.client else "—", _name(t.assigned_to), t.priority.title(),
             t.status.replace("_", " ").title(), t.due_date, "Yes" if t.is_overdue else "No"] for t in q
            if t.client_id is None or t.client_id in ids]
    return {"headers": ["Task", "Client", "Assigned To", "Priority", "Status", "Due Date", "Overdue"], "rows": rows, "money_cols": set()}


def _outstanding_invoices(ids, start, end):
    today = date.today()
    q = Invoice.query.filter(Invoice.client_id.in_(ids), Invoice.status != "paid", *_between(Invoice.invoice_date, start, end)).order_by(Invoice.invoice_date)
    rows = [[i.invoice_number, i.client.name, i.invoice_date, i.due_date, i.total_amount, i.paid_amount, i.balance,
             i.status.replace("_", " ").title(), max(0, (today - i.due_date).days) if i.due_date else 0] for i in q]
    return {"headers": ["Invoice", "Client", "Date", "Due Date", "Total", "Paid", "Balance", "Status", "Days Overdue"],
            "rows": rows, "money_cols": {4, 5, 6}}


def _receivables_ageing(ids, start, end):
    today = date.today()
    buckets: dict[int, list[float]] = {}
    for i in Invoice.query.filter(Invoice.client_id.in_(ids), Invoice.status != "paid", Invoice.balance > 0):
        b = buckets.setdefault(i.client_id, [0.0, 0.0, 0.0, 0.0, 0.0])
        days = (today - (i.due_date or i.invoice_date)).days
        slot = 0 if days <= 0 else 1 if days <= 30 else 2 if days <= 60 else 3 if days <= 90 else 4
        b[slot] += i.balance
    rows = []
    for cid, b in buckets.items():
        rows.append([db.session.get(Client, cid).name] + [round(x, 2) for x in b] + [round(sum(b), 2)])
    rows.sort(key=lambda r: -r[-1])
    if rows:
        rows.append(["TOTAL"] + [round(sum(r[k] for r in rows if r[0] != "TOTAL"), 2) for k in range(1, 7)])
    return {"headers": ["Client", "Not Yet Due", "1-30 Days", "31-60 Days", "61-90 Days", "Over 90 Days", "Total"],
            "rows": rows, "money_cols": {1, 2, 3, 4, 5, 6}}


def _monthly_revenue(ids, start, end):
    months: dict[str, list[float]] = {}
    for i in Invoice.query.filter(Invoice.client_id.in_(ids), *_between(Invoice.invoice_date, start, end)):
        months.setdefault(i.invoice_date.strftime("%Y-%m"), [0.0, 0.0])[0] += i.total_amount
    pq = Payment.query.join(Invoice).filter(Invoice.client_id.in_(ids), *_between(Payment.payment_date, start, end))
    for p in pq:
        months.setdefault(p.payment_date.strftime("%Y-%m"), [0.0, 0.0])[1] += p.amount
    rows = [[datetime.strptime(m, "%Y-%m").strftime("%b %Y"), round(v[0], 2), round(v[1], 2), round(v[0] - v[1], 2)]
            for m, v in sorted(months.items())]
    return {"headers": ["Month", "Invoiced", "Collected", "Invoiced less Collected"], "rows": rows, "money_cols": {1, 2, 3}}


def _client_register(ids, start, end):
    q = Client.query.filter(Client.id.in_(ids)).order_by(Client.name)
    rows = [[c.client_code, c.name, (c.category or "").title(), c.pan or "", c.gstin or "", c.tan or "",
             (c.contact_person or "") + (f" ({c.contact_designation})" if c.contact_person and c.contact_designation else ""), c.mobile or "", c.email or "",
             ", ".join(x for x in (c.address, c.city, c.state, c.pincode) if x), (c.status or "").title(), _name(c.assigned_to)] for c in q]
    return {"headers": ["Code", "Client", "Category", "PAN", "GSTIN", "TAN", "Contact Person", "Mobile", "Email", "Address", "Status", "Owner"], "rows": rows, "money_cols": set()}


def _gst_register(ids, start, end):
    return _gst_status(ids, start, end)


def _itr_register(ids, start, end):
    return _itr_status(ids, start, end)


def _tds_register(ids, start, end):
    return _tds_status(ids, start, end)


def _invoice_register(ids, start, end):
    q = Invoice.query.filter(Invoice.client_id.in_(ids), *_between(Invoice.invoice_date, start, end)).order_by(Invoice.invoice_date, Invoice.id)
    rows = [[i.invoice_date, i.invoice_number, i.client.name, i.client.gstin or "Unregistered", i.taxable_amount, i.cgst_amount, i.sgst_amount,
             i.igst_amount, i.total_amount, i.paid_amount, i.balance, i.status.replace("_", " ").title()] for i in q]
    if rows:
        rows.append(["", "TOTAL", "", ""] + [round(sum(r[k] for r in rows), 2) for k in range(4, 11)] + [""])
    return {"headers": ["Date", "Invoice No.", "Client", "GSTIN", "Taxable Value", "CGST", "SGST", "IGST", "Invoice Total", "Received", "Balance", "Status"],
            "rows": rows, "money_cols": {4, 5, 6, 7, 8, 9, 10}}


def _receipt_register(ids, start, end):
    q = Payment.query.join(Invoice).filter(Invoice.client_id.in_(ids), *_between(Payment.payment_date, start, end)).order_by(Payment.payment_date, Payment.id)
    rows = [[p.payment_date, p.invoice.client.name, p.invoice.invoice_number, (p.mode or "").upper(), p.reference or "", p.amount] for p in q]
    if rows:
        rows.append(["", "TOTAL", "", "", "", round(sum(r[5] for r in rows), 2)])
    return {"headers": ["Date", "Client", "Against Invoice", "Mode", "Reference", "Amount"], "rows": rows, "money_cols": {5}}


def _time_register(ids, start, end):
    from ..models import TimeEntry

    q = TimeEntry.query.filter(TimeEntry.client_id.in_(ids), *_between(TimeEntry.work_date, start, end)).order_by(TimeEntry.work_date, TimeEntry.id)
    rows = [[t.work_date, t.client.name, _name(t.user), t.description or "", round(t.hours or 0, 2), t.rate or 0, t.value if t.billable else 0,
             "Billed " + t.invoice.invoice_number if t.invoice else ("Unbilled" if t.billable else "Not billable")] for t in q]
    if rows:
        rows.append(["", "TOTAL", "", "", round(sum(r[4] for r in rows), 2), "", round(sum(r[6] for r in rows), 2), ""])
    return {"headers": ["Date", "Client", "Staff", "Work Done", "Hours", "Rate", "Value", "Billing"], "rows": rows, "money_cols": {5, 6}}


def _matter_register(ids, start, end):
    from ..models import Matter

    q = Matter.query.filter(Matter.client_id.in_(ids), Matter.status == "open", *_between(Matter.next_hearing, start, end))
    q = q.order_by(Matter.next_hearing.is_(None), Matter.next_hearing, Matter.title)
    rows = [[m.next_hearing, m.court or "", m.case_number or "", m.title, m.client.name, m.opposite_party or "", m.stage or "", _name(m.assigned_to)] for m in q]
    return {"headers": ["Next Hearing", "Court", "Case No.", "Matter", "Client", "Opposite Party", "Stage", "Handled By"], "rows": rows, "money_cols": set()}


def _own_gst_outward(ids, start, end):
    """Invoice-wise outward supplies of the firm itself, the way GSTR-1 wants them."""
    q = Invoice.query.filter(Invoice.client_id.in_(ids), *_between(Invoice.invoice_date, start, end)).order_by(Invoice.invoice_date, Invoice.id)
    rows = []
    for i in q:
        rate = (i.cgst_rate or 0) + (i.sgst_rate or 0) + (i.igst_rate or 0)
        kind = "B2B" if i.client.gstin else "B2C"
        supply = {"cgst_sgst": "Intra-State", "igst": "Inter-State", "exempt": "Nil / Exempt"}.get(i.tax_mode, i.tax_mode)
        rows.append([i.invoice_date, i.invoice_number, kind, i.client.name, i.client.gstin or "", i.client.state or "", supply, rate,
                     i.taxable_amount, i.cgst_amount, i.sgst_amount, i.igst_amount, i.total_amount])
    if rows:
        rows.append(["", "TOTAL", "", "", "", "", "", ""] + [round(sum(r[k] for r in rows), 2) for k in range(8, 13)])
    return {"headers": ["Date", "Invoice No.", "Type", "Recipient", "Recipient GSTIN", "Place of Supply", "Supply", "GST %", "Taxable Value",
                        "CGST", "SGST", "IGST", "Invoice Value"], "rows": rows, "money_cols": {8, 9, 10, 11, 12}}


def _own_gst_summary(ids, start, end):
    months: dict[str, list[float]] = {}
    for i in Invoice.query.filter(Invoice.client_id.in_(ids), *_between(Invoice.invoice_date, start, end)):
        m = months.setdefault(i.invoice_date.strftime("%Y-%m"), [0, 0.0, 0.0, 0.0, 0.0, 0.0])
        m[0] += 1
        if i.tax_mode == "exempt":
            m[2] += i.taxable_amount
        else:
            m[1] += i.taxable_amount
        m[3] += i.cgst_amount
        m[4] += i.sgst_amount
        m[5] += i.igst_amount
    rows = [[datetime.strptime(k, "%Y-%m").strftime("%b %Y"), v[0], round(v[1], 2), round(v[2], 2), round(v[3], 2), round(v[4], 2), round(v[5], 2),
             round(v[3] + v[4] + v[5], 2)] for k, v in sorted(months.items())]
    if rows:
        rows.append(["TOTAL", sum(r[1] for r in rows)] + [round(sum(r[k] for r in rows), 2) for k in range(2, 8)])
    return {"headers": ["Month", "Invoices", "Taxable Supplies", "Nil / Exempt Supplies", "CGST", "SGST", "IGST", "Total Output Tax"],
            "rows": rows, "money_cols": {2, 3, 4, 5, 6, 7}}


def _own_gst_sac(ids, start, end):
    from ..models import InvoiceItem

    sacs: dict[str, list[float]] = {}
    for i in Invoice.query.filter(Invoice.client_id.in_(ids), *_between(Invoice.invoice_date, start, end)):
        gross = sum(it.amount or 0 for it in i.items) or 1
        tax = i.cgst_amount + i.sgst_amount + i.igst_amount
        for it in i.items:
            share = (it.amount or 0) / gross
            s = sacs.setdefault(it.sac_code or "-", [0.0, 0.0, 0.0])
            s[0] += it.quantity or 0
            s[1] += i.taxable_amount * share   # after invoice-level discount
            s[2] += tax * share
    rows = [[k, round(v[0], 2), round(v[1], 2), round(v[2], 2), round(v[1] + v[2], 2)] for k, v in sorted(sacs.items())]
    if rows:
        rows.append(["TOTAL", ""] + [round(sum(r[k] for r in rows), 2) for k in range(2, 5)])
    return {"headers": ["SAC Code", "Quantity", "Taxable Value", "Tax", "Total Value"], "rows": rows, "money_cols": {2, 3, 4}}


# ------------------------------------------------------------------------------ output formats
def meta(kind: str, start: date | None, end: date | None) -> dict:
    fmt = lambda d: d.strftime("%d %b %Y")  # noqa: E731
    if start and end:
        period = f"{fmt(start)} to {fmt(end)}"
    elif start:
        period = f"From {fmt(start)}"
    elif end:
        period = f"Up to {fmt(end)}"
    else:
        period = "All dates"
    return {"title": TYPES.get(kind, "Report"), "period": period, "generated": datetime.now().strftime("%d %b %Y, %I:%M %p")}


def safe_text(v):
    """Stop spreadsheet programs treating user-entered text as a formula (CSV/Excel injection)."""
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + v
    return v


def _plain(v) -> str:
    if isinstance(v, date):
        return v.strftime("%d-%m-%Y")
    return "" if v is None else safe_text(str(v))


def to_csv(report: dict, m: dict) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    for line in letterhead.header_lines():
        w.writerow([line])
    w.writerow([])
    w.writerow([m["title"]])
    w.writerow(["Period: " + m["period"]])
    w.writerow(["Generated on: " + m["generated"]])
    w.writerow([])
    w.writerow(report["headers"])
    for row in report["rows"]:
        w.writerow([_plain(v) for v in row])
    return b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8")  # BOM so Excel reads rupee text and accents cleanly


def to_xlsx(report: dict, m: dict) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = m["title"][:31]
    logo = letterhead.report_logo_bytes()
    text_col = 2 if logo else 1
    row = 1
    for n, line in enumerate(letterhead.header_lines()):
        c = ws.cell(row=row, column=text_col, value=line)
        c.font = Font(bold=(n == 0), size=14 if n == 0 else 10, color="1E3A5F" if n == 0 else "475569")
        row += 1
    if logo:
        img = XlImage(io.BytesIO(logo))
        ratio = 70 / img.height
        img.height, img.width = 70, int(img.width * ratio)
        ws.add_image(img, "A1")
        row = max(row, 5)
    row += 1
    ws.cell(row=row, column=1, value=m["title"]).font = Font(bold=True, size=12, color="0D9488")
    ws.cell(row=row + 1, column=1, value="Period: " + m["period"])
    ws.cell(row=row + 2, column=1, value="Generated on: " + m["generated"])
    row += 4
    for i, h in enumerate(report["headers"], start=1):
        c = ws.cell(row=row, column=i, value=h)
        c.font = Font(bold=True, color="1E3A5F")
        c.fill = PatternFill("solid", fgColor="EFF6FF")
        c.alignment = Alignment(wrap_text=True, vertical="center")
    header_row = row
    for r in report["rows"]:
        row += 1
        for i, v in enumerate(r, start=1):
            c = ws.cell(row=row, column=i, value=safe_text(v))
            if isinstance(v, date):
                c.number_format = "DD-MMM-YYYY"
            elif (i - 1) in report["money_cols"]:
                c.number_format = '#,##0.00'
    for i, h in enumerate(report["headers"], start=1):
        longest = max([len(str(h))] + [len(_plain(r[i - 1])) for r in report["rows"][:200]])
        ws.column_dimensions[get_column_letter(i)].width = min(max(12, longest + 2), 45)
    ws.freeze_panes = ws.cell(row=header_row + 1, column=1)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def display(v, is_money: bool) -> str:
    if isinstance(v, date):
        return v.strftime("%d %b %Y")
    if v is None:
        return "—"
    if is_money:
        return pdfutil.money(v)
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def to_pdf(report: dict, m: dict) -> bytes:
    st = styles()
    regular, bold, _ = pdfutil.fonts()
    pagesize = landscape(A4)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=pagesize, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm,
                            bottomMargin=14 * mm, title=m["title"])
    width = pagesize[0] - 24 * mm
    story = pdfutil.letterhead_block(letterhead.report_profile(), width, m["title"], "Generated on " + m["generated"], "Period: " + m["period"])

    ncols = len(report["headers"])
    data = [[P(h, st["th"]) for h in report["headers"]]]
    for r in report["rows"]:
        data.append([P(display(v, i in report["money_cols"]), st["right"] if i in report["money_cols"] else st["body"])
                     for i, v in enumerate(r)])
    if not report["rows"]:
        data.append([P("No records found for this report criteria.", st["body"])] + [""] * (ncols - 1))
    table = Table(data, colWidths=[width / ncols] * ncols, repeatRows=1)
    ts = [("BACKGROUND", (0, 0), (-1, 0), pdfutil.LIGHT), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
          ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 3),
          ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")])]
    if not report["rows"]:
        ts.append(("SPAN", (0, 1), (-1, 1)))
    table.setStyle(TableStyle(ts))
    story += [table, Spacer(1, 6), P(f"{len(report['rows'])} record(s)", st["small"])]

    firm = letterhead.profile()["name"]

    def footer(canvas, d):
        canvas.saveState()
        canvas.setFont(regular, 7.5)
        canvas.setFillColor(pdfutil.GREY)
        canvas.drawString(12 * mm, 7 * mm, firm)
        canvas.drawRightString(pagesize[0] - 12 * mm, 7 * mm, f"Page {d.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
