"""Applicability Assessment Engine for Financial Reporting Review Assistant.

Validates company profile, applicable financial reporting framework (AS vs Ind AS),
and Schedule III Division (Division I, II, or III) under the Companies Act, 2013
and relevant MCA/ICAI rules.
"""

from typing import Dict, Any, List, Optional


class ApplicabilityEngine:
    """Evaluates and validates statutory applicability for Indian corporate entities."""

    FRAMEWORK_IND_AS = "Indian Accounting Standards (Ind AS)"
    FRAMEWORK_AS = "Accounting Standards (AS)"

    DIV_I = "Division I"   # AS (Non-Ind AS)
    DIV_II = "Division II"  # Ind AS Non-NBFC
    DIV_III = "Division III" # Ind AS NBFC

    @classmethod
    def validate_profile(
        cls,
        company_type: str,
        listing_status: str,
        framework: str,
        schedule_iii_division: str,
        financial_year: str,
        statement_type: str,
        is_nbfc: bool = False,
        net_worth_crores: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Validates company profile and framework compatibility.

        Returns a dictionary with status, errors, warnings, recommendations, and applicable laws.
        """
        errors: List[str] = []
        warnings: List[str] = []
        clarifications_needed: List[str] = []
        recommendations: Dict[str, str] = {}
        applicable_laws: List[str] = [
            "Companies Act, 2013 (Section 129, Section 133, Section 134, Section 135)",
            "Schedule III to the Companies Act, 2013",
        ]

        is_listed = listing_status.strip().lower() == "listed"
        is_ind_as = "ind as" in framework.lower()
        is_as = not is_ind_as

        # 1. Division vs Framework Consistency Check
        if is_as and schedule_iii_division != cls.DIV_I:
            errors.append(
                f"Inconsistent Selection: {cls.FRAMEWORK_AS} entities must apply Schedule III {cls.DIV_I}. "
                f"Currently selected: {schedule_iii_division}."
            )
            recommendations["schedule_iii_division"] = cls.DIV_I

        if is_ind_as:
            if schedule_iii_division == cls.DIV_I:
                correct_div = cls.DIV_III if is_nbfc else cls.DIV_II
                errors.append(
                    f"Inconsistent Selection: {cls.FRAMEWORK_IND_AS} entities cannot apply {cls.DIV_I}. "
                    f"Must apply {correct_div}."
                )
                recommendations["schedule_iii_division"] = correct_div

            if is_nbfc and schedule_iii_division != cls.DIV_III:
                errors.append(
                    f"NBFC Entity Mismatch: Ind AS NBFCs must prepare financial statements under Schedule III {cls.DIV_III}. "
                    f"Currently selected: {schedule_iii_division}."
                )
                recommendations["schedule_iii_division"] = cls.DIV_III

            if not is_nbfc and schedule_iii_division == cls.DIV_III:
                errors.append(
                    f"Non-NBFC Mismatch: Schedule III {cls.DIV_III} is reserved solely for Non-Banking Financial Companies. "
                    f"For regular corporate entities under Ind AS, select {cls.DIV_II}."
                )
                recommendations["schedule_iii_division"] = cls.DIV_II

        # 2. Mandatory Ind AS Mandate for Listed Companies
        if is_listed and not is_ind_as:
            errors.append(
                "Statutory Violation: Under Rule 4(1)(iii)(a) of the Companies (Indian Accounting Standards) Rules, 2015, "
                "any company whose equity or debt securities are listed or in process of listing on any stock exchange "
                "in India or outside India MUST prepare financial statements under Ind AS framework."
            )
            recommendations["framework"] = cls.FRAMEWORK_IND_AS
            recommendations["schedule_iii_division"] = cls.DIV_III if is_nbfc else cls.DIV_II

        # 3. Unlisted Entity Net Worth Evaluation
        if not is_listed:
            if net_worth_crores is not None:
                if net_worth_crores >= 250.0 and is_as:
                    errors.append(
                        f"Threshold Breach: Unlisted company has reported net worth of ₹{net_worth_crores:.2f} Crores "
                        f"(≥ ₹250 Crores). Under Rule 4(1)(iii)(b) of Companies (Ind AS) Rules, 2015, Ind AS is mandatory."
                    )
                    recommendations["framework"] = cls.FRAMEWORK_IND_AS
                    recommendations["schedule_iii_division"] = cls.DIV_III if is_nbfc else cls.DIV_II
                elif net_worth_crores < 250.0 and is_ind_as:
                    warnings.append(
                        f"Voluntary Adoption: Reported net worth is ₹{net_worth_crores:.2f} Crores (< ₹250 Crores). "
                        "Ind AS appears to be voluntarily adopted under Rule 4(1)(ii). Note that once Ind AS is adopted voluntarily, "
                        "the company cannot revert back to AS in subsequent years (Rule 4(3))."
                    )
            else:
                # Clarification prompt as required by prompt
                clarifications_needed.append(
                    "Net Worth Threshold Clarification: Net worth data was not provided for this unlisted company. "
                    "If net worth is ₹250 Crores or more as on 31st March of any preceding financial year, "
                    "Ind AS is mandatory. If net worth is below ₹250 Crores, AS is applicable unless voluntarily adopting Ind AS."
                )

        # 4. Consolidated Financial Statements (CFS) Rules
        if statement_type.strip().lower() == "consolidated":
            applicable_laws.append("Section 129(3) of Companies Act, 2013 (Consolidated Financial Statements)")
            if is_ind_as:
                applicable_laws.extend([
                    "Ind AS 110 (Consolidated Financial Statements)",
                    "Ind AS 111 (Joint Arrangements)",
                    "Ind AS 28 (Investments in Associates and Joint Ventures)",
                    "Ind AS 112 (Disclosure of Interests in Other Entities)"
                ])
            else:
                applicable_laws.extend([
                    "AS 21 (Consolidated Financial Statements)",
                    "AS 23 (Accounting for Investments in Associates)",
                    "AS 27 (Financial Reporting of Interests in Joint Ventures)"
                ])
        else:
            if is_ind_as:
                applicable_laws.append("Ind AS 27 (Separate Financial Statements)")

        # 5. Compile Appropriate Framework Reference Materials
        if is_ind_as:
            applicable_laws.extend([
                "Companies (Indian Accounting Standards) Rules, 2015 as amended",
                f"Schedule III {schedule_iii_division if not errors else recommendations.get('schedule_iii_division', cls.DIV_II)}",
                "ICAI Guidance Note on Division II of Schedule III to the Companies Act, 2013",
                "CARO, 2020 (Companies (Auditor's Report) Order, 2020)",
                "FRRB Study on Compliance of Financial Reporting Requirements (Ind AS Framework)",
            ])
        else:
            applicable_laws.extend([
                "Companies (Accounting Standards) Rules, 2021",
                "Schedule III Division I",
                "ICAI Guidance Note on Division I of Schedule III to the Companies Act, 2013",
                "CARO, 2020 (Companies (Auditor's Report) Order, 2020)",
                "FRRB Selected Observations on AS Framework",
            ])

        is_valid = len(errors) == 0

        status = "Compliant & Valid" if is_valid else "Applicability Non-Compliance"
        if not errors and clarifications_needed:
            status = "Valid (With Threshold Verification Recommended)"

        return {
            "is_valid": is_valid,
            "status": status,
            "errors": errors,
            "warnings": warnings,
            "clarifications_needed": clarifications_needed,
            "recommendations": recommendations,
            "applicable_laws": applicable_laws,
            "profile_summary": {
                "company_type": company_type,
                "listing_status": listing_status,
                "framework": framework,
                "schedule_iii_division": schedule_iii_division,
                "financial_year": financial_year,
                "statement_type": statement_type,
                "is_nbfc": is_nbfc,
                "net_worth_crores": net_worth_crores,
            }
        }
