/*
 * ABC Private Limited - Travel & Expense Management (PWA)
 * Backend server: Node.js (>= 22.13) + built-in SQLite (node:sqlite). Zero npm dependencies.
 *
 * Run:  node server.js            (default http://localhost:8080)
 * Env:  PORT=8080  HOST=0.0.0.0  DB_FILE=./data/abc_travel.db
 *       HTTPS_KEY=./certs/key.pem HTTPS_CERT=./certs/cert.pem   (optional, enables HTTPS)
 */
'use strict';

const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { URL } = require('url');

let DatabaseSync;
try {
  ({ DatabaseSync } = require('node:sqlite'));
} catch (e) {
  console.error('\n[ERROR] This app needs Node.js 22.13 or newer (built-in SQLite).');
  console.error('        Your version: ' + process.version + '. Install the LTS version from https://nodejs.org and try again.\n');
  process.exit(1);
}

const ROOT = __dirname;
const PUBLIC_DIR = path.join(ROOT, 'public');
const DATA_DIR = path.join(ROOT, 'data');
const UPLOAD_DIR = process.env.UPLOAD_DIR ? path.resolve(process.env.UPLOAD_DIR) : path.join(ROOT, 'uploads');
const DB_FILE = process.env.DB_FILE ? path.resolve(process.env.DB_FILE) : path.join(DATA_DIR, 'abc_travel.db');
const PORT = Number(process.env.PORT || 8080);
const HOST = process.env.HOST || '0.0.0.0';
const MAX_UPLOAD_BYTES = 5 * 1024 * 1024; // 5 MB per bill
const SESSION_DAYS = 7;

for (const d of [DATA_DIR, UPLOAD_DIR, path.dirname(DB_FILE)]) fs.mkdirSync(d, { recursive: true });

/* ------------------------------------------------------------------ */
/* Database                                                            */
/* ------------------------------------------------------------------ */
const db = new DatabaseSync(DB_FILE);
db.exec('PRAGMA journal_mode = WAL; PRAGMA foreign_keys = ON;');

db.exec(`
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  emp_code TEXT,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE COLLATE NOCASE,
  password_hash TEXT,
  salt TEXT,
  role TEXT NOT NULL DEFAULT 'Employee',
  department TEXT,
  grade TEXT,
  phone TEXT,
  base_city TEXT,
  business_head_id INTEGER REFERENCES users(id),
  is_admin INTEGER NOT NULL DEFAULT 0,
  is_active INTEGER NOT NULL DEFAULT 1,
  registered INTEGER NOT NULL DEFAULT 0,
  added_by INTEGER,
  created_at TEXT NOT NULL,
  registered_at TEXT,
  last_login_at TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  ip TEXT,
  user_agent TEXT
);
CREATE TABLE IF NOT EXISTS auth_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT,
  user_id INTEGER,
  event TEXT NOT NULL,
  detail TEXT,
  ip TEXT,
  user_agent TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS travel_requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ref_no TEXT UNIQUE,
  employee_id INTEGER NOT NULL REFERENCES users(id),
  trip_type TEXT NOT NULL DEFAULT 'Domestic',
  from_city TEXT NOT NULL,
  to_city TEXT NOT NULL,
  depart_date TEXT NOT NULL,
  return_date TEXT NOT NULL,
  days INTEGER NOT NULL,
  purpose TEXT NOT NULL,
  client_name TEXT,
  cost_center TEXT,
  est_flight REAL DEFAULT 0,
  est_hotel REAL DEFAULT 0,
  est_food REAL DEFAULT 0,
  est_local REAL DEFAULT 0,
  est_misc REAL DEFAULT 0,
  est_total REAL DEFAULT 0,
  approved_amount REAL,
  advance_requested REAL DEFAULT 0,
  advance_paid REAL DEFAULT 0,
  advance_ref TEXT,
  preferred_airline TEXT,
  preferred_time TEXT,
  flight_class_requested TEXT,
  hotel_category_requested TEXT,
  late_justification TEXT,
  lead_days INTEGER,
  stage TEXT NOT NULL DEFAULT 'DRAFT',
  bh_id INTEGER,
  submitted_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  -- booking (Travel Assistant)
  airline TEXT, flight_no TEXT, pnr TEXT, flight_class TEXT, ticket_cost REAL,
  onward_time TEXT, return_flight_no TEXT,
  hotel_name TEXT, hotel_category TEXT, hotel_nights INTEGER, hotel_rate REAL, hotel_cost REAL,
  booking_ref TEXT, booking_notes TEXT, booked_by INTEGER, booked_at TEXT,
  -- claim (expense statement)
  claim_submitted_at TEXT, claim_total REAL, claim_approved REAL, claim_notes TEXT,
  -- accounting / payment
  voucher_no TEXT, gl_code TEXT, payment_mode TEXT, payment_ref TEXT, payment_date TEXT,
  net_payable REAL, paid_by INTEGER, paid_at TEXT, accounting_notes TEXT
);
CREATE TABLE IF NOT EXISTS request_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_id INTEGER NOT NULL REFERENCES travel_requests(id),
  actor_id INTEGER,
  actor_name TEXT,
  actor_role TEXT,
  action TEXT NOT NULL,
  from_stage TEXT,
  to_stage TEXT,
  comment TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS expense_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_id INTEGER NOT NULL REFERENCES travel_requests(id),
  exp_date TEXT NOT NULL,
  category TEXT NOT NULL,
  description TEXT,
  vendor TEXT,
  bill_no TEXT,
  currency TEXT NOT NULL DEFAULT 'INR',
  fx_rate REAL NOT NULL DEFAULT 1,
  amount REAL NOT NULL,
  amount_inr REAL NOT NULL,
  approved_inr REAL,
  approver_note TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS attachments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_id INTEGER NOT NULL REFERENCES travel_requests(id),
  item_id INTEGER,
  kind TEXT NOT NULL DEFAULT 'BILL',
  original_name TEXT NOT NULL,
  stored_name TEXT NOT NULL,
  mime TEXT,
  size INTEGER,
  sha256 TEXT,
  uploaded_by INTEGER,
  uploaded_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  request_id INTEGER,
  message TEXT NOT NULL,
  is_read INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS authority_matrix (
  role TEXT PRIMARY KEY,
  flight_class TEXT NOT NULL,
  hotel_category TEXT NOT NULL,
  hotel_max_per_night REAL NOT NULL,
  da_per_day REAL NOT NULL,
  local_per_day REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS feature_requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'Proposed',
  votes INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS feature_votes (
  feature_id INTEGER NOT NULL, user_id INTEGER NOT NULL, PRIMARY KEY (feature_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_req_emp ON travel_requests(employee_id);
CREATE INDEX IF NOT EXISTS idx_req_stage ON travel_requests(stage);
CREATE INDEX IF NOT EXISTS idx_hist_req ON request_history(request_id);
CREATE INDEX IF NOT EXISTS idx_items_req ON expense_items(request_id);
CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_id, is_read);
`);

/* ------------------------------------------------------------------ */
/* Constants: roles, stages, defaults                                  */
/* ------------------------------------------------------------------ */
const WORKFLOW_ROLES = {
  BH: 'Business Head',
  MD: 'Managing Director',
  TA: 'Travel Assistant',
  HR: 'HR Head',
  AC: 'Accountant',
};
const DEFAULT_ROLES = [
  'Managing Director', 'Business Head', 'Sales Manager', 'Sales Executive', 'HR Head',
  'Accountant', 'Travel Assistant', 'Finance Manager', 'Operations Manager', 'Employee', 'Admin',
];

const STAGES = {
  DRAFT: { label: 'Draft', role: null, phase: 'pre' },
  PENDING_BH: { label: 'Pending Business Head', role: WORKFLOW_ROLES.BH, phase: 'pre' },
  PENDING_MD: { label: 'Pending Managing Director', role: WORKFLOW_ROLES.MD, phase: 'pre' },
  SENT_BACK: { label: 'Sent back to employee', role: null, phase: 'pre' },
  PENDING_BOOKING: { label: 'Pending Travel Booking', role: WORKFLOW_ROLES.TA, phase: 'booking' },
  BOOKED: { label: 'Booked - Travel / Submit Expenses', role: null, phase: 'travel' },
  CLAIM_PENDING_BH: { label: 'Claim Pending Business Head', role: WORKFLOW_ROLES.BH, phase: 'claim' },
  CLAIM_PENDING_HR: { label: 'Claim Pending HR Head', role: WORKFLOW_ROLES.HR, phase: 'claim' },
  CLAIM_SENT_BACK: { label: 'Claim sent back to employee', role: null, phase: 'claim' },
  CLAIM_PENDING_ACCOUNTS: { label: 'Pending Accounting & Payment', role: WORKFLOW_ROLES.AC, phase: 'accounts' },
  PAID: { label: 'Paid & Closed', role: null, phase: 'closed' },
  REJECTED: { label: 'Rejected', role: null, phase: 'closed' },
  CANCELLED: { label: 'Cancelled', role: null, phase: 'closed' },
};

const DEFAULT_SETTINGS = {
  company_name: 'ABC Private Limited',
  base_currency: 'INR',
  min_advance_days: 14,
  over_budget_tolerance_pct: 10,
  bill_required_above: 500,
  claim_deadline_days: 15,
  max_trip_days: 30,
  roles: DEFAULT_ROLES,
  departments: ['Sales', 'Marketing', 'Finance & Accounts', 'Human Resources', 'Operations', 'Administration', 'Management', 'IT'],
  expense_categories: ['Airfare', 'Hotel / Lodging', 'Food & Meals', 'Local Conveyance', 'Taxi / Cab', 'Train / Bus',
    'Visa & Passport', 'Forex Charges', 'Telephone / Internet', 'Client Entertainment', 'Laundry', 'Miscellaneous'],
  airlines: ['Air India', 'IndiGo', 'Akasa Air', 'Air India Express', 'SpiceJet', 'Emirates', 'Qatar Airways',
    'Singapore Airlines', 'Lufthansa', 'British Airways', 'Etihad Airways', 'Other'],
  currencies: { INR: 1, USD: 84, EUR: 92, GBP: 108, AED: 22.9, SGD: 63, JPY: 0.56 },
  features: { international_travel: true, travel_advance: true, feature_board: true, late_booking_justification: true },
};

const DEFAULT_MATRIX = [
  ['Managing Director', 'Business', '5 Star', 15000, 3000, 2000],
  ['Business Head', 'Premium Economy', '5 Star', 10000, 2500, 1500],
  ['HR Head', 'Economy', '4 Star', 7000, 2000, 1200],
  ['Finance Manager', 'Economy', '4 Star', 7000, 2000, 1200],
  ['Operations Manager', 'Economy', '4 Star', 6500, 1800, 1000],
  ['Sales Manager', 'Economy', '4 Star', 6000, 1500, 1000],
  ['Sales Executive', 'Economy', '3 Star', 4000, 1000, 800],
  ['Accountant', 'Economy', '3 Star', 4000, 1000, 800],
  ['Travel Assistant', 'Economy', '3 Star', 4000, 1000, 800],
  ['Employee', 'Economy', '3 Star', 3500, 900, 600],
  ['Admin', 'Economy', '4 Star', 6000, 1500, 1000],
];
const FLIGHT_CLASS_RANK = { 'Economy': 1, 'Premium Economy': 2, 'Business': 3, 'First': 4 };
const HOTEL_RANK = { '2 Star': 2, '3 Star': 3, '4 Star': 4, '5 Star': 5 };

