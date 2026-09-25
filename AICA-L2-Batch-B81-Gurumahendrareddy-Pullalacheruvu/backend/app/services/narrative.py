"""TAB 1, Band 4 — Reading of the Position.

The AI agent in this product does exactly one thing: it reads a structured
pack of facts the engine has already computed and writes four to six sentences
about them. It is never asked to compute a number, and it is never given
anything it could hallucinate a figure from — every value in the prompt is
pre-formatted text.

If no API key is configured, or the call fails, a deterministic narrator
writes the same shape of paragraph from the same facts. The screen never shows
an error and never shows nothing.

And when confidence is Low, the box collapses to the gaps line only. The CFO
was explicit: silence beats confident narration on bad data.
"""
from __future__ import annotations

import json
from datetime import date

from app.config import settings
from app.services.common import Ctx, fmt_date, fmt_inr, fmt_pct


def _facts(ctx: Ctx) -> dict:
    from app.services.burn import burn_by_category, net_burn_average
    from app.services.cash import confidence, position
    from app.services.cashcalendar import build_forecast, week_ahead
    from app.services.liquidity import health_score
    from app.services.payables import statutory as statutory_view
    from app.services.receivables import concentration, invoicing_gap, summary as ar_summary
    from app.services.runway import milestones, runway_movement, runway_summary

    pos = position(ctx)
    rw = runway_summary(ctx)
    mv = runway_movement(ctx)
    hs = health_score(ctx)
    ar = ar_summary(ctx)
    conc = concentration(ctx)
    cover = statutory_view(ctx)["cover"]
    fc = build_forecast(ctx, weeks=13)
    wk = week_ahead(ctx)
    ms = milestones(ctx)
    conf = confidence(ctx)
    gap = invoicing_gap(ctx)
    cats = burn_by_category(ctx)["rows"][:3]

    return {
        "as_on": fmt_date(ctx.as_on),
        "cash_available": fmt_inr(pos["available"]),
        "restricted": fmt_inr(pos["restricted"]),
        "undrawn_credit": fmt_inr(pos["undrawn_credit"]),
        "net_burn": fmt_inr(net_burn_average(ctx, 3, normalised=True)),
        "runway_months": f"{rw['current']['months']:.1f}" if rw["current"]["months"] else "—",
        "cashout_date": fmt_date(date.fromisoformat(rw["current"]["cashout_date"]))
        if rw["current"]["cashout_date"] else "—",
        "fundraise_trigger": fmt_date(date.fromisoformat(rw["fundraise_trigger_date"]))
        if rw["fundraise_trigger_date"] else "—",
        "fundraise_trigger_passed": rw["fundraise_trigger_passed"],
        "runway_movement": mv.get("narrative", ""),
        "runway_change_months": mv.get("change_months"),
        "health_score": f"{hs['score']:.0f} ({hs['band']})",
        "health_delta": hs["delta_text"],
        "weakest_component": min(hs["components"],
                                 key=lambda c: c["contribution"] / max(c["max"], 1))["label"],
        "receivables": fmt_inr(ar["total_receivable"]),
        "overdue": fmt_inr(ar["overdue"]),
        "overdue_pct": fmt_pct(ar["overdue_pct"]),
        "weighted_30d": fmt_inr(ar["weighted_next_30d"]),
        "dso": f"{ar['dso']:.0f} days" if ar["dso"] else "—",
        "top_client": conc["top5_receivables"][0]["client"] if conc["top5_receivables"] else "—",
        "top_client_pct": (f"{conc['top5_receivables'][0]['pct']:.0f}%"
                           if conc["top5_receivables"] else "—"),
        "top_client_impact": conc["impact"]["sentence"] if conc.get("impact") else "",
        "statutory_sentence": cover["sentence"],
        "statutory_gap": fmt_inr(cover["gap"]),
        "lowest_point": fc["lowest_point"]["sentence"] if fc["lowest_point"] else "",
        "lowest_breaches_floor": fc["lowest_point"]["breaches_floor"] if fc["lowest_point"] else False,
        "forecast_accuracy": fc["accuracy"]["sentence"],
        "week_closing": fmt_inr(wk["closing_cash"]),
        "week_net": fmt_inr(wk["net_movement"]),
        "milestone_note": ms.get("note", ""),
        "invoicing_gap": fmt_inr(gap["total"]),
        "top_categories": ", ".join(f"{c['category']} {fmt_inr(c['this_month'])}" for c in cats),
        "confidence": conf["level"],
        "confidence_reasons": conf["reasons"],
    }


def _gaps(ctx: Ctx, f: dict) -> list[str]:
    """What the tool cannot see. Named explicitly, because a CFO reading a
    commentary needs to know its blind spots before trusting it."""
    from app.models import BankStatementImport, Commitment, ExpectedInflow
    from app.services.payables import commitments as commitments_view

    gaps: list[str] = []
    gaps.extend(f["confidence_reasons"])

    com = commitments_view(ctx)
    if com["summary"]["remaining"]:
        gaps.append(f"{fmt_inr(com['summary']['remaining'])} of committed spend is not in the "
                    f"books and depends on a manually maintained register.")

    pipeline = (ctx.db.query(ExpectedInflow)
                .filter(ExpectedInflow.entity_id.in_(ctx.entity_ids),
                        ExpectedInflow.inflow_type == "Funding",
                        ExpectedInflow.is_received.is_(False)).count())
    if pipeline:
        gaps.append("Funding inflows are recorded at an assumed probability and are excluded "
                    "from every base-case figure.")

    last_stmt = (ctx.db.query(BankStatementImport)
                 .filter(BankStatementImport.entity_id.in_(ctx.entity_ids))
                 .order_by(BankStatementImport.as_on.desc()).first())
    if not last_stmt:
        gaps.append("No bank statement has been uploaded, so the bank position is the "
                    "balance recorded manually rather than a verified feed.")

    gaps.append("Sales pipeline, contract renewals and client credit standing are outside "
                "this tool entirely.")
    return gaps


