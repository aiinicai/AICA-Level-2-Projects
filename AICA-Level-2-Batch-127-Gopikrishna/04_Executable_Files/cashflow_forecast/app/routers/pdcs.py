"""PDC list (Action drop-down with Hold), live funding summary, hold register."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Override, OverrideAction, SourceType, User
from app.routers.forecast import item_context
from app.web.deps import viewer
from app.web.grid import STATUS_CSS
from app.web.templating import render
from app.web.view import forecast_for, read_view

router = APIRouter()


def _pdcs(fc, lot: str, q: str, show: str):
    out = [i for i in fc.items if i.source == "vendor_pdc" and i.status in ("active", "excluded", "beyond_horizon")]
    if lot.isdigit():
        out = [i for i in out if i.lot == int(lot)]
    if q:
        ql = q.lower()
        out = [i for i in out if ql in i.item.counterparty.lower() or ql in i.item.reference.lower()
               or ql in i.key.lower()]
    if show == "held":
        out = [i for i in out if i.hold]
    elif show == "not_held":
        out = [i for i in out if not i.hold and i.status == "active"]
    return sorted(out, key=lambda i: (i.lot if i.lot is not None else 999, i.eff_date, i.key))


@router.get("/pdcs")
def pdc_list(request: Request, lot: str = "", q: str = "", show: str = "", user: User = Depends(viewer),
             db: Session = Depends(get_db)):
    v = read_view(request, db)
    fc = forecast_for(db, v)
    items = _pdcs(fc, lot, q.strip(), show)
    ctx = item_context(db, fc, items, user, "pdc")
    ctx.update(v=v, lot=lot, q=q, show=show, status_css=STATUS_CSS,
               total=sum((i.eff_amount for i in items if i.status == "active"), 0),
               held_total=sum((i.hold.amount for i in items if i.hold), 0))
    if request.headers.get("hx-target") == "pdc-table":
        return render(request, "_pdc_table.html", ctx)
    return render(request, "pdcs.html", ctx)


@router.get("/pdcs/summary")
def pdc_summary(request: Request, user: User = Depends(viewer), db: Session = Depends(get_db)):
    fc = forecast_for(db, read_view(request, db))
    return render(request, "_hold_summary.html", {"fc": fc, "status_css": STATUS_CSS, "user": user})


@router.get("/holds")
def hold_register(request: Request, user: User = Depends(viewer), db: Session = Depends(get_db)):
    v = read_view(request, db)
    fc = forecast_for(db, v)
    history = db.scalars(select(Override).where(Override.action == OverrideAction.HOLD,
                                                Override.source_type == SourceType.VENDOR_PDC,
                                                Override.is_active.is_(False))
                         .order_by(Override.revoked_at.desc()).limit(200)).all()
    names = {u.id: u.username for u in db.scalars(select(User))}
    ctx = item_context(db, fc, fc.holds, user, "pdc")
    ctx.update(v=v, history=history, names=names, status_css=STATUS_CSS)
    return render(request, "holds.html", ctx)
