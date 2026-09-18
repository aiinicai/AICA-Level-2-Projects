"""Configuration, constants, theme tokens, and ratio definitions."""
import os
import sys
from pathlib import Path

# Application paths
APP_NAME = "ScheduleIIIRatioAnalyser"

def get_app_data_dir() -> Path:
    """Return platform-specific application data directory."""
    if sys.platform == "win32":
        app_data = os.environ.get("APPDATA")
        base = Path(app_data) if app_data else Path.home() / "AppData" / "Roaming"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".local" / "share"
    
    data_dir = base / APP_NAME
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

def get_database_path() -> Path:
    """Return the path to the SQLite database file."""
    return get_app_data_dir() / "ratio_analyser.db"

# Color tokens (§12 Visual design)
COLORS = {
    "primary_blue": "#0B4F8C",
    "deep_navy": "#073763",
    "accent_blue": "#1E88E5",
    "sky_tint": "#E3F0FB",
    "row_tint": "#F2F7FC",
    "surface_white": "#FFFFFF",
    "border_grey": "#D6DEE7",
    "text_primary": "#1A2330",
    "text_muted": "#5B6B7F",
    "success": "#1E8E5A",
    "warning": "#C77700",
    "danger": "#C0392B",
}

# Standard defaults (§8)
DEFAULT_ASSUMPTIONS = {
    "credit_sales_pct": 1.0,           # 100%
    "credit_purchases_pct": 1.0,       # 100%
    "lease_payments": 0.0,             # Nil
    "preference_dividend": 0.0,        # Nil
    "investment_income": 0.0,          # Nil
    "include_st_repay": 0,             # 0 = Excluded from debt service
    "variance_threshold_pct": 25.0,    # 25%
    "materiality_tolerance": 0.05,     # 0.05 in reporting units
}

# Mandatory disclosure wordings (§8)
DISCLOSURE_TEXTS = {
    "credit_sales_pct": (
        "The split between cash and credit sales is not disclosed in the financial statements. "
        "All sales have been treated as credit sales."
    ),
    "credit_purchases_pct": (
        "The split between cash and credit purchases is not disclosed. "
        "All purchases have been treated as credit purchases."
    ),
    "lease_payments": (
        "Lease payments falling due during the year are not separately disclosed and have been taken as nil."
    ),
    "preference_dividend": (
        "No preference share capital is in issue; preference dividend is nil."
    ),
    "preference_dividend_flagged": (
        "Preference share capital is reported; review whether preference dividend was declared or paid."
    ),
    "investment_income": (
        "The entity holds no investments; income from investments is nil."
    ),
    "investment_income_has_investments": (
        "Investments are reported but investment income is not separately broken out; taken as nil."
    ),
    "include_st_repay_excluded": (
        "Repayment of short-term borrowings represents revolving working capital facilities and has been excluded from debt service."
    ),
    "include_st_repay_included": (
        "Repayment of short-term borrowings has been included in debt service per manual setting."
    ),
    "principal_repayment_extracted": (
        "Principal repayment of long-term borrowings extracted directly from Cash Flow Statement."
    ),
    "principal_repayment_derived": (
        "Principal repayment of long-term borrowings derived from movement in borrowings and cash flow proceeds."
    ),
    "principal_repayment_failed": (
        "The cash flow statement does not articulate with the movement in long-term borrowings. "
        "Debt service comprises interest cost only."
    ),
}

