"""
SQLite Database and Local Persistence for MarketMatch.
Maintains uploaded file audits, file hashes (duplicate detection), settings,
value mappings, exceptions workflow, and external tax returns (GSTR-8, Form 26AS).
"""
import sqlite3
import os
from decimal import Decimal
from typing import Dict, Any, List, Optional
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "marketmatch.db")


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    """Initialize database tables if they do not exist."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    # Uploaded files audit table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS uploaded_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_type TEXT NOT NULL,
        file_name TEXT NOT NULL,
        file_hash TEXT NOT NULL,
        upload_timestamp TEXT NOT NULL,
        period_month INTEGER NOT NULL,
        period_year INTEGER NOT NULL,
        row_count INTEGER NOT NULL,
        valid_count INTEGER NOT NULL,
        error_count INTEGER NOT NULL
    );
    """)

    # App Settings
    cur.execute("""
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)

    # Exceptions tracker
    cur.execute("""
    CREATE TABLE IF NOT EXISTS exceptions (
        id TEXT PRIMARY KEY,
        order_id TEXT NOT NULL,
        invoice_no TEXT,
        reason_code TEXT NOT NULL,
        description TEXT NOT NULL,
        recoverable_amount REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'Open',
        notes TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        source_ref TEXT
    );
    """)

    # User Value Mappings (when value_formats_verified is false)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS value_mappings (
        profile_key TEXT NOT NULL,
        field_name TEXT NOT NULL,
        source_value TEXT NOT NULL,
        mapped_value TEXT NOT NULL,
        PRIMARY KEY (profile_key, field_name, source_value)
    );
    """)

    # External Tax Figures (GSTR-8 and Form 26AS)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS external_figures (
        period_key TEXT PRIMARY KEY,
        gstr8_net_taxable REAL DEFAULT 0.0,
        gstr8_tcs REAL DEFAULT 0.0,
        form26as_tds REAL DEFAULT 0.0
    );
    """)

    conn.commit()
    conn.close()

    # Seed default settings if empty
    defaults = {
        "tolerance": "1.00",
        "unpaid_threshold_days": "10",
        "b2cl_threshold": "100000.00",
        "tcs_statutory_rate": "0.005",   # 0.5%
        "tds_statutory_rate": "0.001",   # 0.1% Section 194-O
        "gst_rate_on_fees": "0.18",      # 18%
        "seller_name": "Ishwaryam Goodness",
        "seller_gstin": "33AAJFI0296H1ZE",
        "as_of_date": datetime.now().strftime("%Y-%m-%d")
    }
    for k, v in defaults.items():
        if get_setting(k, db_path=db_path) is None:
            set_setting(k, v, db_path=db_path)


def get_setting(key: str, default: Optional[str] = None, db_path: str = DB_PATH) -> Optional[str]:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    if row:
        return row["value"]
    return default


def set_setting(key: str, value: str, db_path: str = DB_PATH) -> None:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def get_all_settings(db_path: str = DB_PATH) -> Dict[str, Any]:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM app_settings")
    rows = cur.fetchall()
    conn.close()
    res = {row["key"]: row["value"] for row in rows}
    return {
        "tolerance": Decimal(res.get("tolerance", "1.00")),
        "unpaid_threshold_days": int(res.get("unpaid_threshold_days", "10")),
        "b2cl_threshold": Decimal(res.get("b2cl_threshold", "100000.00")),
        "tcs_statutory_rate": Decimal(res.get("tcs_statutory_rate", "0.005")),
        "tds_statutory_rate": Decimal(res.get("tds_statutory_rate", "0.001")),
        "gst_rate_on_fees": Decimal(res.get("gst_rate_on_fees", "0.18")),
        "seller_name": res.get("seller_name", ""),
        "seller_gstin": res.get("seller_gstin", ""),
        "as_of_date": res.get("as_of_date", datetime.now().strftime("%Y-%m-%d"))
    }


def record_uploaded_file(
    file_type: str,
    file_name: str,
    file_hash: str,
    period_month: int,
    period_year: int,
    row_count: int,
    valid_count: int,
    error_count: int,
    db_path: str = DB_PATH
) -> int:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO uploaded_files (
        file_type, file_name, file_hash, upload_timestamp,
        period_month, period_year, row_count, valid_count, error_count
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        file_type, file_name, file_hash, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        period_month, period_year, row_count, valid_count, error_count
    ))
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id


def is_file_duplicate(file_hash: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM uploaded_files WHERE file_hash = ? ORDER BY id DESC LIMIT 1", (file_hash,))
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def upsert_exception(
    exc_id: str,
    order_id: str,
    invoice_no: str,
    reason_code: str,
    description: str,
    recoverable_amount: float,
    status: str = "Open",
    notes: str = "",
    source_ref: str = "",
    db_path: str = DB_PATH
) -> None:
    conn = get_connection(db_path)
    cur = conn.cursor()
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
    INSERT INTO exceptions (
        id, order_id, invoice_no, reason_code, description,
        recoverable_amount, status, notes, created_at, updated_at, source_ref
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        reason_code=excluded.reason_code,
        description=excluded.description,
        recoverable_amount=excluded.recoverable_amount,
        updated_at=excluded.updated_at,
        source_ref=excluded.source_ref
    """, (
        exc_id, order_id, invoice_no, reason_code, description,
        recoverable_amount, status, notes, now_str, now_str, source_ref
    ))
    conn.commit()
    conn.close()


