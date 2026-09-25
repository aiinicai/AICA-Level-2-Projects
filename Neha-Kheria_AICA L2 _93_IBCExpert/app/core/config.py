"""Application configuration loaded from trusted defaults plus local JSON."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from app.core.errors import ConfigurationError


@dataclass(frozen=True)
class AppConfig:
    host: str = "127.0.0.1"
    port: int = 0
    session_minutes: int = 20
    max_upload_mb: int = 100
    max_zip_uncompressed_mb: int = 500
    max_zip_files: int = 2000
    max_zip_ratio: int = 100
    trial_days: int = 30
    clock_rollback_tolerance_minutes: int = 10
    backup_retention: int = 20
    ocr_command: str = "tesseract"
    allow_outbound_integrations: bool = False

    def __post_init__(self) -> None:
        if self.host != "127.0.0.1":
            raise ConfigurationError("IBC Expert must bind only to 127.0.0.1.")
        if not 0 <= self.port <= 65535:
            raise ConfigurationError("Configured port is invalid.")
        if self.trial_days != 30:
            raise ConfigurationError("Trial duration must remain exactly 30 calendar days.")
        for name in ("session_minutes", "max_upload_mb", "max_zip_uncompressed_mb", "max_zip_files", "backup_retention"):
            if getattr(self, name) <= 0:
                raise ConfigurationError(f"{name} must be greater than zero.")
        if self.backup_retention > 100:
            raise ConfigurationError("backup_retention cannot exceed 100.")

    @classmethod
    def load(cls, path: Path) -> "AppConfig":
        if not path.exists():
            return cls()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationError("Application configuration could not be read.") from exc
        allowed = {f.name for f in fields(cls)}
        unknown = set(raw) - allowed
        if unknown:
            raise ConfigurationError(f"Unknown configuration field(s): {', '.join(sorted(unknown))}")
        return cls(**raw)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(self), indent=2, sort_keys=True), encoding="utf-8")
        temp.replace(path)
