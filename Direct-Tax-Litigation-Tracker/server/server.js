// Litigation Tracker - secure demo/full-stack backend
// Node 22+ / Express / built-in SQLite

import express from 'express';
import helmet from 'helmet';
import cookieParser from 'cookie-parser';
import bcrypt from 'bcryptjs';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { DatabaseSync } from 'node:sqlite';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..');
const DATA_DIR = path.join(ROOT, 'data');
fs.mkdirSync(DATA_DIR, { recursive: true });
const db = new DatabaseSync(path.join(DATA_DIR, 'litigation.db'));

db.exec(`
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
CREATE TABLE IF NOT EXISTS groups (
  group_id TEXT PRIMARY KEY,
  group_name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('Admin','GroupUser')),
  group_id TEXT REFERENCES groups(group_id) ON DELETE SET NULL,
  status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active','Inactive')),
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS invites (
  email TEXT PRIMARY KEY,
  group_id TEXT NOT NULL REFERENCES groups(group_id),
  invited_by TEXT NOT NULL,
  used INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS companies (
  company_id TEXT PRIMARY KEY,
  group_id TEXT NOT NULL REFERENCES groups(group_id),
  entity_name TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  pan TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS masters (
  master_type TEXT NOT NULL,
  value TEXT NOT NULL,
  PRIMARY KEY(master_type, value)
);
CREATE TABLE IF NOT EXISTS proceedings (
  proceeding_id TEXT PRIMARY KEY,
  s_no INTEGER NOT NULL,
  company_id TEXT,
  group_id TEXT NOT NULL REFERENCES groups(group_id),
  financial_year TEXT,
  assessment_year TEXT,
  tax_year TEXT,
  applicable_act TEXT,
  relevant_section TEXT,
  nature_of_proceeding TEXT,
  proceeding_status TEXT,
  stage_of_proceeding TEXT,
  issue_involved TEXT,
  tax_demand_amount REAL DEFAULT 0,
  demand_type TEXT,
  demand_reference TEXT,
  demand_date TEXT,
  estimated_demand_basis TEXT,
  description_of_matter TEXT,
  last_hearing_date TEXT,
  next_hearing_date TEXT,
  proceeding_timeline_due_date TEXT,
  consultant_name TEXT,
  consultant_contact TEXT,
  remarks TEXT,
  created_by TEXT,
  updated_by TEXT,
  created_at TEXT,
  updated_at TEXT,
  FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS proceeding_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  proceeding_id TEXT NOT NULL REFERENCES proceedings(proceeding_id) ON DELETE CASCADE,
  at TEXT NOT NULL,
  by_user TEXT NOT NULL,
  field TEXT NOT NULL,
  from_value TEXT,
  to_value TEXT
);
CREATE TABLE IF NOT EXISTS auth_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT,
  event TEXT NOT NULL,
  success INTEGER NOT NULL,
  at TEXT NOT NULL,
  status_note TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_proc_group ON proceedings(group_id);
CREATE INDEX IF NOT EXISTS idx_proc_next_hearing ON proceedings(next_hearing_date);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
`);

function ensureColumn(table, column, definition) {
  const cols = db.prepare(`PRAGMA table_info(${table})`).all().map(r => r.name);
  if (!cols.includes(column)) db.exec(`ALTER TABLE ${table} ADD COLUMN ${column} ${definition}`);
}
ensureColumn('proceedings', 'demand_reference', 'TEXT');
ensureColumn('proceedings', 'demand_date', 'TEXT');
ensureColumn('proceedings', 'estimated_demand_basis', 'TEXT');

