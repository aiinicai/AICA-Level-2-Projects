"""Post-build verification for the ordinary IBC Expert customer package.

The verifier is intentionally independent of PyInstaller internals. It scans the emitted onedir
folder and fails the release if owner-only code, private signing material, or a missing/invalid
public verification key is detected.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from scripts.validate_public_key import PublicKeyValidationError, validate_public_key

FORBIDDEN_PARTS = {"owner_tools", "tests"}
FORBIDDEN_FILENAMES = {
    "owner_private_key.ibckey",
    "owner_private_key.pem",
    "owner_private_key.key",
}
PRIVATE_MARKERS = (
    b"-----BEGIN PRIVATE KEY-----",
    b"-----BEGIN OPENSSH PRIVATE KEY-----",
    b"IBC-OWNER-KEY-v1\x00",
)
TEXT_SCAN_EXTENSIONS = {".ibckey", ".pem", ".key", ".txt", ".json", ".hex", ".ini", ".cfg"}


def _files(root: Path) -> Iterable[Path]:
    return (path for path in root.rglob("*") if path.is_file())


def verify_customer_package(root: Path, *, require_executable: bool = False) -> list[str]:
    root = root.expanduser().resolve()
    issues: list[str] = []
    if not root.is_dir():
        return [f"Customer package directory does not exist: {root}"]

    paths = list(_files(root))
    for path in paths:
        relative = path.relative_to(root)
        lowered_parts = {part.casefold() for part in relative.parts}
        if lowered_parts & FORBIDDEN_PARTS:
            issues.append(f"Forbidden owner/test path present: {relative}")
        if path.name.casefold() in FORBIDDEN_FILENAMES:
            issues.append(f"Private signing-key filename present: {relative}")
        if path.suffix.casefold() in TEXT_SCAN_EXTENSIONS:
            try:
                payload = path.read_bytes()
            except OSError as exc:
                issues.append(f"Could not inspect package file {relative}: {exc}")
                continue
            for marker in PRIVATE_MARKERS:
                if marker in payload:
                    issues.append(f"Private signing-key marker present: {relative}")
                    break

    public_keys = [path for path in paths if path.name.casefold() == "licence_public_key.hex"]
    if len(public_keys) != 1:
        issues.append(
            f"Customer package must contain exactly one licence_public_key.hex; found {len(public_keys)}."
        )
    else:
        try:
            validate_public_key(public_keys[0])
        except PublicKeyValidationError as exc:
            issues.append(f"Bundled public licence key is invalid: {exc}")

    if require_executable and not (root / "IBCExpert.exe").is_file():
        issues.append("IBCExpert.exe is missing from the PyInstaller onedir output.")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify IBC Expert customer release contents")
    parser.add_argument("package_dir", type=Path)
    parser.add_argument("--require-executable", action="store_true")
    args = parser.parse_args()
    issues = verify_customer_package(args.package_dir, require_executable=args.require_executable)
    if issues:
        print("CUSTOMER PACKAGE VERIFICATION FAILED")
        for issue in issues:
            print(f" - {issue}")
        return 2
    print("Customer package verification passed: no owner tools/private signing key detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
