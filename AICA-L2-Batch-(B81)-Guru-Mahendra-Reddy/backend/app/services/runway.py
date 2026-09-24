"""TAB 2A — Runway: how long the cash lasts, under which assumption, and why
the answer moved since last month."""
from __future__ import annotations

from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from sqlalchemy import func

from app.config import settings
from app.models import BurnCategory, LedgerEntry, NextRaise, PlanLine, Setting
from app.services.common import (
    Ctx, Figure, Status, fmt_date, fmt_inr, month_end, month_start, months_back,
    safe_div, trace,
)


def _setting(ctx: Ctx, key: str, default: float) -> float:
    row = (ctx.db.query(Setting)
           .filter(Setting.entity_id.in_(ctx.entity_ids + [None]), Setting.key == key)
           .first())
    try:
        return float(row.value) if row else default
    except (TypeError, ValueError):
        return default


def cashout_date(as_on: date, months: float | None) -> date | None:
    if months is None or months <= 0:
        return as_on
    whole = int(months)
    days = int(round((months - whole) * 30.4))
    return as_on + relativedelta(months=whole) + timedelta(days=days)


def runway_summary(ctx: Ctx) -> dict:
    """The four-row runway table (SPEC 2A) plus the headline current figure."""
    from app.services.burn import net_burn_average, monthly_burn
    from app.services.cash import position
    from app.services.variance import active_plan, board_plan

    pos = position(ctx)
    available = pos["available"]

    current_burn = net_burn_average(ctx, 3, normalised=True)
    cut_pct = _setting(ctx, "austerity_cut_pct", 35.0)

    # Committed plan — the forward net outflow the active plan actually assumes
    committed_burn = _plan_forward_burn(ctx, active_plan(ctx)) or current_burn
    board_burn = _plan_forward_burn(ctx, board_plan(ctx)) or current_burn

    discretionary = _discretionary_monthly(ctx)
    austerity_burn = max(current_burn - discretionary * cut_pct / 100, 1.0)

    def row(name: str, burn: float, assumes: str, key: str) -> dict:
        months = safe_div(available, burn, None)
        return {
            "key": key,
            "scenario": name,
            "monthly_burn": round(burn, 2),
            "months": round(months, 1) if months is not None else None,
            "cashout_date": (cashout_date(ctx.as_on, months).isoformat()
                             if months is not None else None),
            "assumes": assumes,
        }

    rows = [
        row("Current run-rate", current_burn,
            "The last three months repeat, with one-off items excluded and no change to hiring or spend.",
            "current"),
        row("Committed plan", committed_burn,
            "Spend follows the active plan, including hires already approved and contracts already signed.",
            "committed"),
        row("Austerity case", austerity_burn,
            f"Hiring frozen and discretionary spend cut {cut_pct:.0f}%. Fixed and statutory costs unchanged.",
            "austerity"),
        row("Board-approved plan", board_burn,
            "Spend and collections exactly as tabled to the board.",
            "board"),
    ]

    current = rows[0]
    months = current["months"]
    trigger_months = _setting(ctx, "fundraise_lead_months", settings.FUNDRAISE_LEAD_MONTHS)
    trigger = (cashout_date(ctx.as_on, months - trigger_months)
               if months is not None else None)

    return {
        "cash_available": round(available, 2),
        "rows": rows,
        "current": current,
        "fundraise_trigger_date": trigger.isoformat() if trigger else None,
        "fundraise_trigger_passed": bool(trigger and trigger <= ctx.today),
        "fundraise_lead_months": trigger_months,
        "floor": ctx.floor,
        "basis": "Cash Available ÷ net burn per month, on the assumption stated in each row. "
                 "Undrawn credit is not counted as cash.",
        "as_on": ctx.as_on.isoformat(),
    }


