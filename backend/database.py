"""
DirhamTrack AI - SQLite Local Database
Prioritizes on-device / local storage for maximum financial privacy.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "dirhamtrack.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Accounts table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL, -- 'bank', 'credit_card', 'cash'
        bank_name TEXT,
        account_mask TEXT,
        balance REAL NOT NULL DEFAULT 0.0,
        credit_limit REAL,
        due_date TEXT,
        color TEXT
    )
    """)

    # Transactions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id TEXT PRIMARY KEY,
        amount REAL NOT NULL,
        original_amount REAL,
        original_currency TEXT,
        currency TEXT NOT NULL DEFAULT 'AED',
        merchant TEXT NOT NULL,
        category TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT,
        account_id TEXT NOT NULL,
        to_account_id TEXT,
        type TEXT NOT NULL, -- 'expense', 'income', 'transfer', 'card_payment'
        source TEXT NOT NULL, -- 'auto_notification', 'manual', 'sms_import'
        bank_name TEXT,
        raw_notification_text TEXT,
        is_red_flag INTEGER NOT NULL DEFAULT 0,
        red_flag_reason TEXT,
        is_verified INTEGER NOT NULL DEFAULT 1,
        notes TEXT,
        FOREIGN KEY (account_id) REFERENCES accounts (id)
    )
    """)

    # Learned merchant rules table (Correction Memory)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS merchant_rules (
        keyword TEXT PRIMARY KEY,
        category TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # Category budgets table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS budgets (
        category TEXT PRIMARY KEY,
        monthly_limit REAL NOT NULL,
        color TEXT
    )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("SQLite database initialized successfully at", DB_PATH)