const STAGES = ['CPC','AO','Assessment','CIT(A)','ITAT','HC','SC'];
const STATUSES = ['Ongoing','Closed','Completed'];
const ACTS = ['Income Tax Act, 1961','Income Tax Act, 2025'];
const ENTITY_TYPES = ['Individual','Company','Partnership Firm','LLP'];
const DEMAND_TYPES = ['Raised','Estimated'];
const DEFAULT_NATURE = [
  'Assessment Proceedings','Appellate Proceedings – CIT(A)','Appellate Proceedings – ITAT',
  'Appellate Proceedings – High Court','Appellate Proceedings – Supreme Court','Demand Recovery Proceedings',
  'Refund Proceedings','Rectification Proceedings (154)','Revision Proceedings (263/264)','Penalty Proceedings',
  'Reassessment Proceedings (147/148)','Transfer Pricing Proceedings','Survey/Search Related Proceedings','Other Proceedings'
];
const DEFAULT_TEMPLATES = [
  'Filing of Return of Income','Tax Audit Report Filing (Form 3CA/3CB-3CD)','Response to Notice u/s 143(2)',
  'Response to Notice u/s 142(1)','Filing of Appeal before CIT(A)','Filing of Appeal before ITAT',
  'Rectification Application u/s 154','Stay of Demand Application','Lower/Nil TDS Certificate Application',
  'Advance Tax Computation & Compliance','Transfer Pricing Study/Report','Response to Reassessment Notice u/s 148'
];

const iso = (days = 0) => { const d = new Date(); d.setDate(d.getDate() + days); return d.toISOString().slice(0,10); };
const uid = (p) => `${p}_${crypto.randomBytes(5).toString('hex')}`;
const sha = (s) => crypto.createHash('sha256').update(s).digest('hex');
const json = (r) => { try { return r.json; } catch { return {}; } };

function yearBefore(ay) {
  const [a] = String(ay || '').split('-');
  const start = Number.parseInt(a,10) - 1;
  return Number.isFinite(start) ? `${start}-${String(start+1).slice(2)}` : '';
}
function sectionFor(nature='') {
  if (nature.includes('154')) return '154';
  if (nature.includes('147/148')) return '147/148';
  if (nature.includes('263')) return '263';
  if (nature.includes('270A')) return '270A';
  if (nature.includes('CIT(A)')) return '246A';
  if (nature.includes('ITAT')) return '253';
  return '143(3)';
}

