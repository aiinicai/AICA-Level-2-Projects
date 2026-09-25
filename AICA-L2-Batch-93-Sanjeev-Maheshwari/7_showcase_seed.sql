-- Expense Settlement Tool — realistic showcase seed data
-- Run this AFTER 4_seed_test_data.sql (extends it, doesn't replace it).
-- Adds a second team, four more employees, and a realistic spread of
-- claims across every status, each with a matching approval_log history
-- — so the dashboard reflects a genuine firm-wide picture, not a single
-- test claim per role.

-- ============================================================
-- Second team + four more employees
-- ============================================================

with new_team as (
  insert into teams (team_name) values ('Direct Tax (TEST)')
  returning team_id
)
insert into employees (employee_code, name, designation, team_id, is_accounts)
select v.code, v.name, v.designation::designation_type, t.team_id, false
from new_team t,
(values
  ('TEST-HEAD-02', 'Test Head Two', 'qualified'),
  ('TEST-EMP-04', 'Neha Kulkarni', 'article'),
  ('TEST-EMP-05', 'Arjun Rao', 'staff')
) as v(code, name, designation);

update teams set head_employee_id = (select employee_id from employees where employee_code = 'TEST-HEAD-02')
where team_name = 'Direct Tax (TEST)';

-- Two more employees on the existing Audit team
insert into employees (employee_code, name, designation, team_id, is_accounts)
select 'TEST-EMP-02', 'Priya Shah', 'article'::designation_type, team_id, false from teams where team_name = 'Audit & Assurance (TEST)'
union all
select 'TEST-EMP-03', 'Karan Mehta', 'qualified'::designation_type, team_id, false from teams where team_name = 'Audit & Assurance (TEST)';

-- ============================================================
-- Claims, line items, and matching approval_log history
-- Note: TEST-EMP-01's 2026-09 claim already exists from live testing —
-- these deliberately use other months for that employee to avoid the
-- unique(employee_id, month) constraint.
-- ============================================================

do $$
declare
  v_claim_id uuid;
  v_emp_id uuid;
  v_head_id uuid;
  v_acc_id uuid;
begin
  select employee_id into v_acc_id from employees where employee_code = 'TEST-ACC-01';

  -- ---- SETTLED (3): full submit -> approve -> settle history ----

  -- TEST-EMP-01 / July / settled
  select employee_id into v_emp_id from employees where employee_code = 'TEST-EMP-01';
  select head_employee_id into v_head_id from teams where team_name = 'Audit & Assurance (TEST)';
  insert into claims (employee_id, month, status, submitted_at, approved_at, approved_by, settled_at, settled_by, payment_reference)
    values (v_emp_id, '2026-07', 'settled', '2026-07-05', '2026-07-08', v_head_id, '2026-07-15', v_acc_id, 'NEFT-1007')
    returning claim_id into v_claim_id;
  insert into claim_lines (claim_id, expense_date, category, client_code, amount, description) values
    (v_claim_id, '2026-07-03', 'conveyance', 'GMJ', 320, 'Local travel for audit fieldwork'),
    (v_claim_id, '2026-07-04', 'boarding_lodging', 'Meridian Textiles', 2200, 'Overnight stay, statutory audit');
  insert into approval_log (claim_id, action, actor_id, at) values
    (v_claim_id, 'submitted', v_emp_id, '2026-07-05'),
    (v_claim_id, 'approved', v_head_id, '2026-07-08'),
    (v_claim_id, 'settled', v_acc_id, '2026-07-15');

  -- TEST-EMP-03 / July / settled
  select employee_id into v_emp_id from employees where employee_code = 'TEST-EMP-03';
  insert into claims (employee_id, month, status, submitted_at, approved_at, approved_by, settled_at, settled_by, payment_reference)
    values (v_emp_id, '2026-07', 'settled', '2026-07-10', '2026-07-12', v_head_id, '2026-07-20', v_acc_id, 'NEFT-1008')
    returning claim_id into v_claim_id;
  insert into claim_lines (claim_id, expense_date, category, client_code, amount, description) values
    (v_claim_id, '2026-07-09', 'boarding_lodging', 'Konkan Cold Chain', 5200, 'Three-day inventory verification visit');
  insert into approval_log (claim_id, action, actor_id, at) values
    (v_claim_id, 'submitted', v_emp_id, '2026-07-10'),
    (v_claim_id, 'approved', v_head_id, '2026-07-12'),
    (v_claim_id, 'settled', v_acc_id, '2026-07-20');

  -- TEST-EMP-05 / July / settled
  select employee_id into v_emp_id from employees where employee_code = 'TEST-EMP-05';
  select head_employee_id into v_head_id from teams where team_name = 'Direct Tax (TEST)';
  insert into claims (employee_id, month, status, submitted_at, approved_at, approved_by, settled_at, settled_by, payment_reference)
    values (v_emp_id, '2026-07', 'settled', '2026-07-14', '2026-07-16', v_head_id, '2026-07-22', v_acc_id, 'NEFT-1009')
    returning claim_id into v_claim_id;
  insert into claim_lines (claim_id, expense_date, category, client_code, amount, description) values
    (v_claim_id, '2026-07-13', 'boarding_lodging', 'GMJ', 3100, 'Training program, out of town');
  insert into approval_log (claim_id, action, actor_id, at) values
    (v_claim_id, 'submitted', v_emp_id, '2026-07-14'),
    (v_claim_id, 'approved', v_head_id, '2026-07-16'),
    (v_claim_id, 'settled', v_acc_id, '2026-07-22');

  -- ---- APPROVED, awaiting settlement (3) ----

  -- TEST-EMP-02 / September / approved
  select employee_id into v_emp_id from employees where employee_code = 'TEST-EMP-02';
  select head_employee_id into v_head_id from teams where team_name = 'Audit & Assurance (TEST)';
  insert into claims (employee_id, month, status, submitted_at, approved_at, approved_by)
    values (v_emp_id, '2026-09', 'approved', '2026-09-18', '2026-09-20', v_head_id)
    returning claim_id into v_claim_id;
  insert into claim_lines (claim_id, expense_date, category, client_code, amount, description) values
    (v_claim_id, '2026-09-17', 'conveyance', 'GMJ', 300, 'Client meeting travel');
  insert into approval_log (claim_id, action, actor_id, at) values
    (v_claim_id, 'submitted', v_emp_id, '2026-09-18'),
    (v_claim_id, 'approved', v_head_id, '2026-09-20');

  -- TEST-EMP-03 / August / approved
  select employee_id into v_emp_id from employees where employee_code = 'TEST-EMP-03';
  select head_employee_id into v_head_id from teams where team_name = 'Audit & Assurance (TEST)';
  insert into claims (employee_id, month, status, submitted_at, approved_at, approved_by)
    values (v_emp_id, '2026-08', 'approved', '2026-08-22', '2026-08-24', v_head_id)
    returning claim_id into v_claim_id;
  insert into claim_lines (claim_id, expense_date, category, client_code, amount, description) values
    (v_claim_id, '2026-08-21', 'conveyance', 'GMJ', 410, 'Local conveyance, multiple client visits');
  insert into approval_log (claim_id, action, actor_id, at) values
    (v_claim_id, 'submitted', v_emp_id, '2026-08-22'),
    (v_claim_id, 'approved', v_head_id, '2026-08-24');

  -- TEST-EMP-04 / August / approved
  select employee_id into v_emp_id from employees where employee_code = 'TEST-EMP-04';
  select head_employee_id into v_head_id from teams where team_name = 'Direct Tax (TEST)';
  insert into claims (employee_id, month, status, submitted_at, approved_at, approved_by)
    values (v_emp_id, '2026-08', 'approved', '2026-08-25', '2026-08-27', v_head_id)
    returning claim_id into v_claim_id;
  insert into claim_lines (claim_id, expense_date, category, client_code, amount, description) values
    (v_claim_id, '2026-08-24', 'conveyance', 'Vasai Polymers', 275, 'Site visit for tax assessment');
  insert into approval_log (claim_id, action, actor_id, at) values
    (v_claim_id, 'submitted', v_emp_id, '2026-08-25'),
    (v_claim_id, 'approved', v_head_id, '2026-08-27');

  -- ---- SUBMITTED, awaiting approval (3) ----

  -- TEST-EMP-02 / August / submitted
  select employee_id into v_emp_id from employees where employee_code = 'TEST-EMP-02';
  insert into claims (employee_id, month, status, submitted_at)
    values (v_emp_id, '2026-08', 'submitted', '2026-09-21')
    returning claim_id into v_claim_id;
  insert into claim_lines (claim_id, expense_date, category, client_code, amount, description) values
    (v_claim_id, '2026-08-12', 'conveyance', 'GMJ', 250, 'Local travel'),
    (v_claim_id, '2026-08-14', 'out_of_station', 'Girnar Ceramics', 3400, 'Out-of-station stock verification');
  insert into approval_log (claim_id, action, actor_id, at) values (v_claim_id, 'submitted', v_emp_id, '2026-09-21');

  -- TEST-EMP-03 / September / submitted
  select employee_id into v_emp_id from employees where employee_code = 'TEST-EMP-03';
  insert into claims (employee_id, month, status, submitted_at)
    values (v_emp_id, '2026-09', 'submitted', '2026-09-22')
    returning claim_id into v_claim_id;
  insert into claim_lines (claim_id, expense_date, category, client_code, amount, description) values
    (v_claim_id, '2026-09-20', 'out_of_station', 'Sahyadri Agro Exports', 2800, 'Inventory count, out of town');
  insert into approval_log (claim_id, action, actor_id, at) values (v_claim_id, 'submitted', v_emp_id, '2026-09-22');

  -- TEST-EMP-05 / September / submitted
  select employee_id into v_emp_id from employees where employee_code = 'TEST-EMP-05';
  insert into claims (employee_id, month, status, submitted_at)
    values (v_emp_id, '2026-09', 'submitted', '2026-09-23')
    returning claim_id into v_claim_id;
  insert into claim_lines (claim_id, expense_date, category, client_code, amount, description) values
    (v_claim_id, '2026-09-21', 'conveyance', 'GMJ', 220, 'Local conveyance');
  insert into approval_log (claim_id, action, actor_id, at) values (v_claim_id, 'submitted', v_emp_id, '2026-09-23');

  -- ---- REJECTED then back in Draft, with history (2) ----

  -- TEST-EMP-01 / August / rejected, sitting in Draft with a reason
  select employee_id into v_emp_id from employees where employee_code = 'TEST-EMP-01';
  select head_employee_id into v_head_id from teams where team_name = 'Audit & Assurance (TEST)';
  insert into claims (employee_id, month, status, rejection_reason)
    values (v_emp_id, '2026-08', 'draft', 'Client code missing on the boarding & lodging line — please add before resubmitting')
    returning claim_id into v_claim_id;
  insert into claim_lines (claim_id, expense_date, category, client_code, amount, description, rejection_flag, rejection_note) values
    (v_claim_id, '2026-08-05', 'conveyance', 'GMJ', 180, 'Local travel', false, null),
    (v_claim_id, '2026-08-06', 'boarding_lodging', null, 1900, 'Overnight stay', true, 'Client code missing');
  insert into approval_log (claim_id, action, actor_id, at, note) values
    (v_claim_id, 'submitted', v_emp_id, '2026-08-08', null),
    (v_claim_id, 'rejected', v_head_id, '2026-08-09', 'Client code missing on the boarding & lodging line — please add before resubmitting');

  -- TEST-EMP-05 / August / rejected, sitting in Draft with a reason
  select employee_id into v_emp_id from employees where employee_code = 'TEST-EMP-05';
  select head_employee_id into v_head_id from teams where team_name = 'Direct Tax (TEST)';
  insert into claims (employee_id, month, status, rejection_reason)
    values (v_emp_id, '2026-08', 'draft', 'Receipt not attached for the out-of-station line — please attach before resubmitting')
    returning claim_id into v_claim_id;
  insert into claim_lines (claim_id, expense_date, category, client_code, amount, description, rejection_flag, rejection_note) values
    (v_claim_id, '2026-08-18', 'out_of_station', 'GMJ', 4200, 'Client site visit', true, 'Receipt not attached');
  insert into approval_log (claim_id, action, actor_id, at, note) values
    (v_claim_id, 'submitted', v_emp_id, '2026-08-19', null),
    (v_claim_id, 'rejected', v_head_id, '2026-08-20', 'Receipt not attached for the out-of-station line — please attach before resubmitting');

  -- ---- Plain DRAFT, never submitted (1) ----

  select employee_id into v_emp_id from employees where employee_code = 'TEST-EMP-04';
  insert into claims (employee_id, month, status)
    values (v_emp_id, '2026-09', 'draft')
    returning claim_id into v_claim_id;
  insert into claim_lines (claim_id, expense_date, category, client_code, amount, other_label, description) values
    (v_claim_id, '2026-09-15', 'other', 'GMJ', 150, 'Courier', 'Document courier to client office');

end $$;
