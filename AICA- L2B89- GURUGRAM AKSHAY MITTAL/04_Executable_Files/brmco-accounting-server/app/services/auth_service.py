"""Authentication service (Phase 5).

Will issue tokens to staff users and to registered Local Host installations.
Uses SECRET_KEY from the server environment; the key never leaves the server.
"""
from __future__ import annotations

from app.repositories.base import DocumentRepository


class AuthService:
    def __init__(self, users: DocumentRepository, devices: DocumentRepository) -> None:
        self._users = users
        self._devices = devices
