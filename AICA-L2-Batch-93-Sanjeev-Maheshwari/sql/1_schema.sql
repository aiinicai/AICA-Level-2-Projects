-- Expense Settlement Tool — Supabase schema
-- Separate project from PRISM (FS review). Personal reimbursement data,
-- deliberately isolated per the architecture statement's decision.
-- Run this once, in a fresh Supabase project's SQL Editor.

-- ============================================================
-- ENUM TYPES
-- ============================================================

create type designation_type as enum ('article', 'qualified', 'staff');

create type claim_status as enum ('draft', 'submitted', 'approved', 'settled');
-- 'rejected' is not a stored status: a rejection returns the claim straight
-- to 'draft' (per the architecture doc) and is recorded as an action in
-- approval_log, plus claims.rejection_reason for the employee to see.

create type expense_category as enum ('conveyance', 'out_of_station', 'boarding_lodging', 'other');

create type log_action as enum ('submitted', 'approved', 'rejected', 'withdrawn', 'settled');


-- ============================================================
-- TEAMS and EMPLOYEES reference each other (a team has a head who is an
-- employee; an employee belongs to a team) — created without those two FKs,
-- which are added afterward via ALTER TABLE once both tables exist.
-- ============================================================

create table teams (
  team_id uuid primary key default gen_random_uuid(),
  team_name text not null,
  head_employee_id uuid,        -- FK added below, nullable to allow bootstrapping
  backup_approver_id uuid,      -- FK added below, nullable
  created_at timestamptz not null default now()
);

create table employees (
  employee_id uuid primary key default gen_random_uuid(),
  employee_code text not null unique,
  name text not null,
  designation designation_type not null,
  team_id uuid references teams(team_id),   -- nullable: an employee can exist before team assignment
  status text not null default 'active' check (status in ('active', 'inactive')),
  bank_account_ref text,
  is_accounts boolean not null default false,   -- accounts-department permission flag
  auth_user_id uuid unique references auth.users(id),  -- linked once they sign up; null until then
  created_at timestamptz not null default now()
);

alter table teams
  add constraint fk_teams_head foreign key (head_employee_id) references employees(employee_id),
  add constraint fk_teams_backup foreign key (backup_approver_id) references employees(employee_id);

create index idx_employees_team on employees(team_id);


-- ============================================================
-- CLAIMS (monthly header) and CLAIM_LINES
-- ============================================================

create table claims (
  claim_id uuid primary key default gen_random_uuid(),
  employee_id uuid not null references employees(employee_id),
  month text not null,                       -- e.g. '2026-09'
  status claim_status not null default 'draft',
  submitted_at timestamptz,
  approved_at timestamptz,
  approved_by uuid references employees(employee_id),
  rejection_reason text,
  settled_at timestamptz,
  settled_by uuid references employees(employee_id),
  payment_reference text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (employee_id, month)
);

create index idx_claims_employee on claims(employee_id);
create index idx_claims_status on claims(status);

create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger trg_claims_updated_at
  before update on claims
  for each row execute function set_updated_at();

create table claim_lines (
  line_id uuid primary key default gen_random_uuid(),
  claim_id uuid not null references claims(claim_id) on delete cascade,
  expense_date date not null,
  category expense_category not null,
  client_code text,              -- universal across all categories; 'GMJ' for non-billable
  from_location text,
  to_location text,
  mode_of_transport text,
  amount numeric(12,2) not null check (amount > 0),
  other_label text,
  description text,
  receipt_file_ref text,         -- Supabase Storage path, not the file itself
  rejection_flag boolean not null default false,
  rejection_note text,
  created_at timestamptz not null default now(),
  -- Other category requires both a label and a description
  constraint chk_other_fields check (
    category <> 'other' or (other_label is not null and description is not null)
  )
);

create index idx_claim_lines_claim on claim_lines(claim_id);


-- ============================================================
-- APPROVAL LOG and UNLOCK LOG
-- ============================================================

