"""
ratios.py
=========
Derives key financial line items and computes the 3-year ratio set.

Definitions (all on audited, historical figures)
------------------------------------------------
EBITDA            = Revenue - COGS - Employee - Other operating expenses   (excludes other income)
EBIT              = EBITDA - Depreciation & amortisation
PAT               = EBIT + Other income - Finance costs - Tax
Net worth         = Share capital + Reserves & surplus
TNW               = Net worth - Intangible assets
Total debt        = Long-term + Short-term borrowings + Current maturities of LTD
Capital employed  = TNW + Total debt
ROE / ROCE / ROA  = PAT / avg Net worth ; EBIT / avg Capital employed ; PAT / avg Total assets
ICR               = EBIT / Finance costs
DSCR (policy)     = (EBITDA - Capex - Tax) / (Principal repaid + Finance costs)
DSCR (cash accr.) = (PAT + Depreciation + Finance costs) / (Principal repaid + Finance costs)  [supplementary]
DSO / DIO / DPO   = Receivables / Revenue ; Inventory / COGS ; Payables / COGS   (x 365, closing balances)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import DAYS_IN_YEAR
from .ingestion import ApplicantData


def _div(num: pd.Series, den: pd.Series) -> pd.Series:
    """Safe division: zero denominators -> NaN."""
    return num.astype(float) / den.astype(float).replace(0, np.nan)


def _avg(s: pd.Series) -> pd.Series:
    """Average of opening and closing balance; first year falls back to closing balance."""
    return ((s + s.shift(1)) / 2).fillna(s)


@dataclass
class RatioBundle:
    fin: pd.DataFrame       # derived line items, index = years
    ratios: pd.DataFrame    # ratios, index = years, columns = ratio keys (fractions / multiples / days)
    years: list

    def latest(self, key: str) -> float:
        return float(self.ratios[key].iloc[-1])

    def first(self, key: str) -> float:
        return float(self.ratios[key].iloc[0])

    def change(self, key: str) -> float:
        """Latest minus earliest year (absolute change)."""
        return self.latest(key) - self.first(key)

    @property
    def revenue_cagr(self) -> float:
        rev = self.fin["revenue"]
        n = len(rev) - 1
        if n < 1 or rev.iloc[0] <= 0:
            return np.nan
        return float((rev.iloc[-1] / rev.iloc[0]) ** (1 / n) - 1)


def build_financials(data: ApplicantData) -> pd.DataFrame:
    bs, pl, cf = data.balance_sheet, data.pnl, data.cashflow
    f = pd.DataFrame(index=data.years)

    # ---- P&L ------------------------------------------------------------------------------
    f["revenue"] = pl.loc["Revenue from Operations"]
    f["other_income"] = pl.loc["Other Income"]
    f["cogs"] = pl.loc["Cost of Goods Sold"]
    f["ebitda"] = f["revenue"] - f["cogs"] - pl.loc["Employee Expenses"] - pl.loc["Other Operating Expenses"]
    f["dep"] = pl.loc["Depreciation & Amortization"]
    f["ebit"] = f["ebitda"] - f["dep"]
    f["finance_cost"] = pl.loc["Finance Costs"]
    f["pbt"] = f["ebit"] + f["other_income"] - f["finance_cost"]
    f["tax"] = pl.loc["Tax Expense"]
    f["pat"] = f["pbt"] - f["tax"]

    # ---- Balance sheet ----------------------------------------------------------------------
    f["net_worth"] = bs.loc["Share Capital"] + bs.loc["Reserves & Surplus"]
    f["intangibles"] = bs.loc["Intangible Assets"]
    f["tnw"] = f["net_worth"] - f["intangibles"]
    f["lt_debt"] = bs.loc["Long Term Borrowings"]
    f["st_debt"] = bs.loc["Short Term Borrowings"]
    f["cm_ltd"] = bs.loc["Current Maturities of LTD"]
    f["total_debt"] = f["lt_debt"] + f["st_debt"] + f["cm_ltd"]
    f["payables"] = bs.loc["Trade Payables"]
    f["inventory"] = bs.loc["Inventories"]
    f["receivables"] = bs.loc["Trade Receivables"]
    f["cash"] = bs.loc["Cash & Bank Balances"]
    f["current_assets"] = f["inventory"] + f["receivables"] + f["cash"] + bs.loc["Other Current Assets"]
    f["current_liabilities"] = (f["payables"] + f["st_debt"] + f["cm_ltd"] + bs.loc["Other Current Liabilities"])
    f["total_assets"] = bs.loc[[
        "Net Fixed Assets", "Capital Work in Progress", "Intangible Assets", "Non-Current Investments",
        "Other Non-Current Assets", "Inventories", "Trade Receivables", "Cash & Bank Balances",
        "Other Current Assets"]].sum()
    f["tol"] = f["total_assets"] - f["net_worth"]            # total outside liabilities
    f["capital_employed"] = f["tnw"] + f["total_debt"]

    # ---- Cash flow ------------------------------------------------------------------------------
    f["cfo"] = cf.loc["Cash Flow from Operations"]
    f["capex"] = cf.loc["Capital Expenditure"].abs()
    f["principal_repaid"] = cf.loc["Debt Repaid"].abs()
    f["fcf"] = f["cfo"] - f["capex"]
    return f


def compute_ratios(data: ApplicantData) -> RatioBundle:
    f = build_financials(data)
    r = pd.DataFrame(index=f.index)

    # ---- Profitability --------------------------------------------------------------------------
    r["ebitda_margin"] = _div(f["ebitda"], f["revenue"])
    r["opm"] = _div(f["ebit"], f["revenue"])
    r["npm"] = _div(f["pat"], f["revenue"])
    r["roe"] = _div(f["pat"], _avg(f["net_worth"]))
    r["roce"] = _div(f["ebit"], _avg(f["capital_employed"]))
    r["roa"] = _div(f["pat"], _avg(f["total_assets"]))

    # ---- Liquidity & working capital ----------------------------------------------------------
    r["current_ratio"] = _div(f["current_assets"], f["current_liabilities"])
    r["quick_ratio"] = _div(f["current_assets"] - f["inventory"], f["current_liabilities"])
    r["cash_ratio"] = _div(f["cash"], f["current_liabilities"])
    r["dso"] = _div(f["receivables"], f["revenue"]) * DAYS_IN_YEAR
    r["dio"] = _div(f["inventory"], f["cogs"]) * DAYS_IN_YEAR
    r["dpo"] = _div(f["payables"], f["cogs"]) * DAYS_IN_YEAR
    r["ccc"] = r["dso"] + r["dio"] - r["dpo"]

    # ---- Gearing & coverage ---------------------------------------------------------------------
    r["de"] = pd.Series(np.where(f["tnw"] > 0, f["total_debt"] / f["tnw"].replace(0, np.nan), np.inf), index=f.index)
    r["tol_tnw"] = pd.Series(np.where(f["tnw"] > 0, f["tol"] / f["tnw"].replace(0, np.nan), np.inf), index=f.index)
    r["debt_ebitda"] = pd.Series(np.where(f["ebitda"] > 0, f["total_debt"] / f["ebitda"].replace(0, np.nan), np.inf),
                                 index=f.index)
    r["icr"] = _div(f["ebit"], f["finance_cost"])
    debt_service = f["principal_repaid"] + f["finance_cost"]
    r["dscr"] = _div(f["ebitda"] - f["capex"] - f["tax"], debt_service)
    r["dscr_cash"] = _div(f["pat"] + f["dep"] + f["finance_cost"], debt_service)

    return RatioBundle(fin=f, ratios=r, years=list(f.index))
