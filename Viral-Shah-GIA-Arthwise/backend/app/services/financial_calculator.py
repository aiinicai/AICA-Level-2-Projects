from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Dict, Any, List, Tuple, Optional

PRELIMINARY_ASSESSMENT_DISCLAIMER = (
    "All eligibility results are preliminary estimates for professional review. "
    "Never represent them as a loan sanction, credit approval, or guarantee. "
    "Final underwriting and sanction are subject to lender policies, legal vetting, and credit committee approval."
)

def round_inr(value: Decimal) -> Decimal:
    """Round to 2 decimal places using standard ROUND_HALF_UP."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def calculate_emi(principal: Decimal, annual_rate_pct: float, tenure_months: int) -> Decimal:
    """
    Standard EMI calculation with edge case handling (0% interest, invalid inputs).
    Formula: E = P * r * (1 + r)^n / ((1 + r)^n - 1)
    """
    if principal <= 0 or tenure_months <= 0:
        return Decimal("0.00")
    
    if annual_rate_pct <= 0:
        return round_inr(principal / Decimal(tenure_months))
    
    # Monthly interest rate
    r = Decimal(str(annual_rate_pct)) / Decimal("1200")
    n = tenure_months
    
    one_plus_r_n = (Decimal("1") + r) ** n
    numerator = principal * r * one_plus_r_n
    denominator = one_plus_r_n - Decimal("1")
    
    if denominator == Decimal("0"):
        return round_inr(principal / Decimal(tenure_months))
    
    emi = numerator / denominator
    return round_inr(emi)

def calculate_max_loan_from_emi(monthly_emi: Decimal, annual_rate_pct: float, tenure_months: int) -> Decimal:
    """
    Reverse EMI calculation: Calculates present value principal given supportable EMI.
    P = E * ((1 + r)^n - 1) / (r * (1 + r)^n)
    """
    if monthly_emi <= 0 or tenure_months <= 0:
        return Decimal("0.00")
    
    if annual_rate_pct <= 0:
        return round_inr(monthly_emi * Decimal(tenure_months))
    
    r = Decimal(str(annual_rate_pct)) / Decimal("1200")
    n = tenure_months
    
    one_plus_r_n = (Decimal("1") + r) ** n
    numerator = (one_plus_r_n - Decimal("1"))
    denominator = r * one_plus_r_n
    
    principal = monthly_emi * (numerator / denominator)
    return round_inr(max(Decimal("0.00"), principal))

def generate_amortization_schedule(principal: Decimal, annual_rate_pct: float, tenure_months: int) -> List[Dict[str, Any]]:
    """Generates monthly amortization schedule with opening balance, EMI, interest, principal, and closing balance."""
    schedule = []
    if principal <= 0 or tenure_months <= 0:
        return schedule
    
    emi = calculate_emi(principal, annual_rate_pct, tenure_months)
    monthly_rate = Decimal(str(annual_rate_pct)) / Decimal("1200") if annual_rate_pct > 0 else Decimal("0")
    
    balance = principal
    for month in range(1, tenure_months + 1):
        interest = round_inr(balance * monthly_rate)
        if month == tenure_months:
            # Settle rounding difference on final installment
            principal_paid = balance
            actual_emi = round_inr(principal_paid + interest)
            balance = Decimal("0.00")
        else:
            principal_paid = round_inr(emi - interest)
            balance = round_inr(balance - principal_paid)
            actual_emi = emi
            
        schedule.append({
            "month": month,
            "opening_balance": float(balance + principal_paid),
            "emi": float(actual_emi),
            "interest": float(interest),
            "principal": float(principal_paid),
            "closing_balance": float(balance)
        })
    return schedule

def calculate_foir_eligibility(
    monthly_income: Decimal,
    existing_monthly_emi: Decimal,
    max_foir_pct: float,
    interest_rate_pct: float,
    tenure_months: int
) -> Tuple[Decimal, Decimal, float]:
    """
    Calculates FOIR and maximum eligible loan supported by net income.
    Returns: (foir_eligible_loan, proposed_emi_budget, current_foir_without_loan)
    """
    if monthly_income <= 0:
        return Decimal("0.00"), Decimal("0.00"), 0.0
    
    max_foir_decimal = Decimal(str(max_foir_pct)) / Decimal("100")
    total_allowed_emi = round_inr(monthly_income * max_foir_decimal)
    
    available_monthly_emi = max(Decimal("0.00"), total_allowed_emi - existing_monthly_emi)
    foir_eligible_loan = calculate_max_loan_from_emi(available_monthly_emi, interest_rate_pct, tenure_months)
    
    current_foir = float((existing_monthly_emi / monthly_income) * Decimal("100"))
    return foir_eligible_loan, available_monthly_emi, current_foir

def calculate_ltv_eligibility(collateral_market_value: Decimal, max_ltv_pct: float) -> Decimal:
    """Calculates collateral-backed loan limit from market value."""
    if collateral_market_value <= 0 or max_ltv_pct <= 0:
        return Decimal("0.00")
    ltv_factor = Decimal(str(max_ltv_pct)) / Decimal("100")
    return round_inr(collateral_market_value * ltv_factor)

def calculate_dscr(
    pat: Decimal,
    depreciation: Decimal,
    finance_costs: Decimal,
    principal_repayments: Decimal
) -> float:
    """
    Standard Banking DSCR = (PAT + Depreciation + Finance Costs) / (Principal Repayments + Finance Costs)
    """
    earnings_available = pat + depreciation + finance_costs
    debt_service = principal_repayments + finance_costs
    
    if debt_service <= 0:
        return 99.99 if earnings_available > 0 else 0.0
    
    dscr = float(earnings_available / debt_service)
    return round(dscr, 2)

def calculate_dscr_eligibility(
    pat: Decimal,
    depreciation: Decimal,
    finance_costs: Decimal,
    existing_principal_repayments: Decimal,
    target_dscr: float,
    interest_rate_pct: float,
    tenure_months: int
) -> Decimal:
    """
    Calculates maximum term loan principal supportable by business cash accruals
    maintaining at least target_dscr.
    """
    cash_accrual = pat + depreciation
    total_available_ebitda = cash_accrual + finance_costs
    
    if target_dscr <= 0 or total_available_ebitda <= 0:
        return Decimal("0.00")
    
    # Maximum allowed annual total debt service
    target_dscr_dec = Decimal(str(target_dscr))
    max_total_annual_debt_service = total_available_ebitda / target_dscr_dec
    
    # Existing debt service
    existing_annual_debt_service = existing_principal_repayments + finance_costs
    available_annual_debt_service = max(Decimal("0.00"), max_total_annual_debt_service - existing_annual_debt_service)
    
    available_monthly_debt_service = available_annual_debt_service / Decimal("12")
    return calculate_max_loan_from_emi(available_monthly_debt_service, interest_rate_pct, tenure_months)

def calculate_interest_coverage(ebitda: Decimal, finance_costs: Decimal) -> float:
    if finance_costs <= 0:
        return 99.99 if ebitda > 0 else 0.0
    return round(float(ebitda / finance_costs), 2)

def calculate_working_capital_days(
    debtors: Decimal,
    creditors: Decimal,
    inventory: Decimal,
    turnover: Decimal,
    cogs: Decimal,
    purchases: Decimal
) -> Dict[str, int]:
    """Calculates Debtor Days, Inventory Days, Creditor Days and Net Cash Cycle."""
    debtor_days = int(round(float((debtors / turnover) * Decimal("365")))) if turnover > 0 else 0
    inv_days = int(round(float((inventory / cogs) * Decimal("365")))) if cogs > 0 else 0
    creditor_days = int(round(float((creditors / purchases) * Decimal("365")))) if purchases > 0 else 0
    
    net_cycle = debtor_days + inv_days - creditor_days
    return {
        "debtor_days": max(0, debtor_days),
        "inventory_days": max(0, inv_days),
        "creditor_days": max(0, creditor_days),
        "net_working_capital_cycle_days": net_cycle
    }

def calculate_balance_sheet_ratios(
    current_assets: Decimal,
    current_liabilities: Decimal,
    inventory: Decimal,
    total_debt: Decimal,
    tangible_net_worth: Decimal,
    total_outside_liabilities: Decimal
) -> Dict[str, float]:
    current_ratio = float(current_assets / current_liabilities) if current_liabilities > 0 else 0.0
    quick_assets = max(Decimal("0.00"), current_assets - inventory)
    quick_ratio = float(quick_assets / current_liabilities) if current_liabilities > 0 else 0.0
    
    debt_equity = float(total_debt / tangible_net_worth) if tangible_net_worth > 0 else 0.0
    tol_tnw = float(total_outside_liabilities / tangible_net_worth) if tangible_net_worth > 0 else 0.0
    
    return {
        "current_ratio": round(current_ratio, 2),
        "quick_ratio": round(quick_ratio, 2),
        "debt_equity_ratio": round(debt_equity, 2),
        "tol_tnw_ratio": round(tol_tnw, 2)
    }

def calculate_nayak_turnover_method(projected_turnover: Decimal) -> Dict[str, Decimal]:
    """
    Nayak Committee Turnover Method for MSME Working Capital limits up to ₹5 Crore:
    - Total Working Capital requirement: 25% of turnover
    - Promoter Margin: 5% of turnover
    - Maximum Bank Finance (MPBF): 20% of turnover
    """
    total_wc = round_inr(projected_turnover * Decimal("0.25"))
    promoter_margin = round_inr(projected_turnover * Decimal("0.05"))
    mpbf = round_inr(projected_turnover * Decimal("0.20"))
    return {
        "projected_turnover": projected_turnover,
        "total_working_capital_requirement": total_wc,
        "minimum_promoter_margin": promoter_margin,
        "assessed_bank_finance_limit": mpbf
    }

def calculate_tandon_method_ii(current_assets: Decimal, other_current_liabilities: Decimal) -> Dict[str, Decimal]:
    """
    Tandon Committee Method II (MPBF):
    - Working Capital Gap (WCG) = Current Assets - Other Current Liabilities (excl. bank borrowings)
    - Minimum Net Working Capital (Margin) = 25% of Current Assets
    - Maximum Permissible Bank Finance = WCG - Margin
    """
    wcg = max(Decimal("0.00"), current_assets - other_current_liabilities)
    min_margin = round_inr(current_assets * Decimal("0.25"))
    mpbf = max(Decimal("0.00"), wcg - min_margin)
    return {
        "current_assets": current_assets,
        "other_current_liabilities": other_current_liabilities,
        "working_capital_gap": wcg,
        "minimum_margin_required": min_margin,
        "maximum_permissible_bank_finance": round_inr(mpbf)
    }

def resolve_limiting_factor_and_eligibility(
    product_type: str,
    requested_amount: Decimal,
    foir_eligible: Decimal,
    ltv_eligible: Decimal,
    dscr_eligible: Decimal,
    is_secured: bool = True
) -> Tuple[Decimal, str]:
    """
    Identifies which parameter is the binding limiting constraint among
    FOIR, Collateral LTV, DSCR, and Requested Amount.
    """
    constraints: List[Tuple[str, Decimal]] = [("Requested Loan Amount", requested_amount)]
    
    if foir_eligible > 0:
        constraints.append(("Repayment Capacity (FOIR)", foir_eligible))
    
    if is_secured and ltv_eligible > 0:
        constraints.append(("Collateral Valuation (LTV)", ltv_eligible))
        
    if dscr_eligible > 0 and product_type in ["business_loan_secured", "project_finance_term_loan", "working_capital"]:
        constraints.append(("Debt Service Capacity (DSCR)", dscr_eligible))
        
    # Sort constraints ascending
    sorted_constraints = sorted(constraints, key=lambda x: x[1])
    limiting_factor, eligible_amount = sorted_constraints[0]
    
    return round_inr(eligible_amount), limiting_factor
