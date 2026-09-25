"""In-memory authenticated session manager with inactivity expiration.

Master keys never persist in the database or browser cookie. The browser receives only
an opaque high-entropy token; the server stores a SHA-256 token digest and key material
for the lifetime of the desktop process.
"""
from __future__ import annotations

import hashlib
import secrets
import threading
from dataclasses import dataclass
from datetime import timedelta

from app.core.errors import AuthenticationError
from app.core.time import Clock, SystemClock


@dataclass
class Session:
    user_id: int
    username: str
    master_key: bytes
    created_at: object
    last_seen_at: object


class SessionManager:
    def __init__(self, idle_minutes: int = 20, clock: Clock | None = None) -> None:
        if idle_minutes <= 0:
            raise ValueError("idle_minutes must be positive")
        self.idle = timedelta(minutes=idle_minutes)
        self.clock = clock or SystemClock()
        self._sessions: dict[str, Session] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode("ascii")).hexdigest()

    def create(self, user_id: int, username: str, master_key: bytes) -> str:
        if len(master_key) != 32:
            raise ValueError("master key must contain 32 bytes")
        token = secrets.token_urlsafe(48)
        now = self.clock.now()
        with self._lock:
            self._sessions[self._digest(token)] = Session(user_id, username, master_key, now, now)
        return token

    def require(self, token: str | None) -> Session:
        if not token:
            raise AuthenticationError("Authentication is required.")
        digest = self._digest(token)
        now = self.clock.now()
        with self._lock:
            session = self._sessions.get(digest)
            if not session:
                raise AuthenticationError("Your session is no longer valid. Please sign in again.")
            if now - session.last_seen_at > self.idle:
                self._sessions.pop(digest, None)
                raise AuthenticationError("Your session expired due to inactivity. Please sign in again.")
            session.last_seen_at = now
            return session

    def revoke(self, token: str | None) -> None:
        if not token:
            return
        with self._lock:
            self._sessions.pop(self._digest(token), None)

    def revoke_user(self, user_id: int) -> None:
        with self._lock:
            for digest in [k for k, v in self._sessions.items() if v.user_id == user_id]:
                self._sessions.pop(digest, None)

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()
