"""
CMA workbook writer - fills the built-in master format for one client.

Sheets written (in this order):
  Instructions (hidden) | Covering Letter | Assessment Note |
  FORM-II FORM-III FORM-IV FORM-VI ABF CHECK RATIOS CRA-DATA ANALYSIS  (bank format, kept) |
  Profit and Loss | Balance Sheet | Term Loan | CMA Tests | DSCR | Projection Basis  (rebuilt) |
  FORM-V MPBF | Cash Flow | Break-even | Sensitivity | GST Cross-check | Red Flags |
  Projected vs Actual | Source Mapping | Audit Trail  (extra)

Every estimated / projected figure is a formula; statement years are values.
"""
import datetime as dt

import openpyxl
from openpyxl.styles import Alignment
from openpyxl.comments import Comment
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Font, PatternFill
from openpyxl.styles.differential import DifferentialStyle
from openpyxl.styles.numbers import NumberFormat
from openpyxl.formatting.rule import Rule
from openpyxl.utils import get_column_letter as CL
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.pagebreak import Break, RowBreak

from analysis.layout import (DIRECT, INDIRECT, EXPENSE_HEADS, basis_of, rate_of, section_of, head_label,
                             is_tax_receivable, is_gst_receivable, is_deposit, SINGLE_LABEL)
from config.constants import FA_KEYS
from core.models import fy_label, norm, tax_rate, STATEMENT_KINDS
from reports.master_template import master_path, FORMAT_SHEETS
from reports.styles import *  # noqa

YC = "EFGHIJKLMN"     # FORM sheets year columns
U = "'FORM-II'!$P$6"  # unit divisor
FA_SHORT = {"fa_building": "Land & Building", "fa_plant": "Plant & Machinery", "fa_furniture": "Furniture & Fixtures",
            "fa_vehicle": "Vehicles", "fa_computer": "Computers", "fa_other": "Other Fixed Assets"}


def q(sheet):
    return "'%s'" % sheet


# ======================================================================
class Ctx:
    def __init__(self, project, result, settings):
        self.p = project
        self.r = result
        self.s = settings or {}
        self.it = project.intake
        self.years = project.year_list()
        self.n = len(self.years)
        self.company = self.it.is_company
        L = lambda *h: [ln for ln in project.lines if ln.head in h]   # noqa
        self.sales_l, self.oi_l = L("sales"), L("other_income")
        exp = L(*EXPENSE_HEADS)
        self.dir_l = [ln for ln in exp if section_of(ln) == "trading"]
        self.ind_l = [ln for ln in exp if section_of(ln) == "pl"]
        self.fa_l = [ln for ln in project.lines if ln.head in FA_KEYS]
        self.tl_l, self.ul_l = L("term_loans"), L("unsecured_loans")
        self.stat_l, self.ocl_l = L("statutory_dues"), L("other_cl")
        self.inv_l, self.la_l, self.oca_l = L("investments"), L("loans_advances"), L("other_ca")
        self.include_tax = (tax_rate(self.it) > 0 or any(
            ln.v(y.fy) for ln in L("tax") for y in self.years))
        self.has_intro = not self.company
        self.future = [i for i, y in enumerate(self.years) if y.kind not in STATEMENT_KINDS]
        self.tool = [i for i, y in enumerate(self.years) if not y.from_statement]
        self.sd = self.s.get("defaults", {})
        from analysis.engine import _capex_line
        self.capex_line = _capex_line(project) if (self.it.has_tl and self.it.tl_use == "Capex") else None

    def single(self, head):
        return [ln for ln in self.p.lines if ln.head == head]

    def sval(self, head, fy):
        return sum(ln.v(fy) for ln in self.single(head))

    def has_val(self, head, fy):
        return any(str(fy) in ln.values for ln in self.single(head))


# ======================================================================
# Layouts
# ======================================================================
class PLLayout:
    def __init__(self, c):
        self.c = c
        left = [("s", "opening_stock"), ("s", "purchases")] + [("l", ln) for ln in c.dir_l] + [("gp_cd", None)]
        right = [("l", ln) for ln in c.sales_l] + [("s", "closing_stock")]
        pl_left = [("l", ln) for ln in c.ind_l] + [("s", "interest"), ("s", "depreciation")] + \
            ([("s", "tax")] if c.include_tax else []) + [("np_cd", None)]
        pl_right = [("gp_bd", None)] + [("l", ln) for ln in c.oi_l]
        self.t_first = 8
        nt = max(len(left), len(right))
        self.t_total = self.t_first + nt
        self.p_first = self.t_total + 2
        npl = max(len(pl_left), len(pl_right))
        self.p_total = self.p_first + npl
        self.note = self.p_total + 3
        self.height = self.p_total + 15
        self.left = {}
        self.right = {}
        for i, (k, v) in enumerate(left):
            self.left[self._key(k, v)] = self.t_first + i
        for i, (k, v) in enumerate(right):
            self.right[self._key(k, v)] = self.t_first + i
        for i, (k, v) in enumerate(pl_left):
            self.left[self._key(k, v)] = self.p_first + i
        for i, (k, v) in enumerate(pl_right):
            self.right[self._key(k, v)] = self.p_first + i
        self.trading_left_items, self.trading_right_items = left, right
        self.pl_left_items, self.pl_right_items = pl_left, pl_right

    @staticmethod
    def _key(k, v):
        return v.id if k == "l" else (v if k == "s" else k)

    def start(self, i):
        return 1 + i * self.height

    def row(self, key, i, side="left"):
        return self.start(i) + (self.left if side == "left" else self.right)[key]

    def E(self, key, i):
        return "E%d" % self.row(key, i, "left")

    def I(self, key, i):
        return "I%d" % self.row(key, i, "right")

    def sales_cells(self, i, ext=False):
        cells = ["I%d" % self.row(ln.id, i, "right") for ln in self.c.sales_l]
        if ext:
            cells = ["'Profit and Loss'!" + x for x in cells]
        return "(" + "+".join(cells) + ")" if cells else "0"

    def x(self, ref):
        return "'Profit and Loss'!" + ref


class BSLayout:
    def __init__(self, c):
        self.c = c
        L = []
        if c.company:
            L += [("hd", "SHAREHOLDERS' FUNDS"), ("share", None), ("hd", "Reserves & Surplus"),
                  ("open", None), ("np", None), ("sub", None), ("drw", None)]
        else:
            L += [("hd", "CAPITAL ACCOUNT"), ("open", None), ("intro", None), ("np", None), ("sub", None),
                  ("drw", None)]
        L += [("gap", None), ("hd", "LOANS & BORROWINGS"), ("cc", None)] + [("l", ln) for ln in c.tl_l]
        if c.it.has_tl:
            L += [("newtl", None)]
        L += [("l", ln) for ln in c.ul_l]
        L += [("gap", None), ("hd", "CURRENT LIABILITIES & PROVISIONS"), ("cred", None)] + \
             [("l", ln) for ln in c.stat_l + c.ocl_l] + [("clsub", None)]
        R = [("hd", "FIXED ASSETS")]
        for ln in c.fa_l:
            R += [("fa_a", ln), ("fa_b", ln)]
        if c.inv_l:
            R += [("hd", "INVESTMENTS")] + [("l", ln) for ln in c.inv_l]
        R += [("hd", "CURRENT ASSETS, LOANS & ADVANCES"), ("stock", None), ("debt", None)] + \
             [("l", ln) for ln in c.la_l + c.oca_l] + [("bank", None), ("cash", None)]
        self.first = 8
        self.left_items, self.right_items = L, R
        self.left, self.right = {}, {}
        for i, (k, v) in enumerate(L):
            if k != "gap" and k != "hd":
                self.left[v.id if k == "l" else k] = self.first + i
        self.heads_left = [(self.first + i, v) for i, (k, v) in enumerate(L) if k == "hd"]
        for i, (k, v) in enumerate(R):
            if k == "hd":
                continue
            key = v.id if k == "l" else ((k + ":" + v.id) if k in ("fa_a", "fa_b") else k)
            self.right[key] = self.first + i
        self.heads_right = [(self.first + i, v) for i, (k, v) in enumerate(R) if k == "hd"]
        self.total = self.first + max(len(L), len(R)) + 1
        self.note = self.total + 2
        self.height = self.total + 14

    def start(self, i):
        return 1 + i * self.height

    def L(self, key, i):
        return self.start(i) + self.left[key]

    def R(self, key, i):
        return self.start(i) + self.right[key]

    def x(self, ref):
        return "'Balance Sheet'!" + ref

    def owners_cell(self, i):
        return "D%d" % self.L("drw", i)

    def fa_net_cell(self, ln, i, statement):
        shown_gross = statement and ln.gross.get(str(self.c.years[i].fy))
        return "I%d" % (self.R("fa_a:" + ln.id, i) if statement and not shown_gross else self.R("fa_b:" + ln.id, i))


# ======================================================================
def generate_workbook(project, result, out_path, settings=None, audit_rows=None):
    c = Ctx(project, result, settings)
    wb = openpyxl.load_workbook(master_path())
    pll, bsl = PLLayout(c), BSLayout(c)
    pb = wb.create_sheet("Profit and Loss")
    bs = wb.create_sheet("Balance Sheet")
    tl = wb.create_sheet("Term Loan")
    ct = wb.create_sheet("CMA Tests")
    ds = wb.create_sheet("DSCR")
    pbs = wb.create_sheet("Projection Basis")
    # positions needed across sheets
    PB = _pb_layout(c)
    TL = _tl_layout(c)
    CT = _ct_layout(c)
    _write_projection_basis(pbs, c, PB, pll, bsl)
    _write_term_loan(tl, c, TL, CT)
    _write_pl(pb, c, pll, bsl, PB, CT)
    _write_bs(bs, c, pll, bsl, PB, CT, TL)
    _write_cma_tests(ct, c, CT, pll, bsl, PB, TL)
    _write_dscr(ds, c, CT, pll, bsl)
    _write_format_links(wb, c, pll, bsl, CT)
    from reports import extra_sheets
    extra_sheets.write_all(wb, c, pll, bsl, CT, PB, audit_rows or [])
    from reports import page_setup
    page_setup.apply(wb, c)
    wb.active = wb.sheetnames.index("Covering Letter") if "Covering Letter" in wb.sheetnames else 1
    from reports.styles import clean_empty, to_cambria
    clean_empty(wb)
    to_cambria(wb)
    wb.save(out_path)
    return out_path


