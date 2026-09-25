"""TAB 2B — Burn anatomy.

Definitions used here, and written into the glossary so they can be argued
with:

  Gross burn   every rupee that left the bank in the month
  Collections  cash received against customer invoices (financing inflows are
               deliberately excluded — drawing debt is not trading performance)
  Net burn     gross burn − collections
  Normalised   the same, with items a human has classified as one-off removed
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import case, func

from app.models import BurnCategory, HeadcountMonth, LedgerEntry
from app.services.common import (
    Ctx, Figure, Status, fmt_inr, month_end, month_start, months_back,
    safe_div, trace,
)


def _month_key(col):
    return func.strftime("%Y-%m", col)


def monthly_burn(ctx: Ctx, months: int = 18, normalised: bool = False) -> list[dict]:
    """Gross burn, collections and net burn for each of the last `months`."""
    starts = months_back(ctx.as_on, months)
    first, last = starts[0], month_end(starts[-1])

    q = ctx.db.query(
        _month_key(LedgerEntry.txn_date).label("m"),
        func.sum(case((LedgerEntry.cash_amount < 0, -LedgerEntry.cash_amount), else_=0.0)).label("out"),
        func.sum(case(((LedgerEntry.cash_amount > 0) & (LedgerEntry.voucher_type == "Receipt"),
                       LedgerEntry.cash_amount), else_=0.0)).label("coll"),
        func.sum(case(((LedgerEntry.cash_amount > 0) & (LedgerEntry.voucher_type != "Receipt"),
                       LedgerEntry.cash_amount), else_=0.0)).label("other_in"),
    ).filter(
        LedgerEntry.entity_id.in_(ctx.entity_ids),
        LedgerEntry.txn_date >= first, LedgerEntry.txn_date <= last,
    )
    if normalised:
        q = q.filter(LedgerEntry.is_one_off.is_(False))
    rows = {r.m: r for r in q.group_by("m").all()}

    out = []
    for s in starts:
        key = s.strftime("%Y-%m")
        r = rows.get(key)
        gross = float(r.out) if r else 0.0
        coll = float(r.coll) if r else 0.0
        other_in = float(r.other_in) if r else 0.0
        out.append({
            "month": s.isoformat(),
            "label": s.strftime("%b-%y"),
            "gross_burn": round(gross, 2),
            "collections": round(coll, 2),
            "other_inflow": round(other_in, 2),
            "net_burn": round(gross - coll, 2),
        })
    return out


def net_burn_average(ctx: Ctx, months: int = 3, normalised: bool = True,
                     offset: int = 0) -> float:
    """Average net burn over the last `months`, optionally offset backwards so
    the prior period can be compared against."""
    series = monthly_burn(ctx, months=months + offset + 1, normalised=normalised)
    window = series[len(series) - offset - months: len(series) - offset] if offset \
        else series[-months:]
    if not window:
        return 0.0
    return sum(x["net_burn"] for x in window) / len(window)


def gross_burn_average(ctx: Ctx, months: int = 3, normalised: bool = True) -> float:
    series = monthly_burn(ctx, months=months, normalised=normalised)
    return sum(x["gross_burn"] for x in series) / len(series) if series else 0.0


def net_burn_figure(ctx: Ctx) -> Figure:
    from app.services.cash import position

    current = net_burn_average(ctx, 3, normalised=True)
    prior = net_burn_average(ctx, 3, normalised=True, offset=3)
    change = (safe_div(current - prior, prior, 0.0) or 0.0) * 100
    arrow = "↑" if change > 0 else "↓"

    # Colour is about tolerance, not direction: a burn that is falling but
    # still leaves under six months of runway is not green.
    months = safe_div(position(ctx)["available"], current, None)
    if months is None:
        status = Status.GREY
    elif months < 6:
        status = Status.RED
    elif months < 12 or change > 8:
        status = Status.AMBER
    else:
        status = Status.GREEN

    return Figure(
        label="Net Burn / Month",
        value=current,
        unit="inr",
        basis="Net burn, 3-month average, normalised (one-off items excluded)",
        as_on=ctx.as_on,
        status=status,
        sub_line=f"3-mth average · {arrow} {abs(change):,.0f}% vs prior 3 mths",
        trace=trace("burn_entries", entity_id=ctx.entity.id,
                    months=3, as_on=ctx.as_on, normalised=True),
    )


def burn_summary(ctx: Ctx) -> dict:
    """SPEC 2B — gross / collections / net, across four comparison windows."""
    def window(n: int, offset_months: int = 0) -> dict:
        series = monthly_burn(ctx, months=n + offset_months, normalised=False)
        sel = series[:n] if offset_months else series[-n:]
        if offset_months:
            sel = series[len(series) - offset_months - n: len(series) - offset_months]
        g = sum(x["gross_burn"] for x in sel) / max(len(sel), 1)
        c = sum(x["collections"] for x in sel) / max(len(sel), 1)
        return {"gross_burn": round(g, 2), "collections": round(c, 2),
                "net_burn": round(g - c, 2)}

    this_month = monthly_burn(ctx, months=1, normalised=False)[-1]
    same_month_ly = monthly_burn(ctx, months=13, normalised=False)[0]

    return {
        "this_month": {"label": this_month["label"], **{k: this_month[k] for k in
                       ("gross_burn", "collections", "net_burn")}},
        "avg_3m": {"label": "3-month average", **window(3)},
        "avg_6m": {"label": "6-month average", **window(6)},
        "same_month_last_year": {"label": same_month_ly["label"],
                                 **{k: same_month_ly[k] for k in
                                    ("gross_burn", "collections", "net_burn")}},
        "basis": "Cash basis, from the ledger. Financing inflows are excluded from collections.",
        "as_on": ctx.as_on.isoformat(),
    }


def recurring_vs_one_off(ctx: Ctx, months: int = 3) -> dict:
    """SPEC 2B — the split, and the visible list of what was excluded, with
    the name of whoever classified it."""
    starts = months_back(ctx.as_on, months)
    first, last = starts[0], month_end(starts[-1])

    total = (ctx.db.query(func.sum(-LedgerEntry.cash_amount))
             .filter(LedgerEntry.entity_id.in_(ctx.entity_ids),
                     LedgerEntry.cash_amount < 0,
                     LedgerEntry.txn_date >= first,
                     LedgerEntry.txn_date <= last).scalar() or 0.0)

    one_off_rows = (ctx.db.query(LedgerEntry)
                    .filter(LedgerEntry.entity_id.in_(ctx.entity_ids),
                            LedgerEntry.is_one_off.is_(True),
                            LedgerEntry.txn_date >= first,
                            LedgerEntry.txn_date <= last)
                    .order_by(LedgerEntry.txn_date.desc()).all())
    one_off_total = sum(-e.cash_amount for e in one_off_rows if e.cash_amount < 0)

    # Also show every one-off in the last 18 months so the reclassify view is
    # useful, not just the current window.
    wide_start = months_back(ctx.as_on, 18)[0]
    wide = (ctx.db.query(LedgerEntry)
            .filter(LedgerEntry.entity_id.in_(ctx.entity_ids),
                    LedgerEntry.is_one_off.is_(True),
                    LedgerEntry.txn_date >= wide_start)
            .order_by(LedgerEntry.txn_date.desc()).all())

    return {
        "window_months": months,
        "total_burn": round(total, 2),
        "one_off": round(one_off_total, 2),
        "recurring": round(total - one_off_total, 2),
        "one_off_pct": round((safe_div(one_off_total, total, 0.0) or 0.0) * 100, 1),
        "excluded_items": [{
            "id": e.id,
            "date": e.txn_date.isoformat(),
            "month": e.txn_date.strftime("%b-%y"),
            "party": e.party,
            "narration": e.one_off_note or e.narration,
            "amount": round(-e.cash_amount, 2),
            "direction": "outflow" if e.cash_amount < 0 else "inflow",
            "category": e.burn_category,
            "classified_by": e.classified_by or "—",
            "in_current_window": first <= e.txn_date <= last,
        } for e in wide],
        "basis": f"{months}-month window ending {last:%d-%b-%y}. An item is one-off only "
                 f"when a named person has classified it as such.",
    }


def burn_by_category(ctx: Ctx) -> dict:
    """SPEC 2B — the nine top-level categories with this month, 3-month
    average, share, nature, plan comparison and trend."""
    from app.services.variance import plan_outflow_for_month

    this_start = month_start(ctx.as_on)
    this_end = month_end(ctx.as_on)
    three = months_back(ctx.as_on, 3)
    prev3 = months_back(ctx.as_on, 6)[:3]

    def totals(a: date, b: date) -> dict[str, float]:
        rows = (ctx.db.query(LedgerEntry.burn_category,
                             func.sum(-LedgerEntry.cash_amount))
                .filter(LedgerEntry.entity_id.in_(ctx.entity_ids),
                        LedgerEntry.cash_amount < 0,
                        LedgerEntry.txn_date >= a, LedgerEntry.txn_date <= b)
                .group_by(LedgerEntry.burn_category).all())
        return {(k or BurnCategory.OTHER): float(v or 0.0) for k, v in rows}

    this_m = totals(this_start, this_end)
    avg3 = totals(three[0], month_end(three[-1]))
    prev = totals(prev3[0], month_end(prev3[-1]))

    nature = dict(ctx.db.query(LedgerEntry.burn_category, LedgerEntry.cost_nature)
                  .filter(LedgerEntry.entity_id.in_(ctx.entity_ids),
                          LedgerEntry.cost_nature.isnot(None)).distinct().all())

    plan = plan_outflow_for_month(ctx, this_start)
    total_this = sum(this_m.values()) or 1.0

    rows = []
    for cat in BurnCategory.ALL:
        cur = this_m.get(cat, 0.0)
        a3 = avg3.get(cat, 0.0) / 3
        p3 = prev.get(cat, 0.0) / 3
        planned = plan.get(cat)
        rows.append({
            "category": cat,
            "this_month": round(cur, 2),
            "avg_3m": round(a3, 2),
            "pct_of_total": round(cur / total_this * 100, 1),
            "cost_nature": nature.get(cat) or _default_nature(cat),
            "plan": round(planned, 2) if planned is not None else None,
            "vs_plan": round(cur - planned, 2) if planned is not None else None,
            "trend": "up" if a3 > p3 * 1.03 else "down" if a3 < p3 * 0.97 else "flat",
            "trend_pct": round((safe_div(a3 - p3, p3, 0.0) or 0.0) * 100, 1),
            "trace": trace("burn_entries", entity_id=ctx.entity.id,
                           category=cat, date_from=this_start, date_to=this_end),
        })
    rows.sort(key=lambda r: r["this_month"], reverse=True)
    return {
        "month": this_start.isoformat(),
        "month_label": this_start.strftime("%b-%y"),
        "total": round(total_this, 2),
        "rows": rows,
        "basis": f"Cash outflows for {this_start:%b-%y}, classified to nine top-level "
                 f"categories. Plan column is the active plan version.",
    }


def _default_nature(cat: str) -> str:
    from app.models import CostNature
    return {
        BurnCategory.PEOPLE: CostNature.FIXED,
        BurnCategory.FACILITIES: CostNature.FIXED,
        BurnCategory.FINANCE_COST: CostNature.FIXED,
        BurnCategory.TECH: CostNature.VARIABLE,
        BurnCategory.DELIVERY: CostNature.VARIABLE,
        BurnCategory.STATUTORY: CostNature.VARIABLE,
        BurnCategory.MARKETING: CostNature.DISCRETIONARY,
        BurnCategory.PROFESSIONAL: CostNature.DISCRETIONARY,
    }.get(cat, CostNature.VARIABLE)


def burn_per_unit(ctx: Ctx, months: int = 12) -> dict:
    """SPEC 2B — burn per head and burn per rupee of revenue, trended."""
    series = monthly_burn(ctx, months=months, normalised=True)
    hc = {h.month: h for h in ctx.db.query(HeadcountMonth)
          .filter(HeadcountMonth.entity_id.in_(ctx.entity_ids)).all()}

    rows = []
    for s in series:
        m = date.fromisoformat(s["month"])
        head = hc.get(m)
        heads = head.actual_headcount if head else None
        rows.append({
            "month": s["month"], "label": s["label"],
            "headcount": heads,
            "burn_per_head": round(s["gross_burn"] / heads, 2) if heads else None,
            "burn_to_revenue": round(safe_div(s["gross_burn"], s["collections"], 0.0) or 0.0, 2),
        })

    latest = rows[-1] if rows else {}
    return {
        "rows": rows,
        "current_burn_per_head": latest.get("burn_per_head"),
        "current_burn_to_revenue": latest.get("burn_to_revenue"),
        "basis": "Gross burn ÷ actual headcount, and gross burn ÷ cash collections, "
                 "both on a monthly basis.",
    }


def where_the_cash_went(ctx: Ctx, months: int = 3) -> dict:
    """SPEC 1, Band 5 right chart — horizontal bars by category with
    Fixed / Variable / Discretionary shading."""
    starts = months_back(ctx.as_on, months)
    first, last = starts[0], month_end(starts[-1])

    rows = (ctx.db.query(LedgerEntry.burn_category, LedgerEntry.cost_nature,
                         func.sum(-LedgerEntry.cash_amount))
            .filter(LedgerEntry.entity_id.in_(ctx.entity_ids),
                    LedgerEntry.cash_amount < 0,
                    LedgerEntry.txn_date >= first, LedgerEntry.txn_date <= last)
            .group_by(LedgerEntry.burn_category, LedgerEntry.cost_nature).all())

    agg: dict[str, dict] = {}
    for cat, nat, amt in rows:
        cat = cat or BurnCategory.OTHER
        d = agg.setdefault(cat, {"category": cat, "total": 0.0,
                                 "Fixed": 0.0, "Variable": 0.0, "Discretionary": 0.0})
        d["total"] += float(amt or 0.0)
        d[nat or _default_nature(cat)] = d.get(nat or _default_nature(cat), 0.0) + float(amt or 0.0)

    out = sorted(agg.values(), key=lambda r: r["total"], reverse=True)
    total = sum(r["total"] for r in out) or 1.0
    for r in out:
        r["pct"] = round(r["total"] / total * 100, 1)
        r["total"] = round(r["total"], 2)
        for k in ("Fixed", "Variable", "Discretionary"):
            r[k] = round(r.get(k, 0.0), 2)
        r["trace"] = trace("burn_entries", entity_id=ctx.entity.id,
                           category=r["category"], date_from=first, date_to=last)

    return {
        "period": f"{first:%b-%y} to {last:%b-%y}",
        "total": round(total, 2),
        "rows": out,
        "basis": f"Cash outflows over the {months} months to {last:%d-%b-%y}.",
    }
