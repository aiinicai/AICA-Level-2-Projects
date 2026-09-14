from sqlalchemy.orm import Session
from services.fs_generator import generate_financial_statements
from schemas import RatioItem
from typing import List

def calculate_ratios(client_id: int, db: Session) -> List[RatioItem]:
    fs = generate_financial_statements(client_id, db)
    
    # Extract line values from Balance Sheet & P&L
    bs_map_cy = {line.particulars.strip(): line.cy_amount for line in fs.balance_sheet}
    bs_map_py = {line.particulars.strip(): line.py_amount for line in fs.balance_sheet}
    
    pl_map_cy = {line.particulars.strip(): line.cy_amount for line in fs.profit_and_loss}
    pl_map_py = {line.particulars.strip(): line.py_amount for line in fs.profit_and_loss}

    # Balance Sheet Items
    cy_ca = bs_map_cy.get("2. Current Assets", 0.0)
    py_ca = bs_map_py.get("2. Current Assets", 0.0)
    
    cy_cl = bs_map_cy.get("3. Current Liabilities", 0.0)
    py_cl = bs_map_py.get("3. Current Liabilities", 0.0)

    cy_sf = bs_map_cy.get("1. Shareholders' Funds", 0.0)
    py_sf = bs_map_py.get("1. Shareholders' Funds", 0.0)

    cy_ltb = bs_map_cy.get("(a) Long-term Borrowings", 0.0)
    py_ltb = bs_map_py.get("(a) Long-term Borrowings", 0.0)

    cy_stb = bs_map_cy.get("(a) Short-term Borrowings", 0.0)
    py_stb = bs_map_py.get("(a) Short-term Borrowings", 0.0)

    cy_tot_debt = cy_ltb + cy_stb
    py_tot_debt = py_ltb + py_stb

    cy_tr = bs_map_cy.get("(b) Trade Receivables", 0.0)
    py_tr = bs_map_py.get("(b) Trade Receivables", 0.0)

    cy_tp = bs_map_cy.get("(b) Trade Payables", 0.0)
    py_tp = bs_map_py.get("(b) Trade Payables", 0.0)

    cy_inv = bs_map_cy.get("(a) Inventories", 0.0)
    py_inv = bs_map_py.get("(a) Inventories", 0.0)

    # P&L Items
    cy_rev = pl_map_cy.get("I. Revenue from Operations", 0.0)
    py_rev = pl_map_py.get("I. Revenue from Operations", 0.0)

    cy_pbt = pl_map_cy.get("V. Profit Before Tax (III - IV)", 0.0)
    py_pbt = pl_map_py.get("V. Profit Before Tax (III - IV)", 0.0)

    cy_pat = pl_map_cy.get("VII. Profit After Tax (V - VI)", 0.0)
    py_pat = pl_map_py.get("VII. Profit After Tax (V - VI)", 0.0)

    cy_fc = pl_map_cy.get("Finance Costs", 0.0)
    py_fc = pl_map_py.get("Finance Costs", 0.0)

    cy_dep = pl_map_cy.get("Depreciation and Amortisation Expense", 0.0)
    py_dep = pl_map_py.get("Depreciation and Amortisation Expense", 0.0)

    cy_mc = pl_map_cy.get("Cost of Materials Consumed", 0.0)
    py_mc = pl_map_py.get("Cost of Materials Consumed", 0.0)
    cy_pst = pl_map_cy.get("Purchases of Stock-in-Trade", 0.0)
    py_pst = pl_map_py.get("Purchases of Stock-in-Trade", 0.0)
    cy_cogs = cy_mc + cy_pst
    py_cogs = py_mc + py_pst
    if cy_cogs == 0: cy_cogs = cy_rev * 0.7
    if py_cogs == 0: py_cogs = py_rev * 0.7

    cy_ebitda = cy_pbt + cy_fc + cy_dep
    py_ebitda = py_pbt + py_fc + py_dep

    # Helper for ratio calc
    def safe_div(num, den):
        return round(num / den, 2) if den != 0 else 0.0

    def calc_mov(cy, py):
        if py == 0: return "+100.0%" if cy > 0 else "0.0%"
        diff = ((cy - py) / abs(py)) * 100
        return f"{'+' if diff >= 0 else ''}{diff:.1f}%"

    # 1. Current Ratio
    cr_cy = safe_div(cy_ca, cy_cl)
    cr_py = safe_div(py_ca, py_cl)
    cr_interp = "Satisfactory liquidity buffer (ideal benchmark is 1.5 - 2.0)." if cr_cy >= 1.33 else "Liquidity is tight. Working capital management review recommended."

    # 2. Debt Equity Ratio
    de_cy = safe_div(cy_tot_debt, cy_sf)
    de_py = safe_div(py_tot_debt, py_sf)
    de_interp = "Comfortable leverage levels well within benchmark threshold of 2.0." if de_cy <= 2.0 else "High leverage ratio exceeding 2.0 limit. Monitor debt servicing capacity."

    # 3. Net Profit Ratio
    np_cy = safe_div(cy_pat * 100, cy_rev)
    np_py = safe_div(py_pat * 100, py_rev)
    np_interp = f"Healthy net profit margin of {np_cy}% driven by cost controls." if np_cy >= 5.0 else f"Low net margin of {np_cy}%. Review overhead expenditure."

    # 4. EBITDA Margin
    eb_cy = safe_div(cy_ebitda * 100, cy_rev)
    eb_py = safe_div(py_ebitda * 100, py_rev)
    eb_interp = f"Strong operating cash margin of {eb_cy}%." if eb_cy >= 10.0 else f"EBITDA margin stands at {eb_cy}%."

    # 5. Return on Equity
    roe_cy = safe_div(cy_pat * 100, cy_sf)
    roe_py = safe_div(py_pat * 100, py_sf)
    roe_interp = f"Good return on net worth of {roe_cy}%." if roe_cy >= 12.0 else f"Return on equity is {roe_cy}%."

    # 6. Trade Receivable Days
    tr_days_cy = safe_div(cy_tr * 365, cy_rev)
    tr_days_py = safe_div(py_tr * 365, py_rev)
    tr_interp = f"Average collection period is {tr_days_cy} days. Prompt collection cycle." if tr_days_cy <= 90 else f"Collection period extended to {tr_days_cy} days. Check overdue receivables."

    # 7. Trade Payable Days
    tp_days_cy = safe_div(cy_tp * 365, cy_cogs)
    tp_days_py = safe_div(py_tp * 365, py_cogs)
    tp_interp = f"Vendor payment turnaround is {tp_days_cy} days."

    # 8. Inventory Days
    inv_days_cy = safe_div(cy_inv * 365, cy_cogs)
    inv_days_py = safe_div(py_inv * 365, py_cogs)
    inv_interp = f"Inventory holding cycle of {inv_days_cy} days."

    ratios = [
        RatioItem(code="R01", name="Current Ratio", formula="Current Assets / Current Liabilities", cy_value=cr_cy, py_value=cr_py, unit="times", movement=calc_mov(cr_cy, cr_py), interpretation=cr_interp),
        RatioItem(code="R02", name="Debt Equity Ratio", formula="Total Debt / Shareholders' Equity", cy_value=de_cy, py_value=de_py, unit="times", movement=calc_mov(de_cy, de_py), interpretation=de_interp),
        RatioItem(code="R03", name="Net Profit Ratio", formula="(Net Profit After Tax / Revenue) * 100", cy_value=np_cy, py_value=np_py, unit="%", movement=calc_mov(np_cy, np_py), interpretation=np_interp),
        RatioItem(code="R04", name="EBITDA Margin", formula="(EBITDA / Revenue) * 100", cy_value=eb_cy, py_value=eb_py, unit="%", movement=calc_mov(eb_cy, eb_py), interpretation=eb_interp),
        RatioItem(code="R05", name="Return on Equity", formula="(Net Profit After Tax / Equity) * 100", cy_value=roe_cy, py_value=roe_py, unit="%", movement=calc_mov(roe_cy, roe_py), interpretation=roe_interp),
        RatioItem(code="R06", name="Trade Receivable Days", formula="(Trade Receivables / Revenue) * 365", cy_value=tr_days_cy, py_value=tr_days_py, unit="days", movement=calc_mov(tr_days_cy, tr_days_py), interpretation=tr_interp),
        RatioItem(code="R07", name="Trade Payable Days", formula="(Trade Payables / COGS) * 365", cy_value=tp_days_cy, py_value=tp_days_py, unit="days", movement=calc_mov(tp_days_cy, tp_days_py), interpretation=tp_interp),
        RatioItem(code="R08", name="Inventory Days", formula="(Inventories / COGS) * 365", cy_value=inv_days_cy, py_value=inv_days_py, unit="days", movement=calc_mov(inv_days_cy, inv_days_py), interpretation=inv_interp),
    ]

    return ratios
