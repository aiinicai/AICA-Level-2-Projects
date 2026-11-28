import os
import secrets
import sqlite3
import warnings
from datetime import date, datetime, timedelta

from flask import Flask
from sqlalchemy import event
from sqlalchemy.engine import Engine

from . import gst
from .extensions import db

warnings.filterwarnings("ignore", message=".*does \\*not\\* support Decimal.*")


@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_conn, _):
    if isinstance(dbapi_conn, sqlite3.Connection):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")      # readers never block the writer
        cur.execute("PRAGMA busy_timeout=30000")    # wait for the write lock instead of failing
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


def create_app(overrides=None):
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    inst = os.environ.get("CHALLAN_INSTANCE", os.path.join(base, "instance"))
    os.makedirs(inst, exist_ok=True)
    app = Flask(__name__, instance_path=inst)

    key_file = os.path.join(inst, "secret.key")
    if not os.path.exists(key_file):
        with open(key_file, "w") as f:
            f.write(secrets.token_hex(32))
    with open(key_file) as f:
        secret = f.read().strip()

    app.config.update(
        SECRET_KEY=os.environ.get("CHALLAN_SECRET", secret),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL") or "sqlite:///" + os.path.join(inst, "challan.db").replace("\\", "/"),
        PERMANENT_SESSION_LIFETIME=timedelta(hours=10),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,
    )
    if overrides:
        app.config.update(overrides)
    db.init_app(app)

    from . import auth, vendors, challans, reports, dashboard, uploads, admin
    for m in (auth, vendors, challans, reports, dashboard, uploads, admin):
        app.register_blueprint(m.bp)

    @app.template_filter("inr")
    def _inr(x):
        return gst.inr(x) if x is not None else ""

    @app.template_filter("dmy")
    def _dmy(d):
        return d.strftime("%d-%m-%Y") if isinstance(d, (date, datetime)) else (d or "")

    @app.template_filter("dmyhm")
    def _dmyhm(d):
        return d.strftime("%d-%m-%Y %H:%M") if d else ""

    @app.context_processor
    def _ctx():
        from .models import Challan, FINAL
        from flask import g
        pending = 0
        if getattr(g, "user", None):
            pending = Challan.query.filter_by(status=FINAL, ewb_status="Pending").count()
        return {"gst": gst, "pending_ewb_count": pending, "today": date.today()}

    from .cli import register_cli
    register_cli(app)
    return app
