"""Run: python -m unittest discover -s tests -v   (synthetic names only)"""
import io, sys, unittest, os
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules import redaction as R, narrative_ai as N
from modules.data_ingestion import LINE_ITEMS

ENTITY = "Zephyr Quantum Industries Private Limited"
PERSONS = ["Mr. Anand Velupillai", "Mrs. Meera Chandrasekhar"]
ORGS = ["Krishnan & Partners"]
ADDR = ["12/34 Lotus Road, Calicut"]

SAMPLE = """Zephyr Quantum Industries Private Limited
CIN: U12345KL2010PTC012345  PAN AABCZ1234F  GSTIN 32AABCZ1234F1Z5
Regd. Office: 12/34 Lotus Road, Calicut - 673 001. Tel: +91 495 2345678
Email: accounts@zephyrquantum.com  www.zephyrquantum.com
Anand Velupillai
Managing Director
DIN: 01234567
For Krishnan & Partners, Chartered Accountants
Firm Regn No. 004321S  Membership No. 212345  UDIN: 24212345ABCDEF1234
Total assets 1,234.50 and revenue 9,876.54 (Rs. in million)"""


def red():
    return R.Redactor(ENTITY, PERSONS, ORGS, ADDR)


class Core(unittest.TestCase):
    def test_all_sensitive_removed(self):
        out = red().redact(SAMPLE).text
        for bad in ["Zephyr", "Quantum", "Velupillai", "Meera", "Krishnan", "Lotus",
                    "U12345KL2010PTC012345", "AABCZ1234F", "32AABCZ1234F1Z5",
                    "01234567", "212345", "004321S", "ABCDEF1234", "zephyrquantum",
                    "2345678", "673 001"]:
            self.assertNotIn(bad, out, bad)

    def test_figures_untouched(self):
        out = red().redact(SAMPLE).text
        self.assertIn("1,234.50", out)
        self.assertIn("9,876.54", out)

    def test_restore_roundtrip(self):
        r = red()
        t = r.redact(SAMPLE).text
        self.assertIn("Zephyr Quantum Industries Private Limited", r.restore(t))
        self.assertIn("Mr. Anand Velupillai", r.restore("[PERSON_1] is the MD"))

    def test_guard(self):
        r = red()
        with self.assertRaises(R.RedactionError):
            r.assert_clean("Results of Zephyr for FY26")
        r.assert_clean(r.redact(SAMPLE).text)

    def test_deterministic(self):
        self.assertEqual(red().redact(SAMPLE).text, red().redact(SAMPLE).text)

    def test_generic_words_not_masked(self):
        t = red().redact("Private limited companies in India hold Industries data").text
        self.assertIn("Industries", t)

    def test_page_range(self):
        self.assertEqual(R.parse_page_range("3-4, 7", 10), [3, 4, 7])
        self.assertEqual(R.parse_page_range("", 3), [1, 2, 3])
        with self.assertRaises(ValueError):
            R.parse_page_range("1-99", 10)

    def test_flags(self):
        f = R.review_flags("Signed by Dr. Ramesh Iyer for Foo Bar LLP")
        self.assertTrue(any("Ramesh" in x for x in f))


def fake_client(captured, reply):
    def create(**kw):
        captured.append(kw)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=reply)])
    return SimpleNamespace(messages=SimpleNamespace(create=create))


def sample_data():
    cy = {k: 0.0 for k, *_ in LINE_ITEMS}
    cy.update(revenue=1000, material_cost=600, employee_cost=100, other_expenses=100,
              depreciation=50, finance_cost=40, share_capital=100, reserves=300,
              lt_borrowings=200, trade_payables=150, other_current_liab=50,
              fixed_assets=500, inventory=150, receivables=200, cash=150)
    py = dict(cy); py.update(revenue=900, receivables=120)
    return {"CY": cy, "PY": py, "PY2": None}


