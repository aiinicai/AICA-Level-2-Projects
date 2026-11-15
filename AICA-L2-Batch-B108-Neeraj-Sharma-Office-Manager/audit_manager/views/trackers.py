from datetime import date

import io

from flask import Blueprint, abort, flash, g, redirect, render_template, request, send_file, url_for

from .. import log_activity, parse_date, to_float
from ..access import get_client_or_403, login_required, manager_required, visible_client_ids, visible_clients
from ..models import Client, GstReturn, GstReturnType, ItrFiling, TdsReturn, User, db
from ..services import compliance as comp
from ..services import imports

bp = Blueprint("trackers", __name__)

MODELS = {"gst": GstReturn, "itr": ItrFiling, "tds": TdsReturn}


def _fy_options() -> list[str]:
    y = date.today().year
    return [f"{s}-{str(s + 1)[2:]}" for s in range(y - 1, y + 2)]


def _staff():
    return User.query.filter_by(is_active_user=True).order_by(User.name).all()


def _listing(model, **extra):
    ids = visible_client_ids(g.user)
    q = model.query.filter(model.client_id.in_(ids))
    status = request.args.get("status", "")
    client_id = request.args.get("client_id", type=int)
    if status == "overdue":
        q = q.filter(model.status != "filed", model.due_date < date.today())
    elif status:
        q = q.filter(model.status == status)
    if client_id:
        q = q.filter(model.client_id == client_id)
    base = model.query.filter(model.client_id.in_(ids))
    if client_id:
        base = base.filter(model.client_id == client_id)
    counts = dict(base.with_entities(model.status, db.func.count()).group_by(model.status).all())
    counts["overdue"] = base.filter(model.status != "filed", model.due_date < date.today()).count()
    counts["all"] = base.count()
    g.status_counts = counts
    return q, status, client_id


def _mark_filed(row, form) -> bool:
    """Applies the form. Returns True when this change is what made the return Filed."""
    was = row.status
    row.status = form.get("status") if form.get("status") in comp.RETURN_STATUSES else row.status
    row.filed_date = parse_date(form.get("filed_date")) or (date.today() if row.status == "filed" and not row.filed_date else row.filed_date)
    if row.status != "filed":
        row.filed_date = parse_date(form.get("filed_date"))
    row.assigned_to_id = form.get("assigned_to_id", type=int) or None
    new_due = parse_date(form.get("due_date"))
    if new_due:
        row.due_date = new_due  # e.g. the department extended the date for this client
    return row.status == "filed" and was != "filed"


def _announce(row, label: str, work: str = "") -> None:
    from ..services import automation

    automation.fire("return_filed", client=row.client, values={"period": label, "work_type": work}, user_id=g.user.id)


# ------------------------------------------------------------------ GST
@bp.route("/gst")
@login_required
def gst():
    q, status, client_id = _listing(GstReturn)
    rows = q.order_by(GstReturn.due_date).limit(500).all()
    return render_template("trackers/gst.html", rows=rows, status=status, client_id=client_id, statuses=comp.RETURN_STATUSES,
                           types=GstReturnType.query.filter_by(active=True).all(),
                           clients=visible_clients(g.user).filter(Client.is_gst_registered.is_(True)).order_by(Client.name).all(),
                           staff=_staff())


@bp.route("/gst/add", methods=["POST"])
@login_required
def gst_add():
    client = get_client_or_403(g.user, request.form.get("client_id", type=int) or 0)
    rt = db.get_or_404(GstReturnType, request.form.get("return_type_id", type=int) or 0)
    period = request.form.get("period", "").strip()
    if not comp.valid_gst_period(rt, period):
        flash(f"Period for {rt.name} must look like {'2026-10' if rt.frequency == 'monthly' else '2026-Q3' if rt.frequency == 'quarterly' else '2025'}.", "danger")
    elif GstReturn.query.filter_by(client_id=client.id, return_type_id=rt.id, period=period).first():
        flash("That return is already being tracked for this client.", "warning")
    else:
        db.session.add(GstReturn(client_id=client.id, return_type_id=rt.id, period=period,
                                 due_date=parse_date(request.form.get("due_date")) or comp.gst_due_date(rt, period),
                                 assigned_to_id=client.assigned_to_id))
        log_activity("gst", f"Added {rt.name} {period} for {client.name}")
        db.session.commit()
        flash("GST return added.", "success")
    return redirect(url_for("trackers.gst"))


