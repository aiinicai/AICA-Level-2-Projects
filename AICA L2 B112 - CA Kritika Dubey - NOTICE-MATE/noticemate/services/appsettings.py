"""In-app settings (stored in the local database). Never used for secrets: API keys stay in the environment / .env."""
from __future__ import annotations

from ..core import audit
from ..core.db import ro, tx, utcnow
from ..core.errors import ValidationError
from .auth import require_role

ALLOWED = {
    "local_ai_enabled": ("0", "1"),
    "local_ai_url": None,       # free text, checked to be a loopback address
    "local_ai_model": None,     # free text (model id offered by the local server)
}


def get(key: str, default: str | None = None) -> str | None:
    try:
        with ro() as conn:
            r = conn.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    except Exception:  # table not created yet (before migration v5)
        return default
    return r["value"] if r else default


def all_settings() -> dict:
    return {k: get(k) for k in ALLOWED}


def set_value(user: dict, key: str, value: str) -> dict:
    require_role(user, "CA", "ADMIN")
    if key not in ALLOWED:
        raise ValidationError("Unknown setting.")
    value = (value or "").strip()[:300]
    if ALLOWED[key] and value not in ALLOWED[key]:
        raise ValidationError(f"{key} must be one of {ALLOWED[key]}.")
    if key == "local_ai_url" and value:
        from .ai_providers import check_loopback

        check_loopback(value)
    if any(w in key for w in ("key", "token", "secret", "password")):
        raise ValidationError("Secrets are never stored in the app.")
    with tx() as conn:
        conn.execute("INSERT INTO app_settings(key,value,updated_by,updated_at) VALUES (?,?,?,?) "
                     "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_by=excluded.updated_by, updated_at=excluded.updated_at",
                     (key, value, user["id"], utcnow()))
        audit.log_event(conn, "SETTING_CHANGED", user_id=user["id"], meta={"setting": key, "value": value})
    return all_settings()
