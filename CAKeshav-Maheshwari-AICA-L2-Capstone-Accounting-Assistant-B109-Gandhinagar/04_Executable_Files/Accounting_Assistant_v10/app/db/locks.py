"""One poster per company. The lock row lives on the master DB when reachable,
otherwise on the local DB (offline work is single-PC by definition)."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from .models import CompanyLock, utcnow


class LockHeld(Exception):
    def __init__(self, holder: str, since):
        super().__init__(f"Company is being posted by {holder} (last seen {since:%H:%M:%S} UTC)")
        self.holder = holder


def acquire(session: Session, company_id: str, holder: str, stale_seconds: int = 300) -> CompanyLock:
    now = utcnow()
    lock = session.get(CompanyLock, company_id, with_for_update=True)
    if lock and lock.holder != holder and now - lock.heartbeat_at < timedelta(seconds=stale_seconds):
        session.rollback()
        raise LockHeld(lock.holder, lock.heartbeat_at)
    if lock is None:
        lock = CompanyLock(company_id=company_id, holder=holder, heartbeat_at=now)
        session.add(lock)
    else:
        lock.holder, lock.heartbeat_at = holder, now
    session.commit()
    return lock


def heartbeat(session: Session, company_id: str, holder: str) -> bool:
    lock = session.get(CompanyLock, company_id)
    if not lock or lock.holder != holder:
        return False
    lock.heartbeat_at = utcnow()
    session.commit()
    return True


def release(session: Session, company_id: str, holder: str) -> None:
    lock = session.get(CompanyLock, company_id)
    if lock and lock.holder == holder:
        session.delete(lock)
        session.commit()
