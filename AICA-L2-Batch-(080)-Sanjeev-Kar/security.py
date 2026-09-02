"""
security.py
------------
Low-level cryptographic primitives used throughout the application.

Design summary
~~~~~~~~~~~~~~
* Password -> key derivation: Argon2id (argon2-cffi), memory-hard, resistant
  to GPU/ASIC cracking. This is the OWASP-recommended default for
  password-based key derivation.
* Key wrapping / file encryption: AES-256-GCM (an AEAD cipher) via the
  `cryptography` library (a wrapper around OpenSSL). AEAD gives us both
  confidentiality and tamper detection (authentication tag) in one step.
* Per-file / per-purpose key separation: HKDF-SHA256, so a single master key
  never gets reused verbatim with unrelated nonces across many files.
* All randomness (salts, nonces, master key generation) comes from `secrets`
  / `os.urandom`, which use the OS CSPRNG.

No cryptographic algorithm implemented here is custom. Only the *framing*
(how bytes are laid out on disk) is application-specific, exactly the same
way a ZIP file or TLS record layer frames standard primitives.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass

from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class SecurityError(Exception):
    """Base class for all security-related failures."""


class AuthenticationError(SecurityError):
    """Raised when a credential (password) fails to authenticate."""


class TamperDetectedError(SecurityError):
    """Raised when authenticated-encryption verification fails, indicating
    the ciphertext was corrupted or tampered with."""


class CorruptedFileError(SecurityError):
    """Raised when an encrypted container is structurally malformed."""


NONCE_SIZE = 12          # AES-GCM standard nonce size (96 bits)
KEY_SIZE = 32             # AES-256
SALT_SIZE = 16
MASTER_KEY_SIZE = 32


# ---------------------------------------------------------------------------
# Randomness
# ---------------------------------------------------------------------------

def random_bytes(n: int) -> bytes:
    return secrets.token_bytes(n)


def generate_master_key() -> bytearray:
    """The data-encryption key. Randomly generated once at setup; never
    derived from the password or the face embedding directly. The password
    only *wraps* (encrypts) this key.

    Returns a mutable bytearray (not bytes) so callers can genuinely zero
    it after use via best_effort_zero() — a plain `bytes` object can only
    ever be zeroed by wiping a *copy*, which leaves the original untouched
    (bytes are immutable; bytearray(some_bytes) always copies)."""
    return bytearray(random_bytes(MASTER_KEY_SIZE))


# ---------------------------------------------------------------------------
# Argon2id key derivation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Argon2Params:
    time_cost: int
    memory_cost_kib: int
    parallelism: int
    hash_len: int = KEY_SIZE


def derive_key_argon2id(password: str, salt: bytes, params: Argon2Params) -> bytearray:
    if not isinstance(password, str) or len(password) == 0:
        raise ValueError("password must be a non-empty string")
    return bytearray(hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=params.time_cost,
        memory_cost=params.memory_cost_kib,
        parallelism=params.parallelism,
        hash_len=params.hash_len,
        type=Type.ID,  # Argon2id
    ))


# ---------------------------------------------------------------------------
# HKDF (domain separation for per-file / per-purpose keys)
# ---------------------------------------------------------------------------

def hkdf_derive(key_material: bytes, salt: bytes, info: bytes, length: int = KEY_SIZE) -> bytearray:
    hkdf = HKDF(algorithm=hashes.SHA256(), length=length, salt=salt, info=info)
    return bytearray(hkdf.derive(key_material))


# ---------------------------------------------------------------------------
# AES-256-GCM primitives
# ---------------------------------------------------------------------------

def aes_gcm_encrypt(key: bytes, nonce: bytes, plaintext: bytes, aad: bytes = b"") -> bytes:
    return AESGCM(key).encrypt(nonce, plaintext, aad)


def aes_gcm_decrypt(key: bytes, nonce: bytes, ciphertext: bytes, aad: bytes = b"") -> bytes:
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, aad)
    except InvalidTag as exc:
        raise TamperDetectedError(
            "Authentication tag verification failed: data is corrupted or was tampered with."
        ) from exc


# ---------------------------------------------------------------------------
# Master-key wrapping with a password-derived key-encryption-key (KEK)
# ---------------------------------------------------------------------------

def wrap_master_key(kek: bytes, master_key: bytes) -> tuple[bytes, bytes]:
    """Returns (nonce, wrapped_ciphertext)."""
    nonce = random_bytes(NONCE_SIZE)
    wrapped = aes_gcm_encrypt(kek, nonce, master_key, aad=b"folderlock-master-key-wrap-v1")
    return nonce, wrapped


def unwrap_master_key(kek: bytes, nonce: bytes, wrapped: bytes) -> bytearray:
    """Raises AuthenticationError if the KEK (i.e. the password) is wrong."""
    try:
        return bytearray(aes_gcm_decrypt(kek, nonce, wrapped, aad=b"folderlock-master-key-wrap-v1"))
    except TamperDetectedError as exc:
        raise AuthenticationError("Incorrect password.") from exc


# ---------------------------------------------------------------------------
# Device key (protects the face template at rest; see README limitations —
# this key is *not* secret from a local attacker with full disk access,
# because face verification must be possible before a password is entered.)
# ---------------------------------------------------------------------------

def get_or_create_device_key(path) -> bytes:
    from pathlib import Path
    path = Path(path)
    if path.exists():
        data = path.read_bytes()
        if len(data) != KEY_SIZE:
            raise CorruptedFileError("Device key file is corrupted (unexpected length).")
        return data
    path.parent.mkdir(parents=True, exist_ok=True)
    key = random_bytes(KEY_SIZE)
    path.write_bytes(key)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return key


def best_effort_zero(buf: bytearray) -> None:
    """Best-effort memory scrubbing. CPython cannot guarantee secrets are
    wiped from memory (string/bytes immutability, GC, swap), but zeroing a
    mutable buffer we control reduces the exposure window."""
    for i in range(len(buf)):
        buf[i] = 0
