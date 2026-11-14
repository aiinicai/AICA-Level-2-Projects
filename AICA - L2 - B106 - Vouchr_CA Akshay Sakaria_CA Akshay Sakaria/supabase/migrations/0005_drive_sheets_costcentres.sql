-- v0.4: Google Drive filing, Sheets mirror, payment sources (UPI IDs / cards / petty cash),
-- projects & branches (cost centres), narrations.

-- Documents filed in Drive: Vouchr/<Client>/FY <yyyy-yy>/<Kind>/<file>
create table documents (
  id          uuid primary key default gen_random_uuid(),
  client_id   uuid not null references clients(id),
  fy_label    text,
  kind        text not null check (kind in ('Bills','TDS Challans','Bank Statements','GSTR-2B','Branding')),
  drive_file_id text not null,
  drive_path  text not null,
  web_view_link text,
  sha256      text,
  uploaded_by uuid references profiles(id) default auth.uid(),
  uploaded_at timestamptz not null default now(),
  unique (client_id, sha256)
);
alter table documents enable row level security;
create policy documents_rw on documents for all using (can_see_client(client_id)) with check (can_see_client(client_id));

alter table expenses
  add column document_id uuid references documents(id),
  add column narration text check (char_length(narration) <= 250),
  add column cost_centre_id uuid;
alter table tds_challans add column document_id uuid references documents(id);

-- One Google Sheet per client per FY
create table client_sheets (
  client_id uuid not null references clients(id),
  fy_label  text not null,
  sheet_id  text not null,
  primary key (client_id, fy_label)
);
alter table client_sheets enable row level security;
create policy client_sheets_read on client_sheets for select using (can_see_client(client_id));

-- Payment sources: bank accounts, UPI IDs (linked to a bank), cards, cash boxes
alter table bank_accounts
  add column kind text not null default 'bank' check (kind in ('bank','upi','card','cash')),
  add column upi_id text,
  add column linked_bank_id uuid references bank_accounts(id);
alter table payments drop constraint if exists payments_account_for_non_cash;

-- Projects / branches
create table cost_centres (
  id        uuid primary key default gen_random_uuid(),
  client_id uuid not null references clients(id),
  name      text not null,
  kind      text not null check (kind in ('project','branch')),
  active    boolean not null default true
);
create unique index cost_centres_name on cost_centres (client_id, lower(name)); -- an expression needs an index, not a table constraint
alter table cost_centres enable row level security;
create policy cost_centres_read on cost_centres for select using (can_see_client(client_id));
create policy cost_centres_write on cost_centres for all using (can_see_client(client_id) and app_role() in ('super_admin','client_admin'))
  with check (can_see_client(client_id) and app_role() in ('super_admin','client_admin'));
alter table expenses add constraint expenses_cost_centre_fk foreign key (cost_centre_id) references cost_centres(id);

-- Flat views the Sheets mirror reads
create or replace view expense_register as
select e.client_id, e.fy_label, e.invoice_date, v.name as vendor, v.gstin, e.invoice_no, e.hsn_sac, h.name as head, cc.name as project_branch,
       e.taxable_value, e.cgst, e.sgst, e.igst, e.total_amount, e.tds_amount, e.rcm_tax, e.itc_eligible, e.status, e.narration,
       expense_balance(e.id) as balance
from expenses e left join vendors v on v.id = e.vendor_id left join expense_heads h on h.id = e.head_id left join cost_centres cc on cc.id = e.cost_centre_id
where e.status <> 'draft';

create or replace view payment_register as
select p.client_id, (case when extract(month from p.paid_on) >= 4 then extract(year from p.paid_on) else extract(year from p.paid_on) - 1 end)::int::text
         || '-' || lpad(((case when extract(month from p.paid_on) >= 4 then extract(year from p.paid_on) else extract(year from p.paid_on) - 1 end)::int % 100 + 1)::text, 2, '0') as fy_label,
       p.paid_on, v.name as vendor, p.mode, b.name as paid_from, p.bank_ref as ref, p.amount, payment_unallocated(p.id) as advance, array_to_string(p.flags, ' ') as flags
from payments p join vendors v on v.id = p.vendor_id left join bank_accounts b on b.id = p.account_id;

-- Schedule (enable pg_cron + pg_net first):
-- select cron.schedule('sheets-mirror-nightly', '30 21 * * *', $$ select net.http_post(url := 'https://<ref>.functions.supabase.co/sheets-mirror',
--   headers := jsonb_build_object('Authorization','Bearer <service_role_key>')) $$);   -- 03:00 IST
