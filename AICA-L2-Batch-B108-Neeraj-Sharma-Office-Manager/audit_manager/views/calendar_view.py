import calendar as cal
from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .. import log_activity, parse_date
from ..access import get_client_or_403, login_required, manager_required, visible_client_ids, visible_clients
from ..models import Client, ComplianceDeadline, ComplianceRule, User, db
from ..services import compliance as comp

bp = Blueprint("calendar", __name__, url_prefix="/calendar")


@bp.route("/")
@login_required
def index():
    today = date.today()
    year = request.args.get("year", today.year, type=int)
    month = request.args.get("month", today.month, type=int)
    if not 1 <= month <= 12:
        month = today.month
    ids = visible_client_ids(g.user)
    first, last = date(year, month, 1), date(year, month, cal.monthrange(year, month)[1])
    items = (ComplianceDeadline.query.filter(ComplianceDeadline.client_id.in_(ids), ComplianceDeadline.due_date >= first,
                                             ComplianceDeadline.due_date <= last).order_by(ComplianceDeadline.due_date).all())
    by_day: dict[int, list] = {}
    for d in items:
        by_day.setdefault(d.due_date.day, []).append(d)
    from ..access import visible_tasks
    from ..models import DueDate, Task

    master: dict[int, list] = {}
    for d in DueDate.query.filter(DueDate.due_date >= first, DueDate.due_date <= last).order_by(DueDate.title):
        master.setdefault(d.due_date.day, []).append(d)
    task_days: dict[int, list] = {}
    for t in visible_tasks(g.user).filter(Task.due_date >= first, Task.due_date <= last).order_by(Task.id):
        task_days.setdefault(t.due_date.day, []).append(t)
    prev_y, prev_m = (year - 1, 12) if month == 1 else (year, month - 1)
    next_y, next_m = (year + 1, 1) if month == 12 else (year, month + 1)
    overdue = (ComplianceDeadline.query.filter(ComplianceDeadline.client_id.in_(ids), ComplianceDeadline.status != "completed",
                                               ComplianceDeadline.due_date < today).order_by(ComplianceDeadline.due_date).limit(30).all())
    return render_template("calendar.html", weeks=cal.Calendar(firstweekday=0).monthdayscalendar(year, month), by_day=by_day,
                           year=year, month=month, month_name=cal.month_name[month], prev=(prev_y, prev_m), next=(next_y, next_m),
                           items=items, overdue=overdue, master=master, task_days=task_days, today_date=today, clients=visible_clients(g.user).order_by(Client.name).all(),
                           staff=User.query.filter_by(is_active_user=True).order_by(User.name).all(),
                           types=comp.COMPLIANCE_TYPES, rules=ComplianceRule.query.order_by(ComplianceRule.title).all())


@bp.route("/add", methods=["POST"])
@login_required
def add():
    f = request.form
    client = get_client_or_403(g.user, f.get("client_id", type=int) or 0)
    due = parse_date(f.get("due_date"))
    title = f.get("title", "").strip()
    if not title or not due:
        flash("A title and a due date are required.", "danger")
    else:
        db.session.add(ComplianceDeadline(title=title, compliance_type=f.get("compliance_type", "custom"), client_id=client.id, due_date=due,
                                          assigned_to_id=f.get("assigned_to_id", type=int) or client.assigned_to_id,
                                          priority=f.get("priority", "medium"), description=f.get("description", "").strip() or None))
        log_activity("calendar", f"Added deadline '{title}' for {client.name}")
        db.session.commit()
        flash("Deadline added.", "success")
    return redirect(request.referrer or url_for("calendar.index"))


@bp.route("/<int:did>/status", methods=["POST"])
@login_required
def status(did):
    d = db.get_or_404(ComplianceDeadline, did)
    get_client_or_403(g.user, d.client_id)
    new = request.form.get("status")
    if new in comp.DEADLINE_STATUSES:
        d.status = new
        d.completed_at = None if new != "completed" else __import__("datetime").datetime.utcnow()
        log_activity("calendar", f"Deadline '{d.title}' marked {new}")
        db.session.commit()
    return redirect(request.referrer or url_for("calendar.index"))


@bp.route("/<int:did>/delete", methods=["POST"])
@manager_required
def delete(did):
    d = db.get_or_404(ComplianceDeadline, did)
    db.session.delete(d)
    db.session.commit()
    flash("Deadline deleted.", "success")
    return redirect(request.referrer or url_for("calendar.index"))


