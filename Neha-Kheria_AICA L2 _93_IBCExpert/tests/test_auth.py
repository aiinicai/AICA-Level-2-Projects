from datetime import datetime, timedelta, timezone

import pytest

from app.core.errors import AuthenticationError
from app.db.connection import connect
from app.db.migrate import migrate
from app.security.auth import AuthService
from app.security.sessions import SessionManager
from app.security.totp import code_at


class FakeClock:
    def __init__(self):
        self.value = datetime(2026, 1, 1, tzinfo=timezone.utc)
    def now(self):
        return self.value


def test_first_user_auth_and_session(tmp_path):
    db = connect(tmp_path / "auth.sqlite3")
    migrate(db)
    clock = FakeClock()
    auth = AuthService(db, clock)
    uid = auth.create_first_user("owner", "Owner", "A-strong-password-123")
    assert uid > 0
    user = auth.authenticate("owner", "A-strong-password-123")
    manager = SessionManager(20, clock)
    token = manager.create(user.id, user.username, user.master_key)
    assert manager.require(token).user_id == user.id
    clock.value += timedelta(minutes=21)
    with pytest.raises(AuthenticationError):
        manager.require(token)


def test_wrong_password_throttle_persists(tmp_path):
    db = connect(tmp_path / "auth.sqlite3")
    migrate(db)
    clock = FakeClock()
    auth = AuthService(db, clock)
    auth.create_first_user("owner", "Owner", "A-strong-password-123")
    for _ in range(5):
        with pytest.raises(AuthenticationError):
            auth.authenticate("owner", "wrong-password-123")
    # New service object reads the stored throttle state.
    fresh = AuthService(db, clock)
    with pytest.raises(AuthenticationError):
        fresh.authenticate("owner", "A-strong-password-123")


def test_totp_encrypted_and_required(tmp_path, monkeypatch):
    db = connect(tmp_path / "auth.sqlite3")
    migrate(db)
    clock = FakeClock()
    auth = AuthService(db, clock)
    auth.create_first_user("owner", "Owner", "A-strong-password-123")
    user = auth.authenticate("owner", "A-strong-password-123")
    secret, _uri = auth.begin_totp_setup(user)
    timestamp = 1_800_000_000
    monkeypatch.setattr("app.security.totp.time.time", lambda: timestamp)
    auth.enable_totp(user, secret, code_at(secret, timestamp))
    row = db.execute("SELECT totp_secret_encrypted FROM users WHERE id=?", (user.id,)).fetchone()
    assert secret.encode() not in bytes(row[0])
    with pytest.raises(AuthenticationError):
        auth.authenticate("owner", "A-strong-password-123")
    assert auth.authenticate("owner", "A-strong-password-123", code_at(secret, timestamp)).totp_enabled
