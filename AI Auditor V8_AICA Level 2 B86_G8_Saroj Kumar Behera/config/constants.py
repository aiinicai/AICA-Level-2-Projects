"""
AI Auditor V8 - Configuration & Constants
Standard accounting taxonomy, ratio definitions, threshold defaults, and units.
"""

from typing import Dict, List, Any

APP_NAME = "AI Auditor V8"
APP_VERSION = "8.0.0"
APP_SUBTITLE = "Financial Statement Analysis & Audit Support System"

# Default Analysis Thresholds
DEFAULT_VARIANCE_THRESHOLD = 5.0  # Percentage (5%)
DEFAULT_MATERIALITY_THRESHOLD = 10000.0  # In base currency amount

# Supported Currency Symbols & Multipliers
UNITS_MAP = {
    "₹ (Exact)": 1.0,
    "₹ in Thousands (000s)": 1_000.0,
    "₹ in Lakhs (1,00,000)": 100_000.0,
    "₹ in Millions (10,00,000)": 1_000_000.0,
    "₹ in Crores (1,00,00,000)": 10_000_000.0,
    "$ (Exact)": 1.0,
    "$ in Thousands": 1_000.0,
    "$ in Millions": 1_000_000.0,
    "€ (Exact)": 1.0,
    "£ (Exact)": 1.0,
}

# Standard Financial Statement Categories
STATEMENT_BALANCE_SHEET = "Balance Sheet"
STATEMENT_PROFIT_LOSS = "Profit and Loss"
STATEMENT_CASH_FLOW = "Cash Flow Statement"
STATEMENT_NOTES = "Notes to Accounts"

# Standard Taxonomy Mapping for Balance Sheet
BS_TAXONOMY = {
    # Equity & Liabilities
    "share_capital": {
        "label": "Share Capital / Equity Capital",
        "category": "Equity",
        "synonyms": ["share capital", "equity share capital", "paid up capital", "capital stock", "common stock", "proprietor capital", "partners capital"],
        "is_credit": True
    },
    "reserves_surplus": {
        "label": "Reserves and Surplus / Retained Earnings",
        "category": "Equity",
        "synonyms": ["reserves and surplus", "retained earnings", "other equity", "general reserve", "securities premium", "surplus in p&l", "accumulated profits"],
        "is_credit": True
    },
    "long_term_borrowings": {
        "label": "Long-Term Borrowings / Non-Current Debt",
        "category": "Non-Current Liabilities",
        "synonyms": ["long term borrowings", "long term debt", "term loans", "secured loans", "debentures", "bonds", "non current borrowings", "mortgage loan"],
        "is_credit": True
    },
    "other_non_current_liabilities": {
        "label": "Other Non-Current Liabilities",
        "category": "Non-Current Liabilities",
        "synonyms": ["other non current liabilities", "deferred tax liabilities", "long term provisions", "other long term liabilities"],
        "is_credit": True
    },
    "short_term_borrowings": {
        "label": "Short-Term Borrowings / Current Debt",
        "category": "Current Liabilities",
        "synonyms": ["short term borrowings", "short term loans", "working capital loan", "bank overdraft", "cash credit", "current borrowings", "cc / od limit", "cash credit / overdraft"],
        "is_credit": True
    },
    "trade_payables": {
        "label": "Trade Payables / Creditors",
        "category": "Current Liabilities",
        "synonyms": ["trade payables", "sundry creditors", "accounts payable", "bills payable", "creditors for goods", "trade creditors"],
        "is_credit": True
    },
    "other_current_liabilities": {
        "label": "Other Current Liabilities & Provisions",
        "category": "Current Liabilities",
        "synonyms": ["other current liabilities", "short term provisions", "statutory dues payable", "expenses payable", "advances from customers", "outstanding liabilities", "current liabilities"],
        "is_credit": True
    },
    
    # Assets
    "property_plant_equipment": {
        "label": "Property, Plant & Equipment / Tangible Assets",
        "category": "Non-Current Assets",
        "synonyms": ["property, plant and equipment", "tangible assets", "fixed assets", "gross block", "net block", "plant and machinery", "land and building", "ppe", "property plant and equipment"],
        "is_credit": False
    },
    "capital_work_in_progress": {
        "label": "Capital Work-in-Progress (CWIP)",
        "category": "Non-Current Assets",
        "synonyms": ["capital work in progress", "cwip", "capital wip", "assets under construction"],
        "is_credit": False
    },
    "intangible_assets": {
        "label": "Intangible Assets & Goodwill",
        "category": "Non-Current Assets",
        "synonyms": ["intangible assets", "goodwill", "software", "patents", "trademarks", "intellectual property"],
        "is_credit": False
    },
    "non_current_investments": {
        "label": "Non-Current Investments",
        "category": "Non-Current Assets",
        "synonyms": ["non current investments", "long term investments", "investments in subsidiaries", "quoted investments", "unquoted investments"],
        "is_credit": False
    },
    "other_non_current_assets": {
        "label": "Other Non-Current Assets",
        "category": "Non-Current Assets",
        "synonyms": ["other non current assets", "long term loans and advances", "deferred tax assets", "security deposits", "long term receivables"],
        "is_credit": False
    },
    "inventories": {
        "label": "Inventories / Stock-in-Trade",
        "category": "Current Assets",
        "synonyms": ["inventories", "inventory", "stock in trade", "raw materials", "finished goods", "work in progress", "stores and spares", "closing stock"],
        "is_credit": False
    },
    "trade_receivables": {
        "label": "Trade Receivables / Debtors",
        "category": "Current Assets",
        "synonyms": ["trade receivables", "sundry debtors", "accounts receivable", "bills receivable", "book debts", "debtors"],
        "is_credit": False
    },
    "cash_and_bank": {
        "label": "Cash and Bank Balances",
        "category": "Current Assets",
        "synonyms": ["cash and cash equivalents", "cash and bank balances", "bank balance", "cash on hand", "balances with banks", "fixed deposits", "current accounts"],
        "is_credit": False
    },
    "short_term_investments": {
        "label": "Short-Term Investments / Marketable Securities",
        "category": "Current Assets",
        "synonyms": ["current investments", "short term investments", "marketable securities", "mutual funds current"],
        "is_credit": False
    },
    "other_current_assets": {
        "label": "Other Current Assets & Advances",
        "category": "Current Assets",
        "synonyms": ["other current assets", "short term loans and advances", "prepaid expenses", "gst input tax credit", "advance tax", "tds receivable", "other receivables", "current assets"],
        "is_credit": False
    }
}

