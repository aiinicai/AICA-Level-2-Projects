"""
auth.py - Fixed-password role check (Admin / User).

Only SHA-256 hashes are used, never plaintext passwords.

Production builds: create an untracked file `auth_local.py` next to this file
(copy `auth_local.py.example`) defining ADMIN_HASH and USER_HASH. It is listed
in .gitignore and must never be committed.

Public/demo copy: if `auth_local.py` is absent, DEMO hashes are used so the
app can be run and reviewed. Demo credentials (NOT for real use):
    Admin : Admin@Demo1
    User  : User@Demo1

To generate a hash:
    python -c "import hashlib; print(hashlib.sha256(b'YOUR_PASSWORD').hexdigest())"
"""
import hashlib

try:
    from auth_local import ADMIN_HASH, USER_HASH  # private, not in the repo
except ImportError:
    ADMIN_HASH = "1afb26dcb83a5f442ce1eedf9e927636fa49795a328ca6dd7ab8a9cd73fae80e"  # demo
    USER_HASH = "7fd0a053160bb35acbc1de37eab5d63650df839e11e352671e71dfe12a6f6b15"   # demo


def check_password(password: str):
    """
    Returns 'admin', 'user', or None depending on which fixed password matches.
    """
    if not password:
        return None
    h = hashlib.sha256(password.encode("utf-8")).hexdigest()
    if h == ADMIN_HASH:
        return "admin"
    if h == USER_HASH:
        return "user"
    return None
