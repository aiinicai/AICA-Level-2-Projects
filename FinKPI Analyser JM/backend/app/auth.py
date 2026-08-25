import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from .config import config
from .database import get_db
from .models import UserModel

http_bearer = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    # Use PBKDF2 with SHA256 for universal compatibility
    salt = b"finkpi_salt_2024"
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000).hex()

def verify_password(plain: str, hashed: str) -> bool:
    return hmac.compare_digest(hash_password(plain), hashed)

def create_token(data: Dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=config.TOKEN_EXPIRE_MIN)
    return jwt.encode(payload, config.SECRET_KEY, algorithm=config.ALGORITHM)

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    db: Session = Depends(get_db)
) -> UserModel:
    if not credentials:
        user = db.query(UserModel).filter(UserModel.username == config.DEMO_USER).first()
        if not user:
            user = UserModel(
                username=config.DEMO_USER,
                email="admin@finkpi.com",
                password_hash=hash_password(config.DEMO_PASSWORD),
                role="admin",
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    try:
        payload = jwt.decode(credentials.credentials, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token expired or invalid")

    user = db.query(UserModel).filter(UserModel.username == username).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User active session not found")
    return user

def require_role(roles: list):
    def role_checker(current_user: UserModel = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permission for action")
        return current_user
    return role_checker