# Standard Taxonomy Mapping for Profit and Loss
PL_TAXONOMY = {
    "revenue_operations": {
        "label": "Revenue from Operations / Gross Sales",
        "category": "Revenue",
        "synonyms": ["revenue from operations", "sales", "gross sales", "turnover", "net sales", "operating income", "revenue", "income from services"],
        "is_income": True
    },
    "other_income": {
        "label": "Other Income / Non-Operating Income",
        "category": "Revenue",
        "synonyms": ["other income", "non operating income", "interest income", "dividend income", "profit on sale of assets", "miscellaneous income", "foreign exchange gain"],
        "is_income": True
    },
    "cost_materials_consumed": {
        "label": "Cost of Materials Consumed / Direct Purchases",
        "category": "Expenses",
        "synonyms": ["cost of materials consumed", "raw materials consumed", "purchases of stock in trade", "cost of goods sold", "cogs", "direct purchases", "consumption of raw materials", "purchases"],
        "is_income": False
    },
    "change_in_inventories": {
        "label": "Changes in Inventories (WIP, FG, Stock)",
        "category": "Expenses",
        "synonyms": ["changes in inventories", "increase/decrease in stocks", "change in finished goods", "inventory adjustment"],
        "is_income": False
    },
    "employee_benefits": {
        "label": "Employee Benefits Expense / Salaries & Wages",
        "category": "Expenses",
        "synonyms": ["employee benefit expenses", "employee benefits", "salaries and wages", "staff welfare", "payroll costs", "salaries", "remuneration to directors", "wages"],
        "is_income": False
    },
    "finance_costs": {
        "label": "Finance Costs / Interest Expense",
        "category": "Expenses",
        "synonyms": ["finance costs", "interest expense", "interest and bank charges", "borrowing costs", "bank financial charges", "interest on term loan", "finance cost"],
        "is_income": False
    },
    "depreciation_amortisation": {
        "label": "Depreciation and Amortisation Expense",
        "category": "Expenses",
        "synonyms": ["depreciation and amortisation", "depreciation", "amortisation", "depreciation expense", "depreciation & amortisation"],
        "is_income": False
    },
    "power_fuel": {
        "label": "Power and Fuel / Utility Expenses",
        "category": "Expenses",
        "synonyms": ["power and fuel", "electricity charges", "utility expenses", "fuel charges"],
        "is_income": False
    },
    "freight_transport": {
        "label": "Freight and Transportation / Selling Expenses",
        "category": "Expenses",
        "synonyms": ["freight outward", "carriage outwards", "freight and forwarding", "transportation charges", "selling and distribution expenses"],
        "is_income": False
    },
    "other_expenses": {
        "label": "Other Operating & Administrative Expenses",
        "category": "Expenses",
        "synonyms": ["other expenses", "administrative expenses", "rent, rates and taxes", "repairs and maintenance", "legal and professional fees", "audit fees", "miscellaneous expenses", "general expenses", "operating expenses"],
        "is_income": False
    },
    "profit_before_tax": {
        "label": "Profit / (Loss) Before Tax (PBT)",
        "category": "Profitability",
        "synonyms": ["profit before tax", "pbt", "profit / (loss) before tax and exceptional items", "earnings before tax"],
        "is_income": True
    },
    "tax_expense": {
        "label": "Tax Expense (Current & Deferred)",
        "category": "Tax",
        "synonyms": ["tax expense", "current tax", "provision for tax", "deferred tax", "income tax"],
        "is_income": False
    },
    "profit_after_tax": {
        "label": "Profit / (Loss) After Tax (PAT)",
        "category": "Profitability",
        "synonyms": ["profit for the period", "profit after tax", "pat", "net profit", "net income", "profit / (loss) for the year"],
        "is_income": True
    }
}

