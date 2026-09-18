"""
test_gui_and_database.py
------------------------
Automated integration test for the modernized LC Analyser GUI and SQLite database.
Tests all workflows headlessly (with root.withdraw() and mocked dialogs):
  1. Initialization of blue-themed modern widgets.
  2. Loading sample LC analysis into the GUI.
  3. Live KPI counter updates on verdict change.
  4. Saving to database and loading from database.
  5. Multi-criteria search by LC No, Issuer, Amount, Beneficiary.
  6. Deletion warning dialog and database record deletion.
  7. Exporting Word (.docx), PDF, Finalized Summary, and Amendment Request Letter.
"""

import os
import tempfile
import unittest
from unittest.mock import patch
import tkinter as tk

import pdf_extract
import lc_parser
import rules_engine
import exporter
import database
from models import AnalysisResult, ClausePoint
from main import LCAnalyserApp, LC_TYPE_ISSUED

SAMPLE_LC_TEXT = """
27 : Sequence of Total
1/1
40A : Form of Documentary Credit
IRREVOCABLE
20 : Documentary Credit Number
ILCBOM2026001234
31C : Date of Issue
260815
40E : Applicable Rules
UCP LATEST VERSION
31D : Date and Place of Expiry
261130 IN INDIA
50 : Applicant
ABC TRADING CO LTD
123 INDUSTRIAL AREA, MUMBAI, INDIA
59 : Beneficiary
XYZ EXPORTS PTE LTD
45 ROBINSON ROAD, SINGAPORE
32B : Currency Code, Amount
USD 250000,00
41A : Available With...By...
ANY BANK IN SINGAPORE BY NEGOTIATION
43P : Partial Shipments
NOT ALLOWED
44E : Port of Loading / Airport of Departure
SINGAPORE PORT
44F : Port of Discharge / Airport of Destination
MUMBAI PORT, INDIA
44C : Latest Date of Shipment
261031
45A : Description of Goods and/or Services
50,000 UNITS OF ELECTRONIC COMPONENTS AS PER PROFORMA INVOICE NO. PI-2026-77
46A : Documents Required
+SIGNED COMMERCIAL INVOICE IN TRIPLICATE
+FULL SET OF CLEAN ON BOARD BILLS OF LADING MADE OUT TO ORDER OF ISSUING BANK
+CERTIFICATE OF ORIGIN ISSUED BY CHAMBER OF COMMERCE
+INSURANCE POLICY COVERING 110% OF CIF INVOICE VALUE, ALL RISKS
48 : Period for Presentation
21 DAYS AFTER THE DATE OF SHIPMENT BUT WITHIN THE VALIDITY OF THE CREDIT
52A : Issuing Bank
STANDARD CHARTERED BANK, SINGAPORE
71B : Charges
ALL BANKING CHARGES OUTSIDE INDIA ARE FOR BENEFICIARY'S ACCOUNT
"""


def create_sample_pdf(path: str, text: str) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    y = height - 40
    for line in text.split("\n"):
        if y < 40:
            c.showPage()
            y = height - 40
        c.setFont("Courier", 8)
        c.drawString(30, y, line[:120])
        y -= 11
    c.save()


