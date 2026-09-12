"""Response middleware that enforces the board's visibility policy.

This sits at the edge rather than inside each service for one reason: a rule
that has to be remembered in forty places is a rule that will be forgotten in
one of them, and the one that gets forgotten is the leak. Masking every
response on the way out means a new endpoint is covered the day it is written.

The engine below it is untouched, so the board and the CFO are always reading
the same computation — which is exactly the property the tool cannot afford to
lose.
"""
from __future__ import annotations

import json
import logging

import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.config import settings
from app.database import SessionLocal
from app.models import Role, User
from app.services import boardmask

log = logging.getLogger("cashrunway.mask")

# Never masked: the board still needs to sign in, know who it is, and see the
# same headline strip everyone else does.
EXEMPT_PREFIXES = ("/api/auth", "/api/health", "/api/onboarding")


def _user_from_request(db, request) -> User | None:
    auth = request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        return None
    try:
        payload = jwt.decode(auth[7:], settings.SECRET_KEY,
                             algorithms=[settings.ALGORITHM])
        return db.get(User, int(payload.get("sub", 0)))
    except Exception:
        return None


class BoardVisibilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        if not path.startswith("/api/") or path.startswith(EXEMPT_PREFIXES):
            return await call_next(request)

        db = SessionLocal()
        try:
            user = _user_from_request(db, request)
            if not user or user.role != Role.BOARD:
                return await call_next(request)

            policy = boardmask.load_policy(db)

            # A screen the board is kept off returns a sentence, not a blank.
            for blocked, reason in boardmask.blocked_endpoints(policy).items():
                if path.startswith(blocked):
                    return JSONResponse(status_code=403, content={
                        "detail": reason, "restricted": True})

            response = await call_next(request)
            if response.status_code >= 400:
                return response
            if "application/json" not in (response.headers.get("content-type") or ""):
                return response

            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            try:
                payload = json.loads(body)
            except (ValueError, UnicodeDecodeError):
                return Response(content=body, status_code=response.status_code,
                                headers=dict(response.headers),
                                media_type=response.media_type)

            entity_id = request.query_params.get("entity_id")
            masked = boardmask.mask_payload(
                db, user, payload,
                entity_id=int(entity_id) if entity_id and entity_id.isdigit() else None)

            out = JSONResponse(content=masked, status_code=response.status_code)
            # Content-Length changes once values are replaced; let Starlette
            # recompute it rather than copying a stale header through.
            for k, v in response.headers.items():
                if k.lower() not in ("content-length", "content-type"):
                    out.headers[k] = v
            return out
        except Exception:
            log.exception("Board masking failed on %s — refusing rather than "
                          "returning unmasked data.", path)
            return JSONResponse(status_code=500, content={
                "detail": "Could not apply the board visibility policy, so this "
                          "screen was not shown. Tell the CFO — this is a fault, "
                          "not a restriction."})
        finally:
            db.close()
