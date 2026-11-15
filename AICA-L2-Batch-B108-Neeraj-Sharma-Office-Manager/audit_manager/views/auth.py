from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from .. import clear_failed_logins, log_activity, record_failed_login, throttled
from ..access import login_required
from ..models import FirmSetting, User, db

bp = Blueprint("auth", __name__)


@bp.route("/setup", methods=["GET", "POST"])
def setup():
    """First run only: create the firm and its first Super Admin. No default passwords ship with the app."""
    if User.query.count() > 0:
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        f = request.form
        name, email, firm = f.get("name", "").strip(), f.get("email", "").strip().lower(), f.get("firm_name", "").strip()
        pw, pw2 = f.get("password", ""), f.get("password2", "")
        error = None
        if not (name and email and firm):
            error = "Firm name, your name and your email are required."
        elif len(pw) < 8:
            error = "Choose a password of at least 8 characters."
        elif pw != pw2:
            error = "The two passwords do not match."
        if error:
            flash(error, "danger")
        else:
            user = User(name=name, email=email, role="super_admin")
            user.set_password(pw)
            db.session.add(user)
            FirmSetting.put("firm_name", firm)
            FirmSetting.put("invoice_prefix", "INV")
            db.session.commit()
            flash("Setup complete. Please sign in.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/setup.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        key = f"{request.remote_addr}|{email}"
        if throttled(key):
            flash("Too many failed attempts. Wait 10 minutes and try again.", "danger")
            return render_template("auth/login.html"), 429
        user = User.query.filter_by(email=email).first()
        if user and user.is_active_user and user.check_password(request.form.get("password", "")):
            clear_failed_logins(key)
            session.clear()
            session["uid"] = user.id
            session.permanent = True
            g.user = user
            log_activity("auth", f"{user.name} signed in")
            db.session.commit()
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("dashboard.index"))
        record_failed_login(key)
        flash("Wrong email or password, or the account is switched off.", "danger")
    return render_template("auth/login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@bp.route("/account/password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        cur, new, new2 = (request.form.get(k, "") for k in ("current", "new", "new2"))
        if not g.user.check_password(cur):
            flash("Your current password is wrong.", "danger")
        elif len(new) < 8:
            flash("The new password must be at least 8 characters.", "danger")
        elif new != new2:
            flash("The two new passwords do not match.", "danger")
        else:
            g.user.set_password(new)
            log_activity("auth", f"{g.user.name} changed their password")
            db.session.commit()
            flash("Password changed.", "success")
            return redirect(url_for("dashboard.index"))
    return render_template("auth/password.html")


@bp.route("/account/theme", methods=["POST"])
@login_required
def set_theme():
    from .. import THEMES

    choice = request.form.get("theme", "navy")
    if choice in THEMES:
        FirmSetting.put(f"theme_user_{g.user.id}", choice)
        db.session.commit()
    return redirect(request.referrer or url_for("dashboard.index"))
