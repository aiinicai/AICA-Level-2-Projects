"""Measures, the safe KPI formula language, and the built-in KPI set (ported from measures.ts, expression.ts, registry.ts).

Formulas are parsed into a small syntax tree and evaluated with exact decimals; there is no eval() anywhere.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from .cashflow_ageing import ageing, cash_flow
from .context import Ctx, day_before, ints, memoize, pct_change, rupees
from .periods import DateRange, add_months, month_end, month_label, month_start, months_in, range_days
from .statements import Figure, balance_sheet, profit_and_loss

# ------------------------------------------------------------------------------------------------ expression language
FUNCTIONS = {"abs": (1, 1), "min": (2, 8), "max": (2, 8), "avg": (2, 8), "div": (2, 2), "ratio": (2, 2), "pct": (2, 2), "annualise": (1, 1)}


class FormulaError(Exception):
    pass


def tokenize(src: str):
    if len(src) > 500:
        raise FormulaError("Formula too long (max 500 characters)")
    out, i = [], 0
    while i < len(src):
        c = src[i]
        if c.isspace():
            i += 1
        elif c.isdigit() or c == ".":
            m = re.match(r"(\d+(\.\d+)?|\.\d+)", src[i:])
            if not m:
                raise FormulaError(f"Invalid number at position {i + 1}")
            out.append(("num", m.group(0), i))
            i += len(m.group(0))
        elif c.isalpha() or c == "_":
            m = re.match(r"[a-z_][a-z0-9_]*", src[i:], re.I)
            out.append(("id", m.group(0).lower(), i))
            i += len(m.group(0))
        elif c in "+-*/":
            out.append(("op", c, i)); i += 1
        elif c == "(":
            out.append(("lp", c, i)); i += 1
        elif c == ")":
            out.append(("rp", c, i)); i += 1
        elif c == ",":
            out.append(("comma", c, i)); i += 1
        else:
            raise FormulaError(f'Unexpected character "{c}" at position {i + 1}')
    return out


def parse(src: str, allowed: set[str]):
    toks, p, depth = tokenize(src), [0], [0]

    def peek():
        return toks[p[0]] if p[0] < len(toks) else None

    def guard():
        depth[0] += 1
        if depth[0] > 40:
            raise FormulaError("Formula nested too deeply")

    def expect(k):
        t = peek()
        if not t or t[0] != k:
            raise FormulaError(f"Expected {k} at position {t[2] + 1 if t else len(src) + 1}")
        p[0] += 1

    def expr():
        guard()
        l = term()
        while peek() and peek()[0] == "op" and peek()[1] in "+-":
            op = toks[p[0]][1]; p[0] += 1
            l = ("bin", op, l, term())
        depth[0] -= 1
        return l

    def term():
        l = unary()
        while peek() and peek()[0] == "op" and peek()[1] in "*/":
            op = toks[p[0]][1]; p[0] += 1
            l = ("bin", op, l, unary())
        return l

    def unary():
        if peek() and peek()[0] == "op" and peek()[1] == "-":
            p[0] += 1
            guard()
            e = unary()
            depth[0] -= 1
            return ("neg", e)
        return primary()

    def primary():
        t = peek()
        if not t:
            raise FormulaError("Unexpected end of formula")
        if t[0] == "num":
            p[0] += 1
            return ("num", t[1])
        if t[0] == "lp":
            p[0] += 1
            e = expr()
            expect("rp")
            return e
        if t[0] == "id":
            p[0] += 1
            if peek() and peek()[0] == "lp":
                if t[1] not in FUNCTIONS:
                    raise FormulaError(f'Unknown function "{t[1]}"')
                p[0] += 1
                args = [expr()]
                while peek() and peek()[0] == "comma":
                    p[0] += 1
                    args.append(expr())
                expect("rp")
                lo, hi = FUNCTIONS[t[1]]
                if not lo <= len(args) <= hi:
                    raise FormulaError(f"{t[1]}() takes {lo}–{hi} arguments")
                return ("call", t[1], args)
            if t[1] not in allowed:
                raise FormulaError(f'Unknown field "{t[1]}"')
            return ("id", t[1])
        raise FormulaError(f'Unexpected "{t[1]}" at position {t[2] + 1}')

    ast = expr()
    if p[0] < len(toks):
        raise FormulaError(f'Unexpected "{toks[p[0]][1]}" at position {toks[p[0]][2] + 1}')
    return ast


@dataclass
class Ev:
    value: Decimal | None
    status: str
    notes: list[str] = field(default_factory=list)


_RANK = {"actual": 0, "calculated": 1, "estimated": 2, "unavailable": 3}


def _worse(a: str, b: str) -> str:
    return a if _RANK[a] >= _RANK[b] else b


def evaluate(ast, resolve, period_days: int) -> Ev:
    def merge(vals: list[Ev], value, note: str | None = None) -> Ev:
        status = "calculated"
        for v in vals:
            status = _worse(status, v.status)
        notes = list(dict.fromkeys([n for v in vals for n in v.notes] + ([note] if note else [])))
        if value is None:
            status = "unavailable"
        return Ev(value, status, notes)

    def go(n) -> Ev:
        t = n[0]
        if t == "num":
            return Ev(Decimal(n[1]), "actual", [])
        if t == "id":
            return resolve(n[1])
        if t == "neg":
            e = go(n[1])
            return Ev(None if e.value is None else -e.value, e.status, e.notes)
        if t == "bin":
            l, r = go(n[2]), go(n[3])
            if l.value is None or r.value is None:
                return merge([l, r], None)
            op = n[1]
            if op == "+": return merge([l, r], l.value + r.value)
            if op == "-": return merge([l, r], l.value - r.value)
            if op == "*": return merge([l, r], l.value * r.value)
            if r.value == 0:
                return merge([l, r], None, "Division by zero")
            return merge([l, r], l.value / r.value)
        args = [go(a) for a in n[2]]
        if any(a.value is None for a in args):
            return merge(args, None)
        v = [a.value for a in args]
        fn = n[1]
        if fn == "abs": return merge(args, abs(v[0]))
        if fn == "min": return merge(args, min(v))
        if fn == "max": return merge(args, max(v))
        if fn == "avg": return merge(args, sum(v, Decimal(0)) / len(v))
        if fn == "div":
            return merge(args, None, "Denominator is zero") if v[1] == 0 else merge(args, v[0] / v[1])
        if fn in ("ratio", "pct"):
            if v[1] <= 0:
                return merge(args, None, "Denominator is zero" if v[1] == 0 else "Denominator is negative — ratio not meaningful")
            q = v[0] / v[1]
            return merge(args, q * 100 if fn == "pct" else q)
        if fn == "annualise":
            if period_days > 0:
                return merge(args, v[0] * 365 / period_days, "Annualised from a part-year period" if period_days < 365 else None)
            return merge(args, None)
        raise FormulaError("Invalid formula")

    return go(ast)


# ------------------------------------------------------------------------------------------------ measures
@dataclass
class Measure:
    value: float | None
    status: str
    unit: str = "currency"
    notes: list[str] = field(default_factory=list)


MEASURE_NAMES = [
    "revenue", "gross_sales", "sales_returns", "other_income", "purchases", "direct_expenses", "opening_stock", "closing_stock", "cogs",
    "gross_profit", "opex", "employee_cost", "rent", "freight", "utilities", "selling_expense", "admin_expense", "depreciation", "ebitda",
    "ebit", "finance_cost", "exceptional", "pbt", "tax", "net_profit", "cash_bank", "trade_receivables", "trade_payables", "inventory",
    "current_assets", "current_liabilities", "quick_assets", "total_assets", "total_liabilities", "equity", "debt", "short_term_debt",
    "fixed_assets", "capital_employed", "net_debt", "working_capital", "avg_trade_receivables", "avg_trade_payables", "avg_inventory",
    "avg_total_assets", "avg_equity", "avg_capital_employed", "avg_fixed_assets", "credit_sales", "credit_purchases",
    "operating_cash_flow", "monthly_burn", "overdue_receivables", "overdue_payables", "employees", "days", "prev_revenue",
    "prev_net_profit", "prev_gross_profit"]


def _from_fig(f: Figure) -> Measure:
    return Measure(rupees(f.paise), f.status, "currency", f.notes)


def _credit_sales(ctx: Ctx, r: DateRange):
    rev = ctx.chart.ledgers_of("revenue_operating", "revenue_contra")
    debtors = ctx.chart.ledgers_of("trade_receivable")
    if not rev or not debtors:
        return None
    row = ctx.store.one(
        "SELECT SUM(-vl.amount_paise) AS s FROM voucher_lines vl JOIN vouchers v ON v.id = vl.voucher_id "
        "WHERE v.company_id = ? AND v.is_accounting = 1 AND v.date BETWEEN ? AND ? AND v.base_type IN ('Sales','Credit Note') "
        f"AND vl.ledger_id IN ({ints(rev)}) AND v.party_ledger_id IN ({ints(debtors)})", [ctx.cid, r[0], r[1]])
    return int(row["s"]) if row and row["s"] is not None else 0


def _credit_purchases(ctx: Ctx, r: DateRange):
    pur = ctx.chart.ledgers_of("cogs_purchases", "cogs_direct")
    creditors = ctx.chart.ledgers_of("trade_payable")
    if not pur or not creditors:
        return None
    row = ctx.store.one(
        "SELECT SUM(vl.amount_paise) AS s FROM voucher_lines vl JOIN vouchers v ON v.id = vl.voucher_id "
        "WHERE v.company_id = ? AND v.is_accounting = 1 AND v.date BETWEEN ? AND ? AND v.base_type IN ('Purchase','Debit Note') "
        f"AND vl.ledger_id IN ({ints(pur)}) AND v.party_ledger_id IN ({ints(creditors)})", [ctx.cid, r[0], r[1]])
    return int(row["s"]) if row and row["s"] is not None else 0


def _worst_of(a: str, b: str) -> str:
    return a if _RANK[a] >= _RANK[b] else b


def compute_measures(ctx: Ctx, r: DateRange, prev: DateRange | None) -> dict[str, Measure]:
    return memoize(ctx.store, ctx.cid, f"measures:{r[0]}:{r[1]}:{prev[0] if prev else None}:{prev[1] if prev else None}:{ctx.cost_centre_id}",
                   lambda: _measures(ctx, r, prev))


def _measures(ctx: Ctx, r: DateRange, prev: DateRange | None) -> dict[str, Measure]:
    f = profit_and_loss(ctx, r).figures
    m = Measure
    out: dict[str, Measure] = {
        "revenue": _from_fig(f["revenue"]), "gross_sales": _from_fig(f["grossSales"]), "sales_returns": _from_fig(f["salesReturns"]),
        "other_income": _from_fig(f["otherIncome"]), "purchases": _from_fig(f["purchases"]), "direct_expenses": _from_fig(f["directExpenses"]),
        "opening_stock": _from_fig(f["openingStock"]), "closing_stock": _from_fig(f["closingStock"]), "cogs": _from_fig(f["cogs"]),
        "gross_profit": _from_fig(f["grossProfit"]), "opex": _from_fig(f["opex"]), "employee_cost": _from_fig(f["employeeCost"]),
        "rent": _from_fig(f["rent"]), "freight": _from_fig(f["freight"]), "utilities": _from_fig(f["utilities"]),
        "selling_expense": _from_fig(f["selling"]), "admin_expense": _from_fig(f["admin"]), "depreciation": _from_fig(f["depreciation"]),
        "ebitda": _from_fig(f["ebitda"]), "ebit": _from_fig(f["ebit"]), "finance_cost": _from_fig(f["financeCost"]),
        "exceptional": _from_fig(f["exceptional"]), "pbt": _from_fig(f["pbt"]), "tax": _from_fig(f["tax"]),
        "net_profit": _from_fig(f["netProfit"]), "days": m(range_days(r), "actual", "count"),
    }
    if prev:
        pp = profit_and_loss(ctx, prev).figures
        out["prev_revenue"], out["prev_net_profit"], out["prev_gross_profit"] = (_from_fig(pp[k]) for k in ("revenue", "netProfit", "grossProfit"))
    else:
        for k in ("prev_revenue", "prev_net_profit", "prev_gross_profit"):
            out[k] = m(None, "unavailable", "currency", ["No comparison period selected"])

    cc = ctx.cost_centre_id is not None
    bs_note = ["Balance-sheet figures are company-wide; cost-centre filter applies to P&L only."] if cc else []
    close, opened = balance_sheet(ctx, r[1]), balance_sheet(ctx, day_before(r[0]))
    t, o = close["totals"], opened["totals"]
    inv_st = t["inventoryStatus"]

    def bs(v, st="actual", notes=None):
        return m(rupees(v), "unavailable" if v is None else st, "currency", [*bs_note, *(notes or [])])

    def avg(a, b, st="calculated", notes=None):
        if a is None or b is None:
            return m(None, "unavailable", "currency", list(notes or []))
        return m(rupees((a + b) / 2), st, "currency", [*bs_note, *(notes or [])])

    cap_emp = lambda x: x["equity"] + x["debt"]
    inv_none = t["inventory"] is None
    est = inv_st == "estimated"
    out.update({
        "cash_bank": bs(t["cash"] + t["bank"]), "trade_receivables": bs(t["tradeReceivables"]), "trade_payables": bs(t["tradePayables"]),
        "inventory": bs(t["inventory"], inv_st, ["Inventory value estimated (no Tally valuation snapshot)."] if est else []),
        "current_assets": bs(None if inv_none else t["currentAssets"], "estimated" if est else "actual"),
        "current_liabilities": bs(t["currentLiabilities"]), "quick_assets": bs(t["quickAssets"], "calculated"),
        "total_assets": bs(None if inv_none else t["totalAssets"], "estimated" if est else "actual"),
        "total_liabilities": bs(t["totalLiabilities"]),
        "equity": bs(None if inv_none else t["equity"], "estimated" if est else "calculated"),
        "debt": bs(t["debt"]), "short_term_debt": bs(t["shortTermDebt"]), "fixed_assets": bs(t["fixedAssets"]),
        "capital_employed": bs(None if inv_none else cap_emp(t), "calculated"),
        "net_debt": bs(t["debt"] - t["cash"] - t["bank"], "calculated"),
        "working_capital": bs(None if inv_none else t["currentAssets"] - t["currentLiabilities"], "estimated" if est else "calculated"),
        "avg_trade_receivables": avg(o["tradeReceivables"], t["tradeReceivables"]),
        "avg_trade_payables": avg(o["tradePayables"], t["tradePayables"]),
        "avg_inventory": avg(o["inventory"], t["inventory"], _worst_of(o["inventoryStatus"], inv_st)),
        "avg_total_assets": avg(None if o["inventory"] is None else o["totalAssets"], None if inv_none else t["totalAssets"]),
        "avg_equity": avg(None if o["inventory"] is None else o["equity"], None if inv_none else t["equity"]),
        "avg_capital_employed": avg(None if o["inventory"] is None else cap_emp(o), None if inv_none else cap_emp(t)),
        "avg_fixed_assets": avg(o["fixedAssets"], t["fixedAssets"]),
    })
    cs = None if cc else _credit_sales(ctx, r)
    out["credit_sales"] = (m(None, "unavailable", "currency", ["Needs classified revenue and debtor ledgers (party on sales vouchers)."]) if cs is None
                           else m(rupees(cs), "calculated", "currency", ["Sales vouchers with a debtor party; cash sales excluded."]))
    cp = None if cc else _credit_purchases(ctx, r)
    out["credit_purchases"] = (m(None, "unavailable", "currency", ["Needs classified purchase and creditor ledgers."]) if cp is None
                               else m(rupees(cp), "calculated", "currency", ["Purchase vouchers with a creditor party."]))
    cf = cash_flow(ctx, r)
    cf_ok = len(ctx.chart.ledgers_of("cash", "bank")) > 0 and not cc
    out["operating_cash_flow"] = (m(rupees(cf["byCategory"]["operating"]), "estimated" if abs(cf["check"]) > 100 else "calculated", "currency", cf["notes"])
                                  if cf_ok else m(None, "unavailable", "currency", cf["notes"]))
    months = len(months_in(r))
    net_per_month = cf["net"] / max(1, months)
    if not cf_ok:
        out["monthly_burn"] = m(None, "unavailable")
    elif net_per_month >= 0:
        out["monthly_burn"] = m(None, "unavailable", "currency", ["Cash is not declining over the period; runway not applicable."])
    else:
        out["monthly_burn"] = m(rupees(-net_per_month), "calculated")
    if cc:
        out["overdue_receivables"] = m(None, "unavailable", "currency", bs_note)
        out["overdue_payables"] = m(None, "unavailable", "currency", bs_note)
    else:
        ar, ap = ageing(ctx, "receivable", r[1]), ageing(ctx, "payable", r[1])
        ar_ok = (ar["totals"]["billwiseCoveragePct"] or 0) > 0
        ap_ok = (ap["totals"]["billwiseCoveragePct"] or 0) > 0
        out["overdue_receivables"] = (m(rupees(ar["totals"]["overdue"]), "actual", "currency", ar["notes"]) if ar_ok else
                                      m(None, "unavailable", "currency", ["No bill-wise receivable data: overdue cannot be determined from ledger balances."]))
        out["overdue_payables"] = (m(rupees(ap["totals"]["overdue"]), "actual", "currency", ap["notes"]) if ap_ok else
                                   m(None, "unavailable", "currency", ["No bill-wise payable data."]))
    emp = ctx.settings.get("employees")
    out["employees"] = (m(emp, "actual", "count", ["Configured in company settings"]) if emp else
                        m(None, "unavailable", "count", ["Employee count is not in Tally; set it in Company settings."]))
    return out


# ------------------------------------------------------------------------------------------------ KPI registry
STOCK = ["trading", "distribution", "wholesale", "retail", "manufacturing"]


def _k(code, name, category, unit, expression, mtype, better, description, thresholds=None, industries=None, limitations=None, drill=None):
    return {"code": code, "name": name, "category": category, "unit": unit, "expression": expression, "measureType": mtype, "better": better,
            "description": description, "thresholds": thresholds, "industries": industries or [], "limitations": limitations, "drill": drill}


def _page(t):
    return {"kind": "page", "target": t}


BUILTIN_KPIS = [
    _k("revenue", "Revenue from operations", "Profitability", "currency", "revenue", "official", "higher", "Net revenue: revenue ledgers less returns, discounts and other reductions.", drill=_page("/pnl?tab=revenue")),
    _k("gross_sales", "Gross sales", "Profitability", "currency", "gross_sales", "management", "higher", "Net revenue + sales returns & reductions."),
    _k("sales_returns", "Sales returns & reductions", "Profitability", "currency", "sales_returns", "management", "lower", "Contra-revenue ledgers + credit-note debits to sales ledgers."),
    _k("cogs", "Cost of goods sold", "Profitability", "currency", "cogs", "official", "lower", "Opening stock + purchases + direct expenses − closing stock.", limitations="Depends on the stock valuation source shown in the calculation details.", drill=_page("/pnl?tab=costs")),
    _k("gross_profit", "Gross profit", "Profitability", "currency", "gross_profit", "official", "higher", "Net revenue − COGS."),
    _k("gross_margin_pct", "Gross margin", "Profitability", "percent", "pct(gross_profit, revenue)", "official", "higher", "Gross profit ÷ net revenue × 100. Not meaningful when revenue ≤ 0.", thresholds={"warn": 15, "bad": 8}),
    _k("opex", "Operating expenses", "Profitability", "currency", "opex", "management", "lower", "Operating expense classes; excludes D&A, finance cost, exceptional items and tax.", drill=_page("/pnl?tab=costs")),
    _k("ebitda", "EBITDA", "Profitability", "currency", "ebitda", "management", "higher", "Gross profit − operating expenses. Other income excluded.", limitations="Reliable only when depreciation and finance cost ledgers are correctly classified."),
    _k("ebit", "EBIT (operating profit)", "Profitability", "currency", "ebit", "management", "higher", "EBITDA − depreciation & amortisation."),
    _k("finance_cost", "Finance costs", "Profitability", "currency", "finance_cost", "official", "lower", "Interest and borrowing costs."),
    _k("pbt", "Profit before tax", "Profitability", "currency", "pbt", "official", "higher", "EBIT + other income − finance costs − exceptional items."),
    _k("tax", "Income tax expense", "Profitability", "currency", "tax", "official", "neutral", "Ledgers classified as income tax expense (often booked only at year end)."),
    _k("net_profit", "Net profit / (loss)", "Profitability", "currency", "net_profit", "official", "higher", "Profit before tax − tax.", drill=_page("/pnl")),
    _k("net_margin_pct", "Net profit margin", "Profitability", "percent", "pct(net_profit, revenue)", "official", "higher", "Net profit ÷ net revenue × 100.", thresholds={"warn": 5, "bad": 0}),
    _k("other_income", "Other income", "Profitability", "currency", "other_income", "official", "neutral", "Non-operating income."),
    _k("cash_bank", "Cash & bank balances", "Liquidity", "currency", "cash_bank", "official", "higher", "Closing cash and bank balances (overdrafts are borrowings).", drill=_page("/balance-sheet?tab=liquidity")),
    _k("trade_receivables", "Trade receivables", "Working capital", "currency", "trade_receivables", "official", "neutral", "Closing debtor balances.", drill=_page("/receivables-payables")),
    _k("trade_payables", "Trade payables", "Working capital", "currency", "trade_payables", "official", "neutral", "Closing creditor balances.", drill=_page("/receivables-payables?tab=payables")),
    _k("inventory", "Inventory value", "Working capital", "currency", "inventory", "official", "neutral", "Closing stock value; source disclosed.", industries=STOCK, drill=_page("/inventory")),
    _k("working_capital", "Net working capital", "Working capital", "currency", "working_capital", "official", "neutral", "Current assets − current liabilities."),
    _k("operating_cash_flow", "Operating cash flow", "Liquidity", "currency", "operating_cash_flow", "management", "higher", "Direct method: cash/bank movements attributed to operating classes of their contra ledgers.", limitations="Accuracy depends on classifications of contra ledgers; interest paid is treated as financing."),
    _k("revenue_growth_pct", "Revenue growth", "Growth", "percent", "pct(revenue - prev_revenue, prev_revenue)", "management", "higher", "(Revenue − comparison revenue) ÷ comparison revenue × 100. Not meaningful if the base ≤ 0."),
    _k("ebitda_margin_pct", "EBITDA margin", "Profitability", "percent", "pct(ebitda, revenue)", "management", "higher", "EBITDA ÷ revenue × 100."),
    _k("opex_ratio_pct", "Operating expense ratio", "Efficiency", "percent", "pct(opex, revenue)", "management", "lower", "Operating expenses ÷ revenue × 100."),
    _k("finance_cost_ratio_pct", "Finance cost to revenue", "Solvency", "percent", "pct(finance_cost, revenue)", "management", "lower", "Finance costs ÷ revenue × 100.", thresholds={"warn": 4, "bad": 8}),
    _k("roce_pct", "Return on capital employed", "Returns", "percent", "pct(annualise(ebit), avg_capital_employed)", "management", "higher", "Annualised EBIT ÷ average capital employed (equity + interest-bearing debt, opening & closing) × 100."),
    _k("roa_pct", "Return on assets", "Returns", "percent", "pct(annualise(net_profit), avg_total_assets)", "management", "higher", "Annualised net profit ÷ average total assets × 100."),
    _k("roe_pct", "Return on equity", "Returns", "percent", "pct(annualise(net_profit), avg_equity)", "management", "higher", "Annualised net profit ÷ average equity × 100. Not meaningful when average equity ≤ 0."),
    _k("current_ratio", "Current ratio", "Liquidity", "ratio", "ratio(current_assets, current_liabilities)", "official", "higher", "Current assets ÷ current liabilities (closing).", thresholds={"warn": 1.2, "bad": 1.0}, drill=_page("/balance-sheet?tab=liquidity")),
    _k("quick_ratio", "Quick ratio", "Liquidity", "ratio", "ratio(quick_assets, current_liabilities)", "official", "higher", "(Current assets − inventory − non-quick assets) ÷ current liabilities.", thresholds={"warn": 0.8, "bad": 0.5}),
    _k("cash_ratio", "Cash ratio", "Liquidity", "ratio", "ratio(cash_bank, current_liabilities)", "management", "higher", "Cash & bank ÷ current liabilities."),
    _k("debt_to_equity", "Debt to equity", "Solvency", "ratio", "ratio(debt, equity)", "official", "lower", "Interest-bearing debt ÷ equity. Not meaningful when equity ≤ 0.", thresholds={"warn": 1.5, "bad": 2.5}),
    _k("liabilities_to_assets_pct", "Total liabilities to total assets", "Solvency", "percent", "pct(total_liabilities, total_assets)", "management", "lower", "Total liabilities ÷ total assets × 100."),
    _k("equity_ratio_pct", "Equity ratio", "Solvency", "percent", "pct(equity, total_assets)", "management", "higher", "Equity ÷ total assets × 100."),
    _k("net_debt", "Net debt", "Solvency", "currency", "net_debt", "management", "lower", "Interest-bearing debt − cash & bank."),
    _k("interest_coverage", "Interest coverage", "Solvency", "ratio", "ratio(ebit, finance_cost)", "management", "higher", "EBIT ÷ finance costs. Unavailable when there are no finance costs.", thresholds={"warn": 3, "bad": 1.5}),
    _k("receivable_days", "Receivable days", "Working capital", "days", "ratio(avg_trade_receivables, credit_sales) * days", "management", "lower", "Average trade receivables ÷ credit sales × days in period.", thresholds={"warn": 60, "bad": 90}),
    _k("payable_days", "Payable days", "Working capital", "days", "ratio(avg_trade_payables, credit_purchases) * days", "management", "neutral", "Average trade payables ÷ credit purchases × days in period."),
    _k("inventory_days", "Inventory days", "Working capital", "days", "ratio(avg_inventory, cogs) * days", "management", "lower", "Average inventory ÷ COGS × days in period.", thresholds={"warn": 90, "bad": 150}, industries=STOCK),
    _k("cash_conversion_cycle", "Cash conversion cycle", "Working capital", "days", "inventory_days + receivable_days - payable_days", "management", "lower", "Inventory days + receivable days − payable days.", industries=STOCK),
    _k("cash_runway_months", "Cash runway", "Liquidity", "months", "ratio(max(cash_bank, 0), monthly_burn)", "estimate", "higher", "Cash & bank ÷ average monthly net cash outflow. Only shown when cash is declining.", thresholds={"warn": 6, "bad": 3}),
    _k("revenue_per_employee", "Revenue per employee", "Efficiency", "currency", "ratio(annualise(revenue), employees)", "management", "higher", "Annualised revenue ÷ configured head count.", industries=["services", "professional"]),
    _k("fixed_asset_turnover", "Fixed-asset turnover", "Efficiency", "ratio", "ratio(annualise(revenue), avg_fixed_assets)", "management", "higher", "Annualised revenue ÷ average net fixed assets."),
    _k("overdue_receivables_pct", "Overdue receivables", "Working capital", "percent", "pct(overdue_receivables, trade_receivables)", "management", "lower", "Overdue debtor bills ÷ trade receivables × 100 (bill-wise data only).", thresholds={"warn": 30, "bad": 50}),
]
for _i, _kp in enumerate(BUILTIN_KPIS):
    _kp.update(builtin=True, enabled=True, sortOrder=(_i + 1) * 10, version=1)

DASHBOARD_DEFAULT = ["revenue", "gross_profit", "gross_margin_pct", "opex", "ebitda", "net_profit", "net_margin_pct", "cash_bank",
                     "trade_receivables", "trade_payables", "inventory", "working_capital", "operating_cash_flow", "current_ratio",
                     "receivable_days", "debt_to_equity"]

_MEASURES = set(MEASURE_NAMES)
_ALLOWED = _MEASURES | {k["code"] for k in BUILTIN_KPIS}
_BY_CODE = {k["code"]: k for k in BUILTIN_KPIS}
_AST: dict[str, object] = {}


def _ast(def_: dict):
    a = _AST.get(def_["code"])
    if a is None:
        allowed = _MEASURES | {k["code"] for k in BUILTIN_KPIS if k["code"] != def_["code"]}
        a = _AST[def_["code"]] = parse(def_["expression"], allowed)
    return a


def eval_kpi(def_: dict, measures: dict[str, Measure], days: int, memo: dict) -> Ev:
    if def_["code"] in memo:
        return memo[def_["code"]]
    ast = _ast(def_)
    memo[def_["code"]] = Ev(None, "unavailable", ["Circular reference"])

    def resolve(name: str) -> Ev:
        mm = measures.get(name)
        if mm:
            return Ev(None if mm.value is None else Decimal(repr(mm.value)), mm.status, list(mm.notes))
        k = _BY_CODE.get(name)
        if k and k["code"] != def_["code"]:
            return eval_kpi(k, measures, days, memo)
        return Ev(None, "unavailable", [f"Unknown field {name}"])

    v = evaluate(ast, resolve, days)
    if ast[0] == "id" and ast[1] in measures:
        v.status = "unavailable" if measures[ast[1]].value is None else measures[ast[1]].status
    memo[def_["code"]] = v
    return v


def _to_num(d: Decimal | None, unit: str):
    if d is None:
        return None
    return float(d.quantize(Decimal(1).scaleb(-(2 if unit == "currency" else 4)), rounding=ROUND_HALF_UP))


def _threshold_state(def_: dict, v):
    th = def_.get("thresholds")
    if v is None or not th or (th.get("warn") is None and th.get("bad") is None):
        return None
    warn, bad = th.get("warn"), th.get("bad")
    if def_["better"] == "lower":
        if bad is not None and v >= bad: return "bad"
        if warn is not None and v >= warn: return "warn"
    else:
        if bad is not None and v <= bad: return "bad"
        if warn is not None and v <= warn: return "warn"
    return "ok"


_DRIVER = {
    "revenue": ["revenue_operating", "revenue_contra"],
    "opex": ["opex_employee", "opex_rent", "opex_freight", "opex_utilities", "opex_selling", "opex_admin", "opex_other"],
    "cogs": ["cogs_purchases", "cogs_direct"],
    "gross_profit": ["revenue_operating", "revenue_contra", "cogs_purchases", "cogs_direct"],
    "net_profit": ["revenue_operating", "revenue_contra", "cogs_purchases", "cogs_direct", "opex_employee", "opex_rent", "opex_freight",
                   "opex_utilities", "opex_selling", "opex_admin", "opex_other", "depreciation", "finance_cost", "income_other", "exceptional", "tax_expense"],
}


def drivers(ctx: Ctx, code: str, cur: DateRange, prev: DateRange) -> list[dict]:
    classes = _DRIVER.get(code)
    if not classes:
        return []
    a, b = profit_and_loss(ctx, cur), profit_and_loss(ctx, prev)

    def flat(p):
        m = {}
        for s in p.sections:
            for l in s["lines"]:
                if not l.get("classCode") or l["classCode"] not in classes:
                    continue
                income = s["key"] in ("revenue", "other_income")
                for c in l.get("children") or []:
                    m[c["key"]] = {"label": c["label"], "amount": c["amount"], "income": income}
        return m
    fa, fb = flat(a), flat(b)
    keys = list(dict.fromkeys([*fa.keys(), *fb.keys()]))
    profit_view = code in ("net_profit", "gross_profit")
    out = []
    for k in keys:
        x = fa.get(k) or fb[k]
        delta = (fa[k]["amount"] if k in fa else 0) - (fb[k]["amount"] if k in fb else 0)
        ch = rupees(-delta if profit_view and not x["income"] else delta)
        if ch != 0:
            out.append({"label": x["label"], "change": ch})
    out.sort(key=lambda d: -abs(d["change"]))
    return out[:4]


def trend_ranges(r: DateRange, n: int = 12) -> list[DateRange]:
    end = month_start(r[1])
    out = []
    for i in range(n - 1, -1, -1):
        frm = add_months(end, -i)
        out.append(DateRange(frm, month_end(frm)))
    return out


def evaluate_kpis(ctx: Ctx, r: DateRange, prev: DateRange | None, codes: list[str] | None = None, trend: bool = False) -> list[dict]:
    selected = [k for k in BUILTIN_KPIS if k["enabled"] and (not codes or k["code"] in codes)]
    cur = compute_measures(ctx, r, prev)
    prev_m = compute_measures(ctx, prev, None) if prev else None
    cur_memo, prev_memo = {}, {}
    trends = [t for t in trend_ranges(r) if t[1] >= ctx.books_from] if trend else []
    trend_ms = [(t, compute_measures(ctx, t, None), {}) for t in trends]
    out = []
    for d in selected:
        c = eval_kpi(d, cur, range_days(r), cur_memo)
        value = _to_num(c.value, d["unit"])
        comparison = None
        if prev and prev_m is not None:
            p = eval_kpi(d, prev_m, range_days(prev), prev_memo)
            pv = _to_num(p.value, d["unit"])
            abs_ch = None if value is None or pv is None else float(Decimal(repr(value)) - Decimal(repr(pv)))
            points = d["unit"] in ("percent", "ratio", "days", "months")
            if points:
                pc = {"pct": None, "note": "Change shown in percentage points" if d["unit"] == "percent" else "Change shown in absolute terms"}
            else:
                pc = pct_change(value, pv)
            comparison = {"previous": pv, "absChange": abs_ch, "pctChange": pc["pct"], "pctNote": pc["note"]}
        out.append({
            "code": d["code"], "name": d["name"], "category": d["category"], "description": d["description"], "unit": d["unit"],
            "better": d["better"], "measureType": d["measureType"], "expression": d["expression"],
            "current": {"value": value, "status": c.status, "unit": d["unit"], "notes": [*c.notes, *([d["limitations"]] if d["limitations"] else [])]},
            "comparison": comparison,
            "trend": [{"period": month_label(t[0]), "value": _to_num(eval_kpi(d, m, range_days(t), memo).value, d["unit"])} for t, m, memo in trend_ms],
            "thresholdState": _threshold_state(d, value),
            "drivers": drivers(ctx, d["code"], r, prev) if prev else None,
            "drill": d["drill"],
        })
    return out
