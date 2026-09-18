"""
CAPITAL GAINS TAX COMPARISON CALCULATOR (12.5% vs 20%)
Capital Gain Calculation Engine
Author: Senior Python Developer & Tax-Audit Software Architect
"""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Dict, Any, Optional
from cii_master import get_cii_for_date, date_to_fy, get_cii_for_fy
from tax_rules import (
    parse_date,
    determine_asset_classification,
    check_20_indexation_eligibility,
    get_pre_2001_adopted_cost,
    TaxRuleMaster,
)


@dataclass
class ImprovementItemResult:
    particulars: str
    amount: float
    date_of_improvement: str
    fy_of_improvement: str
    cii_improvement: int
    indexed_amount: float
    is_eligible: bool
    note: str = ""


@dataclass
class CapitalGainComputationResult:
    # Transaction & Assessee Details
    assessee_name: str
    pan: str
    assessee_type: str
    residential_status: str
    assessment_year: str
    financial_year_transfer: str
    asset_type: str
    date_of_sale: str
    date_of_acquisition: str
    holding_period_days: int
    holding_period_months: float
    asset_classification: str  # 'LONG_TERM' or 'SHORT_TERM'

    # Consideration & Transfer Expenses
    gross_sale_price: float
    transfer_expenses: float
    net_sale_price_already_deducted: bool
    net_sale_price: float

    # Acquisition details
    actual_cost_acq: float
    fmv_2001: float
    sdv_2001: Optional[float]
    adopted_cost_acq: float
    acq_fy: str
    acq_cii: int
    sale_cii: int
    indexed_cost_acq: float
    pre_2001_notes: str

    # Improvement details
    improvements: List[ImprovementItemResult]
    total_actual_improvement: float
    total_indexed_improvement: float

    # 12.5% Method
    ltcg_12_5: float
    is_12_5_loss: bool

    # 20% Indexed Method
    is_20_applicable: bool
    ineligibility_reason: str
    ltcg_20: Optional[float]
    is_20_loss: bool

    # Transfer expense breakdown list
    transfer_expense_items: List[Dict[str, Any]] = field(default_factory=list)


