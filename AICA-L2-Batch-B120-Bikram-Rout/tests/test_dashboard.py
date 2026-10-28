"""Regression test for: 'Failed to load dashboard: Cannot read properties of undefined (reading '0-30')'.
Run from the project root:  python -m unittest tests/test_dashboard.py
"""
import os, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["BRS_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")

from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.database import init_db
from backend.seed_data import seed_database
from backend.api import router

REQUIRED = ["total_accounts", "reconciled_accounts", "unreconciled_accounts", "match_rate_percentage",
            "matched_tx_count", "unmatched_tx_count", "gross_unmatched_exposure", "total_residual_variance",
            "pending_periods", "currency_balances", "top_variances", "aging_buckets"]

class DashboardContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db(); seed_database(force=False)
        app = FastAPI(); app.include_router(router)
        cls.client = TestClient(app)

    def test_summary_has_every_key_the_frontend_reads(self):
        r = self.client.get("/api/dashboard/summary")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        for k in REQUIRED:
            self.assertIn(k, d)
        for b in ("0-30", "31-60", "61-90", "90+"):
            self.assertIn(b, d["aging_buckets"])

    def test_acceptance_account_residual_is_1000(self):
        d = self.client.get("/api/dashboard/summary").json()
        v = [x for x in d["top_variances"] if x["account_id"] == "ACC-01"][0]
        self.assertEqual(v["residual_diff"], 1000.0)
        self.assertTrue(v["company_name"])

if __name__ == "__main__":
    unittest.main()
