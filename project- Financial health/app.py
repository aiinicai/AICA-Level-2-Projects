"""
=============================================================================
 SUNDAY SOMEWEAR - END-TO-END FINANCIAL HEALTH CHECKER & EXECUTIVE MIS
 DASHBOARD
=============================================================================
A production-grade Streamlit application that reads an apparel manufacturer's
General Ledger workbook and produces:
    1. Executive Financial Health & Solvency Scorecard
    2. Monthly MIS Financial Statements (P&L / Balance Sheet / Cash Flow)
    3. MoM & Period-over-Period Variance Analysis
    4. Root-Cause Diagnostics & Pareto (80/20) Analytics
    5. Executive Action Plan & Strategic Scenario Simulator

Author: Financial Engineering / Data Science
=============================================================================
"""

from __future__ import annotations

import os
import io
import datetime as dt
from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# =============================================================================
# 0. GLOBAL CONFIGURATION
# =============================================================================

DATA_FILE = "Sunday_Somewear_GL_Database_2026.xlsx"

SHEET_GL = "GL Journal Entries"
SHEET_COA = "Chart of Accounts"
SHEET_SKU = "SKU Master List"

REQUIRED_COLUMNS = {
    SHEET_GL: [
        "Entry ID", "Posting Date", "GL Code", "GL Account Name", "Account Type",
        "Category", "SKU Reference", "Description", "Document Ref",
        "Debit (₹)", "Credit (₹)",
    ],
    SHEET_COA: ["GL Code", "Account Name", "Account Category", "Normal Balance"],
    SHEET_SKU: ["Category", "SKU Code", "Product Name", "Target Segment"],
}

# ---- Corporate finance color palette -------------------------------------
NAVY = "#2B5C8F"
NAVY_DARK = "#1D4468"
TERRACOTTA = "#D9534F"
EMERALD = "#5CB85C"
AMBER = "#E8A33D"
LIGHT_GRAY = "#F4F6F8"
CARD_GRAY = "#FFFFFF"
TEXT_DARK = "#1F2A37"
TEXT_MUTED = "#5B6B7C"

CHART_COLORWAY = [NAVY, TERRACOTTA, EMERALD, AMBER, "#7B8FA6", "#A6516E"]

