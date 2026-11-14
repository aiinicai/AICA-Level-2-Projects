// Applies every migration to a real Postgres (PGlite, in-process) with stand-ins for Supabase auth, then checks the rules.
// Run: npm run test:db   (exits 1 on any failure)
import { PGlite } from '@electric-sql/pglite';

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const dir = process.argv[2] ?? fileURLToPath(new URL('../migrations', import.meta.url));
let failed = 0;
const db = new PGlite();
await db.exec(`
  create role authenticated; create role anon; create role service_role;
  create schema auth;
  create table auth.users (id uuid primary key);
  create function auth.uid() returns uuid language sql stable as $$ select nullif(current_setting('test.uid', true), '')::uuid $$;
`);
for (const f of fs.readdirSync(dir).filter((f) => f.endsWith('.sql')).sort()) {
  try { await db.exec(fs.readFileSync(path.join(dir, f), 'utf8').replace(/create extension if not exists pgcrypto;/g, '-- pgcrypto: gen_random_uuid is built in')); console.log('OK  ', f); }
  catch (e) { console.log('FAIL', f, '→', e.message); process.exit(1); }
}

const as = (uid) => db.exec(`select set_config('test.uid', '${uid ?? ''}', false)`);
const q = async (sql, params) => (await db.query(sql, params)).rows;
const expectErr = async (label, fn, re) => { try { await fn(); failed++; console.log('BAD ', label, '— no error'); } catch (e) { if (!re.test(e.message)) failed++; console.log(re.test(e.message) ? 'OK  ' : 'BAD ', label, '→', e.message); } };
const ok = (label, cond, got) => { if (!cond) failed++; console.log(cond ? 'OK  ' : 'BAD ', label, cond ? '' : JSON.stringify(got)); };

// --- seed: CA, client admin, one client, vendor, TDS rate, bills
const CA = '00000000-0000-4000-8000-000000000001', ADM = '00000000-0000-4000-8000-000000000002', C1 = '00000000-0000-4000-8000-0000000000c1';
await db.exec(`
  insert into auth.users values ('${CA}'), ('${ADM}');
  insert into clients (id, name) values ('${C1}', 'Demo Traders');
  insert into profiles (id, full_name, role, client_id) values ('${CA}', 'CA', 'super_admin', null), ('${ADM}', 'Admin', 'client_admin', '${C1}');
  insert into tds_rates (code, description, rate_pct, no_pan_rate_pct, threshold_single, threshold_aggregate, effective_from) values
    ('CONTRACT_IND', 'Contractor', 1, 20, 30000, 100000, '2026-04-01'), ('PROF_FEES', 'Professional', 10, 20, null, 50000, '2026-04-01');
`).catch((e) => { console.log('seed', e.message); process.exit(1); });
await as(ADM);
const [v] = await q(`insert into vendors (client_id, name, pan, pan_status) values ($1, 'Sample Works', 'AAAPS1234Q', null) returning id`, [C1]);
const bill = async (date, total, tds, code = 'CONTRACT_IND') => (await q(
  `insert into expenses (client_id, fy_label, vendor_id, invoice_no, invoice_date, taxable_value, total_amount, tds_code, tds_rate_pct, tds_amount, status, attachment_name, gross_amount)
   values ($1, '2026-27', $2, 'B-' || floor(random()*1e6)::text, $3, $4, $4, $5, 1, $6, 'submitted', 'bill.pdf', $4) returning id`, [C1, v.id, date, total, code, tds]))[0].id;

// 1) advance with TDS: rate from masters, gross-up on the server
const [ids] = await q(`select record_payment($1, $2, $3::jsonb) as ids`, [C1, v.id, JSON.stringify([{ mode: 'cash', paid_on: '2026-09-10', amount: 99000, tds_code: 'CONTRACT_IND' }])]);
const pid = ids.ids[0];
const [p] = await q(`select tds_amount::float, tds_rate_pct::float, tds_base::float from payments where id = $1`, [pid]);
ok('advance ₹99,000 at 1% → TDS ₹1,000, base ₹1,00,000', p.tds_amount === 1000 && p.tds_base === 100000, p);

