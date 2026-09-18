"""Login endpoint. User creation is admin-only (see routers/users.py) -- there
is no public self-registration endpoint, matching an internal firm tool."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from webapi.database import get_db
from webapi.models import User
from webapi.schemas import LoginRequest, TokenResponse
from webapi.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.username == payload.username).first()
    # Constant-shape failure path: don't reveal whether the username exists.
    if user is None or not user.is_active or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect username or password.")
    token = create_access_token(subject=user.id, role=user.role.value)
    return TokenResponse(access_token=token, role=user.role)