# ======================================================================
# Projection Basis
# ======================================================================
def _pb_layout(c):
    PB = {"cols": {}, "rows": {}, "type": {}, "rate": {}}
    for j, i in enumerate(c.tool):
        PB["cols"][i] = CL(4 + j)        # D, E, ...
    r = 6
    for key in ("growth", "gp", "stock_days", "debtor_days", "creditor_days", "drawings", "intro"):
        PB["rows"][key] = r
        r += 1
    r += 2
    PB["pl_head"] = r
    r += 1
    for ln in c.sales_l + c.dir_l + c.ind_l + c.oi_l:
        if ln.head == "sales":
            continue
        PB["type"][ln.id] = r
        r += 1
    r += 2
    PB["bs_head"] = r
    r += 1
    for ln in c.ul_l + c.stat_l + c.ocl_l + c.inv_l + c.la_l + c.oca_l:
        PB["type"][ln.id] = r
        r += 1
    PB["cash_row"] = None
    r += 2
    PB["fa_head"] = r
    r += 1
    for ln in c.fa_l:
        PB["rate"][ln.id] = r
        r += 1
    PB["end"] = r
    return PB


def pbref(PB, key, i):
    return "'Projection Basis'!$%s$%d" % (PB["cols"][i], PB["rows"][key])


def pbtype(PB, ln):
    return "'Projection Basis'!$C$%d" % PB["type"][ln.id]


def _write_projection_basis(ws, c, PB, pll, bsl):
    ws.sheet_view.showGridLines = False
    put(ws, "B1", "PROJECTION BASIS - SALES, EXPENSES AND BALANCE SHEET ITEMS", F_HEAD)
    put(ws, "B2", "='Profit and Loss'!B1", F_GREEN)
    put(ws, "B3", "Blue cells are inputs. V = varies with sales (previous-year ratio to sales x sales); F = fixed "
                  "(previous year). S = scales with sales; H = held at previous year.", F_SMALL)
    put(ws, "B5", "Year-wise assumptions", F_HEAD)
    for i, col in PB["cols"].items():
        y = c.years[i]
        put(ws, "%s5" % col, "FY %s (%s)" % (y.label, y.kind[:4] + "."), F_HEAD, align=CENTER)
    labels = {"growth": "Sales growth over previous year", "gp": "Gross profit % kept (previous year)",
              "stock_days": "Stock - days of cost of sales", "debtor_days": "Debtors - days of sales",
              "creditor_days": "Creditors - days of purchases",
              "drawings": "Dividend" if c.company else "Drawings", "intro": "Capital introduced"}
    for key, r in PB["rows"].items():
        put(ws, "B%d" % r, labels[key])
    for i, col in PB["cols"].items():
        y = c.r.years[i]
        prev = i - 1
        inp(ws, "%s%d" % (col, PB["rows"]["growth"]), y["growth"], PCT)
        if y.get("gp_override"):
            cg = inp(ws, "%s%d" % (col, PB["rows"]["gp"]), round(y["gp_ratio_used"], 6), '0.000%')
            cg.comment = Comment("Gross profit %% for this year set to keep DSCR within the bank's range "
                                 "(previous year's ratio would give a DSCR outside it).", "InstaCMA")
        else:
            put(ws, "%s%d" % (col, PB["rows"]["gp"]),
                "=IF(%s=0,0,('Profit and Loss'!E%d)/%s)" % (pll.sales_cells(prev, True), pll.row("gp_cd", prev),
                                                           pll.sales_cells(prev, True)), F_GREEN, '0.000%')
        csd = inp(ws, "%s%d" % (col, PB["rows"]["stock_days"]), y["stock_days"], DAYS)
        if y.get("stock_days_raised") is not None:
            csd.comment = Comment("Raised from %d days (actual trend) because debtor days at the cap were not enough "
                                  "for drawing power to exceed the CC limit." % y["stock_days_raised"], "InstaCMA")
        cdd = inp(ws, "%s%d" % (col, PB["rows"]["debtor_days"]), y["debtor_days"], DAYS)
        if y.get("debtor_days_auto"):
            cdd.comment = Comment("Solved: minimum days (from the actual trend) for drawing power to exceed the "
                                  "CC limit + buffer, capped at %d." % c.it.debtor_days_cap, "InstaCMA")
        inp(ws, "%s%d" % (col, PB["rows"]["creditor_days"]), y["creditor_days"], DAYS)
        inp(ws, "%s%d" % (col, PB["rows"]["drawings"]), y["drawings"], ACC)
        inp(ws, "%s%d" % (col, PB["rows"]["intro"]), y["capital_introduced"], ACC)
    put(ws, "B%d" % PB["pl_head"], "Profit & Loss line", F_HEAD, border=B_BOTTOM)
    put(ws, "C%d" % PB["pl_head"], "Type (V / F)", F_HEAD, border=B_BOTTOM)
    for i, col in PB["cols"].items():
        put(ws, "%s%d" % (col, PB["pl_head"]), "Ratio to sales FY %s" % c.years[i - 1].label, F_HEAD,
            border=B_BOTTOM, align=CENTER)
    dv = DataValidation(type="list", formula1='"V,F"')
    dv2 = DataValidation(type="list", formula1='"S,H"')
    ws.add_data_validation(dv)
    ws.add_data_validation(dv2)
    for ln in c.dir_l + c.ind_l + c.oi_l:
        r = PB["type"][ln.id]
        put(ws, "B%d" % r, ln.label)
        inp(ws, "C%d" % r, basis_of(ln) if basis_of(ln) in ("V", "F") else "V").alignment = CENTER
        dv.add("C%d" % r)
        for i, col in PB["cols"].items():
            ref = pll.E(ln.id, i - 1) if ln.id in pll.left else pll.I(ln.id, i - 1)
            put(ws, "%s%d" % (col, r), "=IF(%s=0,0,'Profit and Loss'!%s/%s)" % (
                pll.sales_cells(i - 1, True), ref, pll.sales_cells(i - 1, True)), F_GREEN, '0.000%')
    put(ws, "B%d" % PB["bs_head"], "Balance-sheet item", F_HEAD, border=B_BOTTOM)
    put(ws, "C%d" % PB["bs_head"], "Type (S / H)", F_HEAD, border=B_BOTTOM)
    for ln in c.ul_l + c.stat_l + c.ocl_l + c.inv_l + c.la_l + c.oca_l:
        r = PB["type"][ln.id]
        put(ws, "B%d" % r, ln.label if ln.head != "cash_in_hand" else "Cash in Hand")
        b = basis_of(ln) if ln.head != "cash_in_hand" else (ln.basis or "S")
        inp(ws, "C%d" % r, b if b in ("S", "H") else "H").alignment = CENTER
        dv2.add("C%d" % r)
    put(ws, "B%d" % PB["fa_head"], "Fixed asset", F_HEAD, border=B_BOTTOM)
    put(ws, "C%d" % PB["fa_head"], "Rate (WDV)", F_HEAD, border=B_BOTTOM)
    for ln in c.fa_l:
        r = PB["rate"][ln.id]
        put(ws, "B%d" % r, ln.label)
        inp(ws, "C%d" % r, rate_of(ln), '0.0%')
    put(ws, "B%d" % (PB["end"] + 1), "Purchases are balanced to the previous-year gross profit %; interest is "
                                       "worked out on the CMA Tests sheet; cash at bank is the balancing figure.",
        F_SMALL)
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 42
    ws.column_dimensions["C"].width = 14
    for j in range(len(PB["cols"])):
        ws.column_dimensions[CL(4 + j)].width = 17


# ======================================================================
# Term Loan
# ======================================================================
def _tl_layout(c):
    T = {"yes": "$C$5", "amount": "$C$6", "rate": "$C$7", "tenure": "$C$8", "mor": "$C$9", "method": "$C$10",
         "first": "$C$11", "inst": "$C$12", "emi": "$C$13", "ep": "$C$14", "use": "$C$15", "cls": "$C$16",
         "check": "$C$17", "fy_first": 21}
    T["fy_rows"] = {y.fy: T["fy_first"] + j for j, y in enumerate(c.years)}
    T["sched_hdr"] = T["fy_first"] + len(c.years) + 3
    T["s1"] = T["sched_hdr"] + 1
    T["s2"] = T["s1"] + 119
    return T


def tlref(T, key):
    return "'Term Loan'!" + T[key]


def tlfy(T, fy, col):
    """col: C instalments, D interest, E principal, F closing, G next-FY principal."""
    return "'Term Loan'!$%s$%d" % (col, T["fy_rows"][fy])