// 2) apply to a later bill of ₹1,50,000 (TDS 1,500): credit 1,000, balance 49,500
const e1 = await bill('2026-10-20', 150000, 1500);
const [cr] = await q(`select apply_advance($1, $2, 99000)::float as c`, [pid, e1]);
const [bal] = await q(`select expense_balance($1)::float as b`, [e1]);
ok('credit ₹1,000 carried; balance ₹49,500', cr.c === 1000 && bal.b === 49500, { cr, bal });

// 3) cannot overpay a bill
const e2 = await bill('2026-10-21', 10000, 100);
const [ids2] = await q(`select record_payment($1, $2, $3::jsonb) as ids`, [C1, v.id, JSON.stringify([{ mode: 'cash', paid_on: '2026-10-22', amount: 20000 }])]);
await expectErr('overpay blocked', () => q(`select apply_advance($1, $2, 15000)`, [ids2.ids[0], e2]), /More than the bill balance/);

// 4) split payment is all-or-nothing: second line over the bill → nothing saved
const before = (await q(`select count(*)::int n from payments`))[0].n;
await expectErr('split payment rolls back', () => q(`select record_payment($1, $2, $3::jsonb)`, [C1, v.id, JSON.stringify([
  { mode: 'cash', paid_on: '2026-10-22', amount: 5000, allocations: [{ expense_id: e2, amount: 5000 }] },
  { mode: 'cash', paid_on: '2026-10-22', amount: 9000, allocations: [{ expense_id: e2, amount: 9000 }] }])]), /More than the bill balance/);
ok('no half-saved payment', (await q(`select count(*)::int n from payments`))[0].n === before);

// 5) users cannot insert payments / allocations directly, nor edit amounts
await db.exec(`grant usage on schema public to authenticated; grant select, insert, update, delete on all tables in schema public to authenticated; grant usage on schema auth to authenticated; grant select on auth.users to authenticated; grant usage, select on all sequences in schema public to authenticated`);
for (const t of ['payments', 'payment_allocations', 'expenses', 'vendors', 'profiles', 'audit_log', 'system_events', 'clients', 'month_locks', 'tds_rates']) await db.exec(`alter table ${t} force row level security`).catch(() => {});
await db.exec(`set role authenticated`);
await expectErr('direct payment insert refused', () => q(`insert into payments (client_id, vendor_id, mode, paid_on, amount) values ($1, $2, 'cash', '2026-10-22', 10)`, [C1, v.id]), /row-level security|policy/);
await expectErr('payment amount edit refused', () => q(`update payments set amount = 1 where id = $1`, [pid]), /cannot be changed/);
await db.exec(`reset role`);

// 6) log retention: recent audit rows cannot be deleted or changed
await expectErr('audit delete blocked', () => q(`delete from audit_log`), /at least one year/);
await expectErr('audit update blocked', () => q(`update audit_log set action = 'x'`), /cannot be changed/);

// 7) WhatsApp: users cannot mark their own number confirmed; code is 6 digits, only its hash is stored
await db.exec(`update profiles set whatsapp_number = '919876543210' where id = '${ADM}'`);
await expectErr('self-confirm refused', () => q(`update profiles set whatsapp_verified_at = now() where id = $1`, [ADM]), /code sent from that number/);
const [code] = await q(`select start_whatsapp_verification() as c`);
const [prof] = await q(`select whatsapp_code_hash h from profiles where id = $1`, [ADM]);
ok('6-digit code, hash stored (not the code)', /^\d{6}$/.test(code.c) && prof.h.length === 64 && prof.h !== code.c, { code, prof });

// 8) aggregator bill: approval balance counts the non-GST part
const e3 = await bill('2026-10-23', 2875, 0);
await db.exec(`update expenses set taxable_value = 135.59, cgst = 12.2, sgst = 12.2, non_taxable_amount = 2715, head_id = (select id from expense_heads limit 1) where id = '${e3}'`);
if ((await q(`select count(*)::int n from expense_heads`))[0].n === 0) await db.exec(`insert into expense_heads (name) values ('Travelling Expenses'); update expenses set head_id = (select id from expense_heads limit 1) where id = '${e3}'`);
await as(CA);
await q(`update expenses set status = 'approved' where id = $1`, [e3]).then(() => ok('aggregator bill approves (2,715 non-GST + 135.59 + 24.40 = 2,875)', true)).catch((e) => ok('aggregator bill approves', false, e.message));

