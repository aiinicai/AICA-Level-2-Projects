"""Verify that an offline IBC Expert wheelhouse is complete and integrity-protected.

The verifier intentionally delegates dependency resolution to pip in offline/dry-run mode.  That
checks direct and transitive pinned dependencies for the *current* Python/Windows interpreter
without installing anything.  A SHA-256 manifest is also required so copied wheelhouses can be
checked before use.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

_HASH_LINE = re.compile(r"^(?P<hash>[0-9a-f]{64})\s{2}(?P<name>[^\\/]+)$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(wheelhouse: Path) -> Path:
    wheelhouse = wheelhouse.resolve()
    wheels = sorted(path for path in wheelhouse.iterdir() if path.is_file() and path.suffix.lower() == ".whl")
    if not wheels:
        raise ValueError(f"No wheel files found in {wheelhouse}")
    manifest = wheelhouse / "SHA256SUMS.txt"
    manifest.write_text(
        "".join(f"{sha256_file(path)}  {path.name}\n" for path in wheels),
        encoding="ascii",
    )
    return manifest


def verify_manifest(wheelhouse: Path) -> list[str]:
    wheelhouse = wheelhouse.resolve()
    manifest = wheelhouse / "SHA256SUMS.txt"
    if not manifest.is_file():
        return ["wheelhouse/SHA256SUMS.txt is missing."]

    issues: list[str] = []
    expected: dict[str, str] = {}
    for lineno, raw in enumerate(manifest.read_text(encoding="ascii", errors="replace").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        match = _HASH_LINE.fullmatch(line)
        if not match:
            issues.append(f"Invalid SHA256SUMS.txt line {lineno}.")
            continue
        name = match.group("name")
        if name in expected:
            issues.append(f"Duplicate manifest entry: {name}")
            continue
        expected[name] = match.group("hash")

    wheels = sorted(path for path in wheelhouse.iterdir() if path.is_file() and path.suffix.lower() == ".whl")
    if not wheels:
        issues.append("Wheelhouse contains no .whl files.")
        return issues

    wheel_names = {path.name for path in wheels}
    manifest_names = set(expected)
    for missing in sorted(wheel_names - manifest_names):
        issues.append(f"Wheel missing from SHA256SUMS.txt: {missing}")
    for stale in sorted(manifest_names - wheel_names):
        issues.append(f"Manifest references missing wheel: {stale}")
    for path in wheels:
        recorded = expected.get(path.name)
        if recorded and sha256_file(path) != recorded:
            issues.append(f"SHA-256 mismatch: {path.name}")

    non_wheels = [
        path.name
        for path in wheelhouse.iterdir()
        if path.is_file() and path.name != "SHA256SUMS.txt" and path.suffix.lower() != ".whl"
    ]
    if non_wheels:
        issues.append("Wheelhouse contains non-wheel package artifacts: " + ", ".join(sorted(non_wheels)))
    return issues


def verify_resolution(wheelhouse: Path, requirements: Path, *, python_executable: str | None = None) -> list[str]:
    python = python_executable or sys.executable
    command = [
        python,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--dry-run",
        "--ignore-installed",
        "--no-index",
        "--find-links",
        str(wheelhouse.resolve()),
        "-r",
        str(requirements.resolve()),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0:
        return []
    detail = (result.stderr or result.stdout or "pip returned an unknown error").strip()
    return ["Offline pip dependency resolution failed.\n" + detail]


def verify_wheelhouse(
    wheelhouse: Path,
    requirements: Path,
    *,
    python_executable: str | None = None,
    resolve: bool = True,
) -> list[str]:
    wheelhouse = wheelhouse.expanduser().resolve()
    requirements = requirements.expanduser().resolve()
    if not wheelhouse.is_dir():
        return [f"Wheelhouse directory does not exist: {wheelhouse}"]
    if not requirements.is_file():
        return [f"Requirements file does not exist: {requirements}"]
    issues = verify_manifest(wheelhouse)
    if resolve and not issues:
        issues.extend(verify_resolution(wheelhouse, requirements, python_executable=python_executable))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify IBC Expert offline wheelhouse")
    parser.add_argument("wheelhouse", type=Path)
    parser.add_argument("--requirements", type=Path, default=Path("requirements.txt"))
    parser.add_argument("--write-manifest", action="store_true")
    parser.add_argument("--skip-resolution", action="store_true")
    args = parser.parse_args()
    if args.write_manifest:
        try:
            manifest = write_manifest(args.wheelhouse)
        except (OSError, ValueError) as exc:
            print(f"WHEELHOUSE MANIFEST FAILED: {exc}")
            return 2
        print(f"Wrote {manifest}")
    issues = verify_wheelhouse(
        args.wheelhouse,
        args.requirements,
        resolve=not args.skip_resolution,
    )
    if issues:
        print("WHEELHOUSE VERIFICATION FAILED")
        for issue in issues:
            print(f" - {issue}")
        return 2
    print("Wheelhouse verification passed: hashes match and pinned dependencies resolve offline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
