/*
 * End-to-end API test of the complete travel workflow.
 * Run:  node --no-warnings tests/api_workflow_test.js
 * Uses a temporary database and port 18080; does not touch your real data.
 */
'use strict';
const path = require('path');
const fs = require('fs');
const os = require('os');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'abc-test-'));
process.env.DB_FILE = path.join(tmp, 'test.db');
process.env.PORT = '18080';
process.env.UPLOAD_DIR = path.join(tmp, 'uploads');
const { server } = require('../server.js');
const BASE = 'http://127.0.0.1:18080';

let passed = 0, failed = 0;
const ok = (cond, msg) => { if (cond) { passed++; console.log('  ✔ ' + msg); } else { failed++; console.log('  ✘ FAIL: ' + msg); } };
async function call(method, p, body, token) {
  const r = await fetch(BASE + p, { method, headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: 'Bearer ' + token } : {}) }, body: body ? JSON.stringify(body) : undefined });
  let data = {}; try { data = await r.json(); } catch { /* ignore */ }
  return { status: r.status, data };
}
const day = (n) => { const d = new Date(); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); };
const PDF = Buffer.from('%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF').toString('base64');

(async () => {
  await new Promise((r) => server.listen(18080, '127.0.0.1', r));
  try {
    console.log('\n1. Sign up rules');
    let r = await call('GET', '/api/auth/status');
    ok(r.data.has_users === false, 'Fresh database has no users');
    r = await call('POST', '/api/auth/signup', { name: 'Anita Admin', email: 'admin@abc.com', password: 'Admin@123' });
    ok(r.status === 200 && r.data.admin === true, 'First sign-up becomes Admin');
    r = await call('POST', '/api/auth/signup', { name: 'Stranger', email: 'stranger@gmail.com', password: 'Stranger123' });
    ok(r.status === 403, 'Email not added by admin is refused sign-up');
    r = await call('POST', '/api/auth/login', { email: 'admin@abc.com', password: 'wrong-pass1' });
    ok(r.status === 401, 'Wrong password refused');
    r = await call('POST', '/api/auth/login', { email: 'admin@abc.com', password: 'Admin@123' });
    ok(r.status === 200 && r.data.token, 'Admin logs in');
    const A = r.data.token;

    console.log('\n2. Admin adds employees with roles');
    const people = [
      ['Bharat Head', 'bh@abc.com', 'Business Head', 'Sales'],
      ['Meera Director', 'md@abc.com', 'Managing Director', 'Management'],
      ['Tara Travel', 'ta@abc.com', 'Travel Assistant', 'Administration'],
      ['Harish HR', 'hr@abc.com', 'HR Head', 'Human Resources'],
      ['Arjun Accounts', 'ac@abc.com', 'Accountant', 'Finance & Accounts'],
    ];
    const ids = {};
    for (const [name, email, role, department] of people) {
      r = await call('POST', '/api/employees', { name, email, role, department }, A);
      ids[email] = r.data.id;
    }
    r = await call('POST', '/api/employees', { name: 'Sanjay Sales', email: 'sales@abc.com', role: 'Sales Executive', department: 'Sales', business_head_id: ids['bh@abc.com'], base_city: 'Mumbai' }, A);
    ok(r.status === 200, 'Sales Executive added with assigned Business Head');
    r = await call('POST', '/api/employees', { name: 'Dup', email: 'sales@abc.com', role: 'Employee' }, A);
    ok(r.status === 409, 'Duplicate employee email refused');

    const tok = {};
    for (const email of ['bh@abc.com', 'md@abc.com', 'ta@abc.com', 'hr@abc.com', 'ac@abc.com', 'sales@abc.com']) {
      r = await call('POST', '/api/auth/signup', { email, password: 'Passw0rd!' });
      if (r.status !== 200) console.log(r.data);
      r = await call('POST', '/api/auth/login', { email, password: 'Passw0rd!' });
      tok[email] = r.data.token;
    }
    ok(Object.values(tok).every(Boolean), 'All admin-added employees signed up and logged in');
    r = await call('POST', '/api/auth/signup', { email: 'sales@abc.com', password: 'Passw0rd!' });
    ok(r.status === 409, 'Second sign-up with same email refused');
    r = await call('GET', '/api/employees', null, tok['sales@abc.com']);
    ok(r.status === 403, 'Non-admin cannot open employee dashboard');

    console.log('\n3. Pre-travel approval request');
    const S = tok['sales@abc.com'];
    const reqBody = { from_city: 'Mumbai', to_city: 'Delhi', depart_date: day(5), return_date: day(7), purpose: 'Client meeting with XYZ Ltd for annual contract', client_name: 'XYZ Ltd',
      est_flight: 9000, est_hotel: 8000, est_food: 3000, est_local: 1500, est_misc: 500, advance_requested: 5000, hotel_category_requested: '3 Star', submit: true };
    r = await call('POST', '/api/requests', reqBody, S);
    ok(r.status === 400, 'Late request (5 days ahead) without justification is blocked');
    r = await call('POST', '/api/requests', { ...reqBody, late_justification: 'Client called urgent meeting' }, S);
    ok(r.status === 200 && r.data.stage === 'PENDING_BH', 'Request submitted -> Pending Business Head');
    const id = r.data.id;
    r = await call('PUT', '/api/requests/' + id, { ...reqBody, est_misc: 700, late_justification: 'Client called urgent meeting' }, S);
    ok(r.status === 200, 'Employee can edit while still pending (before first approval)');
    r = await call('POST', `/api/requests/${id}/action`, { action: 'APPROVE' }, tok['md@abc.com']);
    ok(r.status === 403, 'MD cannot approve at Business Head stage');
    r = await call('GET', '/api/requests?scope=approvals', null, tok['bh@abc.com']);
    ok(r.data.some((x) => x.id === id), 'Request visible in Business Head approval queue');
    r = await call('POST', `/api/requests/${id}/action`, { action: 'APPROVE', approved_amount: 21000, comment: 'Approved, keep costs low' }, tok['bh@abc.com']);
    ok(r.status === 200, 'Business Head approves with revised budget');
    r = await call('PUT', '/api/requests/' + id, reqBody, S);
    ok(r.status === 403, 'Employee can no longer edit after approval started');
    r = await call('POST', `/api/requests/${id}/action`, { action: 'APPROVE' }, tok['md@abc.com']);
    ok(r.status === 200, 'Managing Director approves');
    r = await call('GET', '/api/requests/' + id, null, S);
    ok(r.data.stage === 'PENDING_BOOKING' && r.data.approved_amount === 21000, 'Now pending booking with approved budget ₹21000');
    ok(r.data.exceptions.some((x) => x.code === 'LATE_BOOKING'), 'Late booking exception flagged');

    console.log('\n4. Advance & booking');
    r = await call('POST', `/api/requests/${id}/action`, { action: 'PAY_ADVANCE', amount: 5000, reference: 'UTR123' }, tok['ac@abc.com']);
    ok(r.status === 200, 'Accountant disburses travel advance ₹5000');
    const booking = { airline: 'IndiGo', flight_no: '6E 2134', pnr: 'AB12CD', flight_class: 'Economy', ticket_cost: 11200, hotel_name: 'Taj Palace', hotel_category: '5 Star', hotel_nights: 2, hotel_rate: 9000 };
    r = await call('POST', `/api/requests/${id}/action`, { action: 'BOOK', booking }, tok['ta@abc.com']);
    ok(r.status === 400, 'Booking 5 Star for Sales Executive without justification blocked (Matrix of Authority)');
    r = await call('POST', `/api/requests/${id}/action`, { action: 'BOOK', booking: { ...booking, hotel_name: 'Lemon Tree', hotel_category: '3 Star', hotel_rate: 3800 } }, tok['ta@abc.com']);
    ok(r.status === 200, 'Travel Assistant books flight + 3 Star hotel');

    console.log('\n5. Expense statement with bills');
    const items = [
      { exp_date: day(5), category: 'Taxi / Cab', description: 'Airport to hotel', amount: 850 },
      { exp_date: day(5), category: 'Food & Meals', description: 'Dinner', amount: 1200 },
      { exp_date: day(6), category: 'Client Entertainment', description: 'Lunch with client', amount: 2400 },
      { exp_date: day(6), category: 'Miscellaneous', description: 'Printouts', amount: 300 },
    ];
    const itemIds = [];
    for (const it of items) { r = await call('POST', `/api/requests/${id}/items`, it, S); itemIds.push(r.data.id); }
    ok(itemIds.every(Boolean), '4 expense lines added');
    r = await call('POST', `/api/requests/${id}/action`, { action: 'SUBMIT_CLAIM' }, S);
    ok(r.status === 400, 'Claim without bills above ₹500 blocked unless remarks given');
    for (const iid of itemIds.slice(0, 3)) {
      r = await call('POST', `/api/requests/${id}/attachments`, { name: `bill_${iid}.pdf`, mime: 'application/pdf', data: PDF + (iid % 2 ? '' : ''), kind: 'BILL', item_id: iid }, S);
    }
    ok(r.status === 200, 'Bills attached (PDF)');
    r = await call('POST', `/api/requests/${id}/attachments`, { name: 'x.exe', mime: 'application/x-msdownload', data: PDF }, S);
    ok(r.status === 400, 'Disallowed file type rejected');
    r = await call('POST', `/api/requests/${id}/action`, { action: 'SUBMIT_CLAIM', comment: 'All bills attached' }, S);
    ok(r.status === 200, 'Expense statement submitted');
    r = await call('GET', '/api/requests/' + id, null, S);
    ok(r.data.stage === 'CLAIM_PENDING_BH' && r.data.claim_total === 4750, 'Claim ₹4750 pending Business Head');

    console.log('\n6. Claim approvals');
    r = await call('POST', `/api/requests/${id}/action`, { action: 'APPROVE', items: [{ id: itemIds[2], approved_inr: 2000, note: 'Capped' }] }, tok['bh@abc.com']);
    ok(r.status === 200, 'Business Head approves with one line reduced');
    r = await call('POST', `/api/requests/${id}/action`, { action: 'SEND_BACK', comment: 'Attach taxi receipt clearly' }, tok['hr@abc.com']);
    ok(r.status === 200, 'HR Head sends claim back');
    r = await call('POST', `/api/requests/${id}/action`, { action: 'SUBMIT_CLAIM', comment: 'Re-attached' }, S);
    ok(r.status === 200, 'Employee re-submits claim');
    r = await call('POST', `/api/requests/${id}/action`, { action: 'APPROVE', items: [{ id: itemIds[2], approved_inr: 2000, note: 'Capped' }] }, tok['bh@abc.com']);
    r = await call('POST', `/api/requests/${id}/action`, { action: 'APPROVE', comment: 'OK' }, tok['hr@abc.com']);
    ok(r.status === 200, 'HR Head gives final approval');
    r = await call('GET', '/api/requests/' + id, null, S);
    ok(r.data.stage === 'CLAIM_PENDING_ACCOUNTS' && r.data.claim_approved === 4350, 'Approved ₹4350, pending Accountant');

    console.log('\n7. Accounting & payment');
    r = await call('POST', `/api/requests/${id}/action`, { action: 'PROCESS_PAYMENT', payment: { voucher_no: 'JV/TR/001', payment_mode: 'NEFT', payment_ref: 'UTR999', payment_date: day(0) } }, tok['ac@abc.com']);
    ok(r.status === 200 && r.data.net_payable === -650, 'Payment processed; net = 4350 - 5000 advance = -650 (recoverable)');
    r = await call('GET', '/api/requests/' + id, null, S);
    ok(r.data.stage === 'PAID' && r.data.history.length >= 12, 'Request closed as PAID with full audit trail');

    console.log('\n8. Special routing & admin views');
    r = await call('POST', '/api/requests', { ...reqBody, depart_date: day(30), return_date: day(32), submit: true }, tok['bh@abc.com']);
    ok(r.data.stage === 'PENDING_MD', "Business Head's own request skips BH stage -> Pending MD");
    r = await call('POST', `/api/requests/${r.data.id}/action`, { action: 'APPROVE' }, tok['bh@abc.com']);
    ok(r.status === 403, 'Nobody can approve their own request');
    r = await call('GET', '/api/analytics', null, A);
    ok(r.status === 200 && r.data.by_employee.length && r.data.by_airline[0].key === 'IndiGo', 'Analytics: employee-wise & airline-wise data');
    ok(r.data.exceptions.length > 0, 'Analytics: exceptions listed');
    r = await call('GET', '/api/analytics', null, S);
    ok(r.status === 403, 'Analytics restricted to Admin');
    r = await call('GET', '/api/auth-logs', null, A);
    const ev = new Set(r.data.map((l) => l.event));
    ok(ev.has('SIGNUP_SUCCESS') && ev.has('SIGNUP_REJECTED') && ev.has('LOGIN_SUCCESS') && ev.has('LOGIN_FAILED'), 'Sign-in / sign-up events saved in database');
    r = await call('GET', '/api/notifications', null, S);
    ok(r.data.length >= 5, 'Employee received workflow notifications');
  } catch (e) { failed++; console.error(e); }
  console.log(`\nResult: ${passed} passed, ${failed} failed\n`);
  server.close();
  fs.rmSync(tmp, { recursive: true, force: true });
  process.exit(failed ? 1 : 0);
})();
