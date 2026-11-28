import calendar
import io
from datetime import date, datetime

from flask import Blueprint, abort, render_template, request, send_file
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from . import gst, services as sv
from .models import CANCELLED, FINAL, Challan, Plant, SeriesConfig, Vendor

bp = Blueprint("reports", __name__, url_prefix="/reports")

CATALOG = [
    ("monthly", "Monthly challan register", "All challans for a month with every header and line-item field."),
    ("range", "Date-range register", "Same as monthly with flexible From / To dates."),
    ("gstr1", "GSTR-1 documents issued (Table 13)", "First / last number, total, cancelled and net issued per series."),
    ("pending_ewb", "Pending e-way bill", "Issued challans with no e-way bill number yet."),
    ("returnables", "Open / overdue returnable challans", "Returnables not fully received, with the statutory (Sec. 143) due date."),
    ("vendors", "Vendor master export", "All vendors with ERP code status."),
]


def _d(s, default=None):
    return sv._date(s) or default


def _num(x):
    return float(x) if x is not None else None


# ------------------------------------------------------------------ report builders
def _register(d1, d2, ctype=None, plant_id=None):
    q = Challan.query.filter(Challan.status.in_([FINAL, CANCELLED]), Challan.challan_date >= d1, Challan.challan_date <= d2)
    if ctype in ("MRC", "MNRC"):
        q = q.filter(Challan.ctype == ctype)
    if plant_id and str(plant_id).isdigit():
        q = q.filter(Challan.plant_id == int(plant_id))
    heads = ["Challan No", "Date", "Type", "Status", "Plant", "Vendor No", "Consignee", "Consignee GSTIN", "State code",
             "Place of supply", "Supply type", "Purpose", "Purpose detail", "Reason", "Ref doc no", "Ref doc date",
             "Transport mode", "Vehicle no", "Transporter", "Transporter ID", "E-way status", "E-way no", "E-way date",
             "E-way valid upto", "Return status", "Cancel reason", "Line", "Part no", "Description", "HSN", "Qty",
             "UoM", "Rate", "Taxable value", "GST %", "CGST", "SGST/UTGST", "IGST", "Cess", "Line total", "Qty received"]
    rows, cls = [], []
    for c in q.order_by(Challan.ctype, Challan.seq_no, Challan.id):
        ce = sv.consignee(c)
        base = [c.number, c.challan_date, c.ctype, c.status, c.plant.code, ce["vendor_no"], ce["name"], ce["gstin"] or "",
                ce["state_code"], c.place_of_supply, "Inter-state" if c.interstate else "Intra-state", c.purpose,
                c.purpose_text, c.reason, c.ref_doc_no, c.ref_doc_date, c.transport_mode, c.vehicle_no,
                c.transporter_name, c.transporter_id, c.ewb_status, c.ewb_no, c.ewb_date, c.ewb_valid_upto,
                c.return_status, c.cancel_reason]
        for l in c.lines:
            rows.append(base + [l.line_no, l.part_no, l.description, l.hsn, _num(l.qty), l.uom, _num(l.rate),
                                _num(l.taxable_value), _num(l.tax_rate), _num(l.cgst), _num(l.sgst), _num(l.igst),
                                _num(l.cess), _num(l.line_total), _num(l.qty_received) if c.is_returnable else None])
            cls.append("cancelled" if c.status == CANCELLED else "")
    return heads, rows, cls


def r_monthly(a):
    m = a.get("month") or date.today().strftime("%Y-%m")
    try:
        y, mo = int(m[:4]), int(m[5:7])
        d1, d2 = date(y, mo, 1), date(y, mo, calendar.monthrange(y, mo)[1])
    except (ValueError, IndexError):
        d1 = d2 = date.today()
    heads, rows, cls = _register(d1, d2, a.get("ctype"), a.get("plant"))
    return dict(title=f"Monthly challan register - {d1:%B %Y}", heads=heads, rows=rows, cls=cls,
                filters=["month", "ctype", "plant"], note="Cancelled challans are struck through and kept in the register.")


