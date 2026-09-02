"""
Stage 3 review round 2, condition #4: a dedicated migration test.

Runs the REAL `alembic upgrade head` (via Alembic's Python API, not a
shell-out) against a fresh, on-disk SQLite database — deliberately not
:memory: and deliberately not Base.metadata.create_all() — then uses
SQLAlchemy's inspector to confirm the resulting live schema has the
same 24 tables and the same columns per table as app/models/*.py
(Base.metadata). This is the authoritative test; run it wherever
dependencies are installed:

    pip install -r requirements.txt
    pytest tests/unit/test_migration.py -v

NOTE ON THIS SANDBOX: could not be executed here — see
database/migrations/versions/README.md and the Stage 3 round-2 delivery
notes for what was verified instead (a custom harness + AST-based
cross-check against the model source, since Alembic/SQLAlchemy could
not be installed).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest


@pytest.fixture()
def fresh_sqlite_url(tmp_path, monkeypatch):
    db_path = tmp_path / "migration_test.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setenv("FINSIGHT_ALEMBIC_DB_URL", url)
    return url


def test_alembic_upgrade_head_matches_base_metadata(fresh_sqlite_url):
    from alembic import command
    from alembic.config import Config as AlembicConfig
    from sqlalchemy import create_engine, inspect

    from app.models import Base

    project_root = Path(__file__).resolve().parent.parent.parent
    alembic_cfg = AlembicConfig(str(project_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(project_root / "database" / "migrations"))

    # The real thing: actually run the migration against a real file.
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(fresh_sqlite_url, future=True)
    inspector = inspect(engine)

    migrated_tables = set(inspector.get_table_names())
    # alembic_version is Alembic's own bookkeeping table, not one of ours.
    migrated_tables.discard("alembic_version")

    expected_tables = set(Base.metadata.tables.keys())

    assert migrated_tables == expected_tables, (
        f"Migration produced a different table set than Base.metadata.\n"
        f"Missing (in models, not migration): {expected_tables - migrated_tables}\n"
        f"Extra (in migration, not models): {migrated_tables - expected_tables}"
    )
    assert len(expected_tables) == 24

    mismatches = []
    for table_name, table in Base.metadata.tables.items():
        expected_columns = set(table.columns.keys())
        actual_columns = {c["name"] for c in inspector.get_columns(table_name)}
        if expected_columns != actual_columns:
            mismatches.append(
                f"{table_name}: missing={expected_columns - actual_columns} "
                f"extra={actual_columns - expected_columns}"
            )
    assert not mismatches, "Column mismatches:\n" + "\n".join(mismatches)


def test_downgrade_reverses_cleanly(fresh_sqlite_url):
    from alembic import command
    from alembic.config import Config as AlembicConfig
    from sqlalchemy import create_engine, inspect

    project_root = Path(__file__).resolve().parent.parent.parent
    alembic_cfg = AlembicConfig(str(project_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(project_root / "database" / "migrations"))

    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")

    engine = create_engine(fresh_sqlite_url, future=True)
    inspector = inspect(engine)
    remaining = set(inspector.get_table_names()) - {"alembic_version"}
    assert remaining == set(), f"downgrade() left tables behind: {remaining}"
