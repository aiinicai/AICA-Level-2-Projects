-- =====================================================================
--  Aggarwal Samir & Co — Task Delegation App
--  FILE 9 : Periodicity moves from the task to the schedule
--
--  "Monthly Bookkeeping" and "Weekly Bookkeeping" as separate catalogue
--  entries was the wrong shape: the JOB is bookkeeping; how often it recurs
--  is a property of the arrangement with a particular client. So:
--
--    - recurring_assignments gains its own recurrence; the master's value
--      becomes only a default
--    - the two bookkeeping entries are merged into one "Bookkeeping /
--      Data Entry" (history and schedules re-pointed, nothing lost)
--    - the morning job now generates EVERY periodicity, not just Daily:
--      each cycle's instance appears by itself — daily each morning, weekly
--      on Monday, monthly on the 1st, quarterly / half-yearly / annual on
--      the Indian FY boundaries. All idempotent per period label.
--
--  Run AFTER 08a and 08b. Safe to re-run.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Schedule-level recurrence, backfilled from the master
-- ---------------------------------------------------------------------
alter table public.recurring_assignments
  add column if not exists recurrence public.recurrence;

update public.recurring_assignments ra
set recurrence = tm.recurrence
from public.task_master tm
where tm.id = ra.task_master_id
  and ra.recurrence is null;

-- ---------------------------------------------------------------------
-- 2. Merge the bookkeeping masters into one
-- ---------------------------------------------------------------------
do $$
declare
  v_monthly uuid;
  v_weekly  uuid;
  v_merged  uuid;
begin
  select id into v_monthly from public.task_master
   where name = 'Monthly Bookkeeping / Data Entry' and category = 'Accounting';
  select id into v_weekly from public.task_master
   where name = 'Weekly Bookkeeping / Data Entry' and category = 'Accounting';

  if v_monthly is not null then
    update public.task_master set name = 'Bookkeeping / Data Entry' where id = v_monthly;
    v_merged := v_monthly;
  else
    select id into v_merged from public.task_master
     where name = 'Bookkeeping / Data Entry' and category = 'Accounting';
    if v_merged is null then
      insert into public.task_master (name, category, recurrence, default_priority)
      values ('Bookkeeping / Data Entry', 'Accounting', 'Monthly', 'Medium')
      returning id into v_merged;
    end if;
  end if;

  if v_weekly is not null then
    -- Re-point history, keep each schedule's weekly cadence, then retire the
    -- duplicate. A client already holding a schedule on the merged master
    -- keeps that one; the weekly copy is dropped.
    update public.tasks set task_master_id = v_merged where task_master_id = v_weekly;

    update public.recurring_assignments ra
    set task_master_id = v_merged,
        recurrence     = coalesce(ra.recurrence, 'Weekly')
    where ra.task_master_id = v_weekly
      and not exists (
        select 1 from public.recurring_assignments x
        where x.task_master_id = v_merged
          and x.client_id is not distinct from ra.client_id);

    delete from public.recurring_assignments where task_master_id = v_weekly;
    delete from public.task_master where id = v_weekly;
  end if;
end $$;

-- ---------------------------------------------------------------------
-- 3. Generator honours the schedule's own recurrence
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
  if auth.uid() is not null and not public.is_admin() then
    raise exception 'Only an administrator can generate recurring tasks.';
  end if;

  if _period is null or btrim(_period) = '' then
    raise exception 'A period is required, for example "Apr-2026" or "14-Aug-2026".';
  end if;

  select id into v_stage from public.stages where code = '01';

  for r in
    select ra.id, ra.task_master_id, ra.client_id, ra.assigned_to, ra.created_by,
           tm.name, tm.description, tm.default_priority
    from public.recurring_assignments ra
    join public.task_master tm on tm.id = ra.task_master_id
    where ra.is_active
      and tm.is_active
      and ra.assigned_to is not null
      and (_recurrence is null
           or coalesce(ra.recurrence, tm.recurrence)::text = _recurrence)
  loop
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
      r.name, r.task_master_id, r.client_id, r.assigned_to,
      coalesce(auth.uid(), r.created_by, r.assigned_to),
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
-- 4. One morning run covers every periodicity
--    Runs daily; each cycle's period LABEL only changes at its boundary, and
--    the duplicate check makes generation idempotent — so a weekly schedule
--    yields one task per week, a monthly one per month, and so on. A schedule
--    added mid-cycle gets its current instance the next morning.
-- ---------------------------------------------------------------------
create or replace function public.generate_scheduled_tasks()
returns integer
language plpgsql security definer set search_path = public
as $$
declare
  v_today      date := (timezone('Asia/Kolkata', now()))::date;
  v_fy_start   integer;
  v_fy         text;
  v_week_start date;
  v_quarter    integer;
  v_total      integer := 0;
