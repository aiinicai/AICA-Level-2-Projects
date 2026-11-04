-- Platform operations: shared paid APIs, usage metering, compliance watch, system health.
-- All tables here are super-admin only.

-- Shared credentials: ONE account per paid provider, used for all clients (cost pooling).
-- Secrets themselves live in Supabase Vault / Edge Function secrets, never in this table.
create table api_providers (
  code         text primary key,            -- 'gsp', 'gstin_search', 'pan_verify', 'ocr', 'email'
  provider     text not null,               -- vendor name, chosen on quotes
  secret_name  text not null,               -- name of the Edge Function secret holding the key
  free_quota_monthly int,                   -- calls/month covered by the free tier, if any
  unit_cost_inr numeric(10,4),              -- per call beyond free quota (from quote)
  enabled      boolean not null default false,
  notes        text
);

-- Every external call is metered so cost can be attributed per client.
create table api_usage (
  id          bigserial primary key,
  provider    text not null references api_providers(code),
  client_id   uuid references clients(id),
  endpoint    text,
  ok          boolean not null,
  latency_ms  int,
  cached      boolean not null default false,  -- served from cache, no paid call
  error       text,
  at          timestamptz not null default now()
);
create index api_usage_at on api_usage (at);

-- GSTIN/PAN lookups are cached platform-wide: one paid lookup serves every client
-- that has the same vendor.
create table lookup_cache (
  kind        text not null check (kind in ('gstin','pan')),
  key         text not null,
  payload     jsonb not null,
  fetched_at  timestamptz not null default now(),
  primary key (kind, key)
);

-- GSP consent per client GSTIN (OTP-based; can lapse or be revoked by the taxpayer).
create table gsp_sessions (
  client_id   uuid primary key references clients(id),
  gstin       text not null,
  status      text not null default 'not_connected'
              check (status in ('not_connected','active','expired','revoked','error')),
  token_expires_at timestamptz,
  last_fetch_at timestamptz,
  last_error  text
);

-- ---------- Compliance watch (runs quarterly, never auto-changes masters) ----------
create table compliance_sources (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  url         text not null,
  area        text not null check (area in ('tds','gst','rcm','itc','due_dates','forms','other')),
  last_hash   text,
  last_checked_at timestamptz,
  last_changed_at timestamptz,
  active      boolean not null default true
);

create table compliance_runs (
  id          uuid primary key default gen_random_uuid(),
  started_at  timestamptz not null default now(),
  finished_at timestamptz,
  trigger     text not null default 'schedule' check (trigger in ('schedule','manual')),
  sources_checked int default 0,
  changes_found int default 0,
  status      text not null default 'running' check (status in ('running','ok','partial','failed')),
  error       text
);

create table compliance_findings (
  id          uuid primary key default gen_random_uuid(),
  run_id      uuid references compliance_runs(id),
  source_id   uuid references compliance_sources(id),
  area        text not null,
  kind        text not null check (kind in ('source_changed','review_due','unverified_master','source_unreachable')),
  title       text not null,
  detail      text,
  status      text not null default 'open' check (status in ('open','accepted','dismissed')),
  resolved_by uuid references profiles(id),
  resolved_at timestamptz,
  resolution_note text,
  created_at  timestamptz not null default now()
);

-- ---------- System health / errors (audit panel) ----------
create table system_events (
  id          bigserial primary key,
  level       text not null check (level in ('info','warn','error')),
  component   text not null,   -- 'ocr','drive_upload','sheets_sync','gsp_fetch','tally_export','email','push','compliance_watch','client_app'
  client_id   uuid references clients(id),
  message     text not null,
  context     jsonb,
  at          timestamptz not null default now()
);
create index system_events_at on system_events (at desc);

create table job_runs (
  id          bigserial primary key,
  job         text not null,   -- 'sheets_mirror','gst_reco_monthly','gst_reco_yearly','alerts_daily','tally_monthly','compliance_quarterly'
  started_at  timestamptz not null default now(),
  finished_at timestamptz,
  ok          boolean,
  rows_processed int,
  error       text
);

do $$
declare t text;
begin
  foreach t in array array['api_providers','api_usage','lookup_cache','gsp_sessions','compliance_sources',
                           'compliance_runs','compliance_findings','system_events','job_runs'] loop
    execute format('alter table %I enable row level security', t);
    execute format('create policy %1$s_super on %1$s for all using (app_role() = ''super_admin'') with check (app_role() = ''super_admin'')', t);
  end loop;
end $$;

-- client apps may write their own error events (but not read them)
create policy system_events_client_insert on system_events for insert
  with check (auth.uid() is not null and component = 'client_app');

-- ---------- Schedules (pg_cron + pg_net call Edge Functions) ----------
-- Enable pg_cron and pg_net in the Supabase dashboard first, then run with your project ref & service key:
-- select cron.schedule('compliance-quarterly', '0 6 1 1,4,7,10 *',
--   $$ select net.http_post(url := 'https://<ref>.functions.supabase.co/compliance-watch',
--        headers := jsonb_build_object('Authorization','Bearer <service_role_key>')) $$);
-- select cron.schedule('alerts-daily', '30 3 * * *', $$ ...alerts function... $$);
-- select cron.schedule('gst-reco-monthly', '0 5 15 * *', $$ ...gst-reco function... $$);
