"""Sign-in lockout.

Four e-mail addresses are printed in the README. Without a limit, the password
is the only thing between someone who has read it and the books — and they get
unlimited attempts at it, as fast as they can post.

Held in memory rather than in a table, deliberately. It needs no migration on
an installation that already has data, and a counter that resets when the
server restarts is not the weakness it first appears: an attacker on the far
side of the API has no way to restart it. What it does mean is that a lockout
does not survive a restart, which is written down here rather than discovered.

Counted per e-mail *and* per client address, but not at the same threshold.
Per address the limit is three times higher, so someone fumbling their own
password does not lock every account for that machine, while a host working
through the four addresses in the README still runs into a wall. On a shared
NAT the address counter is coarse — that is the trade for catching spraying at
all, and it is why the per-address limit is the loose one.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from app.config import settings


@dataclass
class _Attempts:
    count: int = 0
    first_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    locked_until: datetime | None = None


_lock = threading.Lock()
_state: dict[str, _Attempts] = {}

# A window over which failures accumulate. Five wrong passwords spread over a
# working day is a person with a bad memory; five in two minutes is not.
WINDOW = timedelta(minutes=15)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# (key, how many failures it tolerates)
def _keys(email: str, client: str | None) -> list[tuple[str, int]]:
    per_user = settings.LOGIN_MAX_ATTEMPTS
    out = [(f"user:{email.lower().strip()}", per_user)]
    if client:
        out.append((f"host:{client}", per_user * 3))
    return out


def locked_for(email: str, client: str | None = None) -> int:
    """Seconds remaining on a lockout, or 0 when not locked."""
    now = _now()
    worst = 0
    with _lock:
        for k, _limit in _keys(email, client):
            rec = _state.get(k)
            if rec and rec.locked_until and rec.locked_until > now:
                worst = max(worst, int((rec.locked_until - now).total_seconds()))
    return worst


def record_failure(email: str, client: str | None = None) -> int:
    """Count one failed attempt. Returns seconds locked, or 0."""
    now = _now()
    worst = 0
    with _lock:
        for k, limit in _keys(email, client):
            rec = _state.get(k)
            if rec is None or now - rec.first_at > WINDOW:
                rec = _Attempts()
                _state[k] = rec
            rec.count += 1
            if rec.count >= limit:
                rec.locked_until = now + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
                rec.count = 0
                rec.first_at = now
            if rec.locked_until and rec.locked_until > now:
                worst = max(worst, int((rec.locked_until - now).total_seconds()))
    return worst


def record_success(email: str, client: str | None = None) -> None:
    with _lock:
        for k, _limit in _keys(email, client):
            _state.pop(k, None)


def reset() -> None:
    """For tests."""
    with _lock:
        _state.clear()
