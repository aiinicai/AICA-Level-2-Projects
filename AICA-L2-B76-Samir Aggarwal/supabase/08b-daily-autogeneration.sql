-- =====================================================================
--  Aggarwal Samir & Co — Task Delegation App
--  FILE 8b : Daily recurring tasks, generated automatically each morning
--
--  Run AFTER 08a (which must run alone).
--
--  A Daily schedule is pointless if a human must press Generate every day,
--  so this also sets up pg_cron: every morning at 08:00 IST the database
--  creates the day's tasks itself — one per active Daily schedule, due the
--  same day, skipping anything already created. No app, server or person
--  involved.
--
--  Safe to re-run.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. The generator, made callable by the scheduler
--    pg_cron runs with no signed-in user, so auth.uid() is null there.
--    The admin check now applies only when a real user is calling; the
--    assigner falls back to whoever created the schedule, else the
--    assignee themselves.
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
      and (_recurrence is null or tm.recurrence::text = _recurrence)
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
-- 2. No-argument wrapper the scheduler calls: today's date in IST,
--    period label like "14-Aug-2026", Indian financial year Apr–Mar.
-- ---------------------------------------------------------------------
create or replace function public.generate_daily_tasks()
returns integer
language plpgsql security definer set search_path = public
as $$
declare
  v_today    date := (timezone('Asia/Kolkata', now()))::date;
  v_period   text := to_char(v_today, 'DD-Mon-YYYY');
  v_fy_start integer;
  v_fy       text;
begin
  v_fy_start := case when extract(month from v_today) >= 4
                     then extract(year from v_today)::integer
                     else extract(year from v_today)::integer - 1 end;
  v_fy := v_fy_start || '-' || to_char(((v_fy_start + 1) % 100), 'FM00');

  return public.generate_recurring_tasks(v_period, v_fy, v_today, 'Daily');
end;
$$;

grant execute on function public.generate_daily_tasks() to authenticated;

-- ---------------------------------------------------------------------
-- 3. The morning schedule: 02:30 UTC = 08:00 IST, every day.
--    Re-running this file replaces the job rather than duplicating it.
-- ---------------------------------------------------------------------
create extension if not exists pg_cron;

do $$
declare
  v_id integer;
begin
  select jobid into v_id from cron.job where jobname = 'daily-recurring-tasks';
  if v_id is not null then
    perform cron.unschedule(v_id);
  end if;
end $$;

select cron.schedule(
  'daily-recurring-tasks',
  '30 2 * * *',
  $$select public.generate_daily_tasks()$$
);

-- =====================================================================
--  Verify:
--    select jobname, schedule, active from cron.job;
--       -> one row: daily-recurring-tasks | 30 2 * * * | t
--
--    Run one generation immediately rather than waiting for morning:
--    select public.generate_daily_tasks();
--       -> the number of tasks created for today
--
--  Each run is idempotent: a second call the same day returns 0.
--  Job history, if you ever need it:
--    select * from cron.job_run_details order by start_time desc limit 5;
-- =====================================================================
