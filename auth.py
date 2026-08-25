"""
auth.py
-------
H P M S & Associates - Practice Management System

Authentication rules implemented here:

1. Passwords are NEVER stored in plain text. They are hashed with
   PBKDF2-HMAC-SHA256 (1,00,000 iterations) using a random salt.
2. The FIRST person who registers automatically becomes the Admin.
3. After the Admin exists, open public signup stops. A new person can
   register only if the Admin has already added that e-mail address in
   the Employee Master (authorised_employees table).
4. Inactive employees / users cannot log in.
"""

import hashlib
import hmac
import os
import re

import database as db

PBKDF2_ITERATIONS = 100_000
NOT_AUTHORISED_MSG = "This email address has not been authorised by Admin."


# --------------------------------------------------------------------------
# Password hashing
# --------------------------------------------------------------------------
def hash_password(password):
    """Return 'salt$hash' - both hex encoded. A new random salt every time."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 salt, PBKDF2_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password, stored):
    """Check a typed password against the stored 'salt$hash' value."""
    try:
        salt_hex, hash_hex = stored.split("$")
    except (ValueError, AttributeError):
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 bytes.fromhex(salt_hex), PBKDF2_ITERATIONS)
    # compare_digest avoids leaking information through timing
    return hmac.compare_digest(digest.hex(), hash_hex)


# --------------------------------------------------------------------------
# Basic input validation
# --------------------------------------------------------------------------
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


def is_valid_email(email):
    return bool(EMAIL_PATTERN.match((email or "").strip()))


def validate_signup_input(name, email, password):
    """Return an error message, or None when the input is acceptable."""
    if not name or not name.strip():
        return "Please enter your full name."
    if not is_valid_email(email):
        return "Please enter a valid email address."
    if not password or len(password) < 6:
        return "Password must be at least 6 characters long."
    return None


# --------------------------------------------------------------------------
# Sign up
# --------------------------------------------------------------------------
def signup(name, email, password):
    """
    Create a login account.
    Returns (success: bool, message: str).
    """
    error = validate_signup_input(name, email, password)
    if error:
        return False, error

    email = email.strip().lower()

    if db.fetch_one("SELECT id FROM users WHERE LOWER(email) = ?", (email,)):
        return False, "An account already exists for this email address."

    first_user = db.user_count() == 0

    if first_user:
        # ---- The very first account becomes the Admin ------------------
        role, is_admin = "Partner", 1
    else:
        # ---- Everyone else must be pre-authorised by the Admin ---------
        emp = db.fetch_one(
            "SELECT * FROM authorised_employees WHERE LOWER(email) = ?", (email,))
        if emp is None:
            return False, NOT_AUTHORISED_MSG
        if not emp["active"]:
            return False, "This employee record is marked Inactive. Please contact Admin."
        role, is_admin = emp["role"], 0

    db.execute(
        """INSERT INTO users (name, email, password_hash, role, is_admin, active, created_at)
           VALUES (?, ?, ?, ?, ?, 1, ?)""",
        (name.strip(), email, hash_password(password), role, is_admin, db.now_str()),
    )

    if first_user:
        # Keep the Admin in the employee master too, so tasks can be
        # delegated to the Admin as well.
        if not db.fetch_one("SELECT id FROM authorised_employees WHERE LOWER(email) = ?",
                            (email,)):
            db.add_employee(name, email, "Partner", "", 1)
        return True, "Admin account created successfully. Please login."

    return True, "Account created successfully. Please login."


# --------------------------------------------------------------------------
# Login
# --------------------------------------------------------------------------
def login(email, password):
    """
    Verify credentials.
    Returns (user_dict, None) on success or (None, message) on failure.
    """
    email = (email or "").strip().lower()
    if not email or not password:
        return None, "Please enter both email and password."

    user = db.fetch_one("SELECT * FROM users WHERE LOWER(email) = ?", (email,))
    if user is None or not verify_password(password, user["password_hash"]):
        return None, "Invalid email or password."
    if not user["active"]:
        return None, "This account is inactive. Please contact Admin."

    # Build the small session object used everywhere in the application.
    # employee_id is the link to the employee master and is what every
    # employee-level database query filters on.
    session_user = {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "is_admin": bool(user["is_admin"]),
        "employee_id": db.employee_id_for_email(user["email"]),
    }
    return session_user, None


def change_password(user_id, old_password, new_password):
    """Let a logged-in user change their own password."""
    user = db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if user is None or not verify_password(old_password, user["password_hash"]):
        return False, "Current password is incorrect."
    if len(new_password) < 6:
        return False, "New password must be at least 6 characters long."
    db.execute("UPDATE users SET password_hash = ? WHERE id = ?",
               (hash_password(new_password), user_id))
    return True, "Password changed successfully."


def signup_is_open():
    """True while no Admin exists (i.e. the very first registration)."""
    return db.user_count() == 0
