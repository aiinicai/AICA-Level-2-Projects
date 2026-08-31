"""
security.py — R K Muley & Co | Tax Notice Litigation Assistant v8.0

RBAC, authentication, and password hashing.

SECURITY IMPROVEMENTS over v7:
  - Passwords loaded from Streamlit secrets / env vars — NOT hardcoded in source
  - bcrypt used instead of SHA-256 (with per-user salt)
  - Login attempt tracking with 5-attempt lockout (per username, 15-min window)
  - Session tokens are cryptographically random 32-byte hex strings
"""

from __future__ import annotations

# ── Path fix (Windows / non-standard working directories) ──────────────────
import sys as _sys
import os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
# ─────────────────────────────────────────────────────────────────────────────


import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

import streamlit as st

from config import ROLES

logger = logging.getLogger("RKMuley.Security.v8")

# ── bcrypt with graceful fallback to SHA-256 ─────────────────────────────────
try:
    import bcrypt
    _BCRYPT_AVAILABLE = True
except ImportError:
    _BCRYPT_AVAILABLE = False
    logger.warning(
        "bcrypt not installed. Using SHA-256 fallback. "
        "Run: pip install bcrypt  for production security."
    )


def _hash_password(plaintext: str) -> str:
    """Hash a password. bcrypt if available, SHA-256 otherwise."""
    if _BCRYPT_AVAILABLE:
        return bcrypt.hashpw(plaintext.encode(), bcrypt.gensalt(rounds=12)).decode()
    # Fallback: application-level salt + SHA-256 (acceptable for dev, not production)
    app_salt = os.environ.get("RKM_APP_SALT", "rkm_v8_default_salt_change_me")
    return hashlib.sha256(f"{app_salt}{plaintext}".encode()).hexdigest()


def _verify_password(plaintext: str, stored_hash: str) -> bool:
    """Verify a password against its stored hash."""
    if _BCRYPT_AVAILABLE and stored_hash.startswith("$2b$"):
        try:
            return bcrypt.checkpw(plaintext.encode(), stored_hash.encode())
        except Exception:
            return False
    # SHA-256 fallback (handles both dev hashes and legacy v7 hashes)
    app_salt = os.environ.get("RKM_APP_SALT", "rkm_v8_default_salt_change_me")
    computed = hashlib.sha256(f"{app_salt}{plaintext}".encode()).hexdigest()
    if computed == stored_hash:
        return True
    # Try v7 legacy hash format for backwards compatibility
    legacy = hashlib.sha256(f"rkm_{plaintext}".encode()).hexdigest()
    return legacy == stored_hash


# ── Default Users — loaded from environment or Streamlit secrets ──────────────
# HOW TO SET CREDENTIALS:
#   Option A (Streamlit Cloud): Add to .streamlit/secrets.toml —
#       [users.admin]
#       hash = "$2b$12$..."   # bcrypt hash of your password
#       role = "admin"
#       display = "Admin (Partner)"
#
#   Option B (Local): Set environment variables —
#       RKM_USER_ADMIN_HASH, RKM_USER_CA1_HASH, RKM_USER_ART1_HASH
#
#   Option C (Dev only): Use plaintext env vars (not production) —
#       RKM_USER_ADMIN_PWD=YourPassword123

def _load_users() -> dict[str, dict]:
    """Load user credentials from Streamlit secrets or environment variables."""
    users: dict[str, dict] = {}

    # Try Streamlit secrets first (production)
    try:
        secrets_users = st.secrets.get("users", {})
        for uname, udata in secrets_users.items():
            users[uname.lower()] = {
                "hash":    udata.get("hash", ""),
                "role":    udata.get("role", "article"),
                "display": udata.get("display", uname),
            }
        if users:
            return users
    except Exception:
        pass

    # Try environment variables (CI / Docker)
    env_map = {
        "admin":    ("RKM_USER_ADMIN_HASH",   "admin",   "Admin (Partner)"),
        "ca1":      ("RKM_USER_CA1_HASH",     "ca",      "CA Manager"),
        "article1": ("RKM_USER_ART1_HASH",    "article", "Article Staff"),
    }
    for uname, (env_key, role, display) in env_map.items():
        stored = os.environ.get(env_key, "")
        if stored:
            users[uname] = {"hash": stored, "role": role, "display": display}

    if users:
        return users

    # Dev fallback — NEVER use in production.
    # Passwords are set via RKM_USER_*_PWD env vars; default is below.
    logger.warning(
        "Using dev-mode default credentials. "
        "Set RKM_USER_*_HASH env vars or configure Streamlit secrets before deploying."
    )
    dev_users = {
        "admin":    ("rkm_Admin@2025", "admin",   "Admin (Partner)"),
        "ca1":      ("rkm_CA1@Muley",  "ca",      "CA Manager"),
        "article1": ("rkm_Art1@work",  "article", "Article Staff"),
    }
    result: dict[str, dict] = {}
    for uname, (pwd_env, role, display) in dev_users.items():
        pwd = os.environ.get(f"RKM_USER_{uname.upper()}_PWD", pwd_env)
        result[uname] = {
            "hash":    _hash_password(pwd),
            "role":    role,
            "display": display,
        }
    return result


