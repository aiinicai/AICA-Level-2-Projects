from decimal import Decimal
from pathlib import Path
import sys
import unittest

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
from engine import prepare
from monthly import Monthly, CLOSE, OPEN, MOVE, PDC
from sources import InputError


class MonthlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.week=APP/"demo_week"
        cls.model=prepare(cls.week)

    def setUp(self):
        self.view=Monthly(self.model)

    def test_combined_month_rolls_balances_and_adds_flows(self):
        split=self.view.groups(False)
        self.assertEqual(len(split),5)
        combined=self.view.groups(True)
        self.assertEqual(combined[1],("2026-11 actual","2026-11 remaining"))
        self.assertEqual(self.view.value(OPEN,combined[1]),Decimal("44400"))
        self.assertEqual(self.view.value(CLOSE,combined[1]),Decimal("33899.375"))
        self.assertEqual(self.view.value(MOVE,combined[1]),Decimal("-10500.625"))
        for group in split+combined:
            for row in self.view.rows:
                lines=self.view.detail(row,group)
                self.assertEqual(sum(r[-1] for r in lines),self.view.value(row,group))

    def test_pdc_detail_retains_exclusions(self):
        records=self.view.detail(PDC,("2026-11 remaining",))
        self.assertEqual(sum(r[-1] for r in records),Decimal("-6000.375"))
        replaced=[r for r in records if "LTR-704" in r[1]]
        self.assertEqual(len(replaced),2)
        self.assertTrue(all("PDC.pdf" in r[2] and r[3]==0 for r in replaced))

    def test_prior_uses_month_end_and_project_codes(self):
        self.view.load_demo_previous(self.week/"Previous cash flow.xlsx")
        self.assertEqual(self.view.previous["2026-11",CLOSE],Decimal("38899.375"))
        for row in (CLOSE,"project:00107"):
            self.assertEqual(self.view.month_values("2026-11")[row]-self.view.previous["2026-11",row],-5000)
        self.assertEqual(self.view.month_values("2026-12")[CLOSE],self.view.previous["2026-12",CLOSE])

    def test_absent_or_same_week_comparator(self):
        with self.assertRaises(InputError):
            self.view.load_demo_previous(self.week/"Absent.xlsx")
        with self.assertRaises(InputError):
            self.view.load_demo_previous(APP/"example_output"/"Construction Cash Flow.xlsx")
        self.assertFalse(self.view.previous)
