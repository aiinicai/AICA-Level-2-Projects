-- v0.4 audit hardening (critical findings A12, B1–B4, F1, F5).

-- A12: business dates are Indian dates. current_date on Supabase is UTC, so between 00:00 and 05:30 IST
-- the server is still on "yesterday" → valid bills dated today were rejected as future, and month/backdate
-- checks were off by a day around month-end.
create or replace function ist_today() returns date language sql stable as $$ select (now() at time zone 'Asia/Kolkata')::date $$;

create or replace function enforce_expense_rules() returns trigger
language plpgsql security definer set search_path = public as $$
declare v_window int;
begin
  if exists (select 1 from month_locks where client_id = new.client_id and month = date_trunc('month', new.invoice_date)::date) then
    raise exception 'Month % is locked', to_char(new.invoice_date, 'Mon YYYY');
  end if;
  if new.invoice_date > ist_today() then raise exception 'Bill date cannot be in the future'; end if;
  select backdate_window_days into v_window from clients where id = new.client_id;
  new.is_backdated := new.invoice_date < (ist_today() - v_window) and new.invoice_date < date_trunc('month', ist_today())::date;
  -- B4: after CA approval only the CA firm may change a bill (client admins could otherwise alter approved amounts)
  if tg_op = 'UPDATE' and old.status in ('approved','posted') and app_role() <> 'super_admin' then
    raise exception 'Approved bills can only be changed by the CA firm';
  end if;
  if app_role() = 'sub_user' then
    if tg_op = 'INSERT' and new.is_backdated then raise exception 'Past-dated entries can only be added by your admin'; end if;
    if tg_op = 'UPDATE' then
      if old.status not in ('rejected','draft') or old.created_by <> auth.uid() then raise exception 'Only your own returned entries can be changed'; end if;
      if new.invoice_date <> old.invoice_date and new.is_backdated then raise exception 'Past-dated entries can only be added by your admin'; end if;
      if new.status not in ('submitted','rejected','draft') then raise exception 'Not allowed'; end if;
    end if;
  end if;
  new.updated_at := now();
  return new;
end $$;

create or replace function enforce_payment_rules() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.paid_on > ist_today() then raise exception 'Payment date cannot be in the future'; end if;
  if exists (select 1 from month_locks where client_id = new.client_id and month = date_trunc('month', new.paid_on)::date) then
    raise exception 'Payment date falls in a locked month';
  end if;
  new.is_backdated := new.paid_on < ist_today();
  return new;
end $$;
drop trigger if exists payments_flag on payments;

-- B2: "for all" policies let staff DELETE bills, payments and vendors. Split by command:
-- everyone in the client reads & inserts; updates go through the rule triggers; deletes are not allowed
-- (corrections are reversals / voids, kept in the audit trail).
do $$
declare t text;
begin
  foreach t in array array['vendors','expenses','payments','tds_challans','gstr2b_lines','fiscal_years'] loop
    execute format('drop policy if exists %1$s_rw on %1$s', t);
    execute format('create policy %1$s_select on %1$s for select using (can_see_client(client_id))', t);
    execute format('create policy %1$s_insert on %1$s for insert with check (can_see_client(client_id))', t);
    execute format('create policy %1$s_update on %1$s for update using (can_see_client(client_id)) with check (can_see_client(client_id))', t);
  end loop;
end $$;
-- drafts may be discarded by their creator; nothing else is deletable by users
create policy expenses_delete_draft on expenses for delete using (status = 'draft' and created_by = auth.uid());
-- payment void stays admin-only and pre-Tally (policy payments_void from 0004)

-- B1: client admins could update ANY column of their client (e.g. raise the backdate window or the cash
-- limit to switch off controls). Only branding, Tally company and sources/projects are theirs to change.
create or replace function guard_client_update() returns trigger language plpgsql as $$
begin
  if app_role() <> 'super_admin' and (
       new.backdate_window_days is distinct from old.backdate_window_days
    or new.cash_limit_per_day is distinct from old.cash_limit_per_day
    or new.note_above_amount is distinct from old.note_above_amount
    or new.gstin is distinct from old.gstin or new.pan is distinct from old.pan or new.name is distinct from old.name
    or new.tally_mode is distinct from old.tally_mode) then
    raise exception 'Only the CA firm can change control settings';
  end if;
  return new;
end $$;
create trigger clients_guard before update on clients for each row execute function guard_client_update();

-- B3: verification results drive the TDS rate (inoperative PAN → higher rate). Only the CA firm or the
-- verification API (service role) may set them.
create or replace function guard_vendor_status() returns trigger language plpgsql as $$
begin
  if coalesce(app_role(), 'service') not in ('super_admin','service') and (
       (tg_op = 'INSERT' and (coalesce(new.pan_status, 'Unverified') <> 'Unverified' or new.gstin_status is not null))
    or (tg_op = 'UPDATE' and (new.pan_status is distinct from old.pan_status or new.gstin_status is distinct from old.gstin_status))) then
    raise exception 'PAN / GSTIN status can only be set by the CA firm or the verification service';
  end if;
  return new;
end $$;
create trigger vendors_status_guard before insert or update on vendors for each row execute function guard_vendor_status();

-- F1: two people paying the same bill at the same moment could both pass the balance check.
-- Serialise allocations per bill with a row lock.
create or replace function enforce_allocation_rules() returns trigger
language plpgsql security definer set search_path = public as $$
declare v_pay payments%rowtype; v_exp expenses%rowtype;
begin
  select * into v_exp from expenses where id = new.expense_id for update;   -- lock the bill
  select * into v_pay from payments where id = new.payment_id for update;   -- lock the payment
  if v_exp.vendor_id <> v_pay.vendor_id then raise exception 'A selected bill belongs to another vendor'; end if;
  if v_exp.status in ('rejected','draft') then raise exception 'Bill is not active — fix it first'; end if;
  if new.amount > expense_balance(new.expense_id) + 0.01 then raise exception 'More than the bill balance'; end if;
  if new.amount > payment_unallocated(new.payment_id) + 0.01 then raise exception 'Amounts applied to bills are more than the payment'; end if;
  if exists (select 1 from month_locks where client_id = v_pay.client_id and month = date_trunc('month', v_pay.paid_on)::date) then
    raise exception 'Payment date falls in a locked month';
  end if;
  return new;
end $$;

-- F5: when the CA returns (rejects) a bill that was already paid, its payments become vendor advances
-- instead of silently pointing at a dead bill.
create or replace function release_allocations_on_reject() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.status = 'rejected' and old.status <> 'rejected' then
    delete from payment_allocations where expense_id = new.id;
  end if;
  return new;
end $$;
create trigger expenses_release_on_reject after update on expenses for each row execute function release_allocations_on_reject();
