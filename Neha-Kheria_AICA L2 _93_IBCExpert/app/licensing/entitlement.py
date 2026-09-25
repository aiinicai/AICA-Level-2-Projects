"""Canonical signed offline licence entitlement and activation credentials."""
from __future__ import annotations

import base64
import json
import zlib
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from app.core.errors import LicenceError
from app.core.time import from_utc_iso
from app.licensing.device import normalize_request_code
from app.security import ed25519

ACTIVATION_PREFIX = "IBC1."
SIGNATURE_PREFIX = "SIG1."
LICENCE_TYPES = {
    "OWNER_DEVELOPER", "INDIVIDUAL", "PROFESSIONAL", "ANNUAL_SUBSCRIPTION",
    "PERPETUAL", "ORGANISATION", "ENTERPRISE",
}
ALL_FEATURES = {
    "client_management", "legal_database", "ocr", "advanced_search",
    "semantic_search", "recommendation_engine", "form_generation",
    "dashboard_analytics", "integrations", "amendment_downloader",
    "accounting_integration", "plugins", "multi_user",
}


def _b64e(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64d(value: str) -> bytes:
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        if _b64e(decoded) != value:
            raise ValueError("non-canonical base64 encoding")
        return decoded
    except Exception as exc:
        raise LicenceError("Activation credential uses invalid encoding.") from exc


def canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


@dataclass(frozen=True)
class Entitlement:
    protocol: int
    licence_id: str
    licence_type: str
    customer_name: str
    organisation: str | None
    email_reference: str | None
    issued_at: str
    starts_at: str
    expires_at: str | None
    device_request_code: str | None
    device_allowance: int
    features: tuple[str, ...]
    notes: str | None = None

    def validate_structure(self) -> None:
        if self.protocol != 1:
            raise LicenceError("Licence protocol is not supported by this application version.")
        if self.licence_type not in LICENCE_TYPES:
            raise LicenceError("Licence type is not recognized.")
        if not self.licence_id or len(self.licence_id) > 100:
            raise LicenceError("Licence ID is invalid.")
        if not self.customer_name.strip():
            raise LicenceError("Licence customer name is required.")
        if self.device_allowance < 1:
            raise LicenceError("Licence device allowance is invalid.")
        unknown = set(self.features) - ALL_FEATURES
        if unknown:
            raise LicenceError("Licence contains unknown feature entitlements.")
        issued = from_utc_iso(self.issued_at)
        starts = from_utc_iso(self.starts_at)
        if self.expires_at is not None and from_utc_iso(self.expires_at) <= starts:
            raise LicenceError("Licence expiry must be after its start date.")
        if self.device_request_code is not None:
            normalize_request_code(self.device_request_code)

    def payload(self) -> bytes:
        value = asdict(self)
        value["features"] = sorted(set(self.features))
        return canonical_json(value)

    @classmethod
    def from_payload(cls, payload: bytes) -> "Entitlement":
        try:
            raw = json.loads(payload.decode("utf-8"))
            expected = set(cls.__dataclass_fields__)
            if set(raw) != expected:
                raise ValueError("field mismatch")
            raw["features"] = tuple(raw["features"])
            result = cls(**raw)
            result.validate_structure()
            if result.payload() != payload:
                raise ValueError("payload is not canonical")
            return result
        except LicenceError:
            raise
        except Exception as exc:
            raise LicenceError("Signed licence payload is malformed.") from exc


def issue_credentials(entitlement: Entitlement, private_seed: bytes) -> tuple[str, str]:
    entitlement.validate_structure()
    payload = entitlement.payload()
    compressed = zlib.compress(payload, level=9)
    signature = ed25519.sign(private_seed, payload)
    return ACTIVATION_PREFIX + _b64e(compressed), SIGNATURE_PREFIX + _b64e(signature)


def verify_credentials(
    activation_id: str,
    activation_code: str,
    public_key: bytes,
    expected_request_code: str,
    now: datetime,
) -> Entitlement:
    if not activation_id.startswith(ACTIVATION_PREFIX) or not activation_code.startswith(SIGNATURE_PREFIX):
        raise LicenceError("Activation ID or activation code format is invalid.")
    encoded_payload = activation_id[len(ACTIVATION_PREFIX):]
    if len(encoded_payload) > 16384:
        raise LicenceError("Activation ID is unreasonably large.")
    try:
        compressed = _b64d(encoded_payload)
        decompressor = zlib.decompressobj()
        payload = decompressor.decompress(compressed, 65537)
        if len(payload) > 65536 or decompressor.unconsumed_tail:
            raise ValueError("payload too large")
        payload += decompressor.flush()
        if len(payload) > 65536 or not decompressor.eof or decompressor.unused_data:
            raise ValueError("invalid compressed payload")
    except Exception as exc:
        raise LicenceError("Activation ID is damaged or invalid.") from exc
    signature = _b64d(activation_code[len(SIGNATURE_PREFIX):])
    if not ed25519.verify(public_key, payload, signature):
        raise LicenceError("Activation signature is invalid. The licence was not issued by the owner.")
    entitlement = Entitlement.from_payload(payload)
    request = normalize_request_code(expected_request_code)
    if entitlement.device_request_code is not None and normalize_request_code(entitlement.device_request_code) != request:
        raise LicenceError("This activation was issued for a different installation.")
    now_utc = now.astimezone(from_utc_iso(entitlement.starts_at).tzinfo)
    if now_utc < from_utc_iso(entitlement.starts_at):
        raise LicenceError("This licence is not active yet.")
    if entitlement.expires_at and now_utc >= from_utc_iso(entitlement.expires_at):
        raise LicenceError("This licence has expired.")
    return entitlement