def _write_term_loan(ws, c, T, CT):
    it = c.it
    ws.sheet_view.showGridLines = False
    put(ws, "A1", "TERM LOAN REPAYMENT SCHEDULE & INTEREST", F_TITLE)
    put(ws, "A2", "='Profit and Loss'!B1", F_GREEN)
    put(ws, "A3", "[ AMOUNT IN Rs. ]  -  the schedule follows the repayment method chosen below", F_SMALL)
    put(ws, "A4", "A. INPUTS (blue = input)", F_HEAD)
    sch = c.r.tl_schedule
    rows = [("Term loan proposed (Yes / No)", "Yes" if it.has_tl else "No", "@", True),
            ("Term loan amount (Rs.)", it.tl_amount if it.has_tl else 0, ACC, True),
            ("Rate of interest (p.a.)", norm(it, "tl_rate", c.sd), PCT, True),
            ("Tenure (months, incl. moratorium; max 120)", sch.get("tenure") or it.tl_tenure_months, "0", True),
            ("Moratorium (months, interest only)", sch.get("moratorium", it.tl_moratorium_months), "0", True),
            ("Repayment method", it.tl_method, "@", True),
            ("First instalment month", "='CMA Tests'!$C$%d" % CT["rows"]["start"], "mmm-yyyy", False),
            ("Number of repayment instalments", "=C8-C9", "0", False),
            ("Equal EMI (Rs., rounded)", "=IF(OR(C5<>\"Yes\",C12<=0),0,ROUND(-PMT(C7/12,C12,C6),0))", ACC, False),
            ("Equal principal instalment (Rs., rounded)", "=IF(OR(C5<>\"Yes\",C12<=0),0,ROUND(C6/C12,0))", ACC, False),
            ("Use of term loan", it.tl_use, "@", True),
            ("Asset financed (if capex)", FA_SHORT.get(it.tl_capex_class, "Plant & Machinery"), "@", True),
            ("Check: principal repaid - loan (must be 0)", None, ACC, False)]
    for j, (lab, v, f, is_in) in enumerate(rows):
        r = 5 + j
        put(ws, "A%d" % r, lab)
        inp(ws, "C%d" % r, v, f) if is_in else put(ws, "C%d" % r, v, fmt=f)
    for ref, f in (("C5", '"Yes,No"'), ("C10", '"Equal EMI,Equal Principal"'), ("C15", '"Capex,Working capital"')):
        dv = DataValidation(type="list", formula1=f)
        ws.add_data_validation(dv)
        dv.add(ref)
    if it.tl_purpose:
        put(ws, "D6", "Purpose: " + it.tl_purpose, F_SMALL)
    # FY summary
    put(ws, "A%d" % (T["fy_first"] - 2), "B. YEAR-WISE SUMMARY", F_HEAD)
    for j, h in enumerate(["Financial year", "FY end", "Instalments", "Interest", "Principal", "Closing balance",
                           "Due next FY"]):
        put(ws, "%s%d" % ("ABCDEFG"[j], T["fy_first"] - 1), h, F_HEAD, border=B_BOTTOM, align=CENTER)
    s1, s2 = T["s1"], T["s2"]
    for y in c.years:
        r = T["fy_rows"][y.fy]
        put(ws, "A%d" % r, "FY %s (%s)" % (y.label, y.kind))
        put(ws, "B%d" % r, y.fy, fmt="0")
        put(ws, "C%d" % r, "=SUMIFS($H$%d:$H$%d,$C$%d:$C$%d,$B%d)" % (s1, s2, s1, s2, r), fmt=ACC)
        put(ws, "D%d" % r, "=SUMIFS($E$%d:$E$%d,$C$%d:$C$%d,$B%d)" % (s1, s2, s1, s2, r), fmt=ACC)
        put(ws, "E%d" % r, "=SUMIFS($F$%d:$F$%d,$C$%d:$C$%d,$B%d)" % (s1, s2, s1, s2, r), fmt=ACC)
        put(ws, "F%d" % r, '=IF(AND($C$5="Yes",$B%d>=$C$%d),$C$6-SUMIFS($F$%d:$F$%d,$C$%d:$C$%d,"<="&$B%d),0)' % (
            r, s1, s1, s2, s1, s2, r), fmt=ACC)
        put(ws, "G%d" % r, "=SUMIFS($F$%d:$F$%d,$C$%d:$C$%d,$B%d+1)" % (s1, s2, s1, s2, r), fmt=ACC)
    ws["C17"] = "=IF($C$5=\"Yes\",SUM(F%d:F%d)-C6,0)" % (s1, s2)
    hr = T["sched_hdr"]
    put(ws, "A%d" % (hr - 1), "C. MONTHLY SCHEDULE (method as selected above)", F_HEAD)
    for j, h in enumerate(["No.", "Month", "FY ends", "Opening balance", "Interest", "Principal", "Closing balance",
                           "Instalment"]):
        put(ws, "%s%d" % ("ABCDEFGH"[j], hr), h, F_HEAD, border=B_BOTTOM, align=CENTER)
    tenure = sch.get("tenure", 0) if it.has_tl else 0
    for n in range(1, 121):
        r = hr + n
        put(ws, "A%d" % r, n, fmt="0")
        put(ws, "B%d" % r, "=EDATE($C$11,A%d-1)" % r, fmt="mmm-yy")
        put(ws, "C%d" % r, "=YEAR(B%d)+IF(MONTH(B%d)>=4,1,0)" % (r, r), fmt="0")
        put(ws, "D%d" % r, "=IF($C$5=\"Yes\",$C$6,0)" if n == 1 else "=G%d" % (r - 1), fmt=ACC)
        put(ws, "E%d" % r, "=IF(A%d<=$C$8,ROUND(D%d*$C$7/12,0),0)" % (r, r), fmt=ACC)
        put(ws, "F%d" % r, '=IF(OR(A%d>$C$8,A%d<=$C$9),0,IF(A%d=$C$8,D%d,MIN(D%d,IF($C$10="Equal EMI",$C$13-E%d,$C$14))))'
            % (r, r, r, r, r, r), fmt=ACC)
        put(ws, "G%d" % r, "=D%d-F%d" % (r, r), fmt=ACC)
        put(ws, "H%d" % r, "=E%d+F%d" % (r, r), fmt=ACC)
        if n > max(tenure, 1):
            ws.row_dimensions[r].hidden = True
    for col, w in zip("ABCDEFGH", (44, 11, 10, 17, 15, 15, 17, 15)):
        ws.column_dimensions[col].width = w


# ======================================================================
# CMA Tests layout
# ======================================================================
def _ct_layout(c):
    CT = {"cols": {}, "rows": {}}
    for j, i in enumerate(c.future):
        CT["cols"][i] = CL(3 + j)        # C, D, ...
    keys_a = ["cc_yes", "cc_base", "cc_rate", "sm", "dm", "deduct", "over90", "buffer", "to_fail", "to_pass",
              "dscr_min", "dscr_max", "dscr_drw", "prep", "start", "start_fy", "months", "tax", "ul_rate"]
    r = 4
    for k in keys_a:
        CT["rows"][k] = r
        r += 1
    r += 1
    CT["hdr_b"] = r
    r += 1
    for k in ["fy", "limit", "frac", "cc_bal", "int_cc", "int_full"]:
        CT["rows"][k] = r
        r += 1
    r += 1
    CT["hdr_c"] = r
    r += 1
    for k in ["stock", "cred", "net_stock", "dp_stock", "debtors", "elig", "dp_debt", "dp", "dp_limit", "surplus",
              "dp_status", "dd_used", "dd_need"]:
        CT["rows"][k] = r
        r += 1
    r += 1
    CT["hdr_d"] = r
    r += 1
    for k in ["sales", "to_limit", "mult", "to_status"]:
        CT["rows"][k] = r
        r += 1
    r += 1
    CT["hdr_e"] = r
    r += 1
    for k in ["tl_int", "tl_pr", "tl_close", "tl_cur", "tl_after"]:
        CT["rows"][k] = r
        r += 1
    r += 1
    CT["hdr_f"] = r
    r += 1
    CT["loans"] = {}
    for ln in c.tl_l:
        CT["loans"][ln.id] = {"open": r, "repay": r + 1, "close": r + 2, "int": r + 3}
        r += 4
    for k in ["etl_repay", "etl_int"]:
        CT["rows"][k] = r
        r += 1
    r += 1
    CT["hdr_g"] = r
    r += 1
    for k in ["ul_int", "total_int"]:
        CT["rows"][k] = r
        r += 1
    r += 1
    CT["hdr_h"] = r
    r += 1
    CT["ob_rows"] = r
    nob = 2 + len(c.fa_l) + 2
    for k in ["ob_stock", "ob_cap"] + ["ob_fa:" + ln.id for ln in c.fa_l] + ["bs_diff", "cash"]:
        CT["rows"][k] = r
        r += 1
    CT["rows"]["ob_all"] = r
    r += 2
    CT["hdr_i"] = r
    r += 1
    for k in ["s_dp", "s_to", "s_dscr", "s_dscr_st", "s_ob", "s_avg", "s_avg_st"]:
        CT["rows"][k] = r
        r += 1
    CT["end"] = r
    return CT


def ctref(CT, key, i=None, absolute=True):
    if i is None:
        return "'CMA Tests'!$C$%d" % CT["rows"][key]
    return "'CMA Tests'!%s$%d" % (CT["cols"][i], CT["rows"][key]) if absolute else \
        "'CMA Tests'!%s%d" % (CT["cols"][i], CT["rows"][key])


# ======================================================================
# Profit and Loss
# ======================================================================
def _kind_prefix(y):
    return {"Audited": "", "Actual": "", "Provisional": "PROVISIONAL ", "Estimated": "ESTIMATED ", "Projected": "PROJECTED "}[y.kind]


def _note(c, y):
    t = c.it.signatory_title.lower() or "proprietor"
    if y.kind == "Audited":
        return c.s.get("audited_note") or (
            "In our opinion and to the best of our information and according to the records and explanations given "
            "to us, the accounts give a true and fair view in compliance with the accounting principles and "
            "applicable laws & regulations.")
    if y.kind == "Provisional":
        return "Provisional figures as certified by the %s; not audited." % t
    if y.kind == "Actual":
        return "Actual figures as per the books of accounts, as certified by the %s; not audited." % t
    if y.from_statement:
        return "%s figures as furnished by the %s." % (y.kind, t)
    return ("%s figures prepared on the basis of the management's assumptions set out in the Projection Basis "
            "sheet; not audited or certified." % y.kind)


def _header(ws, c, s, title, basis, src):
    if s == 1:
        put(ws, "B1", c.it.client_name, F_TITLE)
        put(ws, "B2", ("%s : %s" % ({"Proprietor": "Prop", "Partner": "Partner", "Director": "Director"}.get(
            c.it.signatory_title, c.it.signatory_title), c.it.signatory_name)) if c.it.signatory_name else "", F_HEAD)
        put(ws, "B3", c.it.address, F_HEAD)
    else:
        put(ws, "B%d" % s, "=$B$1", F_TITLE)
        put(ws, "B%d" % (s + 1), "=$B$2", F_HEAD)
        put(ws, "B%d" % (s + 2), "=$B$3", F_HEAD)
    put(ws, "B%d" % (s + 4), title, F_HEAD)
    for r in (s, s + 1, s + 2, s + 4):          # centred over the statement, as in the format
        for col in "BCDEFGHI":
            ws["%s%d" % (col, r)].alignment = Alignment(horizontal="centerContinuous")
    put(ws, "K%d" % (s + 4), "Basis: " + basis, F_NOTE)
    if src:
        put(ws, "K%d" % (s + 5), src, F_NOTE)


def _signature(ws, c, r, y):
    put(ws, "B%d" % r, _note(c, y), F_BODY, align=WRAP)
    ws.merge_cells("B%d:I%d" % (r, r + 2))
    ws.row_dimensions[r].height = 16
    put(ws, "F%d" % (r + 4), '="For "&$B$1', F_HEAD)
    put(ws, "F%d" % (r + 8), "(%s)" % c.it.signatory_name if c.it.signatory_name else "", F_BODY)
    put(ws, "B%d" % (r + 9), "Place: %s" % (c.it.place or ""), F_BODY)
    put(ws, "F%d" % (r + 9), c.it.signatory_title, F_BODY)
    put(ws, "B%d" % (r + 10), "Date:", F_BODY)


