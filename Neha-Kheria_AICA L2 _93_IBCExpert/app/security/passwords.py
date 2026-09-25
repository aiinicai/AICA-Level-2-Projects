"""Master-password envelope, verification and escalating local lockout."""
from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import timedelta

from app.core.errors import AccountLockedError, AuthenticationError, IntegrityError
from app.core.time import Clock, SystemClock, from_utc_iso, to_utc_iso
from app.security import aead
from app.security.kdf import derive_password_key, new_master_key, new_salt

ENVELOPE_AAD = b"IBC-EXPERT/MASTER-KEY/v1"
ENVELOPE_MARKER = b"IBC-EXPERT-MASTER-KEY\x00"


def create_master_envelope(password: str, master_key: bytes | None = None) -> tuple[bytes, bytes]:
    salt = new_salt()
    key = derive_password_key(password, salt)
    master_key = master_key or new_master_key()
    if len(master_key) != 32:
        raise ValueError("master key must contain 32 bytes")
    encrypted = aead.encrypt(key, ENVELOPE_MARKER + master_key, ENVELOPE_AAD)
    envelope = {
        "version": 1,
        "kdf": "scrypt",
        "n": 1 << 15,
        "r": 8,
        "p": 1,
        "salt": salt.hex(),
        "payload": encrypted.hex(),
    }
    return json.dumps(envelope, separators=(",", ":"), sort_keys=True).encode("utf-8"), master_key


def unlock_master_envelope(password: str, envelope_bytes: bytes) -> bytes:
    try:
        envelope = json.loads(envelope_bytes.decode("utf-8"))
        if envelope.get("version") != 1 or envelope.get("kdf") != "scrypt":
            raise ValueError("unsupported envelope")
        salt = bytes.fromhex(envelope["salt"])
        payload = bytes.fromhex(envelope["payload"])
        key = derive_password_key(
            password,
            salt,
            n=int(envelope["n"]),
            r=int(envelope["r"]),
            p=int(envelope["p"]),
        )
        clear = aead.decrypt(key, payload, ENVELOPE_AAD)
        if not clear.startswith(ENVELOPE_MARKER) or len(clear) != len(ENVELOPE_MARKER) + 32:
            raise IntegrityError("invalid marker")
        return clear[len(ENVELOPE_MARKER):]
    except (KeyError, ValueError, UnicodeDecodeError, json.JSONDecodeError, IntegrityError) as exc:
        raise AuthenticationError("The master password is incorrect or the secure profile is damaged.") from exc


def change_master_password(old_password: str, new_password: str, envelope_bytes: bytes) -> bytes:
    master_key = unlock_master_envelope(old_password, envelope_bytes)
    new_envelope, _ = create_master_envelope(new_password, master_key)
    return new_envelope


@dataclass
class LoginThrottle:
    clock: Clock = SystemClock()
    failed_attempts: int = 0
    locked_until: str | None = None

    def check_allowed(self) -> None:
        if not self.locked_until:
            return
        now = self.clock.now()
        until = from_utc_iso(self.locked_until)
        if now < until:
            raise AccountLockedError(int((until - now).total_seconds()) + 1)
        self.locked_until = None

    def record_failure(self) -> None:
        self.failed_attempts += 1
        # First four failures have no timed lock. Then 2, 4, 8... seconds,
        # capped at one hour; persistent storage makes restart ineffective.
        if self.failed_attempts >= 5:
            seconds = min(3600, 2 ** (self.failed_attempts - 4))
            self.locked_until = to_utc_iso(self.clock.now() + timedelta(seconds=seconds))

    def record_success(self) -> None:
        self.failed_attempts = 0
        self.locked_until = None

    def to_json(self) -> str:
        return json.dumps(
            {"failed_attempts": self.failed_attempts, "locked_until": self.locked_until},
            separators=(",", ":"),
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, value: str, clock: Clock | None = None) -> "LoginThrottle":
        raw = json.loads(value)
        return cls(
            clock=clock or SystemClock(),
            failed_attempts=max(0, int(raw.get("failed_attempts", 0))),
            locked_until=raw.get("locked_until"),
        )


def new_session_token() -> str:
    return secrets.token_urlsafe(32)
