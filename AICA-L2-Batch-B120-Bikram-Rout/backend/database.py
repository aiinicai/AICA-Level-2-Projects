import sqlite3
import os
import json
from decimal import Decimal
from datetime import datetime

DB_PATH = os.environ.get("BRS_DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "brs.db"))

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL, -- Administrator, Preparer, Reviewer, Approver, Auditor
            email TEXT
        );

        CREATE TABLE IF NOT EXISTS companies (
            id TEXT PRIMARY KEY,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            reporting_currency TEXT NOT NULL DEFAULT 'USD',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS bank_accounts (
            id TEXT PRIMARY KEY,
            company_id TEXT NOT NULL REFERENCES companies(id),
            bank_name TEXT NOT NULL,
            branch TEXT,
            account_number TEXT NOT NULL,
            iban TEXT,
            currency TEXT NOT NULL DEFAULT 'USD',
            gl_account TEXT NOT NULL,
            ledger TEXT,
            legal_entity TEXT,
            owner TEXT,
            preparer TEXT,
            reviewer TEXT,
            approver TEXT,
            status TEXT NOT NULL DEFAULT 'Active',
            opening_balance REAL NOT NULL DEFAULT 0.0,
            recon_start_date TEXT,
            gl_sub_account TEXT,
            gl_allocation_rule TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS periods (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL REFERENCES bank_accounts(id),
            period_name TEXT NOT NULL, -- e.g. '2026-09', '2026-10'
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Draft', -- Draft, In Progress, Submitted, Reviewed, Approved, Locked
            bank_opening_balance REAL DEFAULT 0.0,
            bank_closing_balance REAL DEFAULT 0.0,
            ledger_opening_balance REAL DEFAULT 0.0,
            ledger_closing_balance REAL DEFAULT 0.0,
            residual_diff REAL DEFAULT 0.0,
            locked_at TEXT,
            locked_by TEXT,
            approved_by TEXT,
            reviewed_by TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL REFERENCES bank_accounts(id),
            period_id TEXT REFERENCES periods(id),
            source TEXT NOT NULL, -- 'Oracle Ledger' or 'Bank Statement'
            tx_date TEXT NOT NULL,
            posting_date TEXT,
            value_date TEXT,
            description TEXT NOT NULL,
            counterparty TEXT,
            reference TEXT,
            cheque_number TEXT,
            payment_id TEXT,
            journal_id TEXT,
            debit REAL DEFAULT 0.0,
            credit REAL DEFAULT 0.0,
            signed_amount REAL NOT NULL, -- Exact signed cash flow (+ inflow / deposit, - outflow / payment)
            currency TEXT NOT NULL DEFAULT 'USD',
            running_balance REAL,
            doc_name TEXT,
            doc_row INTEGER,
            batch_id TEXT,
            validation_status TEXT DEFAULT 'Valid', -- Valid, Warning, Rejected, Duplicate Candidate
            recon_status TEXT DEFAULT 'Unmatched', -- Unmatched, Suggested Match, Matched, Partially Matched, Exception, Carried Forward
            match_group_id TEXT,
            allocated_amount REAL DEFAULT 0.0,
            category TEXT, -- 'Outstanding Cheque', 'Deposit in Transit', 'Bank Charge', 'Interest', 'Timing Difference', 'Direct Debit', 'Error'
            flags TEXT,
            cleared_period_id TEXT,
            cleared_date TEXT,
            original_period_id TEXT,
            confidence_score REAL DEFAULT 1.0,
            is_uncertain INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS match_groups (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL REFERENCES bank_accounts(id),
            period_id TEXT REFERENCES periods(id),
            rule_name TEXT NOT NULL,
            match_type TEXT NOT NULL, -- '1-to-1', '1-to-Many', 'Many-to-1', 'Many-to-Many', 'Manual', 'Partial'
            matched_at TEXT NOT NULL,
            matched_by TEXT NOT NULL,
            notes TEXT,
            difference REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Confirmed' -- 'Confirmed', 'Suggested', 'Rejected'
        );

        CREATE TABLE IF NOT EXISTS match_group_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_group_id TEXT NOT NULL REFERENCES match_groups(id) ON DELETE CASCADE,
            transaction_id TEXT NOT NULL REFERENCES transactions(id),
            allocated_amount REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS uploaded_files (
            id TEXT PRIMARY KEY,
            file_hash TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_size INTEGER DEFAULT 0,
            uploaded_at TEXT NOT NULL,
            uploaded_by TEXT NOT NULL,
            account_id TEXT NOT NULL,
            period_id TEXT NOT NULL,
            source_type TEXT NOT NULL,
            batch_id TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user TEXT NOT NULL,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            before_value TEXT,
            after_value TEXT,
            reason TEXT,
            ip_address TEXT
        );

        CREATE TABLE IF NOT EXISTS rules (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            priority INTEGER NOT NULL,
            rule_type TEXT NOT NULL,
            date_tolerance_days INTEGER DEFAULT 0,
            amount_tolerance REAL DEFAULT 0.0,
            is_active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS exchange_rates (
            from_currency TEXT NOT NULL,
            to_currency TEXT NOT NULL,
            rate REAL NOT NULL,
            rate_date TEXT NOT NULL,
            source TEXT DEFAULT 'Central Bank',
            PRIMARY KEY (from_currency, to_currency, rate_date)
        );

        CREATE INDEX IF NOT EXISTS idx_tx_account ON transactions(account_id);
        CREATE INDEX IF NOT EXISTS idx_tx_period ON transactions(period_id);
        CREATE INDEX IF NOT EXISTS idx_tx_status ON transactions(recon_status);
        CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(tx_date);
        CREATE INDEX IF NOT EXISTS idx_tx_signed_amt ON transactions(signed_amount);
        CREATE INDEX IF NOT EXISTS idx_tx_ref ON transactions(reference);
        CREATE INDEX IF NOT EXISTS idx_periods_account ON periods(account_id);
        CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_logs(timestamp);
        CREATE INDEX IF NOT EXISTS idx_uploaded_hash ON uploaded_files(file_hash);
        """)

        # Automatic schema migrations for existing DBs
        table_columns = {
            "transactions": [
                ("cleared_period_id", "TEXT"),
                ("cleared_date", "TEXT"),
                ("original_period_id", "TEXT"),
                ("confidence_score", "REAL DEFAULT 1.0"),
                ("is_uncertain", "INTEGER DEFAULT 0")
            ],
            "bank_accounts": [
                ("gl_sub_account", "TEXT"),
                ("gl_allocation_rule", "TEXT")
            ]
        }
        for table, cols in table_columns.items():
            cur = conn.cursor()
            cur.execute(f"PRAGMA table_info({table})")
            existing_cols = [r[1] for r in cur.fetchall()]
            for col_name, col_def in cols:
                if col_name not in existing_cols:
                    try:
                        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")
                    except Exception:
                        pass
    conn.close()

def log_audit(conn, user, action, entity_type, entity_id, before_val=None, after_val=None, reason=None, ip="127.0.0.1"):
    conn.execute("""
        INSERT INTO audit_logs (timestamp, user, action, entity_type, entity_id, before_value, after_value, reason, ip_address)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        user,
        action,
        entity_type,
        str(entity_id),
        json.dumps(before_val) if isinstance(before_val, (dict, list)) else (str(before_val) if before_val is not None else None),
        json.dumps(after_val) if isinstance(after_val, (dict, list)) else (str(after_val) if after_val is not None else None),
        reason,
        ip
    ))