// seed defaults
{
  const ins = db.prepare('INSERT OR IGNORE INTO settings(key,value) VALUES (?,?)');
  for (const [k, v] of Object.entries(DEFAULT_SETTINGS)) ins.run(k, JSON.stringify(v));
  const cnt = db.prepare('SELECT COUNT(*) c FROM authority_matrix').get().c;
  if (!cnt) {
    const m = db.prepare('INSERT INTO authority_matrix VALUES (?,?,?,?,?,?)');
    for (const r of DEFAULT_MATRIX) m.run(...r);
  }
}

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */
const nowIso = () => new Date().toISOString();
const plain = (o) => (o ? { ...o } : o);
const all = (sql, ...p) => db.prepare(sql).all(...p).map(plain);
const one = (sql, ...p) => plain(db.prepare(sql).get(...p));
const run = (sql, ...p) => db.prepare(sql).run(...p);
const num = (v, d = 0) => { const n = Number(v); return Number.isFinite(n) ? n : d; };
const str = (v, max = 500) => (v === undefined || v === null ? '' : String(v).trim().slice(0, max));
const round2 = (n) => Math.round(num(n) * 100) / 100;

function getSettings() {
  const s = {};
  for (const r of all('SELECT key,value FROM settings')) { try { s[r.key] = JSON.parse(r.value); } catch { s[r.key] = r.value; } }
  return { ...DEFAULT_SETTINGS, ...s };
}
function getMatrix() { return all('SELECT * FROM authority_matrix ORDER BY hotel_max_per_night DESC'); }
function entitlementFor(role) {
  return one('SELECT * FROM authority_matrix WHERE role=?', role) || one("SELECT * FROM authority_matrix WHERE role='Employee'") ||
    { role, flight_class: 'Economy', hotel_category: '3 Star', hotel_max_per_night: 3500, da_per_day: 900, local_per_day: 600 };
}

function hashPassword(pw, salt = crypto.randomBytes(16).toString('hex')) {
  const hash = crypto.scryptSync(pw, salt, 64).toString('hex');
  return { hash, salt };
}
function verifyPassword(pw, salt, hash) {
  if (!salt || !hash) return false;
  const h = crypto.scryptSync(pw, salt, 64);
  const expected = Buffer.from(hash, 'hex');
  return h.length === expected.length && crypto.timingSafeEqual(h, expected);
}
const validEmail = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(e);
function passwordProblem(pw) {
  if (typeof pw !== 'string' || pw.length < 8) return 'Password must be at least 8 characters.';
  if (!/[A-Za-z]/.test(pw) || !/[0-9]/.test(pw)) return 'Password must contain letters and numbers.';
  return null;
}

function clientIp(req) {
  return (req.headers['x-forwarded-for'] || '').split(',')[0].trim() || req.socket.remoteAddress || '';
}
function logAuth(req, event, email, userId, detail) {
  run('INSERT INTO auth_logs(email,user_id,event,detail,ip,user_agent,created_at) VALUES (?,?,?,?,?,?,?)',
    email || null, userId || null, event, detail || null, clientIp(req), str(req.headers['user-agent'], 300), nowIso());
}

function publicUser(u) {
  if (!u) return null;
  const { password_hash, salt, ...rest } = u;
  return rest;
}

function daysBetween(a, b) {
  const d1 = new Date(a + 'T00:00:00Z'), d2 = new Date(b + 'T00:00:00Z');
  return Math.round((d2 - d1) / 86400000);
}
const todayStr = () => new Date().toISOString().slice(0, 10);

function notify(userIds, requestId, message) {
  const ids = [...new Set(userIds.filter(Boolean))];
  const st = db.prepare('INSERT INTO notifications(user_id,request_id,message,created_at) VALUES (?,?,?,?)');
  const t = nowIso();
  for (const id of ids) st.run(id, requestId || null, message, t);
}
function usersWithRole(role) {
  return all('SELECT id FROM users WHERE role=? AND is_active=1', role).map((r) => r.id);
}
function adminIds() { return all('SELECT id FROM users WHERE is_admin=1 AND is_active=1').map((r) => r.id); }

/* ------------------------------------------------------------------ */
/* Workflow engine                                                     */
/* ------------------------------------------------------------------ */
function nextPreStage(emp, from) {
  // Business Head requests skip BH stage; MD requests skip BH & MD
  const role = emp.role;
  if (from === 'SUBMIT') {
    if (role === WORKFLOW_ROLES.MD) return 'PENDING_BOOKING';
    if (role === WORKFLOW_ROLES.BH) return 'PENDING_MD';
    return 'PENDING_BH';
  }
  if (from === 'PENDING_BH') return 'PENDING_MD';
  if (from === 'PENDING_MD') return 'PENDING_BOOKING';
  return from;
}
function nextClaimStage(emp, from) {
  if (from === 'SUBMIT') {
    if (emp.role === WORKFLOW_ROLES.BH || emp.role === WORKFLOW_ROLES.MD) return 'CLAIM_PENDING_HR';
    return 'CLAIM_PENDING_BH';
  }
  if (from === 'CLAIM_PENDING_BH') return 'CLAIM_PENDING_HR';
  if (from === 'CLAIM_PENDING_HR') return 'CLAIM_PENDING_ACCOUNTS';
  return from;
}

function canActOnStage(user, reqRow) {
  const st = STAGES[reqRow.stage];
  if (!st || !st.role) return false;
  if (user.is_admin) return true; // admin override
  if (reqRow.employee_id === user.id) return false; // no self-approval
  if (user.role !== st.role) return false;
  if ((reqRow.stage === 'PENDING_BH' || reqRow.stage === 'CLAIM_PENDING_BH') && reqRow.bh_id && reqRow.bh_id !== user.id) {
    // assigned to a specific Business Head
    return false;
  }
  return true;
}
function canView(user, r) {
  if (user.is_admin || r.employee_id === user.id) return true;
  return Object.values(WORKFLOW_ROLES).includes(user.role);
}

function stageActors(r) {
  const st = STAGES[r.stage];
  if (!st || !st.role) return [];
  if ((r.stage === 'PENDING_BH' || r.stage === 'CLAIM_PENDING_BH') && r.bh_id) return [r.bh_id];
  return usersWithRole(st.role);
}

function addHistory(reqId, user, action, from, to, comment) {
  run('INSERT INTO request_history(request_id,actor_id,actor_name,actor_role,action,from_stage,to_stage,comment,created_at) VALUES (?,?,?,?,?,?,?,?,?)',
    reqId, user ? user.id : null, user ? user.name : 'System', user ? (user.is_admin && user.role === 'Admin' ? 'Admin' : user.role) : 'System',
    action, from || null, to || null, comment || null, nowIso());
}

function computeExceptions(r, items, settings, emp) {
  const flags = [];
  const ent = entitlementFor(emp ? emp.role : 'Employee');
  const add = (code, severity, message) => flags.push({ code, severity, message });
  if (r.lead_days !== null && r.lead_days !== undefined && r.lead_days < settings.min_advance_days && r.stage !== 'DRAFT') {
    add('LATE_BOOKING', r.lead_days < 3 ? 'critical' : 'warning',
      `Raised only ${r.lead_days} day(s) before travel (policy: ${settings.min_advance_days} days) - higher airfare likely.`);
  }
  const hc = r.hotel_category || r.hotel_category_requested;
  if (hc && HOTEL_RANK[hc] > HOTEL_RANK[ent.hotel_category]) add('HOTEL_ABOVE_GRADE', 'serious', `${hc} hotel is above entitlement (${ent.hotel_category}) for ${emp.role}.`);
  if (r.hotel_rate && r.hotel_rate > ent.hotel_max_per_night) add('HOTEL_RATE', 'warning', `Hotel rate ₹${r.hotel_rate}/night exceeds limit ₹${ent.hotel_max_per_night}.`);
  const fc = r.flight_class || r.flight_class_requested;
  if (fc && FLIGHT_CLASS_RANK[fc] > FLIGHT_CLASS_RANK[ent.flight_class]) add('FLIGHT_ABOVE_GRADE', 'serious', `${fc} class is above entitlement (${ent.flight_class}).`);
  if (r.days > settings.max_trip_days) add('LONG_TRIP', 'warning', `Trip of ${r.days} days exceeds ${settings.max_trip_days}-day guideline.`);
  const basis = r.approved_amount || r.est_total;
  if (r.claim_total && basis && r.claim_total > basis * (1 + settings.over_budget_tolerance_pct / 100)) {
    add('OVER_BUDGET', 'serious', `Claim ₹${round2(r.claim_total)} exceeds approved ₹${round2(basis)} by more than ${settings.over_budget_tolerance_pct}%.`);
  }
  if (items && items.length) {
    const noBill = items.filter((i) => i.amount_inr > settings.bill_required_above && !(i.attachment_count > 0));
    if (noBill.length) add('MISSING_BILLS', 'serious', `${noBill.length} expense line(s) above ₹${settings.bill_required_above} without bill attached.`);
    const food = items.filter((i) => /food|meal/i.test(i.category)).reduce((s, i) => s + i.amount_inr, 0);
    if (r.days && food > ent.da_per_day * r.days) add('FOOD_OVER_DA', 'warning', `Food ₹${round2(food)} exceeds DA limit ₹${ent.da_per_day * r.days} (${r.days} days).`);
    const seen = {};
    for (const i of items) {
      const k = `${i.category}|${i.amount}|${i.exp_date}|${(i.bill_no || '').toLowerCase()}`;
      if (seen[k]) { add('DUPLICATE_BILL', 'critical', `Possible duplicate expense: ${i.category} ₹${i.amount} on ${i.exp_date}.`); break; }
      seen[k] = 1;
    }
    const outside = items.filter((i) => i.exp_date < addDays(r.depart_date, -1) || i.exp_date > addDays(r.return_date, 1));
    if (outside.length) add('DATE_OUTSIDE_TRIP', 'warning', `${outside.length} expense(s) dated outside travel period.`);
  }
  if (r.claim_submitted_at && r.return_date) {
    const late = daysBetween(r.return_date, r.claim_submitted_at.slice(0, 10));
    if (late > settings.claim_deadline_days) add('LATE_CLAIM', 'warning', `Expense statement submitted ${late} days after return (policy ${settings.claim_deadline_days}).`);
  } else if (r.stage === 'BOOKED' && r.return_date) {
    const late = daysBetween(r.return_date, todayStr());
    if (late > settings.claim_deadline_days) add('CLAIM_OVERDUE', 'warning', `Expense statement overdue by ${late - settings.claim_deadline_days} day(s).`);
  }
  return flags;
}
function addDays(d, n) { const x = new Date(d + 'T00:00:00Z'); x.setUTCDate(x.getUTCDate() + n); return x.toISOString().slice(0, 10); }

