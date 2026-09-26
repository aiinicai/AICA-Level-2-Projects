"""Flask application factory."""
from __future__ import annotations

import secrets
from datetime import date

from pathlib import Path

from flask import Flask, g, render_template, request, url_for
from flask_wtf.csrf import CSRFError, CSRFProtect
from sqlalchemy import inspect

import engine
from engine.fees import fmt_inr

from .config import Config

csrf = CSRFProtect()
ASSET_VERSION = secrets.token_hex(4)      # new per server start: busts cached CSS after an upgrade


class NotMigrated(RuntimeError):
    pass


def _unread(user) -> int:
    if not getattr(user, "is_authenticated", False):
        return 0
    from sqlalchemy import func, select

    from .models import Notification, db
    return db.session.execute(select(func.count(Notification.id)).where(Notification.user_id == user.id,
                                                                       Notification.read_at.is_(None))).scalar() or 0


def create_app(**overrides) -> Flask:
    cfg = Config(**overrides)
    app = Flask(__name__, instance_path=str(cfg.UPLOAD_DIR.parent))
    app.config.update({k: v for k, v in vars(cfg).items() if k.isupper()})

    # Refuse to start on an invalid rule pack, naming the failing row (brief §6.1)
    app.extensions["rulepack"] = engine.load(cfg.RULEPACK_DIR)

    from .models import db
    db.init(cfg.DATABASE_URL)
    if "alembic_version" not in inspect(db.engine).get_table_names():
        raise NotMigrated(f"The database at {cfg.DATABASE_URL} is not initialised. Run:  python cli.py init-db")
    cfg.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    from .auth import bp as auth_bp, login_manager
    login_manager.init_app(app)
    csrf.init_app(app)
    app.register_blueprint(auth_bp)
    from .routes import admin, dashboard, entities, obligations, rules, tools
    for m in (dashboard, entities, obligations, admin, rules):
        app.register_blueprint(m.bp)
    for bp in (tools.people, tools.tools, tools.wizard):
        app.register_blueprint(bp)
    from .routes import reports
    app.register_blueprint(reports.bp)

    @app.teardown_appcontext
    def _remove_session(exc=None):
        db.session.remove()

    @app.before_request
    def _nonce():
        g.csp_nonce = secrets.token_urlsafe(16)

    @app.after_request
    def _headers(resp):
        nonce = g.get("csp_nonce", "")
        resp.headers["Content-Security-Policy"] = (
            f"default-src 'self'; script-src 'self' 'nonce-{nonce}'; style-src 'self' 'nonce-{nonce}'; "
            "img-src 'self' data:; font-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'")
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "same-origin"
        resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.endpoint == "static":
            resp.headers["Cache-Control"] = "public, max-age=3600"
        else:
            # every page is computed from live data: never serve a stale due date (golden test 24)
            resp.headers["Cache-Control"] = "no-store"
            resp.headers["Pragma"] = "no-cache"
        return resp

    def _error(code: int, title: str, default: str):
        def handler(e):
            msg = g.get("denied_message") or getattr(e, "description", None) or default
            if request.headers.get("HX-Request"):
                from markupsafe import escape
                return (f'<div class="alert alert-danger alert-dismissible" role="alert">{escape(msg)}'
                        '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button></div>',
                        code, {"HX-Retarget": "#htmx-alerts", "HX-Reswap": "innerHTML"})
            return render_template("error.html", code=code, title=title, message=msg), code
        return handler

    app.register_error_handler(403, _error(403, "Not allowed", "You do not have permission to do that."))
    app.register_error_handler(404, _error(404, "Not found", "That page or record does not exist."))
    app.register_error_handler(413, _error(413, "File too large", "Uploads are limited to 5 MB."))
    app.register_error_handler(422, _error(422, "Please correct the form", "Some details need correcting."))

    @app.errorhandler(CSRFError)
    def _csrf(e):
        return render_template("error.html", code=400, title="Form expired",
                               message="The form expired or was sent from another site. Go back, reload and try again."), 400

    @app.template_filter("inr")
    def _inr(v):
        return "—" if v is None else fmt_inr(v)

    @app.template_filter("dmy")
    def _dmy(v):
        return v.strftime("%d-%m-%Y") if isinstance(v, date) else ("—" if v is None else str(v))

    @app.context_processor
    def _ctx():
        from flask_login import current_user

        from .auth import today
        from .permissions import has
        from .services import HEALTH_LABELS, LABELS, get_setting
        firm = get_setting("firm_name") or "Firm"
        words = [w for w in firm.replace("&", " ").replace(",", " ").split() if w[:1].isalpha()]
        return {"can": lambda p: has(current_user, p), "today": today(), "STATUS_LABELS": LABELS,
                "HEALTH_LABELS": HEALTH_LABELS, "firm_name": firm, "firm_tagline": get_setting("firm_tagline"),
                "firm_initials": "".join(w[0].upper() for w in words[:2]) or "CA", "asset_version": ASSET_VERSION,
                "unread": _unread(current_user),
                "logo_url": url_for("static", filename="logo.png", v=ASSET_VERSION)
                if get_setting("show_logo") and (Path(app.static_folder) / "logo.png").exists() else None,
                "firm_phone": get_setting("firm_phone"), "firm_email": get_setting("firm_email"),
                "firm_address": get_setting("firm_address"),
                "brand_primary": get_setting("brand_primary"), "brand_accent": get_setting("brand_accent"),
                "csp_nonce": g.get("csp_nonce", ""), "rulepack_version": app.extensions["rulepack"].version}

    return app
