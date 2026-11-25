"""FastAPI application factory."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app import __version__
from app.core.config import PROJECT_ROOT, get_settings
from app.db import get_engine, session_scope
from app.services.init_db import init_db
from app.services.settings_service import get_business_settings
from app.web.deps import Forbidden, LoginRequired, PasswordChangeRequired

STATIC_DIR = PROJECT_ROOT / "app" / "static"

# Everything is served by this app; nothing is loaded from other hosts.
# 'unsafe-eval' is needed by the standard Alpine.js build (it evaluates x-data expressions).
CSP = ("default-src 'self'; script-src 'self' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'; "
       "object-src 'none'")


def _daily_backup_loop(stop) -> None:
    """While the app runs: make one encrypted backup per day (checked every hour)."""
    import logging

    from app.services.audit import audit
    from app.services.backup import backed_up_today, create_backup
    log = logging.getLogger("cff.backup")
    while not stop.is_set():
        try:
            if not backed_up_today():
                path = create_backup(note="automatic daily")
                with session_scope() as db:
                    audit(db, "backup.create", "backup", path.name, after={"automatic": True})
                log.info("Daily backup written: %s", path)
        except Exception as exc:                                  # never stop the app over a backup
            log.error("Daily backup failed: %s", exc)
        stop.wait(3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import threading
    stop = threading.Event()
    if get_settings().auto_backup:
        threading.Thread(target=_daily_backup_loop, args=(stop,), daemon=True, name="daily-backup").start()
    yield
    stop.set()


def create_app() -> FastAPI:
    settings = get_settings()
    init_db(get_engine())
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        docs_url=None,  # no public API explorer; this is an internal tool
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        resp = await call_next(request)
        resp.headers.setdefault("Content-Security-Policy", CSP)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        resp.headers.setdefault("Cache-Control", "no-store" if not request.url.path.startswith("/static")
                                else "public, max-age=3600")
        if settings.https_enabled:
            resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        return resp

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie="cff_session",
        max_age=settings.session_max_age_minutes * 60,
        same_site="strict",
        https_only=settings.https_enabled,
    )
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.exception_handler(LoginRequired)
    async def _login(request: Request, exc: LoginRequired):
        if request.headers.get("hx-request"):
            from fastapi.responses import Response
            return Response(status_code=204, headers={"HX-Redirect": "/login"})
        nxt = request.url.path if request.method == "GET" else "/"
        return RedirectResponse(f"/login?next={nxt}", status_code=303)

    @app.exception_handler(PasswordChangeRequired)
    async def _pw(request: Request, exc: PasswordChangeRequired):
        if request.headers.get("hx-request"):
            # Never answer a background (HTMX) request with a whole page: that page would be
            # swapped into a small element (e.g. the menu badge) and load itself again and again.
            from fastapi.responses import Response
            return Response(status_code=204, headers={"HX-Redirect": "/account/password"})
        return RedirectResponse("/account/password", status_code=303)

    @app.exception_handler(Forbidden)
    async def _forbidden(request: Request, exc: Forbidden):
        from app.web.templating import render
        if request.headers.get("hx-request"):
            from fastapi.responses import HTMLResponse
            return HTMLResponse(f'<div class="alert alert-danger py-1 my-1">{exc.message}</div>', status_code=200,
                                headers={"HX-Reswap": "innerHTML"})
        return render(request, "error.html", {"title": "Not allowed", "message": exc.message}, status_code=403)

    from app.routers import admin, auth, data, exports, forecast, pdcs, review
    for r in (auth, forecast, pdcs, data, admin, exports, review):
        app.include_router(r.router)

    @app.get("/healthz")
    def healthz() -> dict:
        with session_scope() as db:
            b = get_business_settings(db)
        return {
            "status": "ok",
            "version": __version__,
            "https": settings.https_enabled,
            "database": settings.database_path.name,
            "business_defaults": b.model_dump(),
        }

    return app


app = create_app()