// 8b) WhatsApp draft with no amount yet (as the webhook saves it when AI is off)
await as(ADM);
await q(`insert into expenses (client_id, fy_label, invoice_date, entry_source, drive_file_id, total_amount, status) values ($1, '2026-27', '2026-11-03', 'whatsapp', 'drv1', 0, 'draft')`, [C1])
  .then(() => ok('WhatsApp draft with ₹0 saves', true)).catch((e) => ok('WhatsApp draft with ₹0 saves', false, e.message));
await as(CA);

// 9) views compile and run
await q(`select * from payment_register limit 1`).then(() => ok('payment_register view runs', true)).catch((e) => ok('payment_register view runs', false, e.message));
await q(`select * from orphan_documents limit 1`).then(() => ok('orphan_documents view runs', true)).catch((e) => ok('orphan_documents view runs', false, e.message));

// 10) bill + document in one transaction; a failing bill leaves no document row
await as(ADM);
const billJson = { client_id: C1, fy_label: '2026-27', vendor_id: v.id, invoice_no: 'DOC-1', invoice_date: '2026-10-25', taxable_value: 1000, gross_amount: 1000, total_amount: 1000, status: 'submitted' };
const [sb] = await q(`select save_bill_document($1::jsonb, $2::jsonb) as id`, [JSON.stringify({ drive_file_id: 'drv-ok', drive_path: 'Vouchr/x/a.jpg', sha256: 'aa' }), JSON.stringify(billJson)]);
const [linked] = await q(`select e.document_id is not null as linked, d.staged from expenses e join documents d on d.id = e.document_id where e.id = $1`, [sb.id]);
ok('bill saved with its document (not staged)', linked?.linked && linked.staged === false, linked);
const docsBefore = (await q(`select count(*)::int n from documents`))[0].n;
await expectErr('bad bill → no document row', () => q(`select save_bill_document($1::jsonb, $2::jsonb)`, [JSON.stringify({ drive_file_id: 'drv-bad', drive_path: 'p', sha256: 'bb' }), JSON.stringify({ ...billJson, invoice_no: 'DOC-2', total_amount: -5 })]), /expenses_total|check constraint/);
ok('document rolled back with the bill', (await q(`select count(*)::int n from documents`))[0].n === docsBefore);

// 11) an upload stays staged until a bill uses it; then it is no longer an orphan
await db.exec(`reset role`);
await as(null);
await q(`insert into documents (client_id, kind, drive_file_id, drive_path, sha256, staged, uploaded_at) values ($1, 'Bills', 'drv-staged', 'p/s.jpg', 'cc', true, now() - interval '2 days'),
  ($1, 'Bills', 'drv-orphan', 'p/o.jpg', 'dd', true, now() - interval '2 days')`, [C1]);
await as(ADM);
await q(`insert into expenses (client_id, fy_label, vendor_id, invoice_no, invoice_date, taxable_value, gross_amount, total_amount, status, drive_file_id) values ($1, '2026-27', $2, 'ST-1', '2026-10-26', 500, 500, 500, 'submitted', 'drv-staged')`, [C1, v.id]);
const orphans = (await q(`select drive_file_id from orphan_documents`)).map((r) => r.drive_file_id);
ok('used upload is attached; only the unused one is an orphan', orphans.length === 1 && orphans[0] === 'drv-orphan', orphans);

// 12) alerts: TDS on the September advance (₹1,000) is due 07 Oct; queued once, not again on the next run
await db.exec(`reset role`);
await as(null);
const before12 = (await q(`select count(*)::int n from notifications`))[0].n;
await q(`select queue_due_alerts('2026-10-02')`);
const tdsAlert = (await q(`select title, severity from notifications where ref = 'tds:2026-09:due'`))[0];
ok('TDS alert for Sept advance: ₹1,000.00 due 07 Oct', tdsAlert?.title === 'TDS ₹1,000.00 for Sep 2026 due on 07 Oct 2026', tdsAlert);
const after1 = (await q(`select count(*)::int n from notifications`))[0].n;
await q(`select queue_due_alerts('2026-10-02')`);
ok('second run adds nothing (sent once per stage)', (await q(`select count(*)::int n from notifications`))[0].n === after1 && after1 > before12);
await q(`select queue_due_alerts('2026-10-09')`);
ok('after the due date a separate "overdue" alert', (await q(`select count(*)::int n from notifications where ref = 'tds:2026-09:overdue'`))[0].n === 1);
const sept = (await q(`select sum(tds)::float t from tds_liability where month = '2026-09-01'`))[0].t;
const oct = (await q(`select sum(tds)::float t from tds_liability where month = '2026-10-01' and kind = 'bill' and ref_id = $1`, [e1]))[0].t;
ok('TDS liability matches the app: advance ₹1,000 in Sept, bill ₹500 left in Oct', sept === 1000 && oct === 500, { sept, oct });

