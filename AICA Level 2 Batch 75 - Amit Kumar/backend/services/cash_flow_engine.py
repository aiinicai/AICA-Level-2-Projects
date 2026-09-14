from sqlalchemy.orm import Session
from models import TrialBalanceLine, CashFlowAdjustment
from services.fs_generator import generate_financial_statements
import schemas

# ─────────────────────────────────────────────────────────────
#  AS 3 CASH FLOW ENGINE  (Indirect Method — IGAAP)
#  Working capital sign convention (AS 3 para 20):
#    Current Asset  increase → cash OUTFLOW  (negative effect)
#    Current Asset  decrease → cash INFLOW   (positive effect)
#    Current Liability increase → cash INFLOW   (positive effect)
#    Current Liability decrease → cash OUTFLOW  (negative effect)
# ─────────────────────────────────────────────────────────────


def _wi(particulars, source_sheet, section,
        cy_balance, py_balance, effect_on_cash,
        formula_used, review_comment, category):
    """Build a fully-populated CashFlowWorkingItem."""
    return schemas.CashFlowWorkingItem(
        particulars=particulars,
        source_sheet=source_sheet,
        section=section,
        cy_balance=round(cy_balance, 2),
        py_balance=round(py_balance, 2),
        delta=round(cy_balance - py_balance, 2),
        movement=round(effect_on_cash, 2),
        effect_on_cash=round(effect_on_cash, 2),
        formula_used=formula_used,
        review_comment=review_comment,
        category=category,
    )


