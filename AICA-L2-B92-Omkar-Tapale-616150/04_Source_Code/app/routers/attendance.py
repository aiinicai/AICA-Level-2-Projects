import datetime as dt
import calendar as pycal
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, permissions
from ..auth import get_current_user
from ..main import templates

router = APIRouter()


def _month_bounds(year: int, month: int):
    first = dt.date(year, month, 1)
    last_day = pycal.monthrange(year, month)[1]
    return first, dt.date(year, month, last_day)


@router.get("/attendance")
def attendance_page(request: Request, db: Session = Depends(get_db), user: models.User = Depends(get_current_user),
                     year: int = None, month: int = None):
    today = dt.date.today()
    year = year or today.year
    month = month or today.month
    first, last = _month_bounds(year, month)
    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)

    my_records = db.query(models.Attendance).filter(
        models.Attendance.user_id == user.id, models.Attendance.date >= first, models.Attendance.date <= last,
    ).order_by(models.Attendance.date.desc()).all()

    today_status = next((r.status for r in my_records if r.date == today), None)

    # --- Team matrix: everyone in scope x every day of the selected month, for CEO/Dept Admin/Manager ---
    matrix_days = []
    team_matrix = []
    if permissions.is_ceo(user) or permissions.is_dept_admin(user) or permissions.is_manager(user):
        matrix_days = [first + dt.timedelta(days=i) for i in range((last - first).days + 1)]
        scope_users = permissions.visible_users_scope(db, user).order_by(models.User.employee_code).all()
        scope_ids = [u.id for u in scope_users]
        recs = db.query(models.Attendance).filter(
            models.Attendance.user_id.in_(scope_ids), models.Attendance.date >= first, models.Attendance.date <= last,
        ).all()
        by_user_date = {}
        for r in recs:
            by_user_date[(r.user_id, r.date)] = r.status
        for u in scope_users:
            row = {"user": u, "days": [by_user_date.get((u.id, d)) for d in matrix_days]}
            team_matrix.append(row)

    return templates.TemplateResponse(request, "attendance.html", {
        "request": request, "user": user, "today": today, "today_status": today_status,
        "my_records": my_records, "matrix_days": matrix_days, "team_matrix": team_matrix,
        "year": year, "month": month, "month_name": pycal.month_name[month],
        "prev_year": prev_year, "prev_month": prev_month, "next_year": next_year, "next_month": next_month,
    })


@router.post("/attendance/mark")
def mark_attendance(status: str = Form(...), db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    today = dt.date.today()
    rec = db.query(models.Attendance).filter(models.Attendance.user_id == user.id, models.Attendance.date == today).first()
    if rec:
        rec.status = status
    else:
        db.add(models.Attendance(user_id=user.id, date=today, status=status, raw_prompt_text="[one-click button]"))
    db.commit()
    return RedirectResponse("/attendance", status_code=303)
