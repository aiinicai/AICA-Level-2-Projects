"""SQLite storage, users, audit trail and the monthly payroll run."""
from __future__ import annotations

import calendar
import copy
import hashlib
import json
import secrets
import sqlite3
from datetime import date, datetime

from config import DEFAULT_COMPANY, DEFAULT_RATES
from engine import PayInput, calculate

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY, salt TEXT NOT NULL, pw_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'Admin');
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_no TEXT UNIQUE NOT NULL, first_name TEXT NOT NULL, last_name TEXT NOT NULL,
    id_no TEXT, kra_pin TEXT, nssf_no TEXT, shif_no TEXT, phone TEXT, email TEXT,
    gender TEXT, dob TEXT, department TEXT, designation TEXT,
    hire_date TEXT, exit_date TEXT, status TEXT NOT NULL DEFAULT 'Active',
    employment_type TEXT NOT NULL DEFAULT 'Primary',
    basic_salary REAL DEFAULT 0, house_allowance REAL DEFAULT 0,
    transport_allowance REAL DEFAULT 0, other_allowance REAL DEFAULT 0,
    non_cash_benefits REAL DEFAULT 0, car_benefit REAL DEFAULT 0, housing_benefit REAL DEFAULT 0,
    voluntary_pension REAL DEFAULT 0, insurance_premium REAL DEFAULT 0,
    mortgage_interest REAL DEFAULT 0, prmf REAL DEFAULT 0,
    disabled INTEGER DEFAULT 0, disability_cert TEXT, nssf_contracted_out INTEGER DEFAULT 0,
    payment_mode TEXT DEFAULT 'Bank', bank_name TEXT, bank_branch TEXT, account_no TEXT,
    leave_days_per_year REAL DEFAULT 21);
CREATE TABLE IF NOT EXISTS deductions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    kind TEXT NOT NULL, description TEXT, installment REAL NOT NULL,
    balance REAL, active INTEGER NOT NULL DEFAULT 1, start_period TEXT);
CREATE TABLE IF NOT EXISTS period_inputs (
    employee_id INTEGER NOT NULL REFERENCES employees(id), period TEXT NOT NULL,
    ot_normal_hours REAL DEFAULT 0, ot_holiday_hours REAL DEFAULT 0,
    bonus REAL DEFAULT 0, arrears REAL DEFAULT 0, leave_pay REAL DEFAULT 0,
    other_earnings REAL DEFAULT 0, absent_days REAL DEFAULT 0,
    other_deductions REAL DEFAULT 0, leave_taken REAL DEFAULT 0, notes TEXT,
    PRIMARY KEY (employee_id, period));
CREATE TABLE IF NOT EXISTS runs (
    period TEXT PRIMARY KEY, status TEXT NOT NULL, run_at TEXT, run_by TEXT,
    closed_at TEXT, closed_by TEXT);
