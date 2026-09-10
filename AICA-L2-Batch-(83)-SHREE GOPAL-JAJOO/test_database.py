"""
test_database.py
----------------
Unit tests for database.py module to ensure data persistence, search,
and exact reconstruction of AnalysisResult and ClausePoint objects.
"""

import os
import tempfile
import unittest

from models import AnalysisResult, ClausePoint
import database
import lc_parser
import rules_engine
import pdf_extract

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


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_lc.db")
        database.init_db(self.db_path)

        self.clause1 = ClausePoint(
            sl_no=1,
            point_no="20",
            header="Documentary Credit Number",
            summary="ILCBOM2026001234",
            raw_text="20 : Documentary Credit Number\nILCBOM2026001234",
            section="Main Summary",
            suggested_verdict="Correct / In Order",
            analysis_note="Documentary credit number is present.",
            user_verdict="Correct / In Order",
            user_remarks="Verified with buyer contract.",
        )
        self.clause2 = ClausePoint(
            sl_no=2,
            point_no="32B",
            header="Currency Code, Amount",
            summary="USD 250,000.00",
            raw_text="32B : Currency Code, Amount\nUSD 250000,00",
            section="Main Summary",
            suggested_verdict="Correct / In Order",
            analysis_note="Amount in USD.",
            user_verdict="Requires Amendment",
            user_remarks="Change amount to USD 300,000 as per revised order.",
        )
        self.clause3 = ClausePoint(
            sl_no=3,
            point_no="52A",
            header="Issuing Bank",
            summary="STATE BANK OF INDIA, MUMBAI",
            raw_text="52A : Issuing Bank\nSTATE BANK OF INDIA, MUMBAI MAIN BRANCH",
            section="Main Summary",
            suggested_verdict="Correct / In Order",
            analysis_note="Issuing bank specified.",
            user_verdict="Correct / In Order",
            user_remarks="",
        )
        self.clause4 = ClausePoint(
            sl_no=4,
            point_no="59",
            header="Beneficiary",
            summary="XYZ EXPORTS PTE LTD, SINGAPORE",
            raw_text="59 : Beneficiary\nXYZ EXPORTS PTE LTD\n45 ROBINSON ROAD, SINGAPORE",
            section="Main Summary",
            suggested_verdict="Correct / In Order",
            analysis_note="Beneficiary name matches.",
            user_verdict="Correct / In Order",
            user_remarks="",
        )

        self.sample_result = AnalysisResult(
            lc_type="Issued / Transmitted LC",
            dc_number="ILCBOM2026001234",
            source_filename="sample_lc.pdf",
            full_text="Sample LC Full Text Content...",
            clauses=[self.clause1, self.clause2, self.clause3, self.clause4],
        )

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_save_and_retrieve(self):
        rec_id = database.save_or_update_analysis(self.sample_result, db_path=self.db_path)
        self.assertIsInstance(rec_id, int)
        self.assertGreater(rec_id, 0)

        retrieved = database.get_analysis_by_id(rec_id, db_path=self.db_path)
        self.assertIsNotNone(retrieved)
        res, meta = retrieved

        self.assertEqual(res.dc_number, "ILCBOM2026001234")
        self.assertEqual(res.lc_type, "Issued / Transmitted LC")
        self.assertEqual(res.source_filename, "sample_lc.pdf")
        self.assertEqual(len(res.clauses), 4)

        # Check clause verdicts and remarks preservation
        c2 = res.clauses[1]
        self.assertEqual(c2.point_no, "32B")
        self.assertEqual(c2.user_verdict, "Requires Amendment")
        self.assertEqual(c2.user_remarks, "Change amount to USD 300,000 as per revised order.")
        self.assertEqual(c2.effective_verdict(), "Requires Amendment")

        # Check metadata
        self.assertIn("STATE BANK OF INDIA", meta["issuer_name"])
        self.assertIn("XYZ EXPORTS", meta["beneficiary_name"])
        self.assertEqual(meta["currency"], "USD")
        self.assertEqual(meta["amount_num"], 250000.0)

    def test_search_by_fields(self):
        database.save_or_update_analysis(self.sample_result, db_path=self.db_path)

        # 1. Search by LC No
        results_lc = database.search_analyses(lc_no="ILCBOM", db_path=self.db_path)
        self.assertEqual(len(results_lc), 1)
        self.assertEqual(results_lc[0]["dc_number"], "ILCBOM2026001234")

        # 2. Search by Issuer
        results_issuer = database.search_analyses(issuer="STATE BANK", db_path=self.db_path)
        self.assertEqual(len(results_issuer), 1)

        # 3. Search by Amount
        results_amt = database.search_analyses(amount="250000", db_path=self.db_path)
        self.assertEqual(len(results_amt), 1)

        # 4. Search by Beneficiary
        results_ben = database.search_analyses(beneficiary="XYZ EXPORTS", db_path=self.db_path)
        self.assertEqual(len(results_ben), 1)

        # 5. Search with no matches
        results_none = database.search_analyses(lc_no="NONEXISTENT", db_path=self.db_path)
        self.assertEqual(len(results_none), 0)

    def test_real_pipeline_save_and_search(self):
        # Test full end-to-end pipeline analysis result saved to DB
        text = pdf_extract.normalise_text(SAMPLE_LC_TEXT)
        fields = lc_parser.extract_fields(text)
        clauses = rules_engine.build_clause_points(fields, "issued")
        real_result = AnalysisResult(
            lc_type="Issued / Transmitted LC",
            dc_number="ILCBOM2026001234",
            source_filename="real_sample.pdf",
            full_text=text,
            clauses=clauses,
        )

        rec_id = database.save_or_update_analysis(real_result, db_path=self.db_path)
        self.assertGreater(rec_id, 0)

        # Search by Beneficiary
        res = database.search_analyses(beneficiary="XYZ EXPORTS", db_path=self.db_path)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["id"], rec_id)

        # Search by Issuer
        res_iss = database.search_analyses(issuer="STANDARD CHARTERED", db_path=self.db_path)
        self.assertEqual(len(res_iss), 1)

        # Search by Amount
        res_amt = database.search_analyses(amount="250000", db_path=self.db_path)
        self.assertEqual(len(res_amt), 1)

        # Load back
        loaded_res, meta = database.get_analysis_by_id(rec_id, db_path=self.db_path)
        self.assertEqual(len(loaded_res.clauses), len(clauses))
        self.assertEqual(loaded_res.dc_number, "ILCBOM2026001234")

    def test_update_existing_record(self):
        rec_id = database.save_or_update_analysis(self.sample_result, db_path=self.db_path)

        # Modify remark and re-save with rec_id
        self.sample_result.clauses[0].user_remarks = "Updated remark after second check"
        updated_id = database.save_or_update_analysis(self.sample_result, record_id=rec_id, db_path=self.db_path)
        self.assertEqual(updated_id, rec_id)

        res, meta = database.get_analysis_by_id(rec_id, db_path=self.db_path)
        self.assertEqual(res.clauses[0].user_remarks, "Updated remark after second check")

    def test_delete_record(self):
        rec_id = database.save_or_update_analysis(self.sample_result, db_path=self.db_path)
        self.assertTrue(database.delete_analysis(rec_id, db_path=self.db_path))

        retrieved = database.get_analysis_by_id(rec_id, db_path=self.db_path)
        self.assertIsNone(retrieved)


if __name__ == "__main__":
    unittest.main()
