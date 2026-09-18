"""Password hashing and JWT session tokens.

Passwords are hashed with bcrypt (via the ``bcrypt`` package directly --
no plaintext password is ever stored or logged). JWTs are signed with a
secret loaded from the ``SECRET_KEY`` environment variable; a random key is
generated for local/dev/test runs if it isn't set, which means tokens
issued by one process won't validate after a restart in that mode -- set
``SECRET_KEY`` explicitly for any real deployment.
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

_SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 8 hours


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False  # malformed hash -- never raise on login, just fail closed


def create_access_token(subject: str, role: str, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": subject, "role": role, "iat": now, "exp": now + timedelta(minutes=expires_minutes)}
    return jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)


class TokenError(Exception):
    pass


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Session expired. Please log in again.") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Invalid session token.") from exc
