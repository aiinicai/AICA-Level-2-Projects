"""P0 session boundary: a fresh session has zero carried-over conversation."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from amg.db import utc_now_iso


@dataclass(slots=True)
class Session:
    """Identity and gate state for one genuinely fresh assistant session."""

    session_id: str
    actor: str
    started_at: str
    # Phase 6's confirmation gate is the sole authorized writer of this flag;
    # governance code outside that gate may only read it.
    export_confirmed: bool = False

    # Deliberately absent: messages, transcript, or any other conversation
    # history. Retrieval is the only route by which prior-session information
    # can enter this fresh context, making continuity a persistence proof.


def new_session(actor: str = "demo_user") -> Session:
    """Create a session with a unique id and an unconfirmed export gate."""

    return Session(
        session_id=f"s-{uuid4().hex}",
        actor=actor,
        started_at=utc_now_iso(),
    )
