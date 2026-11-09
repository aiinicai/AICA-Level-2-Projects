"""Application settings: defaults, validation, and persistence.

Settings are stored as JSON in the user's per-OS configuration directory.
The Gemini API key is NEVER written to this file - see ``key_store.py``.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from . import APP_SLUG

log = logging.getLogger(__name__)

# Model IDs listed as available on the Gemini API "Models" page (checked Oct 2026).
# The list is only a convenience: any model ID can be typed in, and the
# "Refresh models" button pulls the live list for the user's key.
DEFAULT_MODEL = "gemini-3.8-flash"
SUGGESTED_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-pro-preview",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
]

ANALYSIS_DEPTHS = ("Concise", "Standard", "Detailed")
MIN_VIEW_FONT, MAX_VIEW_FONT = 9, 24
OCR_MODES = ("Auto", "Always", "Off")

_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-/]{1,127}$")
_OCR_LANG_RE = re.compile(r"^[A-Za-z_]{3,}(\+[A-Za-z_]{3,})*$")


def user_config_dir() -> Path:
    """Return (and create) the per-user data directory (settings, sender profile, audit log, logs).

    On Windows this is %USERPROFILE%\\.JudgmentInsightAnalyzer\\data - deliberately NOT under
    AppData: Microsoft Store Python silently redirects AppData writes into its private package
    folder, where Excel/Explorer cannot find them.
    """
    override = os.environ.get("JIA_CONFIG_DIR")
    if override:
        base = Path(override)
    elif sys.platform.startswith("win"):
        base = Path(os.environ.get("USERPROFILE") or Path.home()) / f".{APP_SLUG}" / "data"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / APP_SLUG
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_SLUG
    base.mkdir(parents=True, exist_ok=True)
    return base


_MIGRATE_FILES = ("settings.json", "sender_profile.json", "email_audit_log.csv")


def migrate_legacy_data() -> list[str]:
    """Copy data saved by earlier versions (Windows %APPDATA%\\JudgmentInsightAnalyzer) to the new
    folder. Files already present in the new folder are never overwritten. Returns copied names."""
    if not sys.platform.startswith("win") or os.environ.get("JIA_CONFIG_DIR"):
        return []
    import shutil

    legacy = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / APP_SLUG
    copied = []
    try:
        if not legacy.is_dir():
            return []
        target = user_config_dir()
        for name in _MIGRATE_FILES:
            src, dst = legacy / name, target / name
            if src.is_file() and not dst.exists():
                shutil.copy2(src, dst)
                copied.append(name)
    except OSError as exc:  # never block start-up
        log.warning("Could not migrate earlier settings: %s", exc)
    return copied


@dataclass
class AppSettings:
    """User-adjustable settings. All values are validated by ``validate()``."""

    model: str = DEFAULT_MODEL
    analysis_depth: str = "Detailed"
    ocr_mode: str = "Auto"
    ocr_language: str = "eng"
    include_page_refs: bool = False  # page numbers differ between copies of the same order; not used
    force_sectioned: bool = False
    # Documents up to this many characters are analysed in a single request.
    single_pass_max_chars: int = 400_000
    # Section size used when a document is split.
    chunk_max_chars: int = 60_000
    chunk_overlap_chars: int = 1_500
    # Used only for models that are NOT Gemini 3.x (see effective_temperature). Gemini 3 models
    # run at their default temperature, as Google's Gemini 3 developer guide recommends.
    temperature: float = 0.2
    # "auto" = model default for Gemini 3.x, ``temperature`` for older models; "fixed" = always ``temperature``.
    temperature_mode: str = "auto"
    include_para_refs: bool = True
    # Ask Gemini twice for the key facts and compare (2 small extra requests per judgment).
    consistency_check: bool = True
    # Precedent register (SQLite) file; "" = precedent_register.db in the app data folder.
    register_path: str = ""
    # Set once the user has chosen where the register is kept (asked at first start).
    register_location_confirmed: bool = False
    max_output_tokens: int = 32_768
    request_timeout_s: int = 300
    max_retries: int = 4
    max_file_size_mb: int = 200
    appearance_mode: str = "Light"
    # Optional full path to tesseract(.exe) if it is not on PATH or in a standard location.
    tesseract_cmd: str = ""
    # Font used in the results panel ("" = system default).
    view_font_family: str = ""
    view_font_size: int = 12
    # Folder for email_audit_log.csv ("" = the user's Downloads folder).
    audit_log_dir: str = ""
    extra: dict = field(default_factory=dict)

    def validate(self) -> list[str]:
        """Return a list of human-readable problems (empty if valid)."""
        problems: list[str] = []
        if not _MODEL_RE.match(self.model or ""):
            problems.append("Model name may contain only letters, digits, '.', '-', '_' or '/'.")
        if self.analysis_depth not in ANALYSIS_DEPTHS:
            problems.append(f"Analysis depth must be one of {', '.join(ANALYSIS_DEPTHS)}.")
        if self.ocr_mode not in OCR_MODES:
            problems.append(f"OCR mode must be one of {', '.join(OCR_MODES)}.")
        if not _OCR_LANG_RE.match(self.ocr_language or ""):
            problems.append("OCR language must be Tesseract codes such as 'eng' or 'eng+hin'.")
        if not 10_000 <= self.chunk_max_chars <= 1_000_000:
            problems.append("Section size must be between 10,000 and 1,000,000 characters.")
        if not 0 <= self.chunk_overlap_chars < self.chunk_max_chars // 2:
            problems.append("Section overlap must be at least 0 and less than half the section size.")
        if self.single_pass_max_chars < 10_000:
            problems.append("Single-pass limit must be at least 10,000 characters.")
        if not 0.0 <= self.temperature <= 2.0:
            problems.append("Temperature must be between 0.0 and 2.0.")
        if not 1_024 <= self.max_output_tokens <= 200_000:
            problems.append("Max output tokens must be between 1,024 and 200,000.")
        if not 10 <= self.request_timeout_s <= 3_600:
            problems.append("Request timeout must be between 10 and 3,600 seconds.")
        if not 0 <= self.max_retries <= 10:
            problems.append("Max retries must be between 0 and 10.")
        if not MIN_VIEW_FONT <= self.view_font_size <= MAX_VIEW_FONT:
            problems.append(f"Results font size must be between {MIN_VIEW_FONT} and {MAX_VIEW_FONT}.")
        if len(self.audit_log_dir) > 500:
            problems.append("Audit log folder path is too long.")
        if len(self.view_font_family) > 64:
            problems.append("Results font name is too long.")
        if self.temperature_mode not in ("auto", "fixed"):
            problems.append("Temperature mode must be 'auto' or 'fixed'.")
        if len(self.register_path) > 500:
            problems.append("Register file path is too long.")
        if self.appearance_mode not in ("Light", "Dark", "System"):
            problems.append("Appearance must be Light, Dark or System.")
        if self.tesseract_cmd and not Path(self.tesseract_cmd).is_file():
            problems.append("The Tesseract path does not point to an existing file.")
        if not 1 <= self.max_file_size_mb <= 2_000:
            problems.append("Max file size must be between 1 and 2,000 MB.")
        return problems


def effective_temperature(settings: AppSettings) -> float | None:
    """Temperature to send to Gemini, or None to use the model's default."""
    if settings.temperature_mode == "fixed":
        return settings.temperature
    return None if settings.model.lower().startswith("gemini-3") else settings.temperature


