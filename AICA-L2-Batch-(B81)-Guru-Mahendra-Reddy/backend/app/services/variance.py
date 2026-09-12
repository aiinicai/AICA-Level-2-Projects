"""TAB 7 — Plan vs Actual.

Every figure here is stamped with the plan version it is measured against.
Variance types are a fixed vocabulary, and timing variances are tracked
separately because they reverse.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import func

from app.models import BurnCategory, Plan, PlanLine, VarianceNote, VarianceType
from app.services.common import (
    Ctx, Status, fmt_inr, month_end, month_start, months_back, safe_div, trace,
)


def active_plan(ctx: Ctx) -> Plan | None:
    return (ctx.db.query(Plan)
            .filter(Plan.entity_id.in_(ctx.entity_ids), Plan.is_active.is_(True))
            .order_by(Plan.uploaded_on.desc()).first())


def board_plan(ctx: Ctx) -> Plan | None:
    return (ctx.db.query(Plan)
            .filter(Plan.entity_id.in_(ctx.entity_ids), Plan.board_approved.is_(True))
            .order_by(Plan.approved_on.desc()).first())


def plan_list(ctx: Ctx) -> list[dict]:
    plans = (ctx.db.query(Plan).filter(Plan.entity_id.in_(ctx.entity_ids))
             .order_by(Plan.uploaded_on.desc()).all())
    return [{
        "id": p.id, "name": p.name, "version": p.version, "note": p.note,
        "uploaded_by": p.uploaded_by, "uploaded_on": p.uploaded_on.isoformat(),
        "is_active": p.is_active, "is_locked": p.is_locked,
        "board_approved": p.board_approved, "approved_by": p.approved_by,
        "seconded_by": p.seconded_by,
        "approved_on": p.approved_on.isoformat() if p.approved_on else None,
        "period_from": p.period_from.isoformat() if p.period_from else None,
        "period_to": p.period_to.isoformat() if p.period_to else None,
        "opening_cash": p.opening_cash,
        "source_filename": p.source_filename,
        "supersedes_id": p.supersedes_id,
    } for p in plans]


def plan_outflow_for_month(ctx: Ctx, month: date) -> dict[str, float]:
    """Planned outflow by category for one month, from the active plan."""
    plan = active_plan(ctx)
    if not plan:
        return {}
    rows = (ctx.db.query(PlanLine.category, func.sum(PlanLine.amount))
            .filter(PlanLine.plan_id == plan.id, PlanLine.month == month_start(month),
                    PlanLine.line_type == "outflow")
            .group_by(PlanLine.category).all())
    return {k: float(v or 0.0) for k, v in rows}


def _plan_monthly(ctx: Ctx, plan: Plan | None) -> dict[date, dict]:
    if not plan:
        return {}
    rows = (ctx.db.query(PlanLine.month, PlanLine.line_type, func.sum(PlanLine.amount))
            .filter(PlanLine.plan_id == plan.id)
            .group_by(PlanLine.month, PlanLine.line_type).all())
    out: dict[date, dict] = {}
    for m, lt, amt in rows:
        m = m if isinstance(m, date) else date.fromisoformat(str(m))
        out.setdefault(m, {"inflow": 0.0, "outflow": 0.0, "closing": 0.0})
        out[m][lt] = float(amt or 0.0)
    return out


def plan_vs_actual(ctx: Ctx, plan_id: int | None = None) -> dict:
    from app.services.burn import monthly_burn
    from app.services.cash import monthly_cash_history
    from app.services.runway import runway_summary

    plan = ctx.db.get(Plan, plan_id) if plan_id else active_plan(ctx)
    prior = ctx.db.get(Plan, plan.supersedes_id) if plan and plan.supersedes_id else None

    plan_m = _plan_monthly(ctx, plan)
    prior_m = _plan_monthly(ctx, prior)

    actual_burn = {date.fromisoformat(r["month"]): r
                   for r in monthly_burn(ctx, months=18, normalised=False)}
    actual_cash = {date.fromisoformat(r["month"]): r["closing_cash"]
                   for r in monthly_cash_history(ctx, months=18)}

    notes = (ctx.db.query(VarianceNote)
             .filter(VarianceNote.entity_id.in_(ctx.entity_ids),
                     VarianceNote.plan_id == (plan.id if plan else -1)).all())
    notes_by_month: dict[date, list[VarianceNote]] = {}
    for n in notes:
        notes_by_month.setdefault(n.month, []).append(n)

    months = sorted(plan_m.keys())
    rows, ytd_plan, ytd_actual = [], 0.0, 0.0
    for m in months:
        p = plan_m.get(m, {})
        a = actual_burn.get(m)
        is_actual = a is not None and m <= month_start(ctx.as_on)
        plan_net = p.get("inflow", 0.0) - p.get("outflow", 0.0)
        actual_net = (a["collections"] + a["other_inflow"] - a["gross_burn"]) if is_actual else None
        var = (actual_net - plan_net) if actual_net is not None else None
        if is_actual:
            ytd_plan += plan_net
            ytd_actual += actual_net

        month_notes = notes_by_month.get(m, [])
        whole = [n for n in month_notes if n.category is None]
        rows.append({
            "month": m.isoformat(),
            "label": m.strftime("%b-%y"),
            "plan_inflow": round(p.get("inflow", 0.0), 2),
            "plan_outflow": round(p.get("outflow", 0.0), 2),
            "plan_net": round(plan_net, 2),
            "plan_closing": round(p.get("closing", 0.0), 2),
            "actual_inflow": round(a["collections"] + a["other_inflow"], 2) if is_actual else None,
            "actual_outflow": round(a["gross_burn"], 2) if is_actual else None,
            "actual_net": round(actual_net, 2) if actual_net is not None else None,
            "actual_closing": round(actual_cash.get(m), 2) if actual_cash.get(m) is not None else None,
            "prior_plan_closing": round(prior_m.get(m, {}).get("closing", 0.0), 2) if prior_m else None,
            "variance": round(var, 2) if var is not None else None,
            "variance_pct": round((safe_div(var, abs(plan_net), 0.0) or 0.0) * 100, 1)
                            if var is not None else None,
            "is_actual": is_actual,
            "variance_type": whole[0].variance_type if whole else None,
            "driver": whole[0].driver if whole else None,
            "owner": whole[0].owner if whole else None,
            "comment": whole[0].comment if whole else None,
            "status": whole[0].status if whole else ("open" if var and abs(var) > 500_000 else None),
            "note_id": whole[0].id if whole else None,
            "trace": trace("month_entries", entity_id=ctx.entity.id, month=m),
        })

    this_month = month_start(ctx.as_on)
    this_row = next((r for r in rows if r["month"] == this_month.isoformat()), None)

    rw = runway_summary(ctx)
    plan_cashout = _plan_cashout_date(plan_m)

    return {
        "plan": ({"id": plan.id, "name": plan.name, "version": plan.version,
                  "approved_by": plan.approved_by, "seconded_by": plan.seconded_by,
                  "approved_on": plan.approved_on.isoformat() if plan.approved_on else None,
                  "is_locked": plan.is_locked, "board_approved": plan.board_approved,
                  "note": plan.note, "uploaded_by": plan.uploaded_by,
                  "uploaded_on": plan.uploaded_on.isoformat()} if plan else None),
        "prior_plan": ({"id": prior.id, "name": prior.name, "version": prior.version}
                       if prior else None),
        "tiles": {
            "this_month_variance": this_row["variance"] if this_row else None,
            "this_month_variance_pct": this_row["variance_pct"] if this_row else None,
            "ytd_variance": round(ytd_actual - ytd_plan, 2),
            "ytd_variance_pct": round((safe_div(ytd_actual - ytd_plan, abs(ytd_plan), 0.0) or 0.0) * 100, 1),
            "cashout_per_plan": plan_cashout.isoformat() if plan_cashout else None,
            "cashout_actual": rw["current"]["cashout_date"],
            "cashout_gap_days": ((date.fromisoformat(rw["current"]["cashout_date"]) - plan_cashout).days
                                 if plan_cashout and rw["current"]["cashout_date"] else None),
            "forecast_accuracy": _forecast_accuracy_score(ctx),
        },
        "rows": rows,
        "waterfall": _variance_waterfall(rows, notes),
        "line_items": _line_item_variance(ctx, plan, this_month),
        "variance_types": VarianceType.ALL,
        "reversing_types": VarianceType.REVERSING,
        "basis": (f"Measured against {plan.name} {plan.version}" if plan
                  else "No active plan — upload one in Setup › Upload Plan."),
        "as_on": ctx.as_on.isoformat(),
    }


def _plan_cashout_date(plan_m: dict[date, dict]) -> date | None:
    for m in sorted(plan_m.keys()):
        if plan_m[m].get("closing", 0.0) <= 0:
            return month_end(m)
    return None


def _variance_waterfall(rows: list[dict], notes: list[VarianceNote]) -> dict:
    """Plan cash → actual cash, bars grouped by variance type. Timing bars are
    flagged so the frontend can shade them differently — they reverse."""
    actuals = [r for r in rows if r["is_actual"]]
    if not actuals:
        return {"bars": [], "start": 0.0, "end": 0.0}

    # Bridge the plan's closing cash for the latest actual month to the actual
    # closing cash for the same month. Bridging from the opening balance would
    # put an ₹ 8 Cr bar next to ₹ 30 L deltas and make the chart unreadable.
    last = actuals[-1]
    start = last["plan_closing"]
    end = last["actual_closing"] if last["actual_closing"] is not None else start

    by_type: dict[str, float] = {}
    explained = 0.0
    for r in actuals:
        if r["variance"] is None:
            continue
        t = r["variance_type"]
        if t:
            by_type[t] = by_type.get(t, 0.0) + r["variance"]
            explained += r["variance"]

    # The gap the bridge actually has to close, not the sum of monthly
    # variances — those only agree when the opening balances agree.
    total_var = end - start
    unexplained = total_var - explained
    if abs(unexplained) > 1:
        by_type["Unexplained"] = unexplained

    bars = [{"label": f"Plan cash, {last['label']}", "type": "start",
             "value": round(start, 2)}]
    for t in VarianceType.ALL + ["Unexplained"]:
        if t in by_type and abs(by_type[t]) > 1:
            bars.append({"label": t, "type": "delta", "value": round(by_type[t], 2),
                         "reverses": t in VarianceType.REVERSING})
    bars.append({"label": f"Actual cash, {last['label']}", "type": "end",
                 "value": round(end, 2)})
    return {"bars": bars, "start": round(start, 2), "end": round(end, 2),
            "total_variance": round(total_var, 2),
            "explained": round(explained, 2),
            "unexplained": round(unexplained, 2)}


def _line_item_variance(ctx: Ctx, plan: Plan | None, month: date) -> list[dict]:
    from app.services.burn import burn_by_category
    if not plan:
        return []
    planned = plan_outflow_for_month(ctx, month)
    actual = {r["category"]: r["this_month"] for r in burn_by_category(ctx)["rows"]}

    plan_inflow = (ctx.db.query(func.sum(PlanLine.amount))
                   .filter(PlanLine.plan_id == plan.id, PlanLine.month == month,
                           PlanLine.line_type == "inflow").scalar() or 0.0)
    from app.services.burn import monthly_burn
    actual_inflow = monthly_burn(ctx, months=1, normalised=False)[-1]["collections"]

    rows = [{
        "line": "Customer Collections", "kind": "revenue",
        "plan": round(float(plan_inflow), 2), "actual": round(actual_inflow, 2),
        "variance": round(actual_inflow - float(plan_inflow), 2),
        "variance_pct": round((safe_div(actual_inflow - float(plan_inflow),
                                        abs(float(plan_inflow)), 0.0) or 0.0) * 100, 1),
    }]
    for cat in BurnCategory.ALL:
        p, a = planned.get(cat, 0.0), actual.get(cat, 0.0)
        if p == 0 and a == 0:
            continue
        rows.append({
            "line": cat, "kind": "cost",
            "plan": round(p, 2), "actual": round(a, 2),
            # For costs, spending less than plan is favourable.
            "variance": round(p - a, 2),
            "variance_pct": round((safe_div(p - a, abs(p) or 1, 0.0) or 0.0) * 100, 1),
        })
    return rows


def _forecast_accuracy_score(ctx: Ctx) -> float | None:
    from app.services.cashcalendar import forecast_accuracy
    fa = forecast_accuracy(ctx)
    return fa.get("score")


def upsert_variance_note(ctx: Ctx, plan_id: int, month: date, variance_type: str,
                         driver: str, owner: str | None, comment: str | None,
                         status: str, user_name: str,
                         category: str | None = None,
                         note_id: int | None = None) -> VarianceNote:
    if variance_type not in VarianceType.ALL:
        raise ValueError(f"Variance type must be one of {VarianceType.ALL}")

    note = ctx.db.get(VarianceNote, note_id) if note_id else None
    if note is None:
        note = VarianceNote(entity_id=ctx.entity.id, plan_id=plan_id,
                            month=month_start(month), category=category,
                            source="manual", created_by=user_name)
        ctx.db.add(note)
    note.variance_type = variance_type
    note.driver = driver
    note.owner = owner
    note.comment = comment
    note.status = status
    note.updated_by = user_name
    ctx.db.flush()
    return note
