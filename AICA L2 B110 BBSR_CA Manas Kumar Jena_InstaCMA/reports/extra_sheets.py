"""
Extra sheets added around the firm's format:

  before FORM-II : Covering Letter, Assessment Note
  after the working sheets : FORM-V MPBF, Cash Flow, Break-even, Sensitivity,
                             GST Cross-check, Red Flags, Projected vs Actual,
                             Source Mapping, Audit Trail
"""
import datetime as dt
import os

from openpyxl.formatting.rule import CellIsRule
from openpyxl.utils import get_column_letter as CL

from analysis.layout import basis_of, INDIRECT, DIRECT, head_label
from core.models import fy_label, norm, STATEMENT_KINDS
from reports.styles import *  # noqa

YC = "EFGHIJKLMN"


def _client_ref():
    return "='Profit and Loss'!B1"


def _firm(c):
    s = c.s
    return {"name": s.get("firm_name", "") or "", "frn": s.get("firm_frn", "") or "",
            "partner": s.get("preparer_name", "") or "", "mrn": s.get("preparer_membership", "") or "",
            "designation": s.get("preparer_designation", "") or "Partner", "address": s.get("firm_address", "") or "",
            "phone": s.get("firm_phone", "") or "", "email": s.get("firm_email", "") or "",
            "place": s.get("firm_place", "") or c.it.place or "", "letterhead": s.get("letterhead_image", "") or ""}


def _firm_signature(ws, r, c, col="B"):
    f = _firm(c)
    put(ws, "%s%d" % (col, r), "For %s" % (f["name"] or "________________"), F_HEAD)
    put(ws, "%s%d" % (col, r + 1), "Chartered Accountants", F_BODY)
    put(ws, "%s%d" % (col, r + 2), "FRN: %s" % (f["frn"] or "________"), F_BODY)
    put(ws, "%s%d" % (col, r + 6), "(CA %s)" % f["partner"] if f["partner"] else "(CA ________________)", F_HEAD)
    put(ws, "%s%d" % (col, r + 7), f["designation"], F_BODY)
    put(ws, "%s%d" % (col, r + 8), "M.No.: %s" % (f["mrn"] or "________"), F_BODY)
    put(ws, "%s%d" % (col, r + 10), "Place: %s" % f["place"], F_BODY)
    put(ws, "%s%d" % (col, r + 11), "Date: %s" % c.it.prep_date.strftime("%d-%m-%Y"), F_BODY)
    return r + 12


def _letterhead(ws, c, width_col="B"):
    f = _firm(c)
    r = 1
    if f["letterhead"] and os.path.exists(f["letterhead"]):
        try:
            from openpyxl.drawing.image import Image
            img = Image(f["letterhead"])
            ratio = 620.0 / max(img.width, 1)
            img.width, img.height = int(img.width * ratio), int(img.height * ratio)
            ws.add_image(img, "B1")
            rows = int(img.height / 20) + 2
            return rows + 1
        except Exception:
            pass
    put(ws, "B1", f["name"] or "[ Firm name - enter in Settings ]", Font(name="Cambria", size=18, bold=True,
                                                                          color="1F3864"), align=CENTER)
    put(ws, "B2", "Chartered Accountants", Font(name="Cambria", size=12, italic=True), align=CENTER)
    put(ws, "B3", f["address"], F_BODY, align=CENTER)
    contact = "  |  ".join(x for x in [("Ph: " + f["phone"]) if f["phone"] else "", f["email"]] if x)
    put(ws, "B4", contact, F_BODY, align=CENTER, border=B_BOTTOM)
    return 6


def _years_text(c, kinds):
    return ", ".join(y.label for y in c.years if y.kind in kinds) or "-"


def _facility_text(c):
    it = c.it
    parts = []
    if it.has_cc:
        parts.append("cash credit limit of Rs %s" % format(int(it.cc_limit), ","))
    if it.has_tl:
        parts.append("term loan of Rs %s%s" % (format(int(it.tl_amount), ","),
                                               (" for " + it.tl_purpose) if it.tl_purpose else ""))
    return " and ".join(parts) or "credit facilities"


