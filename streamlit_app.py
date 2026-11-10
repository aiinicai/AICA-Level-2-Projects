"""Lordship Africa Payroll - Streamlit browser application.

Browser-based replacement for the Tkinter desktop UI (app.py). All payroll
calculations, validations and database logic are unchanged and still come from
config.py, database.py, engine.py and reports.py, which must sit in the same
folder as this file.

Run:  streamlit run streamlit_app.py
"""
from __future__ import annotations

import csv
import io
import json
import mimetypes
import os
import re
import sqlite3
import tempfile
import zipfile
from datetime import date, datetime

import pandas as pd
import streamlit as st

# --- UI shim -----------------------------------------------------------------
# Streamlit may run each rerun of a session on a different thread. The desktop
# app had a single thread, so allow the per-session SQLite connection to be
# reused across reruns. This does not change any payroll logic.
_sqlite_connect = sqlite3.connect


def _connect(*args, **kwargs):
    kwargs.setdefault("check_same_thread", False)
    return _sqlite_connect(*args, **kwargs)


sqlite3.connect = _connect
# -----------------------------------------------------------------------------

import reports  # noqa: E402
from config import (APP_NAME, APP_VERSION, DEDUCTION_KINDS, DEFAULT_RATES, EMPLOYMENT_TYPES,  # noqa: E402
                    PAYMENT_MODES, RATE_HELP)
from database import EMPLOYEE_FIELDS, INPUT_FIELDS, Database  # noqa: E402
from engine import PayInput, calculate, net_to_gross  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "payroll.db")
OUTPUT = os.path.join(BASE, "output")

NAVY, ORANGE, BG, CARD, MUTED = "#0b3d6e", "#e8791d", "#eef1f5", "#ffffff", "#5a6372"
KRA_PIN_RE = re.compile(r"^[AP]\d{9}[A-Z]$")


# =============================================================================
# Helpers carried over unchanged from app.py
# =============================================================================
def num(value) -> float:
    text = str(value).replace(",", "").strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        raise ValueError(f"'{value}' is not a valid number")


def fmt(v) -> str:
    return f"{float(v or 0):,.2f}"


def period_choices():
    today = date.today()
    y, m = today.year, today.month + 1
    out = []
    for _ in range(26):
        if m == 0:
            y, m = y - 1, 12
        out.append(f"{y}-{m:02d}")
        m -= 1
    return out


# =============================================================================
# Streamlit UI helpers (replace messagebox / filedialog / Treeview)
# =============================================================================
ss = st.session_state

# Full-width setting that works on both older and newer Streamlit versions.
try:
    import inspect as _inspect
    FULL = {"width": "stretch"} if "width" in _inspect.signature(st.button).parameters else {"use_container_width": True}
except (TypeError, ValueError):
    FULL = {"use_container_width": True}


def flash(kind: str, msg: str):
    """Queue a message to show after the next rerun (replaces messagebox)."""
    ss.setdefault("flash", []).append((kind, msg))


def show_flash():
    for kind, msg in ss.pop("flash", []):
        getattr(st, kind)(msg)


def table(cols, rows, row_tags=None, height=None):
    """Render rows like the Tkinter Treeview. cols = [(key, label, width, anchor)]."""
    labels = [c[1] for c in cols]
    df = pd.DataFrame(rows, columns=labels) if rows else pd.DataFrame(columns=labels)
    if row_tags and any(row_tags):
        def style_row(r):
            tag = row_tags[r.name]
            if tag == "total":
                return ["background-color: #dfe7f1; font-weight: bold; color: #0b3d6e"] * len(r)
            if tag == "warn":
                return ["color: #aa3333"] * len(r)
            return [""] * len(r)
        df = df.style.apply(style_row, axis=1)
    kwargs = {**FULL, "hide_index": True}
    if height:
        kwargs["height"] = height
    st.dataframe(df, **kwargs)


def file_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def download_file(path: str, label: str | None = None, key: str | None = None, primary=False):
    st.download_button(label or f"Download {os.path.basename(path)}", file_bytes(path),
                       file_name=os.path.basename(path),
                       mime=mimetypes.guess_type(path)[0] or "application/octet-stream",
                       key=key or f"dl_{path}", type="primary" if primary else "secondary")


