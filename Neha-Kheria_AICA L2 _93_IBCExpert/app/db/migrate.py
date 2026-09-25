"""Checksum-protected, transactional schema migration runner."""
from __future__ import annotations

import hashlib
import importlib
import pkgutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.errors import IntegrityError, StorageError
from app.db.connection import transaction
from app.db import migrations as migration_package


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    sql: str
    checksum: str


def discover_migrations() -> list[Migration]:
    found: list[Migration] = []
    prefix = migration_package.__name__ + "."
    for info in pkgutil.iter_modules(migration_package.__path__, prefix):
        leaf = info.name.rsplit(".", 1)[-1]
        if not leaf.startswith("m"):
            continue
        module = importlib.import_module(info.name)
        sql = str(module.SQL).strip()
        checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        found.append(Migration(int(module.VERSION), str(module.NAME), sql, checksum))
    found.sort(key=lambda migration: migration.version)
    versions = [migration.version for migration in found]
    if versions != list(range(1, len(versions) + 1)):
        raise StorageError("Database migrations are missing or out of sequence.")
    return found


def _ensure_history(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            checksum TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )


def migrate(connection: sqlite3.Connection, target: int | None = None) -> int:
    _ensure_history(connection)
    migrations = discover_migrations()
    if target is None:
        target = migrations[-1].version if migrations else 0
    known = {m.version: m for m in migrations}
    if target not in range(0, (migrations[-1].version if migrations else 0) + 1):
        raise StorageError("Requested database schema version is unavailable.")

    applied_rows = connection.execute(
        "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
    ).fetchall()
    for row in applied_rows:
        migration = known.get(int(row["version"]))
        if migration is None or row["name"] != migration.name or row["checksum"] != migration.checksum:
            raise IntegrityError("Database migration history has been altered or is incompatible.")

    current = int(applied_rows[-1]["version"]) if applied_rows else 0
    for migration in migrations:
        if migration.version <= current or migration.version > target:
            continue
        try:
            with transaction(connection):
                # executescript has implicit transaction behavior, so execute each complete
                # statement using SQLite's parser. Migration SQL contains no semicolons in strings.
                statement = ""
                for line in migration.sql.splitlines():
                    statement += line + "\n"
                    if sqlite3.complete_statement(statement):
                        connection.execute(statement)
                        statement = ""
                if statement.strip():
                    raise StorageError(f"Migration {migration.version} contains incomplete SQL.")
                connection.execute(
                    "INSERT INTO schema_migrations(version,name,checksum,applied_at) VALUES(?,?,?,?)",
                    (
                        migration.version,
                        migration.name,
                        migration.checksum,
                        datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    ),
                )
        except sqlite3.Error as exc:
            raise StorageError(f"Database migration {migration.version} failed.") from exc
        current = migration.version
    connection.execute(f"PRAGMA user_version = {current}")
    return current
