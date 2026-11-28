from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from sqlalchemy import or_

from . import gst, services as sv
from .auth import admin_required, approver_required
from .extensions import db
from .models import CANCELLED, DRAFT, FINAL, MNRC, MRC, Challan, ChallanLine, Plant, SeriesConfig, Vendor, now

bp = Blueprint("challans", __name__)


def _get(cid):
    return db.get_or_404(Challan, cid)


@bp.route("/challans")
def list_():
    a = request.args
    q = Challan.query.join(Vendor)
    if a.get("q"):
        like = f"%{a['q'].strip()}%"
        q = q.filter(or_(Challan.number.ilike(like), Vendor.name.ilike(like), Vendor.vendor_no.ilike(like),
                         Challan.ewb_no.ilike(like)))
    if a.get("ctype") in (MRC, MNRC):
        q = q.filter(Challan.ctype == a["ctype"])
    if a.get("status") in (DRAFT, FINAL, CANCELLED):
        q = q.filter(Challan.status == a["status"])
    if a.get("vendor_id", "").isdigit():
        q = q.filter(Challan.vendor_id == int(a["vendor_id"]))
    if a.get("part"):
        q = q.filter(Challan.lines.any(ChallanLine.part_no.ilike(f"%{a['part'].strip()}%")))
    if a.get("ewb") in ("Pending", "Updated"):
        q = q.filter(Challan.ewb_status == a["ewb"], Challan.status == FINAL)
    if a.get("ret") in ("Open", "Partially Received", "Closed"):
        q = q.filter(Challan.return_status == a["ret"])
    for k, op in (("from", ">="), ("to", "<=")):
        d = sv._date(a.get(k))
        if d:
            q = q.filter(Challan.challan_date >= d if op == ">=" else Challan.challan_date <= d)
    if not g.user.is_approver and a.get("mine"):
        q = q.filter(Challan.created_by == g.user.username)
    page = int(a["page"]) if a.get("page", "").isdigit() and int(a["page"]) > 0 else 1
    total = q.count()
    rows = (q.order_by(Challan.challan_date.desc(), Challan.id.desc()).offset((page - 1) * 50).limit(50).all())
    from urllib.parse import urlencode
    qs = urlencode({k: v for k, v in a.items() if v and k != "page"})
    return render_template("challans/list.html", rows=rows, a=a, page=page, total=total, qs=qs)


# ------------------------------------------------------------------ create / edit
def _lines_from_form(form):
    keys = ("part_no", "description", "hsn", "qty", "uom", "rate", "tax_rate", "cess_rate")
    cols = {k: form.getlist(k) for k in keys}
    n = max((len(v) for v in cols.values()), default=0)
    return [{k: (cols[k][i] if i < len(cols[k]) else "") for k in keys} for i in range(n)]


def _lines_from_challan(ch):
    return [{"part_no": l.part_no, "description": l.description, "hsn": l.hsn, "qty": f"{l.qty:g}",
             "uom": l.uom, "rate": f"{l.rate:.2f}", "tax_rate": f"{l.tax_rate:g}", "cess_rate": f"{l.cess_rate:g}"}
            for l in ch.lines]


def _header_from_challan(ch):
    d = {k: getattr(ch, k) for k in sv.HEADER_FIELDS}
    return {k: ("" if v is None else v) for k, v in d.items()}


def _render_form(ctype, ch=None, data=None, lines=None, errors=None):
    cfg = db.session.get(SeriesConfig, ctype)
    return render_template(
        "challans/form.html", ctype=ctype, cfg=cfg, ch=ch, data=data or {}, lines=lines or [{}],
        errors=errors or [], plants=Plant.query.filter_by(active=True).order_by(Plant.code).all(),
        purposes=sv.purposes_for(ctype), modes=sv.TRANSPORT_MODES, uoms=sv.UOMS,
        lines_locked=bool(ch and ch.receipts),
        vendor=(db.session.get(Vendor, int(data["vendor_id"])) if data and str(data.get("vendor_id", "")).isdigit() else None))


@bp.route("/challans/new/<ctype>", methods=["GET", "POST"])
def new(ctype):
    if ctype not in (MRC, MNRC):
        abort(404)
    if request.method == "GET":
        plant = Plant.query.filter_by(active=True).order_by(Plant.code).first()
        return _render_form(ctype, data={"challan_date": date.today().isoformat(),
                                         "plant_id": plant.id if plant else ""})
    h, lines, errs = sv.parse_challan_form(request.form, ctype, g.user)
    if not errs:
        ch = Challan(ctype=ctype, status=DRAFT, created_by=g.user.username)
        try:
            sv.apply_challan(ch, h, lines)
            db.session.add(ch)
            db.session.flush()
            sv.audit(g.user, "challan", ch.id, ch.display_no, "CREATE", f"{ctype} draft")
            if request.form.get("action") == "final":
                sv.finalize(ch, g.user)
            db.session.commit()
            flash(f"Challan {ch.number} issued." if ch.number else "Draft saved (no number assigned yet).", "ok")
            return redirect(url_for("challans.view", cid=ch.id))
        except ValueError as e:
            db.session.rollback()
            errs = [str(e)]
    return _render_form(ctype, data=request.form, lines=_lines_from_form(request.form), errors=errs)


