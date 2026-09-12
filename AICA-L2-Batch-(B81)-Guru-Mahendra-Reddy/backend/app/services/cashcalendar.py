"""TAB 6 — Cash Calendar: which specific week do I have a problem in?

The forecast is built bottom-up from actual open items — named invoices, named
bills, dated statutory liabilities, the payroll date, the repayment schedule —
for as far as those items reach. Beyond that it falls back to run-rate, and it
says so: weeks 1–4 are line-item level, 5–13 are category level, and every
week carries its own confidence.
"""
from __future__ import annotations

from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from sqlalchemy import func

from app.models import (
    Bill, Commitment, Customer, ExpectedInflow, ForecastSnapshot, Invoice,
    RepaymentScheduleItem, StatutoryDue, Vendor,
)
from app.services.common import (
    Ctx, Status, fmt_date, fmt_inr, month_end, month_start, safe_div,
    week_start, weeks_forward,
)

LINE_ITEM_WEEKS = 4


def _payroll_dates(start: date, end: date, after: date) -> list[date]:
    """Last working day of each month in the window.

    `after` is the as-on date: payroll on or before it has already been paid
    and is in the actuals, so forecasting it again would double-count a month
    of people cost — which is exactly the kind of error that makes a forecast
    disagree with the runway figure.
    """
    out, cur = [], month_start(start)
    while cur <= end:
        d = month_end(cur)
        while d.weekday() >= 5:
            d -= timedelta(days=1)
        if start <= d <= end and d > after:
            out.append(d)
        cur += relativedelta(months=1)
    return out


