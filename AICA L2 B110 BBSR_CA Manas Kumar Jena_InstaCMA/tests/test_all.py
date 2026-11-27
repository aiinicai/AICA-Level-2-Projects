"""
Automated tests for CMA Builder V2.

    python -m unittest tests/test_all.py -v

The workbook recalculation and PDF tests need LibreOffice (or run on a PC with
Excel through the app); they are skipped when LibreOffice is not installed.
"""
import copy
import glob
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from analysis import term_loan_engine as tle                    # noqa: E402
from analysis.engine import compute, existing_loan_schedule, suggest_tl_amount   # noqa: E402
from analysis.layout import SINGLE_HEADS                         # noqa: E402
from analysis.mapper import map_label                            # noqa: E402
from analysis.rounding import xround                             # noqa: E402
from analysis.validator2 import validate, has_errors            # noqa: E402
from core.models import CMAProject, YearDef, ExistingLoan       # noqa: E402
from core.sample_data import sample_trading, sample_company, TRADING_LINES, KALINGA_LINES   # noqa: E402
from extraction.reader import read_files                        # noqa: E402
from extraction.statement_detector import parse_amount, detect_years   # noqa: E402
from reports.cma_writer import generate_workbook                 # noqa: E402

SAMPLES = os.path.join(ROOT, "samples")
OUT = os.path.join(ROOT, "test_output")
os.makedirs(OUT, exist_ok=True)
FIRM = {"firm_name": "ABC & CO", "firm_frn": "000000E", "preparer_name": "Test Partner", "preparer_membership": "000000",
        "preparer_designation": "Partner", "firm_address": "Bhubaneswar", "firm_place": "Bhubaneswar"}
SOFFICE = shutil.which("soffice") or shutil.which("libreoffice")


def _samples():
    if not glob.glob(os.path.join(SAMPLES, "Sample_Publication_*.xlsx")):
        from samples.generate_samples import main
        main()


def _recalc(path):
    tmp = tempfile.mkdtemp()
    subprocess.run([SOFFICE, "--headless", "--calc", "--convert-to", "xlsx:Calc MS Excel 2007 XML", "--outdir", tmp,
                    path], capture_output=True, timeout=300)
    out = os.path.join(tmp, os.path.basename(path))
    return out if os.path.exists(out) else None


class TestBasics(unittest.TestCase):
    def test_amounts_and_years(self):
        self.assertEqual(parse_amount("1,23,456.50"), 123456.5)
        self.assertEqual(parse_amount("(12,345)"), -12345)
        self.assertEqual(detect_years("FOR THE YEAR ENDED 31ST MARCH 2026"), [2026])
        self.assertEqual(xround(2.5), 3)
        self.assertEqual(xround(-2.5), -3)

    def test_mapping_sample_labels(self):
        for st, label, head, sec, _ in TRADING_LINES + KALINGA_LINES:
            if head in ("capital", "drawings"):
                continue
            self.assertEqual(map_label(label, st, {})[0], head, label)

    def test_mapping_tform_specials(self):
        self.assertEqual(map_label("Opening Capital", "BS", {})[0], "ignore")
        self.assertEqual(map_label("(As certified by proprietor)", "PL", {})[0], "ignore")
        self.assertEqual(map_label("Cash at Bank", "BS", {})[0], "bank_balance")
        self.assertEqual(map_label("Security Dep. - Telephone Authority", "BS", {})[0], "loans_advances")


class TestReading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _samples()

    def _read(self, files, years, company=False):
        lines = read_files(files, {}, use_ai=False, log=lambda m: None)
        p = CMAProject()
        p.source_lines = lines
        p.years = [YearDef(y) for y in years]
        if company:
            p.intake.constitution = "Private Limited Company"
        p.build_lines_from_sources(SINGLE_HEADS)
        r = compute(p)
        bad = [c for c in validate(p, r) if c[0] != "OK"]
        self.assertEqual(bad, [], files)
        return p, r

    def test_tform_excel_own_layout(self):
        p, r = self._read(sorted(glob.glob(os.path.join(SAMPLES, "Sample_Publication_*.xlsx"))), [2024, 2025, 2026])
        cap = [ln for ln in p.lines if ln.head == "capital"][0]
        self.assertEqual(cap.v(2026), 2669520)
        self.assertEqual(sum(ln.v(2024) for ln in p.lines if ln.head == "drawings"), 280000)

    def test_schedule3_excel(self):
        self._read([os.path.join(SAMPLES, "Sample_Company_Statements.xlsx")], [2025, 2026], True)

    def test_pdf(self):
        self._read([os.path.join(SAMPLES, "Sample_Company_Statements.pdf")], [2025, 2026], True)


