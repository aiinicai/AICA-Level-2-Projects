"""Wires repositories and services together (simple dependency container)."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from app.config.settings import EnvSettings
from app.database.database import Database
from app.database.repositories import (
    AuditRepository, BatchRepository, HistoryRepository, MasterRepository, SettingsRepository,
)
from app.server_client.client import ServerClient
from app.services.audit_service import AuditService
from app.services.import_service import ImportService
from app.services.settings_service import SettingsService
from app.services.tally_service import TallyService


@dataclass
class Container:
    env: EnvSettings
    db: Database
    settings: SettingsService
    audit: AuditService
    history: HistoryRepository
    audit_repo: AuditRepository
    tally: TallyService
    imports: ImportService

    def server_client(self) -> ServerClient:
        return ServerClient(self.settings.get().server_base_url, timeout=self.env.server_timeout_seconds)


def build_container(env: EnvSettings) -> Container:
    env.ensure_dirs()
    db = Database(env.db_path)
    db.initialise()
    settings = SettingsService(SettingsRepository(db), env)
    audit_repo = AuditRepository(db)
    audit = AuditService(audit_repo)
    history = HistoryRepository(db)
    tally = TallyService(env, MasterRepository(db), audit)
    imports = ImportService(env, settings, BatchRepository(db), history, tally, audit)
    return Container(env, db, settings, audit, history, audit_repo, tally, imports)


def get_container(request: Request) -> Container:
    return request.app.state.container
