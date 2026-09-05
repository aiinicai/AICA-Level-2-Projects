-- ============================================================================
--  GST Notice Analyser — Supabase schema
--  Run this once in  Supabase Dashboard → SQL Editor → New query → Run.
--  Safe to re-run: every object uses "if not exists" / "or replace".
-- ============================================================================

-- ── Extensions ──────────────────────────────────────────────────────────────
create extension if not exists "pgcrypto";      -- gen_random_uuid()

-- ── Firms & membership ──────────────────────────────────────────────────────
create table if not exists public.firms (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  join_code   text not null unique default upper(substr(replace(gen_random_uuid()::text,'-',''),1,8)),
  created_by  uuid references auth.users(id),
  created_at  timestamptz not null default now()
);

create table if not exists public.firm_members (
  firm_id    uuid not null references public.firms(id) on delete cascade,
  user_id    uuid not null references auth.users(id) on delete cascade,
  role       text not null default 'member' check (role in ('owner','member')),
  email      text,
  joined_at  timestamptz not null default now(),
  primary key (firm_id, user_id)
);

-- Helper: the firm ids the current user belongs to.
-- security definer so it can read firm_members without recursing through RLS.
create or replace function public.current_firm_ids()
returns setof uuid
language sql
security definer
stable
set search_path = public
as $$
  select firm_id from public.firm_members where user_id = auth.uid()
$$;

-- Create a firm and make the caller its owner. Returns the new firm id.
create or replace function public.create_firm(p_name text)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare new_id uuid;
begin
  insert into public.firms (name, created_by) values (p_name, auth.uid())
  returning id into new_id;
  insert into public.firm_members (firm_id, user_id, role, email)
  values (new_id, auth.uid(), 'owner', (select email from auth.users where id = auth.uid()));
  return new_id;
end;
$$;

-- Join an existing firm by its join code. Returns the firm id.
create or replace function public.join_firm(p_code text)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare target uuid;
begin
  select id into target from public.firms where upper(join_code) = upper(trim(p_code));
  if target is null then
    raise exception 'No firm found for that code';
  end if;
  insert into public.firm_members (firm_id, user_id, role, email)
  values (target, auth.uid(), 'member', (select email from auth.users where id = auth.uid()))
  on conflict (firm_id, user_id) do nothing;
  return target;
end;
$$;

-- Regenerate a firm's join code (owner only).
create or replace function public.rotate_join_code(p_firm uuid)
returns text
language plpgsql
security definer
set search_path = public
as $$
declare new_code text;
begin
  if not exists (select 1 from public.firm_members where firm_id = p_firm and user_id = auth.uid() and role = 'owner') then
    raise exception 'Only the firm owner can rotate the join code';
  end if;
  new_code := upper(substr(replace(gen_random_uuid()::text,'-',''),1,8));
  update public.firms set join_code = new_code where id = p_firm;
  return new_code;
end;
$$;

-- ── Firm settings (one row per firm) ────────────────────────────────────────
create table if not exists public.firm_settings (
  firm_id            uuid primary key references public.firms(id) on delete cascade,
  ca_firm_name       text not null default '',
  ca_name            text not null default '',
  membership_no      text not null default '',
  firm_address       text not null default '',
  contact_email      text not null default '',
  contact_phone      text not null default '',
  letterhead_header   text not null default '',
  updated_at         timestamptz not null default now()
);

-- ── Core data tables ───────────────────────────────────────────────────────
create table if not exists public.clients (
  id          text primary key,
  firm_id     uuid not null references public.firms(id) on delete cascade,
  gstin       text not null default '',
  legal_name  text not null default '',
  trade_name  text not null default '',
  email       text not null default '',
  phone       text not null default '',
  pan         text,
  address     text,
  created_at  timestamptz not null default now()
);
create index if not exists clients_firm_idx on public.clients(firm_id);

create table if not exists public.notice_cases (
  id                  text primary key,
  firm_id             uuid not null references public.firms(id) on delete cascade,
  client_id           text not null references public.clients(id) on delete cascade,
  notice_number       text not null default '',
  form_type           text not null default 'DRC-01',
  financial_year      text not null default '',
  period              text not null default '',
  notice_date         text not null default '',
  reply_deadline      text not null default '',
  hearing_date        text,
  issuing_authority   text not null default '',
  sections_mentioned  text not null default '',
  principal_tax       numeric not null default 0,
  interest            numeric not null default 0,
  penalty             numeric not null default 0,
  total_demand        numeric not null default 0,
  status              text not null default 'UNDER_REVIEW',
  raw_text            text,
  pdf_data_url        text,          -- base64 data URL; see SUPABASE-SETUP.md note on size
  pdf_file_name       text,
  is_ca_verified      boolean not null default false,
  din                 text,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);
create index if not exists cases_firm_idx   on public.notice_cases(firm_id);
create index if not exists cases_client_idx on public.notice_cases(client_id);

