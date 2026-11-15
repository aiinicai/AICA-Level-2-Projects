import hmac
import secrets
import time
from datetime import date, datetime

from flask import Flask, abort, flash, g, redirect, request, session, url_for

from . import perms
from .config import data_dir, read_secret
from .models import ActivityLog, FirmSetting, User, db

__version__ = "1.0.0"

_failed_logins: dict[str, list[float]] = {}


THEMES = {"navy": "Navy (default)", "emerald": "Emerald", "maroon": "Maroon", "purple": "Purple", "dark": "Dark"}


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=read_secret("session.key"),
        SQLALCHEMY_DATABASE_URI="sqlite:///" + str(data_dir() / "auditmanager.db").replace("\\", "/"),
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=60 * 60 * 12,
    )
    if test_config:
        app.config.update(test_config)

    from .services import backup as backup_svc

    from .config import apply_pending_move

    apply_pending_move()  # switch to a new data folder first, if one was chosen in Settings
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(data_dir() / "auditmanager.db").replace("\\", "/")
    restored = backup_svc.apply_pending_restore()  # must happen before the database is opened

    db.init_app(app)
    with app.app_context():
        db.create_all()
        _ensure_columns()
        if restored:
            db.session.add(ActivityLog(module="settings", description="Data was restored from a backup; the previous data was kept as before-restore-" + restored + ".db"))
            db.session.commit()
        from .services.compliance import seed_defaults

        seed_defaults()
        from .services.whatsapp import seed_templates

        seed_templates()
        from .services.billing import seed_services

        seed_services()
        from .services.duedates import seed_due_dates

        seed_due_dates()
        from .services.automation import seed_templates as seed_auto_templates

        seed_auto_templates()
        if not FirmSetting.get("backup_when"):
            FirmSetting.put("backup_when", "daily" if FirmSetting.get("backup_auto") == "1" else "off")
        db.session.commit()

    if not app.config.get("TESTING"):
        import logging
        from logging.handlers import RotatingFileHandler

        handler = RotatingFileHandler(data_dir() / "error.log", maxBytes=500_000, backupCount=2, encoding="utf-8")
        handler.setLevel(logging.ERROR)
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        app.logger.addHandler(handler)

        _start_auto_backup(app)

    register_hooks(app)
    register_filters(app)

    from .views import register_views

    register_views(app)
    return app


