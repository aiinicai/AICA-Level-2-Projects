from __future__ import annotations

from fastapi import Header

from ..core.errors import AuthError
from ..services import auth


def bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("Missing bearer token.")
    return authorization.split(" ", 1)[1].strip()


def current_user(authorization: str | None = Header(default=None)) -> dict:
    return auth.authenticate(bearer(authorization))
