"""
InstaCMA - line-level calculation engine.

Works on the client's own ledger lines.  Statement years (Audited,
Provisional, or client-supplied projections) are taken as given; tool years
(Estimated / Projected) are built with the CMA rules below.  The Excel writer
writes exactly the same rules as formulas, and the tests recalculate the
workbook and compare it with this engine figure by figure.

  Sales line        = previous x (1 + growth)
  Other P&L lines   = V: previous ratio to sales x sales | F: previous amount
  Closing stock     = sales x (1 - previous GP%) x stock days / 365
  Purchases         = sales + closing - opening - direct expenses - sales x previous GP%
  Creditors         = purchases x creditor days / 365
  Debtors           = sales x debtor days / 365 (days solved for drawing power)
  Fixed assets      = (previous WDV + capex) less WDV depreciation, line by line
  Interest          = CC + proposed term loan + existing loans + unsecured loans
  Capital           = opening + introduced + net profit - drawings / dividend
  Cash at bank      = balancing figure
"""
import datetime as dt
import math
from dataclasses import dataclass, field
from typing import Dict, List

from analysis.rounding import xround, safe_div
from analysis import term_loan_engine as tle
from analysis.layout import DIRECT, INDIRECT, EXPENSE_HEADS, basis_of, rate_of, section_of
from config.constants import FA_KEYS
from core.models import (Line, fy_label, fy_end_of, norm, tax_rate, STATEMENT_KINDS)

PASS, AMBER, FAIL = "PASS", "AMBER", "FAIL"


@dataclass
class Result:
    years: List[Dict] = field(default_factory=list)
    tl_schedule: Dict = field(default_factory=dict)
    tl_fy: Dict = field(default_factory=dict)
    loan_sched: Dict = field(default_factory=dict)       # {line_id: {fy: (principal, interest)}}
    warnings: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    summary: Dict = field(default_factory=dict)

    def year(self, fy):
        for y in self.years:
            if y["fy"] == fy:
                return y
        return None

    @property
    def future(self):
        return [y for y in self.years if y["kind"] not in STATEMENT_KINDS]

    @property
    def statement(self):
        return [y for y in self.years if y["from_statement"]]


def _sum(y, lines):
    return sum(y["lines"].get(ln.id, 0.0) for ln in lines)


def ensure_capex_line(project):
    """A fixed-asset line must exist for the term-loan capex class."""
    it = project.intake
    if not (it.has_tl and it.tl_use == "Capex" and it.tl_amount > 0):
        return None
    for ln in project.lines:
        if ln.head == it.tl_capex_class:
            return ln
    from analysis.layout import head_label
    ln = Line(statement="BS", head=it.tl_capex_class,
              label=head_label(it.tl_capex_class).replace(" (WDV)", "") + " (proposed)")
    project.lines.append(ln)
    return ln


def ensure_loans(project):
    from core.models import ExistingLoan
    have = {l.line_id for l in project.loans}
    for ln in project.lines_of("term_loans"):
        if ln.id not in have:
            project.loans.append(ExistingLoan(line_id=ln.id, lender=ln.label))
    ids = {ln.id for ln in project.lines_of("term_loans")}
    project.loans = [l for l in project.loans if l.line_id in ids]


def existing_loan_schedule(loan, opening, fys):
    """Yearly (principal, interest) for an existing loan from its EMI, rate and end date."""
    out = {}
    bal = opening
    end = None
    if loan.end_date:
        try:
            end = dt.date.fromisoformat(str(loan.end_date)[:10])
        except ValueError:
            end = None
    for fy in fys:
        pr_y = it_y = 0.0
        for m in range(12):
            month = dt.date(fy - 1 + (1 if m >= 9 else 0), (m + 3) % 12 + 1, 1)
            if bal <= 0:
                break
            if end and month > end:
                pr_y += bal
                bal = 0
                break
            intr = bal * loan.rate / 12
            if loan.emi > 0:
                pr = min(bal, max(loan.emi - intr, 0))
            else:
                pr = 0
            it_y += intr
            pr_y += pr
            bal -= pr
        pr_y = xround(pr_y)
        if str(fy) in loan.repay_override:
            pr_y = float(loan.repay_override[str(fy)])
        out[fy] = (pr_y, xround(it_y))
        bal = opening - sum(v[0] for v in out.values())
    return out


