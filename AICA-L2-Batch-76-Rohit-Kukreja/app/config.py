"""Application configuration. Build Prompt v2 §1 — pydantic-settings + .env."""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _bundle_root() -> Path:
    """Where the read-only assets live: clauses, templates, static files.

    Under PyInstaller these are unpacked to a temporary directory named by
    `sys._MEIPASS`, which is deleted when the process exits. Nothing writable
    may ever go there.
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def _user_data_root() -> Path:
    """Where this installation's own data lives: the database and documents.

    Beside the source tree when running from source, and under
    %LOCALAPPDATA%/AuditCraft when frozen -- never beside the .exe, which may
    sit on a read-only share or in Program Files, and never inside the bundle,
    which is deleted on exit.
    """
    if getattr(sys, "frozen", False):
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
        return Path(base) / "AuditCraft"
    return _bundle_root()


PROJECT_ROOT = _bundle_root()
USER_DATA_ROOT = _user_data_root()


class Settings(BaseSettings):
    """Every runtime knob. No network endpoints exist by design (§18.1)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AUDITCRAFT_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "development"
    host: str = "127.0.0.1"
    port: int = 8000
    # Not a secret — a deliberately invalid placeholder. run.py refuses to
    # start outside development while it is still set.
    secret_key: str = "change-me-before-first-run"  # noqa: S105

    # Relative paths resolve against USER_DATA_ROOT, so the same default is
    # correct from source and from a frozen build.
    database_url: str = "sqlite:///data/auditcraft.db"

    content_dir: Path = Field(default=Path("content"))
    data_dir: Path = Field(default=Path("data"))
    document_dir: Path = Field(default=Path("data/documents"))

    soffice_path: str = ""

    @property
    def content_path(self) -> Path:
        return self._absolute(self.content_dir)

    @property
    def data_path(self) -> Path:
        return self._writable(self.data_dir)

    @property
    def document_path(self) -> Path:
        return self._writable(self.document_dir)

    @property
    def pdf_enabled(self) -> bool:
        """PDF is optional; absence must degrade gracefully (§1)."""
        return bool(self.soffice_path) and Path(self.soffice_path).exists()

    @staticmethod
    def _absolute(p: Path) -> Path:
        """A read-only asset, shipped with the application."""
        return p if p.is_absolute() else (PROJECT_ROOT / p).resolve()

    @staticmethod
    def _writable(p: Path) -> Path:
        """Somewhere this installation may write. See `_user_data_root`."""
        return p if p.is_absolute() else (USER_DATA_ROOT / p).resolve()

    def ensure_directories(self) -> None:
        for path in (self.data_path, self.document_path):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