def build_forecast(ctx: Ctx, weeks: int = 13, levers: dict | None = None) -> dict:
    """The week grid. `levers` lets the Scenarios tab re-run the same engine
    with different assumptions instead of maintaining a second one."""
    from app.services.burn import monthly_burn
    from app.services.cash import position
    from app.services.receivables import _expected_within

    levers = levers or {}
    coll_factor = float(levers.get("collections_pct_of_plan", 100)) / 100.0
    top_delay = int(levers.get("top_client_delay_days", 0))
    disc_cut = float(levers.get("discretionary_cut_pct", 0)) / 100.0
    hiring = levers.get("hiring", "plan")
    rev_factor = float(levers.get("revenue_pct_of_plan", 100)) / 100.0
    price_up = float(levers.get("price_increase_pct", 0)) / 100.0
    new_funding = float(levers.get("new_funding_amount", 0) or 0)
    new_funding_date = levers.get("new_funding_date")
    if isinstance(new_funding_date, str) and new_funding_date:
        new_funding_date = date.fromisoformat(new_funding_date)
    else:
        new_funding_date = None

    start = week_start(ctx.today)
    windows = weeks_forward(start, weeks)
    horizon_end = windows[-1][1]

    opening = position(ctx)["available"]

    # ---- inflows: open invoices -------------------------------------
    invs = (ctx.db.query(Invoice, Customer.name)
            .join(Customer, Customer.id == Invoice.customer_id)
            .filter(Invoice.entity_id.in_(ctx.entity_ids), Invoice.outstanding > 0).all())

    top_client = None
    if invs:
        by_client: dict[str, float] = {}
        for i, n in invs:
            by_client[n] = by_client.get(n, 0.0) + i.outstanding
        top_client = max(by_client, key=by_client.get)

    inflow_items: list[dict] = []
    for inv, cname in invs:
        expected = inv.promised_date or inv.due_date
        if expected <= ctx.today:
            # Already overdue: assume it lands across the next three weeks,
            # discounted by its probability.
            expected = ctx.today + timedelta(days=7 + (inv.id % 15))
        if top_client and cname == top_client and top_delay:
            expected = expected + timedelta(days=top_delay)
        prob = (inv.collection_probability or 0.6)
        if inv.is_disputed:
            prob = min(prob, 0.4)
        amount = inv.outstanding * prob * coll_factor * (1 + price_up)
        if expected <= horizon_end:
            inflow_items.append({
                "date": expected, "label": f"{cname} — {inv.invoice_no}",
                "counterparty": cname, "gross": inv.outstanding,
                "amount": amount, "row": "Collections Expected",
                "contracted": not inv.is_disputed and expected >= inv.due_date,
                "probability": prob,
            })

    for e in ctx.db.query(ExpectedInflow).filter(
            ExpectedInflow.entity_id.in_(ctx.entity_ids),
            ExpectedInflow.is_received.is_(False)).all():
        if e.expected_on <= horizon_end:
            inflow_items.append({
                "date": e.expected_on, "label": e.description,
                "counterparty": e.counterparty or "—", "gross": e.amount,
                "amount": e.amount * e.probability, "row": "Funding / Other In",
                "contracted": e.probability >= 0.8, "probability": e.probability,
            })
    if new_funding and new_funding_date and start <= new_funding_date <= horizon_end:
        inflow_items.append({
            "date": new_funding_date, "label": "New funding (scenario)",
            "counterparty": "Scenario assumption", "gross": new_funding,
            "amount": new_funding, "row": "Funding / Other In",
            "contracted": False, "probability": 1.0,
        })

    # ---- outflows ----------------------------------------------------
    outflow_items: list[dict] = []

    recent = monthly_burn(ctx, months=3, normalised=True)
    avg = {k: sum(r[k] for r in recent) / len(recent) for k in ("gross_burn", "collections")}
    from app.services.burn import burn_by_category
    cat_rows = burn_by_category(ctx)["rows"]
    cat_avg = {r["category"]: r["avg_3m"] for r in cat_rows}

    people_monthly = cat_avg.get("People", 0.0)
    if hiring == "freeze":
        people_monthly *= 0.985
    elif hiring == "accelerate":
        people_monthly *= 1.06
    for d in _payroll_dates(start, horizon_end, ctx.as_on):
        outflow_items.append({
            "date": d, "label": f"Payroll — {d:%b-%y}", "counterparty": "Employees",
            "amount": people_monthly, "row": "People Cost", "contracted": True,
        })

    for s in ctx.db.query(StatutoryDue).filter(
            StatutoryDue.entity_id.in_(ctx.entity_ids),
            StatutoryDue.status != "paid", StatutoryDue.amount > 0).all():
        d = max(s.due_date, start)
        if d <= horizon_end:
            outflow_items.append({
                "date": d, "label": f"{s.head} — {s.period}",
                "counterparty": "Government of India", "amount": s.amount,
                "row": "Statutory", "contracted": True,
            })
    # Statutory beyond the recorded schedule — keep charging run-rate
    recorded_upto = (ctx.db.query(func.max(StatutoryDue.due_date))
                     .filter(StatutoryDue.entity_id.in_(ctx.entity_ids),
                             StatutoryDue.status != "paid").scalar())
    stat_monthly = cat_avg.get("Statutory & Taxes", 0.0)
    cur = month_start(recorded_upto + relativedelta(months=1)) if recorded_upto else month_start(start)
    while cur <= horizon_end and stat_monthly:
        d = min(date(cur.year, cur.month, 20), horizon_end)
        if d >= start:
            outflow_items.append({
                "date": d, "label": f"Statutory dues — {cur:%b-%y} (estimated)",
                "counterparty": "Government of India", "amount": stat_monthly,
                "row": "Statutory", "contracted": False,
            })
        cur += relativedelta(months=1)

    bills = (ctx.db.query(Bill, Vendor.name)
             .outerjoin(Vendor, Vendor.id == Bill.vendor_id)
             .filter(Bill.entity_id.in_(ctx.entity_ids), Bill.outstanding > 0,
                     Bill.status != "paid").all())
    billed_categories_monthly = 0.0
    for b, vname in bills:
        d = b.due_date
        if d < start:
            # Already overdue. Assume it clears in the next payment run rather
            # than all of it landing on Monday of week 1.
            d = start + timedelta(days=2 + (b.id % 3) * 7)
        if d <= horizon_end:
            outflow_items.append({
                "date": d, "label": f"{vname or 'Vendor'} — {b.bill_no}",
                "counterparty": vname or "—", "amount": b.outstanding,
                "row": "Vendor Payments", "contracted": True,
                "deferrable": b.deferrable, "category": b.burn_category,
            })
            billed_categories_monthly += b.outstanding

    for r in ctx.db.query(RepaymentScheduleItem).filter(
            RepaymentScheduleItem.entity_id.in_(ctx.entity_ids),
            RepaymentScheduleItem.paid.is_(False)).all():
        if start <= r.due_date <= horizon_end:
            outflow_items.append({
                "date": r.due_date, "label": "Venture debt — principal and interest",
                "counterparty": "Alteria Capital", "amount": r.principal + r.interest,
                "row": "Other Out", "contracted": True,
            })

    # ---- residual top-up, month by month ------------------------------
    #
    # Named open items run out well before week 13: invoices get collected,
    # the bill book empties, and nobody has raised next quarter's invoices
    # yet. Left alone, the forecast would show a company that stops billing
    # but keeps paying — which is why a naive 13-week grid always disagrees
    # with the runway figure.
    #
    # So for each month in the horizon we compare what the named items add up
    # to against the actual monthly run-rate, and spread the shortfall across
    # that month's weeks. Named items dominate the near weeks; the run-rate
    # takes over as they thin out. The forecast's monthly net therefore
    # reconciles to net burn by construction, and every topped-up rupee is
    # marked estimated rather than contracted, so week confidence falls away
    # exactly where the certainty does.
    target_out = sum(r["gross_burn"] for r in recent) / len(recent)
    target_in = sum(r["collections"] for r in recent) / len(recent)

    disc_saving = (cat_avg.get("Marketing", 0.0) + cat_avg.get("Professional Fees", 0.0)) * disc_cut
    people_delta = cat_avg.get("People", 0.0) * (
        -0.015 if hiring == "freeze" else 0.06 if hiring == "accelerate" else 0.0)
    target_out = max(target_out - disc_saving + people_delta, 0.0)
    target_in = max(target_in * coll_factor * (1 + price_up)
                    * (1 + (rev_factor - 1) * 0.7), 0.0)

    named_out_by_month: dict[date, float] = {}
    named_in_by_month: dict[date, float] = {}
    weeks_by_month: dict[date, list[int]] = {}
    for idx, (ws, we) in enumerate(windows):
        weeks_by_month.setdefault(month_start(ws), []).append(idx)
    for it in outflow_items:
        m = month_start(it["date"])
        named_out_by_month[m] = named_out_by_month.get(m, 0.0) + it["amount"]
    for it in inflow_items:
        m = month_start(it["date"])
        named_in_by_month[m] = named_in_by_month.get(m, 0.0) + it["amount"]

    residual_out = {i: 0.0 for i in range(len(windows))}
    residual_in = {i: 0.0 for i in range(len(windows))}
    # A slice of spend never shows up as a dated open item — card spend, small
    # recurring debits, reimbursements. Holding it back as an always-on
    # baseline keeps the monthly total identical while stopping a week with no
    # bills due from reading as a week with no outflow at all.
    BASELINE_SHARE = 0.22

    for m, idxs in weeks_by_month.items():
        coverage = len(idxs) / 4.345          # part-months at the edges
        baseline = target_out * coverage * BASELINE_SHARE
        gap_out = max(target_out * coverage - named_out_by_month.get(m, 0.0) - baseline, 0.0)
        gap_in = max(target_in * coverage - named_in_by_month.get(m, 0.0), 0.0)
        for i in idxs:
            residual_out[i] = (baseline + gap_out) / len(idxs)
            residual_in[i] = gap_in / len(idxs)

    # ---- assemble weeks ---------------------------------------------
    rows_def = ["Collections Expected", "Funding / Other In", "People Cost",
                "Statutory", "Vendor Payments", "Other Out"]
    weeks_out = []
    running = opening
    for idx, (ws, we) in enumerate(windows):
        detail = "line-item" if idx < LINE_ITEM_WEEKS else "category"
        buckets = {r: 0.0 for r in rows_def}
        items: list[dict] = []
        contracted_amt, total_amt = 0.0, 0.0

        for it in inflow_items + outflow_items:
            if ws <= it["date"] <= we:
                buckets[it["row"]] += it["amount"]
                total_amt += abs(it["amount"])
                if it.get("contracted"):
                    contracted_amt += abs(it["amount"])
                if detail == "line-item":
                    items.append({
                        "date": it["date"].isoformat(), "label": it["label"],
                        "counterparty": it.get("counterparty"),
                        "row": it["row"], "amount": round(it["amount"], 2),
                        "direction": "in" if it["row"] in rows_def[:2] else "out",
                        "gross": round(it.get("gross", it["amount"]), 2),
                        "probability": it.get("probability"),
                        "contracted": it.get("contracted", False),
                    })

        rr_out = residual_out[idx]
        rr_in = residual_in[idx]
        buckets["Other Out"] += rr_out
        buckets["Collections Expected"] += rr_in
        total_amt += rr_out + rr_in
        if detail == "line-item" and (rr_out > 1 or rr_in > 1):
            if rr_in > 1:
                items.append({"date": ws.isoformat(),
                              "label": "Further billing and collection (run-rate estimate)",
                              "counterparty": "Estimated", "row": "Collections Expected",
                              "amount": round(rr_in, 2), "direction": "in",
                              "gross": round(rr_in, 2), "probability": None,
                              "contracted": False})
            if rr_out > 1:
                items.append({"date": ws.isoformat(),
                              "label": "Ongoing operating spend (run-rate estimate)",
                              "counterparty": "Estimated", "row": "Other Out",
                              "amount": round(rr_out, 2), "direction": "out",
                              "gross": round(rr_out, 2), "probability": None,
                              "contracted": False})

        total_in = buckets["Collections Expected"] + buckets["Funding / Other In"]
        total_out = sum(buckets[r] for r in rows_def[2:])
        net = total_in - total_out
        opening_wk = running
        running += net

        conf_ratio = safe_div(contracted_amt, total_amt, 0.0) or 0.0
        confidence = "High" if conf_ratio > 0.7 else "Medium" if conf_ratio > 0.4 else "Low"

        weeks_out.append({
            "index": idx + 1,
            "week_start": ws.isoformat(),
            "week_end": we.isoformat(),
            "label": f"W{idx + 1} · {ws:%d-%b}",
            "opening_cash": round(opening_wk, 2),
            "collections_expected": round(buckets["Collections Expected"], 2),
            "funding_other_in": round(buckets["Funding / Other In"], 2),
            "total_in": round(total_in, 2),
            "people_cost": round(buckets["People Cost"], 2),
            "statutory": round(buckets["Statutory"], 2),
            "vendor_payments": round(buckets["Vendor Payments"], 2),
            "other_out": round(buckets["Other Out"], 2),
            "total_out": round(total_out, 2),
            "net_movement": round(net, 2),
            "closing_cash": round(running, 2),
            "below_floor": running < ctx.floor,
            "breaches_zero": running < 0,
            "detail_level": detail,
            "confidence": confidence,
            "contracted_pct": round(conf_ratio * 100, 0),
            "items": sorted(items, key=lambda x: x["date"]),
        })

    lowest = min(weeks_out, key=lambda w: w["closing_cash"]) if weeks_out else None
    return {
        "weeks": weeks_out,
        "opening_cash": round(opening, 2),
        "floor": ctx.floor,
        "lowest_point": ({
            "amount": lowest["closing_cash"],
            "week_start": lowest["week_start"],
            "week_label": lowest["label"],
            "floor": ctx.floor,
            "shortfall": round(max(ctx.floor - lowest["closing_cash"], 0.0), 2),
            "breaches_floor": lowest["closing_cash"] < ctx.floor,
            "breaches_zero": lowest["closing_cash"] < 0,
            "headroom": round(lowest["closing_cash"] - ctx.floor, 2),
            "sentence": (
                f"Lowest projected cash: {fmt_inr(lowest['closing_cash'])} in the week of "
                f"{fmt_date(date.fromisoformat(lowest['week_start']))}. "
                f"Floor: {fmt_inr(ctx.floor)}. " +
                (f"Shortfall: {fmt_inr(ctx.floor - lowest['closing_cash'])}."
                 if lowest["closing_cash"] < ctx.floor else
                 f"Headroom: {fmt_inr(lowest['closing_cash'] - ctx.floor)}.")),
        } if lowest else None),
        "detail_note": f"Weeks 1–{LINE_ITEM_WEEKS} are built from named invoices and named "
                       f"payments. Weeks {LINE_ITEM_WEEKS + 1}–{weeks} are category-level "
                       f"estimates from the 3-month run-rate.",
        "accuracy": forecast_accuracy(ctx),
        "basis": f"Built from open items as at {ctx.as_on:%d-%b-%y}, projected from "
                 f"{start:%d-%b-%y}. Collections are probability-weighted.",
        "levers_applied": levers or None,
    }


