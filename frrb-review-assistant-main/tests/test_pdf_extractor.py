"""Unit tests for PDF Extractor and Section Identification Engine."""

import os
import unittest
from core.pdf_extractor import PDFExtractor


class TestPDFExtractor(unittest.TestCase):

    def setUp(self):
        self.pdf_a_path = os.path.join("sample_data", "Sample_Draft_FS_Option_A_With_Errors.pdf")
        self.pdf_b_path = os.path.join("sample_data", "Sample_Annual_Report_Option_B_RedFlags.pdf")
        self.pdf_clean_path = os.path.join("sample_data", "Sample_Compliant_FS_Negative_Test.pdf")

    def test_extract_valid_pdf_a(self):
        with open(self.pdf_a_path, "rb") as f:
            pdf_bytes = f.read()
        res = PDFExtractor.extract_from_bytes(pdf_bytes, filename="Option_A.pdf")
        self.assertTrue(res["success"])
        self.assertFalse(res["is_scanned"])
        self.assertEqual(res["total_pages"], 3)
        self.assertGreater(res["avg_chars_per_page"], 100)
        self.assertTrue(res["sections"]["balance_sheet"]["detected"])
        self.assertTrue(res["sections"]["profit_and_loss"]["detected"])
        self.assertTrue(res["sections"]["notes_to_accounts"]["detected"])

    def test_extract_valid_pdf_b_with_auditor_report(self):
        with open(self.pdf_b_path, "rb") as f:
            pdf_bytes = f.read()
        res = PDFExtractor.extract_from_bytes(pdf_bytes, filename="Option_B.pdf")
        self.assertTrue(res["success"])
        self.assertTrue(res["sections"]["auditor_report"]["detected"])
        self.assertTrue(res["sections"]["caro_report"]["detected"])

    def test_extract_valid_excel_workbook(self):
        excel_path = os.path.join("sample_data", "Sample_Draft_FS_Option_A.xlsx")
        with open(excel_path, "rb") as f:
            excel_bytes = f.read()
        res = PDFExtractor.extract_from_bytes(excel_bytes, filename="Sample_Draft_FS_Option_A.xlsx")
        self.assertTrue(res["success"])
        self.assertFalse(res["is_scanned"])
        self.assertEqual(res["total_pages"], 3)
        self.assertTrue(res["sections"]["balance_sheet"]["detected"])
        self.assertTrue(res["sections"]["profit_and_loss"]["detected"])
        self.assertTrue(res["sections"]["notes_to_accounts"]["detected"])

    def test_scanned_pdf_detection(self):
        # A 1-page PDF with empty text or minimal characters simulates a scanned PDF
        import fitz
        doc = fitz.open()
        doc.new_page()  # blank page
        pdf_bytes = doc.tobytes()
        res = PDFExtractor.extract_from_bytes(pdf_bytes, filename="scanned.pdf")
        self.assertFalse(res["success"])
        self.assertTrue(res["is_scanned"])
        self.assertIn("Scanned / Image-Only PDF Detected", res["error"])


if __name__ == "__main__":
    unittest.main()
