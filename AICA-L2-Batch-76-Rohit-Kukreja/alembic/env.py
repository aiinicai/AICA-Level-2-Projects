"""Alembic environment. Reads the URL from settings, never from alembic.ini."""

from __future__ import annotations

import contextlib
from logging.config import fileConfig

from alembic import context
from app.db import Base, build_engine

# Importing the model packages registers them on Base.metadata so that
# `alembic revision --autogenerate` sees every table. Phase 4 adds these.
with contextlib.suppress(ImportError):  # pragma: no cover
    import app.models

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _set_foreign_keys(connection, *, on: bool) -> None:
    """Toggle SQLite FK enforcement without starting a transaction.

    The PRAGMA goes straight to the DBAPI connection. `_fix_pysqlite_transactions`
    leaves the driver in autocommit and emits BEGIN on SQLAlchemy's "begin"
    event, so anything routed through the SQLAlchemy Connection would open a
    transaction here and swallow the migration's DDL.
    """
    connection.connection.driver_connection.execute(f"PRAGMA foreign_keys={'ON' if on else 'OFF'}")


def run_migrations_offline() -> None:
    engine = build_engine()
    context.configure(
        url=str(engine.url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = build_engine()
    with engine.connect() as connection:
        sqlite = connection.dialect.name == "sqlite"

        # SQLite batch mode alters a table by building a replacement, copying
        # the rows across, dropping the original and renaming. `app.db` turns
        # on `PRAGMA foreign_keys` for every SQLite connection, and with it on
        # that copy trips "FOREIGN KEY constraint failed" the moment the table
        # has any child rows.
        #
        # It therefore succeeds on an empty development database and fails on
        # every populated one — the same trap as a NOT NULL column with no
        # server default, and just as invisible until someone runs it for real.
        # Enforcement is restored below whatever happens.
        #
        # ISSUED ON THE RAW DRIVER CONNECTION, DELIBERATELY. Going through
        # `connection.exec_driver_sql` instead fires SQLAlchemy's "begin"
        # event, and `app.db._fix_pysqlite_transactions` answers that by
        # emitting BEGIN itself. Alembic's own `begin_transaction()` then
        # nests inside a transaction it does not own, and every CREATE TABLE
        # is rolled back when the connection closes — migrations report
        # success and the database stays empty. Verified: 21 tables become 0.
        if sqlite:
            _set_foreign_keys(connection, on=False)

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # SQLite cannot ALTER most things in place; batch mode rewrites the
            # table instead. Keeps the same migration working on PostgreSQL.
            render_as_batch=sqlite,
            compare_type=True,
        )
        try:
            with context.begin_transaction():
                context.run_migrations()
        finally:
            if sqlite:
                _set_foreign_keys(connection, on=True)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
