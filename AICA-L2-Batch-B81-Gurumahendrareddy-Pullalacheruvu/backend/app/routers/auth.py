"""Authentication — the login gate."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core import lockout
from app.core.security import create_access_token, get_current_user, verify_password
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    phone: str | None = None
    last_login: datetime | None = None

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


def _wait_message(seconds: int) -> str:
    minutes = max(1, round(seconds / 60))
    return (f"Too many failed sign-in attempts. Try again in "
            f"{minutes} minute{'s' if minutes != 1 else ''}.")


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client = request.client.host if request.client else None
    email = payload.email.lower()

    # Checked before the password is even looked at, so a locked account costs
    # an attacker a round trip and tells them nothing.
    held = lockout.locked_for(email, client)
    if held:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, _wait_message(held))

    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        # The same sentence whether the address exists or not — otherwise the
        # error itself confirms which addresses are real.
        held = lockout.record_failure(email, client)
        if held:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, _wait_message(held))
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "Email or password is incorrect.")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account is disabled.")

    lockout.record_success(email, client)
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return LoginResponse(access_token=create_access_token(user), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)
