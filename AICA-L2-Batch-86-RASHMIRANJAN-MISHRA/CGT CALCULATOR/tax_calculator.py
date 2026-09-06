"""
CAPITAL GAINS TAX COMPARISON CALCULATOR (12.5% vs 20%)
Tax Liability & Comparison Engine
Author: Senior Python Developer & Tax-Audit Software Architect
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from capital_gain_engine import CapitalGainComputationResult
from tax_rules import calculate_surcharge_rate, TaxRuleMaster


@dataclass
class MethodTaxDetails:
    method_name: str
    tax_rate_percent: float
    taxable_capital_gain: float
    is_loss: bool
    basic_tax: float
    surcharge_rate_percent: float
    surcharge_amount: float
    cess_rate_percent: float
    cess_amount: float
    total_tax_liability: float
    effective_tax_rate_percent: float


@dataclass
class TaxComparisonResult:
    cg_result: CapitalGainComputationResult

    # Method 1: 12.5% Without Indexation
    method_12_5: MethodTaxDetails

    # Method 2: 20% With Indexation (None if ineligibile)
    method_20: Optional[MethodTaxDetails]

    # Comparison & Decision
    is_20_applicable: bool
    ineligibility_reason: str
    recommended_method: str  # '12.5% WITHOUT INDEXATION', '20% WITH INDEXATION', or 'EITHER METHOD'
    recommended_method_code: str  # '12_5', '20', 'EQUAL', 'NOT_APPLICABLE'
    lower_tax_liability: float
    higher_tax_liability: float
    tax_saving: float
    recommendation_summary: str
    detailed_statutory_note: str


def calculate_method_tax(
    taxable_gain: float,
    tax_rate_percent: float,
    method_name: str,
    manual_surcharge_rate: Optional[float] = None,
    tax_rules: Optional[TaxRuleMaster] = None,
) -> MethodTaxDetails:
    """Computes basic tax, surcharge, cess, and total tax rounded as per Section 288B."""
    rules = tax_rules or TaxRuleMaster()
    cess_rate = rules.get("cess_rate", 4.0)

    if taxable_gain <= 0:
        return MethodTaxDetails(
            method_name=method_name,
            tax_rate_percent=tax_rate_percent,
            taxable_capital_gain=taxable_gain,
            is_loss=taxable_gain < 0,
            basic_tax=0.0,
            surcharge_rate_percent=0.0,
            surcharge_amount=0.0,
            cess_rate_percent=cess_rate,
            cess_amount=0.0,
            total_tax_liability=0.0,
            effective_tax_rate_percent=0.0,
        )

    # Basic Tax
    basic_tax = (taxable_gain * tax_rate_percent) / 100.0

    # Surcharge
    surcharge_rate = calculate_surcharge_rate(
        total_taxable_gains=taxable_gain,
        manual_surcharge_rate=manual_surcharge_rate,
        tax_rules=rules,
    )
    surcharge_amt = (basic_tax * surcharge_rate) / 100.0

    # Cess
    cess_amt = ((basic_tax + surcharge_amt) * cess_rate) / 100.0

    # Total Tax rounded to nearest rupee as per Section 288B
    total_tax = round(basic_tax + surcharge_amt + cess_amt)

    eff_rate = (total_tax / taxable_gain * 100.0) if taxable_gain > 0 else 0.0

    return MethodTaxDetails(
        method_name=method_name,
        tax_rate_percent=tax_rate_percent,
        taxable_capital_gain=taxable_gain,
        is_loss=False,
        basic_tax=round(basic_tax, 2),
        surcharge_rate_percent=surcharge_rate,
        surcharge_amount=round(surcharge_amt, 2),
        cess_rate_percent=cess_rate,
        cess_amount=round(cess_amt, 2),
        total_tax_liability=float(total_tax),
        effective_tax_rate_percent=round(eff_rate, 2),
    )


def compare_tax_methods(
    cg_result: CapitalGainComputationResult,
    manual_surcharge_rate: Optional[float] = None,
    tax_rules: Optional[TaxRuleMaster] = None,
) -> TaxComparisonResult:
    """
    Computes tax liabilities under both methods and provides an audit-grade comparative analysis.
    """
    rules = tax_rules or TaxRuleMaster()
    rate_12_5 = rules.get("ltcg_rate_new", 12.5)
    rate_20 = rules.get("ltcg_rate_old", 20.0)

    # 1. Method 1: 12.5% Without Indexation
    method_12_5 = calculate_method_tax(
        taxable_gain=cg_result.ltcg_12_5,
        tax_rate_percent=rate_12_5,
        method_name="12.5% Without Indexation",
        manual_surcharge_rate=manual_surcharge_rate,
        tax_rules=rules,
    )

    # 2. Method 2: 20% With Indexation (if applicable)
    if cg_result.is_20_applicable and cg_result.ltcg_20 is not None:
        method_20 = calculate_method_tax(
            taxable_gain=cg_result.ltcg_20,
            tax_rate_percent=rate_20,
            method_name="20% With Indexation",
            manual_surcharge_rate=manual_surcharge_rate,
            tax_rules=rules,
        )

        tax_1 = method_12_5.total_tax_liability
        tax_2 = method_20.total_tax_liability

        diff = abs(tax_1 - tax_2)

        if tax_1 < tax_2:
            rec_code = "12_5"
            rec_method = "12.5% WITHOUT INDEXATION"
            lower_tax = tax_1
            higher_tax = tax_2
            saving = diff
            summary = (
                f"The 12.5% Without Indexation method produces a LOWER tax liability of ₹{tax_1:,.2f} "
                f"compared to ₹{tax_2:,.2f} under the 20% Indexed method. "
                f"Selecting 12.5% results in a net tax saving of ₹{saving:,.2f}."
            )
        elif tax_2 < tax_1:
            rec_code = "20"
            rec_method = "20% WITH INDEXATION"
            lower_tax = tax_2
            higher_tax = tax_1
            saving = diff
            summary = (
                f"The 20% With Indexation method produces a LOWER tax liability of ₹{tax_2:,.2f} "
                f"compared to ₹{tax_1:,.2f} under the 12.5% method. "
                f"Selecting 20% with indexation results in a net tax saving of ₹{saving:,.2f}."
            )
        else:
            rec_code = "EQUAL"
            rec_method = "EITHER METHOD (IDENTICAL TAX)"
            lower_tax = tax_1
            higher_tax = tax_2
            saving = 0.0
            summary = (
                f"Both methods result in the exact same tax liability of ₹{tax_1:,.2f}. "
                f"The assessee may adopt either method."
            )

        statutory_note = (
            "Statutory basis: In terms of the second proviso to Section 112(1)(a) inserted by the Finance (No. 2) Act, 2024, "
            "for a resident individual or HUF transferring land or building acquired prior to 23-07-2024, "
            "the tax payable shall not exceed the tax computed under the pre-amendment provisions (i.e. at 20% with indexation). "
            "Hence, the assessee is legally entitled to pay the lower of the two tax liabilities."
        )

    else:
        method_20 = None
        rec_code = "NOT_APPLICABLE"
        rec_method = "12.5% WITHOUT INDEXATION"
        lower_tax = method_12_5.total_tax_liability
        higher_tax = method_12_5.total_tax_liability
        saving = 0.0
        summary = (
            f"The 20% Indexed Method is NOT legally applicable for this transaction. "
            f"Tax is payable strictly under the 12.5% unindexed regime (₹{lower_tax:,.2f})."
        )
        statutory_note = (
            f"Statutory safeguard: {cg_result.ineligibility_reason}. "
            f"Under the Income-tax Act, 1961 as amended by Finance (No. 2) Act, 2024, the alternative 20% indexed method cannot be claimed."
        )

    return TaxComparisonResult(
        cg_result=cg_result,
        method_12_5=method_12_5,
        method_20=method_20,
        is_20_applicable=cg_result.is_20_applicable,
        ineligibility_reason=cg_result.ineligibility_reason,
        recommended_method=rec_method,
        recommended_method_code=rec_code,
        lower_tax_liability=lower_tax,
        higher_tax_liability=higher_tax,
        tax_saving=saving,
        recommendation_summary=summary,
        detailed_statutory_note=statutory_note,
    )
