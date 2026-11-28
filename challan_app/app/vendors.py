from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, url_for
from sqlalchemy import or_

from . import gst, services as sv
from .auth import approver_required, admin_required
from .extensions import db
from .models import Challan, Vendor

bp = Blueprint("vendors", __name__)


def _vendor_dict(v):
    return {"id": v.id, "vendor_no": v.vendor_no, "name": v.name, "gstin": v.gstin or "",
            "state_code": v.state_code, "state": gst.STATES.get(v.state_code, ""), "erp_code": v.erp_code or ""}


@bp.route("/vendors")
def list_():
    q = request.args.get("q", "").strip()
    erp = request.args.get("erp", "")
    query = Vendor.query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Vendor.name.ilike(like), Vendor.vendor_no.ilike(like), Vendor.gstin.ilike(like),
                                 Vendor.erp_code.ilike(like)))
    if erp == "yes":
        query = query.filter(Vendor.erp_code.isnot(None))
    elif erp == "no":
        query = query.filter(Vendor.erp_code.is_(None))
    page = max(int(request.args.get("page", 1) or 1), 1)
    total = query.count()
    rows = query.order_by(Vendor.vendor_no).offset((page - 1) * 50).limit(50).all()
    return render_template("vendors/list.html", rows=rows, q=q, erp=erp, page=page, total=total)


@bp.route("/api/vendors/search")
def search():
    q = request.args.get("q", "").strip()
    query = Vendor.query.filter_by(active=True)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Vendor.name.ilike(like), Vendor.vendor_no.ilike(like), Vendor.gstin.ilike(like)))
    return jsonify([_vendor_dict(v) for v in query.order_by(Vendor.name).limit(15)])


def _form_vendor(v=None, data=None, errors=None, warnings=None, similar=None):
    return render_template("vendors/form.html", v=v, data=data or {}, errors=errors or [],
                           warnings=warnings or [], similar=similar or [])


@bp.route("/vendors/new", methods=["GET", "POST"])
def new():
    if request.method == "GET":
        return _form_vendor(data={"name": request.args.get("name", "")})
    data = request.form
    c, errs = sv.clean_vendor(data)
    clash, similar = sv.find_vendor_duplicates(c["name"], c["gstin"])
    if clash:
        errs.append(f"GSTIN already exists in the master as {clash.vendor_no} - {clash.name}.")
    if errs:
        return _form_vendor(data=data, errors=errs, similar=similar)
    if similar and not data.get("confirm_similar"):
        return _form_vendor(data=data, similar=similar, warnings=[
            "Similar vendor name(s) already exist. Tick the confirmation box if this is genuinely a different vendor."])
    v = sv.create_vendor(c, g.user)
    db.session.commit()
    flash(f"Vendor {v.vendor_no} created.", "ok")
    return redirect(url_for("vendors.view", vid=v.id))


@bp.route("/api/vendors/quick-add", methods=["POST"])
def quick_add():
    """Used by the challan form when the typed vendor is not in the master."""
    data = request.get_json(silent=True) or {}
    c, errs = sv.clean_vendor(data)
    clash, similar = sv.find_vendor_duplicates(c["name"], c["gstin"])
    if clash:
        errs.append(f"GSTIN already exists in the master as {clash.vendor_no} - {clash.name}.")
    if errs:
        return jsonify(ok=False, errors=errs), 200
    if similar and not data.get("confirm_similar"):
        return jsonify(ok=False, needs_confirm=True, similar=[_vendor_dict(v) for v in similar]), 200
    v = sv.create_vendor(c, g.user)
    db.session.commit()
    return jsonify(ok=True, vendor=_vendor_dict(v))


@bp.route("/vendors/<int:vid>")
def view(vid):
    v = db.get_or_404(Vendor, vid)
    ch = Challan.query.filter_by(vendor_id=vid).order_by(Challan.challan_date.desc()).limit(50).all()
    return render_template("vendors/view.html", v=v, challans=ch)


@bp.route("/vendors/<int:vid>/edit", methods=["GET", "POST"])
@approver_required
def edit(vid):
    v = db.get_or_404(Vendor, vid)
    if request.method == "GET":
        return _form_vendor(v=v, data=v.__dict__)
    c, errs = sv.clean_vendor(request.form, exclude_id=vid)
    clash, similar = sv.find_vendor_duplicates(c["name"], c["gstin"], exclude_id=vid)
    if clash:
        errs.append(f"GSTIN already used by {clash.vendor_no} - {clash.name}.")
    if errs:
        return _form_vendor(v=v, data=request.form, errors=errs)
    if similar and not request.form.get("confirm_similar") and gst.normalize_name(c["name"]) != v.name_norm:
        return _form_vendor(v=v, data=request.form, similar=similar, warnings=[
            "Similar vendor name(s) exist. Tick the box to confirm."])
    old = {k: getattr(v, k) for k in c}
    for k, val in c.items():
        setattr(v, k, val)
    v.name_norm = gst.normalize_name(v.name)
    sv.audit(g.user, "vendor", v.id, v.vendor_no, "EDIT", sv.diff_text(old, c))
    db.session.commit()
    flash("Vendor updated. (Challans already finalised keep the details they were issued with.)", "ok")
    return redirect(url_for("vendors.view", vid=v.id))


@bp.route("/vendors/<int:vid>/erp", methods=["POST"])
def erp(vid):
    v = db.get_or_404(Vendor, vid)
    try:
        sv.set_erp_code(v, request.form.get("erp_code"), g.user)
        db.session.commit()
        flash("ERP vendor code saved." if v.erp_code else "ERP vendor code cleared.", "ok")
    except ValueError as e:
        db.session.rollback()
        flash(str(e), "error")
    return redirect(url_for("vendors.view", vid=vid))


@bp.route("/vendors/<int:vid>/toggle", methods=["POST"])
@admin_required
def toggle(vid):
    v = db.get_or_404(Vendor, vid)
    v.active = not v.active
    sv.audit(g.user, "vendor", v.id, v.vendor_no, "ACTIVATE" if v.active else "DEACTIVATE")
    db.session.commit()
    return redirect(url_for("vendors.view", vid=vid))
