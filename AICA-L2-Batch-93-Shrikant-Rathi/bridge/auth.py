"""
Users, passwords and sessions for the LookThrough data bridge.

  * Passwords: PBKDF2-HMAC-SHA256, 600,000 iterations, 16-byte random salt (OWASP Password Storage Cheat
    Sheet recommendation for PBKDF2-SHA256); compared in constant time. Plain passwords are never stored or logged.
  * Lockout: 5 consecutive failures lock the account for 15 minutes. Unknown user names take the same time.
  * Sessions: 32-byte random token in an HttpOnly, SameSite=Strict cookie; held in memory, so restarting the bridge
    signs everyone out. A session ends after 30 minutes without activity (automatic background polls, marked
    X-LT-Background, do not count) and in any case 8 hours after sign-in. An idle expiry is audited.
  * Roles: viewer (read), analyst (+ data entry and refresh), admin (+ users). The first account created is admin.
Stored in data/user/users.json (LOOKTHROUGH_USER_DIR redirects it for tests); every change is audited.
"""
import hashlib
import hmac
import re
import secrets
import threading
import time

import ledger
from common import load_json, now_iso, save_json

ROLES = ("viewer", "analyst", "admin")
ITERATIONS = 600_000
MAX_FAILS, LOCK_SECONDS, SESSION_SECONDS = 5, 15 * 60, 8 * 3600
IDLE_SECONDS = 30 * 60  # no activity for this long ends the session
USERNAME_RE = re.compile(r"^[a-z][a-z0-9._-]{2,31}$")
_LOCK = threading.RLock()
_SESSIONS: dict[str, dict] = {}
_DUMMY_SALT = secrets.token_bytes(16)


class AuthError(ValueError):
    """Shown to the user; nothing changed."""


def _path():
    return ledger.USER_DIR / "users.json"


def _load():
    return load_json(_path()) or {"users": {}}


def _save(d):
    save_json(_path(), d, indent=1)


def _hash(password, salt, iterations=ITERATIONS):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations).hex()


def has_users():
    return bool(_load()["users"])


PASSWORD_MIN, PASSWORD_MAX = 6, 8  # user-set policy


def check_password_policy(pw):
    if not PASSWORD_MIN <= len(pw or "") <= PASSWORD_MAX:
        raise AuthError(f"Password must be {PASSWORD_MIN} to {PASSWORD_MAX} characters.")
    if pw.lower() == pw or pw.upper() == pw or not any(c.isdigit() for c in pw):
        raise AuthError("Password must mix upper- and lower-case letters and include a digit.")


def create_user(username, password, role, by):
    username = (username or "").strip().lower()
    if not USERNAME_RE.match(username):
        raise AuthError("User name: 3-32 characters, lower-case letters, digits, dot, dash or underscore, starting with a letter.")
    if role not in ROLES:
        raise AuthError(f"Role must be one of: {', '.join(ROLES)}.")
    check_password_policy(password)
    with _LOCK:
        d = _load()
        if username in d["users"]:
            raise AuthError(f"User {username!r} already exists.")
        salt = secrets.token_bytes(16)
        d["users"][username] = {"salt": salt.hex(), "hash": _hash(password, salt), "iterations": ITERATIONS, "role": role,
                                "active": True, "fails": 0, "locked_until": 0, "created_at": now_iso(), "created_by": by}
        _save(d)
    ledger.audit(by, "USER_CREATE", None, {"user": username, "role": role})


def verify(username, password):
    """Return the user's role on success; raise AuthError otherwise (same message for unknown user and bad password)."""
    username = (username or "").strip().lower()
    with _LOCK:
        d = _load()
        u = d["users"].get(username)
        if not u or not u.get("active"):
            _hash(password or "", _DUMMY_SALT)  # equalise timing
            ledger.audit(username or "?", "LOGIN_FAILED", None, None, "unknown or disabled user")
            raise AuthError("Wrong user name or password.")
        if u["locked_until"] > time.time():
            raise AuthError(f"Account locked after {MAX_FAILS} failed attempts. Try again in {int((u['locked_until'] - time.time()) / 60) + 1} minutes.")
        ok = hmac.compare_digest(_hash(password or "", bytes.fromhex(u["salt"]), u["iterations"]), u["hash"])
        if not ok:
            u["fails"] += 1
            if u["fails"] >= MAX_FAILS:
                u["locked_until"], u["fails"] = time.time() + LOCK_SECONDS, 0
            _save(d)
            ledger.audit(username, "LOGIN_FAILED", None, None, "locked" if u["locked_until"] > time.time() else "bad password")
            raise AuthError("Wrong user name or password.")
        u["fails"], u["locked_until"], u["last_login"] = 0, 0, now_iso()
        _save(d)
    ledger.audit(username, "LOGIN", None, None)
    return u["role"]


