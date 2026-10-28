import uuid
from datetime import datetime
from .database import get_db, init_db, log_audit

def seed_database(force: bool = False):
    init_db()
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM companies")
    count = cur.fetchone()[0]
    if count > 0 and not force:
        conn.close()
        return

    now_iso = datetime.now().isoformat()

    # Clear existing if force
    if force:
        conn.executescript("""
            DELETE FROM match_group_items;
            DELETE FROM match_groups;
            DELETE FROM transactions;
            DELETE FROM periods;
            DELETE FROM bank_accounts;
            DELETE FROM companies;
            DELETE FROM users;
            DELETE FROM rules;
            DELETE FROM audit_logs;
        """)

    # 1. Users
    users = [
        ("USR-01", "admin", "System Administrator", "Administrator", "admin@enterpriserecon.com"),
        ("USR-02", "preparer1", "John Reynolds (Preparer)", "Preparer", "john.reynolds@enterpriserecon.com"),
        ("USR-03", "reviewer1", "Elena Vasquez (Reviewer)", "Reviewer", "elena.vasquez@enterpriserecon.com"),
        ("USR-04", "approver1", "Robert Vance (Approver)", "Approver", "robert.vance@enterpriserecon.com"),
        ("USR-05", "auditor1", "Sarah Jenkins (Auditor)", "Auditor", "sarah.jenkins@enterpriserecon.com")
    ]
    cur.executemany("INSERT INTO users (id, username, full_name, role, email) VALUES (?, ?, ?, ?, ?)", users)

    # 2. Rules
    rules = [
        ("RUL-01", "Exact Unique Reference & Amount", "Matches identical references and exact amounts", 1, "exact_ref", 0, 0.0, 1),
        ("RUL-02", "Exact Cheque / Payment ID & Amount", "Matches cheque number or payment transaction ID", 2, "exact_cheque", 3, 0.0, 1),
        ("RUL-03", "Exact Amount with Date Tolerance", "Matches exact amounts within 7 days window", 3, "amount_date_tol", 7, 0.0, 1),
        ("RUL-04", "One-to-Many Grouped Cash Match", "Matches single bulk ledger record to multiple bank lines", 4, "grouped_match", 5, 0.0, 1)
    ]
    cur.executemany("INSERT INTO rules (id, name, description, priority, rule_type, date_tolerance_days, amount_tolerance, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rules)

    # 3. Companies
    companies = [
        ("CMP-01", "GEH-CORP", "Global Enterprise Holdings Ltd", "USD", now_iso),
        ("CMP-02", "APEX-ME", "Apex Technologies Middle East FZ-LLC", "AED", now_iso),
        ("CMP-03", "EURO-RET", "European Retail Logistics NV", "EUR", now_iso)
    ]
    cur.executemany("INSERT INTO companies (id, code, name, reporting_currency, created_at) VALUES (?, ?, ?, ?, ?)", companies)

    # 4. Bank Accounts
    accounts = [
        # Acceptance Test Account
        ("ACC-01", "CMP-01", "JPMorgan Chase", "New York Corporate", "4892019482", "US89JPMC4892019482001", "USD", "1010-001-CASH", "US_PRIMARY_LEDGER", "GEH US Corp", "John Reynolds", "John Reynolds", "Elena Vasquez", "Robert Vance", "Active", 100000.0, "2026-09-01", now_iso),
        # Interactive Match Demo Account
        ("ACC-02", "CMP-01", "HSBC Commercial Bank", "London City", "7729103941", "GB29HBUK7729103941001", "USD", "1010-002-CASH", "US_PRIMARY_LEDGER", "GEH US Corp", "John Reynolds", "John Reynolds", "Elena Vasquez", "Robert Vance", "Active", 250000.0, "2026-09-01", now_iso),
        # Fully Reconciled Account
        ("ACC-03", "CMP-02", "First Abu Dhabi Bank", "Al Maryah Island", "9918234851", "AE44FAB99182348510001", "AED", "1020-001-AED", "ME_OPERATING_LEDGER", "Apex ME FZ", "John Reynolds", "John Reynolds", "Elena Vasquez", "Robert Vance", "Active", 500000.0, "2026-09-01", now_iso),
        # European Account
        ("ACC-04", "CMP-03", "BNP Paribas", "Brussels Central", "5510293841", "BE68BNPA5510293841001", "EUR", "1030-001-EUR", "EU_CONSOL_LEDGER", "Euro Ret Logistics", "John Reynolds", "John Reynolds", "Elena Vasquez", "Robert Vance", "Active", 180000.0, "2026-09-01", now_iso),
        # Barclays GBP Account
        ("ACC-05", "CMP-01", "Barclays Corporate", "Canary Wharf", "3320194821", "GB12BARC3320194821001", "GBP", "1010-003-GBP", "US_PRIMARY_LEDGER", "GEH US Corp", "John Reynolds", "John Reynolds", "Elena Vasquez", "Robert Vance", "Active", 75000.0, "2026-09-01", now_iso)
    ]
    cur.executemany("INSERT INTO bank_accounts (id, company_id, bank_name, branch, account_number, iban, currency, gl_account, ledger, legal_entity, owner, preparer, reviewer, approver, status, opening_balance, recon_start_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", accounts)

    # 5. Periods
    periods = [
        # ACC-01 Acceptance Test Period (2026-09)
        ("PER-01", "ACC-01", "2026-09", "2026-09-01", "2026-09-30", "In Progress", 100000.0, 108500.0, 100000.0, 100000.0, 1000.0, None, None, None, None, now_iso),
        # ACC-02 Demo Period
        ("PER-02", "ACC-02", "2026-09", "2026-09-01", "2026-09-30", "Draft", 250000.0, 268450.0, 250000.0, 268450.0, 0.0, None, None, None, None, now_iso),
        # ACC-03 Reconciled Period
        ("PER-03", "ACC-03", "2026-09", "2026-09-01", "2026-09-30", "Approved", 500000.0, 524000.0, 500000.0, 524000.0, 0.0, now_iso, "Robert Vance", "Robert Vance", "Elena Vasquez", now_iso)
    ]
    cur.executemany("INSERT INTO periods (id, account_id, period_name, start_date, end_date, status, bank_opening_balance, bank_closing_balance, ledger_opening_balance, ledger_closing_balance, residual_diff, locked_at, locked_by, approved_by, reviewed_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", periods)

    # 6. TRANSACTIONS FOR ACC-01 (Acceptance Test Scenario)
    # Specified in prompt:
    # Ledger closing balance: 100,000.
    # Bank closing balance: 108,500.
    # Ledger-only outstanding payment: signed amount −10,000.
    # Ledger-only deposit in transit: signed amount +2,000.
    # Bank-only charge: signed amount −500.
    # Adjusted bank balance: 108,500 − 10,000 + 2,000 = 100,500.
    # Adjusted ledger balance: 100,000 − 500 = 99,500.
    # Residual difference: 1,000.
    acc1_txs = [
        # Matched base transactions
        ("TX-A1-01", "ACC-01", "PER-01", "Oracle Ledger", "2026-09-05", "2026-09-05", "2026-09-05", "Customer Wire Payment - Zenith Corp", "Zenith Corp", "REF-ZEN-901", "CHK-1001", "PAY-4410", "JE-90112", 0.0, 0.0, 15000.0, "USD", 115000.0, "Oracle_GL_Sep2026.xlsx", 2, "BATCH-01", "Valid", "Matched", "MCH-01", 15000.0, "Receipt", None, now_iso),
        ("TX-A1-02", "ACC-01", "PER-01", "Bank Statement", "2026-09-06", "2026-09-06", "2026-09-06", "INWARD WIRE ZENITH CORP REF-ZEN-901", "Zenith Corp", "REF-ZEN-901", "CHK-1001", "PAY-4410", None, 0.0, 15000.0, 15000.0, "USD", 115000.0, "JPMorgan_Stmt_Sep2026.csv", 4, "BATCH-02", "Valid", "Matched", "MCH-01", 15000.0, "Receipt", None, now_iso),

        # The 3 specific outstanding items from Section 15 Acceptance Test:
        # 1. Ledger-only outstanding payment (-10,000)
        ("TX-A1-03", "ACC-01", "PER-01", "Oracle Ledger", "2026-09-28", "2026-09-28", "2026-09-28", "Vendor Cheque Disbursement - Apex Supplies", "Apex Supplies", "REF-OUT-10K", "CHK-8831", "PAY-9901", "JE-90450", 10000.0, 0.0, -10000.0, "USD", 105000.0, "Oracle_GL_Sep2026.xlsx", 14, "BATCH-01", "Valid", "Unmatched", None, 0.0, "Outstanding Cheque", None, now_iso),
        # 2. Ledger-only deposit in transit (+2,000)
        ("TX-A1-04", "ACC-01", "PER-01", "Oracle Ledger", "2026-09-30", "2026-09-30", "2026-09-30", "Branch Cash Collection Deposit", "Internal Branch", "DEP-2026-99", None, "PAY-9902", "JE-90455", 0.0, 2000.0, 2000.0, "USD", 107000.0, "Oracle_GL_Sep2026.xlsx", 15, "BATCH-01", "Valid", "Unmatched", None, 0.0, "Deposit in Transit", None, now_iso),
        # 3. Bank-only charge (-500)
        ("TX-A1-05", "ACC-01", "PER-01", "Bank Statement", "2026-09-30", "2026-09-30", "2026-09-30", "MONTHLY SERVICE CHARGE & SWIFT FEES", "JPMorgan Chase", "FEE-SEP-26", None, None, None, 500.0, 0.0, -500.0, "USD", 108500.0, "JPMorgan_Stmt_Sep2026.csv", 22, "BATCH-02", "Valid", "Unmatched", None, 0.0, "Bank Charge", None, now_iso)
    ]

    for tx in acc1_txs:
        cur.execute("""
            INSERT INTO transactions (id, account_id, period_id, source, tx_date, posting_date, value_date, description, counterparty, reference, cheque_number, payment_id, journal_id, debit, credit, signed_amount, currency, running_balance, doc_name, doc_row, batch_id, validation_status, recon_status, match_group_id, allocated_amount, category, flags, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, tx)

    # Match group for MCH-01
    cur.execute("""
        INSERT INTO match_groups (id, account_id, period_id, rule_name, match_type, matched_at, matched_by, notes, difference, status)
        VALUES ('MCH-01', 'ACC-01', 'PER-01', 'Exact Reference & Amount', '1-to-1', ?, 'System Engine', 'Auto-matched on REF-ZEN-901', 0.0, 'Confirmed')
    """, (now_iso,))
    cur.execute("INSERT INTO match_group_items (match_group_id, transaction_id, allocated_amount) VALUES ('MCH-01', 'TX-A1-01', 15000.0)")
    cur.execute("INSERT INTO match_group_items (match_group_id, transaction_id, allocated_amount) VALUES ('MCH-01', 'TX-A1-02', 15000.0)")

    # 7. TRANSACTIONS FOR ACC-02 (Interactive Auto-Match Demo Account)
    acc2_samples = [
        # 1-to-1 Exact Reference
        ("TX-A2-L01", "Oracle Ledger", "2026-09-02", "Supplier Wire - Cloud Tech Corp", "REF-CLD-101", "CHK-5501", -8400.0),
        ("TX-A2-B01", "Bank Statement", "2026-09-03", "WIRE OUT CLOUD TECH CORP REF-CLD-101", "REF-CLD-101", "CHK-5501", -8400.0),

        ("TX-A2-L02", "Oracle Ledger", "2026-09-04", "Customer Direct Debit - Delta Logistics", "INV-DLT-882", None, 14250.0),
        ("TX-A2-B02", "Bank Statement", "2026-09-04", "INWARD CREDIT DELTA LOGISTICS INV-DLT-882", "INV-DLT-882", None, 14250.0),

        ("TX-A2-L03", "Oracle Ledger", "2026-09-08", "Office Lease Payment Q3", "LEASE-LON-03", "CHK-5502", -12000.0),
        ("TX-A2-B03", "Bank Statement", "2026-09-09", "DIRECT DEBIT CITY PROPERTIES LEASE-LON-03", "LEASE-LON-03", "CHK-5502", -12000.0),

        ("TX-A2-L04", "Oracle Ledger", "2026-09-12", "Consulting Retainer - KPMG Global", "KPMG-SEP-01", "CHK-5503", -6500.0),
        ("TX-A2-B04", "Bank Statement", "2026-09-14", "FASTER PYMT TO KPMG GLOBAL KPMG-SEP-01", "KPMG-SEP-01", "CHK-5503", -6500.0),

        # 1-to-many: Ledger single entry = 2 Bank transactions
        ("TX-A2-L05", "Oracle Ledger", "2026-09-18", "Payroll Settlement Fortnightly Batch", "PAYROLL-B12", None, -5000.0),
        ("TX-A2-B05a", "Bank Statement", "2026-09-19", "SALARY PAYMENT DEPT 1", "PAY-D1", None, -3000.0),
        ("TX-A2-B05b", "Bank Statement", "2026-09-19", "SALARY PAYMENT DEPT 2", "PAY-D2", None, -2000.0),

        # Outstanding Ledger Payment (timing difference)
        ("TX-A2-L06", "Oracle Ledger", "2026-09-29", "Dividend Payout Check #9910", "DIV-2026", "CHK-9910", -3500.0),
        # Bank charge
        ("TX-A2-B06", "Bank Statement", "2026-09-30", "ACCOUNT MAINTENANCE CHARGE", "CHG-SEP", None, -150.0)
    ]

    for item in acc2_samples:
        t_id, src, dt, desc, ref, chk, signed = item
        debit = abs(signed) if signed < 0 else 0.0
        credit = signed if signed > 0 else 0.0
        cur.execute("""
            INSERT INTO transactions (id, account_id, period_id, source, tx_date, posting_date, value_date, description, counterparty, reference, cheque_number, payment_id, debit, credit, signed_amount, currency, validation_status, recon_status, created_at)
            VALUES (?, 'ACC-02', 'PER-02', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'USD', 'Valid', 'Unmatched', ?)
        """, (t_id, src, dt, dt, dt, desc, "Counterparty", ref, chk, "PAY-" + str(uuid.uuid4().hex[:4]), debit, credit, signed, now_iso))

    # Audit log entry for seeding
    log_audit(conn, "System Setup", "INIT_DEMO_DATA", "system", "all", None, {"companies": len(companies), "accounts": len(accounts)}, "Initial seed with Section 15 Acceptance Test")

    conn.commit()
    conn.close()
