# Data dictionary

Generated from the database comments by `tools/build_dictionary.mjs`. To change a description, edit the comment in `sql/database_schema.sql` and regenerate.

**33 tables.** 22 carry a `tenant_id` and are isolated per client; the rest are global reference data, firm-level data or identity tables (each is listed below as "Scope").

All ids are `uuid`. All timestamps are `timestamptz`. Every client table has `id`, `tenant_id`, `created_at` and `updated_at` unless noted. Composite foreign keys `(id, tenant_id)` stop a row from pointing at another client's row.

## activity_data_categories

Links a processing activity to the categories of personal data it uses.

Scope: one client (tenant)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `tenant_id` | uuid | yes |  | The client institution that owns this row. Never changes after creation; every policy checks it. |
| `activity_id` | uuid | yes |  | The processing activity concerned. |
| `data_category_id` | uuid | yes |  | The data category concerned. |

## activity_systems

Links a processing activity to the systems that hold its data.

Scope: one client (tenant)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `tenant_id` | uuid | yes |  | The client institution that owns this row. Never changes after creation; every policy checks it. |
| `activity_id` | uuid | yes |  | The processing activity concerned. |
| `system_id` | uuid | yes |  | The system concerned. |

## activity_vendors

Links a processing activity to the vendors that receive or process its data.

Scope: one client (tenant)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `tenant_id` | uuid | yes |  | The client institution that owns this row. Never changes after creation; every policy checks it. |
| `activity_id` | uuid | yes |  | The processing activity concerned. |
| `vendor_id` | uuid | yes |  | The vendor concerned. |

## applicability_decisions

Applicability questions with outcome and rationale, recorded per assessment.

Scope: one client (tenant)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `tenant_id` | uuid | yes |  | The client institution that owns this row. Never changes after creation; every policy checks it. |
| `assessment_id` | uuid | yes |  | The assessment this row belongs to. |
| `question_code` | text | yes |  | Code of the applicability question. |
| `question_text` | text | yes |  | Text of the applicability question as asked. |
| `outcome` | text | yes |  | applicable, not_applicable or needs_legal_review. A rationale is always required. |
| `rationale` | text | yes |  | The reason for the decision. |
| `evidence_id` | uuid |  |  | The evidence record concerned. |
| `assessed_by` | uuid |  |  | User who made the assessment (set by the database, not the browser). |
| `assessed_at` | timestamp with time zone |  |  | When the assessor last recorded a result. |
| `created_at` | timestamp with time zone | yes | `now()` | When the row was created. |
| `updated_at` | timestamp with time zone | yes | `now()` | When the row last changed (set by the database). |

Rules enforced by the database:

- `CHECK ((outcome = ANY (ARRAY['applicable'::text, 'not_applicable'::text, 'needs_legal_review'::text])))`
- `CHECK ((length(btrim(rationale)) > 0))`

## assessment_items

One row per control assessed. Keeps the control version used.

Scope: one client (tenant)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `tenant_id` | uuid | yes |  | The client institution that owns this row. Never changes after creation; every policy checks it. |
| `assessment_id` | uuid | yes |  | The assessment this row belongs to. |
| `control_version_id` | uuid | yes |  | The exact control version assessed. Later versions never change this. |
| `applicability` | text | yes | `'applicable'::text` | Legal applicability, kept separate from implementation status. |
| `applicability_rationale` | text |  |  | Why the control applies, does not apply or needs legal review. |
| `result` | text | yes | `'not_assessed'::text` | implemented_verified, partial, gap, not_assessed or not_applicable. not_assessed is never counted as compliant. |
| `evidence_quality` | text | yes | `'none'::text` | none, submitted, verified or insufficient. Verified needs linked verified evidence. |
| `risk_level` | text |  |  | low, medium, high or critical. |
| `assessor_notes` | text |  |  | Assessor notes. Visible to anyone who can read the item. |
| `recommendation` | text |  |  | What the assessor recommends. |
| `owner_user_id` | uuid |  |  | The person responsible for providing evidence or fixing the gap. |
| `target_date` | date |  |  | Date the owner aims to finish. |
| `assessed_by` | uuid |  |  | Set automatically when a result is recorded. |
| `assessed_at` | timestamp with time zone |  |  | When the assessor last recorded a result. |
| `created_at` | timestamp with time zone | yes | `now()` | When the row was created. |
| `updated_at` | timestamp with time zone | yes | `now()` | When the row last changed (set by the database). |

Rules enforced by the database:

- `CHECK ((applicability = ANY (ARRAY['applicable'::text, 'not_applicable'::text, 'needs_legal_review'::text])))`
- `CHECK (((applicability = 'not_applicable'::text) = (result = 'not_applicable'::text)))`
- `CHECK (((applicability = 'applicable'::text) OR (length(btrim(COALESCE(applicability_rationale, ''::text))) > 0)))`
- `CHECK (((result <> 'implemented_verified'::text) OR (evidence_quality = 'verified'::text)))`
- `CHECK ((evidence_quality = ANY (ARRAY['none'::text, 'submitted'::text, 'verified'::text, 'insufficient'::text])))`
- `CHECK ((result = ANY (ARRAY['implemented_verified'::text, 'partial'::text, 'gap'::text, 'not_assessed'::text, 'not_applicable'::text])))`
- `CHECK ((risk_level = ANY (ARRAY['low'::text, 'medium'::text, 'high'::text, 'critical'::text])))`

## assessment_snapshots

Frozen copy of an assessment at each approval, so history survives reopening.

