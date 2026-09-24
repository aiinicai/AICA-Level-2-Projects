"""TAB 9 — Capital & Debt. Amber before breach, not after."""
from __future__ import annotations

from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from sqlalchemy import func

from app.models import Covenant, Facility, FundingRound, NextRaise, RepaymentScheduleItem
from app.services.common import (
    Ctx, Status, fmt_date, fmt_inr, month_start, safe_div,
)


def facilities(ctx: Ctx) -> dict:
    rows = (ctx.db.query(Facility)
            .filter(Facility.entity_id.in_(ctx.entity_ids))
            .order_by(Facility.is_active.desc(), Facility.lender).all())
    return {
        "rows": [{
            "id": f.id, "lender": f.lender, "facility_type": f.facility_type,
            "sanctioned": round(f.sanctioned, 2), "drawn": round(f.drawn, 2),
            "available_to_draw": round(f.available_to_draw, 2),
            "interest_rate": f.interest_rate, "tenure_months": f.tenure_months,
            "start_date": f.start_date.isoformat() if f.start_date else None,
            "end_date": f.end_date.isoformat() if f.end_date else None,
            "next_repayment_date": (f.next_repayment_date.isoformat()
                                    if f.next_repayment_date else None),
            "next_repayment_amount": round(f.next_repayment_amount, 2),
            "security_given": f.security_given,
            "is_active": f.is_active,
        } for f in rows],
        "totals": {
            "sanctioned": round(sum(f.sanctioned for f in rows if f.is_active), 2),
            "drawn": round(sum(f.drawn for f in rows if f.is_active), 2),
            "available_to_draw": round(sum(f.available_to_draw for f in rows if f.is_active), 2),
        },
        "basis": "Facilities as recorded in Setup. Available-to-draw is sanctioned less drawn "
                 "and does not count as cash on any runway calculation.",
    }


def repayment_calendar(ctx: Ctx, months: int = 12) -> dict:
    """Principal and interest by month, laid over projected cash."""
    from app.services.cashcalendar import build_forecast

    start = month_start(ctx.today)
    end = start + relativedelta(months=months)
    rows = (ctx.db.query(RepaymentScheduleItem)
            .filter(RepaymentScheduleItem.entity_id.in_(ctx.entity_ids),
                    RepaymentScheduleItem.due_date >= start,
                    RepaymentScheduleItem.due_date < end)
            .order_by(RepaymentScheduleItem.due_date).all())

    by_month: dict[date, dict] = {}
    for r in rows:
        m = month_start(r.due_date)
        d = by_month.setdefault(m, {"principal": 0.0, "interest": 0.0})
        d["principal"] += r.principal
        d["interest"] += r.interest

    fc = build_forecast(ctx, weeks=13)
    weekly = {date.fromisoformat(w["week_start"]): w["closing_cash"] for w in fc["weeks"]}

    out = []
    for i in range(months):
        m = start + relativedelta(months=i)
        d = by_month.get(m, {"principal": 0.0, "interest": 0.0})
        cash = None
        for ws, c in sorted(weekly.items()):
            if month_start(ws) == m:
                cash = c
        out.append({
            "month": m.isoformat(), "label": m.strftime("%b-%y"),
            "principal": round(d["principal"], 2),
            "interest": round(d["interest"], 2),
            "total": round(d["principal"] + d["interest"], 2),
            "projected_cash": round(cash, 2) if cash is not None else None,
        })
    return {
        "rows": out,
        "total_12m": round(sum(r["total"] for r in out), 2),
        "basis": "Scheduled principal and interest. Projected cash is the Cash Calendar's "
                 "closing balance for the last week falling in that month, where available.",
    }


