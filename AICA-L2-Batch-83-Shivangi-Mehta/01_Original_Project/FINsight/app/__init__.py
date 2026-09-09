"""
FinSight application factory.

Started as a Stage 2 project skeleton (config/logging/DB-engine
plumbing + placeholder blueprints); Stage 5 adds the first real
cross-cutting piece: an app-level context processor that injects
`current_engagement` and `sebi_nav_state` into every template, since
base.html's sidebar/topbar need them on every page, not just the
Engagement blueprint's own routes.
"""
from pathlib import Path

from flask import Flask, render_template, session

from config import Config
from app import extensions
from app.extensions import init_engine
from app.utils.logging_config import setup_logging


def create_app(config_class: type = Config) -> Flask:
    project_root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        template_folder=str(project_root / "frontend" / "templates"),
        static_folder=str(project_root / "frontend" / "static"),
    )
    app.config.from_object(config_class)
    # Stage 6: reject an oversized upload at the WSGI layer, before Flask
    # even reads it into memory — see config.py's MAX_UPLOAD_SIZE_BYTES
    # comment for why this exists and why 50 MB.
    app.config["MAX_CONTENT_LENGTH"] = app.config["MAX_UPLOAD_SIZE_BYTES"]

    # Ensure local-storage directories exist (offline-first design —
    # Blueprint Section A.2 — everything lives under the project root).
    for path_key in ("DATA_INPUT_DIR", "DATA_PROCESSED_DIR", "DATA_OUTPUT_DIR"):
        Path(app.config[path_key]).mkdir(parents=True, exist_ok=True)
    Path(app.config["DATABASE_PATH"]).parent.mkdir(parents=True, exist_ok=True)

    if not app.config.get("TESTING"):
        setup_logging(app)

    # DB engine plumbing (Stage 2) — real ORM usage starts in Stage 5's
    # engagement_service.
    init_engine(app.config["SQLALCHEMY_DATABASE_URI"])

    @app.teardown_appcontext
    def _remove_db_session(_exception=None):
        # Standard scoped_session-per-request cleanup so one request's
        # session never leaks into the next. Reads `extensions.SessionLocal`
        # dynamically (not `from app.extensions import SessionLocal`) for
        # the same reason engagement_service._session() does — create_app()
        # can run more than once per process (every pytest test that calls
        # it does), and each call rebinds this to a fresh session; a
        # name-import here would close over whichever value existed when
        # app/__init__.py was FIRST imported (always None, since that
        # happens before the first init_engine() call), permanently
        # disabling this cleanup.
        if extensions.SessionLocal is not None:
            extensions.SessionLocal.remove()

    _register_blueprints(app)
    _register_context_processors(app)
    _register_template_filters(app)

    # Stage 16: the LAN access gate must run before CSRF enforcement so
    # an unauthenticated request to a protected route is redirected to
    # the login gate with a clear reason, rather than falling through to
    # a CSRF 400 first. It is a no-op entirely (does nothing on every
    # request) unless app.config["LAN_MODE_ENABLED"] is True — see
    # app/security/lan_auth.py's module docstring.
    from app.security.lan_auth import init_lan_access_gate
    init_lan_access_gate(app)

    from app.security.csrf import init_csrf_protection
    init_csrf_protection(app)

    # Stage 15 section 15: normal users must never see a Python stack
    # trace, a SQL query, a filesystem path, or an environment variable.
    # Flask/Werkzeug's own defaults already never expose those for a
    # generic 500 when app.debug is False (production/LAN mode) — these
    # handlers replace Werkzeug's bare, unstyled default error pages
    # with FinSight's own look for the codes this app can actually
    # produce, using a message a CA/reviewer can act on rather than a
    # protocol name. In local `debug=True` development (run.py only,
    # bound to 127.0.0.1), Flask still shows its interactive debugger
    # for a genuine 500 instead of this handler — see run.py's own
    # Stage 15 note for why that stays opt-in rather than the default.
    @app.errorhandler(400)
    def _bad_request(exc):
        message = getattr(exc, "description", None) or "That request could not be completed. Please go back and try again."
        return render_template("error.html", title="Request Not Completed", message=message), 400

    @app.errorhandler(403)
    def _forbidden(_exc):
        return render_template(
            "error.html", title="Not Allowed",
            message="You don't have access to that. If you believe this is wrong, please try again from the Dashboard.",
        ), 403

    @app.errorhandler(404)
    def _not_found(_exc):
        return render_template(
            "error.html", title="Not Found",
            message="That page or record could not be found. It may belong to a different engagement, or may no longer exist.",
        ), 404

    @app.errorhandler(500)
    def _server_error(_exc):
        # The real exception is still handled by Flask/Werkzeug's normal
        # logging path (visible in finsight.log / console) — this
        # handler only controls what the BROWSER sees.
        return render_template(
            "error.html", title="Something Went Wrong",
            message="FINsight was unable to complete that action. Please try again, and check the highlighted fields if this followed a form submission.",
        ), 500

    @app.errorhandler(413)
    def _upload_too_large(_exc):
        # Friendly page instead of Werkzeug's bare "413 Request Entity
        # Too Large" — this is the only route class that accepts large
        # request bodies (Stage 6 upload), so the message is specific.
        # One decimal place, not integer-divided MB: a small configured
        # limit (e.g. a test overriding it to a few hundred bytes) would
        # otherwise silently round down to "0 MB" — found and fixed
        # during Stage 6 delivery verification.
        max_mb = app.config["MAX_CONTENT_LENGTH"] / (1024 * 1024)
        return {
            "error": "file_too_large",
            "message": f"That file is larger than the {max_mb:.1f} MB upload limit.",
        }, 413

    @app.route("/health")
    def health():
        return {
            "status": "ok",
            "app": "FinSight",
            "stage": "7-mapping-validation",
            "ai_enabled": app.config["AI_ENABLED"],
            "lan_mode_enabled": app.config["LAN_MODE_ENABLED"],
        }

    return app


