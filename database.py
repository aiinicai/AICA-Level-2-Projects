"""
database.py
-----------
H P M S & Associates - Practice Management System

This file contains EVERYTHING related to the database:

    1. Connection handling (SQLite)
    2. Table creation (schema)
    3. Seeding of the standard CA-firm Task Master
    4. All read/write helper functions used by the application
    5. A demo-data loader for demonstration / project video

Design notes for readers of the code
------------------------------------
*  Only ONE database file is used: hpms.db (created automatically).
*  Access control is enforced HERE (in the queries), not in the UI.
   For example get_tasks_df() takes the logged-in user and, if that user
   is not an Admin, it adds "WHERE t.assigned_to = ?" to the SQL itself.
*  Money is stored as REAL (rupees). This is a practice tracker, not an
   accounting package, so simple floats are acceptable.
"""

import os
import sqlite3
from datetime import date, datetime, timedelta

import pandas as pd

# --------------------------------------------------------------------------
# Database location
# --------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "hpms.db")


def get_connection():
    """Return a SQLite connection. Rows behave like dictionaries."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def run_query(sql, params=()):
    """Run a SELECT and return the result as a pandas DataFrame."""
    conn = get_connection()
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


def execute(sql, params=()):
    """Run an INSERT / UPDATE / DELETE. Returns the last inserted row id."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def fetch_one(sql, params=()):
    """Run a SELECT and return the first row as a dict (or None)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def fetch_all(sql, params=()):
    """Run a SELECT and return all rows as a list of dicts."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# --------------------------------------------------------------------------
# Master lists used by drop-downs across the application
# --------------------------------------------------------------------------
EMPLOYEE_ROLES = [
    "Partner",
    "Manager",
    "Chartered Accountant",
    "Accountant",
    "Paid Assistant",
    "Article Assistant",
    "Audit Assistant",
    "Intern",
    "Other",
]

CLIENT_TYPES = [
    "Individual",
    "Proprietorship",
    "Partnership Firm",
    "LLP",
    "Private Limited Company",
    "Public Limited Company",
    "Trust",
    "Society",
    "Other",
]

PRIORITIES = ["Low", "Normal", "High", "Urgent"]

STATUSES = [
    "Not Started",
    "In Progress",
    "Waiting for Client",
    "Waiting for Information",
    "Under Review",
    "Query Raised",
    "On Hold",
    "Completed",
]

PROGRESS_OPTIONS = [0, 25, 50, 75, 100]

PAYMENT_MODES = ["Bank Transfer", "UPI", "Cheque", "Cash", "Other"]

FINANCIAL_YEARS = ["2023-24", "2024-25", "2025-26", "2026-27", "2027-28"]

# The standard task master of a small CA firm (category, task name)
DEFAULT_TASK_TYPES = [
    ("GST", "GSTR-1"),
    ("GST", "GSTR-3B"),
    ("GST", "GST Reconciliation"),
    ("GST", "GST Annual Return"),
    ("GST", "GST Registration"),
    ("GST", "GST Notice Reply"),
    ("Income Tax", "Income Tax Return"),
    ("Income Tax", "Tax Audit"),
    ("Income Tax", "Advance Tax Calculation"),
    ("Income Tax", "TDS Return"),
    ("Income Tax", "TDS Reconciliation"),
    ("Income Tax", "Income Tax Notice Reply"),
    ("Audit", "Statutory Audit"),
    ("Audit", "Internal Audit"),
    ("Audit", "Bank Audit"),
    ("Audit", "Stock Audit"),
    ("Audit", "Ledger Scrutiny"),
    ("Audit", "Audit Documentation"),
    ("ROC", "ROC Annual Filing"),
    ("ROC", "Financial Statement Filing"),
    ("ROC", "Director KYC"),
    ("ROC", "Other ROC Compliance"),
    ("Accounts", "Accounting"),
    ("Accounts", "Bank Reconciliation"),
    ("Accounts", "Finalisation of Accounts"),
    ("Accounts", "MIS Preparation"),
    ("Accounts", "Payroll"),
    ("Other", "Certificate Work"),
    ("Other", "Client Documentation"),
    ("Other", "DSC Work"),
    ("Other", "Client Meeting"),
    ("Other", "Other Task"),
]


