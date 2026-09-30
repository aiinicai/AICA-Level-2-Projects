"""Append-only audit trail (spec section 26)."""
from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.orm import Session

from ..db.models import AuditLog


def _s(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        return json.dumps(v, default=str)[:4000]
    if isinstance(v, (date, datetime, Decimal)):
        return str(v)
    return str(v)[:4000]


def log(db: Session, user, action: str, object_type: str, object_id: Any = None, label: str = "", field: str | None = None,
        old: Any = None, new: Any = None, reason: str | None = None, document_id: int | None = None,
        approval_status: str | None = None):
    db.add(AuditLog(user_id=getattr(user, "id", None), username=getattr(user, "username", "system"), action=action,
                    object_type=object_type, object_id=None if object_id is None else str(object_id), object_label=label,
                    field=field, old_value=_s(old), new_value=_s(new), reason=reason, document_id=document_id,
                    approval_status=approval_status))


def log_changes(db: Session, user, obj, changes: dict, object_type: str, label: str, reason: str | None = None,
                approval_status: str | None = None) -> int:
    """Apply field changes to an ORM object and write one audit row per changed field."""
    n = 0
    for field, new in changes.items():
        if not hasattr(obj, field):
            continue
        old = getattr(obj, field)
        if _s(old) == _s(new):
            continue
        setattr(obj, field, new)
        log(db, user, "UPDATE", object_type, getattr(obj, "id", None), label, field, old, new, reason,
            approval_status=approval_status)
        n += 1
    return n
