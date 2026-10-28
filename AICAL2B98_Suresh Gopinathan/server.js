"use strict";
/*
 * TickTrail self-hosted server.
 * Plain Node.js (22.13 or later), no packages to install.
 *   node server.js                      start the server
 *   node server.js --backup <folder>    copy the database and PDFs to a backup folder
 *   node server.js --import <folder>    load exported JSON documents (<folder>/<collection>/<id>.json)
 *   node server.js --reset-password <username>   set a temporary password for a user
 *   node server.js --list-users         show user names and roles
 */
const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
let DatabaseSync;
try{ ({ DatabaseSync } = require("node:sqlite")); }
catch(e){ console.error(`TickTrail needs Node.js 22.13 or later (this is ${process.version}). Install the current LTS from https://nodejs.org and try again.`); process.exit(1); }

const ROOT = __dirname;
const CONFIG_FILE = path.join(ROOT, "config.json");
const DEFAULTS = {
  host: "127.0.0.1",          // 127.0.0.1 when Caddy (or another HTTPS proxy) runs on the same machine; 0.0.0.0 to serve the office network directly
  port: 8080,
  dataDir: "data",
  trustProxy: true,           // read the visitor's address and https from the proxy's X-Forwarded-* headers
  allowSignup: true,          // let new staff create a login and send an access request
  idleMinutes: 30,            // sign out after this long without activity
  maxSessionHours: 12,        // sign out after this long in any case
};
const CFG = { ...DEFAULTS, ...(fs.existsSync(CONFIG_FILE) ? JSON.parse(fs.readFileSync(CONFIG_FILE, "utf8")) : {}) };
const DATA = path.resolve(ROOT, CFG.dataDir);
const BLOBS = path.join(DATA, "blobs");
fs.mkdirSync(BLOBS, { recursive: true });

// ---------------------------------------------------------------- database
const db = new DatabaseSync(path.join(DATA, "ticktrail.db"));
db.exec(`
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS docs (path TEXT PRIMARY KEY, coll TEXT NOT NULL, id TEXT NOT NULL, data TEXT NOT NULL, v INTEGER NOT NULL, updated INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS docs_coll ON docs(coll);
CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE COLLATE NOCASE, name TEXT NOT NULL,
  hash TEXT NOT NULL, salt TEXT NOT NULL, must_change INTEGER NOT NULL DEFAULT 0, owner INTEGER NOT NULL DEFAULT 0,
  created INTEGER NOT NULL, set_at INTEGER, last_login INTEGER, prev_login INTEGER, fails INTEGER NOT NULL DEFAULT 0, lock_until INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, uid TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, created INTEGER NOT NULL, seen INTEGER NOT NULL, ip TEXT);
CREATE TABLE IF NOT EXISTS blobs (id TEXT PRIMARY KEY, name TEXT, type TEXT NOT NULL, size INTEGER NOT NULL, by TEXT NOT NULL, created INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS names (id TEXT PRIMARY KEY, name TEXT NOT NULL);
`);
const q = sql => db.prepare(sql);
const SQL = {
  docGet: q("SELECT data, v FROM docs WHERE path = ?"),
  docList: q("SELECT id, data, v FROM docs WHERE coll = ? ORDER BY id"),
  docPut: q("INSERT INTO docs (path, coll, id, data, v, updated) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(path) DO UPDATE SET data = excluded.data, v = excluded.v, updated = excluded.updated"),
  docDel: q("DELETE FROM docs WHERE path = ?"),
  docCount: q("SELECT COUNT(*) n FROM docs"),
  userById: q("SELECT * FROM users WHERE id = ?"),
  userByName: q("SELECT * FROM users WHERE username = ?"),
  userCount: q("SELECT COUNT(*) n FROM users"),
  userAll: q("SELECT id, username, name, owner, must_change, last_login FROM users ORDER BY created"),
  userIns: q("INSERT INTO users (id, username, name, hash, salt, must_change, owner, created, set_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"),
  userPw: q("UPDATE users SET hash = ?, salt = ?, must_change = ?, set_at = ?, fails = 0, lock_until = 0 WHERE id = ?"),
  userFail: q("UPDATE users SET fails = ?, lock_until = ? WHERE id = ?"),
  userLogin: q("UPDATE users SET prev_login = last_login, last_login = ?, fails = 0, lock_until = 0 WHERE id = ?"),
  userDel: q("DELETE FROM users WHERE id = ? AND owner = 0"),
  ownerGet: q("SELECT id FROM users WHERE owner = 1"),
  sessGet: q("SELECT * FROM sessions WHERE token = ?"),
  sessIns: q("INSERT INTO sessions (token, uid, created, seen, ip) VALUES (?, ?, ?, ?, ?)"),
  sessSeen: q("UPDATE sessions SET seen = ? WHERE token = ?"),
  sessDel: q("DELETE FROM sessions WHERE token = ?"),
  sessDelUser: q("DELETE FROM sessions WHERE uid = ?"),
  sessPrune: q("DELETE FROM sessions WHERE seen < ? OR created < ?"),
  blobIns: q("INSERT INTO blobs (id, name, type, size, by, created) VALUES (?, ?, ?, ?, ?, ?)"),
  blobGet: q("SELECT * FROM blobs WHERE id = ?"),
  blobDel: q("DELETE FROM blobs WHERE id = ?"),
  blobMine: q("SELECT * FROM blobs WHERE by = ? ORDER BY created DESC"),
  blobAll: q("SELECT * FROM blobs ORDER BY created DESC"),
  blobUsage: q("SELECT COUNT(*) n, COALESCE(SUM(size), 0) bytes FROM blobs"),
  nameGet: q("SELECT name FROM names WHERE id = ?"),
  namePut: q("INSERT INTO names (id, name) VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET name = excluded.name"),
};
// one rising version number for every write (also across delete and re-create), so browsers can drop stale updates
let SEQ = Math.max(Date.now(), db.prepare("SELECT COALESCE(MAX(v), 0) m FROM docs").get().m);
const nextV = () => ++SEQ;
function tx(fn){ db.exec("BEGIN IMMEDIATE"); try{ const r = fn(); db.exec("COMMIT"); return r; } catch(e){ db.exec("ROLLBACK"); throw e; } }

