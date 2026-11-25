"""Automated smoke tests for the standalone Windows v0 Edition (v0/)."""

from __future__ import annotations

import io
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app import config
from app.database import init_db
from app.main import app


class V0EditionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        p = Path(self.tmpdir.name)
        config.DATA_DIR = p / "data"
        config.EXPORTS_DIR = config.DATA_DIR / "exports"
        config.UPLOADS_DIR = p / "uploads"
        config.DB_PATH = config.DATA_DIR / "v0_test.db"
        config.MASTER_EXCEL_PATH = config.EXPORTS_DIR / "v0_assets_master.xlsx"
        init_db()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_v0_end_to_end_workflows_without_auth(self) -> None:
        # Home page loads directly with zero login redirect
        r_home = self.client.get("/")
        self.assertEqual(r_home.status_code, 200)
        self.assertNotIn("Developed by", r_home.text)

        # Vendor CRUD
        v = self.client.post("/api/vendors", json={"name": "AC Care", "vendor_type": "SERVICE_CENTER", "phone": "+919861022334"}).json()

        # Manual Asset -> Auto Tag + QR SVG + Print Page + Asset Detail Page
        a = self.client.post(
            "/api/assets",
            json={
                "name": "Daikin Split AC",
                "category": "ELECTRICAL",
                "location": "Boardroom",
                "purchase_cost": 55000,
                "vendor_id": v["id"],
                "next_maintenance_date": (date.today() + timedelta(days=3)).isoformat(),
            },
        ).json()
        self.assertEqual(a["asset_tag"], "AST-ELEC-001")
        self.assertEqual(self.client.get(f"/api/assets/{a['id']}/qr.svg").status_code, 200)
        self.assertEqual(self.client.get("/qr/print").status_code, 200)
        self.assertEqual(self.client.get(f"/assets/{a['id']}").status_code, 200)

        # Singular Maintenance Log (create + complete)
        m = self.client.post(
            "/api/maintenance",
            json={"asset_id": a["id"], "vendor_id": v["id"], "scheduled_date": date.today().isoformat(), "description": "Filter wash"},
        ).json()
        self.assertEqual(self.client.put(f"/api/maintenance/{m['id']}", json={"status": "COMPLETED"}).status_code, 200)

        # Stationery +/- adjust + wa.me link
        s = self.client.post(
            "/api/stationery",
            json={"item_name": "A4 Paper", "category": "PAPER", "current_stock": 5, "unit": "Reams", "minimum_reorder_threshold": 5, "preferred_vendor_id": v["id"]},
        ).json()
        self.assertEqual(self.client.post(f"/api/stationery/{s['id']}/adjust", json={"delta": -2}).json()["current_stock"], 3)

        # Dashboard returns wa.me links (no API/scheduler)
        dash = self.client.get("/api/dashboard").json()
        self.assertEqual(dash["kpis"]["low_stock_count"], 1)
        self.assertIn("https://wa.me/919861022334", dash["low_stock_alerts"][0]["wa_url"])

        # 4-sheet Master Excel export
        dl = self.client.get("/api/export/excel")
        self.assertEqual(dl.status_code, 200)
        wb = load_workbook(io.BytesIO(dl.content))
        self.assertEqual(wb.sheetnames, ["Fixed Assets", "Maintenance Log", "Vendor Directory", "Stationery & Stock"])


if __name__ == "__main__":
    unittest.main()
