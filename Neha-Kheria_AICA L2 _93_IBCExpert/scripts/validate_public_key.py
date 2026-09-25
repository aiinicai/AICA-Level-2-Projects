"""Validate the public Ed25519 verification key supplied to a customer build."""
from __future__ import annotations

import argparse
import re
from pathlib import Path


class PublicKeyValidationError(ValueError):
    pass


def validate_public_key(path: Path) -> str:
    candidate = path.expanduser().resolve()
    if not candidate.is_file():
        raise PublicKeyValidationError(f"Public key file does not exist: {candidate}")
    if candidate.name.lower() != "licence_public_key.hex":
        raise PublicKeyValidationError("Public key file must be named licence_public_key.hex.")
    try:
        text = candidate.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError) as exc:
        raise PublicKeyValidationError("Public key file could not be read as ASCII text.") from exc
    if re.fullmatch(r"[0-9a-fA-F]{64}", text) is None:
        raise PublicKeyValidationError(
            "licence_public_key.hex must contain exactly 64 hexadecimal characters (32 bytes)."
        )
    return text.lower()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate IBC Expert customer public licence key")
    parser.add_argument("public_key", type=Path)
    args = parser.parse_args()
    try:
        fingerprint_source = validate_public_key(args.public_key)
    except PublicKeyValidationError as exc:
        parser.error(str(exc))
    # Do not echo private material. This file is a public verification key, so a short identifier is
    # safe and helps confirm the intended key was selected.
    import hashlib

    fingerprint = hashlib.sha256(bytes.fromhex(fingerprint_source)).hexdigest()[:16]
    print(f"Public licence verification key is valid. SHA-256 prefix: {fingerprint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