function loadItems(reqId) {
  return all(`SELECT e.*, (SELECT COUNT(*) FROM attachments a WHERE a.item_id=e.id) attachment_count
              FROM expense_items e WHERE request_id=? ORDER BY exp_date, id`, reqId);
}
function recalcClaim(reqId) {
  const t = one('SELECT COALESCE(SUM(amount_inr),0) t, COALESCE(SUM(COALESCE(approved_inr,amount_inr)),0) a FROM expense_items WHERE request_id=?', reqId);
  run('UPDATE travel_requests SET claim_total=?, claim_approved=?, updated_at=? WHERE id=?', round2(t.t), round2(t.a), nowIso(), reqId);
}

function fullRequest(id, user) {
  const r = one(`SELECT t.*, u.name employee_name, u.email employee_email, u.role employee_role, u.emp_code, u.department,
                   bh.name bh_name FROM travel_requests t JOIN users u ON u.id=t.employee_id
                   LEFT JOIN users bh ON bh.id=t.bh_id WHERE t.id=?`, id);
  if (!r) return null;
  const emp = one('SELECT * FROM users WHERE id=?', r.employee_id);
  r.items = loadItems(id);
  r.attachments = all('SELECT id,item_id,kind,original_name,mime,size,uploaded_by,uploaded_at FROM attachments WHERE request_id=? ORDER BY id', id);
  r.history = all('SELECT * FROM request_history WHERE request_id=? ORDER BY id', id);
  r.stage_label = STAGES[r.stage] ? STAGES[r.stage].label : r.stage;
  r.entitlement = entitlementFor(emp.role);
  r.exceptions = computeExceptions(r, r.items, getSettings(), emp);
  if (user) {
    r.can_act = canActOnStage(user, r);
    r.is_owner = r.employee_id === user.id;
    r.can_edit = r.is_owner && ['DRAFT', 'SENT_BACK'].includes(r.stage) ||
      (r.is_owner && r.stage === 'PENDING_BH' && !r.history.some((h) => ['APPROVE', 'REJECT', 'SEND_BACK'].includes(h.action) && h.from_stage === 'PENDING_BH'));
    r.can_claim = r.is_owner && ['BOOKED', 'CLAIM_SENT_BACK'].includes(r.stage);
    r.can_cancel = r.is_owner && ['DRAFT', 'SENT_BACK', 'PENDING_BH', 'PENDING_MD', 'PENDING_BOOKING'].includes(r.stage);
  }
  return r;
}

function nextRef() {
  const y = new Date().getFullYear();
  const last = one("SELECT ref_no FROM travel_requests WHERE ref_no LIKE ? ORDER BY id DESC LIMIT 1", `TR-${y}-%`);
  const n = last ? parseInt(last.ref_no.split('-')[2], 10) + 1 : 1;
  return `TR-${y}-${String(n).padStart(4, '0')}`;
}

function requestFieldsFromBody(b, settings) {
  const f = {
    trip_type: ['Domestic', 'International'].includes(b.trip_type) ? b.trip_type : 'Domestic',
    from_city: str(b.from_city, 80), to_city: str(b.to_city, 80),
    depart_date: str(b.depart_date, 10), return_date: str(b.return_date, 10),
    purpose: str(b.purpose, 2000), client_name: str(b.client_name, 200), cost_center: str(b.cost_center, 60),
    est_flight: round2(b.est_flight), est_hotel: round2(b.est_hotel), est_food: round2(b.est_food),
    est_local: round2(b.est_local), est_misc: round2(b.est_misc),
    advance_requested: settings.features.travel_advance ? round2(b.advance_requested) : 0,
    preferred_airline: str(b.preferred_airline, 60), preferred_time: str(b.preferred_time, 60),
    flight_class_requested: str(b.flight_class_requested, 30) || 'Economy',
    hotel_category_requested: str(b.hotel_category_requested, 20) || '3 Star',
    late_justification: str(b.late_justification, 1000),
  };
  const errs = [];
  if (!f.from_city || !f.to_city) errs.push('From and To city are required.');
  if (f.from_city && f.to_city && f.from_city.toLowerCase() === f.to_city.toLowerCase()) errs.push('From and To city cannot be the same.');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(f.depart_date) || !/^\d{4}-\d{2}-\d{2}$/.test(f.return_date)) errs.push('Valid travel dates are required.');
  else if (f.return_date < f.depart_date) errs.push('Return date cannot be before departure date.');
  if (!f.purpose || f.purpose.length < 5) errs.push('Purpose of travel is required.');
  for (const k of ['est_flight', 'est_hotel', 'est_food', 'est_local', 'est_misc', 'advance_requested']) if (f[k] < 0) errs.push('Amounts cannot be negative.');
  if (f.trip_type === 'International' && !settings.features.international_travel) errs.push('International travel is disabled by policy.');
  f.days = errs.length ? 0 : daysBetween(f.depart_date, f.return_date) + 1;
  f.est_total = round2(f.est_flight + f.est_hotel + f.est_food + f.est_local + f.est_misc);
  f.lead_days = errs.length ? null : daysBetween(todayStr(), f.depart_date);
  if (!errs.length && f.lead_days < 0) errs.push('Departure date is in the past. Pre-travel approval must be raised before travel.');
  if (f.advance_requested > f.est_total) errs.push('Advance cannot exceed the estimated total.');
  return { f, errs };
}

/* ------------------------------------------------------------------ */
/* HTTP plumbing                                                       */
/* ------------------------------------------------------------------ */
const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8', '.webmanifest': 'application/manifest+json', '.png': 'image/png',
  '.svg': 'image/svg+xml', '.ico': 'image/x-icon', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp',
  '.pdf': 'application/pdf', '.txt': 'text/plain; charset=utf-8',
};
const ALLOWED_UPLOAD = { 'application/pdf': '.pdf', 'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp', 'image/heic': '.heic' };

class HttpError extends Error { constructor(status, msg) { super(msg); this.status = status; } }
const bad = (m) => new HttpError(400, m);

function send(res, status, body, headers = {}) {
  const isBuf = Buffer.isBuffer(body);
  const data = isBuf || typeof body === 'string' ? body : JSON.stringify(body);
  res.writeHead(status, {
    'Content-Type': isBuf || typeof body === 'string' ? (headers['Content-Type'] || 'text/plain; charset=utf-8') : 'application/json; charset=utf-8',
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'same-origin',
    ...headers,
  });
  res.end(data);
}
function readBody(req, limit = 8 * 1024 * 1024) {
  return new Promise((resolve, reject) => {
    let size = 0; const chunks = [];
    req.on('data', (c) => { size += c.length; if (size > limit) { reject(new HttpError(413, 'Request too large (max 5 MB per file).')); req.destroy(); } else chunks.push(c); });
    req.on('end', () => {
      if (!chunks.length) return resolve({});
      try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf8'))); } catch { reject(bad('Invalid JSON body.')); }
    });
    req.on('error', reject);
  });
}
function authUser(req, url) {
  let token = '';
  const h = req.headers.authorization || '';
  if (h.startsWith('Bearer ')) token = h.slice(7);
  else if (url.searchParams.get('token')) token = url.searchParams.get('token');
  if (!token) return null;
  const s = one('SELECT * FROM sessions WHERE token=?', token);
  if (!s || s.expires_at < nowIso()) return null;
  const u = one('SELECT * FROM users WHERE id=? AND is_active=1', s.user_id);
  if (u) u._token = token;
  return u;
}
function requireUser(ctx) { if (!ctx.user) throw new HttpError(401, 'Please log in.'); return ctx.user; }
function requireAdmin(ctx) { const u = requireUser(ctx); if (!u.is_admin) throw new HttpError(403, 'Admin access only.'); return u; }

const loginFails = new Map(); // email -> {count, until}

/* ------------------------------------------------------------------ */
/* Routes                                                              */
/* ------------------------------------------------------------------ */
const routes = [];
const route = (method, pattern, handler) => {
  const keys = [];
  const rx = new RegExp('^' + pattern.replace(/:(\w+)/g, (_, k) => { keys.push(k); return '([^/]+)'; }) + '$');
  routes.push({ method, rx, keys, handler });
};

// ---- Auth -----------------------------------------------------------
route('GET', '/api/auth/status', () => {
  const c = one('SELECT COUNT(*) c FROM users WHERE registered=1').c;
  return { has_users: c > 0, company: getSettings().company_name };
});

route('POST', '/api/auth/signup', async (ctx) => {
  const b = await readBody(ctx.req);
  const email = str(b.email, 200).toLowerCase();
  const name = str(b.name, 120);
  const pw = b.password;
  if (!validEmail(email)) throw bad('Please enter a valid email id.');
  const pp = passwordProblem(pw); if (pp) throw bad(pp);
  const registeredCount = one('SELECT COUNT(*) c FROM users WHERE registered=1').c;
  const { hash, salt } = hashPassword(pw);
  const t = nowIso();
  if (registeredCount === 0) {
    // First user becomes Admin by default
    if (!name) throw bad('Please enter your name.');
    const existing = one('SELECT id FROM users WHERE email=?', email);
    let id;
    if (existing) {
      run('UPDATE users SET name=?, password_hash=?, salt=?, is_admin=1, registered=1, registered_at=?, role=? WHERE id=?', name, hash, salt, t, 'Admin', existing.id);
      id = existing.id;
    } else {
      id = Number(run(`INSERT INTO users(emp_code,name,email,password_hash,salt,role,department,is_admin,registered,created_at,registered_at)
                VALUES ('ADM001',?,?,?,?, 'Admin','Administration',1,1,?,?)`, name, email, hash, salt, t, t).lastInsertRowid);
    }
    logAuth(ctx.req, 'SIGNUP_SUCCESS', email, id, 'First user - granted Admin role');
    return { ok: true, admin: true, message: 'Welcome! You are the first user and have been made the Administrator. Please log in.' };
  }
  const u = one('SELECT * FROM users WHERE email=?', email);
  if (!u) {
    logAuth(ctx.req, 'SIGNUP_REJECTED', email, null, 'Email not added by admin');
    throw new HttpError(403, 'This email id is not authorised. Please ask your Admin to add you as an employee first.');
  }
  if (!u.is_active) { logAuth(ctx.req, 'SIGNUP_REJECTED', email, u.id, 'Inactive employee'); throw new HttpError(403, 'Your account is deactivated. Contact Admin.'); }
  if (u.registered) { logAuth(ctx.req, 'SIGNUP_REJECTED', email, u.id, 'Already registered'); throw new HttpError(409, 'This email id is already registered. Please log in.'); }
  run('UPDATE users SET password_hash=?, salt=?, registered=1, registered_at=?, name=COALESCE(NULLIF(?,\'\'),name) WHERE id=?', hash, salt, t, name, u.id);
  logAuth(ctx.req, 'SIGNUP_SUCCESS', email, u.id, 'Employee self-registration');
  notify(adminIds(), null, `${u.name} (${email}) completed sign up.`);
  return { ok: true, message: 'Sign up successful. Please log in with your email id and password.' };
});