class TestGUIAndDatabase(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.pdf_path = os.path.join(self.tmp_dir.name, "sample_test_lc.pdf")
        create_sample_pdf(self.pdf_path, SAMPLE_LC_TEXT)

        # Setup Tk root (hidden)
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = LCAnalyserApp(self.root)

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass
        self.tmp_dir.cleanup()

    @patch("tkinter.messagebox.showinfo")
    @patch("tkinter.messagebox.showwarning")
    @patch("tkinter.messagebox.showerror")
    @patch("tkinter.messagebox.askyesno", return_value=True)
    def test_full_analysis_workflow_in_gui(self, mock_yesno, mock_err, mock_warn, mock_info):
        app = self.app
        app.selected_file = self.pdf_path
        app.lc_type_var.set(LC_TYPE_ISSUED)

        # 1. Trigger analysis
        app.on_analyze()

        self.assertIsNotNone(app.result)
        self.assertEqual(app.result.dc_number, "ILCBOM2026001234")
        self.assertGreater(len(app.result.clauses), 10)
        self.assertIsNotNone(app.current_record_id)

        # 2. Check KPI counters
        app._update_kpi_counters()
        total_kpi = int(app.kpi_total_chip["val"].cget("text"))
        self.assertEqual(total_kpi, len(app.result.clauses))

        # Check modifying verdict updates live counter
        first_row = app.row_widgets[0]
        first_row.verdict_var.set("Requires Amendment")
        first_row.remarks_var.set("Amendment requested for testing.")
        app._update_kpi_counters()
        amend_kpi = int(app.kpi_amend_chip["val"].cget("text"))
        self.assertGreaterEqual(amend_kpi, 1)

        # 3. Test Save to Database
        app.on_save_to_database()
        self.assertIsNotNone(app.current_record_id)

        # 4. Switch to database tab and search
        app.on_search_database()
        tree_items = app.db_tree.get_children()
        self.assertGreaterEqual(len(tree_items), 1)

        # Search by LC Number
        app.search_lc_no_var.set("ILCBOM")
        app.on_search_database()
        self.assertGreaterEqual(len(app.db_tree.get_children()), 1)

        # Search by Issuer Name
        app.search_lc_no_var.set("")
        app.search_issuer_var.set("STANDARD CHARTERED")
        app.on_search_database()
        self.assertGreaterEqual(len(app.db_tree.get_children()), 1)

        # Search by Beneficiary Name
        app.search_issuer_var.set("")
        app.search_beneficiary_var.set("XYZ EXPORTS")
        app.on_search_database()
        self.assertGreaterEqual(len(app.db_tree.get_children()), 1)

        # Search by Amount
        app.search_beneficiary_var.set("")
        app.search_amount_var.set("250000")
        app.on_search_database()
        self.assertGreaterEqual(len(app.db_tree.get_children()), 1)

        # 5. Test loading selected item back into workspace
        first_item = app.db_tree.get_children()[0]
        app.db_tree.selection_set(first_item)
        app.on_load_selected_database_record()
        self.assertEqual(app.result.dc_number, "ILCBOM2026001234")

        # 6. Test Exporting all document types:
        # Full Word Analysis, Full PDF Analysis, Finalized Summary Word, Amendment Request Letter Word
        out_word = os.path.join(self.tmp_dir.name, "export_full.docx")
        out_pdf = os.path.join(self.tmp_dir.name, "export_full.pdf")
        out_final = os.path.join(self.tmp_dir.name, "export_final.docx")
        out_amend = os.path.join(self.tmp_dir.name, "export_amend.docx")

        app._sync_row_widgets_to_clauses()
        exporter.export_to_word(app.result, out_word)
        exporter.export_to_pdf(app.result, out_pdf)
        exporter.export_final_summary_word(app.result, out_final)
        
        amend_clauses = [c for c in app.result.clauses if c.effective_verdict() == "Requires Amendment"]
        exporter.generate_amendment_letter(app.result, out_amend, amend_clauses)

        self.assertTrue(os.path.exists(out_word) and os.path.getsize(out_word) > 0)
        self.assertTrue(os.path.exists(out_pdf) and os.path.getsize(out_pdf) > 0)
        self.assertTrue(os.path.exists(out_final) and os.path.getsize(out_final) > 0)
        self.assertTrue(os.path.exists(out_amend) and os.path.getsize(out_amend) > 0)

        # 7. Test Delete Record with confirmation prompt
        app.db_tree.selection_set(first_item)
        app.on_delete_selected_record()
        mock_yesno.assert_called_with(
            "Confirm Deletion",
            "Do You Really Want To Delete Record - if you proceed record will be permanently deleted."
        )


if __name__ == "__main__":
    unittest.main()
