"""FastAPI application factory.

Run locally with:

    uvicorn webapi.app:app --reload

There is no public self-registration endpoint. On first startup, if the
database has no users at all, a single Administrator account is created
automatically so the system is usable -- see :func:`_bootstrap_admin`. Its
password is either read from ``DOCUFLOW_ADMIN_PASSWORD`` (set this for any
real deployment) or, if unset, randomly generated and printed to the
console exactly once. Nothing ever ships with a hardcoded default password.
"""
from __future__ import annotations

import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from webapi.database import SessionLocal, init_db
from webapi.models import User, UserRole
from webapi.routers import approvals, auth, documents, users
from webapi.security import hash_password


def _bootstrap_admin(db: Session) -> None:
    if db.query(User).count() > 0:
        return
    username = os.environ.get("DOCUFLOW_ADMIN_USERNAME", "admin")
    email = os.environ.get("DOCUFLOW_ADMIN_EMAIL", "admin@example.com")
    password = os.environ.get("DOCUFLOW_ADMIN_PASSWORD")
    generated = password is None
    password = password or secrets.token_urlsafe(16)

    admin = User(username=username, email=email, full_name="Administrator", hashed_password=hash_password(password), role=UserRole.ADMIN)
    db.add(admin)
    db.commit()

    if generated:
        print("=" * 70)
        print("First-run setup: created initial Administrator account.")
        print(f"  Username: {username}")
        print(f"  Password: {password}")
        print("This password is shown only once. Log in and consider creating")
        print("a personal admin account, or set DOCUFLOW_ADMIN_PASSWORD before")
        print("first startup in a real deployment.")
        print("=" * 70)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        _bootstrap_admin(db)
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="CA DocuFlow AI -- Team API",
        description="Multi-user document workflow API (maker-checker, roles, audit trail). "
        "See README.md 'Team Deployment' for setup.",
        version="3.0.0",
        lifespan=_lifespan,
    )

    # CORS is permissive here for local development; a real deployment should
    # restrict allow_origins to the actual web frontend's origin(s).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.environ.get("CORS_ALLOW_ORIGINS", "*").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(documents.router)
    app.include_router(approvals.router)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    # A lightweight, dependency-free (no Node/npm build step) HTML+JS frontend,
    # served same-origin so it needs no CORS configuration to talk to the API
    # above. This is a deliberate, documented substitute for a full React/
    # TypeScript SPA -- see README.md "Team Deployment" for why, and how to
    # replace it with a proper React build later without touching the API.
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="frontend")

    return app


app = create_app()
