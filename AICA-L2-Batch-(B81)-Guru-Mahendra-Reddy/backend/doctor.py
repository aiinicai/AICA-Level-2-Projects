#!/usr/bin/env python
"""Diagnose a Cash Runway installation.

    python doctor.py

Checks the things that actually go wrong — missing packages, an empty
database, a password that will not verify — and says what to do about each.
"""
from __future__ import annotations

import sys

OK, BAD, WARN = "  OK  ", " FAIL ", " WARN "


def main() -> int:
    problems: list[str] = []
    print("\n  Cash Runway — installation check\n  " + "=" * 34 + "\n")
    print(f"{OK} Python {sys.version.split()[0]}")

    # --- packages ------------------------------------------------------
    missing = []
    for mod, label in [("fastapi", "fastapi"), ("sqlalchemy", "sqlalchemy"),
                       ("pydantic", "pydantic"), ("jwt", "PyJWT"),
                       ("bcrypt", "bcrypt"), ("openpyxl", "openpyxl"),
                       ("requests", "requests"), ("dateutil", "python-dateutil"),
                       ("uvicorn", "uvicorn")]:
        try:
            __import__(mod)
        except ImportError:
            missing.append(label)
    if missing:
        print(f"{BAD} Missing packages: {', '.join(missing)}")
        problems.append("Run:  python -m pip install --no-index --find-links vendor "
                        "-r requirements.txt")
    else:
        import bcrypt, fastapi, sqlalchemy
        print(f"{OK} Packages present (fastapi {fastapi.__version__}, "
              f"sqlalchemy {sqlalchemy.__version__}, bcrypt {bcrypt.__version__})")

    if missing:
        _report(problems)
        return 1

    # --- database ------------------------------------------------------
    from app.config import DATA_DIR
    from app.database import SessionLocal, engine, init_db
    from sqlalchemy import inspect

    db_file = DATA_DIR / "cashrunway.db"
    if not db_file.exists():
        print(f"{WARN} No database at {db_file}")
        problems.append("Run:  python seed_db.py")
    else:
        size_kb = db_file.stat().st_size / 1024
        print(f"{OK} Database found ({size_kb:,.0f} KB)")

    init_db()
    tables = inspect(engine).get_table_names()
    print(f"{OK if tables else BAD} {len(tables)} tables")

    # --- users ---------------------------------------------------------
    from app.models import Entity, LedgerEntry, User
    db = SessionLocal()
    try:
        users = db.query(User).all()
        entities = db.query(Entity).count()
        entries = db.query(LedgerEntry).count()

        if not users:
            print(f"{BAD} No user accounts in the database — this is why sign-in fails.")
            problems.append("Run:  python seed_db.py    (loads the demo data and the accounts)")
        else:
            print(f"{OK} {len(users)} account(s), {entities} entities, {entries:,} ledger entries")

            # Prove the demo password actually verifies against the stored hash.
            from app.core.security import verify_password
            demo = db.query(User).filter(User.email == "guru@northwindrobotics.in").first()
            if not demo:
                print(f"{BAD} The demo CFO account is missing.")
                problems.append("Run:  python seed_db.py")
            elif verify_password("cashrunway", demo.password_hash):
                print(f"{OK} Sign-in verified for guru@northwindrobotics.in / cashrunway")
            else:
                print(f"{BAD} The stored password hash does not verify.")
                problems.append("The database was written by a different bcrypt build.\n"
                                "       Delete data/cashrunway.db and run:  python seed_db.py")

            if entries == 0:
                print(f"{WARN} No ledger entries — the screens will be empty.")
                problems.append("Delete data/cashrunway.db and run:  python seed_db.py")
    finally:
        db.close()

    # --- frontend ------------------------------------------------------
    from app.config import BASE_DIR
    dist = BASE_DIR.parent / "frontend" / "dist" / "index.html"
    if dist.exists():
        print(f"{OK} Built frontend present")
    else:
        print(f"{BAD} No built frontend at {dist}")
        problems.append("The download is incomplete — re-extract the ZIP.")

    return _report(problems)


def _report(problems: list[str]) -> int:
    print()
    if not problems:
        print("  Everything checks out. Start it with:\n")
        print("      python -m uvicorn app.main:app --port 8000\n")
        print("  Then open http://localhost:8000 and sign in with")
        print("      guru@northwindrobotics.in  /  cashrunway\n")
        return 0
    print("  What to do:\n")
    for p in problems:
        print(f"    - {p}")
    print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
