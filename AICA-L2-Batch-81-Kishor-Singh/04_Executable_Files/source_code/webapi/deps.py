"""FastAPI dependencies: DB session, current-user resolution, role guards.

Every protected endpoint depends on :func:`get_current_user`, which
validates the bearer JWT and loads the real user row from the database on
every request -- a deactivated user's existing token stops working
immediately, rather than remaining valid until it expires.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from webapi.database import get_db
from webapi.models import User, UserRole
from webapi.security import TokenError, decode_access_token

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated.")
    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    user = db.get(User, payload.get("sub"))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer active.")
    return user


def require_roles(*roles: UserRole):
    """Dependency factory: raises 403 unless the current user has one of ``roles``."""

    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles and user.role != UserRole.ADMIN:
            allowed = ", ".join(r.value for r in roles)
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires one of these roles: {allowed}.")
        return user

    return _checker
