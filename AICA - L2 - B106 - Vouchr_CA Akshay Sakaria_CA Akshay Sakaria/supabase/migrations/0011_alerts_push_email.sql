-- v0.11 — alerts by phone notification (Web Push) and e-mail.
-- queue_due_alerts() writes the same alerts the app shows (src/lib/alerts.ts → buildAlerts): TDS deposit due / overdue,
-- bills overdue past credit days, ITC at risk after 180 days unpaid. The alerts-dispatch function sends new ones to the
-- client's admins by push (if they turned it on) and e-mail (if the firm set up SMTP). Each alert is sent once per stage.

-- ---------------------------------------------------------------- TDS liability by month (mirrors lib/tdsAdvance.ts tdsEntries)
-- bill: its TDS less credits from advances paid ON/BEFORE the bill date, in the bill month;
-- advance: its TDS less credits used for bills dated BEFORE the payment, in the payment month.
create or replace view tds_liability as
select e.client_id, date_trunc('month', e.invoice_date)::date as month, 'bill'::text as kind, e.id as ref_id,
       greatest(0, e.tds_amount - coalesce((select sum(a.tds_credit) from payment_allocations a join payments p on p.id = a.payment_id
                                             where a.expense_id = e.id and p.paid_on <= e.invoice_date), 0)) as tds
from expenses e where e.status not in ('draft', 'rejected') and e.tds_amount > 0
union all
select p.client_id, date_trunc('month', p.paid_on)::date, 'advance', p.id,
       p.tds_amount - coalesce((select sum(a.tds_credit) from payment_allocations a join expenses x on x.id = a.expense_id
                                where a.payment_id = p.id and p.paid_on > x.invoice_date), 0)
from payments p where p.tds_amount > 0;

-- due date of the TDS deposit for a month (same rule as tdsDueDate in lib/alerts.ts: 7th of next month; March → 30 April)
create or replace function tds_due_date(m date) returns date language sql immutable as $$
  select case when extract(month from m) = 3 then make_date(extract(year from m)::int, 4, 30) else (date_trunc('month', m) + interval '1 month 6 days')::date end $$;

-- ---------------------------------------------------------------- alerts
alter table notifications
  add column if not exists severity text check (severity in ('info', 'warn', 'danger')),
  add column if not exists ref text,                 -- e.g. 'tds:2026-09:overdue' — one row per item and stage
  add column if not exists push_sent_at timestamptz,
  add column if not exists email_sent_at timestamptz;
create unique index if not exists notifications_once on notifications (client_id, ref) where ref is not null;

create or replace function queue_due_alerts(p_today date default ist_today()) returns int
language plpgsql security definer set search_path = public as $$
declare n int := 0; k int;
begin
  -- TDS: from 10 days before the due date until 60 days after, while challans are short
  insert into notifications (client_id, kind, severity, ref, title, body, due_on)
  select t.client_id, 'tds_due', case when p_today > tds_due_date(t.month) then 'danger' else 'warn' end,
         'tds:' || to_char(t.month, 'YYYY-MM') || ':' || case when p_today > tds_due_date(t.month) then 'overdue' else 'due' end,
         'TDS ₹' || to_char(t.amt - coalesce(c.paid, 0), 'FM99,99,99,990.00') || ' for ' || to_char(t.month, 'Mon YYYY')
           || case when p_today > tds_due_date(t.month) then ' overdue' else ' due on ' || to_char(tds_due_date(t.month), 'DD Mon YYYY') end,
         case when coalesce(c.paid, 0) > 0 then 'Challans recorded ₹' || to_char(c.paid, 'FM99,99,99,990.00') || ' — balance unpaid.'
              else 'Pay the challan, then snap or upload the challan receipt in TDS.' end,
         tds_due_date(t.month)
  from (select client_id, month, sum(tds) amt from tds_liability group by 1, 2) t
  left join (select client_id, month, sum(amount) paid from tds_challans group by 1, 2) c on c.client_id = t.client_id and c.month = t.month
  where t.amt - coalesce(c.paid, 0) > 0.005 and p_today between tds_due_date(t.month) - 10 and tds_due_date(t.month) + 60
  on conflict (client_id, ref) where ref is not null do nothing;
  get diagnostics k = row_count; n := n + k;

  -- bills: ITC at risk after 180 days unpaid (ITC claimed), otherwise overdue past the vendor's / client's credit days
  insert into notifications (client_id, kind, severity, ref, title, body, due_on)
  select x.client_id,
         case when x.age > 180 and x.itc_eligible then 'itc_180' else 'payment_overdue_30' end,
         case when (x.age > 180 and x.itc_eligible) or x.late > 30 then 'danger' else 'warn' end,
         case when x.age > 180 and x.itc_eligible then 'itc:' || x.id else 'due:' || x.id || ':' || case when x.late > 30 then '30' else '1' end end,
         case when x.age > 180 and x.itc_eligible then 'ITC reversal: ' || x.vendor || ' unpaid ' || x.age || ' days'
              else x.vendor || ': ₹' || to_char(x.bal, 'FM99,99,99,990.00') || ' overdue by ' || x.late || ' days' end,
         'Bill ' || coalesce(x.invoice_no, '') || ' dated ' || to_char(x.invoice_date, 'DD Mon YYYY'),
         x.invoice_date + x.terms
  from (select e.id, e.client_id, e.invoice_no, e.invoice_date, e.itc_eligible, coalesce(v.name, '') vendor, expense_balance(e.id) bal,
               (p_today - e.invoice_date) age, coalesce(v.credit_days, c.default_credit_days, 30) terms,
               (p_today - e.invoice_date) - coalesce(v.credit_days, c.default_credit_days, 30) late
        from expenses e join clients c on c.id = e.client_id left join vendors v on v.id = e.vendor_id
        where e.status not in ('draft', 'rejected')) x
  where x.bal > 0.005 and (x.late > 0 or (x.age > 180 and x.itc_eligible))
  on conflict (client_id, ref) where ref is not null do nothing;
  get diagnostics k = row_count; n := n + k;
  return n;
end $$;
revoke all on function queue_due_alerts(date) from public, authenticated, anon;  -- run by the scheduled function only

-- ---------------------------------------------------------------- where to send
create table if not exists push_subscriptions (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references profiles(id) on delete cascade default auth.uid(),
  endpoint   text not null unique,
  p256dh     text not null,
  auth       text not null,
  created_at timestamptz not null default now()
);
alter table push_subscriptions enable row level security;
create policy push_own on push_subscriptions for all using (user_id = auth.uid()) with check (user_id = auth.uid());

alter table profiles
  add column if not exists email text,                               -- copied from auth at sign-up; used for alert e-mails
  add column if not exists email_alerts boolean not null default true;

-- Schedule (enable pg_cron + pg_net first) — 08:00 IST daily:
-- select cron.schedule('alerts-dispatch', '30 2 * * *', $$ select net.http_post(url := 'https://<ref>.functions.supabase.co/alerts-dispatch',
--   headers := jsonb_build_object('x-cron-secret', '<CRON_SECRET>')) $$);
