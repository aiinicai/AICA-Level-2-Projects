"""
LAN access gate (Stage 16 sections 4, 8, 9, 11, 15, 24).

A single before_request hook, active ONLY when
`app.config["LAN_MODE_ENABLED"]` is True — flipped by wsgi_lan.py right
after create_app(), never by run.py's local/dev launcher (see that
file's own comment). Local development at 127.0.0.1 is therefore
completely unaffected by any of this by default, per Section 25 ("do
not break normal local mode") — both modes run the exact same
application code, only this one config flag differs.

Uses the existing Flask session (already used since Stage 5 for
`current_engagement_id` and since Stage 15 for the CSRF token) to hold
one boolean, `lan_authenticated` — no new session mechanism, and no
per-user accounts (Section 4: a single shared access password, not
individual accounts, is the explicit V1 design).

Brute-force lockout state (Section 11) is kept in memory, per source
IP, in this module's own process-local dict — deliberately NOT written
to the database or to logs, so a failed attempt (or the password that
produced it) is never persisted anywhere. This means lockouts reset if
the LAN server process restarts: a disclosed, accepted V1 limitation,
not an oversight (see documentation/stage16_lan_mode.md, Known
Limitations).
"""
from __future__ import annotations

import socket
import time

from flask import Flask, redirect, request, session, url_for

from app.services import lan_access_service

# Endpoints always reachable, LAN mode or not: the static asset route
# (the login/setup pages need their own CSS), the health check
# (Section 24's explicit allowed exception — no client data in it), and
# sign-out itself — Section 27 requires Sign Out to always work and
# always clear local state, including for a session whose stored hash
# has gone stale (e.g. Settings > Security changed the password on
# another device while this one was still signed in). If logout were
# gated like an ordinary route, that exact case would redirect the
# sign-out attempt to the login page instead of ever clearing the
# session — the bug this comment is here to prevent regressing.
_ALWAYS_EXEMPT_ENDPOINTS = frozenset({"static", "health", "access.logout"})

# In-memory only — see module docstring. Keyed by remote IP.
_lockouts: dict[str, dict[str, float]] = {}


def _client_key() -> str:
    return request.remote_addr or "unknown"


def is_locked_out(app: Flask) -> tuple[bool, int]:
    """Returns (locked, seconds_remaining)."""
    entry = _lockouts.get(_client_key())
    if entry is None:
        return False, 0
    remaining = entry.get("locked_until", 0.0) - time.time()
    if remaining <= 0:
        return False, 0
    return True, int(remaining) + 1


def record_failed_attempt(app: Flask) -> None:
    key = _client_key()
    entry = _lockouts.setdefault(key, {"failed_count": 0.0, "locked_until": 0.0})
    entry["failed_count"] += 1
    max_attempts = app.config.get("LAN_MAX_LOGIN_ATTEMPTS", 5)
    if entry["failed_count"] >= max_attempts:
        lockout_seconds = app.config.get("LAN_LOGIN_LOCKOUT_SECONDS", 300)
        entry["locked_until"] = time.time() + lockout_seconds
        entry["failed_count"] = 0  # next window starts clean once the lockout itself is the deterrent


def record_successful_login() -> None:
    _lockouts.pop(_client_key(), None)


def is_authenticated() -> bool:
    """The single source of truth for "is this browser session currently
    signed in", used by the gate itself, by access_bp.login()'s own
    already-signed-in shortcut, and by the base.html Sign Out
    context-processor value (app/__init__.py). Checking the bare
    `lan_authenticated` flag alone is NOT enough: a session authenticated
    under a password that has since been changed (Section 28) must count
    as signed OUT, so every one of these three call sites must agree —
    an earlier version of this code checked the bare flag in one place
    and the hash-matched version in another, which let a stale session
    skip the login form entirely. Centralized here so that can't
    reoccur."""
    return bool(session.get("lan_authenticated")) and session.get("lan_auth_hash") == lan_access_service.get_password_hash()


def get_local_lan_ip() -> str | None:
    """Section 15: local-only OS route lookup. A UDP 'connect' to a
    deliberately non-routable address (RFC 5737 doesn't apply here —
    10.255.255.255 is simply an address nothing on a normal LAN owns)
    sends no actual packet for a connectionless socket; it only asks
    the OS which local interface/address it would use to reach that
    subnet, which is exactly the host's own LAN-facing IP. No external
    service is contacted. Returns None (never raises) if detection
    isn't possible in this environment, per Section 15's "do not block
    startup because IP detection fails"."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0.5)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def init_lan_access_gate(app: Flask) -> None:
    @app.before_request
    def _enforce_lan_access():
        if not app.config.get("LAN_MODE_ENABLED"):
            return None
        if request.endpoint in _ALWAYS_EXEMPT_ENDPOINTS:
            return None

        if not lan_access_service.has_password_set():
            # First-run: only the setup screen itself is reachable.
            if request.endpoint == "access.setup":
                return None
            return redirect(url_for("access.setup"))

        # A password exists — normal operation. The setup screen no
        # longer accepts anonymous access once configured (its own view
        # also re-checks this, as defense in depth); login is the gate.
        if request.endpoint == "access.login":
            return None
        # Section 28: changing the password (Settings > Security) must
        # invalidate every other already-signed-in browser session, not
        # just the one that changed it — is_authenticated()'s hash
        # comparison makes that automatic: a session authenticated under
        # the old password simply stops matching the moment the hash
        # changes.
        if is_authenticated():
            return None
        return redirect(url_for("access.login", next=request.path))