create table if not exists public.notice_issues (
  id                       text primary key,
  firm_id                  uuid not null references public.firms(id) on delete cascade,
  case_id                  text not null references public.notice_cases(id) on delete cascade,
  issue_number             integer not null default 1,
  title                    text not null default '',
  allegation               text not null default '',
  section_rule             text not null default '',
  page_ref                 text not null default '',
  tax_amount               numeric not null default 0,
  interest_amount          numeric not null default 0,
  penalty_amount           numeric not null default 0,
  total_amount             numeric not null default 0,
  probable_reason          text not null default '',
  figure_source            text not null default '',
  data_required            text not null default '',
  reconciliation_required  text not null default '',
  client_questions         text not null default '',
  documents_required       text not null default '',
  defense_points           text not null default '',
  legal_position           text not null default '',
  risk_level               text not null default 'HIGH',
  facts_category           text,
  calculation_summary      text
);
create index if not exists issues_case_idx on public.notice_issues(case_id);

create table if not exists public.reconciliations (
  id               text primary key,
  firm_id          uuid not null references public.firms(id) on delete cascade,
  case_id          text not null references public.notice_cases(id) on delete cascade,
  recon_type       text not null default '',
  period           text not null default '',
  notice_value     numeric not null default 0,
  portal_value     numeric not null default 0,
  books_value      numeric not null default 0,
  variance         numeric not null default 0,
  variance_reason  text not null default '',
  status           text not null default 'MISSING_DATA',
  hsn_code         text,
  supplier_gstin   text,
  issue_number     integer,
  portal_hint      text,
  books_hint       text
);
create index if not exists recons_case_idx on public.reconciliations(case_id);

create table if not exists public.document_items (
  id              text primary key,
  firm_id         uuid not null references public.firms(id) on delete cascade,
  case_id         text not null references public.notice_cases(id) on delete cascade,
  doc_name        text not null default '',
  category        text not null default '',
  status          text not null default 'Pending',
  requested_date  text not null default '',
  due_date        text not null default '',
  received_date   text,
  remarks         text,
  period          text,
  custom_fields   jsonb
);
create index if not exists docs_case_idx on public.document_items(case_id);

create table if not exists public.portal_figure_sets (
  case_id     text primary key references public.notice_cases(id) on delete cascade,
  firm_id     uuid not null references public.firms(id) on delete cascade,
  figures     jsonb not null default '[]'::jsonb,
  updated_at  timestamptz not null default now()
);
create index if not exists pfs_firm_idx on public.portal_figure_sets(firm_id);

create table if not exists public.discussions (
  id               text primary key,
  firm_id          uuid not null references public.firms(id) on delete cascade,
  case_id          text not null references public.notice_cases(id) on delete cascade,
  date             text not null default '',
  mode             text not null default 'Meeting',
  topic            text not null default '',
  notes            text not null default '',
  questions_asked  text not null default '',
  client_response  text not null default '',
  action_items     text not null default '',
  follow_up_date   text not null default '',
  status           text not null default 'Open',
  created_at       timestamptz not null default now()
);
create index if not exists disc_case_idx on public.discussions(case_id);

-- ── Row-Level Security ─────────────────────────────────────────────────────
-- Everything is scoped to "a firm the current user belongs to".

alter table public.firms              enable row level security;
alter table public.firm_members       enable row level security;
alter table public.firm_settings      enable row level security;
alter table public.clients            enable row level security;
alter table public.notice_cases       enable row level security;
alter table public.notice_issues      enable row level security;
alter table public.reconciliations    enable row level security;
alter table public.document_items     enable row level security;
alter table public.portal_figure_sets enable row level security;
alter table public.discussions        enable row level security;

-- firms: members can read; owner can update name.
drop policy if exists firms_read   on public.firms;
drop policy if exists firms_update on public.firms;
create policy firms_read   on public.firms for select using (id in (select current_firm_ids()));
create policy firms_update on public.firms for update using (
  exists (select 1 from public.firm_members m where m.firm_id = firms.id and m.user_id = auth.uid() and m.role = 'owner')
);

-- firm_members: a user sees the rosters of firms they belong to; owner manages.
drop policy if exists members_read   on public.firm_members;
drop policy if exists members_delete on public.firm_members;
create policy members_read on public.firm_members for select using (
  firm_id in (select current_firm_ids())
);
create policy members_delete on public.firm_members for delete using (
  user_id = auth.uid()                                            -- leave a firm yourself
  or exists (select 1 from public.firm_members o
             where o.firm_id = firm_members.firm_id and o.user_id = auth.uid() and o.role = 'owner')
);

-- Generic per-firm policy for every data table.
do $$
declare t text;
begin
  foreach t in array array[
    'firm_settings','clients','notice_cases','notice_issues','reconciliations',
    'document_items','portal_figure_sets','discussions'
  ]
  loop
    execute format('drop policy if exists %I_all on public.%I', t, t);
    execute format(
      'create policy %I_all on public.%I for all
         using (firm_id in (select current_firm_ids()))
         with check (firm_id in (select current_firm_ids()))', t, t);
  end loop;
end $$;

-- ── Grants ────────────────────────────────────────────────────────────────
grant usage on schema public to authenticated;
grant all on all tables in schema public to authenticated;
grant execute on function public.create_firm(text)      to authenticated;
grant execute on function public.join_firm(text)        to authenticated;
grant execute on function public.rotate_join_code(uuid) to authenticated;
grant execute on function public.current_firm_ids()     to authenticated;
