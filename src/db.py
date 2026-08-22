import sqlite3
import os
import datetime
import shutil
import json

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "non_indas_schedule3.db")

def get_connection(db_path=DB_FILE):
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=DB_FILE):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA busy_timeout=30000;")
    except Exception:
        pass


    # Company Settings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS company_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT NOT NULL DEFAULT 'Apex Engineering India Private Limited',
        financial_statement_type TEXT NOT NULL DEFAULT 'Standalone', -- Standalone / Consolidated
        financial_year TEXT NOT NULL DEFAULT '2023-24',
        comparative_year TEXT NOT NULL DEFAULT '2022-23',
        currency TEXT NOT NULL DEFAULT 'INR',
        rounding_unit TEXT NOT NULL DEFAULT 'Lakhs', -- Absolute, Hundreds, Thousands, Lakhs, Millions, Crores
        decimal_places INTEGER NOT NULL DEFAULT 2,
        entity_type TEXT NOT NULL DEFAULT 'Non-SMC', -- Non-SMC, SMC, Micro
        sector_requirements TEXT DEFAULT 'General Manufacturing & Services',
        cin TEXT DEFAULT 'U29253MH2012PTC234567',
        registered_address TEXT DEFAULT 'Plot 45, Industrial Zone, Thane, Maharashtra - 400604',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Check if default company settings exist
    cursor.execute("SELECT COUNT(*) FROM company_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO company_settings (company_name, financial_statement_type, financial_year, comparative_year, currency, rounding_unit, decimal_places, entity_type, sector_requirements, cin, registered_address)
        VALUES ('Apex Engineering India Private Limited', 'Standalone', '2023-24', '2022-23', 'INR', 'Lakhs', 2, 'Non-SMC', 'General Manufacturing & Services', 'U29253MH2012PTC234567', 'Plot 45, Industrial Zone, Thane, Maharashtra - 400604');
        """)

    # Schedule III Line Items Master Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schedule3_master (
        code TEXT PRIMARY KEY,
        code_alias TEXT, -- EQ-01, LI-01, AS-01, IN-01, EX-01 etc.
        statement_type TEXT NOT NULL, -- BS_EQUITY_LIAB, BS_ASSETS, PL_REVENUE, PL_EXPENSES
        major_head TEXT NOT NULL,
        sub_head TEXT NOT NULL,
        line_item_name TEXT NOT NULL,
        note_no TEXT,
        normal_balance TEXT NOT NULL, -- Dr or Cr
        default_classification TEXT NOT NULL, -- Current, Non-Current, N/A
        cash_flow_category TEXT, -- Operating, Investing, Financing, Cash_Equivalent
        is_judgmental INTEGER DEFAULT 0 -- 1 if requires CA review
    );
    """)

    # Raw Tally TB Import Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tally_import (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ledger_name TEXT NOT NULL UNIQUE,
        tally_group TEXT NOT NULL,
        opening_dr REAL DEFAULT 0.0,
        opening_cr REAL DEFAULT 0.0,
        debit REAL DEFAULT 0.0,
        credit REAL DEFAULT 0.0,
        closing_dr REAL DEFAULT 0.0,
        closing_cr REAL DEFAULT 0.0,
        closing_net REAL DEFAULT 0.0, -- Net balance: + for Dr, - for Cr
        prior_closing_net REAL DEFAULT 0.0, -- Comparative year net balance
        source_filename TEXT,
        imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Ledger Mappings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ledger_mappings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ledger_name TEXT NOT NULL UNIQUE,
        schedule3_code TEXT,
        note_no TEXT,
        note_subhead TEXT,
        classification_override TEXT, -- Current, Non-Current, N/A
        cash_flow_category TEXT, -- Operating, Investing, Financing, Cash_Equivalent
        tax_flag TEXT DEFAULT 'None', -- Current Tax, Deferred Tax, Exempt
        related_party_flag INTEGER DEFAULT 0,
        depreciation_flag INTEGER DEFAULT 0,
        review_status TEXT DEFAULT 'CA Review Required', -- Approved, CA Review Required, Pending
        review_note TEXT,
        mapped_by TEXT DEFAULT 'Rule Engine',
        mapped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(ledger_name) REFERENCES tally_import(ledger_name),
        FOREIGN KEY(schedule3_code) REFERENCES schedule3_master(code)
    );
    """)

    # Reusable Mapping Rules Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mapping_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_type TEXT NOT NULL, -- Tally_Group, Ledger_Contains, Ledger_StartsWith
        pattern TEXT NOT NULL,
        schedule3_code TEXT NOT NULL,
        note_no TEXT,
        classification TEXT DEFAULT 'Default',
        cash_flow_category TEXT,
        requires_review INTEGER DEFAULT 0,
        priority INTEGER DEFAULT 10
    );
    """)

    # Disclosures & Notes Data Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notes_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        note_no TEXT NOT NULL UNIQUE,
        note_title TEXT NOT NULL,
        content_json TEXT NOT NULL, -- Flexible JSON for schedules, tables, text overrides
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Company Approved Mappings Table (Permanently retained & frozen per company)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS company_approved_mappings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT NOT NULL,
        ledger_name TEXT NOT NULL,
        tally_group TEXT,
        schedule3_code TEXT NOT NULL,
        note_no TEXT,
        note_subhead TEXT,
        classification_override TEXT,
        cash_flow_category TEXT,
        tax_flag TEXT DEFAULT 'None',
        review_status TEXT DEFAULT 'Approved',
        approved_by TEXT DEFAULT 'CA User',
        approved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_name, ledger_name)
    );
    """)

    # Company Disclosures Checklist Details Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS company_disclosures_checklist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT NOT NULL,
        ref_id TEXT NOT NULL,
        item_title TEXT NOT NULL,
        status TEXT DEFAULT 'Requires Input',
        details_text TEXT,
        updated_by TEXT DEFAULT 'CA User',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_name, ref_id)
    );
    """)

    # Company Custom Notes Table (e.g. Customized Note 1 Accounting Policies)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS company_notes_custom (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT NOT NULL,
        note_no TEXT NOT NULL,
        custom_content_json TEXT NOT NULL,
        updated_by TEXT DEFAULT 'CA User',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_name, note_no)
    );
    """)

    # Company Additional Remarks per Note (Note 2 to Note 29)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS company_note_remarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT NOT NULL,
        note_no TEXT NOT NULL,
        additional_remarks TEXT NOT NULL,
        updated_by TEXT DEFAULT 'CA User',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_name, note_no)
    );
    """)

    # Company CA Note Review & Approval Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS company_note_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT NOT NULL,
        note_no TEXT NOT NULL,
        review_status TEXT DEFAULT 'Approved', -- 'Approved' or 'Pending'
        reviewed_by TEXT DEFAULT 'CA Lead Auditor',
        review_notes TEXT,
        reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_name, note_no)
    );
    """)


    # Audit Trail Log Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT DEFAULT 'CA User',
        action TEXT NOT NULL,
        target_table TEXT NOT NULL,
        target_id TEXT,
        details TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Migrate any existing approved mappings from ledger_mappings to company_approved_mappings
    cursor.execute("SELECT company_name FROM company_settings ORDER BY id DESC LIMIT 1;")
    comp_row = cursor.fetchone()
    current_comp = comp_row[0] if comp_row else 'Apex Engineering India Private Limited'
    cursor.execute("""
    INSERT OR IGNORE INTO company_approved_mappings (company_name, ledger_name, schedule3_code, note_no, classification_override, cash_flow_category, tax_flag, review_status, approved_by)
    SELECT ?, ledger_name, schedule3_code, note_no, classification_override, cash_flow_category, tax_flag, 'Approved', COALESCE(mapped_by, 'CA User')
    FROM ledger_mappings
    WHERE review_status = 'Approved' AND schedule3_code IS NOT NULL;
    """, (current_comp,))


    # Check if code_alias column exists in schedule3_master (migration safety)
    cursor.execute("PRAGMA table_info(schedule3_master);")
    cols = [c[1] for c in cursor.fetchall()]
    if 'code_alias' not in cols:
        cursor.execute("ALTER TABLE schedule3_master ADD COLUMN code_alias TEXT;")

    # Seed or update Schedule III Master Data
    seed_schedule3_master(cursor)

    # Seed Default Mapping Rules if empty
    cursor.execute("SELECT COUNT(*) FROM mapping_rules")
    if cursor.fetchone()[0] == 0:
        seed_default_mapping_rules(cursor)

    conn.commit()
    conn.close()

def seed_schedule3_master(cursor):
    master_items = [
        # --- EQUITY AND LIABILITIES ---
        ('EQUITY_SHARE_CAPITAL', 'EQ-01', 'BS_EQUITY_LIAB', 'Shareholders Funds', 'Share Capital', 'Equity Share Capital', '2', 'Cr', 'Non-Current', 'Financing', 0),
        ('PREFERENCE_SHARE_CAPITAL', 'EQ-01B', 'BS_EQUITY_LIAB', 'Shareholders Funds', 'Share Capital', 'Preference Share Capital', '2', 'Cr', 'Non-Current', 'Financing', 0),
        ('RESERVES_SURPLUS', 'EQ-02', 'BS_EQUITY_LIAB', 'Shareholders Funds', 'Reserves and Surplus', 'Reserves and Surplus', '3', 'Cr', 'Non-Current', 'Financing', 0),
        ('MONEY_SHARE_WARRANTS', 'EQ-03', 'BS_EQUITY_LIAB', 'Shareholders Funds', 'Money received against share warrants', 'Money received against share warrants', '3.1', 'Cr', 'Non-Current', 'Financing', 1),
        ('SHARE_APPLICATION_MONEY', 'EQ-04', 'BS_EQUITY_LIAB', 'Share Application Money Pending Allotment', 'Share Application Money Pending Allotment', 'Share Application Money Pending Allotment', '3.2', 'Cr', 'Non-Current', 'Financing', 1),
        
        ('LONG_TERM_BORROWINGS', 'LI-01', 'BS_EQUITY_LIAB', 'Non-Current Liabilities', 'Long-term borrowings', 'Long-term borrowings', '4', 'Cr', 'Non-Current', 'Financing', 1),
        ('DEFERRED_TAX_LIAB', 'LI-02', 'BS_EQUITY_LIAB', 'Non-Current Liabilities', 'Deferred tax liabilities (Net)', 'Deferred tax liabilities (Net)', '5', 'Cr', 'Non-Current', 'Operating', 1),
        ('OTHER_LONG_TERM_LIAB', 'LI-02B', 'BS_EQUITY_LIAB', 'Non-Current Liabilities', 'Other Long term liabilities', 'Other Long term liabilities', '6', 'Cr', 'Non-Current', 'Operating', 1),
        ('LONG_TERM_PROVISIONS', 'LI-02C', 'BS_EQUITY_LIAB', 'Non-Current Liabilities', 'Long-term provisions', 'Long-term provisions', '7', 'Cr', 'Non-Current', 'Operating', 1),

        ('SHORT_TERM_BORROWINGS', 'LI-03', 'BS_EQUITY_LIAB', 'Current Liabilities', 'Short-term borrowings', 'Short-term borrowings', '8', 'Cr', 'Current', 'Financing', 1),
        ('TRADE_PAYABLES_MSME', 'LI-04A', 'BS_EQUITY_LIAB', 'Current Liabilities', 'Trade payables', 'Total outstanding dues of micro enterprises and small enterprises', '9', 'Cr', 'Current', 'Operating', 0),
        ('TRADE_PAYABLES_OTHERS', 'LI-04B', 'BS_EQUITY_LIAB', 'Current Liabilities', 'Trade payables', 'Total outstanding dues of creditors other than micro enterprises and small enterprises', '9', 'Cr', 'Current', 'Operating', 0),
        ('OTHER_CURRENT_LIAB', 'LI-05', 'BS_EQUITY_LIAB', 'Current Liabilities', 'Other current liabilities', 'Other current liabilities', '10', 'Cr', 'Current', 'Operating', 0),
        ('SHORT_TERM_PROVISIONS', 'LI-06', 'BS_EQUITY_LIAB', 'Current Liabilities', 'Short-term provisions', 'Short-term provisions', '11', 'Cr', 'Current', 'Operating', 1),

        # --- ASSETS ---
        ('PPE_TANGIBLE', 'AS-01', 'BS_ASSETS', 'Non-Current Assets', 'Property, Plant and Equipment and Intangible Assets', 'Property, Plant and Equipment', '12', 'Dr', 'Non-Current', 'Investing', 0),
        ('INTANGIBLE_ASSETS', 'AS-02', 'BS_ASSETS', 'Non-Current Assets', 'Property, Plant and Equipment and Intangible Assets', 'Intangible assets', '12', 'Dr', 'Non-Current', 'Investing', 0),
        ('CAPITAL_WORK_IN_PROGRESS', 'AS-01B', 'BS_ASSETS', 'Non-Current Assets', 'Property, Plant and Equipment and Intangible Assets', 'Capital work-in-progress', '12', 'Dr', 'Non-Current', 'Investing', 1),
        ('INTANGIBLE_ASSETS_UNDER_DEV', 'AS-02B', 'BS_ASSETS', 'Non-Current Assets', 'Property, Plant and Equipment and Intangible Assets', 'Intangible assets under development', '12', 'Dr', 'Non-Current', 'Investing', 1),
        
        ('NON_CURRENT_INVESTMENTS', 'AS-03', 'BS_ASSETS', 'Non-Current Assets', 'Non-current investments', 'Non-current investments', '13', 'Dr', 'Non-Current', 'Investing', 1),
        ('DEFERRED_TAX_ASSETS', 'AS-03B', 'BS_ASSETS', 'Non-Current Assets', 'Deferred tax assets (Net)', 'Deferred tax assets (Net)', '5', 'Dr', 'Non-Current', 'Operating', 1),
        ('LONG_TERM_LOANS_ADV', 'AS-04', 'BS_ASSETS', 'Non-Current Assets', 'Long-term loans and advances', 'Long-term loans and advances', '14', 'Dr', 'Non-Current', 'Investing', 1),
        ('OTHER_NON_CURRENT_ASSETS', 'AS-04B', 'BS_ASSETS', 'Non-Current Assets', 'Other non-current assets', 'Other non-current assets', '15', 'Dr', 'Non-Current', 'Operating', 1),

        ('CURRENT_INVESTMENTS', 'AS-04C', 'BS_ASSETS', 'Current Assets', 'Current investments', 'Current investments', '16', 'Dr', 'Current', 'Investing', 1),
        ('INVENTORIES', 'AS-05', 'BS_ASSETS', 'Current Assets', 'Inventories', 'Inventories', '17', 'Dr', 'Current', 'Operating', 0),
        ('TRADE_RECEIVABLES', 'AS-06', 'BS_ASSETS', 'Current Assets', 'Trade receivables', 'Trade receivables', '18', 'Dr', 'Current', 'Operating', 0),
        ('CASH_BANK_BALANCES', 'AS-07', 'BS_ASSETS', 'Current Assets', 'Cash and cash equivalents', 'Cash and cash equivalents', '19', 'Dr', 'Current', 'Cash_Equivalent', 0),
        ('SHORT_TERM_LOANS_ADV', 'AS-08', 'BS_ASSETS', 'Current Assets', 'Short-term loans and advances', 'Short-term loans and advances', '20', 'Dr', 'Current', 'Operating', 0),
        ('OTHER_CURRENT_ASSETS', 'AS-09', 'BS_ASSETS', 'Current Assets', 'Other current assets', 'Other current assets', '21', 'Dr', 'Current', 'Operating', 0),

        # --- PROFIT AND LOSS ---
        ('REVENUE_OPERATIONS', 'IN-01', 'PL_REVENUE', 'Revenue', 'Revenue from Operations', 'Revenue from operations', '22', 'Cr', 'N/A', 'Operating', 0),
        ('OTHER_INCOME', 'IN-02', 'PL_REVENUE', 'Revenue', 'Other Income', 'Other income', '23', 'Cr', 'N/A', 'Investing', 0),

        ('COST_MATERIALS_CONSUMED', 'EX-01', 'PL_EXPENSES', 'Expenses', 'Cost of materials consumed', 'Cost of materials consumed', '24', 'Dr', 'N/A', 'Operating', 0),
        ('PURCHASES_STOCK_IN_TRADE', 'EX-02', 'PL_EXPENSES', 'Expenses', 'Purchases of Stock-in-Trade', 'Purchases of Stock-in-Trade', '25', 'Dr', 'N/A', 'Operating', 0),
        ('CHANGES_IN_INVENTORIES', 'EX-03', 'PL_EXPENSES', 'Expenses', 'Changes in inventories of finished goods, WIP and Stock-in-Trade', 'Changes in inventories of finished goods, WIP and Stock-in-Trade', '26', 'Dr', 'N/A', 'Operating', 0),
        ('EMPLOYEE_BENEFIT_EXPENSE', 'EX-04', 'PL_EXPENSES', 'Expenses', 'Employee benefits expense', 'Employee benefits expense', '27', 'Dr', 'N/A', 'Operating', 0),
        ('FINANCE_COSTS', 'EX-05', 'PL_EXPENSES', 'Expenses', 'Finance costs', 'Finance costs', '28', 'Dr', 'N/A', 'Financing', 0),
        ('DEPRECIATION_AMORTIZATION', 'EX-06', 'PL_EXPENSES', 'Expenses', 'Depreciation and amortization expense', 'Depreciation and amortization expense', '12', 'Dr', 'N/A', 'Operating', 0),
        ('OTHER_EXPENSES', 'EX-07', 'PL_EXPENSES', 'Expenses', 'Other expenses', 'Other expenses', '29', 'Dr', 'N/A', 'Operating', 0),
        ('EXCEPTIONAL_ITEMS', 'EX-08', 'PL_EXPENSES', 'Expenses', 'Exceptional items', 'Exceptional items', '30', 'Dr', 'N/A', 'Operating', 1),
        ('EXTRAORDINARY_ITEMS', 'EX-09', 'PL_EXPENSES', 'Expenses', 'Extraordinary items', 'Extraordinary items', '31', 'Dr', 'N/A', 'Operating', 1),
        ('CURRENT_TAX_EXPENSE', 'EX-10', 'PL_EXPENSES', 'Tax Expense', 'Current Tax', 'Current tax', '15', 'Dr', 'N/A', 'Operating', 1),
        ('DEFERRED_TAX_EXPENSE', 'EX-11', 'PL_EXPENSES', 'Tax Expense', 'Deferred Tax', 'Deferred tax', '15', 'Dr', 'N/A', 'Operating', 1)
    ]

    for item in master_items:
        cursor.execute("""
        INSERT INTO schedule3_master (code, code_alias, statement_type, major_head, sub_head, line_item_name, note_no, normal_balance, default_classification, cash_flow_category, is_judgmental)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(code) DO UPDATE SET
            code_alias = excluded.code_alias,
            normal_balance = excluded.normal_balance;
        """, item)

def seed_default_mapping_rules(cursor):
    rules = [
        ('Tally_Group', 'Bank Accounts', 'CASH_BANK_BALANCES', '19', 'Current', 'Cash_Equivalent', 0, 10),
        ('Tally_Group', 'Cash-in-Hand', 'CASH_BANK_BALANCES', '19', 'Current', 'Cash_Equivalent', 0, 10),
        ('Tally_Group', 'Sundry Debtors', 'TRADE_RECEIVABLES', '18', 'Current', 'Operating', 0, 10),
        ('Tally_Group', 'Sundry Creditors', 'TRADE_PAYABLES_OTHERS', '9', 'Current', 'Operating', 0, 10),
        ('Tally_Group', 'Sales Accounts', 'REVENUE_OPERATIONS', '22', 'N/A', 'Operating', 0, 10),
        ('Tally_Group', 'Purchase Accounts', 'PURCHASES_STOCK_IN_TRADE', '25', 'N/A', 'Operating', 0, 10),
        ('Tally_Group', 'Direct Expenses', 'OTHER_EXPENSES', '29', 'N/A', 'Operating', 0, 10),
        ('Tally_Group', 'Indirect Expenses', 'OTHER_EXPENSES', '29', 'N/A', 'Operating', 0, 10),
        ('Tally_Group', 'Direct Incomes', 'REVENUE_OPERATIONS', '22', 'N/A', 'Operating', 0, 10),
        ('Tally_Group', 'Indirect Incomes', 'OTHER_INCOME', '23', 'N/A', 'Investing', 0, 10),
        ('Tally_Group', 'Fixed Assets', 'PPE_TANGIBLE', '12', 'Non-Current', 'Investing', 0, 10),
        ('Tally_Group', 'Capital Account', 'EQUITY_SHARE_CAPITAL', '2', 'Non-Current', 'Financing', 1, 10),
        ('Tally_Group', 'Reserves & Surplus', 'RESERVES_SURPLUS', '3', 'Non-Current', 'Financing', 0, 10),
        ('Tally_Group', 'Loans (Liability)', 'LONG_TERM_BORROWINGS', '4', 'Non-Current', 'Financing', 1, 10),
        ('Tally_Group', 'Bank OD A/c', 'SHORT_TERM_BORROWINGS', '8', 'Current', 'Financing', 1, 10),
        ('Tally_Group', 'Duties & Taxes', 'OTHER_CURRENT_LIAB', '10', 'Current', 'Operating', 0, 10),
        ('Tally_Group', 'Stock-in-Hand', 'INVENTORIES', '17', 'Current', 'Operating', 0, 10),
        ('Tally_Group', 'Deposits (Asset)', 'SHORT_TERM_LOANS_ADV', '20', 'Current', 'Operating', 0, 10),
        ('Tally_Group', 'Loans & Advances (Asset)', 'SHORT_TERM_LOANS_ADV', '20', 'Current', 'Operating', 1, 10),
        ('Tally_Group', 'Provisions', 'SHORT_TERM_PROVISIONS', '11', 'Current', 'Operating', 1, 10),
        ('Tally_Group', 'Investments', 'NON_CURRENT_INVESTMENTS', '13', 'Non-Current', 'Investing', 1, 10),
        
        ('Ledger_Contains', 'Salary', 'EMPLOYEE_BENEFIT_EXPENSE', '27', 'N/A', 'Operating', 0, 20),
        ('Ledger_Contains', 'Wages', 'EMPLOYEE_BENEFIT_EXPENSE', '27', 'N/A', 'Operating', 0, 20),
        ('Ledger_Contains', 'PF Contribution', 'EMPLOYEE_BENEFIT_EXPENSE', '27', 'N/A', 'Operating', 0, 20),
        ('Ledger_Contains', 'Depreciation', 'DEPRECIATION_AMORTIZATION', '12', 'N/A', 'Operating', 0, 20),
        ('Ledger_Contains', 'Interest Paid', 'FINANCE_COSTS', '28', 'N/A', 'Financing', 0, 20),
        ('Ledger_Contains', 'Bank Charges', 'FINANCE_COSTS', '28', 'N/A', 'Operating', 0, 20),
        ('Ledger_Contains', 'GST Payable', 'OTHER_CURRENT_LIAB', '10', 'Current', 'Operating', 0, 20),
        ('Ledger_Contains', 'TDS Payable', 'OTHER_CURRENT_LIAB', '10', 'Current', 'Operating', 0, 20),
        ('Ledger_Contains', 'Audit Fee', 'OTHER_EXPENSES', '29', 'N/A', 'Operating', 0, 20),
        ('Ledger_Contains', 'Rent', 'OTHER_EXPENSES', '29', 'N/A', 'Operating', 0, 20),
        ('Ledger_Contains', 'Electricity', 'OTHER_EXPENSES', '29', 'N/A', 'Operating', 0, 20),
        ('Ledger_Contains', 'Share Capital', 'EQUITY_SHARE_CAPITAL', '2', 'Non-Current', 'Financing', 0, 20),
        ('Ledger_Contains', 'Profit & Loss', 'RESERVES_SURPLUS', '3', 'Non-Current', 'Financing', 0, 20),
        ('Ledger_Contains', 'Deferred Tax', 'DEFERRED_TAX_LIAB', '5', 'Non-Current', 'Operating', 1, 20)
    ]

    cursor.executemany("""
    INSERT INTO mapping_rules (rule_type, pattern, schedule3_code, note_no, classification, cash_flow_category, requires_review, priority)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, rules)

def log_audit(action, target_table, target_id=None, details=None, user_name="CA User"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO audit_log (user_name, action, target_table, target_id, details)
    VALUES (?, ?, ?, ?, ?);
    """, (user_name, action, target_table, str(target_id) if target_id else None, details))
    conn.commit()
    conn.close()

def backup_db(backup_folder=None):
    if not backup_folder:
        backup_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backups")
    os.makedirs(backup_folder, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_folder, f"non_indas_schedule3_backup_{timestamp}.db")
    shutil.copy2(DB_FILE, backup_path)
    log_audit("BACKUP_CREATED", "database", details=f"Backup created at {backup_path}")
    return backup_path

def restore_db(backup_path):
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup file not found: {backup_path}")
    shutil.copy2(backup_path, DB_FILE)
    log_audit("BACKUP_RESTORED", "database", details=f"Database restored from {backup_path}")
    return True
