"""Users, passwords and roles. Passwords are stored as salted PBKDF2-SHA256 hashes (Python stdlib)."""
import hashlib
import hmac
import secrets

from . import db

ROLES = ["Partner", "Manager", "Staff"]
ITERATIONS = 200_000

# Which pages each role can open
ACCESS = {
    "Partner": {"dashboard", "tasks", "clients", "calendar", "ai", "team", "billing", "documents", "settings", "account"},
    "Manager": {"dashboard", "tasks", "clients", "calendar", "ai", "team", "billing", "documents", "account"},
    "Staff": {"dashboard", "tasks", "clients", "calendar", "ai", "documents", "account"},
}

DEFAULT_ADMIN = ("admin", "admin@123")


def hash_password(pw: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), ITERATIONS).hex()
    return f"pbkdf2${ITERATIONS}${salt}${h}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        _, iters, salt, h = stored.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), int(iters)).hex()
        return hmac.compare_digest(calc, h)
    except (ValueError, AttributeError):
        return False


def ensure_admin():
    """First run: create a Partner login admin / admin@123 that must be changed on first login."""
    if db.scalar("SELECT COUNT(*) FROM users") == 0:
        create_user("Administrator", DEFAULT_ADMIN[0], DEFAULT_ADMIN[1], "Partner", must_change=True)


def create_user(name, username, password, role, email="", must_change=False):
    return db.insert(
        "INSERT INTO users(name,username,password_hash,role,email,must_change,created_on) "
        "VALUES (:n,:u,:p,:r,:e,:m,:c) RETURNING id",
        n=name.strip(), u=username.strip().lower(), p=hash_password(password), r=role, e=email,
        m=int(must_change), c=db.now())


def authenticate(username: str, password: str):
    u = db.one("SELECT * FROM users WHERE username=:u AND active=1", u=(username or "").strip().lower())
    if u and verify_password(password, u["password_hash"]):
        return u
    return None


def set_password(user_id: int, new_pw: str, must_change=False):
    db.execute("UPDATE users SET password_hash=:p, must_change=:m WHERE id=:i",
               p=hash_password(new_pw), m=int(must_change), i=user_id)


def password_problem(pw: str):
    if len(pw) < 8:
        return "Use at least 8 characters."
    if pw.isalpha() or pw.isdigit():
        return "Mix letters with numbers or symbols."
    return None


def can(user: dict, page: str) -> bool:
    return page in ACCESS.get(user["role"], set())


def sees_all_work(user: dict) -> bool:
    return user["role"] in ("Partner", "Manager")
