"""
Audit Findings Tracker  (AICA Level 2 capstone project)
=======================================================

A Streamlit web app that follows up outstanding internal and external audit
findings across 14 departments until Internal Audit verifies closure.

Run it (after installing the requirements):

    streamlit run app.py

ONE CODE FILE, TWO VARIANTS.  Nothing in this file has to be edited to move
from the Gmail test version to the Microsoft 365 intranet version.  Only
settings change (environment variables, or the .streamlit/secrets.toml file):

    DATABASE_URL   empty            -> local SQLite file (default, easiest test)
                   postgresql://... -> Supabase / PostgreSQL / company server
    EMAIL_MODE     log    -> nothing is sent, emails are only written to the
                             email log (safe default for first tests)
                   gmail  -> Gmail SMTP with an app password (Variant A)
                   smtp   -> any SMTP server / relay, e.g. company Exchange
                   graph  -> Microsoft 365 via Microsoft Graph (Variant B)

All other settings are listed in secrets.toml.example.

The application logic (database, permissions, ageing, rounds, reminders,
e-mail, Excel import/export, sample data) is written without any Streamlit
code so that it can be tested on its own (see tests/test_core.py).  The
Streamlit screens are at the bottom of the file.
"""

import base64
import hashlib
import hmac
import io
import os
import random
import re
import secrets
import smtplib
import sqlite3
import ssl
from collections import defaultdict
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from email.message import EmailMessage

import pandas as pd

try:  # Streamlit is only needed for the screens, not for the core logic
    import streamlit as st
except ImportError:  # pragma: no cover
    st = None


# =============================================================================
# 1.  FIXED LISTS AND DEFINITIONS
# =============================================================================

APP_TITLE = "Audit Findings Tracker"

DEPARTMENTS = [
    "Branch 1", "Branch 2", "Branch 3", "Branch 4", "Branch 5",
    "Compliance, Recovery and Legal", "Finance", "HR", "AQM", "Marketing",
    "IT", "Risk", "Credit", "Corporate",
]

STATUSES = ["Open", "Ongoing", "Closed"]
STATUS_DEFINITIONS = {
    "Open": "No action has started, or no response was received by the follow-up date.",
    "Ongoing": "Implementation has started or is partly done, with a revised date, "
               "but is not yet fully in place.",
    "Closed": "The recommendation is fully implemented and evidence is on file. "
              "For the auditor status, Internal Audit has also verified it.",
}
RISK_LEVELS = ["High", "Medium", "Low"]
SOURCES = ["In-house", "External auditor"]

ROLE_ADMIN = "Audit Admin"
ROLE_OWNER = "Department Owner"
ROLE_MGMT = "Management"

ROUND_QUARTERLY = "Quarterly"
ROUND_MONTHLY = "Monthly (High risk only)"
ROUND_KINDS = [ROUND_QUARTERLY, ROUND_MONTHLY]

AGEING_BUCKETS = ["Not yet due", "1-30 days", "31-60 days", "61-90 days", "Over 90 days"]

# The 14 columns of the Excel file that the audit team imports, in this order.
MASTER_COLUMNS = [
    "Serial number", "Year reported", "In-house or external auditor", "Quarter",
    "Report name", "Department", "Observation", "Heading of the observation",
    "Detailed observation", "Risk implication", "Recommendation",
    "Management response", "Risk level", "Original target date",
]
# Excel column name -> database field name
COLUMN_TO_FIELD = {
    "Serial number": "serial_no",
    "Year reported": "year_reported",
    "In-house or external auditor": "source",
    "Quarter": "quarter",
    "Report name": "report_name",
    "Department": "department",
    "Observation": "observation_ref",
    "Heading of the observation": "heading",
    "Detailed observation": "detailed_observation",
    "Risk implication": "risk_implication",
    "Recommendation": "recommendation",
    "Management response": "initial_management_response",
    "Risk level": "risk_level",
    "Original target date": "original_target_date",
}
FIELD_TO_COLUMN = {v: k for k, v in COLUMN_TO_FIELD.items()}
FINDING_FIELDS = list(COLUMN_TO_FIELD.values())

MAX_EVIDENCE_BYTES = 5 * 1024 * 1024  # 5 MB per evidence file


# =============================================================================
# 2.  SETTINGS, SMALL HELPERS
# =============================================================================

def get_setting(name, default=""):
    """Read a setting: environment variable first, then Streamlit secrets."""
    value = os.environ.get(name)
    if value not in (None, ""):
        return value
    if st is not None:
        try:
            if name in st.secrets:
                return str(st.secrets[name])
        except Exception:
            pass
    return default


def setting_bool(name, default=False):
    return str(get_setting(name, "true" if default else "false")).strip().lower() in (
        "1", "true", "yes", "on")


def setting_int(name, default):
    try:
        return int(get_setting(name, str(default)))
    except ValueError:
        return default


