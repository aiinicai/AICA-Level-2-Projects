#!/usr/bin/env python
"""Back up and restore the Cash Runway database.

    python backup.py                     # take a backup now
    python backup.py --list              # what backups exist
    python backup.py --restore <file>    # put one back
    python backup.py --verify <file>     # check one without restoring

Everything the application knows lives in one SQLite file. That is convenient
until it is lost, and "we have backups" is worth nothing until a restore has
actually been done — so this takes the copy *and* opens it, runs SQLite's own
integrity check, and counts the rows it should contain. A backup that fails
that check is deleted rather than kept, because a corrupt file that looks like
a backup is worse than no backup at all.

The copy is taken with SQLite's online backup API, so it is safe to run while
the application is up. A file copy is not: it can catch the database
mid-write.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
DB = DATA / "cashrunway.db"
BACKUPS = DATA / "backups"
KEEP = 14                      # roughly a fortnight of daily backups

# If these are empty the file is not a Cash Runway database, whatever its name.
EXPECTED_TABLES = ["users", "entities", "alert_rules"]


def _size(p: Path) -> str:
    n = p.stat().st_size
    return f"{n / 1_048_576:.1f} MB" if n >= 1_048_576 else f"{n / 1024:.0f} KB"


def verify(path: Path) -> tuple[bool, str]:
    """Open a backup and satisfy ourselves it is really one."""
    if not path.exists():
        return False, "file does not exist"
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            result = con.execute("PRAGMA integrity_check").fetchone()[0]
            if result != "ok":
                return False, f"integrity check failed: {result}"
            counts = []
            for t in EXPECTED_TABLES:
                n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                counts.append(f"{t} {n}")
                if t == "users" and n == 0:
                    return False, "no sign-in accounts — this would lock you out"
            return True, ", ".join(counts)
        finally:
            con.close()
    except sqlite3.DatabaseError as e:
        return False, f"not a readable SQLite database: {e}"


def take() -> int:
    if not DB.exists():
        print(f"  No database at {DB}. Nothing to back up.")
        return 1
    BACKUPS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = BACKUPS / f"cashrunway-{stamp}.db"

    src = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    dst = sqlite3.connect(dest)
    try:
        src.backup(dst)          # online backup — safe while the app is running
    finally:
        dst.close()
        src.close()

    ok, detail = verify(dest)
    if not ok:
        dest.unlink(missing_ok=True)
        print(f"  Backup failed its own check and was deleted: {detail}")
        return 1

    print(f"  Backed up to  {dest}")
    print(f"  {_size(dest)} · verified · {detail}")

    existing = sorted(BACKUPS.glob("cashrunway-*.db"))
    for old in existing[:-KEEP]:
        old.unlink()
        print(f"  Removed old backup {old.name}")
    return 0


def listing() -> int:
    files = sorted(BACKUPS.glob("cashrunway-*.db"), reverse=True)
    if not files:
        print(f"  No backups in {BACKUPS}.")
        print("  Run 'python backup.py' to take one.")
        return 0
    print(f"  {len(files)} backup(s) in {BACKUPS}\n")
    for f in files:
        when = datetime.fromtimestamp(f.stat().st_mtime).strftime("%d-%b-%Y %H:%M")
        print(f"    {f.name:<34} {when}   {_size(f):>9}")
    return 0


def restore(path: Path) -> int:
    ok, detail = verify(path)
    if not ok:
        print(f"  Refusing to restore: {detail}")
        return 1
    print(f"  Backup checks out — {detail}")

    # The database being replaced is itself backed up first. Restoring the
    # wrong file is a mistake people make once, and it should be reversible.
    if DB.exists():
        BACKUPS.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safety = BACKUPS / f"before-restore-{stamp}.db"
        src = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        dst = sqlite3.connect(safety)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        print(f"  Current database saved to {safety.name} first.")

    dst = sqlite3.connect(DB)
    src = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        src.backup(dst)
    finally:
        src.close()
        dst.close()

    ok, detail = verify(DB)
    print(f"  Restored from {path.name}" if ok else f"  Restore failed: {detail}")
    print("  Restart the application to pick it up.")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Back up and restore Cash Runway.")
    ap.add_argument("--list", action="store_true", help="list existing backups")
    ap.add_argument("--restore", metavar="FILE", help="restore from a backup")
    ap.add_argument("--verify", metavar="FILE", help="check a backup, change nothing")
    a = ap.parse_args()

    print()
    if a.list:
        return listing()
    if a.verify:
        p = Path(a.verify)
        p = p if p.exists() else BACKUPS / a.verify
        ok, detail = verify(p)
        print(f"  {p.name}: {'OK — ' + detail if ok else 'FAILED — ' + detail}")
        return 0 if ok else 1
    if a.restore:
        p = Path(a.restore)
        return restore(p if p.exists() else BACKUPS / a.restore)
    return take()


if __name__ == "__main__":
    raise SystemExit(main())