function seed() {
  const count = db.prepare('SELECT COUNT(*) AS c FROM users').get().c;
  if (count) return;
  const groups = [
    ['GRP001','Sharma Family & Enterprises Group'],['GRP002','Nexa Industries Group']
  ];
  const companies = [
    ['C001','GRP001','Rohit Sharma','Individual','ABCDE1234F'],
    ['C002','GRP001','Sharma Textiles Pvt Ltd','Company','ABCDE5678G'],
    ['C003','GRP001','Sharma & Sons LLP','LLP','ABCDE9012H'],
    ['C004','GRP002','Nexa Industries Ltd','Company','NEXAI1234K'],
    ['C005','GRP002','Nexa Infra Partners','Partnership Firm','NEXAP5678L']
  ];
  db.exec('BEGIN');
  try {
    const gi = db.prepare('INSERT INTO groups(group_id,group_name) VALUES(?,?)');
    groups.forEach(g => gi.run(...g));
    const ci = db.prepare('INSERT INTO companies(company_id,group_id,entity_name,entity_type,pan) VALUES(?,?,?,?,?)');
    companies.forEach(c => ci.run(...c));
    const ui = db.prepare('INSERT INTO users(user_id,name,email,password_hash,role,group_id,status,created_at) VALUES(?,?,?,?,?,?,?,?)');
    ui.run('admin','Admin (Consultant)','admin@taxconsult.in',bcrypt.hashSync('Admin@123',12),'Admin',null,'Active',iso(-120));
    ui.run('sharma_user','Rohit Sharma','rohit@sharmagroup.in',bcrypt.hashSync('User@123',12),'GroupUser','GRP001','Active',iso(-90));
    ui.run('nexa_user','Priya Menon','priya@nexaindustries.in',bcrypt.hashSync('User@123',12),'GroupUser','GRP002','Active',iso(-60));
    db.prepare('INSERT INTO invites(email,group_id,invited_by,used,created_at) VALUES(?,?,?,?,?)').run('cfo@nexaindustries.in','GRP002','admin',0,iso(-1));
    const mi = db.prepare('INSERT INTO masters(master_type,value) VALUES(?,?)');
    DEFAULT_NATURE.forEach(v=>mi.run('nature',v)); DEFAULT_TEMPLATES.forEach(v=>mi.run('template',v));
    const base = [
      ['C001','GRP001','2023-24','Appellate Proceedings – CIT(A)','Ongoing','CIT(A)','Disallowance u/s 14A',845000,'Raised',4,40],
      ['C002','GRP001','2022-23','Reassessment Proceedings (147/148)','Ongoing','AO','Alleged escapement of income - unsecured loans',3120000,'Estimated',2,15],
      ['C002','GRP001','2021-22','Appellate Proceedings – ITAT','Ongoing','ITAT','Transfer pricing adjustment on export sales',5670000,'Raised',25,-5],
      ['C003','GRP001','2023-24','Rectification Proceedings (154)','Completed','CPC','TDS credit mismatch rectified',0,'Raised',null,-60],
      ['C001','GRP001','2024-25','Assessment Proceedings','Ongoing','Assessment','Scrutiny - capital gains on property sale',210000,'Estimated',6,20],
      ['C004','GRP002','2023-24','Appellate Proceedings – High Court','Ongoing','HC','Validity of reopening beyond limitation',12500000,'Raised',45,10],
      ['C004','GRP002','2022-23','Penalty Proceedings','Ongoing','AO','Penalty u/s 270A on TP adjustment',980000,'Raised',1,-3],
      ['C004','GRP002','2024-25','Refund Proceedings','Ongoing','CPC','Refund withheld pending verification',0,'Raised',null,30],
      ['C005','GRP002','2023-24','Demand Recovery Proceedings','Ongoing','AO','Stay of demand pending appeal outcome',1450000,'Raised',12,5],
      ['C005','GRP002','2021-22','Appellate Proceedings – ITAT','Closed','ITAT','Depreciation on goodwill - decided in favour',0,'Raised',null,-100],
      ['C002','GRP001','2024-25','Transfer Pricing Proceedings','Ongoing','Assessment','TP study for royalty payments to AE',0,'Estimated',3,25],
      ['C003','GRP001','2022-23','Survey/Search Related Proceedings','Ongoing','AO','Follow-up assessment post survey u/s 133A',640000,'Estimated',20,-10]
    ];
    const pi = db.prepare(`INSERT INTO proceedings
      (proceeding_id,s_no,company_id,group_id,financial_year,assessment_year,tax_year,applicable_act,relevant_section,nature_of_proceeding,
       proceeding_status,stage_of_proceeding,issue_involved,tax_demand_amount,demand_type,demand_reference,demand_date,estimated_demand_basis,description_of_matter,last_hearing_date,next_hearing_date,
       proceeding_timeline_due_date,consultant_name,consultant_contact,remarks,created_by,updated_by,created_at,updated_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`);
    base.forEach((b,i)=>{
      const [company,group,ay,nature,status,stage,issue,demand,demandType,hear,due]=b;
      const demandRef = demand > 0 ? (demandType === 'Raised' ? 'Demand / Order Ref. — Demo' : 'Notice / Estimate Ref. — Demo') : '';
      const demandDate = demand > 0 ? iso(-15) : null;
      const estimatedBasis = demandType === 'Estimated' ? 'Departmental estimate / working assessment under monitoring.' : '';
      pi.run(uid('proc'),i+1,company,group,yearBefore(ay),ay,null,'Income Tax Act, 1961',sectionFor(nature),nature,status,stage,issue,demand,demandType,demandRef,demandDate,estimatedBasis,
        `${issue}. Matter under active monitoring; refer remarks for latest update.`, hear!=null?iso(hear-30):iso(-45), hear!=null?iso(hear):null, iso(due),
        'Admin (Consultant)','+91-98xxxxxx01','Awaiting further correspondence from the department.','admin','admin',iso(-30),iso(-2));
    });

    db.exec('COMMIT');
  } catch(e) { db.exec('ROLLBACK'); throw e; }
}
seed();

