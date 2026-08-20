-- =====================================================================
--  FILE 13 : Compliance visibility leads, per the firm's preference
--
--  How many days before its due date a compliance task materialises:
--    Monthly       10   (GSTR-3B due 20th appears on the 10th)
--    Quarterly     15
--    Half-yearly   30
--    Annual        60   (two months, per the firm)
--    AGM-anchored  60
--
--  Weekly has no compliance rules in the catalogue — weekly work comes from
--  recurring schedules, which create at the start of the week by design.
--
--  Already-created tasks are never touched; this only changes when FUTURE
--  instances first appear. Run any time. Safe to re-run.
-- =====================================================================

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
  v_p_end    date;
  v_p_start  date;
  v_label    text;
  v_due      date;
  v_lead     integer;
  v_note     text;
  v_from     date;
  q          integer;
  m          date;

  -- The firm's visibility windows (days before due).
  c_lead_monthly     constant integer := 10;
  c_lead_quarterly   constant integer := 15;
  c_lead_half_yearly constant integer := 30;
  c_lead_annual      constant integer := 60;
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
      and cc.assigned_to is not null
  loop
    v_freq := lower(replace(tick.frequency, ' ', '-'));
    v_from := greatest(coalesce(tick.start_date, v_fy_first), v_fy_first);

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
        v_lead := c_lead_monthly;
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
        v_lead := c_lead_quarterly;
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
        v_lead := c_lead_quarterly;
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
        v_lead := c_lead_half_yearly;
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

      -- ============ ANNUAL, fixed date ============
      elsif tick.due_rule_type = 'fixed_annual' then
        v_lead := c_lead_annual;
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
        v_lead := c_lead_annual;
        v_label := 'FY-' || v_fy;
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

grant execute on function public.generate_compliance_tasks() to authenticated;

-- Verify: select public.generate_morning_tasks();
