import hashlib
import secrets
from typing import Optional, Dict, Any
import database as db

def hash_password(password: str, salt: Optional[str] = None) -> str:
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}${hashed}"

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        if "$" not in stored_hash:
            return False
        salt, hashed = stored_hash.split("$", 1)
        expected = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        return secrets.compare_digest(hashed, expected)
    except Exception:
        return False

def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    user = db.get_user_by_username(username.strip())
    if not user:
        return None
    if user.get("status") != "Active":
        return None
    if verify_password(password, user["password_hash"]):
        return user
    return None

def create_default_users():
    """Initializes default partner and team users if table is empty"""
    users = db.get_users()
    if not users:
        # Default Partner
        db.save_user(
            username="partner",
            password_hash=hash_password("admin123"),
            full_name="CA Gaurav Chaudhary (Partner)",
            role="Partner",
            email="gaurav@ca-firm.com",
            mobile="+91 98765 43210",
            status="Active"
        )
        # Default Team Members
        db.save_user(
            username="priya",
            password_hash=hash_password("priya123"),
            full_name="Priya Verma (Audit Senior)",
            role="Team Member",
            email="priya@ca-firm.com",
            mobile="+91 98111 22334",
            status="Active"
        )
        db.save_user(
            username="amit",
            password_hash=hash_password("amit123"),
            full_name="Amit Gupta (Audit Executive)",
            role="Team Member",
            email="amit@ca-firm.com",
            mobile="+91 98222 33445",
            status="Active"
        )
        db.save_user(
            username="sneha",
            password_hash=hash_password("sneha123"),
            full_name="Sneha Patel (Semi-Qualified)",
            role="Team Member",
            email="sneha@ca-firm.com",
            mobile="+91 98333 44556",
            status="Active"
        )
        print("Default users created successfully.")
    else:
        # Ensure partner name is updated if existing
        for u in users:
            if u["username"] == "partner" and u["full_name"] != "CA Gaurav Chaudhary (Partner)":
                db.save_user(
                    username="partner",
                    password_hash=u["password_hash"],
                    full_name="CA Gaurav Chaudhary (Partner)",
                    role="Partner",
                    email="gaurav@ca-firm.com",
                    mobile=u.get("mobile", "+91 98765 43210"),
                    status="Active"
                )

if __name__ == "__main__":
    db.init_db()
    create_default_users()
