-- Fixes from the v0.1 audit. Mirrors the rules enforced in the app (src/data/store.tsx).

alter table expenses
  add column attachment_name text,
  add column no_image_reason text,
  add column rcm_rate_pct numeric(5,2),
  add column rcm_tax numeric(14,2) not null default 0,
  add column resubmitted_at timestamptz,
  -- every bill needs a photo/file, or a stated reason why not
  add constraint expenses_evidence check (drive_file_id is not null or attachment_name is not null or no_image_reason is not null),
  add constraint expenses_discount check (discount >= 0 and discount <= gross_amount),
  add constraint expenses_total check (total_amount > 0);

alter table payments add column posted_at timestamptz;

-- Payments: no future dates, no locked months, never more than the balance due.
create or replace function enforce_payment_rules() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  v_due numeric;
begin
  if new.paid_on > current_date then raise exception 'Payment date cannot be in the future'; end if;
  if exists (select 1 from month_locks where client_id = new.client_id and month = date_trunc('month', new.paid_on)::date) then
    raise exception 'Payment date falls in a locked month';
  end if;
  select e.total_amount - e.tds_amount - coalesce((select sum(p.amount) from payments p where p.expense_id = e.id), 0)
    into v_due from expenses e where e.id = new.expense_id and e.status <> 'rejected';
  if v_due is null then raise exception 'Expense not found or returned'; end if;
  if new.amount > v_due + 0.01 then raise exception 'Amount is more than the balance due (%)', v_due; end if;
  return new;
end $$;
create trigger payments_rules before insert on payments for each row execute function enforce_payment_rules();

-- Approval needs a balanced bill (round-off up to ₹1) and an expense head.
create or replace function guard_approval_balance() returns trigger
language plpgsql as $$
begin
  if new.status = 'approved' and old.status is distinct from 'approved' then
    if abs(new.total_amount - new.taxable_value - new.cgst - new.sgst - new.igst) > 1 then
      raise exception 'Taxable + GST differs from bill total by more than ₹1';
    end if;
    if new.head_id is null then raise exception 'Expense head required'; end if;
    if new.rcm_applicable and coalesce(new.rcm_tax, 0) <= 0 then raise exception 'RCM GST amount required'; end if;
  end if;
  return new;
end $$;
create trigger expenses_approval_balance before update on expenses for each row execute function guard_approval_balance();

-- Resubmission: the creator (or an admin) may edit a RETURNED entry and send it back.
-- Replaces the earlier rule that blocked every sub-user update after submission.
create or replace function enforce_expense_rules() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  v_window int;
begin
  if exists (select 1 from month_locks
             where client_id = new.client_id and month = date_trunc('month', new.invoice_date)::date) then
    raise exception 'Month % is locked', to_char(new.invoice_date, 'Mon YYYY');
  end if;
  if new.invoice_date > current_date then raise exception 'Bill date cannot be in the future'; end if;
  select backdate_window_days into v_window from clients where id = new.client_id;
  new.is_backdated := new.invoice_date < (current_date - v_window)
                      and new.invoice_date < date_trunc('month', current_date)::date;
  if app_role() = 'sub_user' then
    if tg_op = 'INSERT' and new.is_backdated then
      raise exception 'Past-dated entries can only be added by your admin';
    end if;
    if tg_op = 'UPDATE' then
      if old.status <> 'rejected' or old.created_by <> auth.uid() then
        raise exception 'Only your own returned entries can be changed';
      end if;
      if new.invoice_date <> old.invoice_date and new.is_backdated then
        raise exception 'Past-dated entries can only be added by your admin';
      end if;
      if new.status not in ('submitted', 'rejected') then raise exception 'Not allowed'; end if;
    end if;
  end if;
  new.updated_at := now();
  return new;
end $$;

-- TDS challans: BSR code is 7 digits; one row per challan.
alter table tds_challans
  add constraint tds_challans_bsr check (bsr_code ~ '^[0-9]{7}$'),
  add constraint tds_challans_unique unique (client_id, bsr_code, challan_no, paid_on);

-- Users can be deactivated (profiles.active already exists); vendor names unique per client.
create unique index vendors_name_unique on vendors (client_id, lower(name));
