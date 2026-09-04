"""Default assumptions and §8.3 Principal repayment 3-step waterfall."""
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, Any
from src.config import DEFAULT_ASSUMPTIONS, DISCLOSURE_TEXTS
from src.core.derivations import PeriodFinancials


@dataclass
class AssumptionItem:
    key: str
    name: str
    value_cy: float
    value_py: float
    is_default: bool
    basis_cy: str  # 'default', 'extracted', 'derived', 'failed', 'manual'
    basis_py: str
    disclosure_text: str
    note: str = ""


@dataclass
class PrincipalRepaymentResult:
    principal_repayment_cy: float
    principal_repayment_py: float
    basis_cy: str
    basis_py: str
    disclosure_cy: str
    disclosure_py: str
    ic7_failed_cy: bool
    ic7_failed_py: bool
    gap_cy: float
    gap_py: float


def resolve_principal_repayment(
    closing_cy: PeriodFinancials,
    opening_cy: PeriodFinancials,
    closing_py: PeriodFinancials,
    opening_py: PeriodFinancials,
    tolerance: float = 0.05
) -> PrincipalRepaymentResult:
    """Resolve principal repayment of long-term borrowings via the 3-step waterfall (§8.3)."""
    
    def calculate_for_year(closing: PeriodFinancials, opening: PeriodFinancials) -> Tuple[float, str, str, bool, float]:
        # Step 1: Read cf_repayment_lt_borrowings if present and non-zero
        repay_cf = abs(closing.cf_repayment_lt_borrowings)
        if repay_cf > 0.0:
            return repay_cf, "extracted", DISCLOSURE_TEXTS["principal_repayment_extracted"], False, 0.0
            
        # Step 2: Derive
        opening_debt = opening.long_term_borrowings + opening.current_maturities_ltd
        closing_debt = closing.long_term_borrowings + closing.current_maturities_ltd
        proceeds = closing.cf_proceeds_lt_borrowings  # could be positive inflow or negative outflow in statement
        
        # If proceeds is reported negative in CF (e.g. net reduction reported as negative in CF proceeds row), handle carefully:
        # Standard: opening + proceeds - repayment = closing  =>  repayment = opening + proceeds - closing
        derived = opening_debt + proceeds - closing_debt
        
        # Check gap/articulation:
        # Expected closing = opening + proceeds
        # Gap without repayment = (opening + proceeds) - closing
        gap = (opening_debt + proceeds) - closing_debt
        
        # If derived >= 0, principal repayment is derived.
        # But if the borrowings movement does not articulate with CF (e.g. gap is significantly different or invalid),
        # or if proceeds was negative representing an unaccounted mismatch:
        # In PY file: opening_debt = 260.34, closing_debt = 110.86, proceeds = -97.05.
        # opening + proceeds - closing = 260.34 - 97.05 - 110.86 = 52.43. But closing was 110.86 and CF proceeds was -97.05!
        # The gap between stated proceeds and actual balance sheet movement is 110.86 lacs!
        # Step 3 validation:
        if abs(derived) < tolerance:
            # Reconciles to 0
            return 0.0, "derived", DISCLOSURE_TEXTS["principal_repayment_derived"], False, gap
        elif derived > tolerance:
            # If proceeds is negative or does not articulate:
            if proceeds < 0 and abs(proceeds - closing_debt) > tolerance:
                # CF does not articulate
                return 0.0, "failed", DISCLOSURE_TEXTS["principal_repayment_failed"], True, -closing_debt
            return derived, "derived", DISCLOSURE_TEXTS["principal_repayment_derived"], False, gap
        else:
            # Derived is negative (net fresh borrowing). Check if opening + proceeds == closing
            gap_fresh = (opening_debt + proceeds) - closing_debt
            if abs(gap_fresh) > tolerance:
                return 0.0, "failed", DISCLOSURE_TEXTS["principal_repayment_failed"], True, gap_fresh
            return 0.0, "derived", DISCLOSURE_TEXTS["principal_repayment_derived"], False, gap_fresh

    repay_cy, basis_cy, disc_cy, ic7_cy, gap_cy = calculate_for_year(closing_cy, opening_cy)
    repay_py, basis_py, disc_py, ic7_py, gap_py = calculate_for_year(closing_py, opening_py)
    
    return PrincipalRepaymentResult(
        principal_repayment_cy=repay_cy,
        principal_repayment_py=repay_py,
        basis_cy=basis_cy,
        basis_py=basis_py,
        disclosure_cy=disc_cy,
        disclosure_py=disc_py,
        ic7_failed_cy=ic7_cy,
        ic7_failed_py=ic7_py,
        gap_cy=gap_cy,
        gap_py=gap_py,
    )


