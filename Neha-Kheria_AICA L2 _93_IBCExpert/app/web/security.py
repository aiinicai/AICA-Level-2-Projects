"""HTTP security primitives for the localhost-only application UI."""
from __future__ import annotations

import hmac
import secrets
from dataclasses import dataclass

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

SESSION_COOKIE = "ibc_session"
CSRF_COOKIE = "ibc_csrf"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; "
            "form-action 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
            "connect-src 'self'; font-src 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        return response


@dataclass(frozen=True)
class CsrfManager:
    """Double-submit CSRF tokens scoped to localhost sessions.

    The random token is held in a SameSite=Strict cookie and must also be submitted in a
    form field or X-CSRF-Token header. Session authentication itself remains an opaque
    HttpOnly cookie. This separates authentication and CSRF material.
    """

    cookie_name: str = CSRF_COOKIE

    def issue(self) -> str:
        return secrets.token_urlsafe(32)

    def validate(self, request: Request, submitted: str | None) -> None:
        cookie = request.cookies.get(self.cookie_name)
        if not cookie or not submitted or not hmac.compare_digest(cookie, submitted):
            raise HTTPException(status_code=403, detail="The security token is invalid or expired. Reload the page and try again.")


def set_auth_cookies(response: Response, session_token: str, csrf_token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        session_token,
        httponly=True,
        secure=False,  # loopback HTTP; never exposed beyond 127.0.0.1
        samesite="strict",
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        httponly=False,
        secure=False,
        samesite="strict",
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
