"""Module 1 — user access. Local accounts, roles, sessions, lockout."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..core import audit
from ..core.config import get_settings
from ..core.db import ro, row_to_dict, tx, utcnow
from ..core.errors import AuthError, Conflict, NotFound, PermissionDenied, ValidationError
from ..core.security import hash_password, new_token, token_hash, verify_password

ROLES = ("ADMIN", "CA", "STAFF")
_DUMMY_HASH = "scrypt$16384$8$1$" + "00" * 16 + "$" + "00" * 32
_PUBLIC_FIELDS = "id,username,full_name,role,membership_no,active,locked,created_at"


def create_user(username: str, full_name: str, role: str, password: str, *, membership_no: str | None = None,
                actor_id: int | None = None) -> dict:
    username = (username or "").strip().lower()
    if not username or not username.replace("_", "").replace(".", "").isalnum() or len(username) > 50:
        raise ValidationError("Username must be 1-50 characters: letters, digits, '.', '_'.")
    if role not in ROLES:
        raise ValidationError(f"Role must be one of {ROLES}.")
    if not full_name or len(full_name) > 120:
        raise ValidationError("Full name is required (max 120 chars).")
    pw = hash_password(password)
    with tx() as conn:
        n_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if n_users > 0:
            if actor_id is None:
                raise PermissionDenied("Only an ADMIN can create users.")
            actor = conn.execute("SELECT role FROM users WHERE id=?", (actor_id,)).fetchone()
            if not actor or actor["role"] != "ADMIN":
                raise PermissionDenied("Only an ADMIN can create users.")
        elif role != "ADMIN":
            raise ValidationError("The first user must be an ADMIN.")
        if conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            raise Conflict("Username already exists.")
        cur = conn.execute(
            "INSERT INTO users(username,full_name,role,membership_no,password_hash,created_at) VALUES (?,?,?,?,?,?)",
            (username, full_name.strip(), role, (membership_no or None), pw, utcnow()),
        )
        uid = cur.lastrowid
        audit.log_event(conn, "USER_CREATED", user_id=actor_id or uid, meta={"new_user_id": uid, "role": role})
    return get_user(uid)


def get_user(user_id: int) -> dict:
    with ro() as conn:
        r = conn.execute(f"SELECT {_PUBLIC_FIELDS} FROM users WHERE id=?", (user_id,)).fetchone()
    if not r:
        raise NotFound("User not found.")
    return row_to_dict(r)


def list_users() -> list[dict]:
    with ro() as conn:
        return [row_to_dict(r) for r in conn.execute(f"SELECT {_PUBLIC_FIELDS} FROM users ORDER BY id")]


def login(username: str, password: str) -> dict:
    s = get_settings()
    username = (username or "").strip().lower()
    with tx() as conn:
        u = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if not u or not u["active"]:
            verify_password(password or "", _DUMMY_HASH)  # equalise timing (no username enumeration)
            audit.log_event(conn, "LOGIN_FAILED", meta={"reason": "unknown_or_inactive"})
            raise AuthError("Invalid credentials.")
        if u["locked"]:
            audit.log_event(conn, "LOGIN_FAILED", user_id=u["id"], meta={"reason": "locked"})
            raise AuthError("Account locked. Contact an administrator.")
        if not verify_password(password or "", u["password_hash"]):
            fails = u["failed_logins"] + 1
            locked = 1 if fails >= s.max_failed_logins else 0
            conn.execute("UPDATE users SET failed_logins=?, locked=? WHERE id=?", (fails, locked, u["id"]))
            audit.log_event(conn, "LOGIN_FAILED", user_id=u["id"], meta={"reason": "bad_password", "locked": bool(locked)})
            # commit the counter before raising
            conn.execute("COMMIT")
            conn.execute("BEGIN")
            raise AuthError("Invalid credentials.")
        token = new_token()
        now = datetime.now(timezone.utc)
        conn.execute("UPDATE users SET failed_logins=0 WHERE id=?", (u["id"],))
        conn.execute(
            "INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES (?,?,?,?)",
            (token_hash(token), u["id"], now.isoformat(timespec="seconds"),
             (now + timedelta(hours=s.session_hours)).isoformat(timespec="seconds")),
        )
        audit.log_event(conn, "LOGIN", user_id=u["id"])
    return {"token": token, "user": get_user(u["id"])}


def authenticate(token: str | None) -> dict:
    if not token:
        raise AuthError("Missing token.")
    with ro() as conn:
        r = conn.execute(
            "SELECT s.expires_at, s.revoked, u.id, u.active, u.locked FROM sessions s JOIN users u ON u.id=s.user_id "
            "WHERE s.token_hash=?",
            (token_hash(token),),
        ).fetchone()
    if not r or r["revoked"] or not r["active"] or r["locked"]:
        raise AuthError("Invalid or expired session.")
    if datetime.fromisoformat(r["expires_at"]) < datetime.now(timezone.utc):
        raise AuthError("Session expired.")
    return get_user(r["id"])


def logout(token: str) -> None:
    with tx() as conn:
        r = conn.execute("SELECT user_id FROM sessions WHERE token_hash=?", (token_hash(token),)).fetchone()
        conn.execute("UPDATE sessions SET revoked=1 WHERE token_hash=?", (token_hash(token),))
        if r:
            audit.log_event(conn, "LOGOUT", user_id=r["user_id"])


def unlock_user(user_id: int, actor: dict) -> None:
    require_role(actor, "ADMIN")
    with tx() as conn:
        conn.execute("UPDATE users SET locked=0, failed_logins=0 WHERE id=?", (user_id,))
        audit.log_event(conn, "USER_UNLOCKED", user_id=actor["id"], meta={"target_user_id": user_id})


def change_password(user: dict, old: str, new: str) -> None:
    with tx() as conn:
        r = conn.execute("SELECT password_hash FROM users WHERE id=?", (user["id"],)).fetchone()
        if not r or not verify_password(old, r["password_hash"]):
            raise AuthError("Current password is incorrect.")
        conn.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(new), user["id"]))
        conn.execute("UPDATE sessions SET revoked=1 WHERE user_id=?", (user["id"],))
        audit.log_event(conn, "PASSWORD_CHANGED", user_id=user["id"])


def require_role(user: dict, *roles: str) -> None:
    if user["role"] not in roles:
        raise PermissionDenied(f"This action requires role: {', '.join(roles)}.")