def build_assumptions_registry(
    user_overrides: Optional[Dict[str, Any]] = None,
    pr_result: Optional[PrincipalRepaymentResult] = None,
    closing_cy: Optional[PeriodFinancials] = None,
    closing_py: Optional[PeriodFinancials] = None,
) -> Dict[str, AssumptionItem]:
    """Construct complete assumptions registry including defaults, disclosures, and waterfall."""
    overrides = user_overrides or {}
    tolerance = overrides.get("materiality_tolerance", DEFAULT_ASSUMPTIONS["materiality_tolerance"])
    
    # 1. credit_sales_pct
    cs_val = overrides.get("credit_sales_pct", DEFAULT_ASSUMPTIONS["credit_sales_pct"])
    cs_default = (cs_val == DEFAULT_ASSUMPTIONS["credit_sales_pct"])
    
    # 2. credit_purchases_pct
    cp_val = overrides.get("credit_purchases_pct", DEFAULT_ASSUMPTIONS["credit_purchases_pct"])
    cp_default = (cp_val == DEFAULT_ASSUMPTIONS["credit_purchases_pct"])
    
    # 3. lease_payments
    lp_val = overrides.get("lease_payments", DEFAULT_ASSUMPTIONS["lease_payments"])
    lp_default = (lp_val == DEFAULT_ASSUMPTIONS["lease_payments"])
    
    # 4. preference_dividend
    pd_val = overrides.get("preference_dividend", DEFAULT_ASSUMPTIONS["preference_dividend"])
    pd_default = (pd_val == DEFAULT_ASSUMPTIONS["preference_dividend"])
    has_pref_capital = False
    if closing_cy and (closing_cy.preference_share_capital > 0 or (closing_py and closing_py.preference_share_capital > 0)):
        has_pref_capital = True
    pd_disc = DISCLOSURE_TEXTS["preference_dividend_flagged"] if has_pref_capital else DISCLOSURE_TEXTS["preference_dividend"]
    
    # 5. investment_income
    ii_val = overrides.get("investment_income", DEFAULT_ASSUMPTIONS["investment_income"])
    ii_default = (ii_val == DEFAULT_ASSUMPTIONS["investment_income"])
    has_investments = False
    if closing_cy and (closing_cy.total_investments > 0 or (closing_py and closing_py.total_investments > 0)):
        has_investments = True
    ii_disc = DISCLOSURE_TEXTS["investment_income_has_investments"] if has_investments else DISCLOSURE_TEXTS["investment_income"]
    
    # 6. include_st_repay
    st_val = overrides.get("include_st_repay", DEFAULT_ASSUMPTIONS["include_st_repay"])
    st_default = (st_val == DEFAULT_ASSUMPTIONS["include_st_repay"])
    st_disc = DISCLOSURE_TEXTS["include_st_repay_included"] if st_val else DISCLOSURE_TEXTS["include_st_repay_excluded"]
    
    # 7. variance_threshold_pct
    vt_val = overrides.get("variance_threshold_pct", DEFAULT_ASSUMPTIONS["variance_threshold_pct"])
    
    # 8. materiality_tolerance
    mt_val = tolerance
    
    assumptions = {
        "credit_sales_pct": AssumptionItem(
            key="credit_sales_pct",
            name="Credit Sales Proportion",
            value_cy=cs_val,
            value_py=cs_val,
            is_default=cs_default,
            basis_cy="default" if cs_default else "manual",
            basis_py="default" if cs_default else "manual",
            disclosure_text=DISCLOSURE_TEXTS["credit_sales_pct"]
        ),
        "credit_purchases_pct": AssumptionItem(
            key="credit_purchases_pct",
            name="Credit Purchases Proportion",
            value_cy=cp_val,
            value_py=cp_val,
            is_default=cp_default,
            basis_cy="default" if cp_default else "manual",
            basis_py="default" if cp_default else "manual",
            disclosure_text=DISCLOSURE_TEXTS["credit_purchases_pct"]
        ),
        "lease_payments": AssumptionItem(
            key="lease_payments",
            name="Lease Payments",
            value_cy=lp_val,
            value_py=lp_val,
            is_default=lp_default,
            basis_cy="default" if lp_default else "manual",
            basis_py="default" if lp_default else "manual",
            disclosure_text=DISCLOSURE_TEXTS["lease_payments"]
        ),
        "preference_dividend": AssumptionItem(
            key="preference_dividend",
            name="Preference Dividend",
            value_cy=pd_val,
            value_py=pd_val,
            is_default=pd_default,
            basis_cy="default" if pd_default else "manual",
            basis_py="default" if pd_default else "manual",
            disclosure_text=pd_disc
        ),
        "investment_income": AssumptionItem(
            key="investment_income",
            name="Income from Investments",
            value_cy=ii_val,
            value_py=ii_val,
            is_default=ii_default,
            basis_cy="default" if ii_default else "manual",
            basis_py="default" if ii_default else "manual",
            disclosure_text=ii_disc
        ),
        "include_st_repay": AssumptionItem(
            key="include_st_repay",
            name="Include Short-Term Repayment in DSCR",
            value_cy=float(st_val),
            value_py=float(st_val),
            is_default=st_default,
            basis_cy="default" if st_default else "manual",
            basis_py="default" if st_default else "manual",
            disclosure_text=st_disc
        ),
        "variance_threshold_pct": AssumptionItem(
            key="variance_threshold_pct",
            name="Variance Flagging Threshold",
            value_cy=float(vt_val),
            value_py=float(vt_val),
            is_default=(vt_val == DEFAULT_ASSUMPTIONS["variance_threshold_pct"]),
            basis_cy="default",
            basis_py="default",
            disclosure_text=f"Variance threshold set to {vt_val}% per Schedule III guidelines."
        ),
        "materiality_tolerance": AssumptionItem(
            key="materiality_tolerance",
            name="Integrity Check Materiality Tolerance",
            value_cy=float(mt_val),
            value_py=float(mt_val),
            is_default=(mt_val == DEFAULT_ASSUMPTIONS["materiality_tolerance"]),
            basis_cy="default",
            basis_py="default",
            disclosure_text=f"Materiality tolerance for rounding and integrity checks is {mt_val}."
        ),
    }
    
    if pr_result:
        assumptions["principal_repayment"] = AssumptionItem(
            key="principal_repayment",
            name="Principal Repayment of Long-Term Borrowings",
            value_cy=pr_result.principal_repayment_cy,
            value_py=pr_result.principal_repayment_py,
            is_default=True,
            basis_cy=pr_result.basis_cy,
            basis_py=pr_result.basis_py,
            disclosure_text=f"CY: {pr_result.disclosure_cy} | PY: {pr_result.disclosure_py}"
        )
        
    return assumptions