CREATE TABLE IF NOT EXISTS run_lines (
    period TEXT NOT NULL, employee_id INTEGER NOT NULL, data TEXT NOT NULL,
    PRIMARY KEY (period, employee_id));
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, username TEXT, action TEXT, detail TEXT);
"""

EMPLOYEE_FIELDS = [
    "staff_no", "first_name", "last_name", "id_no", "kra_pin", "nssf_no", "shif_no",
    "phone", "email", "gender", "dob", "department", "designation", "hire_date",
    "exit_date", "status", "employment_type", "basic_salary", "house_allowance",
    "transport_allowance", "other_allowance", "non_cash_benefits", "car_benefit",
    "housing_benefit", "voluntary_pension", "insurance_premium", "mortgage_interest",
    "prmf", "disabled", "disability_cert", "nssf_contracted_out", "payment_mode",
    "bank_name", "bank_branch", "account_no", "leave_days_per_year",
]
NUMERIC_EMPLOYEE_FIELDS = {
    "basic_salary", "house_allowance", "transport_allowance", "other_allowance",
    "non_cash_benefits", "car_benefit", "housing_benefit", "voluntary_pension",
    "insurance_premium", "mortgage_interest", "prmf", "leave_days_per_year",
}
INPUT_FIELDS = ["ot_normal_hours", "ot_holiday_hours", "bonus", "arrears", "leave_pay",
                "other_earnings", "absent_days", "other_deductions", "leave_taken"]


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()


def period_bounds(period: str) -> tuple[date, date]:
    y, m = map(int, period.split("-"))
    return date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])


class Database:
    def __init__(self, path: str):
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        if self.get_setting("rates") is None:
            self.set_setting("rates", DEFAULT_RATES)
        if self.get_setting("company") is None:
            self.set_setting("company", DEFAULT_COMPANY)
        self.user = "system"

    # ---- low level -------------------------------------------------------
    def q(self, sql, args=()):
        return self.conn.execute(sql, args).fetchall()

    def x(self, sql, args=()):
        cur = self.conn.execute(sql, args)
        self.conn.commit()
        return cur

    def log(self, action: str, detail: str = ""):
        self.x("INSERT INTO audit (ts, username, action, detail) VALUES (?,?,?,?)",
               (datetime.now().isoformat(timespec="seconds"), self.user, action, detail))

    # ---- settings --------------------------------------------------------
    def get_setting(self, key):
        row = self.q("SELECT value FROM settings WHERE key=?", (key,))
        return json.loads(row[0]["value"]) if row else None

    def set_setting(self, key, value):
        self.x("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, json.dumps(value)))

    def rates(self) -> dict:
        merged = copy.deepcopy(DEFAULT_RATES)
        merged.update(self.get_setting("rates") or {})
        return merged

    def company(self) -> dict:
        merged = dict(DEFAULT_COMPANY)
        merged.update(self.get_setting("company") or {})
        return merged

    # ---- users -----------------------------------------------------------
    def has_users(self) -> bool:
        return bool(self.q("SELECT 1 FROM users LIMIT 1"))

    def create_user(self, username, password, role="Admin"):
        salt = secrets.token_hex(16)
        self.x("INSERT INTO users (username, salt, pw_hash, role) VALUES (?,?,?,?)",
               (username, salt, _hash(password, salt), role))
        self.log("user.create", username)

    def verify_user(self, username, password):
        row = self.q("SELECT * FROM users WHERE username=?", (username,))
        if row and secrets.compare_digest(row[0]["pw_hash"], _hash(password, row[0]["salt"])):
            self.user = username
            self.log("login")
            return row[0]["role"]
        return None

    def change_password(self, username, password):
        salt = secrets.token_hex(16)
        self.x("UPDATE users SET salt=?, pw_hash=? WHERE username=?",
               (salt, _hash(password, salt), username))
        self.log("user.password", username)

    def users(self):
        return self.q("SELECT username, role FROM users ORDER BY username")

    # ---- employees -------------------------------------------------------
    def employees(self, include_exited=True):
        sql = "SELECT * FROM employees"
        if not include_exited:
            sql += " WHERE status='Active'"
        return self.q(sql + " ORDER BY staff_no")

    def employee(self, emp_id):
        rows = self.q("SELECT * FROM employees WHERE id=?", (emp_id,))
        return rows[0] if rows else None

    def save_employee(self, data: dict, emp_id=None) -> int:
        clean = {}
        for f in EMPLOYEE_FIELDS:
            if f not in data:
                continue
            v = data[f]
            if f in NUMERIC_EMPLOYEE_FIELDS:
                v = float(str(v).replace(",", "") or 0)
            elif f in ("disabled", "nssf_contracted_out"):
                v = 1 if str(v).strip().lower() in ("1", "true", "yes", "y") else 0
            else:
                v = (str(v).strip() if v is not None else "")
            clean[f] = v
        if not clean.get("staff_no", "x") or not clean.get("first_name", "x"):
            raise ValueError("Staff number and first name are required.")
        if emp_id:
            sets = ", ".join(f"{k}=?" for k in clean)
            self.x(f"UPDATE employees SET {sets} WHERE id=?", (*clean.values(), emp_id))
            self.log("employee.update", clean.get("staff_no", str(emp_id)))
            return emp_id
        cols = ", ".join(clean)
        marks = ", ".join("?" for _ in clean)
        cur = self.x(f"INSERT INTO employees ({cols}) VALUES ({marks})", tuple(clean.values()))
        self.log("employee.create", clean.get("staff_no", ""))
        return cur.lastrowid

    def employees_for_period(self, period):
        start, end = period_bounds(period)
        out = []
        for e in self.employees():
            hire = e["hire_date"] or ""
            exit_ = e["exit_date"] or ""
            if hire and hire > end.isoformat():
                continue
            if exit_ and exit_ < start.isoformat():
                continue
            if e["status"] != "Active" and not exit_:
                continue
            out.append(e)
        return out

    # ---- deductions ------------------------------------------------------
    def deductions(self, emp_id, active_only=False):
        sql = "SELECT * FROM deductions WHERE employee_id=?"
        if active_only:
            sql += " AND active=1"
        return self.q(sql + " ORDER BY id", (emp_id,))

    def add_deduction(self, emp_id, kind, description, installment, balance, start_period):
        self.x("INSERT INTO deductions (employee_id, kind, description, installment, balance,"
               " active, start_period) VALUES (?,?,?,?,?,1,?)",
               (emp_id, kind, description, installment, balance, start_period or None))
        self.log("deduction.add", f"emp {emp_id} {kind} {installment}")

    def set_deduction_active(self, ded_id, active):
        self.x("UPDATE deductions SET active=? WHERE id=?", (1 if active else 0, ded_id))
        self.log("deduction.toggle", f"{ded_id} -> {active}")

    # ---- monthly inputs --------------------------------------------------
    def inputs(self, emp_id, period) -> dict:
        rows = self.q("SELECT * FROM period_inputs WHERE employee_id=? AND period=?", (emp_id, period))
        if rows:
            return dict(rows[0])
        return {f: 0.0 for f in INPUT_FIELDS} | {"notes": ""}

    def save_inputs(self, emp_id, period, data: dict):
        vals = [float(str(data.get(f, 0) or 0).replace(",", "")) for f in INPUT_FIELDS]
        self.x(f"INSERT OR REPLACE INTO period_inputs (employee_id, period, {', '.join(INPUT_FIELDS)},"
               f" notes) VALUES (?,?,{','.join('?' for _ in INPUT_FIELDS)},?)",
               (emp_id, period, *vals, data.get("notes", "")))

    # ---- runs ------------------------------------------------------------
    def run_status(self, period):
        rows = self.q("SELECT status FROM runs WHERE period=?", (period,))
        return rows[0]["status"] if rows else None

    def run_lines(self, period) -> list[dict]:
        rows = self.q("SELECT data FROM run_lines WHERE period=?", (period,))
        lines = [json.loads(r["data"]) for r in rows]
        return sorted(lines, key=lambda d: d["employee"]["staff_no"])

    def periods(self):
        return [r["period"] for r in self.q("SELECT period FROM runs ORDER BY period DESC")]

    def lines_for_year(self, year: int, emp_id=None) -> list[dict]:
        rows = self.q("SELECT period, employee_id, data FROM run_lines WHERE period LIKE ? ORDER BY period",
                      (f"{year}-%",))
        return [json.loads(r["data"]) for r in rows if emp_id is None or r["employee_id"] == emp_id]

    def leave_balance(self, emp_id, year) -> tuple[float, float]:
        e = self.employee(emp_id)
        taken = self.q("SELECT COALESCE(SUM(leave_taken),0) t FROM period_inputs "
                       "WHERE employee_id=? AND period LIKE ?", (emp_id, f"{year}-%"))[0]["t"]
        entitled = float(e["leave_days_per_year"] or 21)
        return entitled, entitled - taken

    def build_input(self, e, period, rates) -> tuple[PayInput, list]:
        start, end = period_bounds(period)
        days = (end - start).days + 1
        first = max(start, date.fromisoformat(e["hire_date"])) if e["hire_date"] else start
        last = min(end, date.fromisoformat(e["exit_date"])) if e["exit_date"] else end
        proration = max(0.0, ((last - first).days + 1) / days)

        inp_row = self.inputs(e["id"], period)
        applied, deds = [], {}
        for d in self.deductions(e["id"], active_only=True):
            if d["start_period"] and d["start_period"] > period:
                continue
            amt = d["installment"] if d["balance"] is None else min(d["installment"], d["balance"])
            if amt <= 0:
                continue
            label = d["kind"] + (f" - {d['description']}" if d["description"] else "")
            deds[label] = deds.get(label, 0) + amt
            applied.append({"id": d["id"], "amount": amt})
        if inp_row["other_deductions"]:
            deds["Other (this month)"] = inp_row["other_deductions"]

        pi = PayInput(
            period=period, basic=e["basic_salary"] or 0,
            allowances={"House Allowance": e["house_allowance"] or 0,
                        "Transport Allowance": e["transport_allowance"] or 0,
                        "Other Allowance": e["other_allowance"] or 0},
            non_cash_benefits=e["non_cash_benefits"] or 0, car_benefit=e["car_benefit"] or 0,
            housing_benefit=e["housing_benefit"] or 0,
            ot_normal_hours=inp_row["ot_normal_hours"], ot_holiday_hours=inp_row["ot_holiday_hours"],
            bonus=inp_row["bonus"], arrears=inp_row["arrears"], leave_pay=inp_row["leave_pay"],
            other_earnings=inp_row["other_earnings"], absent_days=inp_row["absent_days"],
            proration=proration, voluntary_pension=e["voluntary_pension"] or 0,
            insurance_premium=e["insurance_premium"] or 0,
            mortgage_interest=e["mortgage_interest"] or 0, prmf=e["prmf"] or 0,
            disabled=bool(e["disabled"]), employment_type=e["employment_type"] or "Primary",
            nssf_contracted_out=bool(e["nssf_contracted_out"]), deductions=deds,
        )
        return pi, applied

    def run_payroll(self, period) -> tuple[list[dict], list[str]]:
        if self.run_status(period) == "Closed":
            raise ValueError(f"Payroll for {period} is closed. Reopen it first.")
        rates = self.rates()
        lines, warnings = [], []
        self.conn.execute("DELETE FROM run_lines WHERE period=?", (period,))
        for e in self.employees_for_period(period):
            pi, applied = self.build_input(e, period, rates)
            res = calculate(pi, rates)
            res["employee"] = {k: e[k] for k in e.keys()}
            res["proration"] = round(pi.proration, 4)
            res["applied_deductions"] = applied
            res["period"] = period
            res["inputs"] = self.inputs(e["id"], period)
            for w in res["warnings"]:
                warnings.append(f"{e['staff_no']} {e['first_name']} {e['last_name']}: {w}")
            if not e["kra_pin"] and pi.employment_type != "Consultant (WHT)":
                warnings.append(f"{e['staff_no']}: missing KRA PIN (required for P10).")
            self.conn.execute("INSERT INTO run_lines (period, employee_id, data) VALUES (?,?,?)",
                              (period, e["id"], json.dumps(res)))
            lines.append(res)
        self.conn.execute("INSERT OR REPLACE INTO runs (period, status, run_at, run_by) VALUES (?,?,?,?)",
                          (period, "Draft", datetime.now().isoformat(timespec="seconds"), self.user))
        self.conn.commit()
        self.log("payroll.run", f"{period}: {len(lines)} employees")
        return sorted(lines, key=lambda d: d["employee"]["staff_no"]), warnings

    def close_period(self, period):
        if self.run_status(period) != "Draft":
            raise ValueError("Run the payroll before closing it.")
        for line in self.run_lines(period):
            for a in line.get("applied_deductions", []):
                d = self.q("SELECT balance FROM deductions WHERE id=?", (a["id"],))
                if d and d[0]["balance"] is not None:
                    new_bal = round(d[0]["balance"] - a["amount"], 2)
                    self.conn.execute("UPDATE deductions SET balance=?, active=? WHERE id=?",
                                      (new_bal, 1 if new_bal > 0 else 0, a["id"]))
        self.conn.execute("UPDATE runs SET status='Closed', closed_at=?, closed_by=? WHERE period=?",
                          (datetime.now().isoformat(timespec="seconds"), self.user, period))
        self.conn.commit()
        self.log("payroll.close", period)

    def reopen_period(self, period):
        if self.run_status(period) != "Closed":
            raise ValueError("Period is not closed.")
        for line in self.run_lines(period):
            for a in line.get("applied_deductions", []):
                self.conn.execute("UPDATE deductions SET balance=balance+?, active=1 "
                                  "WHERE id=? AND balance IS NOT NULL", (a["amount"], a["id"]))
        self.conn.execute("UPDATE runs SET status='Draft' WHERE period=?", (period,))
        self.conn.commit()
        self.log("payroll.reopen", period)

    def audit(self, limit=500):
        return self.q("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,))

    def backup(self, dest_path):
        self.conn.commit()
        dest = sqlite3.connect(dest_path)
        with dest:
            self.conn.backup(dest)
        dest.close()
        self.log("backup", dest_path)