route('POST', '/api/auth/login', async (ctx) => {
  const b = await readBody(ctx.req);
  const email = str(b.email, 200).toLowerCase();
  const lf = loginFails.get(email);
  if (lf && lf.until > Date.now()) {
    logAuth(ctx.req, 'LOGIN_BLOCKED', email, null, 'Too many failed attempts');
    throw new HttpError(429, 'Too many failed attempts. Try again in a few minutes.');
  }
  const u = one('SELECT * FROM users WHERE email=?', email);
  if (!u || !u.registered || !verifyPassword(String(b.password || ''), u.salt, u.password_hash)) {
    const c = (lf && lf.until <= Date.now() ? 0 : (lf ? lf.count : 0)) + 1;
    loginFails.set(email, { count: c, until: c >= 5 ? Date.now() + 5 * 60000 : 0 });
    logAuth(ctx.req, 'LOGIN_FAILED', email, u ? u.id : null, !u ? 'Unknown email' : (!u.registered ? 'Not signed up yet' : 'Wrong password'));
    throw new HttpError(401, u && !u.registered ? 'You have not signed up yet. Please use Sign Up first.' : 'Invalid email id or password.');
  }
  if (!u.is_active) { logAuth(ctx.req, 'LOGIN_FAILED', email, u.id, 'Inactive'); throw new HttpError(403, 'Your account is deactivated.'); }
  loginFails.delete(email);
  const token = crypto.randomBytes(32).toString('hex');
  const exp = new Date(Date.now() + SESSION_DAYS * 86400000).toISOString();
  run('INSERT INTO sessions(token,user_id,created_at,expires_at,ip,user_agent) VALUES (?,?,?,?,?,?)', token, u.id, nowIso(), exp, clientIp(ctx.req), str(ctx.req.headers['user-agent'], 300));
  run('UPDATE users SET last_login_at=? WHERE id=?', nowIso(), u.id);
  logAuth(ctx.req, 'LOGIN_SUCCESS', email, u.id, null);
  return { token, user: publicUser(one('SELECT * FROM users WHERE id=?', u.id)) };
});

route('POST', '/api/auth/logout', (ctx) => {
  if (ctx.user) { run('DELETE FROM sessions WHERE token=?', ctx.user._token); logAuth(ctx.req, 'LOGOUT', ctx.user.email, ctx.user.id); }
  return { ok: true };
});

route('GET', '/api/me', (ctx) => {
  const u = requireUser(ctx);
  const unread = one('SELECT COUNT(*) c FROM notifications WHERE user_id=? AND is_read=0', u.id).c;
  return { user: publicUser(u), unread, entitlement: entitlementFor(u.role) };
});

route('POST', '/api/me/password', async (ctx) => {
  const u = requireUser(ctx);
  const b = await readBody(ctx.req);
  if (!verifyPassword(String(b.current || ''), u.salt, u.password_hash)) throw bad('Current password is incorrect.');
  const pp = passwordProblem(b.password); if (pp) throw bad(pp);
  const { hash, salt } = hashPassword(b.password);
  run('UPDATE users SET password_hash=?, salt=? WHERE id=?', hash, salt, u.id);
  run('DELETE FROM sessions WHERE user_id=? AND token<>?', u.id, u._token);
  logAuth(ctx.req, 'PASSWORD_CHANGED', u.email, u.id);
  return { ok: true };
});

// ---- Meta -----------------------------------------------------------
route('GET', '/api/meta', (ctx) => {
  requireUser(ctx);
  const s = getSettings();
  return {
    settings: s, matrix: getMatrix(), stages: STAGES, workflow_roles: WORKFLOW_ROLES,
    business_heads: all("SELECT id,name,email FROM users WHERE role='Business Head' AND is_active=1 ORDER BY name"),
    flight_classes: Object.keys(FLIGHT_CLASS_RANK), hotel_categories: Object.keys(HOTEL_RANK),
  };
});

// ---- Employees (Admin) ----------------------------------------------
function employeeFromBody(b, s) {
  const e = {
    emp_code: str(b.emp_code, 30), name: str(b.name, 120), email: str(b.email, 200).toLowerCase(),
    role: str(b.role, 60) || 'Employee', department: str(b.department, 80), grade: str(b.grade, 30),
    phone: str(b.phone, 30), base_city: str(b.base_city, 80),
    business_head_id: b.business_head_id ? Number(b.business_head_id) : null,
    is_admin: b.is_admin ? 1 : 0, is_active: b.is_active === false || b.is_active === 0 ? 0 : 1,
  };
  if (!e.name) throw bad('Employee name is required.');
  if (!validEmail(e.email)) throw bad('Valid employee email id is required.');
  if (!s.roles.includes(e.role)) throw bad('Invalid role.');
  return e;
}
route('GET', '/api/employees', (ctx) => {
  requireAdmin(ctx);
  return all(`SELECT u.id,u.emp_code,u.name,u.email,u.role,u.department,u.grade,u.phone,u.base_city,u.business_head_id,
      bh.name business_head_name,u.is_admin,u.is_active,u.registered,u.created_at,u.registered_at,u.last_login_at,
      (SELECT COUNT(*) FROM travel_requests t WHERE t.employee_id=u.id) trips,
      (SELECT COALESCE(SUM(COALESCE(claim_approved, approved_amount, est_total)),0) FROM travel_requests t WHERE t.employee_id=u.id AND t.stage NOT IN ('REJECTED','CANCELLED','DRAFT')) spend
      FROM users u LEFT JOIN users bh ON bh.id=u.business_head_id ORDER BY u.is_admin DESC, u.name`);
});
route('POST', '/api/employees', async (ctx) => {
  const admin = requireAdmin(ctx);
  const e = employeeFromBody(await readBody(ctx.req), getSettings());
  if (one('SELECT id FROM users WHERE email=?', e.email)) throw new HttpError(409, 'An employee with this email id already exists.');
  if (!e.emp_code) e.emp_code = 'EMP' + String(one('SELECT COALESCE(MAX(id),0)+1 n FROM users').n).padStart(3, '0');
  const id = run(`INSERT INTO users(emp_code,name,email,role,department,grade,phone,base_city,business_head_id,is_admin,is_active,registered,added_by,created_at)
      VALUES (?,?,?,?,?,?,?,?,?,?,?,0,?,?)`, e.emp_code, e.name, e.email, e.role, e.department, e.grade, e.phone, e.base_city,
  e.business_head_id, e.is_admin, e.is_active, admin.id, nowIso()).lastInsertRowid;
  logAuth(ctx.req, 'EMPLOYEE_ADDED', e.email, Number(id), `Added by ${admin.email} as ${e.role}`);
  return { ok: true, id: Number(id) };
});
route('PUT', '/api/employees/:id', async (ctx) => {
  const admin = requireAdmin(ctx);
  const id = Number(ctx.params.id);
  const cur = one('SELECT * FROM users WHERE id=?', id);
  if (!cur) throw new HttpError(404, 'Employee not found.');
  const e = employeeFromBody(await readBody(ctx.req), getSettings());
  const dup = one('SELECT id FROM users WHERE email=? AND id<>?', e.email, id);
  if (dup) throw new HttpError(409, 'Another employee already uses this email id.');
  if (id === admin.id && (!e.is_admin || !e.is_active)) throw bad('You cannot remove your own admin access or deactivate yourself.');
  if (e.business_head_id === id) throw bad('An employee cannot be their own Business Head.');
  run(`UPDATE users SET emp_code=?,name=?,email=?,role=?,department=?,grade=?,phone=?,base_city=?,business_head_id=?,is_admin=?,is_active=? WHERE id=?`,
    e.emp_code || cur.emp_code, e.name, e.email, e.role, e.department, e.grade, e.phone, e.base_city, e.business_head_id, e.is_admin, e.is_active, id);
  if (!e.is_active) run('DELETE FROM sessions WHERE user_id=?', id);
  logAuth(ctx.req, 'EMPLOYEE_UPDATED', e.email, id, `Updated by ${admin.email}`);
  return { ok: true };
});
route('POST', '/api/employees/:id/reset-password', async (ctx) => {
  const admin = requireAdmin(ctx);
  const id = Number(ctx.params.id);
  const u = one('SELECT * FROM users WHERE id=?', id);
  if (!u) throw new HttpError(404, 'Employee not found.');
  const b = await readBody(ctx.req);
  const pp = passwordProblem(b.password); if (pp) throw bad(pp);
  const { hash, salt } = hashPassword(b.password);
  run('UPDATE users SET password_hash=?, salt=?, registered=1, registered_at=COALESCE(registered_at,?) WHERE id=?', hash, salt, nowIso(), id);
  run('DELETE FROM sessions WHERE user_id=?', id);
  logAuth(ctx.req, 'PASSWORD_RESET', u.email, id, `Reset by ${admin.email}`);
  return { ok: true };
});
route('POST', '/api/employees/import', async (ctx) => {
  const admin = requireAdmin(ctx);
  const b = await readBody(ctx.req);
  const s = getSettings();
  const lines = String(b.csv || '').split(/\r?\n/).filter((l) => l.trim());
  if (lines.length < 2) throw bad('CSV must have a header row and at least one employee.');
  const parse = (l) => { const out = []; let cur = '', q = false; for (const ch of l) { if (ch === '"') q = !q; else if (ch === ',' && !q) { out.push(cur); cur = ''; } else cur += ch; } out.push(cur); return out.map((x) => x.trim()); };
  const head = parse(lines[0]).map((h) => h.toLowerCase().replace(/\s+/g, '_'));
  const result = { added: 0, skipped: [] };
  const pendingBh = [];
  for (const line of lines.slice(1)) {
    const cols = parse(line); const o = {}; head.forEach((h, i) => { o[h] = cols[i]; });
    try {
      const e = employeeFromBody({ ...o, is_admin: false }, s);
      if (one('SELECT id FROM users WHERE email=?', e.email)) { result.skipped.push(`${e.email}: already exists`); continue; }
      const id = run(`INSERT INTO users(emp_code,name,email,role,department,grade,phone,base_city,is_admin,is_active,registered,added_by,created_at)
          VALUES (?,?,?,?,?,?,?,?,0,1,0,?,?)`, e.emp_code || null, e.name, e.email, e.role, e.department, e.grade, e.phone, e.base_city, admin.id, nowIso()).lastInsertRowid;
      if (o.business_head_email) pendingBh.push([Number(id), o.business_head_email.toLowerCase()]);
      result.added++;
      logAuth(ctx.req, 'EMPLOYEE_ADDED', e.email, Number(id), `CSV import by ${admin.email}`);
    } catch (err) { result.skipped.push(`${o.email || '?'}: ${err.message}`); }
  }
  for (const [id, bhEmail] of pendingBh) {
    const bh = one('SELECT id FROM users WHERE email=?', bhEmail);
    if (bh) run('UPDATE users SET business_head_id=? WHERE id=?', bh.id, id);
  }
  run("UPDATE users SET emp_code='EMP'||printf('%03d',id) WHERE emp_code IS NULL OR emp_code=''");
  return result;
});

