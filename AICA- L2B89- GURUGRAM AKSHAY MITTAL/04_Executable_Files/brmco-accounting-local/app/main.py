"""BRMCo Accounting Hub — Local Host entry point.

Run:
    uvicorn app.main:app --host 127.0.0.1 --port 8000
Then open http://127.0.0.1:8000 in a browser.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import api_router
from app.config.logging_config import configure_logging
from app.config.settings import APP_NAME, APP_VERSION, PROJECT_ROOT, EnvSettings, get_env_settings
from app.container import build_container
from app.services.errors import UserError

logger = logging.getLogger("brmco.app")


def create_app(env: EnvSettings | None = None) -> FastAPI:
    env = env or get_env_settings()
    env.ensure_dirs()
    configure_logging(env.log_dir, env.log_level)

    app = FastAPI(title=f"{APP_NAME} — Local Host", version=APP_VERSION,
                  description="Runs on the client computer. Talks to Excel files, local TallyPrime and SQLite.")
    app.state.container = build_container(env)

    @app.exception_handler(UserError)
    async def user_error(_: Request, exc: UserError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(RequestValidationError)
    async def bad_request(_: Request, exc: RequestValidationError) -> JSONResponse:
        messages = []
        for err in exc.errors()[:5]:
            loc = [p for p in err.get("loc", []) if p != "body"]
            # ["ledgers", 0, "name"] -> "Line 1 name"
            if len(loc) >= 2 and isinstance(loc[1], int):
                loc = [f"Line {loc[1] + 1}", *loc[2:]]
            where = " ".join(str(p).replace("_", " ") for p in loc)
            msg = str(err.get("msg", "")).removeprefix("Value error, ")
            messages.append(f"{where}: {msg}" if where else msg)
        return JSONResponse(status_code=422, content={"detail": "; ".join(messages) or "Invalid request."})

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception) -> JSONResponse:
        ref = uuid.uuid4().hex[:8]
        logger.exception("Unhandled error ref=%s on %s %s", ref, request.method, request.url.path)
        return JSONResponse(status_code=500, content={
            "detail": f"Something went wrong on our side (reference {ref}). Details are in logs/errors.log."})

    app.include_router(api_router)
    app.mount("/", StaticFiles(directory=PROJECT_ROOT / "frontend", html=True), name="frontend")

    logger.info("%s Local Host %s started. Data folder: %s", APP_NAME, APP_VERSION, env.data_dir)
    return app


app = create_app()
