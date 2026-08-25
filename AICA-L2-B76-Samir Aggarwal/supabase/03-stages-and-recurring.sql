-- =====================================================================
--  Aggarwal Samir & Co — Task Delegation App
--  FILE 3 of 3 : Stage master, stage ageing, recurring generation
--  Run AFTER 01-schema.sql and 02-seed-task-master.sql.
--  Safe to re-run.
--
--  This converts the app from a productivity tracker into a work-in-progress
--  pipeline tracker. The six-value task_status enum is replaced by a stages
--  MASTER TABLE so stages can be renamed or added later without a migration.
--  Hours tracking is retired (columns are kept but no longer used by the app).
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. STAGE MASTER
-- ---------------------------------------------------------------------
create table if not exists public.stages (
  id          uuid primary key default gen_random_uuid(),
  code        text not null unique,
  name        text not null unique,
  sort_order  integer not null,
  -- Terminal stages are finished work: excluded from "pending" counts.
  is_terminal boolean not null default false,
  -- Dropped work is terminal AND hidden from the default board.
  is_dropped  boolean not null default false,
  description text,
  is_active   boolean not null default true,
  created_at  timestamptz not null default now()
);

insert into public.stages (code, name, sort_order, is_terminal, is_dropped, description) values
  ('01', 'Assigned but not started', 1, false, false, 'Allocated to a team member, no work begun.'),
  ('02', 'In progress',              2, false, false, 'Actively being worked on.'),
  ('03', 'Need Help',                3, false, false, 'Blocked. The assignee has recorded what they are stuck on.'),
  ('04', 'Completed',                4, true,  false, 'Finished and ready to file or hand over.'),
  ('05', 'Dropped',                  5, true,  true,  'Cancelled or no longer required. Kept for the record.')
on conflict (code) do nothing;


-- ---------------------------------------------------------------------
-- 2. TASK COLUMNS
-- ---------------------------------------------------------------------
alter table public.tasks add column if not exists stage_id     uuid references public.stages(id);
-- Denormalised so "how long has this been stuck" is one column read, not a
-- scan of the history table on every dashboard row.
alter table public.tasks add column if not exists stage_since  timestamptz not null default now();
-- What the assignee is blocked on. Cleared automatically on leaving stage 03.
alter table public.tasks add column if not exists help_note    text;

-- Backfill from the old status column, if this is an upgrade rather than a
-- fresh install. 'On Hold' becomes Need Help; 'Pending Review' is still work
-- in progress; 'Cancelled' becomes Dropped.
do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'tasks' and column_name = 'status'
  ) then
    update public.tasks t
    set stage_id = s.id
    from public.stages s
    where t.stage_id is null
      and s.code = case t.status::text
                     when 'Not Started'    then '01'
                     when 'In Progress'    then '02'
                     when 'On Hold'        then '03'
                     when 'Pending Review' then '02'
                     when 'Completed'      then '04'
                     when 'Cancelled'      then '05'
                     else '01'
                   end;
  end if;
end $$;

-- Anything still unset (fresh install) starts at stage 01.
update public.tasks
set stage_id = (select id from public.stages where code = '01')
where stage_id is null;

alter table public.tasks alter column stage_id set not null;

-- Postgres does not allow a subquery in a column DEFAULT, so a BEFORE INSERT
-- trigger supplies the opening stage instead. It runs before the NOT NULL
-- check, so the app can insert a task without naming a stage at all.
create or replace function public.set_default_stage()
returns trigger
language plpgsql security definer set search_path = public
as $$
begin
  if new.stage_id is null then
    select id into new.stage_id from public.stages where code = '01';
  end if;
  new.stage_since := coalesce(new.stage_since, now());
  return new;
end;
$$;

drop trigger if exists trg_set_default_stage on public.tasks;
create trigger trg_set_default_stage
  before insert on public.tasks
  for each row execute function public.set_default_stage();

create index if not exists idx_tasks_stage on public.tasks(stage_id);
create index if not exists idx_tasks_stage_since on public.tasks(stage_since);


-- ---------------------------------------------------------------------
-- 3. STAGE HISTORY — powers "days in stage" honestly
-- ---------------------------------------------------------------------
create table if not exists public.task_stage_history (
  id            uuid primary key default gen_random_uuid(),
  task_id       uuid not null references public.tasks(id) on delete cascade,
  from_stage_id uuid references public.stages(id),
  to_stage_id   uuid not null references public.stages(id),
  note          text,
  changed_by    uuid references auth.users(id) on delete set null,
  created_at    timestamptz not null default now()
);

create index if not exists idx_stage_history_task on public.task_stage_history(task_id);


