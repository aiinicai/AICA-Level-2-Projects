"""
Data model and persistence for one assessment.

Storage model: one folder per organisation assessed, one SQLite file inside it.
No tenancy code, no shared database.

    clients/ABC_Pvt_Ltd/
        assessment.db
        evidence/
        output/

Nothing here calls out to a network. The file never leaves the assessor's machine.
Copying the folder moves the whole engagement; deleting it removes every trace.
"""

from __future__ import annotations

import contextlib
import hashlib
import secrets
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1

DDL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meta (
    key             TEXT PRIMARY KEY,
    value           TEXT NOT NULL
);

-- The entity being assessed. One row per project file.
CREATE TABLE IF NOT EXISTS client (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    name            TEXT NOT NULL,
    entity_type     TEXT NOT NULL,
    sector          TEXT,
    contact_person  TEXT,
    -- Role is decided per engagement, not per firm. See role.py.
    role            TEXT NOT NULL,          -- fiduciary / processor
    role_reasoning  TEXT,
    flags           TEXT NOT NULL DEFAULT '',
    assessed_by     TEXT,
    assessment_date TEXT NOT NULL
);

-- One row per assessed control. Status plus the management response.
CREATE TABLE IF NOT EXISTS response (
    control_id      TEXT PRIMARY KEY,
    status          TEXT NOT NULL CHECK (status IN ('Present','Partial','Absent')),
    assessor_note   TEXT,
    mgmt_response   TEXT,
    mgmt_owner      TEXT,
    mgmt_target_date TEXT,
    updated_at      TEXT NOT NULL
);