// ---- Travel requests -------------------------------------------------
route('GET', '/api/requests', (ctx) => {
  const u = requireUser(ctx);
  const scope = ctx.url.searchParams.get('scope') || 'mine';
  const base = `SELECT t.id,t.ref_no,t.employee_id,u.name employee_name,u.role employee_role,t.trip_type,t.from_city,t.to_city,t.depart_date,t.return_date,
      t.days,t.purpose,t.est_total,t.approved_amount,t.claim_total,t.claim_approved,t.stage,t.bh_id,t.lead_days,t.airline,t.hotel_category,
      t.hotel_category_requested,t.flight_class,t.flight_class_requested,t.hotel_rate,t.submitted_at,t.updated_at,t.advance_requested,t.advance_paid,
      t.net_payable,t.claim_submitted_at FROM travel_requests t JOIN users u ON u.id=t.employee_id`;
  let rows;
  if (scope === 'mine') rows = all(base + ' WHERE t.employee_id=? ORDER BY t.id DESC', u.id);
  else if (scope === 'all') { requireAdmin(ctx); rows = all(base + ' ORDER BY t.id DESC'); }
  else if (scope === 'approvals') {
    rows = all(base + " WHERE t.stage IN ('PENDING_BH','PENDING_MD','PENDING_BOOKING','CLAIM_PENDING_BH','CLAIM_PENDING_HR','CLAIM_PENDING_ACCOUNTS') ORDER BY t.depart_date")
      .filter((r) => canActOnStage(u, r));
  } else if (scope === 'processed') {
    rows = all(base + ' WHERE t.id IN (SELECT request_id FROM request_history WHERE actor_id=? AND action<>\'SUBMIT\' AND action<>\'CREATE\') AND t.employee_id<>? ORDER BY t.updated_at DESC', u.id, u.id);
  } else if (scope === 'advances') {
    if (!(u.is_admin || u.role === WORKFLOW_ROLES.AC)) throw new HttpError(403, 'Accountant access only.');
    rows = all(base + " WHERE t.stage IN ('PENDING_BOOKING','BOOKED') AND t.advance_requested>0 AND COALESCE(t.advance_paid,0)=0 ORDER BY t.depart_date");
  } else throw bad('Unknown scope');
  const s = getSettings();
  for (const r of rows) {
    r.stage_label = STAGES[r.stage] ? STAGES[r.stage].label : r.stage;
    const emp = { role: r.employee_role };
    const items = r.claim_total ? loadItems(r.id) : [];
    r.exceptions = computeExceptions(r, items, s, emp).map((x) => x.code);
  }
  return rows;
});

route('POST', '/api/requests', async (ctx) => {
  const u = requireUser(ctx);
  const b = await readBody(ctx.req);
  const s = getSettings();
  const { f, errs } = requestFieldsFromBody(b, s);
  if (errs.length) throw bad(errs.join(' '));
  const submit = !!b.submit;
  if (submit && f.lead_days < s.min_advance_days && s.features.late_booking_justification && !f.late_justification) {
    throw bad(`Travel is less than ${s.min_advance_days} days away. Please give a justification for late planning.`);
  }
  const t = nowIso();
  const ref = nextRef();
  const stage = submit ? nextPreStage(u, 'SUBMIT') : 'DRAFT';
  const cols = Object.keys(f);
  const id = Number(run(`INSERT INTO travel_requests(ref_no,employee_id,${cols.join(',')},stage,bh_id,submitted_at,created_at,updated_at)
      VALUES (?,?,${cols.map(() => '?').join(',')},?,?,?,?,?)`, ref, u.id, ...cols.map((k) => f[k]), stage, u.business_head_id || null,
  submit ? t : null, t, t).lastInsertRowid);
  addHistory(id, u, 'CREATE', null, 'DRAFT', null);
  if (submit) afterSubmit(id, u, 'DRAFT', stage);
  return { ok: true, id, ref_no: ref, stage };
});

function afterSubmit(id, u, from, to) {
  addHistory(id, u, 'SUBMIT', from, to, to === 'PENDING_MD' && u.role === WORKFLOW_ROLES.BH ? 'Business Head stage skipped (requester is Business Head)' :
    to === 'PENDING_BOOKING' ? 'Approval stages skipped (requester is Managing Director)' : null);
  const r = one('SELECT * FROM travel_requests WHERE id=?', id);
  notify(stageActors(r), id, `${r.ref_no}: ${u.name} requests travel ${r.from_city} → ${r.to_city} (${r.depart_date}). Awaiting your action.`);
}

route('GET', '/api/requests/:id', (ctx) => {
  const u = requireUser(ctx);
  const r = fullRequest(Number(ctx.params.id), u);
  if (!r) throw new HttpError(404, 'Request not found.');
  if (!canView(u, r)) throw new HttpError(403, 'You do not have access to this request.');
  return r;
});

route('PUT', '/api/requests/:id', async (ctx) => {
  const u = requireUser(ctx);
  const id = Number(ctx.params.id);
  const r = fullRequest(id, u);
  if (!r) throw new HttpError(404, 'Request not found.');
  if (!r.can_edit) throw new HttpError(403, 'This request can no longer be edited by you.');
  const b = await readBody(ctx.req);
  const s = getSettings();
  const { f, errs } = requestFieldsFromBody(b, s);
  if (errs.length) throw bad(errs.join(' '));
  const cols = Object.keys(f);
  run(`UPDATE travel_requests SET ${cols.map((c) => c + '=?').join(',')}, updated_at=? WHERE id=?`, ...cols.map((k) => f[k]), nowIso(), id);
  addHistory(id, u, 'EDIT', r.stage, r.stage, 'Request details edited by employee');
  if (b.submit && ['DRAFT', 'SENT_BACK'].includes(r.stage)) {
    if (f.lead_days < s.min_advance_days && s.features.late_booking_justification && !f.late_justification) {
      throw bad(`Travel is less than ${s.min_advance_days} days away. Please give a justification for late planning.`);
    }
    const to = nextPreStage(u, 'SUBMIT');
    run('UPDATE travel_requests SET stage=?, submitted_at=?, bh_id=? WHERE id=?', to, nowIso(), u.business_head_id || null, id);
    afterSubmit(id, u, r.stage, to);
  }
  return { ok: true };
});

