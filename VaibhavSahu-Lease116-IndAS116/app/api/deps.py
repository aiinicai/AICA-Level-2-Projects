from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..db.base import get_db
from ..db.models import Lease, User
from ..services.security import COOKIE_NAME, has_perm, read_token


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:]
    uid = read_token(token) if token else None
    if uid is None:
        raise HTTPException(401, "Not signed in")
    user = db.get(User, uid)
    if user is None or not user.active:
        raise HTTPException(401, "User inactive")
    return user


def require(perm: str):
    def dep(user: User = Depends(current_user)) -> User:
        if not has_perm(user.role.code, perm):
            raise HTTPException(403, f"Permission '{perm}' required (your role: {user.role.name})")
        return user
    return dep


def get_lease(lease_id: int, db: Session, user: User) -> Lease:
    lease = db.get(Lease, lease_id)
    if lease is None:
        raise HTTPException(404, "Lease not found")
    if not user.all_entities and user.role.code != "ADMIN":
        from sqlalchemy import select
        from ..db.models import UserEntityAccess
        ok = db.scalar(select(UserEntityAccess.id).where(UserEntityAccess.user_id == user.id,
                                                         UserEntityAccess.entity_id == lease.entity_id))
        if not ok:
            raise HTTPException(403, "No access to this entity")
    return lease
