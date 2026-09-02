"""Server-side encryption for stored AI provider API keys.

Uses Fernet with COMPANYVAL_MASTER_KEY from the environment. In local
development, if no master key is configured, a key is generated once and
persisted to storage/.master_key (never committed; storage/ is gitignored).
Keys are never logged and never returned to the frontend.
"""
from __future__ import annotations

from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from ..config import PROJECT_DIR, get_settings

_DEV_KEY_FILE = PROJECT_DIR / "storage" / ".master_key"


def _master_key() -> bytes:
    settings = get_settings()
    if settings.companyval_master_key:
        return settings.companyval_master_key.encode()
    if _DEV_KEY_FILE.exists():
        _harden(_DEV_KEY_FILE)  # repair perms on keys written before this was enforced
        return _DEV_KEY_FILE.read_bytes().strip()
    key = Fernet.generate_key()
    _DEV_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Create owner-only *before* writing: this key decrypts every stored provider
    # key, and the default 0644 would leave it world-readable on a shared machine.
    _DEV_KEY_FILE.touch(mode=0o600, exist_ok=True)
    _harden(_DEV_KEY_FILE)
    _DEV_KEY_FILE.write_bytes(key)
    return key


def _harden(path: Path) -> None:
    """Best-effort chmod 0600; silently skipped on filesystems without POSIX modes."""
    try:
        path.chmod(0o600)
    except OSError:
        pass


def encrypt_secret(plain: str) -> str:
    return Fernet(_master_key()).encrypt(plain.encode()).decode()


def decrypt_secret(token: str) -> str | None:
    try:
        return Fernet(_master_key()).decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return None


def mask_key(plain_or_none: str | None) -> str:
    if not plain_or_none:
        return ""
    tail = plain_or_none[-4:] if len(plain_or_none) >= 4 else ""
    return "•" * 24 + tail
