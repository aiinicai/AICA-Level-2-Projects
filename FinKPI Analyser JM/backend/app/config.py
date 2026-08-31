import os

class Config:
    APP_NAME         = "FinKPI Analyzer"
    APP_VERSION      = "1.0.0"
    DATABASE_URL     = os.getenv("DATABASE_URL", "sqlite:///./finkpi.db")
    SECRET_KEY       = os.getenv("SECRET_KEY", "finkpi-secret-key-2024-change-in-production")
    ALGORITHM        = "HS256"
    TOKEN_EXPIRE_MIN = 1440  # 24 hours

    DEMO_USER        = "admin"
    DEMO_PASSWORD    = "admin123"

    REQUIRED_SHEETS = [
        "TB_Q1_FY2023", "TB_Q2_FY2023", "TB_Q3_FY2023", "TB_Q4_FY2023", "TB_Annual_FY2023",
        "TB_Q1_FY2024", "TB_Q2_FY2024", "TB_Q3_FY2024", "TB_Q4_FY2024", "TB_Annual_FY2024"
    ]

    SHEET_MAP = {
        "TB_Q1_FY2023":     {"period_id": "P01", "label": "Q1 FY2023",     "quarter": "Q1",     "year": "FY2023", "sequence": 1},
        "TB_Q2_FY2023":     {"period_id": "P02", "label": "Q2 FY2023",     "quarter": "Q2",     "year": "FY2023", "sequence": 2},
        "TB_Q3_FY2023":     {"period_id": "P03", "label": "Q3 FY2023",     "quarter": "Q3",     "year": "FY2023", "sequence": 3},
        "TB_Q4_FY2023":     {"period_id": "P04", "label": "Q4 FY2023",     "quarter": "Q4",     "year": "FY2023", "sequence": 4},
        "TB_Annual_FY2023": {"period_id": "P05", "label": "Annual FY2023", "quarter": "Annual", "year": "FY2023", "sequence": 0},
        "TB_Q1_FY2024":     {"period_id": "P06", "label": "Q1 FY2024",     "quarter": "Q1",     "year": "FY2024", "sequence": 5},
        "TB_Q2_FY2024":     {"period_id": "P07", "label": "Q2 FY2024",     "quarter": "Q2",     "year": "FY2024", "sequence": 6},
        "TB_Q3_FY2024":     {"period_id": "P08", "label": "Q3 FY2024",     "quarter": "Q3",     "year": "FY2024", "sequence": 7},
        "TB_Q4_FY2024":     {"period_id": "P09", "label": "Q4 FY2024",     "quarter": "Q4",     "year": "FY2024", "sequence": 8},
        "TB_Annual_FY2024": {"period_id": "P10", "label": "Annual FY2024", "quarter": "Annual", "year": "FY2024", "sequence": 0},
    }

    PERIOD_ORDER = ["Q1FY23", "Q2FY23", "Q3FY23", "Q4FY23", "AnnualFY23", "Q1FY24", "Q2FY24", "Q3FY24", "Q4FY24", "AnnualFY24"]
    QUARTER_ORDER_8Q = ["Q1FY23", "Q2FY23", "Q3FY23", "Q4FY23", "Q1FY24", "Q2FY24", "Q3FY24", "Q4FY24"]

    BENCHMARKS = {
        # Profitability
        "gross_profit_margin"  : 35.0,
        "net_profit_margin"    : 12.0,
        "operating_margin"     : 15.0,
        "ebitda_margin"        : 20.0,
        "roa"                  : 8.0,
        "roe"                  : 15.0,
        "roce"                 : 12.0,
        "cost_to_income_ratio" : 60.0,
        "cogs_ratio"           : 65.0,

        # Liquidity
        "current_ratio"        : 1.5,
        "quick_ratio"          : 1.0,
        "cash_ratio"           : 0.5,
        "net_working_capital"  : 1000.0,
        "nwc_ratio"            : 15.0,
        "operating_cf_ratio"   : 0.5,

        # Solvency
        "debt_to_equity"       : 1.0,
        "debt_to_assets"       : 0.5,
        "net_debt"             : 5000.0,
        "net_debt_to_ebitda"   : 2.5,
        "interest_coverage"    : 3.0,
        "debt_service_coverage": 1.5,
        "equity_multiplier"    : 2.0,
        "financial_leverage"   : 2.0,

        # Efficiency
        "asset_turnover"       : 0.8,
        "fixed_asset_turnover" : 2.0,
        "inventory_turnover"   : 4.0,
        "receivables_turnover" : 6.0,
        "payables_turnover"    : 5.0,
        "dso"                  : 60.0,
        "dio"                  : 90.0,
        "dpo"                  : 70.0,
        "ccc"                  : 80.0,
        "revenue_per_employee" : 250.0,

        # Growth
        "revenue_growth"       : 10.0,
        "gross_profit_growth"  : 10.0,
        "ebitda_growth"        : 10.0,
        "ebit_growth"          : 10.0,
        "net_income_growth"    : 10.0,
        "total_assets_growth"  : 8.0,
        "equity_growth"        : 10.0,
        "operating_cf_growth"  : 10.0,

        # Valuation
        "eps"                  : 5.0,
        "book_value_per_share" : 25.0,
        "diluted_eps"          : 5.0
    }

config = Config()