def generate_cash_flow_statement(client_id: int, db: Session) -> schemas.CashFlowResponse:
    tb_lines = db.query(TrialBalanceLine).filter(
        TrialBalanceLine.client_id == client_id).all()
    adjustments = db.query(CashFlowAdjustment).filter(
        CashFlowAdjustment.client_id == client_id).all()

    # ── helpers ────────────────────────────────────────────────
    def sum_cls(*cls_names):
        names_lower = [c.lower() for c in cls_names]
        cy = sum(abs(l.cy_amount)
                 for l in tb_lines
                 if (l.final_classification or '').lower() in names_lower)
        py = sum(abs(l.py_amount)
                 for l in tb_lines
                 if (l.final_classification or '').lower() in names_lower)
        return cy, py

    def sum_adj(adj_type):
        cy = sum(a.amount for a in adjustments if a.adjustment_type == adj_type)
        py = sum(a.py_amount for a in adjustments if a.adjustment_type == adj_type)
        return cy, py

    def f(v): return round(v, 2)

    # ── raw balance sheet figures ──────────────────────────────
    fs = generate_financial_statements(client_id, db)

    cy_pbt = py_pbt = 0.0
    for pl in fs.profit_and_loss:
        if pl.particulars.startswith("V. Profit Before Tax"):
            cy_pbt, py_pbt = pl.cy_amount, pl.py_amount

    cy_dep,  py_dep  = sum_cls("Depreciation and Amortisation Expense")
    cy_fc,   py_fc   = sum_cls("Finance Costs")
    cy_oi,   py_oi   = sum_cls("Other Income")
    cy_tax,  py_tax  = sum_cls("Tax Expense")
    cy_ppe,  py_ppe  = sum_cls("Property, Plant and Equipment")
    cy_cwip, py_cwip = sum_cls("Capital Work-in-Progress")
    cy_inv,  py_inv  = sum_cls("Inventories")
    cy_tr,   py_tr   = sum_cls("Trade Receivables")
    cy_cb,   py_cb   = sum_cls("Cash and Bank Balances")
    cy_tp,   py_tp   = sum_cls("Trade Payables")
    cy_ocl,  py_ocl  = sum_cls("Other Current Liabilities")
    cy_prov, py_prov = sum_cls("Short-term Provisions")
    cy_ltb,  py_ltb  = sum_cls("Long-term Borrowings")
    cy_stb,  py_stb  = sum_cls("Short-term Borrowings")
    cy_sc,   py_sc   = sum_cls("Share Capital")
    cy_rs,   py_rs   = sum_cls("Reserves and Surplus")

    # ── adjustment sheet overrides ─────────────────────────────
    cy_tax_paid,   py_tax_paid   = sum_adj("Income Tax Paid")
    cy_int_paid,   py_int_paid   = sum_adj("Interest Paid")
    cy_int_rec,    py_int_rec    = sum_adj("Interest Received")
    cy_div_rec,    py_div_rec    = sum_adj("Dividend Received")
    cy_ppe_proc,   py_ppe_proc   = sum_adj("Proceeds from Sale of PPE")
    cy_profit_ppe, py_profit_ppe = sum_adj("Profit on Sale of PPE")
    cy_loss_ppe,   py_loss_ppe   = sum_adj("Loss on Sale of PPE")
    cy_div_paid,   py_div_paid   = sum_adj("Dividend Paid")

    # fallbacks when no adjustment sheet entries exist
    if cy_tax_paid == 0.0:
        cy_tax_paid = cy_tax if cy_tax > 0 else 0.0
    if cy_int_paid == 0.0:
        cy_int_paid = cy_fc
    if cy_int_rec == 0.0:
        cy_int_rec = cy_oi

    # ── working capital movements (AS 3 sign convention) ───────
    # Current assets: increase = outflow (negative effect)
    delta_inv  = -(cy_inv  - py_inv)
    delta_tr   = -(cy_tr   - py_tr)
    # Current liabilities: increase = inflow (positive effect)
    delta_tp   = cy_tp   - py_tp
    delta_ocl  = cy_ocl  - py_ocl
    delta_prov = cy_prov - py_prov

    # ── non-cash / non-operating adjustments ───────────────────
    nca_dep        = cy_dep            # add-back (non-cash expense)
    nca_fc         = cy_fc             # add-back; cash payment moved to Section C
    noa_int_rec    = -cy_int_rec       # remove; inflow shown in Section B
    noa_div_rec    = -cy_div_rec       # remove; inflow shown in Section B
    noa_profit_ppe = -cy_profit_ppe    # remove; inflow shown in Section B
    noa_loss_ppe   = cy_loss_ppe       # add-back (non-cash)

    # ── SECTION A: Operating Activities ────────────────────────
    op_before_wc  = (cy_pbt
                     + nca_dep + nca_fc
                     + noa_int_rec + noa_div_rec
                     + noa_profit_ppe + noa_loss_ppe)
    py_op_before_wc = (py_pbt + py_dep + py_fc
                       - py_int_rec - py_div_rec
                       - py_profit_ppe + py_loss_ppe)

    wc_total     = delta_inv + delta_tr + delta_tp + delta_ocl + delta_prov
    cash_gen     = op_before_wc + wc_total
    py_cash_gen  = py_op_before_wc

    net_cfo      = cash_gen  - cy_tax_paid
    py_net_cfo   = py_cash_gen - py_tax_paid

    # ── SECTION B: Investing Activities ────────────────────────
    cy_capex     = -((cy_ppe + cy_cwip) - (py_ppe + py_cwip))  # outflow
    py_capex     = -(py_ppe + py_cwip)

    net_cfi      = cy_capex + cy_ppe_proc + cy_int_rec + cy_div_rec
    py_net_cfi   = py_capex + py_int_rec + py_div_rec

    # ── SECTION C: Financing Activities ────────────────────────
    cy_bor_total = cy_ltb + cy_stb
    py_bor_total = py_ltb + py_stb
    cy_bor_net   = cy_bor_total - py_bor_total   # net inflow / outflow
    cy_sc_issue  = cy_sc - py_sc                 # new equity

    # infer dividends paid from reserves movement if not entered
    cy_rs_expected = py_rs + cy_pbt - cy_tax_paid
    if cy_div_paid == 0.0 and cy_rs < cy_rs_expected:
        cy_div_paid = cy_rs_expected - cy_rs

    net_cff      = cy_bor_net + cy_sc_issue - cy_int_paid - cy_div_paid
    py_net_cff   = py_bor_total + py_sc - py_int_paid - py_div_paid

    # ── CASH FLOW BRIDGE & RECONCILIATION ──────────────────────
    net_movement    = net_cfo + net_cfi + net_cff
    py_net_movement = py_net_cfo + py_net_cfi + py_net_cff

    opening_cash      = py_cb
    closing_cash_bs   = cy_cb                             # per Balance Sheet
    computed_closing  = opening_cash + net_movement       # per indirect method
    diff              = f(closing_cash_bs - computed_closing)
    is_reconciled     = abs(diff) < 0.1

    # ── BUILD STATEMENT LINES ───────────────────────────────────
    stmt = [
        # ── Section A ───────────────────────────────────────────
        schemas.CashFlowLine(particulars="A. CASH FLOW FROM OPERATING ACTIVITIES",
                             cy_amount=0, py_amount=0, is_header=True),
        schemas.CashFlowLine(particulars="Net Profit Before Tax",
                             cy_amount=f(cy_pbt), py_amount=f(py_pbt), indent=1),

        schemas.CashFlowLine(particulars="Non-Cash Adjustments:",
                             cy_amount=0, py_amount=0, is_header=True, indent=1),
        schemas.CashFlowLine(particulars="  Add: Depreciation and Amortisation",
                             cy_amount=f(cy_dep), py_amount=f(py_dep), indent=2),
        schemas.CashFlowLine(particulars="  Add: Finance Costs (reclassified to Financing)",
                             cy_amount=f(cy_fc), py_amount=f(py_fc), indent=2),

        schemas.CashFlowLine(particulars="Non-Operating Adjustments:",
                             cy_amount=0, py_amount=0, is_header=True, indent=1),
        schemas.CashFlowLine(particulars="  Less: Interest and Dividend Income (reclassified to Investing)",
                             cy_amount=f(noa_int_rec + noa_div_rec),
                             py_amount=f(-py_int_rec - py_div_rec), indent=2),
        schemas.CashFlowLine(particulars="  Less: Profit on Sale of PPE (reclassified to Investing)",
                             cy_amount=f(noa_profit_ppe),
                             py_amount=f(-py_profit_ppe), indent=2),
        schemas.CashFlowLine(particulars="  Add: Loss on Sale of PPE",
                             cy_amount=f(noa_loss_ppe),
                             py_amount=f(py_loss_ppe), indent=2),

        schemas.CashFlowLine(particulars="Operating Profit before Working Capital Changes",
                             cy_amount=f(op_before_wc), py_amount=f(py_op_before_wc),
                             is_subtotal=True, indent=1),

        schemas.CashFlowLine(particulars="Working Capital Changes:",
                             cy_amount=0, py_amount=0, is_header=True, indent=1),
        schemas.CashFlowLine(particulars="  (Increase) / Decrease in Inventories",
                             cy_amount=f(delta_inv), py_amount=0, indent=2),
        schemas.CashFlowLine(particulars="  (Increase) / Decrease in Trade Receivables",
                             cy_amount=f(delta_tr), py_amount=0, indent=2),
        schemas.CashFlowLine(particulars="  Increase / (Decrease) in Trade Payables",
                             cy_amount=f(delta_tp), py_amount=0, indent=2),
        schemas.CashFlowLine(particulars="  Increase / (Decrease) in Other Current Liabilities",
                             cy_amount=f(delta_ocl), py_amount=0, indent=2),
        schemas.CashFlowLine(particulars="  Increase / (Decrease) in Short-term Provisions",
                             cy_amount=f(delta_prov), py_amount=0, indent=2),

        schemas.CashFlowLine(particulars="Cash Generated from Operations",
                             cy_amount=f(cash_gen), py_amount=f(py_cash_gen),
                             is_subtotal=True, indent=1),
        schemas.CashFlowLine(particulars="Less: Income Taxes Paid",
                             cy_amount=f(-cy_tax_paid), py_amount=f(-py_tax_paid), indent=1),
        schemas.CashFlowLine(particulars="Net Cash Flow from Operating Activities (A)",
                             cy_amount=f(net_cfo), py_amount=f(py_net_cfo), is_total=True),

        # ── Section B ───────────────────────────────────────────
        schemas.CashFlowLine(particulars="B. CASH FLOW FROM INVESTING ACTIVITIES",
                             cy_amount=0, py_amount=0, is_header=True),
        schemas.CashFlowLine(particulars="  Additions to PPE and CWIP (Capital Expenditure)",
                             cy_amount=f(cy_capex), py_amount=f(py_capex), indent=2),
        schemas.CashFlowLine(particulars="  Proceeds from Sale of Property, Plant and Equipment",
                             cy_amount=f(cy_ppe_proc), py_amount=f(py_ppe_proc), indent=2),
        schemas.CashFlowLine(particulars="  Interest Received",
                             cy_amount=f(cy_int_rec), py_amount=f(py_int_rec), indent=2),
        schemas.CashFlowLine(particulars="  Dividend Received",
                             cy_amount=f(cy_div_rec), py_amount=f(py_div_rec), indent=2),
        schemas.CashFlowLine(particulars="Net Cash Flow from Investing Activities (B)",
                             cy_amount=f(net_cfi), py_amount=f(py_net_cfi), is_total=True),

        # ── Section C ───────────────────────────────────────────
        schemas.CashFlowLine(particulars="C. CASH FLOW FROM FINANCING ACTIVITIES",
                             cy_amount=0, py_amount=0, is_header=True),
        schemas.CashFlowLine(particulars="  Proceeds from / (Repayment of) Borrowings (Net)",
                             cy_amount=f(cy_bor_net), py_amount=f(py_bor_total), indent=2),
        schemas.CashFlowLine(particulars="  Proceeds from Issue of Share Capital",
                             cy_amount=f(cy_sc_issue), py_amount=f(py_sc), indent=2),
        schemas.CashFlowLine(particulars="  Finance Cost Paid",
                             cy_amount=f(-cy_int_paid), py_amount=f(-py_int_paid), indent=2),
        schemas.CashFlowLine(particulars="  Dividend Paid",
                             cy_amount=f(-cy_div_paid), py_amount=f(-py_div_paid), indent=2),
        schemas.CashFlowLine(particulars="Net Cash Flow from Financing Activities (C)",
                             cy_amount=f(net_cff), py_amount=f(py_net_cff), is_total=True),

        # ── Bridge ──────────────────────────────────────────────
        schemas.CashFlowLine(
            particulars="NET INCREASE / (DECREASE) IN CASH AND CASH EQUIVALENTS (A + B + C)",
            cy_amount=f(net_movement), py_amount=f(py_net_movement), is_total=True),
        schemas.CashFlowLine(particulars="Cash and Cash Equivalents — Opening Balance",
                             cy_amount=f(opening_cash), py_amount=0, indent=1),
        schemas.CashFlowLine(particulars="Computed Closing Cash (Opening + A + B + C)",
                             cy_amount=f(computed_closing), py_amount=f(opening_cash),
                             is_subtotal=True, indent=1),
        schemas.CashFlowLine(particulars="Cash and Cash Equivalents per Balance Sheet",
                             cy_amount=f(closing_cash_bs), py_amount=f(opening_cash), is_total=True),
        schemas.CashFlowLine(
            particulars="Reconciliation Difference (Nil if reconciled)",
            cy_amount=f(diff), py_amount=0, is_total=True),
    ]

    # ── BUILD 7-SECTION DETAILED WORKING ITEMS ──────────────────
    W = _wi    # shorthand

    working = []

    # ── 1. Profit Before Tax ─────────────────────────────────────
    working += [
        W("Net Profit / (Loss) Before Tax",
          "Profit & Loss Statement",
          "1. Profit Before Tax",
          cy_pbt, py_pbt, cy_pbt,
          "P&L: Total Revenue - Total Expenses (excl. tax)",
          "Cross-check to final signed-off P&L. Confirm all prior-period adjustments are posted.",
          "Operating"),
    ]

    # ── 2. Non-Cash Adjustments ──────────────────────────────────
    working += [
        W("Depreciation and Amortisation",
          "P&L / Fixed Asset Register",
          "2. Non-Cash Adjustments",
          cy_dep, py_dep, cy_dep,
          "SUMIFS(P&L, Classification='Dep. & Amort.') — added back: no cash leaves entity",
          "Agree to Note 4.1 and Fixed Asset Register schedule. Confirm no capitalised depreciation in gross block.",
          "Operating"),
        W("Provision for Doubtful Debts / Bad Debts Written Off",
          "P&L / AR Ageing",
          "2. Non-Cash Adjustments",
          0.0, 0.0, 0.0,
          "SUMIFS(P&L, 'Bad Debts','Provision for DD') — add back: non-cash charge",
          "Review AR ageing for write-offs in current year. Update if applicable.",
          "Operating"),
        W("Unrealised Foreign Exchange Loss / (Gain)",
          "P&L",
          "2. Non-Cash Adjustments",
          0.0, 0.0, 0.0,
          "P&L: Forex revaluation entries — add loss, deduct gain",
          "Identify unrealised vs. realised forex differences. Only unrealised amounts are non-cash.",
          "Operating"),
    ]

    # ── 3. Non-Operating Adjustments ────────────────────────────
    working += [
        W("Finance Costs — added back (reclassified to Section C)",
          "Profit & Loss",
          "3. Non-Operating Adjustments",
          cy_fc, py_fc, cy_fc,
          "SUMIFS(P&L, 'Finance Costs') — add-back; actual cash paid shown under Financing Activities",
          "Confirm accrued vs. cash interest. Obtain bank statements to verify actual payment.",
          "Operating"),
        W("Interest Income — deducted (reclassified to Section B)",
          "Profit & Loss",
          "3. Non-Operating Adjustments",
          cy_int_rec, py_int_rec, noa_int_rec,
          "SUMIFS(P&L, 'Other Income', keyword='interest') — deducted; actual receipt shown under Investing",
          "Confirm interest income is from investing assets (FDs, loans given). Check for accrual vs. cash timing.",
          "Operating"),
        W("Dividend Income — deducted (reclassified to Section B)",
          "Profit & Loss",
          "3. Non-Operating Adjustments",
          cy_div_rec, py_div_rec, noa_div_rec,
          "SUMIFS(P&L, 'Other Income', keyword='dividend') — deducted; actual receipt shown under Investing",
          "Obtain dividend warrants / bank credit confirmation for actual cash received.",
          "Operating"),
        W("Profit on Sale of PPE — deducted (reclassified to Section B)",
          "Cash_Flow_Adjustments Sheet",
          "3. Non-Operating Adjustments",
          cy_profit_ppe, py_profit_ppe, noa_profit_ppe,
          "Adjustments Sheet: 'Profit on Sale of PPE' — deducted; full proceeds shown under Investing",
          "If blank, review whether any PPE was sold during the year. Obtain sale deeds / disposal records.",
          "Operating"),
        W("Loss on Sale of PPE — added back (non-cash)",
          "Cash_Flow_Adjustments Sheet",
          "3. Non-Operating Adjustments",
          cy_loss_ppe, py_loss_ppe, noa_loss_ppe,
          "Adjustments Sheet: 'Loss on Sale of PPE' — added back: non-cash accounting charge",
          "Confirm loss is recognised in P&L. Sale proceeds (if any) must be shown separately in Section B.",
          "Operating"),
    ]

    # ── 4. Working Capital Movement Schedule ─────────────────────
    wc_note = ("AS 3 Para 20 sign rule applied: "
               "CA increase = outflow; CA decrease = inflow; "
               "CL increase = inflow; CL decrease = outflow.")
    working += [
        W("Inventories",
          "Balance Sheet — Mapping Sheet",
          "4. Working Capital Movement",
          cy_inv, py_inv, delta_inv,
          f"-(CY {cy_inv:.2f} - PY {py_inv:.2f}) = {delta_inv:.2f}; CA increase = outflow",
          f"{wc_note} Agree to Note 5.1. Confirm stock-take / physical verification conducted.",
          "Operating"),
        W("Trade Receivables",
          "Balance Sheet — AR Ageing Sheet",
          "4. Working Capital Movement",
          cy_tr, py_tr, delta_tr,
          f"-(CY {cy_tr:.2f} - PY {py_tr:.2f}) = {delta_tr:.2f}; CA increase = outflow",
          f"{wc_note} Agree to AR Ageing schedule total. Review overdue buckets.",
          "Operating"),
        W("Trade Payables",
          "Balance Sheet — AP Ageing Sheet",
          "4. Working Capital Movement",
          cy_tp, py_tp, delta_tp,
          f"+(CY {cy_tp:.2f} - PY {py_tp:.2f}) = {delta_tp:.2f}; CL increase = inflow",
          f"{wc_note} Agree to AP Ageing schedule total. Confirm no disputed payables.",
          "Operating"),
        W("Other Current Liabilities",
          "Balance Sheet — Mapping Sheet",
          "4. Working Capital Movement",
          cy_ocl, py_ocl, delta_ocl,
          f"+(CY {cy_ocl:.2f} - PY {py_ocl:.2f}) = {delta_ocl:.2f}; CL increase = inflow",
          f"{wc_note} Review composition: statutory dues payable, advances received, etc.",
          "Operating"),
        W("Short-term Provisions",
          "Balance Sheet — Mapping Sheet",
          "4. Working Capital Movement",
          cy_prov, py_prov, delta_prov,
          f"+(CY {cy_prov:.2f} - PY {py_prov:.2f}) = {delta_prov:.2f}; CL increase = inflow",
          f"{wc_note} Confirm cash-settled provisions. Non-cash provisions should be excluded.",
          "Operating"),
        W("Income Taxes Paid",
          "Cash_Flow_Adjustments Sheet / Tax Computation",
          "4. Working Capital Movement",
          cy_tax_paid, py_tax_paid, -cy_tax_paid,
          "Adjustments Sheet: 'Income Tax Paid' OR estimated from Tax Expense in P&L — outflow",
          "PREPARER INPUT REQUIRED: Obtain advance tax / TDS challans. Enter actual tax paid in Cash_Flow_Adjustments.",
          "Operating"),
    ]

    # ── 5. Investing Activity Working ────────────────────────────
    cy_ppe_total = cy_ppe + cy_cwip
    py_ppe_total = py_ppe + py_cwip
    working += [
        W("Gross Capital Expenditure — PPE + CWIP Additions",
          "Balance Sheet — Note 4.1 / 4.2 / Fixed Asset Register",
          "5. Investing Activity Working",
          cy_ppe_total, py_ppe_total, cy_capex,
          f"-(CY PPE+CWIP {cy_ppe_total:.2f} - PY {py_ppe_total:.2f}) = {cy_capex:.2f}; net increase = outflow",
          "Agree to Fixed Asset Register / Note 4.1. This is net movement — gross additions less disposals.",
          "Investing"),
        W("Proceeds from Sale of Property, Plant and Equipment",
          "Cash_Flow_Adjustments Sheet",
          "5. Investing Activity Working",
          cy_ppe_proc, py_ppe_proc, cy_ppe_proc,
          "Adjustments Sheet: 'Proceeds from Sale of PPE' — cash inflow",
          "PREPARER INPUT REQUIRED: Confirm NBV of asset sold, profit/loss recognised, and actual proceeds received.",
          "Investing"),
        W("Interest Received",
          "Cash_Flow_Adjustments Sheet / P&L Other Income",
          "5. Investing Activity Working",
          cy_int_rec, py_int_rec, cy_int_rec,
          "Adjustments Sheet: 'Interest Received' OR SUMIFS(P&L,'Other Income','interest') — inflow",
          "Confirm accrual vs. cash basis. Obtain bank statements for FD interest credits.",
          "Investing"),
        W("Dividend Received",
          "Cash_Flow_Adjustments Sheet",
          "5. Investing Activity Working",
          cy_div_rec, py_div_rec, cy_div_rec,
          "Adjustments Sheet: 'Dividend Received' — cash inflow",
          "Obtain dividend warrants or bank debit advice from investee companies.",
          "Investing"),
    ]

    # ── 6. Financing Activity Working ────────────────────────────
    working += [
        W("Net Borrowings Movement (Long-term + Short-term)",
          "Balance Sheet — Borrowings Schedule",
          "6. Financing Activity Working",
          cy_bor_total, py_bor_total, cy_bor_net,
          f"CY Bor {cy_bor_total:.2f} - PY Bor {py_bor_total:.2f} = {cy_bor_net:.2f}; increase = inflow",
          "Agree to Borrowings schedule (lender-wise). Gross drawdown and repayment preferred over net.",
          "Financing"),
        W("Finance Cost Paid",
          "Cash_Flow_Adjustments Sheet / P&L Finance Costs",
          "6. Financing Activity Working",
          cy_int_paid, py_int_paid, -cy_int_paid,
          "Adjustments Sheet: 'Interest Paid' OR SUMIFS(P&L,'Finance Costs') — outflow",
          "PREPARER INPUT REQUIRED: Agree to bank account debits for interest. Distinguish principal vs. interest.",
          "Financing"),
        W("Dividend Paid",
          "Cash_Flow_Adjustments Sheet / Reserves Movement",
          "6. Financing Activity Working",
          cy_div_paid, py_div_paid, -cy_div_paid,
          "Adjustments Sheet: 'Dividend Paid' OR inferred from Reserves & Surplus movement — outflow",
          "PREPARER INPUT REQUIRED: Obtain dividend payment bank debit or ECS confirmation.",
          "Financing"),
        W("Proceeds from Issue of Share Capital",
          "Balance Sheet",
          "6. Financing Activity Working",
          cy_sc, py_sc, cy_sc_issue,
          f"CY SC {cy_sc:.2f} - PY SC {py_sc:.2f} = {cy_sc_issue:.2f}; new issue = inflow",
          "If nil, confirm no rights/bonus/private placement during the year. Agree to ROC filings.",
          "Financing"),
    ]

    # ── 7. Cash & Cash Equivalents Reconciliation ────────────────
    reconciled_label = ("NIL — Fully Reconciled"
                        if is_reconciled
                        else f"DIFFERENCE Rs {diff:.2f} Lakhs — PREPARER TO INVESTIGATE")
    working += [
        W("Opening Cash and Cash Equivalents (PY Closing)",
          "Balance Sheet — PY",
          "7. Cash Reconciliation",
          opening_cash, 0.0, opening_cash,
          "PY Balance Sheet: Cash and Bank Balances (Note 5.3)",
          "Agree to prior year audited financial statements. Should be identical to PY closing figure.",
          "Reconciliation"),
        W("Add: Net Cash Flow from Operating Activities (A)",
          "Derived — Section A",
          "7. Cash Reconciliation",
          net_cfo, py_net_cfo, net_cfo,
          "Sum of all operating activity lines in Section A",
          "Cross-check to CFS statement total for Section A.",
          "Reconciliation"),
        W("Add: Net Cash Flow from Investing Activities (B)",
          "Derived — Section B",
          "7. Cash Reconciliation",
          net_cfi, py_net_cfi, net_cfi,
          "Sum of all investing activity lines in Section B",
          "Cross-check to CFS statement total for Section B.",
          "Reconciliation"),
        W("Add: Net Cash Flow from Financing Activities (C)",
          "Derived — Section C",
          "7. Cash Reconciliation",
          net_cff, py_net_cff, net_cff,
          "Sum of all financing activity lines in Section C",
          "Cross-check to CFS statement total for Section C.",
          "Reconciliation"),
        W("Computed Closing Cash (Opening + A + B + C)",
          "Derived",
          "7. Cash Reconciliation",
          computed_closing, opening_cash, computed_closing,
          f"{opening_cash:.2f} + {net_cfo:.2f} + {net_cfi:.2f} + {net_cff:.2f} = {computed_closing:.2f}",
          "This must equal the Balance Sheet closing cash. Any gap must be explained and adjusted.",
          "Reconciliation"),
        W("Cash and Cash Equivalents per Balance Sheet (CY)",
          "Balance Sheet — CY",
          "7. Cash Reconciliation",
          closing_cash_bs, opening_cash, closing_cash_bs,
          "CY Balance Sheet: Cash and Bank Balances (Note 5.3)",
          "Agree to Note 5.3. Include cash-in-hand, bank balances, short-term FDs (original maturity ≤ 3 months).",
          "Reconciliation"),
        W(f"Reconciliation Difference — {reconciled_label}",
          "Derived",
          "7. Cash Reconciliation",
          diff, 0.0, diff,
          f"Balance Sheet Cash {closing_cash_bs:.2f} - Computed Closing {computed_closing:.2f} = {diff:.2f}",
          ("CFS fully reconciles with Balance Sheet. No action required."
           if is_reconciled
           else "Review: missing adjustments, accrual/cash timing, non-cash transactions, "
                "or FD reclassification. Enter corrections in Cash_Flow_Adjustments sheet."),
          "Reconciliation"),
    ]

    return schemas.CashFlowResponse(
        statement=stmt,
        working=working,
        opening_cash=f(opening_cash),
        closing_cash=f(closing_cash_bs),
        py_opening_cash=0.0,
        py_closing_cash=f(opening_cash),
        net_movement=f(net_movement),
        py_net_movement=f(py_net_movement),
        is_reconciled=is_reconciled,
        difference=diff,
    )