st.set_page_config(
    page_title="Sunday Somewear | Financial Health & MIS Dashboard",
    page_icon="\U0001F457",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- Global CSS ------------------------------------------------------------
# NOTE: The base theme (light background, dark text) is locked via
# .streamlit/config.toml so the app renders consistently regardless of the
# viewer's OS/browser dark-mode setting - Streamlit auto-switches to a dark
# theme otherwise, which fights with these overrides and produces invisible
# "white on white" text in places this CSS doesn't explicitly repaint. This
# block only adds cosmetic styling on top of that locked light theme; it
# deliberately avoids blanket `* { color: ... }` rules on any container that
# also holds native Streamlit widgets (file uploader, selectbox, etc.),
# since those widgets carry their own light-colored internal backgrounds and
# forcing light text on top of them would make it unreadable.
st.markdown(
    f"""
    <style>
        .stApp {{
            background-color: {LIGHT_GRAY};
        }}
        section[data-testid="stSidebar"] {{
            background-color: #FFFFFF;
            border-right: 1px solid #E3E8EE;
        }}
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {{
            color: {NAVY_DARK};
        }}
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] .stCaption,
        section[data-testid="stSidebar"] small {{
            color: {TEXT_DARK} !important;
        }}
        div[data-testid="stMetric"] {{
            background-color: {CARD_GRAY};
            border: 1px solid #E3E8EE;
            border-left: 5px solid {NAVY};
            border-radius: 10px;
            padding: 14px 16px 10px 16px;
            box-shadow: 0 1px 3px rgba(20,30,45,0.06);
        }}
        div[data-testid="stMetricLabel"] {{
            color: {TEXT_MUTED};
            font-weight: 600;
        }}
        h1, h2, h3 {{
            color: {NAVY_DARK};
            font-family: "Source Sans Pro", "Segoe UI", sans-serif;
        }}
        .health-badge {{
            display: inline-block;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: 700;
            font-size: 1.05rem;
            color: white;
        }}
        .commentary-box {{
            background-color: {CARD_GRAY};
            border: 1px solid #E3E8EE;
            border-radius: 10px;
            padding: 18px 22px;
            box-shadow: 0 1px 3px rgba(20,30,45,0.06);
        }}
        .section-divider {{
            border-top: 2px solid #E3E8EE;
            margin: 1.2rem 0 1.2rem 0;
        }}
        thead tr th {{
            background-color: {NAVY} !important;
            color: white !important;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

pd.set_option("mode.chained_assignment", None)

# =============================================================================
# 1. FORMATTING HELPERS
# =============================================================================

def _indian_grouped_digits(int_digits: str) -> str:
    """
    Groups an integer digit string using the Indian numbering system: the
    last 3 digits together, then groups of 2 to the left (e.g. '1234567'
    -> '12,34,567', which reads as 12 lakh 34 thousand 567) rather than the
    Western groups-of-3 system ('1,234,567').
    """
    if len(int_digits) <= 3:
        return int_digits
    last_three = int_digits[-3:]
    remaining = int_digits[:-3]
    groups = []
    while len(remaining) > 2:
        groups.insert(0, remaining[-2:])
        remaining = remaining[:-2]
    if remaining:
        groups.insert(0, remaining)
    return ",".join(groups) + "," + last_three


def fmt_currency(value: Optional[float], allow_negative_parens: bool = False) -> str:
    """Formats a numeric value as an Indian Rupee currency string using the
    lakh/crore digit-grouping convention, e.g. ₹12,34,567.89."""
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return "₹0.00"
        v = float(value)
    except (TypeError, ValueError):
        return "₹0.00"

    int_part, _, dec_part = f"{abs(v):.2f}".partition(".")
    formatted = f"₹{_indian_grouped_digits(int_part)}.{dec_part}"

    if v < 0:
        return f"({formatted})" if allow_negative_parens else f"-{formatted}"
    return formatted


def fmt_pct(value: Optional[float], decimals: int = 2) -> str:
    """Formats a fractional value (e.g. 0.235) as a 0.00% percentage string."""
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return "0.00%"
        v = float(value)
    except (TypeError, ValueError):
        return "0.00%"
    return f"{v * 100:.{decimals}f}%"


def safe_div(numerator: float, denominator: float) -> float:
    """Division that returns 0.0 instead of raising on a zero/NaN denominator."""
    try:
        if denominator in (0, 0.0) or denominator is None or pd.isna(denominator):
            return 0.0
        return float(numerator) / float(denominator)
    except (TypeError, ZeroDivisionError):
        return 0.0


# =============================================================================
# 2. DATA LOADING
# =============================================================================

class DataLoadError(Exception):
    """Raised when the source workbook is missing, malformed, or incomplete."""


@st.cache_data(show_spinner="Loading GL Database workbook...")
def load_workbook(file_path: str, file_bytes: Optional[bytes] = None) -> dict:
    """
    Loads and validates the three required tabs from the GL workbook.
    Accepts either a path on disk or raw bytes (from an uploaded file), so the
    app remains usable even if the expected filename is not present locally.
    Raises DataLoadError with a human-readable message on any problem.
    """
    source = io.BytesIO(file_bytes) if file_bytes is not None else file_path

    if file_bytes is None and not os.path.exists(file_path):
        raise DataLoadError(
            f"Could not find the workbook '{file_path}' in the application "
            f"directory. Please place the file alongside app.py or upload it "
            f"using the sidebar uploader."
        )

    try:
        xls = pd.ExcelFile(source, engine="openpyxl")
    except Exception as exc:  # noqa: BLE001
        raise DataLoadError(f"The workbook could not be opened/parsed: {exc}") from exc

    missing_sheets = [s for s in REQUIRED_COLUMNS if s not in xls.sheet_names]
    if missing_sheets:
        raise DataLoadError(
            "The workbook is missing required tab(s): "
            f"{', '.join(missing_sheets)}. Found tabs: {', '.join(xls.sheet_names)}"
        )

    frames = {}
    for sheet, required_cols in REQUIRED_COLUMNS.items():
        try:
            df = pd.read_excel(xls, sheet_name=sheet)
        except Exception as exc:  # noqa: BLE001
            raise DataLoadError(f"Failed reading tab '{sheet}': {exc}") from exc

        df.columns = [str(c).strip() for c in df.columns]
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            raise DataLoadError(
                f"Tab '{sheet}' is missing required column(s): {', '.join(missing_cols)}"
            )
        frames[sheet] = df

    return frames


def _kw(text: str, *keywords: str) -> bool:
    """
    Case-insensitive substring keyword match. Safe here because classification
    is scoped in two tiers (see _classify_account): Tier 1 restricts matching
    to the structured 'Account Category'/'Account Type' fields only, and
    Tier 2 keyword checks only run *within* the high-level type that Tier 1
    already determined - so a name like 'Raw Material Inventory' is routed to
    Inventory (its Account Category is 'Current Asset') and never reaches the
    COGS-stage 'raw material' keyword check at all. This scoping is what
    prevents cross-type collisions, so plain substring matching (which also
    naturally handles plurals like 'Materials' containing 'material') is
    safe and preferred over brittle whole-word regexes here.
    """
    return any(k in text for k in keywords)


def _classify_account(row: pd.Series) -> str:
    """
    Maps a GL journal line to a standardized financial-statement bucket.

    Two-tier design:
      1. HIGH-LEVEL TYPE is taken from the structured 'Account Category'
         (Chart of Accounts) / 'Account Type' (GL Journal) fields - these are
         authoritative and prevent cross-type collisions (e.g. an account
         named 'Raw Material Inventory' must land in Inventory, not COGS,
         even though its name contains the words "raw material").
      2. Within that high-level type, the account NAME is used only to pick
         the specific sub-bucket (e.g. which flavor of COGS/Opex/Asset).

    A permissive whole-word keyword fallback is used only when the
    structured category fields are blank or unrecognized (e.g. the GL Code
    did not match any row in the Chart of Accounts).
    """
    category_text = " ".join(
        str(row.get(c, "")) for c in ["Account Category", "Account Type"]
    ).lower()
    name_text = " ".join(
        str(row.get(c, "")) for c in ["GL Account Name", "Account Name"]
    ).lower()
    full_text = f"{category_text} {name_text}"

    # ---- Step 1: high-level type from structured category fields ----------
    high_level = None
    if _kw(category_text, "contra revenue", "contra-revenue", "sales return",
           "returns and allowances", "returns & allowances"):
        high_level = "contra_revenue"
    elif _kw(category_text, "revenue", "sales income", "net sales", "income"):
        high_level = "revenue"
    elif _kw(category_text, "cogs", "cost of goods sold", "cost of good sold",
             "cost of sales"):
        high_level = "cogs"
    elif _kw(category_text, "operating expense", "opex", "expense"):
        high_level = "opex"
    elif _kw(category_text, "current asset", "fixed asset", "asset"):
        high_level = "asset"
    elif _kw(category_text, "current liability", "long-term liability",
             "liability", "liabilities"):
        high_level = "liability"
    elif _kw(category_text, "equity"):
        high_level = "equity"

    # ---- Step 2: refine using the account NAME, scoped by high_level ------
    if high_level == "contra_revenue" or _kw(name_text, "return", "refund", "allowance"):
        return "Sales Returns"

    if high_level == "revenue":
        return "Gross Revenue"

    if high_level == "cogs":
        if _kw(name_text, "raw material", "fabric", "bom", "material cost", "material"):
            return "Raw Materials COGS"
        if _kw(name_text, "direct labor", "labor", "wages", "stitching", "production labor"):
            return "Direct Labor COGS"
        if _kw(name_text, "freight", "inbound shipping", "shipping", "outbound freight"):
            return "Freight COGS"
        return "Other COGS"

    if high_level == "opex":
        if _kw(name_text, "marketing", "advertising", "promotion"):
            return "Marketing Expense"
        if _kw(name_text, "logistics", "warehousing", "distribution"):
            return "Logistics Expense"
        return "Other Opex"

    if high_level == "asset":
        if _kw(name_text, "cash", "bank"):
            return "Cash & Cash Equivalents"
        if _kw(name_text, "receivable"):
            return "Accounts Receivable"
        if _kw(name_text, "inventory", "finished goods", "stock"):
            return "Inventory"
        return "Other Current Asset"

    if high_level == "liability":
        if _kw(name_text, "payable"):
            return "Accounts Payable"
        if _kw(name_text, "accrued"):
            return "Accrued Liabilities"
        return "Other Current Liability"

    if high_level == "equity":
        return "Equity"

    # ---- Fallback: structured category was blank/unrecognized -------------
    if _kw(full_text, "return", "refund", "allowance", "contra"):
        return "Sales Returns"
    if _kw(full_text, "revenue", "sales income", "net sales"):
        return "Gross Revenue"
    if _kw(full_text, "raw material", "fabric", "bom", "material cost"):
        return "Raw Materials COGS"
    if _kw(full_text, "direct labor", "labor", "wages", "stitching", "production labor"):
        return "Direct Labor COGS"
    if _kw(full_text, "freight", "inbound shipping", "shipping cogs", "outbound freight"):
        return "Freight COGS"
    if _kw(full_text, "cogs", "cost of goods"):
        return "Other COGS"
    if _kw(full_text, "marketing", "advertising", "promotion"):
        return "Marketing Expense"
    if _kw(full_text, "logistics", "warehousing", "distribution expense"):
        return "Logistics Expense"
    if _kw(full_text, "operating expense", "opex", "admin", "overhead", "rent",
           "utilities", "depreciation", "insurance", "salaries", "g&a"):
        return "Other Opex"
    if _kw(full_text, "cash", "bank"):
        return "Cash & Cash Equivalents"
    if _kw(full_text, "receivable"):
        return "Accounts Receivable"
    if _kw(full_text, "inventory", "finished goods"):
        return "Inventory"
    if _kw(full_text, "payable"):
        return "Accounts Payable"
    if _kw(full_text, "accrued"):
        return "Accrued Liabilities"
    if _kw(full_text, "equity", "retained earnings", "capital stock", "common stock"):
        return "Equity"
    if _kw(full_text, "asset"):
        return "Other Current Asset"
    if _kw(full_text, "liability"):
        return "Other Current Liability"
    if _kw(full_text, "expense"):
        return "Other Opex"

    return "Unclassified"


NORMAL_BALANCE_MAP = {
    # bucket -> "debit" (increases with Debit) or "credit" (increases with Credit)
    "Gross Revenue": "credit",
    "Sales Returns": "debit",
    "Raw Materials COGS": "debit",
    "Direct Labor COGS": "debit",
    "Freight COGS": "debit",
    "Other COGS": "debit",
    "Marketing Expense": "debit",
    "Logistics Expense": "debit",
    "Other Opex": "debit",
    "Cash & Cash Equivalents": "debit",
    "Accounts Receivable": "debit",
    "Inventory": "debit",
    "Accounts Payable": "credit",
    "Accrued Liabilities": "credit",
    "Equity": "credit",
    "Other Current Asset": "debit",
    "Other Current Liability": "credit",
    "Unclassified": "debit",
}

PNL_REVENUE_BUCKETS = ["Gross Revenue", "Sales Returns"]
PNL_COGS_BUCKETS = ["Raw Materials COGS", "Direct Labor COGS", "Freight COGS", "Other COGS"]
PNL_OPEX_BUCKETS = ["Marketing Expense", "Logistics Expense", "Other Opex"]
BS_CURRENT_ASSET_BUCKETS = ["Cash & Cash Equivalents", "Accounts Receivable", "Inventory", "Other Current Asset"]
BS_CURRENT_LIAB_BUCKETS = ["Accounts Payable", "Accrued Liabilities", "Other Current Liability"]


@st.cache_data(show_spinner="Classifying GL accounts & preparing dataset...")
def prepare_master_dataset(_frames_key: str, gl: pd.DataFrame, coa: pd.DataFrame,
                            sku: pd.DataFrame) -> pd.DataFrame:
    """
    Joins the GL journal to the Chart of Accounts, classifies every line into
    a standardized financial-statement bucket, and computes a signed 'Amount'
    column ( positive = increases the natural balance of that bucket ).
    """
    gl = gl.copy()
    coa = coa.copy()

    gl["GL Code"] = gl["GL Code"].astype(str).str.strip()
    coa["GL Code"] = coa["GL Code"].astype(str).str.strip()

    gl["Posting Date"] = pd.to_datetime(gl["Posting Date"], errors="coerce")
    gl["Debit (₹)"] = pd.to_numeric(gl["Debit (₹)"], errors="coerce").fillna(0.0)
    gl["Credit (₹)"] = pd.to_numeric(gl["Credit (₹)"], errors="coerce").fillna(0.0)

    merged = gl.merge(
        coa[["GL Code", "Account Name", "Account Category", "Normal Balance"]],
        on="GL Code", how="left", suffixes=("", "_coa"),
    )

    merged["Bucket"] = merged.apply(_classify_account, axis=1)
    merged["Balance Direction"] = merged["Bucket"].map(NORMAL_BALANCE_MAP).fillna("debit")

    merged["Amount"] = np.where(
        merged["Balance Direction"] == "debit",
        merged["Debit (₹)"] - merged["Credit (₹)"],
        merged["Credit (₹)"] - merged["Debit (₹)"],
    )

    merged["Month"] = merged["Posting Date"].dt.to_period("M").astype(str)
    merged["Month Label"] = merged["Posting Date"].dt.strftime("%b %Y")

    # Attach SKU master attributes where a SKU reference exists
    sku_clean = sku.copy()
    sku_clean["SKU Code"] = sku_clean["SKU Code"].astype(str).str.strip()
    merged["SKU Reference"] = merged["SKU Reference"].astype(str).str.strip()
    merged = merged.merge(
        sku_clean.rename(columns={
            "Product Name": "SKU Product Name",
            "Target Segment": "SKU Target Segment",
            "Category": "SKU Master Category",
        }),
        left_on="SKU Reference", right_on="SKU Code", how="left", suffixes=("", "_sku"),
    )

    # Prefer the GL's own Category column; fall back to SKU master category
    merged["Product Category"] = merged["Category"].where(
        merged["Category"].notna() & (merged["Category"].astype(str).str.strip() != ""),
        merged["SKU Master Category"],
    )

    return merged


# =============================================================================
# 3. FINANCIAL AGGREGATION FUNCTIONS
# =============================================================================

def month_options(df: pd.DataFrame) -> list:
    valid = df.dropna(subset=["Posting Date"])
    periods = sorted(valid["Posting Date"].dt.to_period("M").unique())
    return [p.strftime("%b %Y") for p in periods]


def filter_by_period(df: pd.DataFrame, period_label: str) -> pd.DataFrame:
    """period_label is either 'H1 2026 (Cumulative)' or a 'Mon YYYY' label."""
    if period_label.startswith("H1") or period_label.lower().startswith("cumulative"):
        return df
    return df[df["Month Label"] == period_label]


def bucket_sum(df: pd.DataFrame, buckets: list) -> float:
    if not buckets:
        return 0.0
    return float(df.loc[df["Bucket"].isin(buckets), "Amount"].sum())


def compute_pnl(df: pd.DataFrame) -> dict:
    gross_revenue = bucket_sum(df, ["Gross Revenue"])
    returns = bucket_sum(df, ["Sales Returns"])
    net_revenue = gross_revenue - returns

    raw_cogs = bucket_sum(df, ["Raw Materials COGS"])
    labor_cogs = bucket_sum(df, ["Direct Labor COGS"])
    freight_cogs = bucket_sum(df, ["Freight COGS"])
    other_cogs = bucket_sum(df, ["Other COGS"])
    total_cogs = raw_cogs + labor_cogs + freight_cogs + other_cogs

    gross_profit = net_revenue - total_cogs

    marketing = bucket_sum(df, ["Marketing Expense"])
    logistics = bucket_sum(df, ["Logistics Expense"])
    other_opex = bucket_sum(df, ["Other Opex"])
    total_opex = marketing + logistics + other_opex

    ebitda = gross_profit - total_opex
    net_income = ebitda  # No separate D&A/interest/tax buckets in source schema

    gross_margin = safe_div(gross_profit, net_revenue)
    ebitda_margin = safe_div(ebitda, net_revenue)
    net_margin = safe_div(net_income, net_revenue)

    return dict(
        gross_revenue=gross_revenue, returns=returns, net_revenue=net_revenue,
        raw_cogs=raw_cogs, labor_cogs=labor_cogs, freight_cogs=freight_cogs,
        other_cogs=other_cogs, total_cogs=total_cogs, gross_profit=gross_profit,
        marketing=marketing, logistics=logistics, other_opex=other_opex,
        total_opex=total_opex, ebitda=ebitda, net_income=net_income,
        gross_margin=gross_margin, ebitda_margin=ebitda_margin, net_margin=net_margin,
    )


def compute_balance_sheet(df_cumulative: pd.DataFrame) -> dict:
    """Balance sheet is always a point-in-time (cumulative-to-date) snapshot."""
    cash = bucket_sum(df_cumulative, ["Cash & Cash Equivalents"])
    ar = bucket_sum(df_cumulative, ["Accounts Receivable"])
    inventory = bucket_sum(df_cumulative, ["Inventory"])
    other_ca = bucket_sum(df_cumulative, ["Other Current Asset"])
    current_assets = cash + ar + inventory + other_ca

    ap = bucket_sum(df_cumulative, ["Accounts Payable"])
    accrued = bucket_sum(df_cumulative, ["Accrued Liabilities"])
    other_cl = bucket_sum(df_cumulative, ["Other Current Liability"])
    current_liabilities = ap + accrued + other_cl

    current_ratio = safe_div(current_assets, current_liabilities)
    quick_assets = current_assets - inventory
    quick_ratio = safe_div(quick_assets, current_liabilities)
    working_capital = current_assets - current_liabilities

    return dict(
        cash=cash, ar=ar, inventory=inventory, other_ca=other_ca,
        current_assets=current_assets, ap=ap, accrued=accrued, other_cl=other_cl,
        current_liabilities=current_liabilities, current_ratio=current_ratio,
        quick_ratio=quick_ratio, working_capital=working_capital,
    )


def compute_cash_flow(df_period: pd.DataFrame) -> dict:
    cash_lines = df_period[df_period["Bucket"] == "Cash & Cash Equivalents"]
    inflows = float(cash_lines.loc[cash_lines["Amount"] > 0, "Amount"].sum())
    outflows = float(-cash_lines.loc[cash_lines["Amount"] < 0, "Amount"].sum())
    net_cash_flow = inflows - outflows
    return dict(inflows=inflows, outflows=outflows, net_cash_flow=net_cash_flow)


def health_rating(pnl: dict, bs: dict) -> tuple:
    """Returns (rating, color, reasons[])."""
    reasons = []
    critical = False
    watchlist = False

    if bs["current_ratio"] < 1.0:
        critical = True
        reasons.append(f"Current Ratio of {bs['current_ratio']:.2f} is below 1.00x - the "
                        f"company cannot cover current liabilities with current assets.")
    if pnl["gross_margin"] < 0:
        critical = True
        reasons.append(f"Gross Margin is negative ({fmt_pct(pnl['gross_margin'])}) - "
                        f"products are being sold below cost on average.")

    if not critical:
        if bs["current_ratio"] < 1.5:
            watchlist = True
            reasons.append(f"Current Ratio of {bs['current_ratio']:.2f} is thin (below 1.50x).")
        if pnl["gross_margin"] < 0.15:
            watchlist = True
            reasons.append(f"Gross Margin of {fmt_pct(pnl['gross_margin'])} is compressed (below 15%).")
        if pnl["ebitda_margin"] < 0:
            watchlist = True
            reasons.append(f"EBITDA Margin is negative ({fmt_pct(pnl['ebitda_margin'])}).")

    if critical:
        return "CRITICAL", TERRACOTTA, reasons
    if watchlist:
        return "WATCHLIST", AMBER, reasons
    return "HEALTHY", EMERALD, ["All core liquidity and profitability thresholds are within healthy range."]


def compute_sku_economics(df_period: pd.DataFrame) -> pd.DataFrame:
    """
    Builds a per-SKU P&L: Net Revenue, Total COGS, Gross Profit, allocated
    Opex (allocated proportional to each SKU's share of gross revenue), and
    resulting Operating Profit/Loss.
    """
    sku_rows = df_period[df_period["SKU Reference"].notna() &
                          (df_period["SKU Reference"].astype(str).str.strip() != "") &
                          (df_period["SKU Reference"].astype(str).str.lower() != "nan")]

    if sku_rows.empty:
        return pd.DataFrame(columns=[
            "SKU Code", "Product Name", "Category", "Gross Revenue", "Returns",
            "Net Revenue", "Raw Materials COGS", "Direct Labor COGS", "Freight COGS",
            "Total COGS", "Gross Profit", "Gross Margin %", "Allocated Opex",
            "Operating Profit", "Cost Coverage Ratio", "Status",
        ])

    grp = sku_rows.groupby("SKU Reference")

    def bucket_series(bucket_name):
        return grp.apply(lambda g: float(g.loc[g["Bucket"] == bucket_name, "Amount"].sum()),
                          include_groups=False)

    gross_revenue = bucket_series("Gross Revenue")
    returns = bucket_series("Sales Returns")
    raw_cogs = bucket_series("Raw Materials COGS")
    labor_cogs = bucket_series("Direct Labor COGS")
    freight_cogs = bucket_series("Freight COGS")

    result = pd.DataFrame({
        "Gross Revenue": gross_revenue,
        "Returns": returns,
        "Raw Materials COGS": raw_cogs,
        "Direct Labor COGS": labor_cogs,
        "Freight COGS": freight_cogs,
    }).fillna(0.0)

    result["Net Revenue"] = result["Gross Revenue"] - result["Returns"]
    result["Total COGS"] = (result["Raw Materials COGS"] + result["Direct Labor COGS"]
                             + result["Freight COGS"])
    result["Gross Profit"] = result["Net Revenue"] - result["Total COGS"]
    result["Gross Margin %"] = result.apply(
        lambda r: safe_div(r["Gross Profit"], r["Net Revenue"]), axis=1)

    # Allocate total company opex proportional to each SKU's share of gross revenue
    total_opex = bucket_sum(df_period, PNL_OPEX_BUCKETS)
    total_gross_rev = result["Gross Revenue"].sum()
    result["Allocated Opex"] = result["Gross Revenue"].apply(
        lambda x: total_opex * safe_div(x, total_gross_rev))

    result["Operating Profit"] = result["Gross Profit"] - result["Allocated Opex"]
    result["Cost Coverage Ratio"] = result.apply(
        lambda r: safe_div(r["Total COGS"], r["Net Revenue"]), axis=1)
    result["Status"] = np.where(
        result["Cost Coverage Ratio"] > 1.0, "⚠️ Cost Exceeds Price", "OK")

    result = result.reset_index().rename(columns={"SKU Reference": "SKU Code"})

    # Attach master attributes
    sku_master_df = st.session_state.get("_sku_master_df")
    if sku_master_df is not None:
        lookup = sku_master_df.set_index(sku_master_df["SKU Code"].astype(str).str.strip())
        result["Product Name"] = result["SKU Code"].map(lookup["Product Name"])
        result["Category"] = result["SKU Code"].map(lookup["Category"])
    else:
        result["Product Name"] = result["SKU Code"]
        result["Category"] = "Unknown"

    cols = ["SKU Code", "Product Name", "Category", "Gross Revenue", "Returns",
            "Net Revenue", "Raw Materials COGS", "Direct Labor COGS", "Freight COGS",
            "Total COGS", "Gross Profit", "Gross Margin %", "Allocated Opex",
            "Operating Profit", "Cost Coverage Ratio", "Status"]
    return result[cols].sort_values("Operating Profit")


# =============================================================================
# 4. SIDEBAR / DATA SOURCE
# =============================================================================

def sidebar_data_source() -> Optional[dict]:
    st.sidebar.markdown("## \U0001F457 Sunday Somewear")
    st.sidebar.caption("Financial Health & Executive MIS Dashboard")
    st.sidebar.markdown("---")

    uploaded = st.sidebar.file_uploader(
        "Upload GL Database workbook (.xlsx)",
        type=["xlsx"],
        help=f"Expected file: {DATA_FILE}. If not uploaded, the app will look "
             f"for this file in its working directory.",
    )

    try:
        if uploaded is not None:
            frames = load_workbook(DATA_FILE, file_bytes=uploaded.getvalue())
            st.sidebar.success(f"Loaded workbook from upload: {uploaded.name}")
        else:
            frames = load_workbook(DATA_FILE)
            st.sidebar.success(f"Loaded workbook: {DATA_FILE}")
    except DataLoadError as exc:
        st.sidebar.error("Data load failed - see main panel for details.")
        st.error(f"### ⚠️ Unable to Load Financial Data\n\n{exc}")
        st.info(
            "**Expected workbook structure:**\n\n"
            "- Tab **'GL Journal Entries'**: Entry ID, Posting Date, GL Code, "
            "GL Account Name, Account Type, Category, SKU Reference, Description, "
            "Document Ref, Debit (₹), Credit (₹)\n"
            "- Tab **'Chart of Accounts'**: GL Code, Account Name, Account Category, "
            "Normal Balance\n"
            "- Tab **'SKU Master List'**: Category, SKU Code, Product Name, Target Segment"
        )
        return None
    except Exception as exc:  # noqa: BLE001
        st.sidebar.error("Unexpected error loading data.")
        st.error(f"### ⚠️ Unexpected Error\n\n`{type(exc).__name__}: {exc}`")
        return None

    return frames


# =============================================================================
# 5. MODULE 1: EXECUTIVE FINANCIAL HEALTH & SOLVENCY SCORECARD
# =============================================================================

def render_module_1(master: pd.DataFrame):
    st.header("\U0001F3E5 Executive Financial Health & Solvency Scorecard")
    st.caption("Consolidated H1 2026 (January - June) performance snapshot")

    pnl = compute_pnl(master)
    bs = compute_balance_sheet(master)
    cf = compute_cash_flow(master)
    rating, color, reasons = health_rating(pnl, bs)

    # ---- KPI Row 1 ----------------------------------------------------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Net Revenue", fmt_currency(pnl["net_revenue"]))
    c2.metric("Gross Margin %", fmt_pct(pnl["gross_margin"]))
    c3.metric("EBITDA Margin %", fmt_pct(pnl["ebitda_margin"]))
    c4.metric("Current Ratio", f"{bs['current_ratio']:.2f}x")

    c5, c6, c7 = st.columns(3)
    c5.metric("Quick Ratio", f"{bs['quick_ratio']:.2f}x")
    c6.metric("Total Accounts Payable", fmt_currency(bs["ap"]))
    c7.metric("Net Cash Flow", fmt_currency(cf["net_cash_flow"]))

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # ---- Health Rating --------------------------------------------------
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.markdown("#### Overall Business Health Rating")
        st.markdown(
            f"<span class='health-badge' style='background-color:{color};'>{rating}</span>",
            unsafe_allow_html=True,
        )
        st.markdown("")
        st.markdown(
            f"""
            <div style='font-size:0.85rem; color:{TEXT_MUTED}; margin-top:10px;'>
            <b>Scoring rules:</b><br>
            &bull; Current Ratio &lt; 1.00x <b>or</b> Gross Margin &lt; 0% &rarr; CRITICAL<br>
            &bull; Current Ratio &lt; 1.50x <b>or</b> Gross Margin &lt; 15% <b>or</b>
            EBITDA Margin &lt; 0% &rarr; WATCHLIST<br>
            &bull; Otherwise &rarr; HEALTHY
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_b:
        gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=bs["current_ratio"],
            number={"suffix": "x", "valueformat": ".2f"},
            title={"text": "Current Ratio (Liquidity)"},
            gauge={
                "axis": {"range": [0, max(3, bs["current_ratio"] + 0.5)]},
                "bar": {"color": NAVY},
                "steps": [
                    {"range": [0, 1.0], "color": "#FBE3E2"},
                    {"range": [1.0, 1.5], "color": "#FCF1DC"},
                    {"range": [1.5, max(3, bs["current_ratio"] + 0.5)], "color": "#E6F4E6"},
                ],
                "threshold": {"line": {"color": TERRACOTTA, "width": 3}, "value": 1.0},
            },
        ))
        gauge.update_layout(height=230, margin=dict(l=20, r=20, t=40, b=10))
        st.plotly_chart(gauge, width="stretch")

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # ---- Executive Summary & Risk Commentary -----------------------------
    st.markdown("#### \U0001F4CB Executive Summary & Risk Commentary")

    sku_econ = compute_sku_economics(master)
    cat_summary = master.groupby("Product Category").apply(
        lambda g: pd.Series({
            "Net Revenue": bucket_sum(g, ["Gross Revenue"]) - bucket_sum(g, ["Sales Returns"]),
            "Total COGS": bucket_sum(g, PNL_COGS_BUCKETS),
        }), include_groups=False,
    )
    cat_summary = cat_summary[~cat_summary.index.isin(["Corporate", None, "nan", ""])]
    cat_summary["Gross Profit"] = cat_summary["Net Revenue"] - cat_summary["Total COGS"]

    runway_months = safe_div(bs["cash"], cf["outflows"]) if cf["outflows"] else float("inf")

    bullets = []
    bullets.append(
        f"**Unit economics:** Company-wide gross margin stands at "
        f"**{fmt_pct(pnl['gross_margin'])}** on net revenue of **{fmt_currency(pnl['net_revenue'])}**, "
        f"with EBITDA margin of **{fmt_pct(pnl['ebitda_margin'])}** "
        f"({fmt_currency(pnl['ebitda'])} EBITDA)."
    )
    bullets.append(
        f"**Cash runway vs. supplier liabilities:** Cash & equivalents of "
        f"**{fmt_currency(bs['cash'])}** against Accounts Payable of "
        f"**{fmt_currency(bs['ap'])}** implies a Current Ratio of **{bs['current_ratio']:.2f}x** "
        + ("(a working-capital deficit of "
           f"{fmt_currency(abs(bs['working_capital']))} exists)."
           if bs["working_capital"] < 0 else
           f"and positive working capital of {fmt_currency(bs['working_capital'])}.")
    )
    if not sku_econ.empty:
        worst = sku_econ.iloc[0]
        underwater = sku_econ[sku_econ["Status"].str.contains("Exceeds")]
        bullets.append(
            f"**Category performance:** " + (
                " vs. ".join(
                    f"**{idx}** ({fmt_currency(row['Net Revenue'])} revenue, "
                    f"{fmt_pct(safe_div(row['Gross Profit'], row['Net Revenue']))} gross margin)"
                    for idx, row in cat_summary.iterrows()
                ) if not cat_summary.empty else "insufficient category-level data."
            )
        )
        bullets.append(
            f"**Loss-driver alert:** {len(underwater)} SKU(s) currently have production cost "
            f"exceeding net sales price, led by **{worst['Product Name']}** "
            f"(Operating Profit of {fmt_currency(worst['Operating Profit'], allow_negative_parens=True)})."
            if not underwater.empty else
            "**Loss-driver alert:** No SKUs currently show cost exceeding sales price - "
            "unit economics are structurally sound across the portfolio."
        )
    bullets.append(
        f"**Liquidity outlook:** At the current monthly cash burn of "
        f"{fmt_currency(safe_div(cf['outflows'], max(1, master['Month'].nunique())))}, "
        f"available cash covers roughly **{runway_months:.1f} months** of operating outflows."
        if runway_months != float("inf") else
        "**Liquidity outlook:** No cash outflows recorded in the selected period."
    )
    for r in reasons:
        bullets.append(f"**Risk flag:** {r}")

    st.markdown(
        "<div class='commentary-box'>" +
        "".join(f"<p style='margin-bottom:8px;'>&bull; {b}</p>" for b in bullets) +
        "</div>",
        unsafe_allow_html=True,
    )


# =============================================================================
# 6. MODULE 2: MONTHLY MIS FINANCIAL STATEMENTS
# =============================================================================

def render_module_2(master: pd.DataFrame):
    st.header("\U0001F4D2 Monthly MIS Financial Statements")

    months = month_options(master)
    period = st.selectbox(
        "Select reporting period",
        ["H1 2026 (Cumulative)"] + months,
        index=0,
    )

    period_df = filter_by_period(master, period)
    cumulative_df = master[master["Month Label"].isin(
        months[: months.index(period) + 1] if period in months else months
    )]

    pnl = compute_pnl(period_df)
    bs = compute_balance_sheet(cumulative_df)  # BS is always as-of cumulative
    cf = compute_cash_flow(period_df)

    tab_pnl, tab_bs, tab_cf = st.tabs(["\U0001F4C8 P&L Statement", "\U0001F4CA Balance Sheet", "\U0001F4B5 Cash Flow"])

    with tab_pnl:
        st.subheader(f"Condensed Profit & Loss - {period}")
        pnl_rows = [
            ("Gross Revenue", pnl["gross_revenue"]),
            ("(-) Returns", -pnl["returns"]),
            ("Net Revenue", pnl["net_revenue"]),
            ("(-) Raw Materials COGS", -pnl["raw_cogs"]),
            ("(-) Direct Labor COGS", -pnl["labor_cogs"]),
            ("(-) Freight COGS", -pnl["freight_cogs"]),
            ("(-) Other COGS", -pnl["other_cogs"]),
            ("Total COGS", -pnl["total_cogs"]),
            ("Gross Profit", pnl["gross_profit"]),
            ("(-) Marketing Expense", -pnl["marketing"]),
            ("(-) Logistics Expense", -pnl["logistics"]),
            ("(-) Other Operating Expense", -pnl["other_opex"]),
            ("Total Operating Expenses", -pnl["total_opex"]),
            ("EBITDA", pnl["ebitda"]),
            ("Net Income", pnl["net_income"]),
        ]
        bold_rows = {"Net Revenue", "Total COGS", "Gross Profit", "Total Operating Expenses",
                     "EBITDA", "Net Income"}
        pnl_df = pd.DataFrame(pnl_rows, columns=["Line Item", "Amount"])
        pnl_df["Formatted"] = pnl_df["Amount"].apply(lambda v: fmt_currency(v, allow_negative_parens=True))

        def style_pnl(row):
            style = "font-weight:700; background-color:#EEF3F9;" if row["Line Item"] in bold_rows else ""
            return [style] * len(row)

        st.dataframe(
            pnl_df[["Line Item", "Formatted"]].rename(columns={"Formatted": "Amount (₹)"})
            .style.apply(style_pnl, axis=1),
            width="stretch", hide_index=True, height=560,
        )

        m1, m2, m3 = st.columns(3)
        m1.metric("Gross Margin %", fmt_pct(pnl["gross_margin"]))
        m2.metric("EBITDA Margin %", fmt_pct(pnl["ebitda_margin"]))
        m3.metric("Net Margin %", fmt_pct(pnl["net_margin"]))

    with tab_bs:
        st.subheader(f"Balance Sheet Snapshot - as of end of {period if period in months else months[-1] if months else period}")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Current Assets**")
            bs_assets = pd.DataFrame([
                ("Cash & Cash Equivalents", bs["cash"]),
                ("Accounts Receivable", bs["ar"]),
                ("Inventory", bs["inventory"]),
                ("Other Current Assets", bs["other_ca"]),
                ("Total Current Assets", bs["current_assets"]),
            ], columns=["Line Item", "Amount"])
            bs_assets["Amount (₹)"] = bs_assets["Amount"].apply(fmt_currency)
            st.dataframe(bs_assets[["Line Item", "Amount (₹)"]], hide_index=True, width="stretch")
        with col2:
            st.markdown("**Current Liabilities**")
            bs_liab = pd.DataFrame([
                ("Accounts Payable", bs["ap"]),
                ("Accrued Liabilities", bs["accrued"]),
                ("Other Current Liabilities", bs["other_cl"]),
                ("Total Current Liabilities", bs["current_liabilities"]),
            ], columns=["Line Item", "Amount"])
            bs_liab["Amount (₹)"] = bs_liab["Amount"].apply(fmt_currency)
            st.dataframe(bs_liab[["Line Item", "Amount (₹)"]], hide_index=True, width="stretch")

        st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
        k1, k2, k3 = st.columns(3)
        k1.metric("Current Ratio", f"{bs['current_ratio']:.2f}x")
        k2.metric("Quick Ratio", f"{bs['quick_ratio']:.2f}x")
        wc_label = "Working Capital Deficit" if bs["working_capital"] < 0 else "Working Capital Surplus"
        k3.metric(wc_label, fmt_currency(abs(bs["working_capital"])))
        if bs["working_capital"] < 0:
            st.warning(
                f"⚠️ Working capital deficit of **{fmt_currency(abs(bs['working_capital']))}** - "
                f"current liabilities exceed current assets."
            )

    with tab_cf:
        st.subheader(f"Cash Flow Highlights - {period}")
        cfc1, cfc2, cfc3 = st.columns(3)
        cfc1.metric("Cash Collected (Inflows)", fmt_currency(cf["inflows"]))
        cfc2.metric("Expenses Paid (Outflows)", fmt_currency(cf["outflows"]))
        cfc3.metric("Net Operating Cash Flow", fmt_currency(cf["net_cash_flow"]))

        waterfall = go.Figure(go.Waterfall(
            orientation="v",
            measure=["relative", "relative", "total"],
            x=["Cash Inflows", "Cash Outflows", "Net Cash Flow"],
            y=[cf["inflows"], -cf["outflows"], 0],
            connector={"line": {"color": TEXT_MUTED}},
            increasing={"marker": {"color": EMERALD}},
            decreasing={"marker": {"color": TERRACOTTA}},
            totals={"marker": {"color": NAVY}},
            text=[fmt_currency(cf["inflows"]), fmt_currency(-cf["outflows"]), fmt_currency(cf["net_cash_flow"])],
            textposition="outside",
        ))
        waterfall.update_layout(
            title=f"Cash Flow Waterfall - {period}",
            height=420, margin=dict(l=20, r=20, t=60, b=20),
            plot_bgcolor="white",
        )
        st.plotly_chart(waterfall, width="stretch")


# =============================================================================
# 7. MODULE 3: MoM & PERIOD-OVER-PERIOD VARIANCE ANALYSIS
# =============================================================================

def render_module_3(master: pd.DataFrame):
    st.header("\U0001F50D Interactive MoM & Period-over-Period Variance Analysis")

    months = month_options(master)
    if len(months) < 2:
        st.info("At least two distinct months of data are required for variance analysis.")
        return

    col1, col2 = st.columns(2)
    with col1:
        base_period = st.selectbox("Base Period", months, index=max(0, len(months) - 2))
    with col2:
        comp_period = st.selectbox("Comparison Period", months, index=len(months) - 1)

    base_df = master[master["Month Label"] == base_period]
    comp_df = master[master["Month Label"] == comp_period]

    base_pnl = compute_pnl(base_df)
    comp_pnl = compute_pnl(comp_df)

    line_items = [
        ("Gross Revenue", "gross_revenue", "higher_better"),
        ("Returns", "returns", "lower_better"),
        ("Net Revenue", "net_revenue", "higher_better"),
        ("Raw Materials COGS", "raw_cogs", "lower_better"),
        ("Direct Labor COGS", "labor_cogs", "lower_better"),
        ("Freight COGS", "freight_cogs", "lower_better"),
        ("Total COGS", "total_cogs", "lower_better"),
        ("Gross Profit", "gross_profit", "higher_better"),
        ("Marketing Expense", "marketing", "lower_better"),
        ("Logistics Expense", "logistics", "lower_better"),
        ("Total Operating Expenses", "total_opex", "lower_better"),
        ("EBITDA", "ebitda", "higher_better"),
        ("Net Income", "net_income", "higher_better"),
    ]

    rows = []
    for label, key, direction in line_items:
        base_val = base_pnl[key]
        comp_val = comp_pnl[key]
        variance = comp_val - base_val
        variance_pct = safe_div(variance, abs(base_val)) if base_val != 0 else 0.0

        favorable = (variance >= 0) if direction == "higher_better" else (variance <= 0)
        if abs(variance_pct) < 0.0001:
            impact = "Flat"
        else:
            impact = "Favorable" if favorable else "Unfavorable"

        rows.append({
            "Line Item": label,
            "Base Period (₹)": base_val,
            "Comparison Period (₹)": comp_val,
            "Variance (₹)": variance,
            "Variance (%)": variance_pct,
            "Impact": impact,
        })

    var_df = pd.DataFrame(rows)

    display_df = var_df.copy()
    display_df["Base Period (₹)"] = display_df["Base Period (₹)"].apply(lambda v: fmt_currency(v, True))
    display_df["Comparison Period (₹)"] = display_df["Comparison Period (₹)"].apply(lambda v: fmt_currency(v, True))
    display_df["Variance (₹)"] = display_df["Variance (₹)"].apply(lambda v: fmt_currency(v, True))
    display_df["Variance (%)"] = var_df["Variance (%)"].apply(fmt_pct)

    def highlight_variance(row):
        idx = row.name
        pct = var_df.loc[idx, "Variance (%)"]
        impact = var_df.loc[idx, "Impact"]
        style = ""
        if abs(pct) >= 0.05:
            if impact == "Unfavorable":
                style = f"background-color:#FBE3E2; color:{TERRACOTTA}; font-weight:600;"
            elif impact == "Favorable":
                style = f"background-color:#E6F4E6; color:#2E7D32; font-weight:600;"
        return [style] * len(row)

    st.caption(
        f"Comparing **{base_period}** (Base) vs. **{comp_period}** (Comparison). "
        f"Rows with |variance| ≥ 5% are highlighted: "
        f"🟥 red = unfavorable, 🟩 green = favorable."
    )
    st.dataframe(
        display_df.style.apply(highlight_variance, axis=1),
        width="stretch", hide_index=True, height=520,
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(name=base_period, x=var_df["Line Item"], y=var_df["Base Period (₹)"],
                          marker_color=NAVY))
    fig.add_trace(go.Bar(name=comp_period, x=var_df["Line Item"], y=var_df["Comparison Period (₹)"],
                          marker_color=TERRACOTTA))
    fig.update_layout(
        barmode="group", height=440, title="Base vs. Comparison Period - Key Line Items",
        plot_bgcolor="white", xaxis_tickangle=-35, margin=dict(l=20, r=20, t=60, b=100),
        colorway=CHART_COLORWAY,
    )
    st.plotly_chart(fig, width="stretch")


# =============================================================================
# 8. MODULE 4: ROOT-CAUSE DIAGNOSTICS & PARETO (80/20) ANALYTICS
# =============================================================================

def render_module_4(master: pd.DataFrame):
    st.header("\U0001F9EA Root-Cause Diagnostics & Pareto (80/20) Analytics")

    sku_econ = compute_sku_economics(master)

    if sku_econ.empty:
        st.info("No SKU-referenced GL entries were found in the selected data.")
        return

    # ---- 80/20 Pareto of operating losses ---------------------------------
    st.subheader("80/20 Loss Driver Identification")
    losses = sku_econ[sku_econ["Operating Profit"] < 0].copy()
    losses["Loss (₹)"] = -losses["Operating Profit"]
    losses = losses.sort_values("Loss (₹)", ascending=False)

    if losses.empty:
        st.success("✅ No SKUs are currently operating-loss makers - no Pareto loss drivers to display.")
    else:
        losses["Cumulative Loss (₹)"] = losses["Loss (₹)"].cumsum()
        total_loss = losses["Loss (₹)"].sum()
        losses["Cumulative %"] = losses["Cumulative Loss (₹)"] / total_loss

        n_skus = len(losses)
        cutoff_idx = max(1, int(np.ceil(n_skus * 0.2)))
        losses["Pareto Zone"] = ["Top 20% Drivers" if i < cutoff_idx else "Remaining SKUs"
                                  for i in range(n_skus)]

        pareto_fig = go.Figure()
        pareto_fig.add_trace(go.Bar(
            x=losses["Product Name"], y=losses["Loss (₹)"], name="Operating Loss (₹)",
            marker_color=[TERRACOTTA if z == "Top 20% Drivers" else "#E8A9A7" for z in losses["Pareto Zone"]],
            yaxis="y1",
        ))
        pareto_fig.add_trace(go.Scatter(
            x=losses["Product Name"], y=losses["Cumulative %"] * 100, name="Cumulative %",
            mode="lines+markers", marker_color=NAVY, yaxis="y2",
        ))
        pareto_fig.add_hline(y=80, line_dash="dash", line_color=NAVY_DARK, yref="y2",
                              annotation_text="80% threshold")
        pareto_fig.update_layout(
            title="Pareto Analysis: SKU Contribution to Total Operating Losses",
            yaxis=dict(title="Operating Loss (₹)"),
            yaxis2=dict(title="Cumulative %", overlaying="y", side="right", range=[0, 110]),
            height=460, plot_bgcolor="white", xaxis_tickangle=-35,
            margin=dict(l=20, r=20, t=60, b=110), legend=dict(orientation="h", y=1.12),
        )
        st.plotly_chart(pareto_fig, width="stretch")

        top_driver_skus = losses.iloc[:cutoff_idx]
        top_share = top_driver_skus["Loss (₹)"].sum() / total_loss
        st.caption(
            f"**{cutoff_idx} SKU(s)** (top 20% by loss magnitude) account for "
            f"**{fmt_pct(top_share)}** of total operating losses "
            f"({fmt_currency(top_driver_skus['Loss (₹)'].sum())} of {fmt_currency(total_loss)})."
        )

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # ---- Category Breakdown ------------------------------------------------
    st.subheader("Category Breakdown: Revenue vs. Cost")
    cat_econ = sku_econ.groupby("Category").agg(
        {"Net Revenue": "sum", "Total COGS": "sum", "Allocated Opex": "sum", "Operating Profit": "sum"}
    ).reset_index()

    if cat_econ.empty:
        st.info("No categorized SKU data available.")
    else:
        cat_fig = go.Figure()
        cat_fig.add_trace(go.Bar(name="Net Revenue", x=cat_econ["Category"], y=cat_econ["Net Revenue"],
                                  marker_color=NAVY))
        cat_fig.add_trace(go.Bar(name="Total COGS", x=cat_econ["Category"], y=cat_econ["Total COGS"],
                                  marker_color=TERRACOTTA))
        cat_fig.add_trace(go.Bar(name="Allocated Opex", x=cat_econ["Category"], y=cat_econ["Allocated Opex"],
                                  marker_color=AMBER))
        cat_fig.update_layout(
            barmode="group", height=420, title="Vacationwear vs. Workwear - Revenue vs. Cost",
            plot_bgcolor="white", margin=dict(l=20, r=20, t=60, b=20),
        )
        st.plotly_chart(cat_fig, width="stretch")

        cat_display = cat_econ.copy()
        for c in ["Net Revenue", "Total COGS", "Allocated Opex", "Operating Profit"]:
            cat_display[c] = cat_display[c].apply(lambda v: fmt_currency(v, True))
        st.dataframe(cat_display, hide_index=True, width="stretch")

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # ---- Price vs Cost Diagnostics -----------------------------------------
    st.subheader("Price vs. Cost Diagnostics (BOM Cost Exceeding Sales Price)")
    underwater = sku_econ[sku_econ["Status"].str.contains("Exceeds")]

    scatter = px.scatter(
        sku_econ, x="Net Revenue", y="Total COGS", size=sku_econ["Total COGS"].abs().clip(lower=1),
        color="Status", text="Product Name",
        color_discrete_map={"OK": EMERALD, "⚠️ Cost Exceeds Price": TERRACOTTA},
        hover_data={"SKU Code": True, "Cost Coverage Ratio": ":.2%"},
    )
    max_axis = max(sku_econ["Net Revenue"].max(), sku_econ["Total COGS"].max()) * 1.1 if len(sku_econ) else 1
    scatter.add_shape(type="line", x0=0, y0=0, x1=max_axis, y1=max_axis,
                       line=dict(color=TEXT_MUTED, dash="dot"))
    scatter.update_traces(textposition="top center")
    scatter.update_layout(
        title="Net Sales Price vs. Total Production Cost per SKU (points above the diagonal are underwater)",
        height=480, plot_bgcolor="white", margin=dict(l=20, r=20, t=60, b=20),
    )
    st.plotly_chart(scatter, width="stretch")

    if underwater.empty:
        st.success("✅ No SKUs currently have BOM/production cost exceeding net sales price.")
    else:
        st.error(
            f"⚠️ **{len(underwater)} SKU(s)** have total production cost exceeding net sales "
            f"price: **{', '.join(underwater['Product Name'].tolist())}**"
        )
        diag_display = underwater[["SKU Code", "Product Name", "Category", "Net Revenue",
                                    "Total COGS", "Cost Coverage Ratio", "Gross Profit"]].copy()
        diag_display["Net Revenue"] = diag_display["Net Revenue"].apply(fmt_currency)
        diag_display["Total COGS"] = diag_display["Total COGS"].apply(fmt_currency)
        diag_display["Cost Coverage Ratio"] = diag_display["Cost Coverage Ratio"].apply(fmt_pct)
        diag_display["Gross Profit"] = diag_display["Gross Profit"].apply(lambda v: fmt_currency(v, True))
        st.dataframe(diag_display, hide_index=True, width="stretch")

    st.session_state["_sku_econ_cache"] = sku_econ


# =============================================================================
# 9. MODULE 5: EXECUTIVE ACTION PLAN & STRATEGIC SCENARIO SIMULATOR
# =============================================================================

def render_module_5(master: pd.DataFrame):
    st.header("\U0001F3AF Executive Action Plan & Strategic Scenario Simulator")

    sku_econ = compute_sku_economics(master)
    pnl = compute_pnl(master)
    cat_econ = (sku_econ.groupby("Category").agg({"Net Revenue": "sum", "Operating Profit": "sum"})
                if not sku_econ.empty else pd.DataFrame())

    underwater = sku_econ[sku_econ["Status"].str.contains("Exceeds")] if not sku_econ.empty else pd.DataFrame()
    ap_total = compute_balance_sheet(master)["ap"]

    best_cat = cat_econ["Operating Profit"].idxmax() if not cat_econ.empty else "N/A"
    worst_cat = cat_econ["Operating Profit"].idxmin() if not cat_econ.empty else "N/A"

    st.subheader("\U0001F4CC Prioritized Corrective Actions")

    rec1, rec2, rec3 = st.columns(3)
    with rec1:
        st.markdown(
            f"""
            <div class='commentary-box'>
            <h5 style='color:{TERRACOTTA};'>1. SKU Rationalization</h5>
            <p>{'Discontinue or re-engineer <b>' + ', '.join(underwater['Product Name'].tolist()) + '</b>, ' if not underwater.empty else 'Continue monitoring SKU-level cost coverage; '}
            where production cost currently exceeds net sales price. Renegotiate BOM
            (fabric/trim) costs or reprice by the cost gap before next production run.</p>
            </div>
            """, unsafe_allow_html=True,
        )
    with rec2:
        st.markdown(
            f"""
            <div class='commentary-box'>
            <h5 style='color:{NAVY};'>2. Resource Pivot to {best_cat if best_cat != 'N/A' else 'Higher-Margin Category'}</h5>
            <p>Shift production capacity, marketing spend, and working capital toward
            <b>{best_cat if best_cat != 'N/A' else 'the stronger-margin category'}</b>, which is
            outperforming <b>{worst_cat if worst_cat != 'N/A' else 'the weaker category'}</b> on
            operating profitability. Reallocate at least one production cycle of capacity.</p>
            </div>
            """, unsafe_allow_html=True,
        )
    with rec3:
        st.markdown(
            f"""
            <div class='commentary-box'>
            <h5 style='color:{EMERALD};'>3. Vendor AP Restructuring</h5>
            <p>Accounts Payable of <b>{fmt_currency(ap_total)}</b> should be renegotiated into
            extended payment terms (Net-60/Net-90) with key fabric and trim vendors to
            relieve near-term liquidity pressure and lift the Current Ratio.</p>
            </div>
            """, unsafe_allow_html=True,
        )

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # ---- Scenario Simulator -------------------------------------------------
    st.subheader("\U0001F52C Interactive Scenario Simulator")
    st.caption(
        "Simulates recovery of Gross Margin and EBITDA under a simplified, "
        "volume-held-constant model. Adjust the levers below."
    )

    s1, s2, s3 = st.columns(3)
    with s1:
        price_increase = st.slider("Price Increase % (applied to Net Revenue)", 0, 30, 5, step=1)
    with s2:
        marketing_adj = st.slider("Marketing Spend Adjustment %", -50, 50, 0, step=5)
    with s3:
        discontinue_pct = st.slider("Discontinue Worst-Performing SKUs (% of SKUs by loss rank)", 0, 100, 0, step=10)

    sim_pnl = dict(pnl)  # baseline copy

    if not sku_econ.empty:
        sku_sim = sku_econ.copy().sort_values("Operating Profit")
        n_to_cut = int(np.ceil(len(sku_sim) * (discontinue_pct / 100)))
        cut_skus = set(sku_sim.iloc[:n_to_cut]["SKU Code"]) if n_to_cut > 0 else set()

        retained = sku_sim[~sku_sim["SKU Code"].isin(cut_skus)].copy()
        retained["Net Revenue Sim"] = retained["Net Revenue"] * (1 + price_increase / 100)
        retained["Total COGS Sim"] = retained["Total COGS"]  # cost structure held constant (no volume change assumed)
        retained["Gross Profit Sim"] = retained["Net Revenue Sim"] - retained["Total COGS Sim"]

        sim_net_revenue = retained["Net Revenue Sim"].sum()
        sim_total_cogs = retained["Total COGS Sim"].sum()
        sim_gross_profit = sim_net_revenue - sim_total_cogs

        sim_marketing = pnl["marketing"] * (1 + marketing_adj / 100)
        sim_logistics = pnl["logistics"]
        sim_other_opex = pnl["other_opex"]
        sim_total_opex = sim_marketing + sim_logistics + sim_other_opex

        sim_ebitda = sim_gross_profit - sim_total_opex
        sim_gross_margin = safe_div(sim_gross_profit, sim_net_revenue)
        sim_ebitda_margin = safe_div(sim_ebitda, sim_net_revenue)
    else:
        sim_net_revenue = pnl["net_revenue"] * (1 + price_increase / 100)
        sim_total_cogs = pnl["total_cogs"]
        sim_gross_profit = sim_net_revenue - sim_total_cogs
        sim_marketing = pnl["marketing"] * (1 + marketing_adj / 100)
        sim_total_opex = sim_marketing + pnl["logistics"] + pnl["other_opex"]
        sim_ebitda = sim_gross_profit - sim_total_opex
        sim_gross_margin = safe_div(sim_gross_profit, sim_net_revenue)
        sim_ebitda_margin = safe_div(sim_ebitda, sim_net_revenue)

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Simulated Net Revenue", fmt_currency(sim_net_revenue),
              delta=fmt_currency(sim_net_revenue - pnl["net_revenue"]))
    r2.metric("Simulated Gross Margin %", fmt_pct(sim_gross_margin),
              delta=fmt_pct(sim_gross_margin - pnl["gross_margin"]))
    r3.metric("Simulated EBITDA", fmt_currency(sim_ebitda),
              delta=fmt_currency(sim_ebitda - pnl["ebitda"]))
    r4.metric("Simulated EBITDA Margin %", fmt_pct(sim_ebitda_margin),
              delta=fmt_pct(sim_ebitda_margin - pnl["ebitda_margin"]))

    compare_fig = go.Figure()
    compare_fig.add_trace(go.Bar(
        name="Current (Actual)",
        x=["Gross Margin %", "EBITDA Margin %"],
        y=[pnl["gross_margin"] * 100, pnl["ebitda_margin"] * 100],
        marker_color=NAVY,
        text=[fmt_pct(pnl["gross_margin"]), fmt_pct(pnl["ebitda_margin"])],
        textposition="outside",
    ))
    compare_fig.add_trace(go.Bar(
        name="Simulated (Scenario)",
        x=["Gross Margin %", "EBITDA Margin %"],
        y=[sim_gross_margin * 100, sim_ebitda_margin * 100],
        marker_color=EMERALD,
        text=[fmt_pct(sim_gross_margin), fmt_pct(sim_ebitda_margin)],
        textposition="outside",
    ))
    compare_fig.update_layout(
        barmode="group", height=420, title="Actual vs. Simulated Margin Recovery",
        yaxis_title="%", plot_bgcolor="white", margin=dict(l=20, r=20, t=60, b=20),
    )
    st.plotly_chart(compare_fig, width="stretch")

    st.caption(
        "ℹ️ Model assumptions: unit volumes held constant under price changes "
        "(no price-elasticity effect modeled); discontinued SKUs remove 100% of their "
        "revenue and cost contribution; marketing spend adjustment does not alter "
        "logistics or other overhead."
    )