def forecast_accuracy(ctx: Ctx) -> dict:
    """SPEC 6 — how wrong we have been, so the grid can be trusted or not."""
    rows = (ctx.db.query(ForecastSnapshot)
            .filter(ForecastSnapshot.entity_id.in_(ctx.entity_ids),
                    ForecastSnapshot.actual_closing.isnot(None))
            .order_by(ForecastSnapshot.week_start.desc()).limit(8).all())
    if not rows:
        return {"weeks": 0, "mean_abs_pct": None, "score": None,
                "sentence": "Not enough forecast history yet to state an accuracy."}

    errs = []
    for r in rows:
        if r.actual_closing:
            errs.append((r.forecast_closing - r.actual_closing) / abs(r.actual_closing) * 100)
    mean_abs = sum(abs(e) for e in errs) / len(errs)
    return {
        "weeks": len(errs),
        "mean_abs_pct": round(mean_abs, 1),
        "min_pct": round(min(errs), 1),
        "max_pct": round(max(errs), 1),
        "score": round(max(0.0, 100 - mean_abs * 4), 0),
        "rows": [{"week_start": r.week_start.isoformat(),
                  "label": r.week_start.strftime("%d-%b"),
                  "forecast": round(r.forecast_closing, 2),
                  "actual": round(r.actual_closing, 2),
                  "error_pct": round((r.forecast_closing - r.actual_closing)
                                     / abs(r.actual_closing) * 100, 1)}
                 for r in reversed(rows)],
        "sentence": (f"Over the last {len(errs)} weeks, actual closing cash differed from "
                     f"forecast by an average of {mean_abs:.1f}% "
                     f"(range {min(errs):.1f}% to {max(errs):.1f}%)."),
    }