def r_range(a):
    d1 = _d(a.get("from"), date.today().replace(day=1))
    d2 = _d(a.get("to"), date.today())
    heads, rows, cls = _register(d1, d2, a.get("ctype"), a.get("plant"))
    return dict(title=f"Challan register {d1:%d-%m-%Y} to {d2:%d-%m-%Y}", heads=heads, rows=rows, cls=cls,
                filters=["from", "to", "ctype", "plant"])


def r_gstr1(a):
    d1 = _d(a.get("from"), date.today().replace(day=1))
    d2 = _d(a.get("to"), date.today())
    heads = ["Series", "Nature of document", "Sr. No. from", "Sr. No. to", "Total number", "Cancelled", "Net issued",
             "Cancelled numbers", "Gaps in sequence (numbers missing in range)"]
    rows = []
    for cfg in SeriesConfig.query.order_by(SeriesConfig.ctype):
        nature = ("Delivery Challan - job work / other than by way of supply (returnable)" if cfg.returnable
                  else "Delivery Challan - other than by way of supply (non-returnable)")
        for fy in sorted({c.fy for c in Challan.query.filter(Challan.ctype == cfg.ctype, Challan.fy.isnot(None))}):
            cs = (Challan.query.filter(Challan.ctype == cfg.ctype, Challan.fy == fy, Challan.status.in_([FINAL, CANCELLED]),
                                       Challan.challan_date >= d1, Challan.challan_date <= d2).order_by(Challan.seq_no).all())
            if not cs:
                continue
            canc = [c for c in cs if c.status == CANCELLED]
            seqs = [c.seq_no for c in cs]
            gaps = sorted(set(range(min(seqs), max(seqs) + 1)) - set(seqs))
            rows.append([f"{cfg.ctype} ({fy})", nature, cs[0].number, cs[-1].number, len(cs), len(canc), len(cs) - len(canc),
                         ", ".join(c.number for c in canc) or "-",
                         ", ".join(sv.format_number(cfg, fy, g) for g in gaps) or "None"])
    return dict(title=f"GSTR-1 Table 13 - documents issued {d1:%d-%m-%Y} to {d2:%d-%m-%Y}", heads=heads, rows=rows,
                cls=[""] * len(rows), filters=["from", "to"],
                note="Figures are per series and financial year for challans dated in the period. 'Net issued' = total - cancelled. "
                     "Cross-check the nature-of-document mapping with your GST consultant before filing.")


def r_pending_ewb(a):
    heads = ["Challan No", "Date", "Type", "Vendor", "Purpose", "Value", "Days since issue", "Transport", "Created by"]
    rows, cls = [], []
    for c in Challan.query.filter_by(status=FINAL, ewb_status="Pending").order_by(Challan.challan_date):
        days = (date.today() - c.challan_date).days
        rows.append([c.number, c.challan_date, c.ctype, c.vendor.name, c.purpose, _num(c.grand_total), days,
                     f"{c.transport_mode or ''} {c.vehicle_no or ''}".strip(), c.created_by])
        cls.append("overdue" if days >= 2 else "")
    return dict(title="Pending e-way bill", heads=heads, rows=rows, cls=cls, filters=[],
                note="Highlighted: issued 2 or more days ago and still without an e-way bill number.", link_col=0)


def r_returnables(a):
    heads = ["Challan No", "Date", "Vendor", "Purpose", "Goods category", "Qty sent", "Qty received", "Qty pending",
             "Return status", "Statutory limit (Sec.143)", "Statutory overdue?"]
    rows, cls = [], []
    today = date.today()
    only_overdue = a.get("only") == "overdue"
    for c in Challan.query.filter(Challan.ctype == "MRC", Challan.status == FINAL,
                                  Challan.return_status != "Closed").order_by(Challan.challan_date):
        sd = c.statutory_due()
        od = bool(sd and sd < today)
        if only_overdue and not od:
            continue
        rows.append([c.number, c.challan_date, c.vendor.name, c.purpose, "Capital goods" if c.goods_category == "CAPITAL" else "Inputs",
                     _num(c.total_qty), _num(c.received_qty), _num(c.total_qty - c.received_qty), c.return_status,
                     sd, "YES" if od else "No"])
        cls.append("overdue" if od else "")
    return dict(title="Open / overdue returnable challans", heads=heads, rows=rows, cls=cls, filters=["only"],
                note="Job-work time limits under the CGST Act: inputs 1 year, capital goods 3 years from the date of sending "
                     "(confirm current law with your GST advisor).", link_col=0)


