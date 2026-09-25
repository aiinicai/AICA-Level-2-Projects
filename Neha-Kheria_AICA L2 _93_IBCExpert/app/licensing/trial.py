"""30-day offline trial with redundant authenticated state and rollback detection."""
from __future__ import annotations

import json
import math
import secrets
import uuid
from dataclasses import asdict, dataclass
from datetime import timedelta
from pathlib import Path

from app.core.errors import ClockRollbackError, IntegrityError
from app.core.time import Clock, SystemClock, from_utc_iso, to_utc_iso
from app.licensing.device import device_request_code
from app.security import aead
from app.security.kdf import derive_subkey
from app.security.secure_store import RedundantSecureStore

STATE_CONTEXT = b"IBC-EXPERT/TRIAL-STATE/v1"
SECRET_CONTEXT = b"IBC-EXPERT/INSTALLATION-SECRET/v1"


@dataclass(frozen=True)
class TrialState:
    protocol: int
    installation_id: str
    started_at: str
    expires_at: str
    highest_seen_at: str
    last_checked_at: str
    status: str

    def validate(self) -> None:
        if self.protocol != 1 or self.status not in {"TRIAL", "EXPIRED", "CLOCK_ANOMALY", "LICENSED"}:
            raise IntegrityError("Trial state format is not supported.")
        uuid.UUID(self.installation_id)
        started = from_utc_iso(self.started_at)
        expires = from_utc_iso(self.expires_at)
        highest = from_utc_iso(self.highest_seen_at)
        if expires != started + timedelta(days=30):
            raise IntegrityError("Trial expiry record has been altered.")
        if highest < started:
            raise IntegrityError("Trial trusted timestamp is invalid.")


@dataclass(frozen=True)
class TrialStatus:
    mode: str
    days_remaining: int
    expires_at: str
    request_code: str
    normal_use_allowed: bool
    warning: str | None


class TrialService:
    def __init__(
        self,
        primary_state: Path,
        secondary_state: Path,
        primary_secret: Path,
        secondary_secret: Path,
        *,
        clock: Clock | None = None,
        rollback_tolerance_minutes: int = 10,
    ):
        self.state_store = RedundantSecureStore(primary_state, secondary_state, "TrialState")
        self.secret_store = RedundantSecureStore(primary_secret, secondary_secret, "InstallationSecret")
        self.clock = clock or SystemClock()
        self.rollback_tolerance = timedelta(minutes=rollback_tolerance_minutes)

    def _secret(self, create: bool) -> bytes:
        candidates = self.secret_store.read_candidates()
        if candidates:
            first = candidates[0]
            if len(first) != 32 or any(candidate != first for candidate in candidates):
                raise IntegrityError("Installation security records do not agree.")
            self.secret_store.heal(first)
            return first
        if self.state_store.raw_copies():
            raise IntegrityError("Trial state exists but its protected installation key is missing.")
        if not create:
            raise IntegrityError("Installation security state is missing.")
        secret = secrets.token_bytes(32)
        self.secret_store.write_all(secret)
        return secret

    def _encode(self, state: TrialState, secret: bytes) -> bytes:
        state.validate()
        clear = json.dumps(asdict(state), separators=(",", ":"), sort_keys=True).encode("utf-8")
        key = derive_subkey(secret, "trial-state", state.installation_id)
        return aead.seal_container(key, clear, STATE_CONTEXT)

    def _decode_any(self, container: bytes, secret: bytes) -> TrialState:
        # installation_id is inside ciphertext, so test a small metadata header is
        # avoided by deriving a stable state key first; device binding remains in data.
        key = derive_subkey(secret, "trial-state", "installation")
        clear = aead.open_container(key, container, STATE_CONTEXT)
        try:
            state = TrialState(**json.loads(clear.decode("utf-8")))
            state.validate()
            return state
        except Exception as exc:
            raise IntegrityError("Trial state is damaged or was modified.") from exc

    def _encode_stable(self, state: TrialState, secret: bytes) -> bytes:
        state.validate()
        clear = json.dumps(asdict(state), separators=(",", ":"), sort_keys=True).encode("utf-8")
        key = derive_subkey(secret, "trial-state", "installation")
        return aead.seal_container(key, clear, STATE_CONTEXT)

    def load_or_start(self) -> TrialState:
        now = self.clock.now()
        secret = self._secret(create=True)
        candidates = self.state_store.read_candidates()
        if not candidates:
            started = now
            state = TrialState(
                protocol=1,
                installation_id=str(uuid.uuid4()),
                started_at=to_utc_iso(started),
                expires_at=to_utc_iso(started + timedelta(days=30)),
                highest_seen_at=to_utc_iso(started),
                last_checked_at=to_utc_iso(started),
                status="TRIAL",
            )
            self.state_store.write_all(self._encode_stable(state, secret))
            return state
        states = [self._decode_any(value, secret) for value in candidates]
        installation_ids = {state.installation_id for state in states}
        starts = {state.started_at for state in states}
        expires = {state.expires_at for state in states}
        if len(installation_ids) != 1 or len(starts) != 1 or len(expires) != 1:
            raise IntegrityError("Redundant trial records do not agree.")
        # Select the highest trusted timestamp, preventing an older copied record
        # from rolling the trial backward.
        state = max(states, key=lambda item: from_utc_iso(item.highest_seen_at))
        self.state_store.heal(self._encode_stable(state, secret))
        return state

    def check(self, licensed: bool = False) -> TrialStatus:
        state = self.load_or_start()
        now = self.clock.now()
        highest = from_utc_iso(state.highest_seen_at)
        expires = from_utc_iso(state.expires_at)
        if licensed:
            updated = TrialState(**{**asdict(state), "highest_seen_at": to_utc_iso(max(now, highest)), "last_checked_at": to_utc_iso(now), "status": "LICENSED"})
            self._save(updated)
            return TrialStatus("LICENSED", 0, state.expires_at, device_request_code(state.installation_id), True, None)
        if now + self.rollback_tolerance < highest:
            updated = TrialState(**{**asdict(state), "last_checked_at": to_utc_iso(now), "status": "CLOCK_ANOMALY"})
            self._save(updated)
            return TrialStatus("CLOCK_ANOMALY", 0, state.expires_at, device_request_code(state.installation_id), False, "The computer clock is earlier than the last trusted use. Correct the clock or activate a valid licence.")
        effective_now = max(now, highest)
        expired = effective_now >= expires
        remaining_seconds = max(0.0, (expires - effective_now).total_seconds())
        days = int(math.ceil(remaining_seconds / 86400.0))
        mode = "EXPIRED" if expired else "TRIAL"
        updated = TrialState(**{**asdict(state), "highest_seen_at": to_utc_iso(effective_now), "last_checked_at": to_utc_iso(now), "status": mode})
        self._save(updated)
        warning = self._warning(days, expired)
        return TrialStatus(mode, days, state.expires_at, device_request_code(state.installation_id), not expired, warning)

    def _save(self, state: TrialState) -> None:
        secret = self._secret(create=False)
        self.state_store.write_all(self._encode_stable(state, secret))

    @staticmethod
    def _warning(days: int, expired: bool) -> str | None:
        if expired:
            return "The 30-day trial has expired. Activation is required for normal use."
        if days == 0:
            return "Trial expires today."
        if days in {1, 3, 7, 15}:
            suffix = "day" if days == 1 else "days"
            return f"Trial — {days} {suffix} remaining."
        return None
