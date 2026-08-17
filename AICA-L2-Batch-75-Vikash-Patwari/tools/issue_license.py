"""Publisher-only command for issuing an offline signed licence file."""

from __future__ import annotations

import argparse
import base64
import json
from datetime import date
from pathlib import Path

from cryptography.hazmat.primitives import serialization

from clock45.license import canonical_payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Issue a signed 45-Day Clock licence")
    parser.add_argument("--private-key", required=True, type=Path)
    parser.add_argument("--firm", required=True)
    parser.add_argument("--seats", required=True, type=int)
    parser.add_argument("--expiry", required=True, help="YYYY-MM-DD")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    expiry = date.fromisoformat(args.expiry)
    if args.seats < 1 or not args.firm.strip():
        raise SystemExit("Firm name and at least one seat are required")
    private_key = serialization.load_pem_private_key(
        args.private_key.read_bytes(), password=None
    )
    payload = {
        "expiry_date": expiry.isoformat(),
        "firm_name": args.firm.strip(),
        "seat_count": args.seats,
    }
    signature = private_key.sign(canonical_payload(payload))
    document = {
        "licence": payload,
        "signature": base64.b64encode(signature).decode("ascii"),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Licence written to {args.output}")


if __name__ == "__main__":
    main()
