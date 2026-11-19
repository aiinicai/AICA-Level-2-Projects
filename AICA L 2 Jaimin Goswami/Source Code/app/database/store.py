from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3

from app.utils.paths import resource_path
from app.utils.time import stamp


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.migrate()

    def connect(self):
        conn = sqlite3.connect(self.path, timeout=20)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=20000")
        return conn

    @contextmanager
    def transaction(self):
        conn = self.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def migrate(self):
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version TEXT PRIMARY KEY,applied_at TEXT NOT NULL)")
            versions = {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}
            for file in sorted(resource_path("migrations").glob("*.sql")):
                if file.name not in versions:
                    # executescript commits before executing: explicitly wrap the entire migration.
                    sql = file.read_text(encoding="utf-8")
                    version = file.name.replace("'", "''")
                    conn.executescript(f"BEGIN IMMEDIATE;\n{sql}\nINSERT INTO schema_migrations VALUES('{version}','{stamp()}');\nCOMMIT;")

    def rows(self, sql, params=()):
        with self.connect() as conn:
            return [dict(row) for row in conn.execute(sql, params)]

    def execute(self, sql, params=()):
        with self.transaction() as conn:
            return conn.execute(sql, params).lastrowid

    def setting(self, key, default=None):
        rows = self.rows("SELECT value FROM user_settings WHERE key=?", (key,))
        return json.loads(rows[0]["value"]) if rows else default

    def set_setting(self, key, value):
        self.execute("INSERT INTO user_settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(value)))

    def backup(self, target):
        if Path(target).resolve() == self.path.resolve():
            raise ValueError("Choose a backup path different from the active database")
        with self.connect() as source, sqlite3.connect(target) as dest:
            source.backup(dest)