# --------------------------------------------------------------------------
# 1. SCHEMA
# --------------------------------------------------------------------------
def init_db():
    """Create all tables if they do not exist and seed the task master."""
    conn = get_connection()
    cur = conn.cursor()

    # --- Login accounts -------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            email         TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role          TEXT NOT NULL,
            is_admin      INTEGER NOT NULL DEFAULT 0,
            active        INTEGER NOT NULL DEFAULT 1,
            created_at    TEXT NOT NULL
        )
    """)

    # --- Employee master (Admin adds employees here first) --------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS authorised_employees (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            name   TEXT NOT NULL,
            email  TEXT NOT NULL UNIQUE,
            role   TEXT NOT NULL,
            mobile TEXT,
            active INTEGER NOT NULL DEFAULT 1
        )
    """)

    # --- Client master --------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            client_code    TEXT NOT NULL UNIQUE,
            client_name    TEXT NOT NULL,
            pan            TEXT,
            gstin          TEXT,
            contact_person TEXT,
            mobile         TEXT,
            email          TEXT,
            client_type    TEXT,
            active         INTEGER NOT NULL DEFAULT 1
        )
    """)

    # --- Task master ----------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS task_types (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            category  TEXT NOT NULL,
            task_name TEXT NOT NULL UNIQUE,
            active    INTEGER NOT NULL DEFAULT 1
        )
    """)

    # --- Delegated tasks ------------------------------------------------
    # assigned_to  -> authorised_employees.id  (the employee master)
    # assigned_by  -> users.id                 (the admin who delegated)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id      INTEGER NOT NULL REFERENCES clients(id),
            task_type_id   INTEGER NOT NULL REFERENCES task_types(id),
            assigned_to    INTEGER NOT NULL REFERENCES authorised_employees(id),
            assigned_by    INTEGER REFERENCES users(id),
            assigned_date  TEXT NOT NULL,
            due_date       TEXT NOT NULL,
            priority       TEXT NOT NULL DEFAULT 'Normal',
            financial_year TEXT,
            instructions   TEXT,
            status         TEXT NOT NULL DEFAULT 'Not Started',
            progress       INTEGER NOT NULL DEFAULT 0,
            created_at     TEXT NOT NULL,
            updated_at     TEXT NOT NULL
        )
    """)

    # --- Task activity history (never overwritten) ----------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS task_updates (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id    INTEGER NOT NULL REFERENCES tasks(id),
            user_id    INTEGER REFERENCES users(id),
            old_status TEXT,
            new_status TEXT,
            progress   INTEGER,
            remark     TEXT,
            updated_at TEXT NOT NULL
        )
    """)

    # --- Bills ----------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id         INTEGER NOT NULL REFERENCES clients(id),
            task_id           INTEGER REFERENCES tasks(id),
            bill_number       TEXT NOT NULL UNIQUE,
            bill_date         TEXT NOT NULL,
            professional_fees REAL NOT NULL DEFAULT 0,
            gst_amount        REAL NOT NULL DEFAULT 0,
            other_charges     REAL NOT NULL DEFAULT 0,
            total_amount      REAL NOT NULL DEFAULT 0,
            due_date          TEXT,
            remarks           TEXT,
            created_by        INTEGER REFERENCES users(id)
        )
    """)

    # --- Payments (a bill may have many part-payments) ------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id          INTEGER NOT NULL REFERENCES bills(id),
            payment_date     TEXT NOT NULL,
            amount_received  REAL NOT NULL,
            payment_mode     TEXT,
            reference_number TEXT,
            remarks          TEXT,
            entered_by       INTEGER REFERENCES users(id)
        )
    """)

    # --- Collection follow-up history -----------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS collection_followups (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id       INTEGER NOT NULL REFERENCES bills(id),
            followup_date TEXT NOT NULL,
            user_id       INTEGER REFERENCES users(id),
            remark        TEXT
        )
    """)

    conn.commit()

    # --- Seed the standard task master (only the first time) ------------
    cur.execute("SELECT COUNT(*) FROM task_types")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO task_types (category, task_name, active) VALUES (?, ?, 1)",
            DEFAULT_TASK_TYPES,
        )
        conn.commit()

    conn.close()


# --------------------------------------------------------------------------
# 2. SMALL HELPERS
# --------------------------------------------------------------------------
def today_str():
    return date.today().isoformat()


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def user_count():
    row = fetch_one("SELECT COUNT(*) AS c FROM users")
    return row["c"] if row else 0


def employee_id_for_email(email):
    """Link a login account to its row in the employee master."""
    row = fetch_one(
        "SELECT id FROM authorised_employees WHERE LOWER(email) = LOWER(?)",
        (email.strip(),),
    )
    return row["id"] if row else None


# --------------------------------------------------------------------------
# 3. EMPLOYEE MASTER
# --------------------------------------------------------------------------
def add_employee(name, email, role, mobile, active=1):
    return execute(
        """INSERT INTO authorised_employees (name, email, role, mobile, active)
           VALUES (?, ?, ?, ?, ?)""",
        (name.strip(), email.strip().lower(), role, mobile, int(active)),
    )


def update_employee(emp_id, name, email, role, mobile, active):
    execute(
        """UPDATE authorised_employees
              SET name = ?, email = ?, role = ?, mobile = ?, active = ?
            WHERE id = ?""",
        (name.strip(), email.strip().lower(), role, mobile, int(active), emp_id),
    )
    # Keep the login account in step with the employee master
    execute(
        "UPDATE users SET name = ?, role = ?, active = ? WHERE LOWER(email) = LOWER(?)",
        (name.strip(), role, int(active), email.strip().lower()),
    )


def get_employees_df(only_active=False):
    sql = "SELECT * FROM authorised_employees"
    if only_active:
        sql += " WHERE active = 1"
    sql += " ORDER BY name"
    return run_query(sql)


# --------------------------------------------------------------------------
# 4. CLIENT MASTER
# --------------------------------------------------------------------------
def add_client(code, name, pan, gstin, contact, mobile, email, ctype, active=1):
    return execute(
        """INSERT INTO clients
           (client_code, client_name, pan, gstin, contact_person,
            mobile, email, client_type, active)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (code.strip().upper(), name.strip(), pan, gstin, contact,
         mobile, email, ctype, int(active)),
    )