def _write_pl(ws, c, L, B, PB, CT):
    ws.sheet_view.showGridLines = False
    for col, w in zip("ABCDEFGHIJK", (2, 4, 5.3, 30, 18.4, 5.1, 26, 3, 18.7, 3, 60)):
        ws.column_dimensions[col].width = w
    for i, y in enumerate(c.years):
        s = L.start(i)
        tool = not y.from_statement
        _header(ws, c, s, "%sTRADING AND PROFIT AND LOSS ACCOUNT FOR THE YEAR ENDED 31ST MARCH %d" % (
            _kind_prefix(y), y.fy), y.kind + (" - client figures" if (y.kind not in STATEMENT_KINDS and
                                                                         y.from_statement) else ""),
                "" if tool else "Source: " + "; ".join(sorted({x.split(": ", 1)[-1] for ln in c.p.lines
                                                                for x in ln.sources if x.startswith(str(y.fy))}))[:200])
        for col, txt in (("B", "PARTICULARS"), ("E", "AMOUNT [ RS.]"), ("F", "PARTICULARS"), ("I", "AMOUNT [ RS.]")):
            put(ws, "%s%d" % (col, s + 6), txt, F_HEAD, border=B_BOTTOM)
        for col in "CDGH":
            ws["%s%d" % (col, s + 6)].border = B_BOTTOM
        sales = L.sales_cells(i)
        psales = L.sales_cells(i - 1) if i else None
        gp_row = L.row("gp_cd", i)
        np_row = L.row("np_cd", i)
        t_tot, p_tot = s + L.t_total, s + L.p_total

        def left(r, label, value, fmt=ACC, bold=False):
            put(ws, "B%d" % r, "To", F_HEAD if bold else F_BODY)
            put(ws, "C%d" % r, label, F_HEAD if bold else F_BODY)
            put(ws, "E%d" % r, value, F_HEAD if bold else F_BODY, fmt)

        def right(r, label, value, fmt=ACC, bold=False):
            put(ws, "F%d" % r, "By", F_HEAD if bold else F_BODY)
            put(ws, "G%d" % r, label, F_HEAD if bold else F_BODY)
            put(ws, "I%d" % r, value, F_HEAD if bold else F_BODY, fmt)

        def scale(cell_prev, ln):
            return '=IF(AND(%s="V",%s<>0),ROUND(%s/%s*%s,0),%s)' % (pbtype(PB, ln), psales, cell_prev, psales,
                                                                    sales, cell_prev)
        # ---- trading Dr
        for k, v in L.trading_left_items:
            key = L._key(k, v)
            r = L.row(key, i)
            if k == "s" and v == "opening_stock":
                if tool or (not c.has_val("opening_stock", y.fy) and i > 0):
                    val = "=" + L.I("closing_stock", i - 1)
                else:
                    val = c.sval("opening_stock", y.fy)
                left(r, "Opening Stock", val)
            elif k == "s" and v == "purchases":
                val = ("=ROUND(%s+%s-%s-%s-%s*%s,0)" % (
                    sales, L.I("closing_stock", i), L.E("opening_stock", i), _dsum(L, c, i), sales,
                    pbref(PB, "gp", i))) if tool else c.sval("purchases", y.fy)
                left(r, "Purchases", val)
            elif k == "l":
                val = scale(L.E(v.id, i - 1), v) if tool else v.v(y.fy)
                left(r, v.label, val)
            elif k == "gp_cd":
                first = s + L.t_first
                left(r, "Gross Profit c/d", "=I%d-SUM(E%d:E%d)" % (t_tot, first, r - 1) if r > first else
                     "=I%d" % t_tot)
        # ---- trading Cr
        for k, v in L.trading_right_items:
            key = L._key(k, v)
            r = L.row(key, i, "right")
            if k == "l":
                val = "=ROUND(%s*(1+%s),0)" % (L.I(v.id, i - 1), pbref(PB, "growth", i)) if tool else v.v(y.fy)
                right(r, v.label, val)
            else:
                if tool:
                    val = "=ROUND(%s*(1-%s)*%s/365,0)" % (sales, pbref(PB, "gp", i), pbref(PB, "stock_days", i))
                else:
                    val = c.sval("closing_stock", y.fy) if c.has_val("closing_stock", y.fy) else c.sval("stock", y.fy)
                right(r, "Closing Stock", val)
        put(ws, "E%d" % t_tot, "=SUM(E%d:E%d)" % (s + L.t_first, t_tot - 1), F_HEAD, ACC, border=B_TOPBOT)
        put(ws, "I%d" % t_tot, "=SUM(I%d:I%d)" % (s + L.t_first, t_tot - 1), F_HEAD, ACC, border=B_TOPBOT)
        if y.from_statement and y.kind in STATEMENT_KINDS:
            put(ws, "G%d" % t_tot, "(As certified by %s)" % (c.it.signatory_title.lower() or "proprietor"), F_SMALL)
        # ---- P&L Dr
        for k, v in L.pl_left_items:
            key = L._key(k, v)
            r = L.row(key, i)
            if k == "l":
                left(r, v.label, scale(L.E(v.id, i - 1), v) if tool else v.v(y.fy))
            elif v == "interest":
                left(r, SINGLE_LABEL["interest"], ("=" + ctref(CT, "total_int", i)) if tool else c.sval("interest", y.fy))
            elif v == "depreciation":
                if tool:
                    cells = ["'Balance Sheet'!H%d" % B.R("fa_b:" + ln.id, i) for ln in c.fa_l]
                    left(r, "Depreciation", "=" + ("+".join(cells) if cells else "0"))
                else:
                    left(r, "Depreciation", c.sval("depreciation", y.fy))
            elif v == "tax":
                if tool:
                    first = s + L.p_first
                    left(r, SINGLE_LABEL["tax"], "=ROUND(MAX(I%d-SUM(E%d:E%d),0)*%s,0)" % (
                        p_tot, first, r - 1, ctref(CT, "tax")))
                else:
                    left(r, SINGLE_LABEL["tax"], c.sval("tax", y.fy))
            elif k == "np_cd":
                left(r, "Net Profit c/d", "=I%d-SUM(E%d:E%d)" % (p_tot, s + L.p_first, r - 1), bold=True)
        for k, v in L.pl_right_items:
            key = L._key(k, v)
            r = L.row(key, i, "right")
            if k == "gp_bd":
                right(r, "Gross Profit b/d", "=E%d" % gp_row)
            else:
                right(r, v.label, scale(L.I(v.id, i - 1), v) if tool else v.v(y.fy))
        put(ws, "E%d" % p_tot, "=SUM(E%d:E%d)" % (s + L.p_first, p_tot - 1), F_HEAD, ACC, border=B_TOPBOT)
        put(ws, "I%d" % p_tot, "=SUM(I%d:I%d)" % (s + L.p_first, p_tot - 1), F_HEAD, ACC, border=B_TOPBOT)
        _signature(ws, c, s + L.note, y)
        if i:
            ws.row_breaks.append(Break(id=s - 1))


def _dsum(L, c, i):
    cells = [L.E(ln.id, i) for ln in c.dir_l]
    return "(" + "+".join(cells) + ")" if cells else "0"


def plx(L, key, i, side="left"):
    return "'Profit and Loss'!%s%d" % ("E" if side == "left" else "I", L.row(key, i, side))


