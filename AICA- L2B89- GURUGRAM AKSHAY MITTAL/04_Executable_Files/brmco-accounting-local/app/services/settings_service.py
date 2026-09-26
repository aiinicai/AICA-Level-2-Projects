"""Loads and saves the user-editable AppConfig."""
from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from app.config.settings import AppConfig, EnvSettings
from app.database.repositories import SettingsRepository

logger = logging.getLogger("brmco.settings")


class SettingsService:
    def __init__(self, repo: SettingsRepository, env: EnvSettings) -> None:
        self.repo = repo
        self.env = env

    def _defaults(self) -> dict[str, Any]:
        return AppConfig(
            tally_host=self.env.tally_host, tally_port=self.env.tally_port,
            server_base_url=self.env.server_base_url, demo_mode=self.env.demo_mode,
        ).model_dump()

    def get(self) -> AppConfig:
        merged = {**self._defaults(), **{k: v for k, v in self.repo.get_all().items() if k in AppConfig.model_fields}}
        try:
            return AppConfig.model_validate(merged)
        except ValidationError as exc:
            # A corrupt stored value must not take the app down; fall back field by field.
            logger.error("Stored settings invalid, using defaults for bad fields: %s", exc)
            bad = {e["loc"][0] for e in exc.errors() if e.get("loc")}
            return AppConfig.model_validate({k: v for k, v in merged.items() if k not in bad})

    def update(self, changes: dict[str, Any]) -> AppConfig:
        """Validates the complete result before saving anything. Raises ValidationError."""
        current = self.get().model_dump()
        unknown = set(changes) - set(AppConfig.model_fields)
        if unknown:
            raise ValueError(f"Unknown settings: {', '.join(sorted(unknown))}")
        updated = AppConfig.model_validate({**current, **changes})
        self.repo.save_all(updated.model_dump(mode="json"))
        logger.info("Settings updated: %s", ", ".join(sorted(changes)))
        return updated
