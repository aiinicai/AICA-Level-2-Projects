"""GET /health — liveness check used by Local Hosts and load balancers."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Request

from app.config.settings import APPLICATION_NAME, APPLICATION_VERSION

router = APIRouter(tags=["contract"])


@router.get("/health")
def health(request: Request) -> dict:
    repositories = request.app.state.repositories
    return {
        "status": "ok",
        "application": APPLICATION_NAME,
        "version": APPLICATION_VERSION,
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "components": {"repository": repositories.backend_name},
    }
