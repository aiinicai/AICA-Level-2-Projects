-- Vouchr core schema
-- Tenancy: one row in `clients` per client business. Super admins (CA firm) see all clients.
-- Invoice images/PDFs are NOT stored here; only their Google Drive file ids.

create extension if not exists pgcrypto;

-- ---------- Tenancy & users ----------
create table clients (
  id            uuid primary key default gen_random_uuid(),
  name          text not null,
  gstin         text,
  pan           text,
  state_code    char(2),
  logo_url      text,
  brand_color   text default '#0f2a44',
  tally_mode    text not null default 'xml_file' check (tally_mode in ('none','xml_file','bridge')),
  tally_company text,
  drive_folder_id text,
  sheet_id      text,
  backdate_window_days int not null default 0,   -- sub-user expense entries older than this need admin
  created_at    timestamptz not null default now()
);

create table profiles (
  id         uuid primary key references auth.users(id) on delete cascade,
  full_name  text not null,
  role       text not null check (role in ('super_admin','client_admin','sub_user')),
  client_id  uuid references clients(id),        -- null for super_admin
  language   text not null default 'en' check (language in ('en','hi')),
  active     boolean not null default true,
  created_at timestamptz not null default now(),
  check (role = 'super_admin' or client_id is not null)
);

create or replace function app_role() returns text
language sql stable security definer set search_path = public as
$$ select role from profiles where id = auth.uid() and active $$;

create or replace function app_client() returns uuid
language sql stable security definer set search_path = public as
$$ select client_id from profiles where id = auth.uid() and active $$;

create or replace function can_see_client(c uuid) returns boolean
language sql stable as
$$ select app_role() = 'super_admin' or app_client() = c $$;

-- ---------- Financial years & month locks ----------
create table fiscal_years (
  id        uuid primary key default gen_random_uuid(),
  client_id uuid not null references clients(id),
  label     text not null,                       -- '2026-27'
  starts_on date not null,
  ends_on   date not null,
  unique (client_id, label)
);

create table month_locks (
  client_id uuid not null references clients(id),
  month     date not null,                       -- first day of month
  locked_by uuid references profiles(id),
  locked_at timestamptz not null default now(),
  reason    text,
  primary key (client_id, month)
);

-- ---------- Vendors ----------
create table vendors (
  id             uuid primary key default gen_random_uuid(),
  client_id      uuid not null references clients(id),
  name           text not null,
  gstin          text,
  gst_registered boolean not null default false,
  gstin_status   text,                            -- Active / Cancelled / Suspended (from API)
  gstin_checked_at timestamptz,
  pan            text,
  pan_entity_type text,                           -- from PAN 4th character
  pan_status     text,                            -- Operative / Inoperative / Unverified
  pan_checked_at timestamptz,
  state_code     char(2),
  default_head_id uuid,
  ldc_rate       numeric(5,2),                    -- lower deduction certificate rate, if any
  ldc_valid_to   date,
  created_at     timestamptz not null default now(),
  unique (client_id, gstin)
);

-- ---------- Masters (platform-wide, edited by super admin only) ----------
create table expense_heads (
  id         uuid primary key default gen_random_uuid(),
  name       text not null unique,
  tally_ledger text,
  keywords   text[] not null default '{}',
  sac_hsn_prefixes text[] not null default '{}',
  default_tds_code text,
  blocked_17_5 boolean not null default false,
  rcm_code   text
);

create table tds_rates (
  code        text primary key,                    -- e.g. 'CONTRACT_IND'
  description text not null,
  act_reference text,                               -- e.g. 'Sec 393(1)' — filled by CA
  rate_pct    numeric(5,2) not null,
  threshold_single numeric(14,2),
  threshold_aggregate numeric(14,2),
  applies_to_entity text[],                         -- PAN 4th chars; null = all
  no_pan_rate_pct numeric(5,2),
  effective_from date not null,
  effective_to date,
  verified    boolean not null default false,       -- CA has confirmed against the Act
  verified_by uuid references profiles(id),
  verified_at timestamptz,
  source_note text
);

create table rcm_rules (
  code        text primary key,
  description text not null,
  supplier_condition text not null,                 -- e.g. 'unregistered', 'any'
  recipient_condition text,
  notification_ref text,
  verified    boolean not null default false,
  source_note text
);

create table blocked_credit_rules (
  code        text primary key,
  description text not null,
  keywords    text[] not null default '{}',
  verified    boolean not null default false
);

