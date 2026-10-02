"""Append-only, hash-chained audit log (brief §8).

* Each row is written in the SAME transaction as the change it records.
* row_hash = sha256(prev_hash + canonical_json(row without row_hash)).
* BEFORE UPDATE / BEFORE DELETE triggers abort any change (installed by the
  Alembic migration — see migrations/versions/0001_initial.py).
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .models import AuditLog

GENESIS = "0" * 64
HASHED_FIELDS = ["ts", "actor_id", "actor_name", "actor_role", "action", "object_type", "object_id",
                 "entity_id", "before_json", "after_json", "ip", "user_agent", "prev_hash"]


def _default(o: Any):
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    return str(o)


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=_default, ensure_ascii=False)


def row_hash(fields: dict[str, Any]) -> str:
    body = {k: fields.get(k) for k in HASHED_FIELDS}
    return hashlib.sha256((fields["prev_hash"] + canonical_json(body)).encode("utf-8")).hexdigest()


@dataclass
class Actor:
    id: int | None
    name: str
    role: str
    ip: str | None = None
    user_agent: str | None = None


SYSTEM = Actor(None, "system", "SYSTEM")


def _lock_chain(session: Session) -> None:
    dialect = session.get_bind().dialect.name
    if dialect == "sqlite":
        # an UPDATE takes SQLite's write lock for the rest of the transaction
        session.execute(text("UPDATE audit_chain_lock SET n = n + 1 WHERE id = 1"))
    elif dialect == "postgresql":  # pragma: no cover - exercised only on PostgreSQL
        session.execute(text("LOCK TABLE audit_log IN SHARE ROW EXCLUSIVE MODE"))


def record(session: Session, actor: Actor, action: str, object_type: str, object_id: Any = None,
           entity_id: int | None = None, before: Any = None, after: Any = None) -> AuditLog:
    """Add one audit row to the current transaction (caller commits)."""
    _lock_chain(session)
    session.flush()
    prev = session.execute(select(AuditLog.row_hash).order_by(AuditLog.id.desc()).limit(1)).scalar()
    fields = dict(
        ts=datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        actor_id=actor.id, actor_name=actor.name, actor_role=actor.role, action=action,
        object_type=object_type, object_id=None if object_id is None else str(object_id), entity_id=entity_id,
        before_json=None if before is None else canonical_json(before),
        after_json=None if after is None else canonical_json(after),
        ip=actor.ip, user_agent=(actor.user_agent or "")[:255] or None, prev_hash=prev or GENESIS)
    fields["row_hash"] = row_hash(fields)
    row = AuditLog(**fields)
    session.add(row)
    session.flush()
    return row


@dataclass
class ChainReport:
    ok: bool
    rows: int
    broken_id: int | None = None
    message: str = ""


def verify_chain(connection_or_session) -> ChainReport:
    """Recompute every hash in id order; report the first broken link."""
    sql = f"SELECT id, row_hash, {', '.join(HASHED_FIELDS)} FROM audit_log ORDER BY id"
    if isinstance(connection_or_session, sqlite3.Connection):     # raw file access (CLI, forensic copy)
        cur = connection_or_session.execute(sql)
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    else:
        rows = connection_or_session.execute(text(sql)).mappings().all()
    prev = GENESIS
    for r in rows:
        fields = dict(r)
        if fields["prev_hash"] != prev:
            return ChainReport(False, len(rows), r["id"], f"Row {r['id']}: prev_hash does not match row "
                                                            f"before it (a row was removed or re-ordered)")
        if row_hash(fields) != r["row_hash"]:
            return ChainReport(False, len(rows), r["id"], f"Row {r['id']}: contents do not match its hash "
                                                            f"(the row was altered)")
        prev = r["row_hash"]
    return ChainReport(True, len(rows), None, f"Audit chain intact: {len(rows)} rows verified")


TRIGGER_SQL = {
    "sqlite": [
        "CREATE TRIGGER IF NOT EXISTS audit_log_no_update BEFORE UPDATE ON audit_log "
        "BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END",
        "CREATE TRIGGER IF NOT EXISTS audit_log_no_delete BEFORE DELETE ON audit_log "
        "BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END",
    ],
    "postgresql": [
        "CREATE OR REPLACE FUNCTION audit_log_append_only() RETURNS trigger AS $$ "
        "BEGIN RAISE EXCEPTION 'audit_log is append-only'; END; $$ LANGUAGE plpgsql",
        "DROP TRIGGER IF EXISTS audit_log_no_update ON audit_log",
        "CREATE TRIGGER audit_log_no_update BEFORE UPDATE ON audit_log "
        "FOR EACH ROW EXECUTE FUNCTION audit_log_append_only()",
        "DROP TRIGGER IF EXISTS audit_log_no_delete ON audit_log",
        "CREATE TRIGGER audit_log_no_delete BEFORE DELETE ON audit_log "
        "FOR EACH ROW EXECUTE FUNCTION audit_log_append_only()",
    ],
}
