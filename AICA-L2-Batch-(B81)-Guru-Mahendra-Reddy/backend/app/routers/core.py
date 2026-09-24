"""Global elements: entities, top strip, glossary, activity log, and the
drill-down endpoint that makes every number traceable."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_write
from app.database import get_db
from app.models import (
    ActivityLog, Bill, Customer, Definition, Entity, Invoice, LedgerEntry,
    RepaymentScheduleItem, StatutoryDue, User, Vendor,
)
from app.services.common import Ctx, fmt_inr, month_end, month_start, months_back
from app.routers.deps import get_ctx, log

router = APIRouter(prefix="/api", tags=["core"])


@router.get("/entities")
def entities(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Entity).order_by(Entity.sort_order, Entity.id).all()
    return [{
        "id": e.id, "name": e.name, "code": e.code, "currency": e.currency,
        "is_consolidated": e.is_consolidated,
        "books_closed_upto": e.books_closed_upto.isoformat() if e.books_closed_upto else None,
        "last_data_update": e.last_data_update.isoformat() if e.last_data_update else None,
        "min_cash_floor": e.min_cash_floor,
    } for e in rows]


@router.get("/top-strip")
def top_strip(ctx: Ctx = Depends(get_ctx), user: User = Depends(get_current_user)):
    """Everything the fixed strip needs, in one call — it is on every tab."""
    from app.models import Alert
    from app.services.cash import confidence, position

    pos = position(ctx)
    conf = confidence(ctx)
    unack = (ctx.db.query(Alert)
             .filter(Alert.entity_id.in_(ctx.entity_ids),
                     Alert.status.in_(["active", "snoozed"])).count())

    return {
        "entity": {"id": ctx.entity.id, "name": ctx.entity.name, "code": ctx.entity.code},
        "as_on": ctx.as_on.isoformat(),
        "today": ctx.today.isoformat(),
        "books_position": pos["books_position"],
        "bank_position": pos["bank_position"],
        "difference": pos["difference"],
        "difference_pct": pos["difference_pct"],
        "difference_status": pos["difference_status"],
        "data_updated": conf["last_data_update"],
        "books_status": conf["books_status"],
        "unacknowledged_alerts": unack,
        "confidence": conf,
        "user": {"name": user.name, "role": user.role, "email": user.email},
    }


@router.get("/definitions")
def definitions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Definition).order_by(Definition.category, Definition.term).all()
    return [{
        "id": d.id, "term": d.term, "category": d.category,
        "plain_english": d.plain_english, "formula": d.formula,
        "basis_note": d.basis_note,
        "updated_by": d.updated_by,
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
    } for d in rows]


@router.get("/activity")
def activity(limit: int = Query(100, le=500), ctx: Ctx = Depends(get_ctx),
             user: User = Depends(get_current_user)):
    rows = (ctx.db.query(ActivityLog)
            .filter(ActivityLog.entity_id.in_(ctx.entity_ids + [None]))
            .order_by(ActivityLog.at.desc()).limit(limit).all())
    return [{
        "id": a.id, "at": a.at.isoformat(), "user": a.user_name,
        "action": a.action, "object_type": a.object_type, "object_id": a.object_id,
        "summary": a.summary, "before": a.before_value, "after": a.after_value,
    } for a in rows]


# ---------------------------------------------------------------------------
# Drill-down — SPEC principle 3: every number is clickable to the entries
# behind it. The frontend passes back the `trace` descriptor it was given.
# ---------------------------------------------------------------------------
@router.get("/trace")
def trace_entries(
    kind: str,
    category: str | None = None,
    customer_id: int | None = None,
    bucket: str | None = None,
    id: int | None = None,
    months: int | None = None,
    month: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    normalised: bool = False,
    key: str | None = None,
    limit: int = Query(300, le=1000),
    ctx: Ctx = Depends(get_ctx),
    user: User = Depends(get_current_user),
):
    if kind == "bank_accounts":
        from app.services.liquidity import where_the_money_is
        w = where_the_money_is(ctx)
        keep = ("institution", "account_name", "purpose", "balance",
                "availability", "restriction_reason")
        return {
            "title": "Bank and cash balances",
            "rows": [{k: r[k] for k in keep} for r in w["rows"]],
            "total": sum(r["balance"] for r in w["rows"]),
            "count": len(w["rows"]),
            "basis": w["basis"],
        }

    if kind in ("burn_entries", "month_entries"):
        if month:
            a, b = month_start(month), month_end(month)
        elif date_from and date_to:
            a, b = date_from, date_to
        else:
            starts = months_back(ctx.as_on, months or 3)
            a, b = starts[0], month_end(starts[-1])
        q = (ctx.db.query(LedgerEntry)
             .filter(LedgerEntry.entity_id.in_(ctx.entity_ids),
                     LedgerEntry.txn_date >= a, LedgerEntry.txn_date <= b))
        if kind == "burn_entries":
            q = q.filter(LedgerEntry.cash_amount < 0)
        if category:
            q = q.filter(LedgerEntry.burn_category == category)
        if normalised:
            q = q.filter(LedgerEntry.is_one_off.is_(False))
        rows = q.order_by(LedgerEntry.txn_date.desc()).limit(limit).all()
        return {
            "title": f"Entries{f' — {category}' if category else ''}, {a:%d-%b-%y} to {b:%d-%b-%y}",
            "columns": ["Date", "Voucher", "Party", "Narration", "Category", "Amount"],
            "rows": [{
                "id": e.id, "date": e.txn_date.isoformat(), "voucher_no": e.voucher_no,
                "voucher_type": e.voucher_type, "party": e.party, "narration": e.narration,
                "category": e.burn_category, "cost_nature": e.cost_nature,
                "amount": round(e.cash_amount, 2), "is_one_off": e.is_one_off,
                "classified_by": e.classified_by, "source": e.source,
            } for e in rows],
            "total": round(sum(e.cash_amount for e in rows), 2),
            "count": len(rows),
            "basis": "Cash-affecting ledger entries as synced from the accounting system.",
        }

    if kind == "invoices":
        q = (ctx.db.query(Invoice, Customer.name)
             .join(Customer, Customer.id == Invoice.customer_id)
             .filter(Invoice.entity_id.in_(ctx.entity_ids), Invoice.outstanding > 0))
        if customer_id:
            q = q.filter(Invoice.customer_id == customer_id)
        rows = q.order_by(Invoice.due_date).limit(limit).all()

        def in_bucket(inv) -> bool:
            if not bucket:
                return True
            if bucket == "Disputed":
                return inv.is_disputed
            if inv.is_disputed:
                return False
            late = (ctx.as_on - inv.due_date).days
            return {
                "Not Yet Due": late < 0, "0–30": 0 <= late <= 30,
                "31–60": 31 <= late <= 60, "61–90": 61 <= late <= 90,
                "90+": late > 90,
            }.get(bucket, True)

        sel = [(i, n) for i, n in rows if in_bucket(i)]
        return {
            "title": f"Open invoices{f' — {bucket}' if bucket else ''}",
            "columns": ["Invoice", "Client", "Invoice date", "Due date", "Days late", "Outstanding"],
            "rows": [{
                "id": i.id, "invoice_no": i.invoice_no, "client": n,
                "invoice_date": i.invoice_date.isoformat(),
                "due_date": i.due_date.isoformat(),
                "days_late": (ctx.as_on - i.due_date).days,
                "amount": round(i.amount, 2), "outstanding": round(i.outstanding, 2),
                "is_disputed": i.is_disputed,
                "probability": i.collection_probability,
                "promised_date": i.promised_date.isoformat() if i.promised_date else None,
            } for i, n in sel],
            "total": round(sum(i.outstanding for i, _ in sel), 2),
            "count": len(sel),
            "basis": f"Open invoices as at {ctx.as_on:%d-%b-%y}.",
        }

    if kind == "bill":
        b = ctx.db.get(Bill, id)
        if not b:
            raise HTTPException(404, "Bill not found")
        v = ctx.db.get(Vendor, b.vendor_id) if b.vendor_id else None
        return {"title": f"Bill {b.bill_no}", "columns": [], "rows": [{
            "bill_no": b.bill_no, "vendor": v.name if v else None,
            "bill_date": b.bill_date.isoformat(), "due_date": b.due_date.isoformat(),
            "amount": b.amount, "outstanding": b.outstanding,
            "category": b.burn_category, "deferrable": b.deferrable,
            "deferral_cost": b.deferral_cost, "penalty": b.penalty_note,
            "approver": b.approver, "status": b.status, "source": b.source,
        }], "basis": "Payable as recorded in the accounting system."}

    if kind == "statutory":
        s = ctx.db.get(StatutoryDue, id)
        if not s:
            raise HTTPException(404, "Statutory due not found")
        return {"title": f"{s.head} — {s.period}", "columns": [], "rows": [{
            "head": s.head, "period": s.period, "due_date": s.due_date.isoformat(),
            "amount": s.amount, "earmarked": s.earmarked_amount, "funded": s.funded,
            "status": s.status, "notes": s.notes,
        }], "basis": "Statutory liability recorded against its statutory due date."}

    if kind == "repayment":
        r = ctx.db.get(RepaymentScheduleItem, id)
        if not r:
            raise HTTPException(404, "Repayment not found")
        return {"title": "Scheduled repayment", "columns": [], "rows": [{
            "due_date": r.due_date.isoformat(), "principal": r.principal,
            "interest": r.interest, "total": r.principal + r.interest, "paid": r.paid,
        }], "basis": "From the facility's amortisation schedule."}

    if kind == "ratio":
        from app.services.liquidity import ratios
        r = ratios(ctx)
        row = next((x for x in r["primary"] + r["lender"] if x["key"] == key), None)
        if not row:
            raise HTTPException(404, "Ratio not found")
        return {
            "title": row["label"],
            "columns": ["Balance", "Amount"],
            "rows": [{"balance": b[0], "amount": b[1]} for b in row["balances_used"]],
            "formula": row["formula"], "value": row["value"],
            "benchmark": row["benchmark"], "basis": r["basis"],
        }

    if kind == "health_components":
        from app.services.liquidity import health_score
        h = health_score(ctx)
        return {"title": "Liquidity health score — full breakdown",
                "columns": ["Component", "Weight", "Contribution", "Why"],
                "rows": h["components"], "basis": h["basis"], "score": h["score"]}

    if kind == "runway_basis":
        from app.services.runway import runway_summary
        s = runway_summary(ctx)
        return {"title": "Runway — every assumption", "columns":
                ["Scenario", "Monthly burn", "Months", "Cash-out", "Assumes"],
                "rows": s["rows"], "basis": s["basis"],
                "cash_available": s["cash_available"]}

    raise HTTPException(400, f"Unknown trace kind '{kind}'")
