"""Schema version 2: structured local-import staging and manual review queue."""

VERSION = 2
NAME = "manual_review_structured_imports"

SQL = r"""
CREATE TABLE import_mapping_profiles (
    id INTEGER PRIMARY KEY,
    profile_uuid TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    target_type TEXT NOT NULL CHECK (target_type IN ('CLIENT','LEGAL_STATUTE','LEGAL_JUDGMENT')),
    source_format TEXT NOT NULL CHECK (source_format IN ('CSV','XLSX','DOCX','JSON')),
    mapping_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(name, target_type, source_format)
);

CREATE TABLE manual_review_queue (
    id INTEGER PRIMARY KEY,
    review_uuid TEXT NOT NULL UNIQUE,
    import_id INTEGER REFERENCES imports(id) ON DELETE SET NULL,
    document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    item_type TEXT NOT NULL CHECK (item_type IN ('STRUCTURED_ROW','LEGAL_SOURCE_DOCUMENT','DOCUMENT_CLASSIFICATION')),
    target_type TEXT NOT NULL CHECK (target_type IN ('CLIENT','LEGAL_STATUTE','LEGAL_JUDGMENT','LEGAL_SOURCE_DOCUMENT','DOCUMENT_METADATA')),
    title TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    source_excerpt TEXT,
    reason TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','RESOLVED','REJECTED')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    resolved_at TEXT,
    resolved_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    resolution_note TEXT,
    created_entity_type TEXT,
    created_entity_id INTEGER
);
CREATE INDEX ix_manual_review_status ON manual_review_queue(status, created_at DESC);
CREATE INDEX ix_manual_review_import ON manual_review_queue(import_id, id);
CREATE INDEX ix_manual_review_document ON manual_review_queue(document_id);
"""
