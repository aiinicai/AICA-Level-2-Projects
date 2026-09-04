"""
Alembic environment script.

Points at app.models.Base.metadata (the single source of truth for the
schema — see app/models/__init__.py) and at config.Config for the DB URL,
so there is exactly one schema definition and one DB-path definition in
the whole project; this file never hardcodes either.

FINSIGHT_ALEMBIC_DB_URL, if set, overrides Config.SQLALCHEMY_DATABASE_URI
— used ONLY by tests/unit/test_migration.py so it can run a real
`alembic upgrade head` against a throwaway temp-file database instead of
the real application database. Unset in normal `alembic upgrade head`
usage, where Config.SQLALCHEMY_DATABASE_URI is used as before.
"""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config import Config  # noqa: E402
from app.models import Base  # noqa: E402  (imports every model so metadata is complete)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

db_url = os.environ.get("FINSIGHT_ALEMBIC_DB_URL", Config.SQLALCHEMY_DATABASE_URI)
config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