Scope: one client (tenant)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `tenant_id` | uuid | yes |  | The client institution that owns this row. Never changes after creation; every policy checks it. |
| `assessment_id` | uuid | yes |  | The assessment this row belongs to. |
| `version_no` | integer | yes |  | Version number. Approved versions are never edited; a change creates a new version. |
| `snapshot` | jsonb | yes |  | Frozen copy of the approved content as JSON. |
| `created_by` | uuid |  |  | User who created the row. |
| `created_at` | timestamp with time zone | yes | `now()` | When the row was created. |

## assessments

A gap assessment for one client and period.

Scope: one client (tenant)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `tenant_id` | uuid | yes |  | The client institution that owns this row. Never changes after creation; every policy checks it. |
| `engagement_id` | uuid | yes |  | The engagement this row belongs to. |
| `title` | text | yes |  | Short title. |
| `period_start` | date | yes |  | First day covered. |
| `period_end` | date | yes |  | Last day covered. |
| `status` | text | yes | `'draft'::text` | draft, in_progress, submitted_for_review, returned, approved or reopened. Changed only through the review functions. |
| `version_no` | integer | yes | `1` | Increases each time an approved assessment is reopened. |
| `prepared_by` | uuid | yes | `auth.uid()` | The preparer. The reviewer must be a different person. |
| `reviewer_id` | uuid |  |  | The assigned firm reviewer. |
| `submitted_at` | timestamp with time zone |  |  | When it was submitted for review. |
| `approved_by` | uuid |  |  | User who approved. |
| `approved_at` | timestamp with time zone |  |  | When the approval was recorded. |
| `shared_with_client` | boolean | yes | `false` | When true, client users can see the assessment. Set on approval. |
| `limitations` | text |  |  | Scope exclusions, assumptions and items not assessed. |
| `created_at` | timestamp with time zone | yes | `now()` | When the row was created. |
| `updated_at` | timestamp with time zone | yes | `now()` | When the row last changed (set by the database). |

Rules enforced by the database:

- `CHECK ((period_end >= period_start))`
- `CHECK (((reviewer_id IS NULL) OR (reviewer_id <> prepared_by)))`
- `CHECK (((status <> 'approved'::text) OR ((approved_by IS NOT NULL) AND (approved_at IS NOT NULL))))`
- `CHECK ((status = ANY (ARRAY['draft'::text, 'in_progress'::text, 'submitted_for_review'::text, 'returned'::text, 'approved'::text, 'reopened'::text])))`

## audit_events

Append-only log of material actions. Holds identifiers and status changes, never personal data or document content.

Scope: one client (tenant)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | bigint | yes |  | Unique identifier. |
| `tenant_id` | uuid |  |  | The client institution that owns this row. Never changes after creation; every policy checks it. |
| `firm_id` | uuid |  |  | The CA firm concerned. |
| `actor_id` | uuid |  |  | User who did it. Empty when the database itself did it. |
| `action` | text | yes |  | What happened, for example insert, update or export. |
| `entity_type` | text | yes |  | Table of the row that changed. |
| `entity_id` | uuid |  |  | Id of the row that changed. |
| `details` | jsonb | yes | `'{}'::jsonb` | Small JSON with changed column names and status or role transitions. |
| `occurred_at` | timestamp with time zone | yes | `now()` | When it happened. |

## control_versions

A versioned control: statement, question, evidence and test. Immutable once approved.

Scope: not tenant-owned (global, firm-level or identity)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `control_id` | uuid | yes |  | The control this version belongs to. |
| `version_no` | integer | yes |  | Version number. Approved versions are never edited; a change creates a new version. |
| `legal_reference` | text | yes |  | Section or rule the control rests on. |
| `statement` | text | yes |  | What the control requires. |
| `applicability_logic` | text |  |  | When the control applies. |
| `commencement_status` | text | yes | `'Requires Verification'::text` | Library commencement status for this control version. |
| `effective_date` | date |  |  | Date from which the provision applies. Verify against the Gazette. |
| `assessment_question` | text | yes |  | The question the assessor answers. |
| `required_evidence` | text |  |  | What evidence supports a result. |
| `test_procedure` | text |  |  | How the assessor tests the control. |
| `expected_result` | text |  |  | What a satisfactory result looks like. |
| `risk_guidance` | text |  |  | How to judge the risk of a gap. |
| `source_version_id` | uuid |  |  | The legal source version this relies on. |
| `review_status` | text | yes | `'draft'::text` | draft, in_review, approved or retired. Approval needs a second person and, outside demos, a verified source. |
| `approved_by` | uuid |  |  | Reviewer who approved the version. |
| `approved_at` | timestamp with time zone |  |  | When the approval was recorded. |
| `retired_at` | timestamp with time zone |  |  | When the version was retired. |
| `is_demo` | boolean | yes | `false` | True for synthetic demonstration records. |
| `change_note` | text |  |  | What changed from the previous version. |
| `created_by` | uuid |  | `auth.uid()` | User who created the row. |
| `created_at` | timestamp with time zone | yes | `now()` | When the row was created. |

Rules enforced by the database:

- `CHECK (((review_status <> ALL (ARRAY['approved'::text, 'retired'::text])) OR ((approved_by IS NOT NULL) AND (approved_at IS NOT NULL))))`
- `CHECK ((commencement_status = ANY (ARRAY['In Force — Verified'::text, 'Scheduled — Verified'::text, 'Not Yet in Force — Verified'::text, 'Requires Verification'::text, 'Superseded'::text])))`
- `CHECK ((review_status = ANY (ARRAY['draft'::text, 'in_review'::text, 'approved'::text, 'retired'::text])))`
- `CHECK ((version_no >= 1))`

