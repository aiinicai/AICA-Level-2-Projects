"""
Quality Controls, Validations, and Reviewer Checklist for Ind AS 116
Performs accounting consistency checks, generates diagnostic alerts,
and provides a standardized Chartered Accountant sign-off checklist.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from modules.config import STATUTORY_DISCLAIMER

@dataclass
class QualityValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    review_points: List[str]


def _normalize_extracted(data: Dict) -> Dict[str, Dict]:
    """Ensures every field in extracted_data is accessible as a dictionary with 'value'."""
    normalized = {}
    if not data:
        return normalized
    for k, v in data.items():
        if hasattr(v, "to_dict") and callable(v.to_dict):
            normalized[k] = v.to_dict()
        elif hasattr(v, "value"):
            normalized[k] = {
                "key": getattr(v, "key", k),
                "label": getattr(v, "label", k),
                "value": v.value,
                "confidence": getattr(v, "confidence", 1.0),
                "source_page": getattr(v, "source_page", 1),
                "source_snippet": getattr(v, "source_snippet", ""),
                "requires_review": getattr(v, "requires_review", False)
            }
        elif isinstance(v, dict):
            normalized[k] = v
        else:
            normalized[k] = {"value": v}
    return normalized


class QualityControlEngine:
    def __init__(self):
        self.disclaimer = STATUTORY_DISCLAIMER

    def run_checks(self, extracted_data: Dict, assessment_obj=None) -> QualityValidationResult:
        """
        Validates internal consistency of contract parameters and accounting elections.
        Works seamlessly with ExtractedField objects, dicts, and None assessment_obj.
        """
        errors: List[str] = []
        warnings: List[str] = []
        review_points: List[str] = []

        # Normalize extracted_data so both ExtractedField and dict are supported
        data = _normalize_extracted(extracted_data)

        # 1. Discount Rate Check
        disc_field = data.get("discount_rate", {})
        disc_rate = float(disc_field.get("value", 8.5) or 8.5)
        if disc_rate <= 0:
            errors.append("Incremental Borrowing Rate (IBR) must be strictly greater than 0%.")
        elif disc_rate < 3.0:
            warnings.append(f"Discount rate {disc_rate}% is unusually low for commercial leases in India. Verify entity IBR.")
        elif disc_rate > 20.0:
            warnings.append(f"Discount rate {disc_rate}% is high. Ensure this matches current borrowing yield curves.")

        # 2. Term & Commencement Date Check
        comm_field = data.get("commencement_date", {})
        comm_date_str = str(comm_field.get("value", ""))
        try:
            comm_dt = datetime.strptime(comm_date_str, "%Y-%m-%d").date()
        except Exception:
            comm_dt = None
            errors.append("Invalid or unparsed Lease Commencement Date. Please verify YYYY-MM-DD format.")

        term_field = data.get("lease_term_months", {})
        term_months = int(term_field.get("value", 0) or 0)
        if term_months <= 0:
            errors.append("Lease term must be at least 1 month.")
        elif term_months > 600:
            warnings.append(f"Lease term of {term_months} months (50+ years) is unusually long. Verify if perpetual or ground lease.")

        # 3. Rental Amount Check
        rent_field = data.get("fixed_rental_amount", {})
        rent_amt = float(rent_field.get("value", 0.0) or 0.0)
        if rent_amt <= 0:
            errors.append("Fixed rental payment must be greater than zero.")

        # 4. Renewal & Termination Options Check
        renewal_option = str(data.get("renewal_option", {}).get("value", "") or "")
        if "detect" not in renewal_option.lower() and len(renewal_option) > 10:
            review_points.append(
                f"AUDIT REVIEW: Contract contains renewal clause ('{renewal_option[:60]}...'). "
                "Confirm if Lessee is reasonably certain to exercise renewal under Ind AS 116 para 18."
            )

        term_option = str(data.get("termination_option", {}).get("value", "") or "")
        if "notice" in term_option.lower() or "lock" in term_option.lower():
            review_points.append(
                f"AUDIT REVIEW: Check early termination rights & lock-in periods ('{term_option[:60]}...'). "
                "Ensure lease term reflects non-cancellable period + penalty periods."
            )

        # 5. Variable Lease Payments Check
        var_payments = str(data.get("variable_lease_payments", {}).get("value", "") or "")
        if var_payments and "none" not in var_payments.lower():
            warnings.append(
                f"Variable Lease Payments Detected: '{var_payments}'. "
                "Note: Variable payments linked to sales/turnover are excluded from lease liability "
                "and must be expensed in P&L as incurred under Ind AS 116 para 27(b)."
            )
            review_points.append("Verify whether variable payments are indexed to CPI/MCLR (included in PV) or turnover/sales (expensed in P&L).")

        # 6. Embedded Lease / Non-Lease Separation Check
        cam_amt = float(data.get("non_lease_components", {}).get("value", 0.0) or 0.0)
        practical_expedient = getattr(assessment_obj, "practical_expedient_elected", False) if assessment_obj else False
        short_term_elected = getattr(assessment_obj, "short_term_elected", False) if assessment_obj else False

        if cam_amt > 0 and not practical_expedient:
            review_points.append(
                f"Non-lease maintenance/CAM charges of {cam_amt:,.2f} are separated from lease liability. "
                "Ensure allocation reflects observable stand-alone prices under Ind AS 116.13."
            )
        elif cam_amt > 0 and practical_expedient:
            review_points.append(
                "Practical expedient elected: Non-lease CAM components are bundled with lease payments and capitalized in ROU Asset."
            )

        # 7. Low-Value & Short-Term Exemption Consistency Check
        if short_term_elected and term_months > 12:
            errors.append("Conflict: Short-term lease exemption cannot be elected for a lease term exceeding 12 months.")

        is_valid = len(errors) == 0
        return QualityValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            review_points=review_points
        )

    def get_reviewer_checklist(self) -> List[Dict[str, str]]:
        """
        Returns structured checklist questions for Chartered Accountant sign-off.
        """
        return [
            {
                "id": "CHK-01",
                "category": "Contract Inception",
                "question": "Has the contract been verified as an identified asset without substantive supplier substitution rights?",
                "reference": "Ind AS 116.B13-B20",
                "default_status": "Verified"
            },
            {
                "id": "CHK-02",
                "category": "Lease Term",
                "question": "Have all renewal and termination options been evaluated for reasonable certainty of exercise?",
                "reference": "Ind AS 116.18-21",
                "default_status": "Verified"
            },
            {
                "id": "CHK-03",
                "category": "Discount Rate",
                "question": "Does the incremental borrowing rate (IBR) reflect entity credit spread, term, currency, and security?",
                "reference": "Ind AS 116.26",
                "default_status": "Verified"
            },
            {
                "id": "CHK-04",
                "category": "ROU Asset Inclusions",
                "question": "Have initial direct costs, lease incentives received, and restoration provisions (Ind AS 37) been correctly adjusted in ROU asset?",
                "reference": "Ind AS 116.24",
                "default_status": "Verified"
            },
            {
                "id": "CHK-05",
                "category": "Disclosures",
                "question": "Are maturity analysis of undiscounted lease liabilities and current/non-current balance sheet splits prepared?",
                "reference": "Ind AS 116.51-60",
                "default_status": "Verified"
            }
        ]