// 13) credit / debit notes from vendors (0012)
await db.exec(`reset role`);
await as(ADM);
const e9 = await bill('2026-10-01', 11800, 0);
await q(`update expenses set itc_eligible = true, cgst = 900, sgst = 900, taxable_value = 10000 where id = $1`, [e9]).catch(() => {});
await q(`insert into vendor_notes (client_id, fy_label, vendor_id, kind, note_no, note_date, expense_id, reason, taxable_value, cgst, sgst, total_amount)
  values ($1, '2026-27', $2, 'credit', 'CN-1', '2026-10-10', $3, 'return', 1000, 90, 90, 1180)`, [C1, v.id, e9]);
const [b9] = await q(`select expense_balance($1)::float b`, [e9]);
ok('credit note ₹1,180 reduces the bill balance to ₹10,620', b9.b === 10620, b9);
const [itc9] = await q(`select itc_eligible from vendor_notes where note_no = 'CN-1'`);
ok('ITC on the note follows the bill', itc9.itc_eligible === true, itc9);
await expectErr('credit note above the bill value refused', () => q(`insert into vendor_notes (client_id, fy_label, vendor_id, kind, note_no, note_date, expense_id, reason, taxable_value, total_amount)
  values ($1, '2026-27', $2, 'credit', 'CN-2', '2026-10-11', $3, 'discount', 11000, 11000)`, [C1, v.id, e9]), /cannot exceed the bill value/);
await expectErr('note dated before the bill refused', () => q(`insert into vendor_notes (client_id, fy_label, vendor_id, kind, note_no, note_date, expense_id, reason, taxable_value, total_amount)
  values ($1, '2026-27', $2, 'debit', 'DN-1', '2026-09-01', $3, 'rate', 100, 100)`, [C1, v.id, e9]), /before the bill/);
await expectErr('same note number twice refused', () => q(`insert into vendor_notes (client_id, fy_label, vendor_id, kind, note_no, note_date, expense_id, reason, taxable_value, total_amount)
  values ($1, '2026-27', $2, 'credit', 'cn/1', '2026-10-12', $3, 'return', 10, 10)`, [C1, v.id, e9]), /duplicate key|unique/);
const [ids9] = await q(`select record_payment($1, $2, $3::jsonb) as ids`, [C1, v.id, JSON.stringify([{ mode: 'cash', paid_on: '2026-10-15', amount: 20000 }])]);
await expectErr('payment above the balance after the credit note refused', () => q(`select apply_advance($1, $2, 10700)`, [ids9.ids[0], e9]), /More than the bill balance/);
await q(`select apply_advance($1, $2, 10620)`, [ids9.ids[0], e9]).then(() => ok('paying exactly the new balance works', true)).catch((e) => ok('paying exactly the new balance works', false, e.message));

// 14) a user cannot insert a bill that is already approved (skipping CA review); control settings stay the CA's
await db.exec(`reset role`);
await as(ADM);
await expectErr('client admin inserting an approved bill refused', () => q(`insert into expenses (client_id, fy_label, vendor_id, invoice_date, taxable_value, gross_amount, total_amount, status, attachment_name)
  values ($1, '2026-27', $2, '2026-10-30', 100, 100, 100, 'approved', 'x.pdf')`, [C1, v.id]), /Only the CA firm can approve/);
await expectErr('client admin switching on auto-approval refused', () => q(`update clients set auto_approve = '{"enabled": true}' where id = $1`, [C1]), /control settings/);
await as(CA);
await q(`update clients set auto_approve = '{"enabled": true, "maxAmount": 5000, "samplePct": 10, "minHistory": 3}' where id = $1`, [C1])
  .then(() => ok('CA firm can switch on auto-approval', true)).catch((e) => ok('CA firm can switch on auto-approval', false, e.message));

if (failed) { console.log(failed + ' check(s) failed'); process.exit(1); } else console.log('all database checks passed');
