"""Persistent local authentication and optional encrypted TOTP configuration."""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

from app.core.errors import AuthenticationError, ValidationError
from app.core.time import Clock, SystemClock, to_utc_iso
from app.db.connection import transaction
from app.security import aead
from app.security.kdf import derive_subkey
from app.security.passwords import LoginThrottle, create_master_envelope, unlock_master_envelope
from app.security.totp import generate_secret, provisioning_uri, verify_code

_USERNAME = re.compile(r"^[A-Za-z0-9_.-]{3,64}$")
_TOTP_AAD = b"IBC-EXPERT/TOTP/v1"


@dataclass(frozen=True)
class AuthenticatedUser:
    id: int
    username: str
    display_name: str
    master_key: bytes
    totp_enabled: bool


class AuthService:
    def __init__(self, connection: sqlite3.Connection, clock: Clock | None = None) -> None:
        self.connection = connection
        self.clock = clock or SystemClock()

    def has_users(self) -> bool:
        return bool(self.connection.execute("SELECT 1 FROM users LIMIT 1").fetchone())

    def create_first_user(self, username: str, display_name: str, password: str) -> int:
        if self.has_users():
            raise ValidationError("Initial user setup has already been completed.")
        username = username.strip()
        display_name = display_name.strip()
        if not _USERNAME.fullmatch(username):
            raise ValidationError("User ID must be 3-64 characters using letters, numbers, dot, dash or underscore.")
        if not display_name or len(display_name) > 120:
            raise ValidationError("Display name is required and must be 120 characters or fewer.")
        try:
            envelope, _ = create_master_envelope(password)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        now = to_utc_iso(self.clock.now())
        with transaction(self.connection):
            cur = self.connection.execute(
                "INSERT INTO users(username,display_name,master_envelope,created_at,updated_at) VALUES(?,?,?,?,?)",
                (username, display_name, envelope, now, now),
            )
        return int(cur.lastrowid)

    def authenticate(self, username: str, password: str, totp_code: str | None = None) -> AuthenticatedUser:
        row = self.connection.execute(
            "SELECT id,username,display_name,master_envelope,throttle_json,totp_secret_encrypted,is_active FROM users WHERE username=? COLLATE NOCASE",
            (username.strip(),),
        ).fetchone()
        # Deliberately use a generic error for unknown and disabled users.
        if row is None or not int(row["is_active"]):
            raise AuthenticationError("The User ID, password or security code is incorrect.")
        throttle = LoginThrottle.from_json(row["throttle_json"], self.clock)
        throttle.check_allowed()
        try:
            master_key = unlock_master_envelope(password, bytes(row["master_envelope"]))
            encrypted_secret = row["totp_secret_encrypted"]
            if encrypted_secret is not None:
                key = derive_subkey(master_key, "totp", str(row["id"]))
                secret = aead.decrypt(key, bytes(encrypted_secret), _TOTP_AAD).decode("ascii")
                if not totp_code or not verify_code(secret, totp_code):
                    raise AuthenticationError("The User ID, password or security code is incorrect.")
        except AuthenticationError:
            throttle.record_failure()
            with transaction(self.connection):
                self.connection.execute(
                    "UPDATE users SET throttle_json=?,updated_at=? WHERE id=?",
                    (throttle.to_json(), to_utc_iso(self.clock.now()), row["id"]),
                )
            raise AuthenticationError("The User ID, password or security code is incorrect.")
        throttle.record_success()
        with transaction(self.connection):
            self.connection.execute(
                "UPDATE users SET throttle_json=?,updated_at=? WHERE id=?",
                (throttle.to_json(), to_utc_iso(self.clock.now()), row["id"]),
            )
        return AuthenticatedUser(
            int(row["id"]), str(row["username"]), str(row["display_name"]), master_key, encrypted_secret is not None
        )


    def totp_enabled(self, user_id: int) -> bool:
        row = self.connection.execute(
            "SELECT totp_secret_encrypted FROM users WHERE id=? AND is_active=1", (user_id,)
        ).fetchone()
        if row is None:
            raise AuthenticationError("The local user account is unavailable.")
        return row["totp_secret_encrypted"] is not None

    def begin_totp_setup(self, user: AuthenticatedUser) -> tuple[str, str]:
        secret = generate_secret()
        return secret, provisioning_uri(secret, user.username)

    def enable_totp(self, user: AuthenticatedUser, secret: str, verification_code: str) -> None:
        if not verify_code(secret, verification_code):
            raise ValidationError("The security code is incorrect. TOTP was not enabled.")
        key = derive_subkey(user.master_key, "totp", str(user.id))
        payload = aead.encrypt(key, secret.encode("ascii"), _TOTP_AAD)
        with transaction(self.connection):
            self.connection.execute(
                "UPDATE users SET totp_secret_encrypted=?,updated_at=? WHERE id=?",
                (payload, to_utc_iso(self.clock.now()), user.id),
            )

    def disable_totp(self, user: AuthenticatedUser, verification_code: str) -> None:
        row = self.connection.execute("SELECT totp_secret_encrypted FROM users WHERE id=?", (user.id,)).fetchone()
        if row is None or row["totp_secret_encrypted"] is None:
            return
        key = derive_subkey(user.master_key, "totp", str(user.id))
        secret = aead.decrypt(key, bytes(row["totp_secret_encrypted"]), _TOTP_AAD).decode("ascii")
        if not verify_code(secret, verification_code):
            raise AuthenticationError("The security code is incorrect.")
        with transaction(self.connection):
            self.connection.execute(
                "UPDATE users SET totp_secret_encrypted=NULL,updated_at=? WHERE id=?",
                (to_utc_iso(self.clock.now()), user.id),
            )