route('POST', '/api/requests/:id/action', async (ctx) => {
  const u = requireUser(ctx);
  const id = Number(ctx.params.id);
  const r = fullRequest(id, u);
  if (!r) throw new HttpError(404, 'Request not found.');
  const b = await readBody(ctx.req);
  const action = str(b.action, 30);
  const comment = str(b.comment, 2000);
  const emp = one('SELECT * FROM users WHERE id=?', r.employee_id);
  const t = nowIso();
  const move = (to, act, note) => {
    run('UPDATE travel_requests SET stage=?, updated_at=? WHERE id=?', to, t, id);
    addHistory(id, u, act, r.stage, to, note || comment);
  };

  // ---- Employee actions
  if (action === 'CANCEL') {
    if (!r.can_cancel) throw new HttpError(403, 'Cannot cancel at this stage.');
    move('CANCELLED', 'CANCEL');
    notify([...stageActors(r)], id, `${r.ref_no} was cancelled by ${u.name}.`);
    return { ok: true };
  }
  if (action === 'SUBMIT_CLAIM') {
    if (!r.can_claim) throw new HttpError(403, 'Expense statement cannot be submitted now.');
    if (!r.items.length) throw bad('Add at least one expense line before submitting the expense statement.');
    const s = getSettings();
    const missing = r.items.filter((i) => i.amount_inr > s.bill_required_above && !i.attachment_count);
    if (missing.length && !comment) throw bad(`${missing.length} expense line(s) above ₹${s.bill_required_above} have no bill attached. Attach bills or give a reason in the remarks.`);
    const to = nextClaimStage(emp, 'SUBMIT');
    run('UPDATE expense_items SET approved_inr=NULL, approver_note=NULL WHERE request_id=?', id);
    recalcClaim(id);
    run('UPDATE travel_requests SET claim_submitted_at=?, claim_notes=? WHERE id=?', t, comment || r.claim_notes, id);
    move(to, 'SUBMIT_CLAIM');
    const r2 = one('SELECT * FROM travel_requests WHERE id=?', id);
    notify(stageActors(r2), id, `${r.ref_no}: ${u.name} submitted expense statement of ₹${round2(r2.claim_total)}. Awaiting your approval.`);
    return { ok: true };
  }

  // ---- Accountant: advance disbursal (any time after MD approval, before claim)
  if (action === 'PAY_ADVANCE') {
    if (!(u.is_admin || u.role === WORKFLOW_ROLES.AC)) throw new HttpError(403, 'Only Accountant can record advance payment.');
    if (!['PENDING_BOOKING', 'BOOKED'].includes(r.stage)) throw bad('Advance can be paid only after MD approval and before claim.');
    const amt = round2(b.amount);
    if (amt <= 0) throw bad('Enter advance amount.');
    run('UPDATE travel_requests SET advance_paid=?, advance_ref=?, updated_at=? WHERE id=?', amt, str(b.reference, 100), t, id);
    addHistory(id, u, 'ADVANCE_PAID', r.stage, r.stage, `Advance ₹${amt} paid. Ref: ${str(b.reference, 100)} ${comment}`);
    notify([r.employee_id], id, `${r.ref_no}: Travel advance of ₹${amt} has been paid.`);
    return { ok: true };
  }

  // ---- Stage owner actions
  if (!r.can_act) throw new HttpError(403, 'You are not the approver for the current stage of this request.');
  const override = u.is_admin && u.role !== STAGES[r.stage].role ? ' [Admin override]' : '';

  if (action === 'REJECT') {
    if (!comment) throw bad('Please give a reason for rejection.');
    move('REJECTED', 'REJECT', comment + override);
    notify([r.employee_id], id, `${r.ref_no} was rejected by ${u.name}: ${comment}`);
    return { ok: true };
  }
  if (action === 'SEND_BACK') {
    if (!comment) throw bad('Please mention what the employee should correct.');
    const to = STAGES[r.stage].phase === 'claim' || r.stage === 'CLAIM_PENDING_ACCOUNTS' ? 'CLAIM_SENT_BACK' : 'SENT_BACK';
    move(to, 'SEND_BACK', comment + override);
    notify([r.employee_id], id, `${r.ref_no} was sent back by ${u.name} for correction: ${comment}`);
    return { ok: true };
  }
  if (action === 'APPROVE') {
    if (['PENDING_BH', 'PENDING_MD'].includes(r.stage)) {
      if (b.approved_amount !== undefined && b.approved_amount !== null && b.approved_amount !== '') {
        const amt = round2(b.approved_amount);
        if (amt <= 0) throw bad('Approved amount must be positive.');
        if (amt !== round2(r.approved_amount || r.est_total)) addHistory(id, u, 'AMOUNT_REVISED', r.stage, r.stage, `Approved budget revised from ₹${round2(r.approved_amount || r.est_total)} to ₹${amt}`);
        run('UPDATE travel_requests SET approved_amount=? WHERE id=?', amt, id);
      } else if (!r.approved_amount) run('UPDATE travel_requests SET approved_amount=est_total WHERE id=?', id);
      const to = nextPreStage(emp, r.stage);
      move(to, 'APPROVE', (comment || '') + override);
      const r2 = one('SELECT * FROM travel_requests WHERE id=?', id);
      notify([r.employee_id], id, `${r.ref_no} approved by ${u.name} (${STAGES[r.stage].role}). Now: ${STAGES[to].label}.`);
      notify(stageActors(r2), id, `${r.ref_no}: travel of ${emp.name} ${r.from_city} → ${r.to_city} awaits your action (${STAGES[to].label}).`);
      if (to === 'PENDING_BOOKING' && r.advance_requested > 0) notify(usersWithRole(WORKFLOW_ROLES.AC), id, `${r.ref_no}: travel advance of ₹${r.advance_requested} requested by ${emp.name}.`);
      return { ok: true };
    }
    if (['CLAIM_PENDING_BH', 'CLAIM_PENDING_HR'].includes(r.stage)) {
      if (Array.isArray(b.items)) {
        const st = db.prepare('UPDATE expense_items SET approved_inr=?, approver_note=? WHERE id=? AND request_id=?');
        for (const it of b.items) {
          const cur = r.items.find((x) => x.id === Number(it.id));
          if (!cur) continue;
          const ap = round2(it.approved_inr);
          if (ap < 0 || ap > cur.amount_inr) throw bad('Approved amount per line must be between 0 and claimed amount.');
          st.run(ap, str(it.note, 300) || null, cur.id, id);
        }
        recalcClaim(id);
      }
      const to = nextClaimStage(emp, r.stage);
      const r1 = one('SELECT claim_total, claim_approved FROM travel_requests WHERE id=?', id);
      const note = r1.claim_approved !== r1.claim_total ? `Approved ₹${r1.claim_approved} of ₹${r1.claim_total} claimed. ` : '';
      move(to, 'APPROVE', note + (comment || '') + override);
      const r2 = one('SELECT * FROM travel_requests WHERE id=?', id);
      notify([r.employee_id], id, `${r.ref_no} expense statement approved by ${u.name}. Now: ${STAGES[to].label}.`);
      notify(stageActors(r2), id, `${r.ref_no}: expense statement of ${emp.name} (₹${r2.claim_approved}) awaits your action.`);
      return { ok: true };
    }
    throw bad('Use the Booking or Payment action for this stage.');
  }
  if (action === 'BOOK') {
    if (r.stage !== 'PENDING_BOOKING') throw bad('Request is not pending booking.');
    const bk = b.booking || {};
    const f = {
      airline: str(bk.airline, 60), flight_no: str(bk.flight_no, 30), return_flight_no: str(bk.return_flight_no, 30), pnr: str(bk.pnr, 30),
      flight_class: str(bk.flight_class, 30) || 'Economy', ticket_cost: round2(bk.ticket_cost), onward_time: str(bk.onward_time, 40),
      hotel_name: str(bk.hotel_name, 120), hotel_category: str(bk.hotel_category, 20), hotel_nights: Math.max(0, Math.round(num(bk.hotel_nights))),
      hotel_rate: round2(bk.hotel_rate), booking_ref: str(bk.booking_ref, 60), booking_notes: str(bk.booking_notes, 1000),
    };
    if (!f.airline && !f.hotel_name) throw bad('Enter flight and/or hotel booking details.');
    if (f.airline && (!f.pnr || f.ticket_cost <= 0)) throw bad('Flight PNR and ticket cost are required.');
    if (f.hotel_name && (!f.hotel_category || f.hotel_rate <= 0 || f.hotel_nights <= 0)) throw bad('Hotel category, nights and rate are required.');
    const ent = entitlementFor(emp.role);
    const overGrade = (f.hotel_category && HOTEL_RANK[f.hotel_category] > HOTEL_RANK[ent.hotel_category]) || (f.flight_class && FLIGHT_CLASS_RANK[f.flight_class] > FLIGHT_CLASS_RANK[ent.flight_class]);
    if (overGrade && !comment) throw bad(`Booking is above the Matrix of Authority for ${emp.role} (${ent.flight_class}, ${ent.hotel_category}). Enter a justification in remarks.`);
    f.hotel_cost = round2(f.hotel_rate * f.hotel_nights);
    const cols = Object.keys(f);
    run(`UPDATE travel_requests SET ${cols.map((c) => c + '=?').join(',')}, booked_by=?, booked_at=? WHERE id=?`, ...cols.map((k) => f[k]), u.id, t, id);
    move('BOOKED', 'BOOK', `Flight: ${f.airline || '-'} ${f.flight_no || ''} PNR ${f.pnr || '-'} (₹${f.ticket_cost}); Hotel: ${f.hotel_name || '-'} ${f.hotel_category || ''} ${f.hotel_nights} night(s) @ ₹${f.hotel_rate}. ${comment}${override}`);
    notify([r.employee_id], id, `${r.ref_no}: Your tickets & hotel are booked. ${f.airline} ${f.flight_no} PNR ${f.pnr}; ${f.hotel_name}. Have a safe trip!`);
    return { ok: true };
  }
  if (action === 'PROCESS_PAYMENT') {
    if (r.stage !== 'CLAIM_PENDING_ACCOUNTS') throw bad('Request is not pending accounting.');
    const p = b.payment || {};
    const f = {
      voucher_no: str(p.voucher_no, 40), gl_code: str(p.gl_code, 40), payment_mode: str(p.payment_mode, 40),
      payment_ref: str(p.payment_ref, 80), payment_date: str(p.payment_date, 10), accounting_notes: str(p.accounting_notes, 1000),
      cost_center: str(p.cost_center, 60) || r.cost_center,
    };
    if (!f.voucher_no || !f.payment_mode || !/^\d{4}-\d{2}-\d{2}$/.test(f.payment_date)) throw bad('Voucher no., payment mode and payment date are required.');
    const net = round2((r.claim_approved || 0) - (r.advance_paid || 0));
    f.net_payable = net;
    const cols = Object.keys(f);
    run(`UPDATE travel_requests SET ${cols.map((c) => c + '=?').join(',')}, paid_by=?, paid_at=? WHERE id=?`, ...cols.map((k) => f[k]), u.id, t, id);
    move('PAID', 'PAYMENT', `Voucher ${f.voucher_no}; ${net >= 0 ? 'Paid to employee' : 'Recoverable from employee'} ₹${Math.abs(net)} via ${f.payment_mode} ${f.payment_ref}. ${comment}${override}`);
    notify([r.employee_id], id, net >= 0 ? `${r.ref_no}: Reimbursement of ₹${net} processed (Voucher ${f.voucher_no}).` : `${r.ref_no}: Excess advance ₹${Math.abs(net)} to be recovered (Voucher ${f.voucher_no}).`);
    return { ok: true, net_payable: net };
  }
  throw bad('Unknown action.');
});

// ---- Expense items (claim) -------------------------------------------
function itemFromBody(b, s) {
  const cur = str(b.currency, 5) || 'INR';
  const fx = cur === 'INR' ? 1 : round2(b.fx_rate || s.currencies[cur] || 0);
  const it = {
    exp_date: str(b.exp_date, 10), category: str(b.category, 60), description: str(b.description, 300),
    vendor: str(b.vendor, 120), bill_no: str(b.bill_no, 60), currency: cur, fx_rate: fx, amount: round2(b.amount),
  };
  if (!/^\d{4}-\d{2}-\d{2}$/.test(it.exp_date)) throw bad('Expense date is required.');
  if (!s.expense_categories.includes(it.category)) throw bad('Choose a valid expense category.');
  if (it.amount <= 0) throw bad('Expense amount must be more than zero.');
  if (fx <= 0) throw bad('Exchange rate is required for foreign currency.');
  it.amount_inr = round2(it.amount * fx);
  return it;
}
route('POST', '/api/requests/:id/items', async (ctx) => {
  const u = requireUser(ctx);
  const id = Number(ctx.params.id);
  const r = fullRequest(id, u);
  if (!r) throw new HttpError(404, 'Request not found.');
  if (!r.can_claim) throw new HttpError(403, 'Expenses can be added only after booking and before claim submission.');
  const it = itemFromBody(await readBody(ctx.req), getSettings());
  const cols = Object.keys(it);
  const iid = run(`INSERT INTO expense_items(request_id,${cols.join(',')},created_at) VALUES (?,${cols.map(() => '?').join(',')},?)`, id, ...cols.map((k) => it[k]), nowIso()).lastInsertRowid;
  recalcClaim(id);
  return { ok: true, id: Number(iid) };
});
route('PUT', '/api/items/:id', async (ctx) => {
  const u = requireUser(ctx);
  const cur = one('SELECT * FROM expense_items WHERE id=?', Number(ctx.params.id));
  if (!cur) throw new HttpError(404, 'Expense not found.');
  const r = fullRequest(cur.request_id, u);
  if (!r.can_claim) throw new HttpError(403, 'This expense can no longer be edited.');
  const it = itemFromBody(await readBody(ctx.req), getSettings());
  const cols = Object.keys(it);
  run(`UPDATE expense_items SET ${cols.map((c) => c + '=?').join(',')}, approved_inr=NULL WHERE id=?`, ...cols.map((k) => it[k]), cur.id);
  recalcClaim(cur.request_id);
  return { ok: true };
});
route('DELETE', '/api/items/:id', (ctx) => {
  const u = requireUser(ctx);
  const cur = one('SELECT * FROM expense_items WHERE id=?', Number(ctx.params.id));
  if (!cur) throw new HttpError(404, 'Expense not found.');
  const r = fullRequest(cur.request_id, u);
  if (!r.can_claim) throw new HttpError(403, 'This expense can no longer be deleted.');
  for (const a of all('SELECT * FROM attachments WHERE item_id=?', cur.id)) { try { fs.unlinkSync(path.join(UPLOAD_DIR, a.stored_name)); } catch { /* ignore */ } }
  run('DELETE FROM attachments WHERE item_id=?', cur.id);
  run('DELETE FROM expense_items WHERE id=?', cur.id);
  recalcClaim(cur.request_id);
  return { ok: true };
});

