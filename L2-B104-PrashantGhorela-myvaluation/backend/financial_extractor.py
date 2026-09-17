from pathlib import Path
from typing import Dict, List, Any, Optional
from difflib import SequenceMatcher
from datetime import datetime, date

import pandas as pd
import re
import math


EXTRACTOR_VERSION = "2.3"


# =========================================================
# DOCUMENT CATEGORIES
# =========================================================

DOCUMENT_CATEGORY_RULES = [
    ("provisional", [
        "01_provisional_financials",
        "provisional",
    ]),
    ("historical", [
        "02_historical_financials",
        "historical",
        "audited",
    ]),
    ("projections", [
        "03_projections",
        "projection",
        "projected",
        "forecast",
    ]),
    ("capital_structure", [
        "04_capital_structure",
        "fully_diluted",
        "capital_structure",
        "cap_table",
    ]),
    ("debt_schedule", [
        "05_debt_schedule",
        "debt_schedule",
        "borrowings_schedule",
    ]),
    ("company_profile", [
        "06_company_profile",
        "company_profile",
    ]),
    ("shareholding", [
        "shareholding",
    ]),
]


SOURCE_PRIORITY = {
    "profit_and_loss": 100,
    "balance_sheet": 100,
    "cash_flow": 100,
    "projected_profit_and_loss": 100,
    "projected_balance_sheet": 100,
    "projected_cash_flow": 100,
    "notes": 50,
    "debt_schedule": 80,
    "capital_structure": 80,
    "shareholding": 80,
    "unknown": 20,
    "cover": 0,
}


# =========================================================
# CANONICAL FIELDS
# =========================================================

