-- Expense Settlement Tool — additional function for account sign-up
-- Run this after the main schema. A brand-new signed-up user has no
-- RLS read access to `employees` yet (auth_user_id is still null, so
-- none of read_employees' OR conditions match) — this function runs
-- as security definer specifically to bridge that one moment.

create or replace function link_employee_account(p_employee_code text)
returns void as $$
declare
  v_employee_id uuid;
  v_existing_auth uuid;
begin
  select employee_id, auth_user_id into v_employee_id, v_existing_auth
  from employees where employee_code = p_employee_code;

  if v_employee_id is null then
    raise exception 'Employee code not found';
  end if;
  if v_existing_auth is not null then
    raise exception 'This employee code is already linked to an account';
  end if;

  update employees set auth_user_id = auth.uid() where employee_id = v_employee_id;
end;
$$ language plpgsql security definer;
