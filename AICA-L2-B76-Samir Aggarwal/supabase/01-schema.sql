-- =====================================================================
--  Aggarwal Samir & Co — Task Delegation App
--  FILE 1 of 2 : Schema, roles, RLS, triggers, views
--  Run this FIRST in the Supabase SQL Editor (Database > SQL Editor > New query).
--  Safe to re-run: everything is guarded with IF NOT EXISTS / OR REPLACE.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. ENUMS
-- ---------------------------------------------------------------------
do $$ begin
  create type public.app_role as enum ('admin', 'employee');
exception when duplicate_object then null; end $$;

do $$ begin
  create type public.designation as enum (
    'Partner', 'Manager', 'Senior Accountant', 'Accountant',
    'Paid Assistant', 'Article Assistant', 'Intern', 'Admin Staff'
  );
exception when duplicate_object then null; end $$;

do $$ begin
  create type public.task_status as enum (
    'Not Started', 'In Progress', 'On Hold', 'Pending Review', 'Completed', 'Cancelled'
  );
exception when duplicate_object then null; end $$;

do $$ begin
  create type public.task_priority as enum ('Low', 'Medium', 'High', 'Urgent');
exception when duplicate_object then null; end $$;

do $$ begin
  create type public.recurrence as enum ('One-time', 'Monthly', 'Quarterly', 'Half-Yearly', 'Annual');
exception when duplicate_object then null; end $$;

do $$ begin
  create type public.client_type as enum (
    'Individual', 'Proprietorship', 'Partnership Firm', 'LLP',
    'Private Limited', 'Public Limited', 'HUF', 'Trust', 'Society', 'AOP/BOI'
  );
exception when duplicate_object then null; end $$;


-- ---------------------------------------------------------------------
-- 2. TABLES
-- ---------------------------------------------------------------------

-- 2.1 Signup allow-list. Admin adds an employee's email here BEFORE they can sign up.
create table if not exists public.allowed_emails (
  id           uuid primary key default gen_random_uuid(),
  email        text not null unique,
  full_name    text,
  designation  public.designation not null default 'Accountant',
  invited_by   uuid references auth.users(id) on delete set null,
  is_used      boolean not null default false,
  created_at   timestamptz not null default now()
);