-- ---------------------------------------------------------------------
-- 4. RECURRING ASSIGNMENTS
--    A standing instruction: "this master task, for this client, every cycle,
--    normally to this person." Generation turns them into real tasks.
-- ---------------------------------------------------------------------
create table if not exists public.recurring_assignments (
  id             uuid primary key default gen_random_uuid(),
  task_master_id uuid not null references public.task_master(id) on delete cascade,
  client_id      uuid references public.clients(id) on delete cascade,
  assigned_to    uuid references public.profiles(id) on delete set null,
  is_active      boolean not null default true,
  notes          text,
  created_by     uuid references auth.users(id) on delete set null,
  created_at     timestamptz not null default now()
);

-- One standing instruction per client+task. A null client means an internal
-- recurring job, and Postgres treats nulls as distinct in a unique index, so
-- that case is covered by a second partial index.
create unique index if not exists uq_recurring_client_task
  on public.recurring_assignments (task_master_id, client_id)
  where client_id is not null;

create unique index if not exists uq_recurring_internal_task
  on public.recurring_assignments (task_master_id)
  where client_id is null;


-- ---------------------------------------------------------------------
-- 5. TRIGGERS
-- ---------------------------------------------------------------------

-- 5.1 Employees may move their own work forward but may not re-assign it,
--     move it to another client, or change the due date.
create or replace function public.guard_task_update()
returns trigger
language plpgsql security definer set search_path = public
as $$
declare
  v_completed boolean;
begin
  if not public.is_admin() then
    if new.assigned_to is distinct from old.assigned_to
       or new.assigned_by is distinct from old.assigned_by
       or new.client_id  is distinct from old.client_id
       or new.due_date   is distinct from old.due_date then
      raise exception 'Only an administrator can change the assignee, client or due date.';
    end if;
  end if;

  if new.stage_id is distinct from old.stage_id then
    new.stage_since := now();

    select s.is_terminal and not s.is_dropped into v_completed
    from public.stages s where s.id = new.stage_id;

    if coalesce(v_completed, false) then
      new.completed_at := now();
    else
      new.completed_at := null;
    end if;

    -- A blocker note belongs to the stage that raised it.
    if not exists (select 1 from public.stages where id = new.stage_id and code = '03') then
      new.help_note := null;
    end if;
  end if;

  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists trg_guard_task_update on public.tasks;
create trigger trg_guard_task_update
  before update on public.tasks
  for each row execute function public.guard_task_update();


-- 5.2 Audit trail + stage history
create or replace function public.log_task_activity()
returns trigger
language plpgsql security definer set search_path = public
as $$
declare
  v_old text;
  v_new text;
begin
  if new.stage_id is distinct from old.stage_id then
    select name into v_old from public.stages where id = old.stage_id;
    select name into v_new from public.stages where id = new.stage_id;

    insert into public.task_activity (task_id, changed_by, field, old_value, new_value)
    values (new.id, auth.uid(), 'stage', v_old, v_new);

    insert into public.task_stage_history (task_id, from_stage_id, to_stage_id, note, changed_by)
    values (new.id, old.stage_id, new.stage_id, new.help_note, auth.uid());
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


-- 5.3 Opening history row, so days-in-stage works from the moment of creation
create or replace function public.log_task_created()
returns trigger
language plpgsql security definer set search_path = public
as $$
begin
  insert into public.task_stage_history (task_id, from_stage_id, to_stage_id, changed_by)
  values (new.id, null, new.stage_id, auth.uid());
  return new;
end;
$$;

drop trigger if exists trg_log_task_created on public.tasks;
create trigger trg_log_task_created
  after insert on public.tasks
  for each row execute function public.log_task_created();


-- ---------------------------------------------------------------------
-- 6. RECURRING GENERATION
--    Creates one task per active standing instruction for the given period,
--    skipping any that already exist. Safe to run twice.
-- ---------------------------------------------------------------------
create or replace function public.generate_recurring_tasks(
  _period         text,
  _financial_year text,
  _due_date       date default null,
  _recurrence     text default null
)
returns integer
language plpgsql security definer set search_path = public
as $$
declare
  v_created integer := 0;
  v_stage   uuid;
  r         record;
