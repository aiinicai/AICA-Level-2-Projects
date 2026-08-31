"""Capture the seeded demo's API responses into the frontend's static snapshot.

Used by the GitHub Pages build: the static preview serves these responses instead
of calling the backend. Run with the backend up on :8000 (freshly seeded):

    cd backend && .venv/bin/python scripts/snapshot_demo.py
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx

BASE = "http://localhost:8000"
OUT = Path(__file__).resolve().parents[2] / "frontend" / "src" / "demo" / "data.json"

GLOBAL_PATHS = ["/api/auth/me", "/api/companies", "/api/dashboard", "/api/settings",
                "/api/valuations"]
CASE_PATHS = ["", "/financials", "/valuation", "/runs", "/insights", "/interview/state",
              "/assumptions", "/scenarios", "/reports", "/triggers", "/normalisations",
              "/documents"]


def main() -> None:
    snapshot: dict[str, object] = {}
    with httpx.Client(base_url=BASE, timeout=30) as client:
        for path in GLOBAL_PATHS:
            snapshot[path] = client.get(path).raise_for_status().json()
        cases = snapshot["/api/valuations"]
        assert isinstance(cases, list)
        for case in cases:
            cid = case["id"]
            for suffix in CASE_PATHS:
                path = f"/api/valuations/{cid}{suffix}"
                resp = client.get(path)
                if resp.status_code == 200:
                    snapshot[path] = resp.json()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot, indent=1))
    print(f"Wrote {len(snapshot)} endpoint snapshots → {OUT} "
          f"({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