class Lines(unittest.TestCase):
    TXT = "Revenue 100.00\nDIN: 01234567\nRegistered Office:\n12 Lotus Road Calicut\nAddress of the unit\nDirector Identification Number 9\nWindinger 5\nExpenses 40.00"

    def test_line_wipe(self):
        r = R.Redactor("X Corp", line_keywords=R.DEFAULT_LINE_KEYWORDS)
        res = r.redact(self.TXT)
        self.assertEqual(res.text.split("\n"), ["Revenue 100.00", R.LINE_TOKEN, R.LINE_TOKEN,
            R.LINE_TOKEN, R.LINE_TOKEN, R.LINE_TOKEN, "Windinger 5", "Expenses 40.00"])
        self.assertTrue(any(e["kind"] == "LINE" for e in res.entries))

    def test_custom_keyword_and_guard(self):
        r = R.Redactor("X Corp", line_keywords=["Bankers"])
        out = r.redact("Bankers: ABC\nCash 5").text
        self.assertEqual(out, R.LINE_TOKEN + "\nCash 5")
        r.assert_clean(out, include_lines=True)
        with self.assertRaises(R.RedactionError):
            r.assert_clean("Bankers list", include_lines=True)

    def test_amount_rows_survive_and_signature_cut(self):
        txt = ("[Sheet: Note 18]\nTelephone expenses |  | 540 | 540\nE-Mail : a@b.com\n"
               "Total | 540\nAs per our report of even date\nFor X & Co.\nVIPIN | DIRECTOR\n8065710\n"
               "[Sheet: Next]\nRevenue | 5 | 6")
        r = R.Redactor("X Corp", line_keywords=R.DEFAULT_LINE_KEYWORDS, cut_markers=R.DEFAULT_CUT_MARKERS)
        out = r.redact(txt).text
        self.assertIn("Telephone expenses |  | 540 | 540", out)
        self.assertNotIn("a@b.com", out); self.assertNotIn("8065710", out); self.assertNotIn("VIPIN", out)
        self.assertIn("[Sheet: Next]\nRevenue | 5 | 6", out)
        r.assert_clean(out, include_lines=True)
        with self.assertRaises(R.RedactionError):
            r.assert_clean("As per our report of even date", include_lines=True)

    def test_off_by_default(self):
        self.assertEqual(R.Redactor("X Corp").redact("DIN: 1").text.count(R.LINE_TOKEN), 0)


class Workbook(unittest.TestCase):
    PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "sample_data", "sample_workbook_with_notes.xlsx")

    def setUp(self):
        if not os.path.exists(self.PATH):
            self.skipTest("sample workbook missing")
        self.b = open(self.PATH, "rb").read()

    def test_sheets_and_selection(self):
        names = [i["name"] for i in R.excel_sheet_info(self.b)]
        self.assertIn("Note 3 Other expenses", names)
        txt = R.extract_excel_text(self.b, ["Note 3 Other expenses"])
        self.assertIn("Power and fuel | 210 | 170", txt)
        self.assertNotIn("Balance Sheet", txt)

    def test_workbook_redaction(self):
        r = R.Redactor("Meridian Alloys Private Limited", ["Mr. Rohan Menon"],
                       ["Nair & Associates"], line_keywords=R.DEFAULT_LINE_KEYWORDS)
        out = r.redact(R.extract_excel_text(self.b)).text
        for bad in ["Meridian", "Menon", "Nair", "Kalamassery", "U27100", "01234567"]:
            self.assertNotIn(bad, out)
        self.assertIn("TOTAL ASSETS |  | 1600 | 1450", out)
        r.assert_clean(out, include_lines=True)

    def test_workbook_prompt_clean_and_mapped(self):
        cap = []
        r = R.Redactor("Meridian Alloys Private Limited", [], [], line_keywords=R.DEFAULT_LINE_KEYWORDS)
        txt = r.redact(R.extract_excel_text(self.b)).text
        reply = '{"unit_detected":"Rs lakhs","CY":{"revenue":3000},"PY":{"revenue":2600},"extraction_notes":[]}'
        with mock.patch.object(N, "_client", lambda k: fake_client(cap, reply)):
            data, _ = N.extract_from_text(txt, "k", redactor=r, workbook=True)
        p = cap[0]["messages"][0]["content"]
        self.assertNotIn("Meridian", p)
        self.assertIn("TRIAL BALANCE", p)
        self.assertEqual(data["CY"]["revenue"], 3000.0)

    def test_bad_file(self):
        with self.assertRaises(R.RedactionError):
            R.excel_sheet_info(b"not a workbook")


