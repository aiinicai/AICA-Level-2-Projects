"""TAB 2C — People Cost: the largest line, and the one most directly controlled."""
from __future__ import annotations

from datetime import date

from dateutil.relativedelta import relativedelta
from sqlalchemy import func

from app.models import EmployeeLiability, FunctionCost, HeadcountMonth, HiringPlanItem
from app.services.common import Ctx, Status, fmt_date, fmt_inr, month_start, safe_div


def people_cost(ctx: Ctx) -> dict:
    from app.services.runway import cashout_date, runway_summary

    months = (ctx.db.query(HeadcountMonth)
              .filter(HeadcountMonth.entity_id.in_(ctx.entity_ids))
              .order_by(HeadcountMonth.month).all())
    latest = months[-1] if months else None

    fn_rows = (ctx.db.query(FunctionCost)
               .filter(FunctionCost.entity_id.in_(ctx.entity_ids),
                       FunctionCost.month == (latest.month if latest else month_start(ctx.as_on)))
               .order_by(FunctionCost.total_cost.desc()).all())

    hires = (ctx.db.query(HiringPlanItem)
             .filter(HiringPlanItem.entity_id.in_(ctx.entity_ids),
                     HiringPlanItem.status.notin_(["cancelled"]))
             .order_by(HiringPlanItem.planned_start).all())

    liability = (ctx.db.query(EmployeeLiability)
                 .filter(EmployeeLiability.entity_id.in_(ctx.entity_ids))
                 .order_by(EmployeeLiability.as_on.desc()).first())

    # Hiring plan cash impact over the next six months
    horizon = [month_start(ctx.as_on) + relativedelta(months=i + 1) for i in range(6)]
    impact_rows = []
    cumulative = 0.0
    for m in horizon:
        monthly = 0.0
        one_time = 0.0
        for h in hires:
            if h.planned_start <= m:
                monthly += h.monthly_cost_each * h.positions
            if month_start(h.planned_start) == m:
                one_time += h.one_time_cost
        cumulative += monthly + one_time
        impact_rows.append({"month": m.isoformat(), "label": m.strftime("%b-%y"),
                            "recurring": round(monthly, 2), "one_time": round(one_time, 2),
                            "total": round(monthly + one_time, 2),
                            "cumulative": round(cumulative, 2)})

    rw = runway_summary(ctx)
    base_months = rw["current"]["months"] or 0
    burn = rw["current"]["monthly_burn"] or 1.0
    added_monthly = impact_rows[-1]["recurring"] if impact_rows else 0.0
    with_hiring_months = safe_div(rw["cash_available"] - cumulative, burn + added_monthly, None)
    base_cashout = date.fromisoformat(rw["current"]["cashout_date"]) if rw["current"]["cashout_date"] else None
    new_cashout = cashout_date(ctx.as_on, with_hiring_months) if with_hiring_months else None

    return {
        "headcount": {
            "funded": latest.funded_headcount if latest else None,
            "actual": latest.actual_headcount if latest else None,
            "approved_unfilled": latest.approved_unfilled if latest else None,
            "offers_accepted_not_joined": latest.offers_accepted_not_joined if latest else None,
            "as_on": latest.month.isoformat() if latest else None,
        },
        "by_function": [{
            "function": f.function, "headcount": f.headcount,
            "cost_per_head": round(f.fully_loaded_cost_per_head, 2),
            "total_cost": round(f.total_cost, 2),
            "pct": round(safe_div(f.total_cost,
                                  sum(x.total_cost for x in fn_rows) or 1, 0.0) * 100, 1),
        } for f in fn_rows],
        "monthly_trend": [{
            "month": m.month.isoformat(), "label": m.month.strftime("%b-%y"),
            "people_cost": round(m.people_cost, 2),
            "headcount": m.actual_headcount,
            "cost_per_head": round(safe_div(m.people_cost, m.actual_headcount, 0.0) or 0.0, 2),
        } for m in months[-12:]],
        "hiring_plan": [{
            "id": h.id, "role": h.role, "function": h.function, "positions": h.positions,
            "planned_start": h.planned_start.isoformat(),
            "monthly_cost_each": round(h.monthly_cost_each, 2),
            "monthly_cost_total": round(h.monthly_cost_each * h.positions, 2),
            "one_time_cost": round(h.one_time_cost, 2),
            "status": h.status, "approved_by": h.approved_by,
        } for h in hires],
        "hiring_impact": {
            "rows": impact_rows,
            "six_month_cash": round(cumulative, 2),
            "added_monthly_runrate": round(added_monthly, 2),
            "cashout_before": rw["current"]["cashout_date"],
            "cashout_after": new_cashout.isoformat() if new_cashout else None,
            "days_moved": ((new_cashout - base_cashout).days
                           if new_cashout and base_cashout else None),
            "sentence": (f"The hiring plan costs {fmt_inr(cumulative)} over six months and adds "
                         f"{fmt_inr(added_monthly)} to the monthly run-rate, moving the cash-out "
                         f"date to {fmt_date(new_cashout)}."
                         if new_cashout else "No hiring plan recorded."),
        },
        "liability": ({
            "as_on": liability.as_on.isoformat(),
            "gratuity": round(liability.gratuity_accrued, 2),
            "leave_encashment": round(liability.leave_encashment_accrued, 2),
            "bonus": round(liability.bonus_accrued, 2),
            "total": round(liability.gratuity_accrued + liability.leave_encashment_accrued
                           + liability.bonus_accrued, 2),
            "funded": round(liability.funded_amount, 2),
            "unfunded": round(liability.gratuity_accrued + liability.leave_encashment_accrued
                              + liability.bonus_accrued - liability.funded_amount, 2),
            "notes": liability.notes,
        } if liability else None),
        "basis": "Headcount and fully-loaded cost are maintained manually; the monthly cost "
                 "line is the People category from the ledger.",
        "as_on": ctx.as_on.isoformat(),
    }
