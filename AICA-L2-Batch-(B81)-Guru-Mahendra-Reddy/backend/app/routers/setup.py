"""TAB 12 — Setup. Four layers: data sources, plan upload, alert rules
(in routers/alerts.py), and people & definitions."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from fastapi import (
    APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile,
)
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.security import (
    get_current_user, hash_password, require_approver, require_write,
)
from app.database import get_db
from app.models import (
    BankStatementImport, Definition, Entity, Plan, Role, Setting, SyncRun, User,
)
from app.routers.deps import get_ctx, log
from app.services import planimport
from app.services.common import Ctx, fmt_inr

router = APIRouter(prefix="/api/setup", tags=["setup"])


# ---------------------------------------------------------------------------
# 12A — Data sources
# ---------------------------------------------------------------------------
@router.get("/data-sources")
def data_sources(ctx: Ctx = Depends(get_ctx), user: User = Depends(get_current_user)):
    from app.adapters.tally import TallyClient
    from app.config import settings

    runs = (ctx.db.query(SyncRun)
            .filter(SyncRun.entity_id.in_(ctx.entity_ids))
            .order_by(SyncRun.started_at.desc()).limit(30).all())
    last_ok = next((r for r in runs if r.status == "success"), None)
    statements = (ctx.db.query(BankStatementImport)
                  .filter(BankStatementImport.entity_id.in_(ctx.entity_ids))
                  .order_by(BankStatementImport.as_on.desc()).limit(20).all())
    schedule = (ctx.db.query(Setting)
                .filter(Setting.entity_id.in_(ctx.entity_ids),
                        Setting.key == "sync_schedule").first())

    return {
        "connector": {
            "name": "Tally Prime",
            "url": f"http://{settings.TALLY_HOST}:{settings.TALLY_PORT}",
            "company": ctx.entity.tally_company,
            "configured": bool(ctx.entity.tally_company),
        },
        "roadmap": [
            {"name": "Zoho Books", "status": "Planned — REST API, OAuth2"},
            {"name": "QuickBooks / Xero", "status": "Planned"},
            {"name": "Generic CSV / Excel", "status": "Planned"},
        ],
        "last_success": ({"at": last_ok.started_at.isoformat(),
                          "records": last_ok.records} if last_ok else None),
        "schedule": schedule.value if schedule else "Manual only",
        "history": [{
            "id": r.id, "source": r.source,
            "started_at": r.started_at.isoformat(),
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "status": r.status, "records": r.records, "message": r.message,
            "triggered_by": r.triggered_by,
        } for r in runs],
        "bank_statements": [{
            "id": s.id, "filename": s.filename, "as_on": s.as_on.isoformat(),
            "closing_balance": s.closing_balance,
            "rows_accepted": s.rows_accepted, "rows_rejected": s.rows_rejected,
            "uploaded_by": s.uploaded_by, "uploaded_at": s.uploaded_at.isoformat(),
        } for s in statements],
    }


@router.get("/tally/ping")
def tally_ping(user: User = Depends(get_current_user)):
    from app.adapters.tally import TallyClient
    return TallyClient().ping()


@router.post("/tally/sync")
def tally_sync(from_date: date | None = Body(None, embed=True),
               to_date: date | None = Body(None, embed=True),
               ctx: Ctx = Depends(get_ctx), user: User = Depends(require_write)):
    """Pull from Tally and normalise into the common schema.

    Every run is recorded — including the failures, because Setup shows sync
    failure history and a connector that quietly stops working is the worst
    kind of data problem."""
    from app.adapters import normalizer
    from app.adapters.tally import TallyClient, TallyError, fetch_bills_outstanding, \
        fetch_ledgers, fetch_vouchers

    run = SyncRun(entity_id=ctx.entity.id, source="tally", triggered_by=user.name,
                  status="running")
    ctx.db.add(run)
    ctx.db.flush()

    client = TallyClient()
    company = ctx.entity.tally_company
    a = from_date or (ctx.as_on.replace(day=1))
    b = to_date or ctx.today

    try:
        ledgers = fetch_ledgers(client, company)
        led_stats = normalizer.normalise_ledgers(ctx.db, ctx.entity, ledgers)

        vouchers = fetch_vouchers(client, a, b, company)
        v_stats = normalizer.normalise_vouchers(ctx.db, ctx.entity, vouchers)

        bills = (fetch_bills_outstanding(client, b, company, receivable=True)
                 + fetch_bills_outstanding(client, b, company, receivable=False))
        b_stats = normalizer.normalise_bills(ctx.db, ctx.entity, bills, b)

        records = (led_stats["accounts_created"] + v_stats["entries_created"]
                   + b_stats["invoices_created"] + b_stats["bills_created"])
        unmapped = led_stats["unmapped_ledgers"]
        run.status = "partial" if unmapped else "success"
        run.records = records
        run.message = (f"{len(unmapped)} ledger(s) had no category mapping and were "
                       f"classified as Other: {', '.join(unmapped[:8])}"
                       f"{'…' if len(unmapped) > 8 else ''}") if unmapped else None
        run.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        ctx.entity.last_data_update = run.finished_at

        log(ctx, user, "synced", "Tally",
            f"Tally sync {run.status} — {records} record(s) from {a:%d-%b-%y} to {b:%d-%b-%y}.")
        ctx.db.commit()
        return {"status": run.status, "records": records,
                "ledgers": led_stats, "vouchers": v_stats, "bills": b_stats,
                "message": run.message}

    except TallyError as e:
        run.status = "failed"
        run.message = str(e)
        run.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        ctx.db.commit()
        raise HTTPException(502, str(e))


@router.post("/bank-statement")
async def upload_bank_statement(
    file: UploadFile = File(...),
    as_on: date = Form(...),
    closing_balance: float = Form(...),
    bank_account_id: int | None = Form(None),
    ctx: Ctx = Depends(get_ctx), user: User = Depends(require_write),
):
    content = await file.read()
    rows_accepted = max(content.count(b"\n") - 1, 0)
    imp = BankStatementImport(
        entity_id=ctx.entity.id, bank_account_id=bank_account_id,
        filename=file.filename or "statement", as_on=as_on,
        closing_balance=closing_balance, rows_accepted=rows_accepted,
        rows_rejected=0, uploaded_by=user.name)
    ctx.db.add(imp)

    if bank_account_id:
        from app.models import BankAccount
        acc = ctx.db.get(BankAccount, bank_account_id)
        if acc:
            acc.balance = closing_balance
            acc.as_on = as_on
            acc.updated_by = user.name

    log(ctx, user, "uploaded", "BankStatement",
        f"Uploaded {file.filename} as on {as_on:%d-%b-%y}, closing "
        f"{fmt_inr(closing_balance)}.")
    ctx.db.commit()
    return {"id": imp.id, "rows_accepted": rows_accepted}


# ---------------------------------------------------------------------------
# 12B — Upload Plan
# ---------------------------------------------------------------------------
@router.get("/plan/template")
def plan_template(user: User = Depends(get_current_user)):
    data = planimport.build_template()
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition":
                 'attachment; filename="Cash_Runway_Plan_Template.xlsx"'})


@router.post("/plan/validate")
async def plan_validate(
    file: UploadFile = File(...),
    mapping: str | None = Form(None),
    opening_cash: float | None = Form(None),
    ctx: Ctx = Depends(get_ctx), user: User = Depends(require_write),
):
    content = await file.read()
    header, rows = planimport.read_workbook(content, file.filename or "plan.xlsx")
    if not header:
        raise HTTPException(400, "The file appears to be empty.")

    mapped = json.loads(mapping) if mapping else planimport.auto_map(header)
    report = planimport.validate(ctx, header, rows, mapped, opening_cash)
    parsed = report.pop("_parsed")
    report["header"] = header
    report["mapping"] = mapped
    report["auto_mapped"] = mapping is None
    report["profiles"] = planimport.list_profiles(ctx)
    report["diff"] = planimport.diff_against_active(ctx, parsed) if parsed else None
    report["filename"] = file.filename
    return report


@router.post("/plan/save")
async def plan_save(
    file: UploadFile = File(...),
    name: str = Form(...),
    version: str = Form(...),
    note: str | None = Form(None),
    mapping: str | None = Form(None),
    opening_cash: float | None = Form(None),
    make_active: bool = Form(True),
    save_profile_as: str | None = Form(None),
    ctx: Ctx = Depends(get_ctx), user: User = Depends(require_write),
):
    content = await file.read()
    header, rows = planimport.read_workbook(content, file.filename or "plan.xlsx")
    mapped = json.loads(mapping) if mapping else planimport.auto_map(header)
    report = planimport.validate(ctx, header, rows, mapped, opening_cash)
    parsed = report.pop("_parsed")

    if not report["can_save"]:
        raise HTTPException(400, f"The file did not pass validation: {report['summary']}")

    existing = (ctx.db.query(Plan)
                .filter(Plan.entity_id == ctx.entity.id, Plan.version == version).first())
    if existing:
        raise HTTPException(400, f"Version '{version}' already exists. Use a new version "
                                 f"number — plan versions are never overwritten.")

    plan = planimport.save_plan(ctx, parsed, name, version, note,
                                report["opening_cash"], file.filename, user.name,
                                make_active=make_active)
    if save_profile_as:
        planimport.save_profile(ctx, save_profile_as, mapped, user.name)

    log(ctx, user, "uploaded", "Plan",
        f"Uploaded '{name}' {version} covering {plan.period_from:%b-%y} to "
        f"{plan.period_to:%b-%y}"
        + (" and made it active." if make_active else "."), str(plan.id))
    ctx.db.commit()
    return {"id": plan.id, "version": plan.version, "is_active": plan.is_active,
            "validation": report}


@router.post("/plan/{plan_id}/activate")
def plan_activate(plan_id: int, ctx: Ctx = Depends(get_ctx),
                  user: User = Depends(require_write)):
    plan = ctx.db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    for p in ctx.db.query(Plan).filter(Plan.entity_id == ctx.entity.id).all():
        p.is_active = (p.id == plan_id)
    log(ctx, user, "updated", "Plan", f"Made '{plan.name}' {plan.version} the active plan.",
        str(plan.id))
    ctx.db.commit()
    return {"ok": True}


class ApproveIn(BaseModel):
    seconded_by: str = Field(min_length=2)


@router.post("/plan/{plan_id}/board-approve")
def plan_board_approve(plan_id: int, payload: ApproveIn, ctx: Ctx = Depends(get_ctx),
                       user: User = Depends(require_approver)):
    """Marking a plan board-approved locks it, and needs a second approver —
    the CFO was explicit that this one action is not a solo click."""
    plan = ctx.db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    if payload.seconded_by.strip().lower() == user.name.strip().lower():
        raise HTTPException(400, "The second approver must be a different person.")

    plan.board_approved = True
    plan.is_locked = True
    plan.approved_by = user.name
    plan.seconded_by = payload.seconded_by
    plan.approved_on = ctx.today
    log(ctx, user, "approved", "Plan",
        f"Board-approved '{plan.name}' {plan.version}, seconded by {payload.seconded_by}. "
        f"The plan is now locked.", str(plan.id))
    ctx.db.commit()
    return {"ok": True, "locked": True}


@router.post("/plan/mapping-profile")
def save_mapping_profile(name: str = Body(..., embed=True),
                         mapping: dict = Body(..., embed=True),
                         ctx: Ctx = Depends(get_ctx),
                         user: User = Depends(require_write)):
    profiles = planimport.save_profile(ctx, name, mapping, user.name)
    ctx.db.commit()
    return {"profiles": profiles}


# ---------------------------------------------------------------------------
# 12D — People & definitions
# ---------------------------------------------------------------------------
class UserIn(BaseModel):
    name: str
    email: EmailStr
    role: str
    phone: str | None = None
    password: str | None = None
    is_active: bool | None = None


@router.get("/users")
def list_users(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(User).order_by(User.name).all()
    return {
        "rows": [{
            "id": u.id, "name": u.name, "email": u.email, "role": u.role,
            "phone": u.phone, "is_active": u.is_active,
            "last_login": u.last_login.isoformat() if u.last_login else None,
            "can_write": u.can_write, "can_approve": u.can_approve,
        } for u in rows],
        "roles": Role.ALL,
        "role_notes": {
            Role.ADMIN: "Everything, including user administration.",
            Role.CFO: "Everything except user administration. Can approve plans.",
            Role.FINANCE: "Can enter and edit data. Cannot approve plans.",
            Role.BOARD: "Read-only. Sees every screen, changes nothing.",
        },
    }


@router.post("/users")
def create_user(payload: UserIn, ctx: Ctx = Depends(get_ctx),
                admin: User = Depends(require_approver)):
    if payload.role not in Role.ALL:
        raise HTTPException(400, f"Role must be one of {Role.ALL}")
    if not payload.password or len(payload.password) < 8:
        raise HTTPException(400, "A password of at least 8 characters is required.")
    if ctx.db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(400, "That email address is already registered.")
    u = User(name=payload.name, email=payload.email.lower(), role=payload.role,
             phone=payload.phone, password_hash=hash_password(payload.password))
    ctx.db.add(u)
    ctx.db.flush()
    log(ctx, admin, "created", "User", f"Added {payload.name} as {payload.role}.", str(u.id))
    ctx.db.commit()
    return {"id": u.id}


@router.patch("/users/{user_id}")
def update_user(user_id: int, payload: UserIn, ctx: Ctx = Depends(get_ctx),
                admin: User = Depends(require_approver)):
    u = ctx.db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    changes = []
    data = payload.model_dump(exclude_unset=True)
    if data.get("password"):
        u.password_hash = hash_password(data.pop("password"))
        changes.append("password reset")
    for field, value in data.items():
        if value is None or not hasattr(u, field):
            continue
        if field == "email":
            value = str(value).lower()
        if getattr(u, field) != value:
            changes.append(f"{field}: {getattr(u, field)} → {value}")
            setattr(u, field, value)
    if changes:
        log(ctx, admin, "updated", "User", f"Updated {u.name} — {'; '.join(changes)}.", str(u.id))
    ctx.db.commit()
    return {"ok": True, "changes": changes}


class DefinitionIn(BaseModel):
    term: str
    plain_english: str
    formula: str | None = None
    basis_note: str | None = None
    category: str = "General"


@router.post("/definitions")
def upsert_definition(payload: DefinitionIn, ctx: Ctx = Depends(get_ctx),
                      user: User = Depends(require_write)):
    d = ctx.db.query(Definition).filter(Definition.term == payload.term).first()
    action = "updated" if d else "created"
    if not d:
        d = Definition(term=payload.term)
        ctx.db.add(d)
    d.plain_english = payload.plain_english
    d.formula = payload.formula
    d.basis_note = payload.basis_note
    d.category = payload.category
    d.updated_by = user.name
    ctx.db.flush()
    log(ctx, user, action, "Definition", f"{action.title()} the definition of '{payload.term}'.",
        str(d.id))
    ctx.db.commit()
    return {"id": d.id}


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
@router.get("/settings")
def get_settings(ctx: Ctx = Depends(get_ctx), user: User = Depends(get_current_user)):
    rows = (ctx.db.query(Setting)
            .filter(Setting.entity_id.in_(ctx.entity_ids + [None]))
            .order_by(Setting.key).all())
    return {
        "rows": [{
            "id": s.id, "key": s.key, "value": s.value, "value_type": s.value_type,
            "label": s.label, "updated_by": s.updated_by,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        } for s in rows if s.value_type != "json"],
        "entity": {
            "min_cash_floor": ctx.entity.min_cash_floor,
            "books_closed_upto": (ctx.entity.books_closed_upto.isoformat()
                                  if ctx.entity.books_closed_upto else None),
            "tally_company": ctx.entity.tally_company,
        },
    }


@router.patch("/settings/{key}")
def update_setting(key: str, value: str = Body(..., embed=True),
                   ctx: Ctx = Depends(get_ctx), user: User = Depends(require_write)):
    s = (ctx.db.query(Setting)
         .filter(Setting.entity_id == ctx.entity.id, Setting.key == key).first())
    before = s.value if s else None
    if not s:
        s = Setting(entity_id=ctx.entity.id, key=key, value=value, value_type="string")
        ctx.db.add(s)
    else:
        s.value = value
    s.updated_by = user.name

    if key == "min_cash_floor":
        try:
            ctx.entity.min_cash_floor = float(value)
        except ValueError:
            raise HTTPException(400, "The cash floor must be a number.")

    log(ctx, user, "updated", "Setting",
        f"Changed '{s.label or key}' from {before} to {value}.", key, before, value)
    ctx.db.commit()
    return {"ok": True}
