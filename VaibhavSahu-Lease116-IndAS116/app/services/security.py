"""Authentication, sessions and role-based permissions."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from typing import Optional

from .. import config

ROLES = {
    "ADMIN": ("Administrator", ["*"]),
    "LEASE_ACCOUNTANT": ("Lease Accountant", ["lease.read", "lease.write", "lease.calculate", "lease.submit", "event.write",
                                              "journal.read", "journal.generate", "report.read", "export", "ai.use",
                                              "import.write", "document.write", "rate.write", "disclosure.read", "audit.read"]),
    "PREPARER": ("Preparer", ["lease.read", "lease.write", "lease.calculate", "lease.submit", "event.write", "journal.read",
                              "report.read", "export", "ai.use", "document.write", "import.write", "disclosure.read"]),
    "REVIEWER": ("Reviewer", ["lease.read", "lease.review", "journal.read", "report.read", "export", "disclosure.read",
                              "audit.read"]),
    "APPROVER": ("Approver", ["lease.read", "lease.review", "lease.approve", "event.approve", "journal.read", "journal.post",
                              "period.lock", "rate.approve", "import.approve", "report.read", "export", "disclosure.read",
                              "audit.read"]),
    "AUDITOR": ("Auditor", ["lease.read", "journal.read", "report.read", "export", "disclosure.read", "audit.read"]),
    "READ_ONLY": ("Read-only User", ["lease.read", "report.read", "disclosure.read"]),
}

PBKDF2_ITERATIONS = 200_000
SESSION_HOURS = 12
COOKIE_NAME = "lease116_session"


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_b64, dk_b64 = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt_b64), int(iters))
        return hmac.compare_digest(dk, base64.b64decode(dk_b64))
    except Exception:
        return False


def make_token(user_id: int, hours: int = SESSION_HOURS) -> str:
    exp = int(time.time()) + hours * 3600
    payload = f"{user_id}:{exp}"
    sig = hmac.new(config.secret_key().encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}:{sig}".encode()).decode()


def read_token(token: str) -> Optional[int]:
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        uid, exp, sig = raw.split(":")
        payload = f"{uid}:{exp}"
        good = hmac.new(config.secret_key().encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, good) or int(exp) < time.time():
            return None
        return int(uid)
    except Exception:
        return None


def permissions_for(role_code: str) -> list[str]:
    return ROLES.get(role_code, ("", []))[1]


def has_perm(role_code: str, perm: str) -> bool:
    perms = permissions_for(role_code)
    return "*" in perms or perm in perms