// ---- Attachments ------------------------------------------------------
route('POST', '/api/requests/:id/attachments', async (ctx) => {
  const u = requireUser(ctx);
  const id = Number(ctx.params.id);
  const r = fullRequest(id, u);
  if (!r) throw new HttpError(404, 'Request not found.');
  const b = await readBody(ctx.req, 8 * 1024 * 1024);
  const kind = ['BILL', 'TICKET', 'HOTEL_VOUCHER', 'OTHER', 'PAYMENT_PROOF', 'APPROVAL_MAIL'].includes(b.kind) ? b.kind : 'BILL';
  const canUpload = (r.is_owner && (r.can_claim || r.can_edit)) || r.can_act || u.is_admin;
  if (!canUpload) throw new HttpError(403, 'You cannot attach documents to this request at this stage.');
  const mime = str(b.mime, 60);
  if (!ALLOWED_UPLOAD[mime]) throw bad('Only PDF, JPG, PNG, WEBP or HEIC files are allowed.');
  const buf = Buffer.from(String(b.data || ''), 'base64');
  if (!buf.length) throw bad('Empty file.');
  if (buf.length > MAX_UPLOAD_BYTES) throw new HttpError(413, 'File too large. Maximum 5 MB per bill.');
  const itemId = b.item_id ? Number(b.item_id) : null;
  if (itemId && !r.items.some((i) => i.id === itemId)) throw bad('Invalid expense line.');
  const sha = crypto.createHash('sha256').update(buf).digest('hex');
  const dup = one('SELECT a.id, t.ref_no FROM attachments a JOIN travel_requests t ON t.id=a.request_id WHERE a.sha256=? AND a.kind=\'BILL\' LIMIT 1', sha);
  const stored = `${id}_${Date.now()}_${crypto.randomBytes(4).toString('hex')}${ALLOWED_UPLOAD[mime]}`;
  fs.writeFileSync(path.join(UPLOAD_DIR, stored), buf);
  const aid = run(`INSERT INTO attachments(request_id,item_id,kind,original_name,stored_name,mime,size,sha256,uploaded_by,uploaded_at) VALUES (?,?,?,?,?,?,?,?,?,?)`,
    id, itemId, kind, str(b.name, 150) || 'document', stored, mime, buf.length, sha, u.id, nowIso()).lastInsertRowid;
  return { ok: true, id: Number(aid), duplicate_of: dup && kind === 'BILL' ? dup.ref_no : null };
});
route('GET', '/api/attachments/:id', (ctx) => {
  const u = requireUser(ctx);
  const a = one('SELECT * FROM attachments WHERE id=?', Number(ctx.params.id));
  if (!a) throw new HttpError(404, 'File not found.');
  const r = one('SELECT * FROM travel_requests WHERE id=?', a.request_id);
  if (!canView(u, r)) throw new HttpError(403, 'No access.');
  const p = path.join(UPLOAD_DIR, a.stored_name);
  if (!fs.existsSync(p)) throw new HttpError(404, 'File missing on server.');
  return { __file: p, mime: a.mime, name: a.original_name };
});
route('DELETE', '/api/attachments/:id', (ctx) => {
  const u = requireUser(ctx);
  const a = one('SELECT * FROM attachments WHERE id=?', Number(ctx.params.id));
  if (!a) throw new HttpError(404, 'File not found.');
  const r = fullRequest(a.request_id, u);
  if (!((r.is_owner && (r.can_claim || r.can_edit)) || u.is_admin) || a.uploaded_by !== u.id && !u.is_admin) throw new HttpError(403, 'Cannot delete this file now.');
  try { fs.unlinkSync(path.join(UPLOAD_DIR, a.stored_name)); } catch { /* ignore */ }
  run('DELETE FROM attachments WHERE id=?', a.id);
  return { ok: true };
});

// ---- Notifications ----------------------------------------------------
route('GET', '/api/notifications', (ctx) => {
  const u = requireUser(ctx);
  return all('SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 100', u.id);
});
route('POST', '/api/notifications/read', (ctx) => {
  const u = requireUser(ctx);
  run('UPDATE notifications SET is_read=1 WHERE user_id=?', u.id);
  return { ok: true };
});

// ---- Personal dashboard -----------------------------------------------
route('GET', '/api/dashboard', (ctx) => {
  const u = requireUser(ctx);
  const mine = all('SELECT stage, est_total, approved_amount, claim_total, claim_approved, net_payable, depart_date, lead_days FROM travel_requests WHERE employee_id=?', u.id);
  const pendingMine = mine.filter((r) => /PENDING/.test(r.stage)).length;
  const approvals = all("SELECT t.* FROM travel_requests t WHERE t.stage IN ('PENDING_BH','PENDING_MD','PENDING_BOOKING','CLAIM_PENDING_BH','CLAIM_PENDING_HR','CLAIM_PENDING_ACCOUNTS')").filter((r) => canActOnStage(u, r)).length;
  const upcoming = all(`SELECT id,ref_no,from_city,to_city,depart_date,return_date,stage,airline,flight_no,pnr,hotel_name FROM travel_requests
                        WHERE employee_id=? AND stage IN ('PENDING_BH','PENDING_MD','PENDING_BOOKING','BOOKED') AND return_date>=? ORDER BY depart_date LIMIT 5`, u.id, todayStr());
  const toClaim = all(`SELECT id,ref_no,from_city,to_city,return_date,stage FROM travel_requests WHERE employee_id=? AND stage IN ('BOOKED','CLAIM_SENT_BACK') AND depart_date<=? ORDER BY return_date`, u.id, todayStr());
  const reimbursed = mine.filter((r) => r.stage === 'PAID').reduce((s, r) => s + (r.net_payable || 0), 0);
  const avgLead = mine.filter((r) => r.lead_days !== null).map((r) => r.lead_days);
  return {
    total_trips: mine.filter((r) => !['DRAFT', 'CANCELLED', 'REJECTED'].includes(r.stage)).length,
    pending_mine: pendingMine, approvals_waiting: approvals, reimbursed: round2(reimbursed),
    in_process: round2(mine.filter((r) => /CLAIM_PENDING/.test(r.stage)).reduce((s, r) => s + (r.claim_total || 0), 0)),
    avg_lead_days: avgLead.length ? Math.round(avgLead.reduce((a, b) => a + b, 0) / avgLead.length) : null,
    upcoming, to_claim: toClaim,
  };
});

// ---- Analytics (Admin) -------------------------------------------------
route('GET', '/api/analytics', (ctx) => {
  requireAdmin(ctx);
  const from = ctx.url.searchParams.get('from') || '0000-01-01';
  const to = ctx.url.searchParams.get('to') || '9999-12-31';
  const s = getSettings();
  const rows = all(`SELECT t.*, u.name employee_name, u.role employee_role, u.department FROM travel_requests t JOIN users u ON u.id=t.employee_id
                    WHERE t.depart_date BETWEEN ? AND ? AND t.stage<>'DRAFT'`, from, to);
  const live = rows.filter((r) => !['REJECTED', 'CANCELLED'].includes(r.stage));
  const spendOf = (r) => r.claim_approved || r.claim_total || ((r.ticket_cost || 0) + (r.hotel_cost || 0)) || r.approved_amount || r.est_total || 0;
  const group = (keyFn, valFn = spendOf) => {
    const m = {};
    for (const r of live) { const k = keyFn(r); if (!k) continue; m[k] = m[k] || { key: k, value: 0, trips: 0 }; m[k].value += valFn(r); m[k].trips++; }
    return Object.values(m).map((x) => ({ ...x, value: round2(x.value) })).sort((a, b) => b.value - a.value);
  };
  const byMonth = {};
  for (const r of live) { const k = r.depart_date.slice(0, 7); byMonth[k] = byMonth[k] || { key: k, value: 0, trips: 0 }; byMonth[k].value += spendOf(r); byMonth[k].trips++; }
  const cat = {};
  const itemRows = all(`SELECT e.category, SUM(COALESCE(e.approved_inr,e.amount_inr)) v FROM expense_items e JOIN travel_requests t ON t.id=e.request_id
                        WHERE t.depart_date BETWEEN ? AND ? AND t.stage NOT IN ('REJECTED','CANCELLED') GROUP BY e.category`, from, to);
  for (const r of itemRows) cat[r.category] = round2(r.v);
  const stages = {};
  for (const r of rows) stages[r.stage] = (stages[r.stage] || 0) + 1;
  const airlines = group((r) => r.airline, (r) => r.ticket_cost || 0).map((a) => ({ ...a, avg_fare: round2(a.value / a.trips) }));
  const leadBuckets = { '0-6 days': { n: 0, fare: 0, c: 0 }, '7-13 days': { n: 0, fare: 0, c: 0 }, '14-29 days': { n: 0, fare: 0, c: 0 }, '30+ days': { n: 0, fare: 0, c: 0 } };
  for (const r of live) {
    if (r.lead_days === null) continue;
    const k = r.lead_days < 7 ? '0-6 days' : r.lead_days < 14 ? '7-13 days' : r.lead_days < 30 ? '14-29 days' : '30+ days';
    leadBuckets[k].n++;
    if (r.ticket_cost && r.trip_type === 'Domestic') { leadBuckets[k].fare += r.ticket_cost; leadBuckets[k].c++; }
  }
  const exceptions = [];
  for (const r of rows) {
    const items = loadItems(r.id);
    for (const e of computeExceptions(r, items, s, { role: r.employee_role })) {
      exceptions.push({ ...e, request_id: r.id, ref_no: r.ref_no, employee_name: r.employee_name, route: `${r.from_city} → ${r.to_city}`, depart_date: r.depart_date, stage: r.stage });
    }
  }
  const sevRank = { critical: 0, serious: 1, warning: 2 };
  exceptions.sort((a, b) => sevRank[a.severity] - sevRank[b.severity]);
  const totalSpend = live.reduce((a, r) => a + spendOf(r), 0);
  const leads = live.filter((r) => r.lead_days !== null).map((r) => r.lead_days);
  return {
    kpis: {
      requests: rows.length, active_trips: live.length, total_spend: round2(totalSpend),
      estimated: round2(live.reduce((a, r) => a + (r.approved_amount || r.est_total || 0), 0)),
      pending_approvals: rows.filter((r) => STAGES[r.stage] && STAGES[r.stage].role).length,
      paid: round2(rows.filter((r) => r.stage === 'PAID').reduce((a, r) => a + (r.net_payable || 0), 0)),
      avg_lead_days: leads.length ? Math.round(leads.reduce((a, b) => a + b, 0) / leads.length) : 0,
      late_bookings: live.filter((r) => r.lead_days !== null && r.lead_days < s.min_advance_days).length,
      exceptions: exceptions.length, employees: one('SELECT COUNT(*) c FROM users WHERE is_active=1').c,
      rejected: rows.filter((r) => r.stage === 'REJECTED').length,
    },
    by_employee: group((r) => r.employee_name),
    by_destination: group((r) => r.to_city),
    by_department: group((r) => r.department || 'Unassigned'),
    by_airline: airlines,
    by_month: Object.values(byMonth).sort((a, b) => a.key.localeCompare(b.key)).map((x) => ({ ...x, value: round2(x.value) })),
    by_category: Object.entries(cat).map(([key, value]) => ({ key, value })).sort((a, b) => b.value - a.value),
    by_stage: Object.entries(stages).map(([key, value]) => ({ key, label: STAGES[key] ? STAGES[key].label : key, value })),
    lead_time: Object.entries(leadBuckets).map(([key, v]) => ({ key, trips: v.n, avg_fare: v.c ? round2(v.fare / v.c) : 0 })),
    by_hotel: group((r) => r.hotel_category, (r) => r.hotel_cost || 0),
    exceptions,
    min_advance_days: s.min_advance_days,
  };
});