def _register_blueprints(app: Flask) -> None:
    """Every blueprint below matches an item in the approved navigation
    (Blueprint Section 8) or is an internal cross-cutting API (risk, ai)
    that has no top-level nav entry of its own."""
    from app.api.dashboard_bp import dashboard_bp
    from app.api.engagement_bp import engagement_bp
    from app.api.upload_bp import upload_bp
    from app.api.mapping_bp import mapping_bp
    from app.api.validation_bp import validation_bp
    from app.api.accounting_bp import accounting_bp
    from app.api.audit_bp import audit_bp
    from app.api.tax_bp import tax_bp
    from app.api.review_bp import review_bp
    from app.api.sebi_bp import sebi_bp
    from app.api.risk_bp import risk_bp
    from app.api.exceptions_bp import exceptions_bp
    from app.api.queries_bp import queries_bp
    from app.api.reports_bp import reports_bp
    from app.api.ai_bp import ai_bp
    from app.api.settings_bp import settings_bp
    from app.api.access_bp import access_bp
    from app.api.faq_bp import faq_bp

    for bp in (
        dashboard_bp, engagement_bp, upload_bp, mapping_bp, validation_bp,
        accounting_bp, audit_bp, tax_bp, review_bp, sebi_bp, risk_bp,
        exceptions_bp, queries_bp, reports_bp, ai_bp, settings_bp, access_bp,
        faq_bp,
    ):
        app.register_blueprint(bp)


def _register_template_filters(app: Flask) -> None:
    """`paise_display` (Stage 8): templates render a paise integer as an
    Indian-grouped rupee string via `app.utils.currency.paise_to_display`
    — the same sole conversion point every service module already uses,
    now also reachable from Jinja so a template never does its own
    paise/rupee arithmetic either."""
    from app.utils.currency import paise_to_display

    app.jinja_env.filters["paise_display"] = paise_to_display


def _register_context_processors(app: Flask) -> None:
    """Values every template needs regardless of which blueprint served
    the request — base.html's topbar (current engagement) and sidebar
    (conditional SEBI nav item, Blueprint Section 8) both need these."""

    @app.context_processor
    def inject_engagement_nav_context():
        from app.services import engagement_service as svc
        from app.services.applicability_engine import NAV_HIDE, compute_sebi_nav_state

        current_engagement = svc.get_current_engagement(session)

        if current_engagement is None:
            # Nothing has been evaluated yet — this is "unresolved", not
            # "uncertain, needs review". compute_sebi_nav_state(None, None)
            # would otherwise fall through to its REVIEW_REQUIRED default
            # (correct for "a listed entity nobody's confirmed yet"), which
            # would wrongly show a "Review Required" SEBI item before any
            # engagement or Entity Profile even exists.
            sebi_nav_state = NAV_HIDE
        else:
            profile = svc.get_entity_profile(current_engagement.engagement_id)
            is_listed = profile.is_listed if profile else None
            sebi_row = svc.get_applicability_row(current_engagement.engagement_id, "SEBI/LODR")
            user_confirmed_status = sebi_row.user_confirmed_status if sebi_row else None
            sebi_nav_state = compute_sebi_nav_state(is_listed, user_confirmed_status)

        # Stage 16: base.html shows a "Sign Out" action only when LAN
        # mode is actually active and this browser session is
        # authenticated against the CURRENT password (not a stale
        # session from before a Settings > Security password change —
        # see app/security/lan_auth.py's matching check). In normal
        # local/dev mode (LAN_MODE_ENABLED False) this is always False.
        lan_mode_active = bool(app.config.get("LAN_MODE_ENABLED"))
        lan_authenticated = False
        if lan_mode_active:
            from app.security.lan_auth import is_authenticated as _lan_is_authenticated
            lan_authenticated = _lan_is_authenticated()

        return {
            "current_engagement": current_engagement,
            "sebi_nav_state": sebi_nav_state,
            "lan_mode_active": lan_mode_active,
            "lan_authenticated": lan_authenticated,
        }
