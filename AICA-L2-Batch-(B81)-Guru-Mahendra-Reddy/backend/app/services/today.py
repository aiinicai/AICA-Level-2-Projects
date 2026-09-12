"""TAB 1 — Today.

Two rules shape this module. The five numbers must fit one row without
scrolling, so there are exactly five. And Band 2 is a to-do list, not a
widget: at most seven rows, ranked by cash impact, each with an owner and an
action rather than an observation.
"""
from __future__ import annotations

from datetime import date, timedelta

from app.services.common import (
    Ctx, Status, fmt_date, fmt_inr, safe_div,
)

MAX_ACTIONS = 7


def five_numbers(ctx: Ctx) -> list[dict]:
    from app.services.burn import net_burn_figure
    from app.services.cash import cash_available_figure, confidence
    from app.services.liquidity import health_figure
    from app.services.runway import cashout_figure, runway_figure

    conf = confidence(ctx)
    confident = conf["level"] == "High"

    out = [
        cashout_figure(ctx),
        cash_available_figure(ctx).to_dict(),
        net_burn_figure(ctx).to_dict(),
        runway_figure(ctx).to_dict(),
        health_figure(ctx),
    ]
    for f in out:
        # SPEC: while the confidence banner shows, every headline number carries
        # the grey dot.
        f["confident"] = f.get("confident", True) and confident
    return out


def what_needs_me(ctx: Ctx) -> dict:
    """Ranked by cash at stake. Seven rows maximum — the eighth thing is not
    urgent, it is just next."""
    from app.services.capital import covenants, next_raise
    from app.services.cashcalendar import build_forecast
    from app.services.payables import obligations, statutory as statutory_view
    from app.services.receivables import (
        by_client, disputes, invoicing_gap, open_invoices,
    )

    items: list[dict] = []

    # 1. Overdue receivables, biggest first
    for inv in sorted(open_invoices(ctx, include_disputed=False),
                      key=lambda i: i.outstanding, reverse=True)[:6]:
        late = (ctx.as_on - inv.due_date).days
        if late <= 0 or inv.outstanding < 200_000:
            continue
        from app.models import Customer
        c = ctx.db.get(Customer, inv.customer_id)
        items.append({
            "item": f"{fmt_inr(inv.outstanding)} from {c.name if c else 'client'} is "
                    f"{late} days overdue",
            "amount": inv.outstanding,
            "by_when": (inv.promised_date or ctx.today + timedelta(days=7)).isoformat(),
            "owner": (c.owner if c else None) or "Collections",
            "action": ("Chase the promised payment" if inv.promised_date
                       else "Call the finance contact and get a dated commitment"),
            "severity": Status.RED if late > 30 else Status.AMBER,
            "link": "/money-in",
            "source": "receivable",
        })

    # 2. Unfunded statutory dues
    for s in statutory_view(ctx)["rows"]:
        if s["gap"] > 0 and 0 <= s["days_to_due"] <= 30:
            items.append({
                "item": f"{s['head']} {fmt_inr(s['amount'])} due {fmt_date(date.fromisoformat(s['due_date']))}, "
                        f"funding gap {fmt_inr(s['gap'])}",
                "amount": s["gap"],
                "by_when": s["due_date"],
                "owner": "Meera Iyer",
                "action": "Earmark cash or move a discretionary payment out",
                "severity": Status.RED,
                "link": "/money-out?sub=statutory",
                "source": "statutory",
            })

    # 3. Forecast weeks that break the floor
    fc = build_forecast(ctx, weeks=13)
    for w in fc["weeks"]:
        if w["below_floor"]:
            items.append({
                "item": f"Week {w['index']} cash dips to {fmt_inr(w['closing_cash'])}, "
                        f"below the {fmt_inr(ctx.floor)} floor",
                "amount": max(ctx.floor - w["closing_cash"], 0.0),
                "by_when": w["week_start"],
                "owner": "Guru Mahendra Reddy",
                "action": "Defer a payment or pull a collection forward",
                # Breaching the floor is a red condition, not an amber one.
                "severity": Status.RED,
                "link": "/cash-calendar",
                "source": "forecast",
            })
            break   # one is enough — the calendar shows the rest

    # 4. Covenants
    cov = covenants(ctx)
    for c in cov["rows"]:
        if c["status"] in (Status.RED, Status.AMBER):
            items.append({
                "item": f"{c['name']} — currently {c['current_display']}, headroom "
                        f"{c['headroom_pct']:.1f}%",
                "amount": 0.0,
                "by_when": c["test_date"],
                "owner": "Guru Mahendra Reddy",
                "action": ("Brief the lender before the test date" if c["status"] == Status.RED
                           else "Watch — headroom is inside the warning band"),
                "severity": c["status"],
                "link": "/capital-debt",
                "source": "covenant",
                "rank_boost": 6_000_000 if c["status"] == Status.RED else 2_500_000,
            })

    # 5. Non-deferrable payments this week
    ob = obligations(ctx, horizon_days=7)
    non_def = [r for r in ob["rows"] if not r["deferrable"] and 0 <= r["days_to_due"] <= 7
               and r["kind"] == "vendor"]
    if non_def:
        total = sum(r["amount"] for r in non_def)
        items.append({
            "item": f"{fmt_inr(total)} of non-deferrable vendor payments fall due this week",
            "amount": total,
            "by_when": min(r["due_date"] for r in non_def),
            "owner": "Meera Iyer",
            "action": "Confirm the cash is in the operating account before Monday",
            "severity": Status.AMBER,
            "link": "/money-out",
            "source": "payable",
        })

    # 6. Uninvoiced work
    gap = invoicing_gap(ctx)
    if gap["total"] > 500_000:
        oldest = max((r["days_elapsed"] for r in gap["rows"]), default=0)
        items.append({
            "item": f"{fmt_inr(gap['total'])} of delivered work is still uninvoiced "
                    f"(oldest {oldest} days)",
            "amount": gap["total"] * 0.5,
            "by_when": (ctx.today + timedelta(days=5)).isoformat(),
            "owner": "Meera Iyer",
            "action": "Raise the invoices — this is the cheapest cash available",
            "severity": Status.AMBER,
            "link": "/money-in?sub=gap",
            "source": "invoicing",
        })

    # 7. Fundraise trigger
    nr = next_raise(ctx)
    if nr.get("exists") and nr.get("trigger_passed"):
        items.append({
            "item": f"Fundraise trigger date passed {abs(nr['days_until_trigger'])} days ago",
            "amount": 0.0,
            "by_when": nr["trigger_date"],
            "owner": "Guru Mahendra Reddy",
            "action": "Set a start date for the Series B process this week",
            "severity": Status.RED,
            "link": "/capital-debt?sub=raise",
            "source": "funding",
            "rank_boost": 9_000_000,
        })

    # 8. Ageing disputes
    for d in disputes(ctx)["rows"]:
        if d["days_open"] and d["days_open"] > 60:
            items.append({
                "item": f"{d['client']} dispute of {fmt_inr(d['amount'])} open {d['days_open']} days",
                "amount": d["amount"] * 0.4,
                "by_when": d["expected_resolution"] or ctx.today.isoformat(),
                "owner": d["owner"] or "Collections",
                "action": "Escalate or write down — it has been open too long to be a maybe",
                "severity": Status.AMBER,
                "link": "/money-in?sub=disputes",
                "source": "dispute",
            })

    items.sort(key=lambda r: r.get("rank_boost", 0) + r["amount"], reverse=True)
    top = items[:MAX_ACTIONS]
    for i, r in enumerate(top, start=1):
        r["priority"] = i
        r["amount"] = round(r["amount"], 2)
        r.pop("rank_boost", None)

    return {
        "rows": top,
        "shown": len(top),
        "total_found": len(items),
        "basis": (f"Ranked by cash at stake. Showing the top {MAX_ACTIONS} of {len(items)} "
                  f"open items — anything below the line is on its own tab."
                  if len(items) > MAX_ACTIONS else
                  f"Ranked by cash at stake. {len(items)} open item(s) need a decision."),
    }