route('GET', '/api/auth-logs', (ctx) => {
  requireAdmin(ctx);
  return all('SELECT * FROM auth_logs ORDER BY id DESC LIMIT 500');
});

route('GET', '/api/export/requests.csv', (ctx) => {
  requireAdmin(ctx);
  const rows = all(`SELECT t.ref_no, u.emp_code, u.name employee, u.role, u.department, t.trip_type, t.from_city, t.to_city, t.depart_date, t.return_date, t.days,
      t.purpose, t.client_name, t.est_flight, t.est_hotel, t.est_food, t.est_local, t.est_misc, t.est_total, t.approved_amount, t.advance_paid,
      t.airline, t.flight_no, t.pnr, t.flight_class, t.ticket_cost, t.hotel_name, t.hotel_category, t.hotel_nights, t.hotel_rate, t.hotel_cost,
      t.claim_total, t.claim_approved, t.net_payable, t.voucher_no, t.payment_mode, t.payment_ref, t.payment_date, t.lead_days, t.stage, t.submitted_at
      FROM travel_requests t JOIN users u ON u.id=t.employee_id ORDER BY t.id`);
  const cols = rows.length ? Object.keys(rows[0]) : ['ref_no'];
  const esc = (v) => { const x = v === null || v === undefined ? '' : String(v); return /[",\n]/.test(x) ? '"' + x.replace(/"/g, '""') + '"' : x; };
  const csv = [cols.join(','), ...rows.map((r) => cols.map((c) => esc(r[c])).join(','))].join('\n');
  return { __raw: '﻿' + csv, type: 'text/csv; charset=utf-8', filename: `ABC_Travel_Requests_${todayStr()}.csv` };
});
route('GET', '/api/backup', (ctx) => {
  requireAdmin(ctx);
  db.exec('PRAGMA wal_checkpoint(TRUNCATE)');
  const tmp = path.join(DATA_DIR, `backup_${Date.now()}.db`);
  db.exec(`VACUUM INTO '${tmp.replace(/'/g, "''")}'`);
  const buf = fs.readFileSync(tmp); fs.unlinkSync(tmp);
  return { __raw: buf, type: 'application/octet-stream', filename: `ABC_Travel_Backup_${todayStr()}.db` };
});

// ---- Settings & Matrix (Admin) ----------------------------------------
route('GET', '/api/settings', (ctx) => { requireAdmin(ctx); return { settings: getSettings(), matrix: getMatrix() }; });
route('PUT', '/api/settings', async (ctx) => {
  const admin = requireAdmin(ctx);
  const b = await readBody(ctx.req);
  const cur = getSettings();
  const allowed = ['company_name', 'min_advance_days', 'over_budget_tolerance_pct', 'bill_required_above', 'claim_deadline_days', 'max_trip_days',
    'roles', 'departments', 'expense_categories', 'airlines', 'currencies', 'features'];
  const st = db.prepare('INSERT INTO settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value');
  for (const k of allowed) {
    if (b[k] === undefined) continue;
    let v = b[k];
    if (['min_advance_days', 'over_budget_tolerance_pct', 'bill_required_above', 'claim_deadline_days', 'max_trip_days'].includes(k)) { v = num(v, cur[k]); if (v < 0) throw bad(k + ' cannot be negative'); }
    if (['roles', 'departments', 'expense_categories', 'airlines'].includes(k)) {
      if (!Array.isArray(v)) throw bad(k + ' must be a list');
      v = [...new Set(v.map((x) => str(x, 60)).filter(Boolean))];
      if (k === 'roles') for (const r of Object.values(WORKFLOW_ROLES).concat(['Admin', 'Employee'])) if (!v.includes(r)) v.push(r);
    }
    if (k === 'company_name') v = str(v, 120) || cur.company_name;
    st.run(k, JSON.stringify(v));
  }
  // ensure every role has a matrix row
  const ins = db.prepare('INSERT OR IGNORE INTO authority_matrix VALUES (?,?,?,?,?,?)');
  for (const r of getSettings().roles) ins.run(r, 'Economy', '3 Star', 3500, 900, 600);
  logAuth(ctx.req, 'SETTINGS_UPDATED', admin.email, admin.id, Object.keys(b).join(','));
  return { ok: true };
});
route('PUT', '/api/matrix', async (ctx) => {
  const admin = requireAdmin(ctx);
  const b = await readBody(ctx.req);
  if (!Array.isArray(b.rows)) throw bad('rows required');
  const st = db.prepare(`INSERT INTO authority_matrix VALUES (?,?,?,?,?,?) ON CONFLICT(role) DO UPDATE SET flight_class=excluded.flight_class,
     hotel_category=excluded.hotel_category, hotel_max_per_night=excluded.hotel_max_per_night, da_per_day=excluded.da_per_day, local_per_day=excluded.local_per_day`);
  for (const r of b.rows) {
    if (!FLIGHT_CLASS_RANK[r.flight_class] || !HOTEL_RANK[r.hotel_category]) throw bad('Invalid class/category for ' + r.role);
    st.run(str(r.role, 60), r.flight_class, r.hotel_category, num(r.hotel_max_per_night), num(r.da_per_day), num(r.local_per_day));
  }
  logAuth(ctx.req, 'MATRIX_UPDATED', admin.email, admin.id);
  return { ok: true };
});

// ---- Feature board -------------------------------------------------------
route('GET', '/api/features', (ctx) => {
  const u = requireUser(ctx);
  return all(`SELECT f.*, u.name by_name, EXISTS(SELECT 1 FROM feature_votes v WHERE v.feature_id=f.id AND v.user_id=?) voted
              FROM feature_requests f LEFT JOIN users u ON u.id=f.user_id ORDER BY f.votes DESC, f.id DESC`, u.id);
});
route('POST', '/api/features', async (ctx) => {
  const u = requireUser(ctx);
  const b = await readBody(ctx.req);
  const title = str(b.title, 150);
  if (title.length < 4) throw bad('Please describe the feature.');
  run('INSERT INTO feature_requests(user_id,title,description,created_at) VALUES (?,?,?,?)', u.id, title, str(b.description, 2000), nowIso());
  notify(adminIds().filter((x) => x !== u.id), null, `New feature suggestion from ${u.name}: ${title}`);
  return { ok: true };
});
route('POST', '/api/features/:id/vote', (ctx) => {
  const u = requireUser(ctx);
  const id = Number(ctx.params.id);
  const has = one('SELECT 1 x FROM feature_votes WHERE feature_id=? AND user_id=?', id, u.id);
  if (has) run('DELETE FROM feature_votes WHERE feature_id=? AND user_id=?', id, u.id);
  else run('INSERT INTO feature_votes VALUES (?,?)', id, u.id);
  run('UPDATE feature_requests SET votes=(SELECT COUNT(*) FROM feature_votes WHERE feature_id=?) WHERE id=?', id, id);
  return { ok: true };
});
route('PUT', '/api/features/:id', async (ctx) => {
  requireAdmin(ctx);
  const b = await readBody(ctx.req);
  const status = ['Proposed', 'Under Review', 'Planned', 'In Progress', 'Released', 'Declined'].includes(b.status) ? b.status : 'Proposed';
  run('UPDATE feature_requests SET status=? WHERE id=?', status, Number(ctx.params.id));
  return { ok: true };
});

route('GET', '/api/health', () => ({ ok: true, time: nowIso(), version: '1.0.0' }));

/* ------------------------------------------------------------------ */
/* Server                                                              */
/* ------------------------------------------------------------------ */
async function handler(req, res) {
  const url = new URL(req.url, 'http://localhost');
  const pathname = decodeURIComponent(url.pathname);
  try {
    if (pathname.startsWith('/api/')) {
      const ctx = { req, res, url, params: {}, user: authUser(req, url) };
      for (const r of routes) {
        if (r.method !== req.method) continue;
        const m = pathname.match(r.rx);
        if (!m) continue;
        r.keys.forEach((k, i) => { ctx.params[k] = m[i + 1]; });
        const out = await r.handler(ctx);
        if (out && out.__file) {
          const safeName = String(out.name).replace(/[^\w.\- ]/g, '_');
          res.writeHead(200, { 'Content-Type': out.mime || 'application/octet-stream', 'Content-Disposition': `inline; filename="${safeName}"`, 'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'private, no-store' });
          return fs.createReadStream(out.__file).pipe(res);
        }
        if (out && out.__raw !== undefined) {
          return send(res, 200, Buffer.isBuffer(out.__raw) ? out.__raw : Buffer.from(out.__raw, 'utf8'), { 'Content-Type': out.type, 'Content-Disposition': `attachment; filename="${out.filename}"`, 'Cache-Control': 'no-store' });
        }
        return send(res, 200, out === undefined ? { ok: true } : out, { 'Cache-Control': 'no-store' });
      }
      throw new HttpError(404, 'API route not found.');
    }
    // static files
    let p = path.normalize(path.join(PUBLIC_DIR, pathname));
    if (!p.startsWith(PUBLIC_DIR)) throw new HttpError(403, 'Forbidden');
    if (pathname === '/' || !fs.existsSync(p) || fs.statSync(p).isDirectory()) p = path.join(PUBLIC_DIR, 'index.html');
    const ext = path.extname(p).toLowerCase();
    const headers = { 'Content-Type': MIME[ext] || 'application/octet-stream', 'X-Content-Type-Options': 'nosniff' };
    headers['Cache-Control'] = ['.html', '.js', '.css', '.webmanifest', '.json'].includes(ext) ? 'no-cache' : 'public, max-age=86400';
    if (path.basename(p) === 'sw.js') headers['Service-Worker-Allowed'] = '/';
    res.writeHead(200, headers);
    fs.createReadStream(p).pipe(res);
  } catch (err) {
    const status = err.status || 500;
    if (status === 500) console.error(err);
    if (!res.headersSent) send(res, status, { error: status === 500 ? 'Internal server error: ' + err.message : err.message });
  }
}

let server;
if (process.env.HTTPS_KEY && process.env.HTTPS_CERT) {
  server = https.createServer({ key: fs.readFileSync(process.env.HTTPS_KEY), cert: fs.readFileSync(process.env.HTTPS_CERT) }, handler);
} else server = http.createServer(handler);

// periodic cleanup of expired sessions
setInterval(() => { try { run('DELETE FROM sessions WHERE expires_at < ?', nowIso()); } catch { /* ignore */ } }, 3600000).unref();

if (require.main === module) {
  server.listen(PORT, HOST, () => {
    const proto = process.env.HTTPS_KEY ? 'https' : 'http';
    console.log('==============================================================');
    console.log('  ABC Private Limited - Travel & Expense Management');
    console.log(`  Running at: ${proto}://localhost:${PORT}`);
    console.log(`  Database : ${DB_FILE}`);
    console.log('  Press Ctrl+C to stop.');
    console.log('==============================================================');
  });
}
module.exports = { server, db };