// ---------------------------------------------------------------- helpers
const now = () => Date.now();
const newId = () => "u_" + crypto.randomBytes(16).toString("base64url").slice(0, 22);
const blobId = () => crypto.randomBytes(16).toString("hex");
const SEG = /^[A-Za-z0-9_\-.~:@+]{1,200}$/;
function splitPath(p, wantDoc){
  if(typeof p !== "string") return null;
  const s = p.split("/");
  if(s.length < 1 || s.length > 16 || s.some(x => !SEG.test(x) || x === "." || x === "..")) return null;
  if(wantDoc ? s.length % 2 !== 0 : s.length % 2 !== 1) return null;
  return s;
}
class ApiError extends Error { constructor(status, code, message){ super(message); this.status = status; this.code = code; } }
const deny = () => new ApiError(403, "permission_denied", "You do not have access to this.");
const bad = m => new ApiError(400, "invalid_argument", m);
function isPlainObject(x){ return x !== null && typeof x === "object" && !Array.isArray(x); }
function merge(target, patch){
  const out = { ...target };
  for(const [k, v] of Object.entries(patch)){
    if(isPlainObject(v) && isPlainObject(out[k])) out[k] = merge(out[k], v);
    else out[k] = v;
  }
  return out;
}
function depth(x, d = 0){ if(d > 32) return d; if(x && typeof x === "object") return Math.max(d, ...Object.values(x).map(v => depth(v, d + 1))); return d; }

// passwords: scrypt with a per-user salt
function hashPw(pw, saltB64){
  const salt = saltB64 ? Buffer.from(saltB64, "base64") : crypto.randomBytes(16);
  const hash = crypto.scryptSync(String(pw), salt, 32, { N: 32768, r: 8, p: 1, maxmem: 64 * 1024 * 1024 });
  return { hash: hash.toString("base64"), salt: salt.toString("base64") };
}
function pwOk(user, pw){
  const h = Buffer.from(hashPw(pw, user.salt).hash, "base64"), want = Buffer.from(user.hash, "base64");
  return h.length === want.length && crypto.timingSafeEqual(h, want);
}
function pwProblem(pw){
  if(typeof pw !== "string" || pw.length < 8 || !/[A-Za-z]/.test(pw) || !/\d/.test(pw)) return "Use at least 8 characters with letters and numbers.";
  if(pw.length > 200) return "That password is too long.";
  return "";
}
function tempPassword(){
  const words = "Ledger Audit Ticket Vouch Folio Margin Credit Debit Tally Annex Cipher Stamp".split(" ");
  return words[crypto.randomInt(words.length)] + "-" + crypto.randomInt(1000, 9999) + "-" + words[crypto.randomInt(words.length)];
}

// ---------------------------------------------------------------- documents
function readDoc(p){ const r = SQL.docGet.get(p); return r ? { data: JSON.parse(r.data), v: r.v } : null; }
function memberOf(uid){ return readDoc("members/" + uid)?.data || null; }