# ======================================================================
def compute(project, settings_defaults=None, shock=None):
    it = project.intake
    sd = settings_defaults or {}
    res = Result()
    years = project.year_list()
    if not years:
        res.warnings.append("No years defined.")
        return res
    ensure_capex_line(project)
    ensure_loans(project)
    lines = project.lines
    L = lambda *h: [ln for ln in lines if ln.head in h]   # noqa: E731
    sales_l, oi_l = L("sales"), L("other_income")
    exp_l = L(*EXPENSE_HEADS)
    dir_l = [ln for ln in exp_l if section_of(ln) == "trading"]
    ind_l = [ln for ln in exp_l if section_of(ln) == "pl"]
    fa_l = [ln for ln in lines if ln.head in FA_KEYS]
    tl_l, ul_l = L("term_loans"), L("unsecured_loans")
    stat_l, ocl_l = L("statutory_dues"), L("other_cl")
    inv_l, la_l, oca_l = L("investments"), L("loans_advances"), L("other_ca")
    single = {h: L(h) for h in ("opening_stock", "purchases", "closing_stock", "interest", "depreciation", "tax",
                                 "capital", "reserves", "drawings", "capital_introduced", "cc", "creditors",
                                 "stock", "debtors", "cash_in_hand", "bank_balance")}
    company = it.is_company
    sm = norm(it, "stock_margin", sd)
    dm = norm(it, "debtor_margin", sd)
    cc_rate = norm(it, "cc_rate", sd)
    tl_rate = norm(it, "tl_rate", sd)
    dmin, dmax = norm(it, "dscr_min", sd), norm(it, "dscr_max", sd)
    to_fail, to_pass = norm(it, "turnover_fail_below", sd), norm(it, "turnover_pass_from", sd)
    g_default = norm(it, "default_growth", sd)
    trate = tax_rate(it)
    start_fy = fy_end_of(it.facility_start)
    over90 = it.debtors_over_90_pct if it.exclude_over90 else 0.0

    # term loan
    tl_amt = it.tl_amount if it.has_tl else 0.0
    sch = tle.build_schedule(tl_amt, tl_rate, it.tl_tenure_months if tl_amt else 0,
                             it.tl_moratorium_months if tl_amt else 0, it.tl_method, it.facility_start)
    fys = [y.fy for y in years]
    res.tl_schedule = sch
    res.tl_fy = tle.fy_summary(sch, fys + [fys[-1] + 1], tl_amt)
    res.summary["tl_amount"] = tl_amt

    prev = None
    first_tool_done = False
    base_days = {}
    last_stmt = None
    for yd in years:
        y = {"fy": yd.fy, "label": yd.label, "kind": yd.kind, "from_statement": yd.from_statement,
             "lines": {}, "fa": {}}
        if yd.from_statement:
            for ln in lines:
                y["lines"][ln.id] = ln.v(yd.fy)
            g = lambda h: sum(ln.v(yd.fy) for ln in single[h])   # noqa: E731
            y["sales"] = _sum(y, sales_l)
            y["other_income"] = _sum(y, oi_l)
            if any(str(yd.fy) in ln.values for ln in single["opening_stock"]) or prev is None:
                y["opening_stock"] = g("opening_stock")
            else:
                y["opening_stock"] = prev["closing_stock"]
            y["purchases"] = g("purchases")
            y["direct_total"] = _sum(y, dir_l)
            cs = g("closing_stock") if any(str(yd.fy) in ln.values for ln in single["closing_stock"]) else g("stock")
            y["closing_stock"] = cs
            y["indirect_total"] = _sum(y, ind_l)
            y["interest"] = g("interest")
            y["depreciation"] = g("depreciation")
            y["tax"] = g("tax")
            for ln in fa_l:
                y["fa"][ln.id] = (None, 0.0, None, ln.v(yd.fy))
            y["cc"] = g("cc")
            y["creditors"] = g("creditors")
            y["debtors"] = g("debtors")
            y["cash_in_hand"] = g("cash_in_hand")
            y["bank_balance"] = g("bank_balance")
            y["new_tl"] = 0.0
            y["drawings"] = g("drawings")
            y["capital_introduced"] = g("capital_introduced")
            _profit(y)
            if company:
                y["share_capital"] = g("capital")
                y["res_close"] = g("reserves")
                y["res_open"] = y["res_close"] - y["pat"] + y["drawings"]
                y["cap_open"] = y["cap_close"] = None
            else:
                y["cap_close"] = g("capital") + g("reserves")
                y["cap_open"] = y["cap_close"] - y["pat"] - y["capital_introduced"] + y["drawings"]
            y["int_cc"] = y["int_cc_full"] = y["int_tl"] = y["int_etl"] = y["int_ul"] = 0.0
            y["tl_principal"] = y["etl_repay"] = y["tl_curmat"] = 0.0
            if yd.kind not in STATEMENT_KINDS:      # client-supplied projections
                t = res.tl_fy.get(yd.fy, {})
                y["int_tl"], y["tl_principal"] = t.get("interest", 0.0), t.get("principal", 0.0)
                y["tl_curmat"] = t.get("next_principal", 0.0)
                limit = (project.year_input(yd.fy).cc_limit or it.cc_limit) if it.has_cc else y["cc"]
                y["cc_limit_input"] = limit
                y["int_cc_full"] = xround(limit * cc_rate)
            last_stmt = y if yd.kind in STATEMENT_KINDS else last_stmt
        else:
            if prev is None:
                res.warnings.append("The first year cannot be an estimated / projected year built by the tool.")
                return res
            if not first_tool_done:
                base_days = _base_days(prev, it)
                res.summary["base_days"] = base_days
                first_tool_done = True
            yi = project.year_input(yd.fy)
            gr = yi.growth if yi.growth is not None else g_default
            y["growth"] = gr
            ps = prev["sales"]
            for ln in sales_l:
                v = xround(prev["lines"].get(ln.id, 0.0) * (1 + gr))
                y["lines"][ln.id] = v
            y["sales"] = _sum(y, sales_l)
            if shock and shock.get("sales_factor"):
                for ln in sales_l:
                    y["lines"][ln.id] = xround(y["lines"][ln.id] * shock["sales_factor"])
                y["sales"] = _sum(y, sales_l)
            s = y["sales"]
            for ln in oi_l + dir_l + ind_l:
                pv = prev["lines"].get(ln.id, 0.0)
                y["lines"][ln.id] = xround(pv / ps * s) if (basis_of(ln) == "V" and ps) else pv
            y["other_income"] = _sum(y, oi_l)
            y["direct_total"] = _sum(y, dir_l)
            y["indirect_total"] = _sum(y, ind_l)
            gp_prev = safe_div(prev["gross_profit"], ps)
            y["gp_override"] = yi.gp_pct is not None
            if yi.gp_pct is not None:
                gp_prev = yi.gp_pct
            if shock and shock.get("cost_factor"):
                gp_prev = 1 - (1 - gp_prev) * shock["cost_factor"]
            y["gp_ratio_used"] = gp_prev
            y["opening_stock"] = prev["closing_stock"]
            y["stock_days"] = yi.stock_days if yi.stock_days is not None else base_days["stock"]
            y["closing_stock"] = xround(s * (1 - gp_prev) * y["stock_days"] / 365)
            y["purchases"] = xround(s + y["closing_stock"] - y["opening_stock"] - y["direct_total"] - s * gp_prev)
            if y["purchases"] < 0:
                res.warnings.append("%s: purchases work out negative; reduce stock days." % y["label"])
            y["creditor_days"] = yi.creditor_days if yi.creditor_days is not None else base_days["creditor"]
            y["creditors"] = xround(max(y["purchases"], 0) * y["creditor_days"] / 365)
            # fixed assets
            dep = 0
            for ln in fa_l:
                op = prev["fa"].get(ln.id, (None, 0, None, 0.0))[3]
                add = tl_amt if (it.has_tl and it.tl_use == "Capex" and ln.head == it.tl_capex_class
                                 and yd.fy == start_fy and ln is _capex_line(project)) else 0.0
                d = xround((op + add) * rate_of(ln))
                y["fa"][ln.id] = (op, add, d, op + add - d)
                dep += d
            y["depreciation"] = dep
            # borrowings
            f = _fraction(yd.fy, it)
            y["cc_fraction"] = f
            limit = (yi.cc_limit if yi.cc_limit is not None else it.cc_limit) if it.has_cc else 0.0
            y["cc_limit_input"] = limit
            y["cc"] = limit if (it.has_cc and yd.fy >= start_fy) else prev["cc"]
            y["int_cc"] = xround(limit * cc_rate * f + prev["cc"] * cc_rate * (1 - f))
            y["int_cc_full"] = xround((limit if it.has_cc else y["cc"]) * cc_rate)
            t = res.tl_fy.get(yd.fy, {})
            y["new_tl"] = t.get("closing", 0.0)
            y["int_tl"] = t.get("interest", 0.0)
            y["tl_principal"] = t.get("principal", 0.0)
            y["tl_curmat"] = t.get("next_principal", 0.0)
            etl_rep = etl_int = 0.0
            for ln in tl_l:
                loan = next((l for l in project.loans if l.line_id == ln.id), None)
                op = prev["lines"].get(ln.id, 0.0)
                if ln.id not in res.loan_sched:
                    tool_fys = [x.fy for x in years if not x.from_statement and x.fy >= yd.fy]
                    res.loan_sched[ln.id] = existing_loan_schedule(loan, op, tool_fys) if loan else {}
                pr, ir = res.loan_sched[ln.id].get(yd.fy, (0.0, 0.0))
                pr = min(pr, op)
                y["lines"][ln.id] = op - pr
                etl_rep += pr
                etl_int += ir
            y["etl_repay"], y["int_etl"] = etl_rep, etl_int
            for ln in ul_l + stat_l + ocl_l + inv_l + la_l + oca_l:
                pv = prev["lines"].get(ln.id, 0.0)
                y["lines"][ln.id] = xround(pv / ps * s) if (basis_of(ln) == "S" and ps) else pv
                if ln.id in yi.line_override:
                    y["lines"][ln.id] = float(yi.line_override[ln.id])
            y["int_ul"] = xround(_sum(y, ul_l) * it.unsecured_loan_rate)
            y["interest"] = y["int_cc"] + y["int_tl"] + y["int_etl"] + y["int_ul"]
            pbt = s + y["closing_stock"] - y["opening_stock"] - y["purchases"] - y["direct_total"] \
                + y["other_income"] - y["indirect_total"] - y["interest"] - y["depreciation"]
            y["tax"] = xround(max(pbt, 0) * trate)
            _profit(y)
            # owners
            y["drawings"] = yi.drawings if yi.drawings is not None else (last_stmt or prev).get("drawings", 0.0)
            y["capital_introduced"] = yi.capital_introduced or 0.0
            if company:
                y["share_capital"] = prev["share_capital"] + y["capital_introduced"]
                y["res_open"] = prev["res_close"]
                y["res_close"] = y["res_open"] + y["pat"] - y["drawings"]
                y["cap_open"] = y["cap_close"] = None
            else:
                y["cap_open"] = prev["cap_close"]
                y["cap_close"] = y["cap_open"] + y["capital_introduced"] + y["pat"] - y["drawings"]
            y["cash_in_hand"] = 0.0      # estimated / projected: one line "Cash and bank balance" (balancing)
            # debtors - solve for drawing power
            if yi.debtor_days is not None:
                days, auto = yi.debtor_days, False
            else:
                auto = True
                days = base_days["debtor"]
                if it.has_cc and limit > 0 and s > 0:
                    stock_part = max(y["closing_stock"] - (y["creditors"] if it.deduct_creditors else 0), 0) * (1 - sm)
                    need = limit * (1 + it.dp_buffer) - stock_part
                    fac = (1 - over90) * (1 - dm)
                    nd = math.ceil((need / fac) * 365 / s - 1e-9) if (need > 0 and fac > 0) else 0
                    y["dp_min_days"] = nd
                    days = max(days, nd)
                    if days > it.debtor_days_cap:
                        needed = days
                        days = int(it.debtor_days_cap)
                        raised = False
                        if it.auto_raise_stock and yi.stock_days is None:
                            sd0 = y["stock_days"]
                            sd = sd0
                            target = limit * (1 + it.dp_buffer)
                            while sd < it.stock_days_cap:
                                sd += 1
                                cl = xround(s * (1 - gp_prev) * sd / 365)
                                pu = xround(s + cl - y["opening_stock"] - y["direct_total"] - s * gp_prev)
                                cr = xround(max(pu, 0) * y["creditor_days"] / 365)
                                deb = xround(s * days / 365)
                                dp_ = max(cl - (cr if it.deduct_creditors else 0), 0) * (1 - sm) + \
                                    deb * (1 - over90) * (1 - dm)
                                if dp_ >= target:
                                    y["stock_days"], y["closing_stock"], y["purchases"] = sd, cl, pu
                                    y["creditors"], y["stock"] = cr, cl
                                    y["stock_days_raised"] = sd0
                                    raised = True
                                    break
                            if raised:
                                pbt = s + y["closing_stock"] - y["opening_stock"] - y["purchases"] - \
                                    y["direct_total"] + y["other_income"] - y["indirect_total"] - y["interest"] - \
                                    y["depreciation"]
                                y["tax"] = xround(max(pbt, 0) * trate)
                                _profit(y)
                                if company:
                                    y["res_close"] = y["res_open"] + y["pat"] - y["drawings"]
                                else:
                                    y["cap_close"] = y["cap_open"] + y["capital_introduced"] + y["pat"] - y["drawings"]
                                res.warnings.append(
                                    "%s: debtor days at the cap of %d were not enough for drawing power (needed %d); "
                                    "stock holding raised from %d to %d days so that drawing power exceeds the CC "
                                    "limit. Confirm this is realistic for the business." % (
                                        y["label"], days, needed, sd0, y["stock_days"]))
                        if not raised:
                            res.warnings.append("%s: drawing power needs %d debtor days to cover the CC limit; capped "
                                                "at %d. Consider a lower limit or higher stock." %
                                                (y["label"], needed, days))
            y["debtor_days"], y["debtor_days_auto"] = days, auto
            y["debtors"] = xround(s * days / 365)
            if auto and days > base_days["debtor"]:
                res.warnings.append("%s: debtor days raised to %d (actual trend %d) to keep drawing power above "
                                    "the CC limit." % (y["label"], days, base_days["debtor"]))
            y["bank_balance"] = 0.0
            _totals(y, project, company)
            y["bank_balance"] = y["total_liabilities"] - y["total_assets"]
        _totals(y, project, company)
        _tests(y, it, sm, dm, over90, to_fail, to_pass)
        if not y["from_statement"] or y["kind"] not in STATEMENT_KINDS:
            _dscr(y, it, dmin, dmax)
        if not y["from_statement"] and y["bank_balance"] < 0:
            res.warnings.append("%s: cash at bank (balancing figure) is negative - funding gap of Rs %s." %
                                (y["label"], format(int(-y["bank_balance"]), ",")))
        res.years.append(y)
        prev = y
    _summary(project, res, dmin, dmax, to_fail)
    return res