const publicUser = (u) => u && ({ user_id:u.user_id,name:u.name,email:u.email,role:u.role,group_id:u.group_id,status:u.status,created_at:u.created_at });
const groupRow = (id) => db.prepare('SELECT group_id,group_name FROM groups WHERE group_id=?').get(id);
const companyRows = (groupId, admin) => admin ? db.prepare('SELECT company_id,group_id,entity_name,entity_type,pan FROM companies ORDER BY entity_name').all() : db.prepare('SELECT company_id,group_id,entity_name,entity_type,pan FROM companies WHERE group_id=? ORDER BY entity_name').all(groupId);
const groupRows = (admin, groupId) => admin ? db.prepare('SELECT group_id,group_name FROM groups ORDER BY group_name').all() : (groupRow(groupId) ? [groupRow(groupId)] : []);
const userRows = (admin, userId) => admin ? db.prepare('SELECT user_id,name,email,role,group_id,status,created_at FROM users ORDER BY name').all() : db.prepare('SELECT user_id,name,email,role,group_id,status,created_at FROM users WHERE user_id=?').all(userId);
const inviteRows = (admin) => admin ? db.prepare('SELECT email,group_id,invited_by,used,created_at FROM invites ORDER BY email').all() : [];
const masterRows = (type) => db.prepare('SELECT value FROM masters WHERE master_type=? ORDER BY rowid').all(type).map(x=>x.value);

function proceedingsFor(user) {
  const rows = user.role === 'Admin'
    ? db.prepare('SELECT * FROM proceedings ORDER BY s_no').all()
    : db.prepare('SELECT * FROM proceedings WHERE group_id=? ORDER BY s_no').all(user.group_id);
  const historyStmt = db.prepare('SELECT at,by_user AS by,field,from_value AS "from",to_value AS "to" FROM proceeding_history WHERE proceeding_id=? ORDER BY id');
  return rows.map(r => ({...r, history: historyStmt.all(r.proceeding_id)}));
}
function appState(user) {
  return {
    groups: groupRows(user.role==='Admin', user.group_id),
    companies: companyRows(user.group_id, user.role==='Admin'),
    users: userRows(user.role==='Admin', user.user_id),
    invited_emails: inviteRows(user.role==='Admin'),
    masterNature: masterRows('nature'),
    masterTemplates: masterRows('template')
  };
}

function makeSession(userId, res) {
  const raw = crypto.randomBytes(48).toString('base64url');
  const hash = sha(raw); const exp = Date.now() + 1000*60*60*8;
  db.prepare('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)').run(hash,userId,exp);
  res.cookie('lt_session', raw, {httpOnly:true, secure:process.env.NODE_ENV==='production', sameSite:'strict', maxAge:1000*60*60*8, path:'/'});
}
function clearSession(req,res) {
  const raw = req.cookies?.lt_session; if (raw) db.prepare('DELETE FROM sessions WHERE token_hash=?').run(sha(raw));
  res.clearCookie('lt_session',{httpOnly:true,secure:process.env.NODE_ENV==='production',sameSite:'strict',path:'/'});
}
function requireAuth(req,res,next) {
  const raw = req.cookies?.lt_session;
  if (!raw) return res.status(401).json({error:'Authentication required'});
  const row = db.prepare(`SELECT u.* FROM sessions s JOIN users u ON u.user_id=s.user_id WHERE s.token_hash=? AND s.expires_at>?`).get(sha(raw),Date.now());
  if (!row || row.status!=='Active') { clearSession(req,res); return res.status(401).json({error:'Session expired'}); }
  req.user = row; next();
}
function requireAdmin(req,res,next){ if(req.user.role!=='Admin') return res.status(403).json({error:'Administrator access required'}); next(); }
function logAuth(userId,event,success,statusNote=''){ db.prepare('INSERT INTO auth_logs(user_id,event,success,at,status_note) VALUES(?,?,?,?,?)').run(userId,event,success?1:0,new Date().toISOString(),statusNote); }

