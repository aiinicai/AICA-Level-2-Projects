"""Lordship Africa Payroll - desktop application (Tkinter + SQLite, no extra installs).

Run:  python app.py
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import tkinter as tk
from datetime import date, datetime
from tkinter import filedialog, messagebox, ttk

import reports
from config import (APP_NAME, APP_VERSION, DEDUCTION_KINDS, DEFAULT_RATES, EMPLOYMENT_TYPES,
                    PAYMENT_MODES, RATE_HELP)
from database import EMPLOYEE_FIELDS, INPUT_FIELDS, Database
from engine import PayInput, calculate, net_to_gross

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "payroll.db")
OUTPUT = os.path.join(BASE, "output")

NAVY, ORANGE, BG, CARD, MUTED = "#0b3d6e", "#e8791d", "#eef1f5", "#ffffff", "#5a6372"
KRA_PIN_RE = re.compile(r"^[AP]\d{9}[A-Z]$")


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


def open_path(path):
    if sys.platform.startswith("win"):
        os.startfile(path)
    else:
        import webbrowser
        webbrowser.open("file://" + os.path.abspath(path))


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


def make_tree(parent, cols, height=16):
    frame = ttk.Frame(parent)
    tree = ttk.Treeview(frame, columns=[c[0] for c in cols], show="headings", height=height)
    for key, label, width, anchor in cols:
        tree.heading(key, text=label)
        tree.column(key, width=width, anchor=anchor, stretch=True)
    vs = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    hs = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vs.grid(row=0, column=1, sticky="ns")
    hs.grid(row=1, column=0, sticky="ew")
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)
    tree.tag_configure("total", background="#dfe7f1", font=("Segoe UI", 9, "bold"))
    tree.tag_configure("warn", foreground="#a33")
    return frame, tree


# =============================================================================
class LoginDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app, self.result = app, None
        self.first = not app.db.has_users()
        self.title(APP_NAME + (" - Create Administrator" if self.first else " - Sign in"))
        self.resizable(False, False)
        self.configure(bg=CARD, padx=24, pady=20)
        tk.Label(self, text=app.db.company()["name"], font=("Segoe UI", 16, "bold"), fg=NAVY,
                 bg=CARD).grid(row=0, column=0, columnspan=2, pady=(0, 4))
        tk.Label(self, text="Create the first administrator account" if self.first else "Payroll sign in",
                 fg=MUTED, bg=CARD).grid(row=1, column=0, columnspan=2, pady=(0, 12))
        self.user, self.pw, self.pw2 = tk.StringVar(value="admin"), tk.StringVar(), tk.StringVar()
        rows = [("Username", self.user, ""), ("Password", self.pw, "*")]
        if self.first:
            rows.append(("Confirm password", self.pw2, "*"))
        for i, (lbl, var, show) in enumerate(rows, start=2):
            tk.Label(self, text=lbl, bg=CARD).grid(row=i, column=0, sticky="w", pady=4)
            ent = ttk.Entry(self, textvariable=var, show=show, width=28)
            ent.grid(row=i, column=1, pady=4)
            if i == 3:
                ent.focus_set()
        ttk.Button(self, text="Continue", style="Accent.TButton", command=self.submit).grid(
            row=10, column=0, columnspan=2, pady=(14, 0), sticky="ew")
        self.bind("<Return>", lambda _e: self.submit())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.grab_set()

    def submit(self):
        u, p = self.user.get().strip(), self.pw.get()
        if self.first:
            if len(p) < 8:
                return messagebox.showerror(APP_NAME, "Password must be at least 8 characters.", parent=self)
            if p != self.pw2.get():
                return messagebox.showerror(APP_NAME, "Passwords do not match.", parent=self)
            self.app.db.create_user(u, p, "Admin")
        role = self.app.db.verify_user(u, p)
        if not role:
            return messagebox.showerror(APP_NAME, "Invalid username or password.", parent=self)
        self.result = (u, role)
        self.destroy()


# =============================================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.ok = False
        self.db = Database(DB_PATH)
        self._style()
        self.withdraw()
        dlg = LoginDialog(self)
        self.wait_window(dlg)
        if not dlg.result:
            self.destroy()
            return
        self.username, self.role = dlg.result
        self.ok = True
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1280x780")
        self.minsize(1000, 640)
        self.configure(bg=BG)
        self.period = tk.StringVar(value=date.today().strftime("%Y-%m"))
        self._header()
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.tabs = [
            ("Dashboard", DashboardTab), ("Employees", EmployeesTab),
            ("Loans & Deductions", DeductionsTab), ("Monthly Inputs", InputsTab),
            ("Run Payroll", PayrollTab), ("Reports & Returns", ReportsTab),
            ("Tax Calculator", CalculatorTab), ("Settings", SettingsTab),
        ]
        self.tab_objs = []
        for name, cls in self.tabs:
            tab = cls(self.nb, self)
            self.nb.add(tab, text=f"  {name}  ")
            self.tab_objs.append(tab)
        self.nb.bind("<<NotebookTabChanged>>", lambda _e: self.refresh_current())
        self.period.trace_add("write", lambda *_: self.refresh_current())
        self.deiconify()
        self.refresh_current()

    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", font=("Segoe UI", 10), background=BG)
        s.configure("TFrame", background=BG)
        s.configure("Card.TFrame", background=CARD)
        s.configure("TLabel", background=BG)
        s.configure("Card.TLabel", background=CARD)
        s.configure("Muted.TLabel", background=CARD, foreground=MUTED)
        s.configure("H.TLabel", background=BG, foreground=NAVY, font=("Segoe UI", 13, "bold"))
        s.configure("TNotebook", background=BG, borderwidth=0)
        s.configure("TNotebook.Tab", padding=(10, 6), font=("Segoe UI", 10))
        s.map("TNotebook.Tab", background=[("selected", CARD)], foreground=[("selected", NAVY)])
        s.configure("Treeview", rowheight=24, font=("Segoe UI", 9))
        s.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), foreground=NAVY)
        s.configure("Accent.TButton", background=NAVY, foreground="white", padding=(12, 6))
        s.map("Accent.TButton", background=[("active", "#164f88")])
        s.configure("Warn.TButton", background=ORANGE, foreground="white", padding=(12, 6))
        s.map("Warn.TButton", background=[("active", "#c9630f")])
        s.configure("TButton", padding=(10, 5))
        s.configure("TLabelframe", background=BG)
        s.configure("TLabelframe.Label", background=BG, foreground=NAVY, font=("Segoe UI", 10, "bold"))
        s.configure("TCheckbutton", background=BG)

    def _header(self):
        bar = tk.Frame(self, bg=NAVY, height=56)
        bar.pack(fill="x")
        self.company_lbl = tk.Label(bar, text=self.db.company()["name"], fg="white", bg=NAVY,
                                    font=("Segoe UI", 15, "bold"))
        self.company_lbl.pack(side="left", padx=16, pady=10)
        tk.Label(bar, text="Payroll  |  Kenya (KRA / NSSF / SHIF / AHL)", fg="#c9d6e6", bg=NAVY).pack(side="left")
        tk.Label(bar, text=f"User: {self.username} ({self.role})", fg="#c9d6e6", bg=NAVY).pack(side="right", padx=16)
        cb = ttk.Combobox(bar, textvariable=self.period, values=period_choices(), width=10)
        cb.pack(side="right", pady=12)
        tk.Label(bar, text="Pay period:", fg="white", bg=NAVY, font=("Segoe UI", 10, "bold")).pack(side="right", padx=6)
        tk.Frame(self, bg=ORANGE, height=3).pack(fill="x", pady=(0, 8))

    def valid_period(self) -> str | None:
        p = self.period.get().strip()
        if re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", p):
            return p
        return None

    def refresh_current(self):
        if not self.valid_period():
            return
        idx = self.nb.index(self.nb.select())
        self.tab_objs[idx].refresh()

    def require_admin(self) -> bool:
        if self.role != "Admin":
            messagebox.showwarning(APP_NAME, "Only an Admin user can do this.")
            return False
        return True


class Tab(ttk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent, padding=12)
        self.app, self.db = app, app.db
        self.build()

    def build(self):
        pass

    def refresh(self):
        pass


# =============================================================================
class DashboardTab(Tab):
    def build(self):
        ttk.Label(self, text="Overview", style="H.TLabel").pack(anchor="w")
        self.cards = ttk.Frame(self)
        self.cards.pack(fill="x", pady=8)
        self.card_vars = {}
        for i, key in enumerate(["Active Employees", "Gross Pay", "Net Pay", "PAYE", "Employer Cost", "Run Status"]):
            f = ttk.Frame(self.cards, style="Card.TFrame", padding=14)
            f.grid(row=0, column=i, sticky="nsew", padx=5)
            self.cards.columnconfigure(i, weight=1)
            ttk.Label(f, text=key, style="Muted.TLabel").pack(anchor="w")
            v = tk.StringVar(value="-")
            tk.Label(f, textvariable=v, bg=CARD, fg=NAVY, font=("Segoe UI", 15, "bold")).pack(anchor="w")
            self.card_vars[key] = v

        lower = ttk.Frame(self)
        lower.pack(fill="both", expand=True)
        lower.columnconfigure(0, weight=1)
        lower.columnconfigure(1, weight=1)
        lower.rowconfigure(0, weight=1)
        lf = ttk.LabelFrame(lower, text="Statutory remittances for selected period", padding=8)
        lf.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        fr, self.stat_tree = make_tree(lf, [("item", "Item", 220, "w"), ("via", "Remit via", 140, "w"),
                                            ("amt", "Amount (KES)", 120, "e"), ("due", "Due", 110, "w")], height=8)
        fr.pack(fill="both", expand=True)
        rf = ttk.LabelFrame(lower, text="Recent activity (audit trail)", padding=8)
        rf.grid(row=0, column=1, sticky="nsew")
        fr2, self.audit_tree = make_tree(rf, [("ts", "Time", 140, "w"), ("user", "User", 80, "w"),
                                              ("act", "Action", 130, "w"), ("det", "Detail", 220, "w")], height=8)
        fr2.pack(fill="both", expand=True)
        tips = ("Workflow: 1) Add employees  2) Set loans/recurring deductions  3) Enter monthly inputs "
                "(overtime, bonus, absence)  4) Run payroll and review warnings  5) Generate payslips and "
                "returns  6) Close the period.  PAYE, NSSF, SHIF, Housing Levy and NITA are due by the 9th "
                "of the following month.")
        ttk.Label(self, text=tips, wraplength=1150, foreground=MUTED).pack(anchor="w", pady=(8, 0))

    def refresh(self):
        p = self.app.valid_period()
        self.card_vars["Active Employees"].set(str(len(self.db.employees_for_period(p))))
        status = self.db.run_status(p)
        self.card_vars["Run Status"].set(status or "Not run")
        for t in self.stat_tree.get_children():
            self.stat_tree.delete(t)
        if status:
            s = reports.summary(self.db, p)
            for k, key in [("Gross Pay", "gross"), ("Net Pay", "net"), ("PAYE", "paye"), ("Employer Cost", "employer_cost")]:
                self.card_vars[k].set(fmt(s[key]))
            for row in [("PAYE", "KRA iTax", s["paye"]), ("Withholding Tax", "KRA iTax", s["wht"]),
                        ("Housing Levy (EE+ER)", "KRA iTax", s["ahl_ee"] + s["ahl_er"]),
                        ("NSSF (EE+ER)", "NSSF", s["nssf_ee"] + s["nssf_er"]),
                        ("SHIF", "SHA", s["shif"]), ("NITA", "NITA", s["nita"])]:
                self.stat_tree.insert("", "end", values=(row[0], row[1], fmt(row[2]), s["due"]))
        else:
            for k in ("Gross Pay", "Net Pay", "PAYE", "Employer Cost"):
                self.card_vars[k].set("-")
        for t in self.audit_tree.get_children():
            self.audit_tree.delete(t)
        for a in self.db.audit(40):
            self.audit_tree.insert("", "end", values=(a["ts"], a["username"], a["action"], a["detail"]))


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


class EmployeeForm(tk.Toplevel):
    def __init__(self, tab, emp=None):
        super().__init__(tab)
        self.tab, self.emp = tab, emp
        self.title("Edit Employee" if emp else "New Employee")
        self.geometry("620x520")
        self.configure(bg=BG)
        self.vars = {}
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=10)
        for section, fields in FORM_SECTIONS:
            f = ttk.Frame(nb, padding=14)
            nb.add(f, text=section)
            for r, spec in enumerate(fields):
                key, label = spec[0], spec[1]
                kind = spec[2] if len(spec) > 2 else None
                current = emp[key] if emp else None
                if kind == "check":
                    v = tk.IntVar(value=int(current or 0))
                    ttk.Checkbutton(f, text=label, variable=v).grid(row=r, column=0, columnspan=2, sticky="w", pady=4)
                else:
                    default = {"status": "Active", "employment_type": "Primary", "payment_mode": "Bank",
                               "leave_days_per_year": 21}.get(key, "")
                    v = tk.StringVar(value="" if current is None and not default else
                                     (current if current is not None else default))
                    ttk.Label(f, text=label).grid(row=r, column=0, sticky="w", pady=4, padx=(0, 12))
                    w = ttk.Combobox(f, textvariable=v, values=kind, width=34, state="readonly") if kind \
                        else ttk.Entry(f, textvariable=v, width=37)
                    w.grid(row=r, column=1, sticky="w", pady=4)
                self.vars[key] = v
        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(btns, text="Save", style="Accent.TButton", command=self.save).pack(side="right")
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=6)
        self.grab_set()

    def save(self):
        data = {k: v.get() for k, v in self.vars.items()}
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
            return messagebox.showerror(APP_NAME, str(ex), parent=self)
        pin = data["kra_pin"].strip().upper()
        data["kra_pin"] = pin
        if pin and not KRA_PIN_RE.match(pin):
            if not messagebox.askyesno(APP_NAME, f"KRA PIN '{pin}' does not look valid (e.g. A012345678Z). Save anyway?", parent=self):
                return
        if data["exit_date"].strip() and data["status"] == "Active":
            data["status"] = "Exited"
        try:
            self.tab.db.save_employee(data, self.emp["id"] if self.emp else None)
        except Exception as ex:
            return messagebox.showerror(APP_NAME, f"Could not save: {ex}", parent=self)
        self.destroy()
        self.tab.refresh()


class EmployeesTab(Tab):
    COLS = [("staff", "Staff No", 80, "w"), ("name", "Name", 200, "w"), ("dept", "Department", 130, "w"),
            ("desig", "Designation", 150, "w"), ("type", "Type", 120, "w"), ("pin", "KRA PIN", 110, "w"),
            ("basic", "Basic Salary", 110, "e"), ("gross", "Fixed Gross", 110, "e"), ("status", "Status", 70, "w")]

    def build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text="Search:").pack(side="left")
        self.search = tk.StringVar()
        self.search.trace_add("write", lambda *_: self.refresh())
        ttk.Entry(top, textvariable=self.search, width=30).pack(side="left", padx=6)
        self.show_exited = tk.IntVar(value=0)
        ttk.Checkbutton(top, text="Show exited", variable=self.show_exited, command=self.refresh).pack(side="left", padx=8)
        for text, cmd, style in [("Export CSV", self.export_csv, "TButton"),
                                 ("Import CSV", self.import_csv, "TButton"),
                                 ("Edit", self.edit, "TButton"),
                                 ("+ Add Employee", self.add, "Accent.TButton")]:
            ttk.Button(top, text=text, command=cmd, style=style).pack(side="right", padx=3)
        fr, self.tree = make_tree(self, self.COLS, height=22)
        fr.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda _e: self.edit())
        self.count = ttk.Label(self, foreground=MUTED)
        self.count.pack(anchor="w", pady=(6, 0))

    def refresh(self):
        for t in self.tree.get_children():
            self.tree.delete(t)
        q = self.search.get().lower()
        n = 0
        for e in self.db.employees(include_exited=bool(self.show_exited.get())):
            name = f"{e['first_name']} {e['last_name']}"
            hay = f"{e['staff_no']} {name} {e['department']} {e['kra_pin']} {e['id_no']}".lower()
            if q and q not in hay:
                continue
            fixed = sum(e[k] or 0 for k in ("basic_salary", "house_allowance", "transport_allowance", "other_allowance"))
            self.tree.insert("", "end", iid=str(e["id"]), values=(
                e["staff_no"], name, e["department"], e["designation"], e["employment_type"], e["kra_pin"],
                fmt(e["basic_salary"]), fmt(fixed), e["status"]))
            n += 1
        self.count.config(text=f"{n} employee(s)")

    def add(self):
        EmployeeForm(self)

    def edit(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showinfo(APP_NAME, "Select an employee first.")
        EmployeeForm(self, self.db.employee(int(sel[0])))

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="employees.csv",
                                            filetypes=[("CSV", "*.csv")])
        if not path:
            return
        rows = [[e[f] for f in EMPLOYEE_FIELDS] for e in self.db.employees()]
        reports.write_csv(path, EMPLOYEE_FIELDS, rows)
        messagebox.showinfo(APP_NAME, f"Exported {len(rows)} employees.\nUse this file as the import template.")

    def import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not path:
            return
        existing = {e["staff_no"]: e["id"] for e in self.db.employees()}
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
                    self.db.save_employee(row, emp_id)
                    updated += bool(emp_id)
                    added += not emp_id
                except Exception as ex:
                    errors.append(f"Row {i}: {ex}")
        msg = f"Added {added}, updated {updated}."
        if errors:
            msg += "\n\nErrors:\n" + "\n".join(errors[:15])
        messagebox.showinfo(APP_NAME, msg)
        self.refresh()


# =============================================================================
class DeductionsTab(Tab):
    def build(self):
        left = ttk.LabelFrame(self, text="Employees", padding=6)
        left.pack(side="left", fill="y")
        fr, self.emp_tree = make_tree(left, [("staff", "Staff", 70, "w"), ("name", "Name", 170, "w")], height=24)
        fr.pack(fill="y", expand=True)
        self.emp_tree.bind("<<TreeviewSelect>>", lambda _e: self.load_deductions())

        right = ttk.Frame(self, padding=(12, 0, 0, 0))
        right.pack(side="left", fill="both", expand=True)
        self.title_lbl = ttk.Label(right, text="Select an employee", style="H.TLabel")
        self.title_lbl.pack(anchor="w")
        fr2, self.tree = make_tree(right, [("id", "#", 40, "w"), ("kind", "Type", 120, "w"),
                                           ("desc", "Description", 200, "w"), ("inst", "Monthly", 100, "e"),
                                           ("bal", "Balance", 110, "e"), ("start", "Start", 80, "w"),
                                           ("st", "Status", 80, "w")], height=12)
        fr2.pack(fill="both", expand=True, pady=6)
        ttk.Button(right, text="Activate / Stop selected", command=self.toggle).pack(anchor="e")

        form = ttk.LabelFrame(right, text="Add loan / recurring deduction", padding=10)
        form.pack(fill="x", pady=8)
        self.kind = tk.StringVar(value=DEDUCTION_KINDS[0])
        self.desc, self.inst, self.bal, self.start = tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()
        items = [("Type", ttk.Combobox(form, textvariable=self.kind, values=DEDUCTION_KINDS, state="readonly", width=18)),
                 ("Description", ttk.Entry(form, textvariable=self.desc, width=26)),
                 ("Monthly amount", ttk.Entry(form, textvariable=self.inst, width=14)),
                 ("Loan balance (blank = recurring)", ttk.Entry(form, textvariable=self.bal, width=14)),
                 ("Start period (YYYY-MM)", ttk.Entry(form, textvariable=self.start, width=10))]
        for c, (lbl, w) in enumerate(items):
            ttk.Label(form, text=lbl).grid(row=0, column=c, sticky="w", padx=4)
            w.grid(row=1, column=c, sticky="w", padx=4)
        ttk.Button(form, text="Add", style="Accent.TButton", command=self.add).grid(row=1, column=len(items), padx=8)
        ttk.Label(right, foreground=MUTED, wraplength=760, text=(
            "Loans with a balance reduce automatically when a payroll period is closed and stop at zero. "
            "Leave the balance blank for recurring deductions such as SACCO, welfare or union dues. "
            "Note: employer loans below the KRA market rate attract Fringe Benefit Tax payable by the employer."
        )).pack(anchor="w")

    def refresh(self):
        sel = self.emp_tree.selection()
        for t in self.emp_tree.get_children():
            self.emp_tree.delete(t)
        for e in self.db.employees(include_exited=False):
            self.emp_tree.insert("", "end", iid=str(e["id"]), values=(e["staff_no"], f"{e['first_name']} {e['last_name']}"))
        if sel and self.emp_tree.exists(sel[0]):
            self.emp_tree.selection_set(sel[0])
        self.start.set(self.app.valid_period() or "")

    def current_emp(self):
        sel = self.emp_tree.selection()
        return int(sel[0]) if sel else None

    def load_deductions(self):
        emp_id = self.current_emp()
        for t in self.tree.get_children():
            self.tree.delete(t)
        if not emp_id:
            return
        e = self.db.employee(emp_id)
        self.title_lbl.config(text=f"{e['staff_no']} - {e['first_name']} {e['last_name']}")
        for d in self.db.deductions(emp_id):
            self.tree.insert("", "end", iid=str(d["id"]), values=(
                d["id"], d["kind"], d["description"], fmt(d["installment"]),
                "Recurring" if d["balance"] is None else fmt(d["balance"]),
                d["start_period"] or "", "Active" if d["active"] else "Stopped"))

    def add(self):
        emp_id = self.current_emp()
        if not emp_id:
            return messagebox.showinfo(APP_NAME, "Select an employee first.")
        try:
            inst = num(self.inst.get())
            bal = num(self.bal.get()) if self.bal.get().strip() else None
            if inst <= 0:
                raise ValueError("Monthly amount must be greater than zero.")
            start = self.start.get().strip()
            if start and not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", start):
                raise ValueError("Start period must be YYYY-MM.")
        except ValueError as ex:
            return messagebox.showerror(APP_NAME, str(ex))
        self.db.add_deduction(emp_id, self.kind.get(), self.desc.get().strip(), inst, bal, start)
        self.desc.set("")
        self.inst.set("")
        self.bal.set("")
        self.load_deductions()

    def toggle(self):
        sel = self.tree.selection()
        if not sel:
            return
        d = self.db.q("SELECT active FROM deductions WHERE id=?", (int(sel[0]),))[0]
        self.db.set_deduction_active(int(sel[0]), not d["active"])
        self.load_deductions()


# =============================================================================
INPUT_LABELS = {"ot_normal_hours": "OT Hrs x1.5", "ot_holiday_hours": "OT Hrs x2.0", "bonus": "Bonus",
                "arrears": "Arrears", "leave_pay": "Leave Pay", "other_earnings": "Other Earnings",
                "absent_days": "Absent Days", "other_deductions": "Other Deduction",
                "leave_taken": "Leave Days Taken"}


class InputsTab(Tab):
    def build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 8))
        self.lbl = ttk.Label(top, style="H.TLabel")
        self.lbl.pack(side="left")
        ttk.Button(top, text="Import CSV", command=self.import_csv).pack(side="right", padx=3)
        ttk.Button(top, text="Export template", command=self.export_csv).pack(side="right", padx=3)
        ttk.Button(top, text="Edit selected", style="Accent.TButton", command=self.edit).pack(side="right", padx=3)
        cols = [("staff", "Staff", 70, "w"), ("name", "Name", 180, "w")] + \
               [(f, INPUT_LABELS[f], 95, "e") for f in INPUT_FIELDS] + [("notes", "Notes", 160, "w")]
        fr, self.tree = make_tree(self, cols, height=22)
        fr.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda _e: self.edit())
        ttk.Label(self, foreground=MUTED, text=(
            "Double-click an employee to enter this month's variable pay. Overtime is computed from basic / "
            "standard monthly hours. Absence deducts basic / days-per-month for each day.")).pack(anchor="w", pady=(6, 0))

    def refresh(self):
        p = self.app.valid_period()
        self.lbl.config(text=f"Variable inputs for {reports.period_label(p)}  [{self.db.run_status(p) or 'Not run'}]")
        for t in self.tree.get_children():
            self.tree.delete(t)
        for e in self.db.employees_for_period(p):
            i = self.db.inputs(e["id"], p)
            self.tree.insert("", "end", iid=str(e["id"]), values=(
                e["staff_no"], f"{e['first_name']} {e['last_name']}",
                *[fmt(i[f]) if i[f] else "" for f in INPUT_FIELDS], i.get("notes") or ""))

    def locked(self):
        if self.db.run_status(self.app.valid_period()) == "Closed":
            messagebox.showwarning(APP_NAME, "This period is closed. Reopen it in Run Payroll to change inputs.")
            return True
        return False

    def edit(self):
        sel = self.tree.selection()
        if not sel or self.locked():
            return
        emp_id, p = int(sel[0]), self.app.valid_period()
        e, cur = self.db.employee(emp_id), self.db.inputs(emp_id, p)
        dlg = tk.Toplevel(self)
        dlg.title(f"{e['first_name']} {e['last_name']} - {p}")
        dlg.configure(bg=BG, padx=16, pady=12)
        vars_ = {}
        for r, f in enumerate(INPUT_FIELDS + ["notes"]):
            ttk.Label(dlg, text=INPUT_LABELS.get(f, "Notes")).grid(row=r, column=0, sticky="w", pady=3)
            v = tk.StringVar(value=(cur.get(f) or "") if f == "notes" else (str(cur[f]) if cur[f] else ""))
            ttk.Entry(dlg, textvariable=v, width=24).grid(row=r, column=1, pady=3, padx=8)
            vars_[f] = v
        ent, bal = self.db.leave_balance(emp_id, int(p[:4]))
        ttk.Label(dlg, text=f"Leave: {ent:g} days/yr, balance {bal:g}", foreground=MUTED).grid(
            row=20, column=0, columnspan=2, sticky="w", pady=4)

        def save():
            try:
                data = {f: num(vars_[f].get()) for f in INPUT_FIELDS}
            except ValueError as ex:
                return messagebox.showerror(APP_NAME, str(ex), parent=dlg)
            data["notes"] = vars_["notes"].get()
            self.db.save_inputs(emp_id, p, data)
            self.db.log("inputs.save", f"{e['staff_no']} {p}")
            dlg.destroy()
            self.refresh()
        ttk.Button(dlg, text="Save", style="Accent.TButton", command=save).grid(row=21, column=1, sticky="e", pady=6)
        dlg.bind("<Return>", lambda _e: save())
        dlg.grab_set()

    def export_csv(self):
        p = self.app.valid_period()
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=f"inputs_{p}.csv")
        if not path:
            return
        rows = []
        for e in self.db.employees_for_period(p):
            i = self.db.inputs(e["id"], p)
            rows.append([e["staff_no"], f"{e['first_name']} {e['last_name']}"] + [i[f] for f in INPUT_FIELDS] + [i.get("notes") or ""])
        reports.write_csv(path, ["staff_no", "name"] + INPUT_FIELDS + ["notes"], rows)
        messagebox.showinfo(APP_NAME, "Template exported. Fill it in and use Import CSV.")

    def import_csv(self):
        if self.locked():
            return
        p = self.app.valid_period()
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not path:
            return
        ids = {e["staff_no"]: e["id"] for e in self.db.employees()}
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
                self.db.save_inputs(ids[sid], p, data)
                n += 1
        self.db.log("inputs.import", f"{p}: {n} rows")
        messagebox.showinfo(APP_NAME, f"Imported {n} rows." + ("\n\n" + "\n".join(errors[:15]) if errors else ""))
        self.refresh()


# =============================================================================
class PayrollTab(Tab):
    COLS = [("staff", "Staff", 65, "w"), ("name", "Name", 170, "w"), ("gross", "Gross Pay", 105, "e"),
            ("nssf", "NSSF", 85, "e"), ("shif", "SHIF", 85, "e"), ("ahl", "Housing Levy", 90, "e"),
            ("taxable", "Taxable Pay", 105, "e"), ("paye", "PAYE", 95, "e"), ("wht", "WHT", 75, "e"),
            ("other", "Other Ded.", 90, "e"), ("net", "Net Pay", 105, "e"), ("cost", "Employer Cost", 105, "e")]

    def build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 8))
        self.lbl = ttk.Label(top, style="H.TLabel")
        self.lbl.pack(side="left")
        ttk.Button(top, text="Reopen Period", command=self.reopen).pack(side="right", padx=3)
        ttk.Button(top, text="Close Period", style="Warn.TButton", command=self.close).pack(side="right", padx=3)
        ttk.Button(top, text="Run / Recalculate Payroll", style="Accent.TButton", command=self.run).pack(side="right", padx=3)
        fr, self.tree = make_tree(self, self.COLS, height=17)
        fr.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.open_slip)
        wf = ttk.LabelFrame(self, text="Validation warnings", padding=6)
        wf.pack(fill="x", pady=(8, 0))
        self.warn = tk.Text(wf, height=5, font=("Consolas", 9), fg="#a33", relief="flat")
        self.warn.pack(fill="x")

    def refresh(self):
        p = self.app.valid_period()
        status = self.db.run_status(p)
        self.lbl.config(text=f"Payroll {reports.period_label(p)}  [{status or 'Not run'}]")
        self.show(self.db.run_lines(p) if status else [], None)

    def show(self, lines, warnings):
        for t in self.tree.get_children():
            self.tree.delete(t)
        keys = ["gross_pay", "nssf_employee", "shif", "ahl_employee", "taxable_pay", "paye", "wht", "other", "net_pay", "employer_cost"]
        tot = dict.fromkeys(keys, 0.0)
        for l in lines:
            e = l["employee"]
            l = dict(l, other=sum(l["other_deductions"].values()) + l["voluntary_pension"])
            for k in keys:
                tot[k] += l[k]
            self.tree.insert("", "end", iid=str(e["id"]), tags=("warn",) if l["warnings"] else (),
                             values=(e["staff_no"], f"{e['first_name']} {e['last_name']}", *[fmt(l[k]) for k in keys]))
        if lines:
            self.tree.insert("", "end", iid="TOTAL", tags=("total",),
                             values=("", f"TOTAL ({len(lines)})", *[fmt(tot[k]) for k in keys]))
        self.warn.delete("1.0", "end")
        if warnings is None:
            warnings = [f"{l['employee']['staff_no']}: {w}" for l in lines for w in l["warnings"]]
        self.warn.insert("end", "\n".join(warnings) if warnings else "No warnings.")

    def run(self):
        p = self.app.valid_period()
        try:
            lines, warnings = self.db.run_payroll(p)
        except ValueError as ex:
            return messagebox.showwarning(APP_NAME, str(ex))
        if not lines:
            messagebox.showinfo(APP_NAME, "No active employees for this period.")
        self.lbl.config(text=f"Payroll {reports.period_label(p)}  [Draft]")
        self.show(lines, warnings)

    def close(self):
        p = self.app.valid_period()
        if not self.app.require_admin():
            return
        if not messagebox.askyesno(APP_NAME, f"Close payroll for {reports.period_label(p)}?\n\n"
                                   "Inputs will be locked and loan balances reduced."):
            return
        try:
            self.db.close_period(p)
        except ValueError as ex:
            return messagebox.showwarning(APP_NAME, str(ex))
        self.refresh()

    def reopen(self):
        p = self.app.valid_period()
        if not self.app.require_admin():
            return
        if not messagebox.askyesno(APP_NAME, f"Reopen {reports.period_label(p)}? Loan balances will be restored."):
            return
        try:
            self.db.reopen_period(p)
        except ValueError as ex:
            return messagebox.showwarning(APP_NAME, str(ex))
        self.refresh()

    def open_slip(self, _e=None):
        sel = self.tree.selection()
        if not sel or sel[0] == "TOTAL":
            return
        open_path(reports.payslips(self.db, self.app.valid_period(), OUTPUT, int(sel[0])))


# =============================================================================
class ReportsTab(Tab):
    def build(self):
        self.lbl = ttk.Label(self, style="H.TLabel")
        self.lbl.pack(anchor="w")
        grid = ttk.LabelFrame(self, text="Monthly reports & statutory returns", padding=12)
        grid.pack(fill="x", pady=8)
        for i, (name, fn) in enumerate(reports.ALL_PERIOD_REPORTS):
            ttk.Button(grid, text=name, width=34, command=lambda f=fn: self.gen(f)).grid(
                row=i // 3, column=i % 3, padx=6, pady=5, sticky="w")
        bar = ttk.Frame(grid)
        bar.grid(row=10, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Button(bar, text="Generate ALL for period", style="Accent.TButton", command=self.gen_all).pack(side="left", padx=6)
        ttk.Button(bar, text="Open output folder", command=self.open_folder).pack(side="left")

        p9 = ttk.LabelFrame(self, text="P9A Tax Deduction Card (annual)", padding=12)
        p9.pack(fill="x", pady=8)
        ttk.Label(p9, text="Year").grid(row=0, column=0, padx=4)
        self.year = tk.StringVar(value=str(date.today().year))
        ttk.Entry(p9, textvariable=self.year, width=8).grid(row=0, column=1, padx=4)
        ttk.Label(p9, text="Employee").grid(row=0, column=2, padx=4)
        self.emp = tk.StringVar(value="All employees")
        self.emp_cb = ttk.Combobox(p9, textvariable=self.emp, width=40, state="readonly")
        self.emp_cb.grid(row=0, column=3, padx=4)
        ttk.Button(p9, text="Generate P9A", style="Accent.TButton", command=self.gen_p9).grid(row=0, column=4, padx=8)

        ttk.Label(self, foreground=MUTED, wraplength=1100, text=(
            "Payslips and P9A open in your browser - use Print > Save as PDF to file or e-mail them. "
            "CSV files open in Excel. Copy the KRA P10 rows into the official iTax P10 Excel template "
            "(Employee Details sheet) and validate it before uploading; NSSF, SHIF and Housing Levy files "
            "follow the portal column order. Files are saved under the 'output' folder by period."
        )).pack(anchor="w", pady=6)
        self.log = tk.Text(self, height=10, font=("Consolas", 9), relief="flat")
        self.log.pack(fill="both", expand=True)

    def refresh(self):
        p = self.app.valid_period()
        self.lbl.config(text=f"Reports for {reports.period_label(p)}  [{self.db.run_status(p) or 'Payroll not run'}]")
        self.emps = {"All employees": None}
        for e in self.db.employees():
            self.emps[f"{e['staff_no']} - {e['first_name']} {e['last_name']}"] = e["id"]
        self.emp_cb.config(values=list(self.emps))

    def _check(self):
        p = self.app.valid_period()
        if not self.db.run_status(p):
            messagebox.showwarning(APP_NAME, "Run payroll for this period first.")
            return None
        return p

    def gen(self, fn, open_it=True):
        p = self._check()
        if not p:
            return None
        path = fn(self.db, p, OUTPUT)
        self.log.insert("end", f"{datetime.now():%H:%M:%S}  Created {path}\n")
        self.log.see("end")
        self.db.log("report", os.path.basename(path) + " " + p)
        if open_it:
            open_path(path)
        return path

    def gen_all(self):
        if not self._check():
            return
        for _, fn in reports.ALL_PERIOD_REPORTS:
            self.gen(fn, open_it=False)
        self.open_folder()

    def open_folder(self):
        p = self.app.valid_period()
        open_path(reports.out_dir(OUTPUT, p))

    def gen_p9(self):
        try:
            year = int(self.year.get())
        except ValueError:
            return messagebox.showerror(APP_NAME, "Enter a valid year.")
        emp_id = self.emps.get(self.emp.get())
        if not self.db.lines_for_year(year, emp_id):
            return messagebox.showinfo(APP_NAME, "No payroll data for that year/employee.")
        path = reports.p9a(self.db, year, os.path.join(OUTPUT, "P9A"), emp_id)
        self.log.insert("end", f"{datetime.now():%H:%M:%S}  Created {path}\n")
        open_path(path)


# =============================================================================
class CalculatorTab(Tab):
    FIELDS = [("basic", "Basic salary / Target net", "100000"), ("allow", "Cash allowances", "0"),
              ("benefits", "Non-cash benefits", "0"), ("pension", "Voluntary pension", "0"),
              ("insurance", "Insurance premium", "0"), ("mortgage", "Mortgage interest", "0")]

    def build(self):
        left = ttk.LabelFrame(self, text="PAYE & net pay calculator", padding=14)
        left.pack(side="left", fill="y")
        self.vars = {}
        for r, (k, lbl, dflt) in enumerate(self.FIELDS):
            ttk.Label(left, text=lbl).grid(row=r, column=0, sticky="w", pady=4)
            self.vars[k] = tk.StringVar(value=dflt)
            ttk.Entry(left, textvariable=self.vars[k], width=18).grid(row=r, column=1, pady=4, padx=8)
        r = len(self.FIELDS)
        self.etype = tk.StringVar(value="Primary")
        ttk.Label(left, text="Employment type").grid(row=r, column=0, sticky="w", pady=4)
        ttk.Combobox(left, textvariable=self.etype, values=EMPLOYMENT_TYPES, state="readonly", width=16).grid(row=r, column=1, pady=4)
        self.disabled, self.mode = tk.IntVar(), tk.StringVar(value="g2n")
        ttk.Checkbutton(left, text="Disability exemption", variable=self.disabled).grid(row=r + 1, column=0, columnspan=2, sticky="w")
        ttk.Radiobutton(left, text="Gross to Net", value="g2n", variable=self.mode).grid(row=r + 2, column=0, sticky="w", pady=(8, 0))
        ttk.Radiobutton(left, text="Net to Gross (gross-up)", value="n2g", variable=self.mode).grid(row=r + 2, column=1, sticky="w", pady=(8, 0))
        ttk.Button(left, text="Calculate", style="Accent.TButton", command=self.calc).grid(row=r + 3, column=0, columnspan=2, sticky="ew", pady=12)
        self.out = tk.Text(self, font=("Consolas", 10), relief="flat", padx=14, pady=10)
        self.out.pack(side="left", fill="both", expand=True, padx=(12, 0))

    def calc(self):
        try:
            v = {k: num(var.get()) for k, var in self.vars.items()}
        except ValueError as ex:
            return messagebox.showerror(APP_NAME, str(ex))
        rates = self.db.rates()
        inp = PayInput(period=self.app.valid_period() or date.today().strftime("%Y-%m"), basic=v["basic"],
                       allowances={"Allowances": v["allow"]}, non_cash_benefits=v["benefits"],
                       voluntary_pension=v["pension"], insurance_premium=v["insurance"],
                       mortgage_interest=v["mortgage"], disabled=bool(self.disabled.get()),
                       employment_type=self.etype.get())
        if self.mode.get() == "n2g":
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
        self.out.delete("1.0", "end")
        self.out.insert("end", text)


# =============================================================================
class SettingsTab(Tab):
    COMPANY = [("name", "Company name"), ("kra_pin", "Employer KRA PIN"), ("nssf_no", "NSSF employer no."),
               ("shif_no", "SHA/SHIF employer no."), ("nita_no", "NITA no."), ("address", "Address"),
               ("phone", "Phone"), ("email", "Email"), ("bank_name", "Paying bank"), ("bank_account", "Bank account")]

    def build(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        cf = ttk.Frame(nb, padding=14)
        nb.add(cf, text="Company")
        self.cvars = {}
        for r, (k, lbl) in enumerate(self.COMPANY):
            ttk.Label(cf, text=lbl).grid(row=r, column=0, sticky="w", pady=4)
            self.cvars[k] = tk.StringVar()
            ttk.Entry(cf, textvariable=self.cvars[k], width=50).grid(row=r, column=1, pady=4, padx=8)
        ttk.Button(cf, text="Save company details", style="Accent.TButton", command=self.save_company).grid(
            row=20, column=1, sticky="e", pady=10)

        rf = ttk.Frame(nb, padding=14)
        nb.add(rf, text="Statutory Rates")
        ttk.Label(rf, foreground=MUTED, wraplength=1100, text=(
            "Edit rates when KRA / NSSF / SHA publish changes (Finance Act, Legal Notices). Values are JSON; "
            "rates are decimals (0.30 = 30%). " + " ".join(RATE_HELP.values()))).pack(anchor="w")
        self.rates_txt = tk.Text(rf, font=("Consolas", 10), relief="flat", undo=True)
        self.rates_txt.pack(fill="both", expand=True, pady=6)
        b = ttk.Frame(rf)
        b.pack(fill="x")
        ttk.Button(b, text="Save rates", style="Accent.TButton", command=self.save_rates).pack(side="right")
        ttk.Button(b, text="Restore defaults", command=self.reset_rates).pack(side="right", padx=6)

        uf = ttk.Frame(nb, padding=14)
        nb.add(uf, text="Users & Security")
        fr, self.user_tree = make_tree(uf, [("u", "Username", 200, "w"), ("r", "Role", 120, "w")], height=6)
        fr.pack(fill="x")
        f2 = ttk.Frame(uf)
        f2.pack(fill="x", pady=10)
        self.nu, self.np, self.nr = tk.StringVar(), tk.StringVar(), tk.StringVar(value="Payroll Officer")
        for c, (lbl, w) in enumerate([("Username", ttk.Entry(f2, textvariable=self.nu, width=18)),
                                      ("Password", ttk.Entry(f2, textvariable=self.np, show="*", width=18)),
                                      ("Role", ttk.Combobox(f2, textvariable=self.nr, values=["Admin", "Payroll Officer"],
                                                            state="readonly", width=16))]):
            ttk.Label(f2, text=lbl).grid(row=0, column=c, sticky="w", padx=4)
            w.grid(row=1, column=c, padx=4)
        ttk.Button(f2, text="Add user", command=self.add_user).grid(row=1, column=3, padx=6)
        ttk.Button(f2, text="Change my password", command=self.change_pw).grid(row=1, column=4, padx=6)
        ttk.Separator(uf).pack(fill="x", pady=10)
        ttk.Button(uf, text="Backup database...", style="Accent.TButton", command=self.backup).pack(anchor="w")
        ttk.Label(uf, foreground=MUTED, text=f"Database: {DB_PATH}").pack(anchor="w", pady=4)
        ttk.Label(uf, text="Audit trail", style="H.TLabel").pack(anchor="w", pady=(10, 0))
        fr3, self.audit_tree = make_tree(uf, [("ts", "Time", 150, "w"), ("u", "User", 100, "w"),
                                              ("a", "Action", 150, "w"), ("d", "Detail", 500, "w")], height=10)
        fr3.pack(fill="both", expand=True)

    def refresh(self):
        c = self.db.company()
        for k, v in self.cvars.items():
            v.set(c.get(k, ""))
        self.rates_txt.delete("1.0", "end")
        self.rates_txt.insert("end", json.dumps(self.db.rates(), indent=2))
        for t in self.user_tree.get_children():
            self.user_tree.delete(t)
        for u in self.db.users():
            self.user_tree.insert("", "end", values=(u["username"], u["role"]))
        for t in self.audit_tree.get_children():
            self.audit_tree.delete(t)
        for a in self.db.audit(300):
            self.audit_tree.insert("", "end", values=(a["ts"], a["username"], a["action"], a["detail"]))

    def save_company(self):
        if not self.app.require_admin():
            return
        data = {k: v.get().strip() for k, v in self.cvars.items()}
        self.db.set_setting("company", data)
        self.db.log("company.update")
        self.app.company_lbl.config(text=data["name"])
        messagebox.showinfo(APP_NAME, "Company details saved.")

    def save_rates(self):
        if not self.app.require_admin():
            return
        try:
            rates = json.loads(self.rates_txt.get("1.0", "end"))
            missing = [k for k in DEFAULT_RATES if k not in rates]
            if missing:
                raise ValueError("Missing keys: " + ", ".join(missing))
            calculate(PayInput(period="2026-01", basic=50000), rates)
        except Exception as ex:
            return messagebox.showerror(APP_NAME, f"Rates not saved: {ex}")
        self.db.set_setting("rates", rates)
        self.db.log("rates.update", rates.get("rates_version", ""))
        messagebox.showinfo(APP_NAME, "Statutory rates saved. Re-run any draft payroll to apply them.")

    def reset_rates(self):
        if self.app.require_admin() and messagebox.askyesno(APP_NAME, "Restore the built-in default rates?"):
            self.db.set_setting("rates", DEFAULT_RATES)
            self.db.log("rates.reset")
            self.refresh()

    def add_user(self):
        if not self.app.require_admin():
            return
        u, p = self.nu.get().strip(), self.np.get()
        if not u or len(p) < 8:
            return messagebox.showerror(APP_NAME, "Enter a username and a password of at least 8 characters.")
        try:
            self.db.create_user(u, p, self.nr.get())
        except Exception as ex:
            return messagebox.showerror(APP_NAME, str(ex))
        self.nu.set("")
        self.np.set("")
        self.refresh()

    def change_pw(self):
        p = self.np.get()
        if len(p) < 8:
            return messagebox.showerror(APP_NAME, "Type the new password (8+ characters) in the Password box.")
        self.db.change_password(self.app.username, p)
        self.np.set("")
        messagebox.showinfo(APP_NAME, "Password changed.")

    def backup(self):
        path = filedialog.asksaveasfilename(defaultextension=".db",
                                            initialfile=f"payroll_backup_{datetime.now():%Y%m%d_%H%M}.db")
        if path:
            self.db.backup(path)
            messagebox.showinfo(APP_NAME, f"Backup saved to\n{path}")


def main():
    app = App()
    if app.ok:
        app.mainloop()


if __name__ == "__main__":
    main()
