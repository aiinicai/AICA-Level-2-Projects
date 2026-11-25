"""Approvals (changes waiting for an Approver) and the audit log viewer."""
from __future__ import annotations

import csv
import io
from dataclasses import replace
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import get_db
from app.engine.forecast import compute
from app.engine.loader import load_inputs
from app.models import ApprovalStatus, AuditLog, LineItem, Override, User
from app.services import overrides as OV
from app.services.settings_service import get_business_settings
from app.web.deps import CAN_ADMIN, approver, auditor, viewer
from app.web.items import ACTION_LABELS
from app.web.templating import flash, render
from app.web.view import refresh_daily_snapshot

router = APIRouter()


def _waiting(db: Session) -> list[Override]:
    return list(db.scalars(select(Override).where(Override.approval_status == ApprovalStatus.PENDING,
                                                  Override.is_active.is_(False), Override.revoked_at.is_(None))
                           .order_by(Override.id)))


def pending_count(db: Session) -> int:
    return len(_waiting(db))


def _impact(db: Session, waiting: list[Override]) -> dict[int, dict]:
    """Lowest funding position after holds now, and if each change were approved (default scenario)."""
    inp = load_inputs(db)
    base = compute(inp)
    out = {}
    for o in waiting:
        ovs = [x for x in inp.overrides
               if not ((x.source, x.key, x.action) == (o.source_type.value, o.source_key, o.action.value))]
        mine = next((x for x in inp.overrides if x.id == o.id), None)
        if mine is None:
            continue
        ovs.append(replace(mine, approval="approved"))
        fc = compute(replace(inp, overrides=ovs, warnings=[]))
        now, after = base.kpis["lowest_fp_after"], fc.kpis["lowest_fp_after"]
        out[o.id] = {"now": now["value"], "now_lot": now["lot"], "after": after["value"], "after_lot": after["lot"],
                     "gaps_now": base.kpis["gap_lots_after"], "gaps_after": fc.kpis["gap_lots_after"]}
    return out


# ------------------------------------------------------------------ approvals
@router.get("/approvals/count")
def approvals_count(user: User = Depends(viewer), db: Session = Depends(get_db)):
    from fastapi.responses import HTMLResponse
    n = pending_count(db)
    return HTMLResponse(f'<span class="badge text-bg-warning">{n}</span>' if n else "")


@router.get("/approvals")
def approvals(request: Request, user: User = Depends(viewer), db: Session = Depends(get_db)):
    waiting = _waiting(db)
    keys = {(o.source_type, o.source_key) for o in waiting}
    items = {}
    for li in db.scalars(select(LineItem).where(LineItem.source_key.in_([k for _, k in keys])).order_by(LineItem.id)):
        items[(li.source_type, li.source_key)] = li           # latest upload wins (ordered by id)
    decided = db.scalars(select(Override).where(
        or_(Override.approval_status.in_([ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]),
            (Override.approval_status == ApprovalStatus.PENDING) & Override.revoked_at.isnot(None)))
        .order_by(func.coalesce(Override.approved_at, Override.revoked_at).desc()).limit(50)).all()
    names = {u.id: u.full_name or u.username for u in db.scalars(select(User))}
    return render(request, "approvals.html", {
        "user": user, "waiting": waiting, "items": items, "decided": decided, "names": names,
        "labels": ACTION_LABELS, "impact": _impact(db, waiting) if waiting else {},
        "enabled": get_business_settings(db).approver_enabled})


