"""
LAN access password persistence (Stage 16 sections 5 & 7).

Stores exactly one thing — a salted/hashed LAN access password — in the
pre-existing, previously-unused `ApplicationSetting` key/value table
(app/models/system.py, part of the original Stage 3 schema, created by
migration 0001_initial_schema.py). No new table, no new column, no new
migration: Stage 16's architecture reconnaissance found this table
already sitting in the schema, unused by any code, for exactly this
kind of single small local setting.

Hashing uses `werkzeug.security` (`generate_password_hash` /
`check_password_hash`) — Werkzeug is already an existing Flask
dependency (installed as of Flask's own requirement), so this
introduces no new package, per Section 5's explicit preference.

The plaintext password is never stored, never logged, and never
returned by any function in this module once set — only a boolean
match result comes back from `verify_password`.
"""
from __future__ import annotations

from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from app import extensions
from app.models.system import ApplicationSetting

_SETTING_KEY = "lan_access_password_hash"

# Section 6: "minimum sensible password length" — 8 is the common
# baseline minimum for a shared local-network access password; not
# configurable via environment variable, since this is a UX/validation
# rule, not a deployment setting.
MIN_PASSWORD_LENGTH = 8


def _session():
    """Re-reads `extensions.SessionLocal` on every call rather than
    binding it at import time — same reasoning as every other service
    module's `_session()` helper (see engagement_service.py): create_app()
    can run more than once per process (every pytest test does), and each
    call rebinds the module-level session factory to a fresh engine."""
    return extensions.SessionLocal()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def has_password_set() -> bool:
    """True once a LAN access password has been configured. Drives the
    first-run setup screen (Section 6) vs. the normal login gate
    (Section 8) — the LAN auth hook checks this on every request."""
    row = _session().get(ApplicationSetting, _SETTING_KEY)
    return row is not None and bool(row.setting_value)


def get_password_hash() -> str | None:
    """Returns the current stored hash string, or None if unset. Used
    as an opaque "which password was this session authenticated
    against" marker (see access_bp.py / lan_auth.py) — since the hash
    changes whenever set_password() is called, comparing against it is
    a simple, correct way to invalidate every other already-signed-in
    browser session the moment the password is changed (Section 28's
    natural expectation), with no separate version counter needed."""
    row = _session().get(ApplicationSetting, _SETTING_KEY)
    return row.setting_value if row is not None else None


def set_password(raw_password: str) -> None:
    """Used by both first-run setup and Settings > Change Password.
    Callers are responsible for length/confirmation validation first —
    this function only hashes and persists."""
    hashed = generate_password_hash(raw_password)
    session = _session()
    row = session.get(ApplicationSetting, _SETTING_KEY)
    if row is None:
        row = ApplicationSetting(setting_key=_SETTING_KEY)
        session.add(row)
    row.setting_value = hashed
    row.updated_at = _now_iso()
    session.commit()


def verify_password(raw_password: str) -> bool:
    """Constant-time-safe comparison via Werkzeug's own hash check.
    Returns False (never raises) if no password has been set yet, so
    callers don't need a separate has_password_set() check first."""
    row = _session().get(ApplicationSetting, _SETTING_KEY)
    if row is None or not row.setting_value:
        return False
    return check_password_hash(row.setting_value, raw_password)
