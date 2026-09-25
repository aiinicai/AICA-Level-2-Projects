"""TAB 5 — Money Going Out.

The ordering rule matters more than the data here: non-deferrable first, then
by date. That ordering is the point of the Due Now screen.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func

from app.models import (
    Bill, Commitment, RepaymentScheduleItem, StatutoryDue, StatutoryHead, Vendor,
)
from app.services.common import (
    Ctx, Status, fmt_date, fmt_inr, months_back, safe_div, trace,
)


def obligations(ctx: Ctx, horizon_days: int = 30) -> dict:
    """SPEC 5A — every rupee that must leave, sorted the way the CFO reads it."""
    horizon = ctx.as_on + timedelta(days=horizon_days)

    bills = (ctx.db.query(Bill, Vendor.name)
             .outerjoin(Vendor, Vendor.id == Bill.vendor_id)
             .filter(Bill.entity_id.in_(ctx.entity_ids), Bill.outstanding > 0,
                     Bill.status != "paid")
             .all())
    stat = (ctx.db.query(StatutoryDue)
            .filter(StatutoryDue.entity_id.in_(ctx.entity_ids),
                    StatutoryDue.status != "paid", StatutoryDue.amount > 0).all())
    loans = (ctx.db.query(RepaymentScheduleItem)
             .filter(RepaymentScheduleItem.entity_id.in_(ctx.entity_ids),
                     RepaymentScheduleItem.paid.is_(False),
                     RepaymentScheduleItem.due_date <= horizon + timedelta(days=60)).all())

    rows: list[dict] = []
    for b, vname in bills:
        rows.append({
            "id": f"bill-{b.id}", "kind": "vendor",
            "due_date": b.due_date.isoformat(),
            "item": b.description or b.bill_no,
            "reference": b.bill_no,
            "counterparty": vname or "—",
            "category": b.burn_category,
            "amount": round(b.outstanding, 2),
            "deferrable": b.deferrable,
            "deferral_cost": round(b.deferral_cost, 2),
            "penalty": b.penalty_note or "None",
            "approver": b.approver,
            "status": b.status,
            "days_to_due": (b.due_date - ctx.as_on).days,
            "trace": trace("bill", id=b.id),
        })
    for s in stat:
        rows.append({
            "id": f"stat-{s.id}", "kind": "statutory",
            "due_date": s.due_date.isoformat(),
            "item": f"{s.head} — {s.period}",
            "reference": s.reference or s.period,
            "counterparty": "Government of India",
            "category": "Statutory & Taxes",
            "amount": round(s.amount, 2),
            "deferrable": False,
            "deferral_cost": 0.0,
            "penalty": "Penal interest and prosecution risk; first charge on cash.",
            "approver": "CFO",
            "status": s.status,
            "funded": s.funded,
            "days_to_due": (s.due_date - ctx.as_on).days,
            "trace": trace("statutory", id=s.id),
        })
    for r in loans:
        rows.append({
            "id": f"loan-{r.id}", "kind": "debt",
            "due_date": r.due_date.isoformat(),
            "item": "Venture debt — principal and interest",
            "reference": f"Facility {r.facility_id}",
            "counterparty": "Lender",
            "category": "Finance Costs",
            "amount": round(r.principal + r.interest, 2),
            "deferrable": False,
            "deferral_cost": 0.0,
            "penalty": "Event of default under the facility agreement.",
            "approver": "CFO",
            "status": "scheduled",
            "days_to_due": (r.due_date - ctx.as_on).days,
            "trace": trace("repayment", id=r.id),
        })

    # THE ordering: non-deferrable first, then by date.
    rows.sort(key=lambda r: (r["deferrable"], r["due_date"]))

    within_week = [r for r in rows if r["days_to_due"] <= 7]
    within_30 = [r for r in rows if r["days_to_due"] <= horizon_days]
    overdue_vendor = [r for r in rows if r["kind"] == "vendor" and r["days_to_due"] < 0]

    return {
        "rows": rows,
        "tiles": {
            "due_this_week": round(sum(r["amount"] for r in within_week), 2),
            "due_next_30d": round(sum(r["amount"] for r in within_30), 2),
            "non_deferrable_30d": round(sum(r["amount"] for r in within_30
                                            if not r["deferrable"]), 2),
            "overdue_to_vendors": round(sum(r["amount"] for r in overdue_vendor), 2),
        },
        "basis": f"Open payables, statutory dues and scheduled repayments as at "
                 f"{ctx.as_on:%d-%b-%y}. Sorted non-deferrable first, then by due date.",
        "as_on": ctx.as_on.isoformat(),
    }


def statutory(ctx: Ctx, horizon_days: int = 30) -> dict:
    """SPEC 5B — its own layer, because these are first-charge."""
    horizon = ctx.as_on + timedelta(days=horizon_days)
    upcoming = (ctx.db.query(StatutoryDue)
                .filter(StatutoryDue.entity_id.in_(ctx.entity_ids),
                        StatutoryDue.status != "paid")
                .order_by(StatutoryDue.due_date).all())
    history = (ctx.db.query(StatutoryDue)
               .filter(StatutoryDue.entity_id.in_(ctx.entity_ids),
                       StatutoryDue.status == "paid")
               .order_by(StatutoryDue.due_date.desc()).limit(80).all())

    in_window = [s for s in upcoming if s.due_date <= horizon and s.amount > 0]
    due_amt = sum(s.amount for s in in_window)
    earmarked = sum(s.earmarked_amount for s in in_window)
    gap = max(due_amt - earmarked, 0.0)

    penalty_paid = sum(s.interest_penalty_paid for s in history)
    late_count = sum(1 for s in history if s.paid_on and s.paid_on > s.due_date)

    return {
        "rows": [{
            "id": s.id, "head": s.head, "period": s.period,
            "due_date": s.due_date.isoformat(),
            "amount": round(s.amount, 2),
            "funded": s.funded,
            "earmarked": round(s.earmarked_amount, 2),
            "gap": round(max(s.amount - s.earmarked_amount, 0.0), 2),
            "days_to_due": (s.due_date - ctx.as_on).days,
            "status": s.status,
            "notes": s.notes,
            "severity": (Status.RED if not s.funded and (s.due_date - ctx.as_on).days <= 15
                         else Status.AMBER if not s.funded else Status.GREEN),
        } for s in upcoming],
        "cover": {
            "window_days": horizon_days,
            "due": round(due_amt, 2),
            "earmarked": round(earmarked, 2),
            "gap": round(gap, 2),
            "ratio": round(safe_div(earmarked, due_amt, 0.0) or 0.0, 2),
            "status": Status.RED if gap > 0 else Status.GREEN,
            "sentence": (f"Statutory dues of {fmt_inr(due_amt)} fall due in the next "
                         f"{horizon_days} days. Cash earmarked: {fmt_inr(earmarked)}. "
                         f"Gap: {fmt_inr(gap)}."),
        },
        "history": [{
            "id": s.id, "head": s.head, "period": s.period,
            "due_date": s.due_date.isoformat(),
            "paid_on": s.paid_on.isoformat() if s.paid_on else None,
            "amount": round(s.amount, 2),
            "days_late": ((s.paid_on - s.due_date).days if s.paid_on and s.paid_on > s.due_date else 0),
            "interest_penalty_paid": round(s.interest_penalty_paid, 2),
        } for s in history],
        "history_summary": {
            "months": 12,
            "late_payments": late_count,
            "penalty_paid": round(penalty_paid, 2),
            "note": (f"{late_count} late payment(s) in the last 12 months, costing "
                     f"{fmt_inr(penalty_paid)} in interest and penalty."
                     if late_count else "No late statutory payments in the last 12 months."),
        },
        "heads": StatutoryHead.ALL,
        "basis": "Statutory liabilities recorded against their statutory due dates. "
                 "'Earmarked' is cash a person has explicitly set aside for the head.",
        "as_on": ctx.as_on.isoformat(),
    }


def commitments(ctx: Ctx) -> dict:
    """SPEC 5C — money already spent that no invoice has arrived for."""
    rows = (ctx.db.query(Commitment)
            .filter(Commitment.entity_id.in_(ctx.entity_ids))
            .order_by(Commitment.ends_on).all())
    remaining = sum(c.remaining for c in rows)
    non_cancellable = sum(c.remaining for c in rows if not c.cancellable)

    return {
        "rows": [{
            "id": c.id,
            "commitment_type": c.commitment_type,
            "counterparty": c.counterparty,
            "description": c.description,
            "total_value": round(c.total_value, 2),
            "consumed": round(c.consumed_to_date, 2),
            "remaining": round(c.remaining, 2),
            "cancellable": c.cancellable,
            "notice_period_days": c.notice_period_days,
            "exit_cost": round(c.exit_cost, 2),
            "starts_on": c.starts_on.isoformat() if c.starts_on else None,
            "ends_on": c.ends_on.isoformat() if c.ends_on else None,
            "monthly_runrate": round(c.monthly_runrate, 2),
            "category": c.burn_category,
            "owner": c.owner,
            "months_left": (round((c.ends_on - ctx.as_on).days / 30.4, 1)
                            if c.ends_on else None),
        } for c in rows],
        "summary": {
            "remaining": round(remaining, 2),
            "non_cancellable": round(non_cancellable, 2),
            "cancellable": round(remaining - non_cancellable, 2),
            "total_exit_cost": round(sum(c.exit_cost for c in rows if c.cancellable), 2),
            "monthly_runrate": round(sum(c.monthly_runrate for c in rows), 2),
            "sentence": (f"Committed spend not yet in books: {fmt_inr(remaining)}. "
                         f"Of which non-cancellable: {fmt_inr(non_cancellable)}."),
        },
        "basis": "Manually maintained register of purchase orders, contracts, offers and "
                 "leases. Nothing here has reached the accounting system yet.",
    }


def vendor_position(ctx: Ctx) -> dict:
    """SPEC 5D — including how long we actually take to pay them."""
    raw = (ctx.db.query(Bill).filter(Bill.entity_id.in_(ctx.entity_ids),
                                     Bill.outstanding > 0).all())
    agg: dict[int, dict] = {}
    for b in raw:
        d = agg.setdefault(b.vendor_id, {"payable": 0.0, "overdue": 0.0, "count": 0})
        d["payable"] += b.outstanding
        d["count"] += 1
        if b.due_date < ctx.as_on:
            d["overdue"] += b.outstanding

    paid = (ctx.db.query(Bill.vendor_id,
                         func.avg(func.julianday(Bill.paid_on) - func.julianday(Bill.bill_date)))
            .filter(Bill.entity_id.in_(ctx.entity_ids), Bill.paid_on.isnot(None))
            .group_by(Bill.vendor_id).all())
    avg_days = {vid: round(float(v or 0)) for vid, v in paid}

    vendors = {v.id: v for v in ctx.db.query(Vendor)
               .filter(Vendor.entity_id.in_(ctx.entity_ids)).all()}

    rows = []
    for vid, d in agg.items():
        v = vendors.get(vid)
        rows.append({
            "vendor_id": vid,
            "vendor": v.name if v else "—",
            "payable": round(d["payable"], 2),
            "overdue": round(d["overdue"], 2),
            "open_bills": d["count"],
            "avg_days_we_take": avg_days.get(vid),
            "credit_terms_days": v.credit_terms_days if v else None,
            "criticality": v.criticality if v else None,
            "on_hold": v.on_hold if v else False,
            "category": v.burn_category if v else None,
        })
    rows.sort(key=lambda r: r["payable"], reverse=True)
    return {
        "rows": rows,
        "top10": rows[:10],
        "total_payable": round(sum(r["payable"] for r in rows), 2),
        "total_overdue": round(sum(r["overdue"] for r in rows), 2),
        "basis": "Open bills by vendor. Criticality is set manually and drives which vendors "
                 "can safely be stretched.",
    }
