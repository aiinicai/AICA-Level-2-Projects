"""One-time publisher key generator. Never distribute the private key."""

from __future__ import annotations

import argparse
import base64
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path, help="Private, access-controlled publisher folder")
    args = parser.parse_args()
    args.folder.mkdir(parents=True, exist_ok=True)
    private_path = args.folder / "clock45-ed25519-private.pem"
    public_path = args.folder / "clock45-ed25519-public.txt"
    if private_path.exists() or public_path.exists():
        raise SystemExit("Refusing to overwrite an existing licensing key")

    private_key = Ed25519PrivateKey.generate()
    private_path.write_bytes(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ))
    raw_public = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    public_path.write_text(base64.b64encode(raw_public).decode("ascii") + "\n", encoding="ascii")
    print(f"Private key: {private_path}")
    print(f"Public key:  {public_path}")
    print("Move the private key to encrypted offline storage before distributing the installer.")


if __name__ == "__main__":
    main()