# ======================================================================
# Balance Sheet
# ======================================================================
def _write_bs(ws, c, PL, B, PB, CT, T):
    ws.sheet_view.showGridLines = False
    for col, w in zip("ABCDEFGHIJK", (2, 30, 14, 18.9, 2.9, 30, 3, 14, 17.9, 3, 50)):
        ws.column_dimensions[col].width = w
    it = c.it
    for i, y in enumerate(c.years):
        s = B.start(i)
        tool = not y.from_statement
        _header(ws, c, s, "%sBALANCE SHEET AS ON 31ST MARCH %d" % (_kind_prefix(y), y.fy), y.kind, "")
        for col, txt in (("B", "LIABILITIES"), ("C", "[ RS.]"), ("D", "[ RS.]"), ("F", "ASSETS"), ("H", "[ RS.]"),
                         ("I", "[ RS.]")):
            put(ws, "%s%d" % (col, s + 6), txt, F_HEAD, border=B_BOTTOM)
        for r, txt in B.heads_left:
            put(ws, "B%d" % (s + r), txt, F_HEAD)
        for r, txt in B.heads_right:
            put(ws, "F%d" % (s + r), txt, F_HEAD)
        yr = c.r.years[i]
        sales = "'Profit and Loss'!" + PL.sales_cells(i).replace("(", "").replace(")", "").replace(
            "+", "+'Profit and Loss'!") if c.sales_l else "0"
        sales = "(" + sales + ")"
        psales = "('Profit and Loss'!" + PL.sales_cells(i - 1).replace("(", "").replace(")", "").replace(
            "+", "+'Profit and Loss'!") + ")" if (i and c.sales_l) else "0"

        def sh(ln, prev_ref):
            return '=IF(AND(%s="S",%s<>0),ROUND(%s/%s*%s,0),%s)' % (pbtype(PB, ln), psales, prev_ref, psales, sales,
                                                                    prev_ref)
        np_ref = "'Profit and Loss'!E%d" % PL.row("np_cd", i)
        # owners
        if c.company:
            r = B.L("share", i)
            put(ws, "B%d" % r, "Share Capital")
            put(ws, "D%d" % r, ("=D%d+%s" % (B.L("share", i - 1), pbref(PB, "intro", i))) if tool else
                c.sval("capital", y.fy), fmt=ACC)
            ob_label, np_label, drw_label = "Opening Balance", "Add: Profit for the year", "Less: Dividend"
            open_val = ("=D%d" % B.L("drw", i - 1)) if tool else yr["res_open"]
        else:
            ob_label, np_label, drw_label = "Opening Capital", "Add: Net Profit", "Less: Drawings"
            open_val = ("=D%d" % B.L("drw", i - 1)) if tool else yr["cap_open"]
            r = B.L("intro", i)
            put(ws, "B%d" % r, "Add: Capital Introduced")
            put(ws, "C%d" % r, ("=" + pbref(PB, "intro", i)) if tool else c.sval("capital_introduced", y.fy), fmt=ACC)
        put(ws, "B%d" % B.L("open", i), ob_label)
        put(ws, "C%d" % B.L("open", i), open_val, fmt=ACC)
        put(ws, "B%d" % B.L("np", i), np_label)
        put(ws, "C%d" % B.L("np", i), "=" + np_ref, fmt=ACC)
        put(ws, "C%d" % B.L("sub", i), "=SUM(C%d:C%d)" % (B.L("open", i), B.L("np", i)), fmt=ACC, border=B_TOP)
        r = B.L("drw", i)
        put(ws, "B%d" % r, drw_label)
        put(ws, "C%d" % r, ("=" + pbref(PB, "drawings", i)) if tool else c.sval("drawings", y.fy), fmt=ACC)
        put(ws, "D%d" % r, "=C%d-C%d" % (B.L("sub", i), r), fmt=ACC)
        # loans
        r = B.L("cc", i)
        put(ws, "B%d" % r, SINGLE_LABEL["cc"])
        put(ws, "D%d" % r, ("=" + ctref(CT, "cc_bal", i)) if tool else c.sval("cc", y.fy), fmt=ACC)
        for ln in c.tl_l:
            r = B.L(ln.id, i)
            put(ws, "B%d" % r, ln.label)
            put(ws, "D%d" % r, ("='CMA Tests'!%s%d" % (CT["cols"][i], CT["loans"][ln.id]["close"])) if tool else
                ln.v(y.fy), fmt=ACC)
        if it.has_tl:
            r = B.L("newtl", i)
            put(ws, "B%d" % r, SINGLE_LABEL["new_term_loan"])
            put(ws, "D%d" % r, ("=" + tlfy_ref(T, y.fy, "F")) if tool else 0, fmt=ACC)
            if tool:
                put(ws, "K%d" % r, "Linked to Term Loan sheet (outstanding at year end)", F_NOTE)
        for ln in c.ul_l:
            r = B.L(ln.id, i)
            put(ws, "B%d" % r, ln.label)
            put(ws, "D%d" % r, sh(ln, "D%d" % B.L(ln.id, i - 1)) if tool else ln.v(y.fy), fmt=ACC)
        # current liabilities
        r = B.L("cred", i)
        put(ws, "B%d" % r, SINGLE_LABEL["creditors"])
        put(ws, "C%d" % r, ("=ROUND(MAX('Profit and Loss'!E%d,0)*%s/365,0)" % (
            PL.row("purchases", i), pbref(PB, "creditor_days", i))) if tool else c.sval("creditors", y.fy), fmt=ACC)
        for ln in c.stat_l + c.ocl_l:
            r = B.L(ln.id, i)
            put(ws, "B%d" % r, ln.label)
            ov = c.p.year_input(y.fy).line_override.get(ln.id) if tool else None
            if ov is not None:
                cc_ = inp(ws, "C%d" % r, ov, ACC)
                cc_.comment = Comment("Increased to keep a positive cash and bank balance.", "InstaCMA")
            else:
                put(ws, "C%d" % r, sh(ln, "C%d" % B.L(ln.id, i - 1)) if tool else ln.v(y.fy), fmt=ACC)
        r = B.L("clsub", i)
        put(ws, "D%d" % r, "=SUM(C%d:C%d)" % (B.L("cred", i), r - 1), fmt=ACC)
        ws["C%d" % (r - 1)].border = B_BOTTOM
        # fixed assets
        for ln in c.fa_l:
            ra, rb = B.R("fa_a:" + ln.id, i), B.R("fa_b:" + ln.id, i)
            put(ws, "F%d" % ra, ln.label)
            if tool:
                prev_net = B.fa_net_cell(ln, i - 1, c.years[i - 1].from_statement)
                add = ""
                if c.capex_line is not None and ln is c.capex_line:
                    add = '+IF(AND(%s="Yes",%s="Capex",%s=%s),%s,0)' % (
                        tlref(T, "yes"), tlref(T, "use"), y.fy, ctref(CT, "start_fy"), tlref(T, "amount"))
                    put(ws, "K%d" % ra, "Includes the asset bought from the term loan in the year of purchase", F_NOTE)
                put(ws, "H%d" % ra, "=%s%s" % (prev_net, add), fmt=ACC)
                put(ws, "F%d" % rb, "Less: Depreciation")
                put(ws, "H%d" % rb, "=ROUND(H%d*'Projection Basis'!$C$%d,0)" % (ra, PB["rate"][ln.id]), fmt=ACC)
                put(ws, "I%d" % rb, "=H%d-H%d" % (ra, rb), fmt=ACC)
            elif ln.gross.get(str(y.fy)):
                g = ln.gross[str(y.fy)]
                put(ws, "H%d" % ra, g, fmt=ACC)
                put(ws, "F%d" % rb, "Less: Depreciation")
                put(ws, "H%d" % rb, "=H%d-I%d" % (ra, rb), fmt=ACC)
                put(ws, "I%d" % rb, ln.v(y.fy), fmt=ACC)
                ws["H%d" % rb].border = B_BOTTOM
            else:
                put(ws, "I%d" % ra, ln.v(y.fy), fmt=ACC)
        for ln in c.inv_l + c.la_l + c.oca_l:
            r = B.R(ln.id, i)
            put(ws, "F%d" % r, ln.label)
            ov = c.p.year_input(y.fy).line_override.get(ln.id) if tool else None
            if ov is not None:
                cc_ = inp(ws, "I%d" % r, ov, ACC)
                cc_.comment = Comment("Reduced (recovered in the year) so that cash and bank balance is not "
                                      "negative.", "InstaCMA")
            else:
                put(ws, "I%d" % r, sh(ln, "I%d" % B.R(ln.id, i - 1)) if tool else ln.v(y.fy), fmt=ACC)
        r = B.R("stock", i)
        put(ws, "F%d" % r, "Closing Stock")
        put(ws, "I%d" % r, "='Profit and Loss'!I%d" % PL.row("closing_stock", i, "right"), fmt=ACC)
        r = B.R("debt", i)
        put(ws, "F%d" % r, SINGLE_LABEL["debtors"])
        put(ws, "I%d" % r, ("=ROUND(%s*%s/365,0)" % (sales, pbref(PB, "debtor_days", i))) if tool else
            c.sval("debtors", y.fy), fmt=ACC)
        r = B.R("cash", i)
        if not tool:                 # estimated / projected: cash is part of "Cash and bank balance"
            put(ws, "F%d" % r, SINGLE_LABEL["cash_in_hand"])
            put(ws, "I%d" % r, c.sval("cash_in_hand", y.fy), fmt=ACC)
        T_ = s + B.total
        d_cells = ["D%d" % B.L("drw", i)] + (["D%d" % B.L("share", i)] if c.company else []) + \
            ["D%d" % B.L("cc", i)] + ["D%d" % B.L(ln.id, i) for ln in c.tl_l + c.ul_l] + \
            (["D%d" % B.L("newtl", i)] if it.has_tl else []) + ["D%d" % B.L("clsub", i)]
        i_other = [B.fa_net_cell(ln, i, y.from_statement) for ln in c.fa_l] + \
            ["I%d" % B.R(ln.id, i) for ln in c.inv_l + c.la_l + c.oca_l] + \
            ["I%d" % B.R("stock", i), "I%d" % B.R("debt", i)] + ([] if tool else ["I%d" % B.R("cash", i)])
        r = B.R("bank", i)
        put(ws, "F%d" % r, "Cash and bank balance" if tool else SINGLE_LABEL["bank_balance"])
        if tool:
            put(ws, "I%d" % r, "=D%d-(%s)" % (T_, "+".join(i_other)), fmt=ACC)
            put(ws, "K%d" % r, "Balancing figure", F_NOTE)
        else:
            put(ws, "I%d" % r, c.sval("bank_balance", y.fy), fmt=ACC)
        put(ws, "D%d" % T_, "=" + "+".join(d_cells), F_HEAD, ACC, border=B_TOPBOT)
        put(ws, "I%d" % T_, "=" + "+".join(i_other + ["I%d" % B.R("bank", i)]), F_HEAD, ACC, border=B_TOPBOT)
        put(ws, "K%d" % (T_ - 1), "Check: Liabilities - Assets (must be 0)", F_NOTE)
        put(ws, "K%d" % T_, "=D%d-I%d" % (T_, T_), F_NOTE, ACC)
        _signature(ws, c, s + B.note, y)
        if i:
            ws.row_breaks.append(Break(id=s - 1))


def tlfy_ref(T, fy, col):
    return "'Term Loan'!$%s$%d" % (col, T["fy_rows"][fy])


def bsx(B, key, i, col):
    return "'Balance Sheet'!%s%d" % (col, B.L(key, i) if col in "BCD" else B.R(key, i))


