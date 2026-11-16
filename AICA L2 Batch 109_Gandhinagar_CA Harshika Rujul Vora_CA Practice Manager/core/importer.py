"""Excel templates, bulk import of clients, and full Excel export (backup / reports)."""
import io
import re

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from . import db, duedates
from .constants import ENTITY_TYPES, GST_FREQ, STATES

PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")

CLIENT_COLUMNS = ["Client Name*", "Entity Type", "PAN", "GSTIN", "State", "Contact Person", "Email", "Phone",
                  "GST Filing", "TDS", "Income Tax Return", "Tax Audit", "Monthly Fee"]
EXAMPLE = ["Shreeji Traders", "Proprietorship", "ABCPS1234A", "24ABCPS1234A1Z5", "Gujarat", "Ramesh Shah",
           "ramesh@example.com", "9876543210", "Monthly", "No", "Yes", "Yes", 5000]


def client_template() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Clients"
    ws.append(CLIENT_COLUMNS)
    ws.append(EXAMPLE)
    head = PatternFill("solid", fgColor="0B1F3A")
    for i, cell in enumerate(ws[1], 1):
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = head
        cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[cell.column_letter].width = max(14, len(CLIENT_COLUMNS[i - 1]) + 4)
    ws.column_dimensions["A"].width = 32
    ws.freeze_panes = "A2"

    lists = wb.create_sheet("Lists")
    for col, values in enumerate([ENTITY_TYPES, STATES, GST_FREQ, ["Yes", "No"]], 1):
        for r, v in enumerate(values, 1):
            lists.cell(row=r, column=col, value=v)
    lists.sheet_state = "hidden"

    def dv(formula, rng):
        v = DataValidation(type="list", formula1=formula, allow_blank=True)
        ws.add_data_validation(v)
        v.add(rng)

    dv(f"=Lists!$A$1:$A${len(ENTITY_TYPES)}", "B2:B2000")
    dv(f"=Lists!$B$1:$B${len(STATES)}", "E2:E2000")
    dv(f"=Lists!$C$1:$C${len(GST_FREQ)}", "I2:I2000")
    dv("=Lists!$D$1:$D$2", "J2:L2000")

    info = wb.create_sheet("How to fill")
    for line in [
        "How to fill this template",
        "1. One client per row on the 'Clients' sheet. Delete the example row first.",
        "2. Only 'Client Name' is compulsory. Use the drop-downs for Entity Type, State, GST Filing and Yes/No columns.",
        "3. PAN must look like ABCDE1234F; GSTIN must be 15 characters.",
        "4. GST Filing: None, Monthly or Quarterly (QRMP).",
        "5. In the app: Clients > Import from Excel > upload this file > check the preview > Import.",
        "6. Statutory tasks for the current financial year are created automatically for every imported client.",
    ]:
        info.append([line])
    info["A1"].font = Font(bold=True, size=13)
    info.column_dimensions["A"].width = 110
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _yes(v) -> int:
    return int(str(v).strip().lower() in ("yes", "y", "true", "1"))


def parse_clients(file) -> pd.DataFrame:
    """Return a preview DataFrame with an 'Issues' column. Rows with no issues can be imported."""
    df = pd.read_excel(file, sheet_name=0, dtype=str).fillna("")
    df.columns = [c.strip().rstrip("*") for c in df.columns]
    need = [c.rstrip("*") for c in CLIENT_COLUMNS]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise ValueError("Columns missing from the file: " + ", ".join(missing) + ". Please use the template.")
    df = df[need]
    df = df[df["Client Name"].str.strip() != ""].copy()
    existing_pans = {r["pan"] for r in db.query("SELECT pan FROM clients WHERE pan IS NOT NULL AND pan <> ''")}
    issues, seen = [], set()
    for _, r in df.iterrows():
        p = []
        pan = r["PAN"].strip().upper()
        gstin = r["GSTIN"].strip().upper()
        if pan and not PAN_RE.match(pan):
            p.append("PAN format")
        if gstin and not GSTIN_RE.match(gstin):
            p.append("GSTIN format")
        if pan and gstin and GSTIN_RE.match(gstin) and gstin[2:12] != pan:
            p.append("GSTIN doesn't contain this PAN")
        if pan and (pan in existing_pans or pan in seen):
            p.append("PAN already exists")
        if r["Entity Type"] and r["Entity Type"] not in ENTITY_TYPES:
            p.append("Entity type")
        if r["GST Filing"] and r["GST Filing"] not in GST_FREQ:
            p.append("GST Filing must be None/Monthly/Quarterly")
        if r["Monthly Fee"]:
            try:
                float(str(r["Monthly Fee"]).replace(",", ""))
            except ValueError:
                p.append("Fee not a number")
        seen.add(pan)
        issues.append(", ".join(p))
    df["Issues"] = issues
    return df


