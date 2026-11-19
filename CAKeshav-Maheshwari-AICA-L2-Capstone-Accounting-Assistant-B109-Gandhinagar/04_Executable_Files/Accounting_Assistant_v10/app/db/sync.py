"""Outbox sync between the local SQLite copy and the LAN PostgreSQL master.

push(): every pending outbox row is upserted to the master; newer updated_at wins.
pull(): rows changed on the master since the last pull are copied down; newer wins.
Both sides keep the older version in audit_log when a conflict is overwritten.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from .models import SYNCED_MODELS, AuditLog, Outbox, SyncState, utcnow

_BY_TABLE = {m.__tablename__: m for m in SYNCED_MODELS}
_EPOCH = datetime(2000, 1, 1)


@dataclass
class SyncResult:
    pushed: int = 0
    pulled: int = 0
    conflicts: int = 0


def _as_dict(obj) -> dict:
    return {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}


def _jsonable(d: dict) -> dict:
    return {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in d.items()}


def _copy_into(target_session: Session, model, src_obj, actor: str) -> tuple[bool, bool]:
    """Upsert src_obj into target_session. Returns (written, conflict)."""
    data = _as_dict(src_obj)
    existing = target_session.get(model, data["id"])
    if existing is None:
        target_session.add(model(**data))
        return True, False
    if existing.updated_at and data["updated_at"] and existing.updated_at > data["updated_at"]:
        return False, False                         # target is newer: keep it
    conflict = existing.updated_by != data["updated_by"] and existing.updated_at != data["updated_at"]
    if conflict and model is not AuditLog:
        target_session.add(AuditLog(company_id=data.get("company_id"), action="sync_overwrite",
                                    entity=model.__tablename__, entity_id=data["id"],
                                    before=_jsonable(_as_dict(existing)), after=_jsonable(data),
                                    updated_by=actor))
    for k, v in data.items():
        setattr(existing, k, v)
    return True, conflict


def push(local: Session, remote: Session, actor: str) -> SyncResult:
    res = SyncResult()
    remote.info["syncing"] = True
    pending = local.scalars(select(Outbox).where(Outbox.pushed_at.is_(None)).order_by(Outbox.id)).all()
    seen: set[tuple[str, str]] = set()
    for ob in pending:
        key = (ob.table, ob.row_id)
        if key not in seen:
            seen.add(key)
            model = _BY_TABLE[ob.table]
            obj = local.get(model, ob.row_id)
            if obj is not None:
                written, conflict = _copy_into(remote, model, obj, actor)
                res.pushed += int(written)
                res.conflicts += int(conflict)
        ob.pushed_at = utcnow()
    remote.commit()
    local.commit()
    return res


def pull(local: Session, remote: Session, actor: str) -> SyncResult:
    res = SyncResult()
    local.info["syncing"] = True
    try:
        for table, model in _BY_TABLE.items():
            state = local.get(SyncState, table)
            since = state.last_pull if state else _EPOCH
            started = utcnow()
            rows = remote.scalars(select(model).where(model.updated_at > since)).all()
            for r in rows:
                written, conflict = _copy_into(local, model, r, actor)
                res.pulled += int(written)
                res.conflicts += int(conflict)
            if state is None:
                local.add(SyncState(table=table, last_pull=started))
            else:
                state.last_pull = started
        local.commit()
    finally:
        local.info["syncing"] = False
    return res


def sync(local: Session, remote: Session, actor: str) -> SyncResult:
    a = push(local, remote, actor)
    b = pull(local, remote, actor)
    return SyncResult(a.pushed, b.pulled, a.conflicts + b.conflicts)
