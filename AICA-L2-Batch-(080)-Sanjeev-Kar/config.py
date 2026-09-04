"""
config.py
---------
Central configuration: file-system layout, cryptographic parameters, and
tunable security settings. No secrets are hard-coded here; only defaults
and paths. Runtime-editable values (Argon2 cost, face threshold, liveness
toggle) live in settings.json inside the app data directory and are loaded
through get_settings()/save_settings().
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

APP_NAME = "FolderLock"

# ---------------------------------------------------------------------------
# Application data directory (per-OS convention)
# ---------------------------------------------------------------------------

def get_app_data_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home())
        p = Path(base) / APP_NAME
    elif sys.platform == "darwin":
        p = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        p = Path(base) / APP_NAME
    return p


APP_DATA_DIR = get_app_data_dir()
VAULT_DIR = APP_DATA_DIR / "vault"
LOG_DIR = APP_DATA_DIR / "logs"

DEVICE_KEY_FILE = VAULT_DIR / "device.key"
SETTINGS_FILE = VAULT_DIR / "settings.json"
AUDIT_LOG_FILE = LOG_DIR / "audit.log"

# ---------------------------------------------------------------------------
# Per-folder credential profiles
#
# Every protected folder has its own independent profile: its own password,
# its own enrolled face, and its own randomly generated encryption key.
# Nothing is shared between folders, so compromising one folder's password
# or face reveals nothing about any other folder.
#
# These are functions rather than module-level constants so that they always
# follow the CURRENT value of VAULT_DIR. The self-tests redirect VAULT_DIR to
# a temp directory, and deriving paths lazily means they cannot accidentally
# read or write the real vault — a class of test-isolation bug that has
# already bitten this project once.
# ---------------------------------------------------------------------------


def folder_registry_file() -> Path:
    """Maps each known folder to its profile and current lock state."""
    return VAULT_DIR / "folders.json"


def profiles_dir() -> Path:
    return VAULT_DIR / "profiles"


def profile_dir(profile_id: str) -> Path:
    return profiles_dir() / profile_id


def profile_password_vault(profile_id: str) -> Path:
    return profile_dir(profile_id) / "password_vault.json"


def profile_face_template(profile_id: str) -> Path:
    return profile_dir(profile_id) / "face_template.enc"


# --- legacy single-identity layout, kept only so existing locked folders can
# --- be migrated forward rather than stranded. Never written to.
def legacy_password_vault_file() -> Path:
    return VAULT_DIR / "password_vault.json"


def legacy_face_template_file() -> Path:
    return VAULT_DIR / "face_template.enc"


def legacy_registry_file() -> Path:
    return VAULT_DIR / "locked_folders.json"


def ensure_dirs() -> None:
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    profiles_dir().mkdir(parents=True, exist_ok=True)
    _restrict_permissions(APP_DATA_DIR)
    _restrict_permissions(VAULT_DIR)
    _restrict_permissions(LOG_DIR)
    _restrict_permissions(profiles_dir())


def _restrict_permissions(path: Path) -> None:
    """Best-effort permission tightening. On POSIX this removes group/other
    access. On Windows, NTFS ACLs already default to the owning user's
    profile; we do not attempt to rewrite ACLs here (see README limitations).
    """
    if sys.platform != "win32":
        try:
            os.chmod(path, 0o700)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Cryptographic / operational defaults
# ---------------------------------------------------------------------------

DEFAULT_SETTINGS = {
    # Argon2id parameters (RFC 9106-informed, tuned for desktop interactive use)
    "argon2_time_cost": 3,
    "argon2_memory_cost_kib": 65536,   # 64 MiB
    "argon2_parallelism": 4,
    "argon2_hash_len": 32,

    # Face recognition (OpenCV LBPH confidence: lower = stricter/more similar;
    # 0 is a perfect pixel-identical match. 60-80 is a commonly used working
    # range for "same person, different frame" under normal webcam conditions.)
    "face_match_threshold": 70.0,
    "face_min_samples": 5,
    "face_verify_timeout_seconds": 25,
    "liveness_check_enabled": True,

    # File encryption
    "chunk_size_bytes": 4 * 1024 * 1024,  # 4 MiB streaming chunks

    # When enabled (Windows/NTFS only), a locked folder also gets an explicit
    # "Deny Read" permission so it refuses to open in Explorer. This is a
    # deterrent layered on top of encryption, not a replacement for it —
    # see access_control.py for the honest limitations.
    "restrict_folder_access": True,

    "min_password_length": 6,
}

MAGIC = b"FLOCKv1\x00"          # 8-byte container magic for encrypted files
MANIFEST_RELPATH = "__manifest__"


def get_settings() -> dict:
    ensure_dirs()
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            merged = dict(DEFAULT_SETTINGS)
            merged.update({k: v for k, v in data.items() if k in DEFAULT_SETTINGS})
            return merged
        except (json.JSONDecodeError, OSError):
            return dict(DEFAULT_SETTINGS)
    return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> None:
    ensure_dirs()
    merged = get_settings()
    merged.update({k: v for k, v in settings.items() if k in DEFAULT_SETTINGS})
    SETTINGS_FILE.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    _restrict_permissions(SETTINGS_FILE)


def is_first_run() -> bool:
    return not PASSWORD_VAULT_FILE.exists()
