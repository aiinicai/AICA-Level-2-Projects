"""SQLite DDL and initialization (§13)."""
import sqlite3
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE COLLATE NOCASE NOT NULL,
    cin TEXT DEFAULT '',
    fy_end TEXT DEFAULT '',
    units TEXT DEFAULT 'Lacs',
    schedule_division TEXT DEFAULT 'Division I',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    year_type TEXT CHECK(year_type IN ('CY','PY')) NOT NULL,
    file_name TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    sheet_map_json TEXT,
    period_columns_json TEXT,
    uploaded_at TEXT NOT NULL,
    FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS line_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_id INTEGER NOT NULL,
    sheet TEXT NOT NULL,
    row_no INTEGER NOT NULL,
    raw_label TEXT,
    normalised_label TEXT,
    amount_reporting REAL,
    amount_comparative REAL,
    FOREIGN KEY(upload_id) REFERENCES uploads(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    component_key TEXT NOT NULL,
    source_sheet TEXT NOT NULL,
    source_row INTEGER,
    source_label TEXT,
    confidence TEXT,
    resolution_rule TEXT,
    is_manual INTEGER DEFAULT 0,
    manual_amount_cy REAL,
    manual_amount_py REAL,
    remark TEXT,
    FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS assumptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    input_key TEXT NOT NULL,
    value_cy REAL,
    value_py REAL,
    is_default INTEGER DEFAULT 1,
    basis TEXT CHECK(basis IN ('extracted','derived','default','manual')),
    note TEXT,
    FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    fy_label TEXT NOT NULL,
    threshold_pct REAL DEFAULT 25.0,
    created_at TEXT NOT NULL,
    FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ratio_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL,
    ratio_key TEXT NOT NULL,
    numerator_cy REAL,
    denominator_cy REAL,
    value_cy REAL,
    numerator_py REAL,
    denominator_py REAL,
    value_py REAL,
    variance_pct REAL,
    is_flagged INTEGER DEFAULT 0,
    status TEXT,
    reason_generated TEXT,
    reason_final TEXT,
    is_reason_edited INTEGER DEFAULT 0,
    FOREIGN KEY(analysis_id) REFERENCES analyses(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS integrity_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL,
    check_id TEXT NOT NULL,
    expected TEXT,
    actual TEXT,
    status TEXT,
    comment TEXT,
    FOREIGN KEY(analysis_id) REFERENCES analyses(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    detail TEXT NOT NULL,
    FOREIGN KEY(analysis_id) REFERENCES analyses(id) ON DELETE CASCADE
);
"""


def init_database(db_path: Path) -> sqlite3.Connection:
    """Initialize SQLite database with full schema. Ships completely empty."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn
