"""Excel export: create (with the LibreOffice formula check), history, result and download."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ExportLog, Scenario, User
from app.services.audit import audit
from app.services.export_service import create_export, export_file
from app.web.deps import Forbidden, client_ip, viewer
from app.web.templating import render
from app.web.view import forecast_for, read_view

router = APIRouter()
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.post("/export")
def export_create(request: Request, user: User = Depends(viewer), db: Session = Depends(get_db)):
    v = read_view(request, db)                  # the view currently on screen (scenario, toggles, horizon)
    fc = forecast_for(db, v)
    log = create_export(db, fc, user)
    db.commit()
    return RedirectResponse(f"/exports/{log.id}", status_code=303)


@router.get("/exports")
def exports(request: Request, user: User = Depends(viewer), db: Session = Depends(get_db)):
    logs = db.scalars(select(ExportLog).order_by(ExportLog.id.desc()).limit(100)).all()
    return render(request, "exports.html", {"user": user, "logs": logs, "names": _names(db),
                                            "scenarios": _scenarios(db)})


@router.get("/exports/{export_id}")
def export_detail(request: Request, export_id: int, user: User = Depends(viewer), db: Session = Depends(get_db)):
    log = db.get(ExportLog, export_id)
    if log is None:
        raise Forbidden("No such export.")
    return render(request, "export_result.html", {"user": user, "log": log, "names": _names(db),
                                                  "scenarios": _scenarios(db),
                                                  "available": export_file(log) is not None})


@router.get("/exports/{export_id}/download")
def export_download(request: Request, export_id: int, user: User = Depends(viewer), db: Session = Depends(get_db)):
    log = db.get(ExportLog, export_id)
    path = export_file(log) if log else None
    if path is None:
        raise Forbidden("This export is blocked or no longer available: it did not pass the formula check, "
                        "or the file has changed since it was checked.")
    audit(db, "export.download", "export_log", log.filename, user_id=user.id, ip=client_ip(request))
    db.commit()
    return FileResponse(path, media_type=XLSX, filename=log.filename)


def _names(db: Session) -> dict[int, str]:
    return {u.id: u.full_name or u.username for u in db.scalars(select(User))}


def _scenarios(db: Session) -> dict[int, str]:
    return {s.id: s.name for s in db.scalars(select(Scenario))}
