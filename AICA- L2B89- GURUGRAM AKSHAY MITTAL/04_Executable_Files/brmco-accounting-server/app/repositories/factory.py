"""Builds the repository set for the configured backend."""
from __future__ import annotations

from dataclasses import dataclass

from app.config.settings import Settings
from app.repositories.base import DocumentRepository
from app.repositories.memory import InMemoryRepository


@dataclass
class Repositories:
    backend_name: str
    users: DocumentRepository
    clients: DocumentRepository
    devices: DocumentRepository


def build_repositories(settings: Settings) -> Repositories:
    backend = settings.repository_backend.lower()
    if backend == "memory":
        return Repositories("memory", InMemoryRepository(), InMemoryRepository(), InMemoryRepository())
    if backend == "mongodb":
        # Phase 5: return MongoRepository(db["users"]), ... using settings.mongodb_uri
        raise NotImplementedError("MongoDB backend is planned for Phase 5. Use REPOSITORY_BACKEND=memory.")
    raise ValueError(f"Unknown REPOSITORY_BACKEND '{settings.repository_backend}'")
