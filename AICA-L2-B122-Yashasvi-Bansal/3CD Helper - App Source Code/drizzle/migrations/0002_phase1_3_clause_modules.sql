-- 3CD Helper – Phase 1, 2 and 3 clause modules (Clauses 18, 20(b), 21(b), 21(d), 22, 23, 26, 31, 34, 35 + Form 3CD questionnaire)
-- Apply once, as one migration, after 0000_init_3cd_helper and 0001_lock_trigger_functions.

-- ===== 20261122000000_phase1_clauses_31_21d_22_26_20b.sql
-- =====================================================================
-- 3CD Helper – Phase 1 clause modules
--   Clause 31  : loans / deposits / specified sums (269SS, 269T) and 269ST receipts & payments
--   Clause 21(d): cash payments u/s 40A(3) / 40A(3A)
--   Clause 22  : MSME payments (section 15 MSMED Act, 43B(h))
--   Clause 26  : sums covered by section 43B
--   Clause 20(b): employees' contributions u/s 36(1)(va)
-- All tables are firm-scoped and protected by RLS (writes only while the year is not locked).
-- Calculations are done in the app (src/lib/clauses/*) so they can be unit-tested.
-- =====================================================================

-- ---------- generic helpers ----------
create or replace function public.derive_firm_id_from_engagement()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  select firm_id into new.firm_id from public.engagements where id = new.engagement_id;
  if new.firm_id is null then raise exception 'Assessment year not found'; end if;
  return new;
end;
$$;

-- Field-level edit history for any table (skips bookkeeping columns)
create or replace function public.log_row_changes()
returns trigger language plpgsql security definer set search_path = public as $$
declare
  o jsonb := to_jsonb(old) - 'updated_at' - 'updated_by' - 'created_at' - 'created_by';
  n jsonb := to_jsonb(new) - 'updated_at' - 'updated_by' - 'created_at' - 'created_by';
  k text;
begin
  for k in select jsonb_object_keys(n) loop
    if (o -> k) is distinct from (n -> k) then
      insert into public.row_history (firm_id, table_name, record_id, field, old_value, new_value, changed_by)
      values (new.firm_id, tg_table_name, new.id, k, o ->> k, n ->> k, auth.uid());
    end if;
  end loop;
  return new;
end;
$$;

-- ---------- party master: extra attributes used by these clauses ----------
alter table public.party_master add column if not exists address text;
alter table public.party_master add column if not exists msme_category text
  check (msme_category in ('micro','small','medium','none'));
alter table public.party_master add column if not exists udyam_no text;
alter table public.party_master add column if not exists msme_trader boolean not null default false;
alter table public.party_master add column if not exists agreed_credit_days integer
  check (agreed_credit_days is null or agreed_credit_days between 0 and 365);
alter table public.party_master add column if not exists is_exempt_lender boolean not null default false;
alter table public.party_master add column if not exists is_transporter boolean not null default false;

-- ---------- engagement level settings ----------
alter table public.engagements add column if not exists return_due_date date;      -- due date u/s 139(1)
alter table public.engagements add column if not exists msme_bank_rate numeric(6,3); -- RBI bank rate % for MSMED s.16 interest
alter table public.engagements add column if not exists clause_answers jsonb not null default '{}'::jsonb; -- yes/no answers & overrides per clause

-- ---------- Clause 31: loans, deposits, specified sums ----------
create table if not exists public.loan_balances (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  engagement_id uuid not null references public.engagements(id) on delete cascade,
  party_name text not null,
  normalized_name text not null,
  -- positive = amount payable by the assessee (loan/deposit taken); negative = receivable (loan given)
  opening_balance numeric(18,2) not null default 0,
  created_by uuid default auth.uid(), created_at timestamptz not null default now(),
  updated_by uuid, updated_at timestamptz not null default now(),
  unique (engagement_id, normalized_name)
);

create table if not exists public.loan_txns (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  engagement_id uuid not null references public.engagements(id) on delete cascade,
  upload_id uuid references public.uploads(id) on delete cascade,
  row_no integer,
  txn_date date,
  voucher_no text,
  party_name text not null,
  normalized_name text not null,
  pan text,
  -- taken / repaid            : loan or deposit taken by the assessee and its repayment (31(a), 31(c))
  -- specified_taken / specified_repaid : specified sum / specified advance (31(b), 31(c))
  -- given / repayment_received : loan given by the assessee and its repayment received (31(d), 31(e))
  kind text not null check (kind in ('taken','repaid','specified_taken','specified_repaid','given','repayment_received','interest')),
  amount numeric(18,2) not null check (amount >= 0),
  mode text not null default 'electronic'
    check (mode in ('cash','non_ac_payee_cheque','ac_payee_cheque','electronic','journal','transfer','other')),
  nature_code text check (nature_code in ('A','B','C','D','E','F','G','H','I','J','K','L')),
  include boolean not null default true,
  remark text,
  created_by uuid default auth.uid(), created_at timestamptz not null default now(),
  updated_by uuid, updated_at timestamptz not null default now()
);
create index if not exists loan_txns_eng_idx on public.loan_txns(engagement_id, normalized_name, txn_date);

-- ---------- Clause 21(d) & 31(ba)-(bd): cash / non-account-payee movements ----------
create table if not exists public.cash_txns (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  engagement_id uuid not null references public.engagements(id) on delete cascade,
  upload_id uuid references public.uploads(id) on delete cascade,
  row_no integer,
  txn_date date not null,
  voucher_no text,
  direction text not null check (direction in ('payment','receipt')),
  party_name text not null,
  normalized_name text not null,
  pan text,
  nature text,                       -- expense head / nature of transaction
  amount numeric(18,2) not null check (amount >= 0),
  mode text not null default 'cash' check (mode in ('cash','non_ac_payee_cheque','ac_payee_cheque','electronic','other')),
  -- for payments: how 40A(3) treats it
  section text not null default '40A3' check (section in ('40A3','40A3A','capital','not_expenditure')),
  rule_6dd text,                     -- exception under rule 6DD, if any
  include boolean not null default true,
  remark text,
  created_by uuid default auth.uid(), created_at timestamptz not null default now(),
  updated_by uuid, updated_at timestamptz not null default now()
);
create index if not exists cash_txns_eng_idx on public.cash_txns(engagement_id, direction, txn_date);

-- ---------- Clause 26: sums covered by section 43B ----------
create table if not exists public.statutory_dues (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  engagement_id uuid not null references public.engagements(id) on delete cascade,
  upload_id uuid references public.uploads(id) on delete cascade,
  row_no integer,
  section_clause text not null check (section_clause in ('a','b','c','d','da','e','f','g','h')),
  nature text not null,
  pre_existing boolean not null default false,   -- liability existed on 1st day of PY and was not allowed earlier
  amount numeric(18,2) not null check (amount >= 0),
  paid_amount numeric(18,2) not null default 0 check (paid_amount >= 0),
  paid_date date,
  include boolean not null default true,
  remark text,
  created_by uuid default auth.uid(), created_at timestamptz not null default now(),
  updated_by uuid, updated_at timestamptz not null default now()
);

-- ---------- Clause 20(b): employees' contributions ----------
create table if not exists public.employee_contributions (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  engagement_id uuid not null references public.engagements(id) on delete cascade,
  upload_id uuid references public.uploads(id) on delete cascade,
  row_no integer,
  fund text not null,                 -- e.g. Provident Fund, ESI, Superannuation, any other fund
  wage_month date not null,           -- first day of the month for which wages were paid
  amount_received numeric(18,2) not null check (amount_received >= 0),
  due_date date,                      -- defaults to 15th of following month when blank
  amount_paid numeric(18,2) not null default 0 check (amount_paid >= 0),
  paid_date date,
  include boolean not null default true,
  remark text,
  created_by uuid default auth.uid(), created_at timestamptz not null default now(),
  updated_by uuid, updated_at timestamptz not null default now()
);

-- ---------- Clause 22: bills of micro / small enterprises ----------
create table if not exists public.msme_bills (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  engagement_id uuid not null references public.engagements(id) on delete cascade,
  upload_id uuid references public.uploads(id) on delete cascade,
  row_no integer,
  party_name text not null,
  normalized_name text not null,
  bill_no text,
  bill_date date not null,
  acceptance_date date,               -- date of acceptance / deemed acceptance (defaults to bill date)
  amount numeric(18,2) not null check (amount >= 0),
  paid_amount numeric(18,2) not null default 0 check (paid_amount >= 0),
  paid_date date,                     -- date of (last) payment
  include boolean not null default true,
  remark text,
  created_by uuid default auth.uid(), created_at timestamptz not null default now(),
  updated_by uuid, updated_at timestamptz not null default now()
);
create index if not exists msme_bills_eng_idx on public.msme_bills(engagement_id, normalized_name);

-- ---------- triggers: audit fields, firm_id from engagement, history ----------
do $$
declare t text;
begin
  foreach t in array array['loan_balances','loan_txns','cash_txns','statutory_dues','employee_contributions','msme_bills']
  loop
    execute format('drop trigger if exists trg_audit on public.%I', t);
    execute format('create trigger trg_audit before insert or update on public.%I for each row execute function public.set_audit_fields()', t);
    execute format('drop trigger if exists trg_derive_firm on public.%I', t);
    execute format('create trigger trg_derive_firm before insert on public.%I for each row execute function public.derive_firm_id_from_engagement()', t);
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists %1$s_select on public.%1$I', t);
    execute format('create policy %1$s_select on public.%1$I for select to authenticated using (public.is_firm_member(firm_id))', t);
    execute format('drop policy if exists %1$s_insert on public.%1$I', t);
    execute format('create policy %1$s_insert on public.%1$I for insert to authenticated with check (public.engagement_editable(engagement_id))', t);
    execute format('drop policy if exists %1$s_update on public.%1$I', t);
    execute format('create policy %1$s_update on public.%1$I for update to authenticated using (public.engagement_editable(engagement_id)) with check (public.engagement_editable(engagement_id))', t);
    execute format('drop policy if exists %1$s_delete on public.%1$I', t);
    execute format('create policy %1$s_delete on public.%1$I for delete to authenticated using (public.engagement_editable(engagement_id))', t);
    execute format('drop trigger if exists trg_history on public.%I', t);
    execute format('create trigger trg_history after update on public.%I for each row execute function public.log_row_changes()', t);
  end loop;
end $$;

-- ===== 20261123000000_phase2_clauses_34_21b_23_18.sql
-- =====================================================================
-- 3CD Helper – Phase 2 clause modules
--   Clause 34 / 21(b): TDS-TCS compliance and 40(a)(i)/(ia) disallowance
--   Clause 23       : payments to persons specified u/s 40A(2)(b)
--   Clause 18       : depreciation as per the Income-tax Act (block of assets)
-- plus party-master extras (related party, MSME activity) and challan details for PF/ESI.
-- =====================================================================

alter table public.party_master add column if not exists is_related boolean not null default false;
alter table public.party_master add column if not exists relationship text;
alter table public.party_master add column if not exists msme_activity text;   -- Manufacturing / Services / Trading (from Udyam / Tally)

alter table public.employee_contributions add column if not exists source text;      -- manual / ECR / challan / IP-wise file
alter table public.employee_contributions add column if not exists challan_ref text;  -- TRRN / challan number

-- ---------- Clause 34 / 21(b): payments as per books (subject to TDS) ----------
create table if not exists public.tds_payments (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  engagement_id uuid not null references public.engagements(id) on delete cascade,
  upload_id uuid references public.uploads(id) on delete cascade,
  row_no integer,
  txn_date date,
  party_name text not null,
  normalized_name text not null,
  pan text,
  section text not null,                 -- 192, 194A, 194C, 194H, 194I(a), 194I(b), 194J, 194Q, 195 ...
  nature text,
  amount numeric(18,2) not null default 0,
  resident boolean not null default true,
  tds_required text not null default 'auto' check (tds_required in ('auto','yes','no')),
  include boolean not null default true,
  remark text,
  created_by uuid default auth.uid(), created_at timestamptz not null default now(),
  updated_by uuid, updated_at timestamptz not null default now()
);
create index if not exists tds_payments_eng_idx on public.tds_payments(engagement_id, section, normalized_name);

-- ---------- Clause 34: deductee-wise details from TDS / TCS returns ----------
create table if not exists public.tds_deductions (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  engagement_id uuid not null references public.engagements(id) on delete cascade,
  upload_id uuid references public.uploads(id) on delete cascade,
  row_no integer,
  tan text,
  form_type text,                        -- 24Q / 26Q / 27Q / 27EQ
  section text not null,
  party_name text not null,
  normalized_name text not null,
  pan text,
  txn_date date,                          -- date of payment / credit
  amount_paid numeric(18,2) not null default 0,
  tds_amount numeric(18,2) not null default 0,
  deduction_date date,
  deposit_date date,
  lower_rate boolean not null default false,   -- lower / nil deduction certificate or non-PAN etc.
  include boolean not null default true,
  remark text,
  created_by uuid default auth.uid(), created_at timestamptz not null default now(),
  updated_by uuid, updated_at timestamptz not null default now()
);
create index if not exists tds_deductions_eng_idx on public.tds_deductions(engagement_id, section, normalized_name);

-- ---------- Clause 34(b): statements (returns) furnished ----------
create table if not exists public.tds_returns (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  engagement_id uuid not null references public.engagements(id) on delete cascade,
  upload_id uuid references public.uploads(id) on delete cascade,
  row_no integer,
  tan text,
  form_type text not null check (form_type in ('24Q','26Q','27Q','27EQ')),
  quarter text not null check (quarter in ('Q1','Q2','Q3','Q4')),
  due_date date,
  filed_date date,
  all_info text not null default 'Yes' check (all_info in ('Yes','No')),
  interest_paid numeric(18,2) not null default 0,
  interest_paid_date date,
  include boolean not null default true,
  remark text,
  created_by uuid default auth.uid(), created_at timestamptz not null default now(),
  updated_by uuid, updated_at timestamptz not null default now()
);

-- ---------- Clause 23: payments to related persons ----------
create table if not exists public.related_txns (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  engagement_id uuid not null references public.engagements(id) on delete cascade,
  upload_id uuid references public.uploads(id) on delete cascade,
  row_no integer,
  party_name text not null,
  normalized_name text not null,
  pan text,
  relationship text,
  nature text,
  amount numeric(18,2) not null default 0,
  source text not null default 'manual' check (source in ('manual','clause44','clause31','import')),
  include boolean not null default true,
  remark text,
  created_by uuid default auth.uid(), created_at timestamptz not null default now(),
  updated_by uuid, updated_at timestamptz not null default now()
);

-- ---------- Clause 18: blocks of assets and movements ----------
create table if not exists public.fa_blocks (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  engagement_id uuid not null references public.engagements(id) on delete cascade,
  block_name text not null,
  rate numeric(6,2) not null check (rate >= 0 and rate <= 100),
  opening_wdv numeric(18,2) not null default 0,
  include boolean not null default true,
  remark text,
  created_by uuid default auth.uid(), created_at timestamptz not null default now(),
  updated_by uuid, updated_at timestamptz not null default now(),
  unique (engagement_id, block_name)
);

create table if not exists public.fa_movements (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  engagement_id uuid not null references public.engagements(id) on delete cascade,
  upload_id uuid references public.uploads(id) on delete cascade,
  row_no integer,
  block_name text not null,
  description text,
  movement text not null default 'addition' check (movement in ('addition','deletion')),
  txn_date date,                           -- date put to use (addition) / date of sale (deletion)
  amount numeric(18,2) not null default 0, -- cost (addition) / sale proceeds (deletion)
  cenvat numeric(18,2) not null default 0,
  forex numeric(18,2) not null default 0,
  subsidy numeric(18,2) not null default 0,
  additional_dep boolean not null default false,  -- s.32(1)(iia) new plant & machinery
  include boolean not null default true,
  remark text,
  created_by uuid default auth.uid(), created_at timestamptz not null default now(),
  updated_by uuid, updated_at timestamptz not null default now()
);

do $$
declare t text;
begin
  foreach t in array array['tds_payments','tds_deductions','tds_returns','related_txns','fa_blocks','fa_movements']
  loop
    execute format('drop trigger if exists trg_audit on public.%I', t);
    execute format('create trigger trg_audit before insert or update on public.%I for each row execute function public.set_audit_fields()', t);
    execute format('drop trigger if exists trg_derive_firm on public.%I', t);
    execute format('create trigger trg_derive_firm before insert on public.%I for each row execute function public.derive_firm_id_from_engagement()', t);
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists %1$s_select on public.%1$I', t);
    execute format('create policy %1$s_select on public.%1$I for select to authenticated using (public.is_firm_member(firm_id))', t);
    execute format('drop policy if exists %1$s_insert on public.%1$I', t);
    execute format('create policy %1$s_insert on public.%1$I for insert to authenticated with check (public.engagement_editable(engagement_id))', t);
    execute format('drop policy if exists %1$s_update on public.%1$I', t);
    execute format('create policy %1$s_update on public.%1$I for update to authenticated using (public.engagement_editable(engagement_id)) with check (public.engagement_editable(engagement_id))', t);
    execute format('drop policy if exists %1$s_delete on public.%1$I', t);
    execute format('create policy %1$s_delete on public.%1$I for delete to authenticated using (public.engagement_editable(engagement_id))', t);
    execute format('drop trigger if exists trg_history on public.%I', t);
    execute format('create trigger trg_history after update on public.%I for each row execute function public.log_row_changes()', t);
  end loop;
end $$;

-- ===== 20261124000000_phase3_declarations_stock_fa_bills.sql
-- =====================================================================
-- 3CD Helper – Phase 3
--   TDS declarations / certificates (194C(6), 197, 15G/15H, exempt, 10F/TRC, 206AB etc.)
--   File attachments for any record (declarations, purchase bills of fixed assets ...)
--   Clause 35 quantitative details of stock (trading / raw material / finished goods / by-products)
--   Clause 18: depreciation booked by the client (book vs Income-tax), purchase bill matching
-- =====================================================================

-- ---------- TDS declarations and certificates ----------
create table if not exists public.tds_declarations (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  engagement_id uuid not null references public.engagements(id) on delete cascade,
  party_name text not null,
  normalized_name text not null,
  pan text,
  decl_type text not null check (decl_type in
    ('194C6_transporter','197_certificate','15G','15H','exempt_entity','10F_TRC','206AA_no_pan','other')),
  section text,                         -- section the declaration / certificate applies to (194C, 194A, 194J, 195 ...)
  cert_no text,                         -- 197 certificate no. / 15G-15H UIN / TRC no.
  valid_from date,
  valid_to date,
  rate numeric(6,3),                    -- lower / nil rate as per 197 certificate (or DTAA rate for 195)
  limit_amount numeric(18,2),           -- amount up to which the 197 certificate applies
  vehicles integer,                     -- 194C(6): number of goods carriages owned (must be ≤ 10)
  received_date date,
  storage_path text,                    -- file in the private 'uploads' bucket
  file_name text,
  verified boolean not null default false,
  include boolean not null default true,
  remark text,
  created_by uuid default auth.uid(), created_at timestamptz not null default now(),
  updated_by uuid, updated_at timestamptz not null default now()
);
create index if not exists tds_declarations_eng_idx on public.tds_declarations(engagement_id, normalized_name);

-- ---------- Generic attachments (purchase bills, certificates, working papers) ----------
create table if not exists public.attachments (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  engagement_id uuid not null references public.engagements(id) on delete cascade,
  entity text not null,                 -- 'fa_bill', 'tds_declaration', 'stock', 'clause' ...
  record_id uuid,                       -- linked row (fa_movements.id, tds_declarations.id ...)
  party_name text,
  kind text,
  file_name text not null,
  storage_path text not null,
  extracted jsonb not null default '{}'::jsonb,   -- invoice no/date, GSTIN, taxable, GST, total read from the bill
  include boolean not null default true,
  remark text,
  created_by uuid default auth.uid(), created_at timestamptz not null default now(),
  updated_by uuid, updated_at timestamptz not null default now()
);
create index if not exists attachments_eng_idx on public.attachments(engagement_id, entity, record_id);

-- ---------- Clause 35: quantitative details ----------
create table if not exists public.stock_items (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  engagement_id uuid not null references public.engagements(id) on delete cascade,
  upload_id uuid references public.uploads(id) on delete cascade,
  row_no integer,
  category text not null default 'trading' check (category in ('trading','raw_material','finished','by_product')),
  item_name text not null,
  unit text,
  opening_qty numeric(18,3) not null default 0,
  purchase_qty numeric(18,3) not null default 0,
  manufactured_qty numeric(18,3) not null default 0,  -- finished goods / by-products produced
  consumption_qty numeric(18,3) not null default 0,   -- raw material consumed
  sales_qty numeric(18,3) not null default 0,
  closing_qty numeric(18,3) not null default 0,       -- as per physical / books
  shortage_qty numeric(18,3) not null default 0,      -- explained shortage / excess (+excess, -shortage handled in app)
  closing_value numeric(18,2),
  include boolean not null default true,
  remark text,
  created_by uuid default auth.uid(), created_at timestamptz not null default now(),
  updated_by uuid, updated_at timestamptz not null default now()
);
create index if not exists stock_items_eng_idx on public.stock_items(engagement_id, category);

-- ---------- Clause 18: book depreciation & bill links ----------
alter table public.fa_blocks add column if not exists book_depreciation numeric(18,2);   -- depreciation booked in accounts for this block
alter table public.fa_movements add column if not exists ledger_name text;              -- Tally / books ledger it came from
alter table public.fa_movements add column if not exists bill_no text;
alter table public.fa_movements add column if not exists bill_date date;
alter table public.fa_movements add column if not exists supplier text;
alter table public.fa_movements add column if not exists gst_amount numeric(18,2);
alter table public.fa_movements drop constraint if exists fa_movements_movement_check;
alter table public.fa_movements add constraint fa_movements_movement_check
  check (movement in ('addition','deletion','book_depreciation'));

-- ledger → block mapping remembered per client (so next year's import maps automatically)
create table if not exists public.fa_ledger_map (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  engagement_id uuid not null references public.engagements(id) on delete cascade,
  ledger_name text not null,
  block_name text,                      -- null = ignore this ledger
  include boolean not null default true,
  remark text,
  created_by uuid default auth.uid(), created_at timestamptz not null default now(),
  updated_by uuid, updated_at timestamptz not null default now(),
  unique (engagement_id, ledger_name)
);

do $$
declare t text;
begin
  foreach t in array array['tds_declarations','attachments','stock_items','fa_ledger_map']
  loop
    execute format('drop trigger if exists trg_audit on public.%I', t);
    execute format('create trigger trg_audit before insert or update on public.%I for each row execute function public.set_audit_fields()', t);
    execute format('drop trigger if exists trg_derive_firm on public.%I', t);
    execute format('create trigger trg_derive_firm before insert on public.%I for each row execute function public.derive_firm_id_from_engagement()', t);
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists %1$s_select on public.%1$I', t);
    execute format('create policy %1$s_select on public.%1$I for select to authenticated using (public.is_firm_member(firm_id))', t);
    execute format('drop policy if exists %1$s_insert on public.%1$I', t);
    execute format('create policy %1$s_insert on public.%1$I for insert to authenticated with check (public.engagement_editable(engagement_id))', t);
    execute format('drop policy if exists %1$s_update on public.%1$I', t);
    execute format('create policy %1$s_update on public.%1$I for update to authenticated using (public.engagement_editable(engagement_id)) with check (public.engagement_editable(engagement_id))', t);
    execute format('drop policy if exists %1$s_delete on public.%1$I', t);
    execute format('create policy %1$s_delete on public.%1$I for delete to authenticated using (public.engagement_editable(engagement_id))', t);
    execute format('drop trigger if exists trg_history on public.%I', t);
    execute format('create trigger trg_history after update on public.%I for each row execute function public.log_row_changes()', t);
  end loop;
end $$;

-- ===== privileges (same pattern as the init migration)
grant select, insert, update, delete on public.loan_balances, public.loan_txns, public.cash_txns, public.statutory_dues, public.employee_contributions, public.msme_bills,
  public.tds_payments, public.tds_deductions, public.tds_returns, public.related_txns, public.fa_blocks, public.fa_movements,
  public.tds_declarations, public.attachments, public.stock_items, public.fa_ledger_map to authenticated;
grant all on public.loan_balances, public.loan_txns, public.cash_txns, public.statutory_dues, public.employee_contributions, public.msme_bills,
  public.tds_payments, public.tds_deductions, public.tds_returns, public.related_txns, public.fa_blocks, public.fa_movements,
  public.tds_declarations, public.attachments, public.stock_items, public.fa_ledger_map to service_role;
revoke execute on function public.derive_firm_id_from_engagement() from public, anon, authenticated;
revoke execute on function public.log_row_changes() from public, anon, authenticated;

-- ===== fix: a corrected GSTIN in the party master also fixes rows whose own GSTIN is invalid
create or replace function public.reclassify_engagement(p_eng uuid)
returns integer language plpgsql security invoker set search_path = public as $$
declare v_count int;
begin
  if not public.engagement_editable(p_eng) then
    return 0;
  end if;
  with x as (
    select e.id,
      -- a valid GSTIN on the entry wins; otherwise a valid GSTIN from the party master
      -- (so correcting a GSTIN once in the party master fixes all entries of that party)
      case
        when public.gstin_is_valid(e.gstin) then upper(trim(e.gstin))
        when public.gstin_is_valid(pm.gstin) then upper(trim(pm.gstin))
        else coalesce(nullif(upper(trim(e.gstin)),''), nullif(upper(trim(pm.gstin)),''))
      end as eg,
      coalesce(pm.is_exempt,false) as ex,
      coalesce(pm.is_composition,false) as co
    from public.expense_rows e
    join public.engagements en on en.id = e.engagement_id
    left join public.party_master pm on pm.client_id = en.client_id and pm.normalized_name = e.normalized_name
    where e.engagement_id = p_eng
  ), y as (
    select id, eg,
      case when eg is null then 'blank' when public.gstin_is_valid(eg) then 'valid' else 'invalid' end as st,
      ex, co
    from x
  )
  update public.expense_rows e set
    effective_gstin = y.eg,
    gstin_status = y.st,
    category = coalesce(e.category_override,
      case when y.st <> 'valid' then 'unregistered'
           when y.ex then 'exempt'
           when y.co then 'composition'
           else 'other_registered' end)
  from y
  where e.id = y.id
    and (e.effective_gstin is distinct from y.eg or e.gstin_status is distinct from y.st
         or e.category is distinct from coalesce(e.category_override,
            case when y.st <> 'valid' then 'unregistered' when y.ex then 'exempt'
                 when y.co then 'composition' else 'other_registered' end));
  get diagnostics v_count = row_count;
  return v_count;
end;
$$;