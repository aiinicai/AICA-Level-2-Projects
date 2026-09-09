import datetime as dt
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, permissions
from ..auth import get_current_user, log_audit
from ..main import templates

router = APIRouter()


def _leave_balances(db: Session, user: models.User, year: int):
    """Dynamic balance = leave type's annual allocation minus days already
    approved this year - always in sync with actual requests, nothing to migrate."""
    leave_types = db.query(models.LeaveType).all()
    approved = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.user_id == user.id, models.LeaveRequest.status == "APPROVED",
    ).all()
    used_by_type = {}
    for lr in approved:
        if lr.start_date.year != year and lr.end_date.year != year:
            continue
        days = (lr.end_date - lr.start_date).days + 1
        used_by_type[lr.leave_type_id] = used_by_type.get(lr.leave_type_id, 0) + days

    balances = []
    for lt in leave_types:
        used = used_by_type.get(lt.id, 0)
        balances.append({
            "leave_type": lt, "allocated": lt.default_annual_days,
            "used": used, "balance": max(lt.default_annual_days - used, 0),
        })
    return balances


@router.get("/leave")
def leave_page(request: Request, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    leave_types = db.query(models.LeaveType).all()
    my_requests = db.query(models.LeaveRequest).filter(models.LeaveRequest.user_id == user.id).order_by(models.LeaveRequest.created_at.desc()).all()
    balances = _leave_balances(db, user, dt.date.today().year)

    approvals = []
    # CEO has no one above them, so their own leave auto-approves (see apply_leave) -
    # there is never a self-approval step to show here.
    if permissions.is_ceo(user) or permissions.is_dept_admin(user) or permissions.is_manager(user):
        scope_ids = [u.id for u in permissions.visible_users_scope(db, user).all() if u.id != user.id]
        approvals = db.query(models.LeaveRequest).filter(
            models.LeaveRequest.user_id.in_(scope_ids), models.LeaveRequest.status == "PENDING"
        ).order_by(models.LeaveRequest.created_at).all()

    return templates.TemplateResponse(request, "leave.html", {
        "request": request, "user": user, "leave_types": leave_types,
        "my_requests": my_requests, "approvals": approvals, "balances": balances,
    })


@router.post("/leave/apply")
def apply_leave(leave_type_id: int = Form(...), start_date: str = Form(...), end_date: str = Form(...),
                 reason: str = Form(""), db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    # The CEO has no manager to approve their leave, so it auto-approves rather
    # than sitting PENDING forever with nobody able to act on it.
    is_ceo = permissions.is_ceo(user)
    lr = models.LeaveRequest(
        user_id=user.id, leave_type_id=leave_type_id,
        start_date=dt.date.fromisoformat(start_date), end_date=dt.date.fromisoformat(end_date),
        reason=reason, status="APPROVED" if is_ceo else "PENDING",
        approver_id=user.id if is_ceo else None,
        raw_prompt_text="[manual form]",
    )
    db.add(lr)
    db.commit()
    return RedirectResponse("/leave", status_code=303)


@router.post("/leave/{request_id}/decision")
def decide_leave(request_id: int, decision: str = Form(...), db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    lr = db.query(models.LeaveRequest).get(request_id)
    if not lr:
        return RedirectResponse("/leave", status_code=303)
    if lr.user_id == user.id:
        return RedirectResponse("/leave", status_code=303)  # no self-approval, for anyone
    target = db.query(models.User).get(lr.user_id)
    if not permissions.can_view_confidential(db, user, target):
        return RedirectResponse("/leave", status_code=303)
    lr.status = "APPROVED" if decision == "approve" else "REJECTED"
    lr.approver_id = user.id
    db.commit()
    log_audit(db, user, "LEAVE_DECISION", f"{lr.status} leave #{lr.id} for user #{lr.user_id}")
    return RedirectResponse("/leave", status_code=303)
