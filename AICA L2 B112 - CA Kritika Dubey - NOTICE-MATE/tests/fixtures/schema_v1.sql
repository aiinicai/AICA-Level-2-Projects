PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('ADMIN','CA','STAFF')),
    membership_no TEXT,                -- ICAI membership no. (CA role), optional
    password_hash TEXT NOT NULL,
    failed_logins INTEGER NOT NULL DEFAULT 0,
    locked INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_ref TEXT NOT NULL UNIQUE,
    assessee_name TEXT NOT NULL,
    assessee_category TEXT NOT NULL,   -- INDIVIDUAL, HUF, FIRM, LLP, COMPANY_DOMESTIC, AOP_BOI, OTHER
    pan TEXT,                          -- stored locally only; never sent to AI
    assessment_year TEXT,              -- e.g. 2026-27 (1961 Act) or tax year label
    status TEXT NOT NULL DEFAULT 'OPEN',
    party_names TEXT NOT NULL DEFAULT '[]',  -- JSON list of names to redact
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS case_members (
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    PRIMARY KEY (case_id, user_id)
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    original_name TEXT NOT NULL,
    stored_name TEXT NOT NULL,
    extension TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    encrypted INTEGER NOT NULL DEFAULT 0,
    doc_type TEXT NOT NULL DEFAULT 'UNCLASSIFIED',
    doc_type_confidence REAL NOT NULL DEFAULT 0,
    doc_type_confirmed INTEGER NOT NULL DEFAULT 0,
    extraction_status TEXT NOT NULL DEFAULT 'PENDING',  -- PENDING, OK, OCR, PARTIAL, FAILED
    extraction_notes TEXT,
    page_count INTEGER,
    is_annexure INTEGER NOT NULL DEFAULT 0,
    annexure_label TEXT,
    uploaded_by INTEGER NOT NULL REFERENCES users(id),
    uploaded_at TEXT NOT NULL,
    UNIQUE (case_id, sha256)
);

CREATE TABLE IF NOT EXISTS doc_text (
    document_id INTEGER PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    tables_json TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS doc_index (
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    term TEXT NOT NULL,
    freq INTEGER NOT NULL,
    PRIMARY KEY (document_id, term)
);
CREATE INDEX IF NOT EXISTS ix_doc_index_term ON doc_index(term);

CREATE TABLE IF NOT EXISTS notices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES documents(id),
    particulars_json TEXT NOT NULL,     -- extracted fields with source snippets & status
    deadline_verified INTEGER NOT NULL DEFAULT 0,
    deadline_verified_by INTEGER REFERENCES users(id),
    deadline_value TEXT,
    applicable_law_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    notice_id INTEGER REFERENCES notices(id) ON DELETE SET NULL,
    seq INTEGER NOT NULL,
    query_text TEXT NOT NULL,
    category TEXT NOT NULL,
    amount REAL,
    analysis_json TEXT NOT NULL,
    strategy TEXT,
    strategy_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    issue_id INTEGER NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
    requirement TEXT NOT NULL,
    document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    status TEXT NOT NULL CHECK (status IN ('SUFFICIENT','PARTIALLY_SUFFICIENT','INSUFFICIENT','NOT_PROVIDED','CONTRADICTORY','REQUIRES_VERIFICATION')),
    establishes TEXT,
    does_not_establish TEXT,
    supports_explanation TEXT,
    inconsistency TEXT,
    source TEXT NOT NULL DEFAULT 'SYSTEM',  -- SYSTEM (auto-mapped) or USER
    updated_by INTEGER REFERENCES users(id),
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recon_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    recon_type TEXT NOT NULL,
    inputs_json TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tax_computations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    inputs_json TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS legal_refs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ref_key TEXT NOT NULL UNIQUE,
    act TEXT NOT NULL,
    provision TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    source_url TEXT,
    status TEXT NOT NULL CHECK (status IN ('VERIFIED','REQUIRES_VERIFICATION')),
    verified_by INTEGER REFERENCES users(id),
    verified_at TEXT,
    origin TEXT NOT NULL DEFAULT 'USER'
);

CREATE TABLE IF NOT EXISTS info_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    content_json TEXT NOT NULL,
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    content_json TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    UNIQUE (case_id, version)
);

CREATE TABLE IF NOT EXISTS review_checklists (
    draft_id INTEGER NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
    item_key TEXT NOT NULL,
    checked INTEGER NOT NULL DEFAULT 0,
    note TEXT,
    checked_by INTEGER REFERENCES users(id),
    checked_at TEXT,
    PRIMARY KEY (draft_id, item_key)
);

CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_id INTEGER NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
    content_hash TEXT NOT NULL,
    approved_by INTEGER NOT NULL REFERENCES users(id),
    approver_membership_no TEXT,
    declaration TEXT NOT NULL,
    approved_at TEXT NOT NULL,
    revoked INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ai_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    task TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDING_APPROVAL','BLOCKED','SENT','FAILED','CANCELLED')),
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    payload_chars INTEGER NOT NULL,
    pii_summary_json TEXT NOT NULL,
    block_reason TEXT,
    pending_payload TEXT,         -- redacted payload; cleared after send unless retention enabled
    response_text TEXT,           -- AI suggestion (from redacted input), labelled as such in UI
    prepared_by INTEGER NOT NULL REFERENCES users(id),
    approved_by INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL,
    sent_at TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    user_id INTEGER,
    case_id INTEGER,
    event TEXT NOT NULL,
    meta_json TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    entry_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_audit_case ON audit_log(case_id);

CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_log
BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_log
BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
