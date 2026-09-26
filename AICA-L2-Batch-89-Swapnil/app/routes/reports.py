"""Calendar (+ .ics), reports and Excel exports, client reminder letters, notifications."""
from __future__ import annotations

import calendar as pycal
from collections import defaultdict
from datetime import date, timedelta

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import select

from .. import audit
from ..auth import actor, today
from ..exports import (REGISTER_HEADERS, REGISTER_WIDTHS, build_ics, kpis, letter_items, register_rows,
                       workbook_bytes)
from ..models import CLOSED, Entity, Filing, Notification, Obligation, User, db, utcnow
from ..permissions import can_see_entity, deny, has, require
from ..services import (HEALTH_LABELS, fee_for, get_setting, health, rulepack, visible_entities_query,
                        visible_obligations_query)
from .entities import to_date

bp = Blueprint("reports", __name__)

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _filtered(args, include_closed=True):
    q = visible_obligations_query(current_user)
    if args.get("entity_id", "").isdigit():
        e = db.session.get(Entity, int(args["entity_id"]))
        if e is None or not can_see_entity(current_user, e):
            abort(404)
        q = q.where(Obligation.entity_id == e.id)
    if args.get("staff", "").isdigit():
        q = q.where(Obligation.assignee_id == int(args["staff"]))
    if args.get("form"):
        q = q.where(Obligation.rule_code == args["form"])
    if not include_closed:
        q = q.where(Obligation.status.not_in(list(CLOSED)))
    return q


def _filters_ctx():
    ents = db.session.execute(visible_entities_query(current_user).order_by(Entity.name)).scalars().all()
    staff = db.session.execute(select(User).where(User.is_active_flag.is_(True)).order_by(User.full_name)).scalars().all()
    codes = sorted({(r.code, r.form) for r in rulepack().rules}, key=lambda x: x[1])
    return {"ents": ents, "staff": staff, "codes": codes, "a": request.args}


# ================================================================ calendar
@bp.route("/calendar")
@require("view")
def calendar():
    t = today()
    view = request.args.get("view", "month")
    try:
        y, m = (int(x) for x in request.args.get("month", f"{t.year}-{t.month:02d}").split("-"))
        first = date(y, m, 1)
    except ValueError:
        first = date(t.year, t.month, 1)
    if view == "agenda":
        start = to_date(request.args.get("from")) or t
        end = to_date(request.args.get("to")) or start + timedelta(days=60)
    else:
        start = first - timedelta(days=first.weekday())
        last = date(first.year, first.month, pycal.monthrange(first.year, first.month)[1])
        end = last + timedelta(days=6 - last.weekday())
    q = _filtered(request.args).where(Obligation.due_date >= start, Obligation.due_date <= end).order_by(
        Obligation.due_date, Obligation.form)
    obls = db.session.execute(q).scalars().all()
    by_day = defaultdict(list)
    for o in obls:
        by_day[o.due_date].append(o)
    weeks = []
    d = start
    while d <= end and view == "month":
        weeks.append([d + timedelta(days=i) for i in range(7)])
        d += timedelta(days=7)
    prev_m = (first - timedelta(days=1)).replace(day=1)
    next_m = (first + timedelta(days=32)).replace(day=1)
    return render_template("calendar.html", view=view, first=first, weeks=weeks, by_day=by_day, obls=obls,
                           start=start, end=end, prev_m=prev_m, next_m=next_m, health=lambda o: health(o, t),
                           **_filters_ctx())