def slug(text):
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def parse_date(value):
    """Turn many date formats (Excel dates, text) into a date, or None."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, datetime):  # includes pandas Timestamp
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d-%b-%Y", "%d %b %Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    parsed = pd.to_datetime(text, dayfirst=True, errors="coerce")
    return None if pd.isna(parsed) else parsed.date()


def iso(value):
    return value.isoformat() if value else None


def clean_text(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


# =============================================================================
# 3.  DATABASE  (SQLite by default, PostgreSQL / Supabase by setting)
# =============================================================================

class Database:
    """Tiny wrapper so the same SQL runs on SQLite and PostgreSQL."""

    def __init__(self, url=None, sqlite_path=None):
        self.url = url if url is not None else get_setting("DATABASE_URL", "")
        self.is_pg = self.url.startswith(("postgres://", "postgresql://"))
        self.sqlite_path = sqlite_path or get_setting("SQLITE_PATH", "audit_tracker.db")

    def _connect(self):
        if self.is_pg:
            import psycopg2
            import psycopg2.extras
            return psycopg2.connect(self.url, cursor_factory=psycopg2.extras.RealDictCursor)
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def session(self):
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute(self, conn, sql, params=()):
        if self.is_pg:
            cur = conn.cursor()
            cur.execute(sql.replace("?", "%s"), params)
            return cur
        return conn.execute(sql, params)

    def insert(self, conn, sql, params=()):
        """Run an INSERT and return the new row id."""
        cur = self.execute(conn, sql + " RETURNING id", params)
        return cur.fetchall()[0]["id"]

    def fetch(self, sql, params=(), conn=None):
        """Run a SELECT and return a list of plain dictionaries."""
        if conn is not None:
            return [dict(r) for r in self.execute(conn, sql, params).fetchall()]
        with self.session() as c:
            return [dict(r) for r in self.execute(c, sql, params).fetchall()]


def schema_statements(is_pg):
    pk = "SERIAL PRIMARY KEY" if is_pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
    return [
        f"""CREATE TABLE IF NOT EXISTS users (
            id {pk}, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
            role TEXT NOT NULL, department TEXT, email TEXT, active INTEGER DEFAULT 1)""",
        """CREATE TABLE IF NOT EXISTS departments (
            name TEXT PRIMARY KEY, head_email TEXT)""",
        f"""CREATE TABLE IF NOT EXISTS findings (
            id {pk}, serial_no TEXT NOT NULL UNIQUE, year_reported TEXT, source TEXT,
            quarter TEXT, report_name TEXT, department TEXT NOT NULL, observation_ref TEXT,
            heading TEXT, detailed_observation TEXT, risk_implication TEXT,
            recommendation TEXT, initial_management_response TEXT, risk_level TEXT,
            original_target_date TEXT, created_at TEXT)""",
        f"""CREATE TABLE IF NOT EXISTS rounds (
            id {pk}, kind TEXT, follow_up_date TEXT, response_due_date TEXT,
            created_by TEXT, created_at TEXT)""",
        f"""CREATE TABLE IF NOT EXISTS followups (
            id {pk}, finding_id INTEGER NOT NULL, round_id INTEGER, follow_up_date TEXT,
            response_due_date TEXT, mgmt_status TEXT, mgmt_response TEXT,
            revised_target_date TEXT, mgmt_updated_on TEXT, mgmt_updated_by TEXT,
            auditor_status TEXT, auditor_remarks TEXT, auditor_reviewed_on TEXT,
            auditor_reviewed_by TEXT, reminder_sent_on TEXT, escalation_sent_on TEXT)""",
        f"""CREATE TABLE IF NOT EXISTS evidence (
            id {pk}, followup_id INTEGER NOT NULL, filename TEXT, content_b64 TEXT,
            uploaded_by TEXT, uploaded_on TEXT)""",
        f"""CREATE TABLE IF NOT EXISTS audit_trail (
            id {pk}, ts TEXT, username TEXT, action TEXT, table_name TEXT,
            record_id TEXT, field TEXT, old_value TEXT, new_value TEXT)""",
        f"""CREATE TABLE IF NOT EXISTS email_log (
            id {pk}, ts TEXT, mode TEXT, to_addr TEXT, cc_addr TEXT, subject TEXT,
            status TEXT, detail TEXT)""",
    ]


def init_db(db):
    """Create the tables and, on first run, the departments and the 30 users."""
    with db.session() as conn:
        for stmt in schema_statements(db.is_pg):
            db.execute(conn, stmt)
        for dept in DEPARTMENTS:
            if not db.execute(conn, "SELECT 1 AS x FROM departments WHERE name = ?", (dept,)).fetchone():
                db.execute(conn, "INSERT INTO departments (name, head_email) VALUES (?, ?)",
                           (dept, f"head.{slug(dept)}@example.com"))
        count = db.execute(conn, "SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        if count == 0:
            password = get_setting("DEFAULT_PASSWORD", "Test@123")
            for username, role, dept, email in default_users():
                db.execute(
                    conn,
                    "INSERT INTO users (username, password_hash, role, department, email, active) "
                    "VALUES (?, ?, ?, ?, ?, 1)",
                    (username, hash_password(password), role, dept, email))


def default_users():
    """Audit Admin, Management and two users per department ('Credit 1', 'Credit 2'...)."""
    users = [
        ("Audit Admin", ROLE_ADMIN, None, "audit.admin@example.com"),
        ("Management", ROLE_MGMT, None, "management@example.com"),
    ]
    for dept in DEPARTMENTS:
        for number in (1, 2):
            users.append((f"{dept} {number}", ROLE_OWNER, dept, f"{slug(dept)}{number}@example.com"))
    return users


# =============================================================================
# 4.  LOGIN, PASSWORDS, PERMISSIONS, AUDIT TRAIL
# =============================================================================

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 100_000)
    return f"{salt}${digest.hex()}"


def check_password(password, stored):
    try:
        salt, digest = stored.split("$")
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt).split("$")[1], digest)


def authenticate(db, username, password):
    """Return the user as a dict if username and password are right, else None.
    The username match ignores capital letters, spaces and commas."""
    wanted = slug(username)
    if not wanted:
        return None
    for row in db.fetch("SELECT * FROM users WHERE active = 1"):
        if slug(row["username"]) == wanted and check_password(password, row["password_hash"]):
            return {"id": row["id"], "username": row["username"], "role": row["role"],
                    "department": row["department"], "email": row["email"]}
    return None


def require_role(user, *roles):
    if not user or user.get("role") not in roles:
        raise PermissionError("You do not have permission to do this.")


def log_change(db, conn, username, action, table, record_id, field=None, old=None, new=None):
    db.execute(
        conn,
        "INSERT INTO audit_trail (ts, username, action, table_name, record_id, field, old_value, new_value) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (now_iso(), username, action, table, str(record_id), field,
         None if old is None else str(old), None if new is None else str(new)))


# =============================================================================
# 5.  FINDINGS: IMPORT FROM EXCEL, ADD, EDIT
# =============================================================================

def _norm_col(name):
    return re.sub(r"\s+", " ", str(name)).strip().lower()


def match_department(value):
    key = slug(value)
    for dept in DEPARTMENTS:
        if slug(dept) == key:
            return dept
    return None


def import_findings(db, df, username):
    """Import a DataFrame with the 14 agreed columns.
    Returns {"inserted": n, "skipped": n, "errors": [(excel_row, message), ...]}.
    Rows with a problem are skipped and reported; good rows are still imported."""
    wanted = {_norm_col(c): c for c in MASTER_COLUMNS}
    renamed = {}
    for col in df.columns:
        if _norm_col(col) in wanted:
            renamed[col] = wanted[_norm_col(col)]
    df = df.rename(columns=renamed)
    missing = [c for c in MASTER_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError("The file is missing these columns: " + ", ".join(missing))

    existing = {r["serial_no"] for r in db.fetch("SELECT serial_no FROM findings")}
    seen = set()
    errors, rows = [], []
    for position, (_, row) in enumerate(df.iterrows()):
        excel_row = position + 2  # row 1 holds the headings
        if all(clean_text(row[c]) == "" for c in MASTER_COLUMNS):
            continue  # completely blank line
        record = {COLUMN_TO_FIELD[c]: clean_text(row[c]) for c in MASTER_COLUMNS}
        problem = None
        if not record["serial_no"]:
            problem = "Serial number is empty"
        elif record["serial_no"] in existing or record["serial_no"] in seen:
            problem = f"Duplicate serial number {record['serial_no']}"
        if not problem:
            dept = match_department(record["department"])
            problem = None if dept else f"Unknown department '{record['department']}'"
            record["department"] = dept
        if not problem:
            risk = record["risk_level"].strip().capitalize()
            if risk not in RISK_LEVELS:
                problem = f"Risk level must be High, Medium or Low (found '{record['risk_level']}')"
            record["risk_level"] = risk
        if not problem:
            source = record["source"].strip().lower()
            if source.startswith("in"):
                record["source"] = "In-house"
            elif source.startswith("ext"):
                record["source"] = "External auditor"
            else:
                problem = f"Auditor type must be In-house or External (found '{record['source']}')"
        if not problem:
            target = parse_date(row["Original target date"])
            if target is None:
                problem = f"Original target date is missing or not a date ('{record['original_target_date']}')"
            record["original_target_date"] = iso(target)
        if not problem and not record["heading"]:
            problem = "Heading of the observation is empty"
        if problem:
            errors.append((excel_row, problem))
            continue
        seen.add(record["serial_no"])
        rows.append(record)

    if rows:
        columns = FINDING_FIELDS + ["created_at"]
        sql = (f"INSERT INTO findings ({', '.join(columns)}) "
               f"VALUES ({', '.join('?' for _ in columns)})")
        with db.session() as conn:
            stamp = now_iso()
            for rec in rows:
                db.execute(conn, sql, [rec[f] for f in FINDING_FIELDS] + [stamp])
            log_change(db, conn, username, "import", "findings", "-", "rows", None,
                       f"{len(rows)} imported, {len(errors)} rejected")
    return {"inserted": len(rows), "skipped": len(errors), "errors": errors}


def validate_finding_record(rec):
    """Check one finding typed in on the screen; returns the cleaned record."""
    rec = {k: clean_text(rec.get(k)) for k in FINDING_FIELDS}
    if not rec["serial_no"]:
        raise ValueError("Serial number is required.")
    if rec["department"] not in DEPARTMENTS:
        raise ValueError("Choose a department from the list.")
    if rec["risk_level"] not in RISK_LEVELS:
        raise ValueError("Risk level must be High, Medium or Low.")
    if rec["source"] not in SOURCES:
        raise ValueError("Auditor type must be In-house or External auditor.")
    if not rec["heading"]:
        raise ValueError("Heading of the observation is required.")
    target = parse_date(rec["original_target_date"])
    if target is None:
        raise ValueError("Original target date is required.")
    rec["original_target_date"] = iso(target)
    return rec


def add_finding(db, user, rec):
    require_role(user, ROLE_ADMIN)
    rec = validate_finding_record(rec)
    if db.fetch("SELECT id FROM findings WHERE serial_no = ?", (rec["serial_no"],)):
        raise ValueError(f"Serial number {rec['serial_no']} already exists.")
    columns = FINDING_FIELDS + ["created_at"]
    with db.session() as conn:
        fid = db.insert(
            conn, f"INSERT INTO findings ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
            [rec[f] for f in FINDING_FIELDS] + [now_iso()])
        log_change(db, conn, user["username"], "add", "findings", fid, "serial_no", None, rec["serial_no"])
    return fid


def update_finding(db, user, finding_id, rec):
    require_role(user, ROLE_ADMIN)
    rec = validate_finding_record(rec)
    old = db.fetch("SELECT * FROM findings WHERE id = ?", (finding_id,))
    if not old:
        raise ValueError("Finding not found.")
    old = old[0]
    clash = db.fetch("SELECT id FROM findings WHERE serial_no = ? AND id <> ?", (rec["serial_no"], finding_id))
    if clash:
        raise ValueError(f"Serial number {rec['serial_no']} already exists.")
    changed = [f for f in FINDING_FIELDS if clean_text(old[f]) != rec[f]]
    if not changed:
        return 0
    with db.session() as conn:
        for f in changed:
            db.execute(conn, f"UPDATE findings SET {f} = ? WHERE id = ?", (rec[f], finding_id))
            log_change(db, conn, user["username"], "edit", "findings", finding_id, f, old[f], rec[f])
    return len(changed)


# =============================================================================
# 6.  CURRENT STATUS AND AGEING
# =============================================================================

def ageing_bucket(days_overdue):
    if days_overdue <= 0:
        return "Not yet due"
    if days_overdue <= 30:
        return "1-30 days"
    if days_overdue <= 60:
        return "31-60 days"
    if days_overdue <= 90:
        return "61-90 days"
    return "Over 90 days"


STATUS_TABLE_COLUMNS = [
    "id", "serial_no", "year_reported", "source", "quarter", "report_name", "department",
    "observation_ref", "heading", "risk_level", "original_target_date",
    "effective_target_date", "current_auditor_status", "current_mgmt_status",
    "latest_follow_up_date", "rounds", "extensions", "days_overdue_original",
    "ageing_original", "days_overdue_revised", "ageing_revised",
    "mgmt_closed_auditor_not_closed", "last_mgmt_response", "last_auditor_remarks",
]


def build_status_table(findings_rows, followup_rows, today=None):
    """One row per finding with its CURRENT status and ageing.

    * Current auditor status = auditor status of the latest REVIEWED round
      (a finding with no reviewed round is Open).  This is the official status.
    * Management status = status given in the latest round (may be awaiting).
    * Ageing = days past the original target date, and also past the latest
      revised target date, for every finding the auditor has not closed.
    """
    today = today or date.today()
    by_finding = defaultdict(list)
    for fu in sorted(followup_rows, key=lambda r: (r["follow_up_date"] or "", r["id"])):
        by_finding[fu["finding_id"]].append(fu)

    out = []
    for f in findings_rows:
        fus = by_finding.get(f["id"], [])
        reviewed = [x for x in fus if x["auditor_status"]]
        auditor = reviewed[-1]["auditor_status"] if reviewed else "Open"
        latest = fus[-1] if fus else None
        if latest is None:
            mgmt = "No follow-up yet"
        else:
            mgmt = latest["mgmt_status"] or "Awaiting response"
        original = parse_date(f["original_target_date"])
        effective, extensions = original, 0
        for x in fus:
            revised = parse_date(x["revised_target_date"])
            if revised and revised != effective:
                effective, extensions = revised, extensions + 1
        if auditor == "Closed" or original is None:
            d_orig = d_rev = None
            b_orig = b_rev = "Closed" if auditor == "Closed" else "No target date"
        else:
            d_orig = (today - original).days
            d_rev = (today - effective).days
            b_orig, b_rev = ageing_bucket(d_orig), ageing_bucket(d_rev)
        last_reviewed = reviewed[-1] if reviewed else None
        out.append({
            "id": f["id"], "serial_no": f["serial_no"], "year_reported": f["year_reported"],
            "source": f["source"], "quarter": f["quarter"], "report_name": f["report_name"],
            "department": f["department"], "observation_ref": f["observation_ref"],
            "heading": f["heading"], "risk_level": f["risk_level"],
            "original_target_date": original, "effective_target_date": effective,
            "current_auditor_status": auditor, "current_mgmt_status": mgmt,
            "latest_follow_up_date": latest["follow_up_date"] if latest else None,
            "rounds": len(fus), "extensions": extensions,
            "days_overdue_original": d_orig, "ageing_original": b_orig,
            "days_overdue_revised": d_rev, "ageing_revised": b_rev,
            "mgmt_closed_auditor_not_closed": bool(latest and latest["mgmt_status"] == "Closed"
                                                  and auditor != "Closed"),
            "last_mgmt_response": (latest["mgmt_response"] if latest and latest["mgmt_response"] else ""),
            "last_auditor_remarks": (last_reviewed["auditor_remarks"] or "") if last_reviewed else "",
        })
    return pd.DataFrame(out, columns=STATUS_TABLE_COLUMNS)


def get_status_table(db, today=None):
    return build_status_table(db.fetch("SELECT * FROM findings ORDER BY id"),
                              db.fetch("SELECT * FROM followups"), today)


def ageing_counts(status_df, which="original"):
    """Counts of findings the auditor has not closed, per ageing bucket."""
    col = "ageing_original" if which == "original" else "ageing_revised"
    open_df = status_df[status_df["current_auditor_status"] != "Closed"]
    counts = open_df[col].value_counts()
    return pd.Series([int(counts.get(b, 0)) for b in AGEING_BUCKETS], index=AGEING_BUCKETS)


# =============================================================================
# 7.  E-MAIL  (log only / Gmail / any SMTP / Microsoft Graph)
# =============================================================================

def _send_smtp(host, port, username, password, sender, to_list, cc_list, subject, text, html):
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = sender, ", ".join(to_list), subject
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    context = ssl.create_default_context()
    if int(port) == 465:
        server = smtplib.SMTP_SSL(host, int(port), context=context, timeout=30)
    else:
        server = smtplib.SMTP(host, int(port), timeout=30)
        server.starttls(context=context)
    try:
        if username:
            server.login(username, password)
        server.send_message(msg, to_addrs=list(to_list) + list(cc_list))
    finally:
        server.quit()


def _send_graph(to_list, cc_list, subject, html_or_text):
    import requests
    tenant = get_setting("GRAPH_TENANT_ID")
    client_id = get_setting("GRAPH_CLIENT_ID")
    secret = get_setting("GRAPH_CLIENT_SECRET")
    sender = get_setting("GRAPH_SENDER")
    if not all([tenant, client_id, secret, sender]):
        raise ValueError("GRAPH_TENANT_ID, GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET and GRAPH_SENDER must be set.")
    token = requests.post(
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        data={"client_id": client_id, "client_secret": secret, "grant_type": "client_credentials",
              "scope": "https://graph.microsoft.com/.default"}, timeout=30)
    token.raise_for_status()
    access = token.json()["access_token"]

    def recipients(addresses):
        return [{"emailAddress": {"address": a}} for a in addresses]

    payload = {"message": {"subject": subject,
                           "body": {"contentType": "HTML", "content": html_or_text},
                           "toRecipients": recipients(to_list),
                           "ccRecipients": recipients(cc_list)},
               "saveToSentItems": True}
    reply = requests.post(f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail",
                          headers={"Authorization": f"Bearer {access}"}, json=payload, timeout=30)
    reply.raise_for_status()


def send_email(db, to_list, cc_list, subject, text, html=None):
    """Send (or only log) one e-mail.  Every attempt is written to the e-mail log.
    Returns (ok, detail)."""
    mode = get_setting("EMAIL_MODE", "log").strip().lower()
    to_list = [a for a in dict.fromkeys(to_list) if a]
    cc_list = [a for a in dict.fromkeys(cc_list) if a and a not in to_list]
    note = ""
    override = get_setting("TEST_EMAIL_OVERRIDE", "")
    if override:
        note = f" [test redirect, originally to {', '.join(to_list)}]"
        to_list, cc_list = [override], []
    try:
        if not to_list:
            raise ValueError("No recipient e-mail address")
        if mode == "log":
            ok, detail = True, "Logged only (EMAIL_MODE=log); nothing was sent"
        elif mode == "gmail":
            user, pw = get_setting("GMAIL_USER"), get_setting("GMAIL_APP_PASSWORD")
            if not user or not pw:
                raise ValueError("GMAIL_USER and GMAIL_APP_PASSWORD must be set")
            _send_smtp("smtp.gmail.com", 465, user, pw, user, to_list, cc_list, subject, text, html)
            ok, detail = True, "Sent through Gmail"
        elif mode == "smtp":
            host = get_setting("SMTP_HOST")
            if not host:
                raise ValueError("SMTP_HOST must be set")
            sender = get_setting("SMTP_FROM") or get_setting("SMTP_USER")
            _send_smtp(host, get_setting("SMTP_PORT", "587"), get_setting("SMTP_USER"),
                       get_setting("SMTP_PASSWORD"), sender, to_list, cc_list, subject, text, html)
            ok, detail = True, "Sent through SMTP"
        elif mode == "graph":
            _send_graph(to_list, cc_list, subject, html or text.replace("\n", "<br>"))
            ok, detail = True, "Sent through Microsoft Graph"
        else:
            raise ValueError(f"Unknown EMAIL_MODE '{mode}'")
    except Exception as exc:  # the failure is logged, never crashes the screen
        ok, detail = False, f"{type(exc).__name__}: {exc}"
    detail += note
    with db.session() as conn:
        db.execute(conn,
                   "INSERT INTO email_log (ts, mode, to_addr, cc_addr, subject, status, detail) "
                   "VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (now_iso(), mode, ", ".join(to_list), ", ".join(cc_list), subject,
                    "sent" if ok else "failed", detail))
    return ok, detail


def department_recipients(db, department):
    rows = db.fetch("SELECT email FROM users WHERE department = ? AND role = ? AND active = 1",
                    (department, ROLE_OWNER))
    return [r["email"] for r in rows if r["email"]]


def admin_recipients(db):
    rows = db.fetch("SELECT email FROM users WHERE role = ? AND active = 1", (ROLE_ADMIN,))
    return [r["email"] for r in rows if r["email"]]


def _items_html(items):
    rows = "".join(
        f"<tr><td>{i['serial_no']}</td><td>{i['heading']}</td><td>{i['risk_level']}</td>"
        f"<td>{i['target']}</td></tr>" for i in items)
    return ("<table border='1' cellpadding='4' cellspacing='0'>"
            "<tr><th>Serial no.</th><th>Observation</th><th>Risk</th><th>Target date</th></tr>"
            f"{rows}</table>")


def _compose(intro, department, items, due_text, closing):
    link = get_setting("APP_URL", "")
    text_lines = [f"Dear {department} team,", "", intro, ""]
    text_lines += [f"- #{i['serial_no']} | {i['heading']} | {i['risk_level']} | target {i['target']}" for i in items]
    text_lines += ["", due_text, closing]
    if link:
        text_lines += ["", f"Open the tracker: {link}"]
    html = (f"<p>Dear {department} team,</p><p>{intro}</p>{_items_html(items)}"
            f"<p>{due_text}</p><p>{closing}</p>"
            + (f"<p><a href='{link}'>Open the tracker</a></p>" if link else ""))
    return "\n".join(text_lines), html


def _item_list(df):
    return [{"serial_no": r["serial_no"], "heading": r["heading"], "risk_level": r["risk_level"],
             "target": r["effective_target_date"] if "effective_target_date" in r
             else r.get("original_target_date")} for _, r in df.iterrows()]


def notify_round(db, department, items, due_date):
    intro = (f"Internal Audit has opened a follow-up round. {len(items)} finding(s) of your department "
             "need your update (status, response and, if needed, a revised target date).")
    text, html = _compose(intro, department, items, f"Please respond by {due_date}.",
                          "Thank you, Internal Audit")
    return send_email(db, department_recipients(db, department), admin_recipients(db),
                      f"Audit follow-up: {len(items)} finding(s) need your update - {department}", text, html)


# =============================================================================
# 8.  FOLLOW-UP ROUNDS, MANAGEMENT UPDATES, AUDITOR REVIEW
# =============================================================================

def open_round(db, user, kind, follow_up_date, response_due_date, send_emails=True, today=None):
    """Audit Admin opens a round.  Quarterly = every finding the auditor has not
    closed.  Monthly = only the unclosed High-risk findings."""
    require_role(user, ROLE_ADMIN)
    if kind not in ROUND_KINDS:
        raise ValueError("Unknown round type.")
    fu_date, due = parse_date(follow_up_date), parse_date(response_due_date)
    if fu_date is None or due is None:
        raise ValueError("Enter both the follow-up date and the response due date.")
    if due < fu_date:
        raise ValueError("The response due date cannot be before the follow-up date.")

    findings = db.fetch("SELECT * FROM findings ORDER BY id")
    followups = db.fetch("SELECT * FROM followups")
    status = build_status_table(findings, followups, today)
    eligible = status[status["current_auditor_status"] != "Closed"]
    if kind == ROUND_MONTHLY:
        eligible = eligible[eligible["risk_level"] == "High"]
    already = {r["finding_id"] for r in followups if r["follow_up_date"] == iso(fu_date)}
    eligible = eligible[~eligible["id"].isin(already)]
    if eligible.empty:
        raise ValueError("No eligible findings for this round (all closed, or already in a round on this date).")

    with db.session() as conn:
        round_id = db.insert(
            conn, "INSERT INTO rounds (kind, follow_up_date, response_due_date, created_by, created_at) "
                  "VALUES (?, ?, ?, ?, ?)",
            (kind, iso(fu_date), iso(due), user["username"], now_iso()))
        for fid in eligible["id"]:
            db.execute(conn, "INSERT INTO followups (finding_id, round_id, follow_up_date, response_due_date) "
                             "VALUES (?, ?, ?, ?)", (int(fid), round_id, iso(fu_date), iso(due)))
        log_change(db, conn, user["username"], "open_round", "rounds", round_id, "findings", None, len(eligible))

    emails = []
    if send_emails:
        for dept, group in eligible.groupby("department"):
            ok, detail = notify_round(db, dept, _item_list(group), iso(due))
            emails.append({"department": dept, "ok": ok, "detail": detail})
    return {"round_id": round_id, "findings": len(eligible), "emails": emails}


def _followup_with_finding(db, followup_id):
    rows = db.fetch(
        "SELECT fu.*, f.department AS department, f.original_target_date AS original_target_date, "
        "f.serial_no AS serial_no FROM followups fu JOIN findings f ON f.id = fu.finding_id "
        "WHERE fu.id = ?", (followup_id,))
    if not rows:
        raise ValueError("Follow-up item not found.")
    return rows[0]


def submit_management_update(db, user, followup_id, status, response, revised_date=None,
                             evidence=None, today=None):
    """Department owner updates ONLY: management status, management response,
    revised target date (and optionally attaches evidence).  The original target
    date and every audit field stay sealed."""
    require_role(user, ROLE_OWNER)
    today = today or date.today()
    fu = _followup_with_finding(db, followup_id)
    if fu["department"] != user["department"]:
        raise PermissionError("This finding belongs to another department.")
    if fu["auditor_status"]:
        raise PermissionError("Internal Audit has already reviewed this round; it can no longer be edited.")
    if status not in STATUSES:
        raise ValueError("Choose Open, Ongoing or Closed.")
    response = clean_text(response)
    if not response:
        raise ValueError("Please write your management response.")
    revised = parse_date(revised_date)
    status_table = get_status_table(db, today)
    effective = status_table[status_table["id"] == fu["finding_id"]].iloc[0]["effective_target_date"]
    if status == "Closed" or revised == effective:
        revised = None  # a Closed finding needs no new date; an unchanged date is not a revision
    if status != "Closed":
        final_date = revised or effective
        if final_date and final_date < today:
            raise ValueError("The target date has passed. Please choose a revised target date "
                             "that is today or later.")
    if evidence is not None:
        name, data = evidence
        if len(data) > MAX_EVIDENCE_BYTES:
            raise ValueError("Evidence file is larger than 5 MB.")

    updates = {"mgmt_status": status, "mgmt_response": response,
               "revised_target_date": iso(revised) if revised else fu["revised_target_date"],
               "mgmt_updated_on": iso(today), "mgmt_updated_by": user["username"]}
    with db.session() as conn:
        for field, new in updates.items():
            old = fu[field]
            db.execute(conn, f"UPDATE followups SET {field} = ? WHERE id = ?", (new, followup_id))
            if field in ("mgmt_status", "mgmt_response", "revised_target_date") and clean_text(old) != clean_text(new):
                log_change(db, conn, user["username"], "management_update", "followups",
                           followup_id, field, old, new)
        if evidence is not None:
            db.execute(conn, "INSERT INTO evidence (followup_id, filename, content_b64, uploaded_by, uploaded_on) "
                             "VALUES (?, ?, ?, ?, ?)",
                       (followup_id, evidence[0], base64.b64encode(evidence[1]).decode("ascii"),
                        user["username"], now_iso()))
            log_change(db, conn, user["username"], "evidence", "followups", followup_id, "file", None, evidence[0])


def submit_auditor_review(db, user, followup_id, status, remarks, today=None):
    """Audit Admin records the auditor's own judgment for a follow-up item."""
    require_role(user, ROLE_ADMIN)
    today = today or date.today()
    fu = _followup_with_finding(db, followup_id)
    if status not in STATUSES:
        raise ValueError("Choose Open, Ongoing or Closed.")
    remarks = clean_text(remarks)
    if status == "Closed" and not remarks:
        raise ValueError("Please write remarks (what evidence was checked) before closing a finding.")
    with db.session() as conn:
        for field, new in {"auditor_status": status, "auditor_remarks": remarks,
                           "auditor_reviewed_on": iso(today), "auditor_reviewed_by": user["username"]}.items():
            db.execute(conn, f"UPDATE followups SET {field} = ? WHERE id = ?", (new, followup_id))
        log_change(db, conn, user["username"], "auditor_review", "followups", followup_id,
                   "auditor_status", fu["auditor_status"], status)


