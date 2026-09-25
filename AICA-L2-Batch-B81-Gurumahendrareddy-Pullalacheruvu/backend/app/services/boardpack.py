"""TAB 10 — Board Pack.

A pack is a frozen snapshot. Everything is computed once at generation time
and stored as JSON, so re-opening the December pack in March shows what was
actually said in December rather than what the numbers look like now.
"""
from __future__ import annotations

import json
from datetime import date, datetime

from app.models import BoardPack, BoardPackSection, Scenario
from app.services.common import Ctx, fmt_date, fmt_inr


def build_snapshot(ctx: Ctx, sections: list[str], scenario_ids: list[int]) -> dict:
    from app.services import (
        burn, capital, cashcalendar, liquidity, narrative, payables,
        receivables, runway, scenarios as sc, variance,
    )

    snap: dict = {"generated_for": ctx.entity.name, "as_on": ctx.as_on.isoformat()}

    if BoardPackSection.CASH_RUNWAY in sections:
        from app.services.cash import position
        snap["cash_runway"] = {
            "position": position(ctx),
            "runway": runway.runway_summary(ctx),
            "movement": runway.runway_movement(ctx),
            "milestones": runway.milestones(ctx),
            "health": liquidity.health_score(ctx),
        }
    if BoardPackSection.BURN in sections:
        snap["burn"] = {
            "summary": burn.burn_summary(ctx),
            "by_category": burn.burn_by_category(ctx),
            "recurring_vs_one_off": burn.recurring_vs_one_off(ctx),
            "per_unit": burn.burn_per_unit(ctx, months=6),
        }
    if BoardPackSection.COLLECTIONS in sections:
        snap["collections"] = {
            "summary": receivables.summary(ctx),
            "ageing": receivables.ageing(ctx),
            "concentration": receivables.concentration(ctx),
            "performance": receivables.collection_performance(ctx),
        }
    if BoardPackSection.PLAN_VS_ACTUAL in sections:
        snap["plan_vs_actual"] = variance.plan_vs_actual(ctx)
    if BoardPackSection.FORECAST in sections:
        snap["forecast"] = cashcalendar.build_forecast(ctx, weeks=13)
    if BoardPackSection.SCENARIOS in sections and scenario_ids:
        snap["scenarios"] = sc.compare(ctx, scenario_ids)
        snap["sensitivity"] = sc.sensitivity(ctx)
    if BoardPackSection.FUNDING in sections:
        snap["funding"] = {
            "facilities": capital.facilities(ctx),
            "covenants": capital.covenants(ctx),
            "history": capital.funding_history(ctx),
            "next_raise": capital.next_raise(ctx),
        }
    if BoardPackSection.RISKS in sections:
        from app.services.today import what_needs_me
        snap["risks"] = {
            "reading": narrative.reading(ctx),
            "what_needs_me": what_needs_me(ctx),
            "statutory_cover": payables.statutory(ctx)["cover"],
        }
    return snap


def generate(ctx: Ctx, title: str, sections: list[str], scenario_ids: list[int],
             commentary: dict[str, str], user_name: str) -> BoardPack:
    from app.services.burn import net_burn_average
    from app.services.cash import confidence, position
    from app.services.runway import runway_summary

    snap = build_snapshot(ctx, sections, scenario_ids)
    rw = runway_summary(ctx)
    conf = confidence(ctx)

    pack = BoardPack(
        entity_id=ctx.entity.id,
        title=title or f"{ctx.entity.name} — cash position as on {fmt_date(ctx.as_on)}",
        as_on=ctx.as_on,
        generated_by=user_name,
        sections=json.dumps(sections),
        scenario_ids=json.dumps(scenario_ids),
        snapshot=json.dumps(snap, default=str),
        commentary=json.dumps(commentary or {}),
        runway_stated=rw["current"]["months"],
        cashout_stated=(date.fromisoformat(rw["current"]["cashout_date"])
                        if rw["current"]["cashout_date"] else None),
        cash_available_stated=position(ctx)["available"],
        net_burn_stated=net_burn_average(ctx, 3, normalised=True),
        confidence=conf["level"],
    )
    ctx.db.add(pack)
    ctx.db.flush()
    return pack


def library(ctx: Ctx) -> list[dict]:
    rows = (ctx.db.query(BoardPack)
            .filter(BoardPack.entity_id.in_(ctx.entity_ids))
            .order_by(BoardPack.generated_on.desc()).all())
    return [{
        "id": p.id, "title": p.title, "as_on": p.as_on.isoformat(),
        "generated_by": p.generated_by, "generated_on": p.generated_on.isoformat(),
        "sections": json.loads(p.sections or "[]"),
        "runway_stated": p.runway_stated,
        "cashout_stated": p.cashout_stated.isoformat() if p.cashout_stated else None,
        "cash_available_stated": p.cash_available_stated,
        "net_burn_stated": p.net_burn_stated,
        "confidence": p.confidence,
    } for p in rows]


def read(ctx: Ctx, pack_id: int) -> dict | None:
    p = ctx.db.get(BoardPack, pack_id)
    if not p:
        return None
    return {
        "id": p.id, "title": p.title, "as_on": p.as_on.isoformat(),
        "generated_by": p.generated_by, "generated_on": p.generated_on.isoformat(),
        "sections": json.loads(p.sections or "[]"),
        "scenario_ids": json.loads(p.scenario_ids or "[]"),
        "snapshot": json.loads(p.snapshot or "{}"),
        "commentary": json.loads(p.commentary or "{}"),
        "runway_stated": p.runway_stated,
        "cashout_stated": p.cashout_stated.isoformat() if p.cashout_stated else None,
        "confidence": p.confidence,
        "note": "This pack is a frozen snapshot taken at generation time. The figures "
                "below are exactly what was issued and are not recomputed.",
    }
