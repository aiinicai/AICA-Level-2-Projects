"""
Password hashing, JWT session tokens, and the admin-approval email.

JWT_SECRET should be set as a real env var in production (Render). Falling
back to a generated one means sessions reset whenever the server restarts -
acceptable for this build, but worth fixing before anything long-lived
depends on it.
"""
import os
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

import jwt
import requests
from passlib.context import CryptContext

JWT_SECRET = os.getenv("JWT_SECRET") or secrets.token_hex(32)
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24 * 7

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "cashubhammishra@gmail.com")
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM = os.getenv("RESEND_FROM", "onboarding@resend.dev")
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "https://ca-practiceos-backend.onrender.com")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_session_token(user_id: str, tenant_id: str, role: str, is_tenant_admin: bool) -> str:
    payload = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "is_tenant_admin": is_tenant_admin,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_session_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def send_email(to_address: str, subject: str, body: str) -> bool:
    """Returns True if sent, False if email isn't configured or sending failed
    (callers should not crash the request just because email couldn't send -
    the signup/approval record is still created either way).

    Tries Resend first (HTTPS API - not blocked by cloud hosts' outbound
    firewall rules), then falls back to Gmail SMTP with a short timeout.
    Render (and most PaaS free tiers) block outbound SMTP ports 465/587 by
    default to prevent spam abuse - confirmed by testing: the raw SMTP path
    hung indefinitely in production even though the exact same code worked
    from a local machine. Resend avoids that entirely."""
    if RESEND_API_KEY:
        try:
            resp = requests.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
                json={"from": RESEND_FROM, "to": [to_address], "subject": subject, "text": body},
                timeout=10,
            )
            if resp.status_code < 300:
                return True
            print(f"[resend send failed] {resp.status_code}: {resp.text}")
        except Exception as exc:
            print(f"[resend send failed] {exc}")
        return False

    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print(f"[email not configured] Would have sent to {to_address}: {subject}")
        return False
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_address
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, [to_address], msg.as_string())
        return True
    except Exception as exc:
        print(f"[email send failed - likely SMTP ports blocked by host] {exc}")
        return False


def send_approval_request_email(applicant_name: str, applicant_email: str, firm_name: str, approval_token: str):
    approve_url = f"{BACKEND_PUBLIC_URL}/api/auth/approve?token={approval_token}"
    reject_url = f"{BACKEND_PUBLIC_URL}/api/auth/reject?token={approval_token}"
    body = f"""A new firm has requested access to CA PracticeOS Compliance.

Name: {applicant_name}
Email: {applicant_email}
Firm: {firm_name}

Approve: {approve_url}
Reject: {reject_url}
"""
    send_email(ADMIN_EMAIL, f"CA PracticeOS: Access request from {firm_name}", body)
