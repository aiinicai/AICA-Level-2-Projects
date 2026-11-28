"""Versioned, additive schema migrations.

Each entry upgrades the schema by one version. Rules:
- Only ADD tables/columns; never drop or rename columns holding user data.
- A database is backed up automatically before migrating (file copy next to it).
- New tables are created with metadata.create_all (idempotent).
- New columns on existing tables: use add_column() below.
"""
from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

log = logging.getLogger(__name__)


def add_column(engine: Engine, table: str, column_ddl: str) -> None:
    name = column_ddl.split()[0]
    cols = {c["name"] for c in inspect(engine).get_columns(table)}
    if name not in cols:
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_ddl}"))


def _v2_invoice_processing(engine: Engine) -> None:
    from ipt.db.base import Base
    from ipt.db import models  # noqa: F401
    Base.metadata.create_all(engine)


def _v3_tally(engine: Engine) -> None:
    from ipt.db.base import Base
    from ipt.db import models  # noqa: F401
    Base.metadata.create_all(engine)


def _v4_invoice_pages(engine: Engine) -> None:
    add_column(engine, "invoices", "page_from INTEGER")
    add_column(engine, "invoices", "page_to INTEGER")


def _v5_reconciliation(engine: Engine) -> None:
    from ipt.db.base import Base
    from ipt.db import models  # noqa: F401
    Base.metadata.create_all(engine)


def _v6_backups(engine: Engine) -> None:
    from ipt.db.base import Base
    from ipt.db import models  # noqa: F401
    Base.metadata.create_all(engine)


def _v7_supplier_layouts(engine: Engine) -> None:
    from ipt.db.base import Base
    from ipt.db import models  # noqa: F401
    Base.metadata.create_all(engine)
    add_column(engine, "supplier_layouts", "anchor VARCHAR(80) DEFAULT ''")
    add_column(engine, "supplier_layouts", "dx FLOAT DEFAULT 0")
    add_column(engine, "supplier_layouts", "dy FLOAT DEFAULT 0")


def _v8_doc_type_default(engine: Engine) -> None:
    """Bills marked 'other' (or with no type) are tax invoices - the only kind IPT books besides notes."""
    with engine.begin() as conn:
        conn.execute(text("UPDATE invoices SET doc_type = 'tax_invoice' WHERE doc_type IS NULL OR doc_type = '' "
                          "OR doc_type = 'other'"))


MIGRATIONS = {
    2: _v2_invoice_processing,
    3: _v3_tally,
    4: _v4_invoice_pages,
    5: _v5_reconciliation,
    6: _v6_backups,
    7: _v7_supplier_layouts,
    8: _v8_doc_type_default,
}
LATEST = max(MIGRATIONS)


def backup_before_migrate(db_file: Path | None) -> Path | None:
    if db_file is None or not db_file.exists():
        return None
    target = db_file.with_name(f"{db_file.stem}.before-migration-{datetime.now():%Y%m%d-%H%M%S}{db_file.suffix}")
    shutil.copy2(db_file, target)
    log.info("Database backed up to %s before migration", target)
    return target
