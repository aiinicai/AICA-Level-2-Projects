/*
 * Creates a DEMO database filled with sample employees and ~45 trips across all workflow stages,
 * so the Analytics dashboard, exceptions and queues can be explored immediately.
 *
 * Usage:  node --no-warnings tools/seed_demo_data.js  [path/to/demo.db]
 * Default output: data/abc_travel_demo.db   (your real database data/abc_travel.db is NOT touched)
 * Then run the app on it:  DB_FILE=data/abc_travel_demo.db node server.js   (Windows: Start_Demo_Mode.bat)
 *
 * All demo users have password:  Demo@1234     Admin: admin@abc-demo.com
 */
'use strict';
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const out = path.resolve(process.argv[2] || path.join(__dirname, '..', 'data', 'abc_travel_demo.db'));
for (const f of [out, out + '-wal', out + '-shm']) { try { fs.unlinkSync(f); } catch { /* none */ } }
process.env.DB_FILE = out;
const { db } = require('../server.js');

const iso = (d) => d.toISOString();
const ds = (d) => d.toISOString().slice(0, 10);
const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
let seed = 42; const rnd = () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };
const pick = (a) => a[Math.floor(rnd() * a.length)];
const between = (a, b) => Math.round(a + rnd() * (b - a));
const salt = crypto.randomBytes(16).toString('hex');
const hash = crypto.scryptSync('Demo@1234', salt, 64).toString('hex');

const users = [
  ['ADM001', 'Anita Sharma', 'admin@abc-demo.com', 'Admin', 'Administration', 1],
  ['MD001', 'Rajiv Mehta', 'md@abc-demo.com', 'Managing Director', 'Management'],
  ['BH001', 'Priya Nair', 'bh.west@abc-demo.com', 'Business Head', 'Sales'],
  ['BH002', 'Vikram Singh', 'bh.north@abc-demo.com', 'Business Head', 'Sales'],
  ['HR001', 'Kavita Rao', 'hr@abc-demo.com', 'HR Head', 'Human Resources'],
  ['AC001', 'Suresh Iyer', 'accounts@abc-demo.com', 'Accountant', 'Finance & Accounts'],
  ['TA001', 'Neha Gupta', 'travel@abc-demo.com', 'Travel Assistant', 'Administration'],
  ['SM001', 'Arjun Kapoor', 'arjun@abc-demo.com', 'Sales Manager', 'Sales', 0, 'BH001', 'Mumbai'],
  ['SM002', 'Deepa Menon', 'deepa@abc-demo.com', 'Sales Manager', 'Sales', 0, 'BH002', 'Delhi'],
  ['SE001', 'Rahul Verma', 'rahul@abc-demo.com', 'Sales Executive', 'Sales', 0, 'BH001', 'Mumbai'],
  ['SE002', 'Sneha Joshi', 'sneha@abc-demo.com', 'Sales Executive', 'Sales', 0, 'BH001', 'Pune'],
  ['SE003', 'Imran Khan', 'imran@abc-demo.com', 'Sales Executive', 'Sales', 0, 'BH002', 'Delhi'],
  ['SE004', 'Pooja Reddy', 'pooja@abc-demo.com', 'Sales Executive', 'Sales', 0, 'BH002', 'Hyderabad'],
  ['OM001', 'Manoj Pillai', 'manoj@abc-demo.com', 'Operations Manager', 'Operations', 0, 'BH001', 'Chennai'],
];
const now = new Date();
const ids = {};
const insU = db.prepare(`INSERT INTO users(emp_code,name,email,password_hash,salt,role,department,is_admin,registered,created_at,registered_at,base_city,last_login_at)
  VALUES (?,?,?,?,?,?,?,?,1,?,?,?,?)`);
