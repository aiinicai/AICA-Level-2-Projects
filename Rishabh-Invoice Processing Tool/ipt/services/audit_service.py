"""Audit trail: append-only record of who did what."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ipt.core.context import CurrentUser
from ipt.db.base import Database
from ipt.db.models import AuditLog

_SECRET_KEYS = {"password", "password_hash", "api_key", "token", "secret"}


def _clean(data: dict[str, Any] | None) -> str:
    if not data:
        return ""
    safe = {k: ("***" if k in _SECRET_KEYS else v) for k, v in data.items()}
    return json.dumps(safe, default=str, ensure_ascii=False)


def record(session: Session, user: CurrentUser | None, action: str, entity: str,
           entity_id: Any = "", before: dict | None = None, after: dict | None = None,
           remark: str = "", company_id: int | None = None) -> None:
    session.add(AuditLog(
        user_id=user.id if user else None,
        username=user.username if user else "system",
        company_id=company_id,
        action=action, entity=entity, entity_id=str(entity_id),
        before_json=_clean(before), after_json=_clean(after), remark=remark,
    ))


class AuditService:
    def __init__(self, db: Database):
        self.db = db

    def recent(self, limit: int = 500, text: str = "") -> list[AuditLog]:
        with self.db.session() as s:
            q = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
            rows = list(s.scalars(q))
        if text:
            t = text.lower()
            rows = [r for r in rows if t in f"{r.username} {r.action} {r.entity} {r.entity_id} {r.remark}".lower()]
        return rows
