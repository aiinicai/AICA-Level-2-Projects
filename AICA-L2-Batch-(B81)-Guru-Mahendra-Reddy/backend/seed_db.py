#!/usr/bin/env python
"""Load the demonstration dataset.

    python seed_db.py

Drops and recreates every table, then loads 18 months of Northwind Robotics
data. Safe to re-run — it is deterministic, so you get the same numbers back.
"""
from __future__ import annotations

import sys

from app.database import SessionLocal, init_db
from app.seed import seed_all


def main() -> int:
    init_db()
    db = SessionLocal()
    try:
        stats = seed_all(db, wipe=True)
    finally:
        db.close()

    print("\n  Cash Runway — demonstration dataset loaded\n")
    width = max(len(k) for k in stats)
    for k, v in stats.items():
        label = k.replace("_", " ").title()
        if k.endswith("cash"):
            print(f"  {label:<{width + 2}} ₹ {v / 10_000_000:,.2f} Cr")
        else:
            print(f"  {label:<{width + 2}} {v:,}")
    print("\n  Sign in with  guru@northwindrobotics.in  /  cashrunway\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
