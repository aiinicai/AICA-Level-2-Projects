-- =====================================================================
--  FILE 14 : Latest progress comment on every task row
--
--  The board shows each task's most recent comment for one-glance context.
--  Comment visibility still follows task visibility (the view is
--  security_invoker, and task_comments RLS checks the task).
--
--  Run AFTER 10. Safe to re-run.
-- =====================================================================

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

  lc.comment     as latest_comment,
  lc.created_at  as latest_comment_at,
  lp.full_name   as latest_comment_by,

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
left join public.compliance_master cm on cm.id = t.compliance_id
left join lateral (
  select tc.comment, tc.created_at, tc.user_id
  from public.task_comments tc
  where tc.task_id = t.id
  order by tc.created_at desc
  limit 1
) lc on true
left join public.profiles lp    on lp.id = lc.user_id;

grant select on public.v_tasks_enriched to authenticated;

-- Verify: select title, latest_comment, latest_comment_by
--         from public.v_tasks_enriched where latest_comment is not null limit 5;
