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
begin
  if not (is_any_head() or is_accounts() or is_admin()) then
    raise exception 'Not authorized for firm-wide dashboard stats';
  end if;

  select json_build_object(
    'total_claims', (select count(*) from claims),
    'by_status', (select coalesce(json_object_agg(status, cnt), '{}') from (
        select status, count(*) cnt from claims group by status
      ) s),
    'amount_by_status', (select coalesce(json_object_agg(status, amt), '{}') from (
        select c.status, coalesce(sum(cl.amount),0) amt
        from claims c left join claim_lines cl on cl.claim_id = c.claim_id
        group by c.status
      ) s2),
    'category_totals', (select coalesce(json_object_agg(category, amt), '{}') from (
        select category, sum(amount) amt from claim_lines group by category
      ) s3),
    'top_claimants', (select coalesce(json_agg(t), '[]') from (
        select e.name, e.employee_code, sum(cl.amount) total
        from claims c
        join employees e on e.employee_id = c.employee_id
        join claim_lines cl on cl.claim_id = c.claim_id
        group by e.employee_id, e.name, e.employee_code
        order by total desc limit 5
      ) t),
    'monthly_totals', (select coalesce(json_agg(m), '[]') from (
        select c.month, sum(cl.amount) total
        from claims c join claim_lines cl on cl.claim_id = c.claim_id
        group by c.month order by c.month desc limit 6
      ) m),
    'recent_activity', (select coalesce(json_agg(r), '[]') from (
        select e.name, c.month, c.status, c.created_at
        from claims c join employees e on e.employee_id = c.employee_id
        order by c.created_at desc limit 8
      ) r)
  ) into result;

  return result;
end;
$$ language plpgsql security definer;