def zip_folder(folder: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _dirs, files in os.walk(folder):
            for name in files:
                full = os.path.join(root, name)
                z.write(full, os.path.relpath(full, folder))
    return buf.getvalue()


def temp_path(filename: str) -> str:
    return os.path.join(tempfile.mkdtemp(prefix="payroll_"), filename)


def uploaded_to_path(upload) -> str:
    """Save a Streamlit upload to disk so the original file-reading code is reused as-is."""
    path = temp_path(os.path.basename(upload.name) or "upload.csv")
    with open(path, "wb") as f:
        f.write(upload.getvalue())
    return path


def confirm(key: str, message: str) -> bool:
    """Two-step Yes/No confirmation (replaces messagebox.askyesno)."""
    if ss.get("confirm") != key:
        return False
    st.warning(message)
    c1, c2, _ = st.columns([1, 1, 6])
    if c1.button("Yes", key=f"{key}_yes", type="primary"):
        ss.confirm = None
        return True
    if c2.button("No", key=f"{key}_no"):
        ss.confirm = None
        st.rerun()
    return False


def require_admin() -> bool:
    if ss.role != "Admin":
        st.warning("Only an Admin user can do this.")
        return False
    return True


def valid_period() -> str | None:
    p = str(ss.get("period", "")).strip()
    if re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", p):
        return p
    return None


def emp_label(e) -> str:
    return f"{e['staff_no']} - {e['first_name']} {e['last_name']}"


def nonce(name: str) -> int:
    return ss.get(f"nonce_{name}", 0)


def bump(name: str):
    ss[f"nonce_{name}"] = nonce(name) + 1


# =============================================================================
# Page setup and styling
# =============================================================================
st.set_page_config(page_title=APP_NAME, page_icon="💼", layout="wide")
st.markdown(f"""
<style>
  .pay-header {{ background:{NAVY}; color:#fff; padding:14px 20px; border-bottom:3px solid {ORANGE};
                 border-radius:6px; display:flex; flex-wrap:wrap; align-items:baseline; gap:16px; margin-bottom:12px; }}
  .pay-header .co {{ font-size:1.35rem; font-weight:700; }}
  .pay-header .sub {{ color:#c9d6e6; }}
  .pay-header .user {{ color:#c9d6e6; margin-left:auto; }}
  h2, h3 {{ color:{NAVY}; }}
  div[data-testid="stMetricValue"] {{ color:{NAVY}; font-size:1.35rem; }}
  .stButton button[kind="primary"], .stDownloadButton button[kind="primary"],
  .stFormSubmitButton button[kind="primary"] {{ background:{NAVY}; border-color:{NAVY}; }}
  .muted {{ color:{MUTED}; font-size:0.9rem; }}
</style>""", unsafe_allow_html=True)

if "db" not in ss:
    ss.db = Database(DB_PATH)
db: Database = ss.db


# =============================================================================
# Login (replaces LoginDialog)
# =============================================================================
def login_page():
    first = not db.has_users()
    _, mid, _ = st.columns([1, 1.3, 1])
    with mid:
        st.markdown(f"## {db.company()['name']}")
        st.markdown(f"<p class='muted'>{'Create the first administrator account' if first else 'Payroll sign in'}</p>",
                    unsafe_allow_html=True)
        with st.form("login"):
            user = st.text_input("Username", value="admin")
            pw = st.text_input("Password", type="password")
            pw2 = st.text_input("Confirm password", type="password") if first else ""
            submitted = st.form_submit_button("Continue", type="primary", **FULL)
        if submitted:
            u, p = user.strip(), pw
            if first:
                if len(p) < 8:
                    return st.error("Password must be at least 8 characters.")
                if p != pw2:
                    return st.error("Passwords do not match.")
                db.create_user(u, p, "Admin")
            role = db.verify_user(u, p)
            if not role:
                return st.error("Invalid username or password.")
            ss.username, ss.role = u, role
            st.rerun()


if not ss.get("username"):
    login_page()
    st.stop()


# =============================================================================
# Header and navigation
# =============================================================================
choices = period_choices()
today_p = date.today().strftime("%Y-%m")
with st.sidebar:
    st.markdown(f"### {APP_NAME}")
    st.caption(f"v{APP_VERSION}")
    st.selectbox("Pay period", choices, index=choices.index(today_p) if today_p in choices else 0, key="period")
    page = st.radio("Go to", ["Dashboard", "Employees", "Loans & Deductions", "Monthly Inputs", "Run Payroll",
                              "Reports & Returns", "Tax Calculator", "Settings"], key="page")
    st.divider()
    if st.button("Sign out", **FULL):
        for k in list(ss.keys()):
            if k != "db":
                del ss[k]
        st.rerun()

st.markdown(
    f"<div class='pay-header'><span class='co'>{db.company()['name']}</span>"
    f"<span class='sub'>Payroll | Kenya (KRA / NSSF / SHIF / AHL)</span>"
    f"<span class='user'>Pay period: <b style='color:#fff'>{ss.period}</b> &nbsp;|&nbsp; "
    f"User: {ss.username} ({ss.role})</span></div>", unsafe_allow_html=True)
show_flash()

P = valid_period()


# =============================================================================
# Dashboard
# =============================================================================
def dashboard_page():
    p = P
    st.subheader("Overview")
    cards = {"Active Employees": str(len(db.employees_for_period(p))), "Gross Pay": "-", "Net Pay": "-",
             "PAYE": "-", "Employer Cost": "-"}
    status = db.run_status(p)
    cards["Run Status"] = status or "Not run"
    stat_rows = []
    if status:
        s = reports.summary(db, p)
        for k, key in [("Gross Pay", "gross"), ("Net Pay", "net"), ("PAYE", "paye"), ("Employer Cost", "employer_cost")]:
            cards[k] = fmt(s[key])
        for row in [("PAYE", "KRA iTax", s["paye"]), ("Withholding Tax", "KRA iTax", s["wht"]),
                    ("Housing Levy (EE+ER)", "KRA iTax", s["ahl_ee"] + s["ahl_er"]),
                    ("NSSF (EE+ER)", "NSSF", s["nssf_ee"] + s["nssf_er"]),
                    ("SHIF", "SHA", s["shif"]), ("NITA", "NITA", s["nita"])]:
            stat_rows.append((row[0], row[1], fmt(row[2]), s["due"]))
    for col, (k, v) in zip(st.columns(6), cards.items()):
        with col.container(border=True):
            st.metric(k, v)

    left, right = st.columns(2)
    with left:
        st.markdown("**Statutory remittances for selected period**")
        table([("item", "Item", 220, "w"), ("via", "Remit via", 140, "w"),
               ("amt", "Amount (KES)", 120, "e"), ("due", "Due", 110, "w")], stat_rows)
    with right:
        st.markdown("**Recent activity (audit trail)**")
        table([("ts", "Time", 140, "w"), ("user", "User", 80, "w"), ("act", "Action", 130, "w"),
               ("det", "Detail", 220, "w")],
              [(a["ts"], a["username"], a["action"], a["detail"]) for a in db.audit(40)], height=300)
    st.caption("Workflow: 1) Add employees  2) Set loans/recurring deductions  3) Enter monthly inputs "
               "(overtime, bonus, absence)  4) Run payroll and review warnings  5) Generate payslips and "
               "returns  6) Close the period.  PAYE, NSSF, SHIF, Housing Levy and NITA are due by the 9th "
               "of the following month.")


# =============================================================================
# Employees
# =============================================================================
FORM_SECTIONS = [
    ("Personal", [("staff_no", "Staff No. *"), ("first_name", "First Name *"), ("last_name", "Last Name *"),
                  ("id_no", "National ID / Passport"), ("gender", "Gender", ["", "Male", "Female"]),
                  ("dob", "Date of Birth (YYYY-MM-DD)"), ("phone", "Phone (M-Pesa)"), ("email", "Email")]),
    ("Employment", [("department", "Department"), ("designation", "Designation"),
                    ("employment_type", "Employment Type", EMPLOYMENT_TYPES),
                    ("hire_date", "Hire Date (YYYY-MM-DD)"), ("exit_date", "Exit Date (YYYY-MM-DD)"),
                    ("status", "Status", ["Active", "Exited"]), ("leave_days_per_year", "Annual Leave Days")]),
    ("Statutory", [("kra_pin", "KRA PIN"), ("nssf_no", "NSSF No."), ("shif_no", "SHIF / SHA No."),
                   ("nssf_contracted_out", "NSSF Tier II contracted out", "check"),
                   ("disabled", "Registered disability (KRA exemption)", "check"),
                   ("disability_cert", "Exemption Certificate No.")]),
    ("Pay & Benefits", [("basic_salary", "Basic Salary"), ("house_allowance", "House Allowance"),
                        ("transport_allowance", "Transport Allowance"), ("other_allowance", "Other Allowance"),
                        ("non_cash_benefits", "Non-cash Benefits (monthly)"), ("car_benefit", "Car Benefit"),
                        ("housing_benefit", "Employer Housing Benefit")]),
    ("Tax Reliefs", [("voluntary_pension", "Pension contribution (deducted)"),
                     ("insurance_premium", "Insurance premium (for 15% relief)"),
                     ("mortgage_interest", "Mortgage interest (monthly)"),
                     ("prmf", "Post-retirement medical fund")]),
    ("Payment", [("payment_mode", "Payment Mode", PAYMENT_MODES), ("bank_name", "Bank"),
                 ("bank_branch", "Branch"), ("account_no", "Account No.")]),
]


def save_employee_data(data, emp):
    try:
        db.save_employee(data, emp["id"] if emp else None)
    except Exception as ex:
        st.error(f"Could not save: {ex}")
        return
    ss.emp_form = None
    ss.pop("emp_pending", None)
    flash("success", "Employee saved.")
    st.rerun()


def employee_form(emp):
    eid = emp["id"] if emp else "new"
    st.subheader("Edit Employee" if emp else "New Employee")

    pending = ss.get("emp_pending")
    if pending and pending[0] == eid:
        data = pending[1]
        st.warning(f"KRA PIN '{data['kra_pin']}' does not look valid (e.g. A012345678Z). Save anyway?")
        c1, c2, _ = st.columns([1, 1, 6])
        if c1.button("Yes, save", type="primary", key="pin_yes"):
            save_employee_data(data, emp)
        if c2.button("No", key="pin_no"):
            ss.pop("emp_pending", None)
            st.rerun()

    with st.form(f"empform_{eid}"):
        values = {}
        for tab, (section, fields) in zip(st.tabs([s for s, _ in FORM_SECTIONS]), FORM_SECTIONS):
            with tab:
                c = st.columns(2)
                for r, spec in enumerate(fields):
                    key, label = spec[0], spec[1]
                    kind = spec[2] if len(spec) > 2 else None
                    current = emp[key] if emp else None
                    wkey = f"emp_{eid}_{key}"
                    col = c[r % 2]
                    if kind == "check":
                        values[key] = ("check", col.checkbox(label, value=bool(int(current or 0)), key=wkey))
                        continue
                    default = {"status": "Active", "employment_type": "Primary", "payment_mode": "Bank",
                               "leave_days_per_year": 21}.get(key, "")
                    init = "" if current is None and not default else (current if current is not None else default)
                    init = str(init)
                    if kind:
                        opts = list(kind)
                        if init not in opts:
                            opts = [init] + opts
                        values[key] = ("text", col.selectbox(label, opts, index=opts.index(init), key=wkey))
                    else:
                        values[key] = ("text", col.text_input(label, value=init, key=wkey))
        b1, b2, _ = st.columns([1, 1, 6])
        submitted = b1.form_submit_button("Save", type="primary")
        cancelled = b2.form_submit_button("Cancel")

    if cancelled:
        ss.emp_form = None
        ss.pop("emp_pending", None)
        st.rerun()
    if not submitted:
        return

    data = {k: (int(v) if t == "check" else v) for k, (t, v) in values.items()}
    try:
        for k in ("dob", "hire_date", "exit_date"):
            if data[k].strip():
                date.fromisoformat(data[k].strip())
        for k in ("basic_salary", "house_allowance", "transport_allowance", "other_allowance",
                  "non_cash_benefits", "car_benefit", "housing_benefit", "voluntary_pension",
                  "insurance_premium", "mortgage_interest", "prmf", "leave_days_per_year"):
            num(data[k])
        if not data["staff_no"].strip() or not data["first_name"].strip():
            raise ValueError("Staff No. and First Name are required.")
    except ValueError as ex:
        return st.error(str(ex))
    pin = data["kra_pin"].strip().upper()
    data["kra_pin"] = pin
    if data["exit_date"].strip() and data["status"] == "Active":
        data["status"] = "Exited"
    if pin and not KRA_PIN_RE.match(pin):
        ss.emp_pending = (eid, data)
        st.rerun()
    save_employee_data(data, emp)


EMP_COLS = [("staff", "Staff No", 80, "w"), ("name", "Name", 200, "w"), ("dept", "Department", 130, "w"),
            ("desig", "Designation", 150, "w"), ("type", "Type", 120, "w"), ("pin", "KRA PIN", 110, "w"),
            ("basic", "Basic Salary", 110, "e"), ("gross", "Fixed Gross", 110, "e"), ("status", "Status", 70, "w")]


def employees_page():
    form_target = ss.get("emp_form")
    if form_target is not None:
        employee_form(None if form_target == "new" else db.employee(int(form_target)))
        return

    c1, c2, c3 = st.columns([3, 1, 2])
    q = c1.text_input("Search", placeholder="Staff no, name, department, KRA PIN or ID").lower()
    show_exited = c2.checkbox("Show exited", value=False)
    if c3.button("+ Add Employee", type="primary", **FULL):
        ss.emp_form = "new"
        st.rerun()

    rows, matched = [], []
    for e in db.employees(include_exited=bool(show_exited)):
        name = f"{e['first_name']} {e['last_name']}"
        hay = f"{e['staff_no']} {name} {e['department']} {e['kra_pin']} {e['id_no']}".lower()
        if q and q not in hay:
            continue
        fixed = sum(e[k] or 0 for k in ("basic_salary", "house_allowance", "transport_allowance", "other_allowance"))
        rows.append((e["staff_no"], name, e["department"], e["designation"], e["employment_type"], e["kra_pin"],
                     fmt(e["basic_salary"]), fmt(fixed), e["status"]))
        matched.append(e)
    table(EMP_COLS, rows, height=460)
    st.caption(f"{len(rows)} employee(s)")

    if matched:
        ec1, ec2 = st.columns([4, 1])
        by_id = {e["id"]: e for e in matched}
        sel_id = ec1.selectbox("Select an employee to edit", list(by_id), format_func=lambda i: emp_label(by_id[i]),
                               key="emp_edit_sel")
        ec2.write("")
        if ec2.button("Edit", **FULL):
            ss.emp_form = sel_id
            st.rerun()

    st.divider()
    x1, x2 = st.columns(2)
    with x1:
        st.markdown("**Export CSV**")
        path = temp_path("employees.csv")
        exp_rows = [[e[f] for f in EMPLOYEE_FIELDS] for e in db.employees()]
        reports.write_csv(path, EMPLOYEE_FIELDS, exp_rows)
        download_file(path, f"Download employees.csv ({len(exp_rows)} employees)", key="emp_export")
        st.caption("Use this file as the import template.")
    with x2:
        st.markdown("**Import CSV**")
        up = st.file_uploader("Employee CSV", type=["csv"], key=f"emp_import_{nonce('emp_import')}",
                              label_visibility="collapsed")
        if up is not None and st.button("Import employees", type="primary"):
            import_employees(uploaded_to_path(up))


def import_employees(path):
    existing = {e["staff_no"]: e["id"] for e in db.employees()}
    added = updated = 0
    errors = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            row = {k.strip(): (v or "").strip() for k, v in row.items() if k}
            if not row.get("staff_no"):
                continue
            row.setdefault("status", "Active")
            row["status"] = row["status"] or "Active"
            row["employment_type"] = row.get("employment_type") or "Primary"
            try:
                emp_id = existing.get(row["staff_no"])
                db.save_employee(row, emp_id)
                updated += bool(emp_id)
                added += not emp_id
            except Exception as ex:
                errors.append(f"Row {i}: {ex}")
    msg = f"Added {added}, updated {updated}."
    if errors:
        msg += "\n\nErrors:\n" + "\n".join(errors[:15])
    flash("warning" if errors else "success", msg)
    bump("emp_import")
    st.rerun()


# =============================================================================
# Loans & Deductions
# =============================================================================
def deductions_page():
    emps = list(db.employees(include_exited=False))
    if not emps:
        st.info("Add employees first.")
        return
    left, right = st.columns([1, 3])
    with left:
        st.markdown("**Employees**")
        by_id = {x["id"]: x for x in emps}
        emp_id = st.radio("Employee", list(by_id), format_func=lambda i: emp_label(by_id[i]), key="ded_emp",
                          label_visibility="collapsed")
    e = by_id[emp_id]
    with right:
        st.subheader(f"{e['staff_no']} - {e['first_name']} {e['last_name']}")
        deds = list(db.deductions(emp_id))
        table([("id", "#", 40, "w"), ("kind", "Type", 120, "w"), ("desc", "Description", 200, "w"),
               ("inst", "Monthly", 100, "e"), ("bal", "Balance", 110, "e"), ("start", "Start", 80, "w"),
               ("st", "Status", 80, "w")],
              [(d["id"], d["kind"], d["description"], fmt(d["installment"]),
                "Recurring" if d["balance"] is None else fmt(d["balance"]),
                d["start_period"] or "", "Active" if d["active"] else "Stopped") for d in deds])
        if deds:
            t1, t2 = st.columns([3, 1])
            d_by_id = {d["id"]: d for d in deds}
            dsel_id = t1.selectbox("Deduction", list(d_by_id), key=f"ded_toggle_sel_{emp_id}",
                                   format_func=lambda i: f"#{i} {d_by_id[i]['kind']} - {d_by_id[i]['description']} "
                                                         f"({'Active' if d_by_id[i]['active'] else 'Stopped'})")
            t2.write("")
            if t2.button("Activate / Stop selected", **FULL):
                d = db.q("SELECT active FROM deductions WHERE id=?", (int(dsel_id),))[0]
                db.set_deduction_active(int(dsel_id), not d["active"])
                st.rerun()

        st.markdown("**Add loan / recurring deduction**")
        n = nonce("ded_form")
        with st.form(f"ded_form_{emp_id}_{n}"):
            f1, f2, f3, f4, f5 = st.columns([1.2, 1.6, 1, 1.4, 1])
            kind = f1.selectbox("Type", DEDUCTION_KINDS)
            desc = f2.text_input("Description")
            inst_s = f3.text_input("Monthly amount")
            bal_s = f4.text_input("Loan balance (blank = recurring)")
            start_s = f5.text_input("Start period (YYYY-MM)", value=P or "")
            add = st.form_submit_button("Add", type="primary")
        if add:
            try:
                inst = num(inst_s)
                bal = num(bal_s) if bal_s.strip() else None
                if inst <= 0:
                    raise ValueError("Monthly amount must be greater than zero.")
                start = start_s.strip()
                if start and not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", start):
                    raise ValueError("Start period must be YYYY-MM.")
            except ValueError as ex:
                st.error(str(ex))
            else:
                db.add_deduction(emp_id, kind, desc.strip(), inst, bal, start)
                bump("ded_form")
                st.rerun()
        st.caption("Loans with a balance reduce automatically when a payroll period is closed and stop at zero. "
                   "Leave the balance blank for recurring deductions such as SACCO, welfare or union dues. "
                   "Note: employer loans below the KRA market rate attract Fringe Benefit Tax payable by the employer.")


# =============================================================================
# Monthly Inputs
# =============================================================================
INPUT_LABELS = {"ot_normal_hours": "OT Hrs x1.5", "ot_holiday_hours": "OT Hrs x2.0", "bonus": "Bonus",
                "arrears": "Arrears", "leave_pay": "Leave Pay", "other_earnings": "Other Earnings",
                "absent_days": "Absent Days", "other_deductions": "Other Deduction",
                "leave_taken": "Leave Days Taken"}


def inputs_locked(p) -> bool:
    if db.run_status(p) == "Closed":
        st.warning("This period is closed. Reopen it in Run Payroll to change inputs.")
        return True
    return False


def inputs_page():
    p = P
    st.subheader(f"Variable inputs for {reports.period_label(p)}  [{db.run_status(p) or 'Not run'}]")
    emps = list(db.employees_for_period(p))
    cols = [("staff", "Staff", 70, "w"), ("name", "Name", 180, "w")] + \
           [(f, INPUT_LABELS[f], 95, "e") for f in INPUT_FIELDS] + [("notes", "Notes", 160, "w")]
    rows = []
    for e in emps:
        i = db.inputs(e["id"], p)
        rows.append((e["staff_no"], f"{e['first_name']} {e['last_name']}",
                     *[fmt(i[f]) if i[f] else "" for f in INPUT_FIELDS], i.get("notes") or ""))
    table(cols, rows, height=380)
    st.caption("Select an employee below to enter this month's variable pay. Overtime is computed from basic / "
               "standard monthly hours. Absence deducts basic / days-per-month for each day.")

    if emps:
        by_id = {x["id"]: x for x in emps}
        e = by_id[st.selectbox("Employee", list(by_id), format_func=lambda i: emp_label(by_id[i]), key=f"inp_sel_{p}")]
        with st.expander(f"Edit inputs: {e['first_name']} {e['last_name']} - {p}", expanded=True):
            if not inputs_locked(p):
                emp_id = e["id"]
                cur = db.inputs(emp_id, p)
                with st.form(f"inp_form_{emp_id}_{p}"):
                    vals = {}
                    cs = st.columns(3)
                    for r, f in enumerate(INPUT_FIELDS + ["notes"]):
                        init = (cur.get(f) or "") if f == "notes" else (str(cur[f]) if cur[f] else "")
                        vals[f] = cs[r % 3].text_input(INPUT_LABELS.get(f, "Notes"), value=str(init),
                                                       key=f"inp_{emp_id}_{p}_{f}")
                    ent, bal = db.leave_balance(emp_id, int(p[:4]))
                    st.caption(f"Leave: {ent:g} days/yr, balance {bal:g}")
                    saved = st.form_submit_button("Save", type="primary")
                if saved:
                    try:
                        data = {f: num(vals[f]) for f in INPUT_FIELDS}
                    except ValueError as ex:
                        st.error(str(ex))
                    else:
                        data["notes"] = vals["notes"]
                        db.save_inputs(emp_id, p, data)
                        db.log("inputs.save", f"{e['staff_no']} {p}")
                        flash("success", f"Inputs saved for {e['staff_no']}.")
                        st.rerun()

    st.divider()
    x1, x2 = st.columns(2)
    with x1:
        st.markdown("**Export template**")
        path = temp_path(f"inputs_{p}.csv")
        exp_rows = []
        for e in emps:
            i = db.inputs(e["id"], p)
            exp_rows.append([e["staff_no"], f"{e['first_name']} {e['last_name']}"] + [i[f] for f in INPUT_FIELDS]
                            + [i.get("notes") or ""])
        reports.write_csv(path, ["staff_no", "name"] + INPUT_FIELDS + ["notes"], exp_rows)
        download_file(path, f"Download inputs_{p}.csv", key=f"inp_export_{p}")
        st.caption("Fill it in and use Import CSV.")
    with x2:
        st.markdown("**Import CSV**")
        up = st.file_uploader("Inputs CSV", type=["csv"], key=f"inp_import_{p}_{nonce('inp_import')}",
                              label_visibility="collapsed")
        if up is not None and st.button("Import inputs", type="primary") and not inputs_locked(p):
            import_inputs(uploaded_to_path(up), p)


def import_inputs(path, p):
    ids = {e["staff_no"]: e["id"] for e in db.employees()}
    n, errors = 0, []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            sid = (row.get("staff_no") or "").strip()
            if sid not in ids:
                errors.append(f"Row {i}: unknown staff_no '{sid}'")
                continue
            try:
                data = {k: num(row.get(k, 0)) for k in INPUT_FIELDS}
            except ValueError as ex:
                errors.append(f"Row {i}: {ex}")
                continue
            data["notes"] = row.get("notes", "")
            db.save_inputs(ids[sid], p, data)
            n += 1
    db.log("inputs.import", f"{p}: {n} rows")
    flash("warning" if errors else "success",
          f"Imported {n} rows." + ("\n\n" + "\n".join(errors[:15]) if errors else ""))
    bump("inp_import")
    st.rerun()


# =============================================================================
# Run Payroll
# =============================================================================
PAY_COLS = [("staff", "Staff", 65, "w"), ("name", "Name", 170, "w"), ("gross", "Gross Pay", 105, "e"),
            ("nssf", "NSSF", 85, "e"), ("shif", "SHIF", 85, "e"), ("ahl", "Housing Levy", 90, "e"),
            ("taxable", "Taxable Pay", 105, "e"), ("paye", "PAYE", 95, "e"), ("wht", "WHT", 75, "e"),
            ("other", "Other Ded.", 90, "e"), ("net", "Net Pay", 105, "e"), ("cost", "Employer Cost", 105, "e")]


def show_payroll(lines, warnings):
    keys = ["gross_pay", "nssf_employee", "shif", "ahl_employee", "taxable_pay", "paye", "wht", "other",
            "net_pay", "employer_cost"]
    tot = dict.fromkeys(keys, 0.0)
    rows, tags = [], []
    for l in lines:
        e = l["employee"]
        l = dict(l, other=sum(l["other_deductions"].values()) + l["voluntary_pension"])
        for k in keys:
            tot[k] += l[k]
        rows.append((e["staff_no"], f"{e['first_name']} {e['last_name']}", *[fmt(l[k]) for k in keys]))
        tags.append("warn" if l["warnings"] else "")
    if lines:
        rows.append(("", f"TOTAL ({len(lines)})", *[fmt(tot[k]) for k in keys]))
        tags.append("total")
    table(PAY_COLS, rows, row_tags=tags, height=420)
    if warnings is None:
        warnings = [f"{l['employee']['staff_no']}: {w}" for l in lines for w in l["warnings"]]
    st.markdown("**Validation warnings**")
    if warnings:
        st.error("\n".join(f"- {w}" for w in warnings))
    else:
        st.success("No warnings.")


def payroll_page():
    p = P
    status = db.run_status(p)
    last = ss.get("last_run")
    if last and last[0] == p and status == "Draft":
        status_label, lines, warnings = "Draft", last[1], last[2]
    else:
        status_label = status or "Not run"
        lines, warnings = (db.run_lines(p) if status else []), None

    h1, h2, h3, h4 = st.columns([3, 1.6, 1, 1])
    h1.subheader(f"Payroll {reports.period_label(p)}  [{status_label}]")
    if h2.button("Run / Recalculate Payroll", type="primary", **FULL):
        try:
            lines, warnings = db.run_payroll(p)
        except ValueError as ex:
            flash("warning", str(ex))
        else:
            if not lines:
                flash("info", "No active employees for this period.")
            ss.last_run = (p, lines, warnings)
        st.rerun()
    if h3.button("Close Period", **FULL) and require_admin():
        ss.confirm = f"close_{p}"
    if h4.button("Reopen Period", **FULL) and require_admin():
        ss.confirm = f"reopen_{p}"

    if confirm(f"close_{p}", f"Close payroll for {reports.period_label(p)}?\n\n"
                             "Inputs will be locked and loan balances reduced."):
        try:
            db.close_period(p)
        except ValueError as ex:
            flash("warning", str(ex))
        ss.pop("last_run", None)
        st.rerun()
    if confirm(f"reopen_{p}", f"Reopen {reports.period_label(p)}? Loan balances will be restored."):
        try:
            db.reopen_period(p)
        except ValueError as ex:
            flash("warning", str(ex))
        ss.pop("last_run", None)
        st.rerun()

    show_payroll(lines, warnings)

    if lines:
        st.markdown("**Payslip**")
        s1, s2 = st.columns([3, 1])
        by_id = {l["employee"]["id"]: l["employee"] for l in lines}
        emp_id = s1.selectbox("Employee", list(by_id), format_func=lambda i: emp_label(by_id[i]),
                              key=f"slip_sel_{p}", label_visibility="collapsed")
        if s2.button("Generate payslip", **FULL):
            ss.slip_path = reports.payslips(db, p, OUTPUT, int(emp_id))
        if ss.get("slip_path") and os.path.exists(ss.slip_path):
            download_file(ss.slip_path, key="slip_dl", primary=True)


# =============================================================================
# Reports & Returns
# =============================================================================
def report_log(path):
    ss.setdefault("report_log", []).append(f"{datetime.now():%H:%M:%S}  Created {path}")
    ss.setdefault("report_files", [])
    if path not in ss.report_files:
        ss.report_files.append(path)


def reports_page():
    p = P
    st.subheader(f"Reports for {reports.period_label(p)}  [{db.run_status(p) or 'Payroll not run'}]")

    def check():
        if not db.run_status(p):
            st.warning("Run payroll for this period first.")
            return None
        return p

    def gen(fn):
        if not check():
            return None
        path = fn(db, p, OUTPUT)
        report_log(path)
        db.log("report", os.path.basename(path) + " " + p)
        return path

    with st.container(border=True):
        st.markdown("**Monthly reports & statutory returns**")
        cols = st.columns(3)
        for i, (name, fn) in enumerate(reports.ALL_PERIOD_REPORTS):
            if cols[i % 3].button(name, key=f"rep_{i}", **FULL):
                if gen(fn):
                    st.rerun()
        b1, b2, _ = st.columns([1, 1, 2])
        if b1.button("Generate ALL for period", type="primary", **FULL):
            if check():
                for _, fn in reports.ALL_PERIOD_REPORTS:
                    gen(fn)
                ss.zip_ready = p
                st.rerun()
        folder = reports.out_dir(OUTPUT, p)
        if os.path.isdir(folder) and any(os.scandir(folder)):
            b2.download_button("Download output folder (ZIP)", zip_folder(folder), file_name=f"payroll_{p}.zip",
                               mime="application/zip", **FULL,
                               type="primary" if ss.get("zip_ready") == p else "secondary")

    with st.container(border=True):
        st.markdown("**P9A Tax Deduction Card (annual)**")
        emps = {"All employees": None}
        for e in db.employees():
            emps[emp_label(e)] = e["id"]
        c1, c2, c3 = st.columns([1, 3, 1])
        year_s = c1.text_input("Year", value=str(date.today().year))
        emp_name = c2.selectbox("Employee", list(emps))
        c3.write("")
        if c3.button("Generate P9A", type="primary", **FULL):
            try:
                year = int(year_s)
            except ValueError:
                st.error("Enter a valid year.")
            else:
                emp_id = emps.get(emp_name)
                if not db.lines_for_year(year, emp_id):
                    st.info("No payroll data for that year/employee.")
                else:
                    path = reports.p9a(db, year, os.path.join(OUTPUT, "P9A"), emp_id)
                    report_log(path)
                    st.rerun()

    st.caption("Payslips and P9A are HTML files - open them in your browser and use Print > Save as PDF to file "
               "or e-mail them. CSV files open in Excel. Copy the KRA P10 rows into the official iTax P10 Excel "
               "template (Employee Details sheet) and validate it before uploading; NSSF, SHIF and Housing Levy "
               "files follow the portal column order. Files are also saved under the 'output' folder by period.")

    files = [f for f in ss.get("report_files", []) if os.path.exists(f)]
    if files:
        st.markdown("**Generated files**")
        for i, f in enumerate(reversed(files)):
            download_file(f, f"Download {os.path.basename(f)}", key=f"repdl_{i}_{f}")
    if ss.get("report_log"):
        st.code("\n".join(ss.report_log), language=None)


# =============================================================================
# Tax Calculator
# =============================================================================
CALC_FIELDS = [("basic", "Basic salary / Target net", "100000"), ("allow", "Cash allowances", "0"),
               ("benefits", "Non-cash benefits", "0"), ("pension", "Voluntary pension", "0"),
               ("insurance", "Insurance premium", "0"), ("mortgage", "Mortgage interest", "0")]


def calculator_page():
    left, right = st.columns([1, 2])
    with left:
        with st.form("calc"):
            st.markdown("**PAYE & net pay calculator**")
            raw = {k: st.text_input(lbl, value=dflt) for k, lbl, dflt in CALC_FIELDS}
            etype = st.selectbox("Employment type", EMPLOYMENT_TYPES,
                                 index=list(EMPLOYMENT_TYPES).index("Primary") if "Primary" in EMPLOYMENT_TYPES else 0)
            disabled = st.checkbox("Disability exemption")
            mode = st.radio("Mode", ["g2n", "n2g"], horizontal=True,
                            format_func=lambda m: "Gross to Net" if m == "g2n" else "Net to Gross (gross-up)")
            go = st.form_submit_button("Calculate", type="primary", **FULL)
    with right:
        if not go:
            st.info("Enter the figures and select Calculate.")
            return
        try:
            v = {k: num(val) for k, val in raw.items()}
        except ValueError as ex:
            return st.error(str(ex))
        rates = db.rates()
        inp = PayInput(period=valid_period() or date.today().strftime("%Y-%m"), basic=v["basic"],
                       allowances={"Allowances": v["allow"]}, non_cash_benefits=v["benefits"],
                       voluntary_pension=v["pension"], insurance_premium=v["insurance"],
                       mortgage_interest=v["mortgage"], disabled=bool(disabled),
                       employment_type=etype)
        if mode == "n2g":
            basic, res = net_to_gross(v["basic"], inp, rates)
            head = f"Required BASIC salary for net KES {fmt(v['basic'])}: KES {fmt(basic)}\n\n"
        else:
            res = calculate(inp, rates)
            head = ""
        rows = [("Gross pay", "gross_pay"), ("Taxable non-cash benefits", "taxable_benefits"),
                ("NSSF Tier I", "nssf_tier1"), ("NSSF Tier II", "nssf_tier2"), ("SHIF (2.75%)", "shif"),
                ("Housing Levy (1.5%)", "ahl_employee"), ("Allowable pension", "pension_allowed"),
                ("Mortgage interest allowed", "mortgage_allowed"), ("Disability exemption", "disability_exempt"),
                ("Taxable pay", "taxable_pay"), ("Tax charged", "tax_charged"),
                ("Less personal relief", "personal_relief"), ("Less insurance relief", "insurance_relief"),
                ("PAYE", "paye"), ("Withholding tax", "wht"), ("Voluntary pension", "voluntary_pension"),
                ("Total deductions", "total_deductions"), ("NET PAY", "net_pay"),
                ("", None), ("Employer NSSF", "nssf_employer"), ("Employer Housing Levy", "ahl_employer"),
                ("NITA", "nita"), ("Total employer cost", "employer_cost")]
        text = head + "\n".join(f"{lbl:<30}{fmt(res[k]):>16}" if k else "" for lbl, k in rows)
        if res["warnings"]:
            text += "\n\nWarnings:\n- " + "\n- ".join(res["warnings"])
        text += f"\n\nRates: {rates.get('rates_version', '')}"
        st.code(text, language=None)


# =============================================================================
# Settings
# =============================================================================
COMPANY = [("name", "Company name"), ("kra_pin", "Employer KRA PIN"), ("nssf_no", "NSSF employer no."),
           ("shif_no", "SHA/SHIF employer no."), ("nita_no", "NITA no."), ("address", "Address"),
           ("phone", "Phone"), ("email", "Email"), ("bank_name", "Paying bank"), ("bank_account", "Bank account")]


def settings_page():
    t_company, t_rates, t_users = st.tabs(["Company", "Statutory Rates", "Users & Security"])

    with t_company:
        c = db.company()
        with st.form(f"company_{nonce('company')}"):
            cvals = {k: st.text_input(lbl, value=str(c.get(k, "") or "")) for k, lbl in COMPANY}
            save = st.form_submit_button("Save company details", type="primary")
        if save and require_admin():
            data = {k: v.strip() for k, v in cvals.items()}
            db.set_setting("company", data)
            db.log("company.update")
            flash("success", "Company details saved.")
            bump("company")
            st.rerun()

    with t_rates:
        st.caption("Edit rates when KRA / NSSF / SHA publish changes (Finance Act, Legal Notices). Values are JSON; "
                   "rates are decimals (0.30 = 30%). " + " ".join(RATE_HELP.values()))
        rates_text = st.text_area("Rates (JSON)", value=json.dumps(db.rates(), indent=2), height=420,
                                  key=f"rates_{nonce('rates')}", label_visibility="collapsed")
        r1, r2, _ = st.columns([1, 1, 4])
        if r1.button("Save rates", type="primary") and require_admin():
            try:
                rates = json.loads(rates_text)
                missing = [k for k in DEFAULT_RATES if k not in rates]
                if missing:
                    raise ValueError("Missing keys: " + ", ".join(missing))
                calculate(PayInput(period="2026-01", basic=50000), rates)
            except Exception as ex:
                st.error(f"Rates not saved: {ex}")
            else:
                db.set_setting("rates", rates)
                db.log("rates.update", rates.get("rates_version", ""))
                flash("success", "Statutory rates saved. Re-run any draft payroll to apply them.")
                bump("rates")
                st.rerun()
        if r2.button("Restore defaults") and require_admin():
            ss.confirm = "reset_rates"
        if confirm("reset_rates", "Restore the built-in default rates?"):
            db.set_setting("rates", DEFAULT_RATES)
            db.log("rates.reset")
            bump("rates")
            st.rerun()

    with t_users:
        table([("u", "Username", 200, "w"), ("r", "Role", 120, "w")],
              [(u["username"], u["role"]) for u in db.users()])
        n = nonce("users")
        u1, u2, u3 = st.columns(3)
        nu = u1.text_input("Username", key=f"nu_{n}")
        np_ = u2.text_input("Password", type="password", key=f"np_{n}")
        nr = u3.selectbox("Role", ["Admin", "Payroll Officer"], index=1, key=f"nr_{n}")
        b1, b2, _ = st.columns([1, 1.4, 3])
        if b1.button("Add user", **FULL) and require_admin():
            u, p = nu.strip(), np_
            if not u or len(p) < 8:
                st.error("Enter a username and a password of at least 8 characters.")
            else:
                try:
                    db.create_user(u, p, nr)
                except Exception as ex:
                    st.error(str(ex))
                else:
                    bump("users")
                    st.rerun()
        if b2.button("Change my password", **FULL):
            if len(np_) < 8:
                st.error("Type the new password (8+ characters) in the Password box.")
            else:
                db.change_password(ss.username, np_)
                bump("users")
                flash("success", "Password changed.")
                st.rerun()

        st.divider()
        st.markdown("**Backup database**")
        if st.button("Prepare backup"):
            path = temp_path(f"payroll_backup_{datetime.now():%Y%m%d_%H%M}.db")
            db.backup(path)
            ss.backup_path = path
        if ss.get("backup_path") and os.path.exists(ss.backup_path):
            download_file(ss.backup_path, key="backup_dl", primary=True)
        st.caption(f"Database: {DB_PATH}")

        st.markdown("### Audit trail")
        table([("ts", "Time", 150, "w"), ("u", "User", 100, "w"), ("a", "Action", 150, "w"),
               ("d", "Detail", 500, "w")],
              [(a["ts"], a["username"], a["action"], a["detail"]) for a in db.audit(300)], height=360)


# =============================================================================
PAGES = {
    "Dashboard": dashboard_page, "Employees": employees_page, "Loans & Deductions": deductions_page,
    "Monthly Inputs": inputs_page, "Run Payroll": payroll_page, "Reports & Returns": reports_page,
    "Tax Calculator": calculator_page, "Settings": settings_page,
}

if P:
    PAGES[page]()
else:
    st.error("Select a valid pay period (YYYY-MM).")