def _plan_forward_burn(ctx: Ctx, plan) -> float | None:
    """Average monthly net outflow the plan assumes from the as-on month on."""
    if not plan:
        return None
    start = month_start(ctx.as_on) + relativedelta(months=1)
    rows = (ctx.db.query(PlanLine.line_type, func.sum(PlanLine.amount))
            .filter(PlanLine.plan_id == plan.id, PlanLine.month >= start,
                    PlanLine.line_type.in_(["inflow", "outflow"]))
            .group_by(PlanLine.line_type).all())
    d = {k: float(v or 0.0) for k, v in rows}
    n = (ctx.db.query(func.count(func.distinct(PlanLine.month)))
         .filter(PlanLine.plan_id == plan.id, PlanLine.month >= start).scalar() or 0)
    if not n:
        return None
    net = (d.get("outflow", 0.0) - d.get("inflow", 0.0)) / n
    return max(net, 1.0)


def _discretionary_monthly(ctx: Ctx) -> float:
    from app.models import CostNature
    starts = months_back(ctx.as_on, 3)
    total = (ctx.db.query(func.sum(-LedgerEntry.cash_amount))
             .filter(LedgerEntry.entity_id.in_(ctx.entity_ids),
                     LedgerEntry.cash_amount < 0,
                     LedgerEntry.cost_nature == CostNature.DISCRETIONARY,
                     LedgerEntry.txn_date >= starts[0],
                     LedgerEntry.txn_date <= month_end(starts[-1])).scalar() or 0.0)
    return float(total) / 3


def runway_figure(ctx: Ctx) -> Figure:
    s = runway_summary(ctx)
    cur = s["current"]["months"]
    others = {r["key"]: r["months"] for r in s["rows"]}
    return Figure(
        label="Runway",
        value=cur,
        unit="months",
        basis="Cash Available ÷ 3-month average normalised net burn",
        as_on=ctx.as_on,
        status=Status.RED if (cur or 0) < 6 else Status.AMBER if (cur or 0) < 12 else Status.GREEN,
        sub_line=(f"Current {others.get('current', 0):.1f} · "
                  f"Committed {others.get('committed', 0):.1f} · "
                  f"Austerity {others.get('austerity', 0):.1f}"),
        trace=trace("runway_basis", entity_id=ctx.entity.id, as_on=ctx.as_on),
    )


def cashout_figure(ctx: Ctx) -> Figure:
    s = runway_summary(ctx)
    d = s["current"]["cashout_date"]
    trigger = s["fundraise_trigger_date"]
    passed = s["fundraise_trigger_passed"]
    return Figure(
        label="Cash-Out Date",
        value=None,
        unit="date",
        basis="Current run-rate, with one-off items excluded",
        as_on=ctx.as_on,
        status=Status.RED if passed else Status.AMBER,
        sub_line=(f"Fundraise trigger: {fmt_date(date.fromisoformat(trigger))}"
                  + (" — passed" if passed else "") if trigger else "Fundraise trigger: —"),
        trace=trace("runway_basis", entity_id=ctx.entity.id, as_on=ctx.as_on),
    ).to_dict() | {"display": fmt_date(date.fromisoformat(d)) if d else "—",
                   "date": d}


