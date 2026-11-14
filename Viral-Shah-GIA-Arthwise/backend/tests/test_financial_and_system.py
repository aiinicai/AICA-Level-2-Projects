import pytest
from decimal import Decimal
from backend.app.services.financial_calculator import (
    calculate_emi,
    calculate_max_loan_from_emi,
    calculate_foir_eligibility,
    calculate_ltv_eligibility,
    calculate_dscr,
    calculate_dscr_eligibility,
    calculate_interest_coverage,
    calculate_working_capital_days,
    calculate_balance_sheet_ratios,
    calculate_nayak_turnover_method,
    calculate_tandon_method_ii,
    resolve_limiting_factor_and_eligibility,
    round_inr
)
from backend.app.services.extractor_service import parse_indian_number, extract_pan, extract_gstin
from backend.app.core.security import (
    mask_pan, mask_gstin, mask_account_number, sanitize_formula_injection,
    hash_password, verify_password
)
from backend.app.services.cma_service import generate_default_cma, validate_cma_balance

# 1. Financial Calculation Unit Tests
def test_emi_calculation():
    # 50 Lakhs at 9.5% for 60 months
    principal = Decimal("5000000.00")
    rate = 9.5
    tenure = 60
    emi = calculate_emi(principal, rate, tenure)
    # Expected EMI is approx 1,05,009.47
    assert emi > Decimal("100000") and emi < Decimal("110000")
    
    # Reverse calculation matches principal
    recovered_loan = calculate_max_loan_from_emi(emi, rate, tenure)
    assert abs(recovered_loan - principal) < Decimal("5.00")

def test_emi_zero_interest_edge_case():
    principal = Decimal("1200000.00")
    emi = calculate_emi(principal, 0.0, 12)
    assert emi == Decimal("100000.00")

def test_foir_eligibility():
    monthly_income = Decimal("300000.00")
    existing_emi = Decimal("60000.00")
    max_foir = 60.0 # 60% of 300,000 = 180,000 max total EMI
    rate = 9.5
    tenure = 60
    
    eligible_loan, available_emi, current_foir = calculate_foir_eligibility(
        monthly_income, existing_emi, max_foir, rate, tenure
    )
    # Available EMI should be 180,000 - 60,000 = 120,000
    assert available_emi == Decimal("120000.00")
    assert current_foir == 20.0
    assert eligible_loan > Decimal("5000000.00")

def test_ltv_eligibility():
    collateral_value = Decimal("20000000.00") # 2 Cr
    max_ltv = 75.0
    eligible_loan = calculate_ltv_eligibility(collateral_value, max_ltv)
    assert eligible_loan == Decimal("15000000.00") # 1.5 Cr

def test_dscr_calculation():
    pat = Decimal("3000000.00")
    depreciation = Decimal("1500000.00")
    finance_costs = Decimal("1200000.00")
    # Total available = 5,700,000
    debt_repayments = Decimal("2500000.00")
    # Total debt service = 3,700,000
    dscr = calculate_dscr(pat, depreciation, finance_costs, debt_repayments)
    # 5700000 / 3700000 = 1.54
    assert dscr == 1.54

def test_nayak_turnover_method():
    turnover = Decimal("40000000.00") # 4 Cr
    res = calculate_nayak_turnover_method(turnover)
    assert res["total_working_capital_requirement"] == Decimal("10000000.00") # 25%
    assert res["minimum_promoter_margin"] == Decimal("2000000.00")           # 5%
    assert res["assessed_bank_finance_limit"] == Decimal("8000000.00")        # 20%

def test_tandon_method_ii():
    current_assets = Decimal("25000000.00") # 2.5 Cr
    other_cl = Decimal("8000000.00")        # 80 Lakhs
    res = calculate_tandon_method_ii(current_assets, other_cl)
    # WCG = 2.5 Cr - 80L = 1.7 Cr
    # Min Margin = 25% of 2.5 Cr = 62.5L
    # MPBF = 1.7 Cr - 62.5L = 1.075 Cr (10,750,000)
    assert res["working_capital_gap"] == Decimal("17000000.00")
    assert res["minimum_margin_required"] == Decimal("6250000.00")
    assert res["maximum_permissible_bank_finance"] == Decimal("10750000.00")

def test_limiting_factor_resolution():
    requested = Decimal("15000000.00") # 1.5 Cr
    foir_cap = Decimal("12000000.00")  # 1.2 Cr
    ltv_cap = Decimal("10000000.00")   # 1.0 Cr (Limiting)
    dscr_cap = Decimal("14000000.00")  # 1.4 Cr
    
    final_amt, factor = resolve_limiting_factor_and_eligibility(
        product_type="lap",
        requested_amount=requested,
        foir_eligible=foir_cap,
        ltv_eligible=ltv_cap,
        dscr_eligible=dscr_cap,
        is_secured=True
    )
    assert final_amt == Decimal("10000000.00")
    assert "Collateral Valuation (LTV)" in factor

# 2. Indian Number & Document Extraction Tests
def test_parse_indian_number():
    assert parse_indian_number("₹ 47,44,316.24") == Decimal("4744316.24")
    assert parse_indian_number("(1,50,000.00)") == Decimal("-150000.00")
    assert parse_indian_number("15.5 Lakhs") == Decimal("1550000.00")
    assert parse_indian_number("2.5 Crores") == Decimal("25000000.00")

def test_extract_pan_and_gstin():
    text = "Borrower PAN is ACAPX0000P and GSTIN is 24AAACX0000M1Z5 registered in Gujarat."
    assert extract_pan(text) == "ACAPX0000P"
    assert extract_gstin(text) == "24AAACX0000M1Z5"

# 3. Privacy, Masking & Formula Injection Security Tests
def test_masking():
    assert mask_pan("ACAPX0000P") == "AC*****P"
    assert mask_gstin("24AAACX0000M1Z5") == "24********1Z5"
    assert mask_account_number("50200012345678") == "**********5678"

def test_formula_injection_prevention():
    # Untrusted spreadsheet formula inputs
    malicious_inputs = ["=CMD('calc')", "+1234", "-cmd|' /C calc'!A0", "@SUM(A1:A10)"]
    for inp in malicious_inputs:
        sanitized = sanitize_formula_injection(inp)
        assert sanitized.startswith("'")

def test_password_hashing():
    pwd = "StrongSecurePassword@2026"
    h = hash_password(pwd)
    assert verify_password(pwd, h) is True
    assert verify_password("WrongPassword", h) is False

# 4. CMA Mathematical Balancing Validation
def test_cma_balance_sheet_balancing():
    cma = generate_default_cma(
        base_turnover_fy24=Decimal("45000000.00"),
        growth_rate_pct=18.0,
        ebitda_margin_pct=16.0,
        requested_cc_limit=Decimal("10000000.00"),
        requested_term_loan=Decimal("5000000.00")
    )
    val = validate_cma_balance(cma)
    assert val["is_reconciled"] is True
    assert val["max_discrepancy"] <= 1.0

def test_manual_financials_entry_schema():
    from backend.app.schemas.schemas import ManualFinancialsPayload, YearWiseFinancialEntry
    entry = YearWiseFinancialEntry(
        financial_period="FY 2024-25 (Audited)",
        revenue_from_operations=Decimal("190000000.00"),
        pat=Decimal("9800000.00"),
        tangible_net_worth=Decimal("11150000.00")
    )
    payload = ManualFinancialsPayload(entries=[entry], sync_to_cma=True)
    assert len(payload.entries) == 1
    assert payload.entries[0].revenue_from_operations == Decimal("190000000.00")

