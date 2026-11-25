"""FastAPI application. Run: python -m noticemate.api.main  (binds 127.0.0.1 by default)."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..core.config import SUBSCRIPTION_DISCLOSURE, get_settings
from ..core.db import init_db
from ..core.errors import NoticeMateError
from ..core.logging_setup import get_logger
from ..services.authorities import import_registry
from ..services.taxlaw import seed_registry
from .routers import analysis_routes, core_routes, output_routes, v2_routes, v3_routes

log = get_logger("api")


def create_app() -> FastAPI:
    s = get_settings()
    init_db()
    seed_registry()
    import_registry()
    app = FastAPI(title="NOTICE-MATE", version="3.0.0-dev",
                  description="Local-first Income-tax notice analysis assistant for CAs. " + SUBSCRIPTION_DISCLOSURE)
    app.add_middleware(CORSMiddleware, allow_origins=[s.ui_origin], allow_methods=["GET", "POST", "PUT", "DELETE"],
                       allow_headers=["Authorization", "Content-Type"], allow_credentials=False)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        resp = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["Referrer-Policy"] = "no-referrer"
        return resp

    @app.exception_handler(NoticeMateError)
    async def domain_error(_: Request, exc: NoticeMateError):
        return JSONResponse(status_code=exc.status_code, content={"error": exc.code, "message": exc.message, "details": exc.details})

    @app.exception_handler(RequestValidationError)
    async def req_validation(_: Request, exc: RequestValidationError):
        errs = [{"loc": e.get("loc"), "msg": e.get("msg")} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"error": "validation_error", "message": "Invalid request.", "details": {"errors": errs}})

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception):
        log.exception("Unhandled error: %s", type(exc).__name__)
        return JSONResponse(status_code=500, content={"error": "internal_error", "message": "Internal error. See local log."})

    @app.get("/health")
    def health():
        return {"status": "ok", "local_only": s.api_host in ("127.0.0.1", "localhost", "::1")}

    for r in (core_routes.router, analysis_routes.router, output_routes.router, v2_routes.router, v3_routes.router):
        app.include_router(r, prefix="/api")
    return app


app = create_app()

if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    s = get_settings()
    if s.api_host not in ("127.0.0.1", "localhost", "::1"):
        log.warning("API is bound to a non-loopback address (%s). Use only on a trusted network behind TLS.", s.api_host)
    uvicorn.run("noticemate.api.main:app", host=s.api_host, port=s.api_port, reload=False)
