-- Tenant-scoped Codex runtime for Task Checker.
-- Apply this migration once in the Supabase SQL editor before starting the new worker.

create extension if not exists pgcrypto;

create table if not exists tenants (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    slug text not null unique,
    status text not null default 'active' check (status in ('active', 'suspended')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists tenant_memberships (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    role text not null check (role in ('super_admin', 'admin')),
    status text not null default 'active' check (status in ('active', 'disabled')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (tenant_id, user_id)
);

-- V1 intentionally permits one active tenant membership per login.
create unique index if not exists tenant_memberships_one_active_tenant_per_user
    on tenant_memberships(user_id) where status = 'active';
create unique index if not exists tenant_memberships_one_superadmin
    on tenant_memberships(tenant_id) where role = 'super_admin' and status = 'active';

-- Backfill the existing single-organization installation into one tenant.
do $$
declare
    default_tenant_id uuid;
    owner_id uuid;
begin
    if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'profiles')
       and exists (select 1 from profiles) then
        select id into default_tenant_id from tenants order by created_at limit 1;
        if default_tenant_id is null then
            insert into tenants(name, slug) values ('Default Tenant', 'default-tenant') returning id into default_tenant_id;
        end if;

        select id into owner_id from profiles where role = 'super_admin' order by created_at nulls last, id limit 1;
        if owner_id is null then
            select id into owner_id from profiles order by created_at nulls last, id limit 1;
        end if;

        insert into tenant_memberships(tenant_id, user_id, role)
        select default_tenant_id, p.id,
               case when p.id = owner_id then 'super_admin' else 'admin' end
        from profiles p
        on conflict (tenant_id, user_id) do nothing;
    end if;
end $$;

alter table agents
    add column if not exists tenant_id uuid references tenants(id),
    add column if not exists created_by uuid references auth.users(id),
    add column if not exists workflow_text text,
    add column if not exists workflow_file_paths jsonb not null default '[]'::jsonb,
    add column if not exists codex_model text not null default 'gpt-5.6-sol',
    add column if not exists codex_reasoning_effort text not null default 'xhigh',
    add column if not exists config_version integer not null default 1,
    add column if not exists is_active boolean not null default true,
    add column if not exists archived_at timestamptz;

update agents a
set tenant_id = tm.tenant_id,
    created_by = coalesce(a.created_by, a.user_id),
    workflow_text = coalesce(a.workflow_text, a.system_prompt, '')
from tenant_memberships tm
where a.user_id = tm.user_id and a.tenant_id is null;

create index if not exists agents_tenant_idx on agents(tenant_id);

create table if not exists agent_assignments (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants(id) on delete cascade,
    agent_id uuid not null references agents(id) on delete cascade,
    admin_user_id uuid not null references auth.users(id) on delete cascade,
    assigned_by uuid not null references auth.users(id),
    created_at timestamptz not null default now(),
    unique (agent_id, admin_user_id)
);
create index if not exists agent_assignments_admin_idx on agent_assignments(tenant_id, admin_user_id);

create table if not exists tenant_onedrive_connections (
    tenant_id uuid primary key references tenants(id) on delete cascade,
    account_name text not null default 'Tenant OneDrive',
    account_email text,
    refresh_token text not null,
    base_folder_path text not null default '/',
    connected_by uuid not null references auth.users(id),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Preserve the active legacy connection when that optional migration exists.
do $migration$
begin
    if to_regclass('public.onedrive_connections') is not null then
        execute $sql$
            insert into tenant_onedrive_connections(tenant_id, account_name, account_email, refresh_token, base_folder_path, connected_by)
            select distinct on (tm.tenant_id)
                   tm.tenant_id, od.account_name, od.account_email, od.refresh_token,
                   coalesce(od.base_folder_path, '/'), tm.user_id
            from onedrive_connections od
            join tenant_memberships tm on tm.user_id = od.user_id
            where od.is_active = true
            order by tm.tenant_id, od.updated_at desc nulls last, od.created_at desc
            on conflict (tenant_id) do nothing
        $sql$;
    end if;
end $migration$;

create table if not exists tenant_codex_connections (
    tenant_id uuid primary key references tenants(id) on delete cascade,
    encrypted_auth_blob text not null,
    account_email text,
    account_plan text,
    sdk_version text,
    connected_by uuid not null references auth.users(id),
    connected_at timestamptz not null default now(),
    last_verified_at timestamptz,
    updated_at timestamptz not null default now()
);

create table if not exists tenant_codex_login_sessions (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants(id) on delete cascade,
    requested_by uuid not null references auth.users(id),
    status text not null default 'QUEUED' check (status in ('QUEUED','WAITING_FOR_USER','CONNECTED','FAILED','EXPIRED','CANCELLED')),
    verification_url text,
    user_code text,
    last_error text,
    created_at timestamptz not null default now(),
    expires_at timestamptz not null default (now() + interval '15 minutes'),
    updated_at timestamptz not null default now()
);
create index if not exists tenant_codex_login_pending_idx on tenant_codex_login_sessions(status, created_at);

alter table check_runs
    add column if not exists tenant_id uuid references tenants(id),
    add column if not exists requested_by uuid references auth.users(id),
    add column if not exists run_status text not null default 'QUEUED',
    add column if not exists codex_verdict text,
    add column if not exists review_status text not null default 'NOT_REQUIRED',
    add column if not exists final_verdict text,
    add column if not exists config_snapshot jsonb,
    add column if not exists result_json jsonb,
    add column if not exists codex_model text,
    add column if not exists codex_reasoning_effort text,
    add column if not exists codex_sdk_version text,
    add column if not exists codex_thread_id text,
    add column if not exists codex_turn_id text,
    add column if not exists token_usage jsonb,
    add column if not exists error_code text,
    add column if not exists error_detail text,
    add column if not exists human_review_resolution jsonb,
    add column if not exists queued_at timestamptz not null default now(),
    add column if not exists started_at timestamptz,
    add column if not exists completed_at timestamptz,
    add column if not exists updated_at timestamptz not null default now(),
    add column if not exists cancel_requested boolean not null default false;

-- `status` is retained for the legacy UI while `run_status` tracks the Codex
-- lifecycle. Older installations constrain it to final verdicts only, which
-- rejects newly queued runs.
alter table check_runs drop constraint if exists check_runs_status_check;
alter table check_runs add constraint check_runs_status_check check (
    status in ('QUEUED','RUNNING','PASS','FAIL','INDETERMINATE','ERROR','CANCELLED')
);

update check_runs cr
set tenant_id = a.tenant_id,
    requested_by = coalesce(cr.requested_by, a.created_by, a.user_id),
    run_status = case when cr.status in ('PASS','FAIL','INDETERMINATE','ERROR') then 'COMPLETED' else coalesce(cr.status, 'QUEUED') end,
    final_verdict = case when cr.status in ('PASS','FAIL','INDETERMINATE') then cr.status else null end
from agents a
where cr.agent_id = a.id and cr.tenant_id is null;

create index if not exists check_runs_tenant_created_idx on check_runs(tenant_id, created_at desc);
create index if not exists check_runs_requester_idx on check_runs(tenant_id, requested_by, created_at desc);
-- Normalize any stale legacy duplicates before enforcing tenant serialization.
with ranked_active as (
    select id, row_number() over (partition by tenant_id order by created_at) as position
    from check_runs
    where tenant_id is not null and run_status in ('PREPARING','RUNNING','FINALIZING')
)
update check_runs set run_status = 'QUEUED', status = 'QUEUED'
where id in (select id from ranked_active where position > 1);

create unique index if not exists check_runs_one_active_per_tenant
    on check_runs(tenant_id)
    where run_status in ('PREPARING','RUNNING','FINALIZING');

create table if not exists check_run_tasks (
    id uuid primary key default gen_random_uuid(),
    check_run_id uuid not null references check_runs(id) on delete cascade,
    stage text not null,
    status text not null default 'PENDING',
    attempt_count integer not null default 0,
    payload jsonb,
    result jsonb,
    last_error text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table check_run_tasks
    add column if not exists claimed_by text,
    add column if not exists lease_expires_at timestamptz,
    add column if not exists next_attempt_at timestamptz not null default now();
create index if not exists check_run_tasks_claim_idx on check_run_tasks(status, next_attempt_at, created_at);

create table if not exists check_run_events (
    id bigint generated always as identity primary key,
    check_run_id uuid not null references check_runs(id) on delete cascade,
    tenant_id uuid not null references tenants(id) on delete cascade,
    event_type text not null,
    message text,
    data jsonb,
    created_at timestamptz not null default now()
);
create index if not exists check_run_events_run_idx on check_run_events(check_run_id, id);

create table if not exists human_reviews (
    id uuid primary key default gen_random_uuid(),
    check_run_id uuid references check_runs(id) on delete cascade,
    conflicts jsonb not null default '[]'::jsonb,
    model_responses jsonb not null default '{}'::jsonb,
    consensus_metadata jsonb,
    status text not null default 'pending' check (status in ('pending','in_progress','resolved','cancelled')),
    assigned_to uuid references profiles(id),
    resolved_by uuid references profiles(id),
    resolution jsonb,
    resolution_reasoning text,
    feedback_to_ai text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    resolved_at timestamptz
);

alter table human_reviews
    add column if not exists tenant_id uuid references tenants(id),
    add column if not exists proposed_verdict text,
    add column if not exists final_verdict text;
update human_reviews hr set tenant_id = cr.tenant_id from check_runs cr
where hr.check_run_id = cr.id and hr.tenant_id is null;
create index if not exists human_reviews_tenant_status_idx on human_reviews(tenant_id, status, created_at);

create table if not exists worker_heartbeats (
    worker_id text primary key,
    worker_type text not null,
    last_seen_at timestamptz not null default now(),
    metadata jsonb
);

-- Atomically claim the oldest eligible validation task. A tenant with an active
-- run is skipped, enforcing one Codex run per tenant while preserving global FIFO.
create or replace function claim_next_check_run_task(p_worker_id text, p_lease_seconds integer default 120)
returns table(task_id uuid, check_run_id uuid, tenant_id uuid, payload jsonb)
language plpgsql security definer set search_path = public as $$
declare selected_task check_run_tasks%rowtype;
begin
    select t.* into selected_task
    from check_run_tasks t
    join check_runs r on r.id = t.check_run_id
    where t.stage = 'codex_validate'
      and (t.status = 'PENDING' or (t.status = 'RUNNING' and t.lease_expires_at < now()))
      and t.next_attempt_at <= now()
      and r.cancel_requested = false
      and not exists (
          select 1 from check_runs active
          where active.tenant_id = r.tenant_id
            and active.id <> r.id
            and active.run_status in ('PREPARING','RUNNING','FINALIZING')
      )
    order by t.created_at
    for update of t skip locked
    limit 1;

    if selected_task.id is null then return; end if;

    update check_run_tasks set status = 'RUNNING', claimed_by = p_worker_id,
        lease_expires_at = now() + make_interval(secs => p_lease_seconds),
        attempt_count = attempt_count + 1, updated_at = now()
    where id = selected_task.id;

    update check_runs set run_status = 'PREPARING', status = 'RUNNING', started_at = coalesce(started_at, now())
    where id = selected_task.check_run_id;

    return query select selected_task.id, selected_task.check_run_id, r.tenant_id, selected_task.payload
    from check_runs r where r.id = selected_task.check_run_id;
end $$;

create or replace function claim_next_codex_login(p_worker_id text)
returns table(session_id uuid, tenant_id uuid, requested_by uuid)
language plpgsql security definer set search_path = public as $$
declare selected_session tenant_codex_login_sessions%rowtype;
begin
    select s.* into selected_session from tenant_codex_login_sessions s
    where s.status = 'QUEUED' and s.expires_at > now()
    order by s.created_at for update skip locked limit 1;
    if selected_session.id is null then return; end if;
    update tenant_codex_login_sessions set status = 'WAITING_FOR_USER', updated_at = now()
    where id = selected_session.id;
    return query select selected_session.id, selected_session.tenant_id, selected_session.requested_by;
end $$;

alter table tenants enable row level security;
alter table tenant_memberships enable row level security;
alter table agent_assignments enable row level security;
alter table tenant_onedrive_connections enable row level security;
alter table tenant_codex_connections enable row level security;
alter table tenant_codex_login_sessions enable row level security;
alter table check_run_events enable row level security;
alter table agents enable row level security;
alter table check_runs enable row level security;
alter table human_reviews enable row level security;

create or replace function current_tenant_id()
returns uuid language sql stable security definer set search_path = public as $$
    select tenant_id from tenant_memberships where user_id = auth.uid() and status = 'active' limit 1
$$;

create or replace function current_tenant_role()
returns text language sql stable security definer set search_path = public as $$
    select role from tenant_memberships where user_id = auth.uid() and status = 'active' limit 1
$$;

-- Replace legacy permissive policies on tenant-sensitive tables. Service-role
-- backend operations continue to bypass RLS.
do $policies$
declare policy_row record;
begin
    for policy_row in
        select schemaname, tablename, policyname from pg_policies
        where schemaname = 'public' and tablename in (
            'tenants', 'tenant_memberships', 'agent_assignments',
            'tenant_onedrive_connections', 'tenant_codex_connections',
            'tenant_codex_login_sessions', 'agents', 'check_runs',
            'human_reviews', 'check_run_events'
        )
    loop
        execute format('drop policy if exists %I on %I.%I', policy_row.policyname, policy_row.schemaname, policy_row.tablename);
    end loop;
end $policies$;

drop policy if exists tenant_members_read on tenant_memberships;
create policy tenant_members_read on tenant_memberships for select
    using (tenant_id = current_tenant_id());
drop policy if exists tenants_read on tenants;
create policy tenants_read on tenants for select using (id = current_tenant_id());
drop policy if exists assignments_read on agent_assignments;
create policy assignments_read on agent_assignments for select using (tenant_id = current_tenant_id());
drop policy if exists tenant_onedrive_superadmin on tenant_onedrive_connections;
create policy tenant_onedrive_superadmin on tenant_onedrive_connections for all
    using (tenant_id = current_tenant_id() and current_tenant_role() = 'super_admin')
    with check (tenant_id = current_tenant_id() and current_tenant_role() = 'super_admin');
drop policy if exists tenant_codex_superadmin on tenant_codex_connections;
create policy tenant_codex_superadmin on tenant_codex_connections for all
    using (tenant_id = current_tenant_id() and current_tenant_role() = 'super_admin')
    with check (tenant_id = current_tenant_id() and current_tenant_role() = 'super_admin');
drop policy if exists tenant_codex_login_superadmin on tenant_codex_login_sessions;
create policy tenant_codex_login_superadmin on tenant_codex_login_sessions for all
    using (tenant_id = current_tenant_id() and current_tenant_role() = 'super_admin')
    with check (tenant_id = current_tenant_id() and current_tenant_role() = 'super_admin');
drop policy if exists run_events_read on check_run_events;
create policy run_events_read on check_run_events for select
    using (tenant_id = current_tenant_id());
create policy agents_read on agents for select using (
    tenant_id = current_tenant_id()
    and (
        current_tenant_role() = 'super_admin'
        or exists (
            select 1 from agent_assignments aa
            where aa.agent_id = agents.id and aa.admin_user_id = auth.uid()
        )
    )
);
create policy agents_superadmin_write on agents for all
    using (tenant_id = current_tenant_id() and current_tenant_role() = 'super_admin')
    with check (tenant_id = current_tenant_id() and current_tenant_role() = 'super_admin');
create policy check_runs_read on check_runs for select using (
    tenant_id = current_tenant_id()
    and (current_tenant_role() = 'super_admin' or requested_by = auth.uid())
);
create policy human_reviews_superadmin on human_reviews for all
    using (tenant_id = current_tenant_id() and current_tenant_role() = 'super_admin')
    with check (tenant_id = current_tenant_id() and current_tenant_role() = 'super_admin');

revoke all on function claim_next_check_run_task(text, integer) from public, anon, authenticated;
revoke all on function claim_next_codex_login(text) from public, anon, authenticated;
grant execute on function claim_next_check_run_task(text, integer) to service_role;
grant execute on function claim_next_codex_login(text) to service_role;
