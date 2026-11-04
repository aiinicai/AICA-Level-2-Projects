-- v0.13 — credit / debit notes received from vendors (CGST Act s.34). Mirrors src/lib/vendorNotes.ts.
-- Credit note: we owe less and its GST reduces ITC. Debit note: we owe more. Linked to the bill it corrects, or kept at
-- vendor level until linked. Matched with GSTR-2B CDNR. Only admins record them; posted notes cannot be changed.

create table vendor_notes (
  id            uuid primary key default gen_random_uuid(),
  client_id     uuid not null references clients(id),
  fy_label      text not null,
  vendor_id     uuid not null references vendors(id),
  kind          text not null check (kind in ('credit', 'debit')),
  note_no       text not null check (length(trim(note_no)) > 0),
  note_date     date not null,
  expense_id    uuid references expenses(id),
  reason        text not null check (reason in ('return', 'rate', 'discount', 'deficiency', 'other')),
  head_id       uuid references expense_heads(id),
  taxable_value numeric(14,2) not null default 0,
  cgst          numeric(14,2) not null default 0,
  sgst          numeric(14,2) not null default 0,
  igst          numeric(14,2) not null default 0,
  total_amount  numeric(14,2) not null check (total_amount > 0),
  itc_eligible  boolean not null default false,
  flags         text[] not null default '{}',
  remark        text check (char_length(remark) <= 250),
  document_id   uuid references documents(id),
  status        text not null default 'active' check (status in ('active', 'void')),
  void_reason   text,
  posted_at     timestamptz,
  created_by    uuid not null references profiles(id) default auth.uid(),
  created_at    timestamptz not null default now(),
  check (abs(taxable_value + cgst + sgst + igst - total_amount) <= 1),
  check (cgst = sgst),
  check (igst = 0 or cgst + sgst = 0),
  check (expense_id is not null or head_id is not null)
);
create unique index vendor_notes_no on vendor_notes (client_id, vendor_id, kind, fy_label, upper(regexp_replace(note_no, '[\s/\\._-]', '', 'g'))) where status = 'active';
alter table vendor_notes enable row level security;
create policy vendor_notes_select on vendor_notes for select using (can_see_client(client_id));
create policy vendor_notes_insert on vendor_notes for insert with check (can_see_client(client_id) and app_role() in ('super_admin', 'client_admin'));
create policy vendor_notes_update on vendor_notes for update using (can_see_client(client_id) and app_role() in ('super_admin', 'client_admin'))
  with check (can_see_client(client_id) and app_role() in ('super_admin', 'client_admin'));
create trigger audit_vendor_notes after insert or update or delete on vendor_notes for each row execute function audit_trigger();

create or replace function expense_note_adjust(e uuid) returns numeric language sql stable as $$
  select coalesce(sum(case when kind = 'debit' then total_amount else -total_amount end), 0) from vendor_notes where expense_id = e and status = 'active' $$;

-- balance now also counts notes on the bill (see 0010 for the TDS-on-advance terms)
create or replace function expense_balance(e uuid) returns numeric language sql stable as $$
  select x.total_amount + expense_note_adjust(x.id) - expense_paid(x.id) - expense_tds_credit(x.id) - greatest(0, x.tds_amount - expense_tds_credit(x.id))
  from expenses x where x.id = e $$;

-- payments: the balance check counts notes too (same function as 0010 with the note term added)
create or replace function enforce_allocation_rules() returns trigger
language plpgsql security definer set search_path = public as $$
declare v_pay payments%rowtype; v_exp expenses%rowtype; v_cr numeric;
begin
  select * into v_exp from expenses where id = new.expense_id for update;   -- lock the bill
  select * into v_pay from payments where id = new.payment_id for update;   -- lock the payment
  if v_exp.vendor_id <> v_pay.vendor_id then raise exception 'A selected bill belongs to another vendor'; end if;
  if v_exp.status in ('rejected','draft') then raise exception 'Bill is not active — fix it first'; end if;
  if new.amount > payment_unallocated(new.payment_id) + 0.01 then raise exception 'Amounts applied to bills are more than the payment'; end if;
  if new.tds_credit > 0 then
    if new.tds_credit > payment_unused_tds(new.payment_id) + 0.01 then raise exception 'More TDS credit than was deducted on the advance'; end if;
    if v_exp.posted_at is not null and v_exp.tds_amount > 0 then
      raise exception 'This bill is already in Tally with its own TDS — the CA must adjust the advance TDS in Tally';
    end if;
  end if;
  v_cr := expense_tds_credit(new.expense_id) + new.tds_credit;
  if v_exp.total_amount + expense_note_adjust(new.expense_id) - expense_paid(new.expense_id) - new.amount - v_cr - greatest(0, v_exp.tds_amount - v_cr) < -0.01 then
    raise exception 'More than the bill balance';
  end if;
  if exists (select 1 from month_locks where client_id = v_pay.client_id and month = date_trunc('month', v_pay.paid_on)::date) then
    raise exception 'Payment date falls in a locked month';
  end if;
  return new;
end $$;

create or replace function enforce_note_rules() returns trigger language plpgsql security definer set search_path = public as $$
declare v_exp expenses%rowtype; v_room numeric;
begin
  if tg_op = 'UPDATE' and old.posted_at is not null and (to_jsonb(new) - 'posted_at') is distinct from (to_jsonb(old) - 'posted_at') then
    raise exception 'Already posted to Tally — reverse it in Tally and ask the CA';
  end if;
  if tg_op = 'UPDATE' and old.status = 'void' then raise exception 'A cancelled note cannot be changed'; end if;
  if new.note_date > ist_today() then raise exception 'Date cannot be in the future'; end if;
  if exists (select 1 from month_locks where client_id = new.client_id and month = date_trunc('month', new.note_date)::date) and (tg_op = 'INSERT' or new.status = old.status) then
    raise exception 'This month is locked. Ask your admin.';
  end if;
  if new.expense_id is not null and new.status = 'active' then
    select * into v_exp from expenses where id = new.expense_id for update;
    if v_exp.vendor_id <> new.vendor_id then raise exception 'The bill belongs to another vendor'; end if;
    if v_exp.status in ('rejected', 'draft') then raise exception 'Choose an active bill'; end if;
    if new.note_date < v_exp.invoice_date then raise exception 'A note cannot be dated before the bill it corrects'; end if;
    new.itc_eligible := coalesce(v_exp.itc_eligible, false);                 -- ITC follows the bill
    if v_exp.tds_amount > 0 and not ('tds_on_original' = any(new.flags)) then new.flags := new.flags || 'tds_on_original'; end if;
    if new.kind = 'credit' then
      v_room := v_exp.total_amount + coalesce((select sum(case when kind = 'debit' then total_amount else -total_amount end) from vendor_notes
                 where expense_id = new.expense_id and status = 'active' and id <> new.id), 0);
      if new.total_amount > v_room + 0.01 then raise exception 'Credit notes cannot exceed the bill value'; end if;
    end if;
  end if;
  return new;
end $$;
create trigger vendor_notes_rules before insert or update on vendor_notes for each row execute function enforce_note_rules();
