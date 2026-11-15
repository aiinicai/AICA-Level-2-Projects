"""The in-memory database. Nothing here ever touches the disk, and `wipe()` removes everything."""
from __future__ import annotations

import gc
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

import duckdb
import pyarrow as pa

from .schema import COLUMNS, TABLES, create_sql

_ARROW = {"BIGINT": pa.int64(), "VARCHAR": pa.string(), "DOUBLE": pa.float64()}
_SCHEMAS = {t: pa.schema([(c, _ARROW[ty]) for c, ty in cols]) for t, cols in TABLES.items()}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self._open()

    def _open(self) -> None:
        self.con = duckdb.connect(":memory:")
        # No temp files: if a query ever needs more memory than allowed it fails instead of spilling to disk.
        self.con.execute("SET temp_directory = ''")
        self.con.execute("SET threads = 4")
        for stmt in create_sql():
            self.con.execute(stmt)
        self.con.execute("SET enable_external_access = false")  # SQL can no longer read or write any file
        self._ids: dict[str, int] = {}
        self.names: dict[tuple[str, int], dict[str, int]] = {}  # (table, company) -> name -> id
        self.data_version: dict[int, int] = {}
        self.closed = False

    # ---------------------------------------------------------------- basic access
    def execute(self, sql: str, params: list | tuple = ()) -> None:
        with self.lock:
            self.con.execute(sql, list(params))

    def rows(self, sql: str, params: list | tuple = ()) -> list[dict]:
        with self.lock:
            cur = self.con.execute(sql, list(params))
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]

    def one(self, sql: str, params: list | tuple = ()) -> dict | None:
        r = self.rows(sql, params)
        return r[0] if r else None

    def scalar(self, sql: str, params: list | tuple = ()):
        with self.lock:
            r = self.con.execute(sql, list(params)).fetchone()
            return r[0] if r else None

    @contextmanager
    def transaction(self):
        with self.lock:
            self.con.execute("BEGIN")
            try:
                yield
            except BaseException:
                self.con.execute("ROLLBACK")
                raise
            else:
                self.con.execute("COMMIT")

    # ---------------------------------------------------------------- bulk loading (Apache Arrow: ~100x faster than SQL rows)
    def insert(self, table: str, rows: list[tuple]) -> None:
        if not rows:
            return
        cols = list(zip(*rows))
        tbl = pa.table(dict(zip(COLUMNS[table], cols)), schema=_SCHEMAS[table])
        with self.lock:
            self.con.register("_incoming", tbl)
            try:
                self.con.execute(f"INSERT INTO {table} SELECT * FROM _incoming")
            finally:
                self.con.unregister("_incoming")

    @contextmanager
    def register(self, name: str, columns: list[str], rows: list[tuple]):
        """Expose Python rows to SQL for the duration of a statement, e.g. UPDATE ... FROM name."""
        data = {c: list(v) for c, v in zip(columns, zip(*rows))} if rows else {c: [] for c in columns}
        with self.lock:
            self.con.register(name, pa.table(data))
            try:
                yield
            finally:
                self.con.unregister(name)

    def delete_where_in(self, table: str, column: str, values: list, extra: str = "", params: list = ()) -> None:
        """DELETE FROM table WHERE column IN (values) [AND extra]."""
        if not values:
            return
        arrow = pa.table({"v": pa.array(values)})
        with self.lock:
            self.con.register("_keys", arrow)
            try:
                self.con.execute(f"DELETE FROM {table} WHERE {column} IN (SELECT v FROM _keys)" + (f" AND ({extra})" if extra else ""),
                                 list(params))
            finally:
                self.con.unregister("_keys")

    def ids_where_in(self, table: str, column: str, values: list, extra: str = "", params: list = ()) -> list[int]:
        if not values:
            return []
        arrow = pa.table({"v": pa.array(values)})
        with self.lock:
            self.con.register("_keys", arrow)
            try:
                return [r[0] for r in self.con.execute(
                    f"SELECT id FROM {table} WHERE {column} IN (SELECT v FROM _keys)" + (f" AND ({extra})" if extra else ""),
                    list(params)).fetchall()]
            finally:
                self.con.unregister("_keys")

    # ---------------------------------------------------------------- ids and names
    def next_id(self, table: str) -> int:
        with self.lock:
            self._ids[table] = self._ids.get(table, 0) + 1
            return self._ids[table]

    def name_map(self, table: str, company_id: int) -> dict[str, int]:
        return self.names.setdefault((table, company_id), {})

    def bump(self, company_id: int) -> None:
        self.data_version[company_id] = self.data_version.get(company_id, 0) + 1

    # ---------------------------------------------------------------- companies
    def ensure_company(self, name: str, *, is_demo: bool = False, books_from: str | None = None) -> int:
        with self.lock:
            ex = self.one("SELECT id FROM companies WHERE source_name = ? AND is_demo = ?", [name, int(is_demo)])
            if ex:
                if books_from:
                    self.execute("UPDATE companies SET books_from = COALESCE(books_from, ?) WHERE id = ?", [books_from, ex["id"]])
                return ex["id"]
            cid = self.next_id("companies")
            self.insert("companies", [(cid, name, name, None, int(is_demo), 4, books_from, "INR", "trading", "auto", "{}", now_iso())])
            return cid

    def counts(self) -> dict[str, int]:
        with self.lock:
            return {t: self.con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES}

    # ---------------------------------------------------------------- wipe
    def wipe(self) -> None:
        """Remove all company data: drop every table, close the database, and release the memory."""
        with self.lock:
            if self.closed:
                return
            try:
                for t in TABLES:
                    self.con.execute(f"DROP TABLE IF EXISTS {t}")
            finally:
                self.con.close()
            self.names.clear()
            self._ids.clear()
            self.data_version.clear()
            self.closed = True
        gc.collect()

    def reset(self) -> None:
        """Wipe and start again with an empty database."""
        self.wipe()
        with self.lock:
            self._open()
