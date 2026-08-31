"""
password_auth.py
-----------------
Password validation and password-based protection of the master encryption
key. The password itself is NEVER stored, logged, or printed — only:

    * a random salt
    * the Argon2id cost parameters
    * a nonce
    * the master key, wrapped (AES-256-GCM) under the Argon2id-derived key

Correctness of the password is proven implicitly: unwrapping only succeeds
if the AES-GCM authentication tag verifies, which only happens if the
Argon2id-derived KEK is correct. There is no separate password hash stored,
which avoids maintaining a second oracle for guessing attacks.
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import config
import security
from security import Argon2Params, AuthenticationError, CorruptedFileError


SPECIAL_CHARS = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"""


def validate_password(password: str) -> tuple[bool, list[str]]:
    """Validate a candidate password against policy.

    Returns (is_valid, messages) where `messages` lists every unmet
    requirement (empty list if the password is fully valid).
    """
    settings = config.get_settings()
    min_len = settings["min_password_length"]
    problems: list[str] = []

    if password is None or len(password) < min_len:
        problems.append(f"Password must be at least {min_len} characters long.")
    if not re.search(r"[A-Za-z]", password or ""):
        problems.append("Password must contain at least one alphabetic character.")
    if not re.search(r"[0-9]", password or ""):
        problems.append("Password must contain at least one number.")
    if not re.search(f"[{re.escape(SPECIAL_CHARS)}]", password or ""):
        problems.append("Password must contain at least one special/symbolic character.")

    return (len(problems) == 0, problems)


@dataclass
class _VaultRecord:
    salt_b64: str
    nonce_b64: str
    wrapped_key_b64: str
    argon2_time_cost: int
    argon2_memory_cost_kib: int
    argon2_parallelism: int
    argon2_hash_len: int


def _params_from_record(rec: dict) -> Argon2Params:
    return Argon2Params(
        time_cost=rec["argon2_time_cost"],
        memory_cost_kib=rec["argon2_memory_cost_kib"],
        parallelism=rec["argon2_parallelism"],
        hash_len=rec["argon2_hash_len"],
    )


def password_vault_exists(profile_id: str) -> bool:
    return config.profile_password_vault(profile_id).exists()


def create_password_vault(profile_id: str, password: str, master_key: bytes) -> None:
    """Creates (or replaces) the password vault for ONE folder's profile:
    wraps that folder's own master key under a key derived from that
    folder's own password. Profiles are fully independent of one another."""
    ok, problems = validate_password(password)
    if not ok:
        raise ValueError("Password does not meet policy: " + "; ".join(problems))

    settings = config.get_settings()
    params = Argon2Params(
        time_cost=settings["argon2_time_cost"],
        memory_cost_kib=settings["argon2_memory_cost_kib"],
        parallelism=settings["argon2_parallelism"],
        hash_len=settings["argon2_hash_len"],
    )
    salt = security.random_bytes(security.SALT_SIZE)
    kek = security.derive_key_argon2id(password, salt, params)
    try:
        nonce, wrapped = security.wrap_master_key(kek, master_key)
    finally:
        security.best_effort_zero(kek)

    rec = _VaultRecord(
        salt_b64=base64.b64encode(salt).decode("ascii"),
        nonce_b64=base64.b64encode(nonce).decode("ascii"),
        wrapped_key_b64=base64.b64encode(wrapped).decode("ascii"),
        argon2_time_cost=params.time_cost,
        argon2_memory_cost_kib=params.memory_cost_kib,
        argon2_parallelism=params.parallelism,
        argon2_hash_len=params.hash_len,
    )
    vault_path = config.profile_password_vault(profile_id)
    vault_path.parent.mkdir(parents=True, exist_ok=True)
    vault_path.write_text(json.dumps(asdict(rec), indent=2), encoding="utf-8")
    config._restrict_permissions(vault_path)


def verify_password_and_get_master_key(profile_id: str, password: str) -> bytearray:
    """Returns that folder's master key on success. Raises
    AuthenticationError on wrong password, or CorruptedFileError if the
    vault is unreadable."""
    vault_path = config.profile_password_vault(profile_id)
    if not vault_path.exists():
        raise CorruptedFileError("No credentials found for this folder.")
    try:
        rec = json.loads(vault_path.read_text(encoding="utf-8"))
        salt = base64.b64decode(rec["salt_b64"])
        nonce = base64.b64decode(rec["nonce_b64"])
        wrapped = base64.b64decode(rec["wrapped_key_b64"])
        params = _params_from_record(rec)
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        raise CorruptedFileError("Password vault file is corrupted.") from exc

    kek = security.derive_key_argon2id(password, salt, params)
    try:
        return security.unwrap_master_key(kek, nonce, wrapped)
    finally:
        security.best_effort_zero(kek)


def change_password(profile_id: str, old_password: str, new_password: str) -> None:
    """Requires that folder's correct current password. Re-wraps the *same*
    master key under a freshly derived KEK with a new random salt/nonce, so
    the folder never needs to be re-encrypted when its password changes."""
    ok, problems = validate_password(new_password)
    if not ok:
        raise ValueError("New password does not meet policy: " + "; ".join(problems))

    master_key = verify_password_and_get_master_key(profile_id, old_password)
    try:
        create_password_vault(profile_id, new_password, master_key)
    finally:
        security.best_effort_zero(master_key)
