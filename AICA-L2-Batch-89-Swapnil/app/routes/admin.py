from __future__ import annotations

import csv
import io
import secrets
import string
from datetime import date, datetime, timedelta

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import select

from .. import audit
from ..auth import actor, hash_password
from ..models import ROLES, AuditLog, User, UserSession, db, utcnow
from ..permissions import require
from ..services import DEFAULT_SETTINGS, get_setting, set_setting

bp = Blueprint("admin", __name__, url_prefix="/admin")


def temp_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "-".join("".join(secrets.choice(alphabet) for _ in range(5)) for _ in range(3))


def _user(user_id: int) -> User:
    u = db.session.get(User, user_id)
    if u is None:
        abort(404)
    return u


# ------------------------------------------------------------------- users
@bp.route("/users", methods=["GET", "POST"])
@require("manage_users")
def users():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip().lower()
        role = request.form.get("role")
        name = (request.form.get("full_name") or "").strip()
        if not username or not name or role not in ROLES:
            flash("Enter a username, full name and role.", "danger")
        elif db.session.execute(select(User).where(User.username == username)).scalar():
            flash("That username is taken.", "danger")
        else:
            pw = temp_password()
            u = User(username=username, full_name=name, role=role, email=request.form.get("email") or None,
                     password_hash=hash_password(pw), must_change_password=True)
            db.session.add(u)
            db.session.flush()
            audit.record(db.session, actor(), "USER_CREATED", "user", u.id, after={"username": username, "role": role})
            db.session.commit()
            flash(f"User {username} created. Temporary password (shown once): {pw}", "warning")
        return redirect(url_for("admin.users"))
    rows = db.session.execute(select(User).order_by(User.is_active_flag.desc(), User.full_name)).scalars().all()
    sessions = db.session.execute(select(UserSession).where(UserSession.revoked_at.is_(None),
                                                            UserSession.expires_at > utcnow()).order_by(
        UserSession.last_seen_at.desc())).scalars().all()
    return render_template("admin.html", mode="users", users=rows, roles=ROLES, sessions=sessions, now=utcnow())


@bp.route("/users/<int:user_id>/<action>", methods=["POST"])
@require("manage_users")
def user_action(user_id: int, action: str):
    u = _user(user_id)
    before = {"role": u.role, "active": u.is_active_flag, "locked_until": u.locked_until}
    if action == "unlock":
        u.failed_count, u.locked_until = 0, None
        flash(f"{u.username} unlocked.", "success")
    elif action == "reset":
        pw = temp_password()
        u.password_hash, u.must_change_password, u.failed_count, u.locked_until = hash_password(pw), True, 0, None
        flash(f"Temporary password for {u.username} (shown once): {pw}", "warning")
    elif action in ("deactivate", "activate"):
        if u.id == current_user.id:
            flash("You cannot deactivate your own account.", "danger")
            return redirect(url_for("admin.users"))
        u.is_active_flag = action == "activate"
        if action == "deactivate":
            for s in db.session.execute(select(UserSession).where(UserSession.user_id == u.id,
                                                                  UserSession.revoked_at.is_(None))).scalars():
                s.revoked_at = utcnow()
        flash(f"{u.username} {'re-activated' if u.is_active_flag else 'deactivated'} (never deleted: the audit trail keeps the name).", "success")
    elif action == "role":
        role = request.form.get("role")
        if role not in ROLES or u.id == current_user.id:
            flash("Choose a valid role (you cannot change your own role).", "danger")
            return redirect(url_for("admin.users"))
        u.role = role
        flash(f"{u.username} is now {role}.", "success")
    elif action == "reset_totp":
        u.totp_enabled, u.totp_secret_enc = False, None
        flash(f"Two-factor sign-in reset for {u.username}.", "success")
    else:
        abort(404)
    audit.record(db.session, actor(), f"USER_{action.upper()}", "user", u.id, before=before,
                 after={"role": u.role, "active": u.is_active_flag, "locked_until": u.locked_until})
    db.session.commit()
    return redirect(url_for("admin.users"))


