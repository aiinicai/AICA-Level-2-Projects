import bcrypt
from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session

from .database import get_db
from . import models


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def get_current_user(request: Request, db: Session = Depends(get_db)) -> models.User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.query(models.User).filter(models.User.id == user_id, models.User.is_active == True).first()  # noqa: E712
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def get_current_user_optional(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(models.User).filter(models.User.id == user_id, models.User.is_active == True).first()  # noqa: E712


def require_role(*allowed_roles):
    def checker(user: models.User = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker


def log_audit(db: Session, actor: models.User, action: str, detail: str = ""):
    entry = models.AuditLog(actor_id=actor.id if actor else None, action=action, detail=detail)
    db.add(entry)
    db.commit()