def list_users():
    return [{"user": k, "role": v["role"], "active": v["active"], "created_at": v["created_at"], "last_login": v.get("last_login"),
             "locked": v["locked_until"] > time.time()} for k, v in sorted(_load()["users"].items())]


def update_user(username, by, role=None, active=None, password=None):
    with _LOCK:
        d = _load()
        u = d["users"].get(username)
        if not u:
            raise AuthError(f"No user {username!r}.")
        before = {"role": u["role"], "active": u["active"]}
        if role is not None:
            if role not in ROLES:
                raise AuthError(f"Role must be one of: {', '.join(ROLES)}.")
            u["role"] = role
        if active is not None:
            u["active"] = bool(active)
        admins = [k for k, v in d["users"].items() if v["role"] == "admin" and v["active"]]
        if not admins:
            raise AuthError("At least one active admin must remain.")
        if password is not None:
            check_password_policy(password)
            salt = secrets.token_bytes(16)
            u.update(salt=salt.hex(), hash=_hash(password, salt), iterations=ITERATIONS, fails=0, locked_until=0)
        _save(d)
    if active is False or role is not None or password is not None:
        end_sessions_for(username)
    ledger.audit(by, "USER_UPDATE", before, {"user": username, "role": u["role"], "active": u["active"], "password_reset": password is not None})


def new_session(username, role):
    token = secrets.token_urlsafe(32)
    with _LOCK:
        now = time.time()
        _SESSIONS[token] = {"user": username, "role": role, "exp": now + SESSION_SECONDS, "seen": now}
    return token


def get_session(token, touch=True):
    """The live session for a token, or None. touch=False (a background poll) checks it without counting as activity."""
    now = time.time()
    with _LOCK:
        s = _SESSIONS.get(token or "")
        if s and s["exp"] > now and now - s["seen"] <= IDLE_SECONDS:
            if touch:
                s["seen"] = now
            return s
        _SESSIONS.pop(token or "", None)
    if s and s["exp"] > now:  # alive by the 8-hour cap, so it ended for inactivity
        ledger.audit(s["user"], "SESSION_IDLE_EXPIRED", None, None, f"no activity for {IDLE_SECONDS // 60} minutes")
    return None


def end_session(token):
    with _LOCK:
        _SESSIONS.pop(token or "", None)


def end_sessions_for(username):
    with _LOCK:
        for k in [k for k, v in _SESSIONS.items() if v["user"] == username]:
            _SESSIONS.pop(k, None)


def allowed(role, need):
    return ROLES.index(role) >= ROLES.index(need)


def reset_local(username, password):
    """Recovery when a password is forgotten or an account is locked: run on THIS PC from a console (Reset_Password.bat),
    never over the network. Sets a new password (the password rule applies), clears the lockout, re-enables the
    account and signs out its sessions. Audited as PASSWORD_RESET_LOCAL."""
    username = (username or "").strip().lower()
    update_user(username, "local-console", active=True, password=password)
    ledger.audit("local-console", "PASSWORD_RESET_LOCAL", None, {"user": username}, "password reset from a console on this PC")


def _cli_reset(argv):
    import getpass
    users = _load()["users"]
    if not users:
        print("No accounts yet. Start the app (Start_LookThrough.bat) to create the admin account.")
        return 1
    print("Accounts: " + ", ".join(f"{k} ({v['role']}{', locked' if v['locked_until'] > time.time() else ''})" for k, v in sorted(users.items())))
    admins = [k for k, v in users.items() if v["role"] == "admin"]
    default = argv[0] if argv else (admins[0] if len(admins) == 1 else "")
    name = (input(f"User name to reset [{default}]: ").strip() or default).lower()
    if name not in users:
        print(f"No account named {name!r}. Nothing changed.")
        return 1
    print("New password: 6 to 8 characters, with upper- and lower-case letters and a digit. It is not shown as you type.")
    for _ in range(3):
        pw = getpass.getpass("New password: ")
        if pw != getpass.getpass("Type it again: "):
            print("The two entries differ. Try again.")
            continue
        try:
            reset_local(name, pw)
        except AuthError as e:
            print(f"{e} Try again.")
            continue
        print(f"Password reset for {name}; the account is unlocked. Sign in at http://localhost:8765/ (no restart needed).")
        return 0
    print("Nothing changed.")
    return 1


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2 and sys.argv[1] == "reset":
        sys.exit(_cli_reset(sys.argv[2:]))
    print("Usage: python bridge/auth.py reset [user name]   (or double-click Reset_Password.bat)")
    sys.exit(2)