# =============================================================================
# 10. MAIN APPLICATION
# =============================================================================

def main():
    frames = sidebar_data_source()
    if frames is None:
        st.stop()
        return

    gl_df = frames[SHEET_GL]
    coa_df = frames[SHEET_COA]
    sku_df = frames[SHEET_SKU]

    st.session_state["_sku_master_df"] = sku_df

    cache_key = f"{len(gl_df)}-{len(coa_df)}-{len(sku_df)}"
    try:
        master = prepare_master_dataset(cache_key, gl_df, coa_df, sku_df)
    except Exception as exc:  # noqa: BLE001
        st.error(f"### ⚠️ Error preparing dataset\n\n`{type(exc).__name__}: {exc}`")
        st.stop()
        return

    if master["Posting Date"].isna().all():
        st.error("### ⚠️ No valid Posting Dates found in the GL Journal Entries tab.")
        st.stop()
        return

    unclassified = master[master["Bucket"] == "Unclassified"]
    if not unclassified.empty:
        with st.sidebar.expander(f"⚠️ {len(unclassified)} unclassified GL line(s)"):
            st.caption(
                "These lines could not be mapped to a P&L/Balance-Sheet bucket and are "
                "excluded from statement totals. Review account naming conventions."
            )
            st.dataframe(
                unclassified[["GL Code", "GL Account Name", "Account Type", "Amount"]].head(50),
                hide_index=True, width="stretch",
            )

    st.sidebar.markdown("---")
    module = st.sidebar.radio(
        "Navigate to module",
        [
            "1. Executive Health Scorecard",
            "2. Monthly MIS Statements",
            "3. MoM Variance Analysis",
            "4. Root-Cause & Pareto Diagnostics",
            "5. Action Plan & Scenario Simulator",
        ],
        index=0,
    )
    st.sidebar.markdown("---")
    st.sidebar.caption(
        f"Data span: {master['Posting Date'].min():%d %b %Y} - "
        f"{master['Posting Date'].max():%d %b %Y}"
    )
    st.sidebar.caption(f"GL lines loaded: {len(master):,}")

    if module.startswith("1"):
        render_module_1(master)
    elif module.startswith("2"):
        render_module_2(master)
    elif module.startswith("3"):
        render_module_3(master)
    elif module.startswith("4"):
        render_module_4(master)
    elif module.startswith("5"):
        render_module_5(master)


if __name__ == "__main__":
    main()
