"""Scenarios (all users see and compare; Admin edits), category and settings admin."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import BusinessDefaults
from app.db import get_db
from app.engine.loader import run_forecast
from app.models import Category, Direction, LineItem, Scenario, Treatment, User
from app.services.audit import audit
from app.services.settings_service import get_business_settings, update_business_settings
from app.web.deps import admin, viewer
from app.web.grid import STATUS_CSS
from app.web.templating import flash, render
from app.web.view import refresh_daily_snapshot

router = APIRouter()


# ------------------------------------------------------------------ scenarios
@router.get("/scenarios")
def scenarios(request: Request, user: User = Depends(viewer), db: Session = Depends(get_db)):
    scs = db.scalars(select(Scenario).order_by(Scenario.is_default.desc(), Scenario.name)).all()
    runs = [(sc, run_forecast(db, scenario=sc)) for sc in scs]
    return render(request, "scenarios.html", {"user": user, "runs": runs, "status_css": STATUS_CSS})


@router.post("/scenarios")
def scenario_save(request: Request, scenario_id: str = Form(""), name: str = Form(""), description: str = Form(""),
                  exclude_risk: str = Form(""), use_delay: str = Form(""), is_default: str = Form(""),
                  user: User = Depends(admin), db: Session = Depends(get_db)):
    name = name.strip()
    sc = db.get(Scenario, int(scenario_id)) if scenario_id.isdigit() else None
    clash = db.scalar(select(Scenario).where(func.lower(Scenario.name) == name.lower()))
    if not name or (clash and clash is not sc):
        flash(request, "Give the scenario a name that is not used yet.", "danger")
        return RedirectResponse("/scenarios", status_code=303)
    before = None
    if sc is None:
        sc = Scenario(name=name, created_by_id=user.id)
        db.add(sc)
    else:
        before = {"name": sc.name, "exclude_risk": sc.exclude_risk_adjusted, "delay": sc.use_delay_model}
    sc.name, sc.description = name, description.strip()
    sc.exclude_risk_adjusted, sc.use_delay_model = bool(exclude_risk), bool(use_delay)
    if is_default:
        for other in db.scalars(select(Scenario).where(Scenario.is_default)):
            other.is_default = False
        sc.is_default = True
    db.flush()
    if not db.scalar(select(Scenario).where(Scenario.is_default)):
        sc.is_default = True
    audit(db, "scenario.save", "scenario", sc.name, before=before,
          after={"exclude_risk": sc.exclude_risk_adjusted, "delay": sc.use_delay_model, "default": sc.is_default},
          user_id=user.id)
    db.commit()
    flash(request, f"Scenario '{sc.name}' saved.")
    return RedirectResponse("/scenarios", status_code=303)


# ------------------------------------------------------------------ categories
@router.get("/admin/categories")
def categories(request: Request, user: User = Depends(admin), db: Session = Depends(get_db)):
    cats = db.scalars(select(Category).order_by(Category.direction, Category.display_order, Category.name)).all()
    used = dict(db.execute(select(LineItem.category_id, func.count()).group_by(LineItem.category_id)).all())
    return render(request, "categories.html", {"user": user, "cats": cats, "used": used,
                                               "groups": sorted({c.summary_group for c in cats})})


@router.post("/admin/categories")
def category_save(request: Request, category_id: str = Form(""), name: str = Form(""), direction: str = Form(""),
                  group: str = Form(""), order: str = Form("0"), treatment: str = Form("fixed"),
                  active: str = Form(""), user: User = Depends(admin), db: Session = Depends(get_db)):
    try:
        name, group = name.strip(), group.strip() or "Other"
        if not name:
            raise ValueError("name is required")
        c = db.get(Category, int(category_id)) if category_id.isdigit() else None
        clash = db.scalar(select(Category).where(func.lower(Category.name) == name.lower()))
        if clash and clash is not c:
            raise ValueError(f"'{name}' already exists")
        before = None
        if c is None:
            c = Category(name=name, direction=Direction(direction))
            db.add(c)
        else:
            before = {"name": c.name, "group": c.summary_group, "order": c.display_order, "active": c.is_active}
            if direction and Direction(direction) != c.direction:
                n = db.scalar(select(func.count()).select_from(LineItem).where(LineItem.category_id == c.id))
                if n:
                    raise ValueError("the direction cannot change: items already use this category")
                c.direction = Direction(direction)
        c.name, c.summary_group, c.display_order = name, group, int(order or 0)
        c.default_treatment, c.is_active = Treatment(treatment), bool(active) or category_id == ""
        db.flush()
        audit(db, "category.save", "category", c.name, before=before,
              after={"group": c.summary_group, "order": c.display_order, "active": c.is_active}, user_id=user.id)
        refresh_daily_snapshot(db, user.id)
        db.commit()
        flash(request, f"Category '{c.name}' saved.")
    except ValueError as exc:
        db.rollback()
        flash(request, f"Not saved: {exc}.", "danger")
    return RedirectResponse("/admin/categories", status_code=303)


# ------------------------------------------------------------------ users
def _users_page(request: Request, user: User, db: Session, temp: dict | None = None, status_code: int = 200):
    from app.services.auth import is_locked
    from app.services.settings_service import active_roles
    users = db.scalars(select(User).order_by(User.is_active.desc(), User.username)).all()
    return render(request, "users.html", {"user": user, "users": users, "roles": active_roles(db),
                                          "locked": {u.id for u in users if is_locked(u)}, "temp": temp},
                  status_code=status_code)


@router.get("/admin/users")
def users(request: Request, user: User = Depends(admin), db: Session = Depends(get_db)):
    return _users_page(request, user, db)


@router.post("/admin/users")
def user_create(request: Request, username: str = Form(""), full_name: str = Form(""), role: str = Form("viewer"),
                user: User = Depends(admin), db: Session = Depends(get_db)):
    from app.services.auth import AuthError, create_user, temporary_password
    from app.services.settings_service import active_roles
    try:
        if role not in {r.value for r in active_roles(db)}:
            raise AuthError(f"Role '{role}' is not available.")
        temp = temporary_password()
        u = create_user(db, username, temp, role, full_name, must_change_password=True, created_by_id=user.id)
        db.commit()
    except AuthError as exc:
        db.rollback()
        flash(request, f"Not created: {exc}", "danger")
        return RedirectResponse("/admin/users", status_code=303)
    # The temporary password is shown in this response only (not stored, not put in a redirect or flash).
    return _users_page(request, user, db, {"username": u.username, "password": temp, "why": "created"})


def _target(db: Session, user_id: int) -> User:
    from app.web.deps import Forbidden
    u = db.get(User, user_id)
    if u is None:
        raise Forbidden("No such user.")
    return u


@router.post("/admin/users/{user_id}")
def user_update(request: Request, user_id: int, full_name: str = Form(""), role: str = Form(""),
                active: str = Form(""), user: User = Depends(admin), db: Session = Depends(get_db)):
    from app.services.auth import AuthError, update_user
    from app.services.settings_service import active_roles
    u = _target(db, user_id)
    try:
        allowed = {r.value for r in active_roles(db)} | {u.role.value}
        if role not in allowed:
            raise AuthError(f"Role '{role}' is not available.")
        update_user(db, user, u, full_name=full_name, role=role, is_active=bool(active))
        db.commit()
        flash(request, f"User '{u.username}' saved.")
    except AuthError as exc:
        db.rollback()
        flash(request, f"Not saved: {exc}", "danger")
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/admin/users/{user_id}/reset")
def user_reset(request: Request, user_id: int, user: User = Depends(admin), db: Session = Depends(get_db)):
    from app.services.auth import reset_password
    u = _target(db, user_id)
    if u.id == user.id:
        flash(request, "Use 'Change password' for your own account.", "warning")
        return RedirectResponse("/admin/users", status_code=303)
    temp = reset_password(db, user, u)
    db.commit()
    return _users_page(request, user, db, {"username": u.username, "password": temp, "why": "reset"})


@router.post("/admin/users/{user_id}/unlock")
def user_unlock(request: Request, user_id: int, user: User = Depends(admin), db: Session = Depends(get_db)):
    from app.services.auth import unlock
    u = _target(db, user_id)
    unlock(db, user, u)
    db.commit()
    flash(request, f"User '{u.username}' unlocked.")
    return RedirectResponse("/admin/users", status_code=303)


# ------------------------------------------------------------------ backups
@router.get("/admin/backups")
def backups(request: Request, user: User = Depends(admin)):
    from app.core.config import get_settings
    from app.services.backup import list_backups
    s = get_settings()
    return render(request, "backups.html", {"user": user, "backups": list_backups(s), "s": s})


@router.post("/admin/backups")
def backup_now(request: Request, user: User = Depends(admin), db: Session = Depends(get_db)):
    from app.services.backup import BackupError, create_backup
    try:
        path = create_backup(note=f"manual, by {user.username}")
        audit(db, "backup.create", "backup", path.name, after={"automatic": False}, user_id=user.id)
        db.commit()
        flash(request, f"Backup saved: {path.name}.")
    except (BackupError, OSError) as exc:
        flash(request, f"Backup failed: {exc}", "danger")
    return RedirectResponse("/admin/backups", status_code=303)


@router.get("/admin/backups/{name}")
def backup_download(request: Request, name: str, user: User = Depends(admin), db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse

    from app.services.backup import list_backups
    from app.web.deps import Forbidden
    match = next((b for b in list_backups() if b.path.name == name), None)     # only files from the list
    if match is None:
        raise Forbidden("No such backup.")
    audit(db, "backup.download", "backup", name, user_id=user.id)
    db.commit()
    return FileResponse(match.path, media_type="application/octet-stream", filename=name)


# ------------------------------------------------------------------ settings
SETTING_HELP = {
    "lot_scheme": "month_thirds: 1-10, 11-20, 21-month end. fixed_days: rolling lots of the lot length.",
    "lot_length_days": "Days per lot (10 gives thirds of a month).",
    "lot_anchor_date": "Blank = lots start on the 1st. month_thirds: the date's day (1-28) starts every period, "
                       "e.g. 5 -> 5 Nov-4 Dec in lots 5-14, 15-24, 25-4. fixed_days: lots repeat every lot length "
                       "from this exact date.",
    "horizon_months": "Months covered by the forecast (month_thirds).",
    "horizon_lots": "Lots covered by the forecast (fixed_days).",
    "show_month_totals": "Show a total column after each month's lots.",
    "grid_start": "current_lot: start at the lot holding the as-of date. month_start: also show earlier lots of the month, locked.",
    "max_bank_accounts_base_currency": "Maximum number of active base-currency bank accounts.",
    "funding_alert_threshold": "Commentary warns when the funding position after holds is below this.",
    "hold_default_days": "Suggested next honouring date = cheque date + this many days.",
    "cheque_validity_days": "Warn when a hold makes the cheque older than this (confirm with your banks).",
    "approver_enabled": "Switch on the Approver role: new changes wait for approval (Phase 8).",
    "base_currency": "Forecast currency.", "currency_decimals": "Decimals of the forecast currency.",
}


@router.get("/admin/settings")
def settings_page(request: Request, user: User = Depends(admin), db: Session = Depends(get_db)):
    s = get_business_settings(db)
    fields = [(k, getattr(s, k), BusinessDefaults.model_fields[k].annotation, SETTING_HELP.get(k, ""))
              for k in BusinessDefaults.model_fields]
    return render(request, "settings.html", {"user": user, "fields": fields})


@router.post("/admin/settings")
async def settings_save(request: Request, user: User = Depends(admin), db: Session = Depends(get_db)):
    form = await request.form()
    current = get_business_settings(db).model_dump()
    changes = {}
    for k, old in current.items():
        if isinstance(old, bool):
            new = bool(form.get(k))
        elif k in form:
            new = form.get(k).strip()
        else:
            continue
        if str(new) != str(old):
            changes[k] = new
    if changes:
        try:
            saved = update_business_settings(db, changes, user.id)
            audit(db, "settings.update", "app_setting", ",".join(changes),
                  before={k: current[k] for k in changes}, after={k: getattr(saved, k) for k in changes},
                  user_id=user.id)
            refresh_daily_snapshot(db, user.id)
            db.commit()
            flash(request, "Settings saved: " + ", ".join(changes) + ".")
        except (ValidationError, ValueError, KeyError) as exc:
            db.rollback()
            msg = "; ".join((f"{e['loc'][0]}: " if e['loc'] else "") + e['msg'].removeprefix("Value error, ")
                           for e in exc.errors()) if isinstance(exc, ValidationError) \
                else str(exc)
            flash(request, f"Not saved: {msg}", "danger")
    else:
        flash(request, "Nothing changed.", "info")
    return RedirectResponse("/admin/settings", status_code=303)
