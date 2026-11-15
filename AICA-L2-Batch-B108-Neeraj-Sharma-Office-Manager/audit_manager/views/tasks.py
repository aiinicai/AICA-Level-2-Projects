from datetime import datetime

from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, url_for

from .. import log_activity, parse_date
from ..access import get_client_or_403, login_required, manager_required, visible_clients, visible_tasks
from ..models import Client, Task, TaskComment, User, db

bp = Blueprint("tasks", __name__, url_prefix="/tasks")

STATUSES = {"todo": "To Do", "in_progress": "In Progress", "under_review": "Under Review", "completed": "Completed"}
PRIORITIES = {"low": "Low", "medium": "Medium", "high": "High", "urgent": "Urgent"}
CATEGORIES = {"general": "General", "gst": "GST", "itr": "ITR", "tds": "TDS", "audit": "Audit", "accounting": "Accounting", "roc": "ROC"}


def _get_task(task_id: int) -> Task:
    task = db.get_or_404(Task, task_id)
    if visible_tasks(g.user).filter(Task.id == task.id).first() is None:
        abort(403)
    return task


@bp.route("/")
@login_required
def index():
    q = visible_tasks(g.user)
    mine = request.args.get("mine") == "1"
    if mine:
        q = q.filter(Task.assigned_to_id == g.user.id)
    tasks = q.order_by(Task.due_date.is_(None), Task.due_date).all()
    view = request.args.get("view", "kanban")
    return render_template("tasks/index.html", tasks=tasks, view=view if view in ("kanban", "table") else "kanban", mine=mine,
                           statuses=STATUSES, priorities=PRIORITIES, categories=CATEGORIES,
                           clients=visible_clients(g.user).order_by(Client.name).all(),
                           staff=User.query.filter_by(is_active_user=True).order_by(User.name).all())


@bp.route("/add", methods=["POST"])
@login_required
def add():
    f = request.form
    title = f.get("title", "").strip()
    if not title:
        flash("A task needs a title.", "danger")
        return redirect(url_for("tasks.index"))
    client_id = f.get("client_id", type=int)
    if client_id:
        get_client_or_403(g.user, client_id)
    assignee = f.get("assigned_to_id", type=int) or g.user.id
    if not g.user.is_manager_or_above:
        assignee = g.user.id  # employees create tasks for themselves; managers allocate work
    db.session.add(Task(title=title, description=f.get("description", "").strip() or None, client_id=client_id or None,
                        assigned_to_id=assignee, created_by_id=g.user.id,
                        category=f.get("category") if f.get("category") in CATEGORIES else "general",
                        priority=f.get("priority") if f.get("priority") in PRIORITIES else "medium", due_date=parse_date(f.get("due_date"))))
    log_activity("tasks", f"Created task '{title}'")
    db.session.commit()
    if assignee != g.user.id:
        from ..services import automation

        due = parse_date(f.get("due_date"))
        automation.fire("task_assigned", staff=db.session.get(User, assignee), user_id=g.user.id,
                        values={"period": title, "due_date": f"{due:%d-%b-%Y}" if due else "Not fixed"})
        db.session.commit()
    flash("Task created.", "success")
    if f.get("back") == "calendar":
        due = parse_date(f.get("due_date"))
        return redirect(url_for("calendar.index", year=due.year, month=due.month) if due else url_for("calendar.index"))
    return redirect(url_for("tasks.index"))


@bp.route("/<int:task_id>")
@login_required
def show(task_id):
    return render_template("tasks/show.html", task=_get_task(task_id), statuses=STATUSES)


@bp.route("/<int:task_id>/status", methods=["POST"])
@login_required
def set_status(task_id):
    task = _get_task(task_id)
    new = request.form.get("status") or (request.get_json(silent=True) or {}).get("status")
    if new not in STATUSES:
        abort(400, "Unknown status.")
    task.status = new
    task.completed_at = datetime.utcnow() if new == "completed" else None
    log_activity("tasks", f"Task '{task.title}' moved to {STATUSES[new]}")
    db.session.commit()
    if request.is_json or request.headers.get("X-Requested-With") == "fetch":
        return jsonify(ok=True, status=new)
    return redirect(request.referrer or url_for("tasks.show", task_id=task.id))


@bp.route("/<int:task_id>/comment", methods=["POST"])
@login_required
def comment(task_id):
    task = _get_task(task_id)
    body = request.form.get("body", "").strip()
    if body:
        db.session.add(TaskComment(task_id=task.id, user_id=g.user.id, body=body))
        db.session.commit()
    return redirect(url_for("tasks.show", task_id=task.id))


@bp.route("/<int:task_id>/delete", methods=["POST"])
@manager_required
def delete(task_id):
    task = db.get_or_404(Task, task_id)
    log_activity("tasks", f"Deleted task '{task.title}'")
    db.session.delete(task)
    db.session.commit()
    flash("Task deleted.", "success")
    return redirect(url_for("tasks.index"))
