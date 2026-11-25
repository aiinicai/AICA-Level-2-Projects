"""Append-only, hash-chained audit log.

Each entry stores event metadata only (ids, hashes, counts, statuses) — never
document content, extracted text, AI payloads or PII. `entry_hash` chains to the
previous entry so tampering is detectable via `verify_chain()`. SQLite triggers
(schema.sql) refuse UPDATE/DELETE on the table."""
from __future__ import annotations

import hashlib
import sqlite3
from typing import Any

from .db import dumps, ro, row_to_dict, utcnow
from .pii import scrub_for_log

GENESIS = "0" * 64
_FORBIDDEN_META_KEYS = {"text", "content", "payload", "password", "token", "api_key", "response"}


def _clean_meta(meta: dict[str, Any] | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in (meta or {}).items():
        if k.lower() in _FORBIDDEN_META_KEYS:
            out[k] = "[omitted]"
        elif isinstance(v, str):
            out[k] = scrub_for_log(v)[:500]
        else:
            out[k] = v
    return out


def _hash(prev: str, ts: str, user_id, case_id, event: str, meta_json: str) -> str:
    h = hashlib.sha256()
    h.update("|".join([prev, ts, str(user_id), str(case_id), event, meta_json]).encode("utf-8"))
    return h.hexdigest()


def log_event(conn: sqlite3.Connection, event: str, *, user_id: int | None = None, case_id: int | None = None,
              meta: dict[str, Any] | None = None) -> None:
    """Must be called inside an open transaction (see db.tx) so the event is atomic
    with the change it records."""
    meta_json = dumps(_clean_meta(meta))
    ts = utcnow()
    row = conn.execute("SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
    prev = row["entry_hash"] if row else GENESIS
    entry_hash = _hash(prev, ts, user_id, case_id, event, meta_json)
    conn.execute(
        "INSERT INTO audit_log(ts,user_id,case_id,event,meta_json,prev_hash,entry_hash) VALUES (?,?,?,?,?,?,?)",
        (ts, user_id, case_id, event, meta_json, prev, entry_hash),
    )


def verify_chain() -> dict[str, Any]:
    with ro() as conn:
        rows = conn.execute("SELECT * FROM audit_log ORDER BY id").fetchall()
    prev = GENESIS
    for r in rows:
        expected = _hash(prev, r["ts"], r["user_id"], r["case_id"], r["event"], r["meta_json"])
        if r["prev_hash"] != prev or r["entry_hash"] != expected:
            return {"valid": False, "broken_at_id": r["id"], "entries": len(rows)}
        prev = r["entry_hash"]
    return {"valid": True, "entries": len(rows)}


def case_history(case_id: int, limit: int = 500) -> list[dict]:
    with ro() as conn:
        rows = conn.execute(
            "SELECT a.id,a.ts,a.event,a.meta_json,u.username FROM audit_log a LEFT JOIN users u ON u.id=a.user_id "
            "WHERE a.case_id=? ORDER BY a.id DESC LIMIT ?",
            (case_id, limit),
        ).fetchall()
    return [row_to_dict(r, ("meta_json",)) for r in rows]


_AUDIT_TRIGGERS = [
    "CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_log "
    "BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END",
    "CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_log "
    "BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END",
]
_VLOG_TRIGGERS = [
    "CREATE TRIGGER IF NOT EXISTS vlog_no_update BEFORE UPDATE ON verification_log "
    "BEGIN SELECT RAISE(ABORT, 'verification_log is append-only'); END",
    "CREATE TRIGGER IF NOT EXISTS vlog_no_delete BEFORE DELETE ON verification_log "
    "BEGIN SELECT RAISE(ABORT, 'verification_log is append-only'); END",
]


def purge_case_history(conn: sqlite3.Connection, case_id: int) -> dict[str, Any]:
    """Permanent case deletion only: remove one case's history entries and re-link the remaining
    chain so verify_chain() stays valid. Runs inside the caller's transaction; the append-only
    triggers are lifted only for this statement block and restored before it ends (a failure
    rolls everything back, triggers included). The caller then records a CASE_DELETED entry
    that holds the previous chain head, so the purge itself remains on the record."""
    head = conn.execute("SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
    removed = conn.execute("SELECT COUNT(*) FROM audit_log WHERE case_id=?", (case_id,)).fetchone()[0]
    has_vlog = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='verification_log'").fetchone()
    vremoved = 0
    conn.execute("DROP TRIGGER IF EXISTS audit_no_update")
    conn.execute("DROP TRIGGER IF EXISTS audit_no_delete")
    try:
        conn.execute("DELETE FROM audit_log WHERE case_id=?", (case_id,))
        prev = GENESIS
        for r in conn.execute("SELECT * FROM audit_log ORDER BY id").fetchall():
            h = _hash(prev, r["ts"], r["user_id"], r["case_id"], r["event"], r["meta_json"])
            if r["prev_hash"] != prev or r["entry_hash"] != h:
                conn.execute("UPDATE audit_log SET prev_hash=?, entry_hash=? WHERE id=?", (prev, h, r["id"]))
            prev = h
    finally:
        for t in _AUDIT_TRIGGERS:
            conn.execute(t)
    if has_vlog:
        vremoved = conn.execute("SELECT COUNT(*) FROM verification_log WHERE case_id=?", (case_id,)).fetchone()[0]
        conn.execute("DROP TRIGGER IF EXISTS vlog_no_update")
        conn.execute("DROP TRIGGER IF EXISTS vlog_no_delete")
        try:
            conn.execute("DELETE FROM verification_log WHERE case_id=?", (case_id,))
        finally:
            for t in _VLOG_TRIGGERS:
                conn.execute(t)
    return {"history_entries_removed": removed, "verification_entries_removed": vremoved,
            "chain_head_before": head["entry_hash"] if head else GENESIS}
