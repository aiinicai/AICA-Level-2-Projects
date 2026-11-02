"""Integration tests for Compliance Review Rules Engine and Negative Test Cases."""

import os
import unittest
from core.pdf_extractor import PDFExtractor
from core.rules_engine import ComplianceEngine


class TestComplianceEngine(unittest.TestCase):

    def setUp(self):
        self.profile_ind_as = {
            "company_type": "Public Company",
            "listing_status": "Listed",
            "framework": "Indian Accounting Standards (Ind AS)",
            "schedule_iii_division": "Division II",
            "financial_year": "FY 2023-24",
            "statement_type": "Standalone",
        }

    def test_option_a_draft_fs_with_errors(self):
        """Option A must detect arithmetic imbalance, missing Schedule III notes & standard violations."""
        pdf_path = os.path.join("sample_data", "Sample_Draft_FS_Option_A_With_Errors.pdf")
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        doc = PDFExtractor.extract_from_bytes(pdf_bytes)

        review = ComplianceEngine.run_review(doc, self.profile_ind_as, review_mode="Option A")

        self.assertEqual(review["review_mode"], "Option A")
        self.assertGreater(review["total_issues"], 0)
        self.assertGreater(review["high_risk_count"], 0)

        # 1. Verify Arithmetic Check
        arith_issues = [i for i in review["issues"] if "Balance Sheet Integrity" in i.get("category", "")]
        self.assertTrue(len(arith_issues) > 0, "Arithmetic imbalance was not detected!")
        self.assertIn("10,810", arith_issues[0]["current_disclosure"])

        # 2. Verify Ind AS 16 PPE Subsequent Cost Policy check
        ppe_issues = [i for i in review["issues"] if "PPE" in i.get("category", "") or "standard of performance" in i.get("description", "").lower()]
        self.assertTrue(len(ppe_issues) > 0, "Ind AS 16 PPE standard of performance defect was not detected!")
        self.assertIn("Ind AS 16", ppe_issues[0]["statutory_ref"])

        # 3. Verify Trade Payables Schedule III Ageing & MSME checks
        tp_issues = [i for i in review["issues"] if "Trade Payables" in i.get("ref", "") or "Trade Payables" in i.get("description", "")]
        self.assertTrue(len(tp_issues) >= 1, "Schedule III Trade Payables check was not triggered!")

        # 4. Verify Ratio Variance Explanation check
        ratio_issues = [i for i in review["issues"] if "Ratios" in i.get("category", "")]
        self.assertTrue(len(ratio_issues) > 0, "Schedule III Ratio variance check was not triggered!")

        # 5. Verify Promoter Shareholding check
        promoter_issues = [i for i in review["issues"] if "Share Capital" in i.get("category", "")]
        self.assertTrue(len(promoter_issues) > 0, "Promoter shareholding check was not triggered!")

    def test_option_b_annual_report_with_red_flags(self):
        """Option B must identify qualified audit opinions, CARO 2020 remarks, and red flags."""
        pdf_path = os.path.join("sample_data", "Sample_Annual_Report_Option_B_RedFlags.pdf")
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        doc = PDFExtractor.extract_from_bytes(pdf_bytes)

        review = ComplianceEngine.run_review(doc, self.profile_ind_as, review_mode="Option B")

        self.assertEqual(review["review_mode"], "Option B")
        self.assertGreater(review["total_issues"], 0)

        # 1. Verify Auditor Qualified Opinion detection
        audit_issues = [i for i in review["issues"] if "Auditor's Report Review" in i.get("category", "")]
        self.assertTrue(len(audit_issues) > 0, "Modified audit opinion was not detected!")
        self.assertEqual(audit_issues[0]["risk"], "High")

        # 2. Verify CARO Clause 3(ii)(b) quarterly bank statement variance detection
        caro_issues = [i for i in review["issues"] if "CARO 2020" in i.get("category", "")]
        self.assertTrue(len(caro_issues) > 0, "CARO 2020 Clause 3(ii)(b) quarterly variance was not detected!")
        self.assertIn("3(ii)(b)", caro_issues[0]["statutory_ref"])

    def test_as_framework_rules_and_division_i(self):
        """Accounting Standards (AS) and Division I must execute in-depth checks with strict parity."""
        excel_path = os.path.join("sample_data", "Sample_Draft_FS_Option_A.xlsx")
        with open(excel_path, "rb") as f:
            file_bytes = f.read()
        doc = PDFExtractor.extract_from_bytes(file_bytes, filename=os.path.basename(excel_path))

        profile_as = {
            "company_type": "Private Company",
            "listing_status": "Unlisted",
            "framework": "Accounting Standards (AS)",
            "schedule_iii_division": "Division I",
            "financial_year": "FY 2025-26",
            "statement_type": "Standalone",
        }

        review = ComplianceEngine.run_review(doc, profile_as, review_mode="Option A")
        self.assertGreaterEqual(review["total_issues"], 15, "AS framework did not run full depth checks!")
        
        # Verify AS standard references exist in findings
        as_refs = [i for i in review["issues"] if "AS " in i.get("statutory_ref", "") or "Division I" in i.get("statutory_ref", "")]
        self.assertGreater(len(as_refs), 0, "No AS or Division I statutory references found!")

    def test_negative_compliant_fs_no_false_positives(self):
        """Negative Test Case: Compliant financial statements must not trigger false positive errors."""
        pdf_path = os.path.join("sample_data", "Sample_Compliant_FS_Negative_Test.pdf")
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        doc = PDFExtractor.extract_from_bytes(pdf_bytes)

        review = ComplianceEngine.run_review(doc, self.profile_ind_as, review_mode="Option A")

        # Arithmetic check must NOT fail
        arith_issues = [i for i in review["issues"] if "Arithmetic & Balance Sheet Integrity" in i.get("category", "")]
        self.assertEqual(len(arith_issues), 0, "Compliant statements falsely triggered arithmetic error!")

        # Trade Payables ageing must NOT fail
        tp_missing = [i for i in review["issues"] if "Mandatory Trade Payables Ageing Schedule is missing" in i.get("description", "")]
        self.assertEqual(len(tp_missing), 0, "Compliant statements falsely triggered Trade Payables missing ageing!")

        # Promoter Shareholding must NOT fail
        prom_missing = [i for i in review["issues"] if "Promoter Shareholding and % Change" in i.get("description", "")]
        self.assertEqual(len(prom_missing), 0, "Compliant statements falsely triggered Promoter Shareholding missing!")


if __name__ == "__main__":
    unittest.main()
