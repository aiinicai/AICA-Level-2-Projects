"""Configuration. Every path is resolved relative to the project folder, never
the current working directory, so the app opens the same database however it
is started (golden test 23)."""
from __future__ import annotations

import os
import secrets
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
INSTANCE = ROOT / "instance"
ENV_FILE = ROOT / ".env"


def ensure_env_file() -> bool:
    """Create .env with fresh random keys on first run. Returns True if created."""
    if ENV_FILE.exists():
        return False
    from cryptography.fernet import Fernet
    ENV_FILE.write_text(
        "# Generated on first run. NEVER commit this file.\n"
        f"SECRET_KEY={secrets.token_urlsafe(48)}\n"
        f"FERNET_KEY={Fernet.generate_key().decode()}\n"
        "# DATABASE_URL=postgresql+psycopg://user:pass@localhost/mca\n"
        "SESSION_COOKIE_SECURE=1\n",
        encoding="utf-8")
    return True


def sqlite_url(path: Path) -> str:
    return "sqlite:///" + path.as_posix()


def database_url() -> str:
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if not url:
        return sqlite_url(INSTANCE / "mca.db")
    if url.startswith("sqlite:///"):
        p = Path(url[len("sqlite:///"):])
        if not p.is_absolute():                 # relative SQLite path -> relative to the project, not CWD
            return sqlite_url(ROOT / p)
    return url


class Config:
    def __init__(self, **overrides):
        load_dotenv(ENV_FILE)
        INSTANCE.mkdir(exist_ok=True)
        self.SECRET_KEY = os.environ.get("SECRET_KEY") or ""
        self.FERNET_KEY = os.environ.get("FERNET_KEY") or ""
        self.DATABASE_URL = database_url()
        self.UPLOAD_DIR = INSTANCE / "uploads"
        self.BACKUP_DIR = INSTANCE / "backups"
        self.RULEPACK_DIR = ROOT / "rulepack"
        self.MAX_CONTENT_LENGTH = 5 * 1024 * 1024 + 64 * 1024      # 5 MB file + form overhead
        self.SESSION_COOKIE_HTTPONLY = True
        self.SESSION_COOKIE_SAMESITE = "Lax"
        # Browsers accept Secure cookies on http://localhost / 127.0.0.1; set 0 only for plain-http LAN use.
        self.SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "1") == "1"
        self.REMEMBER_COOKIE_SECURE = self.SESSION_COOKIE_SECURE
        self.SESSION_IDLE = timedelta(minutes=30)
        self.SESSION_ABSOLUTE = timedelta(hours=12)
        self.LOCKOUT_THRESHOLD = 5
        self.LOCKOUT_PERIOD = timedelta(minutes=15)
        self.LOGIN_RATE_LIMIT = (20, 60)          # attempts per IP per N seconds
        self.WTF_CSRF_TIME_LIMIT = None           # token lives as long as the session
        self.TESTING = False
        self.AS_OF = None                          # fixed "today" for tests/demo; None = real IST date
        self.SCHEDULER = os.environ.get("SCHEDULER", "1") == "1"
        for k, v in overrides.items():
            setattr(self, k, v)
        if not self.SECRET_KEY or not self.FERNET_KEY:
            raise RuntimeError("SECRET_KEY and FERNET_KEY are not set. Run:  python cli.py init-db  "
                               "(it creates .env with fresh keys), or copy .env.example to .env.")
