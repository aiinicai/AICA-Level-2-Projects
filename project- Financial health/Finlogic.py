"""
=============================================================================
 SUNDAY SOMEWEAR - FINANCIAL LOGIC ENGINE (framework-agnostic)
=============================================================================
This module contains ALL the business logic from the original Streamlit
dashboard - GL classification, P&L / Balance Sheet / Cash Flow computation,
SKU-level economics, MoM variance analysis, Pareto loss-driver analysis, and
the scenario simulator - with zero dependency on Streamlit. It is consumed
by main.py (the FastAPI layer) so the exact same, already-validated
calculations can be exposed as a JSON API for any frontend (e.g. a Lovable-
built React app) to call.
=============================================================================
"""

from __future__ import annotations

import io
from typing import Optional

import numpy as np
import pandas as pd

# =============================================================================
# CONFIGURATION
# =============================================================================

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


class DataLoadError(Exception):
    """Raised when the source workbook is missing, malformed, or incomplete."""


# =============================================================================
# WORKBOOK LOADING & VALIDATION
# =============================================================================

def load_workbook_bytes(file_bytes: bytes) -> dict:
    """Loads and validates the three required tabs from raw workbook bytes."""
    try:
        xls = pd.ExcelFile(io.BytesIO(file_bytes), engine="openpyxl")
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


def load_workbook_path(file_path: str) -> dict:
    with open(file_path, "rb") as f:
        return load_workbook_bytes(f.read())


# =============================================================================
# GL ACCOUNT CLASSIFICATION
# =============================================================================

def _kw(text: str, *keywords: str) -> bool:
    """
    Case-insensitive substring keyword match. Safe here because classification
    is scoped in two tiers (see classify_account): Tier 1 restricts matching to
    the structured 'Account Category'/'Account Type' fields only, and Tier 2
    keyword checks only run *within* the high-level type Tier 1 already
    determined - so 'Raw Material Inventory' is routed to Inventory (its
    Account Category is 'Current Asset') and never reaches the COGS-stage
    'raw material' keyword check at all. This scoping is what prevents
    cross-type collisions (e.g. 'rent' inside 'current'), so plain substring
    matching (which also naturally handles plurals) is safe here.
    """
    return any(k in text for k in keywords)


def classify_account(row: pd.Series) -> str:
    """
    Maps a GL journal line to a standardized financial-statement bucket.

    Two-tier design:
      1. HIGH-LEVEL TYPE from the structured 'Account Category' (Chart of
         Accounts) / 'Account Type' (GL Journal) fields - authoritative,
         prevents cross-type collisions.
      2. Account NAME picks the specific sub-bucket within that type.

    A permissive keyword fallback runs only when the structured category
    fields are blank or unrecognized.
    """
    category_text = " ".join(
        str(row.get(c, "")) for c in ["Account Category", "Account Type"]
    ).lower()
    name_text = " ".join(
        str(row.get(c, "")) for c in ["GL Account Name", "Account Name"]
    ).lower()
    full_text = f"{category_text} {name_text}"

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

PNL_COGS_BUCKETS = ["Raw Materials COGS", "Direct Labor COGS", "Freight COGS", "Other COGS"]
PNL_OPEX_BUCKETS = ["Marketing Expense", "Logistics Expense", "Other Opex"]


def prepare_master_dataset(gl: pd.DataFrame, coa: pd.DataFrame, sku: pd.DataFrame) -> pd.DataFrame:
    """Joins GL to Chart of Accounts, classifies every line, computes signed Amount."""
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

    merged["Bucket"] = merged.apply(classify_account, axis=1)
    merged["Balance Direction"] = merged["Bucket"].map(NORMAL_BALANCE_MAP).fillna("debit")
    merged["Amount"] = np.where(
        merged["Balance Direction"] == "debit",
        merged["Debit (₹)"] - merged["Credit (₹)"],
        merged["Credit (₹)"] - merged["Debit (₹)"],
    )

    merged["Month"] = merged["Posting Date"].dt.to_period("M").astype(str)
    merged["Month Label"] = merged["Posting Date"].dt.strftime("%b %Y")

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

    merged["Product Category"] = merged["Category"].where(
        merged["Category"].notna() & (merged["Category"].astype(str).str.strip() != ""),
        merged["SKU Master Category"],
    )

    return merged


