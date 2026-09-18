"""
CAPITAL GAINS TAX COMPARISON CALCULATOR (12.5% vs 20%)
Validation Module
Author: Senior Python Developer & Tax-Audit Software Architect
"""

import re
from datetime import date
from typing import List, Dict, Any, Optional, Tuple
from tax_rules import parse_date, check_20_indexation_eligibility, determine_asset_classification
from cii_master import get_cii_for_date, CIINotFoundError, normalize_fy, date_to_fy


class ValidationResult:
    """Encapsulates validation status, errors, and professional warnings."""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.is_20_applicable: bool = True
        self.ineligibility_reason: str = ""

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


def validate_pan(pan: Optional[str]) -> Tuple[bool, Optional[str]]:
    """Validates 10-character alphanumeric Indian PAN format (e.g. ABCDE1234F)."""
    if not pan or not pan.strip():
        return True, None
    pan_clean = pan.strip().upper()
    if re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", pan_clean):
        return True, None
    return False, "Invalid PAN format. Standard format is 5 uppercase letters, 4 digits, 1 uppercase letter (e.g. ABCDE1234F)."


def validate_transaction_inputs(
    assessee_name: str,
    pan: Optional[str],
    assessee_type: str,
    residential_status: str,
    asset_type: str,
    date_of_sale: Any,
    date_of_acquisition: Any,
    gross_sale_price: float,
    transfer_expenses: float,
    net_sale_already_deducted: bool,
    net_sale_price_input: Optional[float],
    actual_cost_acq: float,
    fmv_2001: float = 0.0,
    sdv_2001: Optional[float] = None,
    improvements: Optional[List[Dict[str, Any]]] = None,
) -> ValidationResult:
    """
    Performs comprehensive statutory, arithmetic, and chronological validation of transaction inputs.
    """
    result = ValidationResult()

    # 1. Assessee validation
    if not assessee_name or not assessee_name.strip():
        result.errors.append("Name of Assessee is required.")

    if pan:
        pan_valid, pan_msg = validate_pan(pan)
        if not pan_valid and pan_msg:
            result.warnings.append(pan_msg)

    # 2. Date parsing and chronology
    d_sale = None
    d_acq = None
    try:
        d_sale = parse_date(date_of_sale)
    except Exception:
        result.errors.append(f"Invalid Date of Sale: '{date_of_sale}'. Expected format DD/MM/YYYY.")

    try:
        d_acq = parse_date(date_of_acquisition)
    except Exception:
        result.errors.append(f"Invalid Date of Acquisition: '{date_of_acquisition}'. Expected format DD/MM/YYYY.")

    if d_sale and d_acq:
        if d_acq > d_sale:
            result.errors.append(
                f"Date of Acquisition ({d_acq.strftime('%d/%m/%Y')}) cannot be after Date of Sale ({d_sale.strftime('%d/%m/%Y')})."
            )

    # 3. Numeric amounts validation
    if gross_sale_price < 0:
        result.errors.append("Gross Sale Consideration cannot be negative.")
    if transfer_expenses < 0:
        result.errors.append("Transfer expenses cannot be negative.")
    if actual_cost_acq < 0:
        result.errors.append("Cost of Acquisition cannot be negative.")
    if fmv_2001 < 0:
        result.errors.append("Fair Market Value as of 01-04-2001 cannot be negative.")
    if sdv_2001 is not None and sdv_2001 < 0:
        result.errors.append("Stamp Duty Value as of 01-04-2001 cannot be negative.")

    # Net sale price check
    if net_sale_already_deducted:
        if net_sale_price_input is not None and net_sale_price_input < 0:
            result.errors.append("Net Sale Price cannot be negative.")
    else:
        effective_net = gross_sale_price - transfer_expenses
        if effective_net < 0:
            result.warnings.append(
                f"Transfer expenses (₹{transfer_expenses:,.2f}) exceed Gross Sale Consideration (₹{gross_sale_price:,.2f}), "
                f"resulting in negative Net Consideration."
            )

    # 4. Improvements validation
    improvements_list = improvements or []
    seen_improvements = set()
    pre_2001_improvements_found = False

    for idx, imp in enumerate(improvements_list, 1):
        amt = imp.get("amount", 0.0)
        p_date = imp.get("date")
        part = imp.get("particulars", f"Improvement #{idx}")

        if amt < 0:
            result.errors.append(f"Improvement #{idx} ('{part}'): Amount cannot be negative.")

        if p_date:
            try:
                d_imp = parse_date(p_date)
                if d_sale and d_imp > d_sale:
                    result.errors.append(
                        f"Improvement #{idx} ('{part}'): Date of Improvement ({d_imp.strftime('%d/%m/%Y')}) cannot be after Date of Sale ({d_sale.strftime('%d/%m/%Y')})."
                    )
                if d_acq and d_imp < d_acq:
                    result.errors.append(
                        f"Improvement #{idx} ('{part}'): Date of Improvement ({d_imp.strftime('%d/%m/%Y')}) cannot be before Date of Acquisition ({d_acq.strftime('%d/%m/%Y')})."
                    )
                if d_imp < date(2001, 4, 1):
                    pre_2001_improvements_found = True
            except Exception:
                result.errors.append(f"Improvement #{idx} ('{part}'): Invalid date format '{p_date}'.")

        # Duplicate check
        row_sig = (part.strip().lower(), str(p_date), amt)
        if row_sig in seen_improvements and amt > 0:
            result.warnings.append(
                f"Duplicate improvement entry detected: '{part}' on {p_date} for ₹{amt:,.2f}. Please confirm this is not an unintentional duplicate."
            )
        seen_improvements.add(row_sig)

    if pre_2001_improvements_found:
        result.warnings.append(
            "Statutory Rule under Section 55(1)(b): Cost of improvement incurred prior to 01-04-2001 is NOT deductible "
            "as it is deemed to be absorbed in the Fair Market Value as of 01-04-2001. Such expenses are excluded from deduction."
        )

    # 5. Check CII availability in Database
    if d_sale:
        try:
            get_cii_for_date(d_sale, is_acquisition=False)
        except CIINotFoundError as e:
            result.errors.append(f"CII Missing for Sale Date: {str(e)}")

    if d_acq:
        try:
            get_cii_for_date(d_acq, is_acquisition=True)
        except CIINotFoundError as e:
            result.errors.append(f"CII Missing for Acquisition Date: {str(e)}")

    for idx, imp in enumerate(improvements_list, 1):
        if imp.get("amount", 0) > 0 and imp.get("date"):
            try:
                d_imp = parse_date(imp["date"])
                if d_imp >= date(2001, 4, 1):
                    get_cii_for_date(d_imp, is_acquisition=False)
            except CIINotFoundError as e:
                result.errors.append(f"CII Missing for Improvement #{idx}: {str(e)}")
            except Exception:
                pass

    # 6. Check Eligibility for 20% Indexation
    if d_sale and d_acq and result.is_valid:
        is_eligible, reason = check_20_indexation_eligibility(
            asset_type=asset_type,
            assessee_type=assessee_type,
            residential_status=residential_status,
            acq_date=d_acq,
            sale_date=d_sale,
        )
        result.is_20_applicable = is_eligible
        result.ineligibility_reason = reason
        if not is_eligible:
            result.warnings.append(f"20% Indexed Method Status: {reason}")

    return result
