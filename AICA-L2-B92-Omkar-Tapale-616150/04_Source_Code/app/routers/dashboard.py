import datetime as dt
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, permissions
from ..auth import get_current_user
from ..main import templates

router = APIRouter()


@router.get("/")
def root(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/dashboard")
    return RedirectResponse("/login")


@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    today = dt.date.today()

    my_tasks_open = db.query(models.CalendarEvent).filter(
        models.CalendarEvent.owner_id == user.id,
        models.CalendarEvent.event_type.in_(["TASK", "PENDING_ACTION"]),
        models.CalendarEvent.status == "OPEN",
    ).count()

    upcoming_meetings = db.query(models.CalendarEvent).filter(
        models.CalendarEvent.owner_id == user.id,
        models.CalendarEvent.event_type == "MEETING",
        models.CalendarEvent.start_date >= today,
    ).order_by(models.CalendarEvent.start_date).limit(5).all()

    today_attendance = db.query(models.Attendance).filter(
        models.Attendance.user_id == user.id, models.Attendance.date == today
    ).first()

    kpis = None
    if permissions.is_ceo(user) or permissions.is_dept_admin(user):
        scope_users = permissions.visible_users_scope(db, user).all()
        scope_ids = [u.id for u in scope_users]
        headcount = len(scope_ids)
        on_notice = sum(1 for u in scope_users if u.employment_status == "ON_NOTICE")
        marked_today = db.query(models.Attendance).filter(
            models.Attendance.user_id.in_(scope_ids), models.Attendance.date == today
        ).count()
        pending_leaves = db.query(models.LeaveRequest).filter(
            models.LeaveRequest.user_id.in_(scope_ids), models.LeaveRequest.status == "PENDING"
        ).count()
        kpis = {
            "headcount": headcount,
            "on_notice": on_notice,
            "attendance_marked_pct": round(100 * marked_today / headcount, 1) if headcount else 0,
            "pending_leaves": pending_leaves,
        }

    team_status = []
    if permissions.is_ceo(user) or permissions.is_dept_admin(user) or permissions.is_manager(user):
        scope_users = permissions.visible_users_scope(db, user).filter(models.User.id != user.id).all()
        for u in scope_users:
            att = db.query(models.Attendance).filter(models.Attendance.user_id == u.id, models.Attendance.date == today).first()
            team_status.append({"user": u, "status": att.status if att else "Not marked"})

    return templates.TemplateResponse(request, "dashboard.html", {
        "request": request, "user": user, "today": today,
        "my_tasks_open": my_tasks_open, "upcoming_meetings": upcoming_meetings,
        "today_attendance": today_attendance, "kpis": kpis, "team_status": team_status,
    })