# =============================================================================
# HELPERS
# =============================================================================

def safe_div(numerator: float, denominator: float) -> float:
    try:
        if denominator in (0, 0.0) or denominator is None or pd.isna(denominator):
            return 0.0
        return float(numerator) / float(denominator)
    except (TypeError, ZeroDivisionError):
        return 0.0


def month_options(df: pd.DataFrame) -> list:
    valid = df.dropna(subset=["Posting Date"])
    periods = sorted(valid["Posting Date"].dt.to_period("M").unique())
    return [p.strftime("%b %Y") for p in periods]


def filter_by_period(df: pd.DataFrame, period_label: str) -> pd.DataFrame:
    """period_label 'H1' / 'CUMULATIVE' (case-insensitive) returns the full df."""
    if period_label is None or period_label.strip().upper() in ("H1", "CUMULATIVE", "ALL"):
        return df
    return df[df["Month Label"] == period_label]


def bucket_sum(df: pd.DataFrame, buckets: list) -> float:
    if not buckets:
        return 0.0
    return float(df.loc[df["Bucket"].isin(buckets), "Amount"].sum())


# =============================================================================
# P&L / BALANCE SHEET / CASH FLOW
# =============================================================================

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
    net_income = ebitda

    return dict(
        gross_revenue=gross_revenue, returns=returns, net_revenue=net_revenue,
        raw_cogs=raw_cogs, labor_cogs=labor_cogs, freight_cogs=freight_cogs,
        other_cogs=other_cogs, total_cogs=total_cogs, gross_profit=gross_profit,
        marketing=marketing, logistics=logistics, other_opex=other_opex,
        total_opex=total_opex, ebitda=ebitda, net_income=net_income,
        gross_margin=safe_div(gross_profit, net_revenue),
        ebitda_margin=safe_div(ebitda, net_revenue),
        net_margin=safe_div(net_income, net_revenue),
    )


def compute_balance_sheet(df_cumulative: pd.DataFrame) -> dict:
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
    quick_ratio = safe_div(current_assets - inventory, current_liabilities)
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
    return dict(inflows=inflows, outflows=outflows, net_cash_flow=inflows - outflows)


def health_rating(pnl: dict, bs: dict) -> tuple:
    reasons = []
    critical = False
    watchlist = False

    if bs["current_ratio"] < 1.0:
        critical = True
        reasons.append(f"Current Ratio of {bs['current_ratio']:.2f} is below 1.00x - the "
                        f"company cannot cover current liabilities with current assets.")
    if pnl["gross_margin"] < 0:
        critical = True
        reasons.append(f"Gross Margin is negative ({pnl['gross_margin']*100:.2f}%) - "
                        f"products are being sold below cost on average.")

    if not critical:
        if bs["current_ratio"] < 1.5:
            watchlist = True
            reasons.append(f"Current Ratio of {bs['current_ratio']:.2f} is thin (below 1.50x).")
        if pnl["gross_margin"] < 0.15:
            watchlist = True
            reasons.append(f"Gross Margin of {pnl['gross_margin']*100:.2f}% is compressed (below 15%).")
        if pnl["ebitda_margin"] < 0:
            watchlist = True
            reasons.append(f"EBITDA Margin is negative ({pnl['ebitda_margin']*100:.2f}%).")

    if critical:
        return "CRITICAL", reasons
    if watchlist:
        return "WATCHLIST", reasons
    return "HEALTHY", ["All core liquidity and profitability thresholds are within healthy range."]


# =============================================================================
# SKU ECONOMICS / PARETO
# =============================================================================

