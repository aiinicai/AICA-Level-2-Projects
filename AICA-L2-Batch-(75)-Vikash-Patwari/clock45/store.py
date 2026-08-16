"""Local SQLite persistence for The 45-Day Clock.

The database is created only in a folder explicitly supplied by the caller.
Completed computation runs are immutable snapshots. Vendor classification
changes are recorded automatically by SQLite triggers in an append-only log.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Optional

from .classify import UdyamRecord
from .engine import ComputationRun, Finding, PaymentLine, PurchaseLine
from .ingest import InvoiceSupplement


SCHEMA_VERSION = 2
DATABASE_FILENAME = "clock45.sqlite3"


class StoreError(RuntimeError):
    pass


class ImmutableRunError(StoreError):
    pass


@dataclass(frozen=True)
class StoredAnalysis:
    analysis_id: str
    client_id: str
    entity_name: str
    entity_pan: str
    fy: str
    stage: str
    acceptance_policy: Optional[str]
    acceptance_plus_days: int
    control_totals: Optional[dict[str, Any]]
    purchases: list[PurchaseLine]
    payments: list[PaymentLine]
    udyam: dict[str, UdyamRecord]
    invoice_supplements: dict[str, InvoiceSupplement]
    completed_run_id: Optional[str]
    updated_at: str


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return {"__decimal__": str(value)}
    if isinstance(value, (date, datetime)):
        return {"__date__": value.isoformat(), "__datetime__": isinstance(value, datetime)}
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def _json_hook(value: dict[str, Any]) -> Any:
    if "__decimal__" in value:
        return Decimal(value["__decimal__"])
    if "__date__" in value:
        return (
            datetime.fromisoformat(value["__date__"])
            if value.get("__datetime__")
            else date.fromisoformat(value["__date__"])
        )
    return value


def _dump(value: Any) -> str:
    return json.dumps(value, default=_json_default, sort_keys=True, separators=(",", ":"))


def _load(value: Optional[str], default: Any = None) -> Any:
    if value is None:
        return default
    return json.loads(value, object_hook=_json_hook)


def _record_json(record: UdyamRecord) -> str:
    return _dump(asdict(record))


def _safe_database_folder(folder: str | Path) -> Path:
    resolved = Path(folder).expanduser().resolve()
    program_roots = [
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
        os.environ.get("ProgramW6432"),
    ]
    for root in (Path(item).resolve() for item in program_roots if item):
        try:
            resolved.relative_to(root)
        except ValueError:
            continue
        raise StoreError(
            "The database cannot be stored under Program Files. "
            "Choose a client-data or firm-data folder where you have write access."
        )
    return resolved


SCHEMA = """
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clients (
    client_id TEXT PRIMARY KEY,
    entity_name TEXT NOT NULL,
    pan TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(entity_name, pan)
);

CREATE TABLE IF NOT EXISTS vendor_master (
    client_id TEXT NOT NULL REFERENCES clients(client_id),
    vendor_id TEXT NOT NULL,
    vendor_name TEXT NOT NULL,
    pan_gstin TEXT NOT NULL DEFAULT '',
    udyam_no TEXT,
    enterprise_class TEXT,
    nic_code TEXT,
    activity_label TEXT,
    registration_date TEXT,
    evidence_source TEXT NOT NULL,
    evidence_file_hash TEXT,
    confirmed_by TEXT,
    confirmed_on TEXT,
    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(client_id, vendor_id)
);

