"""Client registry service (Phase 5)."""
from __future__ import annotations

from app.repositories.base import DocumentRepository


class ClientService:
    def __init__(self, clients: DocumentRepository) -> None:
        self._clients = clients
