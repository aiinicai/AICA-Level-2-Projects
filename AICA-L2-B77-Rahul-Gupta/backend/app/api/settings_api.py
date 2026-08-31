"""Settings: AI configuration (encrypted key), profile, preferences."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AppSetting, AuditLog, User
from ..schemas import AISettingsUpdate, ProfileUpdate
from ..services.ai.provider import AIProviderError
from ..services.ai.service import get_ai_config, get_provider, save_ai_config
from .cases import get_demo_user

router = APIRouter()

PREFS_KEY = "preferences"
DEFAULT_PREFS = {
    "default_method": "DCF",
    "default_discount_rate": 12.5,
    "auto_save": True,
    "data_refresh": "Daily",
    "report_language": "English",
    "report_format": "Comprehensive (Default)",
    "currency_display": "INR (₹)",
    "include_benchmarking": True,
    "include_charts": True,
    "include_data_sources": True,
    "notif_valuation_updates": True,
    "notif_system_alerts": True,
    "notif_weekly_insights": False,
    "notif_marketing": False,
}


@router.get("/api/settings")
def get_settings_api(db: Session = Depends(get_db)):
    user = get_demo_user(db)
    prefs_row = db.get(AppSetting, PREFS_KEY)
    prefs = dict(DEFAULT_PREFS) | (prefs_row.value if prefs_row else {})
    return {
        "ai": get_ai_config(db),
        "profile": {"name": user.name, "role": user.role, "email": user.email,
                    "timezone": user.timezone, "date_format": user.date_format,
                    "number_format": user.number_format},
        "preferences": prefs,
    }


@router.put("/api/settings/ai")
def put_ai_settings(body: AISettingsUpdate, db: Session = Depends(get_db)):
    updates = body.model_dump(exclude={"api_key"}, exclude_none=True)
    api_key = body.api_key
    if api_key is not None:
        api_key = api_key.strip()
        if len(api_key) < 20:
            raise HTTPException(422, "API key looks too short to be valid")
    cfg = save_ai_config(db, updates, api_key=api_key)
    if api_key:
        # validate + test connection; report but keep the stored key either way
        provider = get_provider(db)
        connected = False
        error = ""
        if provider:
            try:
                connected = provider.test_connection()
            except AIProviderError as e:
                error = str(e)
        cfg = save_ai_config(db, {"connected": connected} if connected else {})
        row = db.get(AppSetting, "ai_config")
        if row is not None:
            row.value = dict(row.value) | {"connected": connected}
            db.commit()
        cfg = get_ai_config(db)
        cfg["test_error"] = error
    db.add(AuditLog(action="ai_settings_changed",
                    detail={"keys": list(updates.keys()), "key_replaced": bool(api_key)}))
    db.commit()
    return cfg


@router.post("/api/settings/ai/test")
def test_ai(db: Session = Depends(get_db)):
    provider = get_provider(db)
    if provider is None:
        raise HTTPException(409, "No API key configured — add one in Settings first")
    try:
        ok = provider.test_connection()
    except AIProviderError as e:
        raise HTTPException(502, f"Connection test failed: {e}")
    row = db.get(AppSetting, "ai_config")
    if row is not None:
        row.value = dict(row.value) | {"connected": bool(ok)}
        db.commit()
    return {"connected": bool(ok), "model": provider.model}


@router.put("/api/settings/profile")
def put_profile(body: ProfileUpdate, db: Session = Depends(get_db)):
    user = get_demo_user(db)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    db.commit()
    return {"ok": True}


@router.put("/api/settings/preferences")
def put_preferences(body: dict, db: Session = Depends(get_db)):
    row = db.get(AppSetting, PREFS_KEY)
    merged = dict(DEFAULT_PREFS) | (row.value if row else {}) | body
    if row is None:
        db.add(AppSetting(key=PREFS_KEY, value=merged))
    else:
        row.value = merged
    db.commit()
    return merged
