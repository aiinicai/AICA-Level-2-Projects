from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .. import log_activity, parse_date, perms, to_float
from ..access import get_client_or_403, login_required, visible_clients
from ..models import Client, FirmSetting, TimeEntry, User, db
from ..services import billing as bsvc

bp = Blueprint("timesheet", __name__, url_prefix="/time")


def rate_for(user, client=None) -> float:
    """The client's own rate wins; otherwise the staff member's rate; otherwise the office default."""
    if client is not None and (client.hourly_rate or 0) > 0:
        return float(client.hourly_rate)
    return to_float(FirmSetting.get(f"rate_user_{user.id}") or FirmSetting.get("default_hourly_rate") or 0)


@bp.before_request
def _only_when_switched_on():
    if g.get("user") is not None and FirmSetting.get("hourly_billing") != "1":
        flash("Hour-based billing is switched off. Turn it on in Settings > Type of office.", "warning")
        return redirect(url_for("dashboard.index"))
    return None


def _can_bill() -> bool:
    return perms.can(g.user, "billing")


def _query():
    ids = [c.id for c in visible_clients(g.user, include_archived=True).with_entities(Client.id)]
    q = TimeEntry.query.filter(TimeEntry.client_id.in_(ids))
    if not g.user.is_manager_or_above:
        q = q.filter(TimeEntry.user_id == g.user.id)
    return q


@bp.route("/")
@login_required
def index():
    q = _query()
    client_id, user_id, state = request.args.get("client_id", type=int), request.args.get("user_id", type=int), request.args.get("state", "unbilled")
    start, end = parse_date(request.args.get("from_date")), parse_date(request.args.get("to_date"))
    if client_id:
        q = q.filter(TimeEntry.client_id == client_id)
    if user_id and g.user.is_manager_or_above:
        q = q.filter(TimeEntry.user_id == user_id)
    if start:
        q = q.filter(TimeEntry.work_date >= start)
    if end:
        q = q.filter(TimeEntry.work_date <= end)
    counts = {"unbilled": q.filter(TimeEntry.invoice_id.is_(None), TimeEntry.billable.is_(True)).count(),
              "billed": q.filter(TimeEntry.invoice_id.isnot(None)).count(),
              "non_billable": q.filter(TimeEntry.billable.is_(False)).count(), "all": q.count()}
    if state == "unbilled":
        q = q.filter(TimeEntry.invoice_id.is_(None), TimeEntry.billable.is_(True))
    elif state == "billed":
        q = q.filter(TimeEntry.invoice_id.isnot(None))
    elif state == "non_billable":
        q = q.filter(TimeEntry.billable.is_(False))
    rows = q.order_by(TimeEntry.work_date.desc(), TimeEntry.id.desc()).limit(500).all()
    staff = User.query.filter_by(is_active_user=True).order_by(User.name).all()
    return render_template("timesheet/index.html", rows=rows, counts=counts, state=state, client_id=client_id, user_id=user_id,
                           from_date=request.args.get("from_date", ""), to_date=request.args.get("to_date", ""),
                           clients=visible_clients(g.user).order_by(Client.name).all(), staff=staff, my_rate=rate_for(g.user), today=date.today(),
                           hours=round(sum(r.hours or 0 for r in rows), 2), value=round(sum(r.value for r in rows if r.billable), 2),
                           can_bill=_can_bill(), rates={u.id: FirmSetting.get(f"rate_user_{u.id}") or "" for u in staff},
                           default_rate=FirmSetting.get("default_hourly_rate") or "0", tax_modes=bsvc.TAX_MODES)


