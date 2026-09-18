"""User management -- Administrator only. No public self-registration."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from webapi.database import get_db
from webapi.deps import get_current_user, require_roles
from webapi.models import User, UserRole
from webapi.schemas import UserCreate, UserOut
from webapi.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db), _admin: User = Depends(require_roles(UserRole.ADMIN))) -> User:
    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A user with that username or email already exists.") from exc
    db.refresh(user)
    return user


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _admin: User = Depends(require_roles(UserRole.ADMIN))) -> list[User]:
    return db.query(User).order_by(User.created_at.desc()).all()


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(user_id: str, db: Session = Depends(get_db), _admin: User = Depends(require_roles(UserRole.ADMIN))) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user
