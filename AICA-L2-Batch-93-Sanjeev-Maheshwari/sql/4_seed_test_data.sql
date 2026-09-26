-- TEST seed data for the Expense Settlement Tool
-- Clearly marked as test data (team name and employee codes both say
-- TEST) so it's obvious what to delete before real firm data goes in.
-- Run this in the Expenses Settlement Supabase project's SQL Editor,
-- after the main schema and storage policies.

-- Step 1: one test team, plus three employees on it (ordinary employee,
-- team head, accounts). team_id is filled in via the CTE; head_employee_id
-- is deliberately left null here and set in Step 2, once the employees
-- exist to reference.

with new_team as (
  insert into teams (team_name) values ('Audit & Assurance (TEST)')
  returning team_id
)
insert into employees (employee_code, name, designation, team_id, is_accounts)
select v.code, v.name, v.designation::designation_type, t.team_id, v.is_accounts
from new_team t,
(values
  ('TEST-EMP-01', 'Test Employee', 'article', false),
  ('TEST-HEAD-01', 'Test Head', 'qualified', false),
  ('TEST-ACC-01', 'Test Accounts', 'staff', true)
) as v(code, name, designation, is_accounts);

-- Bootstrap admin — no one is_admin yet, so this one is seeded directly
-- rather than created through the Admin screen (which needs an existing
-- admin to use it). Link this one's login the same one-time way, then
-- every team/employee after it can go through the Admin screen itself.
insert into employees (employee_code, name, designation, team_id, is_admin)
select 'TEST-ADMIN-01', 'Test Admin', 'staff', team_id, true
from teams where team_name = 'Audit & Assurance (TEST)';

-- Step 2: point the team's head_employee_id at the employee just created
-- for that role. No backup approver in this test set — add one later
-- with the same pattern if you want to test that path too.

update teams
set head_employee_id = (select employee_id from employees where employee_code = 'TEST-HEAD-01')
where team_name = 'Audit & Assurance (TEST)';

-- Test employees, for admin-provisioned logins (no self-service sign-up):
--   TEST-EMP-01   -> ordinary employee, test "My Claims"
--   TEST-HEAD-01  -> team head, test "Approvals"
--   TEST-ACC-01   -> accounts, test "Settlement"
--   TEST-ADMIN-01 -> bootstrap admin, test the "Admin" screen
-- Each needs a login created in Supabase Dashboard -> Authentication ->
-- Add user (check "Auto Confirm User"), then linked to their employee_code.
-- TEST-ADMIN-01 must be linked directly (see expense_tool_admin_capability.sql's
-- bootstrap note); the other three can then be linked via the Admin screen's
-- "Link a login" panel once TEST-ADMIN-01 is signed in.

-- To remove this test data later, in this order (children before parents):
--   delete from employees where employee_code like 'TEST-%';
--   delete from teams where team_name = 'Audit & Assurance (TEST)';
