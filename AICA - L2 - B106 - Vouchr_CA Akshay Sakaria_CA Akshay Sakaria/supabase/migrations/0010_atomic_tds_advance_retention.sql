-- v0.11 — mirrors src/data/store.tsx and src/lib/tdsAdvance.ts.
--  A. Bill fields added in the app on 2 Nov 2026 (travel-portal non-GST part, section 9(5)).
--  B. TDS on advances (Income-tax Act 2025 s.393: credit or payment, whichever is earlier).
--  C. One write path for payments (AUDIT-v0.4 A1/A2): record_payment(lines) and apply_advance() run in ONE transaction;
--     users can no longer insert payments / allocations directly.
--  D. Bill + its document saved together (A2): save_bill_document(); staged Drive files that never got a bill are listed
--     for the nightly drive-cleanup function.
--  E. DPDP Rules: security and audit logs are kept for at least one year and cannot be changed by users.
--  F. WhatsApp number check by one-time code sent FROM the number (stronger than self-confirmation).

-- ---------------------------------------------------------------- A. aggregator / 9(5) bills
alter table expenses
  add column if not exists non_taxable_amount numeric(14,2) not null default 0 check (non_taxable_amount >= 0), -- printed charges without GST (fare collected for an airline / IRCTC)
  add column if not exists eco_pays_tax boolean not null default false,  -- s.9(5): GST paid by the e-commerce operator
  add column if not exists eco_gstin text;

create or replace function guard_approval_balance() returns trigger
language plpgsql as $$
begin
  if new.status = 'approved' and old.status is distinct from 'approved' then
    if abs(new.total_amount - new.taxable_value - new.non_taxable_amount - new.cgst - new.sgst - new.igst) > 1 then
      raise exception 'Taxable + GST differs from bill total by more than ₹1';
    end if;
    if new.head_id is null then raise exception 'Expense head required'; end if;
    if new.rcm_applicable and coalesce(new.rcm_tax, 0) <= 0 then raise exception 'RCM GST amount required'; end if;
    if new.eco_pays_tax and new.rcm_applicable then raise exception 'Section 9(5) bill: GST is paid by the operator — no reverse charge'; end if;
  end if;
  return new;
end $$;

-- A WhatsApp / bulk draft has no amount until a person completes it (the webhook saves total 0 when AI is off).
alter table expenses drop constraint if exists expenses_total;
alter table expenses add constraint expenses_total check (status = 'draft' or total_amount > 0);

-- ---------------------------------------------------------------- B. TDS on advances
alter table payments
  add column if not exists tds_code     text references tds_rates(code),
  add column if not exists tds_rate_pct numeric(5,2),
  add column if not exists tds_amount   numeric(14,2) not null default 0 check (tds_amount >= 0),
  add column if not exists tds_base     numeric(14,2);                         -- amount credited to the vendor (cash + TDS)
alter table payment_allocations
  add column if not exists tds_credit numeric(14,2) not null default 0 check (tds_credit >= 0); -- advance TDS carried to this bill

create or replace function expense_paid(e uuid) returns numeric language sql stable as $$
  select coalesce(sum(amount), 0) from payment_allocations where expense_id = e $$;
create or replace function expense_tds_credit(e uuid) returns numeric language sql stable as $$
  select coalesce(sum(tds_credit), 0) from payment_allocations where expense_id = e $$;

-- balance = total − cash paid − TDS deducted on applied advances − TDS still to deduct on the bill
create or replace function expense_balance(e uuid) returns numeric language sql stable as $$
  select x.total_amount - expense_paid(x.id) - expense_tds_credit(x.id) - greatest(0, x.tds_amount - expense_tds_credit(x.id))
  from expenses x where x.id = e $$;

create or replace function payment_unused_tds(p uuid) returns numeric language sql stable as $$
  select y.tds_amount - coalesce((select sum(a.tds_credit) from payment_allocations a where a.payment_id = y.id), 0)
  from payments y where y.id = p $$;

create or replace function gross_up_tds(net numeric, rate numeric) returns numeric language sql immutable as $$
  select case when rate > 0 and rate < 100 then round(net * rate / (100 - rate), 2) else 0 end $$;

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
  if v_exp.total_amount - expense_paid(new.expense_id) - new.amount - v_cr - greatest(0, v_exp.tds_amount - v_cr) < -0.01 then
    raise exception 'More than the bill balance';
  end if;
  if exists (select 1 from month_locks where client_id = v_pay.client_id and month = date_trunc('month', v_pay.paid_on)::date) then
    raise exception 'Payment date falls in a locked month';
  end if;
  return new;
end $$;

-- ---------------------------------------------------------------- C. one write path for payments
drop policy if exists payments_insert on payments;
drop policy if exists payment_allocations_rw on payment_allocations;
create policy payment_allocations_read on payment_allocations for select
  using (exists (select 1 from payments p where p.id = payment_id and can_see_client(p.client_id)));
-- (no insert policy: allocations and payments are created only by the functions below)

-- Users may only mark a payment posted to Tally; amounts, dates, vendor and TDS change only through a void + new payment.
create or replace function guard_payment_update() returns trigger language plpgsql as $$
begin
  if coalesce(app_role(), 'service') <> 'service' and coalesce(current_setting('vouchr.system_update', true), '') <> 'on'
     and (to_jsonb(new) - 'posted_at') is distinct from (to_jsonb(old) - 'posted_at') then
    raise exception 'A saved payment cannot be changed — cancel it and record it again';
  end if;
  return new;
end $$;
create trigger payments_update_guard before update on payments for each row execute function guard_payment_update();

-- lines: [{ "mode", "account_id", "ref", "paid_on", "amount", "allocations": [{ "expense_id", "amount" }], "tds_code"? }]
-- tds_code on a line = deduct TDS on the part of that line not applied to bills; the rate is taken from the masters here,
-- never from the phone (no-PAN / inoperative PAN → no-PAN rate).
create or replace function record_payment(p_client uuid, p_vendor uuid, p_lines jsonb, p_source text default 'manual')
returns uuid[] language plpgsql security definer set search_path = public as $$
declare
  ln jsonb; al jsonb; v_id uuid; v_ids uuid[] := '{}'; v_left numeric; v_rate tds_rates%rowtype; v_pct numeric; v_tds numeric;
  v_vendor vendors%rowtype;
begin
  if not can_see_client(p_client) then raise exception 'Not allowed for this client'; end if;
  select * into v_vendor from vendors where id = p_vendor and client_id = p_client;
  if not found then raise exception 'Vendor not found'; end if;
  if jsonb_array_length(coalesce(p_lines, '[]')) = 0 then raise exception 'Enter the amount paid'; end if;
  for ln in select * from jsonb_array_elements(p_lines) loop
    v_rate := null; v_pct := null; v_tds := 0; v_left := null;
    if coalesce(ln->>'tds_code', '') <> '' then
      -- advance part = this line less what it applies to bills (the allocation trigger checks those amounts)
      v_left := (ln->>'amount')::numeric - coalesce((select sum((a->>'amount')::numeric) from jsonb_array_elements(coalesce(ln->'allocations', '[]')) a), 0);
      if v_left <= 0 then raise exception 'TDS on advance applies only to the part not applied to bills'; end if;
      select * into v_rate from tds_rates where code = ln->>'tds_code'
        and effective_from <= (ln->>'paid_on')::date and (effective_to is null or effective_to >= (ln->>'paid_on')::date);
      if not found then raise exception 'This TDS section is not in the tax masters.'; end if;
      v_pct := case when (v_vendor.pan is null or v_vendor.pan_status = 'Inoperative') and v_rate.no_pan_rate_pct is not null then v_rate.no_pan_rate_pct else v_rate.rate_pct end;
      v_tds := gross_up_tds(v_left, v_pct);
    end if;
    insert into payments (client_id, vendor_id, mode, account_id, bank_ref, paid_on, amount, source, tds_code, tds_rate_pct, tds_amount, tds_base)
    values (p_client, p_vendor, ln->>'mode', nullif(ln->>'account_id', '')::uuid, nullif(ln->>'ref', ''), (ln->>'paid_on')::date, (ln->>'amount')::numeric, p_source,
            v_rate.code, v_pct, v_tds, case when v_tds > 0 then v_left + v_tds end)
    returning id into v_id;
    for al in select * from jsonb_array_elements(coalesce(ln->'allocations', '[]')) loop
      insert into payment_allocations (payment_id, expense_id, amount) values (v_id, (al->>'expense_id')::uuid, (al->>'amount')::numeric);
    end loop;
    v_ids := v_ids || v_id;
  end loop;
  return v_ids;  -- any error above rolls back every line: no half-saved payment