def _capex_line(project):
    it = project.intake
    cands = [ln for ln in project.lines if ln.head == it.tl_capex_class]
    proposed = [ln for ln in cands if "(proposed)" in ln.label]
    return (proposed or cands or [None])[0]


def _cash_basis(project):
    for ln in project.lines:
        if ln.head == "cash_in_hand" and ln.basis:
            return ln.basis
    return "S"


def _profit(y):
    y["gross_profit"] = y["sales"] + y["closing_stock"] - y["opening_stock"] - y["purchases"] - y["direct_total"]
    y["gp_pct"] = safe_div(y["gross_profit"], y["sales"])
    y["pbdit"] = y["gross_profit"] + y["other_income"] - y["indirect_total"]
    y["pbt"] = y["pbdit"] - y["interest"] - y["depreciation"]
    y["pat"] = y["pbt"] - y["tax"]
    y["cogs"] = y["opening_stock"] + y["purchases"] + y["direct_total"] - y["closing_stock"]


def _totals(y, project, company):
    s = lambda heads: sum(y["lines"].get(ln.id, 0.0) for ln in project.lines if ln.head in heads)  # noqa
    y["term_loans"] = s(("term_loans",))
    y["unsecured"] = s(("unsecured_loans",))
    y["statutory"] = s(("statutory_dues",))
    y["other_cl"] = s(("other_cl",))
    y["investments"] = s(("investments",))
    y["loans_adv"] = s(("loans_advances",))
    y["other_ca"] = s(("other_ca",))
    y["fa_net"] = sum(v[3] for v in y["fa"].values())
    y["owners"] = (y["share_capital"] + y["res_close"]) if company else y["cap_close"]
    y["total_liabilities"] = (y["owners"] + y["cc"] + y["term_loans"] + y["new_tl"] + y["unsecured"]
                              + y["creditors"] + y["statutory"] + y["other_cl"])
    y["stock"] = y["closing_stock"]
    y["total_assets"] = (y["fa_net"] + y["investments"] + y["stock"] + y["debtors"] + y["loans_adv"]
                         + y["other_ca"] + y["cash_in_hand"] + y["bank_balance"])
    y["difference"] = y["total_liabilities"] - y["total_assets"]
    y["current_assets"] = y["stock"] + y["debtors"] + y["other_ca"] + y["cash_in_hand"] + y["bank_balance"]
    y["current_liab"] = y["cc"] + y["creditors"] + y["statutory"] + y["other_cl"] + y.get("tl_curmat", 0.0)


