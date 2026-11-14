"""SQLite persistence layer."""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
EXPORT_DIR = os.path.join(DATA_DIR, "exports")
DB_PATH = os.path.join(DATA_DIR, "internal_audit.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    short_code TEXT,
    company_type TEXT DEFAULT 'Single Entity',
    industries TEXT DEFAULT '[]',
    country TEXT,
    base_currency TEXT DEFAULT 'AED',
    fiscal_year_end TEXT DEFAULT '31-Dec',
    reg_no TEXT,
    address TEXT,
    head_of_audit TEXT,
    audit_committee_chair TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    entity_type TEXT DEFAULT 'Subsidiary',
    parent_id INTEGER,
    country TEXT,
    currency TEXT,
    industry TEXT,
    ownership_pct REAL DEFAULT 100,
    entity_head TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS auditors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    designation TEXT,
    role TEXT DEFAULT 'Auditor',
    email TEXT,
    certifications TEXT
);
CREATE TABLE IF NOT EXISTS universe (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    entity_id INTEGER,
    process_code TEXT,
    process_name TEXT,
    industry TEXT,
    process_owner TEXT,
    f_financial INTEGER DEFAULT 3,
    f_fraud INTEGER DEFAULT 3,
    f_regulatory INTEGER DEFAULT 3,
    f_complexity INTEGER DEFAULT 3,
    f_change INTEGER DEFAULT 3,
    f_control_env INTEGER DEFAULT 3,
    impact INTEGER DEFAULT 3,
    likelihood INTEGER DEFAULT 3,
    risk_score REAL DEFAULT 60,
    risk_level TEXT DEFAULT 'Medium',
    audit_frequency TEXT,
    last_audit_date TEXT,
    last_rating TEXT,
    notes TEXT
);
CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    year INTEGER,
    title TEXT,
    status TEXT DEFAULT 'Draft',
    available_hours REAL DEFAULT 0,
    approved_by TEXT,
    approved_on TEXT,
    notes TEXT
);
CREATE TABLE IF NOT EXISTS engagements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    plan_id INTEGER,
    entity_id INTEGER,
    universe_id INTEGER,
    ref TEXT,
    title TEXT NOT NULL,
    audit_type TEXT DEFAULT 'Assurance',
    status TEXT DEFAULT 'Planned',
    quarter TEXT,
    objective TEXT,
    scope TEXT,
    out_of_scope TEXT,
    methodology TEXT,
    period_from TEXT,
    period_to TEXT,
    planned_start TEXT,
    planned_end TEXT,
    actual_start TEXT,
    actual_end TEXT,
    lead_auditor TEXT,
    reviewer TEXT,
    team TEXT,
    auditee_contact TEXT,
    budget_hours REAL DEFAULT 0,
    overall_rating TEXT,
    executive_summary TEXT,
    report_date TEXT,
    process_codes TEXT DEFAULT '[]',
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS procedures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    engagement_id INTEGER NOT NULL,
    process_code TEXT,
    subprocess TEXT,
    risk_id TEXT,
    risk TEXT,
    risk_rating TEXT,
    assertion TEXT,
    control_id TEXT,
    control TEXT,
    control_type TEXT,
    control_nature TEXT,
    frequency TEXT,
    key_control INTEGER DEFAULT 0,
    fraud_risk INTEGER DEFAULT 0,
    steps TEXT,
    population INTEGER,
    sample_size INTEGER,
    sample_method TEXT,
    design_result TEXT DEFAULT 'Not Tested',
    oe_result TEXT DEFAULT 'Not Tested',
    testing_notes TEXT,
    conclusion TEXT,
    wp_ref TEXT,
    status TEXT DEFAULT 'Not Started',
    prepared_by TEXT,
    prepared_on TEXT,
    reviewed_by TEXT,
    reviewed_on TEXT,
    sort INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS pbc (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    engagement_id INTEGER NOT NULL,
    item TEXT,
    process_code TEXT,
    requested_from TEXT,
    requested_on TEXT,
    due_on TEXT,
    status TEXT DEFAULT 'Requested',
    received_on TEXT,
    remarks TEXT
);
CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    engagement_id INTEGER,
    procedure_id INTEGER,
    entity_id INTEGER,
    ref TEXT,
    title TEXT NOT NULL,
    process_code TEXT,
    rating TEXT DEFAULT 'Medium',
    category TEXT,
    root_cause_category TEXT,
    condition TEXT,
    criteria TEXT,
    cause TEXT,
    effect TEXT,
    recommendation TEXT,
    financial_impact REAL DEFAULT 0,
    mgmt_response TEXT,
    action_plan TEXT,
    owner TEXT,
    owner_email TEXT,
    due_date TEXT,
    revised_due_date TEXT,
    status TEXT DEFAULT 'Open',
    repeat_finding INTEGER DEFAULT 0,
    closed_on TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS followups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_id INTEGER NOT NULL,
    update_date TEXT,
    update_text TEXT,
    status TEXT,
    updated_by TEXT
);
CREATE TABLE IF NOT EXISTS review_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    engagement_id INTEGER NOT NULL,
    procedure_id INTEGER,
    note TEXT,
    raised_by TEXT,
    raised_on TEXT,
    response TEXT,
    status TEXT DEFAULT 'Open',
    cleared_by TEXT,
    cleared_on TEXT
);
CREATE TABLE IF NOT EXISTS time_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    engagement_id INTEGER NOT NULL,
    auditor TEXT,
    entry_date TEXT,
    hours REAL DEFAULT 0,
    phase TEXT DEFAULT 'Fieldwork',
    description TEXT
);
CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    engagement_id INTEGER,
    procedure_id INTEGER,
    finding_id INTEGER,
    filename TEXT,
    stored_name TEXT,
    size INTEGER,
    description TEXT,
    uploaded_on TEXT
);
CREATE TABLE IF NOT EXISTS analytics_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    engagement_id INTEGER,
    test TEXT,
    file_name TEXT,
    params TEXT,
    total_records INTEGER,
    exceptions INTEGER,
    result TEXT,
    run_on TEXT
);
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    ts TEXT,
    entity TEXT,
    entity_id INTEGER,
    action TEXT,
    details TEXT
);
"""

_COLUMNS = {}


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today():
    return datetime.now().strftime("%Y-%m-%d")


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def session():
    """Open a connection, commit on success and always close it."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    for d in (DATA_DIR, UPLOAD_DIR, EXPORT_DIR):
        os.makedirs(d, exist_ok=True)
    with session() as conn:
        conn.executescript(SCHEMA)