-- ---------- Expenses ----------
create table expenses (
  id             uuid primary key default gen_random_uuid(),
  client_id      uuid not null references clients(id),
  fy_label       text not null,
  vendor_id      uuid references vendors(id),
  invoice_no     text,
  invoice_date   date not null,
  entry_source   text not null default 'photo' check (entry_source in ('photo','qr','manual','pdf')),
  irn            text,
  drive_file_id  text,
  image_sha256   text,
  hsn_sac        text,
  gross_amount   numeric(14,2) not null default 0,  -- before discount
  discount       numeric(14,2) not null default 0,
  taxable_value  numeric(14,2) not null default 0,
  cgst           numeric(14,2) not null default 0,
  sgst           numeric(14,2) not null default 0,
  igst           numeric(14,2) not null default 0,
  cess           numeric(14,2) not null default 0,
  total_amount   numeric(14,2) not null default 0,
  head_id        uuid references expense_heads(id),
  head_confidence numeric(4,3),
  tds_code       text references tds_rates(code),
  tds_rate_pct   numeric(5,2),
  tds_amount     numeric(14,2) not null default 0,
  rcm_applicable boolean not null default false,
  rcm_code       text references rcm_rules(code),
  itc_eligible   boolean,
  blocked_code   text references blocked_credit_rules(code),
  status         text not null default 'submitted'
                 check (status in ('draft','submitted','approved','rejected','posted')),
  review_note    text,
  reviewed_by    uuid references profiles(id),
  reviewed_at    timestamptz,
  posted_at      timestamptz,
  tally_batch_id uuid,
  is_backdated   boolean not null default false,
  created_by     uuid not null references profiles(id) default auth.uid(),
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);
create unique index expenses_dup_invoice on expenses (client_id, vendor_id, lower(invoice_no), fy_label)
  where invoice_no is not null and status <> 'rejected';
create index expenses_dup_image on expenses (client_id, image_sha256);
create index expenses_client_date on expenses (client_id, invoice_date);

create table payments (
  id          uuid primary key default gen_random_uuid(),
  client_id   uuid not null references clients(id),
  expense_id  uuid not null references expenses(id) on delete cascade,
  mode        text not null check (mode in ('cash','bank')),
  bank_ref    text,
  paid_on     date not null,
  amount      numeric(14,2) not null check (amount > 0),
  is_backdated boolean not null default false,      -- paid_on < entry date -> flagged for audit
  created_by  uuid not null references profiles(id) default auth.uid(),
  created_at  timestamptz not null default now()
);

-- ---------- TDS challans ----------
create table tds_challans (
  id          uuid primary key default gen_random_uuid(),
  client_id   uuid not null references clients(id),
  month       date not null,
  amount      numeric(14,2) not null,
  bsr_code    text,
  challan_no  text,
  paid_on     date,
  created_at  timestamptz not null default now()
);

-- ---------- GST reconciliation ----------
create table gstr2b_lines (
  id          uuid primary key default gen_random_uuid(),
  client_id   uuid not null references clients(id),
  return_period text not null,                      -- 'MMYYYY'
  source      text not null check (source in ('2A','2B')),
  supplier_gstin text not null,
  invoice_no  text not null,
  invoice_date date,
  taxable_value numeric(14,2),
  igst numeric(14,2), cgst numeric(14,2), sgst numeric(14,2), cess numeric(14,2),
  fetched_via text not null default 'gsp' check (fetched_via in ('gsp','json_upload')),
  matched_expense_id uuid references expenses(id),
  match_status text not null default 'unmatched'
               check (match_status in ('matched','mismatch','unmatched','missing_in_books')),
  created_at timestamptz not null default now()
);

-- ---------- Notifications ----------
create table notifications (
  id         uuid primary key default gen_random_uuid(),
  client_id  uuid references clients(id),
  user_id    uuid references profiles(id),
  kind       text not null,  -- gst_reco, tds_due, challan_missing, payment_overdue_30, itc_180, consent_expiry, compliance_change
  title      text not null,
  body       text,
  due_on     date,
  read_at    timestamptz,
  created_at timestamptz not null default now()
);

-- ---------- Audit trail (who changed what) ----------
create table audit_log (
  id         bigserial primary key,
  client_id  uuid,
  actor      uuid,
  table_name text not null,
  row_id     uuid,
  action     text not null,
  flag       text,                                  -- e.g. 'backdated_payment'
  before     jsonb,
  after      jsonb,
  at         timestamptz not null default now()
);

create or replace function audit_trigger() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  v_flag text;
begin
  -- read through jsonb: vendors / tds_rates have no is_backdated column, and new.is_backdated would fail on them
  if tg_op = 'INSERT' and coalesce((to_jsonb(new)->>'is_backdated')::boolean, false) then
    v_flag := case tg_table_name when 'payments' then 'backdated_payment' when 'expenses' then 'backdated_expense' end;
  end if;
  insert into audit_log (client_id, actor, table_name, row_id, action, flag, before, after)
  values (coalesce((to_jsonb(new)->>'client_id')::uuid, (to_jsonb(old)->>'client_id')::uuid),
          auth.uid(), tg_table_name,
          coalesce((to_jsonb(new)->>'id')::uuid, (to_jsonb(old)->>'id')::uuid),
          tg_op, v_flag,
          case when tg_op <> 'INSERT' then to_jsonb(old) end,
          case when tg_op <> 'DELETE' then to_jsonb(new) end);
  return coalesce(new, old);
end $$;

