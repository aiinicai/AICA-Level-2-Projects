"""Timestamps written by SQLite's CURRENT_TIMESTAMP are UTC; show them in the PC's local time."""
from __future__ import annotations

from datetime import datetime, timezone


def local(dt: datetime | None) -> datetime | None:
    """Convert a naive UTC timestamp from the database to naive local time."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone().replace(tzinfo=None)


def fmt(dt: datetime | None, seconds: bool = False) -> str:
    d = local(dt)
    return d.strftime("%d-%m-%Y %H:%M:%S" if seconds else "%d-%m-%Y %H:%M") if d else ""
