from __future__ import annotations

import secrets
from datetime import date
from pathlib import Path

from flask import (Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, url_for)
from flask_login import current_user
from markupsafe import escape
from sqlalchemy import select

from .. import audit
from ..auth import actor, today
from ..models import AuditLog, Filing, Obligation, User, db
from ..permissions import Denied, deny, require
from ..services import (TRANSITIONS, ValidationError, can_see_obligation, change_status, fee_for, health,
                        record_filing, rulepack, visible_obligations_query)
from .entities import to_date, to_money

bp = Blueprint("obligations", __name__)

MAGIC = {b"%PDF-": ".pdf", b"\x89PNG\r\n\x1a\n": ".png"}


def get_obligation(obl_id: int) -> Obligation:
    o = db.session.get(Obligation, obl_id)
    if o is None:
        abort(404)
    if not can_see_obligation(current_user, o):
        deny("view_all", "This obligation belongs to an entity that is not assigned to you.",
             object_type="obligation", object_id=o.key, entity_id=o.entity_id)
    return o


def _render(o: Obligation, status: int = 200):
    t = today()
    what_if = to_date(request.values.get("what_if")) or max(t, o.due_date)
    fb = fee_for(o, what_if) if o.fee_regime != "NONE" else None
    fb_today = fee_for(o, t) if o.fee_regime != "NONE" else None
    filings = db.session.execute(select(Filing).where(Filing.obligation_id == o.id).order_by(Filing.id)).scalars().all()
    history = db.session.execute(select(AuditLog).where(AuditLog.object_id == o.key).order_by(AuditLog.id)).scalars().all()
    rule = rulepack().by_code.get(o.rule_code)
    staff = db.session.execute(select(User).where(User.is_active_flag.is_(True)).order_by(User.full_name)).scalars().all()
    return render_template("obligation.html", o=o, fb=fb, fb_today=fb_today, what_if=what_if, filings=filings,
                           history=history, rule=rule, staff=staff, h=health(o, t),
                           next_statuses=list(TRANSITIONS.get(o.status, {}))), status


@bp.route("/obligations/<int:obl_id>")
@require("view")
def show(obl_id: int):
    return _render(get_obligation(obl_id))


SORTS = {"due": lambda o: (o.due_date, o.form), "entity": lambda o: ((o.entity.name if o.entity else o.person.name), o.due_date),
         "form": lambda o: (o.form, o.due_date), "status": lambda o: (o.status, o.due_date)}


def row_actions(o: Obligation) -> list[str]:
    """One-click next steps this user may take (the server re-checks on POST)."""
    from ..permissions import has
    out = []
    for s, perm in TRANSITIONS.get(o.status, {}).items():
        if s == "FILED" or not has(current_user, perm):
            continue
        if s == "APPROVED_FOR_FILING" and o.ready_by_id == current_user.id:
            continue
        if s in ("NOT_STARTED",) or (s == "IN_PROGRESS" and o.status != "NOT_STARTED"):
            continue
        out.append(s)
    return out


def render_row(o: Obligation):
    from flask import get_template_attribute
    from ..permissions import has
    staff = db.session.execute(select(User).where(User.is_active_flag.is_(True)).order_by(User.full_name)).scalars().all()
    return get_template_attribute("_macros.html", "row")(o, health(o, today()), row_actions(o), has(current_user, "assign"),
                                                      staff)


@bp.route("/work")
@require("view")
def queue():
    from ..permissions import has
    scope = request.args.get("scope", "mine")
    q = visible_obligations_query(current_user).where(Obligation.status.not_in(
        ["FILED", "ROC_APPROVED", "NOT_APPLICABLE", "WAIVED"]))
    if scope == "mine" or not has(current_user, "assign"):
        scope = "mine"
        q = q.where(Obligation.assignee_id == current_user.id)
    elif scope == "unassigned":
        q = q.where(Obligation.assignee_id.is_(None))
    horizon = to_date(request.args.get("until"))
    if horizon:
        q = q.where(Obligation.due_date <= horizon)
    obls = db.session.execute(q).scalars().all()
    sort = request.args.get("sort", "due")
    obls.sort(key=SORTS.get(sort, SORTS["due"]))
    staff = db.session.execute(select(User).where(User.is_active_flag.is_(True)).order_by(User.full_name)).scalars().all()
    t = today()
    return render_template("work.html", obls=obls[:500], total=len(obls), sort=sort, scope=scope, staff=staff,
                           health=lambda o: health(o, t), actions=row_actions, until=request.args.get("until", ""))


