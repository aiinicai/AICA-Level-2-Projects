-- v0.3: payments can settle several bills, be split across modes/dates, and leave vendor advances.
-- Mirrors src/data/store.tsx (recordPayment / applyAdvance / voidPayment) and src/lib/alerts.ts.

-- Client policies & bank accounts
alter table clients
  add column cash_ledger text not null default 'Cash',
  add column default_credit_days int not null default 30 check (default_credit_days between 0 and 365),
  add column cash_limit_per_day numeric(14,2) not null default 10000,   -- to be confirmed under the Income-tax Act 2025
  add column note_above_amount numeric(14,2) not null default 25000;

create table bank_accounts (
  id           uuid primary key default gen_random_uuid(),
  client_id    uuid not null references clients(id),
  name         text not null,
  tally_ledger text not null,
  active       boolean not null default true
);
alter table bank_accounts enable row level security;
create policy bank_accounts_rw on bank_accounts for all using (can_see_client(client_id)) with check (can_see_client(client_id) and app_role() in ('super_admin','client_admin'));

-- Vendor terms & Tally name
alter table vendors
  add column credit_days int check (credit_days between 0 and 365),
  add column tally_ledger text;

-- Look-alike confirmation on bills
alter table expenses add column not_duplicate_of uuid references expenses(id);

-- Payments: one row per payment (mode/date/account); allocations say which bills it settles.
alter table payments drop column expense_id cascade;
alter table payments
  add column vendor_id uuid not null references vendors(id),
  add column account_id uuid references bank_accounts(id),
  add column flags text[] not null default '{}',
  add column source text not null default 'manual' check (source in ('manual','bank_import'));
alter table payments drop constraint if exists payments_mode_check;
alter table payments add constraint payments_mode_check check (mode in ('cash','upi','bank','cheque','card'));
alter table payments add constraint payments_account_for_non_cash check (mode = 'cash' or account_id is not null);

create table payment_allocations (
  payment_id uuid not null references payments(id) on delete cascade,
  expense_id uuid not null references expenses(id),
  amount     numeric(14,2) not null check (amount > 0),
  primary key (payment_id, expense_id)
);
alter table payment_allocations enable row level security;
create policy payment_allocations_rw on payment_allocations for all
  using (exists (select 1 from payments p where p.id = payment_id and can_see_client(p.client_id)))
  with check (exists (select 1 from payments p where p.id = payment_id and can_see_client(p.client_id)));

-- Balance helpers
create or replace function expense_balance(e uuid) returns numeric language sql stable as $$
  select x.total_amount - x.tds_amount - coalesce((select sum(a.amount) from payment_allocations a where a.expense_id = x.id), 0)
  from expenses x where x.id = e $$;

create or replace function payment_unallocated(p uuid) returns numeric language sql stable as $$
  select y.amount - coalesce((select sum(a.amount) from payment_allocations a where a.payment_id = y.id), 0)
  from payments y where y.id = p $$;

-- The old per-payment trigger checked a single bill; replace with allocation-level checks.
drop trigger if exists payments_rules on payments;
create or replace function enforce_payment_rules() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.paid_on > current_date then raise exception 'Payment date cannot be in the future'; end if;
  if exists (select 1 from month_locks where client_id = new.client_id and month = date_trunc('month', new.paid_on)::date) then
    raise exception 'Payment date falls in a locked month';
  end if;
  return new;
end $$;
create trigger payments_rules before insert on payments for each row execute function enforce_payment_rules();

create or replace function enforce_allocation_rules() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  v_pay payments%rowtype;
  v_exp expenses%rowtype;
begin
  select * into v_pay from payments where id = new.payment_id;
  select * into v_exp from expenses where id = new.expense_id;
  if v_exp.vendor_id <> v_pay.vendor_id then raise exception 'A selected bill belongs to another vendor'; end if;
  if v_exp.status in ('rejected','draft') then raise exception 'Bill is not active — fix it first'; end if;
  if new.amount > expense_balance(new.expense_id) + 0.01 then raise exception 'More than the bill balance'; end if;
  if new.amount > payment_unallocated(new.payment_id) + 0.01 then raise exception 'Amounts applied to bills are more than the payment'; end if;
  return new;
end $$;
create trigger payment_allocations_rules before insert on payment_allocations for each row execute function enforce_allocation_rules();

-- Voiding: only admins, only before Tally posting (audit trigger on payments records the deletion)
create policy payments_void on payments for delete
  using (can_see_client(client_id) and app_role() in ('super_admin','client_admin') and posted_at is null);

-- Challans: CIN + receipt, and the deposit cannot be before the TDS month
alter table tds_challans
  add column cin text,
  add column file_name text,
  add constraint tds_challans_serial check (challan_no ~ '^[0-9]{5}$'),
  add constraint tds_challans_after_month check (paid_on >= month);