begin
  if not public.is_admin() then
    raise exception 'Only an administrator can generate recurring tasks.';
  end if;

  if _period is null or btrim(_period) = '' then
    raise exception 'A period is required, for example "Apr-2026" or "Q1".';
  end if;

  select id into v_stage from public.stages where code = '01';

  for r in
    select ra.id, ra.task_master_id, ra.client_id, ra.assigned_to,
           tm.name, tm.description, tm.default_priority, tm.estimated_hours
    from public.recurring_assignments ra
    join public.task_master tm on tm.id = ra.task_master_id
    where ra.is_active
      and tm.is_active
      and ra.assigned_to is not null
      and (_recurrence is null or tm.recurrence::text = _recurrence)
  loop
    -- Skip if this exact job already exists for the period.
    if exists (
      select 1 from public.tasks t
      where t.task_master_id = r.task_master_id
        and t.client_id is not distinct from r.client_id
        and t.period = _period
        and t.financial_year = _financial_year
    ) then
      continue;
    end if;

    insert into public.tasks (
      title, task_master_id, client_id, assigned_to, assigned_by,
      stage_id, priority, description, financial_year, period,
      start_date, due_date, is_adhoc
    ) values (
      r.name, r.task_master_id, r.client_id, r.assigned_to, auth.uid(),
      v_stage, r.default_priority, r.description, _financial_year, _period,
      current_date, _due_date, false
    );

    v_created := v_created + 1;
  end loop;

  return v_created;
end;
$$;

grant execute on function public.generate_recurring_tasks(text, text, date, text) to authenticated;


-- ---------------------------------------------------------------------
-- 7. ROW LEVEL SECURITY
-- ---------------------------------------------------------------------
alter table public.stages                enable row level security;
alter table public.task_stage_history    enable row level security;
alter table public.recurring_assignments enable row level security;

drop policy if exists st_select on public.stages;
create policy st_select on public.stages for select to authenticated using (true);

drop policy if exists st_admin_write on public.stages;
create policy st_admin_write on public.stages
  for all to authenticated using (public.is_admin()) with check (public.is_admin());

-- History is visible exactly where the task is visible.
drop policy if exists tsh_select on public.task_stage_history;
create policy tsh_select on public.task_stage_history
  for select to authenticated
  using (exists (select 1 from public.tasks t
                 where t.id = task_id
                   and (t.assigned_to = auth.uid() or public.is_admin())));

drop policy if exists ra_select on public.recurring_assignments;
create policy ra_select on public.recurring_assignments
  for select to authenticated using (true);

drop policy if exists ra_admin_write on public.recurring_assignments;
create policy ra_admin_write on public.recurring_assignments
  for all to authenticated using (public.is_admin()) with check (public.is_admin());


-- ---------------------------------------------------------------------
-- 8. REPORTING VIEW
-- ---------------------------------------------------------------------
drop view if exists public.v_tasks_enriched;

create view public.v_tasks_enriched with (security_invoker = on) as
select
  t.id, t.title, t.priority, t.description,
  t.financial_year, t.period, t.start_date, t.due_date, t.completed_at,
  t.is_adhoc, t.created_at, t.updated_at,
  t.assigned_to, t.assigned_by, t.client_id, t.task_master_id,
  t.stage_id, t.stage_since, t.help_note,

  s.code        as stage_code,
  s.name        as stage_name,
  s.sort_order  as stage_sort,
  s.is_terminal as stage_is_terminal,
  s.is_dropped  as stage_is_dropped,

  p.full_name    as assignee_name,
  p.designation  as assignee_designation,
  b.full_name    as assigner_name,
  c.name         as client_name,
  c.client_code  as client_code,
  tm.name        as master_task_name,
  coalesce(tm.category, 'Ad-hoc') as category,

  -- The two numbers this app now exists to show.
  (current_date - t.stage_since::date) as days_in_stage,
  (t.due_date is not null
     and t.due_date < current_date
     and not s.is_terminal) as is_overdue,
  (t.due_date - current_date) as days_to_due
from public.tasks t
join public.stages s          on s.id  = t.stage_id
join public.profiles p        on p.id  = t.assigned_to
left join public.profiles b   on b.id  = t.assigned_by
left join public.clients c    on c.id  = t.client_id
left join public.task_master tm on tm.id = t.task_master_id;

grant select on public.v_tasks_enriched to authenticated;


-- ---------------------------------------------------------------------
-- 9. RETIRE THE OLD STATUS COLUMN
--    Done last, because the view above had to stop depending on it first.
-- ---------------------------------------------------------------------
alter table public.tasks drop column if exists status;
drop type if exists public.task_status;

-- Hours columns are intentionally left in place but unused by the app. Drop
-- them here if you are sure you will never want billing:
--   alter table public.tasks drop column estimated_hours, drop column actual_hours;

-- =====================================================================
--  END OF FILE 3
--  Verify:
--    select code, name, sort_order from public.stages order by sort_order;
--    select stage_code, stage_name, count(*) from public.v_tasks_enriched
--    group by 1,2 order by 1;
-- =====================================================================