for (const u of users) {
  const r = insU.run(u[0], u[1], u[2], hash, salt, u[3], u[4], u[5] || 0, iso(addDays(now, -400)), iso(addDays(now, -399)), u[7] || 'Mumbai', iso(addDays(now, -between(0, 5))));
  ids[u[0]] = Number(r.lastInsertRowid);
}
for (const u of users) if (u[6]) db.prepare('UPDATE users SET business_head_id=? WHERE id=?').run(ids[u[6]], ids[u[0]]);
// one invited but not yet signed-up employee
db.prepare(`INSERT INTO users(emp_code,name,email,role,department,registered,created_at,business_head_id,base_city) VALUES ('SE005','Karan Malhotra','karan@abc-demo.com','Sales Executive','Sales',0,?,?,'Kolkata')`).run(iso(now), ids.BH002);

const MATRIX = {}; for (const m of db.prepare('SELECT * FROM authority_matrix').all()) MATRIX[m.role] = m;
const routes = [['Mumbai', 'Delhi'], ['Mumbai', 'Bengaluru'], ['Delhi', 'Kolkata'], ['Pune', 'Hyderabad'], ['Delhi', 'Chennai'], ['Hyderabad', 'Mumbai'],
  ['Mumbai', 'Ahmedabad'], ['Chennai', 'Kochi'], ['Delhi', 'Jaipur'], ['Mumbai', 'Goa'], ['Mumbai', 'Dubai'], ['Delhi', 'Singapore'], ['Bengaluru', 'Delhi']];
const airlines = ['IndiGo', 'Air India', 'Akasa Air', 'Air India Express', 'SpiceJet'];
const hotels = { '3 Star': ['Lemon Tree', 'Ginger Hotel', 'Treebo Trend'], '4 Star': ['Novotel', 'Holiday Inn', 'Radisson'], '5 Star': ['Taj Hotel', 'ITC Grand', 'JW Marriott'] };
const purposes = ['Quarterly business review with key account', 'New dealer onboarding and training', 'Product demo for enterprise prospect', 'Annual contract negotiation',
  'Trade exhibition participation', 'Regional sales team meeting', 'Collection follow-up and client visit', 'Tender pre-bid meeting'];
const travellers = ['SM001', 'SM002', 'SE001', 'SE002', 'SE003', 'SE004', 'OM001', 'BH001', 'BH002', 'SE001', 'SE003'];

const insR = db.prepare(`INSERT INTO travel_requests(ref_no,employee_id,trip_type,from_city,to_city,depart_date,return_date,days,purpose,client_name,cost_center,
 est_flight,est_hotel,est_food,est_local,est_misc,est_total,approved_amount,advance_requested,advance_paid,preferred_airline,flight_class_requested,hotel_category_requested,
 late_justification,lead_days,stage,bh_id,submitted_at,created_at,updated_at,airline,flight_no,pnr,flight_class,ticket_cost,hotel_name,hotel_category,hotel_nights,hotel_rate,hotel_cost,
 booking_ref,booked_by,booked_at,claim_submitted_at,claim_total,claim_approved,voucher_no,gl_code,payment_mode,payment_ref,payment_date,net_payable,paid_by,paid_at)
 VALUES (${Array(54).fill('?').join(',')})`);
const insH = db.prepare('INSERT INTO request_history(request_id,actor_id,actor_name,actor_role,action,from_stage,to_stage,comment,created_at) VALUES (?,?,?,?,?,?,?,?,?)');
const insI = db.prepare('INSERT INTO expense_items(request_id,exp_date,category,description,vendor,bill_no,currency,fx_rate,amount,amount_inr,approved_inr,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)');
const insA = db.prepare('INSERT INTO attachments(request_id,item_id,kind,original_name,stored_name,mime,size,sha256,uploaded_by,uploaded_at) VALUES (?,?,?,?,?,?,?,?,?,?)');
const nameOf = {}; for (const u of users) nameOf[ids[u[0]]] = [u[1], u[3]];

// copy a sample bill into uploads so demo attachments open
const uploads = path.join(__dirname, '..', 'uploads');
fs.mkdirSync(uploads, { recursive: true });
const sampleSrc = path.join(__dirname, 'sample_bill_demo.pdf');
const sampleStored = 'demo_sample_bill.pdf';
if (fs.existsSync(sampleSrc)) fs.copyFileSync(sampleSrc, path.join(uploads, sampleStored));