def update_client(cid, code, name, pan, gstin, contact, mobile, email, ctype, active):
    execute(
        """UPDATE clients
              SET client_code = ?, client_name = ?, pan = ?, gstin = ?,
                  contact_person = ?, mobile = ?, email = ?,
                  client_type = ?, active = ?
            WHERE id = ?""",
        (code.strip().upper(), name.strip(), pan, gstin, contact,
         mobile, email, ctype, int(active), cid),
    )


def get_clients_df(only_active=False):
    sql = "SELECT * FROM clients"
    if only_active:
        sql += " WHERE active = 1"
    sql += " ORDER BY client_name"
    return run_query(sql)


# --------------------------------------------------------------------------
# 5. TASK MASTER
# --------------------------------------------------------------------------
def add_task_type(category, task_name):
    return execute(
        "INSERT INTO task_types (category, task_name, active) VALUES (?, ?, 1)",
        (category.strip(), task_name.strip()),
    )


def get_task_types_df(only_active=True):
    sql = "SELECT * FROM task_types"
    if only_active:
        sql += " WHERE active = 1"
    sql += " ORDER BY category, task_name"
    return run_query(sql)


# --------------------------------------------------------------------------
# 6. TASKS
# --------------------------------------------------------------------------
# The one SELECT used by every task screen. The latest remark is picked up
# with a small sub-query so that history is never overwritten.
TASK_SELECT = """
SELECT  t.id,
        t.client_id,
        c.client_code,
        c.client_name,
        t.task_type_id,
        tt.task_name,
        tt.category,
        t.assigned_to,
        e.name  AS employee_name,
        t.assigned_date,
        t.due_date,
        t.priority,
        t.financial_year,
        t.instructions,
        t.status,
        t.progress,
        t.created_at,
        t.updated_at,
        (SELECT tu.remark FROM task_updates tu
          WHERE tu.task_id = t.id AND IFNULL(tu.remark, '') <> ''
          ORDER BY tu.id DESC LIMIT 1)      AS latest_remark,
        (SELECT tu.updated_at FROM task_updates tu
          WHERE tu.task_id = t.id
          ORDER BY tu.id DESC LIMIT 1)      AS last_update_at
  FROM tasks t
  JOIN clients    c  ON c.id  = t.client_id
  JOIN task_types tt ON tt.id = t.task_type_id
  JOIN authorised_employees e ON e.id = t.assigned_to
"""


