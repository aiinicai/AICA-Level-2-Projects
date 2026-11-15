"""Report builders: the exact JSON the screens receive (ported from the route handlers in routes-analytics.ts).

Each function takes plain filter values and returns a dict that is ready to send as JSON. Amounts are rupees.
"""
from __future__ import annotations

import math

from .analytics import (cost_analysis, ledger_statement, monthly_series, product_analysis, revenue_analysis, voucher_detail)
from .cashflow_ageing import ageing
from .context import Ctx, balances_at, make_ctx, rupees
from .kpi import DASHBOARD_DEFAULT, evaluate_kpis
from .periods import (DateRange, add_days, comparison_range, days_between, fy_of, fy_quarter, is_valid_iso, month_end, month_label,
                      months_in)
from .statements import PnL, balance_sheet, profit_and_loss
from .taxonomy import CLASS_BY_CODE
from ..shared_industry import profile_of

r2 = rupees


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def lines_to_rupees(lines: list[dict]) -> list[dict]:
    out = []
    for l in lines:
        n = {**l, "amount": math.floor(l["amount"] + 0.5) / 100 + 0}
        if "children" in l and l["children"] is not None:
            n["children"] = lines_to_rupees(l["children"])
        out.append(n)
    return out


class Filters:
    def __init__(self, ctx: Ctx, range_: DateRange, prev: DateRange | None, compare: str):
        self.ctx, self.range, self.prev, self.compare = ctx, range_, prev, compare


def make_filters(store, company_id: int, frm: str | None = None, to: str | None = None, compare: str | None = None,
                 cost_centre: str | None = None) -> Filters:
    from .context import NotFoundError
    for v in (frm, to):
        if v and not is_valid_iso(v):
            raise ApiError(400, "Expected a valid date (YYYY-MM-DD)")
    if compare and compare not in ("previous_period", "previous_year", "none"):
        raise ApiError(400, "compare: invalid value")
    try:
        ctx = make_ctx(store, company_id, cost_centre or None)
    except NotFoundError as e:
        raise ApiError(404, str(e))
    latest = ctx.data_to or ctx.books_from
    fy = fy_of(latest, ctx.company["fy_start_month"])
    ytd_end = month_end(latest) if month_end(latest) < fy.to else fy.to
    rng = DateRange(frm or fy.from_, to or (fy_of(frm, ctx.company["fy_start_month"]).to if frm else ytd_end))
    if rng[0] > rng[1]:
        raise ApiError(400, '"from" must be on or before "to"')
    if days_between(rng[0], rng[1]) > 3700:
        raise ApiError(400, "Date range too long (max 10 years)")
    cmp_ = compare or "previous_year"
    return Filters(ctx, rng, comparison_range(rng, cmp_), cmp_)


def _rng(r: DateRange | None):
    return None if r is None else {"from": r[0], "to": r[1]}


# ------------------------------------------------------------------------------------------------ P&L
def _subtotals(p: PnL) -> list[dict]:
    f = p.figures
    rev = f["revenue"].paise
    gm = round_half_up((f["grossProfit"].paise / rev) * 10000) / 100 if rev is not None and rev > 0 and f["grossProfit"].paise is not None else None

    def row(key, label, after, fg):
        return {"key": key, "label": label, "after": after, "kind": "amount", "value": r2(fg.paise), "status": fg.status}
    return [row("gross_profit", "Gross profit", "cogs", f["grossProfit"]),
            {"key": "gross_margin", "label": "Gross margin %", "after": "cogs", "kind": "percent", "value": gm, "status": f["grossProfit"].status},
            row("ebitda", "EBITDA", "opex", f["ebitda"]), row("ebit", "EBIT (operating profit)", "da", f["ebit"]),
            row("ebt", "EBT (profit before tax)", "exceptional", f["pbt"]), row("eat", "EAT (net profit after tax)", "tax", f["netProfit"])]


def round_half_up(x: float) -> int:
    return math.floor(x + 0.5)


