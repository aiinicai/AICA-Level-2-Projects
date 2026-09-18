"""User-preference persistence (JSON, non-sensitive settings only).

Settings live in the user's per-app data directory (``%APPDATA%\\PDFOfficeUtility``
on Windows) so a portable/read-only installation of the program folder still
works, and so re-installing the app doesn't wipe user preferences.

No password, certificate PIN or document password is ever written here --
see the README security section.
"""
from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

from config.app_config import APP_SHORT_NAME
from models.enums import CollisionPolicy, NamingMode, ThemeMode, WordEngine

#: Previous values of APP_SHORT_NAME, oldest first. The app was originally
#: shipped as "PDF Office Utility" (folder name "PDFOfficeUtility") before
#: being rebranded to "CA DocuFlow AI" -- without this list, a rebrand
#: silently strands every existing user's settings, templates, recent-jobs
#: history, and audit log in the old folder, and the app quietly starts
#: over with defaults instead. Add the previous name here on any future
#: rebrand, so upgrading users are migrated forward exactly once.
_LEGACY_APP_SHORT_NAMES = ["PDFOfficeUtility"]

#: Files/folders carried over from a legacy app-data folder on first run.
_MIGRATED_ENTRIES = ["settings.json", "app_data.db", "logs"]


def _migrate_legacy_app_data(base: Path, app_dir: Path) -> None:
    """One-time copy of settings/database/logs from a previous app name's
    data folder into the current one, if the current one is still empty.

    Never touches or deletes the legacy folder -- this is a copy, not a
    move, so a user who somehow still needs the old app version isn't
    affected. Safe to call on every startup: it only acts the first time
    (before ``settings.json`` exists in the new folder).
    """
    if (app_dir / "settings.json").exists():
        return  # already migrated (or a fresh, deliberately-empty install)

    for legacy_name in _LEGACY_APP_SHORT_NAMES:
        legacy_dir = base / legacy_name
        if not legacy_dir.is_dir():
            continue
        for entry_name in _MIGRATED_ENTRIES:
            source = legacy_dir / entry_name
            dest = app_dir / entry_name
            if not source.exists() or dest.exists():
                continue
            try:
                if source.is_dir():
                    shutil.copytree(source, dest)
                else:
                    shutil.copy2(source, dest)
            except OSError:
                pass  # best-effort -- a partial/failed migration must never block startup
        if (app_dir / "settings.json").exists():
            return  # migrated from this legacy folder; don't also merge older ones


def get_app_data_dir() -> Path:
    """Return (and create) the per-user application data directory."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path.home() / ".config"
    app_dir = base / APP_SHORT_NAME
    app_dir.mkdir(parents=True, exist_ok=True)
    _migrate_legacy_app_data(base, app_dir)
    return app_dir


@dataclass
class AppSettings:
    """All persisted, non-sensitive user preferences, with sensible defaults."""

    default_output_folder: str = str(Path.home() / "Documents" / "Signed Documents")
    default_signature_image: str = ""
    default_template_name: str = ""
    naming_mode: str = NamingMode.ADD_SUFFIX.value
    naming_suffix: str = "_Signed"
    naming_prefix: str = "Signed_"
    collision_policy: str = CollisionPolicy.RENAME.value
    remember_last_folder: bool = True
    last_used_folder: str = str(Path.home())
    confirm_before_overwrite: bool = True
    open_output_folder_after_completion: bool = True
    word_conversion_engine: str = WordEngine.AUTO.value
    theme: str = ThemeMode.SYSTEM.value
    temp_folder: str = ""  # empty => system temp
    enable_activity_register: bool = True
    operator_name: str = os.environ.get("USERNAME", "") if os.name == "nt" else ""
    libreoffice_path: str = ""  # optional override, empty => search PATH

    # -- OCR (core.ocr_engine) --
    tesseract_path: str = ""  # optional override, empty => search PATH/well-known locations
    ocr_default_language: str = "eng"
    ocr_default_dpi: int = 300
    ocr_skip_pages_with_text: bool = True

    # -- AI Assistant (core.ai_provider) -- API keys are NEVER stored here; see keyring.
    ai_provider: str = "Anthropic (Claude)"
    ai_model: str = ""  # empty => use core.ai_provider.DEFAULT_MODELS for the selected provider
    ai_ollama_base_url: str = "http://localhost:11434"

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "AppSettings":
        defaults = AppSettings()
        merged = {**asdict(defaults), **{k: v for k, v in data.items() if k in asdict(defaults)}}
        return AppSettings(**merged)


class ConfigManager:
    """Loads/saves :class:`AppSettings` to ``settings.json`` in the app data dir."""

    def __init__(self, app_data_dir: Path | None = None):
        self.app_data_dir = app_data_dir or get_app_data_dir()
        self.settings_path = self.app_data_dir / "settings.json"
        self.settings: AppSettings = self._load()

    def _load(self) -> AppSettings:
        if self.settings_path.exists():
            try:
                data = json.loads(self.settings_path.read_text(encoding="utf-8"))
                return AppSettings.from_dict(data)
            except (json.JSONDecodeError, OSError):
                pass
        return AppSettings()

    def save(self) -> None:
        self.settings_path.write_text(
            json.dumps(self.settings.to_dict(), indent=2), encoding="utf-8"
        )

    def get_output_folder(self) -> Path:
        folder = Path(self.settings.default_output_folder)
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def get_temp_folder(self) -> Path | None:
        return Path(self.settings.temp_folder) if self.settings.temp_folder else None

    def get_log_dir(self) -> Path:
        return self.app_data_dir / "logs"

    def get_database_path(self) -> Path:
        return self.app_data_dir / "app_data.db"