def covenants(ctx: Ctx) -> dict:
    from app.services.liquidity import ratios
    from app.services.cash import position

    r = ratios(ctx)
    from app.services.runway import runway_summary

    values = {x["key"]: x["value"] for x in r["primary"] + r["lender"]}
    values["cash_available"] = position(ctx)["available"]
    values["runway_months"] = runway_summary(ctx)["current"]["months"]

    rows = []
    for c in (ctx.db.query(Covenant)
              .filter(Covenant.entity_id.in_(ctx.entity_ids))
              .order_by(Covenant.test_date).all()):
        current = values.get(c.metric_key)
        headroom_pct = None
        status = Status.GREY
        if current is not None and c.required_value:
            if c.operator in (">=", ">"):
                headroom_pct = (current - c.required_value) / abs(c.required_value) * 100
            else:
                headroom_pct = (c.required_value - current) / abs(c.required_value) * 100
            if headroom_pct < 0:
                status = Status.RED
            elif headroom_pct < c.amber_buffer_pct:
                status = Status.AMBER
            else:
                status = Status.GREEN

        is_money = c.required_value > 1000
        is_months = c.metric_key == "runway_months"
        rows.append({
            "id": c.id, "name": c.name, "metric_key": c.metric_key,
            "operator": c.operator,
            "required_value": c.required_value,
            "required_display": (fmt_inr(c.required_value) if is_money
                                 else f"{c.required_value:.1f} months" if is_months
                                 else f"{c.required_value:.2f}x"),
            "current_value": round(current, 2) if current is not None else None,
            "current_display": (fmt_inr(current) if is_money and current is not None
                                else f"{current:.1f} months" if is_months and current is not None
                                else f"{current:.2f}x" if current is not None else "—"),
            "headroom_pct": round(headroom_pct, 1) if headroom_pct is not None else None,
            "amber_buffer_pct": c.amber_buffer_pct,
            "test_date": c.test_date.isoformat() if c.test_date else None,
            "test_frequency": c.test_frequency,
            "days_to_test": (c.test_date - ctx.today).days if c.test_date else None,
            "status": status,
            "notes": c.notes,
        })
    return {
        "rows": rows,
        "any_breach": any(r["status"] == Status.RED for r in rows),
        "any_amber": any(r["status"] == Status.AMBER for r in rows),
        "basis": "Tested against the ratios on Tab 3 as at the as-on date. Amber appears "
                 "while headroom is still positive, so a breach is seen before it happens.",
    }


def funding_history(ctx: Ctx) -> dict:
    rows = (ctx.db.query(FundingRound)
            .filter(FundingRound.entity_id.in_(ctx.entity_ids))
            .order_by(FundingRound.closed_on).all())
    return {
        "rows": [{
            "id": f.id, "round_name": f.round_name,
            "closed_on": f.closed_on.isoformat(),
            "amount": round(f.amount, 2), "instrument": f.instrument,
            "investor": f.investor,
            "post_money_valuation": (round(f.post_money_valuation, 2)
                                     if f.post_money_valuation else None),
            "cash_remaining": round(f.cash_remaining, 2),
            "deployed_pct": round((1 - safe_div(f.cash_remaining, f.amount, 0.0)) * 100, 1),
            "notes": f.notes,
        } for f in rows],
        "total_raised": round(sum(f.amount for f in rows), 2),
        "basis": "Rounds as recorded in Setup. 'Cash remaining from that round' is maintained "
                 "manually and is a judgement, not an accounting figure.",
    }


def next_raise(ctx: Ctx) -> dict:
    from app.services.runway import runway_summary

    r = (ctx.db.query(NextRaise)
         .filter(NextRaise.entity_id.in_(ctx.entity_ids),
                 NextRaise.is_active.is_(True)).first())
    if not r:
        return {"exists": False}

    rw = runway_summary(ctx)
    trigger = r.target_close_date - relativedelta(months=r.lead_time_months)
    months_at_close = ((rw["current"]["months"] or 0)
                       - (r.target_close_date - ctx.as_on).days / 30.4)
    return {
        "exists": True,
        "target_amount": round(r.target_amount, 2),
        "target_close_date": r.target_close_date.isoformat(),
        "instrument": r.instrument,
        "status": r.status,
        "lead_time_months": r.lead_time_months,
        "trigger_date": trigger.isoformat(),
        "days_until_trigger": (trigger - ctx.today).days,
        "trigger_passed": trigger <= ctx.today,
        "runway_at_close_months": round(months_at_close, 1),
        "runway_at_close_status": (Status.RED if months_at_close < 0 else
                                   Status.AMBER if months_at_close < 3 else Status.GREEN),
        "notes": r.notes,
        "sentence": (f"The trigger date to start raising was {fmt_date(trigger)} — "
                     f"{abs((trigger - ctx.today).days)} days ago."
                     if trigger <= ctx.today else
                     f"{(trigger - ctx.today).days} days until the raise must start."),
        "basis": f"Target close less {r.lead_time_months} months of lead time.",
    }