def pnl_out(p: PnL) -> dict:
    return {
        "range": _rng(p.range), "subtotals": _subtotals(p),
        "sections": [{**s, "total": r2(s["total"]), "lines": lines_to_rupees(s["lines"])} for s in p.sections],
        "figures": {k: {"value": r2(f.paise), "status": f.status, "notes": f.notes} for k, f in p.figures.items()},
        "unclassified": [{**u, "movement": r2(u["movement"])} for u in p.unclassified],
        "reliability": p.reliability, "stockSource": p.stock_source,
    }


def pnl_report(f: Filters, view: str = "compare") -> dict:
    ctx = f.ctx
    cur = profit_and_loss(ctx, f.range)
    columns: list[tuple[str, DateRange]] = []
    if view == "monthly":
        for m in months_in(f.range):
            columns.append((month_label(m), DateRange(f.range[0] if m < f.range[0] else m, f.range[1] if month_end(m) > f.range[1] else month_end(m))))
    if view == "quarterly":
        qs: dict[str, DateRange] = {}
        for m in months_in(f.range):
            k = f"Q{fy_quarter(m, ctx.company['fy_start_month'])} {m[:4]}"
            to = f.range[1] if month_end(m) > f.range[1] else month_end(m)
            prev = qs.get(k)
            qs[k] = DateRange(prev[0] if prev else (f.range[0] if m < f.range[0] else m), to)
        columns = list(qs.items())
    return {
        "current": pnl_out(cur), "previous": pnl_out(profit_and_loss(ctx, f.prev)) if f.prev else None, "prevRange": _rng(f.prev),
        "columns": [{"label": lbl, "range": _rng(r), "pnl": pnl_out(profit_and_loss(ctx, r))} for lbl, r in columns],
        "budget": None,
        "signConvention": "Income and expenses are both shown as positive amounts in their normal direction; contra items (returns, discounts, closing stock) appear negative. Underlying data is stored debit-positive.",
        "costCentreNote": "Filtered to one cost centre: only cost-centre allocations are included; stock adjustments and unallocated amounts are excluded."
        if ctx.cost_centre_id is not None else None,
    }


def pnl_revenue(f: Filters) -> dict:
    return revenue_analysis(f.ctx, f.range, f.prev)


def pnl_costs(f: Filters) -> dict:
    return cost_analysis(f.ctx, f.range, f.prev)


def pnl_products(f: Filters) -> dict:
    return product_analysis(f.ctx, f.range, f.prev)