def compute_sku_economics(df_period: pd.DataFrame, sku_master: pd.DataFrame) -> pd.DataFrame:
    sku_rows = df_period[df_period["SKU Reference"].notna() &
                          (df_period["SKU Reference"].astype(str).str.strip() != "") &
                          (df_period["SKU Reference"].astype(str).str.lower() != "nan")]

    cols = ["SKU Code", "Product Name", "Category", "Gross Revenue", "Returns",
            "Net Revenue", "Raw Materials COGS", "Direct Labor COGS", "Freight COGS",
            "Total COGS", "Gross Profit", "Gross Margin %", "Allocated Opex",
            "Operating Profit", "Cost Coverage Ratio", "Status"]

    if sku_rows.empty:
        return pd.DataFrame(columns=cols)

    grp = sku_rows.groupby("SKU Reference")

    def bucket_series(bucket_name):
        return grp.apply(lambda g: float(g.loc[g["Bucket"] == bucket_name, "Amount"].sum()),
                          include_groups=False)

    result = pd.DataFrame({
        "Gross Revenue": bucket_series("Gross Revenue"),
        "Returns": bucket_series("Sales Returns"),
        "Raw Materials COGS": bucket_series("Raw Materials COGS"),
        "Direct Labor COGS": bucket_series("Direct Labor COGS"),
        "Freight COGS": bucket_series("Freight COGS"),
    }).fillna(0.0)

    result["Net Revenue"] = result["Gross Revenue"] - result["Returns"]
    result["Total COGS"] = (result["Raw Materials COGS"] + result["Direct Labor COGS"]
                             + result["Freight COGS"])
    result["Gross Profit"] = result["Net Revenue"] - result["Total COGS"]
    result["Gross Margin %"] = result.apply(
        lambda r: safe_div(r["Gross Profit"], r["Net Revenue"]), axis=1)

    total_opex = bucket_sum(df_period, PNL_OPEX_BUCKETS)
    total_gross_rev = result["Gross Revenue"].sum()
    result["Allocated Opex"] = result["Gross Revenue"].apply(
        lambda x: total_opex * safe_div(x, total_gross_rev))

    result["Operating Profit"] = result["Gross Profit"] - result["Allocated Opex"]
    result["Cost Coverage Ratio"] = result.apply(
        lambda r: safe_div(r["Total COGS"], r["Net Revenue"]), axis=1)
    result["Status"] = np.where(
        result["Cost Coverage Ratio"] > 1.0, "Cost Exceeds Price", "OK")

    result = result.reset_index().rename(columns={"SKU Reference": "SKU Code"})

    lookup = sku_master.copy()
    lookup["SKU Code"] = lookup["SKU Code"].astype(str).str.strip()
    lookup = lookup.set_index("SKU Code")
    result["Product Name"] = result["SKU Code"].map(lookup["Product Name"]).fillna(result["SKU Code"])
    result["Category"] = result["SKU Code"].map(lookup["Category"]).fillna("Unknown")

    return result[cols].sort_values("Operating Profit").reset_index(drop=True)


def compute_pareto(sku_econ: pd.DataFrame) -> dict:
    losses = sku_econ[sku_econ["Operating Profit"] < 0].copy()
    if losses.empty:
        return dict(has_losses=False, total_loss=0.0, top20_share=0.0, skus=[])

    losses["Loss"] = -losses["Operating Profit"]
    losses = losses.sort_values("Loss", ascending=False).reset_index(drop=True)
    losses["Cumulative Loss"] = losses["Loss"].cumsum()
    total_loss = float(losses["Loss"].sum())
    losses["Cumulative %"] = losses["Cumulative Loss"] / total_loss

    n = len(losses)
    cutoff_idx = max(1, int(np.ceil(n * 0.2)))
    losses["Pareto Zone"] = ["Top 20% Drivers" if i < cutoff_idx else "Remaining SKUs"
                              for i in range(n)]
    top20_share = float(losses.iloc[:cutoff_idx]["Loss"].sum() / total_loss)

    skus = [
        dict(sku_code=r["SKU Code"], product_name=r["Product Name"], category=r["Category"],
             loss=float(r["Loss"]), cumulative_loss=float(r["Cumulative Loss"]),
             cumulative_pct=float(r["Cumulative %"]), pareto_zone=r["Pareto Zone"])
        for _, r in losses.iterrows()
    ]
    return dict(has_losses=True, total_loss=total_loss, top20_share=top20_share, skus=skus)


