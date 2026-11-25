"""Balances and facility, uploads (with the file-hash log), mapping exceptions and advisory findings."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.advisory.overlaps import find_overlaps
from app.core.config import PROJECT_ROOT, get_settings
from app.db import get_db
from app.engine.loader import resolve_as_of
from app.importers import exceptions as X
from app.importers.pipeline import import_file, open_exceptions
from app.importers.specs import SPECS
from app.models import (BankAccount, BankBalance, BankFacility, Category, ExceptionStatus, ImportBatch,
                        MappingException, User)
from app.services import overrides as OV
from app.services.reference_service import EntryError, set_balance, set_facility
from app.services.settings_service import get_business_settings
from app.web.deps import editor, viewer
from app.web.templating import flash, render
from app.web.view import refresh_daily_snapshot

router = APIRouter()
TEMPLATES_DIR = PROJECT_ROOT / "input_templates"
UPLOAD_SOURCES = ["category_list", "collections", "additional", "vendor_pdc", "allocation", "bill_discount", "other",
                  "bank_balances", "bank_facility", "payment_history"]


def _date(v: str, default: date | None = None) -> date | None:
    try:
        return date.fromisoformat(v) if v else default
    except ValueError:
        raise EntryError(f"'{v}' is not a date")


# ------------------------------------------------------------------ balances and facility
@router.get("/balances")
def balances(request: Request, user: User = Depends(viewer), db: Session = Depends(get_db)):
    as_of = resolve_as_of(db)
    accounts = db.scalars(select(BankAccount).order_by(BankAccount.display_order, BankAccount.id)).all()
    rows = []
    for a in accounts:
        hist = db.scalars(select(BankBalance).where(BankBalance.account_id == a.id)
                          .order_by(BankBalance.as_of_date.desc()).limit(5)).all()
        rows.append((a, hist))
    fac = db.scalars(select(BankFacility).order_by(BankFacility.as_of_date.desc(), BankFacility.bank_name)
                     .limit(30)).all()
    return render(request, "balances.html", {"user": user, "rows": rows, "facilities": fac, "as_of": as_of,
                                             "s": get_business_settings(db)})


@router.post("/balances")
def balance_save(request: Request, bank: str = Form(""), account: str = Form(""), currency: str = Form("OMR"),
                 as_of: str = Form(""), balance: str = Form(""), rate: str = Form(""),
                 user: User = Depends(editor), db: Session = Depends(get_db)):
    try:
        set_balance(db, bank=bank, account=account, currency=currency, as_of=_date(as_of, date.today()),
                    balance=balance, rate=rate, user_id=user.id)
        refresh_daily_snapshot(db, user.id)
        db.commit()
        flash(request, f"Balance saved for {bank} {account}.")
    except EntryError as exc:
        db.rollback()
        flash(request, f"Not saved: {exc}.", "danger")
    return RedirectResponse("/balances", status_code=303)


@router.post("/facility")
def facility_save(request: Request, bank: str = Form(""), facility_type: str = Form(""), as_of: str = Form(""),
                  limit: str = Form(""), utilised: str = Form(""), available: str = Form(""),
                  user: User = Depends(editor), db: Session = Depends(get_db)):
    try:
        set_facility(db, bank=bank, facility_type=facility_type, as_of=_date(as_of, date.today()), limit=limit,
                     utilised=utilised, available=available, user_id=user.id)
        refresh_daily_snapshot(db, user.id)
        db.commit()
        flash(request, f"Facility saved for {bank}.")
    except EntryError as exc:
        db.rollback()
        flash(request, f"Not saved: {exc}.", "danger")
    return RedirectResponse("/balances", status_code=303)


# ------------------------------------------------------------------ uploads
@router.get("/uploads")
def uploads(request: Request, user: User = Depends(viewer), db: Session = Depends(get_db)):
    batches = db.scalars(select(ImportBatch).order_by(ImportBatch.id.desc()).limit(100)).all()
    names = {u.id: u.username for u in db.scalars(select(User))}
    return render(request, "uploads.html", {"user": user, "batches": batches, "names": names,
                                            "sources": [SPECS[s] for s in UPLOAD_SOURCES],
                                            "limit_mb": get_settings().upload_max_mb, "today": date.today()})


@router.post("/uploads")
async def upload(request: Request, source: str = Form(...), as_of: str = Form(""), slot: str = Form(""),
                 file: UploadFile = File(...), user: User = Depends(editor), db: Session = Depends(get_db)):
    if source not in UPLOAD_SOURCES:
        flash(request, "Choose what the file contains.", "danger")
        return RedirectResponse("/uploads", status_code=303)
    limit = get_settings().upload_max_mb * 1024 * 1024
    content = await file.read(limit + 1)          # never read more than the limit (+1 to detect oversize)
    try:
        as_of_d = _date(as_of)
    except EntryError:
        as_of_d = None
    rep = import_file(db, source, file.filename or "upload", content, user_id=user.id, as_of=as_of_d,
                      slot=slot.strip() or None)
    if rep.status == "accepted":
        refresh_daily_snapshot(db, user.id)
    db.commit()
    msg = {"accepted": ("File accepted and now current.", "success"),
           "exceptions": ("File read. Some categories need mapping before it becomes current.", "warning"),
           "rejected": ("File rejected. The current data is unchanged. See the errors below.", "danger")}
    flash(request, *msg.get(rep.status, ("Done.", "info")))
    return RedirectResponse(f"/uploads/{rep.batch_id}", status_code=303)


@router.get("/uploads/{batch_id}")
def upload_report(batch_id: int, request: Request, user: User = Depends(viewer), db: Session = Depends(get_db)):
    b = db.get(ImportBatch, batch_id)
    if b is None:
        return render(request, "error.html", {"user": user, "title": "Not found", "message": "No such upload."}, 404)
    exc = db.scalars(select(MappingException).where(MappingException.batch_id == b.id)).all()
    return render(request, "upload_report.html", {"user": user, "b": b, "rep": b.validation_report or {},
                                                  "exceptions": exc})


@router.get("/templates/{name}")
def template_file(name: str, user: User = Depends(viewer)):
    allowed = {SPECS[s].template_file for s in UPLOAD_SOURCES}
    path = TEMPLATES_DIR / name
    if name not in allowed or not path.is_file():
        return HTMLResponse("Not found", status_code=404)
    return FileResponse(path, filename=name,
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ------------------------------------------------------------------ exceptions and findings
@router.get("/exceptions/count")
def exceptions_count(user: User = Depends(viewer), db: Session = Depends(get_db)):
    n = db.scalar(select(func.count()).select_from(MappingException).where(
        MappingException.status == ExceptionStatus.OPEN))
    return HTMLResponse(f'<span class="badge text-bg-danger">{n}</span>' if n else "")


@router.get("/exceptions")
def exceptions_page(request: Request, user: User = Depends(viewer), db: Session = Depends(get_db)):
    rows = []
    for e in open_exceptions(db):
        items = X._items(db, e)
        b = db.get(ImportBatch, e.batch_id)
        dirs = {li.direction.value for li in items if not li.direction_provisional}
        rows.append({"e": e, "batch": b, "n": len(items), "amount": sum((li.amount for li in items), 0),
                     "direction": dirs.pop() if len(dirs) == 1 else "",
                     "suggested": db.get(Category, e.suggested_category_id) if e.suggested_category_id else None})
    cats = db.scalars(select(Category).where(Category.is_active).order_by(Category.direction,
                                                                         Category.display_order)).all()
    groups = sorted({c.summary_group for c in cats})
    try:
        findings, findings_error = find_overlaps(db), ""
    except Exception as exc:                         # advisory only: never block the screen
        findings, findings_error = [], str(exc)
    return render(request, "exceptions.html", {"user": user, "rows": rows, "cats": cats, "groups": groups,
                                               "findings": findings, "findings_error": findings_error})


@router.post("/exceptions/{exc_id}")
def resolve_exception(exc_id: int, request: Request, how: str = Form(...), category_id: str = Form(""),
                      name: str = Form(""), direction: str = Form(""), group: str = Form(""),
                      remember: str = Form(""), user: User = Depends(editor), db: Session = Depends(get_db)):
    try:
        if how == "map":
            done = X.map_to_category(db, exc_id, int(category_id or 0), user.id, remember=bool(remember))
        elif how == "new":
            if direction not in ("inflow", "outflow"):
                raise X.ResolveError("choose inflow or outflow")
            done = X.add_new_category(db, exc_id, name=name or None, direction=direction,
                                      summary_group=group or "Other", user_id=user.id)
        elif how == "ignore":
            done = X.ignore(db, exc_id, user.id)
        else:
            raise X.ResolveError("unknown choice")
        if done:
            refresh_daily_snapshot(db, user.id)
        db.commit()
        flash(request, "Resolved." + (" The file is now current." if done else ""))
    except (X.ResolveError, ValueError) as exc:
        db.rollback()
        flash(request, f"Not resolved: {exc}.", "danger")
    return RedirectResponse("/exceptions", status_code=303)


@router.post("/findings/act")
def finding_action(request: Request, source: str = Form(...), key: str = Form(...), action: str = Form(...),
                   user: User = Depends(editor), db: Session = Depends(get_db)):
    if action not in ("exclude", "bill_discounted"):
        flash(request, "Unknown action.", "danger")
        return RedirectResponse("/exceptions", status_code=303)
    try:
        OV.set_override(db, source, key, action, reason="from advisory check", user_id=user.id)
        refresh_daily_snapshot(db, user.id)
        db.commit()
        flash(request, f"{'Excluded' if action == 'exclude' else 'Flagged as bill discounted'}: {key}.")
    except OV.OverrideError as exc:
        db.rollback()
        flash(request, f"Not saved: {exc}.", "danger")
    return RedirectResponse("/exceptions", status_code=303)
