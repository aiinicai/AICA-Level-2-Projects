"""
Packaged/first-run bootstrap (Stage 17, Sections 10-12, 18).

NOT imported or run by create_app() and NOT used by the pytest suite —
tests build their own throwaway schema directly via
Base.metadata.create_all() in their own fixtures, exactly as before,
and none of that changes here. This module is only ever called by a
real launcher (the new packaged entry point, and optionally run.py /
wsgi_lan.py) BEFORE create_app() (for the secret key) and AFTER it (for
database initialization), so local development and the test suite are
completely unaffected by anything in this file.

Two independent responsibilities, kept separate because they run at
different points in the startup sequence:

1. get_or_create_secret_key() — must run BEFORE create_app(), because
   Flask's SECRET_KEY is read at config-class-body evaluation time
   (config.py's `Config.SECRET_KEY = os.environ.get(...)`), before any
   database connection exists. Storing it in the database (like the
   Stage 16 LAN password) would be a chicken-and-egg problem — Flask
   needs SECRET_KEY before it can even build the app that would open
   the database. So this lives in a small local file instead, exactly
   the "protected local configuration location" Section 18 asks for.
   The launcher sets FINSIGHT_SECRET_KEY from this file's contents
   before importing app.create_app — config.py's own SECRET_KEY logic
   is completely unchanged, still just `os.environ.get(...)`.

2. initialize_database() — must run AFTER create_app() (needs a real
   engine/session). Section 10's exact requirement: a brand-new install
   gets its schema and reference data created automatically; an
   existing database is used as-is, never overwritten, never reset,
   never destructively migrated. Built entirely from already-existing,
   already-approved pieces — Base.metadata (Stage 3), the four
   database/seed/seed_*.py modules' own idempotent seed(session)
   functions (each already checks-before-insert, unmodified here), and
   Alembic (already an approved Stage 1 dependency) invoked
   programmatically instead of requiring a manual `alembic upgrade
   head` from the end user (Section 11).
"""
from __future__ import annotations

