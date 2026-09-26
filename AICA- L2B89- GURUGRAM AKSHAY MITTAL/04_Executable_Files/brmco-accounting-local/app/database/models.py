"""SQLite schema for the Local Host.

SQLite stores operational data only: settings, cached Tally masters, validated
import batches, import history and the audit log. It never replaces Tally's
books — Tally remains the accounting system of record.
"""

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS app_metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_settings (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Cached Tally masters, one row per (company, type, name).
CREATE TABLE IF NOT EXISTS tally_masters (
    company     TEXT NOT NULL,
    master_type TEXT NOT NULL,          -- ledger | group | stock_item | unit | voucher_type
    name        TEXT NOT NULL,
    name_key    TEXT NOT NULL,          -- lower-cased name for case-insensitive lookup
    parent      TEXT,
    extra_json  TEXT,
    synced_at   TEXT NOT NULL,
    PRIMARY KEY (company, master_type, name_key)
);

CREATE TABLE IF NOT EXISTS master_sync_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    synced_at   TEXT NOT NULL,
    company     TEXT NOT NULL,
    master_type TEXT NOT NULL,
    count       INTEGER NOT NULL,
    status      TEXT NOT NULL,
    message     TEXT
);

-- An uploaded + validated Excel file. Posting always reads the vouchers stored
-- here, so nothing that failed validation can ever reach Tally.
CREATE TABLE IF NOT EXISTS import_batches (
    id              TEXT PRIMARY KEY,
    created_at      TEXT NOT NULL,
    voucher_kind    TEXT NOT NULL,
    file_name       TEXT NOT NULL,
    stored_file     TEXT,
    company_name    TEXT,
    tally_company   TEXT,
    financial_year  TEXT,
    demo_mode       INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL,      -- invalid | validated | posted | partial | failed | demo
    voucher_count   INTEGER NOT NULL DEFAULT 0,
    row_count       INTEGER NOT NULL DEFAULT 0,
    error_count     INTEGER NOT NULL DEFAULT 0,
    warning_count   INTEGER NOT NULL DEFAULT 0,
    vouchers_json   TEXT,
    issues_json     TEXT,
    xml_file        TEXT
);

CREATE TABLE IF NOT EXISTS import_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id        TEXT REFERENCES import_batches(id),
    created_at      TEXT NOT NULL,
    company_name    TEXT,
    tally_company   TEXT,
    financial_year  TEXT,
    voucher_kind    TEXT NOT NULL,
    voucher_numbers TEXT,
    excel_file_name TEXT,
    xml_file_name   TEXT,
    record_count    INTEGER NOT NULL DEFAULT 0,
    tally_status    TEXT NOT NULL,      -- SUCCESS | PARTIAL | FAILED | DEMO
    created_count   INTEGER NOT NULL DEFAULT 0,
    altered_count   INTEGER NOT NULL DEFAULT 0,
    ignored_count   INTEGER NOT NULL DEFAULT 0,
    error_count     INTEGER NOT NULL DEFAULT 0,
    tally_response  TEXT,
    error_details   TEXT,
    demo_mode       INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_history_created ON import_history(created_at);

-- Vouchers Tally confirmed as created; used for duplicate detection.
CREATE TABLE IF NOT EXISTS posted_vouchers (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    history_id     INTEGER REFERENCES import_history(id),
    company        TEXT NOT NULL,
    financial_year TEXT,
    voucher_kind   TEXT NOT NULL,
    exact_key      TEXT,
    fuzzy_key      TEXT NOT NULL,
    voucher_label  TEXT,
    voucher_date   TEXT,
    party_ledger   TEXT,
    amount         TEXT,
    posted_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_posted_exact ON posted_vouchers(company, exact_key);
CREATE INDEX IF NOT EXISTS ix_posted_fuzzy ON posted_vouchers(company, fuzzy_key);

CREATE TABLE IF NOT EXISTS audit_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at   TEXT NOT NULL,
    action       TEXT NOT NULL,
    company_name TEXT,
    voucher_kind TEXT,
    batch_id     TEXT,
    details      TEXT
);
CREATE INDEX IF NOT EXISTS ix_audit_created ON audit_log(created_at);
"""
