"""FastAPI application. Build Prompt v2 §2 — app, routers, startup self-check."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import MutableHeaders

from app.clauses.loader import ClauseValidationError, load_clause_set
from app.clauses.model import ClauseSet
from app.config import PROJECT_ROOT, get_settings
from app.routers import clients, documents, engagements, review, rollover
from app.services.auth import CSRF_COOKIE, CSRF_MAX_AGE, issue_csrf_token

logger = logging.getLogger("auditcraft")

_STATE: dict[str, Any] = {}


def get_clause_set() -> ClauseSet:
    """The loaded repository. Raises if the self-check has not run."""
    clause_set = _STATE.get("clause_set")
    if clause_set is None:  # pragma: no cover - only if lifespan was skipped
        raise RuntimeError("clause repository not loaded")
    return clause_set  # type: ignore[no-any-return]


def _sync_catalogue() -> None:
    """Bring `field_catalog` in line with the repository, tolerating a database
    that does not have a schema yet.

    A fresh source checkout has no tables until `alembic upgrade head` runs, and
    refusing to start there would be a worse failure than the one this prevents.
    """
    from sqlalchemy import inspect

    from app.db import SessionLocal, engine
    from app.services.catalog import prune_orphans, sync_field_catalog

    if "field_catalog" not in inspect(engine).get_table_names():
        logger.warning("no field_catalog table yet; run `alembic upgrade head`")
        return

    clause_set = get_clause_set()
    with SessionLocal() as session:
        count = sync_field_catalog(session, clause_set, prune=False)
        kept = prune_orphans(session, clause_set)
        session.commit()
    logger.info("field catalogue synced: %d field(s)", count)
    if kept:
        # Not deleted: a foreign key protects an answered field, and an answer
        # on a live engagement is evidence rather than litter. Cleared
        # deliberately by re-running `scripts/seed.py`.
        logger.warning(
            "%d catalogue field(s) no longer in the repository but already answered: %s",
            len(kept),
            ", ".join(sorted(kept)),
        )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Startup self-check.

    The clause repository is loaded and validated before the first request.
    A malformed repository stops the application here rather than surfacing
    as a defective document later.
    """
    settings = get_settings()
    settings.ensure_directories()

    clause_set = load_clause_set(settings.content_path)
    _STATE["clause_set"] = clause_set

    # The catalogue is what turns a clause into a question on the workspace, and
    # it is derived from the repository — so it belongs to startup, not to a
    # script somebody has to remember. It was built only by `scripts/seed.py`,
    # which meant a copy of the application whose repository had moved on showed
    # the Board's Report as 31 findings blocking export with **no field on the
    # page to answer any of them**: the clauses existed, the document knew they
    # were unanswered, and nothing rendered a control. Reported by the firm's
    # team on 19 August 2026 and reproduced exactly by emptying the catalogue.
    _sync_catalogue()

    logger.info(
        "clause repository loaded: %d clauses, template_version=%s",
        len(clause_set),
        clause_set.manifest.template_version,
    )
    if clause_set.needs_review:
        # Protocol §5: an empty needs_review list is itself a warning sign.
        logger.warning(
            "%d clause(s) flagged needs_review: %s",
            len(clause_set.needs_review),
            ", ".join(c.id for c in clause_set.needs_review),
        )
    yield
    _STATE.clear()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AuditCraft",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.env == "development" else None,
    )

    static_dir = PROJECT_ROOT / "app" / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.middleware("http")
    async def _issue_csrf_cookie(request: Any, call_next: Any) -> Any:
        """Hand every page a CSRF token.

        There is no login to issue one from in a single-user build, so the
        middleware does it. Forms still submit the matching hidden field, so
        another site cannot POST into this one.
        """
        token = request.cookies.get(CSRF_COOKIE)
        issued_now = token is None
        if issued_now:
            token = issue_csrf_token()
            # Made visible to THIS request before it is handled, not only to the
            # next one. Setting it on the response alone is too late for the page
            # being rendered: every template reads
            # `request.cookies.get('auditcraft_csrf')`, so on a fresh
            # installation the first page a user opened carried an empty token in
            # every form, and their first submission failed with "Field
            # required". A refresh hid it, which is how it survived to a
            # packaged build -- found on 21 Aug 2026 by driving the .exe on a
            # clean profile rather than a developer's browser that already had
            # the cookie.
            #
            # Written into the SCOPE's cookie header, not onto
            # `request.cookies`. That dict is cached per Request instance, and
            # the endpoint downstream builds its own Request from the same
            # scope -- so mutating the middleware's copy reaches nothing. The
            # scope is what both share.
            headers = MutableHeaders(scope=request.scope)
            existing = headers.get("cookie")
            headers["cookie"] = (
                f"{existing}; {CSRF_COOKIE}={token}" if existing else f"{CSRF_COOKIE}={token}"
            )

        response = await call_next(request)

        if issued_now:
            response.set_cookie(
                CSRF_COOKIE,
                token,
                max_age=CSRF_MAX_AGE,
                httponly=False,
                samesite="lax",
            )
        return response

    app.include_router(clients.router)
    app.include_router(engagements.router)
    app.include_router(rollover.router)
    app.include_router(review.router)
    app.include_router(documents.router)

    @app.get("/health")
    def health() -> JSONResponse:
        clause_set = get_clause_set()
        return JSONResponse(
            {
                "status": "ok",
                "env": settings.env,
                "template_version": clause_set.manifest.template_version,
                "clauses_loaded": len(clause_set),
                "needs_review": [c.id for c in clause_set.needs_review],
                "pdf_enabled": settings.pdf_enabled,
            }
        )

    @app.exception_handler(ClauseValidationError)
    def _clause_error(_request: Any, exc: ClauseValidationError) -> JSONResponse:
        # §19: never expose a Python stack trace to a user.
        logger.error("clause repository invalid: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "clause repository invalid", "problems": exc.problems},
        )

    return app


app = create_app()
