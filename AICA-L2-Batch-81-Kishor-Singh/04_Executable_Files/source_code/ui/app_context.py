"""Shared application context passed to every tab: config, database, logger."""
from __future__ import annotations

from dataclasses import dataclass

from utils.config_manager import ConfigManager
from utils.database import Database


@dataclass
class AppContext:
    config: ConfigManager
    database: Database
    operator: str = ""

    @staticmethod
    def create() -> "AppContext":
        config = ConfigManager()
        database = Database(config.get_database_path())
        return AppContext(config=config, database=database, operator=config.settings.operator_name)