# ======================================================================
def covering_letter(wb, c):
    ws = wb.create_sheet("Covering Letter", 1)
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 100
    r = _letterhead(ws, c)
    it = c.it
    put(ws, "B%d" % r, "Date: %s" % it.prep_date.strftime("%d-%m-%Y"), F_BODY, align=RIGHT)
    r += 2
    for t in ["To", "The Branch Manager", it.bank_name or "[Bank]", (it.branch + " Branch") if it.branch else ""]:
        put(ws, "B%d" % r, t, F_BODY)
        r += 1
    r += 1
    subj = "Subject: Submission of CMA data in respect of %s - proposal for %s (%s case)" % (
        it.client_name, _facility_text(c), it.case_type.lower())
    put(ws, "B%d" % r, subj, F_HEAD, align=WRAP)
    ws.row_dimensions[r].height = 16.5 * (len(subj) // 88 + 1)
    r += 2
    put(ws, "B%d" % r, "Dear Sir / Madam,", F_BODY)
    r += 2
    paras = [
        "At the request of %s (%s, %s), we enclose the CMA data prepared in support of the proposal for %s." % (
            it.client_name, it.constitution.lower(), it.nature.lower() + " business", _facility_text(c)),
        "The CMA data covers the following years - %s." % "; ".join(
            "%s: %s" % (k.lower(), _years_text(c, (k,))) for k in ("Audited", "Actual", "Provisional", "Estimated",
                                                                    "Projected")
            if any(y.kind == k for y in c.years)),
        "The actual figures are taken from the financial statements furnished by the %s. The estimated and projected "
        "figures have been prepared on the basis of the assumptions furnished by the management, which are set out in "
        "the Projection Basis and CMA Tests sheets. These estimates and projections are not audited or certified by "
        "us; actual results may differ." % (it.signatory_title.lower() or "borrower"),
        "The key results are summarised in the enclosed Assessment Note.",
        "Enclosures: Assessment Note; CMA data - FORM II to FORM VI, ABF, ratios, CRA data and analysis; Profit and "
        "Loss Account and Balance Sheet for all years; term loan repayment schedule; working of drawing power, "
        "turnover and DSCR; projection basis and supporting statements.",
        "We shall be glad to furnish any further information you may require."]
    for t in paras:
        put(ws, "B%d" % r, t, F_BODY, align=WRAP)
        ws.row_dimensions[r].height = 15.5 * (len(t) // 95 + 1)
        r += 2
    put(ws, "B%d" % r, "Yours faithfully,", F_BODY)
    _firm_signature(ws, r + 2, c)
    return ws


def assessment_note(wb, c, pll, bsl, CT):
    ws = wb.create_sheet("Assessment Note", 2)
    ws.sheet_view.showGridLines = False
    it = c.it
    fut = c.future
    ncol = len(fut)
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 44
    for j in range(max(ncol, 2)):
        ws.column_dimensions[CL(3 + j)].width = 17
    put(ws, "B1", "ASSESSMENT NOTE", Font(name="Cambria", size=16, bold=True, color="1F3864"))
    put(ws, "B2", _client_ref(), F_HEAD)
    r = 4
    put(ws, "B%d" % r, "1. BORROWER AND PROPOSAL", F_HEAD)
    r += 1
    info = [("Constitution", it.constitution), ("Nature of business", it.nature), ("Address", it.address),
            ("PAN / GSTIN", " / ".join(x for x in (it.pan, it.gstin) if x) or "-"),
            ("Bank / branch", ", ".join(x for x in (it.bank_name, it.branch) if x) or "-"),
            ("Case", it.case_type),
            ("Existing CC limit", "Rs %s" % format(int(it.cc_existing_limit), ",") if it.cc_existing_limit else "-"),
            ("Proposed CC limit", ("Rs %s at %.2f%% p.a." % (format(int(it.cc_limit), ","),
                                                            norm(it, "cc_rate", c.sd) * 100)) if it.has_cc else "Nil"),
            ("Proposed term loan", ("Rs %s at %.2f%% p.a., %d months (moratorium %d), %s%s" % (
                format(int(it.tl_amount), ","), norm(it, "tl_rate", c.sd) * 100, it.tl_tenure_months,
                it.tl_moratorium_months, it.tl_method, (" - " + it.tl_purpose) if it.tl_purpose else ""))
             if it.has_tl else "Nil"),
            ("Years", " | ".join("%s: %s" % (k, _years_text(c, (k,))) for k in
                                 ("Audited", "Actual", "Provisional", "Estimated", "Projected")
                                 if any(y.kind == k for y in c.years)))]
    last = CL(max(3, 2 + ncol))
    for k, v in info:
        put(ws, "B%d" % r, k, F_HEAD, align=WRAP)
        put(ws, "C%d" % r, v, F_BODY, align=WRAP)
        ws.merge_cells("C%d:%s%d" % (r, last, r))
        ws.row_dimensions[r].height = 16 * (len(str(v)) // (17 * max(ncol, 1) // 1 + 1) + 1)
        r += 1
    r += 1
    put(ws, "B%d" % r, "2. KEY FIGURES AND BANK TESTS (Rs.)", F_HEAD)
    r += 1
    put(ws, "B%d" % r, "Particulars", F_HEAD, border=B_BOTTOM)
    cols = {}
    for j, i in enumerate(fut):
        col = CL(3 + j)
        cols[i] = col
        y = c.years[i]
        put(ws, "%s%d" % (col, r), "%s\n%s" % (y.label, y.kind), F_HEAD, align=CENTER, border=B_BOTTOM)
    ws.row_dimensions[r].height = 32
    r += 1
    rows = [("Sales", lambda i: "=" + pll.sales_cells(i, True), ACC),
            ("Net profit", lambda i: "='Profit and Loss'!E%d" % pll.row("np_cd", i), ACC),
            ("Cash at bank", lambda i: "='Balance Sheet'!I%d" % bsl.R("bank", i), ACC),
            ("Drawing power", lambda i: "='CMA Tests'!%s%d" % (CT["cols"][i], CT["rows"]["dp"]), ACC),
            ("CC limit", lambda i: "='CMA Tests'!%s%d" % (CT["cols"][i], CT["rows"]["limit"]), ACC),
            ("Drawing power test", lambda i: "='CMA Tests'!%s%d" % (CT["cols"][i], CT["rows"]["dp_status"]), None),
            ("Turnover / CC limit", lambda i: "='CMA Tests'!%s%d" % (CT["cols"][i], CT["rows"]["mult"]), X2),
            ("Turnover test", lambda i: "='CMA Tests'!%s%d" % (CT["cols"][i], CT["rows"]["to_status"]), None),
            ("DSCR", lambda i: "=DSCR!%s18" % CT["cols"][i], "0.00"),
            ("DSCR test", lambda i: "=DSCR!%s22" % CT["cols"][i], None),
            ("Current ratio (FORM-III)", lambda i: "='FORM-III'!%s146" % YC[i], "0.00"),
            ("TOL / TNW (FORM-III)", lambda i: "='FORM-III'!%s148" % YC[i], "0.00")]
    for lab, fn, fmt in rows:
        put(ws, "B%d" % r, lab)
        for i, col in cols.items():
            put(ws, "%s%d" % (col, r), fn(i), F_BODY, fmt, align=None if fmt else CENTER)
        r += 1
    put(ws, "B%d" % r, "Average DSCR", F_HEAD)
    if cols:
        put(ws, "C%d" % r, "=DSCR!C24", F_HEAD, "0.00")
        put(ws, "D%d" % r, "=DSCR!C25", F_HEAD, align=CENTER)
    r += 2
    put(ws, "B%d" % r, "3. BASIS OF PREPARATION", F_HEAD)
    r += 1
    bd = c.r.summary.get("base_days", {})
    basis = [
        "Actual figures as per the financial statements furnished; estimated / projected figures are formulas "
        "built on the assumptions in the Projection Basis and CMA Tests sheets.",
        "Sales growth as entered for each year; variable expenses at the previous-year ratio to sales, fixed "
        "expenses held; purchases balanced to the previous-year gross profit %.",
        "Stock %s days of cost of sales and creditors %s days of purchases (actual trend unless changed); debtor "
        "days from the actual trend (%s days), raised only where needed for drawing power (cap %d days)." % (
            bd.get("stock", "-"), bd.get("creditor", "-"), bd.get("debtor", "-"), it.debtor_days_cap),
        "Drawing power = (stock - creditors) x (1 - stock margin) + debtors x (1 - debtor margin); it must exceed "
        "the CC limit in every year.",
        "Interest on CC from %s (part-year in the first year); term-loan interest and principal as per the "
        "repayment schedule; depreciation on WDV." % it.facility_start.strftime("%b-%Y"),
        "DSCR = (net profit + depreciation + interest%s) / (CC interest on the full limit + term-loan interest and "
        "principal + existing loans)." % (" - drawings" if it.dscr_deduct_drawings else
                                          "; drawings not deducted, as banks do"),
        "Cash at bank is the balancing figure in estimated / projected years."]
    for t in basis:
        put(ws, "B%d" % r, "- " + t, F_BODY, align=WRAP)
        ws.merge_cells("B%d:%s%d" % (r, CL(max(3, 2 + ncol)), r))
        ws.row_dimensions[r].height = 16 * (len(t) // 110 + 1)
        r += 1
    r += 1
    put(ws, "B%d" % r, "4. POINTS FOR ATTENTION AND DECISIONS", F_HEAD)
    r += 1
    from analysis.validator2 import validate
    items = c.r.warnings + c.r.decisions + ["%s: %s" % (lv, m) for lv, m in validate(c.p, c.r) if lv == "WARN"]
    for t in items or ["None."]:
        put(ws, "B%d" % r, "- " + t, F_BODY, align=WRAP)
        ws.merge_cells("B%d:%s%d" % (r, CL(max(3, 2 + ncol)), r))
        ws.row_dimensions[r].height = 16 * (len(t) // 110 + 1)
        r += 1
    r += 1
    put(ws, "B%d" % r, "The estimates and projections are based on the management's assumptions and are not audited "
                       "or certified. The lending bank's own norms prevail over the tests shown.", F_SMALL, align=WRAP)
    ws.merge_cells("B%d:%s%d" % (r, CL(max(3, 2 + ncol)), r))
    ws.row_dimensions[r].height = 30
    _firm_signature(ws, r + 2, c)
    ws.conditional_formatting.add("C1:%s200" % CL(3 + ncol), CellIsRule(operator="equal", formula=['"PASS"'], fill=FILL_PASS))
    ws.conditional_formatting.add("C1:%s200" % CL(3 + ncol), CellIsRule(operator="equal", formula=['"FAIL"'], fill=FILL_FAIL))
    ws.conditional_formatting.add("C1:%s200" % CL(3 + ncol), CellIsRule(operator="equal", formula=['"AMBER"'], fill=FILL_AMBER))
    return ws


# ======================================================================
def _year_header(ws, c, r, idxs, start_col=3, title="Particulars"):
    put(ws, "B%d" % r, title, F_HEAD, border=B_BOTTOM)
    cols = {}
    for j, i in enumerate(idxs):
        col = CL(start_col + j)
        cols[i] = col
        y = c.years[i]
        put(ws, "%s%d" % (col, r), "%s\n%s" % (y.label, y.kind), F_HEAD, align=CENTER, border=B_BOTTOM)
    ws.row_dimensions[r].height = 32
    return cols


def _basic(ws, title, widths=(2, 50)):
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = widths[0]
    ws.column_dimensions["B"].width = widths[1]
    put(ws, "B1", title, F_HEAD)
    put(ws, "B2", _client_ref(), F_GREEN)


def form_v(wb, c):
    ws = wb.create_sheet("FORM-V MPBF")
    _basic(ws, "FORM V - COMPUTATION OF MAXIMUM PERMISSIBLE BANK FINANCE (TANDON - SECOND METHOD)")
    put(ws, "B3", '="Amounts in Rs. "&\'FORM-II\'!G6', F_SMALL)
    cols = _year_header(ws, c, 5, list(range(c.n)))
    rows = [("1. Total current assets", "='FORM-III'!%s111"),
            ("2. Other current liabilities (other than bank borrowings)", "='FORM-III'!%s35-'FORM-III'!%s18"),
            ("3. Working capital gap (1 - 2)", "=%s6-%s7"),
            ("4. Minimum stipulated NWC (25% of total current assets)", "=%s6*25%%"),
            ("5. Actual / projected NWC", "='FORM-III'!%s144"),
            ("6. Item 3 minus item 4", "=%s8-%s9"),
            ("7. Item 3 minus item 5", "=%s8-%s10"),
            ("8. MAXIMUM PERMISSIBLE BANK FINANCE (lower of 6 and 7)", "=MIN(%s11,%s12)"),
            ("9. Bank borrowing (cash credit)", "='FORM-III'!%s18"),
            ("10. Excess borrowing over MPBF (9 - 8)", "=%s14-%s13")]
    for k, (lab, f) in enumerate(rows):
        r = 6 + k
        put(ws, "B%d" % r, lab, F_HEAD if k in (2, 7) else F_BODY)
        for i, col in cols.items():
            fc = YC[i]
            n = f.count("%s")
            if f.startswith("='FORM-III'"):
                val = f % tuple([fc] * n)
            else:
                val = f % tuple([col] * n)
            put(ws, "%s%d" % (col, r), val, fmt="#,##0.00")
    for j in range(len(cols)):
        ws.column_dimensions[CL(3 + j)].width = 15


def cash_flow(wb, c, pll, bsl):
    ws = wb.create_sheet("Cash Flow")
    _basic(ws, "CASH FLOW STATEMENT (INDIRECT METHOD) - Rs.")
    idx = list(range(1, c.n))
    cols = _year_header(ws, c, 4, idx)
    P = lambda k, i, side="left": "'Profit and Loss'!%s%d" % ("E" if side == "left" else "I", pll.row(k, i, side))  # noqa

    def B(key, i, col):
        return "'Balance Sheet'!%s%d" % (col, bsl.L(key, i) if col in "CD" else bsl.R(key, i))

    def S(lines, i, col):
        return "(" + "+".join(B(ln.id, i, col) for ln in lines) + ")" if lines else "0"

    def fa(i):
        return "(" + "+".join("'Balance Sheet'!" + bsl.fa_net_cell(ln, i, c.years[i].from_statement)
                              for ln in c.fa_l) + ")" if c.fa_l else "0"

    def own(i):
        return B("drw", i, "D") + (("+" + B("share", i, "D")) if c.company else "")

    def tl(i):
        cells = [B(ln.id, i, "D") for ln in c.tl_l] + ([B("newtl", i, "D")] if c.it.has_tl else [])
        return "(" + "+".join(cells) + ")" if cells else "0"
    tax = (lambda i: P("tax", i)) if c.include_tax else (lambda i: "0")
    lines = [
        ("A. OPERATING ACTIVITIES", None),
        ("Net profit before tax", lambda i: "=%s+%s" % (P("np_cd", i), tax(i))),
        ("Add: Depreciation", lambda i: "=" + P("depreciation", i)),
        ("Add: Interest", lambda i: "=" + P("interest", i)),
        ("Operating profit before working-capital changes", "SUM3"),
        ("(Increase) / decrease in stock", lambda i: "=-(%s-%s)" % (B("stock", i, "I"), B("stock", i - 1, "I"))),
        ("(Increase) / decrease in debtors", lambda i: "=-(%s-%s)" % (B("debt", i, "I"), B("debt", i - 1, "I"))),
        ("(Increase) / decrease in loans, advances & other current assets",
         lambda i: "=-(%s+%s-%s-%s)" % (S(c.la_l, i, "I"), S(c.oca_l, i, "I"), S(c.la_l, i - 1, "I"), S(c.oca_l, i - 1, "I"))),
        ("Increase / (decrease) in creditors", lambda i: "=%s-%s" % (B("cred", i, "C"), B("cred", i - 1, "C"))),
        ("Increase / (decrease) in other current liabilities",
         lambda i: "=%s+%s-%s-%s" % (S(c.stat_l, i, "C"), S(c.ocl_l, i, "C"), S(c.stat_l, i - 1, "C"), S(c.ocl_l, i - 1, "C"))),
        ("Less: Income tax", lambda i: "=-" + tax(i)),
        ("Net cash from operating activities (A)", "SUMOP"),
        ("B. INVESTING ACTIVITIES", None),
        ("Purchase of fixed assets (net)", lambda i: "=-(%s-%s+%s)" % (fa(i), fa(i - 1), P("depreciation", i))),
        ("(Increase) / decrease in investments", lambda i: "=-(%s-%s)" % (S(c.inv_l, i, "I"), S(c.inv_l, i - 1, "I"))),
        ("Net cash from investing activities (B)", "SUMINV"),
        ("C. FINANCING ACTIVITIES", None),
        ("Capital introduced / (drawings, dividend)", lambda i: "=(%s)-(%s)-%s" % (own(i), own(i - 1), P("np_cd", i))),
        ("Increase / (decrease) in cash credit", lambda i: "=%s-%s" % (B("cc", i, "D"), B("cc", i - 1, "D"))),
        ("Increase / (decrease) in term loans", lambda i: "=%s-%s" % (tl(i), tl(i - 1))),
        ("Increase / (decrease) in unsecured loans", lambda i: "=%s-%s" % (S(c.ul_l, i, "D"), S(c.ul_l, i - 1, "D"))),
        ("Interest paid", lambda i: "=-" + P("interest", i)),
        ("Net cash from financing activities (C)", "SUMFIN"),
        ("NET INCREASE / (DECREASE) IN CASH (A + B + C)", "NET"),
        ("Cash and bank at the beginning", lambda i: "=%s+%s" % (B("bank", i - 1, "I"), B("cash", i - 1, "I"))),
        ("Cash and bank at the end", "END"),
        ("Check: as per Balance Sheet (difference must be 0)", "CHK"),
    ]
    r0 = 5
    pos = {}
    for k, (lab, f) in enumerate(lines):
        r = r0 + k
        pos[lab] = r
        bold = f is None or isinstance(f, str)
        put(ws, "B%d" % r, lab, F_HEAD if bold else F_BODY)
        for i, col in cols.items():
            if f is None:
                continue
            if callable(f):
                v = f(i)
            elif f == "SUM3":
                v = "=SUM(%s%d:%s%d)" % (col, r - 3, col, r - 1)
            elif f == "SUMOP":
                v = "=SUM(%s%d:%s%d)" % (col, r - 7, col, r - 1)
            elif f == "SUMINV":
                v = "=SUM(%s%d:%s%d)" % (col, r - 2, col, r - 1)
            elif f == "SUMFIN":
                v = "=SUM(%s%d:%s%d)" % (col, r - 5, col, r - 1)
            elif f == "NET":
                v = "=%s%d+%s%d+%s%d" % (col, pos["Net cash from operating activities (A)"], col,
                                         pos["Net cash from investing activities (B)"], col,
                                         pos["Net cash from financing activities (C)"])
            elif f == "END":
                v = "=%s%d+%s%d" % (col, r - 2, col, r - 1)
            elif f == "CHK":
                v = "=%s%d-(%s+%s)" % (col, r - 1, B("bank", i, "I"), B("cash", i, "I"))
            put(ws, "%s%d" % (col, r), v, F_HEAD if bold else F_BODY, ACC)
    for j in range(len(cols)):
        ws.column_dimensions[CL(3 + j)].width = 17
    return pos


def break_even(wb, c, pll):
    ws = wb.create_sheet("Break-even")
    _basic(ws, "BREAK-EVEN ANALYSIS - Rs.")
    put(ws, "B3", "Variable costs: material cost and expenses marked V; fixed costs: expenses marked F, interest and "
                  "depreciation (classification as per Projection Basis).", F_SMALL)
    cols = _year_header(ws, c, 5, list(range(c.n)))
    P = lambda k, i, side="left": "'Profit and Loss'!%s%d" % ("E" if side == "left" else "I", pll.row(k, i, side))  # noqa
    exp = c.dir_l + c.ind_l

    def cell(ln, i):
        return "'Profit and Loss'!" + (pll.E(ln.id, i) if ln.id in pll.left else pll.I(ln.id, i))
    var_l = [ln for ln in exp if basis_of(ln) == "V"]
    fix_l = [ln for ln in exp if basis_of(ln) != "V"]
    rows = [("Sales", lambda i: "=" + pll.sales_cells(i, True)),
            ("Material cost (opening + purchases - closing)",
             lambda i: "=%s+%s-%s" % (P("opening_stock", i), P("purchases", i), P("closing_stock", i, "right"))),
            ("Other variable expenses", lambda i: "=" + ("+".join(cell(ln, i) for ln in var_l) or "0")),
            ("Total variable cost", lambda i: "=%s7+%s8" % (cols[i], cols[i])),
            ("CONTRIBUTION (sales - variable cost)", lambda i: "=%s6-%s9" % (cols[i], cols[i])),
            ("P/V ratio", lambda i: '=IF(%s6=0,0,%s10/%s6)' % (cols[i], cols[i], cols[i])),
            ("Fixed expenses", lambda i: "=" + ("+".join(cell(ln, i) for ln in fix_l) or "0")),
            ("Interest", lambda i: "=" + P("interest", i)),
            ("Depreciation", lambda i: "=" + P("depreciation", i)),
            ("Total fixed cost", lambda i: "=SUM(%s12:%s14)" % (cols[i], cols[i])),
            ("BREAK-EVEN SALES (fixed cost / P/V ratio)", lambda i: '=IF(%s11<=0,"n/a",%s15/%s11)' % (cols[i], cols[i], cols[i])),
            ("Break-even as % of sales", lambda i: '=IF(OR(%s16="n/a",%s6=0),"n/a",%s16/%s6)' % (cols[i], cols[i], cols[i], cols[i])),
            ("CASH BREAK-EVEN SALES ((fixed cost - depreciation) / P/V)",
             lambda i: '=IF(%s11<=0,"n/a",(%s15-%s14)/%s11)' % (cols[i], cols[i], cols[i], cols[i])),
            ("Margin of safety (sales - break-even sales)", lambda i: '=IF(%s16="n/a","n/a",%s6-%s16)' % (cols[i], cols[i], cols[i]))]
    for k, (lab, fn) in enumerate(rows):
        r = 6 + k
        bold = lab.isupper() or lab.startswith(("CONTRIBUTION", "BREAK", "CASH"))
        put(ws, "B%d" % r, lab, F_HEAD if bold else F_BODY)
        for i, col in cols.items():
            put(ws, "%s%d" % (col, r), fn(i), F_HEAD if bold else F_BODY, PCT if k in (5, 11) else ACC)
    for j in range(len(cols)):
        ws.column_dimensions[CL(3 + j)].width = 17


def sensitivity(wb, c):
    from analysis.engine import sensitivity as sens
    ws = wb.create_sheet("Sensitivity")
    _basic(ws, "SENSITIVITY ANALYSIS - DSCR AND DRAWING POWER UNDER STRESS")
    put(ws, "B3", "Computed by InstaCMA at the time of export (values); change the assumptions and export again "
                  "to refresh.", F_SMALL)
    res = sens(c.p, c.sd)
    r = 5
    for case in res:
        put(ws, "B%d" % r, case["case"], F_HEAD, border=B_BOTTOM)
        for j, h in enumerate(["Sales", "Net profit", "DSCR", "Drawing power", "CC limit", "DP test"]):
            put(ws, "%s%d" % (CL(3 + j), r), h, F_HEAD, align=CENTER, border=B_BOTTOM)
        r += 1
        for (lab, s, pat, d, dp, lim, st) in case["years"]:
            put(ws, "B%d" % r, "FY " + lab)
            for j, (v, f) in enumerate([(s, ACC), (pat, ACC), (d if d is not None else "n/a", "0.00"),
                                        (dp, ACC), (lim, ACC), (st, None)]):
                put(ws, "%s%d" % (CL(3 + j), r), v, F_BODY, f, align=CENTER if f is None else None)
            r += 1
        put(ws, "B%d" % r, "Average DSCR", F_HEAD)
        put(ws, "E%d" % r, case["dscr_avg"] if case["dscr_avg"] is not None else "n/a", F_HEAD, "0.00")
        r += 2
    for j in range(6):
        ws.column_dimensions[CL(3 + j)].width = 16
    ws.conditional_formatting.add("C1:H200", CellIsRule(operator="equal", formula=['"PASS"'], fill=FILL_PASS))
    ws.conditional_formatting.add("C1:H200", CellIsRule(operator="equal", formula=['"FAIL"'], fill=FILL_FAIL))


def gst_check(wb, c, pll):
    ws = wb.create_sheet("GST Cross-check")
    _basic(ws, "TURNOVER CROSS-CHECK - BOOKS vs GST RETURNS (GSTR-3B)")
    put(ws, "B3", "Enter the GSTR-3B taxable + exempt turnover for each actual year (blue). Differences above 5% "
                  "should be reconciled (opening / closing advances, credit notes, non-GST income, inter-branch).",
        F_SMALL, align=WRAP)
    ws.row_dimensions[3].height = 30
    idx = [i for i, y in enumerate(c.years) if y.kind in STATEMENT_KINDS]
    cols = _year_header(ws, c, 5, idx)
    labels = ["Sales as per books", "Turnover as per GSTR-3B (input)", "Difference", "Difference %", "Status"]
    for k, lab in enumerate(labels):
        put(ws, "B%d" % (6 + k), lab, F_HEAD if k in (2, 4) else F_BODY)
    for i, col in cols.items():
        y = c.years[i]
        put(ws, "%s6" % col, "=" + pll.sales_cells(i, True), fmt=ACC)
        inp(ws, "%s7" % col, c.it.gst_turnover.get(str(y.fy)) or None, ACC)
        put(ws, "%s8" % col, '=IF(%s7="","",%s6-%s7)' % (col, col, col), F_HEAD, ACC)
        put(ws, "%s9" % col, '=IF(OR(%s7="",%s7=0),"",%s8/%s7)' % (col, col, col, col), fmt=PCT)
        put(ws, "%s10" % col, '=IF(%s9="","Not entered",IF(ABS(%s9)<=5%%,"PASS","AMBER"))' % (col, col), align=CENTER)
    for j in range(len(cols)):
        ws.column_dimensions[CL(3 + j)].width = 18
    ws.conditional_formatting.add("C10:K10", CellIsRule(operator="equal", formula=['"PASS"'], fill=FILL_PASS))
    ws.conditional_formatting.add("C10:K10", CellIsRule(operator="equal", formula=['"AMBER"'], fill=FILL_AMBER))


def red_flags(wb, c, pll, bsl, CT):
    ws = wb.create_sheet("Red Flags")
    _basic(ws, "RED FLAGS - POINTS A BANK CREDIT OFFICER WILL QUESTION")
    put(ws, "B3", "OK = no issue; FLAG = review and be ready to explain.", F_SMALL)
    cols = _year_header(ws, c, 5, list(range(c.n)))
    S = lambda i: pll.sales_cells(i, True)   # noqa
    GP = lambda i: "'Profit and Loss'!E%d" % pll.row("gp_cd", i)   # noqa
    NP = lambda i: "'Profit and Loss'!E%d" % pll.row("np_cd", i)   # noqa
    checks = [
        ("Gross profit % moves by more than 3 points from the previous year",
         lambda i: '=IF(OR(%s=0,%s=0),"OK",IF(ABS(%s/%s-%s/%s)>3%%,"FLAG","OK"))' % (
             S(i), S(i - 1), GP(i), S(i), GP(i - 1), S(i - 1)) if i else '="OK"'),
        ("Sales growth above 30% in a year",
         lambda i: '=IF(%s=0,"OK",IF(%s/%s-1>30%%,"FLAG","OK"))' % (S(i - 1), S(i), S(i - 1)) if i else '="OK"'),
        ("Net loss", lambda i: '=IF(%s<0,"FLAG","OK")' % NP(i)),
        ("Debtors above 90 days of sales",
         lambda i: '=IF(%s=0,"OK",IF(\'Balance Sheet\'!I%d/%s*365>90,"FLAG","OK"))' % (S(i), bsl.R("debt", i), S(i))),
        ("Current ratio below 1.33", lambda i: '=IF(\'FORM-III\'!%s146="","OK",IF(\'FORM-III\'!%s146<1.33,"FLAG","OK"))'
         % (YC[i], YC[i])),
        ("Negative net working capital", lambda i: '=IF(\'FORM-III\'!%s144<0,"FLAG","OK")' % YC[i]),
        ("TOL / TNW above 3", lambda i: '=IF(\'FORM-III\'!%s148="","OK",IF(\'FORM-III\'!%s148>3,"FLAG","OK"))'
         % (YC[i], YC[i])),
        ("Cash at bank negative", lambda i: '=IF(\'Balance Sheet\'!I%d<0,"FLAG","OK")' % bsl.R("bank", i)),
        ("Drawing power below the CC limit", lambda i: ('=IF(\'CMA Tests\'!%s%d="FAIL","FLAG","OK")' % (
            CT["cols"][i], CT["rows"]["dp_status"])) if i in CT["cols"] else '="OK"'),
        ("DSCR outside the required band", lambda i: ('=IF(OR(DSCR!%s22="FAIL",DSCR!%s22="AMBER"),"FLAG","OK")' % (
            CT["cols"][i], CT["cols"][i])) if i in CT["cols"] else '="OK"'),
    ]
    for k, (lab, fn) in enumerate(checks):
        r = 6 + k
        put(ws, "B%d" % r, lab, align=WRAP)
        for i, col in cols.items():
            put(ws, "%s%d" % (col, r), fn(i), align=CENTER)
    rng = "C6:%s%d" % (CL(2 + len(cols)), 6 + len(checks))
    ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"OK"'], fill=FILL_PASS))
    ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"FLAG"'], fill=FILL_FAIL))
    for j in range(len(cols)):
        ws.column_dimensions[CL(3 + j)].width = 13


def projected_vs_actual(wb, c):
    ws = wb.create_sheet("Projected vs Actual")
    _basic(ws, "PROJECTED vs ACTUAL - EARLIER PROJECTIONS COMPARED WITH THE ACTUAL RESULTS")
    hist = c.p.history or {}
    rows = []
    for y in c.years:
        if y.kind in STATEMENT_KINDS and str(y.fy) in hist:
            rows.append((y, hist[str(y.fy)], c.r.year(y.fy)))
    if not rows:
        put(ws, "B4", "No earlier projection is on file for the actual years. This comparison becomes available at the "
                      "next renewal: the projections in this CMA are saved in the client file and compared with the "
                      "actual results when the next actual year is added.", F_BODY, align=WRAP)
        ws.merge_cells("B4:H6")
        ws.row_dimensions[4].height = 48
        return
    r = 4
    for j, h in enumerate(["Year / item", "Projected", "Actual", "Variance", "Variance %"]):
        put(ws, "%s%d" % (CL(2 + j), r), h, F_HEAD, border=B_BOTTOM, align=CENTER)
    r += 1
    for y, h, act in rows:
        put(ws, "B%d" % r, "FY %s" % y.label, F_HEAD)
        r += 1
        for key, lab in [("sales", "Sales"), ("pat", "Net profit"), ("stock", "Stock"), ("debtors", "Debtors"),
                         ("creditors", "Creditors"), ("bank_balance", "Cash at bank")]:
            pv, av = h.get(key), act.get(key, 0.0) if act else 0.0
            put(ws, "B%d" % r, "   " + lab)
            put(ws, "C%d" % r, pv, fmt=ACC)
            put(ws, "D%d" % r, av, fmt=ACC)
            put(ws, "E%d" % r, "=D%d-C%d" % (r, r), fmt=ACC)
            put(ws, "F%d" % r, '=IF(C%d=0,"",E%d/C%d)' % (r, r, r), fmt=PCT)
            r += 1
    for col in "CDEF":
        ws.column_dimensions[col].width = 16


def source_mapping(wb, c):
    ws = wb.create_sheet("Source Mapping")
    _basic(ws, "SOURCE MAPPING - EVERY LINE OF THE CLIENT'S STATEMENTS AND ITS CMA HEAD")
    years = [y for y in c.years if y.from_statement]
    hdr = ["Statement", "Line as in the books", "CMA head", "Section"] + ["FY " + y.label for y in years] + ["Source"]
    for j, h in enumerate(hdr):
        put(ws, "%s4" % CL(2 + j), h, F_HEAD, border=B_BOTTOM, align=CENTER)
    r = 5
    for ln in c.p.lines:
        vals = [ln.statement, ln.label, head_label(ln.head).replace(" (WDV)", ""),
                ("Trading" if ln.section == "trading" else "P&L") if ln.statement == "PL" else ""]
        vals += [ln.v(y.fy) if str(y.fy) in ln.values else None for y in years]
        vals += ["; ".join(ln.sources)[:250]]
        for j, v in enumerate(vals):
            put(ws, "%s%d" % (CL(2 + j), r), v, F_BODY, ACC if isinstance(v, float) else None)
        r += 1
    ws.column_dimensions["B"].width = 10
    ws.column_dimensions["C"].width = 40
    ws.column_dimensions["D"].width = 34
    ws.column_dimensions["E"].width = 10
    for j in range(len(years)):
        ws.column_dimensions[CL(6 + j)].width = 15
    ws.column_dimensions[CL(6 + len(years))].width = 40


def audit_trail(wb, c, rows):
    ws = wb.create_sheet("Audit Trail")
    _basic(ws, "AUDIT TRAIL - IMPORTS, CHANGES AND EXPORTS")
    for j, h in enumerate(["Time", "User", "Action", "Detail"]):
        put(ws, "%s4" % CL(2 + j), h, F_HEAD, border=B_BOTTOM)
    rows = list(rows) + [(dt.datetime.now().strftime("%d-%m-%Y %H:%M:%S"), "System", "Workbook generated",
                          "InstaCMA")]
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            put(ws, "%s%d" % (CL(2 + j), 5 + i), v, F_BODY, align=WRAP if j == 3 else None)
    for col, w in zip("BCDE", (20, 12, 30, 70)):
        ws.column_dimensions[col].width = w


def write_all(wb, c, pll, bsl, CT, PB, audit_rows):
    covering_letter(wb, c)
    assessment_note(wb, c, pll, bsl, CT)
    form_v(wb, c)
    cash_flow(wb, c, pll, bsl)
    break_even(wb, c, pll)
    sensitivity(wb, c)
    gst_check(wb, c, pll)
    red_flags(wb, c, pll, bsl, CT)
    projected_vs_actual(wb, c)
    source_mapping(wb, c)
    audit_trail(wb, c, audit_rows)
