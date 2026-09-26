"""Data-access layer. All SQL lives here; services never write SQL."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

from app.database.database import Database, utc_now


def _rows(cur) -> list[dict[str, Any]]:
    return [dict(r) for r in cur.fetchall()]


class SettingsRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get_all(self) -> dict[str, Any]:
        with self.db.session() as conn:
            rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
        return {r["key"]: json.loads(r["value"]) for r in rows}

    def save_all(self, values: dict[str, Any]) -> None:
        now = utc_now()
        with self.db.session() as conn:
            conn.executemany(
                "INSERT INTO app_settings(key, value, updated_at) VALUES(?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                [(k, json.dumps(v, default=str), now) for k, v in values.items()],
            )


@dataclass
class MasterRecord:
    name: str
    parent: str | None = None
    extra: dict[str, Any] | None = None


class MasterRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def replace(self, company: str, master_type: str, records: Iterable[MasterRecord]) -> int:
        now = utc_now()
        unique: dict[str, MasterRecord] = {}
        for rec in records:
            if rec.name and rec.name.strip():
                unique.setdefault(rec.name.strip().lower(), rec)
        with self.db.session() as conn:
            conn.execute("DELETE FROM tally_masters WHERE company = ? AND master_type = ?", (company, master_type))
            conn.executemany(
                "INSERT INTO tally_masters(company, master_type, name, name_key, parent, extra_json, synced_at) "
                "VALUES(?, ?, ?, ?, ?, ?, ?)",
                [
                    (company, master_type, r.name.strip(), key, r.parent,
                     json.dumps(r.extra) if r.extra else None, now)
                    for key, r in unique.items()
                ],
            )
        return len(unique)

    def all(self, company: str, master_type: str) -> list[dict[str, Any]]:
        with self.db.session() as conn:
            return _rows(conn.execute(
                "SELECT name, parent, extra_json, synced_at FROM tally_masters "
                "WHERE company = ? AND master_type = ? ORDER BY name COLLATE NOCASE",
                (company, master_type),
            ))

    def search(self, company: str, master_type: str, query: str, limit: int = 200) -> list[dict[str, Any]]:
        with self.db.session() as conn:
            return _rows(conn.execute(
                "SELECT name, parent, synced_at FROM tally_masters "
                "WHERE company = ? AND master_type = ? AND name_key LIKE ? ORDER BY name COLLATE NOCASE LIMIT ?",
                (company, master_type, f"%{query.lower()}%", limit),
            ))

    def counts(self, company: str) -> dict[str, dict[str, Any]]:
        with self.db.session() as conn:
            rows = conn.execute(
                "SELECT master_type, COUNT(*) AS n, MAX(synced_at) AS synced_at FROM tally_masters "
                "WHERE company = ? GROUP BY master_type",
                (company,),
            ).fetchall()
        return {r["master_type"]: {"count": r["n"], "synced_at": r["synced_at"]} for r in rows}

    def log_sync(self, company: str, master_type: str, count: int, status: str, message: str = "") -> None:
        with self.db.session() as conn:
            conn.execute(
                "INSERT INTO master_sync_log(synced_at, company, master_type, count, status, message) "
                "VALUES(?, ?, ?, ?, ?, ?)",
                (utc_now(), company, master_type, count, status, message),
            )


class BatchRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create(self, batch: dict[str, Any]) -> None:
        cols = ", ".join(batch)
        marks = ", ".join("?" for _ in batch)
        with self.db.session() as conn:
            conn.execute(f"INSERT INTO import_batches({cols}) VALUES({marks})", tuple(batch.values()))

    def get(self, batch_id: str) -> dict[str, Any] | None:
        with self.db.session() as conn:
            row = conn.execute("SELECT * FROM import_batches WHERE id = ?", (batch_id,)).fetchone()
        return dict(row) if row else None

    def update(self, batch_id: str, **fields: Any) -> None:
        sets = ", ".join(f"{k} = ?" for k in fields)
        with self.db.session() as conn:
            conn.execute(f"UPDATE import_batches SET {sets} WHERE id = ?", (*fields.values(), batch_id))


_HISTORY_COLUMNS = (
    "batch_id", "created_at", "company_name", "tally_company", "financial_year", "voucher_kind",
    "voucher_numbers", "excel_file_name", "xml_file_name", "record_count", "tally_status",
    "created_count", "altered_count", "ignored_count", "error_count", "tally_response",
    "error_details", "demo_mode",
)


class HistoryRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, entry: dict[str, Any], posted: list[dict[str, Any]]) -> int:
        """Insert a history row and the vouchers Tally confirmed, atomically."""
        entry = {"created_at": utc_now(), **entry}
        values = tuple(entry.get(c) for c in _HISTORY_COLUMNS)
        with self.db.session() as conn:
            cur = conn.execute(
                f"INSERT INTO import_history({', '.join(_HISTORY_COLUMNS)}) "
                f"VALUES({', '.join('?' for _ in _HISTORY_COLUMNS)})",
                values,
            )
            history_id = int(cur.lastrowid)
            conn.executemany(
                "INSERT INTO posted_vouchers(history_id, company, financial_year, voucher_kind, exact_key, "
                "fuzzy_key, voucher_label, voucher_date, party_ledger, amount, posted_at) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (history_id, p["company"], p["financial_year"], p["voucher_kind"], p["exact_key"],
                     p["fuzzy_key"], p["voucher_label"], p["voucher_date"], p["party_ledger"],
                     p["amount"], entry["created_at"])
                    for p in posted
                ],
            )
        return history_id

    def search(self, *, q: str = "", kind: str = "", status: str = "", date_from: str = "",
               date_to: str = "", limit: int = 200) -> list[dict[str, Any]]:
        sql = "SELECT * FROM import_history WHERE 1=1"
        args: list[Any] = []
        if kind:
            sql += " AND voucher_kind = ?"
            args.append(kind)
        if status:
            sql += " AND tally_status = ?"
            args.append(status.upper())
        if date_from:
            sql += " AND substr(created_at, 1, 10) >= ?"
            args.append(date_from)
        if date_to:
            sql += " AND substr(created_at, 1, 10) <= ?"
            args.append(date_to)
        if q:
            sql += (" AND (voucher_numbers LIKE ? OR excel_file_name LIKE ? OR company_name LIKE ? "
                    "OR tally_response LIKE ? OR error_details LIKE ?)")
            args.extend([f"%{q}%"] * 5)
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        with self.db.session() as conn:
            return _rows(conn.execute(sql, args))

    def get(self, history_id: int) -> dict[str, Any] | None:
        with self.db.session() as conn:
            row = conn.execute("SELECT * FROM import_history WHERE id = ?", (history_id,)).fetchone()
        return dict(row) if row else None

    def stats(self) -> dict[str, int]:
        with self.db.session() as conn:
            rows = conn.execute(
                "SELECT tally_status, COUNT(*) AS n FROM import_history GROUP BY tally_status"
            ).fetchall()
        return {r["tally_status"]: r["n"] for r in rows}

    # ---- duplicate lookups -------------------------------------------------
    def find_exact(self, company: str, keys: list[str]) -> dict[str, dict[str, Any]]:
        return self._find(company, "exact_key", keys)

    def find_fuzzy(self, company: str, keys: list[str]) -> dict[str, dict[str, Any]]:
        return self._find(company, "fuzzy_key", keys)

    def _find(self, company: str, column: str, keys: list[str]) -> dict[str, dict[str, Any]]:
        keys = [k for k in set(keys) if k]
        if not keys:
            return {}
        found: dict[str, dict[str, Any]] = {}
        with self.db.session() as conn:
            for i in range(0, len(keys), 500):
                chunk = keys[i:i + 500]
                rows = conn.execute(
                    f"SELECT * FROM posted_vouchers WHERE company = ? AND {column} IN "
                    f"({', '.join('?' for _ in chunk)})",
                    (company, *chunk),
                ).fetchall()
                for r in rows:
                    found.setdefault(r[column], dict(r))
        return found


class AuditRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, action: str, *, company_name: str = "", voucher_kind: str = "",
            batch_id: str = "", details: dict[str, Any] | str | None = None) -> None:
        text = details if isinstance(details, str) or details is None else json.dumps(details, default=str)
        with self.db.session() as conn:
            conn.execute(
                "INSERT INTO audit_log(created_at, action, company_name, voucher_kind, batch_id, details) "
                "VALUES(?, ?, ?, ?, ?, ?)",
                (utc_now(), action, company_name, voucher_kind, batch_id, text),
            )

    def search(self, *, q: str = "", action: str = "", limit: int = 300) -> list[dict[str, Any]]:
        sql = "SELECT * FROM audit_log WHERE 1=1"
        args: list[Any] = []
        if action:
            sql += " AND action = ?"
            args.append(action)
        if q:
            sql += " AND (details LIKE ? OR batch_id LIKE ? OR voucher_kind LIKE ?)"
            args.extend([f"%{q}%"] * 3)
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        with self.db.session() as conn:
            return _rows(conn.execute(sql, args))
