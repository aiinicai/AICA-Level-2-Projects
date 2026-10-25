"""
sample_data.py
==============
Generates three internally consistent mock applicants (strong / moderate / stressed) so the
dashboard can be demonstrated immediately, and writes the Excel input template.

The generator builds each profile from a handful of operating assumptions and then derives a
balance sheet that genuinely balances: cash is rolled forward from the cash-flow statement and
short-term borrowings are drawn automatically if cash would fall below a floor.

All values are in ₹ Crore. Company names are fictitious.
"""
from __future__ import annotations

import io

import numpy as np
import pandas as pd

from .ingestion import (
    APPLICANT_FIELDS, BS_ITEMS, CF_ITEMS, DEBT_COLUMNS, PNL_ITEMS, PROPOSED_FIELDS, ApplicantData,
)

TAX_RATE = 0.2517  # Indian corporate tax (new regime) incl. surcharge & cess

# --------------------------------------------------------------------------- #
# Profile assumptions  (lists are for FY2023, FY2024, FY2025)
# --------------------------------------------------------------------------- #
PROFILES = {
    "Strong - Aarav Precision Components Ltd": dict(
        profile=dict(name="Aarav Precision Components Ltd", cin="U29300MH2006PLC162045",
                     industry="Auto Components (Tier-1 supplier)", constitution="Public Limited",
                     inc_year=2006, promoter_holding_pct=62.5, rating="CRISIL A / Stable", bureau_score=782),
        years=["FY2023", "FY2024", "FY2025"],
        rev_prev=360.0, rev=[420, 505, 590], ebitda_m=[0.170, 0.178, 0.185],
        cogs_pct=0.60, emp_pct=0.08, dep=[14, 16, 19], fin_rate=0.095,
        capex=[40, 45, 35], lt_raised=[25, 30, 20], lt_repaid=[14, 15, 16], payout=0.10,
        dio=55, dso=58, dpo=52, nfa0=230.0, cash0=15.0, lt0=95.0, st0=38.0, share_cap=25.0, cm_pct=0.13,
        existing=[("HDFC Bank", "Term Loan", 0.30, 9.2, 6.0), ("Axis Bank", "Term Loan", 0.28, 9.4, 6.0),
                  ("State Bank of India", "Working Capital CC/OD", 0.60, 9.0, 0),
                  ("ICICI Bank", "Working Capital CC/OD", 0.40, 9.1, 0),
                  ("Sundaram Finance", "Term Loan", 0.22, 10.2, 5.0), ("Debenture Trustee - NCD Series I", "NCD", 0.20, 9.8, 5.0)],
        proposed=dict(facility_type="Term Loan", amount=30.0, tenure_years=5.0, rate_pct=10.75, moratorium_months=6,
                      refinance_amount=0.0, collateral_value=52.0,
                      purpose="Capacity expansion - new forging line at Pune plant (Capex)"),
    ),
    "Moderate - Bharat Agro Foods Pvt Ltd": dict(
        profile=dict(name="Bharat Agro Foods Pvt Ltd", cin="U15400GJ2011PTC064512",
                     industry="Packaged Foods & Agro-processing", constitution="Private Limited",
                     inc_year=2011, promoter_holding_pct=71.0, rating="CARE BBB / Stable", bureau_score=712),
        years=["FY2023", "FY2024", "FY2025"],
        rev_prev=290.0, rev=[310, 340, 365], ebitda_m=[0.140, 0.140, 0.138],
        cogs_pct=0.70, emp_pct=0.06, dep=[11, 12, 13], fin_rate=0.105,
        capex=[18, 22, 15], lt_raised=[8, 15, 10], lt_repaid=[10, 11, 12], payout=0.05,
        dio=70, dso=64, dpo=46, nfa0=150.0, cash0=6.0, lt0=62.0, st0=36.0, share_cap=20.0, cm_pct=0.17,
        existing=[("Bank of Baroda", "Term Loan", 0.35, 10.0, 8.0), ("Kotak Mahindra Bank", "Term Loan", 0.30, 10.4, 7.0),
                  ("Bank of Baroda", "Working Capital CC/OD", 0.62, 10.0, 0),
                  ("Punjab National Bank", "Working Capital CC/OD", 0.38, 10.25, 0),
                  ("Tata Capital", "Term Loan", 0.35, 11.2, 6.0)],
        proposed=dict(facility_type="Term Loan", amount=25.0, tenure_years=6.0, rate_pct=11.50, moratorium_months=12,
                      refinance_amount=0.0, collateral_value=34.0,
                      purpose="Setting up a second processing unit and cold-chain storage"),
    ),
    "Stressed - Coastal Textile Mills Ltd": dict(
        profile=dict(name="Coastal Textile Mills Ltd", cin="L17110TN1998PLC040221",
                     industry="Textiles - Spinning & Weaving", constitution="Public Limited",
                     inc_year=1998, promoter_holding_pct=44.0, rating="ICRA BB / Negative", bureau_score=598),
        years=["FY2023", "FY2024", "FY2025"],
        rev_prev=235.0, rev=[228, 210, 198], ebitda_m=[0.095, 0.075, 0.062],
        cogs_pct=0.74, emp_pct=0.09, dep=[12, 12, 12], fin_rate=0.112,
        capex=[8, 6, 5], lt_raised=[5, 10, 15], lt_repaid=[12, 13, 14], payout=0.0,
        dio=92, dso=84, dpo=40, nfa0=165.0, cash0=5.0, lt0=80.0, st0=48.0, share_cap=30.0, cm_pct=0.20,
        existing=[("Indian Overseas Bank", "Term Loan", 0.40, 11.0, 4.0), ("Union Bank of India", "Term Loan", 0.35, 11.2, 4.0),
                  ("Union Bank of India", "Working Capital CC/OD", 0.70, 11.5, 0),
                  ("Canara Bank", "Working Capital CC/OD", 0.30, 11.5, 0),
                  ("Aditya Birla Finance", "Term Loan", 0.25, 12.5, 3.0)],
        proposed=dict(facility_type="Term Loan", amount=20.0, tenure_years=5.0, rate_pct=12.50, moratorium_months=12,
                      refinance_amount=0.0, collateral_value=22.0,
                      purpose="Modernisation of spinning unit and working-capital funding"),
    ),
}