def _tests(y, it, sm, dm, over90, to_fail, to_pass):
    limit = y.get("cc_limit_input", y["cc"]) if not (y["from_statement"] and y["kind"] in STATEMENT_KINDS) else y["cc"]
    y["cc_limit"] = limit
    net_stock = max(y["stock"] - (y["creditors"] if it.deduct_creditors else 0), 0)
    y["dp_stock"] = net_stock * (1 - sm)
    y["dp_debtors"] = y["debtors"] * (1 - over90) * (1 - dm)
    y["drawing_power"] = y["dp_stock"] + y["dp_debtors"]
    y["dp_surplus"] = y["drawing_power"] - limit
    y["dp_status"] = PASS if (limit <= 0 or y["drawing_power"] > limit) else FAIL
    y["turnover_multiple"] = safe_div(y["sales"], limit, None) if limit > 0 else None
    m = y["turnover_multiple"]
    y["turnover_status"] = "N/A" if m is None else (FAIL if m < to_fail else (AMBER if m < to_pass else PASS))
    y["debtor_days_calc"] = safe_div(y["debtors"], y["sales"]) * 365
    y["stock_days_calc"] = safe_div(y["stock"], y["cogs"]) * 365
    y["creditor_days_calc"] = safe_div(y["creditors"], y["purchases"]) * 365
    tca = y["current_assets"]
    ocl = y["current_liab"] - y["cc"]
    y["wc_gap"] = tca - ocl
    y["mpbf"] = min(y["wc_gap"] - 0.25 * tca, y["wc_gap"] - (tca - y["current_liab"]))
    y["current_ratio"] = safe_div(tca, y["current_liab"], None)


