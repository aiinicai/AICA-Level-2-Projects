"""Presumptive Taxation (Section 44AD / 44ADA) Evaluation Module."""

import pandas as pd
from typing import Dict, Any

def analyze_presumptive_tax(df: pd.DataFrame, declared_business_type: str = "44AD") -> Dict[str, Any]:
    """
    Evaluate presumptive taxation eligibility and limits under Section 44AD / 44ADA.
    
    Section 44AD (Small Businesses):
    - Normal Limit: ₹2 Crore
    - Enhanced Limit (if digital receipts >= 95%): ₹3 Crore
    - Minimum presumptive profit: 6% of digital receipts + 8% of non-digital receipts
    
    Section 44ADA (Professionals):
    - Normal Limit: ₹50 Lakhs
    - Enhanced Limit (if digital receipts >= 95%): ₹75 Lakhs
    - Minimum presumptive profit: 50% of gross receipts
    """
    if df is None or df.empty:
        return {
            "total_turnover": 0.0,
            "digital_receipts": 0.0,
            "cash_receipts": 0.0,
            "digital_percentage": 0.0,
            "sec_44ad_eligible": True,
            "sec_44ada_eligible": True,
            "audit_required_44ad": False,
            "audit_required_44ada": False,
            "min_presumptive_income_44ad": 0.0,
            "min_presumptive_income_44ada": 0.0,
            "remarks": "No transaction data available."
        }

    # Identify business/professional receipts
    # Filter credit entries excluding loans, capital, refunds, internal transfers
    excluded_categories = [
        "Loan Received", "Capital Introduced", "Refund (GST/IT/Vendor)",
        "Reversal/Reimbursement", "Gift/Family Transfer", "Maturity Proceeds (FD/Insurance/Mutual Fund)",
        "Sale of Asset/Investment"
    ]
    
    credits_df = df[df["credit_amount"] > 0]
    business_df = credits_df[~credits_df["nature"].isin(excluded_categories)]
    
    total_turnover = float(business_df["credit_amount"].sum())
    
    # Classify digital vs cash receipts
    cash_mask = business_df["mode"].isin(["CASH", "CDM", "BNA"]) | (business_df["nature"] == "Cash Deposit")
    cash_receipts = float(business_df[cash_mask]["credit_amount"].sum())
    digital_receipts = float(business_df[~cash_mask]["credit_amount"].sum())
    
    digital_pct = (digital_receipts / total_turnover * 100.0) if total_turnover > 0 else 100.0

    # Section 44AD logic
    limit_44ad = 30000000.0 if digital_pct >= 95.0 else 20000000.0
    eligible_44ad = total_turnover <= limit_44ad
    min_income_44ad = (digital_receipts * 0.06) + (cash_receipts * 0.08)

    # Section 44ADA logic
    limit_44ada = 7500000.0 if digital_pct >= 95.0 else 5000000.0
    eligible_44ada = total_turnover <= limit_44ada
    min_income_44ada = total_turnover * 0.50

    return {
        "total_turnover": round(total_turnover, 2),
        "digital_receipts": round(digital_receipts, 2),
        "cash_receipts": round(cash_receipts, 2),
        "digital_percentage": round(digital_pct, 2),
        "sec_44ad_limit_applicable": limit_44ad,
        "sec_44ad_eligible": eligible_44ad,
        "audit_required_44ad": not eligible_44ad,
        "min_presumptive_income_44ad": round(min_income_44ad, 2),
        "sec_44ada_limit_applicable": limit_44ada,
        "sec_44ada_eligible": eligible_44ada,
        "audit_required_44ada": not eligible_44ada,
        "min_presumptive_income_44ada": round(min_income_44ada, 2),
        "enhanced_threshold_qualified": digital_pct >= 95.0,
        "remarks": (
            f"Digital receipts are {digital_pct:.1f}%. "
            f"{'Qualified for enhanced limits (>=95% digital).' if digital_pct >= 95.0 else 'Subject to regular limits (<95% digital).'}"
        )
    }
