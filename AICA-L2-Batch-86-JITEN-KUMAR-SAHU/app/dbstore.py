"""
=============================================================
  ClientLedger India — SQLite Data Store
=============================================================
Replaces the browser's IndexedDB as the single source of truth.
The browser front-end now talks to this via small Flask JSON
routes (see gst_rpa.py, routes mounted under /db/...) instead of
calling indexedDB.open(...) directly.

Two logical "stores" are kept, mirroring the two IndexedDB
databases the app used to keep client-side:

  1. clients            — client master records (autoincrement id,
                           optionally-unique pan / aadhaar / email)
  2. gstin_directory     — supplier GSTIN name-lookup cache
                           (primary key = gstin)

Each record is stored as a JSON blob in a `data` column, exactly
like an IndexedDB record would be — this keeps the schema flexible
(the app can add new client fields without a migration) while a
few columns are pulled out for indexing/uniqueness.

Thread-safety: Flask's dev server (threaded=True) can call these
functions concurrently, so every connection is opened per-call with
a short-lived lock around writes.
"""

import json
import sqlite3
import threading
from datetime import datetime, timezone

_lock = threading.Lock()
_db_path = None


def init(db_path):
    """Call once at startup with the resolved DB file path (see config.Paths)."""
    global _db_path
    _db_path = db_path
    with _connect() as con:
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                pan        TEXT,
                aadhaar    TEXT,
                email      TEXT,
                data       TEXT NOT NULL,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        # Partial unique indexes: only enforce uniqueness when the value is
        # non-empty, matching the practical behaviour of the old IndexedDB
        # unique indexes (which only ever saw one blank value at a time in
        # normal use — this avoids surprising failures on blank fields).
        con.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_clients_pan "
            "ON clients(pan) WHERE pan IS NOT NULL AND pan != ''"
        )
        con.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_clients_aadhaar "
            "ON clients(aadhaar) WHERE aadhaar IS NOT NULL AND aadhaar != ''"
        )
        con.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_clients_email "
            "ON clients(email) WHERE email IS NOT NULL AND email != ''"
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS gstin_directory (
                gstin TEXT PRIMARY KEY,
                data  TEXT NOT NULL
            )
            """
        )
        con.commit()


def _connect():
    if not _db_path:
        raise RuntimeError("dbstore.init(db_path) must be called before use")
    con = sqlite3.connect(_db_path, timeout=10)
    con.row_factory = sqlite3.Row
    return con


def _now():
    return datetime.now(timezone.utc).isoformat()


class DuplicateError(Exception):
    """Raised when a unique field (pan/aadhaar/email) collides, mirroring
    the error IndexedDB's unique index would have thrown."""


# ── clients store ───────────────────────────────────────────────────

def clients_get_all():
    with _connect() as con:
        rows = con.execute("SELECT id, data FROM clients ORDER BY id ASC").fetchall()
    out = []
    for r in rows:
        rec = json.loads(r["data"])
        rec["id"] = r["id"]
        out.append(rec)
    out.reverse()  # match original dbGetAll() which did req.result.reverse()
    return out


def clients_get(rec_id):
    with _connect() as con:
        row = con.execute("SELECT id, data FROM clients WHERE id=?", (rec_id,)).fetchone()
    if not row:
        return None
    rec = json.loads(row["data"])
    rec["id"] = row["id"]
    return rec


def _norm(v):
    return (v or "").strip() if isinstance(v, str) else v


def clients_add(rec):
    rec = dict(rec)
    rec.pop("id", None)
    rec["created_at"] = _now()
    pan, aadhaar, email = _norm(rec.get("pan")), _norm(rec.get("aadhaar")), _norm(rec.get("email"))
    with _lock, _connect() as con:
        try:
            cur = con.execute(
                "INSERT INTO clients (pan, aadhaar, email, data, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?)",
                (pan, aadhaar, email, json.dumps(rec), rec["created_at"], None),
            )
            con.commit()
        except sqlite3.IntegrityError as e:
            raise DuplicateError(str(e))
        new_id = cur.lastrowid
    rec["id"] = new_id
    return new_id


def clients_update(rec):
    rec = dict(rec)
    rec_id = rec.get("id")
    if rec_id is None:
        raise ValueError("record missing id")
    rec["updated_at"] = _now()
    pan, aadhaar, email = _norm(rec.get("pan")), _norm(rec.get("aadhaar")), _norm(rec.get("email"))
    with _lock, _connect() as con:
        exists = con.execute("SELECT 1 FROM clients WHERE id=?", (rec_id,)).fetchone()
        try:
            if exists:
                con.execute(
                    "UPDATE clients SET pan=?, aadhaar=?, email=?, data=?, updated_at=? WHERE id=?",
                    (pan, aadhaar, email, json.dumps(rec), rec["updated_at"], rec_id),
                )
            else:
                con.execute(
                    "INSERT INTO clients (id, pan, aadhaar, email, data, created_at, updated_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (rec_id, pan, aadhaar, email, json.dumps(rec), rec.get("created_at") or _now(), rec["updated_at"]),
                )
            con.commit()
        except sqlite3.IntegrityError as e:
            raise DuplicateError(str(e))
    return rec_id


def clients_delete(rec_id):
    with _lock, _connect() as con:
        con.execute("DELETE FROM clients WHERE id=?", (rec_id,))
        con.commit()


def clients_replace_all(records):
    """Bulk import/restore — used by the /clients/import style flows."""
    with _lock, _connect() as con:
        con.execute("DELETE FROM clients")
        for rec in records:
            rec = dict(rec)
            rec_id = rec.get("id")
            pan, aadhaar, email = _norm(rec.get("pan")), _norm(rec.get("aadhaar")), _norm(rec.get("email"))
            if rec_id is None:
                con.execute(
                    "INSERT INTO clients (pan, aadhaar, email, data, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                    (pan, aadhaar, email, json.dumps(rec), rec.get("created_at") or _now(), rec.get("updated_at")),
                )
            else:
                con.execute(
                    "INSERT OR REPLACE INTO clients (id, pan, aadhaar, email, data, created_at, updated_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (rec_id, pan, aadhaar, email, json.dumps(rec), rec.get("created_at") or _now(), rec.get("updated_at")),
                )
        con.commit()


# ── gstin_directory store ───────────────────────────────────────────

def gdir_get_all():
    with _connect() as con:
        rows = con.execute("SELECT data FROM gstin_directory").fetchall()
    return [json.loads(r["data"]) for r in rows]


def gdir_put(record):
    gstin = (record.get("gstin") or "").strip().upper()
    if not gstin:
        raise ValueError("record missing gstin")
    record = dict(record)
    record["gstin"] = gstin
    with _lock, _connect() as con:
        con.execute(
            "INSERT INTO gstin_directory (gstin, data) VALUES (?,?) "
            "ON CONFLICT(gstin) DO UPDATE SET data=excluded.data",
            (gstin, json.dumps(record)),
        )
        con.commit()


def gdir_put_batch(records):
    with _lock, _connect() as con:
        for record in records:
            gstin = (record.get("gstin") or "").strip().upper()
            if not gstin:
                continue
            record = dict(record)
            record["gstin"] = gstin
            con.execute(
                "INSERT INTO gstin_directory (gstin, data) VALUES (?,?) "
                "ON CONFLICT(gstin) DO UPDATE SET data=excluded.data",
                (gstin, json.dumps(record)),
            )
        con.commit()


def gdir_clear():
    with _lock, _connect() as con:
        con.execute("DELETE FROM gstin_directory")
        con.commit()
