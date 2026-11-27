"""Local SQLite store. One file, no server.

Three tables:
  clients         latest inputs and business working per client
  trial_balances  the uploaded trial balance file and the ledger classification per client
  estimates       a dated history row every time a client is saved

The database folder is `data/` inside the project by default. It can be moved
(for example to an office drive) from the sidebar; the choice is kept in
`settings.json`, which is not committed to Git. The environment variable
ADVTAX_DATA_DIR overrides both.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIR = ROOT / "data"
SETTINGS_PATH = ROOT / "settings.json"
DB_NAME = "advance_tax.db"


# ------------------------------------------------------------------ location
def data_dir() -> Path:
    env = os.environ.get("ADVTAX_DATA_DIR")
    if env:
        return Path(env).expanduser()
    if SETTINGS_PATH.exists():
        try:
            saved = json.loads(SETTINGS_PATH.read_text(encoding="utf-8")).get("data_dir")
            if saved:
                return Path(saved).expanduser()
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_DIR


def set_data_dir(path: str) -> Path:
    """Point the app at another folder. Creates it and checks it is writable."""
    folder = Path(path.strip().strip('"')).expanduser()
    if not folder.is_absolute():
        raise ValueError("Give the full folder path, for example D:\\OfficeData\\AdvanceTax")
    folder.mkdir(parents=True, exist_ok=True)
    probe = folder / ".write_test"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink()
    SETTINGS_PATH.write_text(json.dumps({"data_dir": str(folder)}, indent=2), encoding="utf-8")
    return folder


def reset_data_dir() -> None:
    if SETTINGS_PATH.exists():
        SETTINGS_PATH.unlink()


def db_path() -> Path:
    return data_dir() / DB_NAME


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(path) if path else db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=15)
    con.row_factory = sqlite3.Row
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            inputs TEXT NOT NULL,
            working TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS trial_balances (
            client_name TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            data BLOB NOT NULL,
            meta TEXT NOT NULL DEFAULT '{}',
            ledgers TEXT NOT NULL,
            saved_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS estimates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            saved_at TEXT NOT NULL,
            as_on TEXT NOT NULL,
            inputs TEXT NOT NULL,
            working TEXT NOT NULL DEFAULT '{}',
            summary TEXT NOT NULL DEFAULT '{}',
            message TEXT NOT NULL DEFAULT '',
            explanation TEXT NOT NULL DEFAULT '');
        CREATE INDEX IF NOT EXISTS idx_estimates_client ON estimates (client_name, id);
        """
    )
    return con


# ------------------------------------------------------------------- clients
def save_client(con: sqlite3.Connection, name: str, inputs: dict, working: dict | None = None) -> None:
    con.execute(
        """INSERT INTO clients (name, inputs, working, updated_at) VALUES (?, ?, ?, ?)
           ON CONFLICT(name) DO UPDATE SET inputs=excluded.inputs, working=excluded.working,
           updated_at=excluded.updated_at""",
        (name.strip(), json.dumps(inputs), json.dumps(working or {}), _now()),
    )
    con.commit()


def _client(r: sqlite3.Row) -> dict:
    return {"id": r["id"], "name": r["name"], "inputs": json.loads(r["inputs"]),
            "working": json.loads(r["working"]), "updated_at": r["updated_at"]}


def list_clients(con: sqlite3.Connection) -> list[dict]:
    return [_client(r) for r in con.execute("SELECT * FROM clients ORDER BY name COLLATE NOCASE").fetchall()]


def get_client(con: sqlite3.Connection, name: str) -> dict | None:
    r = con.execute("SELECT * FROM clients WHERE name = ?", (name,)).fetchone()
    return _client(r) if r else None


def delete_client(con: sqlite3.Connection, name: str) -> None:
    """Remove the client together with its trial balance and history."""
    con.execute("DELETE FROM clients WHERE name = ?", (name,))
    con.execute("DELETE FROM trial_balances WHERE client_name = ?", (name,))
    con.execute("DELETE FROM estimates WHERE client_name = ?", (name,))
    con.commit()


# ------------------------------------------------------------ trial balances
def save_trial_balance(con: sqlite3.Connection, name: str, filename: str, data: bytes, meta: dict,
                       ledgers: list[dict]) -> None:
    con.execute(
        """INSERT INTO trial_balances (client_name, filename, data, meta, ledgers, saved_at)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(client_name) DO UPDATE SET filename=excluded.filename, data=excluded.data,
           meta=excluded.meta, ledgers=excluded.ledgers, saved_at=excluded.saved_at""",
        (name.strip(), filename, sqlite3.Binary(data), json.dumps(meta, default=str), json.dumps(ledgers), _now()),
    )
    con.commit()


def get_trial_balance(con: sqlite3.Connection, name: str) -> dict | None:
    r = con.execute("SELECT * FROM trial_balances WHERE client_name = ?", (name,)).fetchone()
    if not r:
        return None
    return {"filename": r["filename"], "data": bytes(r["data"]), "meta": json.loads(r["meta"]),
            "ledgers": json.loads(r["ledgers"]), "saved_at": r["saved_at"]}


# ------------------------------------------------------------------- history
def save_estimate(con: sqlite3.Connection, name: str, as_on: str, inputs: dict, working: dict, summary: dict,
                  message: str = "", explanation: str = "") -> int:
    cur = con.execute(
        """INSERT INTO estimates (client_name, saved_at, as_on, inputs, working, summary, message, explanation)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (name.strip(), _now(), as_on, json.dumps(inputs), json.dumps(working), json.dumps(summary, default=str),
         message, explanation),
    )
    con.commit()
    return int(cur.lastrowid)


def _estimate(r: sqlite3.Row) -> dict:
    return {"id": r["id"], "client_name": r["client_name"], "saved_at": r["saved_at"], "as_on": r["as_on"],
            "inputs": json.loads(r["inputs"]), "working": json.loads(r["working"]),
            "summary": json.loads(r["summary"]), "message": r["message"], "explanation": r["explanation"]}


def list_estimates(con: sqlite3.Connection, name: str) -> list[dict]:
    """Newest first."""
    rows = con.execute("SELECT * FROM estimates WHERE client_name = ? ORDER BY id DESC", (name,)).fetchall()
    return [_estimate(r) for r in rows]


def get_estimate(con: sqlite3.Connection, estimate_id: int) -> dict | None:
    r = con.execute("SELECT * FROM estimates WHERE id = ?", (estimate_id,)).fetchone()
    return _estimate(r) if r else None


def counts(con: sqlite3.Connection) -> dict:
    return {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("clients", "trial_balances", "estimates")}
