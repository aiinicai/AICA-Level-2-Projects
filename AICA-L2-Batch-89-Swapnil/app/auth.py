"""Login, server-side sessions, lockout, password policy, TOTP, PAN encryption."""
from __future__ import annotations

import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from cryptography.fernet import Fernet, InvalidToken
from flask import (Blueprint, current_app, flash, g, redirect, render_template, request, session, url_for)
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from sqlalchemy import func, select

from . import audit
from .models import LoginAttempt, User, UserSession, db, utcnow

bp = Blueprint("auth", __name__)
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please sign in."
login_manager.session_protection = None      # sessions are validated server-side instead

_ph = PasswordHasher()                        # argon2id with library defaults
_COMMON = {ln.strip().lower() for ln in (Path(__file__).parent / "common_passwords.txt")
           .read_text(encoding="utf-8").splitlines() if ln.strip()}
_rate: dict[str, deque] = defaultdict(deque)
IST = timezone(timedelta(hours=5, minutes=30))


# ------------------------------------------------------------------ helpers
def hash_password(pw: str) -> str:
    return _ph.hash(pw)


def check_password(user: User, pw: str) -> bool:
    try:
        _ph.verify(user.password_hash, pw)
    except (VerificationError, InvalidHashError):
        return False
    if _ph.check_needs_rehash(user.password_hash):
        user.password_hash = _ph.hash(pw)
    return True


def password_problems(pw: str, username: str) -> list[str]:
    out = []
    if len(pw) < 12:
        out.append("Use at least 12 characters.")
    if pw.lower() in _COMMON:
        out.append("That password is on the list of commonly used passwords.")
    if username and username.lower() in pw.lower():
        out.append("The password must not contain your username.")
    return out


def fernet() -> Fernet:
    return Fernet(current_app.config["FERNET_KEY"].encode())


def encrypt(value: str | None) -> str | None:
    return fernet().encrypt(value.encode()).decode() if value else None


def decrypt(token: str | None) -> str | None:
    if not token:
        return None
    try:
        return fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return None


def mask_pan(pan: str | None) -> str:
    return f"{pan[:5]}****{pan[-1]}" if pan and len(pan) == 10 else "—"


def actor() -> audit.Actor:
    ip = request.remote_addr if request else None
    ua = request.headers.get("User-Agent") if request else None
    if current_user and current_user.is_authenticated:
        return audit.Actor(current_user.id, current_user.full_name, current_user.role, ip, ua)
    return audit.Actor(None, "anonymous", "ANONYMOUS", ip, ua)


def today():
    fixed = current_app.config.get("AS_OF")
    return fixed or datetime.now(IST).date()


def totp_required(user: User) -> bool:
    from .services import get_setting
    return user.role in ("OWNER", "PARTNER") and bool(get_setting("totp_required_for_partners"))


# --------------------------------------------------------------- sessions
@login_manager.user_loader
def load_user(token: str):
    s = db.session.get(UserSession, token)
    now = utcnow()
    cfg = current_app.config
    if s is None or s.revoked_at or now > s.expires_at or now - s.last_seen_at > cfg["SESSION_IDLE"]:
        return None
    user = s.user
    if not user.is_active:
        return None
    if (now - s.last_seen_at).total_seconds() > 60:
        s.last_seen_at = now
        db.session.commit()
    user.session_token = s.id
    g.user_session = s
    return user


def start_session(user: User, mfa_passed: bool) -> UserSession:
    now = utcnow()
    s = UserSession(id=secrets.token_urlsafe(32), user_id=user.id, created_at=now, last_seen_at=now,
                    expires_at=now + current_app.config["SESSION_ABSOLUTE"], mfa_passed=mfa_passed,
                    ip=request.remote_addr, user_agent=(request.headers.get("User-Agent") or "")[:255])
    db.session.add(s)
    return s


def _rate_limited(ip: str) -> bool:
    limit, window = current_app.config["LOGIN_RATE_LIMIT"]
    q, now = _rate[ip], time.monotonic()
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        return True
    q.append(now)
    return False


def _fail(username: str, reason: str, user: User | None = None):
    s = db.session
    s.add(LoginAttempt(username=username[:64], success=False, reason=reason, ip=request.remote_addr))
    a = audit.Actor(user.id if user else None, user.full_name if user else username[:120] or "?",
                    user.role if user else "ANONYMOUS", request.remote_addr, request.headers.get("User-Agent"))
    audit.record(s, a, "LOGIN_FAILED", "user", user.id if user else username[:64], after={"reason": reason})


# ------------------------------------------------------------------ gates
EXEMPT = {"auth.login", "auth.logout", "auth.change_password", "auth.totp", "auth.totp_setup", "static"}


@bp.before_app_request
def gate():
    if not current_user.is_authenticated or request.endpoint in EXEMPT:
        return None
    s = g.get("user_session")
    if s is not None and not s.mfa_passed:
        return redirect(url_for("auth.totp"))
    if current_user.must_change_password:
        return redirect(url_for("auth.change_password"))
    if totp_required(current_user) and not current_user.totp_enabled:
        return redirect(url_for("auth.totp_setup"))
    return None