create table approval_log (
  log_id uuid primary key default gen_random_uuid(),
  claim_id uuid not null references claims(claim_id) on delete cascade,
  action log_action not null,
  actor_id uuid not null references employees(employee_id),
  note text,
  at timestamptz not null default now()
);

create index idx_approval_log_claim on approval_log(claim_id);

create table unlock_log (
  log_id uuid primary key default gen_random_uuid(),
  claim_id uuid not null references claims(claim_id) on delete cascade,
  unlocked_by uuid not null references employees(employee_id),
  reason text not null check (char_length(trim(reason)) > 0),
  unlocked_at timestamptz not null default now(),
  relocked_at timestamptz
);

create index idx_unlock_log_claim on unlock_log(claim_id);
create index idx_unlock_log_open on unlock_log(claim_id) where relocked_at is null;


-- ============================================================
-- HELPER FUNCTIONS (used by RLS policies and by the RPC functions below)
-- ============================================================

create or replace function current_employee_id()
returns uuid as $$
  select employee_id from employees where auth_user_id = auth.uid();
$$ language sql stable security definer;

create or replace function is_accounts()
returns boolean as $$
  select coalesce((select is_accounts from employees where auth_user_id = auth.uid()), false);
$$ language sql stable security definer;

create or replace function is_head_of_team(p_team_id uuid)
returns boolean as $$
  select exists (
    select 1 from teams
    where team_id = p_team_id
      and (head_employee_id = current_employee_id() or backup_approver_id = current_employee_id())
  );
$$ language sql stable security definer;

create or replace function claim_has_open_unlock(p_claim_id uuid)
returns boolean as $$
  select exists (
    select 1 from unlock_log where claim_id = p_claim_id and relocked_at is null
  );
$$ language sql stable security definer;


-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

alter table teams enable row level security;
alter table employees enable row level security;
alter table claims enable row level security;
alter table claim_lines enable row level security;
alter table approval_log enable row level security;
alter table unlock_log enable row level security;

-- Teams: names/heads are not sensitive — any signed-in employee can read
create policy "read_teams" on teams for select using (auth.uid() is not null);

-- Employees: see your own record, your team's head/backup can see their
-- team's people, accounts can see everyone (needed for settlement/payment)
create policy "read_employees" on employees for select using (
  auth_user_id = auth.uid()
  or is_head_of_team(team_id)
  or is_accounts()
);

-- Claims: owner sees their own; team head/backup sees their team's claims;
-- accounts sees only approved-or-settled claims (never drafts in progress)
create policy "read_claims" on claims for select using (
  employee_id = current_employee_id()
  or is_head_of_team((select team_id from employees where employee_id = claims.employee_id))
  or (is_accounts() and status in ('approved', 'settled'))
);

-- Claims: an employee creates their own claim, starting in Draft
create policy "create_own_claim" on claims for insert with check (
  employee_id = current_employee_id() and status = 'draft'
);

-- Claims: no direct status changes from the client — every transition
-- (submit/approve/reject/settle/unlock) goes through a function below,
-- each of which runs as security definer and enforces its own rules.
-- Direct UPDATE is not granted here at all.

-- Claim lines: same read visibility as the parent claim
create policy "read_claim_lines" on claim_lines for select using (
  exists (select 1 from claims c where c.claim_id = claim_lines.claim_id and (
    c.employee_id = current_employee_id()
    or is_head_of_team((select team_id from employees where employee_id = c.employee_id))
    or (is_accounts() and c.status in ('approved', 'settled'))
  ))
);

-- Claim lines: owner may insert/update/delete only while the claim is Draft
create policy "edit_own_lines_while_draft" on claim_lines for all using (
  exists (select 1 from claims c where c.claim_id = claim_lines.claim_id
    and c.employee_id = current_employee_id() and c.status = 'draft')
) with check (
  exists (select 1 from claims c where c.claim_id = claim_lines.claim_id
    and c.employee_id = current_employee_id() and c.status = 'draft')
);

