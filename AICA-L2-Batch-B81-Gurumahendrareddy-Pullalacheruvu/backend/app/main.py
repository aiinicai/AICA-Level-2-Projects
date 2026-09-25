"""Cash Runway — FastAPI application.

Run locally:

    python seed_db.py                     # load the demonstration dataset
    uvicorn app.main:app --reload         # http://localhost:8000/docs

The API is documented and usable on its own — that was a deliberate
requirement, so the calculation engine can be driven from a script or another
system, not only from this app's own frontend.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import BASE_DIR, settings
from app.database import SessionLocal, init_db
from app.routers import (
    alerts, auth, connect, core, governance, onboarding, registers, scenarios,
    setup, tabs,
)
from app.services.scheduler import daily_sync_loop

log = logging.getLogger("cashrunway")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-7s %(name)s  %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        from app.models import Entity, User

        # An empty database is a dead application: sign-in fails with no
        # explanation, because there is no account to check the password
        # against. Starting the server is what creates the file, so "the file
        # exists" is not evidence that anything is in it. Bootstrap the
        # accounts here — but not the data. Which data to load is the first
        # question the application asks, on the first-run screen.
        from app.seed import seed_users
        made = seed_users(db)
        if made:
            log.warning("No accounts found — created %d sign-in account(s). "
                        "Open http://localhost:8000 to choose what data to load.", made)

        # Alerts moved from WhatsApp to SMS. A database written before that
        # still names the channel "whatsapp" on its rules and its delivery
        # history. The notifier reads the old name as SMS either way, but the
        # Alert Rules screen offers only the new one, so a rule left saying
        # "whatsapp" would show an empty channel box and lose its setting the
        # first time anyone saved it. Rename it once, here.
        from sqlalchemy import text
        renamed = db.execute(text(
            "UPDATE alert_rules SET channels = REPLACE(channels, 'whatsapp', 'sms') "
            "WHERE channels LIKE '%whatsapp%'")).rowcount
        db.execute(text(
            "UPDATE alert_deliveries SET channel = 'sms' WHERE channel = 'whatsapp'"))
        if renamed:
            db.commit()
            log.info("Alert channel renamed from WhatsApp to SMS on %d rule(s).", renamed)

        log.info("Cash Runway ready — %d entity/entities, %d account(s).",
                 db.query(Entity).count(), db.query(User).count())
    finally:
        db.close()

    # The daily Tally pull. Tally cannot push, so this polls; the status banner
    # is honest about how old the data is when a poll was missed.
    task = asyncio.create_task(daily_sync_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Cash command for founders and CFOs.\n\n"
        "Every figure this API returns carries its **basis** (how it was worked out) "
        "and its **as-on date**, and anything a person can click carries a `trace` "
        "descriptor that `/api/trace` replays to show the underlying entries."
    ),
    version=settings.VERSION,
    lifespan=lifespan,
)

from app.middleware import BoardVisibilityMiddleware

# Order matters: this runs inside CORS, on the way back out.
app.add_middleware(BoardVisibilityMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={
        "detail": "Something went wrong working that out. The server log has the "
                  "details.",
        "path": request.url.path,
    })


app.include_router(auth.router)
app.include_router(core.router)
app.include_router(tabs.router)
app.include_router(scenarios.router)
app.include_router(alerts.router)
app.include_router(registers.router)
app.include_router(setup.router)
app.include_router(connect.router)
app.include_router(governance.router)
app.include_router(onboarding.router)


@app.get("/api/health", tags=["core"])
def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.VERSION}


# ---------------------------------------------------------------------------
# Serve the built frontend, when there is one.
#
# A pre-built frontend ships with the application, so running it needs Python
# and nothing else — no Node, no npm install, no second server. During
# development `npm run dev` still runs on :5173 and proxies /api here; this
# mount is simply not used in that case.
# ---------------------------------------------------------------------------
DIST = (BASE_DIR.parent / "frontend" / "dist").resolve()

if (DIST / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        """Serve the single-page app, letting it own its own routing.

        Anything under /api has already been matched by a router above, so a
        request reaching here is either a real file or a client-side route.
        """
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "No such endpoint."})
        candidate = (DIST / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(DIST):
            return FileResponse(candidate)
        return FileResponse(DIST / "index.html")

    log.info("Serving the built frontend from %s", DIST)
else:
    log.warning("No built frontend found at %s — run `npm run build` in frontend/, "
                "or use the dev server on :5173.", DIST)