class TestTermLoan(unittest.TestCase):
    def test_methods_clear(self):
        import datetime as dt
        for method in ("Equal EMI", "Equal Principal"):
            for mor in (0, 6):
                s = tle.build_schedule(1000000, 0.105, 60, mor, method, dt.date(2026, 12, 1))
                self.assertEqual(tle.total_principal(s), 1000000)
                self.assertEqual(s["rows"][59]["sel_close"], 0)

    def test_existing_loan_schedule(self):
        ln = ExistingLoan(line_id="x", emi=90000, rate=0.095, end_date="2031-03-31")
        sch = existing_loan_schedule(ln, 3800000, [2027, 2028, 2029, 2030, 2031])
        self.assertLessEqual(sum(v[0] for v in sch.values()), 3800000)
        self.assertGreater(sch[2027][1], sch[2030][1])


class TestEngine(unittest.TestCase):
    def test_samples(self):
        for p in (sample_trading(), sample_company()):
            r = compute(p)
            self.assertFalse(has_errors(validate(p, r)))
            prev = None
            for y in r.years:
                self.assertLess(abs(y["difference"]), 1)
                if prev and not y["from_statement"]:
                    self.assertEqual(y["opening_stock"], prev["closing_stock"])
                    self.assertAlmostEqual(y["gp_pct"], prev["gp_pct"], delta=0.0005)
                prev = y
            self.assertTrue(r.summary["tl_principal_check"])

    def test_dscr_switch(self):
        p = sample_trading()
        r1 = compute(p)
        p.intake.dscr_deduct_drawings = True
        r2 = compute(p)
        for a, b in zip(r1.future, r2.future):
            self.assertGreater(a["dscr"], b["dscr"])
            self.assertAlmostEqual(a["dscr_net"], b["dscr"])

    def test_dp_solve_and_cap(self):
        for p in (sample_company(), sample_trading()):
            r = compute(p)
            for y in r.future:
                self.assertEqual(y["dp_status"], "PASS", y["label"])
        r = compute(sample_trading())
        self.assertTrue(any("stock holding raised" in w for w in r.warnings))
        p = sample_company()
        p.intake.cc_limit = 30000000
        p.intake.auto_raise_stock = False
        r = compute(p)
        self.assertTrue(any("capped at 90" in w for w in r.warnings))

    def test_unbalanced_blocks(self):
        p = sample_trading()
        p.lines[[ln.head for ln in p.lines].index("debtors")].values["2025"] += 1000
        self.assertTrue(has_errors(validate(p, compute(p))))

    def test_tl_suggestion(self):
        self.assertGreater(suggest_tl_amount(sample_company()), 0)

    def test_roundtrip(self):
        p = sample_company()
        f = os.path.join(OUT, "rt.cma.json")
        p.save(f)
        q = CMAProject.load(f)
        self.assertEqual([y["bank_balance"] for y in compute(p).years], [y["bank_balance"] for y in compute(q).years])
        os.remove(f)