def _dscr(y, it, dmin, dmax):
    gross = y["pat"] + y["depreciation"] + y["interest"]
    net = gross - y["drawings"]
    den = (y["int_cc_full"] + y["int_tl"] + y["int_etl"] + y["int_ul"] + y["tl_principal"] + y["etl_repay"])
    y["dscr_gross"] = safe_div(gross, den, None) if den else None
    y["dscr_net"] = safe_div(net, den, None) if den else None
    y["dscr_numerator"] = net if it.dscr_deduct_drawings else gross
    y["dscr_denominator"] = den
    y["dscr"] = y["dscr_net"] if it.dscr_deduct_drawings else y["dscr_gross"]
    d = y["dscr"]
    y["dscr_status"] = "N/A" if d is None else (FAIL if d < dmin else (AMBER if d > dmax else PASS))


def _base_days(prev, it):
    from config.constants import DEFAULTS
    stock = round(prev["stock_days_calc"]) if prev["cogs"] > 0 and prev["stock"] > 0 else \
        (DEFAULTS["stock_days_mfg"] if it.nature == "Manufacturing" else DEFAULTS["stock_days_trading"])
    if it.nature in ("Service", "Contractor") and prev["stock"] == 0:
        stock = 0
    debtor = math.ceil(prev["debtor_days_calc"] - 1e-9) if prev["sales"] > 0 else DEFAULTS["debtor_days_default"]
    cred = round(prev["creditor_days_calc"]) if prev["purchases"] > 0 and prev["creditors"] > 0 else \
        (DEFAULTS["creditor_days_service"] if it.nature in ("Service", "Contractor") else DEFAULTS["creditor_days"])
    return {"stock": stock, "debtor": debtor, "creditor": cred}


def _fraction(fy, it):
    if not it.has_cc:
        return 0.0
    sfy = fy_end_of(it.facility_start)
    if fy < sfy:
        return 0.0
    if fy > sfy:
        return 1.0
    return ((3 - it.facility_start.month) % 12 + 1) / 12.0


def _summary(project, res, dmin, dmax, to_fail):
    it = project.intake
    fut = res.future
    ds = [y["dscr"] for y in fut if y.get("dscr") is not None]
    avg = sum(ds) / len(ds) if ds else None
    res.summary["dscr_avg"] = avg
    res.summary["dscr_status"] = "N/A" if avg is None else (
        FAIL if (avg < dmin or min(ds) < dmin) else (AMBER if (avg > dmax or max(ds) > dmax) else PASS))
    for y in fut:
        if y["dp_status"] == FAIL:
            res.warnings.append("%s: drawing power Rs %s is below the CC limit Rs %s." % (
                y["label"], format(int(y["drawing_power"]), ","), format(int(y["cc_limit"]), ",")))
        if y["turnover_status"] in (FAIL, AMBER):
            res.warnings.append("%s: turnover %.2f x CC limit (%s)." % (y["label"], y["turnover_multiple"] or 0,
                                                                         y["turnover_status"]))
        if y.get("dscr_status") == FAIL:
            res.warnings.append("%s: DSCR %.2f is below %.2f." % (y["label"], y["dscr"], dmin))
        elif y.get("dscr_status") == AMBER:
            res.warnings.append("%s: DSCR %.2f is above %.2f." % (y["label"], y["dscr"], dmax))
    if it.has_cc and fut and (any(y["bank_balance"] < 0 for y in fut) or
                              any((y.get("dscr") or 0) > dmax for y in fut)):
        sugg = {}
        for y in fut:
            cap = min(y["drawing_power"] / (1 + it.dp_buffer), y["sales"] / to_fail if to_fail else 1e18)
            sugg[y["fy"]] = math.floor(cap / 100000.0) * 100000
        res.summary["suggested_cc_limit"] = sugg
        res.decisions.append("Highest round CC limit that still passes drawing power and the turnover minimum: " +
                             ", ".join("%s Rs %s" % (fy_label(k), format(int(v), ",")) for k, v in sugg.items()) +
                             ". Enter it as the year-wise CC limit if you want to apply it.")
    if res.summary.get("tl_amount", 0) > 0:
        res.summary["tl_principal_check"] = abs(tle.total_principal(res.tl_schedule) - res.summary["tl_amount"]) < 0.5