begin
  v_fy_start := case when extract(month from v_today) >= 4
                     then extract(year from v_today)::integer
                     else extract(year from v_today)::integer - 1 end;
  v_fy := v_fy_start || '-' || to_char(((v_fy_start + 1) % 100), 'FM00');

  -- Daily: due the same day
  v_total := v_total + public.generate_recurring_tasks(
    to_char(v_today, 'DD-Mon-YYYY'), v_fy, v_today, 'Daily');

  -- Weekly: Monday-start, due Sunday
  v_week_start := date_trunc('week', v_today)::date;
  v_total := v_total + public.generate_recurring_tasks(
    'Wk-' || to_char(v_week_start, 'DD-Mon-YYYY'), v_fy, v_week_start + 6, 'Weekly');

  -- Monthly: due month-end
  v_total := v_total + public.generate_recurring_tasks(
    to_char(v_today, 'Mon-YYYY'), v_fy,
    (date_trunc('month', v_today) + interval '1 month - 1 day')::date, 'Monthly');

  -- Quarterly, on Indian FY quarters (Q1 = Apr–Jun), due quarter-end
  v_quarter := case
    when extract(month from v_today) between 4 and 6 then 1
    when extract(month from v_today) between 7 and 9 then 2
    when extract(month from v_today) between 10 and 12 then 3
    else 4 end;
  v_total := v_total + public.generate_recurring_tasks(
    'Q' || v_quarter || '-' || v_fy, v_fy,
    case v_quarter
      when 1 then make_date(v_fy_start, 6, 30)
      when 2 then make_date(v_fy_start, 9, 30)
      when 3 then make_date(v_fy_start, 12, 31)
      else make_date(v_fy_start + 1, 3, 31) end,
    'Quarterly');

  -- Half-yearly: H1 Apr–Sep, H2 Oct–Mar
  v_total := v_total + public.generate_recurring_tasks(
    'H' || (case when extract(month from v_today) between 4 and 9 then 1 else 2 end)
        || '-' || v_fy,
    v_fy,
    case when extract(month from v_today) between 4 and 9
         then make_date(v_fy_start, 9, 30)
         else make_date(v_fy_start + 1, 3, 31) end,
    'Half-Yearly');

  -- Annual: due 31 March
  v_total := v_total + public.generate_recurring_tasks(
    'FY-' || v_fy, v_fy, make_date(v_fy_start + 1, 3, 31), 'Annual');

  return v_total;
end;
$$;

grant execute on function public.generate_scheduled_tasks() to authenticated;

drop function if exists public.generate_daily_tasks();

-- ---------------------------------------------------------------------
-- 5. Replace the cron job
-- ---------------------------------------------------------------------
create extension if not exists pg_cron;

do $$
declare
  v_id integer;
begin
  for v_id in
    select jobid from cron.job
    where jobname in ('daily-recurring-tasks', 'recurring-task-generator')
  loop
    perform cron.unschedule(v_id);
  end loop;
end $$;

select cron.schedule(
  'recurring-task-generator',
  '30 2 * * *',
  $$select public.generate_scheduled_tasks()$$
);

-- =====================================================================
--  Verify:
--    select jobname, schedule, active from cron.job;
--       -> recurring-task-generator | 30 2 * * * | t
--
--    Generate everything currently due, immediately:
--    select public.generate_scheduled_tasks();
--       -> creates today's daily instances, this week's weeklies, this
--          month's monthlies, etc. Second call the same day returns 0.
--
--    select name from public.task_master where name ilike '%bookkeeping%';
--       -> exactly one row: Bookkeeping / Data Entry
-- =====================================================================
