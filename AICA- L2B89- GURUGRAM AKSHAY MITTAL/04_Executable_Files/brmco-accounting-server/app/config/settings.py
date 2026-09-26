"""Server Host configuration.

All environment-specific values and secrets are read from environment variables
(or a local ``.env`` file). Nothing secret is ever hard-coded here, and none of
these values are ever sent to a Local Host.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

APPLICATION_NAME = "BRMCo Accounting Hub Server"
APPLICATION_VERSION = "1.0.0"
API_VERSION = "v1"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = Field(default="development", description="development | staging | production")
    log_level: str = "INFO"

    # Oldest Local Host version this server is willing to talk to. Local Hosts
    # read this from GET /version and warn the user when they are too old.
    min_local_version: str = "1.0.0"

    # Comma-separated list of allowed CORS origins. Local Hosts call the server
    # from Python (not from the browser), so this is empty by default.
    cors_origins: str = ""

    # ---- Future-phase secrets (unused in Phase 1, never sent to Local Hosts) ----
    secret_key: SecretStr = SecretStr("")
    ai_api_key: SecretStr = SecretStr("")
    mongodb_uri: SecretStr = SecretStr("")
    mongodb_database: str = "brmco"

    # Selects the repository backend. "memory" needs no external services.
    repository_backend: str = "memory"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
