"""Timestamped backup with 30-day retention. Build Prompt v2 §11.4.

    python scripts/backup.py            create a backup, prune old ones
    python scripts/backup.py --list     show what exists

Restore procedure is in docs/RESTORE.md. Read it before you need it.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings

RETENTION_DAYS = 30
STAMP = "%Y%m%d-%H%M%S"


def _backup_dir(settings) -> Path:
    path = settings.data_path / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _copy_database(settings, staging: Path) -> Path | None:
    """Copy the SQLite file consistently.

    `sqlite3.backup` is used rather than a file copy: with WAL enabled a
    plain copy can capture a database mid-write and produce an archive that
    restores to a corrupt file.
    """
    url = settings.database_url
    if not url.startswith("sqlite:///"):
        return None

    source = Path(url.removeprefix("sqlite:///"))
    if not source.is_absolute():
        source = settings.data_path.parent / source
    if not source.exists():
        return None

    target = staging / source.name
    with sqlite3.connect(str(source)) as origin, sqlite3.connect(str(target)) as copy:
        origin.backup(copy)
    return target


def create_backup() -> Path:
    settings = get_settings()
    settings.ensure_directories()

    stamp = datetime.now(UTC).strftime(STAMP)
    staging = _backup_dir(settings) / f"staging-{stamp}"
    staging.mkdir(parents=True, exist_ok=True)

    archive_path = _backup_dir(settings) / f"auditcraft-{stamp}.zip"
    try:
        database = _copy_database(settings, staging)
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
            if database is not None:
                archive.write(database, f"database/{database.name}")

            clients = settings.data_path / "clients"
            if clients.exists():
                for item in clients.rglob("*"):
                    if item.is_file():
                        archive.write(item, str(Path("documents") / item.relative_to(clients)))

            content = settings.content_path
            if content.exists():
                for item in content.rglob("*.yaml"):
                    archive.write(item, str(Path("content") / item.relative_to(content)))
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    return archive_path


def prune(retention_days: int = RETENTION_DAYS) -> list[Path]:
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    removed: list[Path] = []
    for archive in _backup_dir(settings).glob("auditcraft-*.zip"):
        stamp = archive.stem.removeprefix("auditcraft-")
        try:
            created = datetime.strptime(stamp, STAMP).replace(tzinfo=UTC)
        except ValueError:
            continue
        if created < cutoff:
            archive.unlink()
            removed.append(archive)
    return removed


def list_backups() -> list[Path]:
    return sorted(_backup_dir(get_settings()).glob("auditcraft-*.zip"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="list existing backups")
    parser.add_argument("--retention-days", type=int, default=RETENTION_DAYS)
    args = parser.parse_args()

    if args.list:
        for archive in list_backups():
            size_mb = archive.stat().st_size / 1_048_576
            print(f"{archive.name}  {size_mb:.1f} MB")
        return 0

    archive = create_backup()
    removed = prune(args.retention_days)
    print(f"created:  {archive}")
    print(f"size:     {archive.stat().st_size / 1_048_576:.1f} MB")
    print(f"pruned:   {len(removed)} archive(s) older than {args.retention_days} days")
    print("restore:  see docs/RESTORE.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