@bp.route("/calendar.ics")
@require("view")
def calendar_ics():
    scope = request.args.get("scope", "mine")
    q = _filtered(request.args)
    if scope == "mine":
        q = q.where(Obligation.assignee_id == current_user.id)
        name = f"MCA compliance — {current_user.full_name}"
    elif scope == "entity":
        if not request.args.get("entity_id", "").isdigit():
            abort(422)
        name = f"MCA compliance — {db.session.get(Entity, int(request.args['entity_id'])).name}"
    else:
        name = f"MCA compliance — {get_setting('firm_name')}"
    obls = db.session.execute(q.order_by(Obligation.due_date)).scalars().all()
    body = build_ics(obls, name, get_setting("firm_name"), today())
    audit.record(db.session, actor(), "ICS_EXPORTED", "calendar", scope, request.args.get("entity_id", type=int),
                 after={"events": len(obls)})
    db.session.commit()
    fname = f"mca-{scope}-{today():%Y%m%d}.ics"
    return Response(body, mimetype="text/calendar; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename={fname}"})


# ================================================================= reports
@bp.route("/reports")
@require("view")
def index():
    t = today()
    obls = db.session.execute(visible_obligations_query(current_user, include_pre_engagement=True)).scalars().all()
    filings = {f.obligation_id: f for f in db.session.execute(select(Filing)).scalars()}
    overdue = sorted((o for o in obls if health(o, t) == "overdue"), key=lambda o: o.due_date)
    exposure = [(o, fee_for(o, t) if o.fee_regime != "NONE" else None) for o in overdue]
    total_exposure = sum(fb.total for _, fb in exposure if fb and not fb.blocked)
    per_entity, per_staff, window_start = kpis(obls, filings, t)
    ents = {e.id: e for e in db.session.execute(visible_entities_query(current_user)).scalars()}
    users = {u.id: u for u in db.session.execute(select(User)).scalars()}
    scores = sorted(((ents[eid], ok, n) for eid, (ok, n) in per_entity.items() if eid in ents),
                    key=lambda x: (x[1] / x[2] if x[2] else 1))
    staff = sorted(((users[uid], ok, n) for uid, (ok, n) in per_staff.items() if uid in users),
                   key=lambda x: -(x[1] / x[2] if x[2] else 0))
    return render_template("reports.html", mode="reports", exposure=exposure, total_exposure=total_exposure,
                           scores=scores, staff_kpi=staff, window_start=window_start, **_filters_ctx())


def _xlsx(data: bytes, name: str):
    return Response(data, mimetype=XLSX, headers={"Content-Disposition": f"attachment; filename={name}"})


@bp.route("/reports/register.xlsx")
@require("view")
def register_xlsx():
    t = today()
    obls = db.session.execute(_filtered(request.args).order_by(Obligation.due_date)).scalars().all()
    rows = register_rows(obls, t, fee_for)
    data = workbook_bytes([dict(title="Compliance register", headers=REGISTER_HEADERS, rows=rows,
                                widths=REGISTER_WIDTHS, money_cols=(11, 12), date_cols=(5, 10))],
                          [("Firm", get_setting("firm_name")), ("Prepared by", current_user.full_name),
                           ("As on", t.strftime("%d-%m-%Y")), ("Rule pack", rulepack().version),
                           ("Use", "INTERNAL — firm working paper; fees are estimates where the rule is unverified")])
    audit.record(db.session, actor(), "EXPORT_REGISTER", "report", "register.xlsx", after={"rows": len(rows)})
    db.session.commit()
    return _xlsx(data, f"compliance-register-{t:%Y%m%d}.xlsx")


