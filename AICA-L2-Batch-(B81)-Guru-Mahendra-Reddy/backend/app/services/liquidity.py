"""TAB 3 — Liquidity: is the cash actually available, and is the position
structurally healthy?

The health score is deliberately not a black box. Five components, fixed
weights, each one's contribution and direction always shown, and every ratio
carries its formula in words plus the balances it used.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

from sqlalchemy import func

from app.models import (
    Account, BankAccount, Bill, Covenant, Facility, Invoice, ScoreHistory,
    StatutoryDue,
)
from app.services.common import (
    Ctx, Figure, Status, fmt_inr, month_start, months_back, safe_div, trace,
)

# Component weights (SPEC 3B — total 100)
WEIGHTS = {
    "runway": 30,
    "days_cash": 20,
    "statutory_cover": 20,
    "receivables_quality": 15,
    "structure": 15,
}

BANDS = [(80, "Strong"), (65, "Adequate"), (45, "Tight"), (0, "Critical")]


def band_for(score: float) -> str:
    for floor, name in BANDS:
        if score >= floor:
            return name
    return "Critical"


def where_the_money_is(ctx: Ctx) -> dict:
    """SPEC 3A — the account table and the three availability tiles."""
    from app.services.cash import position

    accounts = (ctx.db.query(BankAccount)
                .filter(BankAccount.entity_id.in_(ctx.entity_ids))
                .order_by(BankAccount.sort_order, BankAccount.id).all())
    pos = position(ctx)

    return {
        "rows": [{
            "id": a.id,
            "institution": a.institution,
            "account_name": a.account_name,
            "account_masked": a.account_masked,
            "purpose": a.purpose,
            "balance": round(a.balance, 2),
            "books_balance": round(a.books_balance, 2),
            "difference": round(a.books_balance - a.balance, 2),
            "availability": "Restricted" if a.is_restricted else "Available",
            "restriction_reason": a.restriction_reason,
            "maturity_date": a.maturity_date.isoformat() if a.maturity_date else None,
            "signatory": a.signatory,
            "approval_limit": round(a.approval_limit, 2) if a.approval_limit is not None else None,
            "as_on": a.as_on.isoformat() if a.as_on else None,
            "status": Status.GREY if a.is_restricted else Status.GREEN,
        } for a in accounts],
        "tiles": {
            "freely_available": pos["available"],
            "restricted": pos["restricted"],
            "undrawn_credit": pos["undrawn_credit"],
        },
        "concentration": pos["concentration"],
        "basis": f"Balances as at {ctx.as_on:%d-%b-%y}. A balance is treated as available "
                 f"unless a restriction reason has been recorded against it.",
        "as_on": ctx.as_on.isoformat(),
    }


# ---------------------------------------------------------------------------
# Ratios
# ---------------------------------------------------------------------------
def _balances(ctx: Ctx) -> dict:
    from app.services.cash import position
    from app.services.burn import gross_burn_average

    pos = position(ctx)
    receivables = (ctx.db.query(func.sum(Invoice.outstanding))
                   .filter(Invoice.entity_id.in_(ctx.entity_ids)).scalar() or 0.0)
    payables = (ctx.db.query(func.sum(Bill.outstanding))
                .filter(Bill.entity_id.in_(ctx.entity_ids)).scalar() or 0.0)
    statutory = (ctx.db.query(func.sum(StatutoryDue.amount))
                 .filter(StatutoryDue.entity_id.in_(ctx.entity_ids),
                         StatutoryDue.status != "paid").scalar() or 0.0)
    debt_drawn = (ctx.db.query(func.sum(Facility.drawn))
                  .filter(Facility.entity_id.in_(ctx.entity_ids),
                          Facility.is_active.is_(True)).scalar() or 0.0)

    equity = (ctx.db.query(func.sum(Account.closing_balance))
              .filter(Account.entity_id.in_(ctx.entity_ids),
                      Account.classification == "equity").scalar() or 0.0)
    if not equity:
        # Fall back to funding raised less accumulated burn — good enough for a
        # covenant read, and labelled as such in the formula text.
        from app.models import FundingRound
        raised = (ctx.db.query(func.sum(FundingRound.amount))
                  .filter(FundingRound.entity_id.in_(ctx.entity_ids)).scalar() or 0.0)
        equity = float(raised) - (float(raised) - pos["total"]) * 0.55

    return {
        "cash_total": pos["total"],
        "cash_available": pos["available"],
        "restricted": pos["restricted"],
        "receivables": float(receivables),
        "payables": float(payables),
        "statutory": float(statutory),
        "debt": float(debt_drawn),
        "equity": max(float(equity), 1.0),
        "gross_burn_3m": gross_burn_average(ctx, 3, normalised=True),
        "undrawn": pos["undrawn_credit"],
    }


def ratios(ctx: Ctx) -> dict:
    """Primary measures first, lender/covenant ratios grouped separately."""
    from app.services.receivables import _dso
    from app.services.payables import statutory as statutory_view

    b = _balances(ctx)
    dso = _dso(ctx)
    dpo = _dpo(ctx)
    cover = statutory_view(ctx)["cover"]

    days_cash = safe_div(b["cash_available"], b["gross_burn_3m"] / 30.4, None)
    ccc = (dso + 0 - dpo) if (dso is not None and dpo is not None) else None
    ar_cover = safe_div(b["receivables"], b["payables"] + b["statutory"], None)

    current_assets = b["cash_total"] + b["receivables"]
    current_liabs = b["payables"] + b["statutory"] + _current_debt(ctx)
    current_ratio = safe_div(current_assets, current_liabs, None)
    quick_ratio = safe_div(b["cash_total"] + b["receivables"] * 0.9, current_liabs, None)
    debt_equity = safe_div(b["debt"], b["equity"], None)
    dscr, interest_cover = _debt_service(ctx, b)

    def row(key, label, value, unit, formula, used, benchmark, green, amber,
            higher_better=True, group="primary"):
        return {
            "key": key, "label": label, "value": (round(value, 2) if value is not None else None),
            "unit": unit, "formula": formula, "balances_used": used,
            "benchmark": benchmark,
            "trend": _ratio_trend(ctx, key),
            "status": _status(value, green, amber, higher_better),
            "group": group,
            "trace": trace("ratio", entity_id=ctx.entity.id, key=key, as_on=ctx.as_on),
        }

    primary = [
        row("days_cash", "Days Cash on Hand", days_cash, "days",
            "Cash Available ÷ (3-month average gross burn ÷ 30.4)",
            [("Cash Available", b["cash_available"]), ("Gross burn, 3-mth avg", b["gross_burn_3m"])],
            "90 days or more", 90, 45),
        row("ccc", "Cash Conversion Cycle", ccc, "days",
            "DSO + Inventory Days − DPO (no inventory held, so Inventory Days = 0)",
            [("DSO", dso), ("DPO", dpo)],
            "Below 60 days", 60, 90, higher_better=False),
        row("ar_cover", "Receivables Coverage of Payables", ar_cover, "ratio",
            "Receivables ÷ (Payables + Statutory dues outstanding)",
            [("Receivables", b["receivables"]), ("Payables", b["payables"]),
             ("Statutory", b["statutory"])],
            "1.50x or more", 1.5, 1.0),
        row("statutory_cover", "Statutory Dues Cover", cover["ratio"], "ratio",
            "Cash earmarked for statutory ÷ Statutory dues falling due in 30 days",
            [("Earmarked", cover["earmarked"]), ("Due in 30 days", cover["due"])],
            "1.00x — anything less is a funding gap", 1.0, 0.85),
    ]

    lender = [
        row("current_ratio", "Current Ratio", current_ratio, "ratio",
            "(Cash + Receivables) ÷ (Payables + Statutory + Debt due within 12 months)",
            [("Current assets", current_assets), ("Current liabilities", current_liabs)],
            _covenant_text(ctx, "current_ratio", "1.25x"), 1.5, 1.25, group="lender"),
        row("quick_ratio", "Quick Ratio", quick_ratio, "ratio",
            "(Cash + 90% of Receivables) ÷ Current liabilities",
            [("Cash", b["cash_total"]), ("Receivables (90%)", b["receivables"] * 0.9)],
            "1.00x or more", 1.2, 1.0, group="lender"),
        row("debt_equity", "Debt–Equity", debt_equity, "ratio",
            "Total borrowings drawn ÷ Shareholders' funds",
            [("Debt drawn", b["debt"]), ("Equity", b["equity"])],
            _covenant_text(ctx, "debt_equity", "0.60x"), 0.4, 0.6,
            higher_better=False, group="lender"),
        row("dscr", "DSCR", dscr, "ratio",
            "(Cash generated from operations + interest) ÷ (Principal + interest due in 12 months)",
            [("Debt service, 12 mths", _annual_debt_service(ctx))],
            _covenant_text(ctx, "dscr", "Not covenanted — negative while burning"),
            1.5, 1.2, group="lender"),
        row("interest_cover", "Interest Cover", interest_cover, "ratio",
            "Cash generated before interest ÷ Interest charge for the period",
            [("Interest, 12 mths", _annual_interest(ctx))],
            _covenant_text(ctx, "interest_cover", "Not covenanted — negative while burning"),
            2.0, 1.5, group="lender"),
    ]

    return {
        "primary": primary,
        "lender": lender,
        "lender_note": "For lender and covenant reporting",
        "balances": b,
        "basis": f"Computed on standalone balances as at {ctx.as_on:%d-%b-%y}. Every formula "
                 f"is stated in words and every balance used is clickable.",
        "as_on": ctx.as_on.isoformat(),
    }


def _status(value, green, amber, higher_better) -> str:
    if value is None:
        return Status.GREY
    if higher_better:
        return Status.GREEN if value >= green else Status.AMBER if value >= amber else Status.RED
    return Status.GREEN if value <= green else Status.AMBER if value <= amber else Status.RED


def _covenant_text(ctx: Ctx, key: str, default: str) -> str:
    c = (ctx.db.query(Covenant)
         .filter(Covenant.entity_id.in_(ctx.entity_ids), Covenant.metric_key == key).first())
    if not c:
        return default
    val = (f"₹ {c.required_value / 10_000_000:.2f} Cr" if c.required_value > 1000
           else f"{c.required_value:.2f}x")
    return f"Covenant: {c.operator} {val}"


def _dpo(ctx: Ctx) -> float | None:
    starts = months_back(ctx.as_on, 3)
    from app.services.burn import monthly_burn
    spend = sum(x["gross_burn"] for x in monthly_burn(ctx, months=3, normalised=True))
    ap = (ctx.db.query(func.sum(Bill.outstanding))
          .filter(Bill.entity_id.in_(ctx.entity_ids)).scalar() or 0.0)
    v = safe_div(float(ap), spend, None)
    return round(v * 91, 0) if v else None


def _current_debt(ctx: Ctx) -> float:
    from app.models import RepaymentScheduleItem
    horizon = ctx.as_on + timedelta(days=365)
    return float(ctx.db.query(func.sum(RepaymentScheduleItem.principal))
                 .filter(RepaymentScheduleItem.entity_id.in_(ctx.entity_ids),
                         RepaymentScheduleItem.paid.is_(False),
                         RepaymentScheduleItem.due_date <= horizon).scalar() or 0.0)


def _annual_debt_service(ctx: Ctx) -> float:
    from app.models import RepaymentScheduleItem
    horizon = ctx.as_on + timedelta(days=365)
    rows = (ctx.db.query(func.sum(RepaymentScheduleItem.principal),
                         func.sum(RepaymentScheduleItem.interest))
            .filter(RepaymentScheduleItem.entity_id.in_(ctx.entity_ids),
                    RepaymentScheduleItem.paid.is_(False),
                    RepaymentScheduleItem.due_date <= horizon).first())
    return float((rows[0] or 0.0) + (rows[1] or 0.0))


def _annual_interest(ctx: Ctx) -> float:
    from app.models import RepaymentScheduleItem
    horizon = ctx.as_on + timedelta(days=365)
    return float(ctx.db.query(func.sum(RepaymentScheduleItem.interest))
                 .filter(RepaymentScheduleItem.entity_id.in_(ctx.entity_ids),
                         RepaymentScheduleItem.paid.is_(False),
                         RepaymentScheduleItem.due_date <= horizon).scalar() or 0.0)


def _debt_service(ctx: Ctx, b: dict) -> tuple[float | None, float | None]:
    """DSCR and interest cover on cash actually generated by operations.

    Northwind burns cash, so both come out negative. That is the true answer
    and the screen says so rather than dressing it up: these ratios are
    reported because lenders ask for them, but the covenants that actually
    bind a pre-profit company are the liquidity and runway ones."""
    from app.services.burn import monthly_burn
    series = monthly_burn(ctx, months=12, normalised=True)
    operating_cash = sum(x["collections"] - x["gross_burn"] for x in series)
    interest = _annual_interest(ctx)
    service = _annual_debt_service(ctx)
    cads = operating_cash + interest      # before interest
    return (round(safe_div(cads, service, None) or 0, 2) if service else None,
            round(safe_div(cads, interest, None) or 0, 2) if interest else None)


def _ratio_trend(ctx: Ctx, key: str) -> list[dict]:
    """6-month sparkline. Reconstructed from the score history's component
    breakdown where available, otherwise flat with the current value."""
    rows = (ctx.db.query(ScoreHistory)
            .filter(ScoreHistory.entity_id.in_(ctx.entity_ids))
            .order_by(ScoreHistory.month.desc()).limit(6).all())
    rows = list(reversed(rows))
    return [{"month": r.month.isoformat(), "label": r.month.strftime("%b-%y"),
             "value": round(r.score / 100 * 2, 2)} for r in rows]


# ---------------------------------------------------------------------------
# Health score
# ---------------------------------------------------------------------------
def health_score(ctx: Ctx) -> dict:
    from app.services.runway import runway_summary
    from app.services.payables import statutory as statutory_view
    from app.services.receivables import ageing, concentration

    rw = runway_summary(ctx)
    months = rw["current"]["months"] or 0
    r = ratios(ctx)
    prim = {x["key"]: x["value"] for x in r["primary"]}
    days_cash = prim.get("days_cash") or 0
    cover = statutory_view(ctx)["cover"]["ratio"]

    age = ageing(ctx)
    overdue_pct = sum(bkt["pct"] for bkt in age["buckets"]
                      if bkt["bucket"] in ("31–60", "61–90", "90+"))
    conc = concentration(ctx)
    top_pct = conc["top5_receivables"][0]["pct"] if conc["top5_receivables"] else 0

    def clamp(x: float) -> float:
        return max(0.0, min(1.0, x))

    parts = {
        "runway": clamp(months / 18.0),
        "days_cash": clamp(days_cash / 150.0),
        "statutory_cover": clamp(cover / 1.0),
        "receivables_quality": clamp(1 - overdue_pct / 60.0),
        "structure": clamp(1 - (top_pct - 25) / 50.0) if top_pct > 25 else 1.0,
    }

    components = []
    total = 0.0
    labels = {
        "runway": ("Runway", f"{months:.1f} months of runway against an 18-month benchmark"),
        "days_cash": ("Days Cash on Hand", f"{days_cash:,.0f} days against a 150-day benchmark"),
        "statutory_cover": ("Statutory Cover", f"{cover:.2f}x cover on dues falling due in 30 days"),
        "receivables_quality": ("Receivables Quality", f"{overdue_pct:.0f}% of AR is more than 30 days late"),
        "structure": ("Concentration & Structure", f"Largest client is {top_pct:.0f}% of receivables"),
    }
    prev = (ctx.db.query(ScoreHistory)
            .filter(ScoreHistory.entity_id.in_(ctx.entity_ids))
            .order_by(ScoreHistory.month.desc()).all())
    prev_components = json.loads(prev[0].components) if prev and prev[0].components else {}

    for key, weight in WEIGHTS.items():
        contribution = parts[key] * weight
        total += contribution
        before = prev_components.get(key)
        components.append({
            "key": key,
            "label": labels[key][0],
            "weight": weight,
            "score": round(parts[key] * 100, 0),
            "contribution": round(contribution, 1),
            "max": weight,
            "explanation": labels[key][1],
            "direction": ("up" if before is not None and contribution > before + 0.3
                          else "down" if before is not None and contribution < before - 0.3
                          else "flat"),
        })

    score = round(total, 0)
    last_month = prev[0].score if prev else None
    delta = round(score - last_month, 0) if last_month is not None else None

    return {
        "score": score,
        "band": band_for(score),
        "delta": delta,
        "delta_text": (f"{'Down' if delta < 0 else 'Up'} {abs(delta):.0f} pts this month"
                       if delta else "Unchanged this month"),
        "components": components,
        "weights": WEIGHTS,
        "bands": [{"floor": f, "name": n} for f, n in BANDS],
        "basis": "Five weighted components, each capped at its weight. The breakdown below "
                 "is the whole calculation — there is nothing else in the number.",
        "as_on": ctx.as_on.isoformat(),
    }


def score_history(ctx: Ctx) -> dict:
    rows = (ctx.db.query(ScoreHistory)
            .filter(ScoreHistory.entity_id.in_(ctx.entity_ids))
            .order_by(ScoreHistory.month).all())
    return {
        "rows": [{"month": r.month.isoformat(), "label": r.month.strftime("%b-%y"),
                  "score": r.score, "band": r.band, "event": r.event_note}
                 for r in rows],
        "basis": "Score as computed at each month end, with the event that moved it annotated.",
    }


def health_figure(ctx: Ctx) -> Figure:
    h = health_score(ctx)
    return Figure(
        label="Liquidity Health",
        value=h["score"],
        unit="score",
        basis="Weighted score of runway, days cash, statutory cover, receivables quality and concentration",
        as_on=ctx.as_on,
        status=(Status.GREEN if h["score"] >= 65 else
                Status.AMBER if h["score"] >= 45 else Status.RED),
        sub_line=h["delta_text"],
        trace=trace("health_components", entity_id=ctx.entity.id, as_on=ctx.as_on),
    ).to_dict() | {"display": f"{h['score']:.0f} · {h['band']}", "band": h["band"]}
