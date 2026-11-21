import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from jose import jwt, JWTError
import bcrypt
from backend.app.core.config import settings

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

# Masking functions per Indian Privacy standards (DPDP)
def mask_pan(pan: Optional[str]) -> str:
    if not pan:
        return ""
    pan = pan.strip().upper()
    if len(pan) == 10:
        return f"{pan[:2]}*****{pan[-1]}"
    return pan

def mask_gstin(gstin: Optional[str]) -> str:
    if not gstin:
        return ""
    gstin = gstin.strip().upper()
    if len(gstin) == 15:
        return f"{gstin[:2]}********{gstin[-3:]}"
    return gstin

def mask_account_number(acc: Optional[str]) -> str:
    if not acc:
        return ""
    acc = str(acc).strip()
    if len(acc) > 4:
        return f"{'*' * (len(acc) - 4)}{acc[-4:]}"
    return acc

def sanitize_formula_injection(value: Any) -> Any:
    """
    Prevents spreadsheet formula injection (CSV/Excel DDE injection)
    where untrusted inputs begin with =, +, -, @, \t, or \r.
    """
    if isinstance(value, str):
        if value.startswith(("=", "+", "-", "@", "\t", "\r")):
            return f"'{value}"
    return value
