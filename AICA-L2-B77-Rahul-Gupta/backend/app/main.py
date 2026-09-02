"""CompanyVal AI — FastAPI application entrypoint."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import Base, engine
from . import models  # noqa: F401 — register all models
from .api import cases, documents, engine as engine_api, interview, settings_api

logging.basicConfig(level=logging.INFO)
# Defence in depth: the root logger at INFO makes third-party libraries verbose, and
# httpx logs every request URL. Provider credentials must never ride in a URL (see
# gemini.py), but keep the transport layer quiet so a future call site can't leak one.
for _noisy in ("httpx", "httpcore"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

settings = get_settings()

app = FastAPI(
    title="CompanyVal AI",
    description="AI-Assisted Business Valuation — Upload. Understand. Question. "
                "Simulate. Value.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cases.router, tags=["cases"])
app.include_router(documents.router, tags=["documents"])
app.include_router(interview.router, tags=["interview"])
app.include_router(engine_api.router, tags=["valuation"])
app.include_router(settings_api.router, tags=["settings"])


@app.get("/", include_in_schema=False)
def root() -> dict:
    """Signpost for anyone who opens the API port in a browser.

    This is the API, not the app. Hitting :8000 expecting the UI and getting a
    bare {"detail":"Not Found"} reads like the backend is broken when it is
    running perfectly, so say where the app actually is.
    """
    return {
        "service": "CompanyVal AI API",
        "status": "ok",
        "message": "This is the API, not the web app. Open the frontend to use "
                   "CompanyVal AI; browse the API here.",
        "app_url": settings.frontend_url,
        "api_docs": "/docs",
        "openapi": "/openapi.json",
    }


@app.on_event("startup")
def startup() -> None:
    # Alembic manages migrations in production; create_all covers local dev.
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}
