"""Lot grid, drill-down into a cell, item actions, snapshots."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.advisory.commentary import lot_commentary, summary_commentary
from app.db import get_db
from app.engine.forecast import Forecast, ItemOut
from app.models import User
from app.services import overrides as OV
from app.services.snapshots import save_snapshot
from app.web.deps import editor, viewer
from app.web.grid import STATUS_CSS, build_grid
from app.web.items import (ACTION_LABELS, HOLD_REASONS, STATUS_LABELS, actions_for, active_overrides, apply_action,
                           find_item, suggestions)
from app.web.templating import render
from app.web.view import forecast_for, read_view, refresh_daily_snapshot

router = APIRouter()


@router.get("/")
def home():
    return RedirectResponse("/forecast", status_code=303)


def grid_context(db: Session, request: Request, user: User) -> dict:
    v = read_view(request, db)
    fc = forecast_for(db, v)
    return {"user": user, "v": v, "fc": fc, "grid": build_grid(fc), "status_css": STATUS_CSS,
            "commentary": list(zip(fc.fc_lots, lot_commentary(fc))), "summary": summary_commentary(fc)}


@router.get("/forecast")
def forecast_page(request: Request, user: User = Depends(viewer), db: Session = Depends(get_db)):
    ctx = grid_context(db, request, user)
    if request.headers.get("hx-target") == "grid-area":
        return render(request, "_grid.html", ctx)
    return render(request, "forecast.html", ctx)


def item_context(db: Session, fc: Forecast, items: list[ItemOut], user: User, mode: str) -> dict:
    keys = [(i.source, i.key) for i in items]
    return {"fc": fc, "items": items, "ovr": active_overrides(db, keys), "user": user, "mode": mode,
            "actions_for": actions_for, "suggestions": suggestions, "labels": ACTION_LABELS,
            "status_labels": STATUS_LABELS, "reasons": HOLD_REASONS}


@router.get("/forecast/cell")
def cell(request: Request, lot: int, cat: int, user: User = Depends(viewer), db: Session = Depends(get_db)):
    v = read_view(request, db)
    fc = forecast_for(db, v)
    if not 0 <= lot < len(fc.fc_lots):
        return render(request, "_modal_msg.html", {"message": "That lot is no longer in the horizon."})
    items = [i for i in fc.items if i.lot == lot and i.category_id == cat]
    row = next((r for r in fc.rows if r.category_id == cat), None)
    ctx = item_context(db, fc, items, user, "cell")
    ctx.update(lot=fc.fc_lots[lot], row=row, total=sum((i.eff_amount for i in items), 0))
    return render(request, "_cell.html", ctx)


@router.post("/items/action")
async def item_action(request: Request, user: User = Depends(editor), db: Session = Depends(get_db)):
    form = dict(await request.form())
    mode = form.get("mode", "cell")
    message, error = "", ""
    try:
        message = apply_action(db, form, user.id)
        db.flush()
        refresh_daily_snapshot(db, user.id)
        db.commit()
    except OV.OverrideError as exc:
        db.rollback()
        error = str(exc)
    fc = forecast_for(db, read_view(request, db))
    it = find_item(fc, form.get("source", ""), form.get("key", ""))
    ctx = item_context(db, fc, [it] if it else [], user, mode)
    ctx.update(message=message, error=error, gone=it is None)
    headers = {"HX-Trigger": "forecast-changed"} if message else None
    return render(request, "_item.html", {**ctx, "i": it}, headers=headers)


@router.post("/snapshot")
def snapshot(request: Request, user: User = Depends(editor), db: Session = Depends(get_db)):
    v = read_view(request, db)
    fc = forecast_for(db, v)
    snap = save_snapshot(db, fc, user.id)
    db.commit()
    return render(request, "_modal_msg.html", {
        "title": "Snapshot saved",
        "message": f"Snapshot of {fc.scenario} as of {fc.as_of:%d-%b-%Y} saved for {snap.snapshot_date:%d-%b-%Y}. "
                   "Saving again today replaces it."})
