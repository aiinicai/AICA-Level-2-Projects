"""Where the app finds its code, its data and its database.

Works in three situations:
  1. `streamlit run app.py` on a laptop      -> data next to app.py
  2. Hosted on Streamlit Community Cloud      -> DATABASE_URL from st.secrets
  3. Installed Windows app (PyInstaller .exe) -> data in %LOCALAPPDATA%\\CAPracticeManager
"""
import json
import os
import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
# Bundled code/assets (inside the .exe bundle, or the project folder)
CODE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
EXE_DIR = Path(sys.executable).resolve().parent if FROZEN else CODE_DIR


def _data_dir() -> Path:
    """Writable folder for settings, the local database and logs.
    The installed app lives in a folder that may be read-only, so it keeps its data in the user's AppData."""
    if os.environ.get("CAPM_DATA_DIR"):
        d = Path(os.environ["CAPM_DATA_DIR"])
    elif FROZEN:
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        d = Path(base) / "CAPracticeManager"
    else:
        d = CODE_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


DATA_DIR = _data_dir()
SETTINGS_FILE = DATA_DIR / "settings.json"
PRESET_FILE = EXE_DIR / "settings.json"   # optional: a firm can ship a pre-filled settings.json next to the .exe
BUNDLED_DUE_DATES = CODE_DIR / "due_dates.json"
LOG_FILE = DATA_DIR / "app.log"


def local_settings() -> dict:
    merged = {}
    for f in (PRESET_FILE, SETTINGS_FILE):
        try:
            merged.update(json.loads(f.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    return merged


def save_local_settings(data: dict):
    try:
        cur = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cur = {}
    cur.update(data)
    SETTINGS_FILE.write_text(json.dumps(cur, indent=2), encoding="utf-8")


def _from_secrets(key):
    try:
        import streamlit as st
        return st.secrets.get(key)
    except Exception:  # no secrets file -> fine
        return None


def raw_database_url() -> str | None:
    return (os.environ.get("DATABASE_URL")
            or _from_secrets("DATABASE_URL")
            or local_settings().get("database_url"))


def database_url() -> str:
    url = raw_database_url()
    if not url:
        return f"sqlite:///{(DATA_DIR / 'practice.db').as_posix()}"
    url = url.strip()
    # Supabase / Neon give "postgres://" or "postgresql://" URLs; SQLAlchemy needs the driver name
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    if "supabase" in url and "sslmode=" not in url:  # Supabase expects encrypted connections
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return url


def needs_setup() -> bool:
    """Desktop app on first run: ask whether to join the firm's cloud database or work on this PC only."""
    if not (FROZEN or os.environ.get("CAPM_DESKTOP")):
        return False
    if os.environ.get("DATABASE_URL") or _from_secrets("DATABASE_URL"):
        return False
    s = local_settings()
    return not (s.get("database_url") or s.get("mode") == "local")


def database_label() -> str:
    url = database_url()
    if url.startswith("sqlite"):
        return "Local database (this computer only)"
    host = url.split("@")[-1].split("/")[0].split(":")[0]
    return f"Cloud database ({host})"