def sensitivity(project, settings_defaults=None):
    out = []
    for name, shock in [("Base case", None), ("Sales 10% lower", {"sales_factor": 0.9}),
                        ("Cost of sales 5% higher", {"cost_factor": 1.05}),
                        ("Both together", {"sales_factor": 0.9, "cost_factor": 1.05})]:
        r = compute(project, settings_defaults, shock)
        fut = r.future
        out.append({"case": name, "years": [(y["label"], y["sales"], y["pat"], y.get("dscr"), y["drawing_power"],
                                              y["cc_limit"], y["dp_status"]) for y in fut],
                    "dscr_avg": r.summary.get("dscr_avg")})
    return out


def suggest_tl_amount(project, settings_defaults=None, step=50000):
    import copy
    it = project.intake
    if not it.has_tl:
        return None
    dmin = norm(it, "dscr_min", settings_defaults)

    def ok(amount):
        p = copy.deepcopy(project)
        p.intake.tl_amount = amount
        r = compute(p, settings_defaults)
        ds = [y["dscr"] for y in r.future if y.get("dscr") is not None]
        return bool(ds) and min(ds) >= dmin
    if not ok(step):
        return 0
    lo, hi = step, max(int(it.tl_amount * 4), 5000000)
    while hi - lo > step:
        mid = (lo + hi) // 2 // step * step
        if mid <= lo:
            break
        lo, hi = (mid, hi) if ok(mid) else (lo, mid)
    return lo


def fit_dscr(project, settings_defaults=None, target=None, log=print):
    """Keep each estimated / projected year's DSCR within the bank's range by setting that year's gross
    profit % (never above the last actual year's). Drawings are reduced where the lower profit would leave
    cash at bank negative. Statement years (audited / provisional) are never changed. Returns change notes."""
    it = project.intake
    dmin, dmax = norm(it, "dscr_min", settings_defaults), norm(it, "dscr_max", settings_defaults)
    target = target or round(dmin + (dmax - dmin) * 0.8, 2)          # near the top of the band
    notes = []
    tool = project.tool_years()
    user_sd = {}
    for yd in tool:
        yi = project.year_input(yd.fy)
        if yi.gp_pct is not None:            # undo an earlier fit, keep the user's own stock days
            yi.stock_days = None if yi.stock_days is not None and getattr(yi, "_fit_sd", False) else yi.stock_days
        yi.gp_pct = None
        user_sd[yd.fy] = yi.stock_days
    r0 = compute(project, settings_defaults)
    sd0 = {y["fy"]: y.get("stock_days") for y in r0.years}
    stmt = [y for y in r0.years if y["from_statement"]]
    cap_gp = safe_div(stmt[-1]["gross_profit"], stmt[-1]["sales"]) if stmt else 0.5
    orig_draw = {y["fy"]: y["drawings"] for y in r0.years}

    def year(fy):
        rr = compute(project, settings_defaults)
        return next(x for x in rr.years if x["fy"] == fy)
    # 1. one steady margin for every estimated / projected year, if one fits all years
    def set_all(g):
        for yd in tool:
            yi = project.year_input(yd.fy)
            yi.gp_pct = g
            if user_sd[yd.fy] is None and sd0.get(yd.fy):
                yi.stock_days = round(sd0[yd.fy] * (1 - cap_gp) / max(1 - g, 0.01), 2)
        rr = compute(project, settings_defaults)
        return [x.get("dscr") for x in rr.years if not x["from_statement"] and x.get("dscr") is not None]
    ds0 = [x.get("dscr") for x in r0.years if not x["from_statement"] and x.get("dscr") is not None]
    if ds0 and all(dmin <= v <= dmax for v in ds0):
        for yd in tool:
            project.year_input(yd.fy).gp_pct = None
        notes += fix_cash(project, settings_defaults, log=lambda *x: None)
        for n in notes:
            log(n)
        return notes
    best = None
    steps = 400
    for k in range(steps, -1, -1):                 # highest margin first
        g = cap_gp * k / steps
        ds = set_all(g)
        if ds and all(dmin <= v <= dmax for v in ds):
            best = g
            break
    if best is not None:
        g = round(best, 4)
        ds = set_all(g)
        notes.append("Gross profit %% for all estimated / projected years set to %.2f%% (last actual %.2f%%) so that "
                     "DSCR is %s (was %s)." % (g * 100, cap_gp * 100, ", ".join("%.2f" % v for v in ds),
                                                ", ".join("%.2f" % v for v in ds0)))
        notes += fix_cash(project, settings_defaults, log=lambda *x: None)
        for n in notes:
            log(n)
        return notes
    # 2. otherwise year by year, each year's margin as close as possible to the year before
    prev_g = cap_gp
    for yd in tool:
        yi = project.year_input(yd.fy)
        yi.gp_pct = None
        yi.stock_days = user_sd[yd.fy]
    for yd in tool:
        yi = project.year_input(yd.fy)
        y = year(yd.fy)
        # a margin carried from a fitted year: keep the stock value as at the last actual margin
        if user_sd[yd.fy] is None and sd0.get(yd.fy) and abs(y["gp_ratio_used"] - cap_gp) > 1e-6:
            yi.stock_days = round(sd0[yd.fy] * (1 - cap_gp) / max(1 - y["gp_ratio_used"], 0.01), 2)
            y = year(yd.fy)
        d = y.get("dscr")
        if d is None:
            continue
        if not dmin <= d <= dmax:
            def dscr_at(g):
                yi.gp_pct = g
                # keep the stock value unchanged: same days of cost at the last actual margin
                if sd0.get(yd.fy):
                    yi.stock_days = round(sd0[yd.fy] * (1 - cap_gp) / max(1 - g, 0.01), 2)
                return year(yd.fy).get("dscr") or 0.0
            if dscr_at(cap_gp) < dmin:
                yi.gp_pct, yi.stock_days = None, user_sd[yd.fy]
                notes.append("FY %s: DSCR %.2f is below %.2f even at the last actual gross profit %% (%.2f%%); "
                             "reduce the loan or lengthen the tenure." % (yd.label, d, dmin, cap_gp * 100))
            else:
                def edge(level, above):
                    """margin at which DSCR crosses `level` (DSCR rises with the margin)."""
                    lo, hi = 0.0, cap_gp
                    for _ in range(40):
                        mid = (lo + hi) / 2
                        if dscr_at(mid) > level:
                            hi = mid
                        else:
                            lo = mid
                    return lo if not above else hi
                g_hi = min(edge(dmax - 0.02, False), cap_gp)
                g_lo = edge(dmin + 0.02, True) if dscr_at(0.0) < dmin + 0.02 else 0.0
                g = round(min(max(prev_g, g_lo), g_hi), 4)
                got = dscr_at(g)
                prev_g = g
                notes.append("FY %s: gross profit %% set to %.2f%% (last actual %.2f%%) so that DSCR is %.2f "
                             "(was %.2f)." % (yd.label, g * 100, cap_gp * 100, got, d))
    notes += fix_cash(project, settings_defaults, log=lambda *x: None)
    for n in notes:
        log(n)
    return notes


