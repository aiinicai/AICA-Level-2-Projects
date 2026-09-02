import json
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from app.models.user import User

def log_action(
    db: Session,
    action: str,
    entity_name: str,
    entity_id: Optional[Any] = None,
    old_value: Optional[Any] = None,
    new_value: Optional[Any] = None,
    user: Optional[User] = None,
    ip_address: Optional[str] = None
):
    old_str = json.dumps(old_value, default=str) if old_value is not None else None
    new_str = json.dumps(new_value, default=str) if new_value is not None else None

    audit = AuditLog(
        user_id=user.id if user else None,
        username=user.full_name if user else "SYSTEM",
        action=action,
        entity_name=entity_name,
        entity_id=str(entity_id) if entity_id is not None else None,
        old_value=old_str,
        new_value=new_str,
        ip_address=ip_address
    )
    db.add(audit)
    db.commit()
    return audit