def list_sample_profiles() -> list[str]:
    return list(PROFILES.keys())


def generate_sample(profile_name: str) -> ApplicantData:
    p = PROFILES[profile_name]
    n = len(p["rev"])
    years = p["years"]

    # Series with an extra "year 0" at the front (used only to derive opening balances / working-capital movement)
    rev = np.array([p["rev_prev"], *p["rev"]], dtype=float)
    cogs = rev * p["cogs_pct"]
    emp = rev * p["emp_pct"]
    ebitda = np.array([p["rev_prev"] * p["ebitda_m"][0], *[r * m for r, m in zip(p["rev"], p["ebitda_m"])]])
    oth_opex = rev - cogs - emp - ebitda
    other_inc = rev * 0.004

    inv = cogs * p["dio"] / 365
    rec = rev * p["dso"] / 365
    pay = cogs * p["dpo"] / 365
    oca = rev * 0.02
    ocl = rev * 0.03
    nwc = inv + rec + oca - pay - ocl

    # Constant "other" balance-sheet heads
    cwip, intang, ninv, onca, oncl = 8.0, 3.0, 5.0, 6.0, 4.0

    # ---- opening (year-0) balance sheet; reserves is the balancing figure ----
    nfa = p["nfa0"]
    cash = p["cash0"]
    lt_total = p["lt0"]
    st = p["st0"]
    assets0 = nfa + cwip + intang + ninv + onca + inv[0] + rec[0] + cash + oca[0]
    reserves = assets0 - (p["share_cap"] + lt_total + st + pay[0] + ocl[0] + oncl)

    bs_rows, pl_rows, cf_rows = [], [], []
    for i in range(1, n + 1):
        dep = p["dep"][i - 1]
        fin = (lt_total + st) * p["fin_rate"]                       # interest on opening debt
        pbt = ebitda[i] + other_inc[i] - dep - fin
        tax = max(pbt, 0) * TAX_RATE
        pat = pbt - tax
        div = max(pat, 0) * p["payout"]

        capex = p["capex"][i - 1]
        raised, repaid = p["lt_raised"][i - 1], p["lt_repaid"][i - 1]
        d_nwc = nwc[i] - nwc[i - 1]
        cfo = pat + dep + fin - d_nwc                               # pre-interest CFO
        net_cash = cfo - capex + raised - repaid - fin - div
        new_cash = cash + net_cash

        floor = rev[i] * 0.012
        st_draw = 0.0
        if new_cash < floor:                                        # top up with CC/OD so cash stays positive
            st_draw = floor - new_cash
            new_cash = floor
        st += st_draw

        nfa = nfa + capex - dep
        lt_total = lt_total + raised - repaid
        reserves = reserves + pat - div
        cash = new_cash

        cm = lt_total * p["cm_pct"]
        bs_rows.append({
            "Share Capital": p["share_cap"], "Reserves & Surplus": reserves,
            "Long Term Borrowings": lt_total - cm, "Short Term Borrowings": st, "Current Maturities of LTD": cm,
            "Trade Payables": pay[i], "Other Current Liabilities": ocl[i], "Other Non-Current Liabilities": oncl,
            "Net Fixed Assets": nfa, "Capital Work in Progress": cwip, "Intangible Assets": intang,
            "Non-Current Investments": ninv, "Other Non-Current Assets": onca, "Inventories": inv[i],
            "Trade Receivables": rec[i], "Cash & Bank Balances": cash, "Other Current Assets": oca[i],
        })
        pl_rows.append({
            "Revenue from Operations": rev[i], "Other Income": other_inc[i], "Cost of Goods Sold": cogs[i],
            "Employee Expenses": emp[i], "Other Operating Expenses": oth_opex[i],
            "Depreciation & Amortization": dep, "Finance Costs": fin, "Tax Expense": tax,
        })
        cf_rows.append({
            "Cash Flow from Operations": cfo, "Capital Expenditure": capex, "Other Investing Cash Flows": 0.0,
            "Debt Raised": raised + st_draw, "Debt Repaid": repaid, "Interest Paid": fin, "Dividends Paid": div,
        })

    def to_df(rows, items):
        return pd.DataFrame(rows, index=years)[list(items)].T.round(2)

    bs, pl, cf = to_df(bs_rows, BS_ITEMS), to_df(pl_rows, PNL_ITEMS), to_df(cf_rows, CF_ITEMS)

    # ---- existing debt schedule: split latest balance-sheet debt across lenders --------------
    lt_latest = float(bs.loc[["Long Term Borrowings", "Current Maturities of LTD"], years[-1]].sum())
    st_latest = float(bs.loc["Short Term Borrowings", years[-1]])
    tl_share = sum(s for _, t, s, _, _ in p["existing"] if t != "Working Capital CC/OD")
    cc_share = sum(s for _, t, s, _, _ in p["existing"] if t == "Working Capital CC/OD")
    debt_rows = []
    for lender, ftype, share, rate, rem in p["existing"]:
        if ftype == "Working Capital CC/OD":
            out = st_latest * share / cc_share
            debt_rows.append([lender, ftype, round(out / 0.78, 1), round(out, 2), rate, 0.0, round(out * rate / 100, 2)])
        else:
            out = lt_latest * share / tl_share
            debt_rows.append([lender, ftype, round(out * 1.15, 1), round(out, 2), rate,
                              round(out / rem, 2), round(out * rate / 100, 2)])
    existing = pd.DataFrame(debt_rows, columns=DEBT_COLUMNS)

    return ApplicantData(dict(p["profile"]), years, bs, pl, cf, existing, dict(p["proposed"]), [])


