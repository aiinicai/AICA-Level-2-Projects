"""Validate the trusted Windows release interpreter for the IBC Expert 3.14 target."""
from __future__ import annotations

import argparse
import platform
import struct
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-windows", action="store_true")
    args = parser.parse_args()

    if sys.implementation.name != "cpython":
        raise SystemExit("IBC Expert Windows release builds require CPython.")
    if sys.version_info[:2] != (3, 14):
        raise SystemExit(
            f"IBC Expert Build 15 Windows release target is CPython 3.14.x; found {sys.version.split()[0]}."
        )
    if struct.calcsize("P") * 8 != 64:
        raise SystemExit("IBC Expert Windows release builds require 64-bit CPython 3.14.")
    if args.require_windows and platform.system() != "Windows":
        raise SystemExit("This release target validation must be run on Windows.")
    print(f"OK: CPython {sys.version.split()[0]} 64-bit on {platform.system()} is valid for the IBC Expert 3.14 release target.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