# ======================================================================
# CMA Tests
# ======================================================================
def _write_cma_tests(ws, c, CT, PL, B, PB, T):
    it = c.it
    sd = c.sd
    ws.sheet_view.showGridLines = False
    put(ws, "B1", "CMA WORKING TESTS - DRAWING POWER, TURNOVER, INTEREST & OB = CB CHECKS", F_HEAD)
    put(ws, "B2", "='Profit and Loss'!B1", F_GREEN)
    put(ws, "B3", "A. ASSUMPTIONS (blue = input)", F_HEAD)
    R = CT["rows"]
    rows = [("cc_yes", "Cash credit proposed (Yes / No)", "Yes" if it.has_cc else "No", "@", True),
            ("cc_base", "CC limit (Rs.) - base", it.cc_limit, ACC, True),
            ("cc_rate", "Rate of interest on CC (p.a.)", norm(it, "cc_rate", sd), PCT, True),
            ("sm", "Drawing power margin on stock", norm(it, "stock_margin", sd), PCT, True),
            ("dm", "Drawing power margin on debtors", norm(it, "debtor_margin", sd), PCT, True),
            ("deduct", "Deduct creditors from stock (Yes / No)", "Yes" if it.deduct_creditors else "No", "@", True),
            ("over90", "Debtors over 90 days excluded (%)", it.debtors_over_90_pct if it.exclude_over90 else 0, PCT, True),
            ("buffer", "Drawing power buffer over the limit", it.dp_buffer, PCT, True),
            ("to_fail", "Turnover / CC limit - fail below (times)", norm(it, "turnover_fail_below", sd), X2, True),
            ("to_pass", "Turnover / CC limit - pass from (times)", norm(it, "turnover_pass_from", sd), X2, True),
            ("dscr_min", "DSCR - minimum", norm(it, "dscr_min", sd), X2, True),
            ("dscr_max", "DSCR - maximum", norm(it, "dscr_max", sd), X2, True),
            ("dscr_drw", "Deduct drawings while calculating DSCR (Yes / No)", "Yes" if it.dscr_deduct_drawings else "No",
             "@", True),
            ("prep", "Date of preparation", it.prep_date, "dd-mm-yyyy", True),
            ("start", "CC / term loan from (1st of next month)", "=EOMONTH(C%d,0)+1" % R["prep"], "dd-mm-yyyy", False),
            ("start_fy", "Financial year (ending March) of start", "=YEAR(C%d)+IF(MONTH(C%d)>=4,1,0)" % (
                R["start"], R["start"]), "0", False),
            ("months", "Months of CC interest in the first year", "=MOD(3-MONTH(C%d),12)+1" % R["start"], "0", False),
            ("tax", "Income-tax rate charged in the P&L", tax_rate(it), PCT, True),
            ("ul_rate", "Interest rate on unsecured loans", it.unsecured_loan_rate, PCT, True)]
    for key, lab, v, f, is_in in rows:
        r = R[key]
        put(ws, "B%d" % r, lab)
        inp(ws, "C%d" % r, v, f) if is_in else put(ws, "C%d" % r, v, fmt=f)
    for key in ("cc_yes", "deduct", "dscr_drw"):
        dv = DataValidation(type="list", formula1='"Yes,No"')
        ws.add_data_validation(dv)
        dv.add("C%d" % R[key])

    def hdr(r, title):
        put(ws, "B%d" % r, title, F_HEAD)
        for i, col in CT["cols"].items():
            y = c.years[i]
            put(ws, "%s%d" % (col, r), "31.03.%d (%s)" % (y.fy, y.kind), F_HEAD, align=CENTER, border=B_BOTTOM)
    labels = {
        "fy": "Financial year ending (year)", "limit": "CC limit for the year (Rs.) - input",
        "frac": "Share of the year at the new limit", "cc_bal": "CC outstanding at year end (fully drawn)",
        "int_cc": "Interest on CC charged in the year", "int_full": "Interest on CC - full year on the limit (for DSCR)",
        "stock": "Stock-in-trade", "cred": "Less: Sundry creditors (if deducted)", "net_stock": "Paid stock",
        "dp_stock": "Drawing power on stock (after margin)", "debtors": "Sundry debtors",
        "elig": "Eligible debtors (excluding over 90 days)", "dp_debt": "Drawing power on debtors (after margin)",
        "dp": "DRAWING POWER", "dp_limit": "CC limit", "surplus": "Surplus / (shortfall) of DP over CC limit",
        "dp_status": "Test: drawing power shall exceed the CC limit", "dd_used": "Debtor days used",
        "dd_need": "Minimum debtor days for DP = limit + buffer", "sales": "Turnover (sales)",
        "to_limit": "CC limit", "mult": "Turnover / CC limit (times)", "to_status": "Turnover test (bands)",
        "tl_int": "Interest on proposed term loan", "tl_pr": "Principal repaid in the year",
        "tl_close": "Outstanding at year end", "tl_cur": "  of which due within 1 year",
        "tl_after": "  of which term liability (after 1 year)", "etl_repay": "Existing loans - total principal repaid",
        "etl_int": "Existing loans - total interest", "ul_int": "Interest on unsecured loans",
        "total_int": "TOTAL INTEREST TO PROFIT AND LOSS (Bank Interest)",
        "ob_stock": "Opening stock - previous closing stock", "ob_cap": "Opening capital - previous closing capital",
        "bs_diff": "Balance sheet: liabilities - assets", "cash": "Cash at bank (balancing figure, not negative)",
        "ob_all": "Overall result", "s_dp": "Drawing power more than CC limit", "s_to": "Turnover test",
        "s_dscr": "DSCR (times)", "s_dscr_st": "DSCR within the band", "s_ob": "OB = CB / balance sheet check",
        "s_avg": "Average DSCR (estimated and projected years)", "s_avg_st": "Average DSCR status"}
    for k, lab in labels.items():
        put(ws, "B%d" % R[k], lab, F_HEAD if k in ("dp", "total_int", "ob_all") else F_BODY)
    for ln in c.fa_l:
        put(ws, "B%d" % R["ob_fa:" + ln.id], "Opening %s - previous WDV" % ln.label)
    hdr(CT["hdr_b"], "B. CASH CREDIT - LIMIT AND INTEREST")
    hdr(CT["hdr_c"], "C. DRAWING POWER TEST")
    hdr(CT["hdr_d"], "D. TURNOVER TEST")
    hdr(CT["hdr_e"], "E. TERM LOAN (linked from Term Loan sheet)")
    hdr(CT["hdr_f"], "F. EXISTING TERM LOANS (from EMI / rate)")
    hdr(CT["hdr_g"], "G. OTHER INTEREST")
    hdr(CT["hdr_h"], "H. OB = CB CONSISTENCY CHECKS (must be 0)")
    hdr(CT["hdr_i"], "I. SUMMARY OF ALL BANK TESTS")
    for ln in c.tl_l:
        rr = CT["loans"][ln.id]
        put(ws, "B%d" % rr["open"], ln.label + " - opening", F_HEAD)
        put(ws, "B%d" % rr["repay"], "   Principal repaid (input)")
        put(ws, "B%d" % rr["close"], "   Closing balance")
        put(ws, "B%d" % rr["int"], "   Interest for the year (input)")
    for i, col in CT["cols"].items():
        y = c.years[i]
        yr = c.r.years[i]
        tool = not y.from_statement
        A = lambda k: "%s%d" % (col, R[k])   # noqa
        prev_cc = "'Balance Sheet'!D%d" % B.L("cc", i - 1)
        put(ws, A("fy"), y.fy, fmt="0")
        inp(ws, A("limit"), yr.get("cc_limit_input", 0) or 0, ACC)
        put(ws, A("frac"), '=IF($C$%d<>"Yes",0,IF(%s<$C$%d,0,IF(%s>$C$%d,1,$C$%d/12)))' % (
            R["cc_yes"], A("fy"), R["start_fy"], A("fy"), R["start_fy"], R["months"]), fmt="0.00")
        if tool:
            put(ws, A("cc_bal"), '=IF(AND($C$%d="Yes",%s>=$C$%d),%s,%s)' % (R["cc_yes"], A("fy"), R["start_fy"],
                                                                          A("limit"), prev_cc), fmt=ACC)
            put(ws, A("int_cc"), "=ROUND(%s*$C$%d*%s+%s*$C$%d*(1-%s),0)" % (
                A("limit"), R["cc_rate"], A("frac"), prev_cc, R["cc_rate"], A("frac")), fmt=ACC)
        else:
            put(ws, A("cc_bal"), "='Balance Sheet'!D%d" % B.L("cc", i), fmt=ACC)
            put(ws, A("int_cc"), "-", align=RIGHT)
        put(ws, A("int_full"), '=ROUND(IF($C$%d="Yes",%s,%s)*$C$%d,0)' % (R["cc_yes"], A("limit"), A("cc_bal"),
                                                                       R["cc_rate"]), fmt=ACC)
        # DP
        put(ws, A("stock"), "='Balance Sheet'!I%d" % B.R("stock", i), fmt=ACC)
        put(ws, A("cred"), '=IF($C$%d="Yes",\'Balance Sheet\'!C%d,0)' % (R["deduct"], B.L("cred", i)), fmt=ACC)
        put(ws, A("net_stock"), "=MAX(%s-%s,0)" % (A("stock"), A("cred")), fmt=ACC)
        put(ws, A("dp_stock"), "=%s*(1-$C$%d)" % (A("net_stock"), R["sm"]), fmt=ACC)
        put(ws, A("debtors"), "='Balance Sheet'!I%d" % B.R("debt", i), fmt=ACC)
        put(ws, A("elig"), "=%s*(1-$C$%d)" % (A("debtors"), R["over90"]), fmt=ACC)
        put(ws, A("dp_debt"), "=%s*(1-$C$%d)" % (A("elig"), R["dm"]), fmt=ACC)
        put(ws, A("dp"), "=%s+%s" % (A("dp_stock"), A("dp_debt")), F_HEAD, ACC)
        put(ws, A("dp_limit"), "=" + A("limit"), fmt=ACC)
        put(ws, A("surplus"), "=%s-%s" % (A("dp"), A("dp_limit")), fmt=ACC)
        put(ws, A("dp_status"), '=IF(OR(%s<=0,%s>%s),"PASS","FAIL")' % (A("dp_limit"), A("dp"), A("dp_limit")),
            align=CENTER)
        sales = PL.sales_cells(i, True)
        put(ws, A("dd_used"), "=IF(%s=0,0,%s/%s*365)" % (sales, A("debtors"), sales), fmt=DAYS)
        put(ws, A("dd_need"), "=IF(OR(%s<=0,%s=0),0,MAX(0,ROUNDUP((%s*(1+$C$%d)-%s)/((1-$C$%d)*(1-$C$%d))*365/%s,0)))"
            % (A("limit"), sales, A("limit"), R["buffer"], A("dp_stock"), R["over90"], R["dm"], sales), fmt=DAYS)
        put(ws, A("sales"), "=" + sales, fmt=ACC)
        put(ws, A("to_limit"), "=" + A("limit"), fmt=ACC)
        put(ws, A("mult"), '=IF(%s>0,%s/%s,"")' % (A("to_limit"), A("sales"), A("to_limit")), fmt=X2)
        put(ws, A("to_status"), '=IF(%s="","N/A",IF(%s<$C$%d,"FAIL",IF(%s<$C$%d,"AMBER","PASS")))' % (
            A("mult"), A("mult"), R["to_fail"], A("mult"), R["to_pass"]), align=CENTER)
        put(ws, A("tl_int"), "=" + tlfy_ref(T, y.fy, "D"), fmt=ACC)
        put(ws, A("tl_pr"), "=" + tlfy_ref(T, y.fy, "E"), fmt=ACC)
        put(ws, A("tl_close"), "=" + tlfy_ref(T, y.fy, "F"), fmt=ACC)
        put(ws, A("tl_cur"), "=" + tlfy_ref(T, y.fy, "G"), fmt=ACC)
        put(ws, A("tl_after"), "=%s-%s" % (A("tl_close"), A("tl_cur")), fmt=ACC)
        rep_cells, int_cells = [], []
        for ln in c.tl_l:
            rr = CT["loans"][ln.id]
            if tool:
                pr, ir = c.r.loan_sched.get(ln.id, {}).get(y.fy, (0.0, 0.0))
                put(ws, "%s%d" % (col, rr["open"]), "='Balance Sheet'!D%d" % B.L(ln.id, i - 1), fmt=ACC)
                inp(ws, "%s%d" % (col, rr["repay"]), pr, ACC)
                put(ws, "%s%d" % (col, rr["close"]), "=%s%d-MIN(%s%d,%s%d)" % (col, rr["open"], col, rr["open"], col,
                                                                              rr["repay"]), fmt=ACC)
                inp(ws, "%s%d" % (col, rr["int"]), ir, ACC)
                rep_cells.append("MIN(%s%d,%s%d)" % (col, rr["open"], col, rr["repay"]))
                int_cells.append("%s%d" % (col, rr["int"]))
            else:
                put(ws, "%s%d" % (col, rr["close"]), "='Balance Sheet'!D%d" % B.L(ln.id, i), fmt=ACC)
        put(ws, A("etl_repay"), "=" + ("+".join(rep_cells) if rep_cells else "0"), fmt=ACC)
        put(ws, A("etl_int"), "=" + ("+".join(int_cells) if int_cells else "0"), fmt=ACC)
        ul = ["'Balance Sheet'!D%d" % B.L(ln.id, i) for ln in c.ul_l]
        put(ws, A("ul_int"), ("=ROUND((%s)*$C$%d,0)" % ("+".join(ul), R["ul_rate"])) if ul else 0, fmt=ACC)
        if tool:
            put(ws, A("total_int"), "=%s+%s+%s+%s" % (A("int_cc"), A("tl_int"), A("etl_int"), A("ul_int")), F_HEAD, ACC)
        else:
            put(ws, A("total_int"), "='Profit and Loss'!E%d" % PL.row("interest", i), F_HEAD, ACC)
        # OB = CB
        put(ws, A("ob_stock"), "='Profit and Loss'!E%d-'Profit and Loss'!I%d" % (
            PL.row("opening_stock", i), PL.row("closing_stock", i - 1, "right")), fmt=ACC)
        if c.company:
            put(ws, A("ob_cap"), ("='Balance Sheet'!C%d-'Balance Sheet'!D%d" % (B.L("open", i), B.L("drw", i - 1)))
                if tool else 0, fmt=ACC)
        else:
            put(ws, A("ob_cap"), ("='Balance Sheet'!C%d-'Balance Sheet'!D%d" % (B.L("open", i), B.L("drw", i - 1)))
                if tool else 0, fmt=ACC)
        for ln in c.fa_l:
            if tool:
                add = ""
                if c.capex_line is not None and ln is c.capex_line:
                    add = '-IF(AND(%s="Yes",%s="Capex",%s=$C$%d),%s,0)' % (
                        tlref(T, "yes"), tlref(T, "use"), y.fy, R["start_fy"], tlref(T, "amount"))
                put(ws, A("ob_fa:" + ln.id), "='Balance Sheet'!H%d%s-'Balance Sheet'!%s" % (
                    B.R("fa_a:" + ln.id, i), add, B.fa_net_cell(ln, i - 1, c.years[i - 1].from_statement)), fmt=ACC)
            else:
                put(ws, A("ob_fa:" + ln.id), 0, fmt=ACC)
        put(ws, A("bs_diff"), "='Balance Sheet'!K%d" % (B.start(i) + B.total), fmt=ACC)
        put(ws, A("cash"), "='Balance Sheet'!I%d" % B.R("bank", i), fmt=ACC)
        chk = [A(k) for k in ["ob_stock", "ob_cap", "bs_diff"] + ["ob_fa:" + ln.id for ln in c.fa_l]]
        put(ws, A("ob_all"), '=IF(AND(%s,%s>=0),"PASS","FAIL")' % (",".join("ABS(%s)<1" % x for x in chk), A("cash")),
            F_HEAD, align=CENTER)
        put(ws, A("s_dp"), "=" + A("dp_status"), align=CENTER)
        put(ws, A("s_to"), "=" + A("to_status"), align=CENTER)
        put(ws, A("s_dscr"), "=DSCR!%s%d" % (col, 18), fmt="0.00")
        put(ws, A("s_dscr_st"), "=DSCR!%s%d" % (col, 22), align=CENTER)
        put(ws, A("s_ob"), "=" + A("ob_all"), align=CENTER)
    if CT["cols"]:
        first = list(CT["cols"].values())[0]
        put(ws, "%s%d" % (first, R["s_avg"]), "=DSCR!C24", fmt="0.00")
        put(ws, "%s%d" % (first, R["s_avg_st"]), "=DSCR!C25", align=CENTER)
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 50
    for j in range(len(CT["cols"]) + 1):
        ws.column_dimensions[CL(3 + j)].width = 16