# --------------------------------------------------------------------------- #
# Excel template
# --------------------------------------------------------------------------- #
def build_excel_template(data: ApplicantData) -> bytes:
    """Serialise an ApplicantData to the exact workbook layout the ingestion module expects."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        pd.DataFrame({
            "Field": [label for _, label in APPLICANT_FIELDS],
            "Value": [data.profile.get(k) for k, _ in APPLICANT_FIELDS],
        }).to_excel(xw, sheet_name="Applicant", index=False)
        pd.DataFrame({
            "Field": [label for _, label in PROPOSED_FIELDS],
            "Value": [data.proposed.get(k) for k, _ in PROPOSED_FIELDS],
        }).to_excel(xw, sheet_name="Proposed", index=False)
        for sheet, df in (("BalanceSheet", data.balance_sheet), ("PnL", data.pnl), ("CashFlow", data.cashflow)):
            out = df.copy()
            out.index.name = "Line Item"
            out.reset_index().to_excel(xw, sheet_name=sheet, index=False)
        data.existing_debt.to_excel(xw, sheet_name="ExistingDebt", index=False)
        pd.DataFrame({"Instructions": [
            "All amounts in INR Crore. Keep sheet names and the first-column labels unchanged.",
            "Statements: first column 'Line Item', then one column per fiscal year (oldest -> latest), e.g. FY2023, FY2024, FY2025.",
            "Capital Expenditure and Debt Repaid are entered as POSITIVE numbers.",
            "Long Term Borrowings exclude current maturities (reported separately).",
            "Cash Flow from Operations is stated BEFORE interest paid (interest sits under financing).",
            "ExistingDebt: Facility Type = Term Loan / Working Capital CC/OD / NCD. Annual Principal & Interest = next-12-month obligation.",
            "Proposed: Refinance of Existing Debt = portion of the new loan used to take over existing borrowings.",
        ]}).to_excel(xw, sheet_name="README", index=False)
        for ws in xw.book.worksheets:
            ws.column_dimensions["A"].width = 38
            for col in "BCDEFGH":
                ws.column_dimensions[col].width = 20
    return buf.getvalue()
