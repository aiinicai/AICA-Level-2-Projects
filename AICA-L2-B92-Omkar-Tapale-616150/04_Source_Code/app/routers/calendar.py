import datetime as dt
import calendar as pycal
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, permissions
from ..auth import get_current_user, log_audit
from ..prompt_engine import parse_prompt
from ..main import templates

router = APIRouter()


def _month_bounds(year: int, month: int):
    first = dt.date(year, month, 1)
    last_day = pycal.monthrange(year, month)[1]
    last = dt.date(year, month, last_day)
    return first, last


@router.get("/calendar")
def calendar_view(request: Request, db: Session = Depends(get_db), user: models.User = Depends(get_current_user),
                   year: int = None, month: int = None, view_user_id: int = None):
    today = dt.date.today()
    year = year or today.year
    month = month or today.month
    first, last = _month_bounds(year, month)

    target = user
    can_see_target_detail = True
    if view_user_id and view_user_id != user.id:
        target = db.query(models.User).get(view_user_id)
        if not target:
            target = user
        else:
            can_see_target_detail = permissions.can_view_detail(db, user, target)

    events = db.query(models.CalendarEvent).filter(
        models.CalendarEvent.owner_id == target.id,
        models.CalendarEvent.start_date >= first,
        models.CalendarEvent.start_date <= last,
    ).order_by(models.CalendarEvent.start_date).all()

    attendance = db.query(models.Attendance).filter(
        models.Attendance.user_id == target.id,
        models.Attendance.date >= first,
        models.Attendance.date <= last,
    ).all()

    leaves = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.user_id == target.id,
        models.LeaveRequest.status != "REJECTED",
        models.LeaveRequest.start_date <= last,
        models.LeaveRequest.end_date >= first,
    ).all()

    visible_people = permissions.visible_users_scope(db, user).filter(models.User.id != user.id).all()

    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)

    # --- build a full month grid (every day, including days with nothing on them) ---
    day_map = {}
    for e in events:
        day_map.setdefault(e.start_date, {"events": [], "attendance": None, "on_leave": False})["events"].append(e)
    for a in attendance:
        day_map.setdefault(a.date, {"events": [], "attendance": None, "on_leave": False})["attendance"] = a.status
    for lv in leaves:
        d = max(lv.start_date, first)
        end = min(lv.end_date, last)
        while d <= end:
            day_map.setdefault(d, {"events": [], "attendance": None, "on_leave": False})["on_leave"] = True
            d += dt.timedelta(days=1)

    cal = pycal.Calendar(firstweekday=0)  # Monday first
    weeks = []
    for week in cal.monthdatescalendar(year, month):
        week_days = []
        for d in week:
            info = day_map.get(d, {"events": [], "attendance": None, "on_leave": False})
            week_days.append({
                "date": d,
                "in_month": d.month == month,
                "is_today": d == today,
                "is_weekend": d.weekday() >= 5,
                "events": info["events"],
                "attendance": info["attendance"],
                "on_leave": info["on_leave"],
            })
        weeks.append(week_days)

    return templates.TemplateResponse(request, "calendar.html", {
        "request": request, "user": user, "target": target,
        "can_see_detail": can_see_target_detail,
        "year": year, "month": month, "events": events, "attendance": attendance,
        "leaves": leaves, "visible_people": visible_people,
        "month_name": pycal.month_name[month], "weeks": weeks,
        "prev_year": prev_year, "prev_month": prev_month,
        "next_year": next_year, "next_month": next_month,
    })