class TestWorkbook(unittest.TestCase):
    def test_generate_recalc_compare_pdf(self):
        from workbook_compare import compare
        for name, p in (("trading", sample_trading()), ("company", sample_company())):
            r = compute(p)
            path = os.path.join(OUT, "CMA data - sample %s.xlsx" % name)
            generate_workbook(p, r, path, FIRM)
            self.assertTrue(os.path.exists(path))
            if not SOFFICE:
                continue
            rc = _recalc(path)
            self.assertIsNotNone(rc)
            self.assertEqual(compare(rc, p, r), [])
            import openpyxl
            ck = openpyxl.load_workbook(rc, data_only=True)["CHECK"]
            for col in "CDEFGHIJ"[:len(r.years)]:
                for row in (7, 11, 23):
                    self.assertEqual(ck["%s%d" % (col, row)].value, "Yes", "CHECK %s%d" % (col, row))
            from reports.pdf_export import export_pdf
            shutil.copyfile(rc, path)
            pdf, rep = export_pdf(path, log=lambda m: None)
            self.assertTrue(rep["a4"])
            self.assertEqual(rep["problems"], [])

    def test_master_update(self):
        from reports.master_template import prepare_master, FORMAT_SHEETS
        p = sample_trading()
        src = os.path.join(OUT, "tmp_master_src.xlsx")
        generate_workbook(p, compute(p), src, FIRM)
        dst = os.path.join(OUT, "tmp_master.xlsx")
        prepare_master(src, dst)
        import openpyxl
        wb = openpyxl.load_workbook(dst)
        for s in FORMAT_SHEETS:
            self.assertIn(s, wb.sheetnames)
        self.assertNotIn("Profit and Loss", wb.sheetnames)
        os.remove(src)
        os.remove(dst)


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestTwoBlockSheet(unittest.TestCase):
    """Two years one under the other in one sheet, with stray working dates in side columns."""
    def test_blocks(self):
        import openpyxl, tempfile, os
        from extraction.reader import read_files
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = "BS"
        for base, yr, intro, np_, drw, close in ((1, 2025, ("Introduced", 300000), 50000, 20000, 330000),
                                               (40, 2026, ("Opening balance", 330000), 60000, 30000, 360000)):
            ws.cell(base + 4, 2, "BALANCE SHEET AS ON 31ST MARCH %d" % yr)
            for c, v in ((2, "LIABILITIES"), (3, "[ RS.]"), (4, "[ RS.]"), (6, "ASSETS"), (8, "[ RS.]"), (9, "[ RS.]")):
                ws.cell(base + 6, c, v)
            ws.cell(base + 8, 2, intro[0]); ws.cell(base + 8, 3, intro[1])
            ws.cell(base + 9, 2, "Add: Net Profit"); ws.cell(base + 9, 3, np_)
            ws.cell(base + 10, 3, intro[1] + np_)
            ws.cell(base + 11, 2, "Less: Drawings"); ws.cell(base + 11, 3, drw)
            ws.cell(base + 12, 4, close)
            ws.cell(base + 8, 6, "Stock"); ws.cell(base + 8, 9, close)
        ws["L9"] = "31.03.2016"; ws["M9"] = "31.03.2017"; ws["K10"] = "31.03.2018"; ws["L10"] = 1234
        d = tempfile.mkdtemp(); f = os.path.join(d, "two.xlsx"); wb.save(f)
        lines = read_files([f], {}, use_ai=False, log=lambda *a: None)
        self.assertEqual(sorted({l.year for l in lines}), [2025, 2026])
        caps = {l.year: l.amount for l in lines if l.head == "capital"}
        self.assertEqual(caps, {2025: 330000, 2026: 360000})


class TestQuick(unittest.TestCase):
    def test_plan_years(self):
        import datetime as dt
        from core.quick import plan_years
        ys = plan_years([2025, 2026], {2026}, 2, dt.date(2026, 11, 27))
        self.assertEqual([(y.fy, y.kind) for y in ys], [(2025, "Actual"), (2026, "Provisional"),
                                                         (2027, "Estimated"), (2028, "Projected"), (2029, "Projected")])


class TestStylesValid(unittest.TestCase):
    def test_no_duplicate_numfmt_ids(self):
        """Excel 'repairs' (removes) styles.xml when one numFmtId has two format codes."""
        import zipfile, re, collections, tempfile
        from core.sample_data import sample_trading
        from analysis.engine import compute
        from reports.cma_writer import generate_workbook
        p = sample_trading(); r = compute(p)
        f = os.path.join(tempfile.mkdtemp(), "t.xlsx")
        generate_workbook(p, r, f, {}, [])
        s = zipfile.ZipFile(f).read("xl/styles.xml").decode()
        d = collections.defaultdict(set)
        for i, code in re.findall(r'<numFmt numFmtId="(\d+)" formatCode="([^"]*)"', s):
            d[i].add(code)
        self.assertEqual({k: v for k, v in d.items() if len(v) > 1}, {})


class TestNoEmptyTextCells(unittest.TestCase):
    def test_no_empty_strings(self):
        """An empty text cell makes Excel say the file is damaged."""
        import zipfile, re, tempfile
        from core.sample_data import sample_trading
        from analysis.engine import compute
        from reports.cma_writer import generate_workbook
        p = sample_trading(); p.intake.address = ""; r = compute(p)
        f = os.path.join(tempfile.mkdtemp(), "t.xlsx")
        generate_workbook(p, r, f, {}, [])
        z = zipfile.ZipFile(f)
        for n in z.namelist():
            if n.startswith("xl/worksheets/sheet"):
                t = z.read(n).decode()
                self.assertFalse(re.search(r't="(inlineStr|s|str)"\s*/>|t="(inlineStr|s|str)"></c>', t), n)