def create_task(client_id, task_type_id, assigned_to, assigned_by, assigned_date,
                due_date, priority, financial_year, instructions):
    task_id = execute(
        """INSERT INTO tasks
           (client_id, task_type_id, assigned_to, assigned_by, assigned_date,
            due_date, priority, financial_year, instructions,
            status, progress, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Not Started', 0, ?, ?)""",
        (client_id, task_type_id, assigned_to, assigned_by, assigned_date,
         due_date, priority, financial_year, instructions, now_str(), now_str()),
    )
    # First entry of the activity history
    execute(
        """INSERT INTO task_updates
           (task_id, user_id, old_status, new_status, progress, remark, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (task_id, assigned_by, None, "Not Started", 0, "Task delegated.", now_str()),
    )
    return task_id


def get_tasks_df(user, task_id=None, employee_id=None):
    """
    Return tasks as a DataFrame.

    ACCESS CONTROL: if the logged-in user is not an Admin, the WHERE clause
    itself restricts rows to that employee's own tasks. The restriction is
    therefore applied in the database, not by hiding parts of the screen.
    """
    sql = TASK_SELECT
    where = []
    params = []

    if not user.get("is_admin"):
        where.append("t.assigned_to = ?")
        params.append(user.get("employee_id") or -1)
    elif employee_id:
        where.append("t.assigned_to = ?")
        params.append(employee_id)

    if task_id:
        where.append("t.id = ?")
        params.append(task_id)

    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY (t.status = 'Completed'), t.due_date"
    return run_query(sql, tuple(params))


def get_task(user, task_id):
    """Fetch a single task, respecting the same access rules."""
    df = get_tasks_df(user, task_id=task_id)
    return None if df.empty else df.iloc[0].to_dict()


def update_task_progress(user, task_id, new_status, progress, remark):
    """
    Save a status/progress/remark update and append to the history.
    Returns False if the user is not allowed to touch this task.
    """
    task = get_task(user, task_id)          # access check happens here
    if task is None:
        return False

    # Marking a task Completed always forces progress to 100%
    if new_status == "Completed":
        progress = 100

    execute(
        "UPDATE tasks SET status = ?, progress = ?, updated_at = ? WHERE id = ?",
        (new_status, int(progress), now_str(), task_id),
    )
    execute(
        """INSERT INTO task_updates
           (task_id, user_id, old_status, new_status, progress, remark, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (task_id, user.get("id"), task["status"], new_status,
         int(progress), remark.strip(), now_str()),
    )
    return True


def reassign_task(task_id, new_employee_id, admin_user, remark=""):
    old = fetch_one(
        """SELECT e.name AS emp FROM tasks t
             JOIN authorised_employees e ON e.id = t.assigned_to
            WHERE t.id = ?""", (task_id,))
    new = fetch_one("SELECT name FROM authorised_employees WHERE id = ?",
                    (new_employee_id,))
    execute("UPDATE tasks SET assigned_to = ?, updated_at = ? WHERE id = ?",
            (new_employee_id, now_str(), task_id))
    note = f"Task reassigned from {old['emp']} to {new['name']}."
    if remark:
        note += " " + remark
    execute(
        """INSERT INTO task_updates
           (task_id, user_id, old_status, new_status, progress, remark, updated_at)
           VALUES (?, ?, NULL, NULL, NULL, ?, ?)""",
        (task_id, admin_user.get("id"), note, now_str()),
    )


def get_task_history_df(user, task_id):
    """Full activity history of one task (access-checked)."""
    if get_task(user, task_id) is None:
        return pd.DataFrame()
    return run_query(
        """SELECT tu.updated_at, IFNULL(u.name, 'System') AS user_name,
                  tu.old_status, tu.new_status, tu.progress, tu.remark
             FROM task_updates tu
             LEFT JOIN users u ON u.id = tu.user_id
            WHERE tu.task_id = ?
            ORDER BY tu.id""",
        (task_id,),
    )


# --------------------------------------------------------------------------
# 7. BILLING
# --------------------------------------------------------------------------
BILL_SELECT = """
SELECT  b.id,
        b.client_id,
        c.client_code,
        c.client_name,
        b.task_id,
        IFNULL(tt.task_name, '-')            AS task_name,
        b.bill_number,
        b.bill_date,
        b.professional_fees,
        b.gst_amount,
        b.other_charges,
        b.total_amount,
        b.due_date,
        b.remarks,
        IFNULL((SELECT SUM(p.amount_received) FROM payments p
                 WHERE p.bill_id = b.id), 0) AS received
  FROM bills b
  JOIN clients c ON c.id = b.client_id
  LEFT JOIN tasks t       ON t.id  = b.task_id
  LEFT JOIN task_types tt ON tt.id = t.task_type_id
"""


def payment_status(total, received):
    """The three payment states required by the specification."""
    if received <= 0:
        return "Unpaid"
    if received < total:
        return "Partially Paid"
    return "Paid"


def get_bills_df(client_id=None):
    sql = BILL_SELECT
    params = ()
    if client_id:
        sql += " WHERE b.client_id = ?"
        params = (client_id,)
    sql += " ORDER BY b.bill_date DESC, b.id DESC"
    df = run_query(sql, params)
    if df.empty:
        df["outstanding"] = []
        df["payment_status"] = []
        return df
    df["outstanding"] = (df["total_amount"] - df["received"]).round(2)
    df["payment_status"] = df.apply(
        lambda r: payment_status(r["total_amount"], r["received"]), axis=1)
    return df


def add_bill(client_id, task_id, bill_number, bill_date, fees, gst,
             other, due_date, remarks, created_by):
    total = round(float(fees) + float(gst) + float(other), 2)
    return execute(
        """INSERT INTO bills
           (client_id, task_id, bill_number, bill_date, professional_fees,
            gst_amount, other_charges, total_amount, due_date, remarks, created_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (client_id, task_id, bill_number.strip(), bill_date, float(fees),
         float(gst), float(other), total, due_date, remarks, created_by),
    )


def add_payment(bill_id, payment_date, amount, mode, reference, remarks, entered_by):
    return execute(
        """INSERT INTO payments
           (bill_id, payment_date, amount_received, payment_mode,
            reference_number, remarks, entered_by)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (bill_id, payment_date, float(amount), mode, reference, remarks, entered_by),
    )


def get_payments_df(bill_id=None):
    sql = """SELECT p.*, b.bill_number, c.client_name
               FROM payments p
               JOIN bills b   ON b.id = p.bill_id
               JOIN clients c ON c.id = b.client_id"""
    params = ()
    if bill_id:
        sql += " WHERE p.bill_id = ?"
        params = (bill_id,)
    sql += " ORDER BY p.payment_date, p.id"
    return run_query(sql, params)


def add_followup(bill_id, followup_date, user_id, remark):
    return execute(
        """INSERT INTO collection_followups (bill_id, followup_date, user_id, remark)
           VALUES (?, ?, ?, ?)""",
        (bill_id, followup_date, user_id, remark.strip()),
    )


def get_followups_df(bill_id=None):
    sql = """SELECT f.followup_date, b.bill_number, c.client_name,
                    IFNULL(u.name, 'System') AS user_name, f.remark
               FROM collection_followups f
               JOIN bills b   ON b.id = f.bill_id
               JOIN clients c ON c.id = b.client_id
               LEFT JOIN users u ON u.id = f.user_id"""
    params = ()
    if bill_id:
        sql += " WHERE f.bill_id = ?"
        params = (bill_id,)
    sql += " ORDER BY f.followup_date DESC, f.id DESC"
    return run_query(sql, params)


def get_completed_not_billed_df():
    """
    The important business exception:
    task is Completed but no bill has been raised against it.
    """
    return run_query("""
        SELECT t.id, c.client_name, tt.task_name, e.name AS employee_name,
               t.due_date, t.updated_at
          FROM tasks t
          JOIN clients c  ON c.id  = t.client_id
          JOIN task_types tt ON tt.id = t.task_type_id
          JOIN authorised_employees e ON e.id = t.assigned_to
         WHERE t.status = 'Completed'
           AND t.id NOT IN (SELECT task_id FROM bills WHERE task_id IS NOT NULL)
         ORDER BY t.updated_at DESC
    """)


# --------------------------------------------------------------------------
# 8. DEMO DATA
# --------------------------------------------------------------------------
def load_demo_data():
    """
    Populate the database with fictional demonstration data.
    Safe to call only on an (almost) empty database - it refuses to run
    if clients already exist, so real data is never disturbed.
    """
    import auth  # imported here to avoid a circular import at module load

    if not get_clients_df().empty:
        return False, "Demo data not loaded: clients already exist in the database."

    init_db()
    today = date.today()

    def d(offset):
        return (today + timedelta(days=offset)).isoformat()

    # ---- Admin account -------------------------------------------------
    admin = fetch_one("SELECT * FROM users WHERE is_admin = 1")
    if admin is None:
        auth.signup("CA Harshad Mehta-Patel", "admin@hpms.in", "admin123")
        admin = fetch_one("SELECT * FROM users WHERE is_admin = 1")
    admin_id = admin["id"]

    # ---- 8 employees ---------------------------------------------------
    employees = [
        ("Rahul Deshmukh", "rahul@hpms.in", "Chartered Accountant", "9820011001"),
        ("Sneha Iyer", "sneha@hpms.in", "Manager", "9820011002"),
        ("Amit Kulkarni", "amit@hpms.in", "Audit Assistant", "9820011003"),
        ("Priya Nair", "priya@hpms.in", "Article Assistant", "9820011004"),
        ("Vikram Shah", "vikram@hpms.in", "Paid Assistant", "9820011005"),
        ("Neha Joshi", "neha@hpms.in", "Accountant", "9820011006"),
        ("Karan Malhotra", "karan@hpms.in", "Article Assistant", "9820011007"),
        ("Divya Rao", "divya@hpms.in", "Intern", "9820011008"),
    ]
    emp_ids = {}
    for name, email, role, mobile in employees:
        existing = fetch_one("SELECT id FROM authorised_employees WHERE email = ?", (email,))
        emp_ids[name] = existing["id"] if existing else add_employee(name, email, role, mobile)
        # Give every demo employee a login account (password: demo123)
        if fetch_one("SELECT id FROM users WHERE email = ?", (email,)) is None:
            auth.signup(name, email, "demo123")

    user_id_of = {}
    for name, email, _r, _m in employees:
        u = fetch_one("SELECT id FROM users WHERE email = ?", (email,))
        user_id_of[name] = u["id"] if u else admin_id

    # ---- 10 clients ----------------------------------------------------
    clients = [
        ("C001", "ABC Traders Pvt Ltd", "AABCA1234K", "27AABCA1234K1Z5",
         "Mr. Anil Bhatia", "9821001001", "accounts@abctraders.in", "Private Limited Company"),
        ("C002", "Shree Ganesh Enterprises", "AAFPS5678L", "27AAFPS5678L1ZP",
         "Mr. Ganesh Patil", "9821001002", "ganesh@sgent.in", "Proprietorship"),
        ("C003", "Nirmal Textiles LLP", "AAGFN9012M", "27AAGFN9012M1ZQ",
         "Ms. Nirmala Shetty", "9821001003", "info@nirmaltex.in", "LLP"),
        ("C004", "Sunrise Infra Partners", "AAHFS3456N", "27AAHFS3456N1ZR",
         "Mr. Suresh Rane", "9821001004", "suresh@sunriseinfra.in", "Partnership Firm"),
        ("C005", "Mr. Rajesh Kapoor", "AKLPK7890P", "",
         "Mr. Rajesh Kapoor", "9821001005", "rajesh.kapoor@example.in", "Individual"),
        ("C006", "Vidya Education Trust", "AAATV2345Q", "",
         "Dr. Meena Sharma", "9821001006", "trust@vidyaedu.in", "Trust"),
        ("C007", "Metro Retail Ltd", "AABCM6789R", "27AABCM6789R1ZS",
         "Mr. Deepak Verma", "9821001007", "finance@metroretail.in", "Public Limited Company"),
        ("C008", "Krishna Agro Industries", "AAECK0123S", "27AAECK0123S1ZT",
         "Mr. Mohan Yadav", "9821001008", "mohan@krishnaagro.in", "Private Limited Company"),
        ("C009", "Sahyadri Welfare Society", "AAATS4567T", "",
         "Mr. Prakash Jadhav", "9821001009", "society@sahyadri.org", "Society"),
        ("C010", "TechNova Solutions Pvt Ltd", "AABCT8901U", "27AABCT8901U1ZU",
         "Ms. Ritu Menon", "9821001010", "ritu@technova.in", "Private Limited Company"),
    ]
    client_ids = {}
    for code, name, pan, gstin, contact, mobile, email, ctype in clients:
        client_ids[name] = add_client(code, name, pan, gstin, contact, mobile, email, ctype)

    def task_type_id(task_name):
        row = fetch_one("SELECT id FROM task_types WHERE task_name = ?", (task_name,))
        return row["id"]

    # ---- 30 tasks covering every situation -----------------------------
    # (client, task, employee, due-date offset, priority, status, progress, remark)
    tasks = [
        # --- Overdue work (red) ---
        ("ABC Traders Pvt Ltd", "Tax Audit", "Rahul Deshmukh", -12, "Urgent",
         "In Progress", 50, "Audit fieldwork going on, few ledgers pending."),
        ("Nirmal Textiles LLP", "GSTR-3B", "Neha Joshi", -6, "High",
         "Waiting for Client", 25, "Purchase register awaited from client."),
        ("Metro Retail Ltd", "Stock Audit", "Amit Kulkarni", -3, "High",
         "Query Raised", 50, "Stock sheet difference of Rs. 1.2 lakh raised with client."),
        ("Sunrise Infra Partners", "TDS Return", "Vikram Shah", -20, "Normal",
         "On Hold", 25, "Challan details not provided, work kept on hold."),
        # --- Due today (orange) ---
        ("Shree Ganesh Enterprises", "GSTR-1", "Neha Joshi", 0, "Urgent",
         "In Progress", 75, "Sales data uploaded, final check pending."),
        ("TechNova Solutions Pvt Ltd", "Advance Tax Calculation", "Sneha Iyer", 0, "High",
         "Under Review", 75, "Computation prepared, sent to Partner for review."),
        # --- Upcoming within 7 days ---
        ("Krishna Agro Industries", "GST Reconciliation", "Priya Nair", 3, "Normal",
         "In Progress", 50, "2B vs purchase register matching in progress."),
        ("ABC Traders Pvt Ltd", "ROC Annual Filing", "Karan Malhotra", 5, "Normal",
         "Not Started", 0, None),
        ("Vidya Education Trust", "Income Tax Return", "Sneha Iyer", 6, "High",
         "Waiting for Information", 25, "Donation details awaited from trustee."),
        ("Mr. Rajesh Kapoor", "Income Tax Return", "Priya Nair", 7, "Normal",
         "In Progress", 25, "Form 26AS downloaded, capital gain working pending."),
        # --- Later ---
        ("Metro Retail Ltd", "Statutory Audit", "Rahul Deshmukh", 25, "High",
         "In Progress", 25, "Planning memorandum prepared."),
        ("Nirmal Textiles LLP", "Finalisation of Accounts", "Neha Joshi", 18, "Normal",
         "Not Started", 0, None),
        ("Sahyadri Welfare Society", "Accounting", "Divya Rao", 14, "Low",
         "In Progress", 50, "Bank entries posted up to July."),
        ("Krishna Agro Industries", "Bank Reconciliation", "Divya Rao", 10, "Low",
         "Not Started", 0, None),
        ("TechNova Solutions Pvt Ltd", "Payroll", "Neha Joshi", 9, "Normal",
         "In Progress", 50, "Salary sheet prepared for August."),
        ("Sunrise Infra Partners", "GST Notice Reply", "Sneha Iyer", 12, "Urgent",
         "Waiting for Client", 25, "Supporting invoices requested from client."),
        ("Shree Ganesh Enterprises", "Director KYC", "Karan Malhotra", 20, "Low",
         "Not Started", 0, None),
        ("ABC Traders Pvt Ltd", "Bank Reconciliation", "Vikram Shah", 15, "Normal",
         "In Progress", 75, "Only two entries remain unmatched."),
        ("Vidya Education Trust", "Certificate Work", "Amit Kulkarni", 11, "Normal",
         "Under Review", 75, "Certificate drafted, partner signature pending."),
        ("Mr. Rajesh Kapoor", "DSC Work", "Divya Rao", 8, "Low",
         "Waiting for Client", 0, "Client to visit office for video verification."),
        # --- Completed AND billed ---
        ("ABC Traders Pvt Ltd", "GSTR-1", "Neha Joshi", -30, "Normal",
         "Completed", 100, "Return filed, ARN shared with client."),
        ("Metro Retail Ltd", "TDS Return", "Vikram Shah", -25, "Normal",
         "Completed", 100, "24Q filed and FVU acknowledgement saved."),
        ("Nirmal Textiles LLP", "Tax Audit", "Rahul Deshmukh", -40, "High",
         "Completed", 100, "3CD uploaded and accepted by client."),
        ("TechNova Solutions Pvt Ltd", "Income Tax Return", "Sneha Iyer", -35, "Normal",
         "Completed", 100, "ITR-6 filed and verified."),
        ("Krishna Agro Industries", "ROC Annual Filing", "Karan Malhotra", -28, "Normal",
         "Completed", 100, "AOC-4 and MGT-7 filed."),
        ("Shree Ganesh Enterprises", "Accounting", "Divya Rao", -22, "Low",
         "Completed", 100, "Books finalised for the year."),
        ("Sunrise Infra Partners", "Bank Reconciliation", "Vikram Shah", -18, "Low",
         "Completed", 100, "BRS completed for all four bank accounts."),
        # --- Completed but NOT billed (billing pending) ---
        ("Sahyadri Welfare Society", "Income Tax Return", "Priya Nair", -9, "Normal",
         "Completed", 100, "ITR-7 filed. Bill yet to be raised."),
        ("Mr. Rajesh Kapoor", "Advance Tax Calculation", "Priya Nair", -5, "Normal",
         "Completed", 100, "Advance tax challan paid by client."),
        ("Vidya Education Trust", "Audit Documentation", "Amit Kulkarni", -2, "Normal",
         "Completed", 100, "Audit file completed and indexed."),
    ]

    task_ids = {}
    for cl, tk, emp, offset, prio, status, progress, remark in tasks:
        fy = "2026-27" if offset >= -15 else "2025-26"
        tid = create_task(
            client_ids[cl], task_type_id(tk), emp_ids[emp], admin_id,
            d(min(offset - 20, -5)), d(offset), prio, fy,
            f"{tk} for {cl}. Please complete before the due date.",
        )
        task_ids[(cl, tk)] = tid

        if status != "Not Started" or remark:
            execute("UPDATE tasks SET status = ?, progress = ?, updated_at = ? WHERE id = ?",
                    (status, progress, now_str(), tid))
            uid = user_id_of.get(emp, admin_id)
            # A short, realistic activity trail
            execute(
                """INSERT INTO task_updates
                   (task_id, user_id, old_status, new_status, progress, remark, updated_at)
                   VALUES (?, ?, 'Not Started', 'In Progress', 25, ?, ?)""",
                (tid, uid, "Data received from client.", now_str()),
            )
            if status != "In Progress" or progress != 25:
                execute(
                    """INSERT INTO task_updates
                       (task_id, user_id, old_status, new_status, progress, remark, updated_at)
                       VALUES (?, ?, 'In Progress', ?, ?, ?, ?)""",
                    (tid, uid, status, progress,
                     remark or "Work in progress.", now_str()),
                )

    # ---- 10 bills ------------------------------------------------------
    # (client, task, bill no, bill-date offset, fees, gst, other, due offset)
    bills = [
        ("ABC Traders Pvt Ltd", ("ABC Traders Pvt Ltd", "GSTR-1"),
         "HPMS/26-27/001", -28, 8000, 1440, 0, -13),
        ("Metro Retail Ltd", ("Metro Retail Ltd", "TDS Return"),
         "HPMS/26-27/002", -24, 12000, 2160, 500, -9),
        ("Nirmal Textiles LLP", ("Nirmal Textiles LLP", "Tax Audit"),
         "HPMS/26-27/003", -38, 50000, 9000, 0, -23),
        ("TechNova Solutions Pvt Ltd", ("TechNova Solutions Pvt Ltd", "Income Tax Return"),
         "HPMS/26-27/004", -33, 25000, 4500, 0, -18),
        ("Krishna Agro Industries", ("Krishna Agro Industries", "ROC Annual Filing"),
         "HPMS/26-27/005", -26, 15000, 2700, 1000, -11),
        ("Shree Ganesh Enterprises", ("Shree Ganesh Enterprises", "Accounting"),
         "HPMS/26-27/006", -20, 18000, 3240, 0, 10),
        ("Sunrise Infra Partners", ("Sunrise Infra Partners", "Bank Reconciliation"),
         "HPMS/26-27/007", -16, 9000, 1620, 0, 14),
        ("ABC Traders Pvt Ltd", ("ABC Traders Pvt Ltd", "Tax Audit"),
         "HPMS/26-27/008", -10, 60000, 10800, 2000, 20),
        ("Metro Retail Ltd", None,
         "HPMS/26-27/009", -6, 20000, 3600, 0, 24),
        ("Vidya Education Trust", None,
         "HPMS/26-27/010", -2, 11000, 1980, 0, 28),
    ]
    bill_ids = {}
    for cl, tkey, bno, boff, fees, gst, other, doff in bills:
        tid = task_ids.get(tkey) if tkey else None
        bill_ids[bno] = add_bill(client_ids[cl], tid, bno, d(boff),
                                 fees, gst, other, d(doff),
                                 "Professional fees bill.", admin_id)

    # ---- Payments: full, part and nil ----------------------------------
    payments = [
        # Fully paid
        ("HPMS/26-27/001", -20, 9440, "Bank Transfer", "NEFT/8891", "Full payment received."),
        ("HPMS/26-27/003", -30, 30000, "Bank Transfer", "RTGS/1201", "First instalment."),
        ("HPMS/26-27/003", -18, 29000, "Cheque", "CHQ 445671", "Balance received."),
        ("HPMS/26-27/006", -12, 21240, "UPI", "UPI/7781", "Full payment received."),
        # Partially paid
        ("HPMS/26-27/002", -15, 6000, "UPI", "UPI/5567", "Part payment received."),
        ("HPMS/26-27/004", -20, 15000, "Bank Transfer", "NEFT/3345", "Part payment."),
        ("HPMS/26-27/005", -10, 5000, "Cash", "", "Part payment against ROC bill."),
        ("HPMS/26-27/008", -4, 25000, "Bank Transfer", "NEFT/9902", "Advance against tax audit."),
        # Bills 007, 009, 010 remain fully unpaid
    ]
    for bno, poff, amt, mode, ref, rmk in payments:
        add_payment(bill_ids[bno], d(poff), amt, mode, ref, rmk, admin_id)

    # ---- Collection follow-up history ----------------------------------
    followups = [
        ("HPMS/26-27/002", -8, "Called client - balance payment expected on Monday."),
        ("HPMS/26-27/002", -3, "Bill resent to accounts department."),
        ("HPMS/26-27/004", -12, "Rs. 15,000 received, balance promised next week."),
        ("HPMS/26-27/005", -5, "Partner follow-up required, client not responding."),
        ("HPMS/26-27/007", -2, "Reminder e-mail sent along with bill copy."),
    ]
    for bno, foff, remark in followups:
        add_followup(bill_ids[bno], d(foff), admin_id, remark)

    msg = ("Demo data loaded.\n\n"
           "Admin login  : admin@hpms.in / admin123\n"
           "Employee demo: rahul@hpms.in / demo123 (all employees use demo123)")
    return True, msg


def reset_database():
    """Delete the database file completely (used by the Reset button)."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()


# --------------------------------------------------------------------------
# Allow "python database.py --demo" from the command line
# --------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    init_db()
    if "--reset" in sys.argv:
        reset_database()
        print("Database reset.")
    if "--demo" in sys.argv:
        ok, message = load_demo_data()
        print(message)
    else:
        print(f"Database ready at {DB_PATH}")
