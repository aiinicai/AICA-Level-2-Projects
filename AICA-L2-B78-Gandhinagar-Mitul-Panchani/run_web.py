"""Start the local-only web demonstration server."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import uvicorn  # noqa: E402


def main() -> None:
    url = "http://127.0.0.1:8000"
    print(f"AI Memory Governance demo: {url}")
    uvicorn.run("amg.web.app:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