def r_vendors(a):
    heads = ["Vendor No", "Name", "Address", "State", "PIN", "GSTIN", "PAN", "Contact", "Phone", "Email", "ERP code",
             "ERP status", "ERP code updated on", "Active", "Manual challans (MRC)", "Manual challans (MNRC)", "Created on"]
    rows = []
    counts = {}
    for c in Challan.query.filter_by(status=FINAL):
        counts.setdefault(c.vendor_id, {"MRC": 0, "MNRC": 0})[c.ctype] += 1
    for v in Vendor.query.order_by(Vendor.vendor_no):
        n = counts.get(v.id, {"MRC": 0, "MNRC": 0})
        rows.append([v.vendor_no, v.name, v.address, gst.state_label(v.state_code), v.pin, v.gstin, v.pan, v.contact_person,
                     v.phone, v.email, v.erp_code, "Set up in ERP" if v.erp_code else "NOT in ERP", v.erp_code_updated_at,
                     "Yes" if v.active else "No", n["MRC"], n["MNRC"], v.created_at])
    return dict(title="Vendor master", heads=heads, rows=rows, cls=[""] * len(rows), filters=[])


REPORTS = {"monthly": r_monthly, "range": r_range, "gstr1": r_gstr1, "pending_ewb": r_pending_ewb,
           "returnables": r_returnables, "vendors": r_vendors}


# ------------------------------------------------------------------ views
@bp.route("/")
def index():
    return render_template("reports/index.html", catalog=CATALOG)


def to_xlsx(rep):
    wb = Workbook()
    ws = wb.active
    ws.title = rep["title"][:31].replace("/", "-")
    ws.append([rep["title"]])
    ws["A1"].font = Font(bold=True, size=13)
    ws.append([f"Generated {datetime.now():%d-%m-%Y %H:%M}"])
    ws.append([])
    ws.append(rep["heads"])
    for c in ws[4]:
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor="DDE6F0")
        c.alignment = Alignment(wrap_text=True, vertical="top")
    red = PatternFill("solid", fgColor="FADBD8")
    for row, cl in zip(rep["rows"], rep["cls"]):
        ws.append(row)
        r = ws.max_row
        for cell in ws[r]:
            if isinstance(cell.value, (date, datetime)):
                cell.number_format = "DD-MM-YYYY" if not isinstance(cell.value, datetime) else "DD-MM-YYYY HH:MM"
            if cl == "overdue":
                cell.fill = red
            elif cl == "cancelled":
                cell.font = Font(strike=True, color="888888")
    for i, h in enumerate(rep["heads"], 1):
        width = max([len(str(h))] + [len(str(r[i - 1] if r[i - 1] is not None else "")) for r in rep["rows"][:200]])
        ws.column_dimensions[get_column_letter(i)].width = min(max(width + 2, 10), 45)
    ws.freeze_panes = "A5"
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


@bp.route("/<name>")
def show(name):
    fn = REPORTS.get(name)
    if not fn:
        abort(404)
    a = request.args.to_dict()
    rep = fn(a)
    if a.get("export") == "xlsx":
        return send_file(to_xlsx(rep), as_attachment=True, download_name=f"{name}_{date.today():%Y%m%d}.xlsx",
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    return render_template("reports/table.html", rep=rep, name=name, a=a,
                           plants=Plant.query.order_by(Plant.code).all(), month=a.get("month") or date.today().strftime("%Y-%m"),
                           count=len(rep["rows"]))
