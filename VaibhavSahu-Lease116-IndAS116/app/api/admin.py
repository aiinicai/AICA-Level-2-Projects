"""Authentication, settings, master data, controls, imports and system APIs."""
from __future__ import annotations

import shutil
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import config
from ..db.base import get_db
from ..db.models import (AssetClass, AuditLog, CalcRun, Company, Counterparty, DiscountRate, Entity, FxRate, GLMapping, ImportBatch,
                         Lease, ReportingPeriod, Role, User, UserEntityAccess)
from ..engine.calendar_utils import add_months, fy_of, month_end, parse_date
from ..engine.decimal_utils import D, to_jsonable
from ..engine.journals import ROLE_CATALOG
from ..services import audit
from ..services.import_service import TEMPLATES, approve_and_import, error_report_csv, template_xlsx, upload
from ..services.lease_service import ServiceError, company_of, current_run
from ..services.security import COOKIE_NAME, ROLES, hash_password, has_perm, make_token, permissions_for, verify_password
from ..services.settings_service import capabilities, deep_merge, get_settings, public_settings
from ..services.workflow_service import lock_period, reopen_period
from .deps import current_user, require

router = APIRouter(prefix="/api", tags=["admin"])


def _u(u: User) -> dict:
    return {"id": u.id, "username": u.username, "full_name": u.full_name, "email": u.email, "role": u.role.code,
            "role_name": u.role.name, "active": u.active, "all_entities": u.all_entities, "permissions": permissions_for(u.role.code),
            "must_change_password": u.must_change_password, "last_login": u.last_login}


# ---------------------------------------------------------------- auth
@router.post("/auth/login")
def login(payload: dict = Body(...), response: Response = None, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.username == (payload.get("username") or "").strip().lower()))
    if u is None or not u.active or not verify_password(payload.get("password") or "", u.password_hash):
        audit.log(db, None, "LOGIN_FAILED", "User", None, payload.get("username"), None, None, None)
        db.commit()
        raise HTTPException(401, "Invalid username or password")
    u.last_login = datetime.now()
    token = make_token(u.id)
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", max_age=12 * 3600)
    audit.log(db, u, "LOGIN", "User", u.id, u.username)
    db.commit()
    return {"token": token, "user": to_jsonable(_u(u))}


@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.get("/auth/me")
def me(db: Session = Depends(get_db), user: User = Depends(current_user)):
    comp = company_of(db)
    return to_jsonable({"user": _u(user), "company": {"id": comp.id, "name": comp.name, "framework": comp.framework,
                                                       "functional_currency": comp.functional_currency, "fy_start_month": comp.fy_start_month},
                        "entities": [{"id": e.id, "code": e.code, "name": e.name} for e in db.scalars(select(Entity).order_by(Entity.code))],
                        "asset_classes": [{"id": a.id, "code": a.code, "name": a.name, "short_term_election": a.short_term_election,
                                           "non_lease_expedient": a.non_lease_expedient}
                                          for a in db.scalars(select(AssetClass).order_by(AssetClass.name))],
                        "display": get_settings(comp)["display"], "version": config.APP_VERSION})


