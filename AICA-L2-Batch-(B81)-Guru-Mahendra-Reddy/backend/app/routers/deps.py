"""Shared FastAPI dependencies."""
from __future__ import annotations

from datetime import date

from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models import ActivityLog, Entity, User
from app.services.common import Ctx, build_ctx


def get_ctx(entity_id: int | None = Query(None, description="Entity to view. Defaults to the first."),
            as_on: date | None = Query(None, description="As-on date. Defaults to books-closed date."),
            db: Session = Depends(get_db),
            user: User = Depends(get_current_user)) -> Ctx:
    if entity_id is None:
        first = db.query(Entity).order_by(Entity.sort_order, Entity.id).first()
        if not first:
            raise HTTPException(404, "No entities configured. Run seed_db.py.")
        entity_id = first.id
    try:
        ctx = build_ctx(db, entity_id, as_on=as_on)
    except ValueError as e:
        raise HTTPException(404, str(e))
    ctx.user = user           # type: ignore[attr-defined]
    return ctx


def log(ctx: Ctx, user: User, action: str, object_type: str, summary: str,
        object_id: str | None = None, before: str | None = None,
        after: str | None = None) -> None:
    """Every write goes through here — SPEC 12D wants an activity log that
    actually answers 'who changed this threshold?'"""
    ctx.db.add(ActivityLog(entity_id=ctx.entity.id, user_id=user.id, user_name=user.name,
                           action=action, object_type=object_type, object_id=object_id,
                           summary=summary, before_value=before, after_value=after))
