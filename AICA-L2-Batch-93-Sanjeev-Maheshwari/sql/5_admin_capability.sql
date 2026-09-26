-- Expense Settlement Tool — admin capability
-- Run this after the earlier SQL files. Adds an is_admin flag, lets
-- admins create/manage employees and teams from within the app, and
-- lets an admin link a Supabase-Dashboard-created login to an employee
-- record by email, without needing to know or paste a UUID.

alter table employees add column if not exists is_admin boolean not null default false;

create or replace function is_admin()
returns boolean as $$
  select coalesce((select is_admin from employees where auth_user_id = auth.uid()), false);
$$ language sql stable security definer;

-- Admins can create and edit employees and teams from the app
create policy "admin_create_employees" on employees for insert with check (is_admin());
create policy "admin_update_employees" on employees for update using (is_admin()) with check (is_admin());
create policy "admin_create_teams" on teams for insert with check (is_admin());
create policy "admin_update_teams" on teams for update using (is_admin()) with check (is_admin());

-- Links an existing login (created via Supabase Dashboard -> Authentication
-- -> Add user, with "Auto Confirm User" checked) to an employee record, by
-- email. security definer lets this read auth.users, which a normal client
-- cannot query directly under RLS -- the admin never needs to see or paste
-- a UUID by hand.
create or replace function link_employee_by_email(p_employee_code text, p_email text)
returns void as $$
declare
  v_employee_id uuid;
  v_existing_auth uuid;
  v_auth_user_id uuid;
begin
  if not is_admin() then
    raise exception 'Only an admin can link employee accounts';
  end if;

  select employee_id, auth_user_id into v_employee_id, v_existing_auth
  from employees where employee_code = p_employee_code;
  if v_employee_id is null then raise exception 'Employee code not found'; end if;
  if v_existing_auth is not null then raise exception 'This employee is already linked to a login'; end if;

  select id into v_auth_user_id from auth.users where lower(email) = lower(p_email);
  if v_auth_user_id is null then
    raise exception 'No login found with that email. Create it first in Supabase Dashboard -> Authentication -> Add user.';
  end if;

  update employees set auth_user_id = v_auth_user_id where employee_id = v_employee_id;
end;
$$ language plpgsql security definer;

-- Bootstrap note: the very first admin can't be created through the app
-- (nothing is_admin yet to grant the permission). Set one directly via
-- SQL Editor, e.g.:
--   update employees set is_admin = true where employee_code = 'TEST-ADMIN-01';
-- then link that employee's login the same one-time way as before,
-- using link_employee_account or a direct UUID update. Every employee
-- and team after that can be created and linked through the app itself.