def runway_movement(ctx: Ctx) -> dict:
    """SPEC 2A — 'Runway was X months last month, now Y.' The waterfall the
    board asks for when the number moves."""
    from app.services.burn import monthly_burn, net_burn_average
    from app.services.cash import monthly_cash_history
    from app.services.variance import active_plan, plan_outflow_for_month

    hist = monthly_cash_history(ctx, months=3)
    if len(hist) < 2 or hist[-2]["closing_cash"] is None:
        return {"bars": [], "from_months": None, "to_months": None}

    # Runway is always measured on UNRESTRICTED cash, so the movement chart
    # has to strip the restricted balance out too — otherwise this chart and
    # the headline runway figure quietly use two different numerators.
    from app.services.cash import position
    restricted = position(ctx)["restricted"]
    prev_cash = float(hist[-2]["closing_cash"]) - restricted
    now_cash = float(hist[-1]["closing_cash"] or 0.0) - restricted

    prev_burn = net_burn_average(ctx, 3, normalised=True, offset=1) or 1.0
    now_burn = net_burn_average(ctx, 3, normalised=True) or 1.0

    from_months = prev_cash / prev_burn
    to_months = now_cash / now_burn

    this_month = month_start(ctx.as_on)
    actual = monthly_burn(ctx, months=1, normalised=False)[-1]
    plan_out = sum(plan_outflow_for_month(ctx, this_month).values())
    plan_in = 0.0
    plan = active_plan(ctx)
    if plan:
        plan_in = float(ctx.db.query(func.sum(PlanLine.amount))
                        .filter(PlanLine.plan_id == plan.id, PlanLine.month == this_month,
                                PlanLine.line_type == "inflow").scalar() or 0.0)

    collections_delta = actual["collections"] - plan_in
    spend_delta = plan_out - actual["gross_burn"]        # positive = spent less than plan
    one_off = (ctx.db.query(func.sum(LedgerEntry.cash_amount))
               .filter(LedgerEntry.entity_id.in_(ctx.entity_ids),
                       LedgerEntry.is_one_off.is_(True),
                       LedgerEntry.txn_date >= this_month,
                       LedgerEntry.txn_date <= month_end(this_month)).scalar() or 0.0)
    funding = actual["other_inflow"] - max(float(one_off), 0.0)

    def to_m(rupees: float) -> float:
        return round(rupees / now_burn, 2)

    bars = [
        {"label": f"Runway at {hist[-2]['as_on'][:10]}", "type": "start",
         "value": round(from_months, 1)},
        {"label": "Collections vs expected", "type": "delta", "value": to_m(collections_delta)},
        {"label": "Spend vs plan", "type": "delta", "value": to_m(spend_delta)},
        {"label": "One-off items", "type": "delta", "value": to_m(float(one_off))},
        {"label": "New funding", "type": "delta", "value": to_m(funding)},
    ]
    accounted = sum(b["value"] for b in bars[1:])
    residual = round(to_months - from_months - accounted, 2)
    if abs(residual) > 0.05:
        bars.append({"label": "Change in burn rate", "type": "delta", "value": residual})
    bars.append({"label": f"Runway at {hist[-1]['as_on'][:10]}", "type": "end",
                 "value": round(to_months, 1)})

    return {
        "from_months": round(from_months, 1),
        "to_months": round(to_months, 1),
        "change_months": round(to_months - from_months, 1),
        "bars": bars,
        "narrative": (f"Runway was {from_months:.1f} months last month, now "
                      f"{to_months:.1f}."),
        "basis": "Movement decomposed against the active plan for the month, converted "
                 "to months at the current net burn rate.",
    }


def milestones(ctx: Ctx) -> dict:
    """SPEC 2A — runway to the next funding milestone vs runway to zero."""
    s = runway_summary(ctx)
    to_zero = s["current"]["months"]
    raise_row = (ctx.db.query(NextRaise)
                 .filter(NextRaise.entity_id.in_(ctx.entity_ids),
                         NextRaise.is_active.is_(True)).first())
    if not raise_row:
        return {"to_zero_months": to_zero, "to_milestone_months": None, "gap_months": None}

    months_to_close = max((raise_row.target_close_date - ctx.as_on).days / 30.4, 0)
    gap = (to_zero or 0) - months_to_close
    return {
        "to_zero_months": round(to_zero, 1) if to_zero else None,
        "cashout_date": s["current"]["cashout_date"],
        "milestone_name": f"{raise_row.instrument} close",
        "milestone_date": raise_row.target_close_date.isoformat(),
        "to_milestone_months": round(months_to_close, 1),
        "gap_months": round(gap, 1),
        "covered": gap >= 0,
        "note": (f"Cash lasts {gap:.1f} months beyond the target close."
                 if gap >= 0 else
                 f"Cash runs out {abs(gap):.1f} months before the target close of "
                 f"{fmt_date(raise_row.target_close_date)}."),
        "trigger_date": s["fundraise_trigger_date"],
        "trigger_passed": s["fundraise_trigger_passed"],
        "days_until_trigger": ((date.fromisoformat(s["fundraise_trigger_date"]) - ctx.today).days
                               if s["fundraise_trigger_date"] else None),
    }
