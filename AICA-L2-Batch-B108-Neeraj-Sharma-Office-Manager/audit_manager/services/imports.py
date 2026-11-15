"""Bulk client import from Excel, plus the downloadable template."""
import io
import re

from openpyxl import Workbook, load_workbook

from ..models import Client, db

COLUMNS = ["Name", "Category", "PAN", "GSTIN", "TAN", "Email", "Mobile", "Address", "City", "State", "Pincode", "Status", "Contact Person", "Designation"]
PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


def template_xlsx() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Clients"
    ws.append(COLUMNS)
    ws.append(["Apex Precision Pvt Ltd", "business", "AABCA1234F", "03AABCA1234F1Z5", "", "accounts@apex.in", "9876543210",
               "Main Bazar", "Abohar", "Punjab", "152116", "active", "Rajesh Kumar", "Director"])
    for i, w in enumerate([30, 12, 14, 20, 14, 26, 14, 30, 16, 16, 10, 12, 22, 18], start=1):
        ws.column_dimensions[chr(64 + i)].width = w
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def next_client_code() -> str:
    last = db.session.query(db.func.max(Client.id)).scalar() or 0
    code = f"CL-{last + 1:04d}"
    while Client.query.filter_by(client_code=code).first():
        last += 1
        code = f"CL-{last + 1:04d}"
    return code


def import_clients(stream, assign_to_id: int | None = None) -> dict:
    """Returns {'created': n, 'skipped': n, 'errors': [(row, message)]}. Rows are all-or-nothing per row."""
    result = {"created": 0, "skipped": 0, "errors": []}
    try:
        wb = load_workbook(stream, read_only=True, data_only=True)
    except Exception:
        result["errors"].append((0, "That file is not a valid .xlsx workbook."))
        return result

    rows = wb.active.iter_rows(values_only=True)
    try:
        header = [str(h or "").strip().lower() for h in next(rows)]
    except StopIteration:
        result["errors"].append((0, "The file is empty."))
        return result
    if "name" not in header:
        result["errors"].append((1, "No 'Name' column found in the first row. Use the template."))
        return result
    idx = {h: i for i, h in enumerate(header)}

    def cell(row, key):
        i = idx.get(key)
        if i is None or i >= len(row) or row[i] is None:
            return ""
        return str(row[i]).strip()

    seen_pans: set[str] = set()
    for n, row in enumerate(rows, start=2):
        if not any(row):
            continue
        name = cell(row, "name")
        pan = cell(row, "pan").upper()
        gstin = cell(row, "gstin").upper()
        if not name:
            result["errors"].append((n, "Name is missing."))
            continue
        if pan and not PAN_RE.match(pan):
            result["errors"].append((n, f"{name}: PAN '{pan}' is not valid."))
            continue
        if gstin and not GSTIN_RE.match(gstin):
            result["errors"].append((n, f"{name}: GSTIN '{gstin}' is not valid."))
            continue
        if gstin and not pan:
            pan = gstin[2:12]
        if pan and (pan in seen_pans or Client.query.filter_by(pan=pan, archived=False).first()):
            result["skipped"] += 1
            continue
        if not pan and Client.query.filter(db.func.lower(Client.name) == name.lower(), Client.archived.is_(False)).first():
            result["skipped"] += 1
            continue
        category = cell(row, "category").lower()
        status = cell(row, "status").lower()
        mobile = re.sub(r"\.0$", "", cell(row, "mobile"))
        db.session.add(Client(
            client_code=next_client_code(), name=name,
            category=category if category in ("individual", "business") else "business",
            pan=pan or None, gstin=gstin or None, tan=cell(row, "tan").upper() or None,
            email=cell(row, "email") or None, mobile=mobile or None, address=cell(row, "address") or None,
            city=cell(row, "city") or None, state=cell(row, "state") or None,
            pincode=re.sub(r"\.0$", "", cell(row, "pincode")) or None,
            status=status if status in ("active", "onboarding", "inactive") else "active",
            is_gst_registered=bool(gstin), assigned_to_id=assign_to_id,
            contact_person=cell(row, "contact person")[:120] or None, contact_designation=cell(row, "designation")[:80] or None,
        ))
        db.session.flush()  # so the next generated client code is unique
        if pan:
            seen_pans.add(pan)
        result["created"] += 1
    db.session.commit()
    return result