def compute_capital_gains(
    assessee_name: str,
    pan: Optional[str],
    assessee_type: str,
    residential_status: str,
    assessment_year: str,
    asset_type: str,
    date_of_sale: Any,
    date_of_acquisition: Any,
    gross_sale_price: float,
    transfer_expenses: float,
    net_sale_already_deducted: bool = False,
    net_sale_price_input: Optional[float] = None,
    actual_cost_acq: float = 0.0,
    fmv_2001: float = 0.0,
    sdv_2001: Optional[float] = None,
    improvements: Optional[List[Dict[str, Any]]] = None,
    transfer_expense_items: Optional[List[Dict[str, Any]]] = None,
    tax_rules: Optional[TaxRuleMaster] = None,
) -> CapitalGainComputationResult:
    """
    Executes the complete capital gain calculation under both 12.5% unindexed and 20% indexed methods.
    """
    rules = tax_rules or TaxRuleMaster()
    d_sale = parse_date(date_of_sale)
    d_acq = parse_date(date_of_acquisition)

    # 1. Sale FY and CII
    sale_cii, sale_fy = get_cii_for_date(d_sale, is_acquisition=False)

    # 2. Holding period & classification
    classification, holding_months, _ = determine_asset_classification(asset_type, d_acq, d_sale, rules)
    holding_days = (d_sale - d_acq).days

    # 3. Consideration & Expenses
    total_expenses = float(transfer_expenses)
    if net_sale_already_deducted:
        net_sale = float(net_sale_price_input if net_sale_price_input is not None else gross_sale_price)
        gross_sale = net_sale + total_expenses
    else:
        gross_sale = float(gross_sale_price)
        net_sale = max(0.0, gross_sale - total_expenses)

    # 4. Acquisition cost & pre-2001 adoption
    adopted_acq_cost, pre_2001_notes = get_pre_2001_adopted_cost(
        acq_date=d_acq,
        actual_cost=actual_cost_acq,
        fmv_2001=fmv_2001,
        sdv_2001=sdv_2001,
        asset_type=asset_type,
        tax_rules=rules,
    )

    # Acquisition CII
    acq_cii, acq_fy = get_cii_for_date(d_acq, is_acquisition=True)

    # Indexed cost of acquisition: Adopted Cost * (CII Sale / CII Acq)
    indexed_acq_cost = (adopted_acq_cost * sale_cii) / acq_cii if acq_cii > 0 else adopted_acq_cost

    # 5. Improvements computation
    improvements_raw = improvements or []
    calculated_improvements: List[ImprovementItemResult] = []
    total_actual_imp = 0.0
    total_indexed_imp = 0.0

    cut_off_2001 = date(2001, 4, 1)

    for idx, imp in enumerate(improvements_raw, 1):
        part = imp.get("particulars", f"Improvement #{idx}").strip()
        amt = float(imp.get("amount", 0.0))
        d_str = imp.get("date")

        if not d_str or amt <= 0:
            continue

        d_imp = parse_date(d_str)

        if d_imp < cut_off_2001:
            # Under section 55(1)(b), cost of improvement prior to 01-04-2001 is ignored
            calculated_improvements.append(
                ImprovementItemResult(
                    particulars=part,
                    amount=amt,
                    date_of_improvement=d_imp.strftime("%d/%m/%Y"),
                    fy_of_improvement=date_to_fy(d_imp),
                    cii_improvement=0,
                    indexed_amount=0.0,
                    is_eligible=False,
                    note="Incurred prior to 01-04-2001. Deemed absorbed in FMV as of 01-04-2001 (Sec 55(1)(b)).",
                )
            )
            continue

        # Post 01-04-2001 improvement
        imp_cii, imp_fy = get_cii_for_date(d_imp, is_acquisition=False)
        indexed_amt = (amt * sale_cii) / imp_cii if imp_cii > 0 else amt

        total_actual_imp += amt
        total_indexed_imp += indexed_amt

        calculated_improvements.append(
            ImprovementItemResult(
                particulars=part,
                amount=amt,
                date_of_improvement=d_imp.strftime("%d/%m/%Y"),
                fy_of_improvement=imp_fy,
                cii_improvement=imp_cii,
                indexed_amount=indexed_amt,
                is_eligible=True,
                note=f"Indexed: ₹{amt:,.2f} × {sale_cii}/{imp_cii}",
            )
        )

    # 6. Capital Gain under 12.5% Method (Without Indexation)
    # Net Sale Consideration - Adopted Cost of Acq - Total Actual Improvement
    ltcg_12_5 = net_sale - adopted_acq_cost - total_actual_imp
    is_12_5_loss = ltcg_12_5 < 0

    # 7. Eligibility check for 20% Indexed Method
    is_20_eligible, ineligibility_reason = check_20_indexation_eligibility(
        asset_type=asset_type,
        assessee_type=assessee_type,
        residential_status=residential_status,
        acq_date=d_acq,
        sale_date=d_sale,
        tax_rules=rules,
    )

    if is_20_eligible:
        # Net Sale Consideration - Indexed Cost of Acq - Total Indexed Improvement
        ltcg_20 = net_sale - indexed_acq_cost - total_indexed_imp
        is_20_loss = ltcg_20 < 0
    else:
        ltcg_20 = None
        is_20_loss = False

    return CapitalGainComputationResult(
        assessee_name=assessee_name.strip(),
        pan=pan.strip().upper() if pan else "",
        assessee_type=assessee_type,
        residential_status=residential_status,
        assessment_year=assessment_year,
        financial_year_transfer=sale_fy,
        asset_type=asset_type,
        date_of_sale=d_sale.strftime("%d/%m/%Y"),
        date_of_acquisition=d_acq.strftime("%d/%m/%Y"),
        holding_period_days=holding_days,
        holding_period_months=round(holding_months, 1),
        asset_classification=classification,
        gross_sale_price=gross_sale,
        transfer_expenses=total_expenses,
        net_sale_price_already_deducted=net_sale_already_deducted,
        net_sale_price=net_sale,
        actual_cost_acq=actual_cost_acq,
        fmv_2001=fmv_2001,
        sdv_2001=sdv_2001,
        adopted_cost_acq=adopted_acq_cost,
        acq_fy=acq_fy,
        acq_cii=acq_cii,
        sale_cii=sale_cii,
        indexed_cost_acq=indexed_acq_cost,
        pre_2001_notes=pre_2001_notes,
        improvements=calculated_improvements,
        total_actual_improvement=total_actual_imp,
        total_indexed_improvement=total_indexed_imp,
        ltcg_12_5=ltcg_12_5,
        is_12_5_loss=is_12_5_loss,
        is_20_applicable=is_20_eligible,
        ineligibility_reason=ineligibility_reason,
        ltcg_20=ltcg_20,
        is_20_loss=is_20_loss,
        transfer_expense_items=transfer_expense_items or [],
    )