def register_path(settings: AppSettings) -> Path:
    """Location of the precedent register database."""
    if settings.register_path:
        return Path(settings.register_path)
    return user_config_dir() / "precedent_register.db"


def settings_path() -> Path:
    return user_config_dir() / "settings.json"


def load_settings(path: Path | None = None) -> AppSettings:
    """Load settings, falling back to defaults for missing/invalid values.

    Environment variables (e.g. from a ``.env`` file) override the model name.
    """
    path = path or settings_path()
    settings = AppSettings()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            known = {f.name for f in fields(AppSettings)}
            for key, value in data.items():
                if key in known and key != "extra":
                    expected = type(getattr(settings, key))
                    if isinstance(value, expected) or (expected is float and isinstance(value, int)):
                        setattr(settings, key, value)
        except (OSError, ValueError) as exc:
            log.warning("Could not read settings file (%s); using defaults.", exc)

    env_model = os.environ.get("GEMINI_MODEL", "").strip()
    if env_model:
        settings.model = env_model

    if settings.tesseract_cmd and not Path(settings.tesseract_cmd).is_file():
        log.warning("Saved Tesseract path no longer exists; ignoring it.")
        settings.tesseract_cmd = ""

    problems = settings.validate()
    if problems:
        log.warning("Invalid settings found (%s); reverting to defaults.", "; ".join(problems))
        settings = AppSettings()
    return settings


def save_settings(settings: AppSettings, path: Path | None = None) -> None:
    path = path or settings_path()
    data = asdict(settings)
    data.pop("extra", None)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    log.info("Settings saved to %s", path)
