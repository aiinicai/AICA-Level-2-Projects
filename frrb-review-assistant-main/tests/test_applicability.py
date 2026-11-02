"""Unit tests for Applicability Assessment Engine using standard unittest."""

import unittest
from core.applicability import ApplicabilityEngine


class TestApplicabilityEngine(unittest.TestCase):

    def test_listed_company_mandatory_ind_as(self):
        """Listed company with AS must fail validation."""
        result = ApplicabilityEngine.validate_profile(
            company_type="Public Company",
            listing_status="Listed",
            framework="Accounting Standards (AS)",
            schedule_iii_division="Division I",
            financial_year="FY 2023-24",
            statement_type="Standalone"
        )
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("Statutory Violation" in err for err in result["errors"]))
        self.assertEqual(result["recommendations"]["framework"], ApplicabilityEngine.FRAMEWORK_IND_AS)

    def test_listed_company_valid_ind_as(self):
        """Listed company with Ind AS Division II must be valid."""
        result = ApplicabilityEngine.validate_profile(
            company_type="Public Company",
            listing_status="Listed",
            framework="Indian Accounting Standards (Ind AS)",
            schedule_iii_division="Division II",
            financial_year="FY 2023-24",
            statement_type="Standalone"
        )
        self.assertTrue(result["is_valid"])
        self.assertEqual(len(result["errors"]), 0)

    def test_unlisted_company_net_worth_threshold_breach(self):
        """Unlisted company with Net Worth >= 250 Cr must not use AS."""
        result = ApplicabilityEngine.validate_profile(
            company_type="Private Company",
            listing_status="Unlisted",
            framework="Accounting Standards (AS)",
            schedule_iii_division="Division I",
            financial_year="FY 2023-24",
            statement_type="Standalone",
            net_worth_crores=300.0
        )
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("Threshold Breach" in err for err in result["errors"]))

    def test_unlisted_company_net_worth_clarification(self):
        """Unlisted company without net worth specified prompts for clarification."""
        result = ApplicabilityEngine.validate_profile(
            company_type="Private Company",
            listing_status="Unlisted",
            framework="Accounting Standards (AS)",
            schedule_iii_division="Division I",
            financial_year="FY 2023-24",
            statement_type="Standalone",
            net_worth_crores=None
        )
        self.assertTrue(result["is_valid"])
        self.assertGreater(len(result["clarifications_needed"]), 0)
        self.assertTrue(any("Net Worth Threshold Clarification" in c for c in result["clarifications_needed"]))

    def test_nbfc_division_mismatch(self):
        """NBFC selecting Division II must be flagged to use Division III."""
        result = ApplicabilityEngine.validate_profile(
            company_type="Public Company",
            listing_status="Listed",
            framework="Indian Accounting Standards (Ind AS)",
            schedule_iii_division="Division II",
            financial_year="FY 2023-24",
            statement_type="Standalone",
            is_nbfc=True
        )
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("NBFC Entity Mismatch" in err for err in result["errors"]))
        self.assertEqual(result["recommendations"]["schedule_iii_division"], "Division III")


if __name__ == "__main__":
    unittest.main()
