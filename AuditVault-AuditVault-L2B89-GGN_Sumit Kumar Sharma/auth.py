"""
AuditVault - Authentication, Session Management, and Role-Based Access Control
Supports Admin Impersonation ("Switch User") with permanent audit logging.
"""

import os
import hashlib
import binascii
import json
import platform
import uuid
from pathlib import Path
import streamlit as st
from datetime import datetime
from typing import Optional, Tuple
from models import User
from utils import log_audit_action, current_indian_timestamp_str

# Optional bcrypt support with secure PBKDF2 fallback
try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False


# =====================================================================
# 1. SECURE PASSWORD HASHING
# =====================================================================

def hash_password(password: str) -> str:
    """Generate salted hash using bcrypt or PBKDF2-SHA256."""
    if HAS_BCRYPT:
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")
    else:
        # Fallback to PBKDF2
        salt = os.urandom(16)
        pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return f"pbkdf2${binascii.hexlify(salt).decode('ascii')}${binascii.hexlify(pwd_hash).decode('ascii')}"


def verify_password(stored_hash: str, provided_password: str) -> bool:
    """Verify provided password against stored hash."""
    if not stored_hash or not provided_password:
        return False

    if stored_hash.startswith("pbkdf2$"):
        try:
            parts = stored_hash.split("$")
            salt = binascii.unhexlify(parts[1])
            expected_hash = parts[2]
            pwd_hash = hashlib.pbkdf2_hmac("sha256", provided_password.encode("utf-8"), salt, 100_000)
            return binascii.hexlify(pwd_hash).decode("ascii") == expected_hash
        except Exception:
            return False

    if HAS_BCRYPT:
        try:
            return bcrypt.checkpw(provided_password.encode("utf-8"), stored_hash.encode("utf-8"))
        except Exception:
            pass

    # Basic SHA256 fallback for demo compatibility if needed
    test_hash = hashlib.sha256(provided_password.encode("utf-8")).hexdigest()
    return test_hash == stored_hash


DEMO_USERNAME = "demo.viewer"
DEMO_BINDING_FILE = Path(__file__).resolve().parent / "AuditVault_Data" / "demo_device_binding.json"


def get_device_fingerprint() -> str:
    """Return a privacy-preserving fingerprint for local demo-device binding."""
    raw = f"{platform.system()}|{platform.machine()}|{platform.node()}|{uuid.getnode()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def authorize_demo_device(username: str) -> Tuple[bool, str]:
    """Bind the shared demo account to the first computer that activates it."""
    if username.strip().lower() != DEMO_USERNAME:
        return True, ""

    DEMO_BINDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    fingerprint = get_device_fingerprint()
    if DEMO_BINDING_FILE.exists():
        try:
            existing = json.loads(DEMO_BINDING_FILE.read_text(encoding="utf-8"))
            if existing.get("fingerprint") == fingerprint:
                return True, ""
            return False, "This demo account is already activated on another computer."
        except (OSError, ValueError, TypeError):
            return False, "The demo activation record is invalid. Contact the administrator."

    record = {
        "username": DEMO_USERNAME,
        "fingerprint": fingerprint,
        "activated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z"
    }
    DEMO_BINDING_FILE.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return True, "Demo access has been activated on this computer."


# =====================================================================
# 2. USER AUTHENTICATION & MANAGEMENT
# =====================================================================

def authenticate_user(session, username: str, password: str) -> Optional[User]:
    """Validate credentials and return User model or None."""
    clean_user = username.strip()
    user = session.query(User).filter(
        User.username.ilike(clean_user), User.is_deleted == False
    ).first()
    if user and verify_password(user.password_hash, password):
        return user
    return None


def get_user_by_id(session, user_id: int) -> Optional[User]:
    """Fetch user by ID."""
    return session.query(User).filter(User.user_id == user_id).first()


def reset_user_password(session, user_id: int, new_password: str, admin_user: User) -> Tuple[bool, str]:
    """Reset a user's password (Admin feature)."""
    target_user = get_user_by_id(session, user_id)
    if not target_user:
        return False, "Target user not found."

    target_user.password_hash = hash_password(new_password)
    session.commit()

    log_audit_action(
        session=session,
        action_type="PASSWORD_RESET",
        target_entity="User",
        target_id=target_user.user_id,
        description=f"Admin '{admin_user.name}' reset password for user '{target_user.username}' ({target_user.name}).",
        user_id=admin_user.user_id,
        acting_user_name=admin_user.name
    )
    return True, f"Password for {target_user.name} successfully reset."


# =====================================================================
# 3. STREAMLIT SESSION STATE MANAGEMENT
# =====================================================================

