-- Expense Settlement Tool — firm-wide dashboard stats
-- Run after admin_capability.sql. Returns AGGREGATE numbers only (counts,
-- sums) to authorized roles -- never individual claim rows. This is
-- deliberate: existing RLS restricts a team head to their own team's
-- claims, and accounts to approved/settled only. A dashboard that just
-- queried the tables directly would either break those rules or show
-- incomplete data. This function preserves row-level privacy while still
-- answering "what's the firm-wide picture" for roles that need it.

create or replace function is_any_head()
returns boolean as $$
  select exists(
    select 1 from teams
    where head_employee_id = current_employee_id() or backup_approver_id = current_employee_id()
  );
$$ language sql stable security definer;

create or replace function get_dashboard_stats()
returns json as $$
declare
  result json;
  v_role text;
  v_firm_wide boolean;
  v_team_ids uuid[];
begin
  if is_admin() then
    v_role := 'admin'; v_firm_wide := true;
  elsif is_accounts() then
    v_role := 'accounts'; v_firm_wide := true;
  elsif is_any_head() then
    v_role := 'team'; v_firm_wide := false;
    select array_agg(team_id) into v_team_ids from teams
      where head_employee_id = current_employee_id() or backup_approver_id = current_employee_id();
  else
    raise exception 'Not authorized for dashboard stats';
  end if;

  select json_build_object(
    'role', v_role,
    'total_claims', (
      select count(*) from claims c join employees e on e.employee_id = c.employee_id
      where v_firm_wide or e.team_id = any(v_team_ids)
    ),
    'by_status', (select coalesce(json_object_agg(status, cnt), '{}') from (
        select c.status, count(*) cnt
        from claims c join employees e on e.employee_id = c.employee_id
        where v_firm_wide or e.team_id = any(v_team_ids)
        group by c.status
      ) s),
    'amount_by_status', (select coalesce(json_object_agg(status, amt), '{}') from (
        select c.status, coalesce(sum(cl.amount),0) amt
        from claims c
        join employees e on e.employee_id = c.employee_id
        left join claim_lines cl on cl.claim_id = c.claim_id
        where v_firm_wide or e.team_id = any(v_team_ids)
        group by c.status
      ) s2),
    'rejected_count', (
      select count(*) from approval_log al
      join claims c on c.claim_id = al.claim_id
      join employees e on e.employee_id = c.employee_id
      where al.action = 'rejected' and (v_firm_wide or e.team_id = any(v_team_ids))
    ),
    'rejected_amount', (
      select coalesce(sum(sub.amt), 0) from (
        select distinct al.claim_id, (select coalesce(sum(amount),0) from claim_lines where claim_id = al.claim_id) as amt
        from approval_log al
        join claims c on c.claim_id = al.claim_id
        join employees e on e.employee_id = c.employee_id
        where al.action = 'rejected' and (v_firm_wide or e.team_id = any(v_team_ids))
      ) sub
    ),
    'category_totals', (select coalesce(json_object_agg(category, amt), '{}') from (
        select cl.category, sum(cl.amount) amt
        from claim_lines cl
        join claims c on c.claim_id = cl.claim_id
        join employees e on e.employee_id = c.employee_id
        where v_firm_wide or e.team_id = any(v_team_ids)
        group by cl.category
      ) s3),
    'employee_breakdown', (select coalesce(json_agg(t), '[]') from (
        select
          e.name, e.employee_code,
          count(*) filter (where c.status = 'submitted') as pending_count,
          count(*) filter (where c.status = 'approved') as approved_count,
          count(*) filter (where c.status = 'settled') as settled_count,
          coalesce(sum(cl.amount), 0) as total_amount
        from claims c
        join employees e on e.employee_id = c.employee_id
        join claim_lines cl on cl.claim_id = c.claim_id
        where v_firm_wide or e.team_id = any(v_team_ids)
        group by e.employee_id, e.name, e.employee_code
        order by total_amount desc
        limit (case when v_firm_wide then 10 else 50 end)
      ) t),
    'monthly_totals', (select coalesce(json_agg(m), '[]') from (
        select c.month, sum(cl.amount) total
        from claims c
        join employees e on e.employee_id = c.employee_id
        join claim_lines cl on cl.claim_id = c.claim_id
        where v_firm_wide or e.team_id = any(v_team_ids)
        group by c.month order by c.month desc limit 6
      ) m),
    'recent_activity', (select coalesce(json_agg(r), '[]') from (
        select e.name, c.month, c.status, c.created_at
        from claims c join employees e on e.employee_id = c.employee_id
        where v_firm_wide or e.team_id = any(v_team_ids)
        order by c.created_at desc limit 8
      ) r),
    'employee_count', (case when v_role = 'admin' then (select count(*) from employees) else null end),
    'linked_employee_count', (case when v_role = 'admin' then (select count(*) from employees where auth_user_id is not null) else null end),
    'team_count', (case when v_role = 'admin' then (select count(*) from teams) else null end)
  ) into result;

  return result;
end;
$$ language plpgsql security definer;
