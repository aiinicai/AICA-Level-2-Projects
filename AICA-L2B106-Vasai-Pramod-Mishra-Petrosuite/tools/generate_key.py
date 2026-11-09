"""
generate_key.py — PRIVATE tool for the software administrator only.

DO NOT include this file or this folder in the client installer build.
It uses the same licence secret as the app (loaded from the untracked
pyapp/license_secret_local.py). Without that file it uses the DEMO secret.

Usage:
    python generate_key.py <MACHINE-ID-FROM-CLIENT>

Example:
    python generate_key.py ABCD-1234-EF56-7890
    -> prints the Activation Key to give back to that client PC.
"""
import sys
import os

# Reuse the exact same logic the app uses to verify keys, so keys generated
# here are guaranteed to match.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pyapp"))
from license_common import generate_activation_key  # noqa: E402


def main():
    if len(sys.argv) != 2:
        print("Usage: python generate_key.py <MACHINE-ID>")
        sys.exit(1)
    machine_id = sys.argv[1]
    key = generate_activation_key(machine_id)
    print(f"Machine ID     : {machine_id}")
    print(f"Activation Key : {key}")


if __name__ == "__main__":
    main()