-- Claim lines: accounts may correct a line only while an unlock is open
create policy "accounts_edit_during_unlock" on claim_lines for update using (
  is_accounts() and claim_has_open_unlock(claim_lines.claim_id)
) with check (
  is_accounts() and claim_has_open_unlock(claim_lines.claim_id)
);

-- Logs: read-only from the client, same visibility as the parent claim;
-- rows are written only by the functions below (security definer)
create policy "read_approval_log" on approval_log for select using (
  exists (select 1 from claims c where c.claim_id = approval_log.claim_id and (
    c.employee_id = current_employee_id()
    or is_head_of_team((select team_id from employees where employee_id = c.employee_id))
    or is_accounts()
  ))
);
create policy "read_unlock_log" on unlock_log for select using (
  exists (select 1 from claims c where c.claim_id = unlock_log.claim_id and (
    c.employee_id = current_employee_id()
    or is_head_of_team((select team_id from employees where employee_id = c.employee_id))
    or is_accounts()
  ))
);


-- ============================================================
-- GRANTS
-- RLS policies alone are not sufficient in Postgres: a role needs a
-- baseline table-level GRANT before its RLS policies are even
-- evaluated. Without these, every query from `authenticated` fails
-- with 42501 (permission denied) regardless of how correct the RLS
-- policies above are. These grants are deliberately minimal, matching
-- exactly what each table's policies above already gate — nothing
-- broader. Notably, `claims` gets no UPDATE grant: every status change
-- goes through the security-definer functions below, which run with
-- the function owner's privileges, not the caller's — granting direct
-- UPDATE here would reopen the bypass those functions exist to close.

grant select on public.teams to authenticated;
grant insert, update on public.teams to authenticated;
grant select, insert on public.employees to authenticated;
grant update on public.employees to authenticated;
grant select, insert on public.claims to authenticated;
grant select, insert, update, delete on public.claim_lines to authenticated;
grant select on public.approval_log to authenticated;
grant select on public.unlock_log to authenticated;


-- ============================================================
-- STATE-TRANSITION FUNCTIONS
-- Each enforces its own authorization and business rule, then logs the
-- action. Client code calls these via Supabase's RPC endpoint rather than
-- writing to claims.status directly.
-- ============================================================

create or replace function submit_claim(p_claim_id uuid)
returns void as $$
declare
  v_employee_id uuid;
  v_status claim_status;
  v_line_count int;
begin
  select employee_id, status into v_employee_id, v_status from claims where claim_id = p_claim_id;
  if v_employee_id is null then raise exception 'Claim not found'; end if;
  if v_employee_id <> current_employee_id() then raise exception 'Not your claim'; end if;
  if v_status <> 'draft' then raise exception 'Only a Draft claim can be submitted'; end if;

  select count(*) into v_line_count from claim_lines where claim_id = p_claim_id;
  if v_line_count = 0 then raise exception 'Cannot submit a claim with no line items'; end if;

  update claims set status = 'submitted', submitted_at = now(), rejection_reason = null
    where claim_id = p_claim_id;
  insert into approval_log (claim_id, action, actor_id) values (p_claim_id, 'submitted', current_employee_id());
end;
$$ language plpgsql security definer;

create or replace function withdraw_claim(p_claim_id uuid)
returns void as $$
declare
  v_employee_id uuid;
  v_status claim_status;
begin
  select employee_id, status into v_employee_id, v_status from claims where claim_id = p_claim_id;
  if v_employee_id <> current_employee_id() then raise exception 'Not your claim'; end if;
  if v_status <> 'submitted' then raise exception 'Only a Submitted claim can be withdrawn'; end if;

  update claims set status = 'draft' where claim_id = p_claim_id;
  insert into approval_log (claim_id, action, actor_id) values (p_claim_id, 'withdrawn', current_employee_id());
end;
$$ language plpgsql security definer;

create or replace function approve_claim(p_claim_id uuid)
returns void as $$
declare
  v_owner_id uuid;
  v_team_id uuid;
  v_status claim_status;
