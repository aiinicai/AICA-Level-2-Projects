"""Append-only audit trail. Every service that changes data calls ``audit()``."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def _jsonable(v):
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [_jsonable(x) for x in v]
    if isinstance(v, Decimal):
        return f"{v:.3f}" if v == v.quantize(Decimal("0.001")) else str(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, Enum):
        return v.value
    return v


def audit(db: Session, action: str, entity: str = "", key: str = "", before: dict | None = None,
          after: dict | None = None, user: User | None = None, user_id: int | None = None, ip: str = "") -> None:
    if user is not None:
        user_id = user.id
    username = user.username if user is not None else (
        db.get(User, user_id).username if user_id and db.get(User, user_id) else "system")
    db.add(AuditLog(user_id=user_id, username=username, action=action, entity=entity, entity_key=str(key),
                    before=_jsonable(before) if before else None, after=_jsonable(after) if after else None,
                    ip=ip))