CREATE TABLE IF NOT EXISTS vendor_classification_audit (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT NOT NULL,
    vendor_id TEXT NOT NULL,
    action TEXT NOT NULL,
    changed_by TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    evidence_source TEXT NOT NULL,
    before_json TEXT,
    after_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vendor_evidence (
    evidence_id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    vendor_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    media_type TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    content BLOB NOT NULL,
    added_by TEXT NOT NULL,
    added_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vendor_evidence_reviews (
    review_id TEXT PRIMARY KEY,
    evidence_id TEXT NOT NULL REFERENCES vendor_evidence(evidence_id),
    client_id TEXT NOT NULL,
    vendor_id TEXT NOT NULL,
    parsed_json TEXT NOT NULL,
    confirmed_json TEXT NOT NULL,
    conflicts_json TEXT NOT NULL,
    confirmed_by TEXT NOT NULL,
    confirmed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vendor_classification_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT NOT NULL,
    vendor_id TEXT NOT NULL,
    classification_year TEXT NOT NULL,
    enterprise_class TEXT NOT NULL,
    classification_date TEXT,
    evidence_id TEXT REFERENCES vendor_evidence(evidence_id),
    evidence_source TEXT NOT NULL,
    recorded_by TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vendor_metadata (
    client_id TEXT NOT NULL,
    vendor_id TEXT NOT NULL,
    pan TEXT NOT NULL DEFAULT '',
    gstin TEXT NOT NULL DEFAULT '',
    contact TEXT NOT NULL DEFAULT '',
    registration_status TEXT NOT NULL DEFAULT '',
    verification_source TEXT NOT NULL DEFAULT '',
    organisation_type TEXT NOT NULL DEFAULT '',
    incorporation_date TEXT,
    commencement_date TEXT,
    registered_address TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL,
    PRIMARY KEY(client_id, vendor_id)
);

CREATE TABLE IF NOT EXISTS analysis_sessions (
    analysis_id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES clients(client_id),
    fy TEXT NOT NULL,
    stage TEXT NOT NULL,
    acceptance_policy TEXT,
    acceptance_plus_days INTEGER NOT NULL DEFAULT 0,
    control_totals_json TEXT,
    source_label TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ledger_imports (
    import_id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL REFERENCES analysis_sessions(analysis_id),
    record_type TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_name TEXT NOT NULL,
    control_totals_json TEXT NOT NULL,
    imported_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS purchase_lines (
    analysis_id TEXT NOT NULL REFERENCES analysis_sessions(analysis_id),
    line_number INTEGER NOT NULL,
    invoice_id TEXT NOT NULL,
    vendor_id TEXT NOT NULL,
    vendor_name TEXT NOT NULL,
    invoice_date TEXT NOT NULL,
    amount TEXT NOT NULL,
    grn_date TEXT,
    agreement_days INTEGER,
    PRIMARY KEY(analysis_id, line_number)
);

CREATE TABLE IF NOT EXISTS payment_lines (
    analysis_id TEXT NOT NULL REFERENCES analysis_sessions(analysis_id),
    line_number INTEGER NOT NULL,
    invoice_id TEXT NOT NULL,
    payment_date TEXT NOT NULL,
    amount TEXT NOT NULL,
    PRIMARY KEY(analysis_id, line_number)
);

CREATE TABLE IF NOT EXISTS invoice_supplements (
    analysis_id TEXT NOT NULL REFERENCES analysis_sessions(analysis_id),
    invoice_id TEXT NOT NULL,
    agreed_due_date TEXT,
    actual_payment_date TEXT,
    outstanding_amount TEXT,
    ledger_category TEXT NOT NULL DEFAULT '',
    remarks TEXT NOT NULL DEFAULT '',
    PRIMARY KEY(analysis_id, invoice_id)
);

CREATE TABLE IF NOT EXISTS column_mappings (
    client_id TEXT NOT NULL REFERENCES clients(client_id),
    record_type TEXT NOT NULL,
    source_fingerprint TEXT NOT NULL,
    mapping_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(client_id, record_type, source_fingerprint)
);

CREATE TABLE IF NOT EXISTS completed_runs (
    run_id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL REFERENCES analysis_sessions(analysis_id),
    client_id TEXT NOT NULL REFERENCES clients(client_id),
    entity_name TEXT NOT NULL,
    entity_pan TEXT NOT NULL,
    fy TEXT NOT NULL,
    operator TEXT NOT NULL,
    acceptance_policy TEXT NOT NULL,
    acceptance_plus_days INTEGER NOT NULL,
    run_at TEXT NOT NULL,
    rule_pack_version TEXT NOT NULL,
    run_hash TEXT NOT NULL,
    statute_json TEXT NOT NULL,
    control_totals_json TEXT NOT NULL,
    warnings_json TEXT NOT NULL,
    purchases_json TEXT NOT NULL,
    payments_json TEXT NOT NULL,
    udyam_snapshot_json TEXT NOT NULL,
    findings_json TEXT NOT NULL,
    disallowance_total TEXT NOT NULL,
    interest_total TEXT NOT NULL,
    excluded_total TEXT NOT NULL,
    supersedes_run_id TEXT REFERENCES completed_runs(run_id),
    completed_at TEXT NOT NULL,
    UNIQUE(client_id, fy, run_hash, run_at)
);

CREATE TABLE IF NOT EXISTS run_exports (
    export_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES completed_runs(run_id),
    exported_at TEXT NOT NULL,
    exported_by TEXT NOT NULL,
    output_folder TEXT NOT NULL,
    files_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(entity_name);
CREATE INDEX IF NOT EXISTS idx_vendor_master_client ON vendor_master(client_id, active);
CREATE INDEX IF NOT EXISTS idx_vendor_audit_vendor ON vendor_classification_audit(client_id, vendor_id, changed_at);
CREATE INDEX IF NOT EXISTS idx_vendor_evidence_vendor ON vendor_evidence(client_id, vendor_id, added_at);
CREATE INDEX IF NOT EXISTS idx_vendor_reviews_vendor ON vendor_evidence_reviews(client_id, vendor_id, confirmed_at);
CREATE INDEX IF NOT EXISTS idx_vendor_history_vendor ON vendor_classification_history(client_id, vendor_id, classification_year, recorded_at);
CREATE INDEX IF NOT EXISTS idx_analysis_client_fy ON analysis_sessions(client_id, fy, updated_at);
CREATE INDEX IF NOT EXISTS idx_purchase_analysis ON purchase_lines(analysis_id);
CREATE INDEX IF NOT EXISTS idx_payment_analysis ON payment_lines(analysis_id);
CREATE INDEX IF NOT EXISTS idx_runs_client_fy ON completed_runs(client_id, fy, completed_at);
CREATE INDEX IF NOT EXISTS idx_exports_run ON run_exports(run_id, exported_at);
"""


TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS trg_vendor_insert_audit
AFTER INSERT ON vendor_master
BEGIN
    INSERT INTO vendor_classification_audit (
        client_id, vendor_id, action, changed_by, changed_at,
        evidence_source, before_json, after_json
    ) VALUES (
        NEW.client_id, NEW.vendor_id, 'CREATE', clock45_actor(), clock45_now(),
        NEW.evidence_source, NULL,
        json_object(
            'vendor_name', NEW.vendor_name, 'pan_gstin', NEW.pan_gstin,
            'udyam_no', NEW.udyam_no, 'enterprise_class', NEW.enterprise_class,
            'nic_code', NEW.nic_code, 'activity_label', NEW.activity_label,
            'registration_date', NEW.registration_date,
            'evidence_source', NEW.evidence_source,
            'evidence_file_hash', NEW.evidence_file_hash,
            'confirmed_by', NEW.confirmed_by, 'confirmed_on', NEW.confirmed_on,
            'active', NEW.active
        )
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_vendor_update_audit
AFTER UPDATE ON vendor_master
BEGIN
    INSERT INTO vendor_classification_audit (
        client_id, vendor_id, action, changed_by, changed_at,
        evidence_source, before_json, after_json
    ) VALUES (
        NEW.client_id, NEW.vendor_id, 'UPDATE', clock45_actor(), clock45_now(),
        NEW.evidence_source,
        json_object(
            'vendor_name', OLD.vendor_name, 'pan_gstin', OLD.pan_gstin,
            'udyam_no', OLD.udyam_no, 'enterprise_class', OLD.enterprise_class,
            'nic_code', OLD.nic_code, 'activity_label', OLD.activity_label,
            'registration_date', OLD.registration_date,
            'evidence_source', OLD.evidence_source,
            'evidence_file_hash', OLD.evidence_file_hash,
            'confirmed_by', OLD.confirmed_by, 'confirmed_on', OLD.confirmed_on,
            'active', OLD.active
        ),
        json_object(
            'vendor_name', NEW.vendor_name, 'pan_gstin', NEW.pan_gstin,
            'udyam_no', NEW.udyam_no, 'enterprise_class', NEW.enterprise_class,
            'nic_code', NEW.nic_code, 'activity_label', NEW.activity_label,
            'registration_date', NEW.registration_date,
            'evidence_source', NEW.evidence_source,
            'evidence_file_hash', NEW.evidence_file_hash,
            'confirmed_by', NEW.confirmed_by, 'confirmed_on', NEW.confirmed_on,
            'active', NEW.active
        )
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_vendor_no_delete
BEFORE DELETE ON vendor_master
BEGIN
    SELECT RAISE(ABORT, 'vendor master rows cannot be deleted; mark inactive');
END;

CREATE TRIGGER IF NOT EXISTS trg_audit_no_update
BEFORE UPDATE ON vendor_classification_audit
BEGIN
    SELECT RAISE(ABORT, 'vendor classification audit is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_audit_no_delete
BEFORE DELETE ON vendor_classification_audit
BEGIN
    SELECT RAISE(ABORT, 'vendor classification audit is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_evidence_no_update
BEFORE UPDATE ON vendor_evidence
BEGIN
    SELECT RAISE(ABORT, 'vendor evidence is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_evidence_no_delete
BEFORE DELETE ON vendor_evidence
BEGIN
    SELECT RAISE(ABORT, 'vendor evidence is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_evidence_review_no_update
BEFORE UPDATE ON vendor_evidence_reviews
BEGIN
    SELECT RAISE(ABORT, 'vendor evidence reviews are append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_evidence_review_no_delete
BEFORE DELETE ON vendor_evidence_reviews
BEGIN
    SELECT RAISE(ABORT, 'vendor evidence reviews are append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_classification_history_no_update
BEFORE UPDATE ON vendor_classification_history
BEGIN
    SELECT RAISE(ABORT, 'vendor classification history is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_classification_history_no_delete
BEFORE DELETE ON vendor_classification_history
BEGIN
    SELECT RAISE(ABORT, 'vendor classification history is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_runs_no_update
BEFORE UPDATE ON completed_runs
BEGIN
    SELECT RAISE(ABORT, 'completed computation runs are immutable');
END;

CREATE TRIGGER IF NOT EXISTS trg_runs_no_delete
BEFORE DELETE ON completed_runs
BEGIN
    SELECT RAISE(ABORT, 'completed computation runs are immutable');
END;

CREATE TRIGGER IF NOT EXISTS trg_exports_no_update
BEFORE UPDATE ON run_exports
BEGIN
    SELECT RAISE(ABORT, 'run export history is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_exports_no_delete
BEFORE DELETE ON run_exports
BEGIN
    SELECT RAISE(ABORT, 'run export history is append-only');
END;
"""


class Store:
    def __init__(self, folder: str | Path, *, actor: str = "Desktop user") -> None:
        self.folder = _safe_database_folder(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        if not self.folder.is_dir():
            raise StoreError(f"Database folder is not a directory: {self.folder}")
        self.path = self.folder / DATABASE_FILENAME
        self._actor = actor
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(
            self.path, timeout=30, isolation_level=None, check_same_thread=False
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.create_function("clock45_actor", 0, lambda: self._actor)
        self._connection.create_function(
            "clock45_now", 0, lambda: datetime.now().isoformat(timespec="seconds")
        )
        self._configure()
        self._initialize()

    def _configure(self) -> None:
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA synchronous = FULL")
        self._connection.execute("PRAGMA busy_timeout = 30000")

    def _initialize(self) -> None:
        with self._lock:
            self._connection.executescript(SCHEMA)
            self._connection.executescript(TRIGGERS)
            current = self._connection.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            ).fetchone()
            if current:
                version = int(current["value"])
                if version < 1 or version > SCHEMA_VERSION:
                    raise StoreError(
                        f"Database schema {version} is not supported by this application "
                        f"(latest is {SCHEMA_VERSION})."
                    )
                if version < SCHEMA_VERSION:
                    # Version 2 is additive: the tables above are created before this
                    # version marker is advanced, preserving every existing row.
                    self._connection.execute(
                        "UPDATE metadata SET value = ? WHERE key = 'schema_version'",
                        (str(SCHEMA_VERSION),),
                    )
            else:
                self._connection.execute(
                    "INSERT INTO metadata(key, value) VALUES('schema_version', ?)",
                    (str(SCHEMA_VERSION),),
                )
            self._connection.execute("PRAGMA optimize")

    def close(self) -> None:
        with self._lock:
            if self._connection:
                self._connection.execute("PRAGMA optimize")
                self._connection.close()
                self._connection = None

    def set_actor(self, actor: str) -> None:
        self._actor = actor.strip() or "Unknown user"

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        row = self._connection.execute(
            "SELECT value FROM metadata WHERE key = ?", (f"setting:{key}",)
        ).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self._connection.execute(
            "INSERT INTO metadata(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (f"setting:{key}", str(value)),
        )

    def _transaction(self):
        return _Transaction(self)

    def get_or_create_client(self, entity_name: str, pan: str = "") -> str:
        now = datetime.now().isoformat(timespec="seconds")
        with self._transaction():
            row = self._connection.execute(
                "SELECT client_id FROM clients WHERE entity_name = ? AND pan = ?",
                (entity_name.strip(), pan.strip().upper()),
            ).fetchone()
            if row:
                return row["client_id"]
            client_id = uuid.uuid4().hex
            self._connection.execute(
                "INSERT INTO clients(client_id, entity_name, pan, created_at, updated_at) "
                "VALUES(?, ?, ?, ?, ?)",
                (client_id, entity_name.strip(), pan.strip().upper(), now, now),
            )
            return client_id

    def list_clients(self) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            "SELECT client_id, entity_name, pan, created_at, updated_at "
            "FROM clients ORDER BY entity_name"
        ).fetchall()
        return [dict(row) for row in rows]

    def list_client_workspaces(self) -> list[dict[str, Any]]:
        """Return each client with its most recently touched tax year and stage."""
        rows = self._connection.execute(
            "SELECT c.client_id, c.entity_name, c.pan, a.fy, a.stage, a.updated_at "
            "FROM clients c LEFT JOIN analysis_sessions a ON a.analysis_id = ("
            "SELECT latest.analysis_id FROM analysis_sessions latest "
            "WHERE latest.client_id = c.client_id ORDER BY latest.updated_at DESC LIMIT 1) "
            "ORDER BY c.entity_name"
        ).fetchall()
        return [dict(row) for row in rows]

    def start_or_resume_analysis(self, client_id: str, fy: str) -> str:
        row = self._connection.execute(
            "SELECT a.analysis_id FROM analysis_sessions a "
            "WHERE a.client_id = ? AND a.fy = ? "
            "AND NOT EXISTS (SELECT 1 FROM completed_runs r WHERE r.analysis_id = a.analysis_id) "
            "ORDER BY updated_at DESC LIMIT 1",
            (client_id, fy),
        ).fetchone()
        if row:
            return row["analysis_id"]
        analysis_id = uuid.uuid4().hex
        now = datetime.now().isoformat(timespec="seconds")
        self._connection.execute(
            "INSERT INTO analysis_sessions(analysis_id, client_id, fy, stage, created_at, updated_at) "
            "VALUES(?, ?, ?, 'home', ?, ?)",
            (analysis_id, client_id, fy, now, now),
        )
        return analysis_id

    def save_analysis(
        self,
        analysis_id: str,
        *,
        stage: str,
        purchases: list[PurchaseLine],
        payments: list[PaymentLine],
        control_totals: Optional[dict[str, Any]],
        source_label: str = "",
        acceptance_policy: Optional[str] = None,
        acceptance_plus_days: int = 0,
        import_record_type: str = "purchase",
        source_type: str = "application",
        invoice_supplements: Optional[Mapping[str, InvoiceSupplement]] = None,
    ) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self._transaction():
            exists = self._connection.execute(
                "SELECT 1 FROM analysis_sessions WHERE analysis_id = ?", (analysis_id,)
            ).fetchone()
            if not exists:
                raise StoreError(f"Analysis not found: {analysis_id}")
            self._connection.execute(
                "UPDATE analysis_sessions SET stage = ?, acceptance_policy = ?, "
                "acceptance_plus_days = ?, control_totals_json = ?, source_label = ?, "
                "updated_at = ? WHERE analysis_id = ?",
                (
                    stage,
                    acceptance_policy,
                    int(acceptance_plus_days),
                    _dump(control_totals) if control_totals is not None else None,
                    source_label,
                    now,
                    analysis_id,
                ),
            )
            self._connection.execute(
                "DELETE FROM purchase_lines WHERE analysis_id = ?", (analysis_id,)
            )
            self._connection.execute(
                "DELETE FROM payment_lines WHERE analysis_id = ?", (analysis_id,)
            )
            self._connection.execute(
                "DELETE FROM invoice_supplements WHERE analysis_id = ?", (analysis_id,)
            )
            self._connection.executemany(
                "INSERT INTO purchase_lines(analysis_id, line_number, invoice_id, vendor_id, "
                "vendor_name, invoice_date, amount, grn_date, agreement_days) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        analysis_id,
                        number,
                        line.invoice_id,
                        line.vendor_id,
                        line.vendor_name_as_written,
                        line.invoice_date.isoformat(),
                        str(line.amount),
                        line.grn_date.isoformat() if line.grn_date else None,
                        line.agreement_days,
                    )
                    for number, line in enumerate(purchases, 1)
                ],
            )
            self._connection.executemany(
                "INSERT INTO invoice_supplements(analysis_id, invoice_id, agreed_due_date, "
                "actual_payment_date, outstanding_amount, ledger_category, remarks) "
                "VALUES(?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        analysis_id,
                        item.invoice_id,
                        item.agreed_due_date.isoformat() if item.agreed_due_date else None,
                        item.actual_payment_date.isoformat() if item.actual_payment_date else None,
                        str(item.outstanding_amount) if item.outstanding_amount is not None else None,
                        item.ledger_category,
                        item.remarks,
                    )
                    for item in (invoice_supplements or {}).values()
                ],
            )
            self._connection.executemany(
                "INSERT INTO payment_lines(analysis_id, line_number, invoice_id, payment_date, amount) "
                "VALUES(?, ?, ?, ?, ?)",
                [
                    (
                        analysis_id,
                        number,
                        line.invoice_id,
                        line.payment_date.isoformat(),
                        str(line.amount),
                    )
                    for number, line in enumerate(payments, 1)
                ],
            )
            self._connection.execute(
                "INSERT INTO ledger_imports(import_id, analysis_id, record_type, source_type, "
                "source_name, control_totals_json, imported_at) VALUES(?, ?, ?, ?, ?, ?, ?)",
                (
                    uuid.uuid4().hex,
                    analysis_id,
                    import_record_type,
                    source_type,
                    source_label,
                    _dump(control_totals or {}),
                    now,
                ),
            )

    def update_analysis_stage(
        self,
        analysis_id: str,
        stage: str,
        *,
        acceptance_policy: Optional[str] = None,
        acceptance_plus_days: int = 0,
    ) -> None:
        """Save workflow progress without pretending another ledger was imported."""
        now = datetime.now().isoformat(timespec="seconds")
        cursor = self._connection.execute(
            "UPDATE analysis_sessions SET stage = ?, acceptance_policy = ?, "
            "acceptance_plus_days = ?, updated_at = ? WHERE analysis_id = ?",
            (stage, acceptance_policy, int(acceptance_plus_days), now, analysis_id),
        )
        if not cursor.rowcount:
            raise StoreError(f"Analysis not found: {analysis_id}")

    def save_column_mapping(
        self,
        client_id: str,
        record_type: str,
        source_fingerprint: str,
        mapping: Mapping[str, str],
    ) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        self._connection.execute(
            "INSERT INTO column_mappings(client_id, record_type, source_fingerprint, "
            "mapping_json, created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(client_id, record_type, source_fingerprint) DO UPDATE SET "
            "mapping_json = excluded.mapping_json, updated_at = excluded.updated_at",
            (client_id, record_type, source_fingerprint, _dump(dict(mapping)), now, now),
        )

    def load_column_mapping(
        self, client_id: str, record_type: str, source_fingerprint: str
    ) -> Optional[dict[str, str]]:
        row = self._connection.execute(
            "SELECT mapping_json FROM column_mappings WHERE client_id = ? "
            "AND record_type = ? AND source_fingerprint = ?",
            (client_id, record_type, source_fingerprint),
        ).fetchone()
        return _load(row["mapping_json"]) if row else None

    def upsert_vendor(
        self,
        client_id: str,
        record: UdyamRecord,
        *,
        vendor_name: str = "",
        pan_gstin: str = "",
        changed_by: Optional[str] = None,
    ) -> None:
        previous_actor = self._actor
        if changed_by:
            self.set_actor(changed_by)
        now = datetime.now().isoformat(timespec="seconds")
        values = (
            vendor_name or record.vendor_id,
            pan_gstin,
            record.udyam_no,
            record.enterprise_class,
            record.nic_code,
            record.activity_label,
            record.registration_date.isoformat() if record.registration_date else None,
            record.source,
            record.evidence_file_hash,
            record.confirmed_by,
            record.confirmed_on.isoformat() if record.confirmed_on else None,
            now,
        )
        try:
            with self._transaction():
                existing = self._connection.execute(
                    "SELECT vendor_name, pan_gstin, udyam_no, enterprise_class, nic_code, "
                    "activity_label, registration_date, evidence_source, evidence_file_hash, "
                    "confirmed_by, confirmed_on FROM vendor_master "
                    "WHERE client_id = ? AND vendor_id = ?",
                    (client_id, record.vendor_id),
                ).fetchone()
                if existing:
                    desired = values[:-1]
                    current = tuple(existing)
                    if current == desired:
                        return
                    self._connection.execute(
                        "UPDATE vendor_master SET vendor_name = ?, pan_gstin = ?, udyam_no = ?, "
                        "enterprise_class = ?, nic_code = ?, activity_label = ?, "
                        "registration_date = ?, evidence_source = ?, evidence_file_hash = ?, "
                        "confirmed_by = ?, confirmed_on = ?, updated_at = ? "
                        "WHERE client_id = ? AND vendor_id = ?",
                        values + (client_id, record.vendor_id),
                    )
                else:
                    self._connection.execute(
                        "INSERT INTO vendor_master(client_id, vendor_id, vendor_name, pan_gstin, "
                        "udyam_no, enterprise_class, nic_code, activity_label, registration_date, "
                        "evidence_source, evidence_file_hash, confirmed_by, confirmed_on, "
                        "created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (client_id, record.vendor_id) + values[:-1] + (now, now),
                    )
        finally:
            self._actor = previous_actor

    def load_vendor_master(self, client_id: str) -> dict[str, UdyamRecord]:
        rows = self._connection.execute(
            "SELECT * FROM vendor_master WHERE client_id = ? AND active = 1 ORDER BY vendor_name",
            (client_id,),
        ).fetchall()
        return {
            row["vendor_id"]: UdyamRecord(
                vendor_id=row["vendor_id"],
                udyam_no=row["udyam_no"],
                enterprise_class=row["enterprise_class"],
                nic_code=row["nic_code"],
                activity_label=row["activity_label"],
                registration_date=date.fromisoformat(row["registration_date"])
                if row["registration_date"] else None,
                source=row["evidence_source"],
                evidence_file_hash=row["evidence_file_hash"],
                confirmed_by=row["confirmed_by"],
                confirmed_on=date.fromisoformat(row["confirmed_on"])
                if row["confirmed_on"] else None,
            )
            for row in rows
        }

    def vendor_audit_log(
        self, client_id: str, vendor_id: Optional[str] = None
    ) -> list[dict[str, Any]]:
        query = (
            "SELECT * FROM vendor_classification_audit WHERE client_id = ?"
            + (" AND vendor_id = ?" if vendor_id else "")
            + " ORDER BY audit_id"
        )
        parameters = (client_id, vendor_id) if vendor_id else (client_id,)
        rows = self._connection.execute(query, parameters).fetchall()
        output = []
        for row in rows:
            item = dict(row)
            item["before"] = json.loads(item.pop("before_json")) if item["before_json"] else None
            item["after"] = json.loads(item.pop("after_json"))
            before = item["before"] or {}
            item["changes"] = {
                key: {"before": before.get(key), "after": value}
                for key, value in item["after"].items()
                if before.get(key) != value
            }
            output.append(item)
        return output

    def add_vendor_evidence(
        self,
        client_id: str,
        vendor_id: str,
        *,
        filename: str,
        media_type: str,
        content: bytes,
        added_by: str,
    ) -> str:
        """Keep the source document inside the user-chosen SQLite file."""
        import hashlib

        if not content:
            raise StoreError("An empty evidence file cannot be stored")
        digest = "sha256:" + hashlib.sha256(content).hexdigest()
        existing = self.find_vendor_evidence(client_id, vendor_id, digest)
        if existing:
            raise StoreError(
                f"This exact evidence file was already uploaded as {existing['filename']} "
                f"on {existing['added_at']}."
            )
        evidence_id = uuid.uuid4().hex
        self._connection.execute(
            "INSERT INTO vendor_evidence(evidence_id, client_id, vendor_id, filename, "
            "media_type, sha256, content, added_by, added_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                evidence_id, client_id, vendor_id, Path(filename).name,
                media_type or "application/octet-stream", digest, sqlite3.Binary(content),
                added_by.strip() or "Unknown user", datetime.now().isoformat(timespec="seconds"),
            ),
        )
        return digest

    def find_vendor_evidence(self, client_id: str, vendor_id: str, sha256: str) -> Optional[dict[str, Any]]:
        row = self._connection.execute(
            "SELECT evidence_id, filename, media_type, sha256, added_by, added_at, "
            "length(content) AS bytes FROM vendor_evidence WHERE client_id = ? AND vendor_id = ? "
            "AND sha256 = ? ORDER BY added_at DESC LIMIT 1",
            (client_id, vendor_id, sha256),
        ).fetchone()
        return dict(row) if row else None

    def get_vendor_evidence(self, evidence_id: str) -> dict[str, Any]:
        row = self._connection.execute(
            "SELECT * FROM vendor_evidence WHERE evidence_id = ?", (evidence_id,)
        ).fetchone()
        if not row:
            raise StoreError("Evidence document not found")
        return dict(row)

    def record_evidence_review(
        self,
        *,
        evidence_id: str,
        client_id: str,
        vendor_id: str,
        parsed: Mapping[str, Any],
        confirmed: Mapping[str, Any],
        conflicts: Mapping[str, Any],
        confirmed_by: str,
        classification_history: list[Mapping[str, Any]],
    ) -> str:
        """Append a human-confirmed document review and its year-wise history."""
        review_id = uuid.uuid4().hex
        now = datetime.now().isoformat(timespec="seconds")
        with self._transaction():
            self._connection.execute(
                "INSERT INTO vendor_evidence_reviews(review_id, evidence_id, client_id, vendor_id, "
                "parsed_json, confirmed_json, conflicts_json, confirmed_by, confirmed_at) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    review_id, evidence_id, client_id, vendor_id,
                    _dump(dict(parsed)), _dump(dict(confirmed)), _dump(dict(conflicts)),
                    confirmed_by.strip() or "Unknown user", now,
                ),
            )
            self._connection.executemany(
                "INSERT INTO vendor_classification_history(client_id, vendor_id, "
                "classification_year, enterprise_class, classification_date, evidence_id, "
                "evidence_source, recorded_by, recorded_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        client_id, vendor_id, item["classification_year"],
                        str(item["enterprise_class"]).upper(),
                        item.get("classification_date") or None, evidence_id,
                        "UDYAM_CERTIFICATE", confirmed_by.strip() or "Unknown user", now,
                    )
                    for item in classification_history
                ],
            )
        return review_id

    def latest_evidence_review(self, client_id: str, vendor_id: str) -> Optional[dict[str, Any]]:
        row = self._connection.execute(
            "SELECT * FROM vendor_evidence_reviews WHERE client_id = ? AND vendor_id = ? "
            "ORDER BY confirmed_at DESC LIMIT 1",
            (client_id, vendor_id),
        ).fetchone()
        if not row:
            return None
        item = dict(row)
        for key in ("parsed_json", "confirmed_json", "conflicts_json"):
            item[key.removesuffix("_json")] = _load(item.pop(key), {})
        return item

    def classification_history(self, client_id: str, vendor_id: str) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            "SELECT classification_year, enterprise_class, classification_date, evidence_id, "
            "evidence_source, recorded_by, recorded_at FROM vendor_classification_history "
            "WHERE client_id = ? AND vendor_id = ? ORDER BY classification_year DESC, history_id DESC",
            (client_id, vendor_id),
        ).fetchall()
        latest: dict[str, dict[str, Any]] = {}
        for row in rows:
            latest.setdefault(row["classification_year"], dict(row))
        return list(latest.values())

    def upsert_vendor_metadata(self, client_id: str, vendor_id: str, **values: Any) -> None:
        current = self.load_vendor_metadata(client_id, vendor_id)
        merged = {**current, **{key: value for key, value in values.items() if value is not None}}
        now = datetime.now().isoformat(timespec="seconds")
        self._connection.execute(
            "INSERT INTO vendor_metadata(client_id, vendor_id, pan, gstin, contact, "
            "registration_status, verification_source, organisation_type, incorporation_date, "
            "commencement_date, registered_address, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(client_id, vendor_id) DO UPDATE SET pan=excluded.pan, gstin=excluded.gstin, "
            "contact=excluded.contact, registration_status=excluded.registration_status, "
            "verification_source=excluded.verification_source, organisation_type=excluded.organisation_type, "
            "incorporation_date=excluded.incorporation_date, commencement_date=excluded.commencement_date, "
            "registered_address=excluded.registered_address, updated_at=excluded.updated_at",
            (
                client_id, vendor_id, merged.get("pan", ""), merged.get("gstin", ""),
                merged.get("contact", ""), merged.get("registration_status", ""),
                merged.get("verification_source", ""), merged.get("organisation_type", ""),
                merged.get("incorporation_date") or None, merged.get("commencement_date") or None,
                merged.get("registered_address", ""), now,
            ),
        )

    def load_vendor_metadata(self, client_id: str, vendor_id: str) -> dict[str, Any]:
        row = self._connection.execute(
            "SELECT * FROM vendor_metadata WHERE client_id = ? AND vendor_id = ?",
            (client_id, vendor_id),
        ).fetchone()
        return dict(row) if row else {}

    def list_vendor_evidence(self, client_id: str, vendor_id: str) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            "SELECT evidence_id, filename, media_type, sha256, added_by, added_at, length(content) AS bytes "
            "FROM vendor_evidence WHERE client_id = ? AND vendor_id = ? ORDER BY added_at",
            (client_id, vendor_id),
        ).fetchall()
        return [dict(row) for row in rows]

    def save_completed_run(
        self,
        analysis_id: str,
        run: ComputationRun,
        purchases: list[PurchaseLine],
        payments: list[PaymentLine],
        udyam: Mapping[str, UdyamRecord],
        *,
        entity_pan: str = "",
        acceptance_plus_days: int = 0,
        supersedes_run_id: Optional[str] = None,
    ) -> str:
        analysis = self._connection.execute(
            "SELECT client_id FROM analysis_sessions WHERE analysis_id = ?", (analysis_id,)
        ).fetchone()
        if not analysis:
            raise StoreError(f"Analysis not found: {analysis_id}")
        run_id = uuid.uuid4().hex
        now = datetime.now().isoformat(timespec="seconds")
        with self._transaction():
            self._connection.execute(
                "INSERT INTO completed_runs(run_id, analysis_id, client_id, entity_name, "
                "entity_pan, fy, operator, acceptance_policy, acceptance_plus_days, run_at, "
                "rule_pack_version, run_hash, statute_json, control_totals_json, warnings_json, "
                "purchases_json, payments_json, udyam_snapshot_json, findings_json, "
                "disallowance_total, interest_total, excluded_total, supersedes_run_id, completed_at) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    analysis_id,
                    analysis["client_id"],
                    run.entity_name,
                    entity_pan,
                    run.fy,
                    run.operator,
                    run.acceptance_policy,
                    int(acceptance_plus_days),
                    run.run_at.isoformat(),
                    run.rule_pack_version,
                    run.run_hash(),
                    _dump(run.statute),
                    _dump(run.control_totals),
                    _dump(run.warnings),
                    _dump([asdict(item) for item in purchases]),
                    _dump([asdict(item) for item in payments]),
                    _dump({key: asdict(value) for key, value in udyam.items()}),
                    _dump([asdict(item) for item in run.findings]),
                    str(run.disallowance_total),
                    str(run.interest_total),
                    str(run.excluded_total),
                    supersedes_run_id,
                    now,
                ),
            )
            self._connection.execute(
                "UPDATE analysis_sessions SET stage = 'results', updated_at = ? WHERE analysis_id = ?",
                (now, analysis_id),
            )
        return run_id

    def _run_from_row(self, row: sqlite3.Row) -> tuple[ComputationRun, list[PurchaseLine], list[PaymentLine], dict[str, UdyamRecord]]:
        run = ComputationRun(
            entity_name=row["entity_name"],
            fy=row["fy"],
            operator=row["operator"],
            acceptance_policy=row["acceptance_policy"],
            run_at=datetime.fromisoformat(row["run_at"]),
            rule_pack_version=row["rule_pack_version"],
            findings=[Finding(**item) for item in _load(row["findings_json"], [])],
            control_totals=_load(row["control_totals_json"], {}),
            warnings=_load(row["warnings_json"], []),
        )
        purchases = [PurchaseLine(**item) for item in _load(row["purchases_json"], [])]
        payments = [PaymentLine(**item) for item in _load(row["payments_json"], [])]
        udyam = {
            key: UdyamRecord(**value)
            for key, value in _load(row["udyam_snapshot_json"], {}).items()
        }
        if run.run_hash() != row["run_hash"]:
            raise StoreError(
                f"Stored run {row['run_id']} failed its reproduction check: "
                f"expected {row['run_hash']}, reconstructed {run.run_hash()}."
            )
        return run, purchases, payments, udyam

    def load_completed_run(
        self, run_id: str
    ) -> tuple[ComputationRun, list[PurchaseLine], list[PaymentLine], dict[str, UdyamRecord]]:
        row = self._connection.execute(
            "SELECT * FROM completed_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if not row:
            raise StoreError(f"Completed run not found: {run_id}")
        return self._run_from_row(row)

    def list_completed_runs(self, client_id: Optional[str] = None) -> list[dict[str, Any]]:
        query = (
            "SELECT run_id, analysis_id, client_id, entity_name, entity_pan, fy, run_at, "
            "run_hash, disallowance_total, interest_total, excluded_total, completed_at "
            "FROM completed_runs"
        )
        parameters: tuple[Any, ...] = ()
        if client_id:
            query += " WHERE client_id = ?"
            parameters = (client_id,)
        query += " ORDER BY completed_at DESC"
        return [dict(row) for row in self._connection.execute(query, parameters).fetchall()]

    def record_export(
        self,
        run_id: str,
        output_folder: str | Path,
        files: list[str | Path],
        *,
        exported_by: str,
    ) -> int:
        row = self._connection.execute(
            "SELECT 1 FROM completed_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if not row:
            raise StoreError(f"Completed run not found: {run_id}")
        cursor = self._connection.execute(
            "INSERT INTO run_exports(run_id, exported_at, exported_by, output_folder, files_json) "
            "VALUES(?, ?, ?, ?, ?)",
            (
                run_id,
                datetime.now().isoformat(timespec="seconds"),
                exported_by,
                str(Path(output_folder).resolve()),
                _dump([str(Path(item).resolve()) for item in files]),
            ),
        )
        return int(cursor.lastrowid)

    def load_latest_analysis(self) -> Optional[StoredAnalysis]:
        row = self._connection.execute(
            "SELECT a.*, c.entity_name, c.pan FROM analysis_sessions a "
            "JOIN clients c ON c.client_id = a.client_id "
            "ORDER BY a.updated_at DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        purchases = [
            PurchaseLine(
                invoice_id=item["invoice_id"],
                vendor_id=item["vendor_id"],
                vendor_name_as_written=item["vendor_name"],
                invoice_date=date.fromisoformat(item["invoice_date"]),
                amount=Decimal(item["amount"]),
                grn_date=date.fromisoformat(item["grn_date"]) if item["grn_date"] else None,
                agreement_days=item["agreement_days"],
            )
            for item in self._connection.execute(
                "SELECT * FROM purchase_lines WHERE analysis_id = ? ORDER BY line_number",
                (row["analysis_id"],),
            ).fetchall()
        ]
        payments = [
            PaymentLine(
                invoice_id=item["invoice_id"],
                payment_date=date.fromisoformat(item["payment_date"]),
                amount=Decimal(item["amount"]),
            )
            for item in self._connection.execute(
                "SELECT * FROM payment_lines WHERE analysis_id = ? ORDER BY line_number",
                (row["analysis_id"],),
            ).fetchall()
        ]
        invoice_supplements = {
            item["invoice_id"]: InvoiceSupplement(
                invoice_id=item["invoice_id"],
                agreed_due_date=date.fromisoformat(item["agreed_due_date"])
                if item["agreed_due_date"] else None,
                actual_payment_date=date.fromisoformat(item["actual_payment_date"])
                if item["actual_payment_date"] else None,
                outstanding_amount=Decimal(item["outstanding_amount"])
                if item["outstanding_amount"] is not None else None,
                ledger_category=item["ledger_category"],
                remarks=item["remarks"],
            )
            for item in self._connection.execute(
                "SELECT * FROM invoice_supplements WHERE analysis_id = ?",
                (row["analysis_id"],),
            ).fetchall()
        }
        run_row = self._connection.execute(
            "SELECT run_id FROM completed_runs WHERE analysis_id = ? ORDER BY completed_at DESC LIMIT 1",
            (row["analysis_id"],),
        ).fetchone()
        return StoredAnalysis(
            analysis_id=row["analysis_id"],
            client_id=row["client_id"],
            entity_name=row["entity_name"],
            entity_pan=row["pan"],
            fy=row["fy"],
            stage=row["stage"],
            acceptance_policy=row["acceptance_policy"],
            acceptance_plus_days=row["acceptance_plus_days"],
            control_totals=_load(row["control_totals_json"]),
            purchases=purchases,
            payments=payments,
            udyam=self.load_vendor_master(row["client_id"]),
            invoice_supplements=invoice_supplements,
            completed_run_id=run_row["run_id"] if run_row else None,
            updated_at=row["updated_at"],
        )

    def backup(self, destination_folder: str | Path) -> Path:
        destination = _safe_database_folder(destination_folder)
        destination.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        target = destination / f"clock45-backup-{stamp}.sqlite3"
        suffix = 1
        while target.exists():
            target = destination / f"clock45-backup-{stamp}-{suffix}.sqlite3"
            suffix += 1
        backup_connection = sqlite3.connect(target)
        try:
            with self._lock:
                self._connection.backup(backup_connection)
            result = backup_connection.execute("PRAGMA integrity_check").fetchone()[0]
            if result != "ok":
                raise StoreError(f"Backup integrity check failed: {result}")
        finally:
            backup_connection.close()
        return target

    def restore(self, source_file: str | Path) -> None:
        source = Path(source_file).expanduser().resolve()
        if not source.is_file():
            raise StoreError(f"Backup file not found: {source}")
        source_connection = sqlite3.connect(source)
        try:
            integrity = source_connection.execute("PRAGMA integrity_check").fetchone()[0]
            version = source_connection.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            ).fetchone()
            if integrity != "ok":
                raise StoreError(f"Backup integrity check failed: {integrity}")
            if not version or not (1 <= int(version[0]) <= SCHEMA_VERSION):
                raise StoreError("The selected file is not a compatible 45-Day Clock backup")
            with self._lock:
                source_connection.backup(self._connection)
                self._configure()
                self._initialize()
        except sqlite3.DatabaseError as exc:
            raise StoreError(f"Could not restore backup: {exc}") from exc
        finally:
            source_connection.close()

    def integrity_check(self) -> str:
        return str(self._connection.execute("PRAGMA integrity_check").fetchone()[0])


class _Transaction:
    def __init__(self, store: Store) -> None:
        self.store = store

    def __enter__(self):
        self.store._lock.acquire()
        self.store._connection.execute("BEGIN IMMEDIATE")
        return self

    def __exit__(self, exception_type, exception, traceback):
        try:
            self.store._connection.execute("ROLLBACK" if exception_type else "COMMIT")
        finally:
            self.store._lock.release()
        return False
