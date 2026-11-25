"""Minimal 4-table SQLite database layer for the Windows v0 Edition."""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Any, Generator, Optional

from app import config

CATEGORY_PREFIXES = {
    "FURNITURE": "FURN",
    "IT_HARDWARE": "IT",
    "ELECTRICAL": "ELEC",
    "OFFICE_FIXTURES": "FIXT",
    "MACHINERY": "MACH",
}

CYCLE_DAYS = {
    "MONTHLY": 30,
    "QUARTERLY": 90,
    "BI_ANNUAL": 180,
    "ANNUAL": 365,
    "AS_NEEDED": None,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


def calculate_next_maintenance_date(cycle: str, base_date: Optional[str] = None) -> Optional[str]:
    days = CYCLE_DAYS.get(cycle)
    if days is None:
        return None
    if base_date:
        try:
            ref = date.fromisoformat(base_date[:10])
        except ValueError:
            ref = date.today()
    else:
        ref = date.today()
    return (ref + timedelta(days=days)).isoformat()


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(config.DB_PATH), check_same_thread=False, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    config.ensure_directories()
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS vendors (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                vendor_type TEXT NOT NULL,
                contact_person TEXT,
                phone TEXT NOT NULL,
                email TEXT,
                address TEXT,
                notes TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS assets (
                id TEXT PRIMARY KEY,
                asset_tag TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                location TEXT NOT NULL,
                purchase_date TEXT,
                purchase_cost REAL,
                vendor_id TEXT REFERENCES vendors(id) ON DELETE SET NULL,
                warranty_end_date TEXT,
                maintenance_cycle TEXT NOT NULL DEFAULT 'QUARTERLY',
                last_maintenance_date TEXT,
                next_maintenance_date TEXT,
                status TEXT NOT NULL DEFAULT 'OPERATIONAL',
                photos TEXT DEFAULT '[]',
                notes TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS maintenance_records (
                id TEXT PRIMARY KEY,
                asset_id TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
                vendor_id TEXT REFERENCES vendors(id) ON DELETE SET NULL,
                scheduled_date TEXT NOT NULL,
                completed_date TEXT,
                cost REAL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'SCHEDULED',
                photos TEXT DEFAULT '[]',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS recurring_consumables (
                id TEXT PRIMARY KEY,
                item_name TEXT NOT NULL,
                category TEXT NOT NULL,
                current_stock INTEGER NOT NULL DEFAULT 0,
                unit TEXT NOT NULL,
                minimum_reorder_threshold INTEGER NOT NULL DEFAULT 5,
                preferred_vendor_id TEXT REFERENCES vendors(id) ON DELETE SET NULL,
                last_restocked_date TEXT,
                created_at TEXT NOT NULL
            );
            """
        )


def generate_next_asset_tag(conn: sqlite3.Connection, category: str) -> str:
    prefix = f"AST-{CATEGORY_PREFIXES.get(category, 'GEN')}-"
    rows = conn.execute("SELECT asset_tag FROM assets WHERE asset_tag LIKE ?", (f"{prefix}%",)).fetchall()
    max_num = 0
    for row in rows:
        suffix = row["asset_tag"][len(prefix):]
        if suffix.isdigit():
            max_num = max(max_num, int(suffix))
    return f"{prefix}{max_num + 1:03d}"


def parse_json_list(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    try:
        val = json.loads(raw)
        return val if isinstance(val, list) else []
    except (ValueError, TypeError):
        return []