class TestExcelRules(unittest.TestCase):
    def test_no_cross_sheet_conditional_formats(self):
        """Excel treats a conditional format that refers to another sheet as damaged content."""
        import zipfile, re, html, tempfile
        from core.sample_data import sample_trading
        from analysis.engine import compute
        from reports.cma_writer import generate_workbook
        p = sample_trading(); r = compute(p)
        f = os.path.join(tempfile.mkdtemp(), "t.xlsx")
        generate_workbook(p, r, f, {}, [])
        z = zipfile.ZipFile(f)
        for n in z.namelist():
            if n.startswith("xl/worksheets/sheet"):
                for fm in re.findall(r"<cfRule[^>]*>.*?<formula>(.*?)</formula>", z.read(n).decode(), re.S):
                    self.assertNotIn("!", html.unescape(fm), n)


class TestFontNames(unittest.TestCase):
    def test_font_names_valid(self):
        """Excel drops all formatting when a font name is longer than 31 characters or is a format code."""
        import zipfile, re, tempfile
        from core.sample_data import sample_trading
        from analysis.engine import compute
        from reports.cma_writer import generate_workbook
        p = sample_trading(); r = compute(p)
        f = os.path.join(tempfile.mkdtemp(), "t.xlsx")
        generate_workbook(p, r, f, {}, [])
        s = zipfile.ZipFile(f).read("xl/styles.xml").decode()
        for name in re.findall(r'<name val="([^"]*)"', s):
            self.assertTrue(len(name) <= 31 and re.match(r"^[A-Za-z][A-Za-z0-9 \-]*$", name), name)


class TestDscrFit(unittest.TestCase):
    def test_fit_keeps_band_and_actuals(self):
        from core.sample_data import sample_trading
        from analysis.engine import compute, fit_dscr
        p = sample_trading()
        before = {ln.id: dict(ln.values) for ln in p.lines}
        fit_dscr(p, log=lambda *a: None)
        r = compute(p)
        for y in r.future:
            if y.get("dscr") is not None and y["bank_balance"] >= 0:
                self.assertTrue(1.5 - 0.01 <= y["dscr"] <= 2.5 + 0.01, (y["label"], y["dscr"]))
        self.assertEqual(before, {ln.id: dict(ln.values) for ln in p.lines})   # statement figures untouched


class TestCashRule(unittest.TestCase):
    def test_cash_never_negative_and_dp_holds(self):
        from core.sample_data import sample_trading
        from analysis.engine import compute, fit_dscr
        p = sample_trading()
        fit_dscr(p, log=lambda *a: None)
        r = compute(p)
        for y in r.future:
            self.assertGreater(y["bank_balance"], 0, y["label"])
            if y.get("cc_limit"):
                self.assertGreaterEqual(y["drawing_power"], y["cc_limit"], y["label"])


class TestTurnoverFit(unittest.TestCase):
    def test_turnover_green(self):
        from core.sample_data import sample_trading
        from analysis.engine import compute, fit_turnover
        p = sample_trading()
        p.intake.cc_limit = p.intake.cc_limit * 2
        fit_turnover(p, log=lambda *a: None)
        for y in compute(p).future:
            self.assertGreaterEqual(y["turnover_multiple"], 5.0, y["label"])


class TestAllRules(unittest.TestCase):
    def test_every_rule_green(self):
        from core.sample_data import sample_trading
        from core import quick
        from analysis.engine import compute
        p = sample_trading()
        quick.fit(p, log=lambda *a: None)
        for y in compute(p).future:
            tnw = y["owners"]
            tol = y["total_liabilities"] - tnw
            self.assertGreater(y["bank_balance"], 0, y["label"])
            self.assertGreaterEqual(y["current_ratio"], 1.33, y["label"])
            self.assertLessEqual(tol / tnw, 3.0, y["label"])
            if y.get("cc_limit"):
                self.assertGreater(y["drawing_power"], y["cc_limit"], y["label"])
                self.assertGreaterEqual(y["turnover_multiple"], 5.0, y["label"])
            if y.get("dscr") is not None:
                self.assertTrue(1.49 <= y["dscr"] <= 2.51, (y["label"], y["dscr"]))
