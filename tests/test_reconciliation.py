import unittest
import os
import sys
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db import init_db, get_connection
from src.import_engine import load_sample_trial_balance, save_imported_ledgers
from src.mapping_engine import execute_auto_mapping, get_mapping_register
from src.reconciliation_engine import run_reconciliation_check
from src.statement_generator import generate_financial_statements
from src.export_engine import export_excel_working_papers, export_word_draft, export_pdf_report

class TestScheduleIIIBuilder(unittest.TestCase):

    def setUp(self):
        init_db()

    def test_sample_tb_import_and_mapping(self):
        ledgers = load_sample_trial_balance("Manufacturing")
        self.assertGreater(len(ledgers), 0, "Sample ledgers should not be empty")

        mapped_count, review_count = execute_auto_mapping()
        self.assertGreater(mapped_count, 0, "Mapped ledgers count should be > 0")

        mappings = get_mapping_register()
        self.assertEqual(len(mappings), len(ledgers), "Mapping register should match imported ledger count")

    def test_reconciliation_balance(self):
        load_sample_trial_balance("Manufacturing")
        execute_auto_mapping()

        recon = run_reconciliation_check()
        self.assertTrue(recon['tb_stats']['is_balanced'], "Sample Trial Balance should be mathematically balanced")
        self.assertTrue(recon['financial_totals']['is_bs_balanced'], "Balance Sheet Assets should equal Equity + Liabilities")
        self.assertAlmostEqual(recon['financial_totals']['bs_diff'], 0.0, delta=1.0, msg="Balance Sheet difference should be zero")

    def test_financial_statements_generation(self):
        load_sample_trial_balance("Manufacturing")
        execute_auto_mapping()

        data = generate_financial_statements()
        self.assertIn('bs_equity_liabilities', data)
        self.assertIn('bs_assets', data)
        self.assertIn('pl_revenue_ops_cy', data)
        self.assertIn('ratios', data)
        self.assertEqual(len(data['ratios']), 11, "Should generate 11 mandatory Schedule III ratios")

    def test_exports_generation(self):
        load_sample_trial_balance("Manufacturing")
        execute_auto_mapping()

        test_export_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_exports")
        os.makedirs(test_export_dir, exist_ok=True)

        excel_path = os.path.join(test_export_dir, "test_working_papers.xlsx")
        word_path = os.path.join(test_export_dir, "test_draft.docx")
        pdf_path = os.path.join(test_export_dir, "test_report.pdf")

        export_excel_working_papers(excel_path)
        export_word_draft(word_path)
        export_pdf_report(pdf_path)

        self.assertTrue(os.path.exists(excel_path), "Excel export file should exist")
        self.assertTrue(os.path.exists(word_path), "Word export file should exist")
        self.assertTrue(os.path.exists(pdf_path), "PDF export file should exist")

if __name__ == '__main__':
    unittest.main()
