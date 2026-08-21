"""Verify the vendored front-end libraries against their recorded digests.

    python scripts/check_vendored_assets.py

Build Prompt v2 §1 requires HTMX and Alpine to be vendored locally, and §13
forbids any runtime network fetch. Both are therefore files in the repository
rather than a URL, which moves the risk: a vendored library can be replaced
by a bad merge, a partial download, or something deliberate, and nothing about
the page would look different.

The expected digests live in `docs/VENDORED_ASSETS.md` and are parsed from it,
so the documentation is the source of truth rather than a second copy that can
drift from one.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENDOR_DIR = PROJECT_ROOT / "app" / "static" / "vendor"
MANIFEST = PROJECT_ROOT / "docs" / "VENDORED_ASSETS.md"

_ROW = re.compile(r"^\|\s*`([^`]+\.js)`\s*\|\s*([\d,]+)\s*\|\s*`([0-9a-f]{64})`\s*\|", re.M)


def expected() -> dict[str, tuple[int, str]]:
    """{filename: (bytes, sha256)} as recorded in the manifest."""
    text = MANIFEST.read_text(encoding="utf-8")
    found = {
        name: (int(size.replace(",", "")), digest) for name, size, digest in _ROW.findall(text)
    }
    if not found:
        raise SystemExit(f"{MANIFEST}: no asset rows found — has the table changed shape?")
    return found


def problems() -> list[str]:
    out: list[str] = []
    recorded = expected()

    for name, (size, digest) in recorded.items():
        path = VENDOR_DIR / name
        if not path.exists():
            out.append(f"{name}: recorded in the manifest but missing from {VENDOR_DIR}")
            continue
        data = path.read_bytes()
        if len(data) != size:
            out.append(f"{name}: {len(data):,} bytes, manifest says {size:,}")
        actual = hashlib.sha256(data).hexdigest()
        if actual != digest:
            out.append(f"{name}: sha256 {actual}\n    manifest says {digest}")

    for path in sorted(VENDOR_DIR.glob("*.js")):
        if path.name not in recorded:
            out.append(f"{path.name}: present in {VENDOR_DIR} but not recorded in the manifest")

    return out


def main() -> int:
    found = problems()
    if found:
        print("Vendored assets do not match docs/VENDORED_ASSETS.md:\n")
        for problem in found:
            print(f"  - {problem}")
        return 1
    print(f"{len(expected())} vendored assets match their recorded digests.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
