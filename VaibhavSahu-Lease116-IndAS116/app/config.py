"""Application configuration.

Data (SQLite database, uploaded agreements, backups) lives outside the program folder so
that OneDrive/Dropbox sync never touches a live database:

    Windows : %LOCALAPPDATA%\\Lease116\\data
    Linux   : ~/.local/share/lease116/data
Override with the environment variable LEASE116_DATA_DIR.
"""
from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

APP_NAME = "Lease116"
APP_TITLE = "Lease116 — Ind AS 116 / IFRS 16 Lease Accounting"
APP_VERSION = "1.1.0"
HOST = os.environ.get("LEASE116_HOST", "127.0.0.1")
PORT = int(os.environ.get("LEASE116_PORT", "8116"))
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
PROJECT_DIR = BASE_DIR.parent


def default_data_dir() -> Path:
    env = os.environ.get("LEASE116_DATA_DIR")
    if env:
        return Path(env)
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "Lease116" / "data"
    return Path.home() / ".local" / "share" / "lease116" / "data"


DATA_DIR = default_data_dir()
DOCS_DIR = DATA_DIR / "documents"
BACKUP_DIR = DATA_DIR / "backups"
EXPORT_DIR = DATA_DIR / "exports"


def ensure_dirs():
    for d in (DATA_DIR, DOCS_DIR, BACKUP_DIR, EXPORT_DIR):
        d.mkdir(parents=True, exist_ok=True)


def db_url() -> str:
    return os.environ.get("LEASE116_DB_URL") or f"sqlite:///{(DATA_DIR / 'lease116.db').as_posix()}"


def secret_key() -> str:
    ensure_dirs()
    p = DATA_DIR / ".secret_key"
    if p.exists():
        return p.read_text().strip()
    key = secrets.token_hex(32)
    p.write_text(key)
    return key