@bp.route("/gst/<int:rid>/update", methods=["POST"])
@login_required
def gst_update(rid):
    row = db.get_or_404(GstReturn, rid)
    get_client_or_403(g.user, row.client_id)
    if _mark_filed(row, request.form):
        _announce(row, f"{row.return_type.name} for {row.period}", "GST Return")
    row.arn = request.form.get("arn", "").strip() or None
    log_activity("gst", f"Updated {row.return_type.name} {row.period} for {row.client.name}: {row.status}")
    db.session.commit()
    flash("GST return updated.", "success")
    return redirect(request.referrer or url_for("trackers.gst"))


@bp.route("/gst/bulk", methods=["POST"])
@manager_required
def gst_bulk():
    rt = db.get_or_404(GstReturnType, request.form.get("return_type_id", type=int) or 0)
    period = request.form.get("period", "").strip()
    if not comp.valid_gst_period(rt, period):
        flash("Enter the period in the right format, for example 2026-10.", "danger")
    else:
        created, skipped = comp.bulk_gst(visible_clients(g.user), rt, period)
        log_activity("gst", f"Bulk created {rt.name} {period}: {created} added, {skipped} already existed")
        db.session.commit()
        flash(f"{rt.name} {period}: {created} created for GST-registered clients, {skipped} already existed.", "success")
    return redirect(url_for("trackers.gst"))


# ------------------------------------------------------------------ ITR
@bp.route("/itr")
@login_required
def itr():
    q, status, client_id = _listing(ItrFiling)
    return render_template("trackers/itr.html", rows=q.order_by(ItrFiling.due_date).limit(500).all(), status=status, client_id=client_id, verify=comp.ITR_VERIFY,
                           statuses=comp.RETURN_STATUSES, forms=comp.ITR_FORMS, staff=_staff(),
                           clients=visible_clients(g.user).order_by(Client.name).all(), ay_default=f"{date.today().year}-{str(date.today().year + 1)[2:]}")


@bp.route("/itr/add", methods=["POST"])
@login_required
def itr_add():
    client = get_client_or_403(g.user, request.form.get("client_id", type=int) or 0)
    ay, form_type = request.form.get("assessment_year", "").strip(), request.form.get("form_type", "ITR-1")
    if not (len(ay) == 7 and ay[4] == "-" and ay[:4].isdigit()):
        flash("Assessment year must look like 2026-27.", "danger")
    elif ItrFiling.query.filter_by(client_id=client.id, assessment_year=ay, form_type=form_type).first():
        flash("That filing is already tracked for this client.", "warning")
    else:
        db.session.add(ItrFiling(client_id=client.id, assessment_year=ay, form_type=form_type,
                                 due_date=parse_date(request.form.get("due_date")) or comp.itr_due_date(ay),
                                 assigned_to_id=client.assigned_to_id))
        log_activity("itr", f"Added {form_type} AY {ay} for {client.name}")
        db.session.commit()
        flash("ITR filing added.", "success")
    return redirect(url_for("trackers.itr"))


@bp.route("/itr/<int:rid>/update", methods=["POST"])
@login_required
def itr_update(rid):
    row = db.get_or_404(ItrFiling, rid)
    get_client_or_403(g.user, row.client_id)
    if _mark_filed(row, request.form):
        _announce(row, f"Income Tax Return ({row.form_type}) for AY {row.assessment_year}", "Income Tax Return")
    row.ack_number = request.form.get("ack_number", "").strip() or None
    row.refund_amount = to_float(request.form.get("refund_amount"))
    if "verification_status" in request.form:
        v = request.form.get("verification_status", "")
        row.verification_status = v if v in comp.ITR_VERIFY and v else None
        row.verification_date = parse_date(request.form.get("verification_date")) if row.verification_status else None
        if row.verification_status and not row.verification_date:
            row.verification_date = date.today()
    log_activity("itr", f"Updated {row.form_type} AY {row.assessment_year} for {row.client.name}: {row.status}")
    db.session.commit()
    flash("ITR filing updated.", "success")
    return redirect(url_for("trackers.itr"))