def init_session_state():
    """Initialize all session state keys needed for AuditVault."""
    defaults = {
        "authenticated": False,
        "user_id": None,
        "username": None,
        "name": None,
        "role": None,
        "email": None,
        "theme": "light",
        "impersonating": False,
        "true_admin_id": None,
        "true_admin_name": None,
        "active_page": "Dashboard",
        "selected_engagement_id": None,
        "selected_rcm_line_item": None,
        "show_tour": False,
        "notifications_count": 0,
        "search_query": ""
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def login_user(user: User, session):
    """Set session state on successful user login."""
    st.session_state.authenticated = True
    st.session_state.user_id = user.user_id
    st.session_state.username = user.username
    st.session_state.name = user.name
    st.session_state.role = user.role
    st.session_state.email = user.email
    st.session_state.theme = user.theme_preference or "light"
    st.session_state.impersonating = False
    st.session_state.true_admin_id = None
    st.session_state.true_admin_name = None
    st.session_state.show_tour = bool(user.is_first_login)

    # Log successful login
    log_audit_action(
        session=session,
        action_type="LOGIN",
        target_entity="Session",
        target_id=user.username,
        description=f"User '{user.name}' logged in successfully as {user.role}.",
        user_id=user.user_id,
        acting_user_name=user.name
    )


def logout_user(session=None):
    """Clean session state and log sign-out."""
    if session and st.session_state.authenticated:
        log_audit_action(
            session=session,
            action_type="LOGOUT",
            target_entity="Session",
            target_id=st.session_state.username,
            description=f"User '{st.session_state.name}' signed out of AuditVault.",
            user_id=st.session_state.user_id or 0,
            acting_user_name=st.session_state.name or "Unknown",
            true_admin_id=st.session_state.true_admin_id,
            true_admin_name=st.session_state.true_admin_name
        )

    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.name = None
    st.session_state.role = None
    st.session_state.email = None
    st.session_state.impersonating = False
    st.session_state.true_admin_id = None
    st.session_state.true_admin_name = None
    st.session_state.selected_engagement_id = None
    st.session_state.selected_rcm_line_item = None


# =====================================================================
# 4. ADMIN USER IMPERSONATION ("SWITCH USER")
# =====================================================================

def impersonate_user(target_user: User, session):
    """
    ROLE 1 REQUIREMENT:
    Switch into any user account without re-entering credentials for support purposes.
    Audit log entry: 'Admin X accessed AuditVault as User Y at [timestamp]'.
    """
    admin_id = st.session_state.true_admin_id or st.session_state.user_id
    admin_name = st.session_state.true_admin_name or st.session_state.name

    st.session_state.impersonating = True
    st.session_state.true_admin_id = admin_id
    st.session_state.true_admin_name = admin_name

    # Switch identity to target user
    st.session_state.user_id = target_user.user_id
    st.session_state.username = target_user.username
    st.session_state.name = target_user.name
    st.session_state.role = target_user.role
    st.session_state.email = target_user.email
    st.session_state.active_page = "Dashboard"

    t_str = current_indian_timestamp_str()
    log_audit_action(
        session=session,
        action_type="IMPERSONATE",
        target_entity="User",
        target_id=target_user.username,
        description=f"Admin {admin_name} accessed AuditVault as User {target_user.name} at {t_str}",
        user_id=target_user.user_id,
        acting_user_name=target_user.name,
        true_admin_id=admin_id,
        true_admin_name=admin_name
    )


def exit_impersonation(session):
    """Return from impersonation back to the Admin account."""
    if not st.session_state.impersonating or not st.session_state.true_admin_id:
        return

    admin_user = get_user_by_id(session, st.session_state.true_admin_id)
    if not admin_user:
        logout_user(session)
        return

    acting_name = st.session_state.name
    log_audit_action(
        session=session,
        action_type="EXIT_IMPERSONATION",
        target_entity="User",
        target_id=admin_user.username,
        description=f"Admin {admin_user.name} ended impersonation session of {acting_name}.",
        user_id=admin_user.user_id,
        acting_user_name=admin_user.name
    )

    st.session_state.impersonating = False
    st.session_state.user_id = admin_user.user_id
    st.session_state.username = admin_user.username
    st.session_state.name = admin_user.name
    st.session_state.role = admin_user.role
    st.session_state.email = admin_user.email
    st.session_state.true_admin_id = None
    st.session_state.true_admin_name = None
    st.session_state.active_page = "Admin Panel"


# =====================================================================
# 5. PERMISSION CHECKERS
# =====================================================================

def is_admin() -> bool:
    return st.session_state.get("role") == "Admin"

def is_manager() -> bool:
    return st.session_state.get("role") == "Manager"

def is_team_member() -> bool:
    return st.session_state.get("role") == "Team Member"

def is_manager_or_admin() -> bool:
    role = st.session_state.get("role")
    return role in ["Admin", "Manager"]
