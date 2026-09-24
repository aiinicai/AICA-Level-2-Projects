"""TAB 8 — Scenarios, and TAB 10 — Board Pack."""
from __future__ import annotations

import json

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.security import get_current_user, require_write
from app.models import BoardPackSection, Scenario, User
from app.routers.deps import get_ctx, log
from app.services import boardpack as bp_svc, scenarios as sc
from app.services.common import Ctx

router = APIRouter(prefix="/api", tags=["scenarios", "board-pack"])


class ScenarioIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    note: str | None = None
    levers: dict = Field(default_factory=dict)


@router.get("/scenarios")
def list_scenarios(ctx: Ctx = Depends(get_ctx), user: User = Depends(get_current_user)):
    return {
        "scenarios": sc.list_scenarios(ctx),
        "lever_spec": sc.LEVER_SPEC,
        "defaults": sc.DEFAULT_LEVERS,
        "sensitivity": sc.sensitivity(ctx),
    }


@router.post("/scenarios/evaluate")
def evaluate(levers: dict = Body(default_factory=dict),
             ctx: Ctx = Depends(get_ctx), user: User = Depends(get_current_user)):
    """Live re-run as the CFO drags a slider. No side effects."""
    return sc.evaluate(ctx, levers)


@router.post("/scenarios/compare")
def compare(scenario_ids: list[int] = Body(..., embed=True),
            ctx: Ctx = Depends(get_ctx), user: User = Depends(get_current_user)):
    if len(scenario_ids) > 4:
        raise HTTPException(400, "Up to four scenarios can be compared side by side.")
    return sc.compare(ctx, scenario_ids)


@router.post("/scenarios")
def save_scenario(payload: ScenarioIn, ctx: Ctx = Depends(get_ctx),
                  user: User = Depends(require_write)):
    s = Scenario(entity_id=ctx.entity.id, name=payload.name, note=payload.note,
                 levers=json.dumps(sc.normalise(payload.levers)),
                 is_prebuilt=False, sort_order=50,
                 source="manual", created_by=user.name)
    ctx.db.add(s)
    ctx.db.flush()
    log(ctx, user, "created", "Scenario", f"Saved scenario '{payload.name}'.", str(s.id))
    ctx.db.commit()
    return {"id": s.id, "saved": True}


@router.delete("/scenarios/{scenario_id}")
def delete_scenario(scenario_id: int, ctx: Ctx = Depends(get_ctx),
                    user: User = Depends(require_write)):
    s = ctx.db.get(Scenario, scenario_id)
    if not s:
        raise HTTPException(404, "Scenario not found")
    if s.is_prebuilt:
        raise HTTPException(400, "Pre-built scenarios cannot be deleted — they are always "
                                 "available by design.")
    name = s.name
    ctx.db.delete(s)
    log(ctx, user, "deleted", "Scenario", f"Deleted scenario '{name}'.", str(scenario_id))
    ctx.db.commit()
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Board Pack
# ---------------------------------------------------------------------------
class PackIn(BaseModel):
    title: str | None = None
    sections: list[str] = Field(default_factory=lambda: list(BoardPackSection.ALL))
    scenario_ids: list[int] = Field(default_factory=list)
    commentary: dict[str, str] = Field(default_factory=dict)


@router.get("/board-packs")
def packs(ctx: Ctx = Depends(get_ctx), user: User = Depends(get_current_user)):
    return {"packs": bp_svc.library(ctx), "sections": BoardPackSection.ALL,
            "scenarios": sc.list_scenarios(ctx)}


@router.get("/board-packs/{pack_id}")
def pack(pack_id: int, ctx: Ctx = Depends(get_ctx), user: User = Depends(get_current_user)):
    data = bp_svc.read(ctx, pack_id)
    if not data:
        raise HTTPException(404, "Pack not found")
    return data


@router.post("/board-packs")
def generate_pack(payload: PackIn, ctx: Ctx = Depends(get_ctx),
                  user: User = Depends(require_write)):
    unknown = [s for s in payload.sections if s not in BoardPackSection.ALL]
    if unknown:
        raise HTTPException(400, f"Unknown section(s): {', '.join(unknown)}")
    p = bp_svc.generate(ctx, payload.title or "", payload.sections,
                        payload.scenario_ids, payload.commentary, user.name)
    log(ctx, user, "exported", "BoardPack",
        f"Generated board pack '{p.title}' stating {p.runway_stated:.1f} months of runway.",
        str(p.id))
    ctx.db.commit()
    return {"id": p.id, "title": p.title, "generated": True}