def get_evidence(db, followup_id):
    return db.fetch("SELECT id, filename, uploaded_by, uploaded_on FROM evidence WHERE followup_id = ?", (followup_id,))


def get_evidence_bytes(db, evidence_id):
    rows = db.fetch("SELECT filename, content_b64 FROM evidence WHERE id = ?", (evidence_id,))
    if not rows:
        return None, None
    return rows[0]["filename"], base64.b64decode(rows[0]["content_b64"])


def followups_table(db, department=None):
    """All follow-up items joined with their finding, newest first."""
    sql = ("SELECT fu.id AS followup_id, fu.round_id, fu.follow_up_date, fu.response_due_date, "
           "fu.mgmt_status, fu.mgmt_response, fu.revised_target_date, fu.mgmt_updated_on, "
           "fu.mgmt_updated_by, fu.auditor_status, fu.auditor_remarks, fu.auditor_reviewed_on, "
           "fu.reminder_sent_on, fu.escalation_sent_on, f.id AS finding_id, f.serial_no, "
           "f.department, f.heading, f.risk_level, f.original_target_date "
           "FROM followups fu JOIN findings f ON f.id = fu.finding_id ")
    params = ()
    if department:
        sql += "WHERE f.department = ? "
        params = (department,)
    sql += "ORDER BY fu.follow_up_date DESC, fu.id DESC"
    return pd.DataFrame(db.fetch(sql, params))