-- 2.2 Employee master (1:1 with auth.users)
create table if not exists public.profiles (
  id              uuid primary key references auth.users(id) on delete cascade,
  email           text not null,
  full_name       text not null default '',
  designation     public.designation not null default 'Accountant',
  phone           text,
  date_of_joining date,
  is_active       boolean not null default true,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

-- 2.3 Roles kept in a SEPARATE table (never on profiles) so a user cannot
--     escalate their own privileges by editing their profile row.
create table if not exists public.user_roles (
  id      uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  role    public.app_role not null,
  unique (user_id, role)
);

-- 2.4 Client master
create table if not exists public.clients (
  id                   uuid primary key default gen_random_uuid(),
  client_code          text unique,
  name                 text not null,
  client_type          public.client_type not null default 'Individual',
  pan                  text,
  gstin                text,
  contact_person       text,
  email                text,
  phone                text,
  address              text,
  city                 text,
  state                text,
  relationship_manager uuid references public.profiles(id) on delete set null,
  is_active            boolean not null default true,
  notes                text,
  created_by           uuid references auth.users(id) on delete set null,
  created_at           timestamptz not null default now()
);

-- 2.5 Predefined task master (the firm's standard job catalogue)
create table if not exists public.task_master (
  id               uuid primary key default gen_random_uuid(),
  name             text not null,
  category         text not null,
  description      text,
  default_priority public.task_priority not null default 'Medium',
  recurrence       public.recurrence not null default 'One-time',
  statutory_due    text,
  estimated_hours  numeric(5,2),
  is_active        boolean not null default true,
  created_at       timestamptz not null default now(),
  unique (name, category)
);

-- 2.6 Allocated tasks. task_master_id NULL + is_adhoc TRUE = ad-hoc task.
create table if not exists public.tasks (
  id              uuid primary key default gen_random_uuid(),
  title           text not null,
  task_master_id  uuid references public.task_master(id) on delete set null,
  client_id       uuid references public.clients(id) on delete set null,
  assigned_to     uuid not null references public.profiles(id) on delete cascade,
  assigned_by     uuid not null references public.profiles(id) on delete cascade,
  status          public.task_status not null default 'Not Started',
  priority        public.task_priority not null default 'Medium',
  description     text,
  financial_year  text,
  period          text,
  start_date      date,
  due_date        date,
  completed_at    timestamptz,
  estimated_hours numeric(5,2),
  actual_hours    numeric(5,2),
  is_adhoc        boolean not null default false,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

-- 2.7 Comments / progress notes on a task
create table if not exists public.task_comments (
  id         uuid primary key default gen_random_uuid(),
  task_id    uuid not null references public.tasks(id) on delete cascade,
  user_id    uuid not null references public.profiles(id) on delete cascade,
  comment    text not null,
  created_at timestamptz not null default now()
);

-- 2.8 Immutable audit trail of status changes
create table if not exists public.task_activity (
  id          uuid primary key default gen_random_uuid(),
  task_id     uuid not null references public.tasks(id) on delete cascade,
  changed_by  uuid references auth.users(id) on delete set null,
  field       text not null,
  old_value   text,
  new_value   text,
  created_at  timestamptz not null default now()
);

create index if not exists idx_tasks_assigned_to on public.tasks(assigned_to);
create index if not exists idx_tasks_status      on public.tasks(status);
create index if not exists idx_tasks_due_date    on public.tasks(due_date);
create index if not exists idx_tasks_client      on public.tasks(client_id);
create index if not exists idx_comments_task     on public.task_comments(task_id);
create index if not exists idx_activity_task     on public.task_activity(task_id);


-- ---------------------------------------------------------------------
-- 3. SECURITY-DEFINER HELPERS
--    These must be SECURITY DEFINER, otherwise the RLS policies below
--    recurse infinitely when they query user_roles.
-- ---------------------------------------------------------------------
create or replace function public.has_role(_user_id uuid, _role public.app_role)
returns boolean
language sql stable security definer set search_path = public
as $$
  select exists (
    select 1 from public.user_roles where user_id = _user_id and role = _role
  );
$$;

create or replace function public.is_admin()
returns boolean
language sql stable security definer set search_path = public
as $$
  select public.has_role(auth.uid(), 'admin');
$$;

-- Called by the SIGN-UP page BEFORE calling supabase.auth.signUp(), so the UI can
-- show a friendly "not authorised" message instead of a raw database error.
create or replace function public.is_email_allowed(_email text)
returns boolean
language sql stable security definer set search_path = public
as $$
  select (not exists (select 1 from public.profiles))                -- first ever user
      or exists (select 1 from public.allowed_emails
                 where lower(email) = lower(trim(_email)));
$$;

grant execute on function public.is_email_allowed(text) to anon, authenticated;


-- ---------------------------------------------------------------------
-- 4. SIGN-UP TRIGGERS
-- ---------------------------------------------------------------------

-- 4.1 Hard gate: reject any signup whose email the admin has not pre-approved.
--     The very first user ever to sign up is always allowed (they become admin).
create or replace function public.enforce_signup_allowlist()
returns trigger
language plpgsql security definer set search_path = public
as $$
begin
  if not exists (select 1 from public.profiles) then
    return new;                                  -- first user: always allowed
  end if;
  if not exists (
    select 1 from public.allowed_emails where lower(email) = lower(new.email)
  ) then
    raise exception 'EMAIL_NOT_AUTHORISED: this email has not been added by the administrator.';
  end if;
  return new;
end;
$$;

drop trigger if exists trg_enforce_signup_allowlist on auth.users;
create trigger trg_enforce_signup_allowlist
  before insert on auth.users
  for each row execute function public.enforce_signup_allowlist();

-- 4.2 Create the profile row and grant the role.
--     First user  -> role 'admin',    designation defaults to 'Partner'
--     Later users -> role 'employee', designation taken from allowed_emails
create or replace function public.handle_new_user()
returns trigger
language plpgsql security definer set search_path = public
as $$
declare
  v_is_first boolean;
  v_allowed  public.allowed_emails%rowtype;
begin
  select not exists (select 1 from public.profiles) into v_is_first;

  select * into v_allowed
  from public.allowed_emails
  where lower(email) = lower(new.email)
  limit 1;

  insert into public.profiles (id, email, full_name, designation)
  values (
    new.id,
    lower(new.email),
    coalesce(nullif(new.raw_user_meta_data ->> 'full_name', ''),
             v_allowed.full_name,
             split_part(new.email, '@', 1)),
    coalesce(v_allowed.designation,
             case when v_is_first then 'Partner'::public.designation
                  else 'Accountant'::public.designation end)
  );

  insert into public.user_roles (user_id, role)
  values (new.id,
          case when v_is_first then 'admin'::public.app_role
               else 'employee'::public.app_role end);

  if v_allowed.id is not null then
    update public.allowed_emails set is_used = true where id = v_allowed.id;
  end if;

  return new;
end;
$$;

drop trigger if exists trg_handle_new_user on auth.users;
create trigger trg_handle_new_user
  after insert on auth.users
  for each row execute function public.handle_new_user();


-- ---------------------------------------------------------------------
-- 5. TASK TRIGGERS
-- ---------------------------------------------------------------------

-- 5.1 An employee may update their OWN task's progress, but may not
--     re-assign it, move it to another client, or change the due date.
create or replace function public.guard_task_update()
returns trigger
language plpgsql security definer set search_path = public
as $$
begin
  if not public.is_admin() then
    if new.assigned_to is distinct from old.assigned_to
       or new.assigned_by is distinct from old.assigned_by
       or new.client_id  is distinct from old.client_id
       or new.due_date   is distinct from old.due_date then
      raise exception 'Only an administrator can change the assignee, client or due date.';
    end if;
  end if;

  if new.status = 'Completed' and old.status <> 'Completed' then
    new.completed_at := now();
  elsif new.status <> 'Completed' then
    new.completed_at := null;
  end if;

  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists trg_guard_task_update on public.tasks;
create trigger trg_guard_task_update
  before update on public.tasks
  for each row execute function public.guard_task_update();

-- 5.2 Audit trail
create or replace function public.log_task_activity()
returns trigger
language plpgsql security definer set search_path = public
as $$
begin
  if new.status is distinct from old.status then
    insert into public.task_activity (task_id, changed_by, field, old_value, new_value)
    values (new.id, auth.uid(), 'status', old.status::text, new.status::text);
  end if;
  if new.assigned_to is distinct from old.assigned_to then
    insert into public.task_activity (task_id, changed_by, field, old_value, new_value)
    values (new.id, auth.uid(), 'assigned_to', old.assigned_to::text, new.assigned_to::text);
  end if;
  return new;
end;
$$;

drop trigger if exists trg_log_task_activity on public.tasks;
create trigger trg_log_task_activity
  after update on public.tasks
  for each row execute function public.log_task_activity();

-- 5.3 profiles.updated_at
create or replace function public.touch_updated_at()
returns trigger language plpgsql set search_path = public
as $$ begin new.updated_at := now(); return new; end; $$;

drop trigger if exists trg_touch_profiles on public.profiles;
create trigger trg_touch_profiles
  before update on public.profiles
  for each row execute function public.touch_updated_at();


-- ---------------------------------------------------------------------
-- 6. ROW LEVEL SECURITY
-- ---------------------------------------------------------------------
alter table public.allowed_emails enable row level security;
alter table public.profiles       enable row level security;
alter table public.user_roles     enable row level security;
alter table public.clients        enable row level security;
alter table public.task_master    enable row level security;
alter table public.tasks          enable row level security;
alter table public.task_comments  enable row level security;
alter table public.task_activity  enable row level security;

-- 6.1 allowed_emails — admin only
drop policy if exists ae_admin_all on public.allowed_emails;
create policy ae_admin_all on public.allowed_emails
  for all to authenticated using (public.is_admin()) with check (public.is_admin());

-- 6.2 profiles
--     Any signed-in user may READ the staff directory (needed to render
--     "Assigned by <name>"). Only the owner or an admin may WRITE.
--     >> Tighten to (id = auth.uid() OR public.is_admin()) if you want
--        employees unable to see colleagues' names at all.
drop policy if exists pr_select on public.profiles;
create policy pr_select on public.profiles
  for select to authenticated using (true);

drop policy if exists pr_update_own on public.profiles;
create policy pr_update_own on public.profiles
  for update to authenticated
  using (id = auth.uid() or public.is_admin())
  with check (id = auth.uid() or public.is_admin());

drop policy if exists pr_admin_write on public.profiles;
create policy pr_admin_write on public.profiles
  for insert to authenticated with check (public.is_admin());

drop policy if exists pr_admin_delete on public.profiles;
create policy pr_admin_delete on public.profiles
  for delete to authenticated using (public.is_admin());

-- 6.3 user_roles — read own or admin; only admin may grant/revoke
drop policy if exists ur_select on public.user_roles;
create policy ur_select on public.user_roles
  for select to authenticated using (user_id = auth.uid() or public.is_admin());

drop policy if exists ur_admin_write on public.user_roles;
create policy ur_admin_write on public.user_roles
  for all to authenticated using (public.is_admin()) with check (public.is_admin());

-- 6.4 clients — everyone reads, admin writes
drop policy if exists cl_select on public.clients;
create policy cl_select on public.clients for select to authenticated using (true);

drop policy if exists cl_admin_write on public.clients;
create policy cl_admin_write on public.clients
  for all to authenticated using (public.is_admin()) with check (public.is_admin());

-- 6.5 task_master — everyone reads, admin writes
drop policy if exists tm_select on public.task_master;
create policy tm_select on public.task_master for select to authenticated using (true);

drop policy if exists tm_admin_write on public.task_master;
create policy tm_admin_write on public.task_master
  for all to authenticated using (public.is_admin()) with check (public.is_admin());

-- 6.6 tasks — THE CORE RULE
--     An employee sees and edits ONLY tasks assigned to them.
--     An admin sees and edits everything.
drop policy if exists tk_select on public.tasks;
create policy tk_select on public.tasks
  for select to authenticated
  using (assigned_to = auth.uid() or public.is_admin());

drop policy if exists tk_update on public.tasks;
create policy tk_update on public.tasks
  for update to authenticated
  using (assigned_to = auth.uid() or public.is_admin())
  with check (assigned_to = auth.uid() or public.is_admin());

drop policy if exists tk_admin_insert on public.tasks;
create policy tk_admin_insert on public.tasks
  for insert to authenticated with check (public.is_admin());

drop policy if exists tk_admin_delete on public.tasks;
create policy tk_admin_delete on public.tasks
  for delete to authenticated using (public.is_admin());

-- 6.7 task_comments — visible only on tasks you can already see
drop policy if exists tc_select on public.task_comments;
create policy tc_select on public.task_comments
  for select to authenticated
  using (exists (select 1 from public.tasks t
                 where t.id = task_id
                   and (t.assigned_to = auth.uid() or public.is_admin())));

drop policy if exists tc_insert on public.task_comments;
create policy tc_insert on public.task_comments
  for insert to authenticated
  with check (user_id = auth.uid()
              and exists (select 1 from public.tasks t
                          where t.id = task_id
                            and (t.assigned_to = auth.uid() or public.is_admin())));

-- 6.8 task_activity — read-only to the app; written by trigger
drop policy if exists ta_select on public.task_activity;
create policy ta_select on public.task_activity
  for select to authenticated
  using (exists (select 1 from public.tasks t
                 where t.id = task_id
                   and (t.assigned_to = auth.uid() or public.is_admin())));


-- ---------------------------------------------------------------------
-- 7. REPORTING VIEW
--    security_invoker = on makes the view obey the caller's RLS, so the
--    SAME query powers the employee's "My Tasks" and the admin dashboard.
--    The frontend can just: select * from v_tasks_enriched
-- ---------------------------------------------------------------------
drop view if exists public.v_tasks_enriched;
create view public.v_tasks_enriched with (security_invoker = on) as
select
  t.id, t.title, t.status, t.priority, t.description,
  t.financial_year, t.period, t.start_date, t.due_date, t.completed_at,
  t.estimated_hours, t.actual_hours, t.is_adhoc, t.created_at, t.updated_at,
  t.assigned_to, t.assigned_by, t.client_id, t.task_master_id,
  p.full_name    as assignee_name,
  p.designation  as assignee_designation,
  b.full_name    as assigner_name,
  c.name         as client_name,
  c.client_code  as client_code,
  tm.name        as master_task_name,
  coalesce(tm.category, 'Ad-hoc') as category,
  (t.due_date is not null
     and t.due_date < current_date
     and t.status not in ('Completed', 'Cancelled')) as is_overdue,
  (t.due_date - current_date) as days_to_due
from public.tasks t
join public.profiles p       on p.id  = t.assigned_to
left join public.profiles b  on b.id  = t.assigned_by
left join public.clients c   on c.id  = t.client_id
left join public.task_master tm on tm.id = t.task_master_id;

grant select on public.v_tasks_enriched to authenticated;

-- =====================================================================
--  END OF FILE 1. Now run 02-seed-task-master.sql
-- =====================================================================
