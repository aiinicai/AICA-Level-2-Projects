"""UTC time abstraction used by workflows, trials and deterministic tests."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

UTC = timezone.utc


def utc_now() -> datetime:
    return datetime.now(UTC)


def to_utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("naive datetime is not permitted")
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def from_utc_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("stored datetime must contain a UTC offset")
    return parsed.astimezone(UTC)


class Clock(Protocol):
    def now(self) -> datetime: ...


@dataclass(frozen=True)
class SystemClock:
    def now(self) -> datetime:
        return utc_now()


@dataclass
class FixedClock:
    value: datetime

    def now(self) -> datetime:
        if self.value.tzinfo is None:
            raise ValueError("FixedClock requires timezone-aware datetime")
        return self.value.astimezone(UTC)
