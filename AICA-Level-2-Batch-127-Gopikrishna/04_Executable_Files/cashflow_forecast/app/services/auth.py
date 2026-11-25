"""Users and passwords: Argon2id hashing, login with lockout, password changes.

Phase 6 provides what the screens need (login, roles, change password, create-admin).
Phase 8 adds the user admin screen and the approver workflow.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Role, User
from app.models.base import utcnow
from app.services.audit import audit

MAX_FAILED = 5
LOCK_MINUTES = 15
MIN_PASSWORD = 10
_ph = PasswordHasher()   # argon2id with the library's recommended parameters
_DUMMY = _ph.hash("not-a-real-password")


class AuthError(ValueError):
    pass


def hash_password(pw: str) -> str:
    return _ph.hash(pw)


def check_password_rules(pw: str, username: str = "") -> None:
    if len(pw) < MIN_PASSWORD:
        raise AuthError(f"Password must be at least {MIN_PASSWORD} characters.")
    if username and username.lower() in pw.lower():
        raise AuthError("Password must not contain the user name.")
    if pw.isalpha() or pw.isdigit():
        raise AuthError("Use letters and numbers (or symbols) together.")


def create_user(db: Session, username: str, password: str, role: str = "viewer", full_name: str = "",
                must_change_password: bool = True, created_by_id: int | None = None) -> User:
    username = username.strip().lower()
    if not username or not username.replace(".", "").replace("_", "").replace("-", "").isalnum():
        raise AuthError("User name may contain letters, digits, '.', '_' and '-' only.")
    if db.scalar(select(User).where(func.lower(User.username) == username)):
        raise AuthError(f"User '{username}' already exists.")
    check_password_rules(password, username)
    u = User(username=username, full_name=full_name.strip(), password_hash=hash_password(password),
             role=Role(role), must_change_password=must_change_password)
    db.add(u)
    db.flush()
    audit(db, "user.create", "user", username, after={"role": role}, user_id=created_by_id)
    return u


def authenticate(db: Session, username: str, password: str, ip: str = "") -> User:
    """Return the user or raise AuthError with a message that does not reveal which part was wrong."""
    generic = AuthError("User name or password is not correct.")
    u = db.scalar(select(User).where(func.lower(User.username) == (username or "").strip().lower()))
    if u is None or not u.is_active:
        try:
            _ph.verify(_DUMMY, password or "x")      # same work either way (timing)
        except VerificationError:
            pass
        audit(db, "login.failed", "user", (username or "")[:64], after={"reason": "unknown or inactive"}, ip=ip)
        raise generic
    now = utcnow()
    if u.locked_until and u.locked_until > now:
        audit(db, "login.locked", "user", u.username, user_id=u.id, ip=ip)
        raise AuthError(f"Account locked after {MAX_FAILED} failed attempts. Try again after "
                        f"{LOCK_MINUTES} minutes or ask an Admin.")
    try:
        _ph.verify(u.password_hash, password or "")
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        u.failed_logins += 1
        if u.failed_logins >= MAX_FAILED:
            u.locked_until, u.failed_logins = now + timedelta(minutes=LOCK_MINUTES), 0
        audit(db, "login.failed", "user", u.username, after={"failed": u.failed_logins}, user_id=u.id, ip=ip)
        raise generic
    if _ph.check_needs_rehash(u.password_hash):
        u.password_hash = hash_password(password)
    u.failed_logins, u.locked_until, u.last_login_at = 0, None, now
    audit(db, "login.ok", "user", u.username, user_id=u.id, ip=ip)
    return u


def change_password(db: Session, user: User, current: str, new: str, confirm: str) -> None:
    try:
        _ph.verify(user.password_hash, current or "")
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        raise AuthError("Current password is not correct.")
    if new != confirm:
        raise AuthError("The two new passwords do not match.")
    if new == current:
        raise AuthError("Choose a password different from the current one.")
    check_password_rules(new, user.username)
    user.password_hash, user.must_change_password = hash_password(new), False
    audit(db, "user.password_changed", "user", user.username, user_id=user.id)


def temporary_password() -> str:
    """Random one-time password that meets the rules (shown once to the Admin, never stored in clear)."""
    import secrets
    return "Temp-" + secrets.token_urlsafe(9).replace("-", "x").replace("_", "y") + "7"


def _active_admins(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(User).where(User.role == Role.ADMIN, User.is_active)) or 0


def update_user(db: Session, admin: User, user: User, *, full_name: str, role: str, is_active: bool) -> None:
    """Change name, role or active flag. The last active Admin cannot be removed or demoted."""
    new_role = Role(role)
    losing_admin = user.role == Role.ADMIN and user.is_active and (new_role != Role.ADMIN or not is_active)
    if losing_admin and _active_admins(db) <= 1:
        raise AuthError("This is the last active Admin. Make another user Admin first.")
    if user.id == admin.id and not is_active:
        raise AuthError("You cannot deactivate your own account.")
    before = {"name": user.full_name, "role": user.role.value, "active": user.is_active}
    user.full_name, user.role, user.is_active = full_name.strip(), new_role, is_active
    after = {"name": user.full_name, "role": user.role.value, "active": user.is_active}
    if before != after:
        audit(db, "user.update", "user", user.username, before=before, after=after, user_id=admin.id)


def reset_password(db: Session, admin: User, user: User) -> str:
    """Give the user a new temporary password; they must change it at next sign-in.
    Their open sessions end (sessions are tied to the password)."""
    temp = temporary_password()
    user.password_hash, user.must_change_password = hash_password(temp), True
    user.failed_logins, user.locked_until = 0, None
    audit(db, "user.password_reset", "user", user.username, user_id=admin.id)
    return temp


def unlock(db: Session, admin: User, user: User) -> None:
    user.failed_logins, user.locked_until = 0, None
    audit(db, "user.unlock", "user", user.username, user_id=admin.id)


def is_locked(u: User, now: datetime | None = None) -> bool:
    return bool(u.locked_until and u.locked_until > (now or utcnow()))
