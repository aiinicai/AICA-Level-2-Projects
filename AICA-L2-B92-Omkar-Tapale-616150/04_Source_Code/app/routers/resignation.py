import datetime as dt
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, permissions
from ..auth import get_current_user, log_audit
from ..main import templates

router = APIRouter()

DEFAULT_NOTICE_DAYS = 30


@router.get("/resignation")
def resignation_page(request: Request, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    team_on_notice = []
    if permissions.is_ceo(user) or permissions.is_dept_admin(user) or permissions.is_manager(user):
        scope_users = permissions.visible_users_scope(db, user).filter(models.User.id != user.id).all()
        team_on_notice = [u for u in scope_users if u.employment_status in ("ON_NOTICE", "EXITED")]

    return templates.TemplateResponse(request, "resignation.html", {
        "request": request, "user": user, "team_on_notice": team_on_notice,
    })


@router.post("/resignation/submit")
def submit_resignation(last_working_day: str = Form(...), reason: str = Form(""),
                        db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    if permissions.is_ceo(user):
        # The CEO is the top of the hierarchy - there's no one to submit a
        # resignation to, so this action is disabled for that account.
        return RedirectResponse("/resignation", status_code=303)
    lwd = dt.date.fromisoformat(last_working_day)
    user.employment_status = "ON_NOTICE"
    user.resignation_date = dt.date.today()
    user.notice_period_days = (lwd - dt.date.today()).days
    user.last_working_day = lwd
    user.resignation_reason = reason
    db.commit()
    log_audit(db, user, "RESIGNATION_SUBMITTED", f"{user.employee_code} resigned, last working day {lwd}")
    return RedirectResponse("/resignation", status_code=303)


@router.post("/resignation/{user_id}/exit-notes")
def add_exit_notes(user_id: int, exit_notes: str = Form(...), db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    target = db.query(models.User).get(user_id)
    if target and permissions.can_view_confidential(db, user, target):
        target.exit_notes = exit_notes
        db.commit()
        log_audit(db, user, "EXIT_NOTES_UPDATED", f"Exit notes updated for {target.employee_code}")
    return RedirectResponse("/resignation", status_code=303)


@router.post("/resignation/{user_id}/finalize-exit")
def finalize_exit(user_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    target = db.query(models.User).get(user_id)
    if target and permissions.can_view_confidential(db, user, target):
        target.employment_status = "EXITED"
        target.is_active = False
        db.commit()
        log_audit(db, user, "EMPLOYEE_EXITED", f"{target.employee_code} marked as exited, account deactivated")
    return RedirectResponse("/resignation", status_code=303)
