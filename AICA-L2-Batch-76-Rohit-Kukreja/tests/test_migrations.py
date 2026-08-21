"""Migrations must run on a database that already has rows in it.

This has bitten twice, and both times the failure was invisible on an empty
development database:

  * migration 0003 added NOT NULL boolean columns with no server default,
    which succeeds until a row exists;
  * SQLite batch mode rebuilds a table by copying rows into a replacement and
    renaming, which trips "FOREIGN KEY constraint failed" as soon as the
    table has children and `PRAGMA foreign_keys` is on — and `app.db` turns
    it on for every SQLite connection.

A third failure was worse still: the fix for the second, written as
`connection.exec_driver_sql("PRAGMA foreign_keys=OFF")`, fired SQLAlchemy's
"begin" event. `_fix_pysqlite_transactions` answers that by emitting BEGIN
itself, so alembic nested inside a transaction it did not own and every
CREATE TABLE was rolled back at close. Alembic reported success and the
database was empty — 21 tables became 0.

So this file asserts two things a unit test cannot: that a full upgrade
actually creates the schema, and that the last migration applies to a
populated database and leaves the rows alone.
"""

from __future__ import annotations

import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALEMBIC = PROJECT_ROOT / ".venv" / ("Scripts/alembic.exe" if os.name == "nt" else "bin/alembic")

# The revision before the head, so the head can be applied to a seeded
# database. Read from the head file rather than hard-coded, so renaming a
# revision does not leave this test silently exercising the wrong step.
HEAD_MIGRATION = PROJECT_ROOT / "alembic" / "versions" / "0006_drop_bdr_director_change.py"


def _revisions() -> tuple[str, str]:
    """(head, previous) read out of the head migration.

    Both quote styles are accepted: alembic's own template writes single
    quotes, hand-written migrations get double quotes from the formatter, and
    a parser that only knew one of them failed with a bare IndexError that
    said nothing about why.
    """
    text = HEAD_MIGRATION.read_text(encoding="utf-8")

    def value(name: str) -> str:
        match = re.search(rf"^{name}[^=]*=\s*['\"]([0-9a-zA-Z_]+)['\"]", text, re.M)
        assert match, f"{HEAD_MIGRATION.name}: could not read `{name}`"
        return match.group(1)

    return value("revision"), value("down_revision")


def _alembic(target: str, db: Path) -> subprocess.CompletedProcess[str]:
    # S603: the executable is this project's own alembic and the argument is a
    # revision id read from a file in the repository. Nothing here is user input.
    return subprocess.run(  # noqa: S603
        (
            [str(ALEMBIC), "upgrade", target]
            if target != "down"
            else [str(ALEMBIC), "downgrade", "-1"]
        ),
        cwd=PROJECT_ROOT,
        env={**os.environ, "AUDITCRAFT_DATABASE_URL": f"sqlite:///{db.as_posix()}"},
        capture_output=True,
        text=True,
    )


def _tables(db: Path) -> set[str]:
    with sqlite3.connect(db) as connection:
        return {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }


def _insert(db: Path, table: str, **values: object) -> None:
    """Insert a row, defaulting any other NOT NULL column to 0."""
    with sqlite3.connect(db) as connection:
        for _, name, _type, notnull, _default, _pk in connection.execute(
            f"PRAGMA table_info({table})"
        ):
            if notnull and name not in values:
                values.setdefault(name, 0)
        columns = ",".join(values)
        placeholders = ",".join("?" * len(values))
        # S608: table and column names come from this file and from
        # PRAGMA table_info on the database under test; the values are bound.
        connection.execute(
            f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",  # noqa: S608
            list(values.values()),
        )


@pytest.mark.skipif(not ALEMBIC.exists(), reason="alembic console script not installed")
class TestMigrations:
    def test_a_full_upgrade_actually_creates_the_schema(self, tmp_path: Path) -> None:
        """Alembic reporting success is not evidence that anything was written."""
        db = tmp_path / "fresh.db"
        result = _alembic("head", db)
        assert result.returncode == 0, result.stderr[-2000:]
        tables = _tables(db)
        assert "alembic_version" in tables
        assert {"firm", "client", "client_profile", "engagement"} <= tables
        assert len(tables) > 15, f"only {len(tables)} tables created: {sorted(tables)}"

    def test_the_head_migration_applies_to_a_populated_database(self, tmp_path: Path) -> None:
        head, previous = _revisions()
        db = tmp_path / "populated.db"

        assert _alembic(previous, db).returncode == 0
        _insert(db, "firm", firm_name="F", frn="X")
        _insert(db, "client", firm_id=1, client_code="C1", created_by="t")
        _insert(
            db,
            "client_profile",
            client_id=1,
            valid_from="2020-01-01",
            is_current=1,
            company_name="Specimen",
            registered_addr="A",
            company_type="pvt",
            framework="igaap",
            amounts_in="units",
            changed_by="t",
            change_reason="t",
        )
        _insert(
            db,
            "engagement",
            client_id=1,
            fy_code="2025-26",
            fy_start="2025-04-01",
            fy_end="2026-03-31",
            status="data_collection",
        )

        result = _alembic(head, db)
        assert result.returncode == 0, result.stderr[-2000:]

        with sqlite3.connect(db) as connection:
            row = connection.execute("SELECT company_name FROM client_profile").fetchone()
            tables = {
                r[0]
                for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
        assert row == ("Specimen",), "the existing row did not survive the migration"
        assert "key_audit_matter" in tables
        # 0006 drops the table `bdr.directors.kmp` used before it was computed.
        assert "bdr_director_change" not in tables

    def test_every_applicability_flag_has_its_columns(self, tmp_path: Path) -> None:
        """§7 — every flag is overridable. A missing column used to drop the
        flag out of the override map silently rather than raising."""
        from app.core.applicability import DERIVED_FLAGS, FLAGS

        db = tmp_path / "flags.db"
        assert _alembic("head", db).returncode == 0
        with sqlite3.connect(db) as connection:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(client_profile)")}
        # A derived flag has no column because it has no independent value:
        # `full_board_report` is the inverse of `abridged_board_report`, and
        # storing it separately is how the two would come to disagree.
        missing = [
            name
            for flag in FLAGS
            if flag not in DERIVED_FLAGS
            for name in (flag, f"{flag}_override")
            if name not in columns
        ]
        assert not missing, f"client_profile is missing {missing}"


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__]))
