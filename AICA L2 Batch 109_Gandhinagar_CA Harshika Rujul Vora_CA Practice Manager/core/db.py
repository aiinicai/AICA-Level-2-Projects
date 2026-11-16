"""Database layer. Same code runs on SQLite (local / offline) and PostgreSQL (Supabase cloud).

Dates are stored as ISO text ('YYYY-MM-DD', timestamps 'YYYY-MM-DD HH:MM:SS') so that
comparisons and sorting behave identically on both databases.
"""
from sqlalchemy import create_engine, event, text

from . import clock, config

_ENGINE = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id {PK},
    name TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,                 -- Partner / Manager / Staff
    email TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    must_change INTEGER NOT NULL DEFAULT 0,
    created_on TEXT
);
CREATE TABLE IF NOT EXISTS clients (
    id {PK},
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    pan TEXT,
    gstin TEXT,
    state TEXT,
    contact_person TEXT,
    email TEXT,
    phone TEXT,
    gst_freq TEXT DEFAULT 'None',       -- None / Monthly / Quarterly
    has_tds INTEGER DEFAULT 0,
    needs_itr INTEGER DEFAULT 1,
    needs_audit INTEGER DEFAULT 0,
    monthly_fee REAL DEFAULT 0,
    manager_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_on TEXT
);
CREATE TABLE IF NOT EXISTS tasks (
    id {PK},
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    rule_code TEXT,                     -- NULL for manual tasks
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    period TEXT,
    due_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'To Do',
    priority TEXT DEFAULT 'Medium',
    assigned_to INTEGER REFERENCES users(id) ON DELETE SET NULL,
    notes TEXT,
    completed_on TEXT,
    updated_on TEXT,
    UNIQUE (client_id, rule_code, period)
);
CREATE TABLE IF NOT EXISTS task_log (
    id {PK},
    task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    detail TEXT,
    at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS invoices (
    id {PK},
    invoice_no TEXT NOT NULL UNIQUE,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    invoice_date TEXT NOT NULL,
    due_date TEXT,
    description TEXT,
    sac TEXT,
    taxable_value REAL NOT NULL,
    gst_rate REAL NOT NULL,
    cgst REAL DEFAULT 0,
    sgst REAL DEFAULT 0,
    igst REAL DEFAULT 0,
    total REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'Unpaid',
    paid_on TEXT,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS documents (
    id {PK},
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    fin_year TEXT,
    filename TEXT NOT NULL,
    mime TEXT,
    size_bytes INTEGER,
    content {BLOB} NOT NULL,
    uploaded_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    uploaded_on TEXT
);
CREATE TABLE IF NOT EXISTS due_date_rules (
    id {PK},
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    frequency TEXT NOT NULL,
    schedule TEXT NOT NULL,
    applies_to TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS due_date_overrides (
    id {PK},
    rule_code TEXT NOT NULL,
    period TEXT NOT NULL,
    due_date TEXT NOT NULL,
    note TEXT,
    UNIQUE (rule_code, period)
);
CREATE TABLE IF NOT EXISTS ai_log (
    id {PK},
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    feature TEXT NOT NULL,
    model TEXT,
    chars_sent INTEGER,
    at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
CREATE INDEX IF NOT EXISTS ix_tasks_due ON tasks(due_date);
CREATE INDEX IF NOT EXISTS ix_tasks_assignee ON tasks(assigned_to);
CREATE INDEX IF NOT EXISTS ix_log_at ON task_log(at);
"""


def engine():
    global _ENGINE
    if _ENGINE is None:
        url = config.database_url()
        if url.startswith("sqlite"):
            _ENGINE = create_engine(url, connect_args={"check_same_thread": False})

            @event.listens_for(_ENGINE, "connect")
            def _fk_on(dbapi_conn, _):
                dbapi_conn.execute("PRAGMA foreign_keys=ON")
        else:
            _ENGINE = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5, pool_recycle=300)
    return _ENGINE


def explain_url_problem(url: str, error: str = "") -> str | None:
    """Plain-language reason a connection string fails, for the common mistakes."""
    u = (url or "").strip()
    if not u:
        return None
    if "[YOUR-PASSWORD]" in u or "YOUR-PASSWORD" in u or "[" in u.split("@")[0]:
        return "The connection string still contains [YOUR-PASSWORD]. Replace it, including the square brackets, with your Supabase database password."
    rest = u.split("://", 1)[-1]
    if rest.count("@") > 1:
        if ":@" in rest:
            return ("There is an extra @ right after the colon, before your password (…:@password@…). Delete that "
                    "first @ so it reads …:password@aws-…")
        return ("The connection string contains more than one @. If your password itself contains @, reset the "
                "database password in Supabase to one without @ : / # ? and use the new one.")
    if "db." in u and ".supabase.co" in u and "pooler" not in u:
        return ("This is Supabase's 'Direct connection' string, which needs IPv6. Use the Session pooler string "
                "instead (Connect → Direct → Session pooler).")
    if ":6543" in u:
        return "This looks like the Transaction pooler (port 6543). Use the Session pooler string (port 5432)."
    low = error.lower()
    if "password authentication failed" in low:
        return "The database password is wrong. Check it, or reset it in Supabase → Project Settings → Database."
    if "could not translate host name" in low or "name or service not known" in low or "getaddrinfo" in low:
        return "The server name couldn't be found. Check your internet connection and that the string was copied in full."
    if "timeout" in low or "timed out" in low:
        return "The connection timed out. Check your internet connection, and that the Supabase project isn't paused."
    return None


def test_url(url: str) -> tuple[bool, str]:
    """Try a connection string without changing the app's own connection."""
    try:
        u = url.strip().replace("postgres://", "postgresql://", 1).replace("postgresql://", "postgresql+psycopg2://", 1)
        if "supabase" in u and "sslmode=" not in u:
            u += ("&" if "?" in u else "?") + "sslmode=require"
        eng = create_engine(u, connect_args={"connect_timeout": 10})
        with eng.connect() as c:
            c.execute(text("SELECT 1"))
        eng.dispose()
        return True, ""
    except Exception as e:
        return False, (str(e).splitlines() or ["unknown error"])[0][:300]


def reset_engine():
    global _ENGINE
    if _ENGINE is not None:
        _ENGINE.dispose()
    _ENGINE = None


def is_postgres() -> bool:
    return engine().dialect.name == "postgresql"


def now() -> str:
    return clock.now().strftime("%Y-%m-%d %H:%M:%S")


def init_db():
    pg = is_postgres()
    ddl = SCHEMA.replace("{PK}", "SERIAL PRIMARY KEY" if pg else "INTEGER PRIMARY KEY AUTOINCREMENT")
    ddl = ddl.replace("{BLOB}", "BYTEA" if pg else "BLOB")
    with engine().begin() as c:
        for stmt in [s.strip() for s in ddl.split(";") if s.strip()]:
            c.execute(text(stmt))


def query(sql: str, **params) -> list[dict]:
    with engine().connect() as c:
        return [dict(r._mapping) for r in c.execute(text(sql), params)]


def one(sql: str, **params):
    rows = query(sql, **params)
    return rows[0] if rows else None


def scalar(sql: str, **params):
    with engine().connect() as c:
        return c.execute(text(sql), params).scalar()


def execute(sql: str, **params) -> int:
    """Run INSERT/UPDATE/DELETE. Returns affected row count."""
    with engine().begin() as c:
        return c.execute(text(sql), params).rowcount


def insert(sql: str, **params):
    """Run an INSERT ... RETURNING id. Returns the new id (or None if nothing inserted)."""
    with engine().begin() as c:
        row = c.execute(text(sql), params).first()
        return row[0] if row else None


def get_setting(key: str, default=None):
    row = one("SELECT value FROM app_settings WHERE key=:k", k=key)
    return row["value"] if row and row["value"] is not None else default


def set_setting(key: str, value):
    execute("INSERT INTO app_settings(key, value) VALUES (:k, :v) "
            "ON CONFLICT (key) DO UPDATE SET value = excluded.value", k=key, v=None if value is None else str(value))


def log(task_id, user_id, action, detail=""):
    execute("INSERT INTO task_log(task_id,user_id,action,detail,at) VALUES (:t,:u,:a,:d,:at)",
            t=task_id, u=user_id, a=action, d=detail, at=now())