const app = express();
app.disable('x-powered-by');
app.use(helmet({contentSecurityPolicy:false}));
app.use(express.json({limit:'1mb'}));
app.use(cookieParser());
app.use(express.urlencoded({extended:false,limit:'100kb'}));

const authLimiter = new Map();
function authRateLimit(req,res,next){
  const ip = req.ip || 'unknown'; const now=Date.now(); const entry=authLimiter.get(ip) || {count:0,reset:now+15*60*1000};
  if(now>entry.reset){entry.count=0;entry.reset=now+15*60*1000;} entry.count++;
  authLimiter.set(ip,entry); if(entry.count>25) return res.status(429).json({error:'Too many authentication attempts. Try again later.'}); next();
}

app.get('/api/health',(req,res)=>res.json({ok:true,service:'litigation-tracker-api',database:'sqlite',time:new Date().toISOString()}));
app.post('/api/auth/login',authRateLimit,async(req,res)=>{
  const {userId,password}=req.body||{}; const u=db.prepare('SELECT * FROM users WHERE user_id=?').get(String(userId||'').trim());
  const ok=!!u && u.status==='Active' && await bcrypt.compare(String(password||''),u.password_hash);
  logAuth(userId||'', 'login', ok, !u?'unknown user':u.status!=='Active'?'inactive account':ok?'':'invalid password');
  if(!ok) return res.status(401).json({error:'Invalid credentials or inactive account'});
  makeSession(u.user_id,res); res.json({user:publicUser(u),db:appState(u),proc:{list:proceedingsFor(u),nextSNo:(db.prepare('SELECT COALESCE(MAX(s_no),0)+1 AS n FROM proceedings').get().n)}});
});
app.post('/api/auth/signup',authRateLimit,async(req,res)=>{
  const {name,email,userId,password}=req.body||{};
  if(!name||!email||!userId||!password||String(password).length<8) return res.status(400).json({error:'Name, email, user ID and password (8+ characters) are required'});
  if(db.prepare('SELECT 1 FROM users WHERE user_id=?').get(userId)) return res.status(409).json({error:'User ID already exists'});
  const isFirst=db.prepare('SELECT COUNT(*) AS c FROM users').get().c===0;
  let role='GroupUser', groupId=null, invite=null;
  if(!isFirst){ invite=db.prepare('SELECT * FROM invites WHERE lower(email)=lower(?) AND used=0').get(email); if(!invite) return res.status(403).json({error:'This email has not been invited by the administrator'}); groupId=invite.group_id; }
  const ph=await bcrypt.hash(String(password),12); const now=new Date().toISOString();
  db.exec('BEGIN'); try{
    db.prepare('INSERT INTO users(user_id,name,email,password_hash,role,group_id,status,created_at) VALUES(?,?,?,?,?,?,?,?)').run(userId,name,email,ph,role,groupId,'Active',now);
    if(invite) db.prepare('UPDATE invites SET used=1 WHERE email=?').run(invite.email);
    db.exec('COMMIT');
  }catch(e){db.exec('ROLLBACK');return res.status(400).json({error:'Could not create account'});}
  const u=db.prepare('SELECT * FROM users WHERE user_id=?').get(userId); logAuth(userId,'signup',true,role==='Admin'?'bootstrap admin':'invited signup'); makeSession(userId,res);
  res.status(201).json({user:publicUser(u),db:appState(u),proc:{list:proceedingsFor(u),nextSNo:(db.prepare('SELECT COALESCE(MAX(s_no),0)+1 AS n FROM proceedings').get().n)}});
});
app.post('/api/auth/logout',requireAuth,(req,res)=>{logAuth(req.user.user_id,'logout',true,'');clearSession(req,res);res.json({ok:true});});
app.get('/api/bootstrap',requireAuth,(req,res)=>res.json({user:publicUser(req.user),db:appState(req.user),proc:{list:proceedingsFor(req.user),nextSNo:(db.prepare('SELECT COALESCE(MAX(s_no),0)+1 AS n FROM proceedings').get().n)}}));

