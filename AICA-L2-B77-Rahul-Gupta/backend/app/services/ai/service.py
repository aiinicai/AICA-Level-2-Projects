"""AI settings storage (encrypted), provider factory and call logging."""
from __future__ import annotations

import time
from typing import Any

from sqlalchemy.orm import Session

from ...models import AICallLog, AppSetting
from ...utils.crypto import decrypt_secret, encrypt_secret
from .gemini import DEFAULT_MODEL, GeminiProvider
from .provider import AIProvider, AIProviderError

AI_SETTINGS_KEY = "ai_config"

DEFAULT_AI_CONFIG = {
    "provider": "Google Gemini",
    "model": DEFAULT_MODEL,
    "model_display": "Gemini 3.6 Flash",
    "temperature": 0.2,
    "structured_output": True,
    # Off by default: Python extraction is the authoritative source, and rendering
    # every statement page for the vision model dominates processing time. Turn it
    # on in Settings to cross-check extracted values against the page images.
    "visual_verification": False,
    "ai_final_report": True,
    "key_set": False,
    "key_tail": "",
    "connected": False,
}


def get_ai_config(db: Session) -> dict[str, Any]:
    row = db.get(AppSetting, AI_SETTINGS_KEY)
    cfg = dict(DEFAULT_AI_CONFIG)
    if row:
        cfg.update({k: v for k, v in row.value.items() if k != "encrypted_key"})
    return cfg


def _get_raw(db: Session) -> dict[str, Any]:
    row = db.get(AppSetting, AI_SETTINGS_KEY)
    return dict(row.value) if row else {}


def save_ai_config(db: Session, updates: dict[str, Any], api_key: str | None = None) -> dict[str, Any]:
    raw = _get_raw(db)
    base = dict(DEFAULT_AI_CONFIG) | raw
    for k in ("model", "model_display", "temperature", "structured_output",
              "visual_verification", "ai_final_report", "provider"):
        if k in updates and updates[k] is not None:
            base[k] = updates[k]
    if api_key:
        base["encrypted_key"] = encrypt_secret(api_key)
        base["key_set"] = True
        base["key_tail"] = api_key[-4:] if len(api_key) >= 4 else ""
    row = db.get(AppSetting, AI_SETTINGS_KEY)
    if row is None:
        row = AppSetting(key=AI_SETTINGS_KEY, value=base)
        db.add(row)
    else:
        row.value = base
    db.commit()
    return get_ai_config(db)


def get_provider(db: Session) -> AIProvider | None:
    """Configured provider or None (AI unavailable → core app still works)."""
    raw = _get_raw(db)
    token = raw.get("encrypted_key")
    if not token:
        return None
    key = decrypt_secret(token)
    if not key:
        return None
    return GeminiProvider(api_key=key, model=raw.get("model", DEFAULT_MODEL),
                          temperature=float(raw.get("temperature", 0.2)))


def logged_call(db: Session, task: str, case_id: str | None, fn, *args, **kwargs):
    """Run a provider call with latency + outcome logging. Never logs keys."""
    provider = kwargs.pop("_provider", None)
    start = time.monotonic()
    try:
        result = fn(*args, **kwargs)
        db.add(AICallLog(case_id=case_id, task=task,
                         model=getattr(provider, "model", ""),
                         success=1, latency_ms=int((time.monotonic() - start) * 1000)))
        db.commit()
        return result
    except AIProviderError as e:
        db.add(AICallLog(case_id=case_id, task=task,
                         model=getattr(provider, "model", ""),
                         success=0, latency_ms=int((time.monotonic() - start) * 1000),
                         error=str(e)[:500]))
        db.commit()
        raise