# =============================================================================
# 9.  REMINDERS  (1 week after the response due date) AND OPTIONAL ESCALATION
# =============================================================================

def pending_reminders(db, today=None, days=None):
    """Follow-up items with no management update, where the response due date
    plus REMINDER_DAYS (default 7) has passed and no reminder was sent yet."""
    today = today or date.today()
    days = days if days is not None else setting_int("REMINDER_DAYS", 7)
    rows = db.fetch(
        "SELECT fu.id AS followup_id, fu.response_due_date, f.serial_no, f.heading, f.department, "
        "f.risk_level, f.original_target_date FROM followups fu JOIN findings f ON f.id = fu.finding_id "
        "WHERE fu.mgmt_updated_on IS NULL AND fu.auditor_status IS NULL AND fu.reminder_sent_on IS NULL")
    keep = []
    for r in rows:
        due = parse_date(r["response_due_date"])
        if due and due + timedelta(days=days) <= today:
            keep.append(r)
    return pd.DataFrame(keep, columns=["followup_id", "response_due_date", "serial_no", "heading",
                                       "department", "risk_level", "original_target_date"])


def send_due_reminders(db, user, today=None):
    """One reminder e-mail per department to its two users, copying the audit team."""
    require_role(user, ROLE_ADMIN)
    today = today or date.today()
    pending = pending_reminders(db, today)
    results = []
    for dept, group in pending.groupby("department"):
        items = [{"serial_no": r["serial_no"], "heading": r["heading"], "risk_level": r["risk_level"],
                  "target": r["original_target_date"]} for _, r in group.iterrows()]
        days = setting_int("REMINDER_DAYS", 7)
        intro = (f"REMINDER: {len(items)} finding(s) of your department still have no management update, "
                 f"more than {days} days after the response due date.")
        text, html = _compose(intro, dept, items, "Please update them in the tracker today.",
                              "Thank you, Internal Audit")
        ok, detail = send_email(db, department_recipients(db, dept), admin_recipients(db),
                                f"REMINDER: audit findings awaiting your response - {dept}", text, html)
        if ok:
            with db.session() as conn:
                for fid in group["followup_id"]:
                    db.execute(conn, "UPDATE followups SET reminder_sent_on = ? WHERE id = ?", (iso(today), int(fid)))
                log_change(db, conn, user["username"], "reminder", "followups", dept, "items", None, len(items))
        results.append({"department": dept, "items": len(items), "ok": ok, "detail": detail})
    return results