CANONICAL_FIELDS = {

    # P&L
    "revenue_from_operations": {
        "statement": "income_statement",
        "aliases": [
            "revenue from operations",
            "net revenue from operations",
            "operating revenue",
            "revenue from contracts",
            "sales revenue",
            "net sales",
            "turnover",
            "sales",
        ],
    },

    "other_operating_income": {
        "statement": "income_statement",
        "aliases": [
            "other operating income",
            "other operating revenue",
        ],
    },

    "other_income": {
        "statement": "income_statement",
        "aliases": [
            "other income",
            "non operating income",
            "non-operating income",
        ],
    },

    "total_income": {
        "statement": "income_statement",
        "aliases": [
            "total income",
            "total revenue",
        ],
    },

    "cost_of_materials": {
        "statement": "income_statement",
        "aliases": [
            "cost of materials consumed",
            "cost of raw materials consumed",
            "raw material consumed",
            "raw materials consumed",
            "material cost",
            "cost of materials",
            "material cost cost of materials consumed net of change in inventories",
            "material cost cost of materials consumed net of changes in inventories",
        ],
    },

    "purchase_of_stock_in_trade": {
        "statement": "income_statement",
        "aliases": [
            "purchase of stock in trade",
            "purchases of stock in trade",
            "purchases of stock-in-trade",
            "purchase of traded goods",
        ],
    },

    "change_in_inventory": {
        "statement": "income_statement",
        "aliases": [
            "changes in inventories",
            "change in inventories",
            "changes in inventories of finished goods and work in progress",
            "changes in inventories of finished goods and work-in-progress",
            "increase decrease in inventories",
            "increase / decrease in inventories",
        ],
    },

    "employee_cost": {
        "statement": "income_statement",
        "aliases": [
            "employee benefits expense",
            "employee benefit expense",
            "employee cost",
            "staff cost",
            "personnel cost",
        ],
    },

    "finance_cost": {
        "statement": "income_statement",
        "aliases": [
            "finance costs",
            "finance cost",
            "interest expense",
            "interest cost",
            "borrowing cost",
        ],
    },

    "depreciation_amortisation": {
        "statement": "income_statement",
        "aliases": [
            "depreciation and amortisation expense",
            "depreciation and amortization expense",
            "depreciation and amortisation",
            "depreciation and amortization",
            "depreciation & amortisation",
            "depreciation & amortization",
        ],
    },

    "other_operating_expenses": {
        "statement": "income_statement",
        "aliases": [
            "other expenses",
            "other operating expenses",
            "operating expenses",
        ],
    },

    "total_expenses": {
        "statement": "income_statement",
        "aliases": [
            "total expenses",
        ],
    },

    "ebitda": {
        "statement": "income_statement",
        "aliases": [
            "ebitda",
            "earnings before interest tax depreciation and amortisation",
            "earnings before interest tax depreciation and amortization",
            "operating profit before depreciation",
        ],
    },

    "ebit": {
        "statement": "income_statement",
        "aliases": [
            "ebit",
            "earnings before interest and tax",
            "profit before interest and tax",
        ],
    },

    "exceptional_items": {
        "statement": "income_statement",
        "aliases": [
            "exceptional items",
            "exceptional item",
        ],
    },

    "pbt": {
        "statement": "income_statement",
        "aliases": [
            "profit before tax",
            "profit before taxation",
            "profit before income tax",
            "pbt",
        ],
    },

    "current_tax": {
        "statement": "income_statement",
        "aliases": [
            "current tax",
            "current income tax",
        ],
    },

    "deferred_tax": {
        "statement": "income_statement",
        "aliases": [
            "deferred tax",
            "deferred tax expense",
            "deferred tax charge",
        ],
    },

    "tax_expense": {
        "statement": "income_statement",
        "aliases": [
            "total tax expense",
            "tax expense",
            "income tax expense",
            "taxation",
        ],
    },

    "pat": {
        "statement": "income_statement",
        "aliases": [
            "profit after tax",
            "profit after taxation",
            "profit for the year",
            "profit for the period",
            "net profit after tax",
            "net profit",
            "pat",
        ],
    },

    # EQUITY
    "equity_share_capital": {
        "statement": "balance_sheet",
        "aliases": [
            "equity share capital",
            "paid up equity share capital",
            "paid-up equity share capital",
        ],
    },

    "preference_share_capital": {
        "statement": "balance_sheet",
        "aliases": [
            "preference share capital",
            "preference share capital ccps",
            "compulsorily convertible preference share capital",
            "ccps capital",
        ],
    },

    "total_share_capital": {
        "statement": "balance_sheet",
        "aliases": [
            "total share capital",
            "share capital",
        ],
    },

    "other_equity": {
        "statement": "balance_sheet",
        "aliases": [
            "other equity",
            "reserves and surplus",
            "reserves & surplus",
            "total reserves and surplus",
        ],
    },

    "net_worth": {
        "statement": "balance_sheet",
        "aliases": [
            "net worth",
            "total shareholders funds",
            "total shareholders' funds",
            "shareholders funds",
            "shareholders' funds",
            "total equity",
        ],
    },

    # BORROWINGS
    "long_term_borrowings": {
        "statement": "balance_sheet",
        "aliases": [
            "long term borrowings",
            "long-term borrowings",
            "non current borrowings",
            "non-current borrowings",
            "long term debt",
            "term borrowings",
            "term borrowings including current maturities",
            "term loans including current maturities",
            "term loans",
        ],
    },

    "short_term_borrowings": {
        "statement": "balance_sheet",
        "aliases": [
            "short term borrowings",
            "short-term borrowings",
            "current borrowings",
            "short term borrowings cash credit",
            "short-term borrowings cash credit",
            "working capital borrowings",
            "working capital loan",
            "working capital loans",
            "cash credit borrowings",
        ],
    },

    # LIABILITIES
    "deferred_tax_liability": {
        "statement": "balance_sheet",
        "aliases": [
            "deferred tax liabilities",
            "deferred tax liability",
            "deferred tax liabilities net",
        ],
    },

    "long_term_provisions": {
        "statement": "balance_sheet",
        "aliases": [
            "long term provisions",
            "long-term provisions",
        ],
    },

    "non_current_liabilities": {
        "statement": "balance_sheet",
        "aliases": [
            "total non current liabilities",
            "total non-current liabilities",
            "non current liabilities",
            "non-current liabilities",
        ],
    },

    "trade_payables": {
        "statement": "balance_sheet",
        "aliases": [
            "trade payables",
            "accounts payable",
        ],
    },

    "other_current_liabilities": {
        "statement": "balance_sheet",
        "aliases": [
            "other current liabilities",
            "other current liabilities excluding current maturities",
            "other current liabilities excluding current maturity",
        ],
    },

    "short_term_provisions": {
        "statement": "balance_sheet",
        "aliases": [
            "short term provisions",
            "short-term provisions",
        ],
    },

    "current_liabilities": {
        "statement": "balance_sheet",
        "aliases": [
            "total current liabilities",
            "current liabilities",
        ],
    },

    "total_equity_liabilities": {
        "statement": "balance_sheet",
        "aliases": [
            "total equity and liabilities",
            "total liabilities and equity",
        ],
    },

    # ASSETS
    "property_plant_equipment": {
        "statement": "balance_sheet",
        "aliases": [
            "property plant and equipment",
            "property, plant and equipment",
            "ppe",
            "tangible fixed assets",
        ],
    },

    "capital_work_in_progress": {
        "statement": "balance_sheet",
        "aliases": [
            "capital work in progress",
            "capital work-in-progress",
            "cwip",
        ],
    },

    "intangible_assets": {
        "statement": "balance_sheet",
        "aliases": [
            "intangible assets",
            "intangible asset",
        ],
    },

    "goodwill": {
        "statement": "balance_sheet",
        "aliases": [
            "goodwill",
        ],
    },

    "non_current_investments": {
        "statement": "balance_sheet",
        "aliases": [
            "non current investments",
            "non-current investments",
        ],
    },

    "long_term_loans_advances": {
        "statement": "balance_sheet",
        "aliases": [
            "long term loans and advances",
            "long-term loans and advances",
        ],
    },

    "other_non_current_assets": {
        "statement": "balance_sheet",
        "aliases": [
            "other non current assets",
            "other non-current assets",
        ],
    },

    "non_current_assets": {
        "statement": "balance_sheet",
        "aliases": [
            "total non current assets",
            "total non-current assets",
            "non current assets",
            "non-current assets",
        ],
    },

    "inventory": {
        "statement": "balance_sheet",
        "aliases": [
            "inventories",
            "inventory",
        ],
    },

    "trade_receivables": {
        "statement": "balance_sheet",
        "aliases": [
            "trade receivables",
            "accounts receivable",
        ],
    },

    "cash_and_equivalents": {
        "statement": "balance_sheet",
        "aliases": [
            "cash and cash equivalents",
            "cash & cash equivalents",
            "cash and bank balances",
            "cash and bank balance",
        ],
    },

    "short_term_loans_advances": {
        "statement": "balance_sheet",
        "aliases": [
            "short term loans and advances",
            "short-term loans and advances",
        ],
    },

    "other_current_assets": {
        "statement": "balance_sheet",
        "aliases": [
            "other current assets",
        ],
    },

    "current_assets": {
        "statement": "balance_sheet",
        "aliases": [
            "total current assets",
            "current assets",
        ],
    },

    "total_assets": {
        "statement": "balance_sheet",
        "aliases": [
            "total assets",
        ],
    },

    # CASH FLOW
    "cash_flow_from_operations": {
        "statement": "cash_flow",
        "aliases": [
            "net cash from operating activities",
            "net cash generated from operating activities",
            "cash generated from operations",
            "cash flow from operating activities",
        ],
    },

    "cash_flow_from_investing": {
        "statement": "cash_flow",
        "aliases": [
            "net cash used in investing activities",
            "net cash from investing activities",
            "cash flow from investing activities",
        ],
    },

    "cash_flow_from_financing": {
        "statement": "cash_flow",
        "aliases": [
            "net cash used in financing activities",
            "net cash from financing activities",
            "cash flow from financing activities",
            "net cash from used in financing activities",
        ],
    },

    "capital_expenditure": {
        "statement": "cash_flow",
        "aliases": [
            "capital expenditure",
            "cash capital expenditure",
            "capex",
            "purchase of property plant and equipment",
            "purchase of property, plant and equipment",
            "purchase of fixed assets",
        ],
    },

    "opening_cash": {
        "statement": "cash_flow",
        "aliases": [
            "cash and bank balances at the beginning of the period",
            "cash and cash equivalents at beginning of year",
            "opening cash balance",
        ],
    },

    "closing_cash": {
        "statement": "cash_flow",
        "aliases": [
            "cash and bank balances at the end of the period",
            "cash and cash equivalents at end of year",
            "closing cash balance",
        ],
    },
}


BLOCKED_LABEL_PATTERNS = [
    r"^total$",
    r"^subtotal$",
    r"^check\b",
    r"should be nil",
    r"earnings per equity share",
    r"basic earnings per",
    r"diluted earnings per",
    r"ebitda margin",
    r"pat margin",
    r"net profit margin",
    r"revenue growth",
    r"debt.?to.?equity",
    r"interest coverage",
    r"number of equity shares",
    r"face value per equity share",
    r"number of .* preference shares",
    r"face value per .*ccps",
]


