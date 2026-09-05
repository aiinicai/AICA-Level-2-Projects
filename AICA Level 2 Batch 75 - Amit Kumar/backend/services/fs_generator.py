from sqlalchemy.orm import Session
from models import TrialBalanceLine
from schemas import BalanceSheetLine, ProfitAndLossLine, FinancialStatementResponse

def generate_financial_statements(client_id: int, db: Session) -> FinancialStatementResponse:
    lines = db.query(TrialBalanceLine).filter(TrialBalanceLine.client_id == client_id).all()
    
    def get_sums(class_name: str):
        cy_tot = 0.0
        py_tot = 0.0
        for l in lines:
            if (l.final_classification or '').lower() == class_name.lower():
                cy_tot += l.cy_amount
                py_tot += l.py_amount
        return cy_tot, py_tot

    # -------------------------------------------------------------
    # PROFIT AND LOSS FIRST (to compute PAT for Reserves & Surplus)
    # -------------------------------------------------------------
    cy_rev_raw, py_rev_raw = get_sums("Revenue from Operations")
    cy_rev, py_rev = abs(cy_rev_raw), abs(py_rev_raw)

    cy_oi_raw, py_oi_raw = get_sums("Other Income")
    cy_oi, py_oi = abs(cy_oi_raw), abs(py_oi_raw)

    cy_tot_inc = cy_rev + cy_oi
    py_tot_inc = py_rev + py_oi

    cy_mc, py_mc = get_sums("Cost of Materials Consumed")
    cy_pst, py_pst = get_sums("Purchases of Stock-in-Trade")
    cy_cinv, py_cinv = get_sums("Changes in Inventories")
    cy_ebe, py_ebe = get_sums("Employee Benefit Expenses")
    cy_fc, py_fc = get_sums("Finance Costs")
    cy_dep, py_dep = get_sums("Depreciation and Amortisation Expense")
    cy_oe, py_oe = get_sums("Other Expenses")

    cy_tot_exp = cy_mc + cy_pst + cy_cinv + cy_ebe + cy_fc + cy_dep + cy_oe
    py_tot_exp = py_mc + py_pst + py_cinv + py_ebe + py_fc + py_dep + py_oe

    cy_pbt = cy_tot_inc - cy_tot_exp
    py_pbt = py_tot_inc - py_tot_exp

    cy_tax, py_tax = get_sums("Tax Expense")
    cy_pat = cy_pbt - cy_tax
    py_pat = py_pbt - py_tax

    pl_lines = [
        ProfitAndLossLine(particulars="I. Revenue from Operations", note_number="6.1", cy_amount=cy_rev, py_amount=py_rev),
        ProfitAndLossLine(particulars="II. Other Income", note_number="6.2", cy_amount=cy_oi, py_amount=py_oi),
        ProfitAndLossLine(particulars="III. Total Income (I + II)", note_number="", cy_amount=cy_tot_inc, py_amount=py_tot_inc, is_subtotal=True),
        ProfitAndLossLine(particulars="IV. Expenses:", note_number="", cy_amount=0, py_amount=0, is_header=True),
        ProfitAndLossLine(particulars="   Cost of Materials Consumed", note_number="7.1", cy_amount=cy_mc, py_amount=py_mc),
        ProfitAndLossLine(particulars="   Purchases of Stock-in-Trade", note_number="7.1", cy_amount=cy_pst, py_amount=py_pst),
        ProfitAndLossLine(particulars="   Changes in Inventories", note_number="7.1", cy_amount=cy_cinv, py_amount=py_cinv),
        ProfitAndLossLine(particulars="   Employee Benefit Expenses", note_number="7.2", cy_amount=cy_ebe, py_amount=py_ebe),
        ProfitAndLossLine(particulars="   Finance Costs", note_number="7.3", cy_amount=cy_fc, py_amount=py_fc),
        ProfitAndLossLine(particulars="   Depreciation and Amortisation Expense", note_number="7.4", cy_amount=cy_dep, py_amount=py_dep),
        ProfitAndLossLine(particulars="   Other Expenses", note_number="7.5", cy_amount=cy_oe, py_amount=py_oe),
        ProfitAndLossLine(particulars="Total Expenses (IV)", note_number="", cy_amount=cy_tot_exp, py_amount=py_tot_exp, is_subtotal=True),
        ProfitAndLossLine(particulars="V. Profit Before Tax (III - IV)", note_number="", cy_amount=cy_pbt, py_amount=py_pbt, is_subtotal=True),
        ProfitAndLossLine(particulars="VI. Tax Expense", note_number="7.6", cy_amount=cy_tax, py_amount=py_tax),
        ProfitAndLossLine(particulars="VII. Profit After Tax (V - VI)", note_number="", cy_amount=cy_pat, py_amount=py_pat, is_total=True),
    ]

    # -------------------------------------------------------------
    # BALANCE SHEET (Includes Current Year PAT in Reserves & Surplus)
    # -------------------------------------------------------------
    cy_sc_raw, py_sc_raw = get_sums("Share Capital")
    cy_sc, py_sc = abs(cy_sc_raw), abs(py_sc_raw)

    cy_rs_raw, py_rs_raw = get_sums("Reserves and Surplus")
    cy_rs = abs(cy_rs_raw) + cy_pat
    py_rs = abs(py_rs_raw) + py_pat

    cy_sf = cy_sc + cy_rs
    py_sf = py_sc + py_rs

    cy_ltb_raw, py_ltb_raw = get_sums("Long-term Borrowings")
    cy_ltb, py_ltb = abs(cy_ltb_raw), abs(py_ltb_raw)

    cy_ltp_raw, py_ltp_raw = get_sums("Long-term Provisions")
    cy_ltp, py_ltp = abs(cy_ltp_raw), abs(py_ltp_raw)

    cy_ncl = cy_ltb + cy_ltp
    py_ncl = py_ltb + py_ltp

    cy_stb_raw, py_stb_raw = get_sums("Short-term Borrowings")
    cy_stb, py_stb = abs(cy_stb_raw), abs(py_stb_raw)

    cy_tp_raw, py_tp_raw = get_sums("Trade Payables")
    cy_tp, py_tp = abs(cy_tp_raw), abs(py_tp_raw)

    cy_ocl_raw, py_ocl_raw = get_sums("Other Current Liabilities")
    cy_ocl, py_ocl = abs(cy_ocl_raw), abs(py_ocl_raw)

    cy_stp_raw, py_stp_raw = get_sums("Short-term Provisions")
    cy_stp, py_stp = abs(cy_stp_raw), abs(py_stp_raw)

    cy_cl = cy_stb + cy_tp + cy_ocl + cy_stp
    py_cl = py_stb + py_tp + py_ocl + py_stp

    total_eq_liab_cy = cy_sf + cy_ncl + cy_cl
    total_eq_liab_py = py_sf + py_ncl + py_cl

    # Assets
    cy_ppe, py_ppe = get_sums("Property, Plant and Equipment")
    cy_cwip, py_cwip = get_sums("Capital Work-in-Progress")
    cy_nci, py_nci = get_sums("Non-current Investments")
    cy_ltla, py_ltla = get_sums("Long-term Loans and Advances")
    cy_onca, py_onca = get_sums("Other Non-current Assets")

    cy_nca = cy_ppe + cy_cwip + cy_nci + cy_ltla + cy_onca
    py_nca = py_ppe + py_cwip + py_nci + py_ltla + py_onca

    cy_inv, py_inv = get_sums("Inventories")
    cy_tr, py_tr = get_sums("Trade Receivables")
    cy_cb, py_cb = get_sums("Cash and Bank Balances")
    cy_stla, py_stla = get_sums("Short-term Loans and Advances")
    cy_oca, py_oca = get_sums("Other Current Assets")

    cy_ca = cy_inv + cy_tr + cy_cb + cy_stla + cy_oca
    py_ca = py_inv + py_tr + py_cb + py_stla + py_oca

    total_assets_cy = cy_nca + cy_ca
    total_assets_py = py_nca + py_ca

    diff_cy = round(total_eq_liab_cy - total_assets_cy, 2)
    is_tallied = abs(diff_cy) < 0.01

    bs_lines = [
        BalanceSheetLine(particulars="EQUITY AND LIABILITIES", note_number="", cy_amount=0, py_amount=0, is_header=True),
        BalanceSheetLine(particulars="1. Shareholders' Funds", note_number="", cy_amount=cy_sf, py_amount=py_sf, is_subtotal=True),
        BalanceSheetLine(particulars="   (a) Share Capital", note_number="1.1", cy_amount=cy_sc, py_amount=py_sc),
        BalanceSheetLine(particulars="   (b) Reserves and Surplus", note_number="1.2", cy_amount=cy_rs, py_amount=py_rs),
        
        BalanceSheetLine(particulars="2. Non-Current Liabilities", note_number="", cy_amount=cy_ncl, py_amount=py_ncl, is_subtotal=True),
        BalanceSheetLine(particulars="   (a) Long-term Borrowings", note_number="2.1", cy_amount=cy_ltb, py_amount=py_ltb),
        BalanceSheetLine(particulars="   (b) Long-term Provisions", note_number="2.2", cy_amount=cy_ltp, py_amount=py_ltp),
        
        BalanceSheetLine(particulars="3. Current Liabilities", note_number="", cy_amount=cy_cl, py_amount=py_cl, is_subtotal=True),
        BalanceSheetLine(particulars="   (a) Short-term Borrowings", note_number="3.1", cy_amount=cy_stb, py_amount=py_stb),
        BalanceSheetLine(particulars="   (b) Trade Payables", note_number="3.2", cy_amount=cy_tp, py_amount=py_tp),
        BalanceSheetLine(particulars="   (c) Other Current Liabilities", note_number="3.3", cy_amount=cy_ocl, py_amount=py_ocl),
        BalanceSheetLine(particulars="   (d) Short-term Provisions", note_number="3.4", cy_amount=cy_stp, py_amount=py_stp),
        
        BalanceSheetLine(particulars="TOTAL EQUITY AND LIABILITIES", note_number="", cy_amount=total_eq_liab_cy, py_amount=total_eq_liab_py, is_total=True),

        BalanceSheetLine(particulars="ASSETS", note_number="", cy_amount=0, py_amount=0, is_header=True),
        BalanceSheetLine(particulars="1. Non-Current Assets", note_number="", cy_amount=cy_nca, py_amount=py_nca, is_subtotal=True),
        BalanceSheetLine(particulars="   (a) Property, Plant and Equipment", note_number="4.1", cy_amount=cy_ppe, py_amount=py_ppe),
        BalanceSheetLine(particulars="   (b) Capital Work-in-Progress", note_number="4.2", cy_amount=cy_cwip, py_amount=py_cwip),
        BalanceSheetLine(particulars="   (c) Non-current Investments", note_number="4.3", cy_amount=cy_nci, py_amount=py_nci),
        BalanceSheetLine(particulars="   (d) Long-term Loans and Advances", note_number="4.4", cy_amount=cy_ltla, py_amount=py_ltla),
        BalanceSheetLine(particulars="   (e) Other Non-current Assets", note_number="4.5", cy_amount=cy_onca, py_amount=py_onca),
        
        BalanceSheetLine(particulars="2. Current Assets", note_number="", cy_amount=cy_ca, py_amount=py_ca, is_subtotal=True),
        BalanceSheetLine(particulars="   (a) Inventories", note_number="5.1", cy_amount=cy_inv, py_amount=py_inv),
        BalanceSheetLine(particulars="   (b) Trade Receivables", note_number="5.2", cy_amount=cy_tr, py_amount=py_tr),
        BalanceSheetLine(particulars="   (c) Cash and Bank Balances", note_number="5.3", cy_amount=cy_cb, py_amount=py_cb),
        BalanceSheetLine(particulars="   (d) Short-term Loans and Advances", note_number="5.4", cy_amount=cy_stla, py_amount=py_stla),
        BalanceSheetLine(particulars="   (e) Other Current Assets", note_number="5.5", cy_amount=cy_oca, py_amount=py_oca),
        
        BalanceSheetLine(particulars="TOTAL ASSETS", note_number="", cy_amount=total_assets_cy, py_amount=total_assets_py, is_total=True),
    ]

    return FinancialStatementResponse(
        balance_sheet=bs_lines,
        profit_and_loss=pl_lines,
        is_tallied=is_tallied,
        difference=diff_cy
    )