def send_escalations(db, user, today=None):
    """Optional (setting ESCALATION_ENABLED=true): if still no update ESCALATION_DAYS
    (default 14) after the response due date, tell the department head."""
    require_role(user, ROLE_ADMIN)
    if not setting_bool("ESCALATION_ENABLED", False):
        return []
    today = today or date.today()
    days = setting_int("ESCALATION_DAYS", 14)
    rows = db.fetch(
        "SELECT fu.id AS followup_id, fu.response_due_date, f.serial_no, f.heading, f.department, "
        "f.risk_level, f.original_target_date FROM followups fu JOIN findings f ON f.id = fu.finding_id "
        "WHERE fu.mgmt_updated_on IS NULL AND fu.auditor_status IS NULL "
        "AND fu.reminder_sent_on IS NOT NULL AND fu.escalation_sent_on IS NULL")
    rows = [r for r in rows if parse_date(r["response_due_date"]) and
            parse_date(r["response_due_date"]) + timedelta(days=days) <= today]
    results = []
    by_dept = defaultdict(list)
    for r in rows:
        by_dept[r["department"]].append(r)
    for dept, group in by_dept.items():
        head = db.fetch("SELECT head_email FROM departments WHERE name = ?", (dept,))
        head_email = head[0]["head_email"] if head else ""
        items = [{"serial_no": r["serial_no"], "heading": r["heading"], "risk_level": r["risk_level"],
                  "target": r["original_target_date"]} for r in group]
        text, html = _compose(f"ESCALATION: {len(items)} finding(s) of {dept} are still without a response "
                              f"{days} days after the due date.", "Head of " + dept, items,
                              "Kindly ensure your team responds.", "Thank you, Internal Audit")
        ok, detail = send_email(db, [head_email], admin_recipients(db),
                                f"ESCALATION: audit findings without response - {dept}", text, html)
        if ok:
            with db.session() as conn:
                for r in group:
                    db.execute(conn, "UPDATE followups SET escalation_sent_on = ? WHERE id = ?",
                               (iso(today), r["followup_id"]))
        results.append({"department": dept, "items": len(items), "ok": ok, "detail": detail})
    return results


# =============================================================================
# 10.  EXCEL EXPORT
# =============================================================================

