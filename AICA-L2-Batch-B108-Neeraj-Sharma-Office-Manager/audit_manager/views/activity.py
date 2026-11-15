from flask import Blueprint, render_template, request

from .. import parse_date
from ..access import admin_required
from ..models import ActivityLog, User, db

bp = Blueprint("activity", __name__, url_prefix="/activity")


@bp.route("/")
@admin_required
def index():
    q = ActivityLog.query
    user_id, module = request.args.get("user_id", type=int), request.args.get("module", "")
    start, end = parse_date(request.args.get("from_date")), parse_date(request.args.get("to_date"))
    if user_id:
        q = q.filter(ActivityLog.user_id == user_id)
    if module:
        q = q.filter(ActivityLog.module == module)
    if start:
        q = q.filter(db.func.date(ActivityLog.created_at) >= start.isoformat())
    if end:
        q = q.filter(db.func.date(ActivityLog.created_at) <= end.isoformat())
    page = max(1, request.args.get("page", 1, type=int))
    logs = q.order_by(ActivityLog.id.desc()).paginate(page=page, per_page=50, error_out=False)
    modules = db.session.query(ActivityLog.module, db.func.count()).group_by(ActivityLog.module).order_by(ActivityLog.module).all()
    args = {k: v for k, v in request.args.items() if k != "page" and v}
    return render_template("activity/index.html", logs=logs, users=User.query.order_by(User.name).all(), modules=modules,
                           user_id=user_id, module=module, from_date=request.args.get("from_date", ""), to_date=request.args.get("to_date", ""), args=args)
