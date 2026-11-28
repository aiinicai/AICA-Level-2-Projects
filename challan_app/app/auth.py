import secrets
from functools import wraps

from flask import (Blueprint, abort, flash, g, jsonify, redirect, render_template, request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db
from .models import ADMIN, APPROVER, User, now
from .services import audit

bp = Blueprint("auth", __name__)
PUBLIC = {"auth.login", "static"}


def login_required(f):
    return f      # enforced globally in before_request; kept for readability


def roles_required(*roles):
    def deco(f):
        @wraps(f)
        def wrapper(*a, **kw):
            if g.user.role not in roles:
                abort(403)
            return f(*a, **kw)
        return wrapper
    return deco


admin_required = roles_required(ADMIN)
approver_required = roles_required(APPROVER, ADMIN)


def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


@bp.app_context_processor
def _inject():
    return {"csrf_token": csrf_token, "current_user": g.get("user")}


@bp.app_errorhandler(403)
def _403(e):
    return render_template("error.html", code=403, msg="You do not have permission to do that."), 403


@bp.app_errorhandler(404)
def _404(e):
    return render_template("error.html", code=404, msg="Page not found."), 404


@bp.before_app_request
def _gate():
    g.user = None
    uid = session.get("uid")
    if uid:
        u = db.session.get(User, uid)
        if u and u.active:
            g.user = u
        else:
            session.clear()
    if request.method == "POST":
        tok = request.form.get("_csrf") or request.headers.get("X-CSRF-Token")
        if not tok or tok != session.get("_csrf"):
            abort(400, "Security token missing or expired - go back, refresh the page and try again.")
    if request.endpoint in PUBLIC or request.endpoint is None:
        return None
    if not g.user:
        return redirect(url_for("auth.login", next=request.path))
    if g.user.must_change_password and request.endpoint not in ("auth.change_password", "auth.logout"):
        return redirect(url_for("auth.change_password"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(username=request.form.get("username", "").strip().lower()).first()
        if u and u.active and check_password_hash(u.password_hash, request.form.get("password", "")):
            session.clear()
            session["uid"] = u.id
            session.permanent = True
            audit(u, "user", u.id, u.username, "LOGIN")
            db.session.commit()
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("dashboard.index"))
        flash("Wrong username or password.", "error")
    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@bp.route("/password", methods=["GET", "POST"])
def change_password():
    if request.method == "POST":
        cur, new, new2 = (request.form.get(k, "") for k in ("current", "new", "new2"))
        if not check_password_hash(g.user.password_hash, cur):
            flash("Current password is wrong.", "error")
        elif len(new) < 8:
            flash("New password must be at least 8 characters.", "error")
        elif new != new2:
            flash("The two new passwords do not match.", "error")
        elif new == cur:
            flash("Choose a different password.", "error")
        else:
            g.user.password_hash = generate_password_hash(new)
            g.user.must_change_password = False
            audit(g.user, "user", g.user.id, g.user.username, "PASSWORD")
            db.session.commit()
            flash("Password changed.", "ok")
            return redirect(url_for("dashboard.index"))
    return render_template("password.html")