@bp.route("/itr/bulk", methods=["POST"])
@manager_required
def itr_bulk():
    ay, form_type = request.form.get("assessment_year", "").strip(), request.form.get("form_type", "ITR-1")
    if not (len(ay) == 7 and ay[4] == "-" and ay[:4].isdigit()):
        flash("Assessment year must look like 2026-27.", "danger")
    else:
        created, skipped = comp.bulk_itr(visible_clients(g.user), ay, form_type, parse_date(request.form.get("due_date")))
        log_activity("itr", f"Bulk created {form_type} AY {ay}: {created} added, {skipped} already existed")
        db.session.commit()
        flash(f"{form_type} AY {ay}: {created} created for ITR-applicable clients, {skipped} already existed.", "success")
    return redirect(url_for("trackers.itr"))


# ------------------------------------------------------------------ TDS
@bp.route("/tds")
@login_required
def tds():
    q, status, client_id = _listing(TdsReturn)
    return render_template("trackers/tds.html", rows=q.order_by(TdsReturn.due_date).limit(500).all(), status=status, client_id=client_id,
                           statuses=comp.RETURN_STATUSES, forms=comp.TDS_FORMS, quarters=comp.QUARTERS, fys=_fy_options(), staff=_staff(),
                           clients=visible_clients(g.user).filter(Client.is_tds_applicable.is_(True)).order_by(Client.name).all())


@bp.route("/tds/add", methods=["POST"])
@login_required
def tds_add():
    client = get_client_or_403(g.user, request.form.get("client_id", type=int) or 0)
    fy, q, form_type = request.form.get("financial_year", ""), request.form.get("quarter", ""), request.form.get("form_type", "26Q")
    if q not in comp.QUARTERS or form_type not in comp.TDS_FORMS or not fy:
        flash("Choose a financial year, quarter and form.", "danger")
    elif TdsReturn.query.filter_by(client_id=client.id, financial_year=fy, quarter=q, form_type=form_type).first():
        flash("That return is already tracked for this client.", "warning")
    else:
        db.session.add(TdsReturn(client_id=client.id, financial_year=fy, quarter=q, form_type=form_type,
                                 due_date=parse_date(request.form.get("due_date")) or comp.tds_due_date(fy, q),
                                 assigned_to_id=client.assigned_to_id))
        log_activity("tds", f"Added {form_type} {fy} {q} for {client.name}")
        db.session.commit()
        flash("TDS return added.", "success")
    return redirect(url_for("trackers.tds"))


@bp.route("/tds/<int:rid>/update", methods=["POST"])
@login_required
def tds_update(rid):
    row = db.get_or_404(TdsReturn, rid)
    get_client_or_403(g.user, row.client_id)
    if _mark_filed(row, request.form):
        _announce(row, f"TDS return {row.form_type} {row.quarter} FY {row.financial_year}", "TDS Return")
    row.tds_deducted = to_float(request.form.get("tds_deducted"))
    row.tds_deposited = to_float(request.form.get("tds_deposited"))
    row.challan_number = request.form.get("challan_number", "").strip() or None
    if "ack_number" in request.form:
        row.ack_number = request.form.get("ack_number", "").strip() or None
    log_activity("tds", f"Updated {row.form_type} {row.financial_year} {row.quarter} for {row.client.name}: {row.status}")
    db.session.commit()
    flash("TDS return updated.", "success")
    return redirect(url_for("trackers.tds"))


@bp.route("/tds/bulk", methods=["POST"])
@manager_required
def tds_bulk():
    fy, q, form_type = request.form.get("financial_year", ""), request.form.get("quarter", ""), request.form.get("form_type", "26Q")
    if q not in comp.QUARTERS or form_type not in comp.TDS_FORMS or not fy:
        flash("Choose a financial year, quarter and form.", "danger")
    else:
        created, skipped = comp.bulk_tds(visible_clients(g.user), fy, q, form_type)
        log_activity("tds", f"Bulk created {form_type} {fy} {q}: {created} added, {skipped} already existed")
        db.session.commit()
        flash(f"{form_type} {fy} {q}: {created} created for TDS-applicable clients, {skipped} already existed.", "success")
    return redirect(url_for("trackers.tds"))