@bp.route("/challans/<int:cid>/edit", methods=["GET", "POST"])
def edit(cid):
    ch = _get(cid)
    if not sv.can_edit(ch, g.user):
        flash("This challan can no longer be edited by you (finalised challans need Admin rights).", "error")
        return redirect(url_for("challans.view", cid=cid))
    locked = bool(ch.receipts)
    if request.method == "GET":
        return _render_form(ch.ctype, ch=ch, data=_header_from_challan(ch), lines=_lines_from_challan(ch))
    h, lines, errs = sv.parse_challan_form(request.form, ch.ctype, g.user, lines_locked=locked)
    if not errs:
        try:
            before = sv.header_snapshot(ch)
            sv.apply_challan(ch, h, lines, lines_locked=locked)
            ch.updated_by = g.user.username
            if ch.status == FINAL:
                sv.take_snapshots(ch)
            db.session.flush()
            sv.audit(g.user, "challan", ch.id, ch.display_no, "EDIT", sv.diff_text(before, sv.header_snapshot(ch)))
            if ch.status == DRAFT and request.form.get("action") == "final":
                sv.finalize(ch, g.user)
            db.session.commit()
            flash("Challan saved.", "ok")
            return redirect(url_for("challans.view", cid=cid))
        except ValueError as e:
            db.session.rollback()
            errs = [str(e)]
    return _render_form(ch.ctype, ch=ch, data=request.form, lines=_lines_from_form(request.form) if not locked else _lines_from_challan(ch), errors=errs)


@bp.route("/challans/<int:cid>/finalize", methods=["POST"])
def finalize(cid):
    ch = _get(cid)
    if not sv.can_edit(ch, g.user) or ch.status != DRAFT:
        abort(403)
    try:
        sv.finalize(ch, g.user)
        db.session.commit()
        flash(f"Challan {ch.number} issued.", "ok")
    except ValueError as e:
        db.session.rollback()
        flash(str(e), "error")
    return redirect(url_for("challans.view", cid=cid))


@bp.route("/challans/<int:cid>/delete", methods=["POST"])
def delete(cid):
    ch = _get(cid)
    if ch.status != DRAFT or not sv.can_edit(ch, g.user):
        abort(403)
    sv.audit(g.user, "challan", ch.id, ch.display_no, "DELETE_DRAFT")
    db.session.delete(ch)
    db.session.commit()
    flash("Draft deleted. (No number had been used.)", "ok")
    return redirect(url_for("challans.list_"))


# ------------------------------------------------------------------ view + follow-up actions
@bp.route("/challans/<int:cid>")
def view(cid):
    ch = _get(cid)
    history = (sv.AuditLog.query.filter_by(entity="challan", entity_id=cid).order_by(sv.AuditLog.id.desc()).all())
    return render_template("challans/view.html", ch=ch, history=history, can_edit=sv.can_edit(ch, g.user),
                           consignee=sv.consignee(ch), consignor=sv.consignor(ch), cfg=db.session.get(SeriesConfig, ch.ctype))


def _action(cid, fn, ok_msg):
    ch = _get(cid)
    try:
        fn(ch)
        db.session.commit()
        flash(ok_msg, "ok")
    except ValueError as e:
        db.session.rollback()
        flash(str(e), "error")
    return redirect(url_for("challans.view", cid=cid))


@bp.route("/challans/<int:cid>/ewb", methods=["POST"])
def ewb(cid):
    return _action(cid, lambda ch: sv.update_ewb(ch, request.form, g.user), "E-way bill details saved.")


@bp.route("/challans/<int:cid>/ewb/clear", methods=["POST"])
@admin_required
def ewb_clear(cid):
    def f(ch):
        sv.audit(g.user, "challan", ch.id, ch.number, "EWB_CLEAR", ch.ewb_no or "")
        ch.ewb_no = ch.ewb_date = ch.ewb_valid_upto = None
        ch.ewb_status = "Pending"
    return _action(cid, f, "E-way bill details cleared (status back to Pending).")


@bp.route("/challans/<int:cid>/receipt", methods=["POST"])
def receipt(cid):
    return _action(cid, lambda ch: sv.record_receipt(ch, request.form, g.user), "Receipt recorded.")


@bp.route("/challans/<int:cid>/corrective", methods=["POST"])
@approver_required
def corrective(cid):
    return _action(cid, lambda ch: sv.update_corrective(ch, request.form, g.user), "Corrective action updated.")


@bp.route("/challans/<int:cid>/cancel", methods=["POST"])
@approver_required
def cancel(cid):
    return _action(cid, lambda ch: sv.cancel_challan(ch, request.form.get("reason"), g.user), "Challan cancelled. Its number is retained.")


# ------------------------------------------------------------------ printing
COPIES = [("Original for Consignee", "ORIGINAL"), ("Duplicate for Transporter", "DUPLICATE"),
          ("Triplicate for Consignor", "TRIPLICATE")]


@bp.route("/challans/<int:cid>/print")
def print_(cid):
    ch = _get(cid)
    if ch.status == DRAFT:
        flash("Drafts cannot be printed - issue the challan (assign its number) first.", "error")
        return redirect(url_for("challans.view", cid=cid))
    which = request.args.get("copy", "all")
    copies = COPIES if which == "all" else [c for c in COPIES if c[1] == which.upper()] or COPIES
    if request.args.get("mark", "1") == "1":
        ch.print_count = (ch.print_count or 0) + 1
        ch.printed_at = ch.printed_at or now()
        sv.audit(g.user, "challan", ch.id, ch.number, "PRINT", f"{which}")
        db.session.commit()
    cs = sv.consignor(ch)
    cee = sv.consignee(ch)
    labels = gst.tax_labels(cs["state_code"])
    import os
    from flask import current_app
    logo = os.path.exists(os.path.join(current_app.static_folder, "logo.png"))
    return render_template("challans/print.html", ch=ch, copies=copies, cs=cs, cee=cee, labels=labels,
                           cfg=db.session.get(SeriesConfig, ch.ctype), words=gst.amount_in_words(ch.grand_total),
                           logo=logo)