class Egress(unittest.TestCase):
    def test_lens_prompt_clean_and_restored(self):
        cap = []
        reply = '{"workpaper":[],"going_concern":[],"inquiries":["Ask about [ENTITY_1] sales"]}'
        r = red()
        with mock.patch.object(N, "_client", lambda k: fake_client(cap, reply)):
            out = N.auditors_lens(sample_data(), "k", 10, ENTITY, redactor=r)
        prompt = cap[0]["messages"][0]["content"]
        self.assertNotIn("Zephyr", prompt)
        self.assertIn("[ENTITY_1]", prompt)
        self.assertIn(ENTITY, out["inquiries"][0])

    def test_narrative_restored(self):
        cap = []
        r = red()
        with mock.patch.object(N, "_client", lambda k: fake_client(cap, "[ENTITY_1] did well.")):
            t = N.narrative(sample_data(), "k", {"score": 1}, 10, ENTITY, redactor=r)
        self.assertNotIn("Zephyr", cap[0]["messages"][0]["content"])
        self.assertTrue(t.startswith(ENTITY))

    def test_extract_text_blocks_leak_and_sends_nothing(self):
        cap = []
        with mock.patch.object(N, "_client", lambda k: fake_client(cap, "{}")):
            with self.assertRaises(R.RedactionError):
                N.extract_from_text("Zephyr balance sheet", "k", redactor=red())
        self.assertEqual(cap, [])

    def test_extract_text_ok(self):
        cap = []
        r = red()
        txt = r.redact(SAMPLE).text
        reply = '{"unit_detected":"Rs million","CY":{"revenue":9876.54},"PY":{},"extraction_notes":[]}'
        with mock.patch.object(N, "_client", lambda k: fake_client(cap, reply)):
            data, notes = N.extract_from_text(txt, "k", redactor=r)
        self.assertEqual(data["CY"]["revenue"], 9876.54)
        p = cap[0]["messages"][0]["content"]
        self.assertNotIn("Zephyr", p); self.assertNotIn("AABCZ1234F", p)


class Pdf(unittest.TestCase):
    def _pdf(self, text):
        from reportlab.pdfgen import canvas
        b = io.BytesIO(); c = canvas.Canvas(b)
        y = 800
        for line in text.splitlines():
            c.drawString(40, y, line); y -= 14
        c.save(); return b.getvalue()

    def test_pdf_text_route(self):
        try:
            data = self._pdf(SAMPLE * 3)
        except ImportError:
            self.skipTest("reportlab missing")
        self.assertEqual(R.pdf_page_count(data), 1)
        t = R.extract_pdf_text(data, [1])
        out = red().redact(t).text
        self.assertNotIn("Zephyr", out); self.assertIn("9,876.54", out)

    def test_scan_rejected(self):
        try:
            from reportlab.pdfgen import canvas
        except ImportError:
            self.skipTest("reportlab missing")
        b = io.BytesIO(); c = canvas.Canvas(b); c.rect(10, 10, 50, 50); c.save()
        with self.assertRaises(R.NoTextLayerError):
            R.extract_pdf_text(b.getvalue(), [1])


if __name__ == "__main__":
    unittest.main()
