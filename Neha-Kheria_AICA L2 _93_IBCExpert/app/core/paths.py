"""OS-specific paths with no dependency on current working directory."""
from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path

APP_DIR_NAME = "IBC Expert"


def _home() -> Path:
    return Path.home().resolve()


@dataclass(frozen=True)
class AppPaths:
    root: Path
    config: Path
    database: Path
    vault: Path
    backups: Path
    logs: Path
    temp: Path
    trial_primary: Path
    trial_secondary: Path
    public_key: Path

    @classmethod
    def discover(cls, override: Path | str | None = None) -> "AppPaths":
        if override is not None:
            root = Path(override).expanduser().resolve()
            secondary = root / ".protected" / "trial-redundant.bin"
        elif platform.system() == "Windows":
            local = Path(os.environ.get("LOCALAPPDATA", _home() / "AppData" / "Local"))
            roaming = Path(os.environ.get("APPDATA", _home() / "AppData" / "Roaming"))
            root = (local / APP_DIR_NAME).resolve()
            secondary = (roaming / APP_DIR_NAME / "trial-redundant.bin").resolve()
        else:
            root = Path(os.environ.get("XDG_DATA_HOME", _home() / ".local" / "share")) / "ibc-expert"
            secondary = Path(os.environ.get("XDG_STATE_HOME", _home() / ".local" / "state")) / "ibc-expert" / "trial-redundant.bin"
        return cls(
            root=root,
            config=root / "config",
            database=root / "database" / "ibc_expert.sqlite3",
            vault=root / "vault",
            backups=root / "backups",
            logs=root / "logs",
            temp=root / "temp",
            trial_primary=root / "config" / "trial-state.bin",
            trial_secondary=secondary,
            public_key=root / "config" / "licence_public_key.hex",
        )

    def ensure(self) -> None:
        for path in (
            self.root,
            self.config,
            self.database.parent,
            self.vault,
            self.backups,
            self.logs,
            self.temp,
            self.trial_secondary.parent,
        ):
            path.mkdir(parents=True, exist_ok=True)
            try:
                path.chmod(0o700)
            except OSError:
                # Windows ACLs are handled by the user profile and optional DPAPI.
                continue