def to_excel_bytes(sheets):
    """sheets = {"Sheet name": DataFrame}; returns the .xlsx file as bytes."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name[:31], index=False)
            sheet = writer.sheets[name[:31]]
            for idx, col in enumerate(frame.columns, start=1):
                width = min(60, max(12, len(str(col)) + 2))
                sheet.column_dimensions[sheet.cell(row=1, column=idx).column_letter].width = width
    return buffer.getvalue()


def build_wide_export(db, today=None):
    """Master columns + current status, then for each follow-up date a block:
    Date, Management status, Management response, Auditor status."""
    findings = db.fetch("SELECT * FROM findings ORDER BY id")
    followups = db.fetch("SELECT * FROM followups")
    status = build_status_table(findings, followups, today).set_index("id")
    by_finding = defaultdict(list)
    for fu in sorted(followups, key=lambda r: (r["follow_up_date"] or "", r["id"])):
        by_finding[fu["finding_id"]].append(fu)
    rows = []
    for f in findings:
        row = {FIELD_TO_COLUMN[k]: f[k] for k in FINDING_FIELDS}
        row["Current auditor status"] = status.loc[f["id"], "current_auditor_status"]
        row["Current management status"] = status.loc[f["id"], "current_mgmt_status"]
        for n, fu in enumerate(by_finding.get(f["id"], []), start=1):
            row[f"FU{n} date"] = fu["follow_up_date"]
            row[f"FU{n} management status"] = fu["mgmt_status"]
            row[f"FU{n} management response"] = fu["mgmt_response"]
            row[f"FU{n} auditor status"] = fu["auditor_status"]
        rows.append(row)
    return pd.DataFrame(rows)


# =============================================================================
# 11.  SAMPLE (DUMMY) DATA
# =============================================================================

_TOPICS = [
    ("KYC documents not refreshed on time", "Customer KYC records were found past their refresh date.",
     "Regulatory penalty and money-laundering exposure.", "Complete the KYC refresh and add a monthly expiry report."),
    ("Segregation of duties gap in approvals", "The same employee prepares and approves transactions.",
     "Risk of undetected error or fraud.", "Separate maker and checker roles and enforce it in the system."),
    ("Cash handling variances not investigated", "Daily cash differences were not explained or escalated.",
     "Possible loss or misappropriation.", "Investigate every variance and report weekly to the manager."),
    ("User access rights not reviewed", "Access for staff who changed roles or left was not removed.",
     "Unauthorised access to systems and data.", "Perform a quarterly access review and remove old access at once."),
    ("Loan documentation incomplete", "Required documents were missing from sampled loan files.",
     "Recovery difficulty if the borrower defaults.", "Complete the files and add a pre-disbursement checklist."),
    ("Old items in suspense account", "Suspense account items older than 90 days were not cleared.",
     "Misstatement of accounts and hidden errors.", "Clear or write off old items and review the account monthly."),
    ("Vendor due diligence not documented", "New vendors were onboarded without documented checks.",
     "Dealing with unsuitable or high-risk vendors.", "Introduce a vendor onboarding checklist with approval."),
    ("Weak password and log-in controls", "Systems allowed short passwords and had no lock-out rule.",
     "Easier compromise of staff accounts.", "Enforce the password policy and multi-factor log-in."),
    ("Purchases approved above delegated limits", "Several purchases exceeded the approver's authority limit.",
     "Unauthorised spending.", "Apply system limits and report exceptions monthly."),
    ("Statutory filings submitted late", "Some returns were filed after the due date.",
     "Penalties and reputational damage.", "Maintain a compliance calendar with owners and reminders."),
    ("Backups not tested", "Data backups were taken but no restore test was done.",
     "Data may not be recoverable after an incident.", "Test restores twice a year and record the results."),
    ("Staff training records incomplete", "Mandatory training was not completed by some staff.",
     "Skills and compliance gaps.", "Track training centrally and follow up on defaulters."),
    ("Customer complaints answered late", "Complaint turnaround exceeded the policy limit.",
     "Customer dissatisfaction and regulatory attention.", "Track complaints with ageing and escalate delays."),
    ("Policy not reviewed annually", "The department policy has not been reviewed within 12 months.",
     "Outdated rules and inconsistent practice.", "Review and approve the policy, then set a yearly reminder."),
    ("Fixed asset register not updated", "Assets purchased or disposed of were not reflected in the register.",
     "Wrong asset values and possible loss of assets.", "Update the register and verify physically each year."),
]
_RESPONSE_OPEN = ["Management has noted the point and will start action soon.",
                  "Action is planned; resources are being arranged.",
                  "No progress yet because of other priorities."]
_RESPONSE_ONGOING = ["Work has started and about half of it is done.",
                     "System change requested from IT; testing in progress.",
                     "Most items corrected; remaining items need more time."]
_RESPONSE_CLOSED = ["Fully implemented; evidence attached.",
                    "Corrected for all cases and a monitoring report is now in place.",
                    "Policy approved and communicated to all staff."]
_AUDITOR_AGREE_CLOSED = ["Evidence checked and found satisfactory.", "Re-tested a sample; no exception found."]
_AUDITOR_DISAGREE = ["Evidence is incomplete; the control is not yet working in all cases.",
                     "Sample re-test still shows exceptions."]


def generate_sample_findings(seed=42, today=None):
    """About 30 to 50 dummy findings per department, as a DataFrame in the 14 import columns."""
    rnd = random.Random(seed)
    today = today or date.today()
    rows, serial = [], 1
    for dept in DEPARTMENTS:
        for _ in range(rnd.randint(30, 50)):
            topic = rnd.choice(_TOPICS)
            year = rnd.choice([2022, 2023, 2024, 2025, 2026])
            rows.append({
                "Serial number": serial,
                "Year reported": year,
                "In-house or external auditor": rnd.choice(SOURCES),
                "Quarter": f"Q{rnd.randint(1, 4)}",
                "Report name": f"[SAMPLE] {dept} audit report {year}",
                "Department": dept,
                "Observation": f"OBS-{serial:04d}",
                "Heading of the observation": f"[SAMPLE] {topic[0]}",
                "Detailed observation": f"[SAMPLE] {topic[1]} (dummy text for testing, {dept}).",
                "Risk implication": f"[SAMPLE] {topic[2]}",
                "Recommendation": f"[SAMPLE] {topic[3]}",
                "Management response": "[SAMPLE] Management agrees and will implement by the target date.",
                "Risk level": rnd.choices(RISK_LEVELS, weights=[25, 45, 30])[0],
                "Original target date": today + timedelta(days=rnd.randint(-330, 150)),
            })
            serial += 1
    return pd.DataFrame(rows, columns=MASTER_COLUMNS)


def seed_sample_history(db, seed=7, today=None):
    """Create 3 past rounds (history) and 1 current quarterly round whose response
    due date is 10 days ago, so the 7-day reminder rule can be tested."""
    rnd = random.Random(seed)
    today = today or date.today()
    findings = db.fetch("SELECT * FROM findings ORDER BY id")
    state = {f["id"]: {"auditor": "Open", "target": parse_date(f["original_target_date"])} for f in findings}
    plan = [  # (days before today for the follow-up date, kind, weights Open/Ongoing/Closed)
        (200, ROUND_QUARTERLY, (50, 40, 10)),
        (110, ROUND_MONTHLY, (30, 40, 30)),
        (45, ROUND_QUARTERLY, (20, 40, 40)),
    ]
    with db.session() as conn:
        for days_before, kind, weights in plan:
            fu_date = today - timedelta(days=days_before)
            due = fu_date + timedelta(days=14)
            rid = db.insert(conn, "INSERT INTO rounds (kind, follow_up_date, response_due_date, created_by, created_at) "
                                  "VALUES (?, ?, ?, ?, ?)", (kind, iso(fu_date), iso(due), "Audit Admin", now_iso()))
            for f in findings:
                s = state[f["id"]]
                if s["auditor"] == "Closed":
                    continue
                if kind == ROUND_MONTHLY and f["risk_level"] != "High":
                    continue
                mgmt = rnd.choices(STATUSES, weights=weights)[0]
                if mgmt == "Closed":
                    auditor = "Closed" if rnd.random() < 0.8 else rnd.choice(["Open", "Ongoing"])
                elif mgmt == "Ongoing":
                    auditor = "Ongoing" if rnd.random() < 0.9 else "Open"
                else:
                    auditor = "Open"
                response = rnd.choice({"Open": _RESPONSE_OPEN, "Ongoing": _RESPONSE_ONGOING,
                                       "Closed": _RESPONSE_CLOSED}[mgmt])
                revised = None
                if mgmt != "Closed" and rnd.random() < 0.4:
                    revised = max(s["target"], fu_date) + timedelta(days=rnd.randint(30, 120))
                    s["target"] = revised
                if auditor == "Closed":
                    remarks = rnd.choice(_AUDITOR_AGREE_CLOSED)
                elif mgmt == "Closed":
                    remarks = rnd.choice(_AUDITOR_DISAGREE)
                else:
                    remarks = "Progress noted; follow up in the next round."
                db.execute(
                    conn,
                    "INSERT INTO followups (finding_id, round_id, follow_up_date, response_due_date, mgmt_status, "
                    "mgmt_response, revised_target_date, mgmt_updated_on, mgmt_updated_by, auditor_status, "
                    "auditor_remarks, auditor_reviewed_on, auditor_reviewed_by) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (f["id"], rid, iso(fu_date), iso(due), mgmt, "[SAMPLE] " + response, iso(revised),
                     iso(fu_date + timedelta(days=rnd.randint(2, 12))), f"{f['department']} 1",
                     auditor, "[SAMPLE] " + remarks, iso(due + timedelta(days=5)), "Audit Admin"))
                s["auditor"] = auditor

        # Current round: due 10 days ago.  About 25% already answered, the rest pending.
        fu_date = today - timedelta(days=24)
        due = today - timedelta(days=10)
        rid = db.insert(conn, "INSERT INTO rounds (kind, follow_up_date, response_due_date, created_by, created_at) "
                              "VALUES (?, ?, ?, ?, ?)", (ROUND_QUARTERLY, iso(fu_date), iso(due), "Audit Admin", now_iso()))
        pending = 0
        for f in findings:
            if state[f["id"]]["auditor"] == "Closed":
                continue
            answered = rnd.random() < 0.25
            if answered:
                mgmt = rnd.choices(STATUSES, weights=(20, 50, 30))[0]
                values = (mgmt, "[SAMPLE] " + rnd.choice({"Open": _RESPONSE_OPEN, "Ongoing": _RESPONSE_ONGOING,
                                                         "Closed": _RESPONSE_CLOSED}[mgmt]),
                          None, iso(today - timedelta(days=rnd.randint(1, 9))), f"{f['department']} 2")
            else:
                values, pending = (None, None, None, None, None), pending + 1
            db.execute(conn, "INSERT INTO followups (finding_id, round_id, follow_up_date, response_due_date, mgmt_status, "
                             "mgmt_response, revised_target_date, mgmt_updated_on, mgmt_updated_by) "
                             "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (f["id"], rid, iso(fu_date), iso(due)) + values)
        log_change(db, conn, "Audit Admin", "sample_history", "followups", "-", "rounds", None, 4)
    return pending


def load_sample_data(db, user, seed=42, today=None):
    require_role(user, ROLE_ADMIN)
    if db.fetch("SELECT id FROM findings LIMIT 1"):
        raise ValueError("The database already holds findings. Wipe them first if you want sample data.")
    result = import_findings(db, generate_sample_findings(seed, today), user["username"])
    pending = seed_sample_history(db, today=today)
    return {"findings": result["inserted"], "pending_in_current_round": pending}


def wipe_all_data(db, user):
    """Delete all findings, rounds, follow-ups, evidence and e-mail log.  Users stay."""
    require_role(user, ROLE_ADMIN)
    with db.session() as conn:
        for table in ("evidence", "followups", "rounds", "findings", "email_log"):
            db.execute(conn, f"DELETE FROM {table}")
        log_change(db, conn, user["username"], "wipe", "all", "-", "data", None, "wiped")


# =============================================================================
# 12.  STREAMLIT SCREENS
# =============================================================================

def _label_for_finding(row):
    return f"#{row['serial_no']} | {row['department']} | {str(row['heading'])[:70]}"


def _show(df):
    st.dataframe(df, hide_index=True)


def _flash_and_rerun(message):
    """Show a message after the page reloads (a plain st.success would be wiped by st.rerun)."""
    st.session_state["flash"] = message
    st.rerun()


def page_dashboard(db, user):
    st.header("Dashboard")
    status = get_status_table(db)
    if user["role"] == ROLE_OWNER:
        status = status[status["department"] == user["department"]]
    if status.empty:
        st.info("There are no findings yet. The Audit Admin can import them (Import and sample data).")
        return

    cols = st.columns(5)
    with cols[0]:
        dept_options = sorted(status["department"].unique())
        depts = st.multiselect("Department", dept_options, default=dept_options,
                               disabled=(user["role"] == ROLE_OWNER))
    with cols[1]:
        risks = st.multiselect("Risk level", RISK_LEVELS, default=RISK_LEVELS)
    with cols[2]:
        years = st.multiselect("Year reported", sorted(status["year_reported"].unique()),
                               default=sorted(status["year_reported"].unique()))
    with cols[3]:
        quarters = st.multiselect("Quarter", sorted(status["quarter"].unique()),
                                  default=sorted(status["quarter"].unique()))
    with cols[4]:
        stats = st.multiselect("Auditor status", STATUSES, default=STATUSES)
    view = status[status["department"].isin(depts) & status["risk_level"].isin(risks)
                  & status["year_reported"].isin(years) & status["quarter"].isin(quarters)
                  & status["current_auditor_status"].isin(stats)]
    if view.empty:
        st.warning("No findings match these filters.")
        return

    total = len(view)
    closed = int((view["current_auditor_status"] == "Closed").sum())
    ongoing = int((view["current_auditor_status"] == "Ongoing").sum())
    open_n = int((view["current_auditor_status"] == "Open").sum())
    days_over = pd.to_numeric(view["days_overdue_original"], errors="coerce").fillna(0)
    overdue = int(((view["current_auditor_status"] != "Closed") & (days_over > 0)).sum())
    tiles = st.columns(6)
    tiles[0].metric("Total findings", total)
    tiles[1].metric("Open", open_n)
    tiles[2].metric("Ongoing", ongoing)
    tiles[3].metric("Closed", closed)
    tiles[4].metric("Overdue", overdue)
    tiles[5].metric("Closure rate", f"{closed / total:.0%}")
    st.caption("All counts use the AUDITOR status, which is the official status.")

    st.subheader("Ageing of findings not yet closed (days past target date)")
    ageing = pd.DataFrame({"Against original target date": ageing_counts(view, "original"),
                           "Against latest revised target date": ageing_counts(view, "revised")})
    st.bar_chart(ageing)
    _show(ageing.T.reset_index().rename(columns={"index": "Basis"}))

    left, right = st.columns(2)
    with left:
        st.subheader("By department and status")
        st.bar_chart(pd.crosstab(view["department"], view["current_auditor_status"])
                     .reindex(columns=STATUSES, fill_value=0))
        st.subheader("By source")
        st.bar_chart(pd.crosstab(view["source"], view["current_auditor_status"])
                     .reindex(columns=STATUSES, fill_value=0))
    with right:
        st.subheader("By risk level and status")
        st.bar_chart(pd.crosstab(view["risk_level"], view["current_auditor_status"])
                     .reindex(index=RISK_LEVELS, columns=STATUSES, fill_value=0))
        st.subheader("By year reported and status")
        st.bar_chart(pd.crosstab(view["year_reported"], view["current_auditor_status"])
                     .reindex(columns=STATUSES, fill_value=0))

    st.subheader("Auditor status at each follow-up round")
    fu = followups_table(db, user["department"] if user["role"] == ROLE_OWNER else None)
    if not fu.empty:
        reviewed = fu[fu["auditor_status"].notna() & fu["serial_no"].isin(view["serial_no"])]
        if not reviewed.empty:
            st.bar_chart(pd.crosstab(reviewed["follow_up_date"], reviewed["auditor_status"])
                         .reindex(columns=STATUSES, fill_value=0))
        else:
            st.info("No reviewed follow-up rounds yet.")

    st.subheader("Management says Closed, auditor does not")
    gap = view[view["mgmt_closed_auditor_not_closed"]]
    if gap.empty:
        st.success("No disagreements.")
    else:
        _show(gap[["serial_no", "department", "heading", "risk_level", "current_mgmt_status",
                   "current_auditor_status", "last_auditor_remarks"]])

    st.download_button("Download this view as Excel",
                       to_excel_bytes({"Findings": view.drop(columns=["id"])}),
                       file_name="audit_findings_view.xlsx")


def page_findings(db, user):
    st.header("Findings register")
    status = get_status_table(db)
    if user["role"] == ROLE_OWNER:
        status = status[status["department"] == user["department"]]
    if status.empty:
        st.info("No findings yet.")
    else:
        search = st.text_input("Search in heading or report name")
        view = status
        if search:
            mask = (view["heading"].str.contains(search, case=False, na=False)
                    | view["report_name"].str.contains(search, case=False, na=False))
            view = view[mask]
        _show(view[["serial_no", "department", "heading", "risk_level", "original_target_date",
                    "effective_target_date", "current_auditor_status", "current_mgmt_status",
                    "days_overdue_original", "ageing_original", "extensions"]])
        if not view.empty:
            options = list(view["id"])
            labels = {r["id"]: _label_for_finding(r) for _, r in view.iterrows()}
            chosen = st.selectbox("Open a finding", options, format_func=lambda i: labels[i])
            finding = db.fetch("SELECT * FROM findings WHERE id = ?", (int(chosen),))[0]
            st.write(f"**{finding['heading']}**")
            for field in ("detailed_observation", "risk_implication", "recommendation",
                          "initial_management_response"):
                st.write(f"**{FIELD_TO_COLUMN[field]}:** {finding[field]}")
            history = followups_table(db)
            history = history[history["finding_id"] == int(chosen)] if not history.empty else history
            st.write("**Follow-up history**")
            if history.empty:
                st.caption("No follow-up rounds yet.")
            else:
                _show(history[["follow_up_date", "response_due_date", "mgmt_status", "mgmt_response",
                               "revised_target_date", "auditor_status", "auditor_remarks"]])

    if user["role"] == ROLE_ADMIN:
        with st.expander("Add a finding"):
            _finding_form(db, user, None)
        with st.expander("Edit a finding"):
            all_findings = db.fetch("SELECT * FROM findings ORDER BY id")
            if all_findings:
                labels = {r["id"]: _label_for_finding(r) for r in all_findings}
                picked = st.selectbox("Finding to edit", list(labels), format_func=lambda i: labels[i], key="edit_pick")
                _finding_form(db, user, next(r for r in all_findings if r["id"] == picked))


def _finding_form(db, user, existing):
    key = f"finding_form_{existing['id'] if existing else 'new'}"
    cur = existing or {}
    with st.form(key):
        rec = {
            "serial_no": st.text_input("Serial number", cur.get("serial_no", "")),
            "year_reported": st.text_input("Year reported", cur.get("year_reported", "")),
            "source": st.selectbox("In-house or external auditor", SOURCES,
                                   index=SOURCES.index(cur["source"]) if cur.get("source") in SOURCES else 0),
            "quarter": st.text_input("Quarter", cur.get("quarter", "")),
            "report_name": st.text_input("Report name", cur.get("report_name", "")),
            "department": st.selectbox("Department", DEPARTMENTS,
                                       index=DEPARTMENTS.index(cur["department"]) if cur.get("department") in DEPARTMENTS else 0),
            "observation_ref": st.text_input("Observation (reference)", cur.get("observation_ref", "")),
            "heading": st.text_input("Heading of the observation", cur.get("heading", "")),
            "detailed_observation": st.text_area("Detailed observation", cur.get("detailed_observation", "")),
            "risk_implication": st.text_area("Risk implication", cur.get("risk_implication", "")),
            "recommendation": st.text_area("Recommendation", cur.get("recommendation", "")),
            "initial_management_response": st.text_area("Management response (initial)",
                                                        cur.get("initial_management_response", "")),
            "risk_level": st.selectbox("Risk level", RISK_LEVELS,
                                       index=RISK_LEVELS.index(cur["risk_level"]) if cur.get("risk_level") in RISK_LEVELS else 1),
            "original_target_date": st.date_input("Original target date",
                                                  value=parse_date(cur.get("original_target_date")) or date.today()),
        }
        submitted = st.form_submit_button("Save changes" if existing else "Add finding")
    if submitted:
        try:
            if existing:
                n = update_finding(db, user, existing["id"], rec)
                st.success(f"Saved. {n} field(s) changed.")
            else:
                add_finding(db, user, rec)
                st.success("Finding added.")
        except (ValueError, PermissionError) as exc:
            st.error(str(exc))


def page_my_updates(db, user):
    st.header(f"Respond to findings - {user['department']}")
    with st.expander("What do Open, Ongoing and Closed mean?"):
        for name, text in STATUS_DEFINITIONS.items():
            st.write(f"**{name}:** {text}")
    fus = followups_table(db, user["department"])
    if fus.empty:
        st.info("Internal Audit has not opened a follow-up round for your department yet.")
        return
    todo = fus[fus["auditor_status"].isna()]
    st.write(f"**{len(todo)}** item(s) are waiting for your response "
             f"({int(todo['mgmt_updated_on'].notna().sum())} already answered, you may still change them).")
    if todo.empty:
        st.success("Nothing is waiting for your response.")
    else:
        labels = {int(r["followup_id"]): f"#{r['serial_no']} | due {r['response_due_date']} | "
                                          f"{'answered' if pd.notna(r['mgmt_updated_on']) else 'NOT answered'} | "
                                          f"{str(r['heading'])[:55]}" for _, r in todo.iterrows()}
        chosen = st.selectbox("Choose an item", list(labels), format_func=lambda i: labels[i])
        row = todo[todo["followup_id"] == chosen].iloc[0]
        finding = db.fetch("SELECT * FROM findings WHERE id = ?", (int(row["finding_id"]),))[0]
        st.write(f"**{finding['heading']}**  (Risk: {finding['risk_level']})")
        st.write(f"**Detailed observation:** {finding['detailed_observation']}")
        st.write(f"**Recommendation:** {finding['recommendation']}")
        st.write(f"**Original target date (locked):** {finding['original_target_date']}")
        status_tbl = get_status_table(db)
        current_target = status_tbl[status_tbl["id"] == int(row["finding_id"])].iloc[0]["effective_target_date"] or date.today()
        st.write(f"**Current target date:** {current_target}")
        with st.form(f"mgmt_form_{chosen}"):
            current = row["mgmt_status"] if row["mgmt_status"] in STATUSES else "Open"
            status = st.selectbox("Status", STATUSES, index=STATUSES.index(current))
            response = st.text_area("Management response as on today",
                                    value=row["mgmt_response"] if pd.notna(row["mgmt_response"]) else "")
            revised = st.date_input("Target date (change it if you need more time; for Open or Ongoing it must be "
                                    "today or later; ignored if Closed)", value=current_target)
            upload = st.file_uploader("Evidence (optional, max 5 MB)")
            submitted = st.form_submit_button("Submit response")
        if submitted:
            try:
                evidence = (upload.name, upload.getvalue()) if upload is not None else None
                submit_management_update(db, user, int(chosen), status, response, revised, evidence)
                _flash_and_rerun("Your response has been saved.")
            except (ValueError, PermissionError) as exc:
                st.error(str(exc))
    with st.expander("History of all follow-ups for my department"):
        _show(fus[["serial_no", "heading", "follow_up_date", "response_due_date", "mgmt_status",
                   "revised_target_date", "auditor_status", "auditor_remarks"]])


def page_review(db, user):
    st.header("Review management responses")
    fus = followups_table(db)
    if fus.empty:
        st.info("No follow-up rounds yet.")
        return
    tab1, tab2, tab3 = st.tabs(["Awaiting my review", "No response yet", "Already reviewed"])
    waiting = fus[fus["auditor_status"].isna() & fus["mgmt_updated_on"].notna()]
    silent = fus[fus["auditor_status"].isna() & fus["mgmt_updated_on"].isna()]
    with tab1:
        if waiting.empty:
            st.info("No management responses are waiting for review.")
        else:
            labels = {int(r["followup_id"]): f"#{r['serial_no']} | {r['department']} | mgmt says "
                                              f"{r['mgmt_status']} | {str(r['heading'])[:50]}"
                      for _, r in waiting.iterrows()}
            chosen = st.selectbox("Choose an item", list(labels), format_func=lambda i: labels[i])
            row = waiting[waiting["followup_id"] == chosen].iloc[0]
            st.write(f"**Management status:** {row['mgmt_status']}")
            st.write(f"**Management response:** {row['mgmt_response']}")
            st.write(f"**Revised target date:** {row['revised_target_date']}")
            for ev in get_evidence(db, int(chosen)):
                name, data = get_evidence_bytes(db, ev["id"])
                st.download_button(f"Evidence: {name}", data, file_name=name, key=f"ev_{ev['id']}")
            with st.form(f"review_form_{chosen}"):
                status = st.radio("Auditor status", STATUSES, horizontal=True)
                remarks = st.text_area("Auditor remarks (required to close)")
                submitted = st.form_submit_button("Save auditor judgment")
            if submitted:
                try:
                    submit_auditor_review(db, user, int(chosen), status, remarks)
                    _flash_and_rerun("Auditor judgment saved.")
                except (ValueError, PermissionError) as exc:
                    st.error(str(exc))
    with tab2:
        if silent.empty:
            st.success("Every department has responded.")
        else:
            _show(silent[["serial_no", "department", "heading", "risk_level", "response_due_date", "reminder_sent_on"]])
            st.caption("You can record an auditor status for an unanswered item, for example Open, "
                       "using the box below.")
            labels = {int(r["followup_id"]): f"#{r['serial_no']} | {r['department']} | {str(r['heading'])[:50]}"
                      for _, r in silent.iterrows()}
            chosen = st.selectbox("Item with no response", list(labels), format_func=lambda i: labels[i], key="silent_pick")
            with st.form(f"silent_form_{chosen}"):
                remarks = st.text_area("Auditor remarks", value="No management response received.")
                submitted = st.form_submit_button("Record as Open")
            if submitted:
                try:
                    submit_auditor_review(db, user, int(chosen), "Open", remarks)
                    _flash_and_rerun("Recorded as Open.")
                except (ValueError, PermissionError) as exc:
                    st.error(str(exc))
    with tab3:
        done = fus[fus["auditor_status"].notna()]
        _show(done[["serial_no", "department", "follow_up_date", "mgmt_status", "auditor_status",
                    "auditor_remarks", "auditor_reviewed_on"]].head(500))


def page_rounds(db, user):
    st.header("Follow-up rounds and reminders")
    mode = get_setting("EMAIL_MODE", "log")
    st.info(f"E-mail mode: **{mode}**" + ("  (nothing is really sent; see the E-mail log)" if mode == "log" else "")
            + (f"  | all mail redirected to {get_setting('TEST_EMAIL_OVERRIDE')}" if get_setting("TEST_EMAIL_OVERRIDE") else ""))

    st.subheader("Open a new round")
    with st.form("round_form"):
        kind = st.radio("Round type", ROUND_KINDS, horizontal=True)
        fu_date = st.date_input("Follow-up date", value=date.today())
        due = st.date_input("Response due date", value=date.today() + timedelta(days=14))
        send = st.checkbox("E-mail the department users now", value=True)
        submitted = st.form_submit_button("Open round")
    if submitted:
        try:
            result = open_round(db, user, kind, fu_date, due, send)
            st.success(f"Round opened with {result['findings']} finding(s).")
            for e in result["emails"]:
                (st.write if e["ok"] else st.error)(f"{e['department']}: {e['detail']}")
        except (ValueError, PermissionError) as exc:
            st.error(str(exc))

    st.subheader("Reminders (7 days after the response due date)")
    pending = pending_reminders(db)
    if pending.empty:
        st.success("No reminders are due today.")
    else:
        st.write(f"**{len(pending)}** item(s) in **{pending['department'].nunique()}** department(s) need a reminder.")
        _show(pending[["department", "serial_no", "heading", "response_due_date"]])
    if st.button("Send reminders now"):
        results = send_due_reminders(db, user)
        if not results:
            st.info("Nothing to send.")
        for r in results:
            (st.write if r["ok"] else st.error)(f"{r['department']}: {r['items']} item(s) - {r['detail']}")
        for r in send_escalations(db, user):
            (st.write if r["ok"] else st.error)(f"ESCALATION {r['department']}: {r['items']} item(s) - {r['detail']}")

    st.subheader("Send a test e-mail to myself")
    if st.button("Send test e-mail"):
        ok, detail = send_email(db, [user["email"]], [], "Audit tracker test e-mail",
                                "This is a test e-mail from the Audit Findings Tracker.")
        (st.success if ok else st.error)(detail)

    st.subheader("Rounds so far")
    rounds = pd.DataFrame(db.fetch(
        "SELECT r.id, r.kind, r.follow_up_date, r.response_due_date, r.created_by, "
        "(SELECT COUNT(*) FROM followups fu WHERE fu.round_id = r.id) AS findings, "
        "(SELECT COUNT(*) FROM followups fu WHERE fu.round_id = r.id AND fu.mgmt_updated_on IS NOT NULL) AS answered "
        "FROM rounds r ORDER BY r.follow_up_date DESC"))
    _show(rounds)


def page_import(db, user):
    st.header("Import findings and sample data")
    st.write("Upload an Excel file with these 14 columns, in this order:")
    st.code(" | ".join(MASTER_COLUMNS))
    st.download_button("Download an empty import template",
                       to_excel_bytes({"Findings": pd.DataFrame(columns=MASTER_COLUMNS)}),
                       file_name="import_template.xlsx")
    upload = st.file_uploader("Excel file (.xlsx)", type=["xlsx"])
    if upload is not None and st.button("Import this file"):
        try:
            df = pd.read_excel(upload, dtype=object)
            result = import_findings(db, df, user["username"])
            st.success(f"{result['inserted']} finding(s) imported, {result['skipped']} row(s) rejected.")
            if result["errors"]:
                _show(pd.DataFrame(result["errors"], columns=["Excel row", "Problem"]))
        except Exception as exc:
            st.error(str(exc))

    st.subheader("Sample (dummy) data for testing")
    st.caption("Adds 30-50 invented findings per department plus 3 past rounds and 1 current round.")
    if st.button("Load sample data"):
        try:
            res = load_sample_data(db, user)
            st.success(f"Loaded {res['findings']} findings. {res['pending_in_current_round']} items are "
                       "waiting for a response in the current round.")
        except (ValueError, PermissionError) as exc:
            st.error(str(exc))

    st.subheader("Remove all findings (keeps users)")
    confirm = st.text_input("Type WIPE to confirm")
    if st.button("Delete all findings, rounds and follow-ups"):
        if confirm.strip() == "WIPE":
            wipe_all_data(db, user)
            st.success("All findings, rounds and follow-ups were deleted.")
        else:
            st.error("Type WIPE in the box first.")

    st.subheader("Export")
    st.download_button("Download full register (current status)",
                       to_excel_bytes({"Current status": get_status_table(db).drop(columns=["id"])}),
                       file_name="findings_current_status.xlsx")
    st.download_button("Download wide layout (one block per follow-up date)",
                       to_excel_bytes({"Wide": build_wide_export(db)}), file_name="findings_wide_layout.xlsx")


def page_logs(db, user):
    st.header("Audit trail and e-mail log")
    tab1, tab2 = st.tabs(["Audit trail", "E-mail log"])
    with tab1:
        _show(pd.DataFrame(db.fetch("SELECT * FROM audit_trail ORDER BY id DESC LIMIT 1000")))
    with tab2:
        _show(pd.DataFrame(db.fetch("SELECT * FROM email_log ORDER BY id DESC LIMIT 1000")))


def page_users(db, user):
    st.header("Users")
    rows = pd.DataFrame(db.fetch("SELECT id, username, role, department, email, active FROM users ORDER BY id"))
    edited = st.data_editor(rows, disabled=["id", "username", "role", "department"], hide_index=True)
    if st.button("Save e-mail addresses and active flags"):
        with db.session() as conn:
            for _, r in edited.iterrows():
                db.execute(conn, "UPDATE users SET email = ?, active = ? WHERE id = ?",
                           (clean_text(r["email"]), 1 if r["active"] else 0, int(r["id"])))
            log_change(db, conn, user["username"], "edit", "users", "-", "email/active", None, "saved")
        st.success("Saved.")
    st.subheader("Reset a password")
    with st.form("pw_form"):
        who = st.selectbox("User", list(rows["username"]))
        new_pw = st.text_input("New password", type="password")
        submitted = st.form_submit_button("Reset password")
    if submitted:
        if len(new_pw) < 8:
            st.error("Use at least 8 characters.")
        else:
            with db.session() as conn:
                db.execute(conn, "UPDATE users SET password_hash = ? WHERE username = ?", (hash_password(new_pw), who))
                log_change(db, conn, user["username"], "password_reset", "users", who)
            st.success(f"Password for {who} was reset.")


def ui_login(db):
    st.title(APP_TITLE)
    st.write("Please sign in.")
    with st.form("login_form"):
        username = st.text_input("User name")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")
    if submitted:
        user = authenticate(db, username, password)
        if user:
            st.session_state["user"] = user
            st.rerun()
        else:
            st.error("Wrong user name or password.")
    if setting_bool("SHOW_TEST_LOGIN_HINT", True):
        st.info("TEST VERSION. User names: 'Audit Admin', 'Management', or a department user such as "
                "'Credit 1', 'Credit 2', 'Risk 1', 'Branch 3 2', 'Compliance, Recovery and Legal 1'. "
                f"Password for all test users: {get_setting('DEFAULT_PASSWORD', 'Test@123')}")


def ui_main(db):
    user = st.session_state.get("user")
    if not user:
        ui_login(db)
        return
    if st.session_state.get("flash"):
        st.success(st.session_state.pop("flash"))
    pages = {"Dashboard": page_dashboard}
    if user["role"] == ROLE_ADMIN:
        pages.update({"Findings register": page_findings, "Review responses": page_review,
                      "Rounds and reminders": page_rounds, "Import and sample data": page_import,
                      "Audit trail and e-mail log": page_logs, "Users": page_users})
    elif user["role"] == ROLE_OWNER:
        pages.update({"Respond to findings": page_my_updates, "Findings register": page_findings})
        pages = {k: pages[k] for k in ("Respond to findings", "Dashboard", "Findings register")}
    else:
        pages.update({"Findings register": page_findings})
    st.sidebar.title(APP_TITLE)
    st.sidebar.write(f"Signed in as **{user['username']}**  \n{user['role']}")
    choice = st.sidebar.radio("Go to", list(pages))
    if st.sidebar.button("Sign out"):
        st.session_state.pop("user", None)
        st.rerun()
    pages[choice](db, user)


def main():
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    db = Database()
    if not st.session_state.get("db_ready"):
        init_db(db)
        st.session_state["db_ready"] = True
    ui_main(db)


if __name__ == "__main__":
    if st is None:
        print("Streamlit is not installed. Run:  pip install -r requirements.txt  "
              "and then:  streamlit run app.py")
    else:
        main()