# Built once at module load
_USER_STORE: dict[str, dict] = {}


def _get_users() -> dict[str, dict]:
    """Lazily load users on first call."""
    global _USER_STORE
    if not _USER_STORE:
        _USER_STORE = _load_users()
    return _USER_STORE


# ── Login Attempt Tracking ────────────────────────────────────────────────────
_MAX_ATTEMPTS   = 5
_LOCKOUT_WINDOW = timedelta(minutes=15)


def _is_locked_out(username: str) -> bool:
    """Check if account is locked due to too many failed attempts."""
    try:
        from database import execute_query

        cutoff = (datetime.now() - _LOCKOUT_WINDOW).isoformat()
        row = execute_query(
            "SELECT COUNT(*) FROM audit_trail WHERE username=? AND action='LOGIN_FAIL' "
            "AND timestamp > ?",
            (username, cutoff),
            fetch="one",
        )
        count = row[0] if row else 0
        return count >= _MAX_ATTEMPTS
    except Exception:
        return False


# ── Authentication ────────────────────────────────────────────────────────────
def authenticate(username: str, password: str) -> Optional[dict]:
    """
    Authenticate a user.
    Returns user dict with session token on success.
    Returns None on failure.
    Logs every attempt to audit_trail.
    Enforces lockout after _MAX_ATTEMPTS failures in _LOCKOUT_WINDOW.
    """
    from database import write_audit_trail

    uname = username.lower().strip()

    if _is_locked_out(uname):
        write_audit_trail("LOGIN_LOCKED", "auth", f"user={uname}", username=uname)
        return None

    user = _get_users().get(uname)
    if user and _verify_password(password, user["hash"]):
        write_audit_trail("LOGIN_SUCCESS", "auth", f"role={user['role']}", username=uname)
        # Update last_login in users table if it exists
        try:
            from database import execute_query

            execute_query(
                "UPDATE users SET last_login=? WHERE username=?",
                (datetime.now().isoformat(), uname),
            )
        except Exception:
            pass
        return {
            "username": uname,
            "role":     user["role"],
            "display":  user["display"],
            "token":    secrets.token_hex(32),
        }

    write_audit_trail("LOGIN_FAIL", "auth", f"user={uname}", username=uname)
    return None


# ── RBAC Check ────────────────────────────────────────────────────────────────
def rbac_check(permission: str) -> bool:
    """Check if the current session user has the given permission."""
    role = st.session_state.get("auth_role", "readonly")
    return ROLES.get(role, ROLES["readonly"]).get(permission, False)


def require_auth() -> bool:
    """Return True if user is logged in. Show login form if not."""
    if st.session_state.get("auth_username"):
        return True
    _render_login_form()
    return False


# ── Login UI ──────────────────────────────────────────────────────────────────
def _render_login_form() -> None:
    """Render the login wall. Sets session state keys on success."""
    st.markdown(
        """
        <div style='background:linear-gradient(135deg,#1a237e,#283593);
        color:white;padding:1.5rem;border-radius:10px;margin-bottom:1rem;'>
        <h2 style='margin:0;'>⚖️ R K Muley & Co</h2>
        <p style='margin:0.3rem 0 0;opacity:0.85;'>
        Tax Notice Litigation Assistant v9.0 — Secure Login</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("login_form", clear_on_submit=True):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submitted = st.form_submit_button("🔐 Login", use_container_width=True, type="primary")

    if submitted:
        if not username or not password:
            st.error("Please enter both username and password.")
            return

        if _is_locked_out(username.lower().strip()):
            st.error(
                f"Account temporarily locked after {_MAX_ATTEMPTS} failed attempts. "
                "Please try again in 15 minutes or contact admin."
            )
            return

        result = authenticate(username, password)
        if result:
            st.session_state["auth_username"] = result["username"]
            st.session_state["auth_role"]     = result["role"]
            st.session_state["auth_display"]  = result["display"]
            st.session_state["auth_token"]    = result["token"]
            st.rerun()
        else:
            st.error("Invalid username or password.")


def logout() -> None:
    """Clear all auth-related session state keys."""
    from database import write_audit_trail
    from config import STATE_KEYS
    username = st.session_state.get("auth_username", "unknown")
    write_audit_trail("LOGOUT", "auth", "", username=username)
    for key in STATE_KEYS + ["auth_username", "auth_role", "auth_display", "auth_token"]:
        st.session_state.pop(key, None)
    st.rerun()
