from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .. import log_activity, perms
from ..access import manager_required
from ..models import ROLES, Client, Task, User, db

bp = Blueprint("staff", __name__, url_prefix="/staff")


def _allowed_roles():
    """Admins/partners can create any role; managers can only create employees."""
    return list(ROLES) if g.user.is_admin_or_partner else ["employee"]


@bp.route("/")
@manager_required
def index():
    members = User.query.order_by(User.is_active_user.desc(), User.name).all()
    stats = {m.id: {"clients": Client.query.filter_by(assigned_to_id=m.id, archived=False).count(),
                    "open": Task.query.filter(Task.assigned_to_id == m.id, Task.status != "completed").count()} for m in members}
    return render_template("staff/index.html", members=members, stats=stats, roles={k: ROLES[k] for k in _allowed_roles()}, all_roles=ROLES)


@bp.route("/add", methods=["POST"])
@manager_required
def add():
    f = request.form
    name, email, pw = f.get("name", "").strip(), f.get("email", "").strip().lower(), f.get("password", "")
    role = f.get("role", "employee")
    if role not in _allowed_roles():
        abort(403)
    if not (name and "@" in email):
        flash("Name and a valid email are required.", "danger")
    elif len(pw) < 8:
        flash("The password must be at least 8 characters.", "danger")
    elif User.query.filter_by(email=email).first():
        flash("That email is already used by another account.", "danger")
    else:
        u = User(name=name, email=email, role=role, phone=f.get("phone", "").strip() or None,
                 designation=f.get("designation", "").strip() or None, employee_code=f.get("employee_code", "").strip() or None)
        u.set_password(pw)
        db.session.add(u)
        log_activity("staff", f"Added {ROLES[role]} {name}")
        db.session.commit()
        flash(f"{name} can now sign in.", "success")
    return redirect(url_for("staff.index"))


@bp.route("/<int:uid>/update", methods=["POST"])
@manager_required
def update(uid):
    u = db.get_or_404(User, uid)
    f = request.form
    # managers may only manage employees; nobody can lock out or demote themselves
    is_self = u.id == g.user.id
    if not is_self and not g.user.is_admin_or_partner and u.role != "employee":
        abort(403)
    new_role = f.get("role", u.role)
    if new_role != u.role and new_role not in _allowed_roles():
        abort(403)
    if is_self and (new_role != u.role or f.get("active") != "1"):
        flash("You cannot change your own role or switch off your own account.", "danger")
        return redirect(url_for("staff.index"))
    u.name = f.get("name", u.name).strip() or u.name
    u.role = new_role
    u.phone = f.get("phone", "").strip() or None
    u.designation = f.get("designation", "").strip() or None
    u.is_active_user = f.get("active") == "1"
    if f.get("password"):
        if len(f["password"]) < 8:
            flash("The new password must be at least 8 characters.", "danger")
            return redirect(url_for("staff.index"))
        u.set_password(f["password"])
    log_activity("staff", f"Updated account of {u.name}")
    db.session.commit()
    flash("Account updated.", "success")
    return redirect(url_for("staff.index"))


@bp.route("/permissions", methods=["GET", "POST"])
@manager_required
def permissions():
    """Tick which modules each person may open. Only admins and partners can change this; the Super Admin always has everything."""
    if not g.user.is_admin_or_partner:
        abort(403)
    members = User.query.order_by(User.is_active_user.desc(), User.name).all()
    if request.method == "POST":
        for m in members:
            if m.role == "super_admin" or m.id == g.user.id:
                continue  # cannot be locked out / cannot change your own access
            perms.save(m, request.form.getlist(f"perm_{m.id}"))
        log_activity("staff", "Updated user permissions")
        db.session.commit()
        flash("Permissions saved.", "success")
        return redirect(url_for("staff.permissions"))
    return render_template("staff/permissions.html", members=members, modules=perms.MODULES,
                           current={m.id: perms.effective(m) for m in members},
                           defaults={m.id: perms.role_default(m.role) for m in members})


@bp.route("/permissions/<int:uid>/reset", methods=["POST"])
@manager_required
def permissions_reset(uid):
    if not g.user.is_admin_or_partner:
        abort(403)
    u = db.get_or_404(User, uid)
    perms.save(u, list(perms.role_default(u.role)))
    db.session.commit()
    flash(f"{u.name} is back to the standard access for {u.role_label}.", "success")
    return redirect(url_for("staff.permissions"))