# ------------------------------------------------------------------------------------------------ balance sheet and cash flow
def bs_report(f: Filters, as_of: str | None = None) -> dict:
    ctx = f.ctx
    if as_of and not is_valid_iso(as_of):
        as_of = None
    as_of = as_of or f.range[1]
    cmp_as_of = f.prev[1] if f.prev else add_days(f.range[0], -1)

    def out(b: dict) -> dict:
        return {"asOf": b["asOf"], "notes": b["notes"],
                "sections": [{**s, "total": r2(s["total"]), "lines": lines_to_rupees(s["lines"])} for s in b["sections"]],
                "totals": {k: (r2(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v) for k, v in b["totals"].items()}}
    return {"current": out(balance_sheet(ctx, as_of)), "comparison": out(balance_sheet(ctx, cmp_as_of)),
            "comparisonLabel": "Comparison period end" if f.prev else "Opening (start of period)"}


def bs_analysis(f: Filters) -> dict:
    from .balance_analysis import balance_sheet_analysis
    return balance_sheet_analysis(f.ctx, f.range, f.prev)


def cashflow_report(f: Filters) -> dict:
    from .cashflow_ageing import cash_flow
    cf = cash_flow(f.ctx, f.range)
    return {**cf, "range": _rng(f.range), "opening": r2(cf["opening"]), "closing": r2(cf["closing"]), "net": r2(cf["net"]), "check": r2(cf["check"]),
            "byCategory": {k: r2(v) for k, v in cf["byCategory"].items()},
            "byClass": [{**c, "inflow": r2(c["inflow"]), "outflow": r2(c["outflow"])} for c in cf["byClass"]],
            "monthly": [{"month": m["month"], "operating": r2(m["operating"]), "investing": r2(m["investing"]), "financing": r2(m["financing"]),
                         "unclassified": r2(m["unclassified"])} for m in cf["monthly"]]}


# ------------------------------------------------------------------------------------------------ dashboard
def dashboard(f: Filters) -> dict:
    ctx = f.ctx
    prof = profile_of(ctx.company["industry_profile"])
    codes = ctx.settings.get("dashboardKpis") or list(dict.fromkeys([*DASHBOARD_DEFAULT, *prof["kpis"]]))
    kpis = evaluate_kpis(ctx, f.range, f.prev, codes=codes, trend=True)
    by_code = {k["code"]: k for k in kpis}
    ordered = [by_code[c] for c in codes if c in by_code]
    series = monthly_series(ctx, f.range)
    pl = profit_and_loss(ctx, f.range)
    prev_series = monthly_series(ctx, f.prev) if f.prev else []
    composition = {
        "expenses": [x for x in ({"label": s["label"], "value": r2(s["total"])} for s in pl.sections
                                 if s["key"] in ("cogs", "opex", "da", "finance", "exceptional", "tax")) if x["value"]],
        "revenue": [{"label": l["label"], "value": r2(l["amount"])} for l in
                    [c for ln in next((s for s in pl.sections if s["key"] == "revenue"), {"lines": []})["lines"] for c in ln.get("children") or []][:8]],
    }
    exp_children = [c for s in pl.sections if s["key"] in ("opex", "da", "finance", "exceptional") for ln in s["lines"] for c in ln.get("children") or []]
    exp_children.sort(key=lambda c: -c["amount"])
    top_exp = [{"label": l["label"], "value": r2(l["amount"]), "ledgerId": l.get("ledgerId")} for l in exp_children[:8]]
    cc = ctx.cost_centre_id is None
    ar = ageing(ctx, "receivable", f.range[1]) if cc else None
    ap = ageing(ctx, "payable", f.range[1]) if cc else None

    def expo(a):
        t = a["totals"]
        return {"total": r2(t["ledgerBalance"]), "overdue": r2(t["overdue"]),
                "buckets": [{"bucket": k, "value": r2(v)} for k, v in t["buckets"].items()], "coverage": t["billwiseCoveragePct"]}
    return {
        "range": _rng(f.range), "prev": _rng(f.prev), "compare": f.compare, "kpis": ordered, "series": series,
        "prevSeries": [{"label": p["label"], "revenue": p["revenue"], "netProfit": p["netProfit"]} for p in prev_series],
        "composition": composition, "topRevenue": composition["revenue"], "topExpenses": top_exp,
        "exposure": {"receivables": expo(ar), "payables": expo(ap), "bucketOrder": ar["bucketLabels"]} if ar and ap else None,
        "insights": [], "insightCount": 0, "dq": {"high": 0, "medium": 0, "top": []},
        "reliability": pl.reliability, "stockSource": pl.stock_source, "inventoryMode": ctx.inventory_mode,
        "profile": {"code": prof["code"], "label": prof["label"], "notes": prof["notes"], "modules": prof["modules"]},
    }


def kpis_report(f: Filters, codes: list[str] | None = None, trend: bool = False) -> list[dict]:
    return evaluate_kpis(f.ctx, f.range, f.prev, codes=codes, trend=trend)


# ------------------------------------------------------------------------------------------------ receivables & payables
def ageing_report(f: Filters, kind: str = "receivable", as_of: str | None = None, buckets: str | None = None) -> dict:
    ctx = f.ctx
    if kind not in ("receivable", "payable"):
        raise ApiError(400, "kind: invalid value")
    if as_of and not is_valid_iso(as_of):
        raise ApiError(400, "asOf: Expected a valid date (YYYY-MM-DD)")
    as_of = as_of or f.range[1]
    bnds = sorted(int(x) for x in buckets.split(",")) if buckets else None
    a = ageing(ctx, kind, as_of, bnds)
    prev_a = ageing(ctx, kind, f.prev[1], bnds) if f.prev else None
    trend = []
    for m in months_in(f.range):
        d = f.range[1] if month_end(m) > f.range[1] else month_end(m)
        x = ageing(ctx, kind, d, bnds)
        trend.append({"month": month_label(m), "total": r2(x["totals"]["ledgerBalance"]), "overdue": r2(x["totals"]["overdue"])})
    notes = ctx.store.rows("SELECT * FROM collection_notes WHERE company_id = ? ORDER BY id DESC LIMIT 500", [ctx.cid])
    upcoming = sorted([{"party": b["party"], "bill": b["billName"], "dueDate": b["dueDate"], "amount": r2(b["amount"])}
                       for b in a["bills"] if b["dueDate"] and b["dueDate"] > as_of and b["dueDate"] <= add_days(as_of, 60) and b["amount"] > 0],
                      key=lambda u: u["dueDate"])
    t = a["totals"]
    totals = {k: (r2(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and not k.endswith("Pct") and k != "parties" else v)
              for k, v in t.items()}
    totals["buckets"] = {k: r2(v) for k, v in t["buckets"].items()}
    parties = []
    for p in a["parties"]:
        parties.append({**p, "ledgerBalance": r2(p["ledgerBalance"]), "billTotal": r2(p["billTotal"]), "onAccount": r2(p["onAccount"]),
                        "unreconciled": r2(p["unreconciled"]), "overdue": r2(p["overdue"]), "notDue": r2(p["notDue"]),
                        "creditLimit": r2(p["creditLimit"]), "buckets": {k: r2(v) for k, v in p["buckets"].items()},
                        "creditUtilisationPct": (p["ledgerBalance"] / p["creditLimit"]) * 100 if p["creditLimit"] else None})
    prio = [{"party": b["party"], "ledgerId": b["ledgerId"], "bill": b["billName"], "amount": r2(b["amount"]), "daysOverdue": b["daysOverdue"],
             "score": (b["amount"] / 100) * math.log2(2 + (b["daysOverdue"] or 0))}
            for b in a["bills"] if b["amount"] > 0 and (b["daysOverdue"] or 0) > 0]
    prio.sort(key=lambda x: -x["score"])
    return {
        "kind": kind, "asOf": as_of, "bucketLabels": a["bucketLabels"], "notes": a["notes"], "totals": totals,
        "previousTotals": {"ledgerBalance": r2(prev_a["totals"]["ledgerBalance"]), "overdue": r2(prev_a["totals"]["overdue"]), "asOf": f.prev[1]} if prev_a else None,
        "parties": parties,
        "bills": [{**b, "amount": r2(b["amount"]), "original": r2(b["original"]), "settled": r2(b["settled"])} for b in a["bills"][:2000]],
        "trend": trend, "upcoming": upcoming[:200], "collectionNotes": notes, "priority": prio[:25],
        "priorityRule": "Priority score = outstanding amount × log2(2 + days overdue): large and old bills first.",
    }


# ------------------------------------------------------------------------------------------------ ledgers and vouchers
def ledgers_list(f: Filters, search: str = "") -> list[dict]:
    ctx = f.ctx
    q = (search or "").lower()
    bal = balances_at(ctx, f.range[1])
    out = [{"id": e.ledger_id, "name": e.name, "group": e.group_name, "classCode": e.code, "status": e.status, "balance": r2(bal.get(e.ledger_id, 0))}
           for e in ctx.chart.entries.values() if not q or q in e.name.lower() or q in (e.group_name or "").lower()]
    return out[:500]


def ledger_report(f: Filters, ledger_id: int, page: int = 1) -> dict:
    s = ledger_statement(f.ctx, ledger_id, f.range, max(1, page))
    if s is None:
        raise ApiError(404, "Ledger not found")
    return s


def voucher_report(f: Filters, voucher_id: int) -> dict:
    v = voucher_detail(f.ctx, voucher_id)
    if v is None:
        raise ApiError(404, "Voucher not found")
    return v