# ---------------------------------------------------------------- helpers used across views
def _ensure_columns() -> None:
    """Add columns introduced after a firm's database was first created (create_all only adds new tables)."""
    wanted = {"whats_app_message": {"channel": "VARCHAR(10) DEFAULT 'whatsapp'", "subject": "VARCHAR(200)", "send_at": "DATETIME",
                                    "email": "VARCHAR(160)", "image": "VARCHAR(80)"},
              "whats_app_template": {"image": "VARCHAR(80)"},
              "client": {"hourly_rate": "FLOAT", "contact_person": "VARCHAR(120)", "contact_designation": "VARCHAR(80)"},
              "tds_return": {"ack_number": "VARCHAR(60)"},
              "itr_filing": {"verification_status": "VARCHAR(20)", "verification_date": "DATE"},
              "due_date": {"original_date": "DATE"}}
    for table, cols in wanted.items():
        have = {r[1] for r in db.session.execute(db.text(f"PRAGMA table_info({table})"))}
        for name, ddl in cols.items():
            if have and name not in have:
                db.session.execute(db.text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
    db.session.commit()


def _start_auto_backup(app) -> None:
    """Background jobs while the app is open: backup on open, daily backup, and emails scheduled for later."""
    import threading

    def loop():
        time.sleep(20)
        try:
            with app.app_context():
                from .services import backup as backup_svc

                backup_svc.on_open()
        except Exception:
            app.logger.exception("Backup on open failed")
        n = 0
        while True:
            try:
                with app.app_context():
                    from .services import backup as backup_svc
                    from .services import whatsapp as wa

                    wa.send_scheduled()
                    if n % 30 == 0:
                        backup_svc.auto_if_due()
                        from .services import automation

                        automation.run_due_reminders()
            except Exception:
                app.logger.exception("Background job failed")
            n += 1
            time.sleep(60)

    threading.Thread(target=loop, daemon=True, name="background-jobs").start()


def _profession() -> dict:
    from .services.letterhead import profession

    return profession()


def log_activity(module: str, description: str) -> None:
    db.session.add(ActivityLog(user_id=getattr(g, "user", None) and g.user.id, module=module, description=description[:400]))


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def to_float(value, default: float = 0.0) -> float:
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return default


def throttled(key: str, limit: int = 5, window: int = 600) -> bool:
    now = time.time()
    hits = [t for t in _failed_logins.get(key, []) if now - t < window]
    _failed_logins[key] = hits
    return len(hits) >= limit


def record_failed_login(key: str) -> None:
    _failed_logins.setdefault(key, []).append(time.time())


def clear_failed_logins(key: str) -> None:
    _failed_logins.pop(key, None)


# ---------------------------------------------------------------- request hooks
def register_hooks(app: Flask) -> None:
    @app.before_request
    def load_user_and_guard():
        g.user = None
        uid = session.get("uid")
        if uid:
            user = db.session.get(User, uid)
            if user and user.is_active_user:
                g.user = user
            else:
                session.clear()

        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            sent = request.form.get("_csrf") or request.headers.get("X-CSRF-Token") or ""
            expected = session.get("_csrf", "")
            if not expected or not hmac.compare_digest(sent, expected):
                abort(400, "Your session expired or the form was invalid. Go back, refresh the page and try again.")

        if request.endpoint in (None, "static"):
            return None
        if User.query.count() == 0 and request.endpoint != "auth.setup":
            return redirect(url_for("auth.setup"))
        module = perms.BLUEPRINT_MODULE.get(request.blueprint or "")
        if g.user is not None and module and not perms.can(g.user, module):
            abort(403)
        return None

    @app.context_processor
    def inject_globals():
        if "_csrf" not in session:
            session["_csrf"] = secrets.token_urlsafe(24)
        return {
            "csrf_token": session["_csrf"],
            "current_user": g.get("user"),
            "firm_name": FirmSetting.get("firm_name", "Office Manager"),
            "today": date.today(),
            "theme": (FirmSetting.get(f"theme_user_{g.user.id}", "navy") if g.get("user") else "navy"),
            "themes": THEMES,
            "profession": _profession(),
            "hourly_on": FirmSetting.get("hourly_billing") == "1",
            "can": (lambda module: perms.can(g.get("user"), module)),
        }

    @app.after_request
    def save_download_locally(resp):
        """Desktop window on the host PC: instead of a browser download (which the embedded window may not offer), save the file to the
        user's Downloads folder and open it. Asked for with ?save=1 by the window's own script; never honoured for other computers."""
        if request.args.get("save") != "1" or request.remote_addr not in ("127.0.0.1", "::1"):
            return resp
        disp = resp.headers.get("Content-Disposition", "")
        if resp.status_code != 200 or "attachment" not in disp:
            return resp
        import os
        import re as _re
        from pathlib import Path
        from urllib.parse import unquote

        from flask import jsonify

        m = _re.search(r"filename\*=UTF-8''([^;]+)", disp) or _re.search(r'filename="?([^";]+)"?', disp)
        name = _re.sub(r'[\\/:*?"<>|]', "-", unquote(m.group(1)) if m else "download").strip() or "download"
        try:
            resp.direct_passthrough = False
            data = resp.get_data()
            folder = Path.home() / "Downloads"
            folder.mkdir(parents=True, exist_ok=True)
            target, stem, ext, n = folder / name, Path(name).stem, Path(name).suffix, 1
            while target.exists():
                target = folder / f"{stem} ({n}){ext}"
                n += 1
            target.write_bytes(data)
            opened = False
            if not app.config.get("TESTING") and hasattr(os, "startfile"):
                try:
                    os.startfile(str(target))  # opens the PDF / Excel in its usual program
                    opened = True
                except OSError:
                    pass
            return jsonify(ok=True, path=str(target), name=target.name, opened=opened)
        except OSError as e:
            return jsonify(ok=False, message=f"Could not save the file: {e}")

    @app.after_request
    def no_store(resp):
        if request.endpoint != "static":
            resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "SAMEORIGIN"
        return resp

    @app.errorhandler(403)
    def forbidden(e):
        from flask import render_template

        return render_template("error.html", code=403, message="You do not have permission to open this page."), 403

    @app.errorhandler(500)
    def crashed(e):
        from flask import render_template

        db.session.rollback()
        log = data_dir() / "error.log"
        try:
            return render_template("error.html", code="Something went wrong", message=f"Nothing was lost. The details were saved to {log} - "
                                   "send that file to your developer so it can be fixed."), 500
        except Exception:
            return f"Something went wrong. Details were saved to {log}", 500

    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template

        return render_template("error.html", code=404, message="That page or record was not found."), 404

    @app.errorhandler(400)
    def bad_request(e):
        from flask import render_template

        return render_template("error.html", code=400, message=getattr(e, "description", "Bad request.")), 400


def register_filters(app: Flask) -> None:
    def inr(value, decimals: int = 2) -> str:
        """Indian digit grouping: 1,23,456.00"""
        try:
            number = float(value or 0)
        except (TypeError, ValueError):
            return str(value)
        negative = number < 0
        number = abs(number)
        whole, _, frac = f"{number:.{decimals}f}".partition(".")
        if len(whole) > 3:
            head, tail = whole[:-3], whole[-3:]
            parts = []
            while len(head) > 2:
                parts.insert(0, head[-2:])
                head = head[:-2]
            if head:
                parts.insert(0, head)
            whole = ",".join(parts) + "," + tail
        out = whole + (("." + frac) if decimals else "")
        return ("-" if negative else "") + "₹" + out

    def dmy(value) -> str:
        return value.strftime("%d %b %Y") if value else "—"

    def label(value) -> str:
        return str(value or "").replace("_", " ").title()

    def csrf_value() -> str:
        # a global (not a template variable) so it also works inside imported macros
        if "_csrf" not in session:
            session["_csrf"] = secrets.token_urlsafe(24)
        return session["_csrf"]

    app.jinja_env.globals["csrf_value"] = csrf_value
    app.jinja_env.filters["inr"] = inr
    app.jinja_env.filters["dmy"] = dmy
    app.jinja_env.filters["label"] = label
