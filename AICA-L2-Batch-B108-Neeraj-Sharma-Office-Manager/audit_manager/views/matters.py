from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .. import log_activity, parse_date
from ..access import can_access_client, get_client_or_403, login_required, manager_required, visible_clients
from ..models import Client, Matter, User, db

bp = Blueprint("matters", __name__, url_prefix="/matters")


def _visible():
    ids = [c.id for c in visible_clients(g.user).with_entities(Client.id)]
    return Matter.query.filter(Matter.client_id.in_(ids))


@bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        f = request.form
        client = get_client_or_403(g.user, f.get("client_id", type=int) or 0)
        title = f.get("title", "").strip()
        if not title:
            flash("Give the matter a title, for example 'Sharma vs State Bank'.", "danger")
            return redirect(url_for("matters.index"))
        m = db.session.get(Matter, f.get("id", type=int) or 0)
        if m is not None and not can_access_client(g.user, m.client):
            abort(403)
        if m is None:
            m = Matter()
            db.session.add(m)
        m.client_id, m.title = client.id, title[:200]
        m.case_number, m.court = f.get("case_number", "").strip()[:80] or None, f.get("court", "").strip()[:160] or None
        m.opposite_party, m.stage = f.get("opposite_party", "").strip()[:200] or None, f.get("stage", "").strip()[:120] or None
        m.next_hearing = parse_date(f.get("next_hearing"))
        m.status = "closed" if f.get("status") == "closed" else "open"
        m.assigned_to_id = f.get("assigned_to_id", type=int) or None
        m.notes = f.get("notes", "").strip() or None
        log_activity("matters", f"Saved matter {m.title}")
        db.session.commit()
        flash("Matter saved.", "success")
        return redirect(url_for("matters.index"))
    status, when = request.args.get("status", "open"), request.args.get("when", "")
    base = _visible()
    counts = {"open": base.filter(Matter.status == "open").count(), "closed": base.filter(Matter.status == "closed").count(),
              "week": base.filter(Matter.status == "open", Matter.next_hearing >= date.today(),
                                  Matter.next_hearing <= date.fromordinal(date.today().toordinal() + 7)).count(),
              "nodate": base.filter(Matter.status == "open", Matter.next_hearing.is_(None)).count()}
    q = base.filter(Matter.status == ("closed" if status == "closed" else "open"))
    if when == "week":
        q = q.filter(Matter.next_hearing >= date.today(), Matter.next_hearing <= date.fromordinal(date.today().toordinal() + 7))
    elif when == "nodate":
        q = q.filter(Matter.next_hearing.is_(None))
    rows = q.order_by(Matter.next_hearing.is_(None), Matter.next_hearing, Matter.title).limit(500).all()
    edit = db.session.get(Matter, request.args.get("edit", type=int) or 0)
    if edit is not None and not can_access_client(g.user, edit.client):
        edit = None
    return render_template("matters/index.html", rows=rows, counts=counts, status=status, when=when, edit=edit, today=date.today(),
                           clients=visible_clients(g.user).order_by(Client.name).all(),
                           staff=User.query.filter_by(is_active_user=True).order_by(User.name).all())


@bp.route("/<int:mid>/delete", methods=["POST"])
@manager_required
def delete(mid):
    m = db.get_or_404(Matter, mid)
    if not can_access_client(g.user, m.client):
        abort(403)
    db.session.delete(m)
    db.session.commit()
    flash("Matter deleted.", "success")
    return redirect(url_for("matters.index"))