## controls

A stable control identity. The wording lives in control_versions.

Scope: not tenant-owned (global, firm-level or identity)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `scope` | text | yes |  | global (platform library) or firm (one firm's library). |
| `firm_id` | uuid |  |  | The CA firm concerned. |
| `control_code` | text | yes |  | Stable ID such as NTC-01, unique within the owner. |
| `title` | text | yes |  | Short title. |
| `legal_source_id` | uuid |  |  | The legal source concerned. |
| `created_by` | uuid |  | `auth.uid()` | User who created the row. |
| `created_at` | timestamp with time zone | yes | `now()` | When the row was created. |

Rules enforced by the database:

- `CHECK ((((scope = 'global'::text) AND (firm_id IS NULL)) OR ((scope = 'firm'::text) AND (firm_id IS NOT NULL))))`
- `CHECK ((length(btrim(control_code)) > 0))`
- `CHECK ((scope = ANY (ARRAY['global'::text, 'firm'::text])))`

## corrective_actions

Remediation actions, from an assessment gap or raised independently.

Scope: one client (tenant)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `tenant_id` | uuid | yes |  | The client institution that owns this row. Never changes after creation; every policy checks it. |
| `assessment_item_id` | uuid |  |  | The assessment item concerned. |
| `title` | text | yes |  | Short title. |
| `issue` | text | yes |  | What is wrong or missing. |
| `risk_level` | text | yes | `'medium'::text` | low, medium, high or critical. Set by a person, with the rationale. |
| `risk_rationale` | text |  |  | Why this risk level was chosen. |
| `owner_user_id` | uuid |  |  | Person responsible. |
| `due_date` | date |  |  | Date the action is due. |
| `dependencies` | text |  |  | Other work this action depends on. |
| `status` | text | yes | `'open'::text` | open, in_progress, blocked, submitted_for_review, closed or accepted_risk. Changed only through the action functions. |
| `closure_evidence_id` | uuid |  |  | Evidence that shows the action is complete. |
| `closed_at` | timestamp with time zone |  |  | When the action was closed. |
| `closure_verified_by` | uuid |  |  | Reviewer who verified closure. |
| `closure_verified_at` | timestamp with time zone |  |  | When closure evidence was verified. |
| `risk_accepted_by` | uuid |  |  | Authorised approver of an accepted risk. |
| `risk_acceptance_rationale` | text |  |  | Why the risk is accepted. Required. |
| `risk_accepted_at` | timestamp with time zone |  |  | When management accepted the risk. |
| `created_by` | uuid |  | `auth.uid()` | User who created the row. |
| `created_at` | timestamp with time zone | yes | `now()` | When the row was created. |
| `updated_at` | timestamp with time zone | yes | `now()` | When the row last changed (set by the database). |

Rules enforced by the database:

- `CHECK (((status <> 'closed'::text) OR ((closure_evidence_id IS NOT NULL) AND (closure_verified_by IS NOT NULL) AND (closure_verified_at IS NOT NULL) AND (closed_at IS NOT NULL))))`
- `CHECK (((status <> 'accepted_risk'::text) OR ((risk_accepted_by IS NOT NULL) AND (risk_accepted_at IS NOT NULL) AND (length(btrim(COALESCE(risk_acceptance_rationale, ''::text))) > 0))))`
- `CHECK ((risk_level = ANY (ARRAY['low'::text, 'medium'::text, 'high'::text, 'critical'::text])))`
- `CHECK ((status = ANY (ARRAY['open'::text, 'in_progress'::text, 'blocked'::text, 'submitted_for_review'::text, 'closed'::text, 'accepted_risk'::text])))`
- `CHECK ((length(btrim(title)) > 0))`

## data_categories

Global reference list of personal-data categories. Maintained by the platform, readable by signed-in users.

Scope: not tenant-owned (global, firm-level or identity)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `code` | text | yes |  | Short stable code. |
| `name` | text | yes |  | Display name. |
| `category_group` | text | yes |  | Group for display, for example Student or Special case. |
| `is_special_case` | boolean | yes | `false` | True for categories that need extra care, such as children or biometric data. A flag for review, not a legal classification. |
| `description` | text |  |  | Free-text description. |

## departments

A department of the client institution, such as Admissions, Exams, Accounts, HR.

Scope: one client (tenant)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `tenant_id` | uuid | yes |  | The client institution that owns this row. Never changes after creation; every policy checks it. |
| `name` | text | yes |  | Display name. |
| `coordinator_user_id` | uuid |  |  | The department coordinator who may edit inventory records for this department. |
| `archived_at` | timestamp with time zone |  |  | Set when the department is archived. |
| `created_at` | timestamp with time zone | yes | `now()` | When the row was created. |
| `updated_at` | timestamp with time zone | yes | `now()` | When the row last changed (set by the database). |

Rules enforced by the database:

- `CHECK ((length(btrim(name)) > 0))`

## engagement_assignments

Grants a firm user access to one client. This, not firm membership, opens client content.

Scope: one client (tenant)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `tenant_id` | uuid | yes |  | The client institution that owns this row. Never changes after creation; every policy checks it. |
| `engagement_id` | uuid | yes |  | The engagement this row belongs to. |
| `user_id` | uuid | yes |  | The user concerned. |
| `role` | text | yes |  | team_member works on the client. reviewer reviews and signs off. |
| `status` | text | yes | `'active'::text` | active or revoked. Revoking removes access on the next request. |
| `granted_by` | uuid |  | `auth.uid()` | Who granted access. |
| `granted_at` | timestamp with time zone | yes | `now()` | When access was granted. |
| `revoked_at` | timestamp with time zone |  |  | When access was withdrawn. |

Rules enforced by the database:

- `CHECK ((role = ANY (ARRAY['team_member'::text, 'reviewer'::text])))`
- `CHECK ((status = ANY (ARRAY['active'::text, 'revoked'::text])))`

## engagement_notes

Notes on an engagement. firm_only notes are never visible to client users.

Scope: one client (tenant)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `tenant_id` | uuid | yes |  | The client institution that owns this row. Never changes after creation; every policy checks it. |
| `engagement_id` | uuid | yes |  | The engagement this row belongs to. |
| `visibility` | text | yes | `'firm_only'::text` | firm_only or client_visible. |
| `body` | text | yes |  | Text of the note. |
| `author_id` | uuid | yes | `auth.uid()` | User who wrote the note. |
| `created_at` | timestamp with time zone | yes | `now()` | When the row was created. |
| `updated_at` | timestamp with time zone | yes | `now()` | When the row last changed (set by the database). |

Rules enforced by the database:

- `CHECK ((length(btrim(body)) > 0))`
- `CHECK ((visibility = ANY (ARRAY['firm_only'::text, 'client_visible'::text])))`

## engagements

The firm's engagement with a client: scope, period and status.

Scope: one client (tenant)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `tenant_id` | uuid | yes |  | The client institution that owns this row. Never changes after creation; every policy checks it. |
| `firm_id` | uuid | yes |  | Copy of the tenant's firm, enforced by a composite foreign key. |
| `title` | text | yes |  | Short title. |
| `scope` | text |  |  | global (platform library) or firm (one firm's library). |
| `status` | text | yes | `'planned'::text` | Current status. Allowed values are in the rules below. |
| `onboarding_status` | text | yes | `'not_started'::text` | not_started, in_progress or complete. |
| `missing_information` | text |  |  | What the firm is still waiting for from the client. |
| `start_date` | date |  |  | Start date. |
| `assessment_period_start` | date |  |  | First day of the period being assessed. |
| `assessment_period_end` | date |  |  | Last day of the period being assessed. |
| `created_by` | uuid |  | `auth.uid()` | User who created the row. |
| `created_at` | timestamp with time zone | yes | `now()` | When the row was created. |
| `updated_at` | timestamp with time zone | yes | `now()` | When the row last changed (set by the database). |

Rules enforced by the database:

- `CHECK (((assessment_period_end IS NULL) OR (assessment_period_start IS NULL) OR (assessment_period_end >= assessment_period_start)))`
- `CHECK ((onboarding_status = ANY (ARRAY['not_started'::text, 'in_progress'::text, 'complete'::text])))`
- `CHECK ((status = ANY (ARRAY['planned'::text, 'active'::text, 'review'::text, 'closed'::text])))`

## evidence_records

Evidence metadata. File bytes live in the private evidence storage bucket.

Scope: one client (tenant)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `tenant_id` | uuid | yes |  | The client institution that owns this row. Never changes after creation; every policy checks it. |
| `title` | text | yes |  | Short title. |
| `description` | text |  |  | Free-text description. |
| `category` | text | yes | `'document'::text` | policy, procedure, record, screenshot, contract, training, log, report, other or document. |
| `source` | text |  |  | Where the item came from. |
| `status` | text | yes | `'missing'::text` | missing, submitted, under_review, verified, rejected or expired. Changed only through decide_evidence. |
| `storage_bucket` | text | yes | `'evidence'::text` | Storage bucket holding the file (private). |
| `storage_path` | text |  |  | Path in the private bucket. Always starts with the tenant id. |
| `file_name` | text |  |  | Original file name. Do not put personal data in file names. |
| `mime_type` | text |  |  | File type, checked against an allow-list. |
| `size_bytes` | bigint |  |  | File size in bytes. |
| `sha256` | text |  |  | SHA-256 of the file, to show it has not changed. |
| `version_no` | integer | yes | `1` | Version of this evidence item. |
| `supersedes_id` | uuid |  |  | The earlier evidence record this replaces. |
| `valid_until` | date |  |  | Date after which the evidence needs refreshing. |
| `uploaded_by` | uuid |  |  | Who uploaded the file. |
| `uploaded_at` | timestamp with time zone |  |  | When the file was uploaded. |
| `activity_id` | uuid |  |  | The processing activity concerned. |
| `assessment_id` | uuid |  |  | The assessment this row belongs to. |
| `assessment_item_id` | uuid |  |  | The assessment item concerned. |
| `corrective_action_id` | uuid |  |  | The corrective action this evidence supports. |
| `created_at` | timestamp with time zone | yes | `now()` | When the row was created. |
| `updated_at` | timestamp with time zone | yes | `now()` | When the row last changed (set by the database). |

Rules enforced by the database:

- `CHECK ((category = ANY (ARRAY['policy'::text, 'procedure'::text, 'record'::text, 'screenshot'::text, 'contract'::text, 'training'::text, 'log'::text, 'report'::text, 'other'::text, 'document'::text])))`
- `CHECK (((storage_path IS NULL) OR (storage_path ~~ ((tenant_id)::text || '/%'::text))))`
- `CHECK (((status = 'missing'::text) OR ((storage_path IS NOT NULL) AND (uploaded_by IS NOT NULL) AND (uploaded_at IS NOT NULL))))`
- `CHECK (((sha256 IS NULL) OR (sha256 ~ '^[0-9a-f]{64}$'::text)))`
- `CHECK (((size_bytes IS NULL) OR ((size_bytes > 0) AND (size_bytes <= 26214400))))`
- `CHECK ((status = ANY (ARRAY['missing'::text, 'submitted'::text, 'under_review'::text, 'verified'::text, 'rejected'::text, 'expired'::text])))`
- `CHECK ((length(btrim(title)) > 0))`

## evidence_reviews

Append-only record of evidence review decisions.

Scope: one client (tenant)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `tenant_id` | uuid | yes |  | The client institution that owns this row. Never changes after creation; every policy checks it. |
| `evidence_id` | uuid | yes |  | The evidence record concerned. |
| `reviewer_id` | uuid | yes |  | The reviewer. |
| `decision` | text | yes |  | under_review, verified, rejected or needs_refresh. Rejection needs comments. |
| `comments` | text |  |  | Reviewer comments. |
| `reviewed_at` | timestamp with time zone | yes | `now()` | When the review happened. |

Rules enforced by the database:

- `CHECK (((decision = ANY (ARRAY['under_review'::text, 'verified'::text])) OR (length(btrim(COALESCE(comments, ''::text))) > 0)))`
- `CHECK ((decision = ANY (ARRAY['under_review'::text, 'verified'::text, 'rejected'::text, 'needs_refresh'::text])))`

## firm_memberships

Which users belong to a firm and in what role. Membership alone does not give access to any client.

Scope: not tenant-owned (global, firm-level or identity)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `firm_id` | uuid | yes |  | The CA firm concerned. |
| `user_id` | uuid | yes |  | The user concerned. |
| `role` | text | yes |  | firm_admin manages users, clients and assignments. team_member does the work. reviewer reviews and signs off. |
| `status` | text | yes | `'active'::text` | Current status. Allowed values are in the rules below. |
| `granted_by` | uuid |  | `auth.uid()` | Who granted access. |
| `granted_at` | timestamp with time zone | yes | `now()` | When access was granted. |
| `revoked_at` | timestamp with time zone |  |  | When access was withdrawn. |

Rules enforced by the database:

- `CHECK ((role = ANY (ARRAY['firm_admin'::text, 'team_member'::text, 'reviewer'::text])))`
- `CHECK ((status = ANY (ARRAY['invited'::text, 'active'::text, 'disabled'::text])))`

## firms

A Chartered Accountancy firm that serves client institutions.

Scope: not tenant-owned (global, firm-level or identity)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `name` | text | yes |  | Display name. |
| `status` | text | yes | `'active'::text` | Current status. Allowed values are in the rules below. |
| `created_at` | timestamp with time zone | yes | `now()` | When the row was created. |
| `updated_at` | timestamp with time zone | yes | `now()` | When the row last changed (set by the database). |

Rules enforced by the database:

- `CHECK ((length(btrim(name)) > 0))`
- `CHECK ((status = ANY (ARRAY['active'::text, 'suspended'::text])))`

## legal_source_versions

A dated version of a legal source with its verification and commencement status. Immutable once approved.

Scope: not tenant-owned (global, firm-level or identity)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `legal_source_id` | uuid | yes |  | The legal source concerned. |
| `version_label` | text | yes |  | Label of the retrieved version. |
| `retrieved_on` | date | yes |  | Date the official text was retrieved. |
| `published_on` | date |  |  | Date the source was published. |
| `effective_on` | date |  |  | Date the text takes effect, where verified. |
| `commencement_status` | text | yes | `'Requires Verification'::text` | In Force — Verified, Scheduled — Verified, Not Yet in Force — Verified, Requires Verification or Superseded. A library status, not a legal opinion. |
| `verification_status` | text | yes | `'unverified'::text` | unverified or verified against the official text. Verified needs a verifier and a timestamp. |
| `verified_by` | uuid |  |  | User who verified it. |
| `verified_at` | timestamp with time zone |  |  | When it was verified. |
| `approval_state` | text | yes | `'draft'::text` | draft, in_review, approved or retired. |
| `superseded_by` | uuid |  |  | The newer version that replaces this one. |
| `is_demo` | boolean | yes | `false` | True for synthetic demonstration records. Demo records are exempt from the verification gate. |
| `notes` | text |  |  | Free-text notes. |
| `created_by` | uuid |  | `auth.uid()` | User who created the row. |
| `created_at` | timestamp with time zone | yes | `now()` | When the row was created. |

Rules enforced by the database:

- `CHECK ((approval_state = ANY (ARRAY['draft'::text, 'in_review'::text, 'approved'::text, 'retired'::text])))`
- `CHECK (((verification_status <> 'verified'::text) OR ((verified_by IS NOT NULL) AND (verified_at IS NOT NULL))))`
- `CHECK (((commencement_status = ANY (ARRAY['Requires Verification'::text, 'Superseded'::text])) OR (verification_status = 'verified'::text)))`
- `CHECK ((commencement_status = ANY (ARRAY['In Force — Verified'::text, 'Scheduled — Verified'::text, 'Not Yet in Force — Verified'::text, 'Requires Verification'::text, 'Superseded'::text])))`
- `CHECK ((verification_status = ANY (ARRAY['unverified'::text, 'verified'::text])))`

## legal_sources

A legal source: an Act, Rule, notification, order or guidance. Global (platform-maintained) or owned by one firm.

Scope: not tenant-owned (global, firm-level or identity)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `scope` | text | yes |  | global or firm. |
| `firm_id` | uuid |  |  | The CA firm concerned. |
| `title` | text | yes |  | Short title. |
| `issuing_authority` | text | yes |  | Body that issued the source. |
| `source_type` | text | yes |  | act, rule, notification, guidance or other. |
| `official_url` | text |  |  | Link to the official text, for example the Gazette notification. |
| `created_by` | uuid |  | `auth.uid()` | User who created the row. |
| `created_at` | timestamp with time zone | yes | `now()` | When the row was created. |

Rules enforced by the database:

- `CHECK ((((scope = 'global'::text) AND (firm_id IS NULL)) OR ((scope = 'firm'::text) AND (firm_id IS NOT NULL))))`
- `CHECK ((scope = ANY (ARRAY['global'::text, 'firm'::text])))`
- `CHECK ((source_type = ANY (ARRAY['act'::text, 'rule'::text, 'notification'::text, 'corrigendum'::text, 'order'::text, 'guidance'::text])))`

## notifications

In-app and email reminders (later phase). Never holds sensitive content.

Scope: one client (tenant)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `tenant_id` | uuid | yes |  | The client institution that owns this row. Never changes after creation; every policy checks it. |
| `user_id` | uuid | yes |  | The user concerned. |
| `kind` | text | yes |  | Notification kind. |
| `title` | text | yes |  | Short title. |
| `body` | text |  |  | Text of the note. |
| `related_type` | text |  |  | Table of the related row. |
| `related_id` | uuid |  |  | Id of the related row. |
| `due_at` | timestamp with time zone |  |  | When the notification is due. |
| `status` | text | yes | `'pending'::text` | pending, sent, failed, read or cancelled. sent requires provider confirmation. |
| `provider_message_id` | text |  |  | Id returned by the email provider. |
| `provider_confirmed_at` | timestamp with time zone |  |  | When the email provider confirmed delivery. |
| `created_at` | timestamp with time zone | yes | `now()` | When the row was created. |

Rules enforced by the database:

- `CHECK (((status <> 'sent'::text) OR (provider_confirmed_at IS NOT NULL)))`
- `CHECK ((kind = ANY (ARRAY['action_due'::text, 'review_pending'::text, 'evidence_refresh'::text, 'library_update'::text, 'other'::text])))`
- `CHECK ((status = ANY (ARRAY['pending'::text, 'sent'::text, 'failed'::text, 'read'::text, 'cancelled'::text])))`

## platform_admins

Platform administrators. No API access. Managed only with the service role or the SQL editor. Platform administrators have no automatic access to client content.

Scope: not tenant-owned (global, firm-level or identity)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `user_id` | uuid | yes |  | The user concerned. |
| `granted_by` | uuid |  |  | Who granted access. |
| `granted_at` | timestamp with time zone | yes | `now()` | When access was granted. |

## processing_activities

The personal-data inventory. One row per processing activity. Stores metadata about processing, never copies of personal data.

Scope: one client (tenant)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `tenant_id` | uuid | yes |  | The client institution that owns this row. Never changes after creation; every policy checks it. |
| `name` | text | yes |  | Display name. |
| `department_id` | uuid |  |  | The department that runs the activity. |
| `owner_user_id` | uuid |  |  | Accountable owner of the activity at the client. |
| `description` | text |  |  | Free-text description. |
| `data_principal_categories` | ARRAY | yes | `'{}'::text[]` | Whose data: students, applicants, parents, staff, alumni and so on. |
| `collection_source` | text |  |  | Where the data comes from, for example admission form. |
| `purposes` | ARRAY | yes | `'{}'::text[]` | Why the data is processed. Specific, not generic. |
| `processing_operations` | ARRAY | yes | `'{}'::text[]` | What is done with it: collect, store, share, publish, delete. |
| `internal_recipients` | ARRAY | yes | `'{}'::text[]` | Internal teams that receive the data. |
| `external_recipients` | ARRAY | yes | `'{}'::text[]` | Outside parties that receive the data (free text; link vendors through activity_vendors). |
| `lawful_ground` | text | yes | `'not_yet_assessed'::text` | Assessed ground. Defaults to not_yet_assessed. The system never assumes a ground; a rationale is required for any other value except needs_legal_review. |
| `lawful_ground_rationale` | text |  |  | Why the ground applies, with reference to the statutory wording and facts. |
| `notice_reference` | text |  |  | Where the notice for this activity can be found. |
| `consent_reference` | text |  |  | Where consent records for this activity are kept. |
| `retention_criteria` | text |  |  | How long the data is kept and what triggers deletion. |
| `deletion_process` | text |  |  | How deletion is carried out and approved. |
| `cross_border` | text | yes | `'unknown'::text` | none, yes or unknown. Unknown is a gap, not a pass. |
| `cross_border_notes` | text |  |  | Countries, vendors and transfer considerations. |
| `children_data` | boolean | yes | `false` | True if the activity involves children's data. |
| `special_case_flags` | ARRAY | yes | `'{}'::text[]` | Other special cases such as disability, health, biometric. |
| `volume_indicator` | text | yes | `'unknown'::text` | Rough volume for internal risk prioritisation. Not a legal threshold. |
| `sensitivity_indicator` | text | yes | `'unknown'::text` | Rough sensitivity for internal risk prioritisation. Not a legal classification. |
| `review_date` | date |  |  | When the record was last reviewed. |
| `status` | text | yes | `'draft'::text` | draft, active, needs_review or archived. Archiving needs a reason. |
| `archived_at` | timestamp with time zone |  |  | When the record was archived. Archived records are kept, never deleted. |
| `archived_reason` | text |  |  | Why the record was archived. |
| `created_by` | uuid |  | `auth.uid()` | User who created the row. |
| `created_at` | timestamp with time zone | yes | `now()` | When the row was created. |
| `updated_at` | timestamp with time zone | yes | `now()` | When the row last changed (set by the database). |

Rules enforced by the database:

- `CHECK (((lawful_ground = ANY (ARRAY['not_yet_assessed'::text, 'needs_legal_review'::text])) OR (length(btrim(COALESCE(lawful_ground_rationale, ''::text))) > 0)))`
- `CHECK (((status <> 'archived'::text) OR ((archived_at IS NOT NULL) AND (length(btrim(COALESCE(archived_reason, ''::text))) > 0))))`
- `CHECK ((cross_border = ANY (ARRAY['none'::text, 'yes'::text, 'unknown'::text])))`
- `CHECK ((lawful_ground = ANY (ARRAY['not_yet_assessed'::text, 'consent'::text, 'legitimate_use'::text, 'exemption_claimed'::text, 'needs_legal_review'::text])))`
- `CHECK ((length(btrim(name)) > 0))`
- `CHECK ((sensitivity_indicator = ANY (ARRAY['low'::text, 'medium'::text, 'high'::text, 'unknown'::text])))`
- `CHECK ((status = ANY (ARRAY['draft'::text, 'active'::text, 'needs_review'::text, 'archived'::text])))`
- `CHECK ((volume_indicator = ANY (ARRAY['low'::text, 'medium'::text, 'high'::text, 'unknown'::text])))`

## profiles

One row per signed-in user. Created automatically from Supabase Auth. Holds name and email only.

Scope: not tenant-owned (global, firm-level or identity)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes |  | Unique identifier. |
| `email` | text | yes |  | Email address copied from the sign-in account. |
| `full_name` | text |  |  | The user's name. |
| `status` | text | yes | `'active'::text` | active or disabled. A disabled profile loses all access. |
| `created_at` | timestamp with time zone | yes | `now()` | When the row was created. |
| `updated_at` | timestamp with time zone | yes | `now()` | When the row last changed (set by the database). |

Rules enforced by the database:

- `CHECK ((status = ANY (ARRAY['active'::text, 'disabled'::text])))`

## report_runs

A generated report: type, assessment version, draft or final, and the denominators used.

Scope: one client (tenant)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `tenant_id` | uuid | yes |  | The client institution that owns this row. Never changes after creation; every policy checks it. |
| `assessment_id` | uuid | yes |  | The assessment this row belongs to. |
| `assessment_version` | integer | yes |  | Version of the assessment the report was built from. |
| `report_type` | text | yes |  | Kind of report. |
| `status` | text | yes | `'draft'::text` | draft or final. Final needs an approved assessment at the same version. |
| `shared_with_client` | boolean | yes | `false` | Whether the client can see it. |
| `limitations` | text |  |  | Stated limits of the work, shown on reports. |
| `denominators` | jsonb | yes | `'{}'::jsonb` | Counts behind every percentage in the report. |
| `generated_by` | uuid |  | `auth.uid()` | User who generated it. |
| `generated_at` | timestamp with time zone | yes | `now()` | When the report was generated. |

Rules enforced by the database:

- `CHECK ((report_type = ANY (ARRAY['executive_summary'::text, 'applicability_summary'::text, 'data_inventory'::text, 'control_assessment'::text, 'gaps_and_remediation'::text, 'evidence_status'::text, 'outstanding_decisions'::text])))`
- `CHECK ((status = ANY (ARRAY['draft'::text, 'final'::text])))`

## review_decisions

Append-only trail of review decisions: who, when, why, which version.

Scope: one client (tenant)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `tenant_id` | uuid | yes |  | The client institution that owns this row. Never changes after creation; every policy checks it. |
| `subject_type` | text | yes |  | assessment, evidence, corrective_action, risk_acceptance or report. |
| `subject_id` | uuid | yes |  | Id of the item that was decided on. |
| `subject_version` | integer |  |  | Version of the item that was decided on. |
| `decision` | text | yes |  | The reviewer's decision. |
| `reviewer_id` | uuid | yes |  | The reviewer. |
| `reviewer_capacity` | text | yes |  | firm_reviewer (CA firm review) or client_reviewer (client management acceptance). The two are never mixed. |
| `comments` | text |  |  | Reviewer comments. |
| `decided_at` | timestamp with time zone | yes | `now()` | When the decision was made. |

Rules enforced by the database:

- `CHECK (((decision = 'approved'::text) OR (length(btrim(COALESCE(comments, ''::text))) > 0)))`
- `CHECK ((decision = ANY (ARRAY['approved'::text, 'returned_for_revision'::text, 'clarification_requested'::text, 'reopened'::text])))`
- `CHECK ((reviewer_capacity = ANY (ARRAY['firm_reviewer'::text, 'client_reviewer'::text])))`
- `CHECK ((subject_type = ANY (ARRAY['assessment'::text, 'evidence'::text, 'corrective_action'::text, 'risk_acceptance'::text, 'report'::text])))`

## role_capabilities

The role-to-capability matrix. Policies ask "can this user do X on this tenant", never "is this user role Y". Change access here, in one place.

Scope: not tenant-owned (global, firm-level or identity)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `actor_kind` | text | yes |  | client or firm: which kind of user the capability applies to. |
| `role` | text | yes |  | Role held. |
| `capability` | text | yes |  | A named permission, for example edit_assessment. |

Rules enforced by the database:

- `CHECK ((actor_kind = ANY (ARRAY['client'::text, 'firm'::text])))`

## systems

Systems and places where personal data is held: applications, databases, cloud services, paper stores.

Scope: one client (tenant)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `tenant_id` | uuid | yes |  | The client institution that owns this row. Never changes after creation; every policy checks it. |
| `name` | text | yes |  | Display name. |
| `system_type` | text | yes | `'application'::text` | application, database, cloud_service, paper_records, device, network or other. |
| `hosting_location` | text |  |  | Where the system is hosted, for example On premises or Cloud, Mumbai region. |
| `owner_department_id` | uuid |  |  | Department that owns the system. |
| `vendor_id` | uuid |  |  | The vendor concerned. |
| `archived_at` | timestamp with time zone |  |  | When the record was archived. Archived records are kept, never deleted. |
| `created_at` | timestamp with time zone | yes | `now()` | When the row was created. |
| `updated_at` | timestamp with time zone | yes | `now()` | When the row last changed (set by the database). |

Rules enforced by the database:

- `CHECK ((length(btrim(name)) > 0))`
- `CHECK ((system_type = ANY (ARRAY['application'::text, 'database'::text, 'cloud_service'::text, 'paper_records'::text, 'device'::text, 'network'::text, 'other'::text])))`

## tenant_memberships

Which users belong to a client workspace and in what role.

Scope: one client (tenant)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `tenant_id` | uuid | yes |  | The client institution that owns this row. Never changes after creation; every policy checks it. |
| `user_id` | uuid | yes |  | The user concerned. |
| `role` | text | yes |  | client_admin, privacy_lead, department_coordinator, evidence_contributor, management_viewer or client_reviewer. |
| `status` | text | yes | `'active'::text` | Current status. Allowed values are in the rules below. |
| `granted_by` | uuid |  | `auth.uid()` | Who granted access. |
| `granted_at` | timestamp with time zone | yes | `now()` | When access was granted. |
| `revoked_at` | timestamp with time zone |  |  | When access was withdrawn. |

Rules enforced by the database:

- `CHECK ((role = ANY (ARRAY['client_admin'::text, 'privacy_lead'::text, 'department_coordinator'::text, 'evidence_contributor'::text, 'management_viewer'::text, 'client_reviewer'::text])))`
- `CHECK ((status = ANY (ARRAY['invited'::text, 'active'::text, 'disabled'::text])))`

## tenants

A client institution workspace. The tenant_id on every other table points here.

Scope: not tenant-owned (global, firm-level or identity)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `firm_id` | uuid | yes |  | The firm that serves this client. Cannot be changed after creation. |
| `name` | text | yes |  | Display name. |
| `institution_type` | text | yes |  | School, college, university, coaching centre, vocational institute, research institute or other. |
| `sector` | text |  |  | Free-text sector or board, for example CBSE school or State university. |
| `description` | text |  |  | Business context of the institution. |
| `headcount_band` | text |  |  | Approximate size band, for example 1000-5000 students. |
| `primary_contact_name` | text |  |  | Name of the main client contact. Business contact detail only. |
| `primary_contact_email` | text |  |  | Business email of the main client contact. |
| `status` | text | yes | `'onboarding'::text` | onboarding, active, paused or closed. |
| `is_demo` | boolean | yes | `false` | True for synthetic demonstration workspaces. The screens must show a Demo banner. |
| `created_by` | uuid |  | `auth.uid()` | User who created the row. |
| `created_at` | timestamp with time zone | yes | `now()` | When the row was created. |
| `updated_at` | timestamp with time zone | yes | `now()` | When the row last changed (set by the database). |

Rules enforced by the database:

- `CHECK ((institution_type = ANY (ARRAY['school'::text, 'college'::text, 'university'::text, 'coaching'::text, 'vocational'::text, 'research'::text, 'other'::text])))`
- `CHECK ((length(btrim(name)) > 0))`
- `CHECK ((status = ANY (ARRAY['onboarding'::text, 'active'::text, 'paused'::text, 'closed'::text])))`

## vendors

Processors and other recipients of personal data (ERP provider, SMS gateway, cloud host).

Scope: one client (tenant)

| Column | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `id` | uuid | yes | `gen_random_uuid()` | Unique identifier. |
| `tenant_id` | uuid | yes |  | The client institution that owns this row. Never changes after creation; every policy checks it. |
| `name` | text | yes |  | Display name. |
| `relationship` | text | yes | `'processor'::text` | processor, recipient, joint or other. |
| `country_code` | text |  |  | Two-letter country code where the vendor stores or processes data. |
| `contract_status` | text | yes | `'unknown'::text` | none, in_place, under_review or unknown. |
| `notes` | text |  |  | Free-text notes. |
| `archived_at` | timestamp with time zone |  |  | When the record was archived. Archived records are kept, never deleted. |
| `created_at` | timestamp with time zone | yes | `now()` | When the row was created. |
| `updated_at` | timestamp with time zone | yes | `now()` | When the row last changed (set by the database). |

Rules enforced by the database:

- `CHECK ((contract_status = ANY (ARRAY['none'::text, 'in_place'::text, 'under_review'::text, 'unknown'::text])))`
- `CHECK (((country_code IS NULL) OR (length(country_code) = 2)))`
- `CHECK ((length(btrim(name)) > 0))`
- `CHECK ((relationship = ANY (ARRAY['processor'::text, 'recipient'::text, 'joint'::text, 'other'::text])))`