@bp.route("/rules/add", methods=["POST"])
@manager_required
def rule_add():
    f = request.form
    title = f.get("title", "").strip()
    if not title:
        flash("A rule needs a title.", "danger")
    else:
        db.session.add(ComplianceRule(title=title, compliance_type=f.get("compliance_type", "custom"),
                                      frequency=f.get("frequency", "monthly"), due_day=max(1, min(31, f.get("due_day", 1, type=int))),
                                      due_month=f.get("due_month", type=int) or None, applies_to=f.get("applies_to", "all")))
        db.session.commit()
        flash("Rule saved.", "success")
    return redirect(url_for("calendar.index"))


@bp.route("/rules/<int:rid>/generate", methods=["POST"])
@manager_required
def rule_generate(rid):
    rule = db.get_or_404(ComplianceRule, rid)
    year = request.form.get("year", date.today().year, type=int)
    month = request.form.get("month", date.today().month, type=int)
    if not 1 <= month <= 12:
        flash("Choose a month between 1 and 12.", "danger")
        return redirect(url_for("calendar.index"))
    created, skipped = comp.generate_from_rule(rule, year, month, visible_clients(g.user))
    log_activity("calendar", f"Generated '{rule.title}' deadlines: {created} added, {skipped} already existed")
    db.session.commit()
    flash(f"{created} deadline(s) created, {skipped} already existed.", "success")
    return redirect(url_for("calendar.index", year=year, month=month))


# ------------------------------------------------------------------ due-date master
@bp.route("/due-dates", methods=["GET", "POST"])
@login_required
def due_dates():
    from ..models import DueDate
    from ..services import duedates as dd

    if request.method == "POST":
        if not g.user.is_manager_or_above:
            abort(403)
        f = request.form
        if f.get("action") == "extend":
            row = db.get_or_404(DueDate, f.get("id", type=int) or 0)
            new_date = parse_date(f.get("new_date"))
            if not new_date:
                flash("Choose the extended date.", "danger")
            else:
                if row.original_date is None:
                    row.original_date = row.due_date
                row.due_date = new_date
                note = f.get("notes", "").strip()
                row.notes = (note or f"Extended by the department from {row.original_date:%d %b %Y}")[:300]
                log_activity("calendar", f"Extended due date {row.title} to {new_date:%d %b %Y}")
                db.session.commit()
                flash(f"{row.title}: extended to {new_date:%d %b %Y}. Returns already being tracked keep their own dates; change those from the GST / ITR / TDS screen.", "success")
            return redirect(url_for("calendar.due_dates"))
        if f.get("action") == "load_standard":
            n = dd.load_standard()
            log_activity("calendar", f"Loaded {n} standard due dates")
            db.session.commit()
            flash(f"{n} standard due date(s) added." if n else "All standard due dates are already there.", "success")
            return redirect(url_for("calendar.due_dates"))
        title, due = f.get("title", "").strip(), parse_date(f.get("due_date"))
        if not title or not due:
            flash("A due date needs a title and a date.", "danger")
        else:
            row = db.session.get(DueDate, f.get("id", type=int) or 0)
            if row is None:
                row = DueDate()
                db.session.add(row)
            row.title, row.due_date = title[:160], due
            row.category = f.get("category") if f.get("category") in dd.CATEGORIES else "other"
            row.period, row.notes = f.get("period", "").strip()[:80] or None, f.get("notes", "").strip()[:300] or None
            log_activity("calendar", f"Saved due date {title} ({due:%d %b %Y})")
            db.session.commit()
            flash("Due date saved.", "success")
        return redirect(url_for("calendar.due_dates", category=request.args.get("category") or None))
    category, show = request.args.get("category", ""), request.args.get("show", "upcoming")
    q = DueDate.query
    counts = dict(db.session.query(DueDate.category, db.func.count()).group_by(DueDate.category).all())
    if category in dd.CATEGORIES:
        q = q.filter(DueDate.category == category)
    if show != "all":
        q = q.filter(DueDate.due_date >= date.today())
    return render_template("calendar/due_dates.html", rows=q.order_by(DueDate.due_date, DueDate.title).all(), categories=dd.CATEGORIES,
                           category=category, show=show, counts=counts, edit=db.session.get(DueDate, request.args.get("edit", type=int) or 0),
                           extend=db.session.get(DueDate, request.args.get("extend", type=int) or 0), today=date.today())


@bp.route("/due-dates/<int:did>/delete", methods=["POST"])
@manager_required
def due_date_delete(did):
    from ..models import DueDate

    db.session.delete(db.get_or_404(DueDate, did))
    db.session.commit()
    flash("Due date deleted.", "success")
    return redirect(url_for("calendar.due_dates"))