begin
  select c.employee_id, c.status, e.team_id into v_owner_id, v_status, v_team_id
    from claims c join employees e on e.employee_id = c.employee_id
    where c.claim_id = p_claim_id;
  if v_owner_id is null then raise exception 'Claim not found'; end if;
  if not is_head_of_team(v_team_id) then raise exception 'Not authorized to approve this claim'; end if;
  if v_status <> 'submitted' then raise exception 'Only a Submitted claim can be approved'; end if;

  update claims set status = 'approved', approved_at = now(), approved_by = current_employee_id()
    where claim_id = p_claim_id;
  insert into approval_log (claim_id, action, actor_id) values (p_claim_id, 'approved', current_employee_id());
end;
$$ language plpgsql security definer;

create or replace function reject_claim(p_claim_id uuid, p_reason text)
returns void as $$
declare
  v_owner_id uuid;
  v_team_id uuid;
  v_status claim_status;
begin
  if p_reason is null or char_length(trim(p_reason)) = 0 then
    raise exception 'A rejection reason is required';
  end if;

  select c.employee_id, c.status, e.team_id into v_owner_id, v_status, v_team_id
    from claims c join employees e on e.employee_id = c.employee_id
    where c.claim_id = p_claim_id;
  if v_owner_id is null then raise exception 'Claim not found'; end if;
  if not is_head_of_team(v_team_id) then raise exception 'Not authorized to reject this claim'; end if;
  if v_status <> 'submitted' then raise exception 'Only a Submitted claim can be rejected'; end if;

  -- reopens straight to Draft, per the architecture statement
  update claims set status = 'draft', rejection_reason = p_reason where claim_id = p_claim_id;
  insert into approval_log (claim_id, action, actor_id, note) values (p_claim_id, 'rejected', current_employee_id(), p_reason);
end;
$$ language plpgsql security definer;

create or replace function settle_claim(p_claim_id uuid, p_payment_reference text)
returns void as $$
declare
  v_status claim_status;
begin
  if not is_accounts() then raise exception 'Only accounts can settle a claim'; end if;

  select status into v_status from claims where claim_id = p_claim_id;
  if v_status is null then raise exception 'Claim not found'; end if;
  if v_status <> 'approved' then raise exception 'Only an Approved claim can be settled'; end if;

  update claims set status = 'settled', settled_at = now(), settled_by = current_employee_id(),
    payment_reference = p_payment_reference
    where claim_id = p_claim_id;
  insert into approval_log (claim_id, action, actor_id, note) values (p_claim_id, 'settled', current_employee_id(), p_payment_reference);
end;
$$ language plpgsql security definer;

create or replace function unlock_claim(p_claim_id uuid, p_reason text)
returns void as $$
declare
  v_status claim_status;
begin
  if not is_accounts() then raise exception 'Only accounts can unlock a claim'; end if;
  if p_reason is null or char_length(trim(p_reason)) = 0 then
    raise exception 'An unlock reason is required';
  end if;

  select status into v_status from claims where claim_id = p_claim_id;
  if v_status <> 'approved' then raise exception 'Only an Approved claim can be unlocked'; end if;
  if claim_has_open_unlock(p_claim_id) then raise exception 'Claim already has an open unlock'; end if;

  insert into unlock_log (claim_id, unlocked_by, reason) values (p_claim_id, current_employee_id(), p_reason);
  -- claims.status is deliberately left as 'approved' throughout — the open
  -- unlock_log row is what grants the temporary edit permission (see the
  -- accounts_edit_during_unlock policy on claim_lines).
end;
$$ language plpgsql security definer;

create or replace function relock_claim(p_claim_id uuid)
returns void as $$
begin
  if not is_accounts() then raise exception 'Only accounts can relock a claim'; end if;
  if not claim_has_open_unlock(p_claim_id) then raise exception 'No open unlock on this claim'; end if;

  update unlock_log set relocked_at = now()
    where claim_id = p_claim_id and relocked_at is null;
end;
$$ language plpgsql security definer;
