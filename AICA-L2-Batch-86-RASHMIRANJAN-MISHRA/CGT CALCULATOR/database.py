"""
CAPITAL GAINS TAX COMPARISON CALCULATOR (12.5% vs 20%)
Database Manager (SQLite)
Author: Senior Python Developer & Tax-Audit Software Architect
"""

import sqlite3
import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

DEFAULT_DB_PATH = os.path.join(get_base_dir(), "cgt_calculator.db")

# Official CBDT Cost Inflation Index (CII) notifications
DEFAULT_CII_DATA = [
    ("2001-02", 100, 1, "Notification No. S.O. 1790(E)"),
    ("2002-03", 105, 1, "CBDT Notification"),
    ("2003-04", 109, 1, "CBDT Notification"),
    ("2004-05", 113, 1, "CBDT Notification"),
    ("2005-06", 117, 1, "CBDT Notification"),
    ("2006-07", 122, 1, "CBDT Notification"),
    ("2007-08", 129, 1, "CBDT Notification"),
    ("2008-09", 137, 1, "CBDT Notification"),
    ("2009-10", 148, 1, "CBDT Notification"),
    ("2010-11", 167, 1, "CBDT Notification"),
    ("2011-12", 184, 1, "CBDT Notification"),
    ("2012-13", 200, 1, "CBDT Notification"),
    ("2013-14", 220, 1, "CBDT Notification"),
    ("2014-15", 240, 1, "CBDT Notification"),
    ("2015-16", 254, 1, "CBDT Notification"),
    ("2016-17", 264, 1, "CBDT Notification"),
    ("2017-18", 272, 1, "CBDT Notification"),
    ("2018-19", 280, 1, "CBDT Notification"),
    ("2019-20", 289, 1, "CBDT Notification"),
    ("2020-21", 301, 1, "CBDT Notification"),
    ("2021-22", 317, 1, "CBDT Notification"),
    ("2022-23", 331, 1, "CBDT Notification"),
    ("2023-24", 348, 1, "CBDT Notification"),
    ("2024-25", 363, 1, "Notification No. 44/2024"),
    ("2025-26", 377, 1, "Notification No. 51/2025 (or estimated)"),
    ("2026-27", 392, 0, "Provisional / User configurable"),
]