const N = 46;
for (let n = 0; n < N; n++) {
  const code = travellers[n % travellers.length];
  const emp = ids[code]; const role = users.find((u) => u[0] === code)[3];
  const ent = MATRIX[role];
  const [from, to] = pick(routes);
  const intl = ['Dubai', 'Singapore'].includes(to);
  // spread departures over past ~11 months and next 6 weeks
  const offset = n < 36 ? -between(10, 330) : between(3, 45);
  const dep = addDays(now, offset);
  const days = between(2, intl ? 6 : 4);
  const ret = addDays(dep, days - 1);
  const lead = rnd() < 0.3 ? between(1, 9) : between(14, 45);
  const created = addDays(dep, -lead);
  const fare = Math.round((intl ? 38000 : 5200) * (lead < 7 ? 1.9 : lead < 14 ? 1.4 : lead < 30 ? 1.05 : 0.9) * (0.85 + rnd() * 0.3));
  const hc = rnd() < 0.12 ? '5 Star' : ent.hotel_category;
  const rate = Math.round(ent.hotel_max_per_night * (0.7 + rnd() * (hc !== ent.hotel_category ? 0.8 : 0.35)));
  const nights = days - 1;
  const est = { f: Math.round(fare * 0.95), h: ent.hotel_max_per_night * nights, fo: ent.da_per_day * days, l: ent.local_per_day * days, m: 1000 };
  const estTotal = est.f + est.h + est.fo + est.l + est.m;
  // decide stage
  let stage;
  if (offset > 0) stage = pick(['PENDING_BH', 'PENDING_MD', 'PENDING_BOOKING', 'BOOKED', 'BOOKED', 'PENDING_BH']);
  else if (offset > -20) stage = pick(['BOOKED', 'CLAIM_PENDING_BH', 'CLAIM_PENDING_HR', 'CLAIM_PENDING_ACCOUNTS']);
  else stage = rnd() < 0.08 ? 'REJECTED' : rnd() < 0.05 ? 'CANCELLED' : 'PAID';
  if (role === 'Business Head' && stage === 'PENDING_BH') stage = 'PENDING_MD';
  const booked = !['PENDING_BH', 'PENDING_MD', 'PENDING_BOOKING', 'REJECTED', 'CANCELLED'].includes(stage);
  const claimed = /CLAIM|PAID/.test(stage);
  const adv = rnd() < 0.35 ? 5000 : 0;
  const ref = `TR-${dep.getFullYear()}-${String(n + 1).padStart(4, '0')}`;
  const bh = db.prepare('SELECT business_head_id b FROM users WHERE id=?').get(emp).b;
  const airline = pick(airlines);
  const r = insR.run(ref, emp, intl ? 'International' : 'Domestic', from, to, ds(dep), ds(ret), days, pick(purposes), pick(['Tata Motors', 'Reliance Retail', 'Infosys', 'L&T', 'Mahindra', 'Asian Paints', 'Wipro', '']),
    'SALES-' + (bh === ids.BH002 ? 'NORTH' : 'WEST'), est.f, est.h, est.fo, est.l, est.m, estTotal, estTotal, adv, booked && adv ? adv : 0, airline, ent.flight_class, hc,
    lead < 14 ? 'Urgent client requirement' : null, lead, stage, bh || null, iso(created), iso(created), iso(addDays(created, 3)),
    booked ? airline : null, booked ? `${airline === 'IndiGo' ? '6E' : airline === 'Air India' ? 'AI' : airline === 'Akasa Air' ? 'QP' : airline === 'SpiceJet' ? 'SG' : 'IX'} ${between(100, 999)}` : null,
    booked ? crypto.randomBytes(3).toString('hex').toUpperCase() : null, booked ? ent.flight_class : null, booked ? fare : null,
    booked ? pick(hotels[hc]) + ' ' + to : null, booked ? hc : null, booked ? nights : null, booked ? rate : null, booked ? rate * nights : null,
    booked ? 'HB' + between(10000, 99999) : null, booked ? ids.TA001 : null, booked ? iso(addDays(created, 3)) : null,
    null, null, null, null, null, null, null, null, null, null, null);
  const rid = Number(r.lastInsertRowid);
  const H = (actorCode, action, from, to2, comment, when) => insH.run(rid, actorCode ? ids[actorCode] : emp, actorCode ? nameOf[ids[actorCode]][0] : nameOf[emp][0], actorCode ? nameOf[ids[actorCode]][1] : role, action, from, to2, comment, iso(when));
  H(null, 'CREATE', null, 'DRAFT', null, created);
  const first = role === 'Business Head' ? 'PENDING_MD' : 'PENDING_BH';
  H(null, 'SUBMIT', 'DRAFT', first, null, created);
  const bhCode = bh === ids.BH002 ? 'BH002' : 'BH001';
  const order = ['PENDING_BH', 'PENDING_MD', 'PENDING_BOOKING', 'BOOKED', 'CLAIM_PENDING_BH', 'CLAIM_PENDING_HR', 'CLAIM_PENDING_ACCOUNTS', 'PAID'];
  const reach = stage === 'REJECTED' || stage === 'CANCELLED' ? 1 : order.indexOf(stage);
  if (role !== 'Business Head' && reach >= 1) H(bhCode, 'APPROVE', 'PENDING_BH', 'PENDING_MD', 'Approved', addDays(created, 1));
  if (stage === 'REJECTED') { H('MD001', 'REJECT', 'PENDING_MD', 'REJECTED', 'Can be handled over video call', addDays(created, 2)); continue; }
  if (stage === 'CANCELLED') { H(null, 'CANCEL', 'PENDING_MD', 'CANCELLED', 'Client postponed meeting', addDays(created, 2)); continue; }
  if (reach >= 2) H('MD001', 'APPROVE', 'PENDING_MD', 'PENDING_BOOKING', null, addDays(created, 2));
  if (booked && adv) H('AC001', 'ADVANCE_PAID', 'PENDING_BOOKING', 'PENDING_BOOKING', `Advance ₹${adv} paid`, addDays(created, 2));
  if (reach >= 3) H('TA001', 'BOOK', 'PENDING_BOOKING', 'BOOKED', `${airline} PNR booked; ${hc} hotel`, addDays(created, 3));
  if (!claimed) continue;
  // expense items
  const items = [];
  for (let d = 0; d < days; d++) {
    const dt = ds(addDays(dep, d));
    items.push([dt, 'Food & Meals', 'Meals', pick(['Hotel restaurant', 'Cafe Madras', 'Barbeque Nation', 'Haldiram']), Math.round(ent.da_per_day * (0.6 + rnd() * (rnd() < 0.15 ? 1.2 : 0.5)))]);
    items.push([dt, pick(['Taxi / Cab', 'Local Conveyance']), 'Client visits', pick(['Uber', 'Ola', 'Meru Cabs']), Math.round(ent.local_per_day * (0.4 + rnd() * 0.7))]);
  }
  if (rnd() < 0.4) items.push([ds(dep), 'Client Entertainment', 'Business lunch with client', 'Mainland China', between(1800, 4500)]);
  if (intl) items.push([ds(dep), 'Visa & Passport', 'Visa fee', 'VFS Global', between(6000, 9000)]);
  let tot = 0, appr = 0;
  const reviewed = order.indexOf(stage) >= 5;
  items.forEach((it, k) => {
    const cut = reviewed && it[1] === 'Client Entertainment' && rnd() < 0.5 ? Math.round(it[4] * 0.8) : it[4];
    const iid = Number(insI.run(rid, it[0], it[1], it[2], it[3], 'B' + between(1000, 9999), 'INR', 1, it[4], it[4], stage === 'CLAIM_PENDING_BH' ? null : cut, iso(ret)).lastInsertRowid);
    tot += it[4]; appr += cut;
    if (!(n % 7 === 3 && k === 0)) insA.run(rid, iid, 'BILL', `bill_${it[1].split(' ')[0].toLowerCase()}_${k + 1}.pdf`, sampleStored, 'application/pdf', 900, null, emp, iso(ret));
  });
  const claimDay = addDays(ret, n % 9 === 0 ? 22 : between(1, 6));
  db.prepare('UPDATE travel_requests SET claim_submitted_at=?, claim_total=?, claim_approved=? WHERE id=?').run(iso(claimDay), tot, stage === 'CLAIM_PENDING_BH' ? tot : appr, rid);
  H(null, 'SUBMIT_CLAIM', 'BOOKED', role === 'Business Head' ? 'CLAIM_PENDING_HR' : 'CLAIM_PENDING_BH', 'Expense statement with bills', claimDay);
  if (reach >= 5 && role !== 'Business Head') H(bhCode, 'APPROVE', 'CLAIM_PENDING_BH', 'CLAIM_PENDING_HR', appr !== tot ? `Approved ₹${appr} of ₹${tot}` : null, addDays(claimDay, 1));
  if (reach >= 6) H('HR001', 'APPROVE', 'CLAIM_PENDING_HR', 'CLAIM_PENDING_ACCOUNTS', null, addDays(claimDay, 2));
  if (stage === 'PAID') {
    const net = appr - (adv || 0);
    db.prepare(`UPDATE travel_requests SET voucher_no=?, gl_code='6105 - Travel & Conveyance', payment_mode='NEFT', payment_ref=?, payment_date=?, net_payable=?, paid_by=?, paid_at=? WHERE id=?`)
      .run(`JV/TR/${String(n + 1).padStart(3, '0')}`, 'UTR' + between(100000, 999999), ds(addDays(claimDay, 4)), net, ids.AC001, iso(addDays(claimDay, 4)), rid);
    H('AC001', 'PAYMENT', 'CLAIM_PENDING_ACCOUNTS', 'PAID', `Voucher posted; net ₹${net} via NEFT`, addDays(claimDay, 4));
  }
}
// auth log samples
const insL = db.prepare('INSERT INTO auth_logs(email,user_id,event,detail,ip,user_agent,created_at) VALUES (?,?,?,?,?,?,?)');
for (const u of users) insL.run(u[2], ids[u[0]], 'SIGNUP_SUCCESS', u[5] ? 'First user - granted Admin role' : 'Employee self-registration', '10.0.0.' + between(2, 200), 'Chrome (demo)', iso(addDays(now, -399)));
insL.run('outsider@gmail.com', null, 'SIGNUP_REJECTED', 'Email not added by admin', '10.0.0.77', 'Chrome (demo)', iso(addDays(now, -20)));
insL.run('rahul@abc-demo.com', ids.SE001, 'LOGIN_FAILED', 'Wrong password', '10.0.0.45', 'Chrome (demo)', iso(addDays(now, -2)));
db.prepare("INSERT INTO feature_requests(user_id,title,description,status,votes,created_at) VALUES (?,?,?,?,?,?)").run(ids.SE001, 'Corporate credit card statement import', 'Auto-match card transactions with expense lines', 'Planned', 3, iso(addDays(now, -30)));
db.prepare("INSERT INTO feature_requests(user_id,title,description,status,votes,created_at) VALUES (?,?,?,?,?,?)").run(ids.SM002, 'OCR scan of bills', 'Read amount and date from photo of the bill automatically', 'Under Review', 5, iso(addDays(now, -12)));
db.prepare("INSERT INTO feature_requests(user_id,title,description,status,votes,created_at) VALUES (?,?,?,?,?,?)").run(ids.HR001, 'Email alerts on approvals', 'Send email in addition to in-app notification', 'Proposed', 2, iso(addDays(now, -5)));
db.exec('PRAGMA wal_checkpoint(TRUNCATE)');
console.log(`Demo database created: ${out}`);
console.log(`Trips: ${db.prepare('SELECT COUNT(*) c FROM travel_requests').get().c}, Employees: ${db.prepare('SELECT COUNT(*) c FROM users').get().c}`);
console.log('Login: admin@abc-demo.com / Demo@1234  (all demo users use Demo@1234)');
process.exit(0);