@bp.route("/reports/overdue.xlsx")
@require("view")
def overdue_xlsx():
    t = today()
    obls = [o for o in db.session.execute(_filtered(request.args, include_closed=False)).scalars()
            if o.due_date < t]
    rows = []
    for o in sorted(obls, key=lambda o: o.due_date):
        fb = fee_for(o, t) if o.fee_regime != "NONE" else None
        rows.append([o.entity.name if o.entity else o.person.name, o.form, o.period_key, o.due_date, (t - o.due_date).days,
                     fb.normal if fb else None, fb.additional if fb else None, fb.scheme_relief if fb else None,
                     fb.total if fb else None, (fb.slab or "") if fb else "", (fb.scheme or "") if fb else "",
                     ("Verified" if fb.verified else "Estimate — unverified") if fb else "No fee"])
    data = workbook_bytes([dict(title="Overdue & fee exposure",
                                headers=["Entity / person", "Form", "Period", "Due date", "Days late", "Normal ₹",
                                         "Additional ₹", "Scheme relief ₹", "Total if filed today ₹", "Slab", "Scheme",
                                         "Basis"], rows=rows, widths=[32, 26, 16, 12, 10, 12, 14, 14, 18, 22, 14, 22],
                                money_cols=(6, 7, 8, 9), date_cols=(4,))],
                          [("As on", t.strftime("%d-%m-%Y")), ("Penalties",
                           "Not included — adjudicated by the ROC under s.454 / LLP Act s.76A")])
    audit.record(db.session, actor(), "EXPORT_OVERDUE", "report", "overdue.xlsx",
                 after={"rows": len(rows), "fees": [[r[0], r[1], r[8]] for r in rows]})
    db.session.commit()
    return _xlsx(data, f"overdue-fee-exposure-{t:%Y%m%d}.xlsx")


# ============================================================ client letter
def _letter_obligations(e: Entity, start: date, end: date) -> list[Obligation]:
    from ..models import EntityPerson
    persons = select(EntityPerson.person_id).where(EntityPerson.entity_id == e.id, EntityPerson.ceased_on.is_(None))
    q = select(Obligation).where(((Obligation.entity_id == e.id) | Obligation.person_id.in_(persons)),
                                 Obligation.superseded_at.is_(None), Obligation.status.not_in(list(CLOSED)),
                                 Obligation.due_date <= end, Obligation.fee_regime != "NONE")
    return [o for o in db.session.execute(q.order_by(Obligation.due_date)).scalars()
            if o.due_date >= start or o.due_date < today()]


@bp.route("/letters")
@require("view")
def letter():
    t = today()
    ctx = _filters_ctx()
    e = None
    if request.args.get("entity_id", "").isdigit():
        e = db.session.get(Entity, int(request.args["entity_id"]))
        if e is None or not can_see_entity(current_user, e):
            abort(404)
    start = to_date(request.args.get("from")) or t
    end = to_date(request.args.get("to")) or t + timedelta(days=60)
    if e is None:
        return render_template("reports.html", mode="letter_form", start=start, end=end, **ctx)
    obls = _letter_obligations(e, start, end)
    unverified = rulepack().unverified([o.rule_code for o in obls])
    if unverified:
        audit.record(db.session, actor(), "EXPORT_BLOCKED", "letter", e.id, e.id, after={"unverified_rules": unverified})
        db.session.commit()
        return render_template("reports.html", mode="letter_form", start=start, end=end, blocked=unverified, e=e,
                               **ctx), 409
    fees = {o.id: fee_for(o, t) for o in obls if o.due_date < t}
    audit.record(db.session, actor(), "CLIENT_LETTER", "letter", e.id, e.id,
                 after={"window": [start, end], "items": [[o.key, o.due_date, fees[o.id].total if o.id in fees else 0]
                                                          for o in obls]})
    db.session.commit()
    return render_template("reports.html", mode="letter", e=e, items=letter_items(obls), fees=fees, start=start, end=end,
                           signatory=get_setting("firm_signatory"), address=get_setting("firm_address"), **ctx)


# ============================================================ notifications
@bp.route("/notifications")
@require("view")
def notifications():
    rows = db.session.execute(select(Notification).where(Notification.user_id == current_user.id).order_by(
        Notification.read_at.is_not(None), Notification.id.desc()).limit(200)).scalars().all()
    return render_template("reports.html", mode="notifications", rows=rows, **_filters_ctx())


@bp.route("/notifications/read", methods=["POST"])
@require("view")
def notifications_read():
    now = utcnow()
    for n in db.session.execute(select(Notification).where(Notification.user_id == current_user.id,
                                                           Notification.read_at.is_(None))).scalars():
        n.read_at = now
    db.session.commit()
    return redirect(url_for("reports.notifications"))
