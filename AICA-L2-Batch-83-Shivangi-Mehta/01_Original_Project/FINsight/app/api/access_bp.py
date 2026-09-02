"""
LAN access gate — first-run password setup, login, sign-out
(Stage 16 sections 6, 8, 9, 27).

Reachable in local/dev mode too (the blueprint is always registered,
same as every other blueprint — Section 25's "share the same
application code"), but the before_request hook in
app/security/lan_auth.py only ever redirects here when
LAN_MODE_ENABLED is true, so in normal local development these routes
simply sit unused.
"""
from __future__ import annotations

from flask import Blueprint, redirect, render_template, request, session, url_for

from app.security import lan_auth
from app.services import lan_access_service

access_bp = Blueprint("access", __name__, url_prefix="/access")


def _safe_next_path(candidate: str | None) -> str:
    """Only ever redirect to a path within this application. Section 8
    ("do not reveal internal authentication details") extends naturally
    to not becoming an open redirect for an attacker-supplied `next`."""
    if not candidate:
        return url_for("dashboard.index")
    if not candidate.startswith("/") or candidate.startswith("//"):
        return url_for("dashboard.index")
    if "://" in candidate:
        return url_for("dashboard.index")
    return candidate


@access_bp.route("/setup", methods=["GET", "POST"])
def setup():
    # Defense in depth: once a password exists, this screen is not a
    # way to silently reset it without authenticating first — the
    # before_request hook already redirects unauthenticated requests
    # away from here once has_password_set() is true, but an already
    # authenticated LAN user landing here (e.g. a stale bookmark)
    # should be sent somewhere useful rather than re-shown "first run".
    if lan_access_service.has_password_set():
        return redirect(url_for("dashboard.index"))

    errors: dict[str, str] = {}
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(password) < lan_access_service.MIN_PASSWORD_LENGTH:
            errors["password"] = f"Password must be at least {lan_access_service.MIN_PASSWORD_LENGTH} characters."
        if not errors and password != confirm_password:
            errors["confirm_password"] = "Passwords do not match."

        if not errors:
            lan_access_service.set_password(password)
            session["lan_authenticated"] = True
            session["lan_auth_hash"] = lan_access_service.get_password_hash()
            lan_auth.record_successful_login()
            return render_template("access/setup_done.html")

    return render_template(
        "access/setup.html",
        errors=errors,
        min_length=lan_access_service.MIN_PASSWORD_LENGTH,
    )


@access_bp.route("/login", methods=["GET", "POST"])
def login():
    if lan_auth.is_authenticated():
        return redirect(url_for("dashboard.index"))

    next_path = _safe_next_path(request.args.get("next") or request.form.get("next"))
    from flask import current_app

    errors: dict[str, str] = {}
    locked, seconds_remaining = lan_auth.is_locked_out(current_app)

    if request.method == "POST":
        if locked:
            minutes_remaining = max(1, seconds_remaining // 60 + (1 if seconds_remaining % 60 else 0))
            errors["_login"] = f"Too many incorrect attempts. Please try again in about {minutes_remaining} minute(s)."
        else:
            password = request.form.get("password", "")
            # Section 8: a generic message either way — never reveal
            # whether a password was "close", and there is no username
            # to enumerate since this is a single shared password.
            if lan_access_service.verify_password(password):
                session["lan_authenticated"] = True
                session["lan_auth_hash"] = lan_access_service.get_password_hash()
                lan_auth.record_successful_login()
                return redirect(next_path)
            lan_auth.record_failed_attempt(current_app)
            errors["_login"] = "Incorrect password. Please try again."

    return render_template("access/login.html", errors=errors, next_path=next_path, locked=locked)


@access_bp.route("/logout", methods=["POST"])
def logout():
    # Always exempt from the access gate (app/security/lan_auth.py) and
    # always safe to call even on an already-signed-out or stale
    # (hash-mismatched) session — clearing keys that may not be present
    # is a no-op, not an error.
    session.pop("lan_authenticated", None)
    session.pop("lan_auth_hash", None)
    return redirect(url_for("access.login"))
