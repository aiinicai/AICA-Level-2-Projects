"""
FinSight application configuration.

Stage 2 (skeleton) scope only: paths, feature-flag defaults, and the
values needed for the app factory to boot. No business logic lives here.

Every default below reflects an already-approved Stage 1 decision — do not
change a default here to "make something work" without flagging it back,
per the standing instruction not to make silent architectural changes.
"""
import os
import sys
from pathlib import Path

# Stage 17 (EXE Packaging), Section 8: this is the ONLY thing BASE_DIR
# controls (confirmed by grep — DATABASE_PATH, DATA_INPUT/PROCESSED/
# OUTPUT_DIR, LOG_DIR, and nothing else). Templates/static assets are
# resolved separately in app/__init__.py and are correctly left
# bundle-relative — they're application files, not user data.
#
# In a normal (non-frozen) run, __file__ is this source file's real
# location, exactly as before — zero behavior change for dev/test.
#
# In a PyInstaller --onedir build (Section 5 — onedir, not onefile, was
# the approved choice), `sys.frozen` is True and this module's __file__
# resolves to somewhere INSIDE the bundled _internal/ folder. Rooting
# user-data paths there would put the live database and client files
# in the same folder an application upgrade is expected to replace —
# exactly what Section 6 ("user data must not live inside the EXE
# bundle") and Section 23 (upgrade must never lose data) forbid.
# sys.executable, by contrast, is FINsight.exe itself, which in a
# --onedir build sits NEXT TO (not inside) _internal/ — so rooting
# there keeps database/, data/, and logs/ as siblings of the exe that
# an upgrade never touches.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent


DEV_SECRET_KEY_FALLBACK = "dev-key-change-me-before-lan-mode"


class Config:
    # --- Core ---
    # This fallback is acceptable for local, single-machine, standalone-mode
    # development ONLY (Stage 2 review, condition #3). wsgi_lan.py refuses
    # to start if this fallback is still in effect — see the guard there.
    SECRET_KEY = os.environ.get("FINSIGHT_SECRET_KEY", DEV_SECRET_KEY_FALLBACK)

    # --- Database (SQLite, single central file — Blueprint Ambiguity #1) ---
    DATABASE_PATH = BASE_DIR / "database" / "finsight.db"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"

    # --- Local storage paths (Blueprint Section C) ---
    DATA_INPUT_DIR = BASE_DIR / "data" / "input"
    DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
    DATA_OUTPUT_DIR = BASE_DIR / "data" / "output"

    # --- Upload limits (Stage 6 addition — flagged in the Stage 6 delivery
    # notes for your awareness, not an existing default being changed).
    # A generous but finite cap so a single mis-selected file can't quietly
    # exhaust local disk on an offline desktop install; wired to Flask's
    # own MAX_CONTENT_LENGTH in app/__init__.py, which rejects an
    # oversized upload before it is even read into memory. Trial
    # balances/GLs/journal-entry exports are the largest files this
    # product expects, and 50 MB comfortably covers a very large one in
    # CSV/XLSX form — revisit if a real-world file turns out larger.
    MAX_UPLOAD_SIZE_BYTES = int(os.environ.get("FINSIGHT_MAX_UPLOAD_SIZE_BYTES", 50 * 1024 * 1024))

    # --- Feature flags (approved defaults — Blueprint Section 20 / N) ---
    AI_ENABLED = os.environ.get("FINSIGHT_AI_ENABLED", "false").lower() == "true"  # OFF by default
    LAN_MODE_ENABLED = os.environ.get("FINSIGHT_LAN_MODE", "false").lower() == "true"  # OFF by default
    LAN_MODE_PORT = int(os.environ.get("FINSIGHT_LAN_PORT", "8877"))

    # --- Stage 16 — LAN access gate brute-force protection (Section 11).
    # Deliberately small and configurable, not a "security platform":
    # after this many wrong passwords from the same source IP, that IP
    # is locked out of the login attempt for this many seconds. See
    # app/security/lan_auth.py — this state is in-memory only, never
    # written to the database or logs.
    LAN_MAX_LOGIN_ATTEMPTS = int(os.environ.get("FINSIGHT_LAN_MAX_LOGIN_ATTEMPTS", "5"))
    LAN_LOGIN_LOCKOUT_SECONDS = int(os.environ.get("FINSIGHT_LAN_LOCKOUT_SECONDS", "300"))

    # --- Risk engine defaults (Blueprint Section H — configurable, these are only starting points) ---
    RISK_LEVEL_CUTOFFS = {"low_max": 29, "medium_max": 59, "high_max": 79}  # >=80 = Critical

    # --- Currency (Blueprint Correction #7 — INTEGER paise everywhere money is stored) ---
    CURRENCY_STORAGE_UNIT = "paise"

    # --- Logging ---
    LOG_DIR = BASE_DIR / "logs"
    LOG_LEVEL = os.environ.get("FINSIGHT_LOG_LEVEL", "INFO")

    # --- Stage 15 — Security / session cookie hardening ---
    # HTTPONLY is Flask's own default already (JS on any page, including
    # a same-origin XSS payload, cannot read the cookie) — set explicitly
    # here so the decision is visible in source rather than relying on an
    # unstated framework default. SAMESITE=Lax is a real, zero-dependency
    # CSRF mitigation on top of the token check in app/security/csrf.py:
    # a cross-site page's auto-submitted form to this app would not carry
    # the session cookie at all under Lax, so `session["current_engagement_id"]`
    # (and therefore the CSRF token check itself) simply wouldn't line up.
    # Not "Strict" — Strict also blocks the cookie on a plain top-level
    # link click from an external page into a running FinSight tab, which
    # is a legitimate, harmless case for a local single-user tool.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # --- Stage 15 — CSRF ---
    # See app/security/csrf.py. A same-origin synchronizer-token check
    # implemented with the standard library only (secrets + the existing
    # Flask session) — no new dependency (Flask-WTF was never on the
    # approved package list, Blueprint Section L). ON by default for the
    # real application (dev server via run.py and LAN mode via
    # wsgi_lan.py both use this default); TestConfig below turns it off
    # so the existing HTTP test suites (which POST directly without
    # first scraping a token out of rendered HTML) keep working
    # unmodified — the standard, widely-used pattern for testing an app
    # that has CSRF protection (mirrors how Flask-WTF's own
    # WTF_CSRF_ENABLED=False test convention works). Real enforcement is
    # exercised directly by tests/test_stage15_security.py using its own
    # config with this explicitly re-enabled.
    CSRF_ENABLED = True


class TestConfig(Config):
    """Used by the pytest smoke test — in-memory DB, testing flag on."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    CSRF_ENABLED = False
