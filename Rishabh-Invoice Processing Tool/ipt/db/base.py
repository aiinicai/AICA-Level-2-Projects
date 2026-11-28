"""Database engine, sessions and declarative base.

SQLite for local deployment; models avoid SQLite-only features so a
PostgreSQL URL can be used later. Foreign keys are enforced.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker



class Base(DeclarativeBase):
    pass


class Database:
    def __init__(self, url: str):
        self.url = url
        connect_args = {"check_same_thread": False, "timeout": 30} if url.startswith("sqlite") else {}
        self.engine: Engine = create_engine(url, future=True, connect_args=connect_args)
        if url.startswith("sqlite"):
            @event.listens_for(self.engine, "connect")
            def _sqlite_pragmas(dbapi_conn, _record):  # pragma: no cover - trivial
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA foreign_keys=ON")
                cur.execute("PRAGMA journal_mode=WAL")
                cur.close()
        self._factory = sessionmaker(self.engine, expire_on_commit=False)

    @classmethod
    def for_file(cls, path: Path) -> "Database":
        return cls(f"sqlite:///{path}")

    def file_path(self) -> Path | None:
        prefix = "sqlite:///"
        return Path(self.url[len(prefix):]) if self.url.startswith(prefix) else None

    def create_schema(self) -> None:
        """Create a new database, or upgrade an existing one to the latest version."""
        from ipt.db import migrations, models
        with self.session() as s:
            fresh = not self.engine.dialect.has_table(s.connection(), "schema_version")
        if fresh:
            Base.metadata.create_all(self.engine)
            with self.session() as s:
                s.add(models.SchemaVersion(id=1, version=migrations.LATEST))
            return
        with self.session() as s:
            row = s.get(models.SchemaVersion, 1)
            current = row.version if row else 1
        if current >= migrations.LATEST:
            Base.metadata.create_all(self.engine)  # safety: create any missing table
            return
        migrations.backup_before_migrate(self.file_path())
        for version in range(current + 1, migrations.LATEST + 1):
            migrations.MIGRATIONS[version](self.engine)
            with self.session() as s:
                s.get(models.SchemaVersion, 1).version = version

    @contextmanager
    def session(self) -> Iterator[Session]:
        s = self._factory()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()
