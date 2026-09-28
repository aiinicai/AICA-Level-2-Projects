"""Maker-checker workflow, period locks and approvals (spec section 26)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db.models import Approval, CalcRun, Company, Lease, LeaseEventRow, ReportingPeriod
from ..engine.calendar_utils import parse_date
from ..engine.decimal_utils import D
from . import audit
from .lease_service import ServiceError, current_run
from .security import has_perm
from .settings_service import get_settings

ACTIONS = {
    "submit": ("lease.submit", ["Draft"], "Prepared"),
    "start_review": ("lease.review", ["Prepared"], "Under Review"),
    "return": ("lease.review", ["Prepared", "Under Review"], "Draft"),
    "approve": ("lease.approve", ["Prepared", "Under Review"], "Approved"),
    "reopen": ("lease.approve", ["Approved", "Posted", "Modified"], "Draft"),
    "archive": ("settings.write", ["Draft", "Approved", "Posted", "Terminated", "Modified"], "Archived"),
}


def locked_periods(db: Session, company_id: int) -> list[date]:
    return sorted(db.scalars(select(ReportingPeriod.period_end).where(ReportingPeriod.company_id == company_id,
                                                                      ReportingPeriod.status == "Locked")).all())


def is_locked(db: Session, company_id: int, d: date) -> bool:
    """A date falls in a locked period if its month-end is locked."""
    from ..engine.calendar_utils import month_end
    me = month_end(d)
    return db.scalar(select(ReportingPeriod.id).where(ReportingPeriod.company_id == company_id, ReportingPeriod.period_end == me,
                                                      ReportingPeriod.status == "Locked")) is not None


def _locked_period_changes(db: Session, lease: Lease, run: CalcRun) -> list[str]:
    locked = locked_periods(db, lease.company_id)
    if not locked:
        return []
    last_locked = max(locked)
    new_rows = {r["period_end"]: r for r in run.summary.get("periods", []) if parse_date(r["period_end"]) <= last_locked}
    prev = db.scalar(select(CalcRun).where(CalcRun.lease_id == lease.id, CalcRun.status.in_(["Approved", "Posted"]),
                                           CalcRun.id != run.id).order_by(CalcRun.run_no.desc()))
    prev_rows = {r["period_end"]: r for r in (prev.summary.get("periods", []) if prev else []) if parse_date(r["period_end"]) <= last_locked}
    diffs = []
    keys = ("liab_close", "rou_close", "interest", "depreciation", "payments", "gain_loss")
    for pe in sorted(set(new_rows) | set(prev_rows)):
        if parse_date(pe) not in locked:
            continue
        a, b = new_rows.get(pe, {}), prev_rows.get(pe, {})
        for k in keys:
            if D(a.get(k) or 0) != D(b.get(k) or 0):
                diffs.append(f"{pe}: {k} {b.get(k) or 0} → {a.get(k) or 0}")
                break
    return diffs


def transition(db: Session, lease: Lease, action: str, user, comment: str | None = None) -> dict:
    if action not in ACTIONS:
        raise ServiceError(f"Unknown action {action}")
    perm, allowed_from, to_status = ACTIONS[action]
    role = user.role.code
    if not has_perm(role, perm):
        raise ServiceError(f"Your role ({user.role.name}) cannot perform '{action}'.", status=403)
    comp = db.get(Company, lease.company_id)
    controls = get_settings(comp)["controls"]
    run = current_run(db, lease)
    from_status = lease.status
    if lease.status not in allowed_from:
        raise ServiceError(f"Cannot {action.replace('_', ' ')} a lease in status '{lease.status}'.")
    if action in ("submit", "approve", "start_review") and run is None:
        raise ServiceError("Calculate the lease before submitting it.")
    if action == "submit":
        errors = [i for i in (run.summary.get("issues") or []) if i.get("severity") == "ERROR"]
        if errors:
            raise ServiceError("Resolve calculation errors before submitting.", errors)
        if run.summary.get("kind") == "EXEMPT" and not run.summary.get("valid"):
            raise ServiceError("The exemption did not pass validation — the lease cannot be submitted as exempt.",
                               run.summary.get("issues") or [])
        lease.prepared_by = user.id
        run.status = "Prepared"
    elif action == "start_review":
        if controls.get("segregation_of_duties") and lease.prepared_by == user.id:
            raise ServiceError("Segregation of duties: the preparer cannot review their own work.", status=403)
        lease.reviewed_by = user.id
        run.status = "Under Review"
    elif action == "return":
        if not comment:
            raise ServiceError("A comment is required when returning work to the preparer.")
        if run:
            run.status = "Draft"
    elif action == "approve":
        if controls.get("segregation_of_duties") and lease.prepared_by == user.id:
            raise ServiceError("Segregation of duties: the preparer cannot approve their own calculation.", status=403)
        if controls.get("two_step_review") and lease.status != "Under Review":
            raise ServiceError("Two-step review is enabled — a reviewer must review before approval.")
        diffs = _locked_period_changes(db, lease, run)
        if diffs:
            raise ServiceError("Approval would change results in locked accounting period(s). Reopen the period first "
                               "(authorised procedure).", [{"message": d} for d in diffs[:10]])
        for old in db.scalars(select(CalcRun).where(CalcRun.lease_id == lease.id, CalcRun.status.in_(["Approved", "Posted"]),
                                                    CalcRun.id != run.id)):
            old.status = "Superseded"
        run.status = "Approved"
        run.version_no = (db.scalar(select(func.max(CalcRun.version_no)).where(CalcRun.lease_id == lease.id)) or 0) + 1
        run.approved_by = user.id
        run.approved_at = datetime.now()
        lease.approved_by = user.id
        lease.approved_at = datetime.now()
        included = {e.get("ref") for e in run.summary.get("events", [])}
        for ev in lease.events:
            if ev.status in ("Draft", "Submitted") and f"EV-{ev.id}" in included:
                ev.status = "Approved"
                ev.approved_by = user.id
                ev.approved_at = datetime.now()
                ev.result = next((e for e in run.summary.get("events", []) if e.get("ref") == f"EV-{ev.id}"), None)
                audit.log(db, user, "APPROVE", "LeaseEvent", ev.id, lease.lease_code, "status", "Draft", "Approved",
                          comment, approval_status="Approved")
        types = {e.event_type for e in lease.events if e.status == "Approved"}
        if "TERMINATION" in types:
            to_status = "Terminated"
        elif types & {"MODIFICATION", "REASSESSMENT"}:
            to_status = "Modified"
    elif action == "reopen":
        if not comment:
            raise ServiceError("A reason is required to reopen an approved lease (correction).")
    lease.status = to_status
    db.add(Approval(object_type="Lease", object_id=lease.id, action=action, from_status=from_status, to_status=to_status,
                    user_id=user.id, comment=comment))
    audit.log(db, user, action.upper(), "Lease", lease.id, lease.lease_code, "status", from_status, to_status, comment,
              approval_status=to_status)
    return {"status": lease.status, "calc_status": run.status if run else None}


def lock_period(db: Session, company_id: int, period_end: date, user, reason: str | None = None) -> ReportingPeriod:
    if not has_perm(user.role.code, "period.lock"):
        raise ServiceError("Your role cannot lock periods.", status=403)
    rp = db.scalar(select(ReportingPeriod).where(ReportingPeriod.company_id == company_id, ReportingPeriod.period_end == period_end))
    if rp is None:
        rp = ReportingPeriod(company_id=company_id, period_end=period_end)
        db.add(rp)
    if rp.status == "Locked":
        raise ServiceError("Period is already locked.")
    rp.status = "Locked"
    rp.locked_by = user.id
    rp.locked_at = datetime.now()
    rp.reason = reason
    audit.log(db, user, "LOCK_PERIOD", "ReportingPeriod", period_end, str(period_end), "status", "Open", "Locked", reason,
              approval_status="Locked")
    return rp


def reopen_period(db: Session, company_id: int, period_end: date, user, reason: str) -> ReportingPeriod:
    if user.role.code != "ADMIN":
        raise ServiceError("Only an Administrator can reopen a locked period (authorised reopening procedure).", status=403)
    if not reason:
        raise ServiceError("A reason is required to reopen a period.")
    rp = db.scalar(select(ReportingPeriod).where(ReportingPeriod.company_id == company_id, ReportingPeriod.period_end == period_end))
    if rp is None or rp.status != "Locked":
        raise ServiceError("Period is not locked.")
    rp.status = "Open"
    rp.reopened_by = user.id
    rp.reopened_at = datetime.now()
    rp.reason = reason
    audit.log(db, user, "REOPEN_PERIOD", "ReportingPeriod", period_end, str(period_end), "status", "Locked", "Open", reason,
              approval_status="Reopened")
    return rp