def fix_cash(project, settings_defaults=None, log=print, min_pct=0.02, min_abs=25000.0,
             creditor_cap=90, ocl_months=3):
    """Cash and bank balance of an estimated / projected year must stay positive - at least the higher of
    min_pct of sales and min_abs. The cushion comes, in order, from: advances recovered, more credit from
    suppliers (only while drawing power still covers the CC limit), more outstanding expenses (up to
    ocl_months of expenses), and capital introduced. Profit is not touched, so the DSCR does not change."""
    it = project.intake
    notes = []
    f = lambda v: format(int(round(v)), ",")   # noqa: E731

    def year(fy):
        rr = compute(project, settings_defaults)
        return next(x for x in rr.years if x["fy"] == fy)
    for yd in project.tool_years():
        yi = project.year_input(yd.fy)
        y = year(yd.fy)
        floor = max(min_abs, xround(y["sales"] * min_pct))
        if y["bank_balance"] >= floor:
            continue
        start = y["bank_balance"]
        gap = lambda yy: floor - yy["bank_balance"]   # noqa: E731
        # 1. advances / other current assets recovered
        for ln in [l for l in project.lines if l.head in ("loans_advances", "other_ca")]:
            have = y["lines"].get(ln.id, 0.0)
            if have <= 0 or gap(y) <= 0:
                continue
            take = min(have, gap(y))
            yi.line_override[ln.id] = have - take
            y = year(yd.fy)
            notes.append("FY %s: %s reduced from Rs %s to Rs %s (realised in the year)." % (
                yd.label, ln.label, f(have), f(have - take)))
        # 2. creditors: more days of purchases, drawing power still above the CC limit
        if gap(y) > 0 and y["purchases"] > 0:
            cd0 = y["creditor_days"]
            dd_keep = yi.debtor_days
            yi.debtor_days = y["debtor_days"]          # hold debtors so the cash is really freed
            target = y.get("cc_limit_input", 0) * (1 + it.dp_buffer) if it.has_cc else 0.0

            def at(days):
                yi.creditor_days = days
                return year(yd.fy)
            best = cd0
            lo, hi = cd0, max(cd0, creditor_cap)
            if hi > lo:
                for _ in range(25):
                    mid = (lo + hi) / 2
                    yy = at(mid)
                    if (yy["drawing_power"] >= target - 0.5 or not target) and gap(yy) >= 0:
                        best, lo = mid, mid           # still short: more days
                    elif yy["drawing_power"] >= target - 0.5 or not target:
                        best, hi = mid, mid           # enough cash: fewer days
                    else:
                        hi = mid                      # drawing power broken: fewer days
                best = math.ceil(best)
                while best > cd0 and target and at(best)["drawing_power"] < target - 0.5:
                    best -= 1
            if best > cd0:
                y = at(best)
                notes.append("FY %s: creditors raised from %d to %d days of purchases (drawing power Rs %s still "
                             "covers the CC limit)." % (yd.label, round(cd0), best, f(y["drawing_power"])))
            else:
                yi.creditor_days, yi.debtor_days = (yi.creditor_days if yi.creditor_days != cd0 else None), dd_keep
                yi.creditor_days = None if yi.creditor_days == cd0 else yi.creditor_days
                y = year(yd.fy)
        # 3. outstanding expenses
        ocl = [l for l in project.lines if l.head == "other_cl"]
        if gap(y) > 0 and ocl:
            ln = ocl[0]
            have = y["lines"].get(ln.id, 0.0)
            cap = xround((y["direct_total"] + y["indirect_total"]) * ocl_months / 12)
            add = min(max(cap - have, 0.0), gap(y))
            if add > 0:
                yi.line_override[ln.id] = have + add
                y = year(yd.fy)
                notes.append("FY %s: %s raised from Rs %s to Rs %s (expenses outstanding at the year end)." % (
                    yd.label, ln.label, f(have), f(have + add)))
        # 4. capital introduced
        if gap(y) > 0:
            add = math.ceil(gap(y) / 1000.0) * 1000
            yi.capital_introduced = (yi.capital_introduced or 0.0) + add
            y = year(yd.fy)
            notes.append("FY %s: capital of Rs %s introduced by the %s." % (
                yd.label, f(add), "promoters" if it.is_company else it.signatory_title.lower() or "proprietor"))
        notes.append("FY %s: cash and bank balance Rs %s (was Rs %s)." % (yd.label, f(y["bank_balance"]), f(start)))
    for n in notes:
        log(n)
    return notes