# ------------------------------------------------------------------ routes
@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("auth.html", mode="login")
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    generic = "Username or password is incorrect."
    if _rate_limited(request.remote_addr or "?"):
        _fail(username, "rate limited")
        db.session.commit()
        flash("Too many sign-in attempts from this computer. Wait a minute and try again.", "danger")
        return render_template("auth.html", mode="login", username=username), 429
    user = db.session.execute(select(User).where(func.lower(User.username) == username.lower())).scalar()
    now = utcnow()
    if user is None:
        _fail(username, "unknown user")
        db.session.commit()
        flash(generic, "danger")
        return render_template("auth.html", mode="login", username=username), 401
    if not user.is_active:
        _fail(username, "deactivated", user)
        db.session.commit()
        flash("This account has been deactivated. Contact the owner.", "danger")
        return render_template("auth.html", mode="login", username=username), 403
    if user.locked_until and user.locked_until > now:
        _fail(username, "locked", user)
        db.session.commit()
        until = user.locked_until.replace(tzinfo=timezone.utc).astimezone(IST)
        flash(f"This account is locked until {until:%H:%M} after repeated wrong passwords. "
              "The owner can unlock it sooner.", "danger")
        return render_template("auth.html", mode="login", username=username), 423
    if not check_password(user, password):
        user.failed_count += 1
        _fail(username, f"wrong password ({user.failed_count})", user)
        if user.failed_count >= current_app.config["LOCKOUT_THRESHOLD"]:
            user.locked_until = now + current_app.config["LOCKOUT_PERIOD"]
            audit.record(db.session, audit.Actor(user.id, user.full_name, user.role, request.remote_addr),
                         "ACCOUNT_LOCKED", "user", user.id, after={"until": user.locked_until})
            db.session.commit()
            flash("Too many wrong passwords: this account is now locked for 15 minutes.", "danger")
            return render_template("auth.html", mode="login", username=username), 423
        db.session.commit()
        flash(generic, "danger")
        return render_template("auth.html", mode="login", username=username), 401
    user.failed_count, user.locked_until, user.last_login_at = 0, None, now
    s = start_session(user, mfa_passed=not user.totp_enabled)
    db.session.add(LoginAttempt(username=username, success=True, ip=request.remote_addr))
    audit.record(db.session, audit.Actor(user.id, user.full_name, user.role, request.remote_addr,
                                         request.headers.get("User-Agent")), "LOGIN", "user", user.id)
    db.session.commit()
    session.clear()
    user.session_token = s.id
    login_user(user)
    if user.totp_enabled:
        return redirect(url_for("auth.totp"))
    return redirect(url_for("dashboard.index"))


@bp.route("/logout", methods=["POST"])
def logout():
    s = g.get("user_session")
    if s is not None:
        s.revoked_at = utcnow()
        audit.record(db.session, actor(), "LOGOUT", "user", current_user.id)
        db.session.commit()
    logout_user()
    session.clear()
    flash("Signed out.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        cur, new, again = (request.form.get(k) or "" for k in ("current", "new", "again"))
        problems = []
        if not check_password(current_user, cur):
            problems.append("Your current password is not correct.")
        if new != again:
            problems.append("The two new passwords do not match.")
        if new == cur:
            problems.append("Choose a password different from the current one.")
        problems += password_problems(new, current_user.username)
        if problems:
            for p in problems:
                flash(p, "danger")
            return render_template("auth.html", mode="change"), 422
        current_user.password_hash = hash_password(new)
        current_user.must_change_password = False
        # end every other session of this user
        for other in db.session.execute(select(UserSession).where(
                UserSession.user_id == current_user.id, UserSession.id != current_user.session_token,
                UserSession.revoked_at.is_(None))).scalars():
            other.revoked_at = utcnow()
        audit.record(db.session, actor(), "PASSWORD_CHANGED", "user", current_user.id)
        db.session.commit()
        flash("Password changed.", "success")
        return redirect(url_for("dashboard.index"))
    return render_template("auth.html", mode="change")


@bp.route("/totp", methods=["GET", "POST"])
@login_required
def totp():
    s = g.get("user_session")
    if s is None or s.mfa_passed:
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        secret = decrypt(current_user.totp_secret_enc)
        if secret and pyotp.TOTP(secret).verify(request.form.get("code", "").strip(), valid_window=1):
            s.mfa_passed = True
            audit.record(db.session, actor(), "TOTP_PASSED", "user", current_user.id)
            db.session.commit()
            return redirect(url_for("dashboard.index"))
        audit.record(db.session, actor(), "TOTP_FAILED", "user", current_user.id)
        db.session.commit()
        flash("That code is not valid. Check the time on your phone and try again.", "danger")
        return render_template("auth.html", mode="totp"), 401
    return render_template("auth.html", mode="totp")


@bp.route("/totp/setup", methods=["GET", "POST"])
@login_required
def totp_setup():
    if request.method == "POST":
        secret = session.get("totp_pending")
        if secret and pyotp.TOTP(secret).verify(request.form.get("code", "").strip(), valid_window=1):
            current_user.totp_secret_enc = encrypt(secret)
            current_user.totp_enabled = True
            session.pop("totp_pending", None)
            audit.record(db.session, actor(), "TOTP_ENROLLED", "user", current_user.id)
            db.session.commit()
            flash("Two-factor sign-in is now on for your account.", "success")
            return redirect(url_for("dashboard.index"))
        flash("That code is not valid. Try again with the current code from your app.", "danger")
    secret = session.get("totp_pending") or pyotp.random_base32()
    session["totp_pending"] = secret
    uri = pyotp.TOTP(secret).provisioning_uri(name=current_user.username, issuer_name="MCA Compliance Mapper")
    return render_template("auth.html", mode="totp_setup", secret=secret, uri=uri, required=totp_required(current_user))
