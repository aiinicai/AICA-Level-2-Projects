from decimal import Decimal
from typing import List, Dict, Any, Optional
from backend.app.services.financial_calculator import (
    calculate_foir_eligibility,
    calculate_ltv_eligibility,
    calculate_dscr_eligibility,
    calculate_emi,
    round_inr
)

# Seed illustrative lender policies
SEED_LENDERS = [
    {
        "code": "SBI",
        "name": "State Bank of India",
        "category": "public_bank",
        "policies": [
            {
                "product_type": "cash_credit_od",
                "policy_name": "SBI SME Credit Plus / Cash Credit",
                "min_loan": Decimal("1000000.00"),
                "max_loan": Decimal("200000000.00"),
                "max_foir": 60.0,
                "max_ltv": 75.0,
                "min_dscr": 1.35,
                "min_icr": 1.5,
                "min_cibil": 700,
                "min_vintage_years": 3.0,
                "min_turnover": Decimal("5000000.00"),
                "benchmark_rate": 8.85,
                "required_docs": ["Financials 3 Yrs", "ITR 3 Yrs", "GST Returns", "12M Bank Statements", "Debtors Ageing"]
            },
            {
                "product_type": "home_loan",
                "policy_name": "SBI Regular Home Loan",
                "min_loan": Decimal("500000.00"),
                "max_loan": Decimal("100000000.00"),
                "max_foir": 55.0,
                "max_ltv": 80.0,
                "min_dscr": 1.0,
                "min_icr": 1.0,
                "min_cibil": 725,
                "min_vintage_years": 2.0,
                "min_turnover": Decimal("0.00"),
                "benchmark_rate": 8.50,
                "required_docs": ["ITR 3 Yrs", "Form 16 / Salary Slips", "Property Chain Deeds", "Bank Statements 6M"]
            },
            {
                "product_type": "lap",
                "policy_name": "SBI Loan Against Property (SME Collateral)",
                "min_loan": Decimal("1000000.00"),
                "max_loan": Decimal("75000000.00"),
                "max_foir": 55.0,
                "max_ltv": 65.0,
                "min_dscr": 1.30,
                "min_icr": 1.5,
                "min_cibil": 720,
                "min_vintage_years": 3.0,
                "min_turnover": Decimal("3000000.00"),
                "benchmark_rate": 9.25,
                "required_docs": ["Financials 3 Yrs", "ITR 3 Yrs", "Property Valuation", "Bank Statements 12M"]
            }
        ]
    },
    {
        "code": "HDFC",
        "name": "HDFC Bank",
        "category": "private_bank",
        "policies": [
            {
                "product_type": "cash_credit_od",
                "policy_name": "HDFC Smart Business Cash Credit",
                "min_loan": Decimal("1500000.00"),
                "max_loan": Decimal("150000000.00"),
                "max_foir": 65.0,
                "max_ltv": 75.0,
                "min_dscr": 1.30,
                "min_icr": 1.5,
                "min_cibil": 720,
                "min_vintage_years": 3.0,
                "min_turnover": Decimal("7500000.00"),
                "benchmark_rate": 9.15,
                "required_docs": ["Financials 3 Yrs", "GSTR 3B 12M", "Bank Statements 12M", "Sanction Letters"]
            },
            {
                "product_type": "home_loan",
                "policy_name": "HDFC Prime Home Loan",
                "min_loan": Decimal("1000000.00"),
                "max_loan": Decimal("150000000.00"),
                "max_foir": 60.0,
                "max_ltv": 80.0,
                "min_dscr": 1.0,
                "min_icr": 1.0,
                "min_cibil": 750,
                "min_vintage_years": 2.0,
                "min_turnover": Decimal("0.00"),
                "benchmark_rate": 8.70,
                "required_docs": ["Salary Slips 6M", "Form 16 2 Yrs", "Bank Statements 6M", "Property Documents"]
            },
            {
                "product_type": "project_finance_term_loan",
                "policy_name": "HDFC Term Loan for Commercial Expansion",
                "min_loan": Decimal("2500000.00"),
                "max_loan": Decimal("100000000.00"),
                "max_foir": 65.0,
                "max_ltv": 70.0,
                "min_dscr": 1.40,
                "min_icr": 1.75,
                "min_cibil": 720,
                "min_vintage_years": 3.0,
                "min_turnover": Decimal("10000000.00"),
                "benchmark_rate": 9.40,
                "required_docs": ["CMA Projections 8 Yrs", "Audited Financials 3 Yrs", "Project Quotations", "Means of Finance"]
            }
        ]
    },
    {
        "code": "ICICI",
        "name": "ICICI Bank",
        "category": "private_bank",
        "policies": [
            {
                "product_type": "cash_credit_od",
                "policy_name": "ICICI InstaOD & SME Working Capital",
                "min_loan": Decimal("1000000.00"),
                "max_loan": Decimal("100000000.00"),
                "max_foir": 65.0,
                "max_ltv": 75.0,
                "min_dscr": 1.35,
                "min_icr": 1.5,
                "min_cibil": 700,
                "min_vintage_years": 2.5,
                "min_turnover": Decimal("5000000.00"),
                "benchmark_rate": 9.20,
                "required_docs": ["Financials 3 Yrs", "GST Returns", "Bank Statements 12M"]
            },
            {
                "product_type": "lap",
                "policy_name": "ICICI Secured Business LAP",
                "min_loan": Decimal("1500000.00"),
                "max_loan": Decimal("80000000.00"),
                "max_foir": 60.0,
                "max_ltv": 65.0,
                "min_dscr": 1.30,
                "min_icr": 1.5,
                "min_cibil": 700,
                "min_vintage_years": 3.0,
                "min_turnover": Decimal("4000000.00"),
                "benchmark_rate": 9.50,
                "required_docs": ["Financials 3 Yrs", "Property Deeds", "Valuation Report", "ITR 3 Yrs"]
            }
        ]
    },
    {
        "code": "BAJAJ",
        "name": "Bajaj Housing Finance & Finserve",
        "category": "nbfc",
        "policies": [
            {
                "product_type": "lap",
                "policy_name": "Bajaj High LTV LAP",
                "min_loan": Decimal("1000000.00"),
                "max_loan": Decimal("150000000.00"),
                "max_foir": 70.0,
                "max_ltv": 75.0,
                "min_dscr": 1.20,
                "min_icr": 1.3,
                "min_cibil": 680,
                "min_vintage_years": 2.0,
                "min_turnover": Decimal("3000000.00"),
                "benchmark_rate": 9.75,
                "required_docs": ["Property Title Documents", "ITR 2 Yrs", "12M Banking"]
            }
        ]
    }
]

