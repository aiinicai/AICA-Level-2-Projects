"""Password hashing, JWT issue/verify, and the current-user dependency.

A simple login gate, not a commercial licensing system — deliberately, per the
project scope. Roles still matter: Board Read-Only must never be able to write.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Role, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user.id), "email": user.email, "role": user.role,
               "name": user.name, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _credentials_error(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail,
                         headers={"WWW-Authenticate": "Bearer"})


def get_current_user(token: str | None = Depends(oauth2_scheme),
                     db: Session = Depends(get_db)) -> User:
    if not token:
        raise _credentials_error()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload.get("sub", 0))
    except (jwt.PyJWTError, ValueError):
        raise _credentials_error("Session expired or invalid. Please sign in again.")

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise _credentials_error("Account is not active.")
    return user


def require_write(user: User = Depends(get_current_user)) -> User:
    """Board Read-Only can look at everything and change nothing."""
    if user.role not in Role.WRITERS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Your role has read-only access.")
    return user


def require_approver(user: User = Depends(get_current_user)) -> User:
    """Second-approver actions: locking a plan, marking it board-approved."""
    if user.role not in Role.APPROVERS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only an Admin or the CFO can approve this.")
    return user
