"""BRMCo Accounting Hub — Server Host entry point.

Run (development):
    uvicorn app.main:app --host 0.0.0.0 --port 8001

The Server Host never talks to TallyPrime. Tally stays on the client's machine
and is reached only by the Local Host.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import ai, auth, clients, health, settings as settings_api, users, version
from app.config.logging_config import configure_logging
from app.config.settings import APPLICATION_NAME, APPLICATION_VERSION, Settings, get_settings
from app.repositories.factory import build_repositories

logger = logging.getLogger("brmco.server")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=APPLICATION_NAME,
        version=APPLICATION_VERSION,
        description="Central services for BRMCo Accounting Hub. Phase 1 exposes health and version only.",
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
    )
    app.state.settings = settings
    app.state.repositories = build_repositories(settings)

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["*"],
        )

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        ref = uuid.uuid4().hex[:10]
        logger.exception("Unhandled error ref=%s path=%s", ref, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error", "reference": ref})

    # Contract endpoints (unversioned, stable forever).
    app.include_router(health.router)
    app.include_router(version.router)

    # Future modules, versioned.
    prefix = "/api/v1"
    app.include_router(auth.router, prefix=f"{prefix}/auth", tags=["auth (future)"])
    app.include_router(ai.router, prefix=f"{prefix}/ai", tags=["ai (future)"])
    app.include_router(users.router, prefix=f"{prefix}/users", tags=["users (future)"])
    app.include_router(clients.router, prefix=f"{prefix}/clients", tags=["clients (future)"])
    app.include_router(settings_api.router, prefix=f"{prefix}/settings", tags=["settings (future)"])

    logger.info("%s %s started (environment=%s)", APPLICATION_NAME, APPLICATION_VERSION, settings.environment)
    return app


app = create_app()
