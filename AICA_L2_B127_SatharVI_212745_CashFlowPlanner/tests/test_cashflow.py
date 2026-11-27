import hashlib
import shutil
import sys
import tempfile
import unittest
from decimal import Decimal as D
from pathlib import Path

from openpyxl import load_workbook

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from engine import prepare
from excel_report import layout, save
from review import QUESTIONS, answer, topic
from sources import InputError
from make_demo_pdfs import build as build_pdfs


def hashes(folder):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()}


class CashFlowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.week = self.root / "week"
        shutil.copytree(APP / "demo_week", self.week)

    def edit(self, file, sheet, changes):
        path = self.week / file
        book = load_workbook(path)
        for key, value in changes.items():
            book[sheet][key] = value
        book.save(path)
        book.close()

    def test_decimal_control_totals_and_rerun(self):
        before = hashes(self.week)
        m = prepare(self.week)
        self.assertEqual(list(m.closing.values()), [D(n) for n in ("44400", "50249.750", "33899.375", "-7050.750", "14499.250")])
        self.assertEqual(m.closing, prepare(self.week).closing)
        self.assertEqual(before, hashes(self.week))

    def test_cheques_replacements_and_net_cost(self):
        m = prepare(self.week)
        self.assertEqual(m.totals["2026-11 remaining", "PDC"], D("-6000.375"))
        self.assertEqual(m.totals["2026-12 forecast", "PDC"], D("-6200"))
        self.assertEqual(m.totals["2026-12 forecast", "LC/LTR"], D("-7250.125"))
        self.assertEqual(m.totals["2026-11 remaining", "Materials"], D("-12000"))
        reasons = {e.reference:e.reason for e in m.entries}
        for ref in ("CH-022","CH-023"):
            self.assertEqual(reasons[ref], "Replaced by LTR-704")
        self.assertEqual(reasons["CH-024"], "Security")
        self.assertEqual(reasons["INV-015"], "Deferred")

    def test_excel_formulas_and_period_summaries(self):
        m = prepare(self.week)
        path = save(m, self.root / "demo.xlsx")
        saved = load_workbook(path, data_only=True)
        self.assertEqual(saved.sheetnames, ["Cash flow","Period summary","Cash entries","Reconciliations","Sources"])
        row = layout().index("Closing cash") + 5
        self.assertEqual(saved["Cash flow"][f"E{row}"].value, -7050.75)
        self.assertEqual(saved["Period summary"]["G6"].value, 33899.375)  # November actual + remaining
        self.assertEqual(saved["Period summary"]["B9"].value, 39000)      # covered 2026 opening
        self.assertEqual(saved["Period summary"]["G9"].value, -7050.75)
        self.assertEqual(saved["Period summary"]["B10"].value, -7050.75)
        self.assertTrue(all(r[3]==0 for r in saved["Reconciliations"].iter_rows(min_row=5, values_only=True)))
        saved.close()
        formula = load_workbook(path)
        self.assertIn("SUMIFS", formula["Cash flow"]["E6"].value)
        self.assertEqual(formula["Cash flow"]["F5"].value, f"=E{row}")
        formula.close()
        with self.assertRaisesRegex(InputError, "already exists"):
            save(m,path)

    def test_edit_management_timing(self):
        self.edit("Starting Model.xlsx","Plan",{"C3":"2027-01"})
        m = prepare(self.week)
        self.assertEqual(m.closing["2026-11 remaining"], D("17899.375"))
        self.assertEqual(m.closing["2026-12 forecast"], D("-23050.75"))
        self.assertEqual(m.closing["2027-01 forecast"], D("14499.25"))

    def test_missing_and_duplicate_files(self):
        shutil.copyfile(self.week/"CF.pdf", self.week/"ACTCF-21-11-2026.pdf")
        (self.week/"LC.xlsx").unlink()
        with self.assertRaises(InputError) as error:
            prepare(self.week)
        self.assertIn("Multiple files for Summary",str(error.exception))
        self.assertIn("Missing LC.xlsx",str(error.exception))

    def test_stale_snapshot(self):
        self.edit("Creditors.xlsx","Net",{"B1":"2026-11-06"})
        with self.assertRaisesRegex(InputError,"2026-11-06"):
            prepare(self.week)

    def test_unmatched_replacement(self):
        build_pdfs(self.week, replacement="LTR-UNKNOWN")
        with self.assertRaisesRegex(InputError,"needs an outstanding LTR"):
            prepare(self.week)

    def test_future_register_control(self):
        from make_demo_pdfs import draw
        draw(self.week/"CF-Proj.pdf","Projected payments",("Month","Category","Amount"),(42,228,614),
             [("2026-12","PDC Payable","0.000"),("2027-01","PDC Payable","2400.000")])
        with self.assertRaisesRegex(InputError,"Future PDC"):
            prepare(self.week)

    def test_missing_is_not_zero(self):
        self.edit("Material Purchase.xlsx","CF-DTLD",{"D3":None})
        with self.assertRaisesRegex(InputError,"expected an amount"):
            prepare(self.week)

    def test_source_overlap(self):
        self.edit("Creditors.xlsx","Net",{"A3":"LTR-704"})
        with self.assertRaisesRegex(InputError,"duplicate reference"):
            prepare(self.week)

    def test_lifetime_collections(self):
        self.edit("Starting Model.xlsx","Plan",{"E3":17000})
        with self.assertRaisesRegex(InputError,"00107"):
            prepare(self.week)

    def test_no_unexplained_actual_difference(self):
        self.edit("Starting Model.xlsx","History",{"B3":39001,"T3":44401})
        with self.assertRaisesRegex(InputError,"Opening agrees to prior month"):
            prepare(self.week)

    def test_offline_review_and_evidence(self):
        m = prepare(self.week)
        for key, examples in QUESTIONS.items():
            self.assertEqual(topic(examples[0]), key)
            self.assertIn("Cash ", answer(m, examples[0]))
        self.assertIn("7,050.750", answer(m,"When is cash lowest?"))
        self.assertIn("LTR-704", answer(m,"Which cheques or payments were excluded?"))
        self.assertIsNone(topic("how do I bake bread"))


if __name__ == "__main__":
    unittest.main()