@bp.route("/work/assign", methods=["POST"])
@require("assign")
def bulk_assign():
    ids = [int(i) for i in request.form.getlist("ids") if i.isdigit()]
    uid = request.form.get("assignee_id")
    user = db.session.get(User, int(uid)) if uid else None
    if not ids or (uid and (user is None or not user.is_active)):
        flash("Tick at least one obligation and choose an active staff member.", "danger")
        return redirect(request.referrer or url_for("obligations.queue")), 303
    n = 0
    for oid in ids:
        o = get_obligation(oid)
        before = o.assignee_id
        o.assignee_id = user.id if user else None
        audit.record(db.session, actor(), "ASSIGNED", "obligation", o.key, o.entity_id, before={"assignee_id": before},
                     after={"assignee_id": o.assignee_id, "bulk": True})
        n += 1
    db.session.commit()
    flash(f"{n} obligation(s) assigned to {user.full_name if user else 'nobody'}.", "success")
    return redirect(request.referrer or url_for("obligations.queue", scope="team"))


@bp.route("/obligations/<int:obl_id>/status", methods=["POST"])
@require("view")
def set_status(obl_id: int):
    o = get_obligation(obl_id)
    new = request.form.get("status", "")
    try:
        change_status(o, new, current_user, actor(), request.form.get("reason"))
    except Denied as d:
        deny(d.perm, d.message, object_type="obligation", object_id=o.key, entity_id=o.entity_id)
    except ValidationError as v:
        db.session.rollback()
        if request.headers.get("HX-Request"):
            abort(422, " ".join(v.messages))
        for m in v.messages:
            flash(m, "danger")
        return _render(o, 422)
    db.session.commit()
    if request.headers.get("HX-Request"):
        return render_row(o)
    flash("Status updated.", "success")
    return redirect(url_for("obligations.show", obl_id=o.id))


def save_upload(fs) -> tuple[str, str, int] | None:
    """Sniff the content (not the extension), cap at 5 MB, store under a random name
    outside static/. Returns (stored_name, original_name, size)."""
    if fs is None or not fs.filename:
        return None
    head = fs.stream.read(8)
    fs.stream.seek(0)
    ext = next((e for magic, e in MAGIC.items() if head.startswith(magic)), None)
    if ext is None:
        raise ValidationError("Only PDF or PNG files can be uploaded (the file's content was checked, not its name).")
    data = fs.read()
    if len(data) > 5 * 1024 * 1024:
        raise ValidationError("The file is larger than 5 MB.")
    name = secrets.token_hex(16) + ext
    folder = Path(current_app.config["UPLOAD_DIR"])
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(data)
    return name, Path(fs.filename).name[:200], len(data)


@bp.route("/obligations/<int:obl_id>/file", methods=["POST"])
@require("mark_filed")
def file(obl_id: int):
    o = get_obligation(obl_id)
    try:
        saved = save_upload(request.files.get("attachment"))
        att = saved[:2] if saved else None
        fd = to_date(request.form.get("filing_date"))
        if fd is None:
            raise ValidationError("Enter the filing date.")
        f = record_filing(o, current_user, actor(), srn=request.form.get("srn", ""), filing_date=fd,
                          normal_paid=to_money(request.form.get("normal_fee_paid")) or 0.0,
                          additional_paid=to_money(request.form.get("additional_fee_paid")) or 0.0,
                          today=today(), attachment=att)
    except Denied as d:
        deny(d.perm, d.message, object_type="obligation", object_id=o.key, entity_id=o.entity_id)
    except ValidationError as v:
        db.session.rollback()
        for m in v.messages:
            flash(m, "danger")
        return _render(o, 422)
    db.session.commit()
    if f.fee_mismatch:
        flash(f"Marked filed. Note: fees paid differ from the engine's computation "
              f"({f.computed_fee_json.get('total')}). Check the breakdown.", "warning")
    else:
        flash("Marked filed.", "success")
    return redirect(url_for("obligations.show", obl_id=o.id))


@bp.route("/obligations/<int:obl_id>/assign", methods=["POST"])
@require("assign")
def assign(obl_id: int):
    o = get_obligation(obl_id)
    uid = request.form.get("assignee_id")
    user = db.session.get(User, int(uid)) if uid else None
    if uid and (user is None or not user.is_active):
        abort(422)
    before = {"assignee_id": o.assignee_id}
    o.assignee_id = user.id if user else None
    audit.record(db.session, actor(), "ASSIGNED", "obligation", o.key, o.entity_id, before=before,
                 after={"assignee_id": o.assignee_id, "assignee": user.full_name if user else None})
    db.session.commit()
    if request.headers.get("HX-Request"):
        return f'<span class="text-success">Assigned to {escape(user.full_name) if user else "nobody"}</span>'
    flash("Assignment saved.", "success")
    return redirect(url_for("obligations.show", obl_id=o.id))


@bp.route("/files/<int:filing_id>")
@require("view")
def download(filing_id: int):
    f = db.session.get(Filing, filing_id)
    if f is None or not f.attachment_path:
        abort(404)
    get_obligation(f.obligation_id)
    path = Path(current_app.config["UPLOAD_DIR"]) / f.attachment_path
    if not path.is_file():
        abort(404)
    audit.record(db.session, actor(), "FILE_DOWNLOADED", "filing", f.id, f.obligation.entity_id)
    db.session.commit()
    return send_file(path, download_name=f.attachment_name or f.attachment_path, as_attachment=True)