# ------------------------------------------------------------------ filing imports (GST monthly/quarterly, ITR, TDS quarterly)
from datetime import date as _date, datetime as _datetime

FILING_COLUMNS = {
    "gst": ["Client Code", "GSTIN", "PAN", "Client Name", "Return Type", "Period", "Due Date", "Status", "Filed Date", "ARN"],
    "itr": ["Client Code", "PAN", "Client Name", "Assessment Year", "Form", "Due Date", "Status", "Filed Date", "Ack Number", "Refund Amount",
            "Verification", "Verification Date"],
    "tds": ["Client Code", "PAN", "Client Name", "Financial Year", "Quarter", "Form", "Due Date", "Status", "Filed Date",
            "TDS Deducted", "TDS Deposited", "Challan Number", "Ack Number"],
}
FILING_SAMPLES = {
    "gst": [["", "03AABCA1234F1Z5", "", "Apex Precision Pvt Ltd", "GSTR-3B", "2026-10", "20-11-2026", "Filed", "18-11-2026", "AA0311260001234"],
            ["CL-0002", "", "", "Beta Traders", "GSTR-1", "2026-Q2", "", "Pending", "", ""]],
    "itr": [["", "AABCA1234F", "Apex Precision Pvt Ltd", "2026-27", "ITR-6", "31-10-2026", "Filed", "25-10-2026", "123456789012345", "0", "e-Verified", "25-10-2026"],
            ["CL-0003", "", "Charlie Individual", "2026-27", "ITR-1", "", "Pending", "", "", "", "", ""]],
    "tds": [["", "AABCA1234F", "Apex Precision Pvt Ltd", "2026-27", "Q2", "26Q", "31-10-2026", "Filed", "28-10-2026", "45000", "45000", "CH12345", "770000123456789"]],
}
FILING_HELP = {
    "gst": ["Identify the client by Client Code, GSTIN or PAN (any one). Client Name is only for your reference.",
            "Return Type must match a return type in the app, e.g. GSTR-1, GSTR-3B.",
            "Period: monthly returns as YYYY-MM (2026-10); quarterly returns as YYYY-Qn (2026-Q2).",
            "Due Date and Filed Date as DD-MM-YYYY. Leave Due Date blank to use the standard due date.",
            "Status: Pending, Documents Pending, In Progress, Ready to File or Filed. A row with a Filed Date counts as Filed.",
            "Importing the same file again updates the existing rows instead of duplicating them."],
    "itr": ["Identify the client by Client Code or PAN.", "Assessment Year as 2026-27. Form as ITR-1 ... ITR-7.",
            "Verification: e-Verified, ITR-V sent by post, or ITR-V received at CPC. Leave blank if not yet verified.",
            "Dates as DD-MM-YYYY. Leave Due Date blank to use the standard due date.",
            "Importing the same file again updates the existing rows."],
    "tds": ["Identify the client by Client Code or PAN.", "Financial Year as 2026-27. Quarter as Q1, Q2, Q3 or Q4. Form as 24Q, 26Q, 27Q or 27EQ.",
            "Dates as DD-MM-YYYY. Leave Due Date blank to use the standard due date.",
            "Importing the same file again updates the existing rows."],
}


def filing_template(kind: str) -> bytes:
    from openpyxl.styles import Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = kind.upper() + " filings"
    ws.append(FILING_COLUMNS[kind])
    for row in FILING_SAMPLES[kind]:
        ws.append(row)
    for i, _ in enumerate(FILING_COLUMNS[kind], start=1):
        c = ws.cell(row=1, column=i)
        c.font, c.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1E3A5F")
        ws.column_dimensions[c.column_letter].width = 20
    ws.freeze_panes = "A2"
    hs = wb.create_sheet("How to fill")
    hs.column_dimensions["A"].width = 120
    hs.append(["Delete the sample rows and type or paste your own. Keep the heading row as it is."])
    for line in FILING_HELP[kind]:
        hs.append([line])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _to_date(v):
    if v is None or v == "":
        return None
    if isinstance(v, _datetime):
        return v.date()
    if isinstance(v, _date):
        return v
    text = str(v).strip()
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d.%m.%Y", "%d-%b-%Y", "%d %b %Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return _datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise ValueError(text)


def _num(v) -> float:
    try:
        return float(str(v).replace(",", "").strip() or 0)
    except ValueError:
        return 0.0


def import_filings(kind: str, stream, clients_query) -> dict:
    """Create or update tracker rows from Excel. Returns {'created','updated','errors':[(row, msg)]}."""
    from ..models import GstReturn, GstReturnType, ItrFiling, TdsReturn
    from . import compliance as comp

    result = {"created": 0, "updated": 0, "errors": []}
    try:
        wb = load_workbook(stream, read_only=True, data_only=True)
    except Exception:
        result["errors"].append((0, "That file is not a valid .xlsx workbook."))
        return result
    rows = wb.worksheets[0].iter_rows(values_only=True)
    try:
        header = [str(h or "").strip().lower() for h in next(rows)]
    except StopIteration:
        result["errors"].append((0, "The file is empty."))
        return result
    idx = {h: i for i, h in enumerate(header)}
    need = {"gst": ["return type", "period"], "itr": ["assessment year"], "tds": ["financial year", "quarter"]}[kind]
    missing = [n for n in need if n not in idx]
    if missing:
        result["errors"].append((1, "Missing column(s): " + ", ".join(m.title() for m in missing) + ". Download the sample template and use its headings."))
        return result

    clients = clients_query.all()
    by_code = {(c.client_code or "").upper(): c for c in clients}
    by_gstin = {(c.gstin or "").upper(): c for c in clients if c.gstin}
    by_pan = {(c.pan or "").upper(): c for c in clients if c.pan}
    by_name = {c.name.strip().lower(): c for c in clients}
    statuses = {**{k: k for k in comp.RETURN_STATUSES}, **{v.lower(): k for k, v in comp.RETURN_STATUSES.items()}}
    types = {t.name.strip().lower().replace(" ", ""): t for t in GstReturnType.query.all()} if kind == "gst" else {}

    def cell(row, key):
        i = idx.get(key)
        return "" if i is None or i >= len(row) or row[i] is None else row[i]

    def text(row, key):
        v = cell(row, key)
        return re.sub(r"\.0$", "", str(v).strip()) if not isinstance(v, (_date, _datetime)) else str(v)

    for n, row in enumerate(rows, start=2):
        if not any(v not in (None, "") for v in row):
            continue
        client = (by_code.get(text(row, "client code").upper()) or by_gstin.get(text(row, "gstin").upper())
                  or by_pan.get(text(row, "pan").upper()) or by_name.get(text(row, "client name").lower()))
        if client is None:
            result["errors"].append((n, "Client not found. Give a Client Code, GSTIN or PAN that exists in Clients."))
            continue
        try:
            due, filed = _to_date(cell(row, "due date")), _to_date(cell(row, "filed date"))
        except ValueError as e:
            result["errors"].append((n, f"{client.name}: date '{e}' is not understood. Use DD-MM-YYYY."))
            continue
        raw_status = text(row, "status").lower().replace("-", " ")
        status = statuses.get(raw_status) or statuses.get(raw_status.replace(" ", "_"))
        if raw_status and not status:
            result["errors"].append((n, f"{client.name}: status '{text(row, 'status')}' is not one of {', '.join(comp.RETURN_STATUSES.values())}."))
            continue
        if filed and not raw_status:
            status = "filed"
        status = status or "pending"

        if kind == "gst":
            rt = types.get(text(row, "return type").lower().replace(" ", ""))
            period = text(row, "period").upper()
            if rt is None:
                result["errors"].append((n, f"{client.name}: return type '{text(row, 'return type')}' is not set up in the app."))
                continue
            if not comp.valid_gst_period(rt, period):
                want = "YYYY-Qn, e.g. 2026-Q2" if rt.frequency == "quarterly" else "YYYY-MM, e.g. 2026-10"
                result["errors"].append((n, f"{client.name}: period '{period}' is wrong for {rt.name} ({rt.frequency}). Use {want}."))
                continue
            obj = GstReturn.query.filter_by(client_id=client.id, return_type_id=rt.id, period=period).first()
            new = obj is None
            if new:
                obj = GstReturn(client_id=client.id, return_type_id=rt.id, period=period, assigned_to_id=client.assigned_to_id)
                db.session.add(obj)
            obj.due_date = due or obj.due_date or comp.gst_due_date(rt, period)
            obj.arn = text(row, "arn") or obj.arn
        elif kind == "itr":
            ay, form = text(row, "assessment year"), (text(row, "form") or "ITR-1").upper()
            if not re.fullmatch(r"\d{4}-\d{2}", ay):
                result["errors"].append((n, f"{client.name}: assessment year '{ay}' should look like 2026-27."))
                continue
            if form not in comp.ITR_FORMS:
                result["errors"].append((n, f"{client.name}: form '{form}' is not a valid ITR form."))
                continue
            obj = ItrFiling.query.filter_by(client_id=client.id, assessment_year=ay, form_type=form).first()
            new = obj is None
            if new:
                obj = ItrFiling(client_id=client.id, assessment_year=ay, form_type=form, assigned_to_id=client.assigned_to_id)
                db.session.add(obj)
            obj.due_date = due or obj.due_date or comp.itr_due_date(ay)
            obj.ack_number = text(row, "ack number") or obj.ack_number
            if text(row, "refund amount"):
                obj.refund_amount = _num(cell(row, "refund amount"))
            ver = text(row, "verification").lower().replace("-", " ").replace("  ", " ")
            if ver:
                key = ("e_verified" if ver.startswith("e ver") or ver in ("everified", "verified", "evc") else
                       "itrv_received" if "received" in ver else "itrv_sent" if "itr" in ver or "post" in ver else None)
                if key:
                    obj.verification_status = key
                    try:
                        obj.verification_date = _to_date(cell(row, "verification date")) or obj.verification_date
                    except ValueError:
                        pass
        else:
            fy, q, form = text(row, "financial year"), text(row, "quarter").upper(), (text(row, "form") or "26Q").upper()
            if not re.fullmatch(r"\d{4}-\d{2}", fy) or q not in ("Q1", "Q2", "Q3", "Q4"):
                result["errors"].append((n, f"{client.name}: financial year should look like 2026-27 and quarter like Q2."))
                continue
            if form not in comp.TDS_FORMS:
                result["errors"].append((n, f"{client.name}: form '{form}' is not a valid TDS form."))
                continue
            obj = TdsReturn.query.filter_by(client_id=client.id, financial_year=fy, quarter=q, form_type=form).first()
            new = obj is None
            if new:
                obj = TdsReturn(client_id=client.id, financial_year=fy, quarter=q, form_type=form, assigned_to_id=client.assigned_to_id)
                db.session.add(obj)
            obj.due_date = due or obj.due_date or comp.tds_due_date(fy, q)
            if text(row, "tds deducted"):
                obj.tds_deducted = _num(cell(row, "tds deducted"))
            if text(row, "tds deposited"):
                obj.tds_deposited = _num(cell(row, "tds deposited"))
            obj.challan_number = text(row, "challan number") or obj.challan_number
            obj.ack_number = text(row, "ack number") or obj.ack_number
        obj.status = status
        obj.filed_date = filed or (obj.filed_date if status == "filed" else None)
        db.session.flush()
        result["created" if new else "updated"] += 1
    db.session.commit()
    return result
