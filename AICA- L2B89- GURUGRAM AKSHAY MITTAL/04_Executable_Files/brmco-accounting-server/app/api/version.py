"""GET /version — lets a Local Host check compatibility before using other APIs."""
from __future__ import annotations

from fastapi import APIRouter, Request

from app.config.settings import API_VERSION, APPLICATION_NAME, APPLICATION_VERSION

router = APIRouter(tags=["contract"])

# Features the server offers. Local Hosts enable UI features based on this list,
# so new capabilities can be rolled out without changing the Local Host code path.
FEATURES: dict[str, bool] = {
    "auth": False,
    "ai_invoice_extraction": False,
    "clients": False,
    "central_settings": False,
}


@router.get("/version")
def version(request: Request) -> dict:
    settings = request.app.state.settings
    return {
        "status": "ok",
        "application": APPLICATION_NAME,
        "version": APPLICATION_VERSION,
        "api_version": API_VERSION,
        "min_local_version": settings.min_local_version,
        "environment": settings.environment,
        "features": FEATURES,
    }
