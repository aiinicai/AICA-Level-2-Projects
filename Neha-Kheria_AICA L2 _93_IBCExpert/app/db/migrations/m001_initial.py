"""Schema version 1: complete normalized application foundation."""

VERSION = 1
NAME = "initial_complete_schema"

SQL = r"""
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    display_name TEXT NOT NULL,
    master_envelope BLOB NOT NULL,
    throttle_json TEXT NOT NULL DEFAULT '{"failed_attempts":0,"locked_until":null}',
    totp_secret_encrypted BLOB,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    is_sensitive INTEGER NOT NULL DEFAULT 0 CHECK (is_sensitive IN (0,1)),
    updated_at TEXT NOT NULL
);

CREATE TABLE clients (
    id INTEGER PRIMARY KEY,
    client_uuid TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    corporate_debtor TEXT,
    cin TEXT,
    pan_encrypted BLOB,
    gst TEXT,
    registered_office TEXT,
    industry TEXT,
    primary_email TEXT,
    primary_phone TEXT,
    notes TEXT,
    custom_fields_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','ARCHIVED','DELETED')),
    archived_at TEXT,
    deleted_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    row_version INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX ix_clients_name ON clients(name COLLATE NOCASE);
CREATE INDEX ix_clients_status ON clients(status);
CREATE INDEX ix_clients_cin ON clients(cin);

CREATE TABLE matters (
    id INTEGER PRIMARY KEY,
    matter_uuid TEXT NOT NULL UNIQUE,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    matter_type TEXT NOT NULL,
    case_number TEXT,
    nclt_bench TEXT,
    applicant TEXT,
    initiating_provision TEXT,
    date_of_default TEXT,
    demand_notice_date TEXT,
    filing_date TEXT,
    admission_date TEXT,
    insolvency_commencement_date TEXT,
    irp TEXT,
    rp TEXT,
    liquidator TEXT,
    advisor TEXT,
    notes TEXT,
    custom_fields_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','STAYED','CLOSED','ARCHIVED')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    row_version INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX ix_matters_client ON matters(client_id);
CREATE INDEX ix_matters_status ON matters(status);

CREATE TABLE client_change_history (
    id INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    matter_id INTEGER REFERENCES matters(id) ON DELETE CASCADE,
    field_name TEXT NOT NULL,
    previous_value TEXT,
    new_value TEXT,
    changed_at TEXT NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    audit_entry_id INTEGER,
    change_group TEXT NOT NULL
);
CREATE INDEX ix_client_history_client ON client_change_history(client_id, changed_at DESC);

CREATE TABLE creditors (
    id INTEGER PRIMARY KEY,
    matter_id INTEGER NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    creditor_type TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    address TEXT,
    identification_encrypted BLOB,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE claims (
    id INTEGER PRIMARY KEY,
    matter_id INTEGER NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    creditor_id INTEGER REFERENCES creditors(id) ON DELETE SET NULL,
    claim_number TEXT,
    claimed_amount_minor INTEGER NOT NULL DEFAULT 0 CHECK (claimed_amount_minor >= 0),
    admitted_amount_minor INTEGER CHECK (admitted_amount_minor IS NULL OR admitted_amount_minor >= 0),
    currency TEXT NOT NULL DEFAULT 'INR',
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','UNDER_REVIEW','ADMITTED','PARTLY_ADMITTED','REJECTED','WITHDRAWN')),
    received_date TEXT,
    decision_date TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX ix_claims_matter_status ON claims(matter_id, status);

CREATE TABLE coc_members (
    id INTEGER PRIMARY KEY,
    matter_id INTEGER NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    creditor_id INTEGER REFERENCES creditors(id) ON DELETE SET NULL,
    member_name TEXT NOT NULL,
    voting_share_basis_points INTEGER NOT NULL CHECK (voting_share_basis_points BETWEEN 0 AND 10000),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
    effective_from TEXT,
    effective_to TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE meetings (
    id INTEGER PRIMARY KEY,
    matter_id INTEGER NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    meeting_type TEXT NOT NULL,
    sequence_number INTEGER,
    scheduled_at TEXT NOT NULL,
    venue_or_mode TEXT,
    agenda TEXT,
    minutes TEXT,
    status TEXT NOT NULL DEFAULT 'SCHEDULED' CHECK (status IN ('DRAFT','SCHEDULED','HELD','ADJOURNED','CANCELLED')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE voting (
    id INTEGER PRIMARY KEY,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    resolution_text TEXT NOT NULL,
    member_id INTEGER REFERENCES coc_members(id) ON DELETE SET NULL,
    vote TEXT CHECK (vote IN ('FOR','AGAINST','ABSTAIN','NOT_CAST')),
    voting_share_basis_points INTEGER CHECK (voting_share_basis_points BETWEEN 0 AND 10000),
    cast_at TEXT
);

CREATE TABLE assets (
    id INTEGER PRIMARY KEY,
    matter_id INTEGER NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    asset_type TEXT,
    location TEXT,
    book_value_minor INTEGER,
    estimated_value_minor INTEGER,
    currency TEXT NOT NULL DEFAULT 'INR',
    status TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE litigation (
    id INTEGER PRIMARY KEY,
    matter_id INTEGER NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    forum TEXT,
    case_number TEXT,
    title TEXT NOT NULL,
    next_hearing_date TEXT,
    status TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE professional_fees (
    id INTEGER PRIMARY KEY,
    matter_id INTEGER NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    professional_name TEXT NOT NULL,
    role TEXT,
    invoice_number TEXT,
    invoice_date TEXT,
    amount_minor INTEGER NOT NULL CHECK (amount_minor >= 0),
    tax_minor INTEGER NOT NULL DEFAULT 0 CHECK (tax_minor >= 0),
    currency TEXT NOT NULL DEFAULT 'INR',
    payment_status TEXT NOT NULL DEFAULT 'PENDING',
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE process_definitions (
    id INTEGER PRIMARY KEY,
    definition_uuid TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    process_type TEXT NOT NULL,
    version INTEGER NOT NULL,
    verification_status TEXT NOT NULL CHECK (verification_status IN ('VERIFIED','UNVERIFIED','REVIEW_REQUIRED','SUPERSEDED')),
    effective_from TEXT,
    effective_to TEXT,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
    created_at TEXT NOT NULL,
    UNIQUE(process_type, version)
);

CREATE TABLE process_stage_definitions (
    id INTEGER PRIMARY KEY,
    process_definition_id INTEGER NOT NULL REFERENCES process_definitions(id) ON DELETE CASCADE,
    stage_key TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    stage_name TEXT NOT NULL,
    statutory_basis TEXT,
    citation_id INTEGER,
    trigger_field TEXT,
    due_offset_days INTEGER,
    due_calendar_type TEXT NOT NULL DEFAULT 'CALENDAR' CHECK (due_calendar_type IN ('CALENDAR','BUSINESS')),
    due_rule_json TEXT NOT NULL DEFAULT '{}',
    required_documents_json TEXT NOT NULL DEFAULT '[]',
    checklist_template_json TEXT NOT NULL DEFAULT '[]',
    form_template_id INTEGER,
    communication_template_id INTEGER,
    verification_status TEXT NOT NULL CHECK (verification_status IN ('VERIFIED','UNVERIFIED','REVIEW_REQUIRED','SUPERSEDED')),
    UNIQUE(process_definition_id, stage_key)
);

CREATE TABLE process_instances (
    id INTEGER PRIMARY KEY,
    instance_uuid TEXT NOT NULL UNIQUE,
    matter_id INTEGER NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    process_definition_id INTEGER NOT NULL REFERENCES process_definitions(id),
    started_at TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','COMPLETED','CANCELLED','ARCHIVED')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE process_stages (
    id INTEGER PRIMARY KEY,
    process_instance_id INTEGER NOT NULL REFERENCES process_instances(id) ON DELETE CASCADE,
    stage_definition_id INTEGER NOT NULL REFERENCES process_stage_definitions(id),
    trigger_date TEXT,
    computed_due_date TEXT,
    status TEXT NOT NULL DEFAULT 'NOT_STARTED' CHECK (status IN ('NOT_STARTED','IN_PROGRESS','DONE','NOT_APPLICABLE','OVERDUE')),
    completion_date TEXT,
    notes TEXT,
    last_recalculated_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(process_instance_id, stage_definition_id)
);
CREATE INDEX ix_process_stage_due ON process_stages(computed_due_date, status);

CREATE TABLE process_stage_documents (
    process_stage_id INTEGER NOT NULL REFERENCES process_stages(id) ON DELETE CASCADE,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    attached_at TEXT NOT NULL,
    PRIMARY KEY(process_stage_id, document_id)
);

CREATE TABLE checklists (
    id INTEGER PRIMARY KEY,
    process_stage_id INTEGER NOT NULL REFERENCES process_stages(id) ON DELETE CASCADE,
    item_key TEXT NOT NULL,
    label TEXT NOT NULL,
    completed INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0,1)),
    completed_at TEXT,
    notes TEXT,
    sequence_number INTEGER NOT NULL DEFAULT 0,
    UNIQUE(process_stage_id, item_key)
);

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    matter_id INTEGER REFERENCES matters(id) ON DELETE CASCADE,
    process_stage_id INTEGER REFERENCES process_stages(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    due_at TEXT,
    priority TEXT NOT NULL DEFAULT 'NORMAL' CHECK (priority IN ('LOW','NORMAL','HIGH','CRITICAL')),
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','IN_PROGRESS','DONE','CANCELLED','OVERDUE')),
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX ix_tasks_due_status ON tasks(status, due_at);

CREATE TABLE deadlines (
    id INTEGER PRIMARY KEY,
    matter_id INTEGER NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    process_stage_id INTEGER REFERENCES process_stages(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    trigger_date TEXT,
    due_date TEXT NOT NULL,
    citation_id INTEGER,
    verification_status TEXT NOT NULL CHECK (verification_status IN ('VERIFIED','UNVERIFIED','REVIEW_REQUIRED','SUPERSEDED')),
    status TEXT NOT NULL DEFAULT 'UPCOMING' CHECK (status IN ('UPCOMING','DUE_TODAY','OVERDUE','COMPLETED','WAIVED')),
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(process_stage_id)
);
CREATE INDEX ix_deadlines_due ON deadlines(status, due_date);

CREATE TABLE forms (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    form_code TEXT,
    category TEXT,
    classification TEXT NOT NULL CHECK (classification IN ('VERIFIED_OFFICIAL','PRACTITIONER_TEMPLATE','DRAFT_UNVERIFIED')),
    template_type TEXT NOT NULL CHECK (template_type IN ('DOCX','HTML','XLSX','TEXT')),
    template_path TEXT,
    template_content BLOB,
    verification_status TEXT NOT NULL CHECK (verification_status IN ('VERIFIED','UNVERIFIED','REVIEW_REQUIRED','SUPERSEDED')),
    citation_id INTEGER,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE form_versions (
    id INTEGER PRIMARY KEY,
    form_id INTEGER NOT NULL REFERENCES forms(id) ON DELETE CASCADE,
    matter_id INTEGER REFERENCES matters(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    merged_data_json TEXT NOT NULL,
    editable_content BLOB NOT NULL,
    output_type TEXT NOT NULL,
    output_path TEXT,
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(form_id, matter_id, version_number)
);

CREATE TABLE communication_drafts (
    id INTEGER PRIMARY KEY,
    matter_id INTEGER REFERENCES matters(id) ON DELETE CASCADE,
    process_stage_id INTEGER REFERENCES process_stages(id) ON DELETE SET NULL,
    draft_type TEXT NOT NULL,
    recipient TEXT,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','FINAL','ARCHIVED')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    document_uuid TEXT NOT NULL UNIQUE,
    client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE,
    matter_id INTEGER REFERENCES matters(id) ON DELETE CASCADE,
    legal_entity_type TEXT,
    legal_entity_id INTEGER,
    original_filename TEXT NOT NULL,
    safe_filename TEXT NOT NULL,
    media_type TEXT NOT NULL,
    category TEXT,
    content_hash TEXT NOT NULL,
    encrypted_path TEXT NOT NULL,
    size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
    source TEXT,
    tags_json TEXT NOT NULL DEFAULT '[]',
    version INTEGER NOT NULL DEFAULT 1,
    ocr_status TEXT NOT NULL DEFAULT 'NOT_REQUIRED' CHECK (ocr_status IN ('NOT_REQUIRED','PENDING','COMPLETE','FAILED','UNAVAILABLE')),
    review_status TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED' CHECK (review_status IN ('ACCEPTED','REVIEW_REQUIRED','REJECTED')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(content_hash, client_id, matter_id)
);
CREATE INDEX ix_documents_client ON documents(client_id, created_at DESC);
CREATE INDEX ix_documents_matter ON documents(matter_id, created_at DESC);
CREATE INDEX ix_documents_hash ON documents(content_hash);

CREATE TABLE document_text (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER,
    text_content TEXT NOT NULL,
    extraction_method TEXT NOT NULL,
    confidence REAL,
    created_at TEXT NOT NULL
);
CREATE INDEX ix_document_text_doc ON document_text(document_id, page_number);

CREATE TABLE statutes (
    id INTEGER PRIMARY KEY,
    statute_uuid TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    short_title TEXT,
    statute_type TEXT NOT NULL,
    jurisdiction TEXT NOT NULL DEFAULT 'India',
    enactment_date TEXT,
    commencement_date TEXT,
    identifier TEXT,
    verification_status TEXT NOT NULL CHECK (verification_status IN ('VERIFIED','UNVERIFIED','REVIEW_REQUIRED','SUPERSEDED')),
    source_document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX ix_statutes_title ON statutes(title COLLATE NOCASE);

CREATE TABLE legal_provisions (
    id INTEGER PRIMARY KEY,
    provision_uuid TEXT NOT NULL,
    statute_id INTEGER NOT NULL REFERENCES statutes(id) ON DELETE CASCADE,
    parent_id INTEGER REFERENCES legal_provisions(id) ON DELETE CASCADE,
    provision_type TEXT NOT NULL,
    number_label TEXT,
    heading TEXT,
    text_content TEXT NOT NULL,
    effective_from TEXT,
    effective_to TEXT,
    source_document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    source_page INTEGER,
    amendment_identifier TEXT,
    verification_status TEXT NOT NULL CHECK (verification_status IN ('VERIFIED','UNVERIFIED','REVIEW_REQUIRED','SUPERSEDED')),
    supersedes_id INTEGER REFERENCES legal_provisions(id) ON DELETE SET NULL,
    imported_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(provision_uuid, effective_from)
);
CREATE INDEX ix_legal_provision_statute ON legal_provisions(statute_id, provision_type, number_label);
CREATE INDEX ix_legal_provision_dates ON legal_provisions(effective_from, effective_to);

CREATE TABLE amendments (
    id INTEGER PRIMARY KEY,
    statute_id INTEGER NOT NULL REFERENCES statutes(id) ON DELETE CASCADE,
    identifier TEXT NOT NULL,
    title TEXT NOT NULL,
    effective_date TEXT,
    source_document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    source_page INTEGER,
    verification_status TEXT NOT NULL CHECK (verification_status IN ('VERIFIED','UNVERIFIED','REVIEW_REQUIRED','SUPERSEDED')),
    notes TEXT,
    imported_at TEXT NOT NULL
);

CREATE TABLE circulars (
    id INTEGER PRIMARY KEY,
    identifier TEXT,
    title TEXT NOT NULL,
    issuing_authority TEXT,
    issue_date TEXT,
    text_content TEXT,
    source_document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    verification_status TEXT NOT NULL CHECK (verification_status IN ('VERIFIED','UNVERIFIED','REVIEW_REQUIRED','SUPERSEDED')),
    imported_at TEXT NOT NULL
);

CREATE TABLE notifications (
    id INTEGER PRIMARY KEY,
    identifier TEXT,
    title TEXT NOT NULL,
    issuing_authority TEXT,
    issue_date TEXT,
    effective_date TEXT,
    text_content TEXT,
    source_document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    verification_status TEXT NOT NULL CHECK (verification_status IN ('VERIFIED','UNVERIFIED','REVIEW_REQUIRED','SUPERSEDED')),
    imported_at TEXT NOT NULL
);

CREATE TABLE judgments (
    id INTEGER PRIMARY KEY,
    judgment_uuid TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    neutral_citation TEXT,
    reported_citation TEXT,
    court TEXT NOT NULL,
    bench TEXT,
    judgment_date TEXT,
    case_number TEXT,
    parties TEXT,
    text_content TEXT NOT NULL,
    holding_summary TEXT,
    source_document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    source_page INTEGER,
    verification_status TEXT NOT NULL CHECK (verification_status IN ('VERIFIED','UNVERIFIED','REVIEW_REQUIRED','SUPERSEDED')),
    imported_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX ix_judgments_court_date ON judgments(court, judgment_date);
CREATE INDEX ix_judgments_citation ON judgments(neutral_citation, reported_citation);

CREATE TABLE citations (
    id INTEGER PRIMARY KEY,
    citation_text TEXT NOT NULL,
    statute_id INTEGER REFERENCES statutes(id) ON DELETE CASCADE,
    provision_id INTEGER REFERENCES legal_provisions(id) ON DELETE CASCADE,
    judgment_id INTEGER REFERENCES judgments(id) ON DELETE CASCADE,
    source_document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    source_page INTEGER,
    verification_status TEXT NOT NULL CHECK (verification_status IN ('VERIFIED','UNVERIFIED','REVIEW_REQUIRED','SUPERSEDED')),
    created_at TEXT NOT NULL,
    CHECK (statute_id IS NOT NULL OR provision_id IS NOT NULL OR judgment_id IS NOT NULL OR source_document_id IS NOT NULL)
);

CREATE TABLE legal_cross_references (
    id INTEGER PRIMARY KEY,
    from_entity_type TEXT NOT NULL,
    from_entity_id INTEGER NOT NULL,
    to_entity_type TEXT NOT NULL,
    to_entity_id INTEGER NOT NULL,
    relationship_type TEXT NOT NULL,
    notes TEXT,
    verification_status TEXT NOT NULL CHECK (verification_status IN ('VERIFIED','UNVERIFIED','REVIEW_REQUIRED','SUPERSEDED')),
    created_at TEXT NOT NULL,
    UNIQUE(from_entity_type, from_entity_id, to_entity_type, to_entity_id, relationship_type)
);

CREATE TABLE recommendations (
    id INTEGER PRIMARY KEY,
    matter_id INTEGER NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    process_stage_id INTEGER REFERENCES process_stages(id) ON DELETE SET NULL,
    priority TEXT NOT NULL CHECK (priority IN ('LOW','NORMAL','HIGH','CRITICAL')),
    title TEXT NOT NULL,
    action_text TEXT NOT NULL,
    reason TEXT NOT NULL,
    citation_id INTEGER NOT NULL REFERENCES citations(id),
    source_document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    source_page INTEGER,
    applicable_due_date TEXT,
    related_case_law_json TEXT NOT NULL DEFAULT '[]',
    verification_status TEXT NOT NULL CHECK (verification_status IN ('VERIFIED','UNVERIFIED','REVIEW_REQUIRED','SUPERSEDED')),
    rule_key TEXT NOT NULL,
    dismissed INTEGER NOT NULL DEFAULT 0 CHECK (dismissed IN (0,1)),
    generated_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(matter_id, rule_key, applicable_due_date)
);
CREATE INDEX ix_recommendations_matter ON recommendations(matter_id, dismissed, priority);

CREATE TABLE audit_entries (
    id INTEGER PRIMARY KEY,
    event_uuid TEXT NOT NULL UNIQUE,
    occurred_at TEXT NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    summary TEXT NOT NULL,
    details_json TEXT NOT NULL,
    previous_hash TEXT NOT NULL,
    entry_hash TEXT NOT NULL UNIQUE
);

CREATE TABLE imports (
    id INTEGER PRIMARY KEY,
    import_uuid TEXT NOT NULL UNIQUE,
    import_type TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_hash TEXT,
    status TEXT NOT NULL CHECK (status IN ('PENDING','RUNNING','COMPLETE','PARTIAL','FAILED','REVIEW_REQUIRED')),
    total_items INTEGER NOT NULL DEFAULT 0,
    imported_items INTEGER NOT NULL DEFAULT 0,
    rejected_items INTEGER NOT NULL DEFAULT 0,
    error_log TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE backups (
    id INTEGER PRIMARY KEY,
    backup_uuid TEXT NOT NULL UNIQUE,
    path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('CREATING','VALID','INVALID','RESTORED','DELETED')),
    created_at TEXT NOT NULL,
    verified_at TEXT,
    restored_at TEXT
);

CREATE TABLE licences (
    id INTEGER PRIMARY KEY,
    licence_id TEXT NOT NULL UNIQUE,
    licence_type TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    organisation TEXT,
    issued_at TEXT NOT NULL,
    starts_at TEXT NOT NULL,
    expires_at TEXT,
    device_request_code TEXT,
    device_allowance INTEGER NOT NULL DEFAULT 1 CHECK (device_allowance > 0),
    signed_payload TEXT NOT NULL,
    signature TEXT NOT NULL,
    activation_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ACTIVE','EXPIRED','REVOKED','REPLACED','INVALID')),
    installed_at TEXT NOT NULL,
    last_validated_at TEXT
);

CREATE TABLE licence_features (
    id INTEGER PRIMARY KEY,
    licence_id INTEGER NOT NULL REFERENCES licences(id) ON DELETE CASCADE,
    feature_key TEXT NOT NULL,
    enabled INTEGER NOT NULL CHECK (enabled IN (0,1)),
    UNIQUE(licence_id, feature_key)
);

CREATE TABLE licence_events (
    id INTEGER PRIMARY KEY,
    occurred_at TEXT NOT NULL,
    event_type TEXT NOT NULL,
    licence_id TEXT,
    summary TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE trial_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    installation_id TEXT NOT NULL UNIQUE,
    started_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    highest_seen_at TEXT NOT NULL,
    last_checked_at TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('TRIAL','EXPIRED','CLOCK_ANOMALY','LICENSED')),
    state_digest TEXT NOT NULL
);

CREATE TABLE activation_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    request_code TEXT NOT NULL,
    active_licence_id TEXT,
    activation_id TEXT,
    credential_digest TEXT,
    activated_at TEXT,
    last_validated_at TEXT
);

CREATE TABLE plugin_configuration (
    id INTEGER PRIMARY KEY,
    plugin_key TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    version TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0,1)),
    permissions_json TEXT NOT NULL DEFAULT '[]',
    config_encrypted BLOB,
    updated_at TEXT NOT NULL
);

CREATE TABLE event_outbox (
    id INTEGER PRIMARY KEY,
    event_uuid TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    processed_at TEXT
);

CREATE TABLE deadline_recalculation_history (
    id INTEGER PRIMARY KEY,
    process_stage_id INTEGER NOT NULL REFERENCES process_stages(id) ON DELETE CASCADE,
    previous_trigger_date TEXT,
    new_trigger_date TEXT,
    previous_due_date TEXT,
    new_due_date TEXT,
    reason TEXT NOT NULL,
    recalculated_at TEXT NOT NULL,
    audit_entry_id INTEGER REFERENCES audit_entries(id) ON DELETE SET NULL
);

CREATE VIRTUAL TABLE search_index USING fts5(
    entity_type UNINDEXED,
    entity_id UNINDEXED,
    title,
    body,
    citation,
    verification_status UNINDEXED,
    tokenize='unicode61 remove_diacritics 2',
    prefix='2 3 4'
);
"""
