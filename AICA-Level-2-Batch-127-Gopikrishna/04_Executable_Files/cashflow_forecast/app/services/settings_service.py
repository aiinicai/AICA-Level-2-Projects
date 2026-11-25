"""Business settings stored in the ``app_setting`` table, validated through BusinessDefaults."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import BusinessDefaults, get_business_defaults
from app.models import AppSetting, Role

BUSINESS_KEYS = tuple(BusinessDefaults.model_fields)


def get_business_settings(db: Session) -> BusinessDefaults:
    stored = {s.key: s.value for s in db.scalars(select(AppSetting)) if s.key in BUSINESS_KEYS}
    merged = {**get_business_defaults().model_dump(), **stored}
    return BusinessDefaults.model_validate(merged)


def update_business_settings(db: Session, changes: dict, user_id: int | None = None) -> BusinessDefaults:
    """Validate the full merged set first, so an invalid value never reaches the table."""
    unknown = set(changes) - set(BUSINESS_KEYS)
    if unknown:
        raise KeyError(f"unknown setting(s): {sorted(unknown)}")
    current = get_business_settings(db).model_dump()
    validated = BusinessDefaults.model_validate({**current, **changes})
    for key in changes:
        row = db.get(AppSetting, key)
        value = getattr(validated, key)
        if row is None:
            db.add(AppSetting(key=key, value=value, updated_by_id=user_id))
        else:
            row.value, row.updated_by_id = value, user_id
    db.flush()
    return validated


def active_roles(db: Session) -> list[Role]:
    """Approver exists in the data model but is offered only when the setting is on."""
    roles = [Role.ADMIN, Role.PREPARER, Role.VIEWER]
    if get_business_settings(db).approver_enabled:
        roles.append(Role.APPROVER)
    return roles