@bp.route("/trackers/<kind>/<int:rid>/delete", methods=["POST"])
@manager_required
def tracker_delete(kind, rid):
    model = MODELS.get(kind) or abort(404)
    row = db.get_or_404(model, rid)
    log_activity(kind, f"Deleted a {kind.upper()} tracker row for {row.client.name}")
    db.session.delete(row)
    db.session.commit()
    flash("Row deleted.", "success")
    return redirect(url_for(f"trackers.{kind}"))


# ------------------------------------------------------------------ Excel import of filings
KIND_TITLES = {"gst": "GST returns (monthly and quarterly)", "itr": "ITR filings", "tds": "TDS returns (quarterly)"}


@bp.route("/trackers/import/<kind>", methods=["GET", "POST"])
@manager_required
def import_filings(kind):
    if kind not in MODELS:
        abort(404)
    result = None
    if request.method == "POST":
        upload = request.files.get("file")
        if not upload or not upload.filename:
            flash("Choose an Excel file first.", "danger")
        else:
            result = imports.import_filings(kind, upload.stream, visible_clients(g.user))
            log_activity(kind, f"Imported {kind.upper()} filings from Excel: {result['created']} added, {result['updated']} updated, {len(result['errors'])} problems")
            db.session.commit()
    return render_template("trackers/import.html", kind=kind, title=KIND_TITLES[kind], result=result, columns=imports.FILING_COLUMNS[kind],
                           help_lines=imports.FILING_HELP[kind])


@bp.route("/trackers/import/<kind>/template.xlsx")
@manager_required
def import_template(kind):
    if kind not in MODELS:
        abort(404)
    return send_file(io.BytesIO(imports.filing_template(kind)), as_attachment=True, download_name=f"{kind}-filings-template.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ------------------------------------------------------------------ due date extended by the department
@bp.route("/trackers/extend/<kind>", methods=["POST"])
@manager_required
def extend_due(kind):
    """Move the due date of every return of one kind and period that is not yet filed (for the clients this user can see)."""
    if kind not in MODELS:
        abort(404)
    f = request.form
    new_date = parse_date(f.get("new_date"))
    back = {"gst": "trackers.gst", "itr": "trackers.itr", "tds": "trackers.tds"}[kind]
    if not new_date:
        flash("Choose the new due date.", "danger")
        return redirect(url_for(back))
    model = MODELS[kind]
    q = model.query.filter(model.client_id.in_(visible_client_ids(g.user)), model.status != "filed")
    if kind == "gst":
        rt = db.get_or_404(GstReturnType, f.get("return_type_id", type=int) or 0)
        period = f.get("period", "").strip().upper()
        q, label = q.filter(GstReturn.return_type_id == rt.id, GstReturn.period == period), f"{rt.name} {period}"
    elif kind == "itr":
        ay = f.get("assessment_year", "").strip()
        q, label = q.filter(ItrFiling.assessment_year == ay), f"ITR AY {ay}"
        if f.get("form_type") in comp.ITR_FORMS:
            q, label = q.filter(ItrFiling.form_type == f["form_type"]), f"{f['form_type']} AY {ay}"
    else:
        fy, quarter = f.get("financial_year", "").strip(), f.get("quarter", "").strip().upper()
        q, label = q.filter(TdsReturn.financial_year == fy, TdsReturn.quarter == quarter), f"TDS {quarter} FY {fy}"
        if f.get("form_type") in comp.TDS_FORMS:
            q = q.filter(TdsReturn.form_type == f["form_type"])
    rows = q.all()
    for r in rows:
        r.due_date = new_date
    log_activity(kind, f"Extended due date of {label} to {new_date:%d %b %Y} for {len(rows)} unfiled return(s)")
    db.session.commit()
    flash(f"{label}: due date changed to {new_date:%d %b %Y} for {len(rows)} return(s) not yet filed." if rows
          else f"No unfiled {label} returns were found, so nothing changed.", "success" if rows else "warning")
    return redirect(url_for(back))
