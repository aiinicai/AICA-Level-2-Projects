-- =====================================================================
--  Aggarwal Samir & Co — Task Delegation App
--  FILE 10 : Compliance engine (schema + generation)
--
--  Absorbs the firm's Flask compliance tracker. Design as agreed:
--    - granularity: client + GSTIN (no persons table — director-level items
--      are ticked on the director's own Individual client row)
--    - instances are ORDINARY TASKS tagged with compliance_id
--    - generation covers the CURRENT financial year only
--    - a tick without an assignee is skipped (the UI shows a loud warning)
--    - ticks: any staff may ADD; only an admin may remove or change dates
--    - event-driven rules (DIR-12, CHG-1…) are seeded but NOT generatable —
--      that work is created manually from the Task Master
--
--  Run AFTER 09. Then run 11-compliance-seed.sql. Safe to re-run.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. GST registrations under a client
-- ---------------------------------------------------------------------
create table if not exists public.gst_registrations (
  id            uuid primary key default gen_random_uuid(),
  client_id     uuid not null references public.clients(id) on delete cascade,
  gstin         text not null,
  state         text,
  trade_name    text,
  is_active     boolean not null default true,
  registered_on date,
  notes         text,
  created_by    uuid references auth.users(id) on delete set null,
  created_at    timestamptz not null default now(),
  unique (client_id, gstin)
);

create index if not exists idx_gstreg_client on public.gst_registrations(client_id);

-- ---------------------------------------------------------------------
-- 2. Compliance rule catalogue (seeded from the firm's spreadsheet)
-- ---------------------------------------------------------------------
create table if not exists public.compliance_master (
  id                    uuid primary key default gen_random_uuid(),
  code                  text not null unique,
  name                  text not null,
  law                   text,
  entity_types          text,
  target_level          text not null default 'Client'
                        check (target_level in ('Client', 'GSTIN')),
  alt_group             text,
  frequency             text,
  frequency_overridable boolean not null default false,
  period_basis          text,
  due_rule_type         text,
  due_anchor            text,
  due_day               integer,
  due_month             integer,
  due_event             text,
  due_offset_days       integer,
  period_due_dates      text,
  due_rule_text         text,
  -- Calendar rules generate tasks; event-driven rules exist for reference
  -- and are created manually from the Task Master instead.
  is_generatable        boolean not null default false,
  default_applicable    boolean not null default false,
  active                boolean not null default true,
  notes                 text,
  created_at            timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- 3. The tick: this compliance applies to this client
-- ---------------------------------------------------------------------
create table if not exists public.client_compliance (
  id                 uuid primary key default gen_random_uuid(),
  client_id          uuid not null references public.clients(id) on delete cascade,
  compliance_id      uuid not null references public.compliance_master(id) on delete cascade,
  start_date         date,
  assigned_to        uuid references public.profiles(id) on delete set null,
  frequency_override text,   -- e.g. QRMP: master says Monthly, this client files Quarterly
  notes              text,
  created_by         uuid references auth.users(id) on delete set null,
  created_at         timestamptz not null default now(),
  unique (client_id, compliance_id)
);

create index if not exists idx_cc_client on public.client_compliance(client_id);

-- ---------------------------------------------------------------------
-- 4. Task columns + dedup key for generated instances
-- ---------------------------------------------------------------------
alter table public.tasks add column if not exists compliance_id uuid references public.compliance_master(id) on delete set null;
alter table public.tasks add column if not exists gstin        text;
alter table public.tasks add column if not exists filing_date  date;
alter table public.tasks add column if not exists filing_link  text;

create unique index if not exists uq_tasks_compliance_period
  on public.tasks (compliance_id, client_id, coalesce(gstin, ''), period, financial_year)
  where compliance_id is not null;

-- ---------------------------------------------------------------------
-- 5. Row-level security
--    Reads open to all staff. Adds open to all staff. Removal and edits of
--    the switches that stop statutory generation are admin-only, enforced
--    here and not just in the UI.
-- ---------------------------------------------------------------------
alter table public.gst_registrations enable row level security;
alter table public.compliance_master enable row level security;
alter table public.client_compliance enable row level security;

drop policy if exists gr_select on public.gst_registrations;
create policy gr_select on public.gst_registrations for select to authenticated using (true);

drop policy if exists gr_insert on public.gst_registrations;
create policy gr_insert on public.gst_registrations
  for insert to authenticated with check (true);

drop policy if exists gr_admin_update on public.gst_registrations;
create policy gr_admin_update on public.gst_registrations
  for update to authenticated using (public.is_admin()) with check (public.is_admin());

drop policy if exists gr_admin_delete on public.gst_registrations;
create policy gr_admin_delete on public.gst_registrations
  for delete to authenticated using (public.is_admin());

drop policy if exists cm_select on public.compliance_master;
create policy cm_select on public.compliance_master for select to authenticated using (true);

drop policy if exists cm_admin_write on public.compliance_master;
create policy cm_admin_write on public.compliance_master
  for all to authenticated using (public.is_admin()) with check (public.is_admin());

drop policy if exists cc_select on public.client_compliance;
create policy cc_select on public.client_compliance for select to authenticated using (true);

drop policy if exists cc_insert on public.client_compliance;
create policy cc_insert on public.client_compliance
  for insert to authenticated with check (true);

drop policy if exists cc_update on public.client_compliance;
create policy cc_update on public.client_compliance
  for update to authenticated using (true) with check (true);

drop policy if exists cc_admin_delete on public.client_compliance;
create policy cc_admin_delete on public.client_compliance
  for delete to authenticated using (public.is_admin());

-- Staff may edit a tick's assignee or notes, but the start date — which
-- decides what generates — is admin-only, same spirit as un-ticking.
create or replace function public.guard_client_compliance()
returns trigger
language plpgsql security definer set search_path = public
as $$
begin
  if not public.is_admin() and new.start_date is distinct from old.start_date then
    raise exception 'Only an administrator can change a compliance start date.';
  end if;
  return new;
end;
$$;

drop trigger if exists trg_guard_client_compliance on public.client_compliance;
create trigger trg_guard_client_compliance
  before update on public.client_compliance
  for each row execute function public.guard_client_compliance();

-- ---------------------------------------------------------------------
-- 6. Reporting view — compliance fields travel with every task
-- ---------------------------------------------------------------------
drop view if exists public.v_tasks_enriched;

create view public.v_tasks_enriched with (security_invoker = on) as
select
  t.id, t.title, t.priority, t.description,
  t.financial_year, t.period, t.start_date, t.due_date, t.completed_at,
  t.is_adhoc, t.created_at, t.updated_at,
  t.assigned_to, t.assigned_by, t.client_id, t.task_master_id,
  t.stage_id, t.stage_since, t.help_note,
  t.compliance_id, t.gstin, t.filing_date, t.filing_link,

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
  c.client_group as client_group,
  tm.name        as master_task_name,
  cm.code        as compliance_code,
  cm.name        as compliance_name,
  cm.law         as compliance_law,
  (t.compliance_id is not null) as is_compliance,

  coalesce(cm.law, tm.category, 'Ad-hoc') as category,

  (current_date - t.stage_since::date) as days_in_stage,
  (t.due_date is not null
     and t.due_date < current_date
     and not s.is_terminal) as is_overdue,
  (t.due_date - current_date) as days_to_due
from public.tasks t
join public.stages s            on s.id  = t.stage_id
join public.profiles p          on p.id  = t.assigned_to
left join public.profiles b     on b.id  = t.assigned_by
left join public.clients c      on c.id  = t.client_id
left join public.task_master tm on tm.id = t.task_master_id
left join public.compliance_master cm on cm.id = t.compliance_id;

grant select on public.v_tasks_enriched to authenticated;

-- ---------------------------------------------------------------------
-- 7. The due engine
-- ---------------------------------------------------------------------

-- "Q1=31-Jul; Q2=31-Oct; …" -> the due date for one period of one FY.
-- The due year follows the period end: a due month earlier in the calendar
-- than the period-end month lands in the following year (Q3 Oct–Dec due
-- 31-Jan means January NEXT year).
create or replace function public.compliance_schedule_due(
  _schedule   text,   -- the period_due_dates string
  _label      text,   -- Q1 / Q2 / H1 / H2 ...
  _period_end date
)
returns date
language plpgsql immutable
as $$
declare
  v_part  text;
  v_datep text;
  v_day   integer;
  v_month integer;
  v_year  integer;
begin
  foreach v_part in array string_to_array(_schedule, ';') loop
    v_part := btrim(v_part);
    if upper(split_part(v_part, '=', 1)) = upper(_label) then
      v_datep := btrim(split_part(v_part, '=', 2));            -- e.g. 31-Jul
      v_day   := split_part(v_datep, '-', 1)::integer;
      v_month := extract(month from to_date(split_part(v_datep, '-', 2) || '-2000', 'Mon-YYYY'))::integer;
      v_year  := extract(year from _period_end)::integer;
      if v_month < extract(month from _period_end)::integer then
        v_year := v_year + 1;
      end if;
      return make_date(v_year, v_month, v_day);
    end if;
  end loop;
  return null;
end;
$$;

-- One morning pass: create every compliance task of the current FY whose due
-- date is inside its visibility lead. Idempotent via the unique index.
create or replace function public.generate_compliance_tasks()
returns integer
language plpgsql security definer set search_path = public
as $$
declare
  v_today    date := (timezone('Asia/Kolkata', now()))::date;
  v_fy_start integer;
  v_fy       text;
  v_fy_first date;
  v_created  integer := 0;
  v_stage    uuid;
  tick       record;
  tgt        record;
  v_freq     text;
  v_p_start  date;
  v_p_end    date;
  v_label    text;
  v_due      date;
  v_lead     integer;
  v_note     text;
  v_from     date;
  q          integer;
  m          date;
begin
  if auth.uid() is not null and not public.is_admin() then
    raise exception 'Only an administrator can generate compliance tasks.';
  end if;

  v_fy_start := case when extract(month from v_today) >= 4
                     then extract(year from v_today)::integer
                     else extract(year from v_today)::integer - 1 end;
  v_fy       := v_fy_start || '-' || to_char(((v_fy_start + 1) % 100), 'FM00');
  v_fy_first := make_date(v_fy_start, 4, 1);

  select id into v_stage from public.stages where code = '01';

  for tick in
    select cc.id, cc.client_id, cc.assigned_to, cc.created_by, cc.start_date,
           coalesce(cc.frequency_override, cm.frequency) as frequency,
           cm.id as cm_id, cm.code, cm.name, cm.law, cm.target_level,
           cm.due_rule_type, cm.due_anchor, cm.due_day, cm.due_month,
           cm.due_event, cm.due_offset_days, cm.period_due_dates, cm.due_rule_text
    from public.client_compliance cc
    join public.compliance_master cm on cm.id = cc.compliance_id
    join public.clients c            on c.id  = cc.client_id
    where cm.is_generatable and cm.active and c.is_active
      and cc.assigned_to is not null                      -- blank = skip (UI warns)
  loop
    v_freq := lower(replace(tick.frequency, ' ', '-'));   -- 'Half Yearly' -> 'half-yearly'
    v_from := greatest(coalesce(tick.start_date, v_fy_first), v_fy_first);

    -- Per-GSTIN rules expand across the client's active registrations; a
    -- ticked GSTIN rule with no registrations yields nothing (UI warns).
    for tgt in
      select * from (
        select g.gstin from public.gst_registrations g
        where tick.target_level = 'GSTIN'
          and g.client_id = tick.client_id and g.is_active
        union all
        select null::text where tick.target_level = 'Client'
      ) targets
    loop

      -- ============ MONTHLY ============
      if v_freq = 'monthly' and tick.due_rule_type in ('period_relative', 'fixed_annual') then
        v_lead := 30;
        m := date_trunc('month', v_from)::date;
        while m < make_date(v_fy_start + 1, 4, 1) loop
          v_p_end := (m + interval '1 month - 1 day')::date;
          v_label := to_char(m, 'Mon-YYYY');
          v_due   := make_date(
                       extract(year from (m + interval '1 month'))::integer,
                       extract(month from (m + interval '1 month'))::integer,
                       least(coalesce(tick.due_day, 20), 28));
          if tick.due_day is not null and tick.due_day <= 28 then
            v_due := (date_trunc('month', m + interval '1 month')
                      + make_interval(days => tick.due_day - 1))::date;
          end if;
          exit when v_due - v_lead > v_today;
          v_created := v_created + public.insert_compliance_task(
            tick.cm_id, tick.client_id, tgt.gstin, tick.assigned_to,
            coalesce(tick.created_by, tick.assigned_to), v_stage,
            tick.name, tick.law, tick.due_rule_text, v_fy, v_label, v_p_end, v_due, null);
          m := (m + interval '1 month')::date;
        end loop;

      -- ============ QUARTERLY (explicit schedule) ============
      elsif tick.due_rule_type = 'quarterly_schedule'
            or (v_freq = 'quarterly' and tick.period_due_dates is not null) then
        v_lead := 30;
        for q in 1..4 loop
          v_p_start := make_date(v_fy_start, 4, 1) + make_interval(months => (q - 1) * 3);
          v_p_end   := (v_p_start + interval '3 months - 1 day')::date;
          continue when v_p_end < v_from;
          v_label := 'Q' || q || '-' || v_fy;
          v_due   := public.compliance_schedule_due(tick.period_due_dates, 'Q' || q, v_p_end);
          continue when v_due is null or v_due - v_lead > v_today;
          v_created := v_created + public.insert_compliance_task(
            tick.cm_id, tick.client_id, tgt.gstin, tick.assigned_to,
            coalesce(tick.created_by, tick.assigned_to), v_stage,
            tick.name, tick.law, tick.due_rule_text, v_fy, v_label, v_p_end, v_due, null);
        end loop;

      -- ============ QUARTERLY (day-of-next-month rule, e.g. QRMP) ============
      elsif v_freq = 'quarterly' and tick.due_rule_type = 'period_relative' then
        v_lead := 30;
        for q in 1..4 loop
          v_p_start := make_date(v_fy_start, 4, 1) + make_interval(months => (q - 1) * 3);
          v_p_end   := (v_p_start + interval '3 months - 1 day')::date;
          continue when v_p_end < v_from;
          v_label := 'Q' || q || '-' || v_fy;
          v_due   := (date_trunc('month', v_p_end + interval '1 month')
                      + make_interval(days => least(coalesce(tick.due_day, 22), 28) - 1))::date;
          continue when v_due - v_lead > v_today;
          v_created := v_created + public.insert_compliance_task(
            tick.cm_id, tick.client_id, tgt.gstin, tick.assigned_to,
            coalesce(tick.created_by, tick.assigned_to), v_stage,
            tick.name, tick.law, tick.due_rule_text, v_fy, v_label, v_p_end, v_due, null);
        end loop;

      -- ============ HALF-YEARLY ============
      elsif tick.due_rule_type = 'half_yearly_schedule' then
        v_lead := 45;
        for q in 1..2 loop
          v_p_start := make_date(v_fy_start, 4, 1) + make_interval(months => (q - 1) * 6);
          v_p_end   := (v_p_start + interval '6 months - 1 day')::date;
          continue when v_p_end < v_from;
          v_label := 'H' || q || '-' || v_fy;
          v_due   := public.compliance_schedule_due(tick.period_due_dates, 'H' || q, v_p_end);
          continue when v_due is null or v_due - v_lead > v_today;
          v_created := v_created + public.insert_compliance_task(
            tick.cm_id, tick.client_id, tgt.gstin, tick.assigned_to,
            coalesce(tick.created_by, tick.assigned_to), v_stage,
            tick.name, tick.law, tick.due_rule_text, v_fy, v_label, v_p_end, v_due, null);
        end loop;

      -- ============ ANNUAL, fixed date after the FY ============
      elsif tick.due_rule_type = 'fixed_annual' then
        v_lead := 120;
        v_label := 'FY-' || v_fy;
        v_due := make_date(
          v_fy_start + 1 + case when coalesce(tick.due_month, 12) < 4 then 1 else 0 end,
          coalesce(tick.due_month, 12),
          coalesce(tick.due_day, 31));
        if tick.due_anchor = 'before_period' then
          v_due := make_date(v_fy_start, coalesce(tick.due_month, 3), coalesce(tick.due_day, 31));
        end if;
        if v_due - v_lead <= v_today then
          v_created := v_created + public.insert_compliance_task(
            tick.cm_id, tick.client_id, tgt.gstin, tick.assigned_to,
            coalesce(tick.created_by, tick.assigned_to), v_stage,
            tick.name, tick.law, tick.due_rule_text, v_fy,
            v_label, make_date(v_fy_start + 1, 3, 31), v_due, null);
        end if;

      -- ============ ANNUAL, anchored to the AGM ============
      elsif tick.due_rule_type = 'event_anchored' and tick.due_event = 'AGM' then
        v_lead := 90;
        v_label := 'FY-' || v_fy;
        -- Provisional: AGM assumed 30-Sep after the FY. The due date is
        -- editable on the task (and the change is logged).
        v_due  := make_date(v_fy_start + 1, 9, 30) + coalesce(tick.due_offset_days, 30);
        v_note := 'Due date is PROVISIONAL — computed from an assumed AGM of 30-Sep. '
                  || coalesce(tick.due_rule_text, '');
        if v_due - v_lead <= v_today then
          v_created := v_created + public.insert_compliance_task(
            tick.cm_id, tick.client_id, tgt.gstin, tick.assigned_to,
            coalesce(tick.created_by, tick.assigned_to), v_stage,
            tick.name, tick.law, v_note, v_fy,
            v_label, make_date(v_fy_start + 1, 3, 31), v_due, v_note);
        end if;
      end if;

    end loop;
  end loop;

  return v_created;
end;
$$;

-- Shared insert with the dedup check. Returns 1 if created, 0 if it existed.
create or replace function public.insert_compliance_task(
  _cm_id uuid, _client_id uuid, _gstin text, _assigned_to uuid, _assigned_by uuid,
  _stage uuid, _name text, _law text, _rule_text text, _fy text,
  _period text, _period_end date, _due date, _description text
)
returns integer
language plpgsql security definer set search_path = public
as $$
begin
  if exists (
    select 1 from public.tasks t
    where t.compliance_id = _cm_id
      and t.client_id = _client_id
      and coalesce(t.gstin, '') = coalesce(_gstin, '')
      and t.period = _period
      and t.financial_year = _fy
  ) then
    return 0;
  end if;

  insert into public.tasks (
    title, compliance_id, gstin, client_id, assigned_to, assigned_by,
    stage_id, priority, description, financial_year, period,
    start_date, due_date, is_adhoc
  ) values (
    _name || case when _gstin is not null then ' [' || _gstin || ']' else '' end,
    _cm_id, _gstin, _client_id, _assigned_to, _assigned_by,
    _stage, 'High',
    coalesce(_description, 'Compliance: ' || coalesce(_rule_text, _law, '')),
    _fy, _period, _period_end, _due, false
  );
  return 1;
end;
$$;

grant execute on function public.generate_compliance_tasks() to authenticated;

-- ---------------------------------------------------------------------
-- 8. One morning job runs recurring AND compliance generation
-- ---------------------------------------------------------------------
create or replace function public.generate_morning_tasks()
returns integer
language plpgsql security definer set search_path = public
as $$
begin
  return public.generate_scheduled_tasks() + public.generate_compliance_tasks();
end;
$$;

grant execute on function public.generate_morning_tasks() to authenticated;

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
  $$select public.generate_morning_tasks()$$
);

-- =====================================================================
--  Verify after 11-compliance-seed.sql:
--    select count(*) filter (where is_generatable) as generatable,
--           count(*) as total from public.compliance_master;
--    select public.generate_compliance_tasks();  -- 0 until ticks exist
-- =====================================================================