def evaluate_lender_policy_fit(
    policy: Dict[str, Any],
    borrower_profile: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evaluates borrower inputs against a specific lender policy.
    Identifies deviations, missing inputs, and policy fit status.
    """
    deviations = []
    missing = []
    
    requested_amount = Decimal(str(borrower_profile.get("requested_amount", "0")))
    monthly_income = Decimal(str(borrower_profile.get("monthly_income", "0")))
    existing_emi = Decimal(str(borrower_profile.get("existing_emi", "0")))
    tenure_months = int(borrower_profile.get("tenure_months", 60))
    collateral_value = Decimal(str(borrower_profile.get("collateral_value", "0")))
    cibil_score = borrower_profile.get("cibil_score")
    vintage_years = borrower_profile.get("vintage_years")
    turnover = Decimal(str(borrower_profile.get("turnover", "0")))
    dscr = borrower_profile.get("dscr", 0.0)
    
    # 1. Loan Size Limits
    if requested_amount < policy["min_loan"]:
        deviations.append(f"Requested amount ₹{requested_amount:,.2f} is below policy minimum ₹{policy['min_loan']:,.2f}")
    if requested_amount > policy["max_loan"]:
        deviations.append(f"Requested amount ₹{requested_amount:,.2f} exceeds policy maximum cap ₹{policy['max_loan']:,.2f}")
        
    # 2. CIBIL check
    if cibil_score is None:
        missing.append("Credit Bureau / CIBIL Score not provided")
    elif cibil_score < policy["min_cibil"]:
        deviations.append(f"Credit Score ({cibil_score}) is below benchmark requirement ({policy['min_cibil']})")
        
    # 3. Vintage check
    if vintage_years is None:
        missing.append("Business / Employment Vintage not specified")
    elif vintage_years < policy["min_vintage_years"]:
        deviations.append(f"Vintage ({vintage_years} yrs) is less than required ({policy['min_vintage_years']} yrs)")
        
    # 4. Turnover check
    if policy["min_turnover"] > 0 and turnover < policy["min_turnover"]:
        deviations.append(f"Turnover ₹{turnover:,.2f} is below lender minimum ₹{policy['min_turnover']:,.2f}")

    # 5. Financial Eligibility Limits under this lender's specific FOIR / LTV / Rate
    rate = policy["benchmark_rate"]
    foir_eligible, _, _ = calculate_foir_eligibility(
        monthly_income=monthly_income,
        existing_monthly_emi=existing_emi,
        max_foir_pct=policy["max_foir"],
        interest_rate_pct=rate,
        tenure_months=tenure_months
    )
    
    ltv_eligible = calculate_ltv_eligibility(
        collateral_market_value=collateral_value,
        max_ltv_pct=policy["max_ltv"]
    )
    
    # Calculate Max Eligible under this policy
    caps = [policy["max_loan"]]
    if foir_eligible > 0:
        caps.append(foir_eligible)
    if collateral_value > 0 and policy["max_ltv"] > 0:
        caps.append(ltv_eligible)
        
    max_eligible = min(caps) if caps else Decimal("0.00")
    
    # 6. DSCR check for term / business facilities
    if policy["product_type"] in ["cash_credit_od", "project_finance_term_loan"]:
        if dscr > 0 and dscr < policy["min_dscr"]:
            deviations.append(f"DSCR {dscr:.2f}x is below required minimum {policy['min_dscr']:.2f}x")
            
    # Determine Fit Status
    if len(deviations) == 0 and len(missing) == 0:
        fit_status = "ELIGIBLE"
    elif len(deviations) <= 1 and (cibil_score is None or cibil_score >= policy["min_cibil"] - 25):
        fit_status = "BORDERLINE"
    else:
        fit_status = "INELIGIBLE"
        
    return {
        "lender_code": policy.get("lender_code", "LNDR"),
        "lender_name": policy.get("lender_name", "Bank"),
        "product_type": policy["product_type"],
        "policy_name": policy["policy_name"],
        "fit_status": fit_status,
        "max_eligible_amount": round_inr(max_eligible),
        "benchmark_rate": policy["benchmark_rate"],
        "deviations": deviations,
        "missing_inputs": missing,
        "required_docs": policy.get("required_docs", [])
    }