import logging
import secrets
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Section 27: full exception detail (which the console/first-run banner
# must never show — Section 12) goes only to logs/finsight.log. "app"
# is Flask's own logger name here (Flask(__name__) inside app/__init__.py,
# where __name__ == "app") — app.utils.logging_config.setup_logging()
# attaches the rotating file handler to that logger, and "app.bootstrap"
# is a child of it, so anything logged here propagates to the same file
# handler once setup_logging() has run (i.e. once create_app() has been
# called — always true by the time initialize_database() runs). Never
# logs passwords/secrets/financial data — only migration/seed exceptions.
_logger = logging.getLogger("app.bootstrap")


def get_or_create_secret_key(app_data_root: Path) -> str:
    """Section 18: never hard-coded, never logged, never shown to the
    user, never in source control (the config/ folder this writes to
    is outside the bundled application and is not part of the
    repository). Generated once with `secrets.token_hex(32)` — the
    same standard-library primitive already used for the Stage 15 CSRF
    token and the Stage 16 LAN lockout keys — and reused on every
    subsequent start so existing signed session cookies keep working
    across restarts."""
    secret_path = app_data_root / "config" / "secret_key"
    if secret_path.exists():
        existing = secret_path.read_text(encoding="utf-8").strip()
        if existing:
            return existing

    secret_path.parent.mkdir(parents=True, exist_ok=True)
    new_key = secrets.token_hex(32)
    secret_path.write_text(new_key, encoding="utf-8")
    try:
        # Best-effort on POSIX; Windows ACL management is explicitly
        # out of scope (Stage 17 Section 26 — documented, not built).
        secret_path.chmod(0o600)
    except OSError:
        pass
    return new_key


def _alembic_config(sqlalchemy_url: str):
    """Builds an Alembic Config pointed at absolute, bundle-relative
    paths — never relying on the process's current working directory
    (Section 8's explicit warning), since a desktop shortcut can launch
    FINsight.exe from any "Start in" directory. script_location and
    alembic.ini both live under the application bundle (they're code,
    not user data) and are resolved the same __file__-relative way
    app/__init__.py already resolves templates/static — correct in
    both dev mode and a frozen --onedir build.

    Imports Alembic lazily, inside this function, so that nothing in
    this module fails to import in an environment where Alembic isn't
    installed (this sandbox is exactly such an environment — see
    documentation/stage17_exe_packaging.md's Known Limitations). A
    caller must be ready to catch ImportError."""
    from alembic.config import Config as AlembicConfig

    cfg = AlembicConfig(str(PROJECT_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(PROJECT_ROOT / "database" / "migrations"))
    cfg.set_main_option("sqlalchemy.url", sqlalchemy_url)
    return cfg


def _run_seed_modules(session) -> list[str]:
    """Every seed module's seed(session) is idempotent by construction
    (checks existing rows before inserting — unmodified here, see each
    module's own docstring) — safe to call on both a brand-new database
    and an existing one that's simply gaining new reference data on
    upgrade."""
    from database.seed import seed_reference_data, seed_accounting_rules, seed_audit_rules, seed_tax_rules

    applied = []
    for module in (seed_reference_data, seed_accounting_rules, seed_audit_rules, seed_tax_rules):
        module.seed(session)
        applied.append(module.__name__)
    session.commit()
    return applied


def initialize_database(app_config: dict, db_existed_before: bool, log=print) -> dict:
    """The Section 10 first-run/every-run initializer.

    `db_existed_before` MUST be determined by the caller before
    create_app() (and therefore init_engine()) ever runs — deliberately
    not recomputed here from `Path(app_config["DATABASE_PATH"]).exists()`
    at this point, because that would no longer reliably distinguish
    "brand new" from "already existing": opening any connection to a
    SQLite path (which engine construction can trigger, depending on
    the SQLAlchemy version/driver) creates the file on disk immediately,
    even before a single table exists. Checking strictly before any
    engine activity removes any dependency on connection-timing
    behavior that isn't part of SQLAlchemy's documented contract.
    finsight_app.py's main() does this via `Config.DATABASE_PATH.exists()`
    — a plain class-attribute read, no engine involved.

    `log` defaults to plain print() (this runs before Flask's own
    logger exists in the packaged launcher's startup sequence); the
    real launcher passes a function that also writes to
    logs/finsight.log so this shows up there too, per Section 27.

    Returns a small result dict for the caller to report honestly
    (never silently swallowed) — see the packaged launcher's own
    console output and documentation/stage17_exe_packaging.md's Test
    Results section for how this surfaces."""
    from app import extensions
    from app.models import Base

    result = {"db_existed_before": db_existed_before, "schema_created": False, "seeded_modules": [], "migration": "not_attempted"}

    if not db_existed_before:
        log("Preparing database...")
        Base.metadata.create_all(extensions.engine)
        result["schema_created"] = True
        try:
            command_module = __import__("alembic.command", fromlist=["stamp"])
            command_module.stamp(_alembic_config(app_config["SQLALCHEMY_DATABASE_URI"]), "head")
            result["migration"] = "stamped_head_new_db"
        except ImportError:
            result["migration"] = "skipped_alembic_not_installed"
            log("Note: Alembic is not installed — schema was created directly from the current models. "
                "This is safe for a brand-new database; a future FINsight update that ships a migration "
                "will need Alembic available to apply it automatically.")
        except Exception as exc:  # noqa: BLE001 — see module docstring: never crash startup over this
            result["migration"] = f"stamp_failed: {exc.__class__.__name__}"
            _logger.exception("Alembic stamp-head failed for a newly created database")
            log("Note: could not record the schema baseline for future updates. Your new database was "
                "still created successfully and is fully usable — this only affects automatic updates "
                "later. Details were written to the log file, not shown here.")
    else:
        log("Using existing database — checking for pending updates...")
        try:
            command_module = __import__("alembic.command", fromlist=["upgrade"])
            command_module.upgrade(_alembic_config(app_config["SQLALCHEMY_DATABASE_URI"]), "head")
            result["migration"] = "upgraded_existing_db"
        except ImportError:
            result["migration"] = "skipped_alembic_not_installed"
            log("Note: Alembic is not installed — skipped checking for schema updates. "
                "Your existing data was not touched.")
        except Exception as exc:  # noqa: BLE001 — never destructive, never crash startup over this
            result["migration"] = f"upgrade_failed: {exc.__class__.__name__}"
            _logger.exception("Alembic upgrade-head failed for an existing database")
            log("Note: could not check for schema updates this time. Your existing data was not touched. "
                "Details were written to the log file, not shown here. If problems continue, back up your "
                "data directory and contact support before trying again.")

    log("Loading reference data...")
    try:
        # Deliberately extensions.SessionLocal() (the same scoped-session
        # factory every service module in this app already uses) rather
        # than a bare Session(engine) — the four seed modules' own
        # standalone main() functions use Session(engine) directly, which
        # is correct for a one-off script but is not the pattern the rest
        # of the live application uses. Using the same factory here keeps
        # this in line with how every other part of FinSight touches the
        # database, and each seed module's seed(session) function only
        # ever needs an ordinary Session-like object — it doesn't care
        # which one it's given.
        session = extensions.SessionLocal()
        result["seeded_modules"] = _run_seed_modules(session)
    except Exception:  # noqa: BLE001 — never crash startup over reference-data seeding
        _logger.exception("Reference-data seeding failed")
        log("Note: could not confirm reference data is up to date. Your engagements, findings, queries "
            "and working papers are unaffected. Details were written to the log file, not shown here.")

    return result