# =============================================================================
# VARIANCE ANALYSIS
# =============================================================================

VARIANCE_LINE_ITEMS = [
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


def compute_variance(base_df: pd.DataFrame, comp_df: pd.DataFrame) -> list:
    base_pnl = compute_pnl(base_df)
    comp_pnl = compute_pnl(comp_df)

    rows = []
    for label, key, direction in VARIANCE_LINE_ITEMS:
        base_val = base_pnl[key]
        comp_val = comp_pnl[key]
        variance = comp_val - base_val
        variance_pct = safe_div(variance, abs(base_val)) if base_val != 0 else 0.0

        favorable = (variance >= 0) if direction == "higher_better" else (variance <= 0)
        if abs(variance_pct) < 0.0001:
            impact = "Flat"
        else:
            impact = "Favorable" if favorable else "Unfavorable"

        rows.append(dict(
            line_item=label, base_value=base_val, comparison_value=comp_val,
            variance=variance, variance_pct=variance_pct, impact=impact,
            threshold_flag=abs(variance_pct) >= 0.05,
        ))
    return rows


# =============================================================================
# SCENARIO SIMULATOR
# =============================================================================

def run_simulation(df_period: pd.DataFrame, sku_master: pd.DataFrame,
                    price_increase_pct: float, marketing_adj_pct: float,
                    discontinue_pct: float) -> dict:
    pnl = compute_pnl(df_period)
    sku_econ = compute_sku_economics(df_period, sku_master)

    if not sku_econ.empty:
        sku_sim = sku_econ.copy().sort_values("Operating Profit")
        n_to_cut = int(np.ceil(len(sku_sim) * (discontinue_pct / 100)))
        cut_skus = set(sku_sim.iloc[:n_to_cut]["SKU Code"]) if n_to_cut > 0 else set()

        retained = sku_sim[~sku_sim["SKU Code"].isin(cut_skus)].copy()
        retained["Net Revenue Sim"] = retained["Net Revenue"] * (1 + price_increase_pct / 100)
        retained["Total COGS Sim"] = retained["Total COGS"]

        sim_net_revenue = float(retained["Net Revenue Sim"].sum())
        sim_total_cogs = float(retained["Total COGS Sim"].sum())
        discontinued_skus = sorted(cut_skus)
    else:
        sim_net_revenue = pnl["net_revenue"] * (1 + price_increase_pct / 100)
        sim_total_cogs = pnl["total_cogs"]
        discontinued_skus = []

    sim_gross_profit = sim_net_revenue - sim_total_cogs
    sim_marketing = pnl["marketing"] * (1 + marketing_adj_pct / 100)
    sim_total_opex = sim_marketing + pnl["logistics"] + pnl["other_opex"]
    sim_ebitda = sim_gross_profit - sim_total_opex
    sim_gross_margin = safe_div(sim_gross_profit, sim_net_revenue)
    sim_ebitda_margin = safe_div(sim_ebitda, sim_net_revenue)

    return dict(
        baseline=dict(
            net_revenue=pnl["net_revenue"], gross_margin=pnl["gross_margin"],
            ebitda=pnl["ebitda"], ebitda_margin=pnl["ebitda_margin"],
        ),
        simulated=dict(
            net_revenue=sim_net_revenue, gross_margin=sim_gross_margin,
            ebitda=sim_ebitda, ebitda_margin=sim_ebitda_margin,
            total_cogs=sim_total_cogs, total_opex=sim_total_opex,
        ),
        deltas=dict(
            net_revenue=sim_net_revenue - pnl["net_revenue"],
            gross_margin=sim_gross_margin - pnl["gross_margin"],
            ebitda=sim_ebitda - pnl["ebitda"],
            ebitda_margin=sim_ebitda_margin - pnl["ebitda_margin"],
        ),
        discontinued_skus=discontinued_skus,
        assumptions=(
            "Unit volumes are held constant under price changes (no price-elasticity "
            "effect modeled); discontinued SKUs remove 100% of their revenue and cost "
            "contribution; marketing spend adjustment does not alter logistics or other "
            "overhead."
        ),
    )
