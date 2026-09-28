"""Lease116 web application (FastAPI) — serves the API and the offline single-page UI."""
from __future__ import annotations

import logging
import os
import secrets
import threading
import webbrowser
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .api import admin, extract, leases, reports
from .db.base import get_engine, init_db, session_scope
from .db.seed import seed_defaults
from .services.lease_service import ServiceError

log = logging.getLogger("lease116")
_server = None  # the uvicorn server started by run(); lets the Lease116.exe launcher stop it cleanly


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_engine()
    init_db()
    with session_scope() as db:
        seed_defaults(db)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=config.APP_TITLE, version=config.APP_VERSION, docs_url="/api/docs", redoc_url=None,
                  openapi_url="/api/openapi.json", lifespan=lifespan)
    for r in (admin.router, leases.router, extract.router, reports.router):
        app.include_router(r)

    @app.exception_handler(ServiceError)
    async def _svc(request: Request, exc: ServiceError):
        return JSONResponse(status_code=exc.status, content={"detail": {"message": exc.message, "issues": exc.issues}})

    @app.middleware("http")
    async def _revalidate_static(request: Request, call_next):
        # the UI is served from this PC: ask the browser to revalidate app code (ETag) so upgrades take effect at once
        response = await call_next(request)
        p = request.url.path
        if p.startswith("/static/js/") or p.startswith("/static/css/"):
            response.headers["Cache-Control"] = "no-cache"
        return response

    app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(config.STATIC_DIR / "index.html", headers={"Cache-Control": "no-cache"})

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon():
        return FileResponse(config.STATIC_DIR / "img" / "favicon.svg", media_type="image/svg+xml")

    @app.get("/api/health", include_in_schema=False)
    def health():
        return {"status": "ok", "version": config.APP_VERSION}

    @app.post("/api/system/shutdown", include_in_schema=False)
    def shutdown(request: Request):
        """Stop the server. Only the Lease116.exe launcher that started it can do this: it passes a random per-launch
        token in LEASE116_LAUNCHER_TOKEN and sends it back in a custom header (which a web page cannot forge)."""
        token = os.environ.get("LEASE116_LAUNCHER_TOKEN", "")
        given = request.headers.get("x-lease116-token", "")
        if not token or not secrets.compare_digest(given.encode(), token.encode()):
            raise HTTPException(status_code=403, detail="Not allowed")
        if _server is not None:
            _server.should_exit = True
        return {"status": "stopping"}

    return app


app = create_app()


def _already_running(url: str) -> bool:
    """True if a Lease116 server already answers on this port (second launch just opens the browser)."""
    import json
    import urllib.request
    try:
        with urllib.request.urlopen(url + "api/health", timeout=1.5) as r:
            return json.loads(r.read().decode("utf-8")).get("status") == "ok"
    except Exception:
        return False


def run(open_browser: bool = True):
    global _server
    import socket

    import uvicorn

    url = f"http://{config.HOST}:{config.PORT}/"
    if _already_running(url):
        print(f"\n  Lease116 is already running at {url} — opening it in the browser.\n")
        if open_browser:
            webbrowser.open(url)
        return
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex((config.HOST, config.PORT)) == 0:
            print(f"\n  Port {config.PORT} is used by another program. Close it, or set LEASE116_PORT to a free port.\n")
            raise SystemExit(1)
    if open_browser:
        threading.Timer(1.8, lambda: webbrowser.open(url)).start()
    how_to_stop = ("Started by Lease116.exe - stop it from the Lease116 icon next to the clock (right-click > Stop Lease116)."
                   if os.environ.get("LEASE116_LAUNCHER_TOKEN") else
                   "Keep this window open while you work; close it (or press Ctrl+C) to stop the app.")
    print(f"\n  Lease116 v{config.APP_VERSION} is running at {url}\n  Data folder: {config.DATA_DIR}\n  {how_to_stop}\n")
    _server = uvicorn.Server(uvicorn.Config(app, host=config.HOST, port=config.PORT, log_level="warning"))
    _server.run()