# Schedule III Prescribed 11 Ratios (§6)
SCHEDULE_III_RATIOS = [
    {
        "id": 1,
        "key": "current_ratio",
        "name": "Current Ratio",
        "numerator_desc": "Current Assets",
        "denominator_desc": "Current Liabilities",
        "unit": "x",
        "is_percentage": False,
        "clause": "Clause 6(L)(i) of General Instructions to Schedule III",
    },
    {
        "id": 2,
        "key": "debt_equity_ratio",
        "name": "Debt-Equity Ratio",
        "numerator_desc": "Total Debt",
        "denominator_desc": "Shareholders' Equity",
        "unit": "x",
        "is_percentage": False,
        "clause": "Clause 6(L)(ii) of General Instructions to Schedule III",
    },
    {
        "id": 3,
        "key": "dscr",
        "name": "Debt Service Coverage Ratio",
        "numerator_desc": "Earnings available for debt service",
        "denominator_desc": "Debt Service (Interest + Principal Repayment)",
        "unit": "x",
        "is_percentage": False,
        "clause": "Clause 6(L)(iii) of General Instructions to Schedule III",
    },
    {
        "id": 4,
        "key": "return_on_equity",
        "name": "Return on Equity",
        "numerator_desc": "Net Profit after taxes − Preference Dividend",
        "denominator_desc": "Average Shareholders' Equity",
        "unit": "%",
        "is_percentage": True,
        "clause": "Clause 6(L)(iv) of General Instructions to Schedule III",
    },
    {
        "id": 5,
        "key": "inventory_turnover",
        "name": "Inventory Turnover Ratio",
        "numerator_desc": "Cost of Goods Sold",
        "denominator_desc": "Average Inventories",
        "unit": "x",
        "is_percentage": False,
        "clause": "Clause 6(L)(v) of General Instructions to Schedule III",
    },
    {
        "id": 6,
        "key": "trade_receivables_turnover",
        "name": "Trade Receivables Turnover Ratio",
        "numerator_desc": "Net Credit Sales (Net Revenue)",
        "denominator_desc": "Average Trade Receivables",
        "unit": "x",
        "is_percentage": False,
        "clause": "Clause 6(L)(vi) of General Instructions to Schedule III",
    },
    {
        "id": 7,
        "key": "trade_payables_turnover",
        "name": "Trade Payables Turnover Ratio",
        "numerator_desc": "Net Credit Purchases (Materials Consumed + Purchases)",
        "denominator_desc": "Average Trade Payables",
        "unit": "x",
        "is_percentage": False,
        "clause": "Clause 6(L)(vii) of General Instructions to Schedule III",
    },
    {
        "id": 8,
        "key": "net_capital_turnover",
        "name": "Net Capital Turnover Ratio",
        "numerator_desc": "Net Revenue",
        "denominator_desc": "Average Working Capital",
        "unit": "x",
        "is_percentage": False,
        "clause": "Clause 6(L)(viii) of General Instructions to Schedule III",
    },
    {
        "id": 9,
        "key": "net_profit_ratio",
        "name": "Net Profit Ratio",
        "numerator_desc": "Profit After Tax",
        "denominator_desc": "Net Revenue",
        "unit": "%",
        "is_percentage": True,
        "clause": "Clause 6(L)(ix) of General Instructions to Schedule III",
    },
    {
        "id": 10,
        "key": "roce",
        "name": "Return on Capital Employed",
        "numerator_desc": "Earnings Before Interest and Tax (EBIT)",
        "denominator_desc": "Capital Employed (Tangible Net Worth + Total Debt + DTL)",
        "unit": "%",
        "is_percentage": True,
        "clause": "Clause 6(L)(x) of General Instructions to Schedule III",
    },
    {
        "id": 11,
        "key": "roi",
        "name": "Return on Investment",
        "numerator_desc": "Income from Investments",
        "denominator_desc": "Average Total Investments",
        "unit": "%",
        "is_percentage": True,
        "clause": "Clause 6(L)(xi) of General Instructions to Schedule III",
    },
]

# Additional ratios (§6)
ADDITIONAL_RATIOS = [
    {
        "key": "quick_ratio",
        "name": "Quick Ratio",
        "numerator_desc": "Current Assets − Inventories",
        "denominator_desc": "Current Liabilities",
        "unit": "x",
        "is_percentage": False,
    },
    {
        "key": "interest_coverage",
        "name": "Interest Coverage Ratio",
        "numerator_desc": "EBIT",
        "denominator_desc": "Finance Costs",
        "unit": "x",
        "is_percentage": False,
    },
    {
        "key": "return_on_assets",
        "name": "Return on Assets",
        "numerator_desc": "Profit After Tax",
        "denominator_desc": "Average Total Assets",
        "unit": "%",
        "is_percentage": True,
    },
    {
        "key": "ebitda_margin",
        "name": "EBITDA Margin",
        "numerator_desc": "EBITDA (EBIT + Depreciation)",
        "denominator_desc": "Net Revenue",
        "unit": "%",
        "is_percentage": True,
    },
    {
        "key": "inventory_holding_days",
        "name": "Inventory Holding Days",
        "numerator_desc": "Average Inventories × 365",
        "denominator_desc": "Cost of Goods Sold",
        "unit": "days",
        "is_percentage": False,
    },
    {
        "key": "debtor_days",
        "name": "Debtor Days",
        "numerator_desc": "Average Trade Receivables × 365",
        "denominator_desc": "Net Revenue",
        "unit": "days",
        "is_percentage": False,
    },
    {
        "key": "creditor_days",
        "name": "Creditor Days",
        "numerator_desc": "Average Trade Payables × 365",
        "denominator_desc": "Cost of Materials + Purchases",
        "unit": "days",
        "is_percentage": False,
    },
    {
        "key": "cash_conversion_cycle",
        "name": "Cash Conversion Cycle",
        "numerator_desc": "Debtor Days + Inventory Days − Creditor Days",
        "denominator_desc": "N/A",
        "unit": "days",
        "is_percentage": False,
    },
    {
        "key": "fixed_asset_turnover",
        "name": "Fixed Asset Turnover",
        "numerator_desc": "Net Revenue",
        "denominator_desc": "Average Net Fixed Assets (PPE + CWIP)",
        "unit": "x",
        "is_percentage": False,
    },
    {
        "key": "proprietary_ratio",
        "name": "Proprietary Ratio",
        "numerator_desc": "Shareholders' Equity",
        "denominator_desc": "Total Assets",
        "unit": "%",
        "is_percentage": True,
    },
]
