"""Secure, optional, local storage of the Gemini API key.

The key is stored in the operating system's credential vault via ``keyring``
(Windows Credential Manager, macOS Keychain, Linux Secret Service). It is never
written to plain-text files by this application. If no secure backend is
available, saving is refused and the user must re-enter the key each session
or provide it through the GEMINI_API_KEY environment variable / .env file.
"""

from __future__ import annotations

import logging
import os
import re

log = logging.getLogger(__name__)

SERVICE_NAME = "JudgmentInsightAnalyzer"
ACCOUNT_NAME = "gemini_api_key"

# Deliberately permissive: Google issues keys in more than one format (classic
# "AIza..." keys and newer formats that may contain '.'), so only obvious
# paste mistakes are rejected locally. Google's API is the real validator.
_KEY_RE = re.compile(r"^[\x21-\x7E]{10,512}$")  # printable ASCII, no spaces
_INVISIBLE = dict.fromkeys(map(ord, "​‌‍⁠﻿  "), None)
_PREFIX_RE = re.compile(r"^\s*(?:export\s+)?(?:GEMINI_API_KEY|GOOGLE_API_KEY|API_KEY)\s*[=:]\s*", re.IGNORECASE)


class KeyStoreError(Exception):
    """Raised when the secure store is unavailable or fails."""


def normalize_api_key(raw: str) -> str:
    """Clean common copy/paste artefacts: whitespace, line breaks, invisible
    characters, surrounding quotes and a leading 'GEMINI_API_KEY=' prefix."""
    key = (raw or "").translate(_INVISIBLE).strip()
    key = _PREFIX_RE.sub("", key).strip()
    if len(key) >= 2 and key[0] == key[-1] and key[0] in "\"'`":
        key = key[1:-1].strip()
    return "".join(key.split())  # remove any internal line breaks / spaces from wrapped pastes


def validate_api_key_format(key: str) -> str | None:
    """Return an error message if the (normalised) key is obviously malformed, else None."""
    key = normalize_api_key(key)
    if not key:
        return "Please enter your Gemini API key."
    if not _KEY_RE.match(key):
        bad = sorted({ch for ch in key if not "\x21" <= ch <= "\x7e"})
        if bad:
            shown = ", ".join(f"U+{ord(c):04X}" for c in bad[:5])
            return (f"The API key contains unexpected characters ({shown}). Copy it again directly "
                    "from Google AI Studio using its copy button.")
        return (f"The API key looks too short or too long ({len(key)} characters). "
                "Copy it again from Google AI Studio.")
    return None


def mask_key(key: str) -> str:
    """Return a display-safe version of the key, e.g. 'AIza••••••••x9Q2'."""
    key = key or ""
    if len(key) <= 8:
        return "•" * len(key)
    return f"{key[:4]}{'•' * 8}{key[-4:]}"


def _keyring():
    try:
        import keyring
        from keyring.backends import fail

        backend = keyring.get_keyring()
        if isinstance(backend, fail.Keyring):
            raise KeyStoreError("No secure credential store is available on this computer.")
        return keyring
    except ImportError as exc:
        raise KeyStoreError("The 'keyring' package is not installed.") from exc


def save_api_key(key: str) -> None:
    error = validate_api_key_format(key)
    if error:
        raise KeyStoreError(error)
    try:
        _keyring().set_password(SERVICE_NAME, ACCOUNT_NAME, normalize_api_key(key))
    except KeyStoreError:
        raise
    except Exception as exc:
        raise KeyStoreError(f"Could not save the key securely: {exc}") from exc
    log.info("API key saved to the system credential store.")


def load_api_key() -> tuple[str, str]:
    """Return (key, source). Source is 'keyring', 'environment' or ''."""
    try:
        stored = _keyring().get_password(SERVICE_NAME, ACCOUNT_NAME)
        if stored:
            return normalize_api_key(stored), "keyring"
    except Exception as exc:  # store unavailable is not fatal
        log.info("Credential store not available: %s", exc)
    for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        value = normalize_api_key(os.environ.get(var, ""))
        if value and "your" not in value.lower():
            return value, "environment"
    return "", ""


def delete_api_key() -> None:
    try:
        _keyring().delete_password(SERVICE_NAME, ACCOUNT_NAME)
        log.info("API key removed from the system credential store.")
    except Exception as exc:
        log.info("No stored key removed: %s", exc)


# ------------------------------------------------------- other secrets ---
def secret_account(kind: str, user: str) -> str:
    return f"{kind}:{(user or '').strip().lower()}"


def save_secret(account: str, value: str) -> None:
    """Store another secret (e.g. an email App Password) in the OS credential vault."""
    if not value:
        raise KeyStoreError("Nothing to save.")
    try:
        _keyring().set_password(SERVICE_NAME, account, value)
    except KeyStoreError:
        raise
    except Exception as exc:
        raise KeyStoreError(f"Could not save the password securely: {exc}") from exc


def load_secret(account: str) -> str:
    try:
        return _keyring().get_password(SERVICE_NAME, account) or ""
    except Exception as exc:
        log.info("Credential store not available: %s", exc)
        return ""


def delete_secret(account: str) -> None:
    try:
        _keyring().delete_password(SERVICE_NAME, account)
    except Exception as exc:
        log.info("No stored secret removed: %s", exc)
