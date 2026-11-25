"""Create tables, apply schema migrations and seed the minimum rows. Safe to run repeatedly.

Seeds: business settings (from defaults), schema version, and two scenarios.
It does NOT seed categories (they come from the uploaded category list) or users
(the first Admin is created with ``python -m app.cli create-admin`` in Phase 8).

Migrations are additive (SQLite ADD COLUMN) and keyed by schema version, so an existing
database is upgraded in place without losing data.
"""
from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import get_business_defaults
from app.models import AppSetting, Base, Scenario

SCHEMA_VERSION = 2

# version -> list of (table, column, SQL type and default)
MIGRATIONS: dict[int, list[tuple[str, str, str]]] = {
    2: [
        ("import_batch", "slot", "VARCHAR(80) NOT NULL DEFAULT ''"),
        ("line_item", "category_text", "VARCHAR(120) NOT NULL DEFAULT ''"),
        ("line_item", "direction_provisional", "BOOLEAN NOT NULL DEFAULT 0"),
        ("line_item", "bill_discounted_imported", "BOOLEAN NOT NULL DEFAULT 0"),
        ("line_item", "linked_invoice", "VARCHAR(80) NOT NULL DEFAULT ''"),
    ],
}


def _migrate(engine: Engine, from_version: int) -> None:
    with engine.begin() as conn:
        for v in range(from_version + 1, SCHEMA_VERSION + 1):
            for table, column, ddl in MIGRATIONS.get(v, []):
                cols = {r[1] for r in conn.exec_driver_sql(f"PRAGMA table_info('{table}')")}
                if column not in cols:
                    conn.exec_driver_sql(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {ddl}')
            if v == 2:  # existing batches: slot = source type
                conn.execute(text("UPDATE import_batch SET slot = source_type WHERE slot = ''"))


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        stored = db.get(AppSetting, "schema_version")
        version = int(stored.value) if stored else None
    if version is not None and version < SCHEMA_VERSION:
        _migrate(engine, version)
    with Session(engine) as db:
        existing = {k for k in db.scalars(select(AppSetting.key))}
        for key, value in get_business_defaults().model_dump().items():
            if key not in existing:
                db.add(AppSetting(key=key, value=value))
        sv = db.get(AppSetting, "schema_version")
        if sv is None:
            db.add(AppSetting(key="schema_version", value=SCHEMA_VERSION))
        elif int(sv.value) < SCHEMA_VERSION:
            sv.value = SCHEMA_VERSION
        if db.scalar(select(Scenario).limit(1)) is None:
            db.add_all([
                Scenario(name="Base", description="All items as imported plus overrides.", is_default=True),
                Scenario(name="Risk-adjusted",
                         description="Base, excluding collections flagged as risk-adjusted.",
                         exclude_risk_adjusted=True),
            ])
        db.commit()
