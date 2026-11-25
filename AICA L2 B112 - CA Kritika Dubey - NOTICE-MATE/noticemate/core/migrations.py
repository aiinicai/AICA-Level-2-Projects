"""Versioned, additive schema migrations.

Rules:
* Migrations only ADD tables/columns/indexes. They never drop, rename or
  rewrite existing data, so v1 users, cases and records are preserved.
* Before any pending migration runs on an existing database, a full copy is
  written to <data_dir>/backups/ with SQLite's online backup API.
* Each migration runs in one transaction and bumps schema_version.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

MIGRATIONS: dict[int, list[str]] = {
    2: [
        # legal registry: source type, effective dates, applicability
        "ALTER TABLE legal_refs ADD COLUMN ref_type TEXT NOT NULL DEFAULT 'STATUTE'",
        "ALTER TABLE legal_refs ADD COLUMN effective_from TEXT",
        "ALTER TABLE legal_refs ADD COLUMN effective_to TEXT",
        "ALTER TABLE legal_refs ADD COLUMN applies_to TEXT",
        "ALTER TABLE legal_refs ADD COLUMN verification_note TEXT",
        # AI submissions: purpose + error classification
        "ALTER TABLE ai_submissions ADD COLUMN purpose TEXT NOT NULL DEFAULT 'GENERAL'",
        "ALTER TABLE ai_submissions ADD COLUMN error_kind TEXT",
        "ALTER TABLE ai_submissions ADD COLUMN related_id INTEGER",
        """CREATE TABLE IF NOT EXISTS ai_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            notice_id INTEGER REFERENCES notices(id) ON DELETE SET NULL,
            submission_id INTEGER REFERENCES ai_submissions(id) ON DELETE SET NULL,
            source TEXT NOT NULL CHECK (source IN ('LOCAL','AI','MERGED')),
            version INTEGER NOT NULL,
            content_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','ACCEPTED','REJECTED')),
            review_comment TEXT,
            reviewed_by INTEGER REFERENCES users(id),
            reviewed_at TEXT,
            created_by INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS ix_ai_analyses_case ON ai_analyses(case_id)",
        """CREATE TABLE IF NOT EXISTS research_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            issue_id INTEGER REFERENCES issues(id) ON DELETE SET NULL,
            question TEXT NOT NULL,
            content_json TEXT NOT NULL,
            submission_id INTEGER REFERENCES ai_submissions(id) ON DELETE SET NULL,
            live_research INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'UNVERIFIED' CHECK (status IN ('UNVERIFIED','PARTLY_VERIFIED','VERIFIED','DISCARDED')),
            created_by INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS draft_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            draft_id INTEGER NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
            section TEXT NOT NULL,
            comment TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','RESOLVED')),
            created_by INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL,
            resolved_by INTEGER REFERENCES users(id),
            resolved_at TEXT,
            resolution TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS draft_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draft_id INTEGER NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
            decision TEXT NOT NULL CHECK (decision IN ('APPROVED','REJECTED','CHANGES_REQUESTED')),
            comment TEXT,
            content_hash TEXT NOT NULL,
            reviewer_id INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS party_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            record_type TEXT NOT NULL CHECK (record_type IN ('LENDER','PARTNER_CAPITAL','CUSTOMER_ADVANCE')),
            party_name TEXT NOT NULL,
            amount REAL NOT NULL,
            txn_date TEXT,
            mode TEXT,
            evidence_json TEXT NOT NULL DEFAULT '{}',
            observations TEXT,
            issue_id INTEGER REFERENCES issues(id) ON DELETE SET NULL,
            created_by INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
    ],
    3: [
        # ---- V3: OCR page-level provenance ----
        "ALTER TABLE documents ADD COLUMN extraction_pages_json TEXT",
        # ---- V3: legal authorities with citation, applicability and verification ----
        """CREATE TABLE IF NOT EXISTS legal_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_key TEXT NOT NULL UNIQUE,
            source_class TEXT NOT NULL CHECK (source_class IN ('PRIMARY','SECONDARY','AI_SUGGESTION')),
            source_type TEXT NOT NULL CHECK (source_type IN ('ACT_SECTION','RULE','NOTIFICATION','CIRCULAR','INSTRUCTION',
                'CASE_LAW','COMMENTARY','ARTICLE','AI_OUTPUT','OTHER')),
            title TEXT NOT NULL,
            citation TEXT,
            issuing_body TEXT,
            court_level TEXT CHECK (court_level IS NULL OR court_level IN ('SUPREME_COURT','HIGH_COURT','ITAT','AAR_BAR','OTHER')),
            document_number TEXT,
            date_issued TEXT,
            effective_from TEXT,
            effective_to TEXT,
            act TEXT CHECK (act IS NULL OR act IN ('IT_ACT_1961','IT_ACT_2025','IT_RULES_1962','IT_RULES_2026','OTHER')),
            provision TEXT,
            pinpoint TEXT,
            excerpt TEXT,
            summary TEXT,
            applicability_note TEXT,
            ay_from TEXT,
            ay_to TEXT,
            official_url TEXT,
            url_is_official INTEGER NOT NULL DEFAULT 0,
            superseded_by INTEGER REFERENCES legal_sources(id),
            status TEXT NOT NULL DEFAULT 'UNVERIFIED' CHECK (status IN ('UNVERIFIED','VERIFIED','OUTDATED','NEEDS_CA_REVIEW')),
            origin TEXT NOT NULL DEFAULT 'USER' CHECK (origin IN ('USER','SEED','AI','IMPORTED_REGISTRY')),
            content_hash TEXT NOT NULL,
            verified_hash TEXT,
            created_by INTEGER REFERENCES users(id),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS propositions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            issue_id INTEGER REFERENCES issues(id) ON DELETE CASCADE,
            text TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT 'LEGAL' CHECK (kind IN ('LEGAL','FACTUAL','MIXED')),
            origin TEXT NOT NULL DEFAULT 'USER' CHECK (origin IN ('SYSTEM','USER','AI')),
            status TEXT NOT NULL DEFAULT 'UNVERIFIED' CHECK (status IN ('UNVERIFIED','VERIFIED','NEEDS_CA_REVIEW','REJECTED')),
            ca_note TEXT,
            verified_hash TEXT,
            decided_by INTEGER REFERENCES users(id),
            decided_at TEXT,
            created_by INTEGER REFERENCES users(id),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS ix_prop_issue ON propositions(issue_id)",
        """CREATE TABLE IF NOT EXISTS proposition_sources (
            proposition_id INTEGER NOT NULL REFERENCES propositions(id) ON DELETE CASCADE,
            source_id INTEGER NOT NULL REFERENCES legal_sources(id) ON DELETE CASCADE,
            stance TEXT NOT NULL CHECK (stance IN ('SUPPORTS','DIFFERS','DISTINGUISHABLE','CONTEXT')),
            relevance_note TEXT,
            pinpoint TEXT,
            added_by INTEGER REFERENCES users(id),
            added_at TEXT NOT NULL,
            PRIMARY KEY (proposition_id, source_id)
        )""",
        """CREATE TABLE IF NOT EXISTS proposition_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposition_id INTEGER NOT NULL REFERENCES propositions(id) ON DELETE CASCADE,
            fact_type TEXT NOT NULL CHECK (fact_type IN ('NOTICE_TEXT','DOCUMENT_SPAN','EVIDENCE_ITEM','RECON_RUN','CLIENT_EXPLANATION','ASSUMPTION')),
            basis TEXT NOT NULL CHECK (basis IN ('ESTABLISHED','DOCUMENT_AVAILABLE','CLIENT_EXPLANATION','ASSUMPTION','UNRESOLVED')),
            document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
            page INTEGER,
            quote TEXT,
            evidence_item_id INTEGER REFERENCES evidence_items(id) ON DELETE SET NULL,
            recon_run_id INTEGER REFERENCES recon_runs(id) ON DELETE SET NULL,
            note TEXT,
            added_by INTEGER REFERENCES users(id),
            added_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS verification_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL CHECK (entity_type IN ('SOURCE','PROPOSITION')),
            entity_id INTEGER NOT NULL,
            case_id INTEGER,
            decision TEXT NOT NULL,
            checked_url TEXT,
            checked_pinpoint TEXT,
            applicability_confirmed INTEGER NOT NULL DEFAULT 0,
            note TEXT,
            content_hash TEXT NOT NULL,
            decided_by INTEGER NOT NULL REFERENCES users(id),
            decided_at TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS ix_vlog_entity ON verification_log(entity_type, entity_id)",
        """CREATE TRIGGER IF NOT EXISTS vlog_no_update BEFORE UPDATE ON verification_log
           BEGIN SELECT RAISE(ABORT, 'verification_log is append-only'); END""",
        """CREATE TRIGGER IF NOT EXISTS vlog_no_delete BEFORE DELETE ON verification_log
           BEGIN SELECT RAISE(ABORT, 'verification_log is append-only'); END""",
        # ---- V3: CA approval bound to an exact draft version (explicit link) ----
        "ALTER TABLE approvals ADD COLUMN draft_version INTEGER",
    ],
    4: [
        # ---- V3.1: the notice's own heading for each query ----
        "ALTER TABLE issues ADD COLUMN title TEXT",
        # ---- V3.1: content-based mapping of document passages to issues ----
        """CREATE TABLE IF NOT EXISTS doc_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            issue_id INTEGER NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
            document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            passage TEXT NOT NULL,
            passage_kind TEXT NOT NULL,
            score REAL NOT NULL,
            reason TEXT NOT NULL,
            certainty TEXT NOT NULL CHECK (certainty IN ('STRONG','UNCERTAIN')),
            status TEXT NOT NULL DEFAULT 'AUTO' CHECK (status IN ('AUTO','ACCEPTED','REJECTED')),
            created_at TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS ix_doc_links_issue ON doc_links(issue_id)",
    ],
    5: [
        # ---- V3.2: where in the document a matched passage sits (page / sheet / table row) ----
        "ALTER TABLE doc_links ADD COLUMN location TEXT",
        # ---- V3.2: in-app settings (no secrets are ever stored here) ----
        """CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_by INTEGER REFERENCES users(id),
            updated_at TEXT NOT NULL
        )""",
        # ---- V3.2: AI-written issue paragraphs, with the evidence each paragraph relies on ----
        """CREATE TABLE IF NOT EXISTS ai_issue_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            issue_id INTEGER NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            paragraphs_json TEXT NOT NULL,
            sources_json TEXT NOT NULL,
            checks_json TEXT NOT NULL,
            context_hash TEXT NOT NULL,
            submission_id INTEGER REFERENCES ai_submissions(id) ON DELETE SET NULL,
            created_by INTEGER REFERENCES users(id),
            created_at TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS ix_ai_issue_drafts_issue ON ai_issue_drafts(issue_id)",
        # local-only map to restore redacted identifiers in a cloud answer; never transmitted
        "ALTER TABLE ai_submissions ADD COLUMN restore_map_json TEXT",
    ],
}

LATEST = max(MIGRATIONS)


def current_version(conn: sqlite3.Connection) -> int:
    r = conn.execute("SELECT version FROM schema_version").fetchone()
    return int(r[0]) if r else 1


def backup_database(db_path: Path, backups_dir: Path, label: str) -> Path:
    backups_dir.mkdir(parents=True, exist_ok=True)
    dest = backups_dir / f"noticemate_{label}_{datetime.now():%Y%m%d_%H%M%S}.db"
    src = sqlite3.connect(db_path)
    dst = sqlite3.connect(dest)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return dest


def _column_exists(conn: sqlite3.Connection, table: str, col: str) -> bool:
    return any(r[1] == col for r in conn.execute(f"PRAGMA table_info({table})"))


def apply_migrations(db_path: Path, backups_dir: Path, *, existed_before: bool) -> dict:
    conn = sqlite3.connect(db_path, isolation_level=None)
    try:
        ver = current_version(conn)
        pending = [v for v in sorted(MIGRATIONS) if v > ver]
        if not pending:
            return {"from": ver, "to": ver, "backup": None}
        backup = None
        has_data = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0
        if existed_before and has_data:
            backup = str(backup_database(db_path, backups_dir, f"pre_v{pending[-1]}"))
        for v in pending:
            conn.execute("BEGIN IMMEDIATE")
            try:
                for stmt in MIGRATIONS[v]:
                    s = stmt.strip()
                    if s.upper().startswith("ALTER TABLE") and " ADD COLUMN " in s.upper():
                        parts = s.split()
                        table, col = parts[2], parts[5]
                        if _column_exists(conn, table, col):
                            continue
                    conn.execute(s)
                conn.execute("UPDATE schema_version SET version=?", (v,))
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
        return {"from": ver, "to": pending[-1], "backup": backup}
    finally:
        conn.close()