// Who is asking, and what may they do?
function ctxFor(user){
  const m = memberOf(user.id);
  const owner = !!user.owner;
  const admin = owner || (m && m.status === "active" && m.role === "admin");
  const approved = admin || (m && m.status === "active");
  return { uid: user.id, owner, admin: !!admin, approved: !!approved };
}
// Mirrors the hosted app's rules, plus: nobody sees firm data until an admin approves them.
function canRead(c, segs){
  const top = segs[0], id = segs[1];
  if(top === "auth") return false;
  if(top === "requests") return c.admin || (segs.length === 2 && id === c.uid);
  if(top === "members") return c.approved || (segs.length === 2 && id === c.uid);
  if(top === "rates") return c.admin;
  return c.approved;
}
function canWrite(c, segs){
  const top = segs[0], id = segs[1];
  if(top === "auth") return false;
  if(top === "requests") return c.admin || (segs.length === 2 && id === c.uid);
  if(top === "members" || top === "rates" || top === "library") return c.admin;
  return c.approved;
}
function writeDoc(c, op, p, data){
  const segs = splitPath(p, true); if(!segs) throw bad("Bad document path.");
  if(!canWrite(c, segs)) throw deny();
  if(op !== "delete"){
    if(!isPlainObject(data)) throw bad("A document must be an object.");
    if(depth(data) > 32) throw bad("The document is nested too deeply.");
  }
  const res = tx(() => {
    const cur = readDoc(p);
    if(op === "delete"){ if(!cur) return { v: 0, data: null, changed: false }; SQL.docDel.run(p); return { v: nextV(), data: null, changed: true }; }
    let next;
    if(op === "set") next = data;
    else if(op === "update"){ if(!cur) throw bad("That document does not exist."); next = merge(cur.data, data); }
    else throw bad("Unknown write.");
    const txt = JSON.stringify(next);
    if(Buffer.byteLength(txt) > 256 * 1024) throw new ApiError(413, "invalid_argument", "The document is larger than 256 KB.");
    if(!cur && SQL.docCount.get().n >= 100000) throw new ApiError(507, "quota_exceeded", "The database is full.");
    const v = nextV();
    SQL.docPut.run(p, segs.slice(0, -1).join("/"), segs[segs.length - 1], txt, v, now());
    return { v, data: next, changed: true };
  });
  if(res.changed) broadcast(p, segs, res.v, res.data);
  return res;
}

// ---------------------------------------------------------------- live updates (server-sent events)
const streams = new Set();
function broadcast(p, segs, v, data){
  const ctxCache = new Map();
  for(const s of streams){
    let c = ctxCache.get(s.uid);
    if(!c){ const u = SQL.userById.get(s.uid); if(!u){ s.res.end(); streams.delete(s); continue; } c = ctxFor(u); ctxCache.set(s.uid, c); }
    // a member or request document changing can change what this person may see; tell them to reload their lists
    if(canRead(c, segs)) send(s, "change", { path: p, v, data });
    if(segs[0] === "members" && segs[1] === s.uid) send(s, "resync", {});
  }
}
function send(s, event, obj){ try{ s.res.write(`event: ${event}\ndata: ${JSON.stringify(obj)}\n\n`); }catch(e){ streams.delete(s); } }
setInterval(() => { for(const s of streams) try{ s.res.write(": ping\n\n"); }catch(e){ streams.delete(s); } }, 25000).unref();

// ---------------------------------------------------------------- sessions
const COOKIE = "tt_sid";
const IDLE_MS = CFG.idleMinutes * 60000, MAX_MS = CFG.maxSessionHours * 3600000;
const sha = t => crypto.createHash("sha256").update(t).digest("hex");
function cookies(req){ const o = {}; (req.headers.cookie || "").split(";").forEach(x => { const i = x.indexOf("="); if(i > 0) o[x.slice(0, i).trim()] = decodeURIComponent(x.slice(i + 1).trim()); }); return o; }
function isHttps(req){ return !!req.socket.encrypted || (CFG.trustProxy && String(req.headers["x-forwarded-proto"] || "").split(",")[0].trim() === "https"); }
function clientIp(req){ if(CFG.trustProxy && req.headers["x-forwarded-for"]) return String(req.headers["x-forwarded-for"]).split(",")[0].trim(); return req.socket.remoteAddress || ""; }
function setCookie(req, res, value, maxAgeSec){
  const parts = [`${COOKIE}=${value}`, "Path=/", "HttpOnly", "SameSite=Lax", `Max-Age=${maxAgeSec}`];
  if(isHttps(req)) parts.push("Secure");
  res.setHeader("Set-Cookie", parts.join("; "));
}
function startSession(req, res, uid){
  const token = crypto.randomBytes(32).toString("base64url"), t = now();
  SQL.sessIns.run(sha(token), uid, t, t, clientIp(req));
  setCookie(req, res, token, Math.floor(MAX_MS / 1000));
}
function sessionOf(req, touch){
  const token = cookies(req)[COOKIE]; if(!token) return null;
  const s = SQL.sessGet.get(sha(token)); if(!s) return null;
  const t = now();
  if(t - s.seen > IDLE_MS || t - s.created > MAX_MS){ SQL.sessDel.run(s.token); return null; }
  const user = SQL.userById.get(s.uid); if(!user){ SQL.sessDel.run(s.token); return null; }
  if(touch && t - s.seen > 60000) SQL.sessSeen.run(t, s.token);
  return { token: s.token, user };
}
setInterval(() => SQL.sessPrune.run(now() - IDLE_MS, now() - MAX_MS), 10 * 60000).unref();

// simple per-address limit for sign-in and sign-up attempts
const hits = new Map();
function limited(req, kind, max, windowMs){
  const k = kind + ":" + clientIp(req), t = now();
  const a = (hits.get(k) || []).filter(x => t - x < windowMs); a.push(t); hits.set(k, a);
  return a.length > max;
}
setInterval(() => { const t = now(); for(const [k, a] of hits) if(a.every(x => t - x > 3600000)) hits.delete(k); }, 600000).unref();

