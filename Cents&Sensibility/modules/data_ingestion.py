"""
Cents & Sensibility — Data Ingestion Module
Parses the Cents & Sensibility Excel template (or confirmed PDF-extracted data)
into the canonical internal data structure used by all downstream engines.
"""

import io
import pandas as pd

# ---------------------------------------------------------------------------
# Canonical schema — every downstream module works off these keys
# ---------------------------------------------------------------------------
LINE_ITEMS = [
    # (canonical_key, display_label, statement, required)
    ("revenue",              "Revenue from Operations",            "P&L", True),
    ("other_income",         "Other Income",                       "P&L", False),
    ("material_cost",        "Cost of Materials / Purchases",      "P&L", True),
    ("employee_cost",        "Employee Benefit Expenses",          "P&L", True),
    ("finance_cost",         "Finance Costs",                      "P&L", True),
    ("depreciation",         "Depreciation & Amortisation",        "P&L", True),
    ("other_expenses",       "Other / SG&A Expenses",              "P&L", True),
    ("pbt",                  "Profit Before Tax",                  "P&L", True),
    ("tax",                  "Tax Expense",                        "P&L", True),
    ("pat",                  "Profit After Tax",                   "P&L", True),
    ("share_capital",        "Share Capital",                      "BS",  True),
    ("reserves",             "Reserves & Surplus",                 "BS",  True),
    ("lt_borrowings",        "Long-term Borrowings",               "BS",  False),
    ("st_borrowings",        "Short-term Borrowings",              "BS",  False),
    ("trade_payables",       "Trade Payables",                     "BS",  True),
    ("other_current_liab",   "Other Current Liabilities",          "BS",  False),
    ("provisions",           "Provisions",                         "BS",  False),
    ("net_ppe",              "Property, Plant & Equipment (Net)",  "BS",  True),
    ("nc_investments",       "Non-current Investments",            "BS",  False),
    ("other_nc_assets",      "Other Non-current Assets",           "BS",  False),
    ("inventory",            "Inventories",                        "BS",  True),
    ("receivables",          "Trade Receivables",                  "BS",  True),
    ("cash",                 "Cash & Bank Balances",               "BS",  True),
    ("st_loans_advances",    "Short-term Loans & Advances",        "BS",  False),
    ("other_current_assets", "Other Current Assets",               "BS",  False),
]

KEY_BY_LABEL = {label.strip().lower(): key for key, label, _, _ in LINE_ITEMS}
LABEL_BY_KEY = {key: label for key, label, _, _ in LINE_ITEMS}
PERIODS = ["CY", "PY", "PY2"]          # Current year, Prior year, Prior-prior year
PERIOD_LABELS = {"CY": "Current Year", "PY": "Previous Year", "PY2": "Year Before Previous"}


def blank_period() -> dict:
    return {key: 0.0 for key, *_ in LINE_ITEMS}


def make_template_bytes() -> bytes:
    """Generate the downloadable Cents & Sensibility Excel input template."""
    rows = []
    for key, label, stmt, req in LINE_ITEMS:
        rows.append({
            "Statement": stmt,
            "Line Item": label,
            "Current Year": 0,
            "Previous Year": 0,
            "Year Before Previous (optional)": 0,
        })
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        df.to_excel(xw, sheet_name="Financials", index=False)
    return buf.getvalue()


def parse_excel(file_like) -> tuple[dict, list[str]]:
    """
    Parse an uploaded Cents & Sensibility template Excel.
    Returns (data, warnings): data = {"CY": {...}, "PY": {...}, "PY2": {...} or None}
    """
    warnings = []
    df = pd.read_excel(file_like, sheet_name=0)
    df.columns = [str(c).strip() for c in df.columns]

    # Locate columns flexibly
    label_col = next((c for c in df.columns if "line item" in c.lower()), None)
    cy_col = next((c for c in df.columns if "current" in c.lower()), None)
    py_col = next((c for c in df.columns if c.lower().startswith("previous")
                   or "prior year" in c.lower()), None)
    py2_col = next((c for c in df.columns if "before previous" in c.lower()
                    or "py-1" in c.lower() or "py2" in c.lower()), None)

    if not (label_col and cy_col and py_col):
        raise ValueError(
            "Could not find required columns. Please use the Cents & Sensibility template "
            "(columns: 'Line Item', 'Current Year', 'Previous Year')."
        )

    data = {"CY": blank_period(), "PY": blank_period(), "PY2": blank_period()}
    matched = set()

    for _, row in df.iterrows():
        label = str(row[label_col]).strip().lower()
        key = KEY_BY_LABEL.get(label)
        if key is None:
            continue
        matched.add(key)
        for period, col in (("CY", cy_col), ("PY", py_col), ("PY2", py2_col)):
            if col is None:
                continue
            val = pd.to_numeric(row.get(col), errors="coerce")
            data[period][key] = float(val) if pd.notna(val) else 0.0

    required = [k for k, _, _, req in LINE_ITEMS if req]
    missing = [LABEL_BY_KEY[k] for k in required if k not in matched]
    if missing:
        warnings.append("Missing / unrecognised line items (treated as zero): "
                        + ", ".join(missing))

    # Is PY2 actually populated?
    if all(abs(v) < 1e-9 for v in data["PY2"].values()):
        data["PY2"] = None
        warnings.append("Third-year data not provided — trend analysis will use two years.")

    return data, warnings


# ---------------------------------------------------------------------------
# Derived totals — single source of truth
# ---------------------------------------------------------------------------
def derive(p: dict) -> dict:
    """Compute derived totals for one period dict. Returns an enriched copy."""
    d = dict(p)
    d["total_income"] = d["revenue"] + d["other_income"]
    d["total_expenses"] = (d["material_cost"] + d["employee_cost"] + d["finance_cost"]
                           + d["depreciation"] + d["other_expenses"])
    d["ebit"] = d["pbt"] + d["finance_cost"]
    d["ebitda"] = d["ebit"] + d["depreciation"]
    d["gross_profit"] = d["revenue"] - d["material_cost"]

    d["total_equity"] = d["share_capital"] + d["reserves"]
    d["total_debt"] = d["lt_borrowings"] + d["st_borrowings"]
    d["current_assets"] = (d["inventory"] + d["receivables"] + d["cash"]
                           + d["st_loans_advances"] + d["other_current_assets"])
    d["current_liab"] = (d["st_borrowings"] + d["trade_payables"]
                         + d["other_current_liab"] + d["provisions"])
    d["non_current_assets"] = d["net_ppe"] + d["nc_investments"] + d["other_nc_assets"]
    d["total_assets"] = d["current_assets"] + d["non_current_assets"]
    d["total_liabilities"] = d["total_debt"] + d["trade_payables"] + d["other_current_liab"] + d["provisions"]
    d["working_capital"] = d["current_assets"] - d["current_liab"]
    d["capital_employed"] = d["total_equity"] + d["lt_borrowings"]
    return d


def balance_check(p: dict) -> tuple[bool, float]:
    """Assets vs Equity + Liabilities self-check. Returns (ok, difference)."""
    d = derive(p)
    diff = d["total_assets"] - (d["total_equity"] + d["total_liabilities"])
    tol = max(1.0, 0.005 * max(d["total_assets"], 1.0))   # 0.5% tolerance
    return abs(diff) <= tol, diff