def columns(table):
    if table not in _COLUMNS:
        with session() as conn:
            _COLUMNS[table] = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})")]
    return _COLUMNS[table]


def query(sql, params=()):
    with session() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def one(sql, params=()):
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql, params=()):
    with session() as conn:
        cur = conn.execute(sql, params)
        return cur.lastrowid


def _clean(table, data):
    cols = set(columns(table)) - {"id"}
    out = {}
    for k, v in (data or {}).items():
        if k in cols:
            if isinstance(v, (list, dict)):
                v = json.dumps(v)
            elif isinstance(v, bool):
                v = int(v)
            out[k] = v
    return out


def insert(table, data):
    data = _clean(table, data)
    if "created_at" in columns(table) and not data.get("created_at"):
        data["created_at"] = now()
    keys = list(data.keys())
    sql = f"INSERT INTO {table} ({', '.join(keys)}) VALUES ({', '.join('?' for _ in keys)})"
    return execute(sql, [data[k] for k in keys])


def insert_many(table, rows):
    if not rows:
        return
    rows = [_clean(table, r) for r in rows]
    keys = list(rows[0].keys())
    sql = f"INSERT INTO {table} ({', '.join(keys)}) VALUES ({', '.join('?' for _ in keys)})"
    with session() as conn:
        conn.executemany(sql, [[r.get(k) for k in keys] for r in rows])


def update(table, row_id, data):
    data = _clean(table, data)
    data.pop("created_at", None)
    if not data:
        return
    sets = ", ".join(f"{k} = ?" for k in data)
    execute(f"UPDATE {table} SET {sets} WHERE id = ?", list(data.values()) + [row_id])


def delete(table, row_id):
    execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))


def log(company_id, entity, entity_id, action, details=""):
    execute("INSERT INTO activity_log (company_id, ts, entity, entity_id, action, details) VALUES (?,?,?,?,?,?)",
            (company_id, now(), entity, entity_id, action, details))