@bp.route("/add", methods=["POST"])
@login_required
def add():
    f = request.form
    client = get_client_or_403(g.user, f.get("client_id", type=int) or 0)
    hours = to_float(f.get("hours"))
    minutes = to_float(f.get("minutes"))
    hours = round(hours + minutes / 60.0, 2)
    if hours <= 0 or hours > 24:
        flash("Enter the time spent (more than 0 and up to 24 hours).", "danger")
        return redirect(url_for("timesheet.index"))
    who = g.user
    if g.user.is_manager_or_above and f.get("user_id", type=int):
        who = db.session.get(User, f.get("user_id", type=int)) or g.user
    rate = to_float(f.get("rate"), -1)
    if rate < 0 or not (g.user.is_manager_or_above or _can_bill()):
        rate = rate_for(who, client)  # staff cannot set their own billing rate
    db.session.add(TimeEntry(client_id=client.id, user_id=who.id, work_date=parse_date(f.get("work_date")) or date.today(), hours=hours,
                             description=f.get("description", "").strip()[:300] or None, rate=rate, billable=f.get("billable", "1") == "1"))
    log_activity("timesheet", f"Logged {hours} hour(s) for {client.name}")
    db.session.commit()
    flash(f"{hours} hour(s) logged for {client.name}.", "success")
    return redirect(url_for("timesheet.index"))


@bp.route("/<int:tid>/delete", methods=["POST"])
@login_required
def delete(tid):
    t = db.get_or_404(TimeEntry, tid)
    if _query().filter(TimeEntry.id == t.id).first() is None:
        abort(403)
    if t.invoice_id:
        flash("This time is already on an invoice and cannot be deleted.", "danger")
    else:
        db.session.delete(t)
        db.session.commit()
        flash("Time entry deleted.", "success")
    return redirect(url_for("timesheet.index"))


@bp.route("/rates", methods=["POST"])
@login_required
def rates():
    if not (g.user.is_manager_or_above or _can_bill()):
        abort(403)
    FirmSetting.put("default_hourly_rate", str(max(0.0, to_float(request.form.get("default_hourly_rate")))))
    for u in User.query.all():
        raw = request.form.get(f"rate_{u.id}", "").strip()
        FirmSetting.put(f"rate_user_{u.id}", str(max(0.0, to_float(raw))) if raw else "")
    log_activity("timesheet", "Updated hourly billing rates")
    db.session.commit()
    flash("Hourly rates saved. They apply to time logged from now on.", "success")
    return redirect(url_for("timesheet.index") + "#rates")


@bp.route("/bill", methods=["POST"])
@login_required
def bill():
    """Turn a client's unbilled hours into an invoice: one line per entry, hours x rate."""
    if not _can_bill():
        abort(403)
    f = request.form
    client = get_client_or_403(g.user, f.get("client_id", type=int) or 0)
    upto = parse_date(f.get("upto")) or date.today()
    entries = (TimeEntry.query.filter(TimeEntry.client_id == client.id, TimeEntry.invoice_id.is_(None), TimeEntry.billable.is_(True),
                                      TimeEntry.work_date <= upto).order_by(TimeEntry.work_date, TimeEntry.id).all())
    entries = [e for e in entries if e.value > 0]
    if not entries:
        flash(f"{client.name} has no unbilled hours with a rate up to {upto:%d %b %Y}.", "warning")
        return redirect(url_for("timesheet.index", client_id=client.id))
    if f.get("style") == "summary":
        by_rate: dict[float, float] = {}
        for e in entries:
            by_rate[e.rate] = by_rate.get(e.rate, 0) + e.hours
        first, last = entries[0].work_date, entries[-1].work_date
        items = [{"description": f"Professional services ({first:%d %b %Y} to {last:%d %b %Y})", "quantity": round(h, 2), "rate": r, "sac_code": "998221"}
                 for r, h in sorted(by_rate.items())]
    else:
        items = [{"description": (f"{e.description or 'Professional services'} ({e.work_date:%d %b %Y}"
                                  + (f", {e.user.name}" if e.user else "") + ")")[:300], "quantity": e.hours, "rate": e.rate, "sac_code": "998221"} for e in entries]
    tax_mode = f.get("tax_mode") if f.get("tax_mode") in bsvc.TAX_MODES else "cgst_sgst"
    inv = bsvc.create_invoice(client.id, date.today(), None, tax_mode, items, 0.0, "Billed on time basis (hours x hourly rate).", g.user.id)
    for e in entries:
        e.invoice_id = inv.id
    log_activity("billing", f"Created invoice {inv.invoice_number} for {client.name} from {len(entries)} time entries")
    db.session.commit()
    flash(f"Invoice {inv.invoice_number} created from {len(entries)} time entries.", "success")
    return redirect(url_for("billing.show", invoice_id=inv.id))