create trigger audit_expenses after insert or update or delete on expenses for each row execute function audit_trigger();
create trigger audit_payments after insert or update or delete on payments for each row execute function audit_trigger();
create trigger audit_vendors  after insert or update or delete on vendors  for each row execute function audit_trigger();
create trigger audit_tds      after insert or update or delete on tds_rates for each row execute function audit_trigger();

-- ---------- Business rules enforced in the database ----------
-- Rule: sub-users cannot add expenses dated before the current month (beyond the client's window);
-- backdated payments are allowed for everyone but flagged; locked months reject changes.
create or replace function enforce_expense_rules() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  v_window int;
begin
  if exists (select 1 from month_locks
             where client_id = new.client_id and month = date_trunc('month', new.invoice_date)::date) then
    raise exception 'Month % is locked', to_char(new.invoice_date, 'Mon YYYY');
  end if;
  select backdate_window_days into v_window from clients where id = new.client_id;
  new.is_backdated := new.invoice_date < (current_date - v_window)
                      and new.invoice_date < date_trunc('month', current_date)::date;
  if tg_op = 'INSERT' and new.is_backdated and app_role() = 'sub_user' then
    raise exception 'Past-dated entries can only be added by your admin';
  end if;
  if app_role() = 'sub_user' and tg_op = 'UPDATE' and old.status <> 'draft' then
    raise exception 'Submitted entries can only be changed by your admin';
  end if;
  new.updated_at := now();
  return new;
end $$;
create trigger expenses_rules before insert or update on expenses for each row execute function enforce_expense_rules();

create or replace function flag_backdated_payment() returns trigger
language plpgsql as $$
begin
  new.is_backdated := new.paid_on < current_date;
  return new;
end $$;
create trigger payments_flag before insert on payments for each row execute function flag_backdated_payment();

-- ---------- Row Level Security ----------
alter table clients        enable row level security;
alter table profiles       enable row level security;
alter table fiscal_years   enable row level security;
alter table month_locks    enable row level security;
alter table vendors        enable row level security;
alter table expenses       enable row level security;
alter table payments       enable row level security;
alter table tds_challans   enable row level security;
alter table gstr2b_lines   enable row level security;
alter table notifications  enable row level security;
alter table audit_log      enable row level security;
alter table expense_heads  enable row level security;
alter table tds_rates      enable row level security;
alter table rcm_rules      enable row level security;
alter table blocked_credit_rules enable row level security;

create policy clients_read   on clients for select using (can_see_client(id));
create policy clients_write  on clients for all using (app_role() = 'super_admin') with check (app_role() = 'super_admin');
create policy clients_brand  on clients for update using (app_role() = 'client_admin' and id = app_client());

create policy profiles_read  on profiles for select using (id = auth.uid() or can_see_client(client_id) and app_role() <> 'sub_user' or app_role() = 'super_admin');
create policy profiles_admin on profiles for all
  using (app_role() = 'super_admin' or (app_role() = 'client_admin' and client_id = app_client() and role <> 'super_admin'))
  with check (app_role() = 'super_admin' or (app_role() = 'client_admin' and client_id = app_client() and role <> 'super_admin'));

-- tenant tables: read/write within own client
do $$
declare t text;
begin
  foreach t in array array['fiscal_years','vendors','expenses','payments','tds_challans','gstr2b_lines'] loop
    execute format('create policy %1$s_rw on %1$s for all using (can_see_client(client_id)) with check (can_see_client(client_id))', t);
  end loop;
end $$;

-- month locks: client admin can lock; only super admin can unlock (delete)
create policy locks_read   on month_locks for select using (can_see_client(client_id));
create policy locks_insert on month_locks for insert with check (can_see_client(client_id) and app_role() in ('super_admin','client_admin'));
create policy locks_delete on month_locks for delete using (app_role() = 'super_admin');

-- review fields: only super admin may approve/reject (CA firm reviews everything)
create or replace function guard_review() returns trigger
language plpgsql as $$
begin
  if new.status in ('approved','rejected','posted') and old.status is distinct from new.status
     and app_role() <> 'super_admin' then
    raise exception 'Only the CA firm can approve entries';
  end if;
  return new;
end $$;
create trigger expenses_review_guard before update on expenses for each row execute function guard_review();

create policy notif_read  on notifications for select using (user_id = auth.uid() or (user_id is null and can_see_client(client_id)));
create policy notif_mark  on notifications for update using (user_id = auth.uid() or can_see_client(client_id));

create policy audit_read  on audit_log for select using (app_role() = 'super_admin' or (app_role() = 'client_admin' and client_id = app_client()));

-- masters: everyone reads, super admin writes
do $$
declare t text;
begin
  foreach t in array array['expense_heads','tds_rates','rcm_rules','blocked_credit_rules'] loop
    execute format('create policy %1$s_read on %1$s for select using (auth.uid() is not null)', t);
    execute format('create policy %1$s_write on %1$s for all using (app_role() = ''super_admin'') with check (app_role() = ''super_admin'')', t);
  end loop;
end $$;