# ======================================================================
# DSCR
# ======================================================================
def _write_dscr(ws, c, CT, PL, B):
    ws.sheet_view.showGridLines = False
    put(ws, "B1", "DEBT SERVICE COVERAGE RATIO (DSCR)", F_HEAD)
    put(ws, "B2", "='Profit and Loss'!B1", F_GREEN)
    put(ws, "B3", "Drawings deducted?  ='CMA Tests' C%d  (Yes / No - default No, as banks do)" % CT["rows"]["dscr_drw"],
        F_SMALL)
    put(ws, "B4", "Particulars", F_HEAD, border=B_BOTTOM)
    labels = {5: "Net Profit after tax", 6: "Add: Depreciation", 7: "Add: Interest charged in the year",
              8: "Gross cash accruals", 9: "Less: Drawings / dividend", 10: "Net cash accruals (after drawings)",
              11: "Cash accruals used for DSCR (as per the switch)",
              13: "Interest on CC - full year on the limit", 14: "Interest on proposed term loan",
              15: "Principal repayment of proposed term loan", 16: "Interest and principal of existing loans",
              17: "Total debt service", 18: "DSCR", 19: "Memo: DSCR on the other basis", 20: "Required minimum",
              21: "Required maximum", 22: "Status", 24: "AVERAGE DSCR", 25: "Average DSCR status"}
    for r, lab in labels.items():
        put(ws, "B%d" % r, lab, F_HEAD if r in (8, 11, 17, 18, 24) else F_BODY)
    sw = "'CMA Tests'!$C$%d" % CT["rows"]["dscr_drw"]
    put(ws, "B3", '="Drawings deducted in the main DSCR: "&%s&"  (change on CMA Tests)"' % sw, F_SMALL)
    cols = []
    for i, col in CT["cols"].items():
        y = c.years[i]
        cols.append(col)
        put(ws, "%s4" % col, "FY %s (%s)" % (y.label, y.kind), F_HEAD, border=B_BOTTOM, align=CENTER)
        P = lambda k, side="left": "'Profit and Loss'!%s%d" % ("E" if side == "left" else "I", PL.row(k, i, side))  # noqa
        put(ws, "%s5" % col, "=" + P("np_cd"), fmt=ACC)
        put(ws, "%s6" % col, "=" + P("depreciation"), fmt=ACC)
        put(ws, "%s7" % col, "=" + P("interest"), fmt=ACC)
        put(ws, "%s8" % col, "=SUM(%s5:%s7)" % (col, col), F_HEAD, ACC, border=B_TOP)
        put(ws, "%s9" % col, "='Balance Sheet'!C%d" % B.L("drw", i), fmt=ACC)
        put(ws, "%s10" % col, "=%s8-%s9" % (col, col), fmt=ACC)
        put(ws, "%s11" % col, '=IF(%s="Yes",%s10,%s8)' % (sw, col, col), F_HEAD, ACC)
        ct = lambda k: "'CMA Tests'!%s%d" % (col, CT["rows"][k])   # noqa
        put(ws, "%s13" % col, "=" + ct("int_full"), fmt=ACC)
        put(ws, "%s14" % col, "=" + ct("tl_int"), fmt=ACC)
        put(ws, "%s15" % col, "=" + ct("tl_pr"), fmt=ACC)
        put(ws, "%s16" % col, "=%s+%s+%s" % (ct("etl_repay"), ct("etl_int"), ct("ul_int")), fmt=ACC)
        put(ws, "%s17" % col, "=SUM(%s13:%s16)" % (col, col), F_HEAD, ACC, border=B_TOP)
        put(ws, "%s18" % col, '=IF(%s17=0,"n/a",%s11/%s17)' % (col, col, col), F_HEAD, "0.00")
        put(ws, "%s19" % col, '=IF(%s17=0,"n/a",IF(%s="Yes",%s8,%s10)/%s17)' % (col, sw, col, col, col), F_SMALL, "0.00")
        put(ws, "%s20" % col, "='CMA Tests'!$C$%d" % CT["rows"]["dscr_min"], fmt="0.00")
        put(ws, "%s21" % col, "='CMA Tests'!$C$%d" % CT["rows"]["dscr_max"], fmt="0.00")
        put(ws, "%s22" % col, '=IF(%s18="n/a","N/A",IF(%s18<%s20,"FAIL",IF(%s18>%s21,"AMBER","PASS")))' % (
            col, col, col, col, col), align=CENTER)
    if cols:
        rng = "%s18:%s18" % (cols[0], cols[-1])
        put(ws, "C24", '=IFERROR(AVERAGE(%s),"n/a")' % rng, F_HEAD, "0.00")
        put(ws, "C25", '=IF(C24="n/a","N/A",IF(OR(C24<%s20,MIN(%s)<%s20),"FAIL",IF(OR(C24>%s21,MAX(%s)>%s21),"AMBER","PASS")))'
            % (cols[0], rng, cols[0], cols[0], rng, cols[0]), align=CENTER)
    put(ws, "B27", "Debt service = CC interest on the full limit + term-loan interest and principal + existing loans "
                   "+ interest on unsecured loans.", F_SMALL)
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 50
    for j in range(len(cols) + 1):
        ws.column_dimensions[CL(3 + j)].width = 18