def dashboard(ctx: Ctx) -> dict:
    """Everything Tab 1 needs, in one call."""
    from app.services.burn import where_the_cash_went
    from app.services.cash import confidence, monthly_cash_history, weekly_cash_history
    from app.services.cashcalendar import build_forecast, week_ahead
    from app.services.narrative import reading

    fc = build_forecast(ctx, weeks=13)
    hist = monthly_cash_history(ctx, months=12)

    forecast_line = [{
        "label": w["label"], "date": w["week_start"],
        "closing_cash": w["closing_cash"],
        "band_low": round(w["closing_cash"] * (1 - 0.03 * w["index"] / 4), 2),
        "band_high": round(w["closing_cash"] * (1 + 0.03 * w["index"] / 4), 2),
        "actual": False, "confidence": w["confidence"],
    } for w in fc["weeks"]]

    actual_line = [{
        "label": date.fromisoformat(h["month"]).strftime("%b-%y"),
        "date": h["as_on"], "closing_cash": h["closing_cash"], "actual": True,
    } for h in hist]

    return {
        "five_numbers": five_numbers(ctx),
        "what_needs_me": what_needs_me(ctx),
        "week_ahead": week_ahead(ctx),
        "reading": reading(ctx),
        "cash_chart": {
            "actual": actual_line,
            "forecast": forecast_line,
            "floor": ctx.floor,
            "title": "Cash — last 12 months and next 13 weeks",
            "basis": "Actuals are month-end closing cash from the ledger. The forecast is the "
                     "13-week calendar, with a confidence band that widens with distance.",
        },
        "where_cash_went": where_the_cash_went(ctx, months=3),
        "confidence": confidence(ctx),
        "as_on": ctx.as_on.isoformat(),
        "today": ctx.today.isoformat(),
    }
