"""TAB 4 — Money Coming In.

Two things this module refuses to do, because the spec is explicit:
  * mix disputed invoices into the ageing buckets, and
  * describe a client by their stated credit terms when their actual payment
    behaviour is known and different.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func

from app.models import (
    CollectionPerformance, Customer, ExpectedInflow, Invoice, Receipt, UnbilledWork,
)
from app.services.common import (
    Ctx, Status, fmt_date, fmt_inr, month_end, months_back, safe_div, trace,
)

BUCKETS = [
    ("Not Yet Due", None, 0),
    ("0–30", 0, 30),
    ("31–60", 31, 60),
    ("61–90", 61, 90),
    ("90+", 91, None),
]


def open_invoices(ctx: Ctx, include_disputed: bool = True) -> list[Invoice]:
    q = (ctx.db.query(Invoice)
         .filter(Invoice.entity_id.in_(ctx.entity_ids), Invoice.outstanding > 0))
    if not include_disputed:
        q = q.filter(Invoice.is_disputed.is_(False))
    return q.all()


def _days_late(inv: Invoice, as_on: date) -> int:
    return (as_on - inv.due_date).days


def _bucket(days_late: int) -> str:
    if days_late < 0:
        return "Not Yet Due"
    for name, lo, hi in BUCKETS[1:]:
        if (lo is None or days_late >= lo) and (hi is None or days_late <= hi):
            return name
    return "90+"


def payment_behaviour(ctx: Ctx) -> dict[int, dict]:
    """Average days actually taken to pay, per customer, from receipts."""
    rows = (ctx.db.query(Receipt.customer_id,
                         func.avg(func.julianday(Receipt.received_on)
                                  - func.julianday(Invoice.invoice_date)),
                         func.count(Receipt.id))
            .join(Invoice, Invoice.id == Receipt.invoice_id)
            .filter(Receipt.entity_id.in_(ctx.entity_ids))
            .group_by(Receipt.customer_id).all())
    return {cid: {"avg_days": round(float(avg or 0.0)), "invoices_paid": int(n)}
            for cid, avg, n in rows}


def ageing(ctx: Ctx) -> dict:
    """Buckets in ₹ and % of total. Disputed sits in its own bucket, never
    blended into the others."""
    invs = open_invoices(ctx)
    totals = {name: 0.0 for name, _, _ in BUCKETS}
    totals["Disputed"] = 0.0
    counts = {k: 0 for k in totals}

    for inv in invs:
        if inv.is_disputed:
            totals["Disputed"] += inv.outstanding
            counts["Disputed"] += 1
            continue
        b = _bucket(_days_late(inv, ctx.as_on))
        totals[b] += inv.outstanding
        counts[b] += 1

    grand = sum(totals.values()) or 1.0
    order = [n for n, _, _ in BUCKETS] + ["Disputed"]
    return {
        "total": round(grand, 2),
        "buckets": [{
            "bucket": b,
            "amount": round(totals[b], 2),
            "pct": round(totals[b] / grand * 100, 1),
            "count": counts[b],
            "status": (Status.GREEN if b == "Not Yet Due" else
                       Status.AMBER if b in ("0–30", "31–60") else
                       Status.GREY if b == "Disputed" else Status.RED),
            "trace": trace("invoices", entity_id=ctx.entity.id, bucket=b),
        } for b in order],
        "basis": f"Open invoices as at {ctx.as_on:%d-%b-%y}, aged against the invoice due "
                 f"date. Disputed invoices are shown separately and excluded from the "
                 f"ageing buckets.",
        "as_on": ctx.as_on.isoformat(),
    }


def by_client(ctx: Ctx) -> dict:
    invs = open_invoices(ctx)
    behaviour = payment_behaviour(ctx)
    customers = {c.id: c for c in ctx.db.query(Customer)
                 .filter(Customer.entity_id.in_(ctx.entity_ids)).all()}

    agg: dict[int, dict] = {}
    for inv in invs:
        d = agg.setdefault(inv.customer_id, {
            "customer_id": inv.customer_id,
            "client": customers[inv.customer_id].name if inv.customer_id in customers else "—",
            "total_outstanding": 0.0, "overdue": 0.0, "disputed": 0.0,
            "oldest_days": 0, "weighted_30d": 0.0, "invoice_count": 0,
        })
        d["total_outstanding"] += inv.outstanding
        d["invoice_count"] += 1
        late = _days_late(inv, ctx.as_on)
        if inv.is_disputed:
            d["disputed"] += inv.outstanding
        else:
            if late > 0:
                d["overdue"] += inv.outstanding
                d["oldest_days"] = max(d["oldest_days"], late)
            d["weighted_30d"] += inv.outstanding * (inv.collection_probability or 0.5) \
                if _expected_within(inv, ctx.as_on, 30) else 0.0

    grand = sum(d["total_outstanding"] for d in agg.values()) or 1.0
    rows = []
    for cid, d in agg.items():
        c = customers.get(cid)
        b = behaviour.get(cid, {})
        rows.append({
            **d,
            "total_outstanding": round(d["total_outstanding"], 2),
            "overdue": round(d["overdue"], 2),
            "disputed": round(d["disputed"], 2),
            "weighted_30d": round(d["weighted_30d"], 2),
            "credit_terms_days": c.credit_terms_days if c else None,
            "avg_days_to_pay": b.get("avg_days"),
            "behaviour_note": (f"Pays in ~{b['avg_days']} days against "
                               f"{c.credit_terms_days}-day terms"
                               if b.get("avg_days") and c else "No payment history yet"),
            "pct_of_ar": round(d["total_outstanding"] / grand * 100, 1),
            "last_contact": c.last_contact.isoformat() if c and c.last_contact else None,
            "owner": c.owner if c else None,
            "trace": trace("invoices", entity_id=ctx.entity.id, customer_id=cid),
        })
    rows.sort(key=lambda r: r["total_outstanding"], reverse=True)
    return {"rows": rows, "total": round(grand, 2),
            "basis": "Open invoices by client. 'Average days taken to pay' is their actual "
                     "behaviour from receipts, not their agreed terms."}


def _expected_within(inv: Invoice, as_on: date, days: int) -> bool:
    """Will this invoice plausibly land in the next `days`? A promised date
    beats the due date; an already-overdue invoice is assumed collectible in
    the window at its probability."""
    horizon = as_on + timedelta(days=days)
    if inv.promised_date:
        return inv.promised_date <= horizon
    if inv.due_date <= as_on:
        return True
    return inv.due_date <= horizon


def summary(ctx: Ctx) -> dict:
    """The five collection tiles."""
    invs = open_invoices(ctx)
    total = sum(i.outstanding for i in invs)
    overdue = sum(i.outstanding for i in invs
                  if not i.is_disputed and _days_late(i, ctx.as_on) > 0)
    weighted = sum(i.outstanding * (i.collection_probability or 0.5)
                   for i in invs if not i.is_disputed and _expected_within(i, ctx.as_on, 30))

    dso = _dso(ctx)
    dso_prev = _dso(ctx, offset_months=3)

    this_month = months_back(ctx.as_on, 1)[0]
    collected = (ctx.db.query(func.sum(Receipt.amount))
                 .filter(Receipt.entity_id.in_(ctx.entity_ids),
                         Receipt.received_on >= this_month,
                         Receipt.received_on <= month_end(this_month)).scalar() or 0.0)
    perf = (ctx.db.query(CollectionPerformance)
            .filter(CollectionPerformance.entity_id.in_(ctx.entity_ids),
                    CollectionPerformance.month == this_month).first())
    target = perf.target if perf else None

    return {
        "total_receivable": round(total, 2),
        "overdue": round(overdue, 2),
        "overdue_pct": round((safe_div(overdue, total, 0.0) or 0.0) * 100, 1),
        "weighted_next_30d": round(weighted, 2),
        "dso": dso,
        "dso_trend": (round(dso - dso_prev, 0) if dso and dso_prev else None),
        "collected_this_month": round(float(collected), 2),
        "target_this_month": round(target, 2) if target else None,
        "vs_target_pct": (round(float(collected) / target * 100, 1)
                          if target else None),
        "basis": f"Open invoices as at {ctx.as_on:%d-%b-%y}. Weighted collectible applies each "
                 f"invoice's collection probability, which comes from that client's payment "
                 f"history unless a person has overridden it.",
        "as_on": ctx.as_on.isoformat(),
    }


def _dso(ctx: Ctx, offset_months: int = 0) -> float | None:
    """Receivables ÷ credit sales × days, on a 3-month basis."""
    starts = months_back(ctx.as_on, 3 + offset_months)
    window = starts[:3] if offset_months else starts[-3:]
    first, last = window[0], month_end(window[-1])

    sales = (ctx.db.query(func.sum(Invoice.amount))
             .filter(Invoice.entity_id.in_(ctx.entity_ids),
                     Invoice.invoice_date >= first, Invoice.invoice_date <= last).scalar() or 0.0)
    ar = (ctx.db.query(func.sum(Invoice.outstanding))
          .filter(Invoice.entity_id.in_(ctx.entity_ids),
                  Invoice.invoice_date <= last).scalar() or 0.0)
    days = (last - first).days + 1
    v = safe_div(float(ar), float(sales), None)
    return round(v * days, 0) if v else None


def concentration(ctx: Ctx) -> dict:
    """Top 5 as a share of receivables and of revenue, plus the plain sentence
    the CFO asked for about what happens if the biggest one pays late."""
    from app.config import settings
    from app.services.runway import cashout_date, runway_summary
    from app.services.burn import net_burn_average

    clients = by_client(ctx)["rows"]
    top5_ar = clients[:5]

    starts = months_back(ctx.as_on, 12)
    rev_rows = (ctx.db.query(Customer.name, func.sum(Invoice.amount))
                .join(Invoice, Invoice.customer_id == Customer.id)
                .filter(Invoice.entity_id.in_(ctx.entity_ids),
                        Invoice.invoice_date >= starts[0])
                .group_by(Customer.name)
                .order_by(func.sum(Invoice.amount).desc()).all())
    total_rev = sum(float(v or 0) for _, v in rev_rows) or 1.0

    top = clients[0] if clients else None
    impact = None
    if top:
        rw = runway_summary(ctx)
        burn = net_burn_average(ctx, 3, normalised=True) or 1.0
        base_months = rw["current"]["months"] or 0
        # 45 days later means 1.5 months of that client's outstanding is absent
        delayed = top["total_outstanding"]
        new_months = max((rw["cash_available"] - delayed * 0.6) / burn, 0)
        impact = {
            "client": top["client"],
            "delay_days": 45,
            "cashout_before": rw["current"]["cashout_date"],
            "cashout_after": cashout_date(ctx.as_on, new_months).isoformat(),
            "months_before": round(base_months, 1),
            "months_after": round(new_months, 1),
            "sentence": (f"If {top['client']} paid 45 days late, the cash-out date moves from "
                         f"{fmt_date(date.fromisoformat(rw['current']['cashout_date']))} to "
                         f"{fmt_date(cashout_date(ctx.as_on, new_months))}."),
        }

    threshold = settings.CLIENT_CONCENTRATION_THRESHOLD * 100
    return {
        "top5_receivables": [{"client": c["client"], "amount": c["total_outstanding"],
                              "pct": c["pct_of_ar"]} for c in top5_ar],
        "top5_revenue": [{"client": n, "amount": round(float(v or 0), 2),
                          "pct": round(float(v or 0) / total_rev * 100, 1)}
                         for n, v in rev_rows[:5]],
        "threshold_pct": threshold,
        "breached": bool(clients and clients[0]["pct_of_ar"] > threshold),
        "impact": impact,
        "basis": "Receivables share is as at the as-on date; revenue share is the last 12 months of billing.",
    }


def disputes(ctx: Ctx) -> dict:
    rows = (ctx.db.query(Invoice, Customer.name)
            .join(Customer, Customer.id == Invoice.customer_id)
            .filter(Invoice.entity_id.in_(ctx.entity_ids),
                    Invoice.is_disputed.is_(True), Invoice.outstanding > 0)
            .order_by(Invoice.dispute_raised_on).all())
    return {
        "total": round(sum(i.outstanding for i, _ in rows), 2),
        "rows": [{
            "id": i.id, "client": name, "invoice_no": i.invoice_no,
            "amount": round(i.outstanding, 2), "reason": i.dispute_reason,
            "raised_on": i.dispute_raised_on.isoformat() if i.dispute_raised_on else None,
            "days_open": (ctx.as_on - i.dispute_raised_on).days if i.dispute_raised_on else None,
            "owner": i.dispute_owner,
            "expected_resolution": i.expected_resolution.isoformat() if i.expected_resolution else None,
            "probability": i.collection_probability,
        } for i, name in rows],
        "basis": "Invoices flagged as disputed or withheld. Never included in the ageing buckets.",
    }


def collection_performance(ctx: Ctx) -> dict:
    """Promised vs actually received — the calibration for the weighted figure."""
    rows = (ctx.db.query(CollectionPerformance)
            .filter(CollectionPerformance.entity_id.in_(ctx.entity_ids))
            .order_by(CollectionPerformance.month).all())
    data = [{
        "month": r.month.isoformat(), "label": r.month.strftime("%b-%y"),
        "promised": round(r.promised, 2), "received": round(r.received, 2),
        "target": round(r.target, 2),
        "hit_rate": round((safe_div(r.received, r.promised, 0.0) or 0.0) * 100, 1),
    } for r in rows]
    avg = (sum(d["hit_rate"] for d in data) / len(data)) if data else None
    return {
        "rows": data,
        "average_hit_rate": round(avg, 1) if avg else None,
        "note": (f"Over the last {len(data)} months, {avg:.0f}% of what was promised "
                 f"actually arrived. Discount the weighted figure accordingly."
                 if avg else "No collection history recorded yet."),
        "basis": "Amounts customers promised in the month against what was banked in that month.",
    }


def invoicing_gap(ctx: Ctx) -> dict:
    rows = (ctx.db.query(UnbilledWork, Customer.name)
            .join(Customer, Customer.id == UnbilledWork.customer_id)
            .filter(UnbilledWork.entity_id.in_(ctx.entity_ids))
            .order_by(UnbilledWork.delivered_on).all())
    total = sum(u.amount for u, _ in rows)
    return {
        "total": round(total, 2),
        "count": len(rows),
        "rows": [{
            "id": u.id, "client": name, "description": u.description,
            "amount": round(u.amount, 2),
            "delivered_on": u.delivered_on.isoformat(),
            "days_elapsed": (ctx.as_on - u.delivered_on).days,
            "expected_invoice_date": (u.expected_invoice_date.isoformat()
                                      if u.expected_invoice_date else None),
            "blocker": u.blocker, "owner": u.owner,
        } for u, name in rows],
        "note": (f"{fmt_inr(total)} of delivered work is not yet invoiced. This is cash "
                 f"delayed by our own process, not the client's."),
        "basis": "Work recorded as delivered with no invoice raised against it.",
    }


def expected_inflows(ctx: Ctx, horizon_days: int = 120) -> list[ExpectedInflow]:
    return (ctx.db.query(ExpectedInflow)
            .filter(ExpectedInflow.entity_id.in_(ctx.entity_ids),
                    ExpectedInflow.is_received.is_(False),
                    ExpectedInflow.expected_on <= ctx.as_on + timedelta(days=horizon_days))
            .order_by(ExpectedInflow.expected_on).all())