def week_ahead(ctx: Ctx) -> dict:
    """SPEC 1, Band 3 — the seven-day strip, including the single-assumption
    stress: what if the top client slips?"""
    base = build_forecast(ctx, weeks=1)
    w = base["weeks"][0]

    stressed = build_forecast(ctx, weeks=1, levers={"top_client_delay_days": 30})
    sw = stressed["weeks"][0]

    from app.services.receivables import by_client
    clients = by_client(ctx)["rows"]
    top = clients[0]["client"] if clients else "the largest client"

    gross_in = sum(i["gross"] for i in w["items"] if i["direction"] == "in") \
        if w["items"] else w["total_in"]

    return {
        "week_start": w["week_start"],
        "week_end": w["week_end"],
        "opening_cash": w["opening_cash"],
        "expected_in_gross": round(gross_in, 2),
        "expected_in_weighted": w["total_in"],
        "committed_out": w["total_out"],
        "net_movement": w["net_movement"],
        "closing_cash": w["closing_cash"],
        "if_top_client_slips": {
            "client": top,
            "closing_cash": sw["closing_cash"],
            "delta": round(sw["closing_cash"] - w["closing_cash"], 2),
            "assumption": f"{top} pays 30 days later than currently expected",
        },
        "below_floor": w["below_floor"],
        "floor": ctx.floor,
        "basis": "Seven days from the Monday of the current week. 'Expected in' is shown "
                 "both gross and probability-weighted; the weighted figure is the one to use.",
    }
