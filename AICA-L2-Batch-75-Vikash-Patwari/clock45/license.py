"""Entirely offline Ed25519 licence verification and trial policy."""

from __future__ import annotations

import base64
import json
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Mapping, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .store import Store


PUBLIC_KEY_B64 = "wIp4Cox0GD47Km1LttJHA2fjU74kL08Qv1LqjTB0aOY="
LICENCE_FILENAME = "clock45.licence.json"
TRIAL_DAYS = 30
TRIAL_LINE_LIMIT = 200


class LicenceError(ValueError):
    pass


@dataclass(frozen=True)
class LicenceStatus:
    mode: str
    firm_name: str
    seat_count: int
    expiry_date: Optional[str]
    days_remaining: int
    line_limit: Optional[int]
    can_analyse: bool
    message: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def canonical_payload(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        dict(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def verify_licence_document(
    document: Mapping[str, Any], *, public_key_b64: str = PUBLIC_KEY_B64
) -> dict[str, Any]:
    payload = document.get("licence")
    signature_text = document.get("signature")
    if not isinstance(payload, dict) or not isinstance(signature_text, str):
        raise LicenceError("The licence file does not have the required signed structure")
    try:
        signature = base64.b64decode(signature_text, validate=True)
        public_bytes = base64.b64decode(public_key_b64, validate=True)
        Ed25519PublicKey.from_public_bytes(public_bytes).verify(
            signature, canonical_payload(payload)
        )
    except (ValueError, InvalidSignature) as exc:
        raise LicenceError("The licence signature is not valid") from exc

    firm_name = str(payload.get("firm_name", "")).strip()
    try:
        seats = int(payload.get("seat_count", 0))
        expiry = date.fromisoformat(str(payload.get("expiry_date", "")))
    except (TypeError, ValueError) as exc:
        raise LicenceError("The licence has an invalid seat count or expiry date") from exc
    if not firm_name or seats < 1:
        raise LicenceError("The licence must name a firm and provide at least one seat")
    return {**payload, "firm_name": firm_name, "seat_count": seats, "expiry_date": expiry}


class LicenceManager:
    def __init__(self, store: Store) -> None:
        self.store = store

    @property
    def licence_path(self) -> Path:
        return self.store.folder / LICENCE_FILENAME

    def begin_trial(self, *, today: Optional[date] = None) -> None:
        if not self.store.get_setting("trial_started_on"):
            started = (today or date.today()).isoformat()
            self.store.set_setting("trial_started_on", started)
            self.store.set_setting("trial_last_seen_on", started)

    def install(self, source: str | Path) -> LicenceStatus:
        source_path = Path(source).expanduser().resolve()
        try:
            raw = source_path.read_bytes()
            document = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LicenceError(f"Could not read the selected licence file: {exc}") from exc
        verify_licence_document(document)
        self.licence_path.write_bytes(raw)
        return self.status()

    def status(self, *, today: Optional[date] = None) -> LicenceStatus:
        current = today or date.today()
        if self.licence_path.is_file():
            try:
                document = json.loads(self.licence_path.read_text(encoding="utf-8"))
                payload = verify_licence_document(document)
            except (OSError, json.JSONDecodeError, LicenceError) as exc:
                return LicenceStatus(
                    "INVALID_LICENCE", "", 0, None, 0, None, False,
                    f"The installed licence cannot be verified: {exc}",
                )
            expiry = payload["expiry_date"]
            days = (expiry - current).days
            if days < 0:
                return LicenceStatus(
                    "EXPIRED_LICENCE", payload["firm_name"], payload["seat_count"],
                    expiry.isoformat(), 0, None, False,
                    f"The licence for {payload['firm_name']} expired on {expiry:%d-%b-%Y}.",
                )
            return LicenceStatus(
                "LICENSED", payload["firm_name"], payload["seat_count"], expiry.isoformat(),
                days, None, True,
                f"Licensed to {payload['firm_name']} for {payload['seat_count']} seat(s).",
            )

        self.begin_trial(today=current)
        started = date.fromisoformat(self.store.get_setting("trial_started_on"))
        last_seen = date.fromisoformat(self.store.get_setting("trial_last_seen_on", started.isoformat()))
        if current < last_seen:
            return LicenceStatus(
                "TRIAL_CLOCK_ERROR", "Trial user", 1, None, 0, TRIAL_LINE_LIMIT, False,
                "The computer date is earlier than the last recorded use. Correct the Windows date to continue.",
            )
        self.store.set_setting("trial_last_seen_on", current.isoformat())
        expires = started + timedelta(days=TRIAL_DAYS)
        days = max(0, (expires - current).days)
        if current >= expires:
            return LicenceStatus(
                "EXPIRED_TRIAL", "Trial user", 1, expires.isoformat(), 0,
                TRIAL_LINE_LIMIT, False,
                "The 30-day trial has ended. Install a signed licence to run a new analysis.",
            )
        return LicenceStatus(
            "TRIAL", "Trial user", 1, expires.isoformat(), days, TRIAL_LINE_LIMIT, True,
            f"Trial mode: {days} day(s) remaining, limited to {TRIAL_LINE_LIMIT} purchase lines.",
        )

    def require_analysis(self, purchase_line_count: int) -> LicenceStatus:
        status = self.status()
        if not status.can_analyse:
            raise LicenceError(status.message)
        if status.line_limit is not None and purchase_line_count > status.line_limit:
            raise LicenceError(
                f"Trial mode accepts at most {status.line_limit} purchase lines. "
                f"This ledger contains {purchase_line_count}. Install a signed licence to continue."
            )
        return status