app.put('/api/admin/state',requireAuth,requireAdmin,async(req,res)=>{
  const next=req.body||{};
  if(!Array.isArray(next.companies)||!Array.isArray(next.users)||!Array.isArray(next.groups)) return res.status(400).json({error:'Invalid state'});
  db.exec('BEGIN');
  try{
    const existingUsers = db.prepare('SELECT user_id,password_hash,created_at,role FROM users').all();
    const oldById=new Map(existingUsers.map(u=>[u.user_id,u]));
    const oldGroups=new Set(db.prepare('SELECT group_id FROM groups').all().map(x=>x.group_id));
    const oldCompanies=new Set(db.prepare('SELECT company_id FROM companies').all().map(x=>x.company_id));
    // Groups: insert/update; do not delete groups referenced by data.
    for(const g of next.groups){ if(!g.group_id||!g.group_name) continue; db.prepare('INSERT INTO groups(group_id,group_name) VALUES(?,?) ON CONFLICT(group_id) DO UPDATE SET group_name=excluded.group_name').run(g.group_id,g.group_name); }
    // Companies: insert/update.
    for(const c of next.companies){ if(!c.company_id||!c.group_id||!c.entity_name) continue; if(!groupRow(c.group_id)) throw new Error('Invalid group'); db.prepare(`INSERT INTO companies(company_id,group_id,entity_name,entity_type,pan) VALUES(?,?,?,?,?) ON CONFLICT(company_id) DO UPDATE SET group_id=excluded.group_id,entity_name=excluded.entity_name,entity_type=excluded.entity_type,pan=excluded.pan`).run(c.company_id,c.group_id,c.entity_name,c.entity_type,c.pan); }
    const incomingCompanyIds=new Set(next.companies.map(c=>c.company_id));
    for(const c of db.prepare('SELECT company_id FROM companies').all()){ if(!incomingCompanyIds.has(c.company_id)) db.prepare('DELETE FROM companies WHERE company_id=?').run(c.company_id); }
    // Admin may add/update users. Server owns password hashes. Existing password hashes are preserved.
    for(const u of next.users){
      if(!u.user_id||!u.name||!u.email||!u.role) continue;
      const old=oldById.get(u.user_id);
      if(old){
        db.prepare('UPDATE users SET name=?,email=?,role=?,group_id=?,status=? WHERE user_id=?').run(u.name,u.email,u.role,u.role==='Admin'?null:u.group_id,u.status||'Active',u.user_id);
        if(u.password){ db.prepare('UPDATE users SET password_hash=? WHERE user_id=?').run(await bcrypt.hash(String(u.password),12),u.user_id); }
      } else {
        const ph=await bcrypt.hash(String(u.password||crypto.randomBytes(12).toString('base64url')),12);
        db.prepare('INSERT INTO users(user_id,name,email,password_hash,role,group_id,status,created_at) VALUES(?,?,?,?,?,?,?,?)').run(u.user_id,u.name,u.email,ph,u.role,u.role==='Admin'?null:u.group_id,u.status||'Active',u.created_at||new Date().toISOString());
      }
    }
    if(Array.isArray(next.invited_emails)){
      for(const i of next.invited_emails){ if(i.email&&i.group_id) db.prepare(`INSERT INTO invites(email,group_id,invited_by,used,created_at) VALUES(?,?,?,?,?) ON CONFLICT(email) DO UPDATE SET group_id=excluded.group_id,invited_by=excluded.invited_by,used=excluded.used`).run(i.email,i.group_id,i.invited_by||req.user.user_id,i.used?1:0,i.created_at||new Date().toISOString()); }
    }
    if(Array.isArray(next.masterNature)){
      db.prepare('DELETE FROM masters WHERE master_type=?').run('nature'); for(const v of next.masterNature) db.prepare('INSERT OR IGNORE INTO masters(master_type,value) VALUES(?,?)').run('nature',v);
    }
    if(Array.isArray(next.masterTemplates)){
      db.prepare('DELETE FROM masters WHERE master_type=?').run('template'); for(const v of next.masterTemplates) db.prepare('INSERT OR IGNORE INTO masters(master_type,value) VALUES(?,?)').run('template',v);
    }
    db.exec('COMMIT');
  }catch(e){db.exec('ROLLBACK');return res.status(400).json({error:e.message||'Could not save admin state'});}
  res.json({db:appState(req.user)});
});

