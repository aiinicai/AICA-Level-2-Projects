"""Key derivation and deterministic sub-key hierarchy."""
from __future__ import annotations

import hashlib
import hmac
import secrets

SCRYPT_N = 1 << 15
SCRYPT_R = 8
SCRYPT_P = 1
KEY_BYTES = 32


def derive_password_key(
    password: str,
    salt: bytes,
    *,
    n: int = SCRYPT_N,
    r: int = SCRYPT_R,
    p: int = SCRYPT_P,
    length: int = KEY_BYTES,
) -> bytes:
    if not isinstance(password, str) or len(password) < 12:
        raise ValueError("master password must contain at least 12 characters")
    if len(salt) < 16:
        raise ValueError("KDF salt must contain at least 16 bytes")
    # Explicit maxmem avoids OpenSSL's implementation-dependent 32 MiB default;
    # N=32768/r=8 needs slightly over 32 MiB including working overhead.
    maxmem = max(64 * 1024 * 1024, 256 * n * r)
    return hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=length, maxmem=maxmem
    )


def hkdf_extract(salt: bytes, key_material: bytes) -> bytes:
    return hmac.new(salt or bytes(32), key_material, hashlib.sha256).digest()


def hkdf_expand(pseudorandom_key: bytes, info: bytes, length: int = 32) -> bytes:
    if length <= 0 or length > 255 * 32:
        raise ValueError("invalid HKDF output length")
    output = bytearray()
    previous = b""
    counter = 1
    while len(output) < length:
        previous = hmac.new(
            pseudorandom_key, previous + info + bytes([counter]), hashlib.sha256
        ).digest()
        output.extend(previous)
        counter += 1
    return bytes(output[:length])


def derive_subkey(master_key: bytes, purpose: str, object_id: str = "") -> bytes:
    if len(master_key) != KEY_BYTES:
        raise ValueError("master key must be 32 bytes")
    if not purpose or any(ord(ch) < 32 for ch in purpose):
        raise ValueError("purpose must be non-empty printable text")
    context = f"IBC-EXPERT/v1/{purpose}/{object_id}".encode("utf-8")
    return hkdf_expand(hkdf_extract(b"IBC-EXPERT-HKDF-v1", master_key), context, KEY_BYTES)


def new_master_key() -> bytes:
    return secrets.token_bytes(KEY_BYTES)


def new_salt() -> bytes:
    return secrets.token_bytes(16)