DEFAULT_TAX_RULES = [
    (
        "statutory_cut_off_date",
        "Finance Act (No. 2) 2024 Cut-off Date",
        "2024-07-23",
        "str",
        "GENERAL",
        "Statutory transition date from which Section 112 12.5% rate became effective.",
    ),
    (
        "ltcg_rate_new",
        "LTCG Rate without Indexation (New)",
        "12.5",
        "float",
        "RATES",
        "Long-term capital gains tax rate under Section 112 (amended).",
    ),
    (
        "ltcg_rate_old",
        "LTCG Rate with Indexation (Old / Proviso)",
        "20.0",
        "float",
        "RATES",
        "Long-term capital gains tax rate under Section 112 with indexation benefit.",
    ),
    (
        "cess_rate",
        "Health & Education Cess Rate (%)",
        "4.0",
        "float",
        "RATES",
        "Applicable Health and Education Cess on (Tax + Surcharge).",
    ),
    (
        "surcharge_cap_ltcg_112",
        "Surcharge Cap for Section 112 LTCG (%)",
        "15.0",
        "float",
        "SURCHARGE",
        "Maximum surcharge applicable on Section 112 LTCG for Individual/HUF.",
    ),
    (
        "surcharge_slab_1_limit",
        "Surcharge Slab 1 Threshold (INR)",
        "5000000.0",
        "float",
        "SURCHARGE",
        "Income threshold up to which surcharge is 0%.",
    ),
    (
        "surcharge_slab_1_rate",
        "Surcharge Slab 1 Rate (%)",
        "10.0",
        "float",
        "SURCHARGE",
        "Surcharge for income between ₹50 Lakh and ₹1 Crore.",
    ),
    (
        "surcharge_slab_2_limit",
        "Surcharge Slab 2 Threshold (INR)",
        "10000000.0",
        "float",
        "SURCHARGE",
        "Income threshold above which surcharge is 15%.",
    ),
    (
        "surcharge_slab_2_rate",
        "Surcharge Slab 2 Rate (%)",
        "15.0",
        "float",
        "SURCHARGE",
        "Surcharge for income above ₹1 Crore.",
    ),
    (
        "holding_period_immovable_months",
        "Holding Period for Land / Building (Months)",
        "24",
        "int",
        "CLASSIFICATION",
        "Minimum holding period in months for immovable property to qualify as Long-Term.",
    ),
    (
        "holding_period_unlisted_shares_months",
        "Holding Period for Unlisted Shares (Months)",
        "24",
        "int",
        "CLASSIFICATION",
        "Minimum holding period in months for unlisted shares (amended w.e.f. 23-07-2024).",
    ),
    (
        "holding_period_listed_shares_months",
        "Holding Period for Listed Shares (Months)",
        "12",
        "int",
        "CLASSIFICATION",
        "Minimum holding period in months for listed securities.",
    ),
    (
        "eligible_grandfathering_assets",
        "Assets Eligible for 20% Indexation Proviso",
        json.dumps(["Land", "Building", "Land & Building"]),
        "json",
        "ELIGIBILITY",
        "Asset classes eligible for grandfathered indexation comparison under Section 112.",
    ),
    (
        "eligible_grandfathering_assessees",
        "Assessees Eligible for 20% Indexation Proviso",
        json.dumps(["Individual", "HUF"]),
        "json",
        "ELIGIBILITY",
        "Assessee types eligible for transitional indexation relief.",
    ),
    (
        "pre_2001_cut_off_date",
        "Pre-2001 Grandfathering Cut-off Date",
        "2001-04-01",
        "str",
        "LEGACY",
        "Assets acquired prior to this date may adopt FMV as of 01-04-2001.",
    ),
    (
        "pre_2001_base_cii_fy",
        "Pre-2001 Base Financial Year",
        "2001-02",
        "str",
        "LEGACY",
        "Base financial year for indexation of pre-2001 assets.",
    ),
]


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Returns a SQLite connection with row factory enabled."""
    path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initializes the database schema and seeds master data if not present."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # 1. CII Master Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cii_master (
            financial_year TEXT PRIMARY KEY,
            cii_value INTEGER NOT NULL,
            is_notified INTEGER DEFAULT 1,
            notification_ref TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Tax Rule Master Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tax_rule_master (
            rule_key TEXT PRIMARY KEY,
            rule_name TEXT NOT NULL,
            rule_value TEXT NOT NULL,
            value_type TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3. Calculation History / Audit Trail Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calculation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            calculation_date TEXT NOT NULL,
            assessee_name TEXT NOT NULL,
            pan TEXT,
            assessee_type TEXT NOT NULL,
            residential_status TEXT NOT NULL,
            assessment_year TEXT NOT NULL,
            financial_year TEXT NOT NULL,
            asset_type TEXT NOT NULL,
            date_of_sale TEXT NOT NULL,
            date_of_acquisition TEXT NOT NULL,
            gross_sale_price REAL NOT NULL,
            transfer_expenses REAL NOT NULL,
            net_sale_price REAL NOT NULL,
            actual_cost_acq REAL NOT NULL,
            fmv_2001 REAL DEFAULT 0.0,
            adopted_cost_acq REAL NOT NULL,
            acq_cii INTEGER NOT NULL,
            sale_cii INTEGER NOT NULL,
            indexed_cost_acq REAL NOT NULL,
            total_actual_improvement REAL NOT NULL,
            total_indexed_improvement REAL NOT NULL,
            improvements_json TEXT,
            transfer_expenses_json TEXT,
            holding_period_months REAL NOT NULL,
            asset_classification TEXT NOT NULL,
            is_20_applicable INTEGER NOT NULL,
            ineligibility_reason TEXT,
            ltcg_12_5 REAL NOT NULL,
            tax_12_5 REAL NOT NULL,
            surcharge_12_5 REAL NOT NULL,
            cess_12_5 REAL NOT NULL,
            total_tax_12_5 REAL NOT NULL,
            ltcg_20 REAL NOT NULL,
            tax_20 REAL NOT NULL,
            surcharge_20 REAL NOT NULL,
            cess_20 REAL NOT NULL,
            total_tax_20 REAL NOT NULL,
            recommended_method TEXT NOT NULL,
            tax_saving REAL NOT NULL,
            notes TEXT
        )
    """)

    # 4. Audit Log Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT,
            details TEXT
        )
    """)

    conn.commit()

    # Seed master data if tables are empty
    seed_default_cii(conn)
    seed_default_tax_rules(conn)

    conn.close()


def seed_default_cii(conn: sqlite3.Connection) -> None:
    """Seeds default CII data if cii_master is empty."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM cii_master")
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.executemany(
            """
            INSERT INTO cii_master (financial_year, cii_value, is_notified, notification_ref, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            """,
            DEFAULT_CII_DATA,
        )
        conn.commit()
        log_audit(
            action="INITIALIZE",
            entity_type="CII_MASTER",
            entity_id="ALL",
            details=f"Seeded {len(DEFAULT_CII_DATA)} official CII records.",
            conn=conn,
        )


def seed_default_tax_rules(conn: sqlite3.Connection) -> None:
    """Seeds default tax rules if tax_rule_master is empty."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tax_rule_master")
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.executemany(
            """
            INSERT INTO tax_rule_master (rule_key, rule_name, rule_value, value_type, category, description, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            DEFAULT_TAX_RULES,
        )
        conn.commit()
        log_audit(
            action="INITIALIZE",
            entity_type="TAX_RULE_MASTER",
            entity_id="ALL",
            details=f"Seeded {len(DEFAULT_TAX_RULES)} statutory tax rules.",
            conn=conn,
        )


def log_audit(
    action: str,
    entity_type: str,
    entity_id: Optional[str],
    details: str,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    """Records an entry in the audit_log table."""
    owns_conn = False
    if conn is None:
        conn = get_db_connection()
        owns_conn = True

    try:
        conn.execute(
            """
            INSERT INTO audit_log (timestamp, action, entity_type, entity_id, details)
            VALUES (datetime('now'), ?, ?, ?, ?)
            """,
            (action, entity_type, entity_id, details),
        )
        conn.commit()
    finally:
        if owns_conn:
            conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