app.post('/api/admin/users/:userId/password',requireAuth,requireAdmin,async(req,res)=>{
  const target=req.params.userId; const pwd=String(req.body?.password||'');
  if(pwd.length<8) return res.status(400).json({error:'Password must be at least 8 characters'});
  const hash=await bcrypt.hash(pwd,12); const r=db.prepare('UPDATE users SET password_hash=? WHERE user_id=?').run(hash,target);
  if(!r.changes) return res.status(404).json({error:'User not found'});
  db.prepare('INSERT INTO auth_logs(user_id,event,success,at,status_note) VALUES(?,?,?,?,?)').run(req.user.user_id,'password_reset',1,new Date().toISOString(),`reset for ${target}`);
  res.json({ok:true});
});

app.put('/api/proceedings/state',requireAuth,(req,res)=>{
  const payload=req.body||{}; if(!Array.isArray(payload.list)) return res.status(400).json({error:'Invalid proceedings payload'});
  const incoming=payload.list;
  db.exec('BEGIN');
  try{
    const current=proceedingsFor(req.user); const currentMap=new Map(current.map(x=>[x.proceeding_id,x]));
    if(req.user.role==='Admin'){
      const existingIds=new Set(db.prepare('SELECT proceeding_id FROM proceedings').all().map(x=>x.proceeding_id));
      const incomingIds=new Set(incoming.map(x=>x.proceeding_id));
      for(const p of incoming){
        if(!p.proceeding_id||!p.group_id) continue;
        const company = p.company_id ? db.prepare('SELECT * FROM companies WHERE company_id=?').get(p.company_id) : null;
        if(p.company_id && !company) throw new Error('Invalid company');
        if(company && company.group_id!==p.group_id) throw new Error('Company/group mismatch');
        const row={...p,group_id:company?.group_id||p.group_id,updated_by:req.user.user_id,updated_at:iso()};
        const exists=existingIds.has(p.proceeding_id);
        if(exists){
          db.prepare(`UPDATE proceedings SET s_no=?,company_id=?,group_id=?,financial_year=?,assessment_year=?,tax_year=?,applicable_act=?,relevant_section=?,nature_of_proceeding=?,proceeding_status=?,stage_of_proceeding=?,issue_involved=?,tax_demand_amount=?,demand_type=?,demand_reference=?,demand_date=?,estimated_demand_basis=?,description_of_matter=?,last_hearing_date=?,next_hearing_date=?,proceeding_timeline_due_date=?,consultant_name=?,consultant_contact=?,remarks=?,updated_by=?,updated_at=? WHERE proceeding_id=?`).run(row.s_no,row.company_id||null,row.group_id,row.financial_year,row.assessment_year,row.tax_year||null,row.applicable_act,row.relevant_section,row.nature_of_proceeding,row.proceeding_status,row.stage_of_proceeding,row.issue_involved,Number(row.tax_demand_amount)||0,row.demand_type,row.demand_reference||null,row.demand_date||null,row.estimated_demand_basis||null,row.description_of_matter,row.last_hearing_date||null,row.next_hearing_date||null,row.proceeding_timeline_due_date||null,row.consultant_name,row.consultant_contact,row.remarks,row.updated_by,row.updated_at,p.proceeding_id);
        } else {
          db.prepare(`INSERT INTO proceedings(proceeding_id,s_no,company_id,group_id,financial_year,assessment_year,tax_year,applicable_act,relevant_section,nature_of_proceeding,proceeding_status,stage_of_proceeding,issue_involved,tax_demand_amount,demand_type,demand_reference,demand_date,estimated_demand_basis,description_of_matter,last_hearing_date,next_hearing_date,proceeding_timeline_due_date,consultant_name,consultant_contact,remarks,created_by,updated_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`).run(p.proceeding_id,p.s_no,p.company_id||null,row.group_id,p.financial_year,p.assessment_year,p.tax_year||null,p.applicable_act,p.relevant_section,p.nature_of_proceeding,p.proceeding_status,p.stage_of_proceeding,p.issue_involved,Number(p.tax_demand_amount)||0,p.demand_type,p.demand_reference||null,p.demand_date||null,p.estimated_demand_basis||null,p.description_of_matter,p.last_hearing_date||null,p.next_hearing_date||null,p.proceeding_timeline_due_date||null,p.consultant_name,p.consultant_contact,p.remarks,req.user.user_id,req.user.user_id,iso(),iso());
        }
        if(currentMap.has(p.proceeding_id)){
          const old=currentMap.get(p.proceeding_id); for(const field of ['company_id','assessment_year','applicable_act','relevant_section','nature_of_proceeding','proceeding_status','stage_of_proceeding','issue_involved','tax_demand_amount','demand_type','demand_reference','demand_date','estimated_demand_basis','description_of_matter','last_hearing_date','next_hearing_date','proceeding_timeline_due_date','consultant_name','consultant_contact','remarks']){
            if(String(old[field]??'')!==String(p[field]??'')) db.prepare('INSERT INTO proceeding_history(proceeding_id,at,by_user,field,from_value,to_value) VALUES(?,?,?,?,?,?)').run(p.proceeding_id,new Date().toISOString(),req.user.user_id,field,String(old[field]??''),String(p[field]??''));
          }
        }
      }
      for(const id of existingIds){ if(!incomingIds.has(id)) db.prepare('DELETE FROM proceedings WHERE proceeding_id=?').run(id); }
    } else {
      // Group users can only change remarks on their own group's records.
      const byId=new Map(incoming.map(p=>[p.proceeding_id,p]));
      for(const old of current){
        const p=byId.get(old.proceeding_id); if(!p) continue;
        const newRemarks=String(p.remarks??''); if(newRemarks!==String(old.remarks??'')){
          db.prepare('UPDATE proceedings SET remarks=?,updated_by=?,updated_at=? WHERE proceeding_id=? AND group_id=?').run(newRemarks,req.user.user_id,iso(),old.proceeding_id,req.user.group_id);
          db.prepare('INSERT INTO proceeding_history(proceeding_id,at,by_user,field,from_value,to_value) VALUES(?,?,?,?,?,?)').run(old.proceeding_id,new Date().toISOString(),req.user.user_id,'remarks',String(old.remarks??''),newRemarks);
        }
      }
    }
    db.exec('COMMIT');
  }catch(e){db.exec('ROLLBACK');return res.status(400).json({error:e.message||'Could not save proceedings'});}
  res.json({proc:{list:proceedingsFor(req.user),nextSNo:(db.prepare('SELECT COALESCE(MAX(s_no),0)+1 AS n FROM proceedings').get().n)}});
});

app.get('/api/admin/audit',requireAuth,requireAdmin,(req,res)=>{
  res.json({logs:db.prepare('SELECT id,user_id,event,success,at,status_note FROM auth_logs ORDER BY id DESC LIMIT 200').all()});
});

const publicDir = path.join(ROOT,'dist');
if(fs.existsSync(publicDir)){
  app.use(express.static(publicDir));
  app.get(/.*/,(req,res)=>res.sendFile(path.join(publicDir,'index.html')));
}

const port=Number(process.env.PORT||4000);
app.listen(port,()=>console.log(`Litigation Tracker API listening on http://localhost:${port}`));