# ======================================================================
# FORM-II / FORM-III links, unit drop-down, year headers
# ======================================================================
def _write_format_links(wb, c, PL, B, CT):
    f2, f3 = wb["FORM-II"], wb["FORM-III"]
    f2["C4"] = "='Profit and Loss'!B1"
    f2["F6"] = "Amounts in Rs."
    f2["G6"] = {"Actual": "Actual", "'000": "Thousand", "Thousand": "Thousand", "Lakh": "Lakh",
                "Crore": "Crore"}.get(c.it.unit, "Actual")
    dv = DataValidation(type="list", formula1='"Actual,Thousand,Lakh,Crore"', allow_blank=False)
    f2.add_data_validation(dv)
    dv.add("G6")
    f2["P5"] = "Unit divisor"
    f2["P6"] = '=IF(G6="Thousand",1000,IF(G6="Lakh",100000,IF(G6="Crore",10000000,1)))'
    f2.column_dimensions["P"].hidden = True
    P = lambda key, i, side="left": "'Profit and Loss'!%s%d" % ("E" if side == "left" else "I", PL.row(key, i, side))  # noqa
    Bs = lambda col, key, i: "'Balance Sheet'!%s%d" % (col, B.L(key, i) if col in "CD" else B.R(key, i))  # noqa

    def lsum(lines, i, col_of):
        cells = [col_of(ln) for ln in lines]
        return "+".join(cells) if cells else "0"

    def plcell(ln, i):
        return "'Profit and Loss'!%s" % (PL.E(ln.id, i) if ln.id in PL.left else PL.I(ln.id, i))

    def w(ws, ref, expr):
        ws[ref] = "=ROUND((%s)/%s,2)" % (expr, U)

    for i, y in enumerate(c.years):
        col = YC[i]
        f2["%s8" % col] = y.kind
        f2["%s9" % col] = y.label
        f2["%s10" % col] = 12
        exp = c.dir_l + c.ind_l
        w(f2, "%s12" % col, lsum(c.sales_l, i, lambda ln: plcell(ln, i)))
        w(f2, "%s24" % col, P("purchases", i))
        w(f2, "%s28" % col, lsum([ln for ln in exp if ln.head == "power_fuel"], i, lambda ln: plcell(ln, i)))
        w(f2, "%s29" % col, lsum([ln for ln in exp if ln.head == "wages"], i, lambda ln: plcell(ln, i)))
        w(f2, "%s30" % col, lsum([ln for ln in exp if ln.head == "other_direct"], i, lambda ln: plcell(ln, i)))
        w(f2, "%s31" % col, P("depreciation", i))
        if i == 0:
            w(f2, "E38", P("opening_stock", 0))
        w(f2, "%s40" % col, P("closing_stock", i, "right"))
        w(f2, "%s43" % col, lsum([ln for ln in exp if ln.head in INDIRECT], i, lambda ln: plcell(ln, i)))
        w(f2, "%s46" % col, P("interest", i))
        w(f2, "%s51" % col, lsum(c.oi_l, i, lambda ln: plcell(ln, i)))
        if c.include_tax:
            w(f2, "%s64" % col, P("tax", i))
        if c.company:
            w(f2, "%s68" % col, Bs("C", "drw", i))
        # FORM-III
        w(f3, "%s15" % col, Bs("D", "cc", i))
        w(f3, "%s20" % col, Bs("C", "cred", i))
        w(f3, "%s25" % col, lsum(c.stat_l, i, lambda ln: Bs("C", ln.id, i)))
        w(f3, "%s32" % col, lsum(c.ocl_l, i, lambda ln: Bs("C", ln.id, i)))
        if not y.from_statement or y.kind not in STATEMENT_KINDS:
            cur = "'CMA Tests'!%s%d" % (CT["cols"][i], CT["rows"]["tl_cur"])
            nxt = ""
            if i + 1 < c.n and (i + 1) in CT["cols"] and not c.years[i + 1].from_statement:
                nxt = "+" + "'CMA Tests'!%s%d" % (CT["cols"][i + 1], CT["rows"]["etl_repay"])
            w(f3, "%s27" % col, cur + nxt)
        else:
            f3["%s27" % col] = None
        tl_cells = [Bs("D", ln.id, i) for ln in c.tl_l] + ([Bs("D", "newtl", i)] if c.it.has_tl else [])
        f3["%s41" % col] = "=ROUND((%s)/%s,2)-%s27" % ("+".join(tl_cells) if tl_cells else "0", U, col)
        w(f3, "%s45" % col, lsum(c.ul_l, i, lambda ln: Bs("D", ln.id, i)))
        own = Bs("D", "drw", i) + (("+" + Bs("D", "share", i)) if c.company else "")
        np_ = P("np_cd", i)
        drw = Bs("C", "drw", i)
        if i == 0:
            if c.company:
                opening = "(%s+%s)" % (Bs("C", "open", 0), Bs("D", "share", 0))
            else:
                opening = Bs("C", "open", 0)
            w(f3, "E50", opening)
            prev_own = opening
        else:
            pown = Bs("D", "drw", i - 1) + (("+" + Bs("D", "share", i - 1)) if c.company else "")
            prev_own = "(%s)" % pown
        f3["%s58" % col] = "=ROUND((%s)/%s,2)-ROUND((%s)/%s,2)-%s54-%s59" % (own, U, prev_own, U, col, col)
        f3["%s58" % col].number_format = "#,##0.00,"
        w(f3, "%s59" % col, "-" + drw)
        w(f3, "%s81" % col, "%s+%s" % (Bs("I", "bank", i), Bs("I", "cash", i)))
        w(f3, "%s87" % col, Bs("I", "debt", i))
        w(f3, "%s105" % col, lsum([ln for ln in c.oca_l if is_tax_receivable(ln.label)], i, lambda ln: Bs("I", ln.id, i)))
        w(f3, "%s109" % col, lsum([ln for ln in c.oca_l if not is_tax_receivable(ln.label) and is_gst_receivable(ln.label)],
                                   i, lambda ln: Bs("I", ln.id, i)))
        w(f3, "%s110" % col, lsum([ln for ln in c.oca_l if not is_tax_receivable(ln.label) and
                                   not is_gst_receivable(ln.label)], i, lambda ln: Bs("I", ln.id, i)))
        w(f3, "%s108" % col, lsum([ln for ln in c.la_l if not is_deposit(ln.label)], i, lambda ln: Bs("I", ln.id, i)))
        w(f3, "%s130" % col, lsum([ln for ln in c.la_l if is_deposit(ln.label)], i, lambda ln: Bs("I", ln.id, i)))
        w(f3, "%s124" % col, lsum(c.inv_l, i, lambda ln: Bs("I", ln.id, i)))
        net = "+".join("'Balance Sheet'!" + B.fa_net_cell(ln, i, y.from_statement) for ln in c.fa_l) or "0"
        if i == 0:
            w(f3, "E116", P("depreciation", 0))
        else:
            f3["%s116" % col] = "=%s116+'FORM-II'!%s31" % (YC[i - 1], col)
        f3["%s115" % col] = "=ROUND((%s)/%s,2)+%s116" % (net, U, col)
    # FORM-III 58 label (others = capital introduced / adjustments)
    if f3["D58"].value in (None, ""):
        f3["D58"] = "Capital introduced / adjustments"
    _unit_formats(wb)
    _hide_unused_columns(wb, c.n)
    _hide_errors(wb)


def _unit_formats(wb):
    """'#,##0.00,' (thousands) -> '#,##0.00' (values are already divided); whole rupees when unit = Actual."""
    ids = {}                     # one id per format code across the workbook (Excel rejects duplicates)
    # Excel does not accept a direct reference to another sheet in conditional formatting: use a name
    from openpyxl.workbook.defined_name import DefinedName
    if "CMA_UNIT" not in wb.defined_names:
        wb.defined_names["CMA_UNIT"] = DefinedName("CMA_UNIT", attr_text="'FORM-II'!$G$6")
    for name in FORMAT_SHEETS:
        ws = wb[name]
        groups = {}
        for row in ws.iter_rows():
            for cell in row:
                f = cell.number_format
                if "0.00," in f:
                    nf = f.replace("0.00,", "0.00")
                    cell.number_format = nf
                    groups.setdefault(nf.replace("0.00", "0"), []).append(cell.coordinate)
        for fmt0, cells in sorted(groups.items()):
            rng = " ".join(cells)
            fid = ids.setdefault(fmt0, 300 + len(ids))
            dxf = DifferentialStyle(numFmt=NumberFormat(numFmtId=fid, formatCode=fmt0))
            rule = Rule(type="expression", dxf=dxf, formula=['CMA_UNIT="Actual"'])
            ws.conditional_formatting.add(rng, rule)


def _hide_unused_columns(wb, n):
    """Hide year columns beyond the client's years in every bank format sheet."""
    import re
    from reports.page_setup import ungroup_columns
    for name in FORMAT_SHEETS:
        ungroup_columns(wb[name])
    used = set(YC[:n])
    f2 = wb["FORM-II"]
    for col in YC[n:]:
        f2.column_dimensions[col].hidden = True
    pat = re.compile(r"'?FORM-I{1,3}'?!\$?([E-N])\$?(8|9|10)\b")
    for name in FORMAT_SHEETS:
        if name == "FORM-II":
            continue
        ws = wb[name]
        mapped = {}
        for row in ws.iter_rows(min_row=1, max_row=14):
            for cell in row:
                v = cell.value
                if isinstance(v, str):
                    m = pat.search(v)
                    if m and cell.column_letter not in mapped:
                        mapped[cell.column_letter] = m.group(1)
        for col, src in mapped.items():
            if src not in used:
                ws.column_dimensions[col].hidden = True


def _hide_errors(wb):
    """Format formulas that divide by a zero (unused items) print blank instead of #DIV/0!."""
    white = DifferentialStyle(font=Font(color="FFFFFF"), fill=PatternFill("solid", fgColor="FFFFFF",
                                                                          bgColor="FFFFFF"))
    for name in FORMAT_SHEETS:
        ws = wb[name]
        rng = "A1:%s%d" % (CL(max(ws.max_column, 1)), max(ws.max_row, 1))
        ws.conditional_formatting.add(rng, Rule(type="expression", dxf=white, formula=["ISERROR(A1)"]))
