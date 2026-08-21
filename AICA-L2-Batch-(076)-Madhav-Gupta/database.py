"""AssetDepPro - Database layer."""
import sqlite3
from utils.paths import get_database_path

SCHEMA_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS tax_blocks (
        block_id INTEGER PRIMARY KEY AUTOINCREMENT,
        block_name TEXT NOT NULL,
        block_code TEXT NOT NULL UNIQUE,
        description TEXT,
        default_rate REAL NOT NULL,
        applicable_from TEXT,
        applicable_to TEXT,
        active INTEGER NOT NULL DEFAULT 1
    )""",
    """CREATE TABLE IF NOT EXISTS asset_categories (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_name TEXT NOT NULL UNIQUE,
        category_code TEXT NOT NULL UNIQUE,
        description TEXT,
        default_method TEXT DEFAULT 'SLM',
        default_useful_life REAL,
        default_residual_pct REAL DEFAULT 0,
        default_tax_block_id INTEGER,
        default_tax_rate REAL,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        modified_at TEXT NOT NULL,
        FOREIGN KEY (default_tax_block_id) REFERENCES tax_blocks(block_id)
    )""",
    """CREATE TABLE IF NOT EXISTS asset_id_sequences (
        category_id INTEGER PRIMARY KEY,
        category_code TEXT NOT NULL,
        last_sequence INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (category_id) REFERENCES asset_categories(category_id)
    )""",
    """CREATE TABLE IF NOT EXISTS global_id_sequence (
        seq_key TEXT PRIMARY KEY,
        last_sequence INTEGER NOT NULL DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS assets (
        asset_id TEXT PRIMARY KEY,
        asset_name TEXT NOT NULL,
        category_id INTEGER NOT NULL,
        description TEXT,
        location TEXT,
        department TEXT,
        purchase_date TEXT NOT NULL,
        date_put_to_use TEXT,
        original_cost NUMERIC NOT NULL,
        capitalised_cost NUMERIC,
        residual_value NUMERIC NOT NULL DEFAULT 0,
        useful_life_years REAL,
        useful_life_months REAL,
        companies_act_method TEXT NOT NULL DEFAULT 'SLM',
        companies_act_rate REAL,
        income_tax_block_id INTEGER,
        income_tax_rate REAL,
        quantity REAL DEFAULT 1,
        vendor_name TEXT,
        invoice_number TEXT,
        opening_wdv NUMERIC,
        opening_accum_dep NUMERIC DEFAULT 0,
        opening_tax_wdv NUMERIC,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        disposal_date TEXT,
        disposal_value NUMERIC,
        buyer_name TEXT,
        remarks TEXT,
        parent_asset_id TEXT,
        is_depreciable INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        modified_at TEXT NOT NULL,
        FOREIGN KEY (category_id) REFERENCES asset_categories(category_id),
        FOREIGN KEY (income_tax_block_id) REFERENCES tax_blocks(block_id),
        FOREIGN KEY (parent_asset_id) REFERENCES assets(asset_id)
    )""",
    """CREATE TABLE IF NOT EXISTS depreciation_runs (
        run_id TEXT PRIMARY KEY,
        financial_year TEXT NOT NULL,
        period_start TEXT NOT NULL,
        period_end TEXT NOT NULL,
        calculation_basis TEXT NOT NULL DEFAULT 'DAYS',
        status TEXT NOT NULL DEFAULT 'DRAFT',
        created_at TEXT NOT NULL,
        created_by TEXT,
        total_assets INTEGER DEFAULT 0,
        total_ca_dep NUMERIC DEFAULT 0,
        total_it_dep NUMERIC DEFAULT 0,
        total_deferred_tax NUMERIC DEFAULT 0,
        reversed_run_id TEXT,
        FOREIGN KEY (reversed_run_id) REFERENCES depreciation_runs(run_id)
    )""",
    # Companies Act only - asset level. Income-tax is now handled at BLOCK level
    # (see tax_block_records) because the block-of-assets concept does not allow
    # depreciation to be attributed to an individual asset.
    """CREATE TABLE IF NOT EXISTS depreciation_records (
        record_id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        asset_id TEXT NOT NULL,
        financial_year TEXT NOT NULL,
        period_start TEXT NOT NULL,
        period_end TEXT NOT NULL,
        opening_carrying_amount NUMERIC,
        companies_act_method TEXT,
        companies_act_depreciation NUMERIC,
        closing_carrying_amount NUMERIC,
        status TEXT NOT NULL DEFAULT 'CALCULATED',
        created_at TEXT NOT NULL,
        FOREIGN KEY (run_id) REFERENCES depreciation_runs(run_id),
        FOREIGN KEY (asset_id) REFERENCES assets(asset_id)
    )""",
    # Income-tax Block of Assets - depreciation, WDV and deferred tax are computed
    # ONCE PER BLOCK PER RUN, never per individual asset.
    """CREATE TABLE IF NOT EXISTS tax_block_records (
        block_record_id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        block_id INTEGER NOT NULL,
        financial_year TEXT NOT NULL,
        period_start TEXT NOT NULL,
        period_end TEXT NOT NULL,
        opening_wdv NUMERIC,
        additions_full_rate NUMERIC DEFAULT 0,
        additions_half_rate NUMERIC DEFAULT 0,
        disposals NUMERIC DEFAULT 0,
        wdv_before_depreciation NUMERIC,
        tax_rate REAL,
        depreciation NUMERIC,
        closing_wdv NUMERIC,
        short_term_capital_gain NUMERIC DEFAULT 0,
        closing_carrying_amount_total NUMERIC,
        temporary_difference NUMERIC,
        deferred_tax_rate REAL,
        deferred_tax NUMERIC,
        deferred_tax_type TEXT,
        status TEXT NOT NULL DEFAULT 'CALCULATED',
        created_at TEXT NOT NULL,
        FOREIGN KEY (run_id) REFERENCES depreciation_runs(run_id),
        FOREIGN KEY (block_id) REFERENCES tax_blocks(block_id)
    )""",
    """CREATE TABLE IF NOT EXISTS disposal_records (
        disposal_id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id TEXT NOT NULL,
        disposal_date TEXT NOT NULL,
        sale_consideration NUMERIC NOT NULL,
        selling_expenses NUMERIC NOT NULL DEFAULT 0,
        buyer_name TEXT,
        invoice_number TEXT,
        remarks TEXT,
        original_cost NUMERIC,
        accumulated_depreciation NUMERIC,
        net_book_value NUMERIC,
        net_sale_proceeds NUMERIC,
        profit_loss NUMERIC,
        profit_loss_type TEXT,
        tax_opening_wdv NUMERIC,
        tax_closing_wdv NUMERIC,
        tax_impact NUMERIC,
        tax_impact_type TEXT,
        carrying_amount_before NUMERIC,
        tax_base_before NUMERIC,
        temporary_difference_before NUMERIC,
        deferred_tax_before NUMERIC,
        created_at TEXT NOT NULL,
        FOREIGN KEY (asset_id) REFERENCES assets(asset_id)
    )""",
    """CREATE TABLE IF NOT EXISTS financial_years (
        fy_id INTEGER PRIMARY KEY AUTOINCREMENT,
        fy_label TEXT NOT NULL UNIQUE,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS application_settings (
        setting_key TEXT PRIMARY KEY,
        setting_value TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS tax_settings (
        setting_id INTEGER PRIMARY KEY AUTOINCREMENT,
        deferred_tax_rate REAL NOT NULL,
        effective_from TEXT,
        effective_to TEXT,
        active INTEGER NOT NULL DEFAULT 1
    )""",
    """CREATE TABLE IF NOT EXISTS audit_log (
        audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        entity TEXT NOT NULL,
        entity_id TEXT,
        old_value TEXT,
        new_value TEXT,
        timestamp TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_assets_category ON assets(category_id)",
    "CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(status)",
    "CREATE INDEX IF NOT EXISTS idx_assets_block ON assets(income_tax_block_id)",
    "CREATE INDEX IF NOT EXISTS idx_dep_records_asset ON depreciation_records(asset_id)",
    "CREATE INDEX IF NOT EXISTS idx_dep_records_run ON depreciation_records(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_dep_records_fy ON depreciation_records(financial_year)",
    "CREATE INDEX IF NOT EXISTS idx_block_records_block ON tax_block_records(block_id)",
    "CREATE INDEX IF NOT EXISTS idx_block_records_run ON tax_block_records(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_block_records_fy ON tax_block_records(financial_year)",
    "CREATE INDEX IF NOT EXISTS idx_disposal_asset ON disposal_records(asset_id)",
]


def get_connection(db_path=None):
    path = db_path or get_database_path()
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database(db_path=None):
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        for statement in SCHEMA_STATEMENTS:
            cur.execute(statement)
        conn.commit()
        _seed_defaults(conn)
    finally:
        conn.close()


def _seed_defaults(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM application_settings")
    if cur.fetchone()["c"] == 0:
        defaults = {
            "company_name": "Sample Company Pvt Ltd",
            "financial_year": "FY 2026-27",
            "default_depreciation_method": "SLM",
            "decimal_places": "2",
            "currency_symbol": "\u20b9",
            "asset_id_mode": "CATEGORY",
        }
        cur.executemany(
            "INSERT INTO application_settings(setting_key, setting_value) VALUES (?,?)",
            list(defaults.items()),
        )
    cur.execute("SELECT COUNT(*) as c FROM tax_settings")
    if cur.fetchone()["c"] == 0:
        cur.execute(
            """INSERT INTO tax_settings(deferred_tax_rate, effective_from, active)
               VALUES (25.00, '2000-04-01', 1)"""
        )
    conn.commit()