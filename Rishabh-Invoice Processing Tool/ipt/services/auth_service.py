"""Users, login and roles."""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import func, select

from ipt.core import permissions as perms
from ipt.core.context import CurrentUser
from ipt.core.security import hash_password, verify_password
from ipt.db.base import Database
from ipt.db.models import User
from ipt.services import audit_service

log = logging.getLogger(__name__)
MIN_PASSWORD = 8


class AuthError(Exception):
    pass


def _to_current(u: User) -> CurrentUser:
    return CurrentUser(id=u.id, username=u.username, full_name=u.full_name, role=u.role)


class AuthService:
    def __init__(self, db: Database):
        self.db = db

    def has_users(self) -> bool:
        with self.db.session() as s:
            return (s.scalar(select(func.count(User.id))) or 0) > 0

    def create_user(self, username: str, password: str, role: str, full_name: str = "",
                    actor: CurrentUser | None = None) -> CurrentUser:
        username = username.strip().lower()
        if not username:
            raise AuthError("Username is required")
        if role not in perms.ROLES:
            raise AuthError(f"Unknown role: {role}")
        if len(password) < MIN_PASSWORD:
            raise AuthError(f"Password must be at least {MIN_PASSWORD} characters")
        if self.has_users():
            perms.require(actor.role if actor else None, "user.manage")
        elif role != perms.ADMIN:
            raise AuthError("The first user must be an admin")
        with self.db.session() as s:
            if s.scalar(select(User).where(User.username == username)):
                raise AuthError("Username already exists")
            u = User(username=username, full_name=full_name.strip(), role=role,
                     password_hash=hash_password(password), is_active=True)
            s.add(u)
            s.flush()
            audit_service.record(s, actor, "user.create", "user", u.id,
                                 after={"username": username, "role": role})
            return _to_current(u)

    def authenticate(self, username: str, password: str) -> CurrentUser:
        with self.db.session() as s:
            u = s.scalar(select(User).where(User.username == username.strip().lower()))
            if u is None or not u.is_active or not verify_password(password, u.password_hash):
                log.info("Failed login for user '%s'", username)
                raise AuthError("Invalid username or password")
            u.last_login_at = datetime.now()
            cu = _to_current(u)
            audit_service.record(s, cu, "user.login", "user", u.id)
            return cu

    def list_users(self) -> list[User]:
        with self.db.session() as s:
            return list(s.scalars(select(User).order_by(User.username)))

    def _active_admins(self, s) -> int:
        return s.scalar(select(func.count(User.id)).where(
            User.role == perms.ADMIN, User.is_active.is_(True))) or 0

    def set_role(self, user_id: int, role: str, actor: CurrentUser) -> None:
        perms.require(actor.role, "user.manage")
        if role not in perms.ROLES:
            raise AuthError(f"Unknown role: {role}")
        with self.db.session() as s:
            u = s.get(User, user_id)
            if u is None:
                raise AuthError("User not found")
            if u.role == perms.ADMIN and role != perms.ADMIN and self._active_admins(s) <= 1:
                raise AuthError("At least one active admin is required")
            before = {"role": u.role}
            u.role = role
            audit_service.record(s, actor, "user.role", "user", u.id, before, {"role": role})

    def set_active(self, user_id: int, active: bool, actor: CurrentUser) -> None:
        perms.require(actor.role, "user.manage")
        with self.db.session() as s:
            u = s.get(User, user_id)
            if u is None:
                raise AuthError("User not found")
            if not active and u.role == perms.ADMIN and self._active_admins(s) <= 1:
                raise AuthError("At least one active admin is required")
            if not active and u.id == actor.id:
                raise AuthError("You cannot deactivate yourself")
            u.is_active = active
            audit_service.record(s, actor, "user.activate" if active else "user.deactivate", "user", u.id)

    def reset_password(self, user_id: int, new_password: str, actor: CurrentUser) -> None:
        if actor.id != user_id:
            perms.require(actor.role, "user.manage")
        if len(new_password) < MIN_PASSWORD:
            raise AuthError(f"Password must be at least {MIN_PASSWORD} characters")
        with self.db.session() as s:
            u = s.get(User, user_id)
            if u is None:
                raise AuthError("User not found")
            u.password_hash = hash_password(new_password)
            audit_service.record(s, actor, "user.password_reset", "user", u.id)
