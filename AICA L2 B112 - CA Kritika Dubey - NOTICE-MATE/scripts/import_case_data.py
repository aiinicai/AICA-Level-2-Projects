"""Safely import a local copy of the upgraded V2 database and documents."""
from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT / "source-data"
SOURCE_DB = SOURCE / "noticemate.db"
SOURCE_DOCUMENTS = SOURCE / "documents"
WORKSPACE = PROJECT / "workspace"
TARGET_DB = WORKSPACE / "noticemate.db"
TARGET_DOCUMENTS = WORKSPACE / "documents"


def count_rows(db: sqlite3.Connection, table: str, tables: set[str]) -> int | None:
    if table not in tables:
        return None
    return int(db.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])


def main() -> int:
    if not SOURCE_DB.is_file() or not SOURCE_DOCUMENTS.is_dir():
        raise SystemExit(
            "Copy noticemate.db and the full documents folder into the sibling "
            "work/source-data folder, then run this script again."
        )
    if TARGET_DB.exists() or TARGET_DOCUMENTS.exists():
        raise SystemExit("V3 already has database or documents. Import stopped to avoid overwriting them.")

    WORKSPACE.mkdir(parents=True, exist_ok=True)
    source_uri = SOURCE_DB.resolve().as_uri() + "?mode=ro"
    source = sqlite3.connect(source_uri, uri=True)
    target = sqlite3.connect(TARGET_DB)
    try:
        source.execute("PRAGMA query_only=ON")
        source.backup(target)
        integrity = str(target.execute("PRAGMA integrity_check").fetchone()[0])
        if integrity.lower() != "ok":
            raise SystemExit(f"Imported database integrity check failed: {integrity}")
        tables = {
            str(row[0])
            for row in target.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        summary = {
            "integrity": integrity,
            "table_count": len(tables),
            "case_rows": count_rows(target, "cases", tables),
            "document_rows": count_rows(target, "documents", tables),
        }
    except Exception:
        target.close()
        source.close()
        TARGET_DB.unlink(missing_ok=True)
        raise
    target.close()
    source.close()

    try:
        shutil.copytree(SOURCE_DOCUMENTS, TARGET_DOCUMENTS)
    except Exception:
        TARGET_DB.unlink(missing_ok=True)
        shutil.rmtree(TARGET_DOCUMENTS, ignore_errors=True)
        raise

    report = WORKSPACE / "import_summary.json"
    report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
