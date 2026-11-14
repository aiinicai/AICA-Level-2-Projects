"""
============================================================================
 JE TESTING  --  Login & licence checks
----------------------------------------------------------------------------
 * Two roles:  admin  (run + Settings + manage users)
               user   (run testing and open the workpaper only)
 * Passwords are never stored: only a salted PBKDF2-SHA256 hash
   (600,000 iterations, the OWASP recommendation).
 * Every login ID needs a LICENCE KEY sold by the vendor.  The key is a
   small JSON record (licensee, login ID, role, expiry) signed with the
   vendor's Ed25519 PRIVATE key.  This program holds only the PUBLIC key,
   so it can check a licence but can never create one.
 * The role used is the role written inside the signed licence, so editing
   users.json to make a normal user an admin does not work.
============================================================================
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import date

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

import je_testing as core

USERS_PATH = core.BASE_DIR / "users.json"
PBKDF2_ITERATIONS = 600_000
MAX_LOGIN_ATTEMPTS = 5
LICENCE_PREFIX = "JE1-"

# Vendor's PUBLIC key (raw Ed25519, base64).  The matching PRIVATE key stays
# with the vendor (vendor/ folder, never shipped, never uploaded).
VENDOR_PUBLIC_KEY_B64 = "rUy6cTPo97w7uHRqQ9G2+pmK8Q88+CStn9P7ViI1aVk="


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------
def hash_password(password, salt=None, iterations=PBKDF2_ITERATIONS):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return {"salt": salt.hex(), "hash": digest.hex(), "iterations": iterations}


def check_password(password, record):
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 bytes.fromhex(record["salt"]), int(record["iterations"]))
    return hmac.compare_digest(digest.hex(), record["hash"])     # constant-time compare


# ---------------------------------------------------------------------------
# User store  (users.json next to the program)
# ---------------------------------------------------------------------------
def load_users(path=USERS_PATH):
    if not path.exists():
        raise FileNotFoundError(
            f"User file not found: {path.name}\nThe software has not been set up. "
            "Contact your software vendor.")
    return json.loads(path.read_text(encoding="utf-8"))


def save_users(store, path=USERS_PATH):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(store, indent=2), encoding="utf-8")
    os.replace(tmp, path)                        # atomic: never a half-written file


def authenticate(username, password, store):
    """Return the user's record if the password is right, else None.  The
    same message is shown for an unknown ID and a wrong password, so the
    screen does not reveal which login IDs exist."""
    rec = store.get("users", {}).get(username.strip().lower())
    if rec is None:
        hash_password(password)                 # same delay as a real check
        return None
    return rec if check_password(password, rec["password"]) else None


def set_password(store, username, new_password):
    if len(new_password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    store["users"][username]["password"] = hash_password(new_password)


# ---------------------------------------------------------------------------
# Licence keys
# ---------------------------------------------------------------------------
def _b64d(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def verify_licence(key, username):
    """Check a licence key.  Returns the licence details if valid for this
    login ID, otherwise raises ValueError with a plain-English reason."""
    key = "".join(key.split())                  # ignore spaces / line breaks
    if not key.startswith(LICENCE_PREFIX) or "." not in key:
        raise ValueError("This is not a JE Testing licence key.")
    body, sig = key[len(LICENCE_PREFIX):].split(".", 1)
    try:
        payload_bytes, sig_bytes = _b64d(body), _b64d(sig)
        Ed25519PublicKey.from_public_bytes(_b64d(VENDOR_PUBLIC_KEY_B64)).verify(
            sig_bytes, payload_bytes)
        lic = json.loads(payload_bytes)
    except (InvalidSignature, ValueError, TypeError):
        raise ValueError("The licence key is not genuine or has been altered.") from None
    if lic.get("username") != username:
        raise ValueError(f"This licence belongs to login ID '{lic.get('username')}', "
                         f"not '{username}'.")
    if date.fromisoformat(lic["expires"]) < date.today():
        raise ValueError(f"This licence expired on {lic['expires']}. Please renew it.")
    if lic.get("role") not in ("admin", "user"):
        raise ValueError("The licence has an unknown role.")
    return lic


def licence_status(rec, username):
    """(licence dict, None) if the stored licence is valid, else (None, reason)."""
    key = rec.get("licence_key", "")
    if not key:
        return None, "This login ID has not been activated yet."
    try:
        return verify_licence(key, username), None
    except ValueError as e:
        return None, str(e)
