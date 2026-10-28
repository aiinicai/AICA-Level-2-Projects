"""
Cents & Sensibility — Ratio & Variance Engine
Computes 25+ financial ratios per period and the SA 520-style
expectation-vs-actual variance table.
"""

from .data_ingestion import derive


def _safe_div(a, b):
    return a / b if b not in (0, 0.0) else None


def compute_ratios(period: dict) -> dict:
    """Compute the full ratio set for one period. None = not computable."""
    d = derive(period)
    r = {}

    # ---- Liquidity ----
    r["Current Ratio"] = _safe_div(d["current_assets"], d["current_liab"])
    r["Quick Ratio"] = _safe_div(d["current_assets"] - d["inventory"], d["current_liab"])
    r["Cash Ratio"] = _safe_div(d["cash"], d["current_liab"])
    r["Working Capital / Total Assets"] = _safe_div(d["working_capital"], d["total_assets"])

    # ---- Solvency ----
    r["Debt-Equity Ratio"] = _safe_div(d["total_debt"], d["total_equity"])
    r["Debt Ratio (Debt/Assets)"] = _safe_div(d["total_debt"], d["total_assets"])
    r["Interest Coverage (EBIT/Finance Cost)"] = _safe_div(d["ebit"], d["finance_cost"])
    r["Proprietary Ratio (Equity/Assets)"] = _safe_div(d["total_equity"], d["total_assets"])

    # ---- Profitability ----
    r["Gross Profit Margin %"] = _pct(_safe_div(d["gross_profit"], d["revenue"]))
    r["EBITDA Margin %"] = _pct(_safe_div(d["ebitda"], d["revenue"]))
    r["EBIT Margin %"] = _pct(_safe_div(d["ebit"], d["revenue"]))
    r["Net Profit Margin %"] = _pct(_safe_div(d["pat"], d["revenue"]))
    r["Return on Equity %"] = _pct(_safe_div(d["pat"], d["total_equity"]))
    r["Return on Capital Employed %"] = _pct(_safe_div(d["ebit"], d["capital_employed"]))
    r["Return on Assets %"] = _pct(_safe_div(d["pat"], d["total_assets"]))

    # ---- Efficiency / Turnover ----
    r["Receivable Days"] = _days(_safe_div(d["receivables"], d["revenue"]))
    r["Inventory Days"] = _days(_safe_div(d["inventory"], d["material_cost"]))
    r["Payable Days"] = _days(_safe_div(d["trade_payables"], d["material_cost"]))
    rec_d, inv_d, pay_d = r["Receivable Days"], r["Inventory Days"], r["Payable Days"]
    r["Cash Conversion Cycle (days)"] = (
        rec_d + inv_d - pay_d if None not in (rec_d, inv_d, pay_d) else None
    )
    r["Total Asset Turnover (x)"] = _safe_div(d["revenue"], d["total_assets"])
    r["Fixed Asset Turnover (x)"] = _safe_div(d["revenue"], d["net_ppe"])
    r["Working Capital Turnover (x)"] = _safe_div(d["revenue"], d["working_capital"])
    r["Inventory Turnover (x)"] = _safe_div(d["material_cost"], d["inventory"])
    r["Receivables Turnover (x)"] = _safe_div(d["revenue"], d["receivables"])

    # ---- Expense structure & other ----
    r["Employee Cost % of Revenue"] = _pct(_safe_div(d["employee_cost"], d["revenue"]))
    r["Finance Cost % of Revenue"] = _pct(_safe_div(d["finance_cost"], d["revenue"]))
    r["Other Expenses % of Revenue"] = _pct(_safe_div(d["other_expenses"], d["revenue"]))
    r["Effective Tax Rate %"] = _pct(_safe_div(d["tax"], d["pbt"]))
    r["Other Income % of PBT"] = _pct(_safe_div(d["other_income"], d["pbt"]))

    return r


