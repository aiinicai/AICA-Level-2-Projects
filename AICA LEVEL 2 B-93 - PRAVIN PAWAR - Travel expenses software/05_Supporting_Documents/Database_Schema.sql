-- ABC Private Limited - Travel & Expense Management
-- SQLite database schema (auto-created by server.js on first run)
-- Database file: data/abc_travel.db

CREATE TABLE attachments (
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

CREATE TABLE auth_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT,
  user_id INTEGER,
  event TEXT NOT NULL,
  detail TEXT,
  ip TEXT,
  user_agent TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE authority_matrix (
  role TEXT PRIMARY KEY,
  flight_class TEXT NOT NULL,
  hotel_category TEXT NOT NULL,
  hotel_max_per_night REAL NOT NULL,
  da_per_day REAL NOT NULL,
  local_per_day REAL NOT NULL
);

CREATE TABLE expense_items (
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

CREATE TABLE feature_requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'Proposed',
  votes INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE TABLE feature_votes (
  feature_id INTEGER NOT NULL, user_id INTEGER NOT NULL, PRIMARY KEY (feature_id, user_id)
);

CREATE TABLE notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  request_id INTEGER,
  message TEXT NOT NULL,
  is_read INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE TABLE request_history (
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

CREATE TABLE sessions (
  token TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  ip TEXT,
  user_agent TEXT
);

CREATE TABLE settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE travel_requests (
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

CREATE TABLE users (
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

CREATE INDEX idx_hist_req ON request_history(request_id);

CREATE INDEX idx_items_req ON expense_items(request_id);

CREATE INDEX idx_notif_user ON notifications(user_id, is_read);

CREATE INDEX idx_req_emp ON travel_requests(employee_id);

CREATE INDEX idx_req_stage ON travel_requests(stage);

-- Default Matrix of Authority
INSERT INTO authority_matrix VALUES ('Managing Director','Business','5 Star',15000,3000,2000);
INSERT INTO authority_matrix VALUES ('Business Head','Premium Economy','5 Star',10000,2500,1500);
INSERT INTO authority_matrix VALUES ('HR Head','Economy','4 Star',7000,2000,1200);
INSERT INTO authority_matrix VALUES ('Finance Manager','Economy','4 Star',7000,2000,1200);
INSERT INTO authority_matrix VALUES ('Operations Manager','Economy','4 Star',6500,1800,1000);
INSERT INTO authority_matrix VALUES ('Sales Manager','Economy','4 Star',6000,1500,1000);
INSERT INTO authority_matrix VALUES ('Admin','Economy','4 Star',6000,1500,1000);
INSERT INTO authority_matrix VALUES ('Sales Executive','Economy','3 Star',4000,1000,800);
INSERT INTO authority_matrix VALUES ('Accountant','Economy','3 Star',4000,1000,800);
INSERT INTO authority_matrix VALUES ('Travel Assistant','Economy','3 Star',4000,1000,800);
INSERT INTO authority_matrix VALUES ('Employee','Economy','3 Star',3500,900,600);