PROMPT = """You are writing the "Reading of the Position" box in a CFO cash tool.

Write 4 to 6 sentences of plain English, in this order:
1. What changed since last week and why.
2. The single biggest risk in the next 30 days.
3. What the CFO should be deciding now.

Rules:
- Use ONLY the facts given. Never invent, adjust or recompute a figure.
- Quote figures exactly as they appear in the facts, including the ₹ notation.
- No greeting, no heading, no bullet points, no closing summary.
- Write to a Chartered Accountant. Direct, unhedged, no cheerleading.
- Do not write the "Not visible to me" line — it is added separately.

FACTS
{facts}
"""


def _ai_narrative(facts: dict) -> str | None:
    if not (settings.AI_ENABLED and settings.ANTHROPIC_API_KEY):
        return None
    try:
        import anthropic  # imported lazily so the app runs without the SDK
    except ImportError:
        return None
    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model=settings.AI_MODEL,
            max_tokens=520,
            messages=[{"role": "user",
                       "content": PROMPT.format(facts=json.dumps(facts, indent=2))}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
        return text or None
    except Exception:
        return None


def _rule_narrative(ctx: Ctx, f: dict) -> str:
    """Deterministic narrator. Same structure, same facts, no API needed."""
    s: list[str] = []

    change = f.get("runway_change_months")
    if change is not None and abs(change) >= 0.1:
        direction = "shortened" if change < 0 else "lengthened"
        driver = (f"collections against {f['top_client']} not landing and spend running "
                  f"ahead of plan" if change < 0 else
                  f"collections arriving ahead of expectation and spend running below plan")
        s.append(f"{f['runway_movement']} Runway {direction} by {abs(change):.1f} months, "
                 f"driven mainly by {driver}.")
    else:
        s.append(f"Runway is broadly unchanged at {f['runway_months']} months on "
                 f"{f['cash_available']} of available cash and a net burn of {f['net_burn']}.")

    s.append(f"The liquidity score is {f['health_score']}, {f['health_delta'].lower()}, with "
             f"{f['weakest_component']} the weakest component.")

    risks = []
    if f["statutory_gap"] not in ("₹ 0", "—"):
        risks.append(f"{f['statutory_sentence']}")
    if f["lowest_breaches_floor"]:
        risks.append(f["lowest_point"])
    if f["top_client_impact"]:
        risks.append(f["top_client_impact"])
    if risks:
        # These are complete sentences, so lead into them rather than splicing
        # one into a clause.
        s.append(f"The biggest exposure in the next 30 days: {risks[0]}")
    else:
        s.append(f"The biggest exposure in the next 30 days is the {f['overdue']} of "
                 f"receivables already past due, {f['overdue_pct']} of the book.")

    if len(risks) > 1:
        s.append(risks[1])

    decisions = []
    if f["fundraise_trigger_passed"]:
        decisions.append(f"the fundraise trigger date of {f['fundraise_trigger']} has already "
                         f"passed, so the Series B process needs a start date this week")
    if f["statutory_gap"] not in ("₹ 0", "—"):
        decisions.append(f"the {f['statutory_gap']} statutory funding gap needs to be closed "
                         f"before the due date, not on it")
    if f["invoicing_gap"] not in ("₹ 0", "—"):
        decisions.append(f"{f['invoicing_gap']} of delivered work is still uninvoiced and is "
                         f"the fastest cash available without asking anyone for anything")
    s.append("Decisions that cannot wait: " + "; ".join(decisions[:3]) + "." if decisions
             else "No decision is forced this week, but the position should be reviewed again "
                  "before month end.")

    return " ".join(s)


def reading(ctx: Ctx) -> dict:
    f = _facts(ctx)
    gaps = _gaps(ctx, f)
    confidence = f["confidence"]

    if confidence == "Low":
        # Collapse to the gaps line only. Silence beats confident narration.
        return {
            "collapsed": True,
            "confidence": confidence,
            "text": None,
            "not_visible": gaps,
            "footer": f"Based on data as on {f['as_on']}. Confidence: {confidence}.",
            "reason": "Commentary is suppressed while confidence is Low. The gaps below are "
                      "why.",
            "source": "suppressed",
        }

    text = _ai_narrative(f)
    source = "ai" if text else "rules"
    if not text:
        text = _rule_narrative(ctx, f)

    return {
        "collapsed": False,
        "confidence": confidence,
        "text": text,
        "not_visible": gaps,
        "footer": f"Based on data as on {f['as_on']}. Confidence: {confidence}.",
        "source": source,
        "facts": f,
    }
