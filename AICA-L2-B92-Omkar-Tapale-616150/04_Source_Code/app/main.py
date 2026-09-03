import os
import sys
import socket
import secrets

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .database import Base, engine, SessionLocal, DATA_DIR
from . import models

# --- resolve base dir whether running as script or as a PyInstaller exe ---
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.join(sys._MEIPASS, "app")  # type: ignore[attr-defined]
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

Base.metadata.create_all(bind=engine)


def _migrate():
    """Lightweight auto-migration for existing SQLite files created by an
    earlier version of the schema, so upgrading doesn't wipe real data."""
    with engine.connect() as conn:
        cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(calendar_events)")]
        if "assigned_by_id" not in cols:
            conn.exec_driver_sql("ALTER TABLE calendar_events ADD COLUMN assigned_by_id INTEGER")
        conn.commit()


_migrate()

# Auto-seed a CEO account + demo org on very first run (empty DB) so the
# app is usable immediately after packaging, without a separate step.
def _ensure_seeded():
    db = SessionLocal()
    try:
        if db.query(models.User).count() == 0:
            from .seed import run_seed
            run_seed(db)
    finally:
        db.close()


_ensure_seeded()

app = FastAPI(title="Company OS")

SECRET_KEY_FILE = os.path.join(DATA_DIR, ".session_secret")


def _get_or_create_secret():
    if os.path.exists(SECRET_KEY_FILE):
        with open(SECRET_KEY_FILE, "r") as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    with open(SECRET_KEY_FILE, "w") as f:
        f.write(key)
    return key


app.add_middleware(SessionMiddleware, secret_key=_get_or_create_secret(), same_site="lax")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

from .routers import auth as auth_router
from .routers import dashboard as dashboard_router
from .routers import calendar as calendar_router
from .routers import attendance as attendance_router
from .routers import leave as leave_router
from .routers import admin as admin_router
from .routers import reports as reports_router
from .routers import resignation as resignation_router
from .routers import tasks as tasks_router

app.include_router(auth_router.router)
app.include_router(dashboard_router.router)
app.include_router(calendar_router.router)
app.include_router(attendance_router.router)
app.include_router(leave_router.router)
app.include_router(admin_router.router)
app.include_router(reports_router.router)
app.include_router(resignation_router.router)
app.include_router(tasks_router.router)


def _lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def run():
    import uvicorn
    ip = _lan_ip()
    port = 8000
    print("=" * 60)
    print(" COMPANY OS is starting...")
    print(f" On this PC:      http://127.0.0.1:{port}")
    print(f" On the office LAN (share with your team): http://{ip}:{port}")
    print(" Default CEO login -> Employee Code: EMP-0001  Password: Welcome@123")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=port)
