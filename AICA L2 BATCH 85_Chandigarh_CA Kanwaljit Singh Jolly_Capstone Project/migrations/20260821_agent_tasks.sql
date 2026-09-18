-- Move run-specific OneDrive selections from agents into reusable tasks.
begin;

create table if not exists public.tasks (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references public.tenants(id) on delete cascade,
    agent_id uuid not null references public.agents(id) on delete cascade,
    created_by uuid not null references auth.users(id),
    name text not null,
    client_folder_path text,
    client_file_paths jsonb not null default '[]'::jsonb,
    onedrive_folder_path text not null,
    task_file_paths jsonb not null default '[]'::jsonb,
    workflow_file_paths jsonb not null default '[]'::jsonb,
    config_version integer not null default 1,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    archived_at timestamptz
);

create index if not exists tasks_tenant_agent_idx
    on public.tasks(tenant_id, agent_id, created_at desc)
    where is_active = true;
create index if not exists tasks_agent_id_idx on public.tasks(agent_id);
create index if not exists tasks_created_by_idx on public.tasks(created_by);

alter table public.check_runs
    add column if not exists task_id uuid references public.tasks(id) on delete set null;
create index if not exists check_runs_task_created_idx
    on public.check_runs(task_id, created_at desc);

-- Preserve every existing configured agent as one editable task.
insert into public.tasks (
    tenant_id, agent_id, created_by, name,
    client_folder_path, client_file_paths,
    onedrive_folder_path, task_file_paths, workflow_file_paths
)
select
    a.tenant_id,
    a.id,
    coalesce(a.created_by, a.user_id),
    coalesce(
        nullif(regexp_replace(rtrim(coalesce(a.onedrive_folder_path, ''), '/'), '^.*/', ''), ''),
        a.name || ' task'
    ),
    nullif(a.client_folder_path, ''),
    to_jsonb(coalesce(a.client_file_paths, '{}'::text[])),
    coalesce(a.onedrive_folder_path, ''),
    to_jsonb(coalesce(a.task_file_paths, '{}'::text[])),
    coalesce(a.workflow_file_paths, '[]'::jsonb)
from public.agents a
where a.tenant_id is not null
  and a.is_active = true
  and not exists (select 1 from public.tasks t where t.agent_id = a.id)
  and (
      nullif(a.onedrive_folder_path, '') is not null
      or nullif(a.client_folder_path, '') is not null
      or cardinality(coalesce(a.task_file_paths, '{}'::text[])) > 0
      or cardinality(coalesce(a.client_file_paths, '{}'::text[])) > 0
      or jsonb_array_length(coalesce(a.workflow_file_paths, '[]'::jsonb)) > 0
  );

update public.check_runs cr
set task_id = (
    select t.id
    from public.tasks t
    where t.agent_id = cr.agent_id
    order by t.created_at
    limit 1
)
where cr.task_id is null;

alter table public.tasks enable row level security;

drop policy if exists tasks_select on public.tasks;
create policy tasks_select on public.tasks for select to authenticated using (
    tenant_id = current_tenant_id()
    and (
        current_tenant_role() = 'super_admin'
        or exists (
            select 1 from public.agent_assignments aa
            where aa.tenant_id = tasks.tenant_id
              and aa.agent_id = tasks.agent_id
              and aa.admin_user_id = auth.uid()
        )
    )
);

drop policy if exists tasks_superadmin_write on public.tasks;
drop policy if exists tasks_superadmin_insert on public.tasks;
drop policy if exists tasks_superadmin_update on public.tasks;
drop policy if exists tasks_superadmin_delete on public.tasks;
create policy tasks_superadmin_insert on public.tasks for insert to authenticated with check (
    tenant_id = current_tenant_id()
    and current_tenant_role() = 'super_admin'
    and exists (
        select 1 from public.agents a
        where a.id = tasks.agent_id and a.tenant_id = tasks.tenant_id and a.is_active = true
    )
);
create policy tasks_superadmin_update on public.tasks for update to authenticated using (
    tenant_id = current_tenant_id() and current_tenant_role() = 'super_admin'
) with check (
    tenant_id = current_tenant_id()
    and current_tenant_role() = 'super_admin'
    and exists (
        select 1 from public.agents a
        where a.id = tasks.agent_id and a.tenant_id = tasks.tenant_id and a.is_active = true
    )
);
create policy tasks_superadmin_delete on public.tasks for delete to authenticated using (
    tenant_id = current_tenant_id() and current_tenant_role() = 'super_admin'
);

revoke all on public.tasks from anon;
revoke all on public.tasks from authenticated;
grant select, insert, update, delete on public.tasks to authenticated;

commit;
