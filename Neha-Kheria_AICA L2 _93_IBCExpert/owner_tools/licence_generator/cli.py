"""Owner-only command-line licence generator.

Run from the source tree:
  python -m owner_tools.licence_generator.cli generate-key --key-dir OWNER_KEY_DIR
  python -m owner_tools.licence_generator.cli issue --key-dir OWNER_KEY_DIR ...
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.time import to_utc_iso
from app.licensing.entitlement import ALL_FEATURES, Entitlement, LICENCE_TYPES, issue_credentials
from app.licensing.device import normalize_request_code
from app.security import aead, ed25519
from app.security.kdf import derive_password_key, new_salt

PRIVATE_MAGIC = b"IBC-OWNER-KEY-v1\x00"


def _write_exclusive(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def generate_key(key_dir: Path) -> None:
    private_path = key_dir / "owner_private_key.ibckey"
    public_path = key_dir / "licence_public_key.hex"
    if private_path.exists() or public_path.exists():
        raise SystemExit("Refusing to overwrite an existing owner key. Back it up securely.")
    password = getpass.getpass("Create owner-key password (minimum 12 characters): ")
    confirm = getpass.getpass("Confirm owner-key password: ")
    if password != confirm:
        raise SystemExit("Passwords do not match.")
    salt = new_salt()
    key = derive_password_key(password, salt)
    seed = ed25519.generate_signing_key()
    payload = salt + aead.encrypt(key, PRIVATE_MAGIC + seed, b"IBC-OWNER-PRIVATE-KEY/v1")
    _write_exclusive(private_path, payload)
    _write_exclusive(public_path, (ed25519.publickey_from_seed(seed).hex() + "\n").encode("ascii"))
    print(f"Owner signing key created. Back up: {private_path}")
    print(f"Public key for customer build: {public_path}")


def load_seed(key_dir: Path) -> bytes:
    payload = (key_dir / "owner_private_key.ibckey").read_bytes()
    if len(payload) < 16 + 12 + 16:
        raise SystemExit("Owner private-key file is damaged.")
    password = getpass.getpass("Owner-key password: ")
    key = derive_password_key(password, payload[:16])
    try:
        clear = aead.decrypt(key, payload[16:], b"IBC-OWNER-PRIVATE-KEY/v1")
    except Exception:
        raise SystemExit("Owner-key password is incorrect or the key file was altered.")
    if not clear.startswith(PRIVATE_MAGIC) or len(clear) != len(PRIVATE_MAGIC) + 32:
        raise SystemExit("Owner private-key file is invalid.")
    return clear[len(PRIVATE_MAGIC):]


def issue(args) -> None:
    request = normalize_request_code(args.request_code) if args.request_code else None
    features = tuple(sorted(set(args.feature or [])))
    unknown = set(features) - ALL_FEATURES
    if unknown:
        raise SystemExit(f"Unknown features: {', '.join(sorted(unknown))}")
    now = datetime.now(timezone.utc)
    entitlement = Entitlement(
        protocol=1,
        licence_id=args.licence_id or str(uuid.uuid4()),
        licence_type=args.licence_type,
        customer_name=args.customer_name,
        organisation=args.organisation,
        email_reference=args.email,
        issued_at=to_utc_iso(now),
        starts_at=args.starts_at or to_utc_iso(now),
        expires_at=args.expires_at,
        device_request_code=request,
        device_allowance=args.devices,
        features=features,
        notes=args.notes,
    )
    activation_id, activation_code = issue_credentials(entitlement, load_seed(args.key_dir))
    result = {
        "licence": json.loads(entitlement.payload()),
        "activation_id": activation_id,
        "activation_code": activation_code,
    }
    output = args.output or Path(f"licence-{entitlement.licence_id}.json")
    _write_exclusive(output, json.dumps(result, indent=2, sort_keys=True).encode("utf-8"))
    print(f"Licence issued: {output}")
    print("ACTIVATION ID:")
    print(activation_id)
    print("ACTIVATION PASSWORD / CODE:")
    print(activation_code)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="IBC Expert owner-only licence generator")
    sub = root.add_subparsers(dest="command", required=True)
    key = sub.add_parser("generate-key", help="Create owner signing key pair once")
    key.add_argument("--key-dir", type=Path, required=True)
    key.set_defaults(func=lambda args: generate_key(args.key_dir))
    create = sub.add_parser("issue", help="Issue a signed offline activation")
    create.add_argument("--key-dir", type=Path, required=True)
    create.add_argument("--customer-name", required=True)
    create.add_argument("--organisation")
    create.add_argument("--email")
    create.add_argument("--licence-id")
    create.add_argument("--licence-type", choices=sorted(LICENCE_TYPES), required=True)
    create.add_argument("--starts-at", help="UTC ISO date/time, e.g. 2026-09-22T00:00:00Z")
    create.add_argument("--expires-at", help="UTC ISO date/time; omit for perpetual")
    create.add_argument("--devices", type=int, default=1)
    create.add_argument("--request-code", help="Customer DEVICE / INSTALLATION REQUEST CODE")
    create.add_argument("--feature", action="append", choices=sorted(ALL_FEATURES))
    create.add_argument("--notes")
    create.add_argument("--output", type=Path)
    create.set_defaults(func=issue)
    return root


def main() -> None:
    args = parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
