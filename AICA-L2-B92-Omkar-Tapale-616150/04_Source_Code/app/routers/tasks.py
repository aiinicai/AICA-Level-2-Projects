import datetime as dt
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, permissions
from ..auth import get_current_user, log_audit
from ..main import templates

router = APIRouter()

TASK_TYPES = ("TASK", "PENDING_ACTION")


@router.get("/tasks")
def tasks_page(request: Request, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    assigned_to_me = db.query(models.CalendarEvent).filter(
        models.CalendarEvent.owner_id == user.id,
        models.CalendarEvent.event_type.in_(TASK_TYPES),
        models.CalendarEvent.assigned_by_id.isnot(None),
    ).order_by(models.CalendarEvent.status, models.CalendarEvent.start_date).all()

    my_own_tasks = db.query(models.CalendarEvent).filter(
        models.CalendarEvent.owner_id == user.id,
        models.CalendarEvent.event_type.in_(TASK_TYPES),
        models.CalendarEvent.assigned_by_id.is_(None),
    ).order_by(models.CalendarEvent.status, models.CalendarEvent.start_date).all()

    assigned_by_me = db.query(models.CalendarEvent).filter(
        models.CalendarEvent.assigned_by_id == user.id,
        models.CalendarEvent.event_type.in_(TASK_TYPES),
    ).order_by(models.CalendarEvent.status, models.CalendarEvent.start_date).all()

    all_ids = [e.id for e in (assigned_to_me + my_own_tasks + assigned_by_me)]
    comments_by_event = {}
    if all_ids:
        rows = db.query(models.TaskComment).filter(models.TaskComment.event_id.in_(all_ids)).order_by(models.TaskComment.created_at).all()
        for c in rows:
            comments_by_event.setdefault(c.event_id, []).append(c)

    assignable = permissions.assignable_users(db, user)

    return templates.TemplateResponse(request, "tasks.html", {
        "request": request, "user": user,
        "assigned_to_me": assigned_to_me, "my_own_tasks": my_own_tasks, "assigned_by_me": assigned_by_me,
        "comments_by_event": comments_by_event, "assignable": assignable,
    })


@router.post("/tasks/assign")
def assign_task(assignee_id: int = Form(...), title: str = Form(...), description: str = Form(""),
                 due_date: str = Form(...), priority: str = Form("MEDIUM"),
                 db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    assignee = db.query(models.User).get(assignee_id)
    if not assignee or not permissions.can_assign_to(db, user, assignee):
        return RedirectResponse("/tasks", status_code=303)

    ev = models.CalendarEvent(
        owner_id=assignee.id, assigned_by_id=user.id, event_type="TASK",
        title=title, description=description, start_date=dt.date.fromisoformat(due_date),
        priority=priority, status="OPEN", raw_prompt_text=f"[assigned by {user.employee_code}]",
    )
    db.add(ev)
    db.commit()
    log_audit(db, user, "TASK_ASSIGNED", f"{user.employee_code} assigned '{title}' to {assignee.employee_code}")
    return RedirectResponse("/tasks", status_code=303)


@router.post("/tasks/{event_id}/status")
def update_task_status(event_id: int, status: str = Form(...), db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    ev = db.query(models.CalendarEvent).get(event_id)
    if not ev:
        return RedirectResponse("/tasks", status_code=303)
    owner = db.query(models.User).get(ev.owner_id)
    if permissions.can_manage_task(db, user, owner, ev.assigned_by_id):
        ev.status = status
        db.commit()
        log_audit(db, user, "TASK_STATUS_UPDATED", f"Task #{ev.id} '{ev.title}' -> {status} by {user.employee_code}")
    return RedirectResponse("/tasks", status_code=303)


@router.post("/tasks/{event_id}/comment")
def add_comment(event_id: int, message: str = Form(...), comment_type: str = Form("COMMENT"),
                 db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    ev = db.query(models.CalendarEvent).get(event_id)
    if not ev or not message.strip():
        return RedirectResponse("/tasks", status_code=303)
    owner = db.query(models.User).get(ev.owner_id)
    if permissions.can_manage_task(db, user, owner, ev.assigned_by_id):
        db.add(models.TaskComment(
            event_id=ev.id, author_id=user.id,
            comment_type="QUERY" if comment_type == "QUERY" else "COMMENT",
            message=message.strip(),
        ))
        db.commit()
    return RedirectResponse("/tasks", status_code=303)