def update_exception_status(exc_id: str, status: str, notes: Optional[str] = None, db_path: str = DB_PATH) -> None:
    conn = get_connection(db_path)
    cur = conn.cursor()
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    if notes is not None:
        cur.execute("UPDATE exceptions SET status = ?, notes = ?, updated_at = ? WHERE id = ?", (status, notes, now_str, exc_id))
    else:
        cur.execute("UPDATE exceptions SET status = ?, updated_at = ? WHERE id = ?", (status, now_str, exc_id))
    conn.commit()
    conn.close()


def get_all_exceptions(status_filter: Optional[str] = None, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    cur = conn.cursor()
    if status_filter:
        cur.execute("SELECT * FROM exceptions WHERE status = ? ORDER BY recoverable_amount DESC", (status_filter,))
    else:
        cur.execute("SELECT * FROM exceptions ORDER BY recoverable_amount DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_value_mappings(profile_key: str, field_name: str, db_path: str = DB_PATH) -> Dict[str, str]:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT source_value, mapped_value FROM value_mappings WHERE profile_key = ? AND field_name = ?", (profile_key, field_name))
    rows = cur.fetchall()
    conn.close()
    return {r["source_value"]: r["mapped_value"] for r in rows}


def set_value_mapping(profile_key: str, field_name: str, source_value: str, mapped_value: str, db_path: str = DB_PATH) -> None:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("""
    INSERT OR REPLACE INTO value_mappings (profile_key, field_name, source_value, mapped_value)
    VALUES (?, ?, ?, ?)
    """, (profile_key, field_name, source_value, mapped_value))
    conn.commit()
    conn.close()


def get_external_figures(period_key: str, db_path: str = DB_PATH) -> Dict[str, Decimal]:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM external_figures WHERE period_key = ?", (period_key,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "gstr8_net_taxable": Decimal(str(row["gstr8_net_taxable"])),
            "gstr8_tcs": Decimal(str(row["gstr8_tcs"])),
            "form26as_tds": Decimal(str(row["form26as_tds"]))
        }
    return {
        "gstr8_net_taxable": Decimal("0.00"),
        "gstr8_tcs": Decimal("0.00"),
        "form26as_tds": Decimal("0.00")
    }


def set_external_figures(period_key: str, gstr8_net_taxable: Decimal, gstr8_tcs: Decimal, form26as_tds: Decimal, db_path: str = DB_PATH) -> None:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("""
    INSERT OR REPLACE INTO external_figures (period_key, gstr8_net_taxable, gstr8_tcs, form26as_tds)
    VALUES (?, ?, ?, ?)
    """, (period_key, float(gstr8_net_taxable), float(gstr8_tcs), float(form26as_tds)))
    conn.commit()
    conn.close()