def import_clients(df: pd.DataFrame, manager_id=None) -> tuple[int, int]:
    fy = duedates.current_fy_start()
    n_clients = n_tasks = 0
    for _, r in df[df["Issues"] == ""].iterrows():
        cid = db.insert(
            "INSERT INTO clients(name,entity_type,pan,gstin,state,contact_person,email,phone,gst_freq,has_tds,"
            "needs_itr,needs_audit,monthly_fee,manager_id,created_on) VALUES "
            "(:n,:e,:pan,:g,:s,:cp,:em,:ph,:gf,:tds,:itr,:aud,:fee,:m,:c) RETURNING id",
            n=r["Client Name"].strip(), e=r["Entity Type"] or "Individual", pan=r["PAN"].strip().upper(),
            g=r["GSTIN"].strip().upper(), s=r["State"] or "Gujarat", cp=r["Contact Person"], em=r["Email"],
            ph=r["Phone"], gf=r["GST Filing"] or "None", tds=_yes(r["TDS"]),
            itr=_yes(r["Income Tax Return"]) if r["Income Tax Return"] else 1, aud=_yes(r["Tax Audit"]),
            fee=float(str(r["Monthly Fee"] or 0).replace(",", "")), m=manager_id, c=db.now())
        client = db.one("SELECT * FROM clients WHERE id=:i", i=cid)
        n_tasks += duedates.generate_for_client(client, fy)
        n_clients += 1
    return n_clients, n_tasks


def export_all() -> bytes:
    sheets = {
        "Clients": "SELECT c.id, c.name, c.entity_type, c.pan, c.gstin, c.state, c.contact_person, c.email, c.phone, "
                   "c.gst_freq, c.has_tds, c.needs_itr, c.needs_audit, c.monthly_fee, u.name AS manager, c.active "
                   "FROM clients c LEFT JOIN users u ON u.id=c.manager_id ORDER BY c.name",
        "Tasks": "SELECT t.id, c.name AS client, t.category, t.title, t.period, t.due_date, t.status, t.priority, "
                 "u.name AS assigned_to, t.completed_on, t.notes FROM tasks t JOIN clients c ON c.id=t.client_id "
                 "LEFT JOIN users u ON u.id=t.assigned_to ORDER BY t.due_date",
        "Invoices": "SELECT i.invoice_no, c.name AS client, i.invoice_date, i.due_date, i.description, i.sac, "
                    "i.taxable_value, i.cgst, i.sgst, i.igst, i.total, i.status, i.paid_on "
                    "FROM invoices i JOIN clients c ON c.id=i.client_id ORDER BY i.invoice_date",
        "Activity": "SELECT l.at, u.name AS by_user, c.name AS client, t.title, t.period, l.action, l.detail "
                    "FROM task_log l LEFT JOIN users u ON u.id=l.user_id LEFT JOIN tasks t ON t.id=l.task_id "
                    "LEFT JOIN clients c ON c.id=t.client_id ORDER BY l.at DESC",
        "Documents": "SELECT c.name AS client, d.category, d.fin_year, d.filename, d.size_bytes, d.uploaded_on "
                     "FROM documents d JOIN clients c ON c.id=d.client_id ORDER BY d.uploaded_on DESC",
    }
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for name, sql in sheets.items():
            df = pd.DataFrame(db.query(sql))
            if df.empty:
                df = pd.DataFrame({"(no data)": []})
            df.to_excel(xw, sheet_name=name, index=False)
            ws = xw.sheets[name]
            for cell in ws[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="0B1F3A")
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = 18
            ws.freeze_panes = "A2"
    return buf.getvalue()
