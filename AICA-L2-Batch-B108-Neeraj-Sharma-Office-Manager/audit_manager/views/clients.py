import re

from flask import Blueprint, abort, flash, g, redirect, render_template, request, send_file, url_for
import io

from .. import log_activity
from ..access import get_client_or_403, login_required, manager_required, visible_clients
from ..models import Client, User, db
from ..services import imports

bp = Blueprint("clients", __name__, url_prefix="/clients")

PAN_RE = imports.PAN_RE
GSTIN_RE = imports.GSTIN_RE


def _staff_options():
    return User.query.filter_by(is_active_user=True).order_by(User.name).all()


def _designations() -> list[str]:
    from ..services import letterhead

    return letterhead.designations()


def _apply_form(client: Client, form) -> list[str]:
    errors = []
    name = form.get("name", "").strip()
    pan = form.get("pan", "").strip().upper()
    gstin = form.get("gstin", "").strip().upper()
    if gstin and not pan and GSTIN_RE.match(gstin):
        pan = gstin[2:12]  # the PAN is inside every GSTIN
    if not name:
        errors.append("Client name is required.")
    if pan and not PAN_RE.match(pan):
        errors.append("PAN must look like ABCDE1234F.")
    if gstin and not GSTIN_RE.match(gstin):
        errors.append("GSTIN is not in a valid format.")
    if pan:
        dup = Client.query.filter(Client.pan == pan, Client.archived.is_(False), Client.id != (client.id or 0)).first()
        if dup:
            errors.append(f"A client with PAN {pan} already exists ({dup.name}).")
    if errors:
        return errors
    client.name = name
    client.category = form.get("category") if form.get("category") in ("individual", "business") else "business"
    client.pan, client.gstin = pan or None, gstin or None
    client.tan = form.get("tan", "").strip().upper() or None
    client.email = form.get("email", "").strip() or None
    client.mobile = form.get("mobile", "").strip() or None
    client.address = form.get("address", "").strip() or None
    client.city = form.get("city", "").strip() or None
    client.state = form.get("state", "").strip() or None
    client.pincode = form.get("pincode", "").strip() or None
    client.status = form.get("status") if form.get("status") in ("active", "onboarding", "inactive") else "active"
    client.is_gst_registered = form.get("is_gst_registered") == "1" or bool(gstin)
    client.is_itr_applicable = form.get("is_itr_applicable") == "1"
    client.is_tds_applicable = form.get("is_tds_applicable") == "1"
    client.notes = form.get("notes", "").strip() or None
    client.contact_person = form.get("contact_person", "").strip()[:120] or None
    client.contact_designation = form.get("contact_designation", "").strip()[:80] or None
    if "hourly_rate" in form:
        try:
            rate = float(form.get("hourly_rate") or 0)
        except ValueError:
            rate = 0
        client.hourly_rate = rate if rate > 0 else None
    if g.user.is_manager_or_above:
        with db.session.no_autoflush:
            assigned = form.get("assigned_to_id", type=int)
            client.assigned_to_id = assigned if assigned and db.session.get(User, assigned) else None
            ids = {int(x) for x in form.getlist("staff_ids") if str(x).isdigit()}
            client.staff = User.query.filter(User.id.in_(ids)).all() if ids else []
    elif client.id is None:
        client.assigned_to_id = g.user.id  # an employee's new client is theirs
    return []