RATIO_GROUPS = {
    "Liquidity": ["Current Ratio", "Quick Ratio", "Cash Ratio",
                  "Working Capital / Total Assets"],
    "Solvency": ["Debt-Equity Ratio", "Debt Ratio (Debt/Assets)",
                 "Interest Coverage (EBIT/Finance Cost)", "Proprietary Ratio (Equity/Assets)"],
    "Profitability": ["Gross Profit Margin %", "EBITDA Margin %", "EBIT Margin %",
                      "Net Profit Margin %", "Return on Equity %",
                      "Return on Capital Employed %", "Return on Assets %"],
    "Efficiency": ["Receivable Days", "Inventory Days", "Payable Days",
                   "Cash Conversion Cycle (days)", "Total Asset Turnover (x)",
                   "Fixed Asset Turnover (x)", "Working Capital Turnover (x)",
                   "Inventory Turnover (x)", "Receivables Turnover (x)"],
    "Expense Structure": ["Employee Cost % of Revenue", "Finance Cost % of Revenue",
                          "Other Expenses % of Revenue", "Effective Tax Rate %",
                          "Other Income % of PBT"],
}

# Ratios where an INCREASE is generally adverse (for arrow colouring)
ADVERSE_IF_UP = {
    "Debt-Equity Ratio", "Debt Ratio (Debt/Assets)", "Receivable Days",
    "Inventory Days", "Cash Conversion Cycle (days)",
    "Employee Cost % of Revenue", "Finance Cost % of Revenue",
    "Other Expenses % of Revenue", "Other Income % of PBT",
}


def _pct(x):
    return x * 100 if x is not None else None


def _days(x):
    return x * 365 if x is not None else None


# ---------------------------------------------------------------------------
# SA 520 — expectation vs actual variance analysis
# ---------------------------------------------------------------------------
def variance_table(data: dict, threshold_pct: float = 10.0) -> list[dict]:
    """
    Compare CY vs PY for key line items AND key ratios.
    Rows breaching |change %| >= threshold are flagged for investigation.
    """
    cy, py = derive(data["CY"]), derive(data["PY"])
    rows = []

    line_items = [
        ("Revenue from Operations", "revenue"), ("Other Income", "other_income"),
        ("Cost of Materials / Purchases", "material_cost"),
        ("Employee Benefit Expenses", "employee_cost"), ("Finance Costs", "finance_cost"),
        ("Depreciation & Amortisation", "depreciation"),
        ("Other / SG&A Expenses", "other_expenses"), ("Profit Before Tax", "pbt"),
        ("Profit After Tax", "pat"), ("Trade Receivables", "receivables"),
        ("Inventories", "inventory"), ("Trade Payables", "trade_payables"),
        ("Total Borrowings", "total_debt"), ("Cash & Bank Balances", "cash"),
    ]
    for label, key in line_items:
        a, e = cy[key], py[key]      # actual (CY) vs expectation basis (PY)
        chg = _safe_div(a - e, abs(e)) if e else None
        rows.append({
            "Item": label, "Type": "Line item",
            "Prior Year (Expectation basis)": round(e, 2),
            "Current Year (Actual)": round(a, 2),
            "Change %": round(chg * 100, 1) if chg is not None else None,
            "Flag": bool(chg is not None and abs(chg * 100) >= threshold_pct),
        })

    rcy, rpy = compute_ratios(data["CY"]), compute_ratios(data["PY"])
    key_ratios = ["Current Ratio", "Debt-Equity Ratio", "Gross Profit Margin %",
                  "Net Profit Margin %", "Receivable Days", "Inventory Days",
                  "Interest Coverage (EBIT/Finance Cost)"]
    for name in key_ratios:
        a, e = rcy.get(name), rpy.get(name)
        chg = _safe_div(a - e, abs(e)) if (a is not None and e) else None
        rows.append({
            "Item": name, "Type": "Ratio",
            "Prior Year (Expectation basis)": round(e, 2) if e is not None else None,
            "Current Year (Actual)": round(a, 2) if a is not None else None,
            "Change %": round(chg * 100, 1) if chg is not None else None,
            "Flag": bool(chg is not None and abs(chg * 100) >= threshold_pct),
        })
    return rows