end $$;

-- Apply an advance to a bill. The TDS credit is worked out here from the advance's own TDS.
create or replace function apply_advance(p_payment uuid, p_expense uuid, p_amount numeric)
returns numeric language plpgsql security definer set search_path = public as $$
declare v_pay payments%rowtype; v_exp expenses%rowtype; v_credit numeric := 0; v_flags text[];
begin
  select * into v_pay from payments where id = p_payment for update;
  if not found or not can_see_client(v_pay.client_id) then raise exception 'Payment not found'; end if;
  select * into v_exp from expenses where id = p_expense;
  if v_pay.tds_amount > 0 then
    v_credit := least(gross_up_tds(p_amount, v_pay.tds_rate_pct), payment_unused_tds(p_payment));
  end if;
  insert into payment_allocations (payment_id, expense_id, amount, tds_credit) values (p_payment, p_expense, round(p_amount, 2), v_credit);
  if v_credit > 0 and v_exp.tds_code is not null and v_exp.tds_code <> v_pay.tds_code then
    -- carried so TDS is not deducted twice, but marked: the section differs and the CA must check the rate / return entry
    v_flags := array(select distinct unnest(v_pay.flags || array['adv_tds_section_differs']));
    perform set_config('vouchr.system_update', 'on', true);  -- this transaction only; lets the guard accept the flag
    update payments set flags = v_flags where id = p_payment;
    perform set_config('vouchr.system_update', '', true);
  end if;
  return v_credit;
end $$;

revoke all on function record_payment(uuid, uuid, jsonb, text) from public;
revoke all on function apply_advance(uuid, uuid, numeric) from public;
grant execute on function record_payment(uuid, uuid, jsonb, text) to authenticated;
grant execute on function apply_advance(uuid, uuid, numeric) to authenticated;

-- ---------------------------------------------------------------- D. bill + document together
alter table documents add column if not exists staged boolean not null default true; -- true until a record uses it

-- Saves the document row and the bill in one transaction. The Drive file is uploaded first (to the right folder);
-- if this fails, the document stays staged and drive-cleanup removes the file after 24 hours.
create or replace function save_bill_document(p_doc jsonb, p_bill jsonb)
returns uuid language plpgsql security definer set search_path = public as $$
declare v_doc uuid; v_bill uuid; v_client uuid := (p_bill->>'client_id')::uuid; v_j jsonb; v_cols text;
begin
  if not can_see_client(v_client) then raise exception 'Not allowed for this client'; end if;
  if coalesce(p_bill->>'status', 'submitted') not in ('draft', 'submitted') then raise exception 'A new bill is saved as draft or submitted'; end if;
  if p_doc is not null then
    -- drive-upload normally recorded it already (staged); otherwise record it now
    select id into v_doc from documents where client_id = v_client and drive_file_id = p_doc->>'drive_file_id';
    if v_doc is null then
      insert into documents (client_id, fy_label, kind, drive_file_id, drive_path, web_view_link, sha256, staged)
      values (v_client, p_bill->>'fy_label', 'Bills', p_doc->>'drive_file_id', p_doc->>'drive_path', p_doc->>'web_view_link', p_doc->>'sha256', false)
      returning id into v_doc;
    end if;
  end if;
  v_j := (p_bill - 'created_by' - 'created_at' - 'updated_at' - 'reviewed_by' - 'reviewed_at' - 'posted_at')
         || jsonb_strip_nulls(jsonb_build_object('document_id', v_doc, 'drive_file_id', p_doc->>'drive_file_id'));
  -- only the columns sent: the others keep their table defaults (jsonb_populate_record alone would set them to null)
  select string_agg(quote_ident(k), ', ') into v_cols from jsonb_object_keys(v_j) k
   where k in (select column_name from information_schema.columns where table_schema = 'public' and table_name = 'expenses');
  execute format('insert into expenses (%1$s) select %1$s from jsonb_populate_record(null::expenses, $1) returning id', v_cols) using v_j into v_bill;
  return v_bill;
end $$;
revoke all on function save_bill_document(jsonb, jsonb) from public;
grant execute on function save_bill_document(jsonb, jsonb) to authenticated;

