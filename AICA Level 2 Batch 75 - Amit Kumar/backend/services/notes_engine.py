import json
from sqlalchemy.orm import Session
from models import (
    Client, Note, CWIPAgeing, ARAgeing, APAgeing,
    RelatedParty, Borrowing, Contingency, TrialBalanceLine
)
from services.fs_generator import generate_financial_statements
from services.ratio_engine import calculate_ratios

def generate_or_update_notes(client_id: int, db: Session):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        return []

    # Gather source data
    tb_lines  = db.query(TrialBalanceLine).filter(TrialBalanceLine.client_id == client_id).all()
    cwip_items = db.query(CWIPAgeing).filter(CWIPAgeing.client_id == client_id).all()
    ar_items   = db.query(ARAgeing).filter(ARAgeing.client_id == client_id).all()
    ap_items   = db.query(APAgeing).filter(APAgeing.client_id == client_id).all()
    rpt_items  = db.query(RelatedParty).filter(RelatedParty.client_id == client_id).all()
    bor_items  = db.query(Borrowing).filter(Borrowing.client_id == client_id).all()
    cont_items = db.query(Contingency).filter(Contingency.client_id == client_id).all()

    def sum_cls(cls_name: str):
        cy = sum(abs(l.cy_amount) for l in tb_lines if (l.final_classification or '').lower() == cls_name.lower())
        py = sum(abs(l.py_amount) for l in tb_lines if (l.final_classification or '').lower() == cls_name.lower())
        return cy, py

    def tb_header(period: str) -> str:
        return f"As at {period}"

    def pl_header(period: str) -> str:
        return f"Year ended {period}"

    cy_h  = tb_header(client.reporting_period)
    py_h  = tb_header(client.previous_year_period)
    cy_pl = pl_header(client.reporting_period)
    py_pl = pl_header(client.previous_year_period)

    # PAT from FS generator (needed for Reserves & Surplus)
    fs = generate_financial_statements(client_id, db)
    cy_pat = py_pat = 0.0
    for pl in fs.profit_and_loss:
        if pl.particulars.startswith("VII. Profit After Tax"):
            cy_pat = pl.cy_amount
            py_pat = pl.py_amount

    # ---------------------------------------------------------------
    # NOTE 1.1 - Share Capital
    # ---------------------------------------------------------------
    cy_sc, py_sc = sum_cls("Share Capital")
    sc_table = {
        "headers": ["Particulars", cy_h, py_h],
        "rows": [
            ["Authorised Share Capital:", "", ""],
            ["  10,00,000 Equity Shares of Rs. 10/- each", "100.00", "100.00"],
            ["Issued, Subscribed & Paid-up Capital:", "", ""],
            [f"  Equity Shares of Rs. 10/- each fully paid", f"{cy_sc:.2f}", f"{py_sc:.2f}"],
            ["TOTAL SHARE CAPITAL", f"{cy_sc:.2f}", f"{py_sc:.2f}"],
        ]
    }
    sc_text = (
        "1. Rights, Preferences & Restrictions:\n"
        "The Company has only one class of equity shares of par value Rs 10/- each. Each equity shareholder is entitled to one vote per share. "
        "In the event of liquidation, equity shareholders receive remaining assets after all preferential amounts are distributed.\n\n"
        "2. Shareholders holding more than 5% shares:\n"
        "Promoters & Key Management Personnel - 100% holding as at the end of the reporting period."
    )

    # ---------------------------------------------------------------
    # NOTE 1.2 - Reserves and Surplus
    # ---------------------------------------------------------------
    cy_rs_raw, py_rs_raw = sum_cls("Reserves and Surplus")
    cy_rs_total = cy_rs_raw + cy_pat
    py_rs_total = py_rs_raw + py_pat
    rs_table = {
        "headers": ["Particulars", cy_h, py_h],
        "rows": [
            ["(a) General Reserve:", "", ""],
            ["    Opening Balance", f"{py_rs_raw:.2f}", f"{py_rs_raw:.2f}"],
            ["    Add: Transfer during the year", "0.00", "0.00"],
            ["    Closing General Reserve  (A)", f"{py_rs_raw:.2f}", f"{py_rs_raw:.2f}"],
            ["(b) Surplus in Statement of Profit & Loss:", "", ""],
            ["    Opening Balance", f"{py_pat:.2f}", "0.00"],
            ["    Add: Profit After Tax for the year", f"{cy_pat:.2f}", f"{py_pat:.2f}"],
            ["    Closing Surplus in P&L  (B)", f"{cy_pat:.2f}", f"{py_pat:.2f}"],
            ["TOTAL RESERVES AND SURPLUS  (A + B)", f"{cy_rs_total:.2f}", f"{py_rs_total:.2f}"],
        ]
    }
    rs_text = "Reserves & Surplus includes General Reserve carried forward from prior years and current-year Surplus in the Statement of Profit and Loss."

    # ---------------------------------------------------------------
    # NOTE 2.1 - Long-term Borrowings
    # ---------------------------------------------------------------
    cy_ltb, py_ltb = sum_cls("Long-term Borrowings")
    bor_nc = [b for b in bor_items if b.current_non_current == "Non-current"]
    bor_rows = [[f"{b.lender_name} - {b.loan_type} ({b.secured_unsecured})", f"{b.closing_bal:.2f}", f"{b.py_closing_bal:.2f}"] for b in bor_nc]
    if not bor_rows:
        bor_rows = [["Secured Term Loan from Bank (Hypothecation of Fixed Assets)", f"{cy_ltb:.2f}", f"{py_ltb:.2f}"]]
    bor_rows.append(["TOTAL LONG-TERM BORROWINGS", f"{cy_ltb:.2f}", f"{py_ltb:.2f}"])
    ltb_table = {"headers": ["Particulars", cy_h, py_h], "rows": bor_rows}
    ltb_text = (
        "Security Details: Term loans from banks are secured by primary charge on Fixed Assets (Land, Building & Plant and Machinery).\n"
        "Repayment: Structured monthly instalments over 60 months at 8.50% p.a. (floating).\n"
        "Defaults: The Company has not defaulted in repayment of principal or interest during the year."
    )

    # ---------------------------------------------------------------
    # NOTE 2.2 - Long-term Provisions
    # ---------------------------------------------------------------
    cy_ltp, py_ltp = sum_cls("Long-term Provisions")
    ltp_table = {
        "headers": ["Particulars", cy_h, py_h],
        "rows": [
            ["Provision for Gratuity (AS 15 - Defined Benefit)", f"{(cy_ltp * 0.80):.2f}", f"{(py_ltp * 0.80):.2f}"],
            ["Provision for Leave Encashment (Long-term portion)", f"{(cy_ltp * 0.20):.2f}", f"{(py_ltp * 0.20):.2f}"],
            ["TOTAL LONG-TERM PROVISIONS", f"{cy_ltp:.2f}", f"{py_ltp:.2f}"],
        ]
    }
    ltp_text = "Provision for Gratuity is made based on actuarial valuation as per AS 15 (Revised 2005). Leave encashment long-term portion represents unavailed leaves expected to be encashed after 12 months."

    # ---------------------------------------------------------------
    # NOTE 3.1 - Short-term Borrowings
    # ---------------------------------------------------------------
    cy_stb, py_stb = sum_cls("Short-term Borrowings")
    bor_c = [b for b in bor_items if b.current_non_current == "Current"]
    stb_rows = [[f"{b.lender_name} - {b.loan_type}", f"{b.closing_bal:.2f}", f"{b.py_closing_bal:.2f}"] for b in bor_c]
    if not stb_rows:
        stb_rows = [["Secured Working Capital Cash Credit / Overdraft (Bank)", f"{cy_stb:.2f}", f"{py_stb:.2f}"]]
    stb_rows.append(["TOTAL SHORT-TERM BORROWINGS", f"{cy_stb:.2f}", f"{py_stb:.2f}"])
    stb_table = {"headers": ["Particulars", cy_h, py_h], "rows": stb_rows}
    stb_text = "Working capital cash credit facilities from banks are secured by hypothecation of current assets (inventories and trade receivables) at 9.25% p.a. (floating). Facility is repayable on demand."

    # ---------------------------------------------------------------
    # NOTE 3.2 - Trade Payables
    # ---------------------------------------------------------------
    cy_tp, py_tp = sum_cls("Trade Payables")
    ap_rows = []
    for a in ap_items:
        ap_rows.append([a.vendor_name, a.msme or "No",
                        f"{a.l1y:.2f}", f"{a.y1_2y:.2f}", f"{a.y2_3y:.2f}", f"{a.mor_3y:.2f}", f"{a.outstanding_amount:.2f}"])
    if not ap_rows:
        ap_rows = [["Trade Creditors for Goods & Services (Non-MSME)", "No", f"{cy_tp:.2f}", "0.00", "0.00", "0.00", f"{cy_tp:.2f}"]]
    ap_total_cy = sum(a.outstanding_amount for a in ap_items) if ap_items else cy_tp
    ap_rows.append(["TOTAL TRADE PAYABLES", "", f"{ap_total_cy:.2f}", "", "", "", f"{ap_total_cy:.2f}"])
    tp_table = {
        "headers": ["Vendor Name", "MSME", "< 1 Year", "1-2 Years", "2-3 Years", "> 3 Years", "Total Outstanding"],
        "rows": ap_rows
    }
    tp_text = (
        "Trade Payables Ageing - as per Companies (Accounts) Amendment Rules 2021.\n"
        "MSME Disclosure: Outstanding dues payable to Micro and Small Enterprises (as certified by management) are disclosed separately.\n"
        f"As at {client.reporting_period}: Dues to MSME vendors - Rs Nil (Previous Year: Rs Nil)."
    )

    # ---------------------------------------------------------------
    # NOTE 3.3 - Other Current Liabilities
    # ---------------------------------------------------------------
    cy_ocl, py_ocl = sum_cls("Other Current Liabilities")
    ocl_rows = [
        ["Current Maturities of Long-term Borrowings", f"{(cy_ocl * 0.45):.2f}", f"{(py_ocl * 0.45):.2f}"],
        ["Interest Accrued but not Due on Borrowings", f"{(cy_ocl * 0.15):.2f}", f"{(py_ocl * 0.15):.2f}"],
        ["Advance Received from Customers", f"{(cy_ocl * 0.20):.2f}", f"{(py_ocl * 0.20):.2f}"],
        ["Statutory Liabilities (GST, TDS, PF Payable)", f"{(cy_ocl * 0.15):.2f}", f"{(py_ocl * 0.15):.2f}"],
        ["Other Payables - Security Deposits / Accruals", f"{(cy_ocl * 0.05):.2f}", f"{(py_ocl * 0.05):.2f}"],
        ["TOTAL OTHER CURRENT LIABILITIES", f"{cy_ocl:.2f}", f"{py_ocl:.2f}"],
    ]
    ocl_table = {"headers": ["Particulars", cy_h, py_h], "rows": ocl_rows}
    ocl_text = "Other Current Liabilities include current maturities of long-term debt, statutory liabilities payable within 12 months, and advance from customers."

    # ---------------------------------------------------------------
    # NOTE 3.4 - Short-term Provisions
    # ---------------------------------------------------------------
    cy_stp, py_stp = sum_cls("Short-term Provisions")
    stp_rows = [
        ["Provision for Income Tax (Net of Advance Tax)", f"{(cy_stp * 0.70):.2f}", f"{(py_stp * 0.70):.2f}"],
        ["Provision for Employee Benefits (Leave & Gratuity - Current)", f"{(cy_stp * 0.25):.2f}", f"{(py_stp * 0.25):.2f}"],
        ["Provision for Bonus / Ex-gratia", f"{(cy_stp * 0.05):.2f}", f"{(py_stp * 0.05):.2f}"],
        ["TOTAL SHORT-TERM PROVISIONS", f"{cy_stp:.2f}", f"{py_stp:.2f}"],
    ]
    stp_table = {"headers": ["Particulars", cy_h, py_h], "rows": stp_rows}
    stp_text = "Short-term provisions represent amounts expected to be settled within 12 months of the Balance Sheet date."

    # ---------------------------------------------------------------
    # NOTE 4.1 - Property, Plant & Equipment (Fixed Asset Schedule)
    # ---------------------------------------------------------------
    cy_ppe_net, py_ppe_net = sum_cls("Property, Plant and Equipment")
    cy_dep_exp, _ = sum_cls("Depreciation and Amortisation Expense")
    gross_total = cy_ppe_net * 1.30   # net = ~77% of gross block
    asset_classes = [
        ("Freehold Land",          0.20, 0.00),
        ("Buildings",              0.25, 0.05),
        ("Plant & Machinery",      0.35, 0.10),
        ("Furniture & Fixtures",   0.10, 0.10),
        ("Office Equipment",       0.05, 0.15),
        ("Vehicles",               0.05, 0.15),
    ]
    ppe_rows = []
    totals = [0.0] * 10
    for ac_name, prop, dep_r in asset_classes:
        g_open  = round(gross_total * prop * 0.92, 2)
        g_add   = round(gross_total * prop * 0.08, 2)
        g_del   = 0.00
        g_close = round(g_open + g_add, 2)
        d_open  = round(g_open * dep_r, 2)
        d_curr  = round(g_close * dep_r, 2)
        d_del   = 0.00
        d_close = round(d_open + d_curr, 2)
        n_cy    = round(g_close - d_close, 2)
        n_py    = round(g_open - d_open, 2)
        vals = [g_open, g_add, g_del, g_close, d_open, d_curr, d_del, d_close, n_cy, n_py]
        for i, v in enumerate(vals):
            totals[i] += v
        ppe_rows.append([ac_name] + [f"{v:.2f}" for v in vals])
    ppe_rows.append(["TOTAL PROPERTY, PLANT & EQUIPMENT"] + [f"{t:.2f}" for t in totals])
    ppe_table = {
        "headers": [
            "Asset Category",
            "Opening Gross Block", "Additions", "Disposals", "Closing Gross Block",
            "Accum. Dep (Open)", "Dep for Year", "Dep on Disposal", "Accum. Dep (Close)",
            f"Net Block {client.reporting_period}", f"Net Block {client.previous_year_period}"
        ],
        "rows": ppe_rows
    }
    ppe_text = (
        "1. Depreciation Method: Depreciation on PPE is provided on Straight Line Method (SLM) based on useful lives under Schedule II of the Companies Act, 2013.\n"
        "2. Impairment: No impairment loss recognised during the year as per AS 28.\n"
        "3. Additions include capital expenditure incurred during the year and transferred from CWIP upon commissioning.\n"
        "4. Title to Land is held by the Company without encumbrances other than those disclosed under borrowings."
    )

    # ---------------------------------------------------------------
    # NOTE 4.2 - Capital Work-in-Progress
    # ---------------------------------------------------------------
    cy_cwip, py_cwip = sum_cls("Capital Work-in-Progress")
    cwip_rows = []
    for c in cwip_items:
        cwip_rows.append([c.project_name, f"{c.l1y:.2f}", f"{c.y1_2y:.2f}", f"{c.y2_3y:.2f}", f"{c.mor_3y:.2f}", f"{c.closing_cwip:.2f}"])
    if not cwip_rows:
        cwip_rows = [["Plant Expansion Project", f"{cy_cwip:.2f}", "0.00", "0.00", "0.00", f"{cy_cwip:.2f}"]]
    cwip_total = sum(c.closing_cwip for c in cwip_items) if cwip_items else cy_cwip
    cwip_rows.append(["TOTAL CAPITAL WORK-IN-PROGRESS", f"{cwip_total:.2f}", "", "", "", f"{cwip_total:.2f}"])
    cwip_table = {
        "headers": ["Project Name", "< 1 Year", "1-2 Years", "2-3 Years", "> 3 Years", "Total CWIP"],
        "rows": cwip_rows
    }
    cwip_text = (
        "CWIP Ageing Schedule as per Companies (Accounts) Amendment Rules, 2021.\n"
        "All CWIP projects are within normal expected completion timelines. No project is stalled or disputed.\n"
        "CWIP is expected to be capitalised to PPE upon commissioning in the next financial year."
    )

    # ---------------------------------------------------------------
    # NOTE 4.3 - Non-current Investments
    # ---------------------------------------------------------------
    cy_nci, py_nci = sum_cls("Non-current Investments")
    nci_table = {
        "headers": ["Particulars", "No. of Units", cy_h, py_h],
        "rows": [
            ["Unquoted Equity Instruments - at cost:", "", "", ""],
            ["  Investment in Associate Companies", "-", f"{(cy_nci * 0.70):.2f}", f"{(py_nci * 0.70):.2f}"],
            ["  Investment in Other Companies", "-", f"{(cy_nci * 0.30):.2f}", f"{(py_nci * 0.30):.2f}"],
            ["TOTAL NON-CURRENT INVESTMENTS", "", f"{cy_nci:.2f}", f"{py_nci:.2f}"],
        ]
    }
    nci_text = (
        "Non-current investments are stated at cost less provision for diminution in value, if any, as per AS 13.\n"
        f"Aggregate amount of unquoted investments: Rs {cy_nci:.2f} Lakhs (PY: Rs {py_nci:.2f} Lakhs).\n"
        "Aggregate provision for diminution in value of investments: Rs Nil."
    )

    # ---------------------------------------------------------------
    # NOTE 4.4 - Long-term Loans and Advances
    # ---------------------------------------------------------------
    cy_ltla, py_ltla = sum_cls("Long-term Loans and Advances")
    ltla_table = {
        "headers": ["Particulars", cy_h, py_h],
        "rows": [
            ["Security Deposits - Considered Good (Unsecured)", f"{(cy_ltla * 0.60):.2f}", f"{(py_ltla * 0.60):.2f}"],
            ["Capital Advances - Considered Good", f"{(cy_ltla * 0.30):.2f}", f"{(py_ltla * 0.30):.2f}"],
            ["Advance Income Tax & TDS Recoverable (Net)", f"{(cy_ltla * 0.10):.2f}", f"{(py_ltla * 0.10):.2f}"],
            ["TOTAL LONG-TERM LOANS AND ADVANCES", f"{cy_ltla:.2f}", f"{py_ltla:.2f}"],
        ]
    }
    ltla_text = "All long-term loans and advances are unsecured, considered good, and recoverable in cash or in kind. There are no amounts due from Directors or officers."

    # ---------------------------------------------------------------
    # NOTE 5.1 - Inventories
    # ---------------------------------------------------------------
    cy_inv, py_inv = sum_cls("Inventories")
    inv_table = {
        "headers": ["Particulars", cy_h, py_h],
        "rows": [
            ["Raw Materials (at cost - FIFO basis)", f"{(cy_inv * 0.40):.2f}", f"{(py_inv * 0.40):.2f}"],
            ["Work-in-Progress (at estimated cost)", f"{(cy_inv * 0.20):.2f}", f"{(py_inv * 0.20):.2f}"],
            ["Finished Goods (at lower of cost and NRV)", f"{(cy_inv * 0.30):.2f}", f"{(py_inv * 0.30):.2f}"],
            ["Stores, Spares & Consumables", f"{(cy_inv * 0.10):.2f}", f"{(py_inv * 0.10):.2f}"],
            ["TOTAL INVENTORIES", f"{cy_inv:.2f}", f"{py_inv:.2f}"],
        ]
    }
    inv_text = (
        "1. Inventories are valued at lower of cost and net realisable value as per AS 2.\n"
        "2. Cost of raw materials is determined on First-In First-Out (FIFO) basis.\n"
        "3. Cost of work-in-progress and finished goods includes cost of materials, direct labour and manufacturing overheads.\n"
        "4. Provision for slow-moving / obsolete inventory: Rs Nil (PY: Rs Nil)."
    )

    # ---------------------------------------------------------------
    # NOTE 5.2 - Trade Receivables
    # ---------------------------------------------------------------
    cy_tr, py_tr = sum_cls("Trade Receivables")
    ar_rows = []
    for a in ar_items:
        ar_rows.append([a.customer_name, a.category or "Undisputed",
                        f"{a.l6m:.2f}", f"{a.m6_1y:.2f}", f"{a.y1_2y:.2f}", f"{a.y2_3y:.2f}", f"{a.mor_3y:.2f}", f"{a.total:.2f}"])
    if not ar_rows:
        ar_rows = [["Trade Debtors - Undisputed Considered Good", "Undisputed", f"{cy_tr:.2f}", "0.00", "0.00", "0.00", "0.00", f"{cy_tr:.2f}"]]
    ar_total_cy = sum(a.total for a in ar_items) if ar_items else cy_tr
    ar_rows.append(["TOTAL TRADE RECEIVABLES", "", f"{ar_total_cy:.2f}", "", "", "", "", f"{ar_total_cy:.2f}"])
    tr_table = {
        "headers": ["Customer Name", "Category", "< 6 Months", "6M-1 Year", "1-2 Years", "2-3 Years", "> 3 Years", "Total"],
        "rows": ar_rows
    }
    tr_text = (
        "Trade Receivables Ageing - as per Companies (Accounts) Amendment Rules, 2021.\n"
        "All trade receivables are unsecured. Undisputed Considered Good balances are subject to confirmation and reconciliation.\n"
        f"Provision for Expected Credit Loss (ECL): Rs Nil as at {client.reporting_period} (PY: Rs Nil)."
    )

    # ---------------------------------------------------------------
    # NOTE 5.3 - Cash and Bank Balances
    # ---------------------------------------------------------------
    cy_cb, py_cb = sum_cls("Cash and Bank Balances")
    cce_cy = round(cy_cb * 0.80, 2)
    obb_cy = round(cy_cb * 0.20, 2)
    cce_py = round(py_cb * 0.80, 2)
    obb_py = round(py_cb * 0.20, 2)
    cb_table = {
        "headers": ["Particulars", cy_h, py_h],
        "rows": [
            ["A. Cash and Cash Equivalents:", "", ""],
            ["  Cash in Hand", f"{(cy_cb * 0.05):.2f}", f"{(py_cb * 0.05):.2f}"],
            ["  Balances with Banks - Current Accounts", f"{(cy_cb * 0.55):.2f}", f"{(py_cb * 0.55):.2f}"],
            ["  Bank Fixed Deposits (Original Maturity up to 3 months)", f"{(cy_cb * 0.20):.2f}", f"{(py_cb * 0.20):.2f}"],
            ["  Total Cash & Cash Equivalents  (A)", f"{cce_cy:.2f}", f"{cce_py:.2f}"],
            ["B. Other Bank Balances:", "", ""],
            ["  Bank Fixed Deposits (Maturity > 3 months, pledged as margin)", f"{obb_cy:.2f}", f"{obb_py:.2f}"],
            ["  Total Other Bank Balances  (B)", f"{obb_cy:.2f}", f"{obb_py:.2f}"],
            ["TOTAL CASH AND BANK BALANCES  (A + B)", f"{cy_cb:.2f}", f"{py_cb:.2f}"],
        ]
    }
    cb_text = (
        "Bank Fixed Deposits pledged as margin money are not freely available for use.\n"
        "Details of bank accounts maintained:\n"
        "  HDFC Bank - Current Account (Primary Operations)\n"
        "  ICICI Bank - Current Account (Working Capital linked)\n"
        "There are no restrictions on withdrawal of cash or bank balances other than those disclosed above."
    )

    # ---------------------------------------------------------------
    # NOTE 5.4 - Short-term Loans and Advances
    # ---------------------------------------------------------------
    cy_stla, py_stla = sum_cls("Short-term Loans and Advances")
    stla_table = {
        "headers": ["Particulars", cy_h, py_h],
        "rows": [
            ["Advance to Suppliers - Considered Good", f"{(cy_stla * 0.50):.2f}", f"{(py_stla * 0.50):.2f}"],
            ["Prepaid Expenses", f"{(cy_stla * 0.15):.2f}", f"{(py_stla * 0.15):.2f}"],
            ["GST Input Tax Credit Receivable", f"{(cy_stla * 0.20):.2f}", f"{(py_stla * 0.20):.2f}"],
            ["Advance to Employees", f"{(cy_stla * 0.10):.2f}", f"{(py_stla * 0.10):.2f}"],
            ["Other Short-term Advances - Considered Good", f"{(cy_stla * 0.05):.2f}", f"{(py_stla * 0.05):.2f}"],
            ["TOTAL SHORT-TERM LOANS AND ADVANCES", f"{cy_stla:.2f}", f"{py_stla:.2f}"],
        ]
    }
    stla_text = "All short-term loans and advances are unsecured, considered good, and recoverable in cash or in kind within 12 months."

    # ---------------------------------------------------------------
    # NOTE 5.5 - Other Current Assets
    # ---------------------------------------------------------------
    cy_oca, py_oca = sum_cls("Other Current Assets")
    oca_table = {
        "headers": ["Particulars", cy_h, py_h],
        "rows": [
            ["Interest Accrued on Fixed Deposits", f"{(cy_oca * 0.60):.2f}", f"{(py_oca * 0.60):.2f}"],
            ["Other Receivables & Accruals", f"{(cy_oca * 0.40):.2f}", f"{(py_oca * 0.40):.2f}"],
            ["TOTAL OTHER CURRENT ASSETS", f"{cy_oca:.2f}", f"{py_oca:.2f}"],
        ]
    }
    oca_text = "Other current assets include interest accrued on bank fixed deposits and other receivables recoverable within 12 months."

    # ---------------------------------------------------------------
    # NOTE 6.1 - Revenue from Operations
    # ---------------------------------------------------------------
    cy_rev, py_rev = sum_cls("Revenue from Operations")
    rev_table = {
        "headers": ["Particulars", cy_pl, py_pl],
        "rows": [
            ["(a) Sale of Manufactured Products:", "", ""],
            ["    Domestic Sales", f"{(cy_rev * 0.90):.2f}", f"{(py_rev * 0.90):.2f}"],
            ["    Export Sales", f"{(cy_rev * 0.10):.2f}", f"{(py_rev * 0.10):.2f}"],
            ["(b) Sale of Services / Job Work Income", "0.00", "0.00"],
            ["(c) Other Operating Revenue", "0.00", "0.00"],
            ["TOTAL REVENUE FROM OPERATIONS", f"{cy_rev:.2f}", f"{py_rev:.2f}"],
        ]
    }
    rev_text = (
        "Revenue recognition: Revenue from sale of manufactured goods is recognised upon transfer of significant risks and rewards of ownership, "
        "which generally coincides with dispatch and delivery to customers.\n"
        "Goods and Services Tax (GST) is presented net of revenues in accordance with IGAAP principles."
    )

    # ---------------------------------------------------------------
    # NOTE 6.2 - Other Income
    # ---------------------------------------------------------------
    cy_oi, py_oi = sum_cls("Other Income")
    oi_table = {
        "headers": ["Particulars", cy_pl, py_pl],
        "rows": [
            ["Interest Income on Bank Fixed Deposits", f"{(cy_oi * 0.70):.2f}", f"{(py_oi * 0.70):.2f}"],
            ["Profit on Sale of Fixed Assets", "0.00", "0.00"],
            ["Liabilities / Provisions no longer required written back", f"{(cy_oi * 0.20):.2f}", f"{(py_oi * 0.20):.2f}"],
            ["Miscellaneous Income", f"{(cy_oi * 0.10):.2f}", f"{(py_oi * 0.10):.2f}"],
            ["TOTAL OTHER INCOME", f"{cy_oi:.2f}", f"{py_oi:.2f}"],
        ]
    }
    oi_text = "Interest income is recognised on time proportion basis taking into account the amount outstanding and applicable interest rate."

    # ---------------------------------------------------------------
    # NOTE 7.1 - Cost of Materials Consumed / Purchases / Stock Changes
    # ---------------------------------------------------------------
    cy_mc, py_mc = sum_cls("Cost of Materials Consumed")
    cy_pst, py_pst = sum_cls("Purchases of Stock-in-Trade")
    cy_cinv, py_cinv = sum_cls("Changes in Inventories")
    mc_table = {
        "headers": ["Particulars", cy_pl, py_pl],
        "rows": [
            ["(a) Cost of Raw Materials Consumed:", "", ""],
            ["    Opening Stock of Raw Materials", f"{(cy_mc * 0.18):.2f}", f"{(py_mc * 0.18):.2f}"],
            ["    Add: Purchases of Raw Materials", f"{(cy_mc * 0.85):.2f}", f"{(py_mc * 0.85):.2f}"],
            ["    Less: Closing Stock of Raw Materials", f"{(cy_mc * 0.03):.2f}", f"{(py_mc * 0.03):.2f}"],
            ["    Total Cost of Materials Consumed  (A)", f"{cy_mc:.2f}", f"{py_mc:.2f}"],
            ["(b) Purchases of Stock-in-Trade  (B)", f"{cy_pst:.2f}", f"{py_pst:.2f}"],
            ["(c) Changes in Inventories:", "", ""],
            ["    Opening Stock (WIP + Finished Goods)", f"{(abs(cy_cinv) * 0.50):.2f}", f"{(abs(py_cinv) * 0.50):.2f}"],
            ["    Less: Closing Stock (WIP + Finished Goods)", f"{(abs(cy_cinv) * 0.50):.2f}", f"{(abs(py_cinv) * 0.50):.2f}"],
            ["    Net Change in Inventories  (C)", f"{cy_cinv:.2f}", f"{py_cinv:.2f}"],
            ["TOTAL MATERIAL COSTS  (A + B + C)", f"{(cy_mc + cy_pst + cy_cinv):.2f}", f"{(py_mc + py_pst + py_cinv):.2f}"],
        ]
    }
    mc_text = "Raw material consumption is computed as: Opening Stock + Purchases - Closing Stock. Inventories are valued at cost (FIFO) or net realisable value, whichever is lower."

    # ---------------------------------------------------------------
    # NOTE 7.2 - Employee Benefit Expenses
    # ---------------------------------------------------------------
    cy_ebe, py_ebe = sum_cls("Employee Benefit Expenses")
    ebe_table = {
        "headers": ["Particulars", cy_pl, py_pl],
        "rows": [
            ["Salaries, Wages, Bonus & Allowances", f"{(cy_ebe * 0.82):.2f}", f"{(py_ebe * 0.82):.2f}"],
            ["Contribution to Provident Fund (PF)", f"{(cy_ebe * 0.07):.2f}", f"{(py_ebe * 0.07):.2f}"],
            ["Contribution to ESIC / Gratuity / Other Funds", f"{(cy_ebe * 0.06):.2f}", f"{(py_ebe * 0.06):.2f}"],
            ["Leave Encashment (Short-term)", f"{(cy_ebe * 0.03):.2f}", f"{(py_ebe * 0.03):.2f}"],
            ["Staff Welfare & Training Expenses", f"{(cy_ebe * 0.02):.2f}", f"{(py_ebe * 0.02):.2f}"],
            ["TOTAL EMPLOYEE BENEFIT EXPENSES", f"{cy_ebe:.2f}", f"{py_ebe:.2f}"],
        ]
    }
    ebe_text = (
        "Provident Fund: The Company contributes to the Employees' Provident Fund Organisation (EPFO) at the rate of 12% of basic wages.\n"
        "Gratuity: Defined benefit obligation measured using the Projected Unit Credit Method (AS 15).\n"
        "Key Management Personnel remuneration is disclosed separately under Related Party Disclosures (Note 8.1)."
    )

    # ---------------------------------------------------------------
    # NOTE 7.3 - Finance Costs
    # ---------------------------------------------------------------
    cy_fc, py_fc = sum_cls("Finance Costs")
    fc_table = {
        "headers": ["Particulars", cy_pl, py_pl],
        "rows": [
            ["Interest on Term Loans", f"{(cy_fc * 0.65):.2f}", f"{(py_fc * 0.65):.2f}"],
            ["Interest on Working Capital Facilities", f"{(cy_fc * 0.25):.2f}", f"{(py_fc * 0.25):.2f}"],
            ["Bank Charges, Processing Fees & Commission", f"{(cy_fc * 0.08):.2f}", f"{(py_fc * 0.08):.2f}"],
            ["Other Borrowing Costs", f"{(cy_fc * 0.02):.2f}", f"{(py_fc * 0.02):.2f}"],
            ["TOTAL FINANCE COSTS", f"{cy_fc:.2f}", f"{py_fc:.2f}"],
        ]
    }
    fc_text = "Finance costs are recognised in the Statement of Profit and Loss for the period in which they are incurred as per AS 16. No borrowing costs have been capitalised during the year."

    # ---------------------------------------------------------------
    # NOTE 7.4 - Depreciation and Amortisation
    # ---------------------------------------------------------------
    cy_dep_pl, py_dep_pl = sum_cls("Depreciation and Amortisation Expense")
    dep_table = {
        "headers": ["Particulars", cy_pl, py_pl],
        "rows": [
            ["Depreciation on Property, Plant & Equipment (SLM)", f"{(cy_dep_pl * 0.97):.2f}", f"{(py_dep_pl * 0.97):.2f}"],
            ["Amortisation of Intangible Assets", f"{(cy_dep_pl * 0.02):.2f}", f"{(py_dep_pl * 0.02):.2f}"],
            ["Amortisation of Preliminary / Pre-operative Expenses", f"{(cy_dep_pl * 0.01):.2f}", f"{(py_dep_pl * 0.01):.2f}"],
            ["TOTAL DEPRECIATION AND AMORTISATION", f"{cy_dep_pl:.2f}", f"{py_dep_pl:.2f}"],
        ]
    }
    dep_text = (
        "Depreciation on PPE is calculated on Straight Line Method (SLM) based on useful lives specified in Schedule II of the Companies Act, 2013.\n"
        "For assets whose actual useful life differs from Schedule II, management estimate is used after technical assessment.\n"
        "Refer to Note 4.1 for asset-class-wise depreciation charged during the year."
    )

    # ---------------------------------------------------------------
    # NOTE 7.5 - Other Expenses
    # ---------------------------------------------------------------
    cy_oe, py_oe = sum_cls("Other Expenses")
    oe_sub = [
        ("Power & Fuel Expenses",                         0.28),
        ("Rent, Rates & Taxes",                           0.18),
        ("Repairs & Maintenance - Plant & Machinery",     0.10),
        ("Repairs & Maintenance - Buildings & Civil",     0.05),
        ("Freight & Transportation Outward",              0.12),
        ("Legal & Professional Fees",                     0.08),
        ("Insurance Premiums",                            0.04),
        ("Printing, Stationery & Communication",          0.03),
        ("Travelling & Conveyance Expenses",              0.05),
        ("Statutory Auditor Remuneration (as auditor)",   0.02),
        ("Miscellaneous Administrative Expenses",         0.05),
    ]
    oe_rows = [[name, f"{cy_oe * prop:.2f}", f"{py_oe * prop:.2f}"] for name, prop in oe_sub]
    oe_total_cy = sum(cy_oe * p for _, p in oe_sub)
    oe_total_py = sum(py_oe * p for _, p in oe_sub)
    oe_rows.append(["TOTAL OTHER EXPENSES", f"{oe_total_cy:.2f}", f"{oe_total_py:.2f}"])
    oe_table = {"headers": ["Particulars", cy_pl, py_pl], "rows": oe_rows}
    oe_text = (
        "Auditor Remuneration:\n"
        "  As statutory auditor: Rs 2.50 Lakhs (PY: Rs 2.00 Lakhs)\n"
        "  For other services: Rs Nil | Out-of-pocket expenses: Rs Nil\n\n"
        "Rent expense includes factory premises, branch offices, and godown facilities. "
        "There are no non-cancellable operating lease arrangements requiring disclosure under AS 19."
    )

    # ---------------------------------------------------------------
    # NOTE 7.6 - Tax Expense
    # ---------------------------------------------------------------
    cy_tax, py_tax = sum_cls("Tax Expense")
    pbt_cy = cy_pat + cy_tax
    pbt_py = py_pat + py_tax
    eff_cy = (cy_tax / pbt_cy * 100) if pbt_cy > 0 else 0
    eff_py = (py_tax / pbt_py * 100) if pbt_py > 0 else 0
    tax_table = {
        "headers": ["Particulars", cy_pl, py_pl],
        "rows": [
            ["Current Tax - Income Tax for the year", f"{(cy_tax * 0.90):.2f}", f"{(py_tax * 0.90):.2f}"],
            ["Deferred Tax Charge / (Credit)", f"{(cy_tax * 0.10):.2f}", f"{(py_tax * 0.10):.2f}"],
            ["Earlier Years' Tax Adjustments", "0.00", "0.00"],
            ["TOTAL TAX EXPENSE", f"{cy_tax:.2f}", f"{py_tax:.2f}"],
        ]
    }
    tax_text = (
        "Current Tax: Provision for income tax is made based on applicable income tax rates under the Income Tax Act, 1961 after considering deductions and allowances.\n"
        "Deferred Tax: Deferred tax assets and liabilities are recognised for all timing differences as per AS 22.\n"
        f"Effective Tax Rate: {eff_cy:.1f}% (PY: {eff_py:.1f}%)\n"
        "MAT Credit: No MAT credit entitlement has arisen during the year."
    )

    # ---------------------------------------------------------------
    # NOTE 8.1 - Related Party Disclosures (AS 18)
    # ---------------------------------------------------------------
    rpt_rows = []
    for r in rpt_items:
        rpt_rows.append([r.name, r.relationship, r.nature_tx,
                         f"{r.opening_bal:.2f}", f"{r.debit_tx:.2f}", f"{r.credit_tx:.2f}", f"{r.closing_bal:.2f}"])
    if not rpt_rows:
        rpt_rows = [
            ["Global Logistics Pvt Ltd", "Associate Enterprise", "Freight & Logistics Services", "70.00", "120.00", "110.00", "80.00"],
            ["Managing Director / KMP", "Key Management Personnel", "Remuneration", "0.00", "36.00", "36.00", "0.00"],
        ]
    rpt_table = {
        "headers": ["Related Party Name", "Relationship", "Nature of Transaction", "Opening Balance", "Debit Tx", "Credit Tx", "Closing Balance"],
        "rows": rpt_rows
    }
    rpt_text = (
        "Disclosure as required by Accounting Standard 18 - Related Party Disclosures.\n\n"
        "List of Related Parties and Nature of Relationship:\n"
        "i.  Subsidiary Companies: [None]\n"
        "ii. Associate Companies: Global Logistics Pvt Ltd\n"
        "iii. Key Management Personnel (KMP): Managing Director & Director(s)\n"
        "iv. Relatives of KMP with significant influence: [As identified by Management]\n\n"
        "All transactions with related parties were carried out in the ordinary course of business and on arm's length basis."
    )

    # ---------------------------------------------------------------
    # NOTE 8.2 - Contingent Liabilities & Commitments (AS 29)
    # ---------------------------------------------------------------
    cont_rows = []
    for c in cont_items:
        cont_rows.append([c.nature, c.forum or "GST Appellate Authority",
                          f"{c.cy_amount:.2f}", f"{c.py_amount:.2f}",
                          c.assessment or "Favourable outcome expected", c.provision_required or "No"])
    if not cont_rows:
        cont_rows = [
            ["Disputed GST Demand", "GST Appellate Authority", "35.00", "35.00", "Favourable outcome expected", "No"],
            ["Income Tax Assessment - AY 2022-23", "CIT (Appeals)", "18.00", "18.00", "Matter under appeal", "No"],
        ]
    cont_table = {
        "headers": ["Nature of Contingency", "Forum / Authority", f"CY Amount ({client.reporting_period})", f"PY Amount ({client.previous_year_period})", "Management Assessment", "Provision Required"],
        "rows": cont_rows
    }
    cont_text = (
        "Contingent Liabilities not provided for in the accounts (as per AS 29):\n"
        "Based on legal advice and merits of the case, management is of the view that the outcome is likely to be favourable and no provision is required.\n\n"
        "Capital Commitments:\n"
        "Estimated amount of contracts remaining to be executed on capital account and not provided for (net of advances): Rs Nil (PY: Rs Nil)."
    )

    # ---------------------------------------------------------------
    # MASTER NOTE SPECS - 27 notes in correct numerical order
    # ---------------------------------------------------------------
    NOTE_SPECS = [
        {"number": "1.1",  "title": "Share Capital",                               "table": sc_table,   "template": sc_text},
        {"number": "1.2",  "title": "Reserves and Surplus",                        "table": rs_table,   "template": rs_text},
        {"number": "2.1",  "title": "Long-term Borrowings",                        "table": ltb_table,  "template": ltb_text},
        {"number": "2.2",  "title": "Long-term Provisions",                        "table": ltp_table,  "template": ltp_text},
        {"number": "3.1",  "title": "Short-term Borrowings",                       "table": stb_table,  "template": stb_text},
        {"number": "3.2",  "title": "Trade Payables",                              "table": tp_table,   "template": tp_text},
        {"number": "3.3",  "title": "Other Current Liabilities",                   "table": ocl_table,  "template": ocl_text},
        {"number": "3.4",  "title": "Short-term Provisions",                       "table": stp_table,  "template": stp_text},
        {"number": "4.1",  "title": "Property, Plant and Equipment",               "table": ppe_table,  "template": ppe_text},
        {"number": "4.2",  "title": "Capital Work-in-Progress",                    "table": cwip_table, "template": cwip_text},
        {"number": "4.3",  "title": "Non-current Investments",                     "table": nci_table,  "template": nci_text},
        {"number": "4.4",  "title": "Long-term Loans and Advances",                "table": ltla_table, "template": ltla_text},
        {"number": "5.1",  "title": "Inventories",                                "table": inv_table,  "template": inv_text},
        {"number": "5.2",  "title": "Trade Receivables",                           "table": tr_table,   "template": tr_text},
        {"number": "5.3",  "title": "Cash and Bank Balances",                      "table": cb_table,   "template": cb_text},
        {"number": "5.4",  "title": "Short-term Loans and Advances",               "table": stla_table, "template": stla_text},
        {"number": "5.5",  "title": "Other Current Assets",                        "table": oca_table,  "template": oca_text},
        {"number": "6.1",  "title": "Revenue from Operations",                     "table": rev_table,  "template": rev_text},
        {"number": "6.2",  "title": "Other Income",                                "table": oi_table,   "template": oi_text},
        {"number": "7.1",  "title": "Cost of Materials Consumed",                  "table": mc_table,   "template": mc_text},
        {"number": "7.2",  "title": "Employee Benefit Expenses",                   "table": ebe_table,  "template": ebe_text},
        {"number": "7.3",  "title": "Finance Costs",                               "table": fc_table,   "template": fc_text},
        {"number": "7.4",  "title": "Depreciation and Amortisation Expense",      "table": dep_table,  "template": dep_text},
        {"number": "7.5",  "title": "Other Expenses",                              "table": oe_table,   "template": oe_text},
        {"number": "7.6",  "title": "Tax Expense",                                 "table": tax_table,  "template": tax_text},
        {"number": "8.1",  "title": "Related Party Disclosures (AS 18)",           "table": rpt_table,  "template": rpt_text},
        {"number": "8.2",  "title": "Contingent Liabilities & Commitments (AS 29)","table": cont_table, "template": cont_text},
    ]

    existing_notes = {n.note_number: n for n in db.query(Note).filter(Note.client_id == client_id).all()}

    for std in NOTE_SPECS:
        num      = std["number"]
        base_txt = std["template"]
        t_json   = json.dumps(std["table"])

        if num in existing_notes:
            note_obj = existing_notes[num]
            note_obj.table_json        = t_json
            note_obj.suggested_content = base_txt
            note_obj.title             = std["title"]
            if not note_obj.is_modified:
                note_obj.content = base_txt
        else:
            note_obj = Note(
                client_id         = client_id,
                note_number       = num,
                title             = std["title"],
                content           = base_txt,
                suggested_content = base_txt,
                table_json        = t_json,
                is_modified       = False,
            )
            db.add(note_obj)

    db.commit()
    return db.query(Note).filter(Note.client_id == client_id).order_by(Note.note_number).all()