@router.post("/auth/change-password")
def change_password(payload: dict = Body(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not verify_password(payload.get("current") or "", user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    new = payload.get("new") or ""
    if len(new) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    user.password_hash = hash_password(new)
    user.must_change_password = False
    audit.log(db, user, "CHANGE_PASSWORD", "User", user.id, user.username)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- settings
@router.get("/settings")
def get_s(db: Session = Depends(get_db), user: User = Depends(current_user)):
    comp = company_of(db)
    return {"company": {"name": comp.name, "framework": comp.framework, "functional_currency": comp.functional_currency,
                        "fy_start_month": comp.fy_start_month}, "settings": public_settings(comp)}


@router.put("/settings")
def put_s(payload: dict = Body(...), db: Session = Depends(get_db), user: User = Depends(require("settings.write"))):
    comp = company_of(db)
    c = payload.get("company") or {}
    for k in ("name", "framework", "functional_currency", "fy_start_month"):
        if k in c and c[k] not in (None, ""):
            old = getattr(comp, k)
            if str(old) != str(c[k]):
                setattr(comp, k, c[k] if k != "fy_start_month" else int(c[k]))
                audit.log(db, user, "UPDATE", "Company", comp.id, comp.name, k, old, c[k], payload.get("_reason"))
    s = payload.get("settings") or {}
    cur = get_settings(comp)
    if "ai" in s and "claude" in s["ai"]:
        key = s["ai"]["claude"].get("api_key")
        if key is None or key.startswith("••"):
            s["ai"]["claude"]["api_key"] = cur["ai"]["claude"].get("api_key", "")
        s["ai"]["claude"].pop("has_key", None)
    new = deep_merge(cur, s)
    for section in ("policies", "controls", "ai", "display", "journal", "tax"):
        if section in s:
            old_sec = dict(cur.get(section) or {})
            new_sec = dict(new.get(section) or {})
            if section == "ai":
                old_sec = {**old_sec, "claude": {**old_sec.get("claude", {}), "api_key": "***"}}
                new_sec = {**new_sec, "claude": {**new_sec.get("claude", {}), "api_key": "***"}}
            if old_sec != new_sec:
                audit.log(db, user, "UPDATE", "Settings", comp.id, section, section, old_sec, new_sec, payload.get("_reason"))
    comp.settings = new
    db.commit()
    return {"settings": public_settings(comp)}


@router.post("/settings/ai/test")
def ai_test(payload: dict = Body(default={}), db: Session = Depends(get_db), user: User = Depends(require("settings.write"))):
    from ..docintel.llm import LocalLLM
    found = LocalLLM.detect()
    comp = company_of(db)
    ai = get_settings(comp)["ai"]
    out = {"local_servers": found, "configured_local_model": ai["local"].get("model")}
    if payload.get("probe") and ai["local"].get("model"):
        try:
            llm = LocalLLM(base_url=ai["local"]["base_url"], kind=ai["local"]["kind"], model=ai["local"]["model"], timeout=120)
            res = llm.chat_json("Reply with JSON only.", 'Return {"ok": true}', {"type": "object", "properties": {"ok": {"type": "boolean"}}})
            out["probe"] = res
        except Exception as exc:
            out["probe_error"] = str(exc)
    return out


# ---------------------------------------------------------------- users
@router.get("/users")
def users(db: Session = Depends(get_db), user: User = Depends(require("users.manage"))):
    out = []
    for u in db.scalars(select(User).order_by(User.username)).all():
        d = _u(u)
        d["entity_ids"] = list(db.scalars(select(UserEntityAccess.entity_id).where(UserEntityAccess.user_id == u.id)).all())
        out.append(d)
    return to_jsonable({"users": out, "roles": [{"code": k, "name": v[0], "permissions": v[1]} for k, v in ROLES.items()]})


@router.post("/users")
def user_save(payload: dict = Body(...), db: Session = Depends(get_db), user: User = Depends(require("users.manage"))):
    role = db.scalar(select(Role).where(Role.code == payload.get("role")))
    if role is None:
        raise HTTPException(400, "Unknown role")
    if payload.get("id"):
        u = db.get(User, int(payload["id"]))
        changes = {"full_name": payload.get("full_name"), "email": payload.get("email"), "role_id": role.id,
                   "active": bool(payload.get("active", True)), "all_entities": bool(payload.get("all_entities", True))}
        audit.log_changes(db, user, u, changes, "User", u.username)
    else:
        uname = (payload.get("username") or "").strip().lower()
        if not uname or db.scalar(select(User.id).where(User.username == uname)):
            raise HTTPException(400, "Username missing or already exists")
        if len(payload.get("password") or "") < 8:
            raise HTTPException(400, "Initial password must be at least 8 characters")
        u = User(username=uname, full_name=payload.get("full_name") or uname, email=payload.get("email"), role_id=role.id,
                 password_hash=hash_password(payload["password"]), all_entities=bool(payload.get("all_entities", True)),
                 must_change_password=True)
        db.add(u)
        db.flush()
        audit.log(db, user, "CREATE", "User", u.id, u.username, "role", None, role.code)
    if payload.get("password") and payload.get("id"):
        u.password_hash = hash_password(payload["password"])
        u.must_change_password = True
        audit.log(db, user, "RESET_PASSWORD", "User", u.id, u.username)
    if "entity_ids" in payload:
        for x in db.scalars(select(UserEntityAccess).where(UserEntityAccess.user_id == u.id)).all():
            db.delete(x)
        for eid in payload["entity_ids"] or []:
            db.add(UserEntityAccess(user_id=u.id, entity_id=int(eid)))
    db.commit()
    return {"ok": True, "id": u.id}


# ---------------------------------------------------------------- master data
@router.get("/master")
def master(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return to_jsonable({
        "entities": [{"id": e.id, "code": e.code, "name": e.name, "functional_currency": e.functional_currency, "cin": e.cin, "pan": e.pan}
                     for e in db.scalars(select(Entity).order_by(Entity.code))],
        "asset_classes": [{"id": a.id, "code": a.code, "name": a.name, "short_term_election": a.short_term_election,
                           "non_lease_expedient": a.non_lease_expedient, "default_useful_life_months": a.default_useful_life_months}
                          for a in db.scalars(select(AssetClass).order_by(AssetClass.name))],
        "counterparties": [{"id": c.id, "name": c.name, "vendor_id": c.vendor_id, "related_party": c.related_party,
                            "contact_person": c.contact_person, "email": c.email, "phone": c.phone, "address": c.address,
                            "pan": c.pan, "gstin": c.gstin} for c in db.scalars(select(Counterparty).order_by(Counterparty.name))],
        "gl_roles": [{"role": r, "default_code": v[0], "default_name": v[1], "nature": v[2]} for r, v in ROLE_CATALOG.items()],
    })


MASTER_MODELS = {"entities": (Entity, ("code", "name", "functional_currency", "cin", "pan")),
                 "asset_classes": (AssetClass, ("code", "name", "short_term_election", "non_lease_expedient", "default_useful_life_months")),
                 "counterparties": (Counterparty, ("name", "vendor_id", "related_party", "contact_person", "email", "phone", "address",
                                                   "pan", "gstin"))}


@router.post("/master/{kind}")
def master_save(kind: str, payload: dict = Body(...), db: Session = Depends(get_db), user: User = Depends(require("lease.write"))):
    if kind not in MASTER_MODELS:
        raise HTTPException(404)
    if kind in ("entities", "asset_classes") and not has_perm(user.role.code, "settings.write"):
        raise HTTPException(403, "Administrator permission required")
    Model, fields = MASTER_MODELS[kind]
    comp = company_of(db)
    if payload.get("id"):
        obj = db.get(Model, int(payload["id"]))
        audit.log_changes(db, user, obj, {f: payload.get(f) for f in fields if f in payload}, Model.__name__,
                          getattr(obj, "name", "") or getattr(obj, "code", ""), payload.get("_reason"))
    else:
        obj = Model(company_id=comp.id, **{f: payload.get(f) for f in fields if f in payload})
        db.add(obj)
        db.flush()
        audit.log(db, user, "CREATE", Model.__name__, obj.id, getattr(obj, "name", ""))
    db.commit()
    return {"id": obj.id}


@router.get("/gl-mappings")
def gl_maps(db: Session = Depends(get_db), user: User = Depends(require("journal.read"))):
    return to_jsonable([{"id": m.id, "role": m.role, "account_code": m.account_code, "account_name": m.account_name,
                         "entity_id": m.entity_id, "asset_class_id": m.asset_class_id, "cost_centre": m.cost_centre, "lease_type": m.lease_type}
                        for m in db.scalars(select(GLMapping).order_by(GLMapping.role, GLMapping.id))])


@router.put("/gl-mappings")
def gl_maps_put(payload: list = Body(...), db: Session = Depends(get_db), user: User = Depends(require("settings.write"))):
    comp = company_of(db)
    old = len(db.scalars(select(GLMapping)).all())
    for m in db.scalars(select(GLMapping)).all():
        db.delete(m)
    for m in payload:
        if not m.get("role") or not m.get("account_code"):
            continue
        db.add(GLMapping(company_id=comp.id, role=m["role"], account_code=str(m["account_code"]), account_name=m.get("account_name"),
                         entity_id=m.get("entity_id") or None, asset_class_id=m.get("asset_class_id") or None,
                         cost_centre=m.get("cost_centre") or None, lease_type=m.get("lease_type") or None))
    audit.log(db, user, "UPDATE", "GLMapping", None, "GL mapping", "rows", old, len(payload))
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- discount rates & FX
@router.get("/discount-rates")
def rates(db: Session = Depends(get_db), user: User = Depends(require("lease.read"))):
    return to_jsonable([{k: getattr(r, k) for k in ("id", "entity_id", "scope", "currency", "tenor_from_months", "tenor_to_months",
                                                     "rate_pct", "rate_type", "security", "source", "methodology", "effective_date",
                                                     "documentation", "status", "approved_by", "approved_at")}
                        for r in db.scalars(select(DiscountRate).order_by(DiscountRate.currency, DiscountRate.effective_date.desc(),
                                                                         DiscountRate.tenor_from_months))])


@router.post("/discount-rates")
def rate_save(payload: dict = Body(...), db: Session = Depends(get_db), user: User = Depends(require("rate.write"))):
    comp = company_of(db)
    r = db.get(DiscountRate, int(payload["id"])) if payload.get("id") else DiscountRate(company_id=comp.id)
    if r.id and r.status == "Approved":
        raise HTTPException(409, "Approved rates are locked — add a new rate with a later effective date.")
    for k in ("scope", "currency", "rate_type", "security", "source", "methodology", "documentation"):
        if k in payload:
            setattr(r, k, payload[k])
    r.entity_id = payload.get("entity_id") or None
    r.tenor_from_months = int(payload.get("tenor_from_months") or 0)
    r.tenor_to_months = int(payload.get("tenor_to_months") or 600)
    r.rate_pct = D(payload["rate_pct"])
    r.effective_date = parse_date(payload["effective_date"])
    r.status = "Draft"
    if not r.id:
        db.add(r)
    db.flush()
    audit.log(db, user, "SAVE", "DiscountRate", r.id, f"{r.currency} {r.tenor_from_months}-{r.tenor_to_months}m", "rate_pct", None, str(r.rate_pct))
    db.commit()
    return {"id": r.id}


@router.post("/discount-rates/{rid}/approve")
def rate_approve(rid: int, db: Session = Depends(get_db), user: User = Depends(require("rate.approve"))):
    r = db.get(DiscountRate, rid)
    r.status = "Approved"
    r.approved_by = user.id
    r.approved_at = datetime.now()
    audit.log(db, user, "APPROVE", "DiscountRate", r.id, f"{r.currency} {r.rate_pct}%", "status", "Draft", "Approved",
              approval_status="Approved")
    db.commit()
    return {"ok": True}


@router.post("/discount-rates/lookup")
def rate_lookup(payload: dict = Body(...), db: Session = Depends(get_db), user: User = Depends(require("lease.read"))):
    """Suggest an approved IBR for a lease (currency, tenor in months, entity, commencement date)."""
    months = int(payload.get("tenor_months") or 0)
    ccy = payload.get("currency") or "INR"
    when = parse_date(payload.get("date")) or date.today()
    ent = payload.get("entity_id")
    cands = [r for r in db.scalars(select(DiscountRate).where(DiscountRate.currency == ccy, DiscountRate.status == "Approved")).all()
             if r.tenor_from_months <= months <= r.tenor_to_months and r.effective_date <= when and (r.entity_id in (None, ent))]
    cands.sort(key=lambda r: (r.entity_id is None, -r.effective_date.toordinal()))
    if not cands:
        return {"rate": None, "message": "No approved IBR matches this currency/tenor/date — enter a lease-specific rate with support."}
    r = cands[0]
    return to_jsonable({"rate": r.rate_pct, "id": r.id, "source": r.source, "methodology": r.methodology,
                        "effective_date": r.effective_date, "message": f"Approved portfolio IBR {r.rate_pct}% "
                                                                      f"({r.tenor_from_months}–{r.tenor_to_months} months, {r.currency})"})


@router.get("/fx-rates")
def fx(db: Session = Depends(get_db), user: User = Depends(require("lease.read"))):
    return to_jsonable([{"id": r.id, "from_ccy": r.from_ccy, "to_ccy": r.to_ccy, "rate_date": r.rate_date, "rate": r.rate,
                         "rate_type": r.rate_type, "source": r.source}
                        for r in db.scalars(select(FxRate).order_by(FxRate.from_ccy, FxRate.rate_date.desc())).all()])


@router.post("/fx-rates")
def fx_save(payload: dict = Body(...), db: Session = Depends(get_db), user: User = Depends(require("rate.write"))):
    items = payload.get("rates") or [payload]
    for it in items:
        db.add(FxRate(from_ccy=it["from_ccy"].upper(), to_ccy=(it.get("to_ccy") or "INR").upper(), rate_date=parse_date(it["rate_date"]),
                      rate=D(it["rate"]), rate_type=it.get("rate_type") or "CLOSING", source=it.get("source")))
    audit.log(db, user, "CREATE", "FxRate", None, "FX rates", "rows", None, len(items))
    db.commit()
    return {"ok": True, "count": len(items)}


# ---------------------------------------------------------------- periods, approvals, audit
@router.get("/periods")
def periods(fy: Optional[str] = None, db: Session = Depends(get_db), user: User = Depends(require("lease.read"))):
    comp = company_of(db)
    ref = parse_date(fy) or date.today()
    s, e = fy_of(ref, comp.fy_start_month or 4)
    rows = {p.period_end: p for p in db.scalars(select(ReportingPeriod)).all()}
    out = []
    for i in range(12):
        pe = month_end(add_months(s, i))
        p = rows.get(pe)
        out.append({"period_end": pe, "status": p.status if p else "Open", "locked_at": p.locked_at if p else None,
                    "reopened_at": p.reopened_at if p else None, "reason": p.reason if p else None})
    return to_jsonable({"fy_start": s, "fy_end": e, "periods": out})


@router.post("/periods/{period_end}/{action}")
def period_action(period_end: str, action: str, payload: dict = Body(default={}), db: Session = Depends(get_db),
                  user: User = Depends(current_user)):
    comp = company_of(db)
    pe = parse_date(period_end)
    try:
        if action == "lock":
            lock_period(db, comp.id, pe, user, (payload or {}).get("reason"))
        elif action == "reopen":
            reopen_period(db, comp.id, pe, user, (payload or {}).get("reason"))
        else:
            raise HTTPException(404)
    except ServiceError as exc:
        db.rollback()
        raise HTTPException(exc.status, exc.message)
    db.commit()
    return {"ok": True}


@router.get("/approvals")
def approvals(db: Session = Depends(get_db), user: User = Depends(require("lease.read"))):
    out = []
    for l in db.scalars(select(Lease).where(Lease.status.in_(["Prepared", "Under Review", "Draft"]))).all():
        run = current_run(db, l)
        if l.status == "Draft" and not run:
            continue
        out.append({"lease_id": l.id, "lease_code": l.lease_code, "description": l.description, "status": l.status,
                    "run_no": run.run_no if run else None, "run_status": run.status if run else None,
                    "prepared_by": l.prepared_by, "updated_at": l.updated_at,
                    "pending_events": [e.event_type for e in l.events if e.status in ("Draft", "Submitted")],
                    "initial_liability": (run.summary.get("initial") or {}).get("liability") if run else None})
    rates_pending = [{"id": r.id, "currency": r.currency, "rate_pct": r.rate_pct, "tenor": f"{r.tenor_from_months}-{r.tenor_to_months}m"}
                     for r in db.scalars(select(DiscountRate).where(DiscountRate.status == "Draft")).all()]
    imports_pending = [{"id": b.id, "template": b.template, "filename": b.filename, "rows": b.rows_total}
                       for b in db.scalars(select(ImportBatch).where(ImportBatch.status == "Validated")).all()]
    return to_jsonable({"leases": out, "rates": rates_pending, "imports": imports_pending})


@router.get("/audit")
def audit_list(object_type: str = "", q: str = "", limit: int = 500, db: Session = Depends(get_db),
               user: User = Depends(require("audit.read"))):
    stmt = select(AuditLog).order_by(AuditLog.at.desc())
    if object_type:
        stmt = stmt.where(AuditLog.object_type == object_type)
    rows = db.scalars(stmt.limit(min(limit, 5000))).all()
    out = [{"id": a.id, "at": a.at, "username": a.username, "action": a.action, "object_type": a.object_type, "object_id": a.object_id,
            "object_label": a.object_label, "field": a.field, "old_value": a.old_value, "new_value": a.new_value, "reason": a.reason,
            "document_id": a.document_id, "approval_status": a.approval_status} for a in rows]
    if q:
        ql = q.lower()
        out = [r for r in out if any(ql in str(v or "").lower() for v in r.values())]
    return to_jsonable(out)


# ---------------------------------------------------------------- imports
@router.get("/imports")
def imports_list(db: Session = Depends(get_db), user: User = Depends(require("lease.read"))):
    return to_jsonable({"templates": {k: [c[0] for c in v] for k, v in TEMPLATES.items()},
                        "batches": [{"id": b.id, "template": b.template, "filename": b.filename, "status": b.status,
                                     "uploaded_at": b.uploaded_at, "rows_total": b.rows_total, "rows_valid": b.rows_valid,
                                     "rows_error": b.rows_error} for b in db.scalars(select(ImportBatch).order_by(ImportBatch.id.desc()))]})


@router.get("/imports/templates/{kind}")
def import_template(kind: str, user: User = Depends(require("lease.read"))):
    return Response(template_xlsx(kind), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="Lease116_template_{kind}.xlsx"'})


@router.post("/imports")
async def import_upload(kind: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db),
                        user: User = Depends(require("import.write"))):
    try:
        b = upload(db, company_of(db), kind, await file.read(), file.filename, user)
    except ServiceError as exc:
        raise HTTPException(exc.status, exc.message)
    db.commit()
    return to_jsonable({"id": b.id, "status": b.status, "rows_total": b.rows_total, "rows_valid": b.rows_valid, "rows_error": b.rows_error,
                        "errors": b.errors[:200], "preview": b.preview[:50]})


@router.get("/imports/{bid}")
def import_get(bid: int, db: Session = Depends(get_db), user: User = Depends(require("lease.read"))):
    b = db.get(ImportBatch, bid)
    return to_jsonable({"id": b.id, "template": b.template, "status": b.status, "rows_total": b.rows_total, "rows_valid": b.rows_valid,
                        "rows_error": b.rows_error, "errors": b.errors[:500], "preview": b.preview[:100]})


@router.get("/imports/{bid}/errors.csv")
def import_errors(bid: int, db: Session = Depends(get_db), user: User = Depends(require("lease.read"))):
    b = db.get(ImportBatch, bid)
    return Response(error_report_csv(b), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="import_{bid}_errors.csv"'})


@router.post("/imports/{bid}/approve")
def import_approve(bid: int, db: Session = Depends(get_db), user: User = Depends(require("import.approve"))):
    b = db.get(ImportBatch, bid)
    try:
        res = approve_and_import(db, company_of(db), b, user)
    except ServiceError as exc:
        db.rollback()
        raise HTTPException(exc.status, exc.message)
    db.commit()
    return res


# ---------------------------------------------------------------- system
@router.get("/system/capabilities")
def caps(user: User = Depends(current_user)):
    c = capabilities()
    c["data_dir"] = str(config.DATA_DIR)
    c["version"] = config.APP_VERSION
    return c


@router.post("/system/backup")
def backup(db: Session = Depends(get_db), user: User = Depends(require("settings.write"))):
    config.ensure_dirs()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = config.BACKUP_DIR / f"Lease116_backup_{stamp}.zip"
    dbfile = config.DATA_DIR / "lease116.db"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        if dbfile.exists():
            import sqlite3
            tmp = config.BACKUP_DIR / f"_snap_{stamp}.db"
            src = sqlite3.connect(str(dbfile))
            dst = sqlite3.connect(str(tmp))
            src.backup(dst)
            dst.close()
            src.close()
            z.write(tmp, "lease116.db")
            tmp.unlink()
        for p in config.DOCS_DIR.rglob("*"):
            if p.is_file():
                z.write(p, f"documents/{p.relative_to(config.DOCS_DIR)}")
    audit.log(db, user, "BACKUP", "System", None, target.name)
    db.commit()
    return {"file": str(target)}


@router.post("/system/demo-data")
def demo(db: Session = Depends(get_db), user: User = Depends(require("settings.write"))):
    from ..db.seed import load_demo_data
    n = load_demo_data(db, user)
    db.commit()
    return {"created": n}
