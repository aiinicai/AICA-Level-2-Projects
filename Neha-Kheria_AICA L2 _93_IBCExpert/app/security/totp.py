"""Dependency-free RFC 6238 TOTP helpers for optional offline second factor."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote


def generate_secret(byte_length: int = 20) -> str:
    if byte_length < 20:
        raise ValueError("TOTP secret must contain at least 160 bits")
    return base64.b32encode(secrets.token_bytes(byte_length)).decode("ascii").rstrip("=")


def _decode_secret(secret: str) -> bytes:
    normalized = "".join(secret.upper().split())
    padding = "=" * ((8 - len(normalized) % 8) % 8)
    try:
        raw = base64.b32decode(normalized + padding, casefold=True)
    except Exception as exc:
        raise ValueError("Invalid TOTP secret") from exc
    if len(raw) < 20:
        raise ValueError("TOTP secret is too short")
    return raw


def code_at(secret: str, timestamp: int | float | None = None, *, period: int = 30, digits: int = 6) -> str:
    if period <= 0 or digits not in range(6, 9):
        raise ValueError("Invalid TOTP configuration")
    timestamp = time.time() if timestamp is None else timestamp
    counter = int(timestamp) // period
    digest = hmac.new(_decode_secret(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(binary % (10 ** digits)).zfill(digits)


def verify_code(secret: str, supplied: str, timestamp: int | float | None = None, *, window: int = 1) -> bool:
    supplied = supplied.strip()
    if not supplied.isdigit() or len(supplied) != 6:
        return False
    now = time.time() if timestamp is None else float(timestamp)
    for offset in range(-window, window + 1):
        if hmac.compare_digest(code_at(secret, now + offset * 30), supplied):
            return True
    return False


def provisioning_uri(secret: str, username: str, issuer: str = "IBC Expert") -> str:
    _decode_secret(secret)
    label = quote(f"{issuer}:{username}")
    return f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}&algorithm=SHA1&digits=6&period=30"
