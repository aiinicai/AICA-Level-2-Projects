-- DPDP Act 2023 / DPDP Rules 2025: consent records, rights requests, firm privacy contact, engagement end dates.
-- Consent rows are never deleted (the Data Fiduciary must be able to prove notice and consent — s.6(10)).
-- Withdrawal only stamps withdrawn_at; a new decision is a new row.

alter table clients add column if not exists engagement_ends_on date;

create table platform_settings (
  id                   int primary key default 1 check (id = 1),
  firm_name            text not null,
  privacy_contact_name text,
  privacy_email        text,
  privacy_phone        text,
  updated_at           timestamptz not null default now()
);
alter table platform_settings enable row level security;
create policy platform_settings_read  on platform_settings for select using (auth.uid() is not null);
create policy platform_settings_write on platform_settings for all using (app_role() = 'super_admin') with check (app_role() = 'super_admin');

create table consents (
  id             uuid primary key default gen_random_uuid(),
  scope          text not null check (scope in ('user', 'client')),
  user_id        uuid references profiles(id),
  client_id      uuid references clients(id),
  notice_version text not null,
  purposes       jsonb not null,                 -- {"core": true, "ai": false}
  lang           text not null check (lang in ('en', 'hi')),
  method         text not null check (method in ('in_app', 'engagement_letter')),
  age_confirmed  boolean,
  reference      text,                           -- engagement letter reference & date
  accepted_by    uuid not null references profiles(id) default auth.uid(),
  accepted_at    timestamptz not null default now(),
  valid_until    date,
  withdrawn_at   timestamptz,
  withdrawn_by   uuid references profiles(id),
  withdraw_reason text,
  check ((scope = 'user' and user_id is not null) or (scope = 'client' and client_id is not null))
);
create index consents_user on consents (user_id, accepted_at desc);
create index consents_client on consents (client_id, accepted_at desc);
alter table consents enable row level security;
-- read: your own; a client admin sees the company's; the CA firm sees all
create policy consents_read on consents for select using (
  user_id = auth.uid() or app_role() = 'super_admin' or (app_role() = 'client_admin' and client_id = app_client()));
-- give: your own consent; company terms by that company's admin; CA firm records from the engagement letter
create policy consents_insert on consents for insert with check (
  accepted_by = auth.uid() and (
    (scope = 'user' and user_id = auth.uid()) or
    (scope = 'client' and method = 'in_app' and app_role() = 'client_admin' and client_id = app_client()) or
    (scope = 'client' and method = 'engagement_letter' and app_role() = 'super_admin')));
-- withdraw only (stamp), never edit what was agreed
create policy consents_withdraw on consents for update using (
  withdrawn_at is null and ((scope = 'user' and user_id = auth.uid()) or (scope = 'client' and (app_role() = 'super_admin' or (app_role() = 'client_admin' and client_id = app_client())))))
  with check (withdrawn_by = auth.uid());
create or replace function guard_consent_update() returns trigger language plpgsql as $$
begin
  if (new.scope, new.user_id, new.client_id, new.notice_version, new.purposes, new.lang, new.method, new.reference, new.accepted_by, new.accepted_at, new.valid_until)
     is distinct from (old.scope, old.user_id, old.client_id, old.notice_version, old.purposes, old.lang, old.method, old.reference, old.accepted_by, old.accepted_at, old.valid_until)
  then raise exception 'Consent records cannot be changed — only withdrawn'; end if;
  return new;
end $$;
create trigger consents_guard before update on consents for each row execute function guard_consent_update();

create table privacy_requests (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references profiles(id) default auth.uid(),
  client_id   uuid references clients(id),
  kind        text not null check (kind in ('access', 'correction', 'erasure', 'grievance', 'nominate')),
  details     text not null,
  created_at  timestamptz not null default now(),
  due_by      date not null default (current_date + 90),   -- DPDP Rules 2025: respond within 90 days
  status      text not null default 'open' check (status in ('open', 'resolved')),
  resolution  text,
  resolved_by uuid references profiles(id),
  resolved_at timestamptz
);
alter table privacy_requests enable row level security;
create policy privacy_requests_read    on privacy_requests for select using (user_id = auth.uid() or app_role() = 'super_admin');
create policy privacy_requests_insert  on privacy_requests for insert with check (user_id = auth.uid());
create policy privacy_requests_resolve on privacy_requests for update using (app_role() = 'super_admin') with check (app_role() = 'super_admin');