def normalize_text(value: Any) -> str:

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    text = str(value)
    text = text.replace("\n", " ")
    text = text.replace("\r", " ")
    text = text.replace("&", " and ")
    text = text.strip().lower()
    text = re.sub(r"[,:;]+", " ", text)
    text = re.sub(r"[^a-z0-9%()./\- ]+", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def strip_prefixes(text: str) -> str:

    text = normalize_text(text)

    for prefix in [
        "less:",
        "add:",
        "less ",
        "add ",
    ]:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()

    return text


def clean_number(value: Any) -> Optional[float]:

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    if isinstance(value, (int, float)):

        if (
            isinstance(value, float)
            and math.isnan(value)
        ):
            return None

        return float(value)

    text = str(value).strip()

    if not text:
        return None

    if text.lower() in {
        "na",
        "n/a",
        "nil",
        "-",
        "--",
    }:
        return 0.0

    negative = (
        text.startswith("(")
        and text.endswith(")")
    )

    text = text.replace(",", "")
    text = text.replace("₹", "")
    text = re.sub(
        r"\brs\.?\b",
        "",
        text,
        flags=re.IGNORECASE
    )
    text = re.sub(
        r"\binr\b",
        "",
        text,
        flags=re.IGNORECASE
    )
    text = text.replace("%", "")
    text = text.replace("(", "")
    text = text.replace(")", "")
    text = text.strip()

    try:

        value = float(text)

        if negative:
            value = -value

        return value

    except Exception:
        return None


def detect_document_category(
    file_path: Path
) -> str:

    text = normalize_text(
        str(file_path)
    ).replace(" ", "_")

    for category, keywords in (
        DOCUMENT_CATEGORY_RULES
    ):

        for keyword in keywords:

            if keyword in text:
                return category

    return "other"


def get_sheet_text(
    dataframe: pd.DataFrame,
    max_rows: int = 60,
    max_cols: int = 20,
) -> str:

    values = []

    for row_index in range(
        min(len(dataframe), max_rows)
    ):

        for col_index in range(
            min(
                len(dataframe.columns),
                max_cols
            )
        ):

            text = normalize_text(
                dataframe.iloc[
                    row_index,
                    col_index
                ]
            )

            if text:
                values.append(text)

    return " ".join(values)


def extract_stub_period_from_text(
    text: str
) -> Optional[Dict]:

    normalized = normalize_text(text)

    month_pattern = (
        r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|"
        r"may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|"
        r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    )

    pattern = (
        r"(\d{1,2})\s+"
        + month_pattern
        + r"\s+(20\d{2})\s+(?:to|until|through|-)\s+"
        + r"(\d{1,2})\s+"
        + month_pattern
        + r"\s+(20\d{2})"
    )

    match = re.search(
        pattern,
        normalized
    )

    if not match:
        return None

    month_map = {
        "jan": 1, "january": 1,
        "feb": 2, "february": 2,
        "mar": 3, "march": 3,
        "apr": 4, "april": 4,
        "may": 5,
        "jun": 6, "june": 6,
        "jul": 7, "july": 7,
        "aug": 8, "august": 8,
        "sep": 9, "september": 9,
        "oct": 10, "october": 10,
        "nov": 11, "november": 11,
        "dec": 12, "december": 12,
    }

    start_date = date(
        int(match.group(3)),
        month_map[
            match.group(2)
        ],
        int(match.group(1)),
    )

    end_date = date(
        int(match.group(6)),
        month_map[
            match.group(5)
        ],
        int(match.group(4)),
    )

    return {
        "key":
            f"STUB_{start_date.isoformat()}_{end_date.isoformat()}",

        "display":
            f"{start_date.strftime('%d-%b-%Y')} to "
            f"{end_date.strftime('%d-%b-%Y')}",

        "kind":
            "stub_period",

        "start_date":
            start_date.isoformat(),

        "end_date":
            end_date.isoformat(),

        "sort_key":
            end_date.strftime("%Y%m%d"),
    }


def detect_workbook_context(
    excel: pd.ExcelFile,
    file_path: Path,
) -> Dict:

    context = {
        "stub_period": None
    }

    if (
        detect_document_category(file_path)
        != "provisional"
    ):
        return context

    for sheet_name in excel.sheet_names:

        name = normalize_text(
            sheet_name
        )

        if not (
            "cover" in name
            or "profit" in name
            or "cash flow" in name
        ):
            continue

        try:

            dataframe = pd.read_excel(
                file_path,
                sheet_name=sheet_name,
                header=None,
                dtype=object,
            )

            stub = (
                extract_stub_period_from_text(
                    get_sheet_text(
                        dataframe,
                        max_rows=20,
                        max_cols=10,
                    )
                )
            )

            if stub:

                context[
                    "stub_period"
                ] = stub

                return context

        except Exception:
            pass

    return context


def classify_sheet(
    sheet_name: str,
    document_category: str,
    dataframe: pd.DataFrame,
) -> Dict:

    name = normalize_text(
        sheet_name
    )

    if document_category == "capital_structure":
        return {
            "type": "capital_structure",
            "confidence": 100,
        }

    if document_category == "debt_schedule":
        return {
            "type": "debt_schedule",
            "confidence": 100,
        }

    if document_category == "shareholding":
        return {
            "type": "shareholding",
            "confidence": 100,
        }

    if document_category == "company_profile":
        return {
            "type": "company_profile",
            "confidence": 100,
        }

    if "cover" in name:
        return {
            "type": "cover",
            "confidence": 100,
        }

    if (
        "profit and loss" in name
        or "profit & loss" in name
        or name == "p&l"
        or "income statement" in name
    ):

        return {
            "type":
                (
                    "projected_profit_and_loss"
                    if document_category
                    == "projections"
                    else "profit_and_loss"
                ),
            "confidence": 100,
        }

    if (
        "balance sheet" in name
        or "financial position" in name
    ):

        return {
            "type":
                (
                    "projected_balance_sheet"
                    if document_category
                    == "projections"
                    else "balance_sheet"
                ),
            "confidence": 100,
        }

    if "cash flow" in name:

        return {
            "type":
                (
                    "projected_cash_flow"
                    if document_category
                    == "projections"
                    else "cash_flow"
                ),
            "confidence": 100,
        }

    if (
        name == "notes"
        or "notes to accounts" in name
        or "notes to financial" in name
    ):

        return {
            "type": "notes",
            "confidence": 100,
        }

    if (
        document_category
        == "projections"
    ):

        if "debt" in name:

            return {
                "type": "debt_schedule",
                "confidence": 100,
            }

        if "working capital" in name:

            return {
                "type": "working_capital_schedule",
                "confidence": 100,
            }

        if (
            "fixed asset" in name
            or "capex" in name
        ):

            return {
                "type": "fixed_asset_schedule",
                "confidence": 100,
            }

        if "assumption" in name:

            return {
                "type": "assumptions",
                "confidence": 100,
            }

        if "stub" in name:

            return {
                "type": "stub_schedule",
                "confidence": 100,
            }

    preview = get_sheet_text(
        dataframe,
        max_rows=50,
        max_cols=15,
    )

    scores = {
        "profit_and_loss": 0,
        "balance_sheet": 0,
        "cash_flow": 0,
    }

    for keyword in [
        "revenue from operations",
        "employee benefits expense",
        "finance costs",
        "profit before tax",
        "profit for the year",
        "profit for the period",
    ]:
        if keyword in preview:
            scores[
                "profit_and_loss"
            ] += 1

    for keyword in [
        "property plant and equipment",
        "trade receivables",
        "trade payables",
        "share capital",
        "current assets",
        "current liabilities",
        "total assets",
    ]:
        if keyword in preview:
            scores[
                "balance_sheet"
            ] += 1

    for keyword in [
        "operating activities",
        "investing activities",
        "financing activities",
        "cash generated from operations",
        "net cash",
    ]:
        if keyword in preview:
            scores[
                "cash_flow"
            ] += 1

    best_type = max(
        scores,
        key=scores.get
    )

    best_score = (
        scores[
            best_type
        ]
    )

    if best_score == 0:

        return {
            "type": "unknown",
            "confidence": 0,
        }

    if (
        document_category
        == "projections"
    ):

        best_type = {
            "profit_and_loss":
                "projected_profit_and_loss",

            "balance_sheet":
                "projected_balance_sheet",

            "cash_flow":
                "projected_cash_flow",
        }[
            best_type
        ]

    return {
        "type":
            best_type,

        "confidence":
            min(
                85,
                40
                +
                best_score * 8
            ),
    }


def detect_period_label(
    value: Any
) -> Optional[Dict]:

    if value is None:
        return None

    if isinstance(
        value,
        (
            pd.Timestamp,
            datetime,
            date,
        )
    ):

        dt = pd.Timestamp(
            value
        )

        return {
            "key":
                dt.strftime(
                    "%Y-%m-%d"
                ),

            "display":
                dt.strftime(
                    "%d-%b-%Y"
                ),

            "kind":
                "date",

            "sort_key":
                dt.strftime(
                    "%Y%m%d"
                ),
        }

    if isinstance(
        value,
        (int, float)
    ):
        return None

    text = normalize_text(
        value
    )

    if not text:
        return None

    match = re.search(
        r"\bfy\s*(20\d{2})\s*[-/]\s*(\d{2,4})\b",
        text,
    )

    if match:

        start_year = int(
            match.group(1)
        )

        end_part = (
            match.group(2)
        )

        if len(end_part) == 2:

            end_year = (
                start_year // 100
            ) * 100 + int(
                end_part
            )

        else:

            end_year = int(
                end_part
            )

        return {
            "key":
                f"FY{end_year}",

            "display":
                f"FY {start_year}-{str(end_year)[-2:]}",

            "kind":
                "financial_year",

            "sort_key":
                f"{end_year}0331",
        }

    match = re.search(
        r"\bfy\s*(\d{2})\s*[-/]\s*(\d{2})\b",
        text,
    )

    if match:

        start_year = (
            2000 +
            int(
                match.group(1)
            )
        )

        end_year = (
            2000 +
            int(
                match.group(2)
            )
        )

        return {
            "key":
                f"FY{end_year}",

            "display":
                f"FY {start_year}-{str(end_year)[-2:]}",

            "kind":
                "financial_year",

            "sort_key":
                f"{end_year}0331",
        }

    match = re.search(
        r"(?:year ended|as at|ended)\s+"
        r"(\d{1,2})\s+"
        r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
        r"[a-z]*\s+(20\d{2})",
        text,
    )

    if match:

        month_map = {
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "may": 5,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        }

        day = int(
            match.group(1)
        )

        month = (
            month_map[
                match.group(2)
            ]
        )

        year = int(
            match.group(3)
        )

        dt = date(
            year,
            month,
            day
        )

        if (
            day == 31
            and month == 3
        ):

            return {
                "key":
                    f"FY{year}",

                "display":
                    f"FY {year - 1}-{str(year)[-2:]}",

                "kind":
                    "financial_year",

                "sort_key":
                    f"{year}0331",
            }

        return {
            "key":
                dt.isoformat(),

            "display":
                dt.strftime(
                    "%d-%b-%Y"
                ),

            "kind":
                "date",

            "sort_key":
                dt.strftime(
                    "%Y%m%d"
                ),
        }

    match = re.search(
        r"\b(\d{1,2})[-/ ]"
        r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
        r"[a-z]*[-/ ](20\d{2})\b",
        text,
    )

    if match:

        month_map = {
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "may": 5,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        }

        day = int(
            match.group(1)
        )

        month = (
            month_map[
                match.group(2)
            ]
        )

        year = int(
            match.group(3)
        )

        dt = date(
            year,
            month,
            day
        )

        if (
            day == 31
            and month == 3
        ):

            return {
                "key":
                    f"FY{year}",

                "display":
                    f"FY {year - 1}-{str(year)[-2:]}",

                "kind":
                    "financial_year",

                "sort_key":
                    f"{year}0331",
            }

        return {
            "key":
                dt.isoformat(),

            "display":
                dt.strftime(
                    "%d-%b-%Y"
                ),

            "kind":
                "date",

            "sort_key":
                dt.strftime(
                    "%Y%m%d"
                ),
        }

    return None


def detect_period_columns(
    dataframe: pd.DataFrame,
    sheet_type: str,
    document_category: str,
    workbook_context: Dict,
    scan_rows: int = 12,
) -> Dict[int, Dict]:

    candidates = {}

    for row_index in range(
        min(
            scan_rows,
            len(dataframe)
        )
    ):

        for col_index in range(
            len(
                dataframe.columns
            )
        ):

            period = (
                detect_period_label(
                    dataframe.iloc[
                        row_index,
                        col_index
                    ]
                )
            )

            if not period:
                continue

            existing = (
                candidates.get(
                    col_index
                )
            )

            if (
                existing is None
                or row_index
                >
                existing[
                    "header_row"
                ]
            ):

                candidates[
                    col_index
                ] = {
                    **period,

                    "header_row":
                        row_index,
                }

    if (
        document_category
        == "provisional"
        and sheet_type
        in {
            "profit_and_loss",
            "cash_flow",
        }
    ):

        stub = (
            workbook_context.get(
                "stub_period"
            )
        )

        if stub:

            for (
                col_index,
                period
            ) in list(
                candidates.items()
            ):

                if (
                    period.get(
                        "kind"
                    )
                    == "date"
                    and period.get(
                        "key"
                    )
                    == stub.get(
                        "start_date"
                    )
                ):

                    candidates[
                        col_index
                    ] = {
                        **stub,

                        "header_row":
                            period[
                                "header_row"
                            ],
                    }

    if (
        document_category
        == "projections"
        and sheet_type
        in {
            "projected_profit_and_loss",
            "projected_balance_sheet",
            "projected_cash_flow",
        }
    ):

        candidates = {
            col:
                period

            for (
                col,
                period
            ) in candidates.items()

            if (
                period.get(
                    "kind"
                )
                == "financial_year"
            )
        }

    return candidates


def is_blocked_label(
    label: str
) -> bool:

    text = normalize_text(
        label
    )

    for pattern in (
        BLOCKED_LABEL_PATTERNS
    ):

        if re.search(
            pattern,
            text
        ):
            return True

    return False


def mapping_allowed_for_sheet(
    field_statement: str,
    sheet_type: str,
) -> bool:

    if sheet_type in {
        "profit_and_loss",
        "projected_profit_and_loss",
    }:

        return (
            field_statement
            == "income_statement"
        )

    if sheet_type in {
        "balance_sheet",
        "projected_balance_sheet",
    }:

        return (
            field_statement
            == "balance_sheet"
        )

    if sheet_type in {
        "cash_flow",
        "projected_cash_flow",
    }:

        return (
            field_statement
            == "cash_flow"
        )

    if sheet_type == "notes":
        return True

    return False


def similarity(
    left: str,
    right: str,
) -> float:

    return SequenceMatcher(
        None,
        normalize_text(left),
        normalize_text(right),
    ).ratio()


def map_label(
    label: Any,
    sheet_type: str,
) -> Optional[Dict]:

    source = strip_prefixes(
        str(label)
    )

    if (
        not source
        or is_blocked_label(
            source
        )
    ):
        return None

    # EBITDA
    if (
        source == "ebitda"
        or source.startswith(
            "ebitda "
        )
    ):

        if sheet_type in {
            "profit_and_loss",
            "projected_profit_and_loss",
            "notes",
        }:

            return {
                "canonical_field":
                    "ebitda",

                "statement":
                    "income_statement",

                "confidence":
                    100.0,

                "matched_alias":
                    "ebitda",

                "match_type":
                    "override",
            }

    # =====================================================
    # CRITICAL FIX:
    # SHORT TERM MUST BE CHECKED BEFORE TERM BORROWINGS
    # =====================================================

    short_term_patterns = [
        r"\bshort[\s\-]*term borrowings\b",
        r"\bcurrent borrowings\b",
        r"\bworking capital borrowings\b",
        r"\bcash credit borrowings\b",
        r"\bshort[\s\-]*term borrowings.*cash credit\b",
    ]

    for pattern in (
        short_term_patterns
    ):

        if re.search(
            pattern,
            source
        ):

            if sheet_type in {
                "balance_sheet",
                "projected_balance_sheet",
                "notes",
            }:

                return {
                    "canonical_field":
                        "short_term_borrowings",

                    "statement":
                        "balance_sheet",

                    "confidence":
                        100.0,

                    "matched_alias":
                        "short term borrowings",

                    "match_type":
                        "override",
                }

    long_term_patterns = [
        r"\blong[\s\-]*term borrowings\b",
        r"\bnon[\s\-]*current borrowings\b",
        r"\bterm borrowings\b",
        r"\bterm loans\b",
    ]

    for pattern in (
        long_term_patterns
    ):

        if re.search(
            pattern,
            source
        ):

            if sheet_type in {
                "balance_sheet",
                "projected_balance_sheet",
                "notes",
            }:

                return {
                    "canonical_field":
                        "long_term_borrowings",

                    "statement":
                        "balance_sheet",

                    "confidence":
                        100.0,

                    "matched_alias":
                        "long term borrowings",

                    "match_type":
                        "override",
                }

    blocked_contexts = [
        "interest on cash credit",
        "sales promotion",
        "selling expense",
        "commission and discounts",
        "encashment",
    ]

    for blocked in (
        blocked_contexts
    ):

        if blocked in source:
            return None

    # EXACT
    for (
        field,
        config
    ) in CANONICAL_FIELDS.items():

        statement = (
            config[
                "statement"
            ]
        )

        if not mapping_allowed_for_sheet(
            statement,
            sheet_type,
        ):
            continue

        for alias in (
            config[
                "aliases"
            ]
        ):

            if (
                source
                ==
                normalize_text(
                    alias
                )
            ):

                return {
                    "canonical_field":
                        field,

                    "statement":
                        statement,

                    "confidence":
                        100.0,

                    "matched_alias":
                        alias,

                    "match_type":
                        "exact",
                }

    # FUZZY
    best = None

    for (
        field,
        config
    ) in CANONICAL_FIELDS.items():

        statement = (
            config[
                "statement"
            ]
        )

        if not mapping_allowed_for_sheet(
            statement,
            sheet_type,
        ):
            continue

        for alias in (
            config[
                "aliases"
            ]
        ):

            score = similarity(
                source,
                alias
            )

            if score < 0.88:
                continue

            if (
                best is None
                or score
                >
                best[
                    "score"
                ]
            ):

                best = {
                    "canonical_field":
                        field,

                    "statement":
                        statement,

                    "confidence":
                        round(
                            score * 100,
                            1
                        ),

                    "matched_alias":
                        alias,

                    "match_type":
                        "fuzzy",

                    "score":
                        score,
                }

    if best:

        best.pop(
            "score",
            None
        )

    return best


def extract_values_for_row(
    dataframe: pd.DataFrame,
    row_index: int,
    label_col: int,
    period_columns: Dict[int, Dict],
) -> Dict[str, Dict]:

    values = {}

    for (
        col_index,
        period
    ) in period_columns.items():

        if col_index <= label_col:
            continue

        try:

            value = clean_number(
                dataframe.iloc[
                    row_index,
                    col_index
                ]
            )

        except Exception:
            continue

        if value is None:
            continue

        values[
            period[
                "key"
            ]
        ] = {
            "value":
                value,

            "period":
                period,
        }

    return values


def should_review_unmapped(
    sheet_type: str,
    source_label: str,
) -> bool:

    if sheet_type in {
        "notes",
        "cash_flow",
        "projected_cash_flow",
    }:

        return False

    if sheet_type not in {
        "profit_and_loss",
        "balance_sheet",
        "projected_profit_and_loss",
        "projected_balance_sheet",
    }:

        return False

    return not is_blocked_label(
        source_label
    )


def extract_financial_sheet(
    dataframe: pd.DataFrame,
    sheet_name: str,
    sheet_type: str,
    document_category: str,
    workbook_context: Dict,
) -> Dict:

    period_columns = (
        detect_period_columns(
            dataframe,
            sheet_type,
            document_category,
            workbook_context,
        )
    )

    mapped_rows = []
    review_rows = []

    max_label_columns = min(
        len(
            dataframe.columns
        ),
        6
    )

    for row_index in range(
        len(dataframe)
    ):

        best_candidate = None

        for col_index in range(
            max_label_columns
        ):

            cell = dataframe.iloc[
                row_index,
                col_index
            ]

            text = normalize_text(
                cell
            )

            if not text:
                continue

            if (
                clean_number(
                    cell
                )
                is not None
            ):
                continue

            mapping = map_label(
                cell,
                sheet_type,
            )

            if not mapping:
                continue

            values = (
                extract_values_for_row(
                    dataframe,
                    row_index,
                    col_index,
                    period_columns,
                )
            )

            if not values:
                continue

            candidate = {
                "source_label":
                    str(cell).strip(),

                "canonical_field":
                    mapping[
                        "canonical_field"
                    ],

                "statement":
                    mapping[
                        "statement"
                    ],

                "confidence":
                    mapping[
                        "confidence"
                    ],

                "match_type":
                    mapping[
                        "match_type"
                    ],

                "matched_alias":
                    mapping[
                        "matched_alias"
                    ],

                "sheet":
                    sheet_name,

                "sheet_type":
                    sheet_type,

                "document_category":
                    document_category,

                "row":
                    row_index + 1,

                "column":
                    col_index + 1,

                "values":
                    values,
            }

            if (
                best_candidate is None
                or candidate[
                    "confidence"
                ]
                >
                best_candidate[
                    "confidence"
                ]
            ):

                best_candidate = (
                    candidate
                )

        if best_candidate:

            mapped_rows.append(
                best_candidate
            )

            continue

        text_cells = []
        numeric_values = []

        for cell in (
            dataframe.iloc[
                row_index
            ]
        ):

            text = normalize_text(
                cell
            )

            number = clean_number(
                cell
            )

            if (
                text
                and number is None
            ):

                text_cells.append(
                    str(cell).strip()
                )

            if number is not None:

                numeric_values.append(
                    number
                )

        if (
            text_cells
            and numeric_values
        ):

            source_label = (
                text_cells[0]
            )

            if should_review_unmapped(
                sheet_type,
                source_label,
            ):

                review_rows.append({
                    "source_label":
                        source_label,

                    "sheet":
                        sheet_name,

                    "sheet_type":
                        sheet_type,

                    "document_category":
                        document_category,

                    "row":
                        row_index + 1,

                    "reason":
                        "No confident canonical mapping",
                })

    return {
        "sheet_name":
            sheet_name,

        "sheet_type":
            sheet_type,

        "document_category":
            document_category,

        "period_columns":
            {
                str(
                    column + 1
                ):
                    period

                for (
                    column,
                    period
                ) in period_columns.items()
            },

        "mapped_rows":
            mapped_rows,

        "review_rows":
            review_rows,
    }


def extract_generic_table(
    dataframe: pd.DataFrame,
    sheet_name: str,
    sheet_type: str,
    document_category: str,
) -> Dict:

    rows = []

    for row_index in range(
        len(dataframe)
    ):

        row_data = []

        for col_index in range(
            len(
                dataframe.columns
            )
        ):

            value = dataframe.iloc[
                row_index,
                col_index
            ]

            try:
                if pd.isna(value):
                    value = None
            except Exception:
                pass

            row_data.append(
                value
            )

        if any(
            value is not None
            and str(
                value
            ).strip() != ""

            for value in row_data
        ):

            rows.append({
                "row":
                    row_index + 1,

                "values":
                    row_data,
            })

    return {
        "sheet_name":
            sheet_name,

        "sheet_type":
            sheet_type,

        "document_category":
            document_category,

        "rows":
            rows,
    }


def normalized_bucket_for_document(
    document_category: str,
) -> str:

    if document_category == "historical":
        return "historical"

    if document_category == "provisional":
        return "provisional"

    if document_category == "projections":
        return "projected"

    return "other"


def source_priority(
    row: Dict
) -> int:

    return SOURCE_PRIORITY.get(
        row.get(
            "sheet_type",
            "unknown"
        ),
        20
    )


def should_replace_existing(
    existing: Optional[Dict],
    candidate: Dict,
) -> bool:

    if existing is None:
        return True

    existing_priority = (
        existing.get(
            "source_priority",
            0
        )
    )

    candidate_priority = (
        candidate.get(
            "source_priority",
            0
        )
    )

    if (
        candidate_priority
        >
        existing_priority
    ):
        return True

    if (
        candidate_priority
        <
        existing_priority
    ):
        return False

    return (
        candidate.get(
            "confidence",
            0
        )
        >
        existing.get(
            "confidence",
            0
        )
    )


def build_normalized_dataset(
    financial_sheets: List[Dict],
    file_name: str,
) -> Dict:

    normalized = {
        "historical": {
            "income_statement": {},
            "balance_sheet": {},
            "cash_flow": {},
        },

        "provisional": {
            "income_statement": {},
            "balance_sheet": {},
            "cash_flow": {},
        },

        "projected": {
            "income_statement": {},
            "balance_sheet": {},
            "cash_flow": {},
        },
    }

    mapping_review = []

    for sheet in (
        financial_sheets
    ):

        bucket = (
            normalized_bucket_for_document(
                sheet[
                    "document_category"
                ]
            )
        )

        if bucket == "other":
            continue

        for row in (
            sheet[
                "mapped_rows"
            ]
        ):

            statement = (
                row[
                    "statement"
                ]
            )

            field = (
                row[
                    "canonical_field"
                ]
            )

            priority = (
                source_priority(
                    row
                )
            )

            for (
                period_key,
                period_item
            ) in row[
                "values"
            ].items():

                if (
                    period_key
                    not in normalized[
                        bucket
                    ][
                        statement
                    ]
                ):

                    normalized[
                        bucket
                    ][
                        statement
                    ][
                        period_key
                    ] = {
                        "_period":
                            period_item[
                                "period"
                            ]
                    }

                candidate = {
                    "value":
                        period_item[
                            "value"
                        ],

                    "confidence":
                        row[
                            "confidence"
                        ],

                    "source_priority":
                        priority,

                    "source_label":
                        row[
                            "source_label"
                        ],

                    "sheet":
                        row[
                            "sheet"
                        ],

                    "file_name":
                        file_name,

                    "row":
                        row[
                            "row"
                        ],
                }

                existing = (
                    normalized[
                        bucket
                    ][
                        statement
                    ][
                        period_key
                    ].get(
                        field
                    )
                )

                if should_replace_existing(
                    existing,
                    candidate,
                ):

                    normalized[
                        bucket
                    ][
                        statement
                    ][
                        period_key
                    ][
                        field
                    ] = candidate

            mapping_review.append(
                row
            )

    return {
        "normalized":
            normalized,

        "mapping_review":
            mapping_review,
    }


def extract_excel_file(
    file_path: Path,
) -> Dict:

    file_path = Path(
        file_path
    )

    category = (
        detect_document_category(
            file_path
        )
    )

    result = {
        "extractor_version":
            EXTRACTOR_VERSION,

        "file_name":
            file_path.name,

        "file_path":
            str(file_path),

        "document_category":
            category,

        "sheets":
            [],

        "normalized":
            {},

        "mapping_review":
            [],

        "review_required":
            [],

        "generic_tables":
            [],

        "workbook_context":
            {},
    }

    try:

        excel = pd.ExcelFile(
            file_path
        )

    except Exception as exc:

        result[
            "error"
        ] = str(exc)

        return result

    workbook_context = (
        detect_workbook_context(
            excel,
            file_path,
        )
    )

    result[
        "workbook_context"
    ] = workbook_context

    financial_sheets = []

    for sheet_name in (
        excel.sheet_names
    ):

        try:

            dataframe = (
                pd.read_excel(
                    file_path,
                    sheet_name=
                        sheet_name,
                    header=None,
                    dtype=object,
                )
            )

            dataframe = (
                dataframe
                .dropna(
                    axis=0,
                    how="all"
                )
                .dropna(
                    axis=1,
                    how="all"
                )
                .reset_index(
                    drop=True
                )
            )

            if dataframe.empty:
                continue

            classification = (
                classify_sheet(
                    sheet_name,
                    category,
                    dataframe,
                )
            )

            sheet_type = (
                classification[
                    "type"
                ]
            )

            financial_types = {
                "profit_and_loss",
                "balance_sheet",
                "cash_flow",
                "projected_profit_and_loss",
                "projected_balance_sheet",
                "projected_cash_flow",
                "notes",
            }

            if (
                sheet_type
                in financial_types
            ):

                sheet_result = (
                    extract_financial_sheet(
                        dataframe,
                        sheet_name,
                        sheet_type,
                        category,
                        workbook_context,
                    )
                )

                financial_sheets.append(
                    sheet_result
                )

                result[
                    "review_required"
                ].extend(
                    sheet_result[
                        "review_rows"
                    ]
                )

                result[
                    "sheets"
                ].append({
                    "sheet_name":
                        sheet_name,

                    "sheet_type":
                        sheet_type,

                    "classification_confidence":
                        classification[
                            "confidence"
                        ],

                    "mapped_count":
                        len(
                            sheet_result[
                                "mapped_rows"
                            ]
                        ),

                    "review_count":
                        len(
                            sheet_result[
                                "review_rows"
                            ]
                        ),

                    "period_columns":
                        sheet_result[
                            "period_columns"
                        ],
                })

            else:

                generic = (
                    extract_generic_table(
                        dataframe,
                        sheet_name,
                        sheet_type,
                        category,
                    )
                )

                result[
                    "generic_tables"
                ].append(
                    generic
                )

                result[
                    "sheets"
                ].append({
                    "sheet_name":
                        sheet_name,

                    "sheet_type":
                        sheet_type,

                    "classification_confidence":
                        classification[
                            "confidence"
                        ],

                    "mapped_count":
                        0,

                    "review_count":
                        0,
                })

        except Exception as exc:

            result[
                "sheets"
            ].append({
                "sheet_name":
                    sheet_name,

                "error":
                    str(exc),
            })

    normalized_result = (
        build_normalized_dataset(
            financial_sheets,
            file_path.name,
        )
    )

    result[
        "normalized"
    ] = normalized_result[
        "normalized"
    ]

    result[
        "mapping_review"
    ] = normalized_result[
        "mapping_review"
    ]

    return result


def merge_normalized_workbooks(
    workbooks: List[Dict],
) -> Dict:

    combined = {
        "historical": {
            "income_statement": {},
            "balance_sheet": {},
            "cash_flow": {},
        },

        "provisional": {
            "income_statement": {},
            "balance_sheet": {},
            "cash_flow": {},
        },

        "projected": {
            "income_statement": {},
            "balance_sheet": {},
            "cash_flow": {},
        },
    }

    for workbook in (
        workbooks
    ):

        normalized = (
            workbook.get(
                "normalized",
                {}
            )
        )

        for (
            bucket,
            statements
        ) in normalized.items():

            if bucket not in combined:
                continue

            for (
                statement,
                periods
            ) in statements.items():

                for (
                    period_key,
                    fields
                ) in periods.items():

                    if (
                        period_key
                        not in combined[
                            bucket
                        ][
                            statement
                        ]
                    ):

                        combined[
                            bucket
                        ][
                            statement
                        ][
                            period_key
                        ] = {}

                    if (
                        "_period"
                        in fields
                    ):

                        combined[
                            bucket
                        ][
                            statement
                        ][
                            period_key
                        ][
                            "_period"
                        ] = fields[
                            "_period"
                        ]

                    for (
                        field,
                        candidate
                    ) in fields.items():

                        if field == "_period":
                            continue

                        existing = (
                            combined[
                                bucket
                            ][
                                statement
                            ][
                                period_key
                            ].get(
                                field
                            )
                        )

                        if should_replace_existing(
                            existing,
                            candidate,
                        ):

                            combined[
                                bucket
                            ][
                                statement
                            ][
                                period_key
                            ][
                                field
                            ] = candidate

    return combined


def clean_projected_periods(
    combined: Dict,
) -> Dict:

    historical_years = []

    for statement in [
        "income_statement",
        "balance_sheet",
    ]:

        for period_key in (
            combined[
                "historical"
            ][
                statement
            ].keys()
        ):

            match = re.match(
                r"FY(20\d{2})$",
                period_key
            )

            if match:

                historical_years.append(
                    int(
                        match.group(1)
                    )
                )

    if not historical_years:
        return combined

    latest_historical_year = (
        max(
            historical_years
        )
    )

    for statement in [
        "income_statement",
        "balance_sheet",
        "cash_flow",
    ]:

        projected = (
            combined[
                "projected"
            ][
                statement
            ]
        )

        remove_keys = []

        for period_key in (
            projected.keys()
        ):

            match = re.match(
                r"FY(20\d{2})$",
                period_key
            )

            if not match:

                remove_keys.append(
                    period_key
                )

                continue

            if (
                int(
                    match.group(1)
                )
                <= latest_historical_year
            ):

                remove_keys.append(
                    period_key
                )

        for key in (
            remove_keys
        ):

            projected.pop(
                key,
                None
            )

    return combined


def get_value(
    period_data: Dict,
    field: str,
) -> Optional[float]:

    item = period_data.get(
        field
    )

    if not item:
        return None

    return item.get(
        "value"
    )


def build_cross_checks(
    combined: Dict,
) -> List[Dict]:

    checks = []

    for bucket in [
        "historical",
        "provisional",
        "projected",
    ]:

        for (
            period_key,
            period_data
        ) in combined[
            bucket
        ][
            "balance_sheet"
        ].items():

            total_assets = get_value(
                period_data,
                "total_assets"
            )

            total_equity_liabilities = (
                get_value(
                    period_data,
                    "total_equity_liabilities"
                )
            )

            if (
                total_assets is not None
                and
                total_equity_liabilities
                is not None
            ):

                difference = (
                    total_assets
                    -
                    total_equity_liabilities
                )

                checks.append({
                    "bucket":
                        bucket,

                    "period":
                        period_key,

                    "check":
                        "Balance Sheet",

                    "difference":
                        round(
                            difference,
                            4
                        ),

                    "status":
                        (
                            "OK"
                            if abs(
                                difference
                            ) < 0.01
                            else "REVIEW"
                        ),
                })

        for (
            period_key,
            period_data
        ) in combined[
            bucket
        ][
            "income_statement"
        ].items():

            revenue = get_value(
                period_data,
                "revenue_from_operations"
            )

            other_income = get_value(
                period_data,
                "other_income"
            )

            total_income = get_value(
                period_data,
                "total_income"
            )

            if (
                revenue is not None
                and other_income is not None
                and total_income is not None
            ):

                difference = (
                    revenue
                    +
                    other_income
                    -
                    total_income
                )

                checks.append({
                    "bucket":
                        bucket,

                    "period":
                        period_key,

                    "check":
                        "Revenue + Other Income = Total Income",

                    "difference":
                        round(
                            difference,
                            4
                        ),

                    "status":
                        (
                            "OK"
                            if abs(
                                difference
                            ) < 0.01
                            else "REVIEW"
                        ),
                })

    return checks


def period_summary(
    combined: Dict,
    bucket: str,
) -> List[str]:

    periods = set()

    for statement in [
        "income_statement",
        "balance_sheet",
        "cash_flow",
    ]:

        periods.update(
            combined[
                bucket
            ][
                statement
            ].keys()
        )

    def sort_key(
        key: str
    ):

        for statement in [
            "income_statement",
            "balance_sheet",
            "cash_flow",
        ]:

            data = (
                combined[
                    bucket
                ][
                    statement
                ].get(
                    key
                )
            )

            if (
                data
                and "_period"
                in data
            ):

                return (
                    data[
                        "_period"
                    ].get(
                        "sort_key",
                        key
                    )
                )

        return key

    return sorted(
        periods,
        key=sort_key
    )


def build_review_queue(
    workbooks: List[Dict],
) -> List[Dict]:

    review_queue = []
    seen = set()

    for workbook in (
        workbooks
    ):

        file_name = (
            workbook.get(
                "file_name",
                ""
            )
        )

        for item in workbook.get(
            "review_required",
            []
        ):

            key = (
                file_name,
                item.get("sheet"),
                item.get("row"),
                item.get(
                    "source_label"
                ),
            )

            if key in seen:
                continue

            seen.add(key)

            review_queue.append({
                "file_name":
                    file_name,

                **item,
            })

        for mapping in workbook.get(
            "mapping_review",
            []
        ):

            if (
                mapping.get(
                    "match_type"
                )
                != "fuzzy"
            ):
                continue

            sheet_type = (
                mapping.get(
                    "sheet_type"
                )
            )

            confidence = (
                mapping.get(
                    "confidence",
                    0
                )
            )

            if (
                sheet_type == "notes"
                and confidence >= 90
            ):
                continue

            if confidence >= 95:
                continue

            key = (
                file_name,
                mapping.get("sheet"),
                mapping.get("row"),
                mapping.get(
                    "source_label"
                ),
            )

            if key in seen:
                continue

            seen.add(key)

            review_queue.append({
                "file_name":
                    file_name,

                "reason":
                    "Fuzzy mapping requires review",

                **mapping,
            })

    return review_queue


def extract_assignment_financials(
    assignment_folder: Path,
) -> Dict:

    assignment_folder = Path(
        assignment_folder
    )

    documents_folder = (
        assignment_folder
        /
        "documents"
    )

    result = {
        "extractor_version":
            EXTRACTOR_VERSION,

        "assignment_folder":
            str(
                assignment_folder
            ),

        "files":
            [],

        "combined_normalized":
            {},

        "review_required":
            [],

        "cross_checks":
            [],

        "summary":
            {},
    }

    if not documents_folder.exists():
        return result

    allowed_extensions = {
        ".xlsx",
        ".xls",
        ".xlsm",
    }

    workbook_results = []

    for file_path in sorted(
        documents_folder.rglob(
            "*"
        )
    ):

        if not file_path.is_file():
            continue

        if (
            file_path.suffix.lower()
            not in allowed_extensions
        ):
            continue

        workbook_results.append(
            extract_excel_file(
                file_path
            )
        )

    result[
        "files"
    ] = workbook_results

    combined = (
        merge_normalized_workbooks(
            workbook_results
        )
    )

    combined = (
        clean_projected_periods(
            combined
        )
    )

    result[
        "combined_normalized"
    ] = combined

    review_queue = (
        build_review_queue(
            workbook_results
        )
    )

    result[
        "review_required"
    ] = review_queue

    result[
        "cross_checks"
    ] = build_cross_checks(
        combined
    )

    result[
        "summary"
    ] = {
        "workbooks_found":
            len(
                workbook_results
            ),

        "historical_periods":
            period_summary(
                combined,
                "historical"
            ),

        "provisional_periods":
            period_summary(
                combined,
                "provisional"
            ),

        "projected_periods":
            period_summary(
                combined,
                "projected"
            ),

        "review_items":
            len(
                review_queue
            ),
    }

    return result