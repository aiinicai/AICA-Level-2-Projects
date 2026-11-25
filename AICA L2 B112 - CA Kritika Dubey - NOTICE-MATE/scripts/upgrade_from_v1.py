"""Safely upgrade an existing NOTICE-MATE v1 installation to v2 in place.

Run from THIS (v2) folder, pointing at your existing installation:

    python scripts/upgrade_from_v1.py "C:\\Users\\you\\Documents\\noticemate" --dry-run
    python scripts/upgrade_from_v1.py "C:\\Users\\you\\Documents\\noticemate"

What it does
1. Never touches: .env (API keys), workspace/ (database, documents, exports), .venv/venv,
   backups, .git, or any file that is not part of NOTICE-MATE.
2. For each NOTICE-MATE file it would replace, compares the existing file with the original
   v1 file (hash manifest). If YOU changed the file since v1, it is SKIPPED and listed,
   unless you pass --force (the old file is still backed up).
3. Copies every replaced file to <install>/_upgrade_backup_<timestamp>/ first.
4. Runs scripts/init_db.py inside your installation: this backs up the database with
   SQLite's backup API to <data_dir>/backups/ and then applies ADDITIVE migrations only
   (new tables/columns). Users, passwords, cases and records are not modified.
Rollback: copy the files back from _upgrade_backup_<timestamp>/ and restore the DB copy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
NEVER = {".env", "workspace", ".venv", "venv", "env", ".git", "backups", "exports", "__pycache__", ".pytest_cache", "test_workspace"}


def h(p: Path) -> str:
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def skip(rel: Path) -> bool:
    return any(part in NEVER or part.startswith("_upgrade_backup_") for part in rel.parts) or rel.suffix in (".pyc", ".db", ".log")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="Folder of your existing installation (the one containing run_api.bat and the noticemate/ package)")
    ap.add_argument("--dry-run", action="store_true", help="Show what would change; change nothing")
    ap.add_argument("--force", action="store_true", help="Also replace files you modified since v1 (they are backed up)")
    ap.add_argument("--skip-db", action="store_true", help="Do not run the database migration")
    a = ap.parse_args()

    tgt = Path(a.target).expanduser().resolve()
    if not (tgt / "noticemate" / "core" / "config.py").exists():
        print(f"ERROR: {tgt} does not look like a NOTICE-MATE installation (noticemate/core/config.py not found).")
        return 2
    if tgt == SRC:
        print("ERROR: target is this v2 folder itself. Point it at your existing installation.")
        return 2
    manifest = json.loads((SRC / "scripts" / "v1_manifest.json").read_text())["files"]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bdir = tgt / f"_upgrade_backup_{ts}"
    plan = {"new": [], "replace": [], "unchanged": [], "modified_skipped": [], "modified_forced": []}
    for f in sorted(SRC.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(SRC)
        if skip(rel):
            continue
        dest = tgt / rel
        if not dest.exists():
            plan["new"].append(rel)
            continue
        cur = h(dest)
        if cur == h(f):
            plan["unchanged"].append(rel)
        elif manifest.get(rel.as_posix()) == cur:
            plan["replace"].append(rel)
        else:
            (plan["modified_forced"] if a.force else plan["modified_skipped"]).append(rel)

    print(f"Target: {tgt}")
    for k in ("new", "replace", "unchanged", "modified_skipped", "modified_forced"):
        print(f"  {k:18s}: {len(plan[k])}")
    if plan["modified_skipped"]:
        print("\nThese files were changed in your installation since v1 and will NOT be replaced:")
        for r in plan["modified_skipped"]:
            print(f"   - {r}")
        print("Review them (compare with this folder) and re-run with --force if you want the v2 version (old copy is backed up).")
    if a.dry_run:
        print("\nDry run — nothing changed.")
        return 0
    if plan["modified_skipped"] and any(str(r).startswith(("noticemate", "frontend")) for r in plan["modified_skipped"]):
        print("\nWARNING: skipping modified application files may leave v1 and v2 code mixed. The app may not start until resolved.")

    for rel in plan["replace"] + plan["modified_forced"]:
        b = bdir / rel
        b.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tgt / rel, b)
    for rel in plan["new"] + plan["replace"] + plan["modified_forced"]:
        d = tgt / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SRC / rel, d)
    print(f"\nFiles updated. Backup of replaced files: {bdir if bdir.exists() else '(none needed)'}")
    (tgt / "UPGRADE_LOG.txt").open("a", encoding="utf-8").write(
        f"{ts} upgraded to v2: new={len(plan['new'])} replaced={len(plan['replace']) + len(plan['modified_forced'])} "
        f"skipped_modified={[str(r) for r in plan['modified_skipped']]}\n")

    if a.skip_db:
        print("Database migration skipped (--skip-db). Run 'python scripts/init_db.py' in the installation folder later.")
        return 0
    print("Backing up and migrating the database (additive only)…")
    r = subprocess.run([sys.executable, "scripts/init_db.py"], cwd=tgt)
    if r.returncode != 0:
        print("ERROR: migration failed. Your files are backed up in", bdir, "and the database backup (if taken) is in <data_dir>/backups/.")
        return r.returncode
    print("Upgrade complete. Start the API and UI as before (run_api.bat, run_ui.bat).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