// ---------------------------------------------------------------- http plumbing
const SECURITY_HEADERS = {
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "same-origin",
  "X-Frame-Options": "DENY",
  "Cross-Origin-Opener-Policy": "same-origin",
};
const PAGE_CSP = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data: blob:; connect-src 'self'; frame-src 'self' blob:; worker-src 'self' blob:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'";
function head(res, status, type, extra = {}){
  res.writeHead(status, { ...SECURITY_HEADERS, "Content-Type": type, "Cache-Control": "no-store", ...extra });
}
function json(res, status, obj){ head(res, status, "application/json; charset=utf-8"); res.end(JSON.stringify(obj)); }
function html(res, status, body){ head(res, status, "text/html; charset=utf-8", { "Content-Security-Policy": PAGE_CSP }); res.end(body); }
function redirect(res, to){ res.writeHead(303, { ...SECURITY_HEADERS, Location: to, "Cache-Control": "no-store" }); res.end(); }
function readBody(req, limit){
  return new Promise((resolve, reject) => {
    const chunks = []; let n = 0;
    req.on("data", c => { n += c.length; if(n > limit){ reject(new ApiError(413, "invalid_argument", "The upload is too large.")); req.destroy(); } else chunks.push(c); });
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}
async function readJson(req){ const b = await readBody(req, 2 * 1024 * 1024); try{ return JSON.parse(b.toString("utf8") || "{}"); }catch(e){ throw bad("Bad JSON."); } }
async function readForm(req){ const b = await readBody(req, 64 * 1024); return Object.fromEntries(new URLSearchParams(b.toString("utf8"))); }
// Forms must be posted from this site.
function sameOrigin(req){
  const o = req.headers.origin || req.headers.referer; if(!o) return true;
  try{ return new URL(o).host === req.headers.host; }catch(e){ return false; }
}

// ---------------------------------------------------------------- pages (sign-in, sign-up, first-run setup)
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
function shell(title, inner){
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(title)} · TickTrail</title>
<style>
:root{--bg:#f3f6f5;--surface:#fff;--ink:#18282c;--muted:#5a6b6d;--line:#d6dfdc;--accent:#14566b;--accent-ink:#fff;--accent-soft:#dcebef;--bad:#b3261e;--bad-soft:#f9e1de;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--bg:#111a1c;--surface:#172326;--ink:#e3ecea;--muted:#9db0b0;--line:#2a3b3e;--accent:#5cb3cc;--accent-ink:#06191e;--accent-soft:#183842;--bad:#ff8a7e;--bad-soft:#3d1c19;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 "Segoe UI",system-ui,-apple-system,sans-serif}
.box{max-width:420px;margin:7vh auto 40px;background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:32px 28px;display:flex;flex-direction:column;gap:16px;box-shadow:0 12px 40px -18px rgba(10,30,35,.35)}
@media (max-width:460px){.box{margin:16px;padding:24px 18px}}
.brand{display:flex;gap:12px;align-items:center}.brand b{display:block;font-family:Georgia,"Times New Roman",serif;font-size:18px;line-height:1.2}
.brand span{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.mark{width:40px;height:40px;border-radius:10px;background:var(--accent);color:var(--accent-ink);display:grid;place-items:center;font-size:22px;font-weight:700}
h1{font-family:Georgia,"Times New Roman",serif;font-size:26px;margin:0;font-weight:650}
form{display:flex;flex-direction:column;gap:14px}
label{display:flex;flex-direction:column;gap:5px;font-size:13px;font-weight:600}
input{font:inherit;color:inherit;padding:10px 11px;border:1px solid var(--line);border-radius:6px;background:var(--bg);font-weight:400}
input:focus-visible,button:focus-visible,a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
button{font:inherit;font-weight:600;background:var(--accent);color:var(--accent-ink);border:0;border-radius:8px;padding:11px 14px;cursor:pointer}
.msg{background:var(--bad-soft);color:var(--bad);border-radius:6px;padding:9px 12px;font-size:14px;font-weight:500}
.msg.info{background:var(--accent-soft);color:var(--ink)}
p{margin:0}.muted{color:var(--muted);font-size:13.5px}a{color:var(--accent);font-weight:600}
</style></head><body><main class="box"><div class="brand"><span class="mark" aria-hidden="true">✓</span><div><b>TickTrail</b><span>Audit compliance register</span></div></div>${inner}</main></body></html>`;
}
const msgBox = (m, info) => m ? `<div class="msg${info ? " info" : ""}" role="alert">${esc(m)}</div>` : "";
function loginPage(msg, info, username){
  return shell("Log in", `<h1>Log in</h1>
<form method="post" action="/login">
<label>User name<input name="username" autocomplete="username" required value="${esc(username || "")}" autofocus></label>
<label>Password<input name="password" type="password" autocomplete="current-password" required></label>
<button type="submit">Log in</button>${msgBox(msg, info)}</form>
<p class="muted">Forgot your password? Ask an admin to reset it from Team &amp; access.${CFG.allowSignup ? ` New to the firm? <a href="/signup">Create your login</a>.` : ""}</p>
<p class="muted">You are logged out after ${CFG.idleMinutes} minutes without activity.</p>`);
}
function signupPage(msg, f = {}){
  return shell("Create your login", `<h1>Create your login</h1>
<p class="muted">After this, send an access request from the next page. You will see clients and audit files once an admin approves you.</p>
<form method="post" action="/signup">
<label>Full name<input name="name" autocomplete="name" required maxlength="80" value="${esc(f.name || "")}"></label>
<label>User name<input name="username" autocomplete="username" required maxlength="40" pattern="[A-Za-z0-9._\\-]{3,40}" title="3 to 40 letters, numbers, dots, dashes or underscores" value="${esc(f.username || "")}"></label>
<label>Password<input name="password" type="password" autocomplete="new-password" required></label>
<label>Confirm password<input name="password2" type="password" autocomplete="new-password" required></label>
<button type="submit">Create login</button>${msgBox(msg)}</form>
<p class="muted">Already have a login? <a href="/login">Log in</a>.</p>`);
}
function setupPage(msg, f = {}){
  return shell("Set up TickTrail", `<h1>Set up TickTrail</h1>
<p class="muted">This is the first start on this server. Create the owner's login. The owner is the firm's administrator and cannot be removed.</p>
<form method="post" action="/setup">
<label>Full name<input name="name" autocomplete="name" required maxlength="80" value="${esc(f.name || "")}"></label>
<label>User name<input name="username" autocomplete="username" required maxlength="40" pattern="[A-Za-z0-9._\\-]{3,40}" value="${esc(f.username || "")}"></label>
<label>Password<input name="password" type="password" autocomplete="new-password" required></label>
<label>Confirm password<input name="password2" type="password" autocomplete="new-password" required></label>
<button type="submit">Create owner login</button>${msgBox(msg)}</form>`);
}
function changePage(msg){
  return shell("Choose a new password", `<h1>Choose a new password</h1>
<p class="muted">You signed in with a temporary password. Choose your own before continuing: at least 8 characters with letters and numbers.</p>
<form method="post" action="/change-password">
<label>New password<input name="password" type="password" autocomplete="new-password" required autofocus></label>
<label>Confirm new password<input name="password2" type="password" autocomplete="new-password" required></label>
<button type="submit">Save and continue</button>${msgBox(msg)}</form>
<p class="muted"><a href="/logout">Log out</a></p>`);
}
const USERNAME = /^[A-Za-z0-9._\-]{3,40}$/;

// ---------------------------------------------------------------- the app page
const APP_FILE = path.join(ROOT, "public", "app.html");
const SHIM_FILE = path.join(ROOT, "public", "shim.js");
function appPage(user){
  const c = ctxFor(user);
  const boot = { ownerId: SQL.ownerGet.get()?.id || null, me: meOf(user, c) };
  const inject = `<script>window.__TT_BOOT=${JSON.stringify(boot).replace(/</g, "\\u003c")};</script><script src="/shim.js"></script>`;
  const page = fs.readFileSync(APP_FILE, "utf8");
  const at = page.indexOf("<script>");
  return at < 0 ? page : page.slice(0, at) + inject + page.slice(at);
}
function meOf(user, c){
  return { id: user.id, name: user.name, username: user.username, isOwner: c.owner, canEdit: c.admin,
    auth: { lastLogin: user.last_login, prevLogin: user.prev_login, setAt: user.set_at } };
}

// ---------------------------------------------------------------- routes
async function route(req, res){
  const url = new URL(req.url, "http://x");
  const p = url.pathname, m = req.method;
  const noUsers = SQL.userCount.get().n === 0;

  if(p === "/healthz") return json(res, 200, { ok: true });

  // first start: create the owner
  if(p === "/setup"){
    if(!noUsers) return redirect(res, "/login");
    if(m === "GET") return html(res, 200, setupPage());
    if(m !== "POST" || !sameOrigin(req)) return html(res, 400, setupPage("Please try again."));
    const f = await readForm(req);
    const err = !f.name?.trim() ? "Enter your full name." : !USERNAME.test(f.username || "") ? "User names use 3 to 40 letters, numbers, dots, dashes or underscores." : pwProblem(f.password) || (f.password !== f.password2 ? "The two passwords do not match." : "");
    if(err) return html(res, 400, setupPage(err, f));
    // keep the owner's id from the hosted app when their member record was imported
    const seeded = SQL.docList.all("members").find(r => { const d = JSON.parse(r.data); return d.role === "admin" && d.designation === "Owner"; });
    const id = seeded && !SQL.userById.get(seeded.id) ? seeded.id : newId();
    const h = hashPw(f.password);
    SQL.userIns.run(id, f.username.trim(), f.name.trim(), h.hash, h.salt, 0, 1, now(), now());
    SQL.namePut.run(id, f.name.trim());
    SQL.userLogin.run(now(), id); startSession(req, res, id); return redirect(res, "/");
  }
  if(noUsers && !p.startsWith("/api/")) return redirect(res, "/setup");

  if(p === "/login"){
    if(m === "GET") return html(res, 200, loginPage(url.searchParams.get("r") || (url.searchParams.has("expired") ? "Your session ended. Please log in again." : ""), true));
    if(m !== "POST" || !sameOrigin(req)) return html(res, 400, loginPage("Please try again."));
    const f = await readForm(req);
    if(limited(req, "login", 20, 15 * 60000)) return html(res, 429, loginPage("Too many attempts from this address. Wait 15 minutes and try again.", false, f.username));
    const u = SQL.userByName.get(String(f.username || "").trim());
    if(!u){ hashPw("x"); return html(res, 401, loginPage("Wrong user name or password.", false, f.username)); }
    if(u.lock_until > now()) return html(res, 423, loginPage(`Too many wrong attempts. Try again after ${new Date(u.lock_until).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}, or ask an admin to reset your password.`, false, f.username));
    if(!pwOk(u, f.password || "")){
      const fails = u.fails + 1, lock = fails >= 5 ? now() + 15 * 60000 : 0;
      SQL.userFail.run(lock ? 0 : fails, lock, u.id);
      return html(res, 401, loginPage(lock ? "Five wrong attempts. Login is locked for 15 minutes." : "Wrong user name or password.", false, f.username));
    }
    SQL.userLogin.run(now(), u.id); startSession(req, res, u.id);
    return redirect(res, u.must_change ? "/change-password" : "/");
  }
  if(p === "/logout"){
    const s = sessionOf(req, false); if(s) SQL.sessDel.run(s.token);
    setCookie(req, res, "", 0);
    const r = url.searchParams.get("r");
    return redirect(res, "/login" + (r ? "?r=" + encodeURIComponent(r.slice(0, 120)) : ""));
  }
  if(p === "/signup"){
    if(!CFG.allowSignup) return redirect(res, "/login");
    if(m === "GET") return html(res, 200, signupPage());
    if(m !== "POST" || !sameOrigin(req)) return html(res, 400, signupPage("Please try again."));
    const f = await readForm(req);
    if(limited(req, "signup", 5, 60 * 60000)) return html(res, 429, signupPage("Too many new logins from this address. Try again later.", f));
    const name = String(f.name || "").trim().replace(/\s+/g, " ");
    const err = !name ? "Enter your full name." : name.length > 80 ? "The name is too long." : !USERNAME.test(f.username || "") ? "User names use 3 to 40 letters, numbers, dots, dashes or underscores." : SQL.userByName.get(f.username.trim()) ? "That user name is taken. Choose another." : pwProblem(f.password) || (f.password !== f.password2 ? "The two passwords do not match." : "");
    if(err) return html(res, 400, signupPage(err, f));
    const id = newId(), h = hashPw(f.password);
    SQL.userIns.run(id, f.username.trim(), name, h.hash, h.salt, 0, 0, now(), now());
    SQL.namePut.run(id, name);
    SQL.userLogin.run(now(), id); startSession(req, res, id); return redirect(res, "/");
  }

  // everything below needs a signed-in person
  const sess = sessionOf(req, true);
  if(!sess){
    if(p.startsWith("/api/")) return json(res, 401, { code: "unauthenticated", message: "Please log in again." });
    return redirect(res, p === "/" ? "/login" : "/login?expired=1");
  }
  const user = sess.user;

  if(p === "/change-password"){
    if(m === "GET") return html(res, 200, changePage());
    if(m !== "POST" || !sameOrigin(req)) return html(res, 400, changePage("Please try again."));
    const f = await readForm(req);
    const err = pwProblem(f.password) || (f.password !== f.password2 ? "The two passwords do not match." : "");
    if(err) return html(res, 400, changePage(err));
    const h = hashPw(f.password); SQL.userPw.run(h.hash, h.salt, 0, now(), user.id);
    return redirect(res, "/");
  }
  if(user.must_change && !p.startsWith("/api/")) return redirect(res, "/change-password");

  if(p === "/" || p === "/index.html"){ if(m !== "GET") return json(res, 405, {}); return html(res, 200, appPage(user)); }
  if(p === "/shim.js"){ head(res, 200, "text/javascript; charset=utf-8"); return res.end(fs.readFileSync(SHIM_FILE)); }

  if(p.startsWith("/_blob/")){
    const id = p.slice(7); const c = ctxFor(user);
    const b = /^[a-f0-9]{32}$/.test(id) ? SQL.blobGet.get(id) : null;
    if(!b || !c.approved) return json(res, 404, { code: "not_found" });
    const file = path.join(BLOBS, id);
    if(!fs.existsSync(file)) return json(res, 404, { code: "not_found" });
    res.writeHead(200, { ...SECURITY_HEADERS, "Content-Type": b.type, "Content-Length": b.size, "Cache-Control": "private, max-age=3600",
      "Content-Disposition": `inline; filename*=UTF-8''${encodeURIComponent(b.name || id + ".pdf")}`, "X-Frame-Options": "SAMEORIGIN" });
    return fs.createReadStream(file).pipe(res);
  }

  if(!p.startsWith("/api/")) return json(res, 404, { code: "not_found" });
  // API calls must come from the app itself (a custom header cannot be sent cross-site without permission)
  // (the live-update stream is exempt: browsers cannot add headers to it, and it only reads, using the same-site login cookie)
  if(p !== "/api/events" && req.headers["x-ticktrail"] !== "1") return json(res, 403, { code: "permission_denied", message: "Missing app header." });
  const c = ctxFor(user);

  if(p === "/api/me") return json(res, 200, meOf(user, c));

  if(p === "/api/events"){
    res.writeHead(200, { ...SECURITY_HEADERS, "Content-Type": "text/event-stream", "Cache-Control": "no-store", Connection: "keep-alive", "X-Accel-Buffering": "no" });
    res.write("retry: 3000\n\n");
    const s = { res, uid: user.id }; streams.add(s);
    req.on("close", () => streams.delete(s));
    return;
  }
  if(p === "/api/doc" && m === "GET"){
    const segs = splitPath(url.searchParams.get("p"), true); if(!segs) throw bad("Bad document path.");
    const d = canRead(c, segs) ? readDoc(segs.join("/")) : null;
    return json(res, 200, d ? { exists: true, data: d.data, v: d.v } : { exists: false });
  }
  if(p === "/api/list" && m === "GET"){
    const segs = splitPath(url.searchParams.get("c"), false); if(!segs) throw bad("Bad collection path.");
    const docs = SQL.docList.all(segs.join("/")).filter(r => canRead(c, [...segs, r.id])).map(r => ({ id: r.id, data: JSON.parse(r.data), v: r.v }));
    return json(res, 200, { docs });
  }
  if(p === "/api/write" && m === "POST"){
    const b = await readJson(req);
    const r = writeDoc(c, b.op, b.p, b.data);
    return json(res, 200, { ok: true, v: r.v, data: r.data });
  }
  if(p === "/api/profiles" && m === "GET"){
    const ids = String(url.searchParams.get("ids") || "").split(",").filter(Boolean).slice(0, 200);
    const out = {}; ids.forEach(id => { const u = SQL.userById.get(id); out[id] = { name: u?.name || SQL.nameGet.get(id)?.name || "" }; });
    return json(res, 200, out);
  }
  if(p === "/api/password" && m === "POST"){
    const b = await readJson(req);
    if(limited(req, "pwchange", 10, 15 * 60000)) throw new ApiError(429, "rate_limited", "Too many attempts. Wait 15 minutes.");
    if(!pwOk(user, b.old || "")) throw new ApiError(400, "invalid_argument", "Current password is wrong.");
    const err = pwProblem(b.new); if(err) throw bad(err);
    const h = hashPw(b.new); SQL.userPw.run(h.hash, h.salt, 0, now(), user.id);
    return json(res, 200, { ok: true, setAt: now() });
  }
  if(p === "/api/admin/reset" && m === "POST"){
    if(!c.admin) throw deny();
    const b = await readJson(req); const u = SQL.userById.get(b.uid);
    if(!u) throw new ApiError(404, "not_found", "That person has no login on this server.");
    if(u.owner && !c.owner) throw deny();
    const pw = tempPassword(), h = hashPw(pw);
    SQL.userPw.run(h.hash, h.salt, 1, now(), u.id); SQL.sessDelUser.run(u.id);
    return json(res, 200, { ok: true, username: u.username, password: pw });
  }
  if(p === "/api/admin/delete-user" && m === "POST"){
    if(!c.admin) throw deny();
    const b = await readJson(req); const u = SQL.userById.get(b.uid);
    if(!u) return json(res, 200, { ok: true });
    if(u.owner) throw new ApiError(400, "invalid_argument", "The owner's login cannot be deleted.");
    if(u.id === user.id) throw new ApiError(400, "invalid_argument", "You cannot delete your own login.");
    SQL.namePut.run(u.id, u.name);   // keep the name on work already done
    SQL.sessDelUser.run(u.id); SQL.userDel.run(u.id);
    for(const s of streams) if(s.uid === u.id){ s.res.end(); streams.delete(s); }
    return json(res, 200, { ok: true });
  }
  if(p === "/api/admin/users" && m === "GET"){
    if(!c.admin) throw deny();
    return json(res, 200, { users: SQL.userAll.all().map(u => ({ id: u.id, username: u.username, name: u.name, owner: !!u.owner })) });
  }
  if(p === "/api/assets" && m === "POST"){
    if(!c.approved) throw deny();
    const type = String(req.headers["content-type"] || "").split(";")[0].trim();
    if(type !== "application/pdf") throw bad("Only PDF files can be attached.");
    const body = await readBody(req, 20 * 1024 * 1024);
    if(body.subarray(0, 5).toString("latin1") !== "%PDF-") throw bad("That file is not a PDF.");
    const id = blobId(); const name = decodeURIComponent(String(req.headers["x-filename"] || "document.pdf")).slice(0, 200);
    fs.writeFileSync(path.join(BLOBS, id), body);
    SQL.blobIns.run(id, name, type, body.length, user.id, now());
    return json(res, 200, { id, url: "/_blob/" + id, sizeBytes: body.length, contentType: type });
  }
  if(p === "/api/assets" && m === "GET"){
    if(!c.approved) throw deny();
    const rows = c.admin ? SQL.blobAll.all() : SQL.blobMine.all(user.id);
    const u = SQL.blobUsage.get();
    return json(res, 200, { assets: rows.map(b => ({ id: b.id, url: "/_blob/" + b.id, sizeBytes: b.size, contentType: b.type, name: b.name })), usage: { files: u.n, bytes: u.bytes } });
  }
  if(p.startsWith("/api/assets/") && m === "DELETE"){
    const id = p.slice(12); const b = SQL.blobGet.get(id);
    if(!b) return json(res, 200, { ok: true });
    if(!(c.admin || (c.approved && b.by === user.id))) throw deny();
    SQL.blobDel.run(id); fs.rmSync(path.join(BLOBS, id), { force: true });
    return json(res, 200, { ok: true });
  }
  return json(res, 404, { code: "not_found", message: "Unknown request." });
}

// ---------------------------------------------------------------- command line tools
function seedIfEmpty(){
  if(SQL.docCount.get().n > 0) return;
  const seed = path.join(ROOT, "seed");
  if(fs.existsSync(seed)){ const n = importFolder(seed); if(n) console.log(`Loaded ${n} starting documents (checklist library and settings).`); }
}
function importFolder(dir){
  let n = 0;
  const walk = (folder, collSegs) => {
    for(const ent of fs.readdirSync(folder, { withFileTypes: true })){
      if(ent.isDirectory()) walk(path.join(folder, ent.name), [...collSegs, ent.name]);
      else if(ent.name.endsWith(".json") && collSegs.length % 2 === 1){
        const id = ent.name.slice(0, -5), p = [...collSegs, id].join("/");
        if(!splitPath(p, true) || collSegs[0] === "auth") continue;
        const data = JSON.parse(fs.readFileSync(path.join(folder, ent.name), "utf8"));
        SQL.docPut.run(p, collSegs.join("/"), id, JSON.stringify(data), nextV(), now()); n++;
      }
    }
  };
  tx(() => walk(dir, []));
  return n;
}
function cli(args){
  const [cmd, arg] = args;
  if(cmd === "--backup"){
    const d = new Date(), z = n => String(n).padStart(2, "0");
    const stamp = `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}-${z(d.getHours())}-${z(d.getMinutes())}-${z(d.getSeconds())}`;
    const dest = path.resolve(arg || path.join(ROOT, "backups", stamp));
    fs.mkdirSync(path.join(dest, "blobs"), { recursive: true });
    fs.rmSync(path.join(dest, "ticktrail.db"), { force: true });
    db.exec(`VACUUM INTO '${path.join(dest, "ticktrail.db").replace(/'/g, "''")}'`);
    for(const f of fs.readdirSync(BLOBS)) fs.copyFileSync(path.join(BLOBS, f), path.join(dest, "blobs", f));
    console.log("Backup saved to " + dest);
    if(!arg){ // automatic backups: keep the newest 30
      const dir = path.join(ROOT, "backups");
      const old = fs.readdirSync(dir).filter(n => /^\d{4}(-\d{2}){5}$/.test(n)).sort().slice(0, -30);
      old.forEach(n => fs.rmSync(path.join(dir, n), { recursive: true, force: true }));
      if(old.length) console.log(`Removed ${old.length} older backup${old.length > 1 ? "s" : ""} (the newest 30 are kept).`);
    }
    return true;
  }
  if(cmd === "--import"){
    if(!arg || !fs.existsSync(arg)){ console.error("Give the folder to import, e.g. node server.js --import export"); process.exitCode = 1; return true; }
    console.log(`Imported ${importFolder(path.resolve(arg))} documents.`); return true;
  }
  if(cmd === "--reset-password"){
    const u = SQL.userByName.get(String(arg || "")); if(!u){ console.error("No user with that user name."); process.exitCode = 1; return true; }
    const pw = tempPassword(), h = hashPw(pw); SQL.userPw.run(h.hash, h.salt, 1, now(), u.id); SQL.sessDelUser.run(u.id);
    console.log(`Temporary password for ${u.username}: ${pw}\nThey will choose a new one when they log in.`); return true;
  }
  if(cmd === "--list-users"){
    for(const u of SQL.userAll.all()){ const m = memberOf(u.id); console.log(`${u.username.padEnd(20)} ${u.name.padEnd(28)} ${u.owner ? "owner" : m ? `${m.role} (${m.status})` : "no access yet"}`); }
    return true;
  }
  return false;
}

// ---------------------------------------------------------------- start
if(cli(process.argv.slice(2))) process.exit();
seedIfEmpty();
const server = http.createServer((req, res) => {
  route(req, res).catch(e => {
    if(!(e instanceof ApiError)) console.error(new Date().toISOString(), req.method, req.url, e);
    if(res.headersSent){ try{ res.end(); }catch(_){} return; }
    const status = e instanceof ApiError ? e.status : 500;
    json(res, status, { code: e.code || "unavailable", message: e instanceof ApiError ? e.message : "The server hit an error. Try again." });
  });
});
server.requestTimeout = 120000;
server.headersTimeout = 30000;
server.listen(CFG.port, CFG.host, () => {
  console.log(`TickTrail is running at http://${CFG.host === "0.0.0.0" ? "localhost" : CFG.host}:${CFG.port}  (data folder: ${DATA})`);
  if(SQL.userCount.get().n === 0) console.log("First start: open the address above to create the owner's login.");
});
const stop = () => { server.close(); for(const s of streams) try{ s.res.end(); }catch(_){} db.close(); process.exit(0); };
process.on("SIGINT", stop); process.on("SIGTERM", stop);
