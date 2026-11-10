"""Calculation checks. Run:  python -m unittest test_payroll -v"""
import os
import tempfile
import unittest

import reports
from config import DEFAULT_RATES
from database import Database
from engine import PayInput, calculate, net_to_gross, nssf_limits

R = DEFAULT_RATES


class EngineTests(unittest.TestCase):
    def test_gross_100k_primary(self):
        r = calculate(PayInput(period="2026-03", basic=100000), R)
        self.assertEqual(r["nssf_tier1"], 540.00)
        self.assertEqual(r["nssf_tier2"], 5460.00)          # 6% x (100,000 - 9,000)
        self.assertEqual(r["shif"], 2750.00)
        self.assertEqual(r["ahl_employee"], 1500.00)
        self.assertEqual(r["taxable_pay"], 89750.00)
        self.assertEqual(r["tax_charged"], 21708.35)
        self.assertEqual(r["paye"], 19308.35)
        self.assertEqual(r["net_pay"], 70441.65)
        self.assertEqual(r["employer_cost"], 100000 + 6000 + 1500 + 50)

    def test_nssf_capped_at_uel(self):
        r = calculate(PayInput(period="2026-03", basic=250000), R)
        self.assertEqual(r["nssf_employee"], 6480.00)       # 540 + 5,940

    def test_nssf_schedule_by_period(self):
        self.assertEqual(nssf_limits(R, "2025-06"), (8000, 72000))
        self.assertEqual(nssf_limits(R, "2026-01"), (8000, 72000))
        self.assertEqual(nssf_limits(R, "2026-02"), (9000, 108000))

    def test_low_earner_no_paye_and_shif_minimum(self):
        r = calculate(PayInput(period="2026-03", basic=10000), R)
        self.assertEqual(r["shif"], 300.00)
        self.assertEqual(r["paye"], 0.0)
        self.assertIn("minimum wage", " ".join(r["warnings"]))

    def test_top_band(self):
        r = calculate(PayInput(period="2026-03", basic=1_000_000), R)
        # taxable = 1,000,000 - 6,480 - 27,500 - 15,000
        self.assertEqual(r["taxable_pay"], 951020.00)
        expected = 2400 + 8333 * 0.25 + 467667 * 0.30 + 300000 * 0.325 + (951020 - 800000) * 0.35
        self.assertAlmostEqual(r["tax_charged"], round(expected, 2), places=2)

    def test_pension_cap_and_insurance_relief(self):
        r = calculate(PayInput(period="2026-03", basic=200000, voluntary_pension=40000,
                               insurance_premium=50000), R)
        self.assertEqual(r["pension_allowed"], 30000.00)
        self.assertEqual(r["insurance_relief"], 5000.00)

    def test_non_cash_threshold(self):
        self.assertEqual(calculate(PayInput(period="2026-03", basic=50000, non_cash_benefits=5000), R)["taxable_benefits"], 0)
        self.assertEqual(calculate(PayInput(period="2026-03", basic=50000, non_cash_benefits=6000), R)["taxable_benefits"], 6000)

    def test_disability_exemption(self):
        r = calculate(PayInput(period="2026-03", basic=120000, disabled=True), R)
        self.assertEqual(r["paye"], 0.0)

    def test_secondary_and_consultant(self):
        s = calculate(PayInput(period="2026-03", basic=50000, employment_type="Secondary"), R)
        self.assertEqual(s["personal_relief"], 0.0)
        self.assertEqual(s["paye"], round(s["taxable_pay"] * 0.35, 2))
        c = calculate(PayInput(period="2026-03", basic=80000, employment_type="Consultant (WHT)"), R)
        self.assertEqual(c["wht"], 4000.00)
        self.assertEqual(c["net_pay"], 76000.00)

    def test_overtime_and_absence(self):
        r = calculate(PayInput(period="2026-03", basic=45000, ot_normal_hours=10, ot_holiday_hours=5,
                               absent_days=2), R)
        self.assertEqual(r["overtime"], round(45000 / 225 * (15 + 10), 2))
        self.assertEqual(r["absence"], 3000.00)

    def test_net_to_gross(self):
        basic, r = net_to_gross(70441.65, PayInput(period="2026-03"), R)
        self.assertAlmostEqual(basic, 100000, delta=0.05)


class DatabaseFlowTests(unittest.TestCase):
    def test_run_close_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(os.path.join(tmp, "t.db"))
            emp = db.save_employee({"staff_no": "LA001", "first_name": "Jane", "last_name": "Wanjiku",
                                    "kra_pin": "A012345678Z", "basic_salary": 80000, "house_allowance": 15000,
                                    "hire_date": "2025-01-01", "status": "Active", "employment_type": "Primary"})
            db.save_employee({"staff_no": "LA002", "first_name": "Otieno", "last_name": "Odhiambo",
                              "basic_salary": 60000, "hire_date": "2026-03-16", "status": "Active",
                              "employment_type": "Primary"})
            db.add_deduction(emp, "Loan", "Staff loan", 5000, 12000, "2026-03")
            db.save_inputs(emp, "2026-03", {"bonus": 10000, "ot_normal_hours": 4})
            lines, warnings = db.run_payroll("2026-03")
            self.assertEqual(len(lines), 2)
            joiner = [l for l in lines if l["employee"]["staff_no"] == "LA002"][0]
            self.assertAlmostEqual(joiner["proration"], 16 / 31, places=3)
            self.assertTrue(any("LA002" in w and "KRA PIN" in w for w in warnings))
            db.close_period("2026-03")
            self.assertEqual(db.deductions(emp)[0]["balance"], 7000)
            for _, fn in reports.ALL_PERIOD_REPORTS:
                self.assertTrue(os.path.exists(fn(db, "2026-03", tmp)))
            self.assertTrue(os.path.exists(reports.p9a(db, 2026, tmp)))
            db.reopen_period("2026-03")
            self.assertEqual(db.deductions(emp)[0]["balance"], 12000)
            db.conn.close()


if __name__ == "__main__":
    unittest.main()