@bp.route("/sessions/<sid>/revoke", methods=["POST"])
@require("manage_users")
def revoke_session(sid: str):
    s = db.session.get(UserSession, sid)
    if s is None:
        abort(404)
    s.revoked_at = utcnow()
    audit.record(db.session, actor(), "SESSION_REVOKED", "session", sid[:8], after={"user_id": s.user_id})
    db.session.commit()
    flash("Session revoked.", "success")
    return redirect(url_for("admin.users"))


# ------------------------------------------------------------------- audit
def _audit_query():
    q = select(AuditLog)
    a = request.args
    if a.get("entity_id"):
        q = q.where(AuditLog.entity_id == int(a["entity_id"]))
    if a.get("user"):
        q = q.where(AuditLog.actor_name.ilike(f"%{a['user']}%"))
    if a.get("action"):
        q = q.where(AuditLog.action == a["action"].upper())
    if a.get("from"):
        q = q.where(AuditLog.ts >= a["from"])
    if a.get("to"):
        q = q.where(AuditLog.ts < (date.fromisoformat(a["to"]) + timedelta(days=1)).isoformat())
    return q.order_by(AuditLog.id.desc())


@bp.route("/audit")
@require("read_audit")
def audit_trail():
    rows = db.session.execute(_audit_query().limit(300)).scalars().all()
    actions = [r[0] for r in db.session.execute(select(AuditLog.action).distinct().order_by(AuditLog.action))]
    return render_template("audit.html", rows=rows, actions=actions, args=request.args)


@bp.route("/audit.csv")
@require("read_audit")
def audit_csv():
    rows = db.session.execute(_audit_query()).scalars().all()
    buf = io.StringIO()
    w = csv.writer(buf)
    cols = ["id", "ts", "actor_name", "actor_role", "action", "object_type", "object_id", "entity_id",
            "before_json", "after_json", "ip", "prev_hash", "row_hash"]
    w.writerow(cols)
    for r in rows:
        w.writerow([getattr(r, c) for c in cols])
    audit.record(db.session, actor(), "AUDIT_EXPORTED", "audit_log", None, after={"rows": len(rows)})
    db.session.commit()
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=audit_{date.today():%Y%m%d}.csv"})


@bp.route("/audit/verify", methods=["POST"])
@require("settings")
def audit_verify():
    rep = audit.verify_chain(db.session)
    audit.record(db.session, actor(), "AUDIT_CHAIN_VERIFIED", "audit_log", None,
                 after={"ok": rep.ok, "rows": rep.rows, "broken_id": rep.broken_id})
    db.session.commit()
    flash(rep.message, "success" if rep.ok else "danger")
    return redirect(url_for("admin.audit_trail"))


# ---------------------------------------------------------------- settings
EDITABLE = ["firm_name", "firm_tagline", "firm_address", "firm_phone", "firm_email", "firm_signatory", "show_logo", "srn_regex", "totp_required_for_partners",
            "adt1_for_first_auditor", "retention_years", "brand_primary", "brand_accent"]


@bp.route("/settings", methods=["GET", "POST"])
@require("settings")
def settings():
    if request.method == "POST":
        import re
        for k in EDITABLE:
            default = DEFAULT_SETTINGS[k]
            if isinstance(default, bool):
                v = request.form.get(k) == "on"
            elif isinstance(default, int):
                try:
                    v = int(request.form.get(k) or default)
                except ValueError:
                    flash(f"{k.replace('_', ' ').capitalize()} must be a whole number.", "danger")
                    return redirect(url_for("admin.settings"))
            else:
                v = (request.form.get(k) or "").strip()
            if k == "srn_regex":
                try:
                    re.compile(v)
                except re.error:
                    flash("The SRN pattern is not a valid regular expression.", "danger")
                    return redirect(url_for("admin.settings"))
            if k.startswith("brand_") and not re.fullmatch(r"#[0-9a-fA-F]{6}", v):
                flash("Colours must be hex values like #1f3a5f.", "danger")
                return redirect(url_for("admin.settings"))
            if v != get_setting(k):
                set_setting(k, v, actor())
        db.session.commit()
        flash("Settings saved.", "success")
        return redirect(url_for("admin.settings"))
    return render_template("admin.html", mode="settings", values={k: get_setting(k) for k in EDITABLE}, defaults=DEFAULT_SETTINGS)