@router.post("/approvals/{override_id}")
def decide(request: Request, override_id: int, decision: str = Form(""), comment: str = Form(""),
           user: User = Depends(viewer), db: Session = Depends(get_db)):
    o = db.get(Override, override_id)
    try:
        if decision == "withdraw":
            if o is None or (o.created_by_id != user.id and user.role not in CAN_ADMIN):
                raise OV.OverrideError("only the person who asked for it, or an Admin, can withdraw it")
            if not OV.is_open_pending(o):
                raise OV.OverrideError("this change is not waiting for approval")
            OV.revoke(db, override_id, user.id, comment.strip() or "withdrawn")
            msg = "Request withdrawn."
        else:
            approver(user)                                   # role check (raises Forbidden)
            if decision == "approve":
                OV.approve(db, override_id, user.id, comment)
                msg = "Approved: the forecast now uses this change."
            elif decision == "reject":
                OV.reject(db, override_id, user.id, comment)
                msg = "Rejected: the change will not be applied."
            else:
                raise OV.OverrideError("unknown decision")
        refresh_daily_snapshot(db, user.id)
        db.commit()
        flash(request, msg)
    except OV.OverrideError as exc:
        db.rollback()
        flash(request, f"Not saved: {exc}.", "danger")
    return RedirectResponse("/approvals", status_code=303)


# ------------------------------------------------------------------ audit log
PAGE = 100


def _audit_query(q: dict):
    stmt = select(AuditLog)
    if q.get("user"):
        stmt = stmt.where(func.lower(AuditLog.username) == q["user"].strip().lower())
    if q.get("action"):
        stmt = stmt.where(AuditLog.action.startswith(q["action"].strip()))
    if q.get("text"):
        like = f"%{q['text'].strip()}%"
        stmt = stmt.where(or_(AuditLog.entity_key.ilike(like), AuditLog.entity.ilike(like)))
    off = timedelta(hours=get_settings().utc_offset_hours)       # filter dates are local dates
    if q.get("date_from"):
        stmt = stmt.where(AuditLog.ts >= datetime.combine(date.fromisoformat(q["date_from"]), datetime.min.time()) - off)
    if q.get("date_to"):
        stmt = stmt.where(AuditLog.ts < datetime.combine(date.fromisoformat(q["date_to"]) + timedelta(days=1),
                                                         datetime.min.time()) - off)
    return stmt


ACTION_GROUPS = ["login", "user", "override", "upload", "exception", "balance", "facility", "category", "settings",
                 "scenario", "snapshot", "export"]


@router.get("/audit")
def audit_page(request: Request, user: User = Depends(auditor), db: Session = Depends(get_db)):
    q = {k: request.query_params.get(k, "") for k in ("user", "action", "text", "date_from", "date_to")}
    p = request.query_params.get("page", "1")
    page = max(1, int(p)) if p.isdigit() else 1
    try:
        stmt = _audit_query(q)
    except ValueError:
        stmt, q["date_from"], q["date_to"] = _audit_query({**q, "date_from": "", "date_to": ""}), "", ""
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(AuditLog.id.desc()).offset((page - 1) * PAGE).limit(PAGE)).all()
    users = sorted({u for u in db.scalars(select(AuditLog.username).distinct()) if u})
    return render(request, "audit.html", {"user": user, "rows": rows, "q": q, "page": page, "total": total,
                                          "pages": max(1, -(-total // PAGE)), "users": users,
                                          "groups": ACTION_GROUPS})


@router.get("/audit.csv")
def audit_csv(request: Request, user: User = Depends(auditor), db: Session = Depends(get_db)):
    from app.services.audit import audit
    from app.web.templating import dmy
    q = {k: request.query_params.get(k, "") for k in ("user", "action", "text", "date_from", "date_to")}
    try:
        stmt = _audit_query(q)
    except ValueError:
        stmt = _audit_query({**q, "date_from": "", "date_to": ""})
    rows = db.scalars(stmt.order_by(AuditLog.id)).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "time (local)", "time (UTC)", "user", "action", "entity", "key", "before", "after", "ip"])
    for r in rows:
        w.writerow([r.id, dmy(r.ts), f"{r.ts:%Y-%m-%d %H:%M:%S}", r.username, r.action, r.entity,
                    _safe(r.entity_key), _safe(r.before), _safe(r.after), r.ip])
    audit(db, "audit.download", "audit_log", f"{len(rows)} rows", after={k: v for k, v in q.items() if v},
          user_id=user.id)
    db.commit()
    name = f"audit_log_{date.today():%Y%m%d}.csv"
    return StreamingResponse(iter(["﻿" + buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})


def _safe(v) -> str:
    """CSV cell that a spreadsheet will not run as a formula."""
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s