-- Any bill / challan that points at a document (by id or by Drive file id) takes it out of staging.
create or replace function attach_document() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.document_id is null and tg_table_name = 'expenses' and to_jsonb(new)->>'drive_file_id' is not null then
    select id into new.document_id from documents where client_id = new.client_id and drive_file_id = new.drive_file_id;
  end if;
  if new.document_id is not null then update documents set staged = false where id = new.document_id and staged; end if;
  return new;
end $$;
create trigger expenses_attach_document before insert or update of document_id, drive_file_id on expenses for each row execute function attach_document();
create trigger challans_attach_document before insert or update of document_id on tds_challans for each row execute function attach_document();

-- Files uploaded but never attached to a record (the save failed or the phone went away).
create or replace view orphan_documents as
select d.* from documents d
where d.staged and d.uploaded_at < now() - interval '24 hours'
  and not exists (select 1 from expenses e where e.document_id = d.id)
  and not exists (select 1 from tds_challans c where c.document_id = d.id);

-- ---------------------------------------------------------------- E. log retention (DPDP Rules: at least one year)
create or replace function guard_log_retention() returns trigger language plpgsql as $$
begin
  if tg_op = 'UPDATE' then raise exception 'Logs cannot be changed'; end if;
  if old.at > now() - interval '1 year' then raise exception 'Logs must be kept for at least one year'; end if;
  return old;
end $$;
create trigger audit_log_retention before update or delete on audit_log for each row execute function guard_log_retention();
create trigger system_events_retention before update or delete on system_events for each row execute function guard_log_retention();

create or replace function guard_received_retention() returns trigger language plpgsql as $$
begin
  if tg_op = 'UPDATE' then raise exception 'Logs cannot be changed'; end if;
  if old.received_at > now() - interval '1 year' then raise exception 'Logs must be kept for at least one year'; end if;
  return old;
end $$;
create trigger whatsapp_messages_retention before update or delete on whatsapp_messages for each row execute function guard_received_retention();
revoke update, delete on audit_log, system_events, whatsapp_messages from authenticated, anon;

-- ---------------------------------------------------------------- F. WhatsApp one-time code
alter table profiles
  add column if not exists whatsapp_code_hash text,         -- sha256 of the code; the code itself is never stored
  add column if not exists whatsapp_code_expires timestamptz,
  add column if not exists whatsapp_code_tries int not null default 0;

-- The signed-in user asks for a code; they send "VERIFY <code>" from their WhatsApp to the firm number. The webhook
-- (service role) checks it and sets whatsapp_verified_at. Users cannot set whatsapp_verified_at themselves.
create or replace function start_whatsapp_verification() returns text
language plpgsql security definer set search_path = public as $$
-- 6 digits from a cryptographically random uuid (the first 8 hex digits of a v4 uuid are random)
declare v_code text := lpad(((('x' || substr(replace(gen_random_uuid()::text, '-', ''), 1, 8))::bit(32)::bigint % 1000000))::text, 6, '0');
begin
  if not exists (select 1 from profiles where id = auth.uid() and whatsapp_number is not null) then
    raise exception 'No WhatsApp number on your account';
  end if;
  update profiles set whatsapp_code_hash = encode(sha256(convert_to(v_code, 'UTF8')), 'hex'), whatsapp_code_expires = now() + interval '15 minutes',
    whatsapp_code_tries = 0, whatsapp_verified_at = null where id = auth.uid();
  return v_code;
end $$;
revoke all on function start_whatsapp_verification() from public;
grant execute on function start_whatsapp_verification() to authenticated;

create or replace function guard_profile_whatsapp() returns trigger language plpgsql as $$
begin
  if coalesce(app_role(), 'service') <> 'service' then
    if new.whatsapp_verified_at is not null and new.whatsapp_verified_at is distinct from old.whatsapp_verified_at then
      raise exception 'A WhatsApp number is confirmed only by the code sent from that number';
    end if;
    if new.whatsapp_number is distinct from old.whatsapp_number then new.whatsapp_verified_at := null; end if;
  end if;
  return new;
end $$;
create trigger profiles_whatsapp_guard before update on profiles for each row execute function guard_profile_whatsapp();

alter table whatsapp_messages drop constraint if exists whatsapp_messages_status_check;
alter table whatsapp_messages add constraint whatsapp_messages_status_check check (status in ('draft_created', 'duplicate', 'unknown_sender', 'no_consent',
  'unsupported', 'too_large', 'error', 'number_verified', 'verify_failed'));