def fit_turnover(project, settings_defaults=None, log=print):
    """Raise the sales growth of an estimated / projected year just enough for turnover to reach the
    'pass' multiple of the CC limit (green). Returns change notes."""
    it = project.intake
    if not it.has_cc:
        return []
    pass_from = norm(it, "turnover_pass_from", settings_defaults)
    notes = []
    for yd in project.tool_years():
        yi = project.year_input(yd.fy)
        rr = compute(project, settings_defaults)
        ys = rr.years
        k = next(i for i, x in enumerate(ys) if x["fy"] == yd.fy)
        y, prev = ys[k], ys[k - 1] if k else None
        limit = y.get("cc_limit") or 0
        if not limit or prev is None or not prev["sales"]:
            continue
        need = limit * pass_from * 1.001
        if y["sales"] >= need:
            continue
        g_old = y["growth"]
        g = math.ceil((need / prev["sales"] - 1) * 200) / 200.0      # round up to 0.5%
        yi.growth = g
        y2 = next(x for x in compute(project, settings_defaults).years if x["fy"] == yd.fy)
        notes.append("FY %s: sales growth raised from %.1f%% to %.1f%% (sales Rs %s) so that turnover is %.2f x the "
                     "CC limit." % (yd.label, g_old * 100, g * 100, format(int(y2["sales"]), ","),
                                    y2["sales"] / limit))
    for n in notes:
        log(n)
    return notes


def fix_ratios(project, settings_defaults=None, log=print, cr_min=1.35, tol_max=2.9):
    """Current ratio at least 1.33 and TOL / TNW at most 3 in every estimated / projected year (small margin kept
    for the FORM-III classification). Met by capital introduced, which raises current assets and net worth."""
    it = project.intake
    notes = []
    f = lambda v: format(int(round(v)), ",")   # noqa: E731
    for yd in project.tool_years():
        yi = project.year_input(yd.fy)
        for _ in range(4):
            y = next(x for x in compute(project, settings_defaults).years if x["fy"] == yd.fy)
            ca, cl = y["current_assets"], y["current_liab"]
            tnw = y["owners"]
            tol = y["total_liabilities"] - tnw
            x1 = cr_min * cl - ca if cl else 0.0
            x2 = tol / tol_max - tnw
            x = max(x1, x2, 0.0)
            if x < 1:
                break
            add = math.ceil(x / 1000.0) * 1000
            yi.capital_introduced = (yi.capital_introduced or 0.0) + add
            notes.append("FY %s: capital of Rs %s introduced so that current ratio is at least 1.33 and TOL / TNW at "
                         "most 3 (were %.2f and %.2f)." % (yd.label, f(add), ca / cl if cl else 0,
                                                            tol / tnw if tnw else 0))
    for n in notes:
        log(n)
    return notes


def tidy_creditors(project, settings_defaults=None, log=print, min_pct=0.02, min_abs=25000.0):
    """After capital is introduced, bring creditor days back towards the client's normal days as far as the
    cash cushion allows (improves current ratio and TOL / TNW)."""
    notes = []
    for yd in project.tool_years():
        yi = project.year_input(yd.fy)
        if yi.creditor_days is None:
            continue
        cur = yi.creditor_days
        yi.creditor_days = None
        base = next(x for x in compute(project, settings_defaults).years if x["fy"] == yd.fy)["creditor_days"]
        yi.creditor_days = cur
        if cur <= base:
            continue

        def ok(days):
            yi.creditor_days = days
            y = next(x for x in compute(project, settings_defaults).years if x["fy"] == yd.fy)
            floor = max(min_abs, xround(y["sales"] * min_pct))
            return y["bank_balance"] >= floor
        lo, hi = base, cur                  # smallest days that still keep the cushion
        if ok(base):
            best = base
        else:
            for _ in range(25):
                mid = (lo + hi) / 2
                if ok(mid):
                    hi = mid
                else:
                    lo = mid
            best = math.ceil(hi)
        yi.creditor_days = best if best > base else None
        if best < cur:
            notes.append("FY %s: creditors brought back from %d to %d days of purchases after the capital "
                         "introduced." % (yd.label, round(cur), round(best)))
    for n in notes:
        log(n)
    return notes
