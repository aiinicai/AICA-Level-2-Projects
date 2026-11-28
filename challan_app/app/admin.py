from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from . import gst, services as sv
from .auth import admin_required
from .extensions import db
from .models import AuditLog, Plant, ROLES, SeriesConfig, User

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.before_request
@admin_required
def _only_admin():
    return None


# ------------------------------------------------------------ users
@bp.route("/users", methods=["GET", "POST"])
def users():
    if request.method == "POST":
        f = request.form
        uname = f.get("username", "").strip().lower()
        if not uname or not f.get("full_name", "").strip() or f.get("role") not in ROLES:
            flash("Username, full name and role are required.", "error")
        elif User.query.filter_by(username=uname).first():
            flash("That username already exists.", "error")
        elif len(f.get("password", "")) < 8:
            flash("Initial password must be at least 8 characters.", "error")
        else:
            u = User(username=uname, full_name=f["full_name"].strip(), role=f["role"],
                     password_hash=generate_password_hash(f["password"]), must_change_password=True)
            db.session.add(u)
            db.session.flush()
            sv.audit(g.user, "user", u.id, uname, "CREATE", f["role"])
            db.session.commit()
            flash(f"User {uname} created; they must change the password at first login.", "ok")
        return redirect(url_for("admin.users"))
    return render_template("admin/users.html", users=User.query.order_by(User.username).all(), roles=ROLES)


@bp.route("/users/<int:uid>", methods=["POST"])
def user_update(uid):
    u = db.get_or_404(User, uid)
    f = request.form
    if u.id == g.user.id and (f.get("role") != u.role or not f.get("active")):
        flash("You cannot change your own role or deactivate yourself.", "error")
        return redirect(url_for("admin.users"))
    if f.get("role") in ROLES:
        u.role = f["role"]
    u.active = bool(f.get("active"))
    if f.get("password"):
        if len(f["password"]) < 8:
            flash("Password must be at least 8 characters.", "error")
            return redirect(url_for("admin.users"))
        u.password_hash = generate_password_hash(f["password"])
        u.must_change_password = True
    sv.audit(g.user, "user", u.id, u.username, "UPDATE", f"role={u.role} active={u.active}")
    db.session.commit()
    flash("User updated.", "ok")
    return redirect(url_for("admin.users"))


# ------------------------------------------------------------ plants (consignor GSTINs)
@bp.route("/plants")
def plants():
    return render_template("admin/plants.html", plants=Plant.query.order_by(Plant.code).all())


@bp.route("/plants/<pid>", methods=["GET", "POST"])
def plant(pid):
    p = None if pid == "new" else db.get_or_404(Plant, int(pid))
    errs = []
    if request.method == "POST":
        f = {k: request.form.get(k, "").strip() for k in
             ("code", "company_name", "address", "pin", "gstin", "phone", "email", "signatory")}
        f["gstin"] = gst.norm_gstin(f["gstin"])
        errs = gst.validate_gstin(f["gstin"])
        for k in ("code", "company_name", "address"):
            if not f[k]:
                errs.append(f"{k.replace('_', ' ').title()} is required.")
        if not gst.PIN_RE.match(f["pin"]):
            errs.append("PIN must be 6 digits.")
        dup = Plant.query.filter(Plant.code == f["code"].upper()).first()
        if dup and (not p or dup.id != p.id):
            errs.append("Plant code already exists.")
        if not errs:
            if not p:
                p = Plant()
                db.session.add(p)
            for k, v in f.items():
                setattr(p, k, v or None)
            p.code = f["code"].upper()
            p.state_code = f["gstin"][:2]
            p.active = bool(request.form.get("active", "1" if pid == "new" else ""))
            db.session.flush()
            sv.audit(g.user, "plant", p.id, p.code, "SAVE", p.gstin)
            db.session.commit()
            flash("Plant saved.", "ok")
            return redirect(url_for("admin.plants"))
    return render_template("admin/plant_form.html", p=p, data=request.form if request.method == "POST" else (p.__dict__ if p else {}), errors=errs)


# ------------------------------------------------------------ numbering series
@bp.route("/series", methods=["GET", "POST"])
def series():
    if request.method == "POST":
        ct = request.form.get("ctype")
        cfg = db.get_or_404(SeriesConfig, ct)
        prefix = request.form.get("prefix", "").strip().upper()
        style = request.form.get("fy_style", "short")
        sep = request.form.get("separator", "/")
        pad = int(request.form.get("pad", 4) or 4)
        errs = sv.check_series_config(prefix, style, sep, pad)
        if errs:
            for e in errs:
                flash(e, "error")
        else:
            cfg.prefix, cfg.fy_style, cfg.separator, cfg.pad = prefix, style, sep, pad
            sv.audit(g.user, "series", None, ct, "CONFIG", f"{prefix} {style} {sep} {pad}")
            db.session.commit()
            flash("Numbering format saved. It applies to numbers issued from now on; issued numbers never change.", "ok")
        return redirect(url_for("admin.series"))
    rows = [(c, sv.format_number(c, gst.fy_of(__import__("datetime").date.today()), 1)) for c in SeriesConfig.query.all()]
    return render_template("admin/series.html", rows=rows)


# ------------------------------------------------------------ audit log
@bp.route("/audit")
def audit_log():
    q = AuditLog.query
    for k in ("entity", "username"):
        if request.args.get(k):
            q = q.filter(getattr(AuditLog, k) == request.args[k])
    if request.args.get("ref"):
        q = q.filter(AuditLog.ref.ilike(f"%{request.args['ref']}%"))
    return render_template("admin/audit.html", rows=q.order_by(AuditLog.id.desc()).limit(300).all(), a=request.args)
