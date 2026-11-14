-- v0.13 — GST registers (mirrors src/lib/gstRegisters.ts): goods / services on the RCM masters (decides the time-of-supply
-- rule), and the 180-day ITC reversal register recorded by the CA firm.

alter table rcm_rules add column if not exists supply text not null default 'services' check (supply in ('goods', 'services'));

create table itc_reversals (
  id               uuid primary key default gen_random_uuid(),
  client_id        uuid not null references clients(id),
  expense_id       uuid not null unique references expenses(id),
  amount           numeric(14,2) not null check (amount > 0),
  reversed_in      date not null,                 -- first day of the return period
  reclaimed_amount numeric(14,2) not null default 0 check (reclaimed_amount >= 0),
  reclaimed_in     date,
  by_user          uuid not null references profiles(id) default auth.uid(),
  at               timestamptz not null default now(),
  check (reclaimed_amount <= amount),
  check (reclaimed_in is null or reclaimed_in >= reversed_in)
);
alter table itc_reversals enable row level security;
create policy itc_reversals_read on itc_reversals for select using (can_see_client(client_id));
create policy itc_reversals_ca on itc_reversals for insert with check (app_role() = 'super_admin');
create policy itc_reversals_ca_update on itc_reversals for update using (app_role() = 'super_admin') with check (app_role() = 'super_admin');
create trigger audit_itc_reversals after insert or update or delete on itc_reversals for each row execute function audit_trigger();
