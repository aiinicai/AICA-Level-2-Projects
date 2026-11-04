-- v0.13 — review controls and Drive sharing.
--  1) SECURITY FIX: guard_review (0001) checks only UPDATEs, so a user could INSERT a bill that is already "approved" and skip
--     the CA review. New bills from users may only be draft or submitted. Auto-approval (lib/autoApprove.ts) is applied by
--     the server (service role) only — it is not live until that step runs server-side (see SUPABASE-SETUP.md).
--  2) Auto-approval settings, sample checks and reviewer assignment (AUDIT-v0.4 B10).
--  3) Client admins can view their own Drive folder when the CA firm turns it on (B8) — drive-share function.

create or replace function guard_new_bill_status() returns trigger language plpgsql as $$
begin
  if coalesce(app_role(), 'service') not in ('super_admin', 'service') and new.status not in ('draft', 'submitted') then
    raise exception 'Only the CA firm can approve entries';
  end if;
  if coalesce(app_role(), 'service') <> 'service' and new.auto_approved then
    raise exception 'Only the auto-approval service can mark a bill auto-approved';
  end if;
  return new;
end $$;

alter table clients
  add column if not exists auto_approve jsonb not null default '{"enabled": false, "maxAmount": 5000, "samplePct": 10, "minHistory": 3}',
  add column if not exists drive_share_with_admins boolean not null default false,
  add column if not exists drive_folder_id text;                       -- Vouchr/<Client> folder, filled by drive-share
alter table expenses
  add column if not exists auto_approved boolean not null default false,
  add column if not exists sample_check boolean not null default false,
  add column if not exists assigned_to uuid references profiles(id),
  add column if not exists reviewed_at timestamptz;
alter table expenses add constraint expenses_auto_limits check (not auto_approved or status in ('approved', 'posted', 'rejected'));

create trigger expenses_new_status_guard before insert on expenses for each row execute function guard_new_bill_status();

-- the new settings are the CA firm's, like the other control fields (extends guard_client_update from 0006)
create or replace function guard_client_update() returns trigger language plpgsql as $$
begin
  if app_role() <> 'super_admin' and (
       new.backdate_window_days is distinct from old.backdate_window_days
    or new.cash_limit_per_day is distinct from old.cash_limit_per_day
    or new.note_above_amount is distinct from old.note_above_amount
    or new.gstin is distinct from old.gstin or new.pan is distinct from old.pan or new.name is distinct from old.name
    or new.tally_mode is distinct from old.tally_mode
    or new.auto_approve is distinct from old.auto_approve
    or new.drive_share_with_admins is distinct from old.drive_share_with_admins
    or new.drive_folder_id is distinct from old.drive_folder_id) then
    raise exception 'Only the CA firm can change control settings';
  end if;
  return new;
end $$;

-- reviewer assignment: CA firm only
create or replace function guard_assignment() returns trigger language plpgsql as $$
begin
  if new.assigned_to is distinct from old.assigned_to and coalesce(app_role(), 'service') not in ('super_admin', 'service') then
    raise exception 'Only the CA firm can approve entries';
  end if;
  return new;
end $$;
create trigger expenses_assignment_guard before update on expenses for each row execute function guard_assignment();

-- Drive permissions given by drive-share, so they can be removed again
create table drive_shares (
  client_id     uuid not null references clients(id),
  user_id       uuid not null references profiles(id),
  permission_id text not null,
  email         text not null,
  granted_at    timestamptz not null default now(),
  primary key (client_id, user_id)
);
alter table drive_shares enable row level security;
create policy drive_shares_read on drive_shares for select using (app_role() = 'super_admin' or user_id = auth.uid());

-- 4) Financial-year close (B11, lib/fyClose.ts): who closed it, which warnings were seen, carry-forward totals. Locks are
--    written to month_locks by the same transaction in the app's RPC step; closing is the CA firm's only.
alter table fiscal_years
  add column if not exists closed_at timestamptz,
  add column if not exists closed_by uuid references profiles(id),
  add column if not exists warnings_acknowledged text[] not null default '{}',
  add column if not exists carry_forward jsonb;
create or replace function guard_fy_close() returns trigger language plpgsql as $$
begin
  if (new.closed_at is distinct from old.closed_at or new.carry_forward is distinct from old.carry_forward) and coalesce(app_role(), 'service') not in ('super_admin', 'service') then
    raise exception 'Only the CA firm can close a financial year';
  end if;
  return new;
end $$;
create trigger fiscal_years_close_guard before update on fiscal_years for each row execute function guard_fy_close();