@bp.route("/")
@login_required
def index():
    q = visible_clients(g.user)
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    if search:
        like = f"%{search}%"
        q = q.filter(db.or_(Client.name.ilike(like), Client.pan.ilike(like), Client.gstin.ilike(like),
                            Client.client_code.ilike(like), Client.mobile.ilike(like)))
    if status in ("active", "onboarding", "inactive"):
        q = q.filter(Client.status == status)
    page = max(1, request.args.get("page", 1, type=int))
    pagination = q.order_by(Client.name).paginate(page=page, per_page=25, error_out=False)
    counts = dict(visible_clients(g.user).with_entities(Client.status, db.func.count()).group_by(Client.status).all())
    return render_template("clients/index.html", pagination=pagination, search=search, status=status, counts=counts)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    client = Client()
    if request.method == "POST":
        errors = _apply_form(client, request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
        else:
            with db.session.no_autoflush:
                client.client_code = imports.next_client_code()
            db.session.add(client)
            log_activity("clients", f"Added client {client.name}")
            db.session.commit()
            flash(f"Client {client.name} added.", "success")
            return redirect(url_for("clients.show", client_id=client.id))
    return render_template("clients/form.html", client=client, staff_options=_staff_options(), form=request.form, designations=_designations())


@bp.route("/<int:client_id>")
@login_required
def show(client_id):
    client = get_client_or_403(g.user, client_id)
    return render_template("clients/show.html", client=client, portals=PORTALS)


@bp.route("/<int:client_id>/edit", methods=["GET", "POST"])
@login_required
def edit(client_id):
    client = get_client_or_403(g.user, client_id)
    if request.method == "POST":
        errors = _apply_form(client, request.form)
        if errors:
            db.session.rollback()
            for e in errors:
                flash(e, "danger")
        else:
            log_activity("clients", f"Updated client {client.name}")
            db.session.commit()
            flash("Client updated.", "success")
            return redirect(url_for("clients.show", client_id=client.id))
    return render_template("clients/form.html", client=client, staff_options=_staff_options(), form=request.form, designations=_designations())


@bp.route("/<int:client_id>/archive", methods=["POST"])
@manager_required
def archive(client_id):
    client = db.get_or_404(Client, client_id)
    client.archived = True
    log_activity("clients", f"Archived client {client.name}")
    db.session.commit()
    flash(f"{client.name} was archived. Their records are kept.", "success")
    return redirect(url_for("clients.index"))


@bp.route("/import", methods=["GET", "POST"])
@manager_required
def import_page():
    result = None
    if request.method == "POST":
        upload = request.files.get("file")
        if not upload or not upload.filename.lower().endswith(".xlsx"):
            flash("Choose an Excel (.xlsx) file.", "danger")
        else:
            result = imports.import_clients(io.BytesIO(upload.read()), assign_to_id=request.form.get("assigned_to_id", type=int))
            log_activity("clients", f"Imported clients from Excel: {result['created']} added, {result['skipped']} skipped")
            db.session.commit()
    return render_template("clients/import.html", result=result, staff_options=_staff_options())


@bp.route("/import/template.xlsx")
@manager_required
def import_template():
    return send_file(io.BytesIO(imports.template_xlsx()), as_attachment=True, download_name="client_import_template.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ------------------------------------------------------------------ portal logins (passwords stored encrypted)
PORTALS = {
    "Income Tax e-Filing": "https://www.incometax.gov.in/iec/foportal/", "GST Portal": "https://services.gst.gov.in/services/login",
    "TRACES (TDS)": "https://www.tdscpc.gov.in/app/login.xhtml", "E-Way Bill": "https://ewaybillgst.gov.in/", "MCA": "https://www.mca.gov.in/",
    "EPFO": "https://unifiedportal-emp.epfindia.gov.in/epfo/", "ESIC": "https://www.esic.gov.in/", "Other": "",
}


@bp.route("/<int:client_id>/credentials", methods=["POST"])
@login_required
def credential_save(client_id):
    from ..models import ClientCredential
    from ..services import mailer

    client = get_client_or_403(g.user, client_id)
    f = request.form
    portal = f.get("portal", "").strip()[:60] or "Other"
    row = db.session.get(ClientCredential, f.get("id", type=int) or 0)
    if row is not None and row.client_id != client.id:
        abort(404)
    if row is None:
        row = ClientCredential(client_id=client.id)
        db.session.add(row)
    row.portal, row.username = portal, f.get("username", "").strip()[:160] or None
    row.notes = f.get("notes", "").strip()[:300] or None
    if f.get("password"):
        row.secret = mailer.encrypt_password(f["password"])
    log_activity("clients", f"Saved {portal} login for {client.name}")
    db.session.commit()
    flash(f"{portal} login saved.", "success")
    return redirect(url_for("clients.show", client_id=client.id) + "#logins")


@bp.route("/<int:client_id>/credentials/<int:cid>/reveal", methods=["POST"])
@login_required
def credential_reveal(client_id, cid):
    from flask import jsonify

    from ..models import ClientCredential
    from ..services import mailer

    client = get_client_or_403(g.user, client_id)
    row = db.get_or_404(ClientCredential, cid)
    if row.client_id != client.id:
        abort(404)
    log_activity("clients", f"Viewed the {row.portal} password of {client.name}")
    db.session.commit()
    return jsonify(ok=True, password=mailer._decrypt(row.secret) or "")


@bp.route("/<int:client_id>/credentials/<int:cid>/delete", methods=["POST"])
@login_required
def credential_delete(client_id, cid):
    from ..models import ClientCredential

    client = get_client_or_403(g.user, client_id)
    row = db.get_or_404(ClientCredential, cid)
    if row.client_id != client.id:
        abort(404)
    db.session.delete(row)
    log_activity("clients", f"Deleted the {row.portal} login of {client.name}")
    db.session.commit()
    flash("Login deleted.", "success")
    return redirect(url_for("clients.show", client_id=client.id) + "#logins")
