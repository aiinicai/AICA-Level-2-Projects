-- =====================================================================
-- DPDP Compliance Manager: core schema (PostgreSQL / Supabase)
-- File 1 of 3. Run in this order: database_schema.sql, row_level_security.sql,
-- then (demo projects only) seed_demo_data.sql.
--
-- Design rules (from PROJECT_SPEC.md sections 5, 9 and 10)
--  * Every tenant-owned table has tenant_id.
--  * Child tables reference their parent with a composite key (id, tenant_id), so a
--    child row can never point at a parent that belongs to another tenant.
--  * Status values are text with CHECK constraints, so a change is one migration.
--  * Approved legal controls and approved assessments cannot be edited in place.
--  * No personal data values are stored here, only processing metadata.
--
-- STATUS: for review. Do not load real client data until the tenant isolation tests
-- in TEST_PLAN.md pass on your own Supabase project and an independent reviewer
-- has checked row_level_security.sql.
-- =====================================================================

create schema if not exists app_private;
comment on schema app_private is 'Internal helpers. Not exposed through the Supabase API. Never add this schema to the exposed schemas list.';

-- ---------------------------------------------------------------------
-- 1. Identity and firm structure
-- ---------------------------------------------------------------------
create table public.profiles (
  id          uuid primary key references auth.users(id) on delete cascade,
  email       text not null,
  full_name   text,
  status      text not null default 'active' check (status in ('active','disabled')),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create table public.platform_admins (
  user_id     uuid primary key references auth.users(id) on delete cascade,
  granted_by  uuid,
  granted_at  timestamptz not null default now()
);

create table public.firms (
  id          uuid primary key default gen_random_uuid(),
  name        text not null check (length(btrim(name)) > 0),
  status      text not null default 'active' check (status in ('active','suspended')),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create table public.firm_memberships (
  id          uuid primary key default gen_random_uuid(),
  firm_id     uuid not null references public.firms(id),
  user_id     uuid not null references public.profiles(id),
  role        text not null check (role in ('firm_admin','team_member','reviewer')),
  status      text not null default 'active' check (status in ('invited','active','disabled')),
  granted_by  uuid default auth.uid(),
  granted_at  timestamptz not null default now(),
  revoked_at  timestamptz,
  unique (firm_id, user_id)
);

create table public.tenants (
  id                     uuid primary key default gen_random_uuid(),
  firm_id                uuid not null references public.firms(id),
  name                   text not null check (length(btrim(name)) > 0),
  institution_type       text not null check (institution_type in ('school','college','university','coaching','vocational','research','other')),
  sector                 text,
  description            text,
  headcount_band         text,
  primary_contact_name   text,
  primary_contact_email  text,
  status                 text not null default 'onboarding' check (status in ('onboarding','active','paused','closed')),
  is_demo                boolean not null default false,
  created_by             uuid default auth.uid(),
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now(),
  unique (id, firm_id)
);

create table public.tenant_memberships (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references public.tenants(id),
  user_id     uuid not null references public.profiles(id),
  role        text not null check (role in ('client_admin','privacy_lead','department_coordinator','evidence_contributor','management_viewer','client_reviewer')),
  status      text not null default 'active' check (status in ('invited','active','disabled')),
  granted_by  uuid default auth.uid(),
  granted_at  timestamptz not null default now(),
  revoked_at  timestamptz,
  unique (tenant_id, user_id)
);

create table public.engagements (
  id                       uuid primary key default gen_random_uuid(),
  tenant_id                uuid not null,
  firm_id                  uuid not null,
  title                    text not null,
  scope                    text,
  status                   text not null default 'planned' check (status in ('planned','active','review','closed')),
  onboarding_status        text not null default 'not_started' check (onboarding_status in ('not_started','in_progress','complete')),
  missing_information      text,
  start_date               date,
  assessment_period_start  date,
  assessment_period_end    date,
  created_by               uuid default auth.uid(),
  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now(),
  unique (id, tenant_id),
  foreign key (tenant_id, firm_id) references public.tenants (id, firm_id),
  check (assessment_period_end is null or assessment_period_start is null or assessment_period_end >= assessment_period_start)
);

create table public.engagement_assignments (
  id             uuid primary key default gen_random_uuid(),
  tenant_id      uuid not null,
  engagement_id  uuid not null,
  user_id        uuid not null references public.profiles(id),
  role           text not null check (role in ('team_member','reviewer')),
  status         text not null default 'active' check (status in ('active','revoked')),
  granted_by     uuid default auth.uid(),
  granted_at     timestamptz not null default now(),
  revoked_at     timestamptz,
  unique (engagement_id, user_id),
  foreign key (engagement_id, tenant_id) references public.engagements (id, tenant_id)
);

create table public.engagement_notes (
  id             uuid primary key default gen_random_uuid(),
  tenant_id      uuid not null,
  engagement_id  uuid not null,
  visibility     text not null default 'firm_only' check (visibility in ('firm_only','client_visible')),
  body           text not null check (length(btrim(body)) > 0),
  author_id      uuid not null default auth.uid() references public.profiles(id),
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  foreign key (engagement_id, tenant_id) references public.engagements (id, tenant_id)
);

-- ---------------------------------------------------------------------
-- 2. Institution structure and the personal-data inventory
-- ---------------------------------------------------------------------
create table public.departments (
  id                   uuid primary key default gen_random_uuid(),
  tenant_id            uuid not null references public.tenants(id),
  name                 text not null check (length(btrim(name)) > 0),
  coordinator_user_id  uuid references public.profiles(id),
  archived_at          timestamptz,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  unique (id, tenant_id),
  unique (tenant_id, name)
);

create table public.vendors (
  id               uuid primary key default gen_random_uuid(),
  tenant_id        uuid not null references public.tenants(id),
  name             text not null check (length(btrim(name)) > 0),
  relationship     text not null default 'processor' check (relationship in ('processor','recipient','joint','other')),
  country_code     text check (country_code is null or length(country_code) = 2),
  contract_status  text not null default 'unknown' check (contract_status in ('none','in_place','under_review','unknown')),
  notes            text,
  archived_at      timestamptz,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  unique (id, tenant_id)
);

create table public.systems (
  id                    uuid primary key default gen_random_uuid(),
  tenant_id             uuid not null references public.tenants(id),
  name                  text not null check (length(btrim(name)) > 0),
  system_type           text not null default 'application' check (system_type in ('application','database','cloud_service','paper_records','device','network','other')),
  hosting_location      text,
  owner_department_id   uuid,
  vendor_id             uuid,
  archived_at           timestamptz,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  unique (id, tenant_id),
  foreign key (owner_department_id, tenant_id) references public.departments (id, tenant_id),
  foreign key (vendor_id, tenant_id) references public.vendors (id, tenant_id)
);

-- Global reference list of personal-data categories. Not tenant-owned.
create table public.data_categories (
  id               uuid primary key default gen_random_uuid(),
  code             text not null unique,
  name             text not null,
  category_group   text not null,
  is_special_case  boolean not null default false,
  description      text
);

create table public.processing_activities (
  id                          uuid primary key default gen_random_uuid(),
  tenant_id                   uuid not null references public.tenants(id),
  name                        text not null check (length(btrim(name)) > 0),
  department_id               uuid,
  owner_user_id               uuid references public.profiles(id),
  description                 text,
  data_principal_categories   text[] not null default '{}',
  collection_source           text,
  purposes                    text[] not null default '{}',
  processing_operations       text[] not null default '{}',
  internal_recipients         text[] not null default '{}',
  external_recipients         text[] not null default '{}',
  lawful_ground               text not null default 'not_yet_assessed' check (lawful_ground in ('not_yet_assessed','consent','legitimate_use','exemption_claimed','needs_legal_review')),
  lawful_ground_rationale     text,
  notice_reference            text,
  consent_reference           text,
  retention_criteria          text,
  deletion_process            text,
  cross_border                text not null default 'unknown' check (cross_border in ('none','yes','unknown')),
  cross_border_notes          text,
  children_data               boolean not null default false,
  special_case_flags          text[] not null default '{}',
  volume_indicator            text not null default 'unknown' check (volume_indicator in ('low','medium','high','unknown')),
  sensitivity_indicator       text not null default 'unknown' check (sensitivity_indicator in ('low','medium','high','unknown')),
  review_date                 date,
  status                      text not null default 'draft' check (status in ('draft','active','needs_review','archived')),
  archived_at                 timestamptz,
  archived_reason             text,
  created_by                  uuid default auth.uid(),
  created_at                  timestamptz not null default now(),
  updated_at                  timestamptz not null default now(),
  unique (id, tenant_id),
  foreign key (department_id, tenant_id) references public.departments (id, tenant_id),
  check (lawful_ground in ('not_yet_assessed','needs_legal_review') or length(btrim(coalesce(lawful_ground_rationale,''))) > 0),
  check (status <> 'archived' or (archived_at is not null and length(btrim(coalesce(archived_reason,''))) > 0))
);

create table public.activity_systems (
  tenant_id    uuid not null,
  activity_id  uuid not null,
  system_id    uuid not null,
  primary key (activity_id, system_id),
  foreign key (activity_id, tenant_id) references public.processing_activities (id, tenant_id) on delete cascade,
  foreign key (system_id, tenant_id) references public.systems (id, tenant_id)
);

create table public.activity_vendors (
  tenant_id    uuid not null,
  activity_id  uuid not null,
  vendor_id    uuid not null,
  primary key (activity_id, vendor_id),
  foreign key (activity_id, tenant_id) references public.processing_activities (id, tenant_id) on delete cascade,
  foreign key (vendor_id, tenant_id) references public.vendors (id, tenant_id)
);

create table public.activity_data_categories (
  tenant_id         uuid not null,
  activity_id       uuid not null,
  data_category_id  uuid not null references public.data_categories(id),
  primary key (activity_id, data_category_id),
  foreign key (activity_id, tenant_id) references public.processing_activities (id, tenant_id) on delete cascade
);

-- ---------------------------------------------------------------------
-- 3. Legal source and control register (global or firm-owned, never tenant-owned)
-- ---------------------------------------------------------------------
create table public.legal_sources (
  id                 uuid primary key default gen_random_uuid(),
  scope              text not null check (scope in ('global','firm')),
  firm_id            uuid references public.firms(id),
  title              text not null,
  issuing_authority  text not null,
  source_type        text not null check (source_type in ('act','rule','notification','corrigendum','order','guidance')),
  official_url       text,
  created_by         uuid default auth.uid(),
  created_at         timestamptz not null default now(),
  check ((scope = 'global' and firm_id is null) or (scope = 'firm' and firm_id is not null))
);

create table public.legal_source_versions (
  id                    uuid primary key default gen_random_uuid(),
  legal_source_id       uuid not null references public.legal_sources(id),
  version_label         text not null,
  retrieved_on          date not null,
  published_on          date,
  effective_on          date,
  commencement_status   text not null default 'Requires Verification' check (commencement_status in ('In Force — Verified','Scheduled — Verified','Not Yet in Force — Verified','Requires Verification','Superseded')),
  verification_status   text not null default 'unverified' check (verification_status in ('unverified','verified')),
  verified_by           uuid,
  verified_at           timestamptz,
  approval_state        text not null default 'draft' check (approval_state in ('draft','in_review','approved','retired')),
  superseded_by         uuid references public.legal_source_versions(id),
  is_demo               boolean not null default false,
  notes                 text,
  created_by            uuid default auth.uid(),
  created_at            timestamptz not null default now(),
  unique (legal_source_id, version_label),
  check (verification_status <> 'verified' or (verified_by is not null and verified_at is not null)),
  check (commencement_status in ('Requires Verification','Superseded') or verification_status = 'verified')
);

create table public.controls (
  id               uuid primary key default gen_random_uuid(),
  scope            text not null check (scope in ('global','firm')),
  firm_id          uuid references public.firms(id),
  control_code     text not null check (length(btrim(control_code)) > 0),
  title            text not null,
  legal_source_id  uuid references public.legal_sources(id),
  created_by       uuid default auth.uid(),
  created_at       timestamptz not null default now(),
  check ((scope = 'global' and firm_id is null) or (scope = 'firm' and firm_id is not null))
);
create unique index controls_code_uq on public.controls (coalesce(firm_id, '00000000-0000-0000-0000-000000000000'::uuid), control_code);

create table public.control_versions (
  id                    uuid primary key default gen_random_uuid(),
  control_id             uuid not null references public.controls(id),
  version_no            integer not null check (version_no >= 1),
  legal_reference       text not null,
  statement             text not null,
  applicability_logic   text,
  commencement_status   text not null default 'Requires Verification' check (commencement_status in ('In Force — Verified','Scheduled — Verified','Not Yet in Force — Verified','Requires Verification','Superseded')),
  effective_date        date,
  assessment_question   text not null,
  required_evidence     text,
  test_procedure        text,
  expected_result       text,
  risk_guidance         text,
  source_version_id     uuid references public.legal_source_versions(id),
  review_status         text not null default 'draft' check (review_status in ('draft','in_review','approved','retired')),
  approved_by           uuid,
  approved_at           timestamptz,
  retired_at            timestamptz,
  is_demo               boolean not null default false,
  change_note           text,
  created_by            uuid default auth.uid(),
  created_at            timestamptz not null default now(),
  unique (control_id, version_no),
  check (review_status not in ('approved','retired') or (approved_by is not null and approved_at is not null))
);

-- ---------------------------------------------------------------------
-- 4. Assessments, evidence, actions and review
-- ---------------------------------------------------------------------
create table public.assessments (
  id                 uuid primary key default gen_random_uuid(),
  tenant_id          uuid not null references public.tenants(id),
  engagement_id      uuid not null,
  title              text not null,
  period_start       date not null,
  period_end         date not null,
  status             text not null default 'draft' check (status in ('draft','in_progress','submitted_for_review','returned','approved','reopened')),
  version_no         integer not null default 1,
  prepared_by        uuid not null default auth.uid() references public.profiles(id),
  reviewer_id        uuid references public.profiles(id),
  submitted_at       timestamptz,
  approved_by        uuid,
  approved_at        timestamptz,
  shared_with_client boolean not null default false,
  limitations        text,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  unique (id, tenant_id),
  foreign key (engagement_id, tenant_id) references public.engagements (id, tenant_id),
  check (period_end >= period_start),
  check (reviewer_id is null or reviewer_id <> prepared_by),
  check (status <> 'approved' or (approved_by is not null and approved_at is not null))
);

create table public.applicability_decisions (
  id             uuid primary key default gen_random_uuid(),
  tenant_id      uuid not null,
  assessment_id  uuid not null,
  question_code  text not null,
  question_text  text not null,
  outcome        text not null check (outcome in ('applicable','not_applicable','needs_legal_review')),
  rationale      text not null check (length(btrim(rationale)) > 0),
  evidence_id    uuid,
  assessed_by    uuid,
  assessed_at    timestamptz,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  unique (id, tenant_id),
  unique (assessment_id, question_code),
  foreign key (assessment_id, tenant_id) references public.assessments (id, tenant_id)
);

create table public.assessment_items (
  id                      uuid primary key default gen_random_uuid(),
  tenant_id               uuid not null,
  assessment_id           uuid not null,
  control_version_id      uuid not null references public.control_versions(id),
  applicability           text not null default 'applicable' check (applicability in ('applicable','not_applicable','needs_legal_review')),
  applicability_rationale text,
  result                  text not null default 'not_assessed' check (result in ('implemented_verified','partial','gap','not_assessed','not_applicable')),
  evidence_quality        text not null default 'none' check (evidence_quality in ('none','submitted','verified','insufficient')),
  risk_level              text check (risk_level in ('low','medium','high','critical')),
  assessor_notes          text,
  recommendation          text,
  owner_user_id           uuid references public.profiles(id),
  target_date             date,
  assessed_by             uuid,
  assessed_at             timestamptz,
  created_at              timestamptz not null default now(),
  updated_at              timestamptz not null default now(),
  unique (id, tenant_id),
  unique (assessment_id, control_version_id),
  foreign key (assessment_id, tenant_id) references public.assessments (id, tenant_id),
  check ((applicability = 'not_applicable') = (result = 'not_applicable')),
  check (applicability = 'applicable' or length(btrim(coalesce(applicability_rationale,''))) > 0),
  check (result <> 'implemented_verified' or evidence_quality = 'verified')
);

create table public.evidence_records (
  id                    uuid primary key default gen_random_uuid(),
  tenant_id             uuid not null references public.tenants(id),
  title                 text not null check (length(btrim(title)) > 0),
  description           text,
  category              text not null default 'document' check (category in ('policy','procedure','record','screenshot','contract','training','log','report','other','document')),
  source                text,
  status                text not null default 'missing' check (status in ('missing','submitted','under_review','verified','rejected','expired')),
  storage_bucket        text not null default 'evidence',
  storage_path          text unique,
  file_name             text,
  mime_type             text,
  size_bytes            bigint check (size_bytes is null or (size_bytes > 0 and size_bytes <= 26214400)),
  sha256                text check (sha256 is null or sha256 ~ '^[0-9a-f]{64}$'),
  version_no            integer not null default 1,
  supersedes_id         uuid,
  valid_until           date,
  uploaded_by           uuid references public.profiles(id),
  uploaded_at           timestamptz,
  activity_id           uuid,
  assessment_id         uuid,
  assessment_item_id    uuid,
  corrective_action_id  uuid,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  unique (id, tenant_id),
  foreign key (supersedes_id, tenant_id) references public.evidence_records (id, tenant_id),
  foreign key (activity_id, tenant_id) references public.processing_activities (id, tenant_id),
  foreign key (assessment_id, tenant_id) references public.assessments (id, tenant_id),
  foreign key (assessment_item_id, tenant_id) references public.assessment_items (id, tenant_id),
  check (storage_path is null or storage_path like tenant_id::text || '/%'),
  check (status = 'missing' or (storage_path is not null and uploaded_by is not null and uploaded_at is not null))
);

alter table public.applicability_decisions
  add foreign key (evidence_id, tenant_id) references public.evidence_records (id, tenant_id);

create table public.evidence_reviews (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null,
  evidence_id  uuid not null,
  reviewer_id  uuid not null references public.profiles(id),
  decision     text not null check (decision in ('under_review','verified','rejected','needs_refresh')),
  comments     text,
  reviewed_at  timestamptz not null default now(),
  foreign key (evidence_id, tenant_id) references public.evidence_records (id, tenant_id),
  check (decision in ('under_review','verified') or length(btrim(coalesce(comments,''))) > 0)
);

create table public.corrective_actions (
  id                          uuid primary key default gen_random_uuid(),
  tenant_id                   uuid not null references public.tenants(id),
  assessment_item_id          uuid,
  title                       text not null check (length(btrim(title)) > 0),
  issue                       text not null,
  risk_level                  text not null default 'medium' check (risk_level in ('low','medium','high','critical')),
  risk_rationale              text,
  owner_user_id               uuid references public.profiles(id),
  due_date                    date,
  dependencies                text,
  status                      text not null default 'open' check (status in ('open','in_progress','blocked','submitted_for_review','closed','accepted_risk')),
  closure_evidence_id         uuid,
  closed_at                   timestamptz,
  closure_verified_by         uuid,
  closure_verified_at         timestamptz,
  risk_accepted_by            uuid,
  risk_acceptance_rationale   text,
  risk_accepted_at            timestamptz,
  created_by                  uuid default auth.uid(),
  created_at                  timestamptz not null default now(),
  updated_at                  timestamptz not null default now(),
  unique (id, tenant_id),
  foreign key (assessment_item_id, tenant_id) references public.assessment_items (id, tenant_id),
  foreign key (closure_evidence_id, tenant_id) references public.evidence_records (id, tenant_id),
  check (status <> 'closed' or (closure_evidence_id is not null and closure_verified_by is not null and closure_verified_at is not null and closed_at is not null)),
  check (status <> 'accepted_risk' or (risk_accepted_by is not null and risk_accepted_at is not null and length(btrim(coalesce(risk_acceptance_rationale,''))) > 0))
);

alter table public.evidence_records
  add foreign key (corrective_action_id, tenant_id) references public.corrective_actions (id, tenant_id);

create table public.review_decisions (
  id                  uuid primary key default gen_random_uuid(),
  tenant_id           uuid not null references public.tenants(id),
  subject_type        text not null check (subject_type in ('assessment','evidence','corrective_action','risk_acceptance','report')),
  subject_id          uuid not null,
  subject_version     integer,
  decision            text not null check (decision in ('approved','returned_for_revision','clarification_requested','reopened')),
  reviewer_id         uuid not null references public.profiles(id),
  reviewer_capacity   text not null check (reviewer_capacity in ('firm_reviewer','client_reviewer')),
  comments            text,
  decided_at          timestamptz not null default now(),
  check (decision = 'approved' or length(btrim(coalesce(comments,''))) > 0)
);

create table public.assessment_snapshots (
  id             uuid primary key default gen_random_uuid(),
  tenant_id      uuid not null,
  assessment_id  uuid not null,
  version_no     integer not null,
  snapshot       jsonb not null,
  created_by     uuid,
  created_at     timestamptz not null default now(),
  unique (assessment_id, version_no),
  foreign key (assessment_id, tenant_id) references public.assessments (id, tenant_id)
);

create table public.audit_events (
  id           bigint generated always as identity primary key,
  tenant_id    uuid,
  firm_id      uuid,
  actor_id     uuid,
  action       text not null,
  entity_type  text not null,
  entity_id    uuid,
  details      jsonb not null default '{}'::jsonb,
  occurred_at  timestamptz not null default now()
);

-- Later phase tables (created now so the model is complete; screens come later)
create table public.notifications (
  id                     uuid primary key default gen_random_uuid(),
  tenant_id              uuid not null references public.tenants(id),
  user_id                uuid not null references public.profiles(id),
  kind                   text not null check (kind in ('action_due','review_pending','evidence_refresh','library_update','other')),
  title                  text not null,
  body                   text,
  related_type           text,
  related_id             uuid,
  due_at                 timestamptz,
  status                 text not null default 'pending' check (status in ('pending','sent','failed','read','cancelled')),
  provider_message_id    text,
  provider_confirmed_at  timestamptz,
  created_at             timestamptz not null default now(),
  check (status <> 'sent' or provider_confirmed_at is not null)
);

create table public.report_runs (
  id                   uuid primary key default gen_random_uuid(),
  tenant_id            uuid not null,
  assessment_id        uuid not null,
  assessment_version   integer not null,
  report_type          text not null check (report_type in ('executive_summary','applicability_summary','data_inventory','control_assessment','gaps_and_remediation','evidence_status','outstanding_decisions')),
  status               text not null default 'draft' check (status in ('draft','final')),
  shared_with_client   boolean not null default false,
  limitations          text,
  denominators         jsonb not null default '{}'::jsonb,
  generated_by         uuid default auth.uid(),
  generated_at         timestamptz not null default now(),
  foreign key (assessment_id, tenant_id) references public.assessments (id, tenant_id)
);

-- ---------------------------------------------------------------------
-- 5. Indexes for the access paths the policies and screens use
-- ---------------------------------------------------------------------
create index on public.firm_memberships (user_id) where status = 'active';
create index on public.tenant_memberships (user_id) where status = 'active';
create index on public.engagement_assignments (user_id, tenant_id) where status = 'active';
create index on public.tenants (firm_id);
create index on public.processing_activities (tenant_id, status);
create index on public.assessment_items (assessment_id);
create index on public.assessment_items (owner_user_id) where owner_user_id is not null;
create index on public.evidence_records (tenant_id, status);
create index on public.evidence_records (assessment_item_id) where assessment_item_id is not null;
create index on public.corrective_actions (tenant_id, status, due_date);
create index on public.corrective_actions (owner_user_id) where owner_user_id is not null;
create index on public.review_decisions (tenant_id, subject_type, subject_id);
create index on public.audit_events (tenant_id, occurred_at desc);
create index on public.audit_events (firm_id, occurred_at desc);

-- ---------------------------------------------------------------------
-- 6. Generic triggers
-- ---------------------------------------------------------------------
create function app_private.touch_updated_at() returns trigger
language plpgsql set search_path = '' as $$
begin new.updated_at := now(); return new; end $$;

create function app_private.prevent_tenant_change() returns trigger
language plpgsql set search_path = '' as $$
begin
  if new.tenant_id is distinct from old.tenant_id then
    raise exception 'tenant_id cannot be changed' using errcode = '42501';
  end if;
  return new;
end $$;

create function app_private.block_change() returns trigger
language plpgsql set search_path = '' as $$
begin
  raise exception '% is append-only; % is not allowed', tg_table_name, tg_op using errcode = '55000';
end $$;

do $$
declare t record;
begin
  for t in select table_name from information_schema.columns
           where table_schema = 'public' and column_name = 'updated_at' loop
    execute format('create trigger touch_updated_at before update on public.%I for each row execute function app_private.touch_updated_at()', t.table_name);
  end loop;
  for t in select table_name from information_schema.columns
           where table_schema = 'public' and column_name = 'tenant_id'
             and table_name not in ('tenants') and table_name <> 'audit_events'
             and table_name in (select table_name from information_schema.tables where table_schema='public' and table_type='BASE TABLE') loop
    execute format('create trigger prevent_tenant_change before update on public.%I for each row execute function app_private.prevent_tenant_change()', t.table_name);
  end loop;
end $$;

-- Append-only tables: no update or delete, even for the table owner.
create trigger append_only before update or delete on public.review_decisions   for each row execute function app_private.block_change();
create trigger append_only before update or delete on public.evidence_reviews   for each row execute function app_private.block_change();
create trigger append_only before update or delete on public.assessment_snapshots for each row execute function app_private.block_change();
create trigger append_only before update or delete on public.audit_events       for each row execute function app_private.block_change();

-- Create a profile whenever Supabase Auth creates a user.
create function app_private.handle_new_user() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  insert into public.profiles (id, email, full_name)
  values (new.id, coalesce(new.email, ''), nullif(new.raw_user_meta_data ->> 'full_name', ''))
  on conflict (id) do nothing;
  return new;
end $$;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function app_private.handle_new_user();

-- ---------------------------------------------------------------------
-- 7. Integrity rules that a CHECK constraint cannot express
-- ---------------------------------------------------------------------

-- A firm user can only be assigned to a client of their own firm.
create function app_private.guard_assignment() returns trigger
language plpgsql security definer set search_path = '' as $$
declare v_firm uuid;
begin
  select firm_id into v_firm from public.tenants where id = new.tenant_id;
  if not exists (select 1 from public.firm_memberships fm
                 where fm.firm_id = v_firm and fm.user_id = new.user_id and fm.status = 'active') then
    raise exception 'User is not an active member of the firm that owns this client' using errcode = '23514';
  end if;
  return new;
end $$;
create trigger guard_assignment before insert or update of user_id, tenant_id on public.engagement_assignments
  for each row execute function app_private.guard_assignment();

-- Legal source versions: once approved, only retirement or supersession may change.
create function app_private.guard_source_version() returns trigger
language plpgsql security definer set search_path = '' as $$
declare v_scope_changed boolean;
begin
  if tg_op = 'UPDATE' and old.approval_state in ('approved','retired') then
    if (to_jsonb(new) - array['approval_state','superseded_by','commencement_status']) is distinct from
       (to_jsonb(old) - array['approval_state','superseded_by','commencement_status']) then
      raise exception 'An approved legal source version cannot be edited. Create a new version.' using errcode = '55000';
    end if;
    if new.approval_state not in ('approved','retired') then
      raise exception 'An approved legal source version cannot go back to draft' using errcode = '55000';
    end if;
  end if;
  if new.approval_state = 'approved' and not new.is_demo then
    if new.verification_status <> 'verified' then
      raise exception 'A legal source version must be verified against the official text before approval' using errcode = '23514';
    end if;
    if new.verified_by is not distinct from new.created_by then
      raise exception 'The verifier must be a different person from the person who created the record' using errcode = '23514';
    end if;
  end if;
  return new;
end $$;
create trigger guard_source_version before insert or update on public.legal_source_versions
  for each row execute function app_private.guard_source_version();
create trigger no_delete_source_version before delete on public.legal_source_versions
  for each row execute function app_private.block_change();

-- Control versions: immutable once approved. Approval needs a verified source and a second person.
create function app_private.guard_control_version() returns trigger
language plpgsql security definer set search_path = '' as $$
declare s record;
begin
  if tg_op = 'UPDATE' and old.review_status in ('approved','retired') then
    if (to_jsonb(new) - array['review_status','retired_at']) is distinct from
       (to_jsonb(old) - array['review_status','retired_at']) then
      raise exception 'An approved control version cannot be edited. Create a new version.' using errcode = '55000';
    end if;
    if new.review_status <> 'retired' and new.review_status <> old.review_status then
      raise exception 'An approved control version can only be retired' using errcode = '55000';
    end if;
  end if;
  if new.review_status = 'approved' and (tg_op = 'INSERT' or old.review_status <> 'approved') and not new.is_demo then
    if new.approved_by is not distinct from new.created_by then
      raise exception 'A control version must be approved by someone other than its author' using errcode = '23514';
    end if;
    select * into s from public.legal_source_versions where id = new.source_version_id;
    if s.id is null or s.approval_state <> 'approved' or s.verification_status <> 'verified' then
      raise exception 'A control version can only be approved against a verified, approved legal source version' using errcode = '23514';
    end if;
    if new.commencement_status = 'Requires Verification' then
      raise exception 'Commencement status must be verified before approval' using errcode = '23514';
    end if;
  end if;
  return new;
end $$;
create trigger guard_control_version before insert or update on public.control_versions
  for each row execute function app_private.guard_control_version();
create trigger no_delete_control_version before delete on public.control_versions
  for each row execute function app_private.block_change();

-- Assessment children cannot change while the assessment is submitted or approved.
create function app_private.guard_assessment_children() returns trigger
language plpgsql security definer set search_path = '' as $$
declare v_status text; v_id uuid;
begin
  v_id := case when tg_op = 'DELETE' then old.assessment_id else new.assessment_id end;
  select status into v_status from public.assessments where id = v_id;
  if v_status in ('submitted_for_review','approved') then
    raise exception 'The assessment is % and cannot be edited. Reopen it with a reason first.', v_status using errcode = '55000';
  end if;
  return case when tg_op = 'DELETE' then old else new end;
end $$;
create trigger guard_children before insert or update or delete on public.assessment_items
  for each row execute function app_private.guard_assessment_children();
create trigger guard_children before insert or update or delete on public.applicability_decisions
  for each row execute function app_private.guard_assessment_children();

create function app_private.assessment_item_rules() returns trigger
language plpgsql security definer set search_path = '' as $$
declare cv record; v_firm uuid;
begin
  if tg_op = 'INSERT' or new.control_version_id is distinct from old.control_version_id then
    select v.review_status, c.scope, c.firm_id into cv
      from public.control_versions v join public.controls c on c.id = v.control_id
     where v.id = new.control_version_id;
    select firm_id into v_firm from public.tenants where id = new.tenant_id;
    if cv.review_status is distinct from 'approved' then
      raise exception 'Only approved control versions can be assessed' using errcode = '23514';
    end if;
    if cv.scope = 'firm' and cv.firm_id is distinct from v_firm then
      raise exception 'That control belongs to a different firm' using errcode = '42501';
    end if;
  end if;
  if new.evidence_quality = 'verified' and not exists (
       select 1 from public.evidence_records e
        where e.assessment_item_id = new.id and e.status = 'verified'
          and (e.valid_until is null or e.valid_until >= current_date)) then
    raise exception 'Evidence quality can be Verified only when verified, unexpired evidence is linked to this item' using errcode = '23514';
  end if;
  if tg_op = 'INSERT' or new.result is distinct from old.result then
    if new.result <> 'not_assessed' then
      new.assessed_by := auth.uid();
      new.assessed_at := now();
    end if;
  end if;
  return new;
end $$;
create trigger item_rules before insert or update on public.assessment_items
  for each row execute function app_private.assessment_item_rules();

create function app_private.mark_assessment_in_progress() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  update public.assessments set status = 'in_progress' where id = new.assessment_id and status = 'draft';
  return null;
end $$;
create trigger mark_in_progress after insert or update on public.assessment_items
  for each row execute function app_private.mark_assessment_in_progress();

-- Approved assessments keep their content. The reviewer RPC reopens them with a reason.
create function app_private.guard_assessment() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  if old.status = 'approved' and new.status = 'approved' and
     (to_jsonb(new) - array['updated_at','shared_with_client']) is distinct from (to_jsonb(old) - array['updated_at','shared_with_client']) then
    raise exception 'An approved assessment cannot be edited. Reopen it with a reason first.' using errcode = '55000';
  end if;
  if new.reviewer_id is not null and new.reviewer_id is distinct from old.reviewer_id then
    if not exists (select 1 from public.engagement_assignments ea join public.firm_memberships fm on fm.user_id = ea.user_id
                    join public.tenants t on t.id = ea.tenant_id and t.firm_id = fm.firm_id
                    where ea.tenant_id = new.tenant_id and ea.user_id = new.reviewer_id
                      and ea.role = 'reviewer' and ea.status = 'active' and fm.status = 'active') then
      raise exception 'The reviewer must hold an active reviewer assignment for this client' using errcode = '23514';
    end if;
  end if;
  return new;
end $$;
create trigger guard_assessment before update on public.assessments
  for each row execute function app_private.guard_assessment();

-- Closed or risk-accepted actions are locked until a reviewer reopens them.
create function app_private.guard_action() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  if old.status in ('closed','accepted_risk') and new.status = old.status
     and (to_jsonb(new) - 'updated_at') is distinct from (to_jsonb(old) - 'updated_at') then
    raise exception 'A closed or risk-accepted action is locked. Ask a reviewer to reopen it.' using errcode = '55000';
  end if;
  return new;
end $$;
create trigger guard_action before update on public.corrective_actions
  for each row execute function app_private.guard_action();

-- A final report requires an approved assessment at the same version.
create function app_private.guard_report() returns trigger
language plpgsql security definer set search_path = '' as $$
declare a record;
begin
  select status, version_no into a from public.assessments where id = new.assessment_id;
  if new.status = 'final' and (a.status is distinct from 'approved' or a.version_no is distinct from new.assessment_version) then
    raise exception 'A report can be marked final only for an approved assessment at the same version' using errcode = '23514';
  end if;
  return new;
end $$;
create trigger guard_report before insert or update on public.report_runs
  for each row execute function app_private.guard_report();

-- ---------------------------------------------------------------------
-- 8. Descriptions (these feed DATA_DICTIONARY.md and show in the Supabase table editor)
-- ---------------------------------------------------------------------
create function app_private.c(p_table text, p_col text, p_text text) returns void
language plpgsql as $$
begin
  if p_col is null then execute format('comment on table public.%I is %L', p_table, p_text);
  else execute format('comment on column public.%I.%I is %L', p_table, p_col, p_text); end if;
end $$;

select app_private.c('profiles', null, 'One row per signed-in user. Created automatically from Supabase Auth. Holds name and email only.');
select app_private.c('profiles','status','active or disabled. A disabled profile loses all access.');
select app_private.c('platform_admins', null, 'Platform administrators. No API access. Managed only with the service role or the SQL editor. Platform administrators have no automatic access to client content.');
select app_private.c('firms', null, 'A Chartered Accountancy firm that serves client institutions.');
select app_private.c('firm_memberships', null, 'Which users belong to a firm and in what role. Membership alone does not give access to any client.');
select app_private.c('firm_memberships','role','firm_admin manages users, clients and assignments. team_member does the work. reviewer reviews and signs off.');
select app_private.c('tenants', null, 'A client institution workspace. The tenant_id on every other table points here.');
select app_private.c('tenants','firm_id','The firm that serves this client. Cannot be changed after creation.');
select app_private.c('tenants','institution_type','School, college, university, coaching centre, vocational institute, research institute or other.');
select app_private.c('tenants','sector','Free-text sector or board, for example CBSE school or State university.');
select app_private.c('tenants','description','Business context of the institution.');
select app_private.c('tenants','headcount_band','Approximate size band, for example 1000-5000 students.');
select app_private.c('tenants','primary_contact_name','Name of the main client contact. Business contact detail only.');
select app_private.c('tenants','primary_contact_email','Business email of the main client contact.');
select app_private.c('tenants','status','onboarding, active, paused or closed.');
select app_private.c('tenants','is_demo','True for synthetic demonstration workspaces. The screens must show a Demo banner.');
select app_private.c('tenant_memberships', null, 'Which users belong to a client workspace and in what role.');
select app_private.c('tenant_memberships','role','client_admin, privacy_lead, department_coordinator, evidence_contributor, management_viewer or client_reviewer.');
select app_private.c('engagements', null, 'The firm''s engagement with a client: scope, period and status.');
select app_private.c('engagements','firm_id','Copy of the tenant''s firm, enforced by a composite foreign key.');
select app_private.c('engagements','onboarding_status','not_started, in_progress or complete.');
select app_private.c('engagements','missing_information','What the firm is still waiting for from the client.');
select app_private.c('engagements','assessment_period_start','First day of the period being assessed.');
select app_private.c('engagements','assessment_period_end','Last day of the period being assessed.');
select app_private.c('engagement_assignments', null, 'Grants a firm user access to one client. This, not firm membership, opens client content.');
select app_private.c('engagement_assignments','role','team_member works on the client. reviewer reviews and signs off.');
select app_private.c('engagement_assignments','status','active or revoked. Revoking removes access on the next request.');
select app_private.c('engagement_notes', null, 'Notes on an engagement. firm_only notes are never visible to client users.');
select app_private.c('engagement_notes','visibility','firm_only or client_visible.');
select app_private.c('departments', null, 'A department of the client institution, such as Admissions, Exams, Accounts, HR.');
select app_private.c('departments','coordinator_user_id','The department coordinator who may edit inventory records for this department.');
select app_private.c('departments','archived_at','Set when the department is archived.');
select app_private.c('vendors', null, 'Processors and other recipients of personal data (ERP provider, SMS gateway, cloud host).');
select app_private.c('vendors','relationship','processor, recipient, joint or other.');
select app_private.c('vendors','country_code','Two-letter country code where the vendor stores or processes data.');
select app_private.c('vendors','contract_status','none, in_place, under_review or unknown.');
select app_private.c('systems', null, 'Systems and places where personal data is held: applications, databases, cloud services, paper stores.');
select app_private.c('systems','system_type','application, database, cloud_service, paper_records, device, network or other.');
select app_private.c('systems','hosting_location','Where the system is hosted, for example On premises or Cloud, Mumbai region.');
select app_private.c('data_categories', null, 'Global reference list of personal-data categories. Maintained by the platform, readable by signed-in users.');
select app_private.c('data_categories','is_special_case','True for categories that need extra care, such as children or biometric data. A flag for review, not a legal classification.');
select app_private.c('processing_activities', null, 'The personal-data inventory. One row per processing activity. Stores metadata about processing, never copies of personal data.');
select app_private.c('processing_activities','owner_user_id','Accountable owner of the activity at the client.');
select app_private.c('processing_activities','data_principal_categories','Whose data: students, applicants, parents, staff, alumni and so on.');
select app_private.c('processing_activities','collection_source','Where the data comes from, for example admission form.');
select app_private.c('processing_activities','purposes','Why the data is processed. Specific, not generic.');
select app_private.c('processing_activities','processing_operations','What is done with it: collect, store, share, publish, delete.');
select app_private.c('processing_activities','internal_recipients','Internal teams that receive the data.');
select app_private.c('processing_activities','external_recipients','Outside parties that receive the data (free text; link vendors through activity_vendors).');
select app_private.c('processing_activities','lawful_ground','Assessed ground. Defaults to not_yet_assessed. The system never assumes a ground; a rationale is required for any other value except needs_legal_review.');
select app_private.c('processing_activities','lawful_ground_rationale','Why the ground applies, with reference to the statutory wording and facts.');
select app_private.c('processing_activities','notice_reference','Where the notice for this activity can be found.');
select app_private.c('processing_activities','consent_reference','Where consent records for this activity are kept.');
select app_private.c('processing_activities','retention_criteria','How long the data is kept and what triggers deletion.');
select app_private.c('processing_activities','deletion_process','How deletion is carried out and approved.');
select app_private.c('processing_activities','cross_border','none, yes or unknown. Unknown is a gap, not a pass.');
select app_private.c('processing_activities','cross_border_notes','Countries, vendors and transfer considerations.');
select app_private.c('processing_activities','children_data','True if the activity involves children''s data.');
select app_private.c('processing_activities','special_case_flags','Other special cases such as disability, health, biometric.');
select app_private.c('processing_activities','volume_indicator','Rough volume for internal risk prioritisation. Not a legal threshold.');
select app_private.c('processing_activities','sensitivity_indicator','Rough sensitivity for internal risk prioritisation. Not a legal classification.');
select app_private.c('processing_activities','review_date','When the record was last reviewed.');
select app_private.c('processing_activities','status','draft, active, needs_review or archived. Archiving needs a reason.');
select app_private.c('activity_systems', null, 'Links a processing activity to the systems that hold its data.');
select app_private.c('activity_vendors', null, 'Links a processing activity to the vendors that receive or process its data.');
select app_private.c('activity_data_categories', null, 'Links a processing activity to the categories of personal data it uses.');
select app_private.c('legal_sources', null, 'A legal source: an Act, Rule, notification, order or guidance. Global (platform-maintained) or owned by one firm.');
select app_private.c('legal_sources','scope','global or firm.');
select app_private.c('legal_sources','official_url','Link to the official text, for example the Gazette notification.');
select app_private.c('legal_source_versions', null, 'A dated version of a legal source with its verification and commencement status. Immutable once approved.');
select app_private.c('legal_source_versions','retrieved_on','Date the official text was retrieved.');
select app_private.c('legal_source_versions','effective_on','Date the text takes effect, where verified.');
select app_private.c('legal_source_versions','commencement_status','In Force — Verified, Scheduled — Verified, Not Yet in Force — Verified, Requires Verification or Superseded. A library status, not a legal opinion.');
select app_private.c('legal_source_versions','verification_status','unverified or verified against the official text. Verified needs a verifier and a timestamp.');
select app_private.c('legal_source_versions','approval_state','draft, in_review, approved or retired.');
select app_private.c('legal_source_versions','superseded_by','The newer version that replaces this one.');
select app_private.c('legal_source_versions','is_demo','True for synthetic demonstration records. Demo records are exempt from the verification gate.');
select app_private.c('controls', null, 'A stable control identity. The wording lives in control_versions.');
select app_private.c('controls','control_code','Stable ID such as NTC-01, unique within the owner.');
select app_private.c('control_versions', null, 'A versioned control: statement, question, evidence and test. Immutable once approved.');
select app_private.c('control_versions','legal_reference','Section or rule the control rests on.');
select app_private.c('control_versions','statement','What the control requires.');
select app_private.c('control_versions','applicability_logic','When the control applies.');
select app_private.c('control_versions','commencement_status','Library commencement status for this control version.');
select app_private.c('control_versions','assessment_question','The question the assessor answers.');
select app_private.c('control_versions','required_evidence','What evidence supports a result.');
select app_private.c('control_versions','test_procedure','How the assessor tests the control.');
select app_private.c('control_versions','expected_result','What a satisfactory result looks like.');
select app_private.c('control_versions','risk_guidance','How to judge the risk of a gap.');
select app_private.c('control_versions','review_status','draft, in_review, approved or retired. Approval needs a second person and, outside demos, a verified source.');
select app_private.c('control_versions','approved_by','Reviewer who approved the version.');
select app_private.c('control_versions','is_demo','True for synthetic demonstration records.');
select app_private.c('control_versions','change_note','What changed from the previous version.');
select app_private.c('assessments', null, 'A gap assessment for one client and period.');
select app_private.c('assessments','status','draft, in_progress, submitted_for_review, returned, approved or reopened. Changed only through the review functions.');
select app_private.c('assessments','version_no','Increases each time an approved assessment is reopened.');
select app_private.c('assessments','prepared_by','The preparer. The reviewer must be a different person.');
select app_private.c('assessments','reviewer_id','The assigned firm reviewer.');
select app_private.c('assessments','shared_with_client','When true, client users can see the assessment. Set on approval.');
select app_private.c('assessments','limitations','Scope exclusions, assumptions and items not assessed.');
select app_private.c('applicability_decisions', null, 'Applicability questions with outcome and rationale, recorded per assessment.');
select app_private.c('applicability_decisions','outcome','applicable, not_applicable or needs_legal_review. A rationale is always required.');
select app_private.c('assessment_items', null, 'One row per control assessed. Keeps the control version used.');
select app_private.c('assessment_items','control_version_id','The exact control version assessed. Later versions never change this.');
select app_private.c('assessment_items','applicability','Legal applicability, kept separate from implementation status.');
select app_private.c('assessment_items','result','implemented_verified, partial, gap, not_assessed or not_applicable. not_assessed is never counted as compliant.');
select app_private.c('assessment_items','evidence_quality','none, submitted, verified or insufficient. Verified needs linked verified evidence.');
select app_private.c('assessment_items','risk_level','low, medium, high or critical.');
select app_private.c('assessment_items','assessor_notes','Assessor notes. Visible to anyone who can read the item.');
select app_private.c('assessment_items','owner_user_id','The person responsible for providing evidence or fixing the gap.');
select app_private.c('assessment_items','assessed_by','Set automatically when a result is recorded.');
select app_private.c('evidence_records', null, 'Evidence metadata. File bytes live in the private evidence storage bucket.');
select app_private.c('evidence_records','category','policy, procedure, record, screenshot, contract, training, log, report, other or document.');
select app_private.c('evidence_records','status','missing, submitted, under_review, verified, rejected or expired. Changed only through decide_evidence.');
select app_private.c('evidence_records','storage_path','Path in the private bucket. Always starts with the tenant id.');
select app_private.c('evidence_records','file_name','Original file name. Do not put personal data in file names.');
select app_private.c('evidence_records','sha256','SHA-256 of the file, to show it has not changed.');
select app_private.c('evidence_records','version_no','Version of this evidence item.');
select app_private.c('evidence_records','supersedes_id','The earlier evidence record this replaces.');
select app_private.c('evidence_records','valid_until','Date after which the evidence needs refreshing.');
select app_private.c('evidence_records','uploaded_by','Who uploaded the file.');
select app_private.c('evidence_reviews', null, 'Append-only record of evidence review decisions.');
select app_private.c('evidence_reviews','decision','under_review, verified, rejected or needs_refresh. Rejection needs comments.');
select app_private.c('corrective_actions', null, 'Remediation actions, from an assessment gap or raised independently.');
select app_private.c('corrective_actions','status','open, in_progress, blocked, submitted_for_review, closed or accepted_risk. Changed only through the action functions.');
select app_private.c('corrective_actions','closure_evidence_id','Evidence that shows the action is complete.');
select app_private.c('corrective_actions','closure_verified_by','Reviewer who verified closure.');
select app_private.c('corrective_actions','risk_accepted_by','Authorised approver of an accepted risk.');
select app_private.c('corrective_actions','risk_acceptance_rationale','Why the risk is accepted. Required.');
select app_private.c('review_decisions', null, 'Append-only trail of review decisions: who, when, why, which version.');
select app_private.c('review_decisions','subject_type','assessment, evidence, corrective_action, risk_acceptance or report.');
select app_private.c('review_decisions','reviewer_capacity','firm_reviewer (CA firm review) or client_reviewer (client management acceptance). The two are never mixed.');
select app_private.c('assessment_snapshots', null, 'Frozen copy of an assessment at each approval, so history survives reopening.');
select app_private.c('audit_events', null, 'Append-only log of material actions. Holds identifiers and status changes, never personal data or document content.');
select app_private.c('audit_events','details','Small JSON with changed column names and status or role transitions.');
select app_private.c('notifications', null, 'In-app and email reminders (later phase). Never holds sensitive content.');
select app_private.c('notifications','status','pending, sent, failed, read or cancelled. sent requires provider confirmation.');
select app_private.c('report_runs', null, 'A generated report: type, assessment version, draft or final, and the denominators used.');
select app_private.c('report_runs','status','draft or final. Final needs an approved assessment at the same version.');
select app_private.c('report_runs','denominators','Counts behind every percentage in the report.');

drop function app_private.c(text, text, text);