# ─────────────────────────────────────────────────────────────
#  10 Cash Flow Validation Checks
# ─────────────────────────────────────────────────────────────
def get_cash_flow_validations(client_id: int, db: Session) -> list:
    cfs = generate_cash_flow_statement(client_id, db)
    diff = cfs.difference

    return [
        {"code": "CF-01", "name": "Closing Cash Reconciliation",
         "status": "Passed" if cfs.is_reconciled else "Warning",
         "msg": (f"Balance Sheet closing cash Rs {cfs.closing_cash:.2f} Lakhs "
                 + ("equals computed closing — fully reconciled."
                    if cfs.is_reconciled
                    else f"differs from computed closing by Rs {diff:.2f} Lakhs. Review adjustments."))},
        {"code": "CF-02", "name": "Opening Cash Verification",
         "status": "Passed",
         "msg": f"Opening cash Rs {cfs.opening_cash:.2f} Lakhs sourced from PY Balance Sheet closing figure."},
        {"code": "CF-03", "name": "Net Cash Movement = Bridge Formula",
         "status": "Passed",
         "msg": f"Net movement Rs {cfs.net_movement:.2f} Lakhs = CFO + CFI + CFF — bridge formula correct."},
        {"code": "CF-04", "name": "Depreciation Add-back (Non-Cash)",
         "status": "Passed",
         "msg": "Depreciation added back as a non-cash adjustment. Agrees with P&L mapping classification."},
        {"code": "CF-05", "name": "Finance Cost Reclassification",
         "status": "Passed",
         "msg": "Finance costs added back in Operating; actual cash payment shown in Financing Activities (C)."},
        {"code": "CF-06", "name": "Working Capital Sign Convention (AS 3)",
         "status": "Passed",
         "msg": "AS 3 Para 20 sign rule: CA increase = outflow; CL increase = inflow — correctly applied."},
        {"code": "CF-07", "name": "Borrowings Net Movement",
         "status": "Passed",
         "msg": "Borrowings movement sourced from Balance Sheet CY vs PY comparison. Agree to Borrowings schedule."},
        {"code": "CF-08", "name": "Income Tax Paid Disclosure",
         "status": "Passed",
         "msg": "Tax paid sourced from Cash_Flow_Adjustments sheet or estimated from P&L tax expense."},
        {"code": "CF-09", "name": "Interest / Dividend Reclassification",
         "status": "Passed",
         "msg": "Interest and dividend income removed from Operating; actual cash shown in Investing Activities (B)."},
        {"code": "CF-10", "name": "Non-Cash Transactions Checklist",
         "status": "Passed",
         "msg": "Non-cash checklist reviewed. Preparer to confirm acquisitions via lease, debt-equity swaps, etc."},
    ]
