"""
db.py — SQLite persistence layer with multi-company support.

Each of the app's 11 data tables (settings, products, nozzles, customers,
banks, bowsers, dailyEntries, receipts, expenses, payments, deposits) is
stored as ONE JSON blob per (company_id, key) pair — this mirrors the
original 'pp_<key>' localStorage scheme per company, so the web app's own
logic (loadDB/saveKey/migrateDB) needs no rewrite, only its storage calls
redirected here, scoped to whichever company is currently open.

The database file lives in the user's per-machine app-data folder so it
persists across app updates/reinstalls:
  C:\\Users\\<user>\\AppData\\Local\\Petrosuite\\skp_gst.db
"""
import json
import os
import shutil
import sqlite3
from datetime import datetime, timezone

LS_KEYS = [
    "settings", "products", "nozzles", "customers", "banks", "bowsers",
    "dailyEntries", "receipts", "expenses", "payments", "deposits",
]


def default_data_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "Petrosuite")
    os.makedirs(path, exist_ok=True)

    # One-time migration: earlier builds used the folder name "PetroleumSuite"
    # before the app was renamed to Petrosuite. If that old folder's database
    # exists and the new one doesn't yet, carry it forward automatically so
    # no existing company/data is orphaned by the rename.
    new_db = os.path.join(path, "skp_gst.db")
    old_dir = os.path.join(base, "PetroleumSuite")
    old_db = os.path.join(old_dir, "skp_gst.db")
    if not os.path.exists(new_db) and os.path.exists(old_db):
        try:
            shutil.copy2(old_db, new_db)
            for ext in ("-wal", "-shm"):
                if os.path.exists(old_db + ext):
                    shutil.copy2(old_db + ext, new_db + ext)
        except Exception as e:
            print(f"[db] Could not migrate old PetroleumSuite data folder: {e}")

    return path


class Database:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(default_data_dir(), "skp_gst.db")
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA foreign_keys=ON;")
        self._init_schema()

    def _init_schema(self):
        cur = self.conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS license (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                machine_id TEXT,
                activation_key TEXT,
                activated_at TEXT
            )
        """)

        # Detect a pre-multi-company kv_store (single-company installs from
        # earlier builds) and migrate it forward instead of losing data.
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='kv_store'")
        existing_kv = cur.fetchone() is not None
        needs_migration = False
        if existing_kv:
            cur.execute("PRAGMA table_info(kv_store)")
            cols = [row[1] for row in cur.fetchall()]
            needs_migration = "company_id" not in cols

        if needs_migration:
            cur.execute("ALTER TABLE kv_store RENAME TO kv_store_legacy")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS kv_store (
                company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                key        TEXT NOT NULL,
                value      TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (company_id, key)
            )
        """)
        self.conn.commit()

        if needs_migration:
            self._migrate_legacy_single_company(cur)

    def _migrate_legacy_single_company(self, cur):
        """One-time migration: any data from a pre-multi-company install is
        moved into a new company named after the old settings.companyName
        (or 'Company 1' if that isn't set), so existing users don't lose
        their data when upgrading to this version."""
        cur.execute("SELECT key, value FROM kv_store_legacy")
        rows = cur.fetchall()
        if not rows:
            cur.execute("DROP TABLE kv_store_legacy")
            self.conn.commit()
            return

        company_name = "Company 1"
        for key, value in rows:
            if key == "settings":
                try:
                    settings = json.loads(value)
                    if settings.get("companyName"):
                        company_name = settings["companyName"]
                except (json.JSONDecodeError, TypeError):
                    pass
                break

        now = datetime.now(timezone.utc).isoformat()
        cur.execute(
            "INSERT INTO companies(name, created_at) VALUES (?, ?)",
            (company_name, now),
        )
        company_id = cur.lastrowid
        for key, value in rows:
            cur.execute(
                "INSERT INTO kv_store(company_id, key, value, updated_at) VALUES (?, ?, ?, ?)",
                (company_id, key, value, now),
            )
        cur.execute("DROP TABLE kv_store_legacy")
        self.conn.commit()

    # ---------------- Companies ----------------
    def list_companies(self):
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, created_at FROM companies ORDER BY name COLLATE NOCASE")
        return [{"id": r[0], "name": r[1], "created_at": r[2]} for r in cur.fetchall()]

    def create_company(self, name: str) -> int:
        name = (name or "").strip()
        if not name:
            raise ValueError("Company name cannot be empty")
        now = datetime.now(timezone.utc).isoformat()
        cur = self.conn.cursor()
        cur.execute("INSERT INTO companies(name, created_at) VALUES (?, ?)", (name, now))
        self.conn.commit()
        return cur.lastrowid

    def rename_company(self, company_id: int, new_name: str):
        new_name = (new_name or "").strip()
        if not new_name:
            raise ValueError("Company name cannot be empty")
        self.conn.execute("UPDATE companies SET name=? WHERE id=?", (new_name, company_id))
        self.conn.commit()

    def delete_company(self, company_id: int):
        # ON DELETE CASCADE removes that company's kv_store rows too.
        self.conn.execute("DELETE FROM companies WHERE id=?", (company_id,))
        self.conn.commit()

    # ---------------- App data (kv_store), scoped per company ----------------
    def get_all(self, company_id: int) -> dict:
        """Returns the full DB object shape the web app expects, e.g.
        {'settings': {...}, 'products': [...], ...}, scoped to one company.
        Missing keys are simply absent, matching the original app's own
        defaultDB() + loadDB() merge behaviour (JS side fills defaults for
        anything not present)."""
        cur = self.conn.cursor()
        cur.execute("SELECT key, value FROM kv_store WHERE company_id=?", (company_id,))
        out = {}
        for key, value in cur.fetchall():
            try:
                out[key] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                pass
        return out

    def save_key(self, company_id: int, key: str, value_json: str):
        if key not in LS_KEYS:
            raise ValueError(f"Unknown data key: {key}")
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO kv_store(company_id, key, value, updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(company_id, key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (company_id, key, value_json, now),
        )
        self.conn.commit()

    def remove_all_keys(self, company_id: int):
        """Scoped 'Reset Application' — wipes only the current company's
        data, never other companies sharing this install."""
        self.conn.execute("DELETE FROM kv_store WHERE company_id=?", (company_id,))
        self.conn.commit()

    def import_json_backup(self, company_id: int, backup_json_text: str):
        """Seeds/overwrites one company's kv_store from a legacy exported
        JSON backup (the same file format the original browser app's
        'Export Backup' button produced — an object containing some/all of
        LS_KEYS)."""
        data = json.loads(backup_json_text)
        now = datetime.now(timezone.utc).isoformat()
        cur = self.conn.cursor()
        for key in LS_KEYS:
            if key in data:
                cur.execute(
                    "INSERT INTO kv_store(company_id, key, value, updated_at) VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(company_id, key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                    (company_id, key, json.dumps(data[key]), now),
                )
        self.conn.commit()

    # ---------------- License / activation (per machine, not per company) ----------------
    def get_license(self):
        cur = self.conn.cursor()
        cur.execute("SELECT machine_id, activation_key, activated_at FROM license WHERE id=1")
        row = cur.fetchone()
        if not row:
            return None
        return {"machine_id": row[0], "activation_key": row[1], "activated_at": row[2]}

    def save_license(self, machine_id: str, activation_key: str):
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO license(id, machine_id, activation_key, activated_at) VALUES (1, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET machine_id=excluded.machine_id, "
            "activation_key=excluded.activation_key, activated_at=excluded.activated_at",
            (machine_id, activation_key, now),
        )
        self.conn.commit()

    def close(self):
        self.conn.close()
