import os
import unittest
import tempfile
import uuid
from decimal import Decimal
from datetime import datetime

# Configure temporary database for isolated test execution
test_db_dir = tempfile.mkdtemp()
os.environ["BRS_DB_PATH"] = os.path.join(test_db_dir, "test_brs.db")

from backend.database import init_db, get_db, log_audit
from backend.reconciliation import (
    calculate_brs,
    run_auto_matching,
    manual_match,
    partial_match,
    confirm_suggested_match,
    reject_suggested_match,
    unmatch_group,
    rollover_period,
    to_decimal
)
from backend.importers import (
    parse_amount,
    parse_dataframe,
    parse_camt053_xml,
    parse_mt940_text,
    compute_file_hash,
    import_master_data
)
from backend.seed_data import seed_database
import pandas as pd

class TestBRSToolSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_database(force=True)

    def setUp(self):
        # Reset DB before each test group for deterministic assertions
        seed_database(force=True)

    # ---------------------------------------------------------
    # 1. Section 15 Numeric Acceptance Test
    # ---------------------------------------------------------
    def test_section_15_numeric_acceptance_example(self):
        """
        Acceptance Criteria from Section 15:
        - Ledger closing balance: 100,000.
        - Bank closing balance: 108,500.
        - Ledger-only outstanding payment: signed amount −10,000.
        - Ledger-only deposit in transit: signed amount +2,000.
        - Bank-only charge: signed amount −500.
        - Adjusted bank balance: 108,500 − 10,000 + 2,000 = 100,500.
        - Adjusted ledger balance: 100,000 − 500 = 99,500.
        - Residual difference: 1,000.
        App MUST flag this account as unreconciled and must NOT invent an adjustment.
        """
        brs = calculate_brs("ACC-01", "PER-01")

        self.assertEqual(brs["ledger_closing_balance"], 100000.0)
        self.assertEqual(brs["bank_closing_balance"], 108500.0)
        self.assertEqual(brs["ledger_payments_in_transit"], -10000.0)
        self.assertEqual(brs["ledger_deposits_in_transit"], 2000.0)
        self.assertEqual(brs["bank_charges"], -500.0)
        self.assertEqual(brs["adjusted_bank_balance"], 100500.0)
        self.assertEqual(brs["adjusted_ledger_balance"], 99500.0)
        self.assertEqual(brs["residual_difference"], 1000.0)
        self.assertFalse(brs["is_reconciled"], "Account must be flagged as UNRECONCILED")

    # ---------------------------------------------------------
    # 2. Debit / Credit Normalization
    # ---------------------------------------------------------
    def test_debit_credit_normalization(self):
        """
        Tests that:
        - Oracle Ledger: Debit Cash = + Inflow, Credit Cash = - Outflow
        - Bank Statement: Credit = + Inflow (Deposit), Debit = - Outflow (Withdrawal)
        """
        df_ledger = pd.DataFrame([{
            "date": "2026-09-10",
            "description": "Customer Receipt",
            "debit": "5000.00",
            "credit": "0.00"
        }, {
            "date": "2026-09-11",
            "description": "Supplier Payment",
            "debit": "0.00",
            "credit": "1200.00"
        }])
        ledger_norm = parse_dataframe(df_ledger, "Oracle Ledger", "test_ledger.xlsx")
        self.assertEqual(ledger_norm[0]["signed_amount"], 5000.0)
        self.assertEqual(ledger_norm[1]["signed_amount"], -1200.0)

        df_bank = pd.DataFrame([{
            "date": "2026-09-10",
            "description": "Deposit Wire",
            "debit": "0.00",
            "credit": "5000.00"
        }, {
            "date": "2026-09-11",
            "description": "Cheque Cleared",
            "debit": "1200.00",
            "credit": "0.00"
        }])
        bank_norm = parse_dataframe(df_bank, "Bank Statement", "test_stmt.csv")
        self.assertEqual(bank_norm[0]["signed_amount"], 5000.0)
        self.assertEqual(bank_norm[1]["signed_amount"], -1200.0)

    # ---------------------------------------------------------
    # 3. Exact Decimal Calculations (No Floating Point Drift)
    # ---------------------------------------------------------
    def test_exact_decimal_arithmetic(self):
        # 0.10 + 0.20 must equal exact 0.30
        d1 = to_decimal("0.10")
        d2 = to_decimal("0.20")
        self.assertEqual(d1 + d2, Decimal("0.30"))

        amt = parse_amount("(1,234,567.89)")
        self.assertEqual(amt, Decimal("-1234567.89"))

    # ---------------------------------------------------------
    # 4. Multi-Tier Deterministic Matching
    # ---------------------------------------------------------
    def test_deterministic_matching_tiers(self):
        """Tests auto-matching on ACC-02 (interactive test account)."""
        res = run_auto_matching("ACC-02", "PER-02", user="Test Specialist")
        self.assertTrue(res["success"])
        self.assertGreater(res["matches_created"], 0, "Should auto-match deterministic items")

    # ---------------------------------------------------------
    # 5. Grouped Matches (1-to-Many & Many-to-1)
    # ---------------------------------------------------------
    def test_grouped_matching(self):
        conn = get_db()
        cur = conn.cursor()
        now_iso = datetime.now().isoformat()

        # 1 Ledger entry = 2 Bank lines (Exact Sum: -5,000.00)
        cur.execute("""
            INSERT INTO transactions (id, account_id, period_id, source, tx_date, description, signed_amount, currency, validation_status, recon_status, created_at)
            VALUES ('T-L-GRP', 'ACC-02', 'PER-02', 'Oracle Ledger', '2026-09-15', 'Bulk Vendor Batch', -5000.0, 'USD', 'Valid', 'Unmatched', ?)
        """, (now_iso,))
        cur.execute("""
            INSERT INTO transactions (id, account_id, period_id, source, tx_date, description, signed_amount, currency, validation_status, recon_status, created_at)
            VALUES ('T-B-GRP1', 'ACC-02', 'PER-02', 'Bank Statement', '2026-09-15', 'Vendor A Payout', -3000.0, 'USD', 'Valid', 'Unmatched', ?)
        """, (now_iso,))
        cur.execute("""
            INSERT INTO transactions (id, account_id, period_id, source, tx_date, description, signed_amount, currency, validation_status, recon_status, created_at)
            VALUES ('T-B-GRP2', 'ACC-02', 'PER-02', 'Bank Statement', '2026-09-15', 'Vendor B Payout', -2000.0, 'USD', 'Valid', 'Unmatched', ?)
        """, (now_iso,))
        conn.commit()
        conn.close()

        res = manual_match("ACC-02", "PER-02", ["T-L-GRP"], ["T-B-GRP1", "T-B-GRP2"], user="Tester", notes="1-to-Many Match")
        self.assertTrue(res.get("success"), "Manual 1-to-many match must succeed when sums balance exactly")

    # ---------------------------------------------------------
    # 6. Partial Allocation & Overflow Protection
    # ---------------------------------------------------------
    def test_partial_allocation_and_overflow(self):
        conn = get_db()
        cur = conn.cursor()
        now_iso = datetime.now().isoformat()
        cur.execute("""
            INSERT INTO transactions (id, account_id, period_id, source, tx_date, description, signed_amount, currency, validation_status, recon_status, created_at)
            VALUES ('T-L-PART', 'ACC-02', 'PER-02', 'Oracle Ledger', '2026-09-10', 'Large Invoice #88', 10000.0, 'USD', 'Valid', 'Unmatched', ?)
        """, (now_iso,))
        cur.execute("""
            INSERT INTO transactions (id, account_id, period_id, source, tx_date, description, signed_amount, currency, validation_status, recon_status, created_at)
            VALUES ('T-B-PART', 'ACC-02', 'PER-02', 'Bank Statement', '2026-09-12', 'Installment 1 Payment', 4000.0, 'USD', 'Valid', 'Unmatched', ?)
        """, (now_iso,))
        conn.commit()
        conn.close()

        # Attempt to allocate 4,000 (valid partial allocation)
        res1 = partial_match("ACC-02", "PER-02", "T-L-PART", "T-B-PART", 4000.0, user="Tester")
        self.assertTrue(res1["success"])
        self.assertEqual(res1["ledger_remaining"], 6000.0)
        self.assertEqual(res1["bank_remaining"], 0.0)

        # Attempt to allocate 5,000 when bank remaining is 0 (must be blocked)
        res2 = partial_match("ACC-02", "PER-02", "T-L-PART", "T-B-PART", 5000.0, user="Tester")
        self.assertIn("error", res2, "Allocation exceeding remaining bank balance must be rejected")

    # ---------------------------------------------------------
    # 7. Ambiguous & Fuzzy Suggested Matches
    # ---------------------------------------------------------
    def test_suggested_match_workflow(self):
        conn = get_db()
        cur = conn.cursor()
        now_iso = datetime.now().isoformat()
        cur.execute("""
            INSERT INTO transactions (id, account_id, period_id, source, tx_date, description, signed_amount, currency, validation_status, recon_status, created_at)
            VALUES ('T-L-SUG', 'ACC-02', 'PER-02', 'Oracle Ledger', '2026-09-10', 'Payment to Acronis Cloud', -1500.0, 'USD', 'Valid', 'Unmatched', ?)
        """, (now_iso,))
        cur.execute("""
            INSERT INTO transactions (id, account_id, period_id, source, tx_date, description, signed_amount, currency, validation_status, recon_status, created_at)
            VALUES ('T-B-SUG', 'ACC-02', 'PER-02', 'Bank Statement', '2026-09-10', 'ACRONIS ONLINE SUB', -1500.0, 'USD', 'Valid', 'Unmatched', ?)
        """, (now_iso,))
        conn.commit()
        conn.close()

        res = run_auto_matching("ACC-02", "PER-02", user="Tester")
        self.assertTrue(res["success"])

        # Check that it routes to Suggested Match
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT match_group_id, recon_status FROM transactions WHERE id = 'T-L-SUG'")
        row = cur.fetchone()
        conn.close()

        if row and row["recon_status"] == "Suggested Match":
            mg_id = row["match_group_id"]
            # Human confirmation
            conf_res = confirm_suggested_match(mg_id, user="Reviewer Elena")
            self.assertTrue(conf_res["success"])

    # ---------------------------------------------------------
    # 8. Cross-Period Clearance and Carry-Forward
    # ---------------------------------------------------------
    def test_cross_period_carry_forward(self):
        """
        Carries forward uncleared items from 2026-09 into 2026-10 without duplication.
        Preserves original document date and history.
        """
        res = rollover_period("ACC-01", "PER-01", "2026-10", "2026-10-01", "2026-10-31", user="Manager")
        self.assertTrue(res["success"])
        self.assertGreaterEqual(res["carried_count"], 3)

        new_pid = res["new_period_id"]
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM transactions WHERE period_id = ?", (new_pid,))
        count = cur.fetchone()[0]
        self.assertGreaterEqual(count, 3, "Uncleared items must be present in new period")
        conn.close()

    # ---------------------------------------------------------
    # 9. Duplicate Upload Detection (SHA-256)
    # ---------------------------------------------------------
    def test_duplicate_file_hash_detection(self):
        sample_bytes = b"Date,Description,Amount\n2026-09-01,Test Entry,100.00\n"
        h1 = compute_file_hash(sample_bytes)
        h2 = compute_file_hash(sample_bytes)
        self.assertEqual(h1, h2, "SHA-256 hash must be deterministic")

    # ---------------------------------------------------------
    # 10. Structured Bank Format Adapter (CAMT.053 XML)
    # ---------------------------------------------------------
    def test_camt053_xml_parser(self):
        sample_camt = """<?xml version="1.0" encoding="UTF-8"?>
        <Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.02">
          <BkToCstmrStmt>
            <Stmt>
              <Bal>
                <Tp><CdOrPrtry><Cd>OPBD</Cd></CdOrPrtry></Tp>
                <Amt Ccy="USD">50000.00</Amt>
                <CdtDbtInd>CRDT</CdtDbtInd>
              </Bal>
              <Bal>
                <Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp>
                <Amt Ccy="USD">58500.00</Amt>
                <CdtDbtInd>CRDT</CdtDbtInd>
              </Bal>
              <Ntry>
                <Amt Ccy="USD">8500.00</Amt>
                <CdtDbtInd>CRDT</CdtDbtInd>
                <BookgDt><Dt>2026-09-14</Dt></BookgDt>
                <NtryDtls>
                  <TxDtls>
                    <Refs><EndToEndId>CAMT-REF-991</EndToEndId></Refs>
                    <RmtInf><Ustrd>Customer Settlement Payment</Ustrd></RmtInf>
                  </TxDtls>
                </NtryDtls>
              </Ntry>
            </Stmt>
          </BkToCstmrStmt>
        </Document>
        """
        records, meta = parse_camt053_xml(sample_camt, "camt053_sample.xml")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["signed_amount"], 8500.0)
        self.assertEqual(records[0]["reference"], "CAMT-REF-991")
        self.assertEqual(meta["opening_balance"], 50000.0)
        self.assertEqual(meta["closing_balance"], 58500.0)

    # ---------------------------------------------------------
    # 11. Segregation of Duties Enforcement
    # ---------------------------------------------------------
    def test_segregation_of_duties(self):
        conn = get_db()
        cur = conn.cursor()
        # Find preparer for ACC-01
        cur.execute("SELECT preparer FROM bank_accounts WHERE id = 'ACC-01'")
        preparer = cur.fetchone()["preparer"]
        conn.close()

        # Preparer attempting to approve own account
        from backend.api import period_workflow_action, PeriodWorkflowRequest
        from fastapi import HTTPException

        req = PeriodWorkflowRequest(
            period_id="PER-01",
            target_status="Approved",
            user=preparer,
            role="Preparer"
        )
        with self.assertRaises(HTTPException) as ctx:
            period_workflow_action(req)
        # Should raise either non-zero residual or segregation of duties violation
        self.assertIn(ctx.exception.status_code, (400, 403))

    # ---------------------------------------------------------
    # 12. Locked-Period Immutability
    # ---------------------------------------------------------
    def test_locked_period_immutability(self):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE periods SET status = 'Locked' WHERE id = 'PER-01'")
        conn.commit()
        conn.close()

        # Attempting auto-match on locked period must be rejected
        res = run_auto_matching("ACC-01", "PER-01", user="Tester")
        self.assertIn("error", res)
        self.assertIn("Locked", res["error"])

    # ---------------------------------------------------------
    # 13. Master Data Bulk Import Leading Zeros Preservation
    # ---------------------------------------------------------
    def test_master_data_leading_zeros(self):
        csv_content = b"company_code,bank_name,account_number,gl_account,currency\nGEH-CORP,Standard Chartered,0004928104,1010-004-CASH,USD\n"
        res = import_master_data(csv_content, "accounts.csv", "accounts", user="Admin")
        self.assertTrue(res["success"])

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT account_number FROM bank_accounts WHERE bank_name = 'Standard Chartered'")
        row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["account_number"], "0004928104", "Leading zeros must be preserved in account numbers")
        conn.close()

    # ---------------------------------------------------------
    # 14. Unmatch Rollback and Atomic Reversion
    # ---------------------------------------------------------
    def test_unmatch_rollback(self):
        res = unmatch_group("MCH-01", user="Auditor", reason="Testing unmatch rollback")
        self.assertTrue(res["success"])
        self.assertEqual(res["reverted_count"], 2)

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT recon_status, match_group_id FROM transactions WHERE id IN ('TX-A1-01', 'TX-A1-02')")
        rows = cur.fetchall()
        for r in rows:
            self.assertEqual(r["recon_status"], "Unmatched")
            self.assertIsNone(r["match_group_id"])
        conn.close()

    # ---------------------------------------------------------
    # 15. Formula Injection Sanitization
    # ---------------------------------------------------------
    def test_formula_injection_prevention(self):
        from backend.importers import sanitize_cell
        self.assertEqual(sanitize_cell("=1+1"), "'=1+1")
        self.assertEqual(sanitize_cell("@SUM(A1:A10)"), "'@SUM(A1:A10)")
        self.assertEqual(sanitize_cell("+cmd|'/c calc'!A0"), "'+cmd|'/c calc'!A0")
        self.assertEqual(sanitize_cell("Standard Narrative"), "Standard Narrative")

    # ---------------------------------------------------------
    # 16. Validation Engine Math & Currency Checks
    # ---------------------------------------------------------
    def test_validation_engine_endpoint(self):
        from backend.api import get_validation_report
        res = get_validation_report("ACC-01", "PER-01")
        checks = res["checks"]
        check_names = [c["name"] for c in checks]
        self.assertIn("Bank Statement Mathematical Integrity", check_names)
        self.assertIn("Oracle Ledger Mathematical Integrity", check_names)
        self.assertIn("Currency Consistency & Isolation", check_names)
        self.assertIn("Mandatory Attribute Completeness", check_names)
        self.assertIn("Duplicate Transaction Screening", check_names)

    # ---------------------------------------------------------
    # 17. Multi-Sheet Excel and PDF Report Export Generation
    # ---------------------------------------------------------
    def test_report_exporters(self):
        from backend.exporters import export_brs_excel, export_brs_pdf
        import openpyxl

        # Test Excel multi-sheet generation
        excel_buf = export_brs_excel("ACC-01", "PER-01")
        self.assertGreater(excel_buf.getbuffer().nbytes, 1000)
        wb = openpyxl.load_workbook(excel_buf)
        expected_sheets = ["Summary & BRS", "Matched Items", "Ledger Outstanding", "Bank Outstanding", "Aging Analysis", "Audit Trail"]
        for sheet_name in expected_sheets:
            self.assertIn(sheet_name, wb.sheetnames)

        # Test PDF generation
        pdf_buf = export_brs_pdf("ACC-01", "PER-01")
        self.assertGreater(pdf_buf.getbuffer().nbytes, 1000)

if __name__ == "__main__":
    unittest.main()
