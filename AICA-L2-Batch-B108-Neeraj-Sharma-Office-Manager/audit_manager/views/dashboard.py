from datetime import date, timedelta

from flask import Blueprint, g, render_template

from ..access import login_required, visible_client_ids, visible_tasks
from ..models import Client, ComplianceDeadline, GstReturn, Invoice, ItrFiling, Task, TdsReturn

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required
def index():
    ids = visible_client_ids(g.user)
    today = date.today()

    def pending(model):
        return model.query.filter(model.client_id.in_(ids), model.status != "filed")

    open_deadlines = ComplianceDeadline.query.filter(ComplianceDeadline.client_id.in_(ids), ComplianceDeadline.status != "completed")
    open_tasks = visible_tasks(g.user).filter(Task.status != "completed")
    kpis = [
        ("Active clients", Client.query.filter(Client.id.in_(ids), Client.status == "active").count(), "bi-building", "primary"),
        ("GST returns pending", pending(GstReturn).count(), "bi-receipt-cutoff", "info"),
        ("ITR filings pending", pending(ItrFiling).count(), "bi-file-earmark-check", "info"),
        ("TDS returns pending", pending(TdsReturn).count(), "bi-percent", "info"),
        ("Overdue deadlines", open_deadlines.filter(ComplianceDeadline.due_date < today).count(), "bi-exclamation-triangle", "danger"),
        ("Open tasks", open_tasks.count(), "bi-kanban", "warning"),
    ]
    outstanding = None
    if g.user.is_manager_or_above:
        outstanding = round(sum(i.balance for i in Invoice.query.filter(Invoice.status != "paid")), 2)
    upcoming = (open_deadlines.filter(ComplianceDeadline.due_date <= today + timedelta(days=14))
                .order_by(ComplianceDeadline.due_date).limit(12).all())
    mine = open_tasks.filter(Task.assigned_to_id == g.user.id).all()
    my_tasks = sorted(mine, key=lambda t: (t.due_date or date.max))[:8]
    return render_template("dashboard.html", kpis=kpis, outstanding=outstanding, upcoming=upcoming, my_tasks=my_tasks)


@bp.route("/help")
@login_required
def help_page():
    from ..help_content import GROUPS, TROUBLE

    return render_template("help.html", groups=GROUPS, trouble=TROUBLE)