# Standard Taxonomy Mapping for Cash Flow Statement
CF_TAXONOMY = {
    "cf_operations": {
        "label": "Net Cash Flow from Operating Activities",
        "category": "Cash Flow",
        "synonyms": ["cash flow from operating activities", "operating cash flow", "cash generated from operations", "cfo", "net cash from operations"]
    },
    "cf_investing": {
        "label": "Net Cash Flow from / (used in) Investing Activities",
        "category": "Cash Flow",
        "synonyms": ["cash flow from investing activities", "investing cash flow", "net cash used in investing activities", "cfi"]
    },
    "cf_financing": {
        "label": "Net Cash Flow from / (used in) Financing Activities",
        "category": "Cash Flow",
        "synonyms": ["cash flow from financing activities", "financing cash flow", "net cash from financing activities", "cff"]
    },
    "net_change_cash": {
        "label": "Net Increase / (Decrease) in Cash & Cash Equivalents",
        "category": "Cash Flow",
        "synonyms": ["net increase in cash and cash equivalents", "net change in cash", "net increase / decrease in cash"]
    },
    "opening_cash": {
        "label": "Cash & Cash Equivalents at Beginning of Period",
        "category": "Cash Flow",
        "synonyms": ["cash and cash equivalents at the beginning", "opening cash and cash equivalents", "opening balance of cash"]
    },
    "closing_cash": {
        "label": "Cash & Cash Equivalents at End of Period",
        "category": "Cash Flow",
        "synonyms": ["cash and cash equivalents at the end", "closing cash and cash equivalents", "closing balance of cash"]
    }
}

DISCLAIMER_TEXT = (
    "DISCLAIMER & LIMITATIONS: This analytical report is generated by AI Auditor V8 based strictly "
    "upon financial figures uploaded by the user and mathematical / financial calculations. All identified "
    "variations, interpretations, possible reasons, and suggested audit verification requirements are "
    "designed to assist in professional audit planning, credit appraisal, and financial review. They do NOT "
    "constitute a conclusive audit opinion, proof of fraud, or legal finding. Independent verification "
    "of physical records, primary vouchers, bank statements, and statutory filings by a qualified Chartered "
    "Accountant or auditor is mandatory."
)
