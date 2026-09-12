"""TAB 8 — Scenarios.

The levers drive the same forecast engine the Cash Calendar uses, so a
scenario can never disagree with the base case for structural reasons — only
because of the assumptions the CFO changed.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

from app.models import Covenant, Scenario
from app.services.common import Ctx, Status, fmt_date, fmt_inr, safe_div

DEFAULT_LEVERS = {
    "top_client_delay_days": 0,
    "collections_pct_of_plan": 100,
    "hiring": "plan",                 # freeze | plan | accelerate
    "discretionary_cut_pct": 0,
    "funding_slip_months": 0,
    "new_funding_amount": 0,
    "new_funding_date": None,
    "revenue_pct_of_plan": 100,
    "price_increase_pct": 0,
}

LEVER_SPEC = [
    {"key": "top_client_delay_days", "label": "Top client pays … days late",
     "type": "slider", "min": -30, "max": 120, "step": 5, "unit": "days"},
    {"key": "collections_pct_of_plan", "label": "Collections at … % of plan",
     "type": "slider", "min": 50, "max": 130, "step": 5, "unit": "%"},
    {"key": "hiring", "label": "Hiring",
     "type": "choice", "options": ["freeze", "plan", "accelerate"]},
    {"key": "discretionary_cut_pct", "label": "Discretionary spend cut … %",
     "type": "slider", "min": 0, "max": 100, "step": 5, "unit": "%"},
    {"key": "funding_slip_months", "label": "Funding round slips … months",
     "type": "slider", "min": 0, "max": 12, "step": 1, "unit": "months"},
    {"key": "new_funding_amount", "label": "New funding of ₹ …",
     "type": "money", "min": 0, "max": 500000000, "step": 5000000, "unit": "inr"},
    {"key": "new_funding_date", "label": "… closes on",
     "type": "date"},
    {"key": "revenue_pct_of_plan", "label": "Revenue at … % of plan",
     "type": "slider", "min": 50, "max": 150, "step": 5, "unit": "%"},
    {"key": "price_increase_pct", "label": "Price increase of … %",
     "type": "slider", "min": 0, "max": 25, "step": 1, "unit": "%"},
]


def normalise(levers: dict | None) -> dict:
    out = dict(DEFAULT_LEVERS)
    out.update({k: v for k, v in (levers or {}).items() if k in DEFAULT_LEVERS})
    return out


def evaluate(ctx: Ctx, levers: dict | None) -> dict:
    """Run one scenario and return the result panel."""
    from app.services.burn import burn_by_category, net_burn_average
    from app.services.cash import position
    from app.services.cashcalendar import build_forecast
    from app.services.payables import statutory as statutory_view
    from app.services.runway import cashout_date, runway_summary

    lv = normalise(levers)
    base_rw = runway_summary(ctx)
    base_cashout = date.fromisoformat(base_rw["current"]["cashout_date"]) \
        if base_rw["current"]["cashout_date"] else None

    available = position(ctx)["available"] + float(lv["new_funding_amount"] or 0)

    # A delay by the largest client is a cash-timing event: that much money is
    # simply not there over the delay window. Without this the lever moved the
    # 13-week grid but left runway untouched, which made the sensitivity
    # ranking say collection speed did not matter.
    delay_days = int(lv["top_client_delay_days"] or 0)
    if delay_days:
        from app.services.receivables import by_client
        clients = by_client(ctx)["rows"]
        if clients:
            top_out = clients[0]["total_outstanding"]
            # Cap at 90 days: beyond a quarter the receivable is a recovery
            # question, not a timing one.
            available -= top_out * min(abs(delay_days), 90) / 90.0 * (1 if delay_days > 0 else -1)
            available = max(available, 0.0)

    # Burn under the scenario
    burn = net_burn_average(ctx, 3, normalised=True)
    cats = {r["category"]: r["avg_3m"] for r in burn_by_category(ctx)["rows"]}
    disc = cats.get("Marketing", 0.0) + cats.get("Professional Fees", 0.0)
    people = cats.get("People", 0.0)

    burn -= disc * float(lv["discretionary_cut_pct"]) / 100.0
    if lv["hiring"] == "freeze":
        burn -= people * 0.015
    elif lv["hiring"] == "accelerate":
        burn += people * 0.06

    coll_swing = (float(lv["collections_pct_of_plan"]) - 100) / 100.0
    rev_swing = (float(lv["revenue_pct_of_plan"]) - 100) / 100.0
    price_swing = float(lv["price_increase_pct"]) / 100.0
    from app.services.burn import monthly_burn
    coll = sum(r["collections"] for r in monthly_burn(ctx, months=3, normalised=True)) / 3
    # Price increases reach cash slowly — they apply to new billing, and the
    # existing book runs off at the old rate. 0.55 is the realisation factor.
    burn -= coll * (coll_swing + rev_swing * 0.7 + price_swing * 0.55)
    burn = max(burn, 1.0)

    months = safe_div(available, burn, None)
    new_cashout = cashout_date(ctx.as_on, months)

    fc = build_forecast(ctx, weeks=13, levers=lv)
    low = fc["lowest_point"]

    cover = statutory_view(ctx)["cover"]
    statutory_ok = cover["ratio"] >= 1.0 and (not low or not low["breaches_zero"])

    breached = _covenants_breached(ctx, available, burn)

    return {
        "levers": lv,
        "runway_months": round(months, 1) if months else None,
        "cashout_date": new_cashout.isoformat() if new_cashout else None,
        "cashout_days_moved": ((new_cashout - base_cashout).days
                               if new_cashout and base_cashout else None),
        "monthly_burn": round(burn, 2),
        "cash_available": round(available, 2),
        "lowest_cash": low["amount"] if low else None,
        "lowest_week": low["week_label"] if low else None,
        "lowest_breaches_floor": low["breaches_floor"] if low else None,
        "statutory_cover_maintained": statutory_ok,
        "covenants_breached": bool(breached),
        "covenants_breached_list": breached,
        "verdict": _verdict(months, low, statutory_ok, breached),
        "basis": "Same forecast engine as the Cash Calendar, re-run with the levers applied.",
    }


def _covenants_breached(ctx: Ctx, available: float, burn: float) -> list[str]:
    from app.services.liquidity import ratios
    out = []
    r = ratios(ctx)
    current = {x["key"]: x["value"] for x in r["primary"] + r["lender"]}
    current["cash_available"] = available
    for c in ctx.db.query(Covenant).filter(Covenant.entity_id.in_(ctx.entity_ids)).all():
        v = current.get(c.metric_key)
        if v is None:
            continue
        if c.operator in (">=", ">") and v < c.required_value:
            out.append(c.name)
        elif c.operator in ("<=", "<") and v > c.required_value:
            out.append(c.name)
    return out


def _verdict(months, low, statutory_ok, breached) -> str:
    if months is None:
        return "Not computable"
    if low and low["breaches_zero"]:
        return "Runs out of cash inside 13 weeks"
    if not statutory_ok:
        return "Statutory cover breaks"
    if breached:
        return "Covenant breach"
    if low and low["breaches_floor"]:
        return "Dips below the cash floor"
    if months >= 18:
        return "Comfortable"
    if months >= 12:
        return "Workable"
    if months >= 6:
        return "Tight"
    return "Critical"


def sensitivity(ctx: Ctx) -> dict:
    """SPEC 8 — 'What Matters Most'. Move each lever one notch and rank by how
    far the cash-out date shifts. Tells the CFO where to spend attention."""
    base = evaluate(ctx, {})
    base_cashout = date.fromisoformat(base["cashout_date"]) if base["cashout_date"] else None

    probes = [
        ("Collection speed", {"top_client_delay_days": 30}, "top client pays 30 days later"),
        ("Collections level", {"collections_pct_of_plan": 85}, "collections at 85% of plan"),
        ("Hiring pace", {"hiring": "freeze"}, "all open roles frozen"),
        ("Discretionary spend", {"discretionary_cut_pct": 50}, "discretionary spend halved"),
        ("Revenue level", {"revenue_pct_of_plan": 85}, "revenue at 85% of plan"),
        ("Pricing", {"price_increase_pct": 10}, "a 10% price increase sticks"),
    ]

    rows = []
    for label, lv, desc in probes:
        r = evaluate(ctx, lv)
        d = date.fromisoformat(r["cashout_date"]) if r["cashout_date"] else None
        shift = (d - base_cashout).days if d and base_cashout else 0
        rows.append({"lever": label, "assumption": desc, "days_moved": shift,
                     "abs_days": abs(shift),
                     "runway_months": r["runway_months"],
                     "direction": "extends" if shift > 0 else "shortens" if shift < 0 else "no change"})
    rows.sort(key=lambda r: r["abs_days"], reverse=True)

    top3 = rows[:3]
    sentence = "The three inputs that move your cash-out date most: " + " ".join(
        f"{i + 1}. {r['lever']} (± {r['abs_days']} days)" for i, r in enumerate(top3))
    return {"rows": rows, "top3": top3, "sentence": sentence,
            "base_cashout": base["cashout_date"],
            "basis": "Each lever moved one realistic notch, everything else held at base."}


def list_scenarios(ctx: Ctx) -> list[dict]:
    rows = (ctx.db.query(Scenario)
            .filter(Scenario.entity_id.in_(ctx.entity_ids))
            .order_by(Scenario.sort_order, Scenario.id).all())
    return [{
        "id": s.id, "name": s.name, "note": s.note,
        "levers": json.loads(s.levers or "{}"),
        "is_prebuilt": s.is_prebuilt, "is_pinned": s.is_pinned,
        "created_by": s.created_by,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    } for s in rows]


def compare(ctx: Ctx, scenario_ids: list[int]) -> dict:
    rows = []
    for sid in scenario_ids[:4]:
        s = ctx.db.get(Scenario, sid)
        if not s:
            continue
        r = evaluate(ctx, json.loads(s.levers or "{}"))
        rows.append({"scenario_id": s.id, "name": s.name, "note": s.note,
                     "cashout_date": r["cashout_date"],
                     "runway_months": r["runway_months"],
                     "lowest_cash": r["lowest_cash"],
                     "lowest_week": r["lowest_week"],
                     "verdict": r["verdict"],
                     "covenants_breached": r["covenants_breached"],
                     "statutory_cover_maintained": r["statutory_cover_maintained"]})
    return {"rows": rows, "basis": "Up to four saved scenarios, each re-run against the "
                                   "current position."}