@router.post("/calendar/prompt")
def submit_prompt(request: Request, text: str = Form(...), confirm: bool = Form(False),
                   db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    parsed = parse_prompt(text)

    if parsed["confidence"] == "LOW" and not confirm:
        return JSONResponse({"needs_confirmation": True, "parsed": _jsonable(parsed)})

    intent = parsed["intent"]
    f = parsed["fields"]

    if intent == "TASK_UPDATE":
        q = db.query(models.CalendarEvent).filter(models.CalendarEvent.owner_id == user.id)
        if f.get("title_contains"):
            q = q.filter(models.CalendarEvent.title.ilike(f"%{f['title_contains']}%"))
        ev = q.order_by(models.CalendarEvent.created_at.desc()).first()
        if ev:
            ev.status = f.get("new_status", "DONE")
            db.commit()
            return JSONResponse({"ok": True, "message": f"Updated '{ev.title}' to {ev.status}."})
        return JSONResponse({"ok": False, "message": "Could not find a matching task."})

    if intent == "RESIGNATION":
        return JSONResponse({"ok": False, "message": "Please use the Resignation page to submit this formally.", "redirect": "/resignation"})

    if intent == "ATTENDANCE":
        start = f["start_date"]
        end = f["end_date"]
        d = start
        count = 0
        while d <= end:
            existing = db.query(models.Attendance).filter(models.Attendance.user_id == user.id, models.Attendance.date == d).first()
            if existing:
                existing.status = f["status"]
                existing.raw_prompt_text = text
            else:
                db.add(models.Attendance(user_id=user.id, date=d, status=f["status"], raw_prompt_text=text))
            d += dt.timedelta(days=1)
            count += 1
        db.commit()
        return JSONResponse({"ok": True, "message": f"Marked {f['status']} for {count} day(s)."})

    if intent == "LEAVE":
        if not f.get("start_date"):
            return JSONResponse({"ok": False, "message": "Could not detect leave dates. Please use the Leave page."})
        default_lt = db.query(models.LeaveType).first()
        lr = models.LeaveRequest(
            user_id=user.id, leave_type_id=default_lt.id if default_lt else None,
            start_date=f["start_date"], end_date=f["end_date"] or f["start_date"],
            reason=text, status="PENDING", raw_prompt_text=text,
        )
        db.add(lr)
        db.commit()
        return JSONResponse({"ok": True, "message": "Leave request submitted for approval."})

    if intent in ("TASK", "MEETING", "PENDING_ACTION", "REMINDER"):
        start_date = f.get("start_date") or f.get("due_date") or dt.date.today()
        ev = models.CalendarEvent(
            owner_id=user.id, event_type=intent, title=f.get("title", text)[:255],
            start_date=start_date, start_time=f.get("start_time"),
            priority=f.get("priority", "MEDIUM"), status="OPEN", raw_prompt_text=text,
        )
        db.add(ev)
        db.commit()
        return JSONResponse({"ok": True, "message": f"{intent.replace('_', ' ').title()} added to your calendar."})

    return JSONResponse({"ok": False, "message": "Sorry, I couldn't understand that. Please use a manual form."})


def _jsonable(parsed):
    f = dict(parsed["fields"])
    for k, v in f.items():
        if isinstance(v, dt.date):
            f[k] = v.isoformat()
    return {"intent": parsed["intent"], "confidence": parsed["confidence"], "fields": f, "raw_prompt_text": parsed["raw_prompt_text"]}


@router.post("/calendar/manual")
def manual_create(request: Request, event_type: str = Form(...), title: str = Form(...),
                   start_date: str = Form(...), start_time: str = Form(None),
                   priority: str = Form("MEDIUM"), description: str = Form(None),
                   db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    ev = models.CalendarEvent(
        owner_id=user.id, event_type=event_type, title=title,
        start_date=dt.date.fromisoformat(start_date), start_time=start_time or None,
        priority=priority, status="OPEN", description=description,
        raw_prompt_text="[manual entry]",
    )
    db.add(ev)
    db.commit()
    return RedirectResponse("/calendar", status_code=303)


@router.post("/calendar/event/{event_id}/status")
def update_status(event_id: int, status: str = Form(...), db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    ev = db.query(models.CalendarEvent).get(event_id)
    if ev and ev.owner_id == user.id:
        ev.status = status
        db.commit()
    return RedirectResponse("/calendar", status_code=303)