-- Evidence files copied into evidence/ and hashed. Drives the evidence gate.
CREATE TABLE IF NOT EXISTS evidence (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    control_id      TEXT NOT NULL,
    filename        TEXT NOT NULL,
    stored_path     TEXT NOT NULL,
    sha256          TEXT NOT NULL,
    description     TEXT,
    added_at        TEXT NOT NULL,
    FOREIGN KEY (control_id) REFERENCES response(control_id) ON DELETE CASCADE
);
"""


@dataclass
class Client:
    name: str
    entity_type: str
    role: str
    assessment_date: str
    sector: str | None = None
    contact_person: str | None = None
    role_reasoning: str | None = None
    assessed_by: str | None = None
    flags: set[str] = field(default_factory=set)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _text(value) -> str:
    return "" if value is None else value


class Project:
    """A single assessment folder, with its SQLite file open."""

    def __init__(self, folder: str | Path):
        self.folder = Path(folder)
        self.evidence_dir = self.folder / "evidence"
        self.output_dir = self.folder / "output"
        for d in (self.folder, self.evidence_dir, self.output_dir):
            d.mkdir(parents=True, exist_ok=True)

        # Autocommit with explicit transactions only, so each write is atomic.
        self.db = sqlite3.connect(self.folder / "assessment.db", isolation_level=None, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(DDL)
        row = self.db.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
        if row is None:
            with self.transaction():
                self.db.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', ?)",
                                (str(SCHEMA_VERSION),))

    @contextlib.contextmanager
    def transaction(self):
        """One atomic write. BEGIN IMMEDIATE so concurrent autosaves queue."""
        if self.db.in_transaction:
            raise RuntimeError("transaction already open")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield self.db
        except BaseException:
            if self.db.in_transaction:
                self.db.execute("ROLLBACK")
            raise
        self.db.execute("COMMIT")

    # -- client ------------------------------------------------------------

    def save_client(self, c: Client) -> None:
        with self.transaction():
            self.db.execute(
                """INSERT INTO client
                     (id, name, entity_type, sector, contact_person, role,
                      role_reasoning, flags, assessed_by, assessment_date)
                   VALUES (1,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET
                     name=excluded.name, entity_type=excluded.entity_type,
                     sector=excluded.sector, contact_person=excluded.contact_person,
                     role=excluded.role, role_reasoning=excluded.role_reasoning,
                     flags=excluded.flags, assessed_by=excluded.assessed_by,
                     assessment_date=excluded.assessment_date""",
                (c.name, c.entity_type, c.sector, c.contact_person, c.role,
                 c.role_reasoning, ",".join(sorted(c.flags)), c.assessed_by, c.assessment_date),
            )

    def set_role(self, role: str, reasoning: str | None) -> None:
        with self.transaction():
            if not self.db.execute("SELECT 1 FROM client WHERE id = 1").fetchone():
                raise ValueError("Client profile not saved yet.")
            self.db.execute("UPDATE client SET role = ?, role_reasoning = ? WHERE id = 1",
                            (role, reasoning))

    def get_client(self) -> Client | None:
        row = self.db.execute("SELECT * FROM client WHERE id = 1").fetchone()
        if not row:
            return None
        return Client(
            name=row["name"], entity_type=row["entity_type"], role=row["role"],
            assessment_date=row["assessment_date"], sector=row["sector"],
            contact_person=row["contact_person"], role_reasoning=row["role_reasoning"],
            assessed_by=row["assessed_by"],
            flags={f for f in (row["flags"] or "").split(",") if f},
        )

    # -- responses ---------------------------------------------------------

    _RESPONSE_FIELDS = ("status", "assessor_note", "mgmt_response", "mgmt_owner", "mgmt_target_date")

    def set_response(self, control_id: str, status: str, assessor_note: str = "",
                     mgmt_response: str = "", mgmt_owner: str = "",
                     mgmt_target_date: str = "") -> bool:
        """Save one control's answer. Returns False when nothing changed."""
        new = {"status": status, "assessor_note": _text(assessor_note),
               "mgmt_response": _text(mgmt_response), "mgmt_owner": _text(mgmt_owner),
               "mgmt_target_date": _text(mgmt_target_date)}
        with self.transaction():
            row = self.db.execute(
                "SELECT status, assessor_note, mgmt_response, mgmt_owner, mgmt_target_date "
                "FROM response WHERE control_id = ?", (control_id,)).fetchone()
            old = {k: _text(row[k]) for k in self._RESPONSE_FIELDS} if row else None
            if old == new:
                return False
            self.db.execute(
                """INSERT INTO response
                     (control_id, status, assessor_note, mgmt_response,
                      mgmt_owner, mgmt_target_date, updated_at)
                   VALUES (?,?,?,?,?,?,?)
                   ON CONFLICT(control_id) DO UPDATE SET
                     status=excluded.status, assessor_note=excluded.assessor_note,
                     mgmt_response=excluded.mgmt_response, mgmt_owner=excluded.mgmt_owner,
                     mgmt_target_date=excluded.mgmt_target_date,
                     updated_at=excluded.updated_at""",
                (control_id, new["status"], new["assessor_note"], new["mgmt_response"],
                 new["mgmt_owner"], new["mgmt_target_date"], _now()),
            )
        return True

    def responses(self) -> dict[str, dict]:
        """control_id -> plain dict. Report and engine layers never see Row objects."""
        return {r["control_id"]: dict(r) for r in self.db.execute("SELECT * FROM response")}

    def statuses(self) -> dict[str, str]:
        """control_id -> status, in the shape catalogue.score() expects."""
        return {cid: r["status"] for cid, r in self.responses().items()}

    # -- evidence ----------------------------------------------------------

    def add_evidence(self, control_id: str, source: str | Path, description: str = "") -> int:
        """Store a copy of a file in evidence/, hash it, and link it to the control.

        Each upload gets a name of its own and is created exclusively, holding
        exactly the bytes that were hashed, so a recorded SHA-256 always resolves
        to the file it describes.
        """
        src = Path(source)
        data = src.read_bytes()
        digest = hashlib.sha256(data).hexdigest()

        dest = None
        for _ in range(5):
            candidate = self.evidence_dir / f"{control_id}__{secrets.token_hex(8)}__{src.name}"
            try:
                with open(candidate, "xb") as fh:
                    dest = candidate
                    fh.write(data)
                break
            except FileExistsError:
                continue
        if dest is None:
            raise RuntimeError("Could not choose a unique name for the evidence file.")

        try:
            with self.transaction():
                cur = self.db.execute(
                    """INSERT INTO evidence
                         (control_id, filename, stored_path, sha256, description, added_at)
                       VALUES (?,?,?,?,?,?)""",
                    (control_id, src.name, str(dest.relative_to(self.folder)), digest,
                     description, _now()),
                )
                new_id = cur.lastrowid
        except BaseException:
            dest.unlink(missing_ok=True)
            raise
        return new_id

    def evidence_counts(self) -> dict[str, int]:
        rows = self.db.execute("SELECT control_id, COUNT(*) AS n FROM evidence GROUP BY control_id")
        return {r["control_id"]: r["n"] for r in rows}

    def evidence(self) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT * FROM evidence ORDER BY id")]

    def close(self) -> None:
        self.db.close()


if __name__ == "__main__":
    # Self-check in a temporary folder: create, answer, attach, read back.
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        p = Project(Path(tmp) / "Selfcheck_Ltd")
        p.save_client(Client(name="Selfcheck Ltd", entity_type="LLP", role="fiduciary",
                             assessment_date="2026-09-20"))
        assert p.set_response("R6.1", "Present") is True
        assert p.set_response("R6.1", "Present") is False
        f = Path(tmp) / "policy.txt"
        f.write_text("encryption policy", encoding="utf-8")
        p.add_evidence("R6.1", f, "Encryption policy")
        assert p.evidence_counts() == {"R6.1": 1}
        assert p.evidence()[0]["sha256"] == hashlib.sha256(b"encryption policy").hexdigest()
        p.close()
    print("models self-check: ok")
