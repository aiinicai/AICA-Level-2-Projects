-- =====================================================================
--  Aggarwal Samir & Co — Task Delegation App
--  FILE 5 : Client grouping
--
--  An Indian practice rarely bills "a client" — it bills a group. The
--  individual, the HUF, the family LLP and the Pvt Ltd are one relationship
--  and one conversation, but four rows in public.clients. This adds the group
--  so the Status Board can pivot the way a partner actually thinks.
--
--  Free text rather than a master table, deliberately: the app offers the
--  existing groups in a combobox so typos do not fragment a group, while a
--  new group needs no migration. Same approach as task_master.category.
--
--  Safe to re-run.
-- =====================================================================

alter table public.clients add column if not exists client_group text;

create index if not exists idx_clients_group on public.clients(client_group);

-- Rebuild the reporting view so the group travels with every task.
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
  c.client_group as client_group,
  tm.name        as master_task_name,
  coalesce(tm.category, 'Ad-hoc') as category,

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

-- =====================================================================
--  Verify:
--    select client_group, count(*) from public.clients group by 1 order by 1;
--    select client_group from public.v_tasks_enriched limit 1;
-- =====================================================================
