/* ChatVault — WhatsApp export archiver. All processing happens in the browser; nothing is uploaded. */
(() => {
"use strict";
const VERSION = "1.1";

/* ============================================================ utilities */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const h = (html) => { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstElementChild; };
const uid = () => Math.random().toString(36).slice(2, 10);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const hueOf = s => { let x = 0; for (const c of String(s)) x = (x * 31 + c.codePointAt(0)) >>> 0; return x % 360; };
const initials = s => { const p = String(s).replace(/[^\p{L}\p{N} ]/gu, " ").trim().split(/\s+/).filter(Boolean); return ((p[0]?.[0] || "?") + (p.length > 1 ? p[p.length - 1][0] : "")).toUpperCase(); };
const fmtBytes = n => n < 1024 ? n + " B" : n < 1048576 ? (n / 1024).toFixed(n < 10240 ? 1 : 0) + " KB" : (n / 1048576).toFixed(1) + " MB";
const pad = n => String(n).padStart(2, "0");
const fmtTime = ts => { const d = new Date(ts); let H = d.getHours(); const ap = H >= 12 ? "pm" : "am"; H = H % 12 || 12; return `${H}:${pad(d.getMinutes())} ${ap}`; };
const fmtDate = ts => new Date(ts).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
const fmtDay = ts => new Date(ts).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short", year: "numeric" });
const fmtDT = ts => new Date(ts).toLocaleString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit", second: "2-digit" });
const isoDay = ts => { const d = new Date(ts); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; };
const slug = s => String(s).normalize("NFKD").replace(/[^\w\s.-]/g, "").trim().replace(/\s+/g, "-").replace(/-{2,}/g, "-").slice(0, 60) || "chat";
const hex = buf => [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
const fromHex = s => Uint8Array.from(String(s).match(/../g) || [], x => parseInt(x, 16));
const b64 = buf => { const u = new Uint8Array(buf); let s = ""; for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000)); return btoa(s); };
const unb64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
const fmtDur = ms => { const m = Math.round(ms / 60000); if (m < 1) return "under 1 min"; if (m < 60) return m + " min"; const hh = Math.floor(m / 60); if (hh < 24) return `${hh} h ${m % 60} min`; const d = Math.floor(hh / 24); return `${d} d ${hh % 24} h`; };
async function sha256(data) {
  const buf = data instanceof ArrayBuffer ? data : data instanceof Blob ? await data.arrayBuffer() : new TextEncoder().encode(data);
  return hex(await crypto.subtle.digest("SHA-256", buf));
}
const store = {
  get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch { return false; } }
};
const mem = {}; // fallback when storage is blocked
function sget(k, d) { const v = store.get(k, undefined); return v === undefined ? (k in mem ? mem[k] : d) : v; }
function sset(k, v) { mem[k] = v; store.set(k, v); }

/* icons (inline, stroke-based) */
const I = {
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  dots: '<circle cx="12" cy="5" r="1.4" fill="currentColor"/><circle cx="12" cy="12" r="1.4" fill="currentColor"/><circle cx="12" cy="19" r="1.4" fill="currentColor"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  back: '<path d="M19 12H5M11 18l-6-6 6-6"/>',
  close: '<path d="M18 6 6 18M6 6l12 12"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.01"/>',
  image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="m21 16-5-5-9 9"/>',
  chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  download: '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>',
  lock: '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
  shield: '<path d="M12 3 5 6v6c0 4.4 3 7.8 7 9 4-1.2 7-4.6 7-9V6z"/><path d="m9 12 2 2 4-4"/>',
  users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7M21.5 20a6.5 6.5 0 0 0-4-6"/>',
  log: '<path d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01"/>',
  out: '<path d="M15 4h4v16h-4M10 17l5-5-5-5M15 12H3"/>',
  key: '<circle cx="8" cy="15" r="4"/><path d="m11 12 9-9M17 6l3 3"/>',
  eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  eyeoff: '<path d="M3 3l18 18M10.6 5.1A10 10 0 0 1 12 5c6.5 0 10 7 10 7a17 17 0 0 1-3 3.8M6.5 6.6C3.8 8.3 2 12 2 12s3.5 7 10 7a9.6 9.6 0 0 0 4.2-1M9.9 9.9a3 3 0 0 0 4.2 4.2"/>',
  copy: '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
  check: '<path d="m5 12 5 5 9-10"/>',
  ban: '<circle cx="12" cy="12" r="9"/><path d="m5.6 5.6 12.8 12.8"/>',
  clip: '<path d="m21 11-8.5 8.5a5.5 5.5 0 0 1-7.8-7.8L13.4 3a3.7 3.7 0 0 1 5.2 5.2L10 16.9a1.8 1.8 0 0 1-2.6-2.6L15 6.8"/>',
  doc: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
  zip: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M11 6h1M11 9h1M11 12h1M10 15h3v3h-3z"/>',
  sheet: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/>',
  html: '<path d="m8 8-4 4 4 4M16 8l4 4-4 4M14 5l-4 14"/>',
  spark: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
  chevL: '<path d="m15 18-6-6 6-6"/>', chevR: '<path d="m9 18 6-6-6-6"/>', chevD: '<path d="m6 9 6 6 6-6"/>',
  play: '<path d="M8 5.5v13l11-6.5z"/>', pause: '<path d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z"/>',
  mic: '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3zM5 11a7 7 0 0 0 14 0h-2a5 5 0 0 1-10 0zM11 19h2v3h-2z"/>',
  video: '<rect x="2" y="6" width="14" height="12" rx="2"/><path d="m16 10 6-3v10l-6-3"/>',
  upload: '<path d="M12 16V4M7 9l5-5 5 5M5 20h14"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
  trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
  link: '<path d="M10 14a4.5 4.5 0 0 0 6.4 0l3-3a4.5 4.5 0 0 0-6.4-6.4l-1 1M14 10a4.5 4.5 0 0 0-6.4 0l-3 3a4.5 4.5 0 0 0 6.4 6.4l1-1"/>',
  tag: '<path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="8.5" r="1.3"/>',
  merge: '<path d="M6 3v6a6 6 0 0 0 6 6h6M15 12l3 3-3 3M6 21v-6"/>',
  diff: '<path d="M8 4v10M3 9h10M14 15h7M5 20h14"/>',
  db: '<ellipse cx="12" cy="5.5" rx="7.5" ry="2.8"/><path d="M4.5 5.5v13c0 1.5 3.4 2.8 7.5 2.8s7.5-1.3 7.5-2.8v-13M4.5 12c0 1.5 3.4 2.8 7.5 2.8s7.5-1.3 7.5-2.8"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 .9-1 1.7M12 17h.01"/>',
  restore: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5"/>',
  cloud: '<path d="M7 18.5a4.5 4.5 0 0 1-.6-9A6 6 0 0 1 18 9a4.5 4.5 0 0 1-.5 9.5z"/>',
  sort: '<path d="M7 4v16M3 16l4 4 4-4M17 20V4M13 8l4-4 4 4"/>',
  star: '<path d="m12 3 2.7 5.6 6.1.8-4.5 4.2 1.1 6.1L12 16.8 6.6 19.7l1.1-6.1L3.2 9.4l6.1-.8z"/>',
  pen: '<path d="M4 20h4L19 9l-4-4L4 16zM14 6l4 4"/>',
  quote: '<path d="M7 7h4v4c0 3-1.5 5-4 6M15 7h4v4c0 3-1.5 5-4 6"/>',
  briefcase: '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 13h18"/>',
  palette: '<path d="M12 3a9 9 0 1 0 0 18c1.1 0 1.6-.8 1.6-1.6 0-.9-.6-1.3-.6-2.1 0-.9.7-1.5 1.6-1.5H17a4 4 0 0 0 4-4c0-4.9-4-8.8-9-8.8z"/><circle cx="7.5" cy="11" r="1.2"/><circle cx="10" cy="7" r="1.2"/><circle cx="15" cy="7.5" r="1.2"/>',
  shade: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><path d="M3 3l18 18"/>',
  keyboard: '<rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7 14h10"/>',
  cert: '<path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5M9 12h7M9 16h4"/><circle cx="16.5" cy="17.5" r="2.5"/>',
  vault: '<rect x="3" y="4" width="18" height="15" rx="3"/><circle cx="12" cy="11.5" r="3.5"/><path d="M12 8v1.2M12 13.8V15M8.5 11.5H9.7M14.3 11.5h1.2M7 19v2M17 19v2"/>'
};
const ic = (n, cls = "i") => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${I[n]}</svg>`;

/* toasts */
function toast(msg, kind = "") {
  const box = $(".toasts") || document.body.appendChild(h('<div class="toasts" role="status" aria-live="polite"></div>'));
  const t = h(`<div class="toast ${kind}">${esc(msg)}</div>`); box.append(t);
  setTimeout(() => { t.style.transition = "opacity .3s"; t.style.opacity = "0"; setTimeout(() => t.remove(), 320); }, kind === "err" ? 4200 : 2600);
}
async function copyText(text) {
  try { await navigator.clipboard.writeText(text); toast("Copied"); }
  catch { const ta = h(`<textarea style="position:fixed;opacity:0">${esc(text)}</textarea>`); document.body.append(ta); ta.select(); try { document.execCommand("copy"); toast("Copied"); } catch { toast("Select and copy the text manually", "err"); } ta.remove(); }
}

/* ============================================================ platform capabilities (optional) */
const cap = { downloads: Promise.resolve(null), sample: Promise.resolve(null) };
if (window.claude && typeof window.claude.use === "function") {
  cap.downloads = window.claude.use("downloads").catch(() => null);
  cap.sample = window.claude.use("sample").catch(() => null);
}
const DL_OK = /\.(gif|png|jpe?g|webp|mp4|webm|txt|json|md|docx|pptx|csv|html|svg|pdf|xlsx|zip)$/i;
async function saveFile(filename, data, mime = "application/octet-stream") {
  const blob = data instanceof Blob ? data : new Blob([data], { type: mime });
  const dl = await cap.downloads;
  if (dl) {
    if (!DL_OK.test(filename)) { // wrap unsupported types (e.g. .opus) in a zip
      await libs.zip(); const z = new JSZip(); z.file(filename, blob);
      return saveFile(filename.replace(/\.[^.]+$/, "") + ".zip", await z.generateAsync({ type: "blob" }));
    }
    try { await dl.save({ filename, data: blob }); toast(`Saved ${filename}`); return true; }
    catch (e) {
      if (e?.code === "declined") toast("Download cancelled");
      else if (e?.code === "rate_limited") toast("Another download is waiting for confirmation", "err");
      else toast("Downloads are not available in this view", "err");
      return false;
    }
  }
  const url = URL.createObjectURL(blob);
  const a = h(`<a href="${url}" download="${esc(filename)}" style="display:none"></a>`); document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60000); toast(`Downloading ${filename}`); return true;
}

/* lazily loaded libraries (cdnjs) */
function loadScript(src) { return new Promise((res, rej) => { const s = document.createElement("script"); s.src = src; s.onload = res; s.onerror = () => rej(new Error("Could not load " + src)); document.head.append(s); }); }
const CDN = "https://cdnjs.cloudflare.com/ajax/libs/";
const libs = {
  _z: null, _x: null, _p: null,
  zip() { return window.JSZip ? Promise.resolve() : (this._z ||= loadScript(CDN + "jszip/3.10.1/jszip.min.js")); },
  xlsx() { return window.XLSX ? Promise.resolve() : (this._x ||= loadScript(CDN + "xlsx/0.18.5/xlsx.full.min.js")); },
  pdf() { return window.pdfjsLib ? Promise.resolve() : (this._p ||= loadScript(CDN + "pdf.js/3.11.174/pdf.worker.min.js").then(() => loadScript(CDN + "pdf.js/3.11.174/pdf.min.js"))); }
};

/* ============================================================ access control */
const ROLES = {
  admin: { label: "Admin", desc: "Full access, manages users and the audit log" },
  reviewer: { label: "Reviewer", desc: "Imports, analyses and exports chats" },
  viewer: { label: "Viewer", desc: "Read-only; phone numbers and emails are masked" }
};
const PERMS = [
  ["import", "Import and merge chats"], ["view", "Read chats and search"], ["insights", "Chat insights"], ["ai", "AI summary"],
  ["organise", "Edit tags and notes"], ["media", "Download attachments"], ["export", "Export archives"], ["unmasked", "See unmasked contact details"],
  ["manage", "Saved chats, backup and restore"], ["purge", "Permanently delete saved chats"], ["users", "Manage users"], ["audit", "View audit log"]
];
const GRANTS = {
  admin: ["import", "view", "insights", "ai", "organise", "media", "export", "unmasked", "manage", "purge", "users", "audit"],
  reviewer: ["import", "view", "insights", "ai", "organise", "media", "export", "unmasked", "manage"],
  viewer: ["view", "insights"]
};
const K = { users: "cv.users", audit: "cv.audit", lock: "cv.lockouts", settings: "cv.settings", toured: "cv.toured" };
const S = { user: null, chats: [], active: null, drawer: null, lastActivity: Date.now(), locked: false, vaultKey: null, tagFilter: "", sort: "recent" };
const can = p => !!S.user && GRANTS[S.user.role]?.includes(p);
const settings = () => Object.assign({ idleMin: 10, autoSave: true, viewerNames: false, privacyOnBlur: false }, sget(K.settings, {}));

async function pbkdf2(pw, saltHex) {
  const salt = saltHex ? Uint8Array.from(saltHex.match(/../g).map(x => parseInt(x, 16))) : crypto.getRandomValues(new Uint8Array(16));
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(pw), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits({ name: "PBKDF2", salt, iterations: 150000, hash: "SHA-256" }, key, 256);
  return { salt: hex(salt), hash: hex(bits) };
}
/* ---- vault key: one AES-256 key for saved chats, wrapped separately with each user's password ---- */
async function pwKey(pw, saltHex) {
  const base = await crypto.subtle.importKey("raw", new TextEncoder().encode(pw), "PBKDF2", false, ["deriveKey"]);
  return crypto.subtle.deriveKey({ name: "PBKDF2", salt: fromHex(saltHex), iterations: 150000, hash: "SHA-256" }, base, { name: "AES-GCM", length: 256 }, false, ["encrypt", "decrypt"]);
}
const newVaultKey = () => crypto.subtle.generateKey({ name: "AES-GCM", length: 256 }, true, ["encrypt", "decrypt"]);
async function wrapFor(pw) {
  if (!S.vaultKey) return {};
  const wsalt = hex(crypto.getRandomValues(new Uint8Array(16))); const k = await pwKey(pw, wsalt);
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ct = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, k, await crypto.subtle.exportKey("raw", S.vaultKey));
  return { wsalt, wiv: hex(iv), wct: hex(ct) };
}
async function unwrapFor(u, pw) {
  const k = await pwKey(pw, u.wsalt);
  const raw = await crypto.subtle.decrypt({ name: "AES-GCM", iv: fromHex(u.wiv) }, k, fromHex(u.wct));
  return crypto.subtle.importKey("raw", raw, "AES-GCM", true, ["encrypt", "decrypt"]);
}
async function aesEnc(key, data) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const pt = data instanceof ArrayBuffer ? data : ArrayBuffer.isView(data) ? data : new TextEncoder().encode(JSON.stringify(data));
  return { iv, ct: await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, pt) };
}
async function aesDec(key, rec, json) { const pt = await crypto.subtle.decrypt({ name: "AES-GCM", iv: rec.iv }, key, rec.ct); return json ? JSON.parse(new TextDecoder().decode(pt)) : pt; }

/* ---- IndexedDB store: "chats" holds encrypted metadata, "blobs" holds encrypted export files keyed id/hash ---- */
const idb = {
  _db: null,
  open() {
    return this._db ||= new Promise((res, rej) => {
      let r; try { r = indexedDB.open("chatvault", 1); } catch (e) { return rej(e); }
      r.onupgradeneeded = () => { const d = r.result; if (!d.objectStoreNames.contains("chats")) d.createObjectStore("chats", { keyPath: "id" }); if (!d.objectStoreNames.contains("blobs")) d.createObjectStore("blobs"); };
      r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error);
    });
  },
  async run(store, mode, fn) {
    const d = await this.open();
    return new Promise((res, rej) => { const t = d.transaction(store, mode); let out; const q = fn(t.objectStore(store)); if (q) q.onsuccess = () => { out = q.result; }; t.oncomplete = () => res(out); t.onerror = () => rej(t.error); t.onabort = () => rej(t.error); });
  },
  all() { return this.run("chats", "readonly", s => s.getAll()); },
  put(rec) { return this.run("chats", "readwrite", s => s.put(rec)); },
  del(id) { return this.run("chats", "readwrite", s => s.delete(id)); },
  blob(k) { return this.run("blobs", "readonly", s => s.get(k)); },
  putBlob(k, v) { return this.run("blobs", "readwrite", s => s.put(v, k)); },
  delBlob(k) { return this.run("blobs", "readwrite", s => s.delete(k)); },
  async delBlobs(prefix) { const keys = await this.run("blobs", "readonly", s => s.getAllKeys()); await this.run("blobs", "readwrite", s => { keys.filter(k => String(k).startsWith(prefix)).forEach(k => s.delete(k)); }); },
  async ok() { try { await this.open(); return true; } catch { return false; } }
};

const users = () => sget(K.users, []);
function saveUsers(u) { sset(K.users, u); if (typeof scheduleFolderSync === "function") try { scheduleFolderSync(); } catch {} }
function pwProblem(pw) {
  if (pw.length < 8) return "Use at least 8 characters.";
  if (!/[A-Za-z]/.test(pw) || !/\d/.test(pw)) return "Include at least one letter and one number.";
  return "";
}
async function createUser({ name, username, password, role }) {
  username = username.trim().toLowerCase();
  if (!/^[a-z0-9._-]{3,24}$/.test(username)) throw new Error("Username: 3–24 letters, numbers, dots, dashes or underscores.");
  if (users().some(u => u.username === username)) throw new Error("That username is already taken.");
  const p = pwProblem(password); if (p) throw new Error(p);
  const { salt, hash } = await pbkdf2(password);
  const u = { id: uid(), name: name.trim() || username, username, role, salt, hash, active: true, created: Date.now(), lastLogin: null, ...(await wrapFor(password)) };
  saveUsers([...users(), u]); return u;
}
function audit(action, detail = "") {
  const log = sget(K.audit, []);
  log.unshift({ t: Date.now(), user: S.user?.username || "-", role: S.user?.role || "-", action, detail });
  sset(K.audit, log.slice(0, 1000));
}
async function login(username, password) {
  username = username.trim().toLowerCase();
  const locks = sget(K.lock, {}); const L = locks[username] || { n: 0, until: 0 };
  if (L.until > Date.now()) throw new Error(`Too many attempts. Try again in ${Math.ceil((L.until - Date.now()) / 1000)} s.`);
  const u = users().find(x => x.username === username);
  const ok = u && (await pbkdf2(password, u.salt)).hash === u.hash;
  if (!ok) {
    L.n++; if (L.n >= 5) { L.until = Date.now() + 120000; L.n = 0; }
    locks[username] = L; sset(K.lock, locks);
    const prev = S.user; S.user = { username, role: u?.role || "-" }; audit("Sign-in failed", u ? "Wrong password" : "Unknown user"); S.user = prev;
    throw new Error(L.until > Date.now() ? "Too many attempts. Account locked for 2 minutes." : "Incorrect username or password.");
  }
  if (!u.active) { const prev = S.user; S.user = u; audit("Sign-in blocked", "Account disabled"); S.user = prev; throw new Error("This account is disabled. Ask an admin to enable it."); }
  delete locks[username]; sset(K.lock, locks);
  S.vaultKey = null; let extra = {};
  try {
    if (u.wsalt) S.vaultKey = await unwrapFor(u, password);
    else if (u.role === "admin" && !users().some(x => x.wsalt)) { S.vaultKey = await newVaultKey(); extra = await wrapFor(password); } // first sign-in after upgrade
  } catch (e) { console.error(e); S.vaultKey = null; }
  saveUsers(users().map(x => x.id === u.id ? { ...x, ...extra, lastLogin: Date.now() } : x));
  S.user = { ...u, ...extra }; audit("Signed in"); return S.user;
}

/* ============================================================ WhatsApp export parser */
const RE_AND = /^(\d{1,2})[\/.\-](\d{1,2})[\/.\-](\d{2,4}),?\s+(\d{1,2})[:.](\d{2})(?:[:.](\d{2}))?(?:[\s  ]*([AaPp])\.?\s?[Mm]\.?)?\s*[-–]\s(.*)$/;
const RE_IOS = /^[‎‏]?\[(\d{1,2})[\/.\-](\d{1,2})[\/.\-](\d{2,4}),?\s+(\d{1,2})[:.](\d{2})(?:[:.](\d{2}))?(?:[\s  ]*([AaPp])\.?\s?[Mm]\.?)?\]\s?(.*)$/;
const SYS_RE = /(end-to-end encrypted|created group|created this group|\badded\b|\bremoved\b|\bleft$|joined using|changed the subject|changed this group|changed the group|security code|changed their phone number|changed to \+|pinned a message|disappearing messages|is a contact|now an admin|turned (on|off)|deleted this group|You're now|blocked this contact|unblocked this contact)/i;
const OMIT_RE = /^(?:<Media omitted>|(image|video|audio|document|sticker|GIF|Contact card|video note) omitted|<attached: .* omitted>)$/i;
const DEL_RE = /^(This message was deleted\.?|You deleted this message\.?|This message was deleted by admin.*)$/i;
function kindOf(name) {
  const n = name.toLowerCase();
  if (/^stk-|sticker/.test(n) && n.endsWith(".webp")) return "sticker";
  if (/\.(jpe?g|png|webp|gif|heic|bmp)$/.test(n)) return "image";
  if (/\.(mp4|3gp|mov|mkv|webm|m4v)$/.test(n)) return "video";
  if (/\.(opus|ogg|m4a|mp3|aac|amr|wav)$/.test(n)) return "audio";
  if (/\.vcf$/.test(n)) return "contact";
  return "doc";
}
function parseChat(raw) {
  const text = raw.replace(/^﻿/, "").replace(/\r\n?/g, "\n");
  const lines = text.split("\n");
  let ios = 0, and = 0;
  for (const l of lines.slice(0, 80)) { if (RE_IOS.test(l)) ios++; else if (RE_AND.test(l)) and++; }
  const RE = ios > and ? RE_IOS : RE_AND, format = ios > and ? "iPhone" : "Android";
  if (!ios && !and) throw new Error("This file does not look like a WhatsApp chat export.");
  const raws = []; let cur = null;
  for (const l of lines) {
    const m = RE.exec(l);
    if (m) { cur = { a: +m[1], b: +m[2], y: +m[3], H: +m[4], M: +m[5], s: +(m[6] || 0), ap: (m[7] || "").toLowerCase(), rest: m[8], more: [] }; raws.push(cur); }
    else if (cur) cur.more.push(l);
  }
  if (raws.length && raws[raws.length - 1].more.length && raws[raws.length - 1].more[raws[raws.length - 1].more.length - 1] === "") raws[raws.length - 1].more.pop();
  const mdy = !raws.some(r => r.a > 12) && raws.some(r => r.b > 12);
  const msgs = []; const counts = {};
  raws.forEach((r, i) => {
    const day = mdy ? r.b : r.a, mon = mdy ? r.a : r.b, yr = r.y < 100 ? 2000 + r.y : r.y;
    let H = r.H; if (r.ap === "p" && H < 12) H += 12; if (r.ap === "a" && H === 12) H = 0;
    const ts = new Date(yr, mon - 1, day, H, r.M, r.s).getTime();
    let sender = null, body = r.rest;
    const ci = r.rest.indexOf(": ");
    if (ci > 0 && ci <= 80) { sender = r.rest.slice(0, ci).replace(/[‎‏‪-‮]/g, "").trim(); body = r.rest.slice(ci + 2); }
    body = [body, ...r.more].join("\n");
    const m = { id: i + 1, ts, sender, type: "text", text: "", edited: false };
    if (/<This message was edited>\s*$/.test(body)) { m.edited = true; body = body.replace(/\s*‎?<This message was edited>\s*$/, ""); }
    const lrmLead = /^‎/.test(body);
    const attI = /<attached:\s*([^>]+)>/.exec(body);
    const attA = /^‎?(.+?\.[A-Za-z0-9]{2,5})\s\(file attached\)\s*(?:\n([\s\S]*))?$/.exec(body);
    const clean = s => s.replace(/[‎‏]/g, "").trim();
    if (!sender) { m.type = "system"; m.text = clean(body); }
    else if (attI) {
      const file = attI[1].trim(); const rest = clean(body.replace(attI[0], ""));
      m.type = "media"; m.media = { name: file, kind: kindOf(file) };
      if (/ • /.test(rest)) { m.media.meta = rest; const pg = /(\d+)\s+pages?/.exec(rest); if (pg) m.media.pages = +pg[1]; } else m.text = rest;
    } else if (attA) {
      const file = attA[1].trim(); m.type = "media"; m.media = { name: file, kind: kindOf(file) }; m.text = clean(attA[2] || "");
    } else if (OMIT_RE.test(clean(body))) {
      m.type = "omitted"; const k = (OMIT_RE.exec(clean(body))[1] || "media").toLowerCase(); m.text = k;
    } else if (DEL_RE.test(clean(body))) { m.type = "deleted"; m.text = clean(body); }
    else if (lrmLead && SYS_RE.test(body) && format === "iPhone") { m.type = "system"; m.text = clean(body); m.sysBy = sender; sender = m.sender = null; }
    else m.text = body.replace(/[‎‏]/g, "");
    if (m.sender) counts[m.sender] = (counts[m.sender] || 0) + 1;
    msgs.push(m);
  });
  // Android: a bare "file attached" line followed by a separate caption-less line is already handled; merge consecutive identical-ts captions
  const participants = Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([name, n]) => ({ name, n, h: hueOf(name) }));
  return { format, messages: msgs, participants };
}

/* ============================================================ import, merge and saved chats */
const nameFromFile = n => n.replace(/\.(zip|txt)$/i, "").replace(/^WhatsApp Chat (with |- )?/i, "").replace(/\s*\((\d{1,2} \w{3}|\d+)\)$/, "").replace(/^_chat$/, "").trim();

/* Read one export file into a "source": hashes, parsed messages and its media. */
async function readSource(file, { prog, importedAt = Date.now(), importedBy = S.user?.username || "-" } = {}) {
  const isZip = /\.zip$/i.test(file.name) || /zip/.test(file.type || "");
  const isTxt = /\.txt$/i.test(file.name);
  if (!isZip && !isTxt) throw new Error("Choose the .zip (with media) or .txt file exported from WhatsApp.");
  const buf = await file.arrayBuffer();
  prog?.step(0);
  const hash = await sha256(buf.slice(0));
  prog?.step(1, `SHA-256 ${hash.slice(0, 16)}…`);
  let chatText, txtName = file.name; const media = new Map(); const fileHashes = [];
  if (isZip) {
    await libs.zip();
    const zip = await JSZip.loadAsync(buf);
    const entries = Object.values(zip.files).filter(f => !f.dir && !/^__MACOSX\//.test(f.name));
    const txts = entries.filter(f => /\.txt$/i.test(f.name));
    const chatEntry = txts.find(f => /(^|\/)_chat\.txt$/i.test(f.name)) || txts.find(f => /WhatsApp Chat/i.test(f.name)) || txts.sort((a, b) => (b._data?.uncompressedSize || 0) - (a._data?.uncompressedSize || 0))[0];
    if (!chatEntry) throw new Error("No chat text file found inside the ZIP.");
    chatText = await chatEntry.async("string"); txtName = chatEntry.name;
    let done = 0;
    for (const f of entries) {
      const blob = await f.async("blob"); const base = f.name.split("/").pop(); const hsh = await sha256(blob);
      fileHashes.push({ name: base, size: blob.size, hash: hsh });
      if (f !== chatEntry) media.set(base, { name: base, blob, size: blob.size, hash: hsh, kind: kindOf(base), url: null });
      if (++done % 5 === 0) prog?.bar(done / entries.length);
    }
  } else { chatText = new TextDecoder().decode(buf); fileHashes.push({ name: file.name, size: buf.byteLength, hash }); }
  prog?.step(2);
  const parsed = parseChat(chatText);
  prog?.step(3, `${parsed.messages.length.toLocaleString("en-IN")} messages`);
  const ts = parsed.messages.map(m => m.ts);
  return { name: file.name, size: buf.byteLength, hash, buf, fileHashes, txtName, rawText: chatText, parsed, media, format: parsed.format,
    first: Math.min(...ts), last: Math.max(...ts), count: parsed.messages.length, importedAt, importedBy };
}

/* Build (or rebuild) a chat from one or more sources. Repeat exports are merged:
   the same message seen again is matched by minute + sender + position, and differences become
   "recovered" (deleted later), "history" (edited later) or "goneIn" (absent from a later export). */
function buildChat(info, sources) {
  sources = sources.slice().sort((a, b) => a.last - b.last || a.first - b.first);
  const media = new Map(), byKey = new Map(), out = [];
  const sig = x => x.type + "\u0001" + (x.text || "") + "\u0001" + (x.media?.name || "");
  sources.forEach((src, si) => {
    const keyOf = new Map();
    for (const [n, f] of src.media) {
      let k = n; const ex = media.get(k);
      if (ex && ex.hash !== f.hash) k = `${n}~${si + 1}`;
      if (!media.has(k)) media.set(k, f);
      keyOf.set(n, k);
    }
    const seen = {};
    for (const m0 of src.parsed.messages) {
      const m = { ...m0, media: m0.media ? { ...m0.media } : undefined, src: si, seenIn: [si] };
      if (m.media) {
        const f = src.media.get(m.media.name) || [...src.media.values()].find(x => x.name.endsWith(m.media.name) || m.media.name.endsWith(x.name));
        if (f) { m.media.file = keyOf.get(f.name); m.media.kind = f.kind; delete m.media.missing; } else m.media.missing = true;
      }
      const base = `${Math.floor(m.ts / 60000)}|${m.sender || "~sys"}|${m.type === "system" ? m.text : ""}`;
      seen[base] = (seen[base] || 0) + 1;
      const key = base + "|" + seen[base];
      m.key = key;
      const prev = byKey.get(key);
      if (!prev) { byKey.set(key, m); out.push(m); continue; }
      prev.seenIn.push(si);
      if (sig(prev) === sig(m)) { if (prev.media?.missing && m.media && !m.media.missing) prev.media = m.media; continue; }
      if (m.type === "deleted" && prev.type !== "deleted") {
        prev.recovered = { type: prev.type, text: prev.text, media: prev.media, src: prev.src };
        Object.assign(prev, { type: "deleted", text: m.text, media: undefined, deletedIn: si, src: si });
      } else if (prev.type === "deleted" && m.type !== "deleted") {
        Object.assign(prev, { type: m.type, text: m.text, media: m.media, src: si });
      } else {
        (prev.history ||= []).push({ text: prev.text, src: prev.src });
        Object.assign(prev, { type: m.type, text: m.text, media: m.media || prev.media, edited: true, editedIn: si, src: si });
      }
    }
  });
  for (const m of out) {
    const firstSeen = Math.min(...m.seenIn);
    for (let sj = firstSeen + 1; sj < sources.length; sj++)
      if (!m.seenIn.includes(sj) && sources[sj].first <= m.ts && m.ts <= sources[sj].last) { m.goneIn = sj; break; }
    m.newIn = firstSeen;
  }
  out.sort((a, b) => a.ts - b.ts);
  out.forEach((m, i) => m.id = i + 1);
  const counts = {}; for (const m of out) if (m.sender) counts[m.sender] = (counts[m.sender] || 0) + 1;
  const participants = Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([name, n]) => ({ name, n, h: hueOf(name) }));
  const latest = sources[sources.length - 1];
  let title = info.title || nameFromFile(latest.name) || nameFromFile(latest.txtName.split("/").pop()) || participants.slice(0, 3).map(p => p.name).join(", ");
  const isGroup = participants.length > 2 || out.some(m => m.type === "system" && /created (group|this group)|added/i.test(m.text));
  let me = info.me;
  if (me === undefined) {
    me = null;
    if (!isGroup && participants.length === 2) me = participants.find(p => p.name !== title)?.name || null;
    if (!me) me = participants.find(p => /^(you|me)$/i.test(p.name))?.name || null;
  }
  const used = new Set(out.filter(m => m.media?.file).map(m => m.media.file));
  const omitted = out.filter(m => m.type === "omitted").length, refs = out.filter(m => m.type === "media").length;
  const noMedia = media.size === 0 && (omitted + refs) > 0;
  return {
    id: info.id || uid(), title, me, tags: info.tags || [], note: info.note || "", sample: !!info.sample, saved: !!info.saved, verified: info.verified,
    matter: info.matter || {}, stars: info.stars || {}, mnotes: info.mnotes || {}, events: info.events || [], noMedia, omittedCount: omitted + out.filter(m => m.media?.missing).length,
    sources, messages: out, participants, isGroup, media, h: hueOf(title),
    // convenience fields for the latest export
    zipHash: latest.hash, sourceName: latest.name, sourceSize: latest.size, format: latest.format, rawText: latest.rawText,
    fileHashes: sources.flatMap(s => s.fileHashes), importedAt: info.importedAt || sources[0].importedAt, importedBy: info.importedBy || sources[0].importedBy,
    linked: out.filter(m => m.media?.file).length, missing: out.filter(m => m.media?.missing).length,
    unlinkedFiles: [...media.keys()].filter(k => !used.has(k)).length, stub: false
  };
}
const changeStats = chat => ({
  recovered: chat.messages.filter(m => m.recovered).length,
  edited: chat.messages.filter(m => m.history).length,
  gone: chat.messages.filter(m => m.goneIn != null).length,
  added: chat.sources.map((s, i) => chat.messages.filter(m => m.newIn === i).length)
});

function findSameChat(src) {
  const t = nameFromFile(src.name).toLowerCase();
  const names = new Set(src.parsed.participants.map(p => p.name));
  return S.chats.find(c => !c.sample && (c.title.toLowerCase() === t ||
    (names.size >= 2 && (c.stub ? c.pnames : c.participants.map(p => p.name)).filter(n => names.has(n)).length >= Math.min(names.size, 2))));
}
function askMerge(chat, src) {
  return new Promise(res => {
    const ov = h(`<div class="overlay"><div class="modal" role="dialog" aria-modal="true" aria-labelledby="mgT">
      <div class="modal-head"><h3 id="mgT">This looks like a chat you already have</h3></div>
      <div class="modal-body"><p class="muted" style="margin:0">“${esc(src.name)}” has the same participants as <b>${esc(mask(chat.title, chat))}</b>.</p>
        <button class="exp-opt" data-c="merge"><span class="ico">${ic("merge")}</span><div><b>Merge into the existing chat</b><span>Adds new messages, recovers messages deleted since the earlier export and flags edits. Both exports keep their own fingerprints.</span></div></button>
        <button class="exp-opt" data-c="new"><span class="ico">${ic("plus")}</span><div><b>Keep as a separate chat</b><span>Import it on its own.</span></div></button></div></div></div>`);
    document.body.append(ov);
    ov.addEventListener("click", e => { const b = e.target.closest("[data-c]"); if (b) { ov.remove(); res(b.dataset.c); } });
  });
}

async function importFile(file, { sample = false, me: sampleMe, into = null, quiet = false, bulk = false, autoMerge = true } = {}) {
  if (!sample && !can("import")) { toast("Your role cannot import chats", "err"); return; }
  S.lastImportError = "";
  const prog = (sample || quiet || bulk) ? null : progressModal(file.name);
  try {
    const src = await readSource(file, { prog });
    await sleep(prog ? 250 : 0); prog?.close();
    let target = into ? S.chats.find(c => c.id === into) : null;
    if (!target && !sample) { const cand = findSameChat(src); if (cand && (bulk ? autoMerge : await askMerge(cand, src) === "merge")) target = cand; }
    if (target) {
      if (target.stub) await hydrate(target);
      if (target.sources.some(s => s.hash === src.hash)) { if (!bulk) { toast("This export is already part of the chat"); openChat(target.id); } target._lastAction = "duplicate"; return target; }
      const before = changeStats(target);
      Object.assign(target, buildChat(target, [...target.sources, src])); delete target._alias;
      const st = changeStats(target);
      if (!target.sample) { audit("Merged export", `${target.title} · ${file.name} · SHA-256 ${src.hash}`); (target.events ||= []).push({ t: Date.now(), user: S.user?.username || "-", action: "Merged newer export", detail: `${file.name} · ${src.count} messages`, hash: src.hash }); await persistChat(target); }
      target._lastAction = "merged";
      renderList(); if (bulk) return target;
      await openChat(target.id);
      if (!target.sample) toast(`Merged: ${st.added[target.sources.findIndex(s => s.hash === src.hash)] || 0} new messages · ${st.recovered - before.recovered} deleted messages recovered · ${st.edited - before.edited} edits found`);
      return target;
    }
    const chat = buildChat({ sample, me: sampleMe }, [src]);
    S.chats.unshift(chat);
    if (!sample) {
      audit("Imported chat", `${file.name} · ${src.count} messages · SHA-256 ${src.hash}`);
      chat.events.push({ t: Date.now(), user: S.user?.username || "-", action: "Imported", detail: `${file.name} · ${src.count} messages · ${fmtBytes(src.size)}`, hash: src.hash });
      if (!bulk) { const who = await askWhoAmI(chat); if (who !== undefined) chat.me = who; }
      await persistChat(chat);
    }
    chat._lastAction = "new";
    renderList(); if (bulk) { if (!S.active) openChat(chat.id); return chat; }
    await openChat(chat.id);
    if (!sample) toast(`Imported ${src.count.toLocaleString("en-IN")} messages and ${chat.linked} attachments${chat.saved ? " · saved securely" : ""}`);
    return chat;
  } catch (e) { prog?.close(); console.error(e); S.lastImportError = e.message || "Could not read this file"; if (!bulk) toast(S.lastImportError, "err"); }
}
function progressModal(name) {
  const steps = ["Reading archive", "Computing SHA-256 fingerprints", "Parsing messages", "Linking attachments"];
  const ov = h(`<div class="overlay"><div class="modal" role="dialog" aria-modal="true" aria-label="Importing">
    <div class="modal-head"><h3>Importing chat</h3></div>
    <div class="modal-body"><div class="muted" style="overflow-wrap:anywhere">${esc(name)}</div>
      <div class="progress-steps">${steps.map((s, i) => `<div class="pstep" data-i="${i}"><span class="dot"></span><span>${s}</span><span class="faint" style="margin-left:auto;font-size:12px"></span></div>`).join("")}</div>
      <div class="pbar"><i></i></div><div class="note">Processing happens on this device. The file is not uploaded anywhere.</div></div></div></div>`);
  document.body.append(ov);
  return {
    step(i, note) { $$(".pstep", ov).forEach((el, j) => { el.classList.toggle("done", j < i); el.classList.toggle("on", j === i); if (j < i) el.querySelector(".dot").innerHTML = ic("check"); }); if (note) $$(".pstep", ov)[i].lastElementChild.textContent = note; $(".pbar i", ov).style.width = ((i + 1) / steps.length * 100) + "%"; },
    bar(f) { $(".pbar i", ov).style.width = (25 + f * 25) + "%"; },
    close() { ov.remove(); }
  };
}
function askWhoAmI(chat) {
  return new Promise(res => {
    let pick = chat.me;
    const ov = h(`<div class="overlay"><div class="modal" role="dialog" aria-modal="true" aria-labelledby="whoT">
      <div class="modal-head"><h3 id="whoT">Who are you in this chat?</h3></div>
      <div class="modal-body"><p class="muted" style="margin:0">Your messages will appear on the right, the way they do on your phone. You can change this later in chat info.</p>
      <div class="who-grid">${chat.participants.map(p => `<button class="who-opt${p.name === pick ? " on" : ""}" data-n="${esc(p.name)}"><span class="avatar sm" style="--h:${p.h}">${esc(initials(mask(p.name, chat)))}</span><span class="pn"><b>${esc(mask(p.name, chat))}</b><span>${p.n} messages</span></span></button>`).join("")}
      <button class="who-opt${pick ? "" : " on"}" data-n=""><span class="avatar sm" style="--h:210">–</span><span class="pn"><b>None of these</b><span>Show every message on the left</span></span></button></div></div>
      <div class="modal-foot"><button class="btn btn-primary" id="whoOk">Open chat</button></div></div></div>`);
    document.body.append(ov);
    ov.addEventListener("click", e => { const b = e.target.closest(".who-opt"); if (b) { pick = b.dataset.n || null; $$(".who-opt", ov).forEach(x => x.classList.toggle("on", x === b)); } });
    $("#whoOk", ov).onclick = () => { ov.remove(); res(pick); };
  });
}
function mediaUrl(chat, name) { const f = chat.media.get(name); if (!f) return ""; return f.url ||= URL.createObjectURL(f.blob); }
function logEvent(chat, action, detail = "", hash = "") {
  if (!chat || chat.sample) return;
  (chat.events ||= []).push({ t: Date.now(), user: S.user?.username || "-", action, detail, hash });
  if (chat.saved && !chat.stub) persistChat(chat, { metaOnly: true });
}
const srcLabel = (chat, i) => chat.sources[i] ? `export of ${fmtDate(chat.sources[i].last)}` : "earlier export";

/* ---- saved chats (encrypted at rest) ---- */
function chatMeta(chat) {
  const last = [...chat.messages].reverse().find(m => m.type !== "system");
  return {
    title: chat.title, me: chat.me, tags: chat.tags, note: chat.note, isGroup: chat.isGroup, importedAt: chat.importedAt, importedBy: chat.importedBy,
    matter: chat.matter, stars: chat.stars, mnotes: chat.mnotes, events: (chat.events || []).slice(-300),
    pnames: chat.participants.map(p => p.name), msgCount: chat.messages.length,
    first: chat.messages[0]?.ts, lastTs: last?.ts,
    preview: last ? { sender: last.sender, type: last.type, kind: last.media?.kind, name: last.media?.name, text: (last.text || "").slice(0, 120), ts: last.ts } : null,
    sources: chat.sources.map(s => ({ name: s.name, size: s.size, hash: s.hash, format: s.format, first: s.first, last: s.last, count: s.count, importedAt: s.importedAt, importedBy: s.importedBy }))
  };
}
async function persistChat(chat, { metaOnly = false } = {}) {
  if (chat.sample || !S.vaultKey) return false;
  if (!chat.saved && !settings().autoSave) return false;
  try {
    if (!metaOnly) for (const s of chat.sources) if (!s.stored) { await idb.putBlob(`${chat.id}/${s.hash}`, await aesEnc(S.vaultKey, s.buf.slice(0))); s.stored = true; }
    await idb.put({ id: chat.id, m: await aesEnc(S.vaultKey, chatMeta(chat)), savedAt: Date.now(), size: chat.sources.reduce((a, s) => a + s.size, 0) });
    chat.saved = true; scheduleFolderSync(); return true;
  } catch (e) { console.error(e); toast("Could not save this chat on the device", "err"); return false; }
}
async function loadSavedIndex() {
  if (!S.vaultKey || !(await idb.ok())) return 0;
  let n = 0, bad = 0;
  for (const rec of await idb.all()) {
    if (S.chats.some(c => c.id === rec.id)) continue;
    try { const meta = await aesDec(S.vaultKey, rec.m, true); S.chats.push({ ...meta, id: rec.id, stub: true, saved: true, savedAt: rec.savedAt, size: rec.size, h: hueOf(meta.title), participants: [], messages: [] }); n++; }
    catch { bad++; }
  }
  if (bad) toast(`${bad} saved chat${bad > 1 ? "s" : ""} could not be unlocked with this account`, "err");
  return n;
}
async function hydrate(chat) {
  if (!chat.stub) return chat;
  const sources = [];
  for (const sm of chat.sources) {
    const rec = await idb.blob(`${chat.id}/${sm.hash}`);
    if (!rec) throw new Error(`Saved file missing: ${sm.name}`);
    const buf = await aesDec(S.vaultKey, rec);
    const src = await readSource(new File([buf], sm.name, { type: /\.zip$/i.test(sm.name) ? "application/zip" : "text/plain" }), { importedAt: sm.importedAt, importedBy: sm.importedBy });
    src.stored = true; src.verified = src.hash === sm.hash; sources.push(src);
  }
  const built = buildChat({ id: chat.id, title: chat.title, me: chat.me, tags: chat.tags, note: chat.note, importedAt: chat.importedAt, importedBy: chat.importedBy, saved: true,
    matter: chat.matter, stars: chat.stars, mnotes: chat.mnotes, events: chat.events }, sources);
  built.verified = sources.every(s => s.verified);
  if (!built.verified) { audit("Integrity check failed", chat.title); logEvent(built, "Integrity check FAILED on open", "A saved export no longer matches its fingerprint"); }
  else { const lv = [...built.events].reverse().find(e => e.action === "Verified on open"); if (!lv || Date.now() - lv.t > 12 * 3600e3) logEvent(built, "Verified on open", `${sources.length} export${sources.length > 1 ? "s" : ""} re-hashed and matched`, sources.map(s => s.hash).join(" ")); }
  Object.keys(chat).forEach(k => delete chat[k]); Object.assign(chat, built);
  return chat;
}
async function hydrateAll() { for (const c of S.chats.filter(c => c.stub)) { try { await hydrate(c); } catch (e) { console.error(e); } } }

/* ============================================================ masking and redaction */
const PHONE_RE = /(\+?\d[\d\s\-]{8,}\d)/g, MAIL_RE = /([\w.+-]+)@([\w-]+\.[\w.-]+)/g;
function maskStr(s) { return String(s).replace(PHONE_RE, p => { const d = p.replace(/\D/g, ""); return d.length < 10 ? p : "•••• ••" + d.slice(-3); }).replace(MAIL_RE, (m, a, b) => a[0] + "•••@" + b); }
let R = null; // redaction context while exporting: {contacts, names}
function aliasMap(chat) {
  if (chat._alias) return chat._alias;
  const L = i => (i >= 26 ? L(Math.floor(i / 26) - 1) : "") + String.fromCharCode(65 + (i % 26));
  const names = chat.stub ? (chat.pnames || []) : chat.participants.map(p => p.name);
  const pairs = names.map((n, i) => [n, "Participant " + L(i)]);
  const firsts = {}; names.forEach(n => { const f = n.split(/\s+/)[0]; if (f.length >= 3 && /^\p{L}/u.test(f)) firsts[f] = (firsts[f] || 0) + 1; });
  names.forEach((n, i) => { const f = n.split(/\s+/)[0]; if (firsts[f] === 1 && f !== n) pairs.push([f, "Participant " + L(i)]); });
  pairs.sort((a, b) => b[0].length - a[0].length);
  const re = pairs.length ? new RegExp("(?<![\\p{L}\\p{N}])(" + pairs.map(p => p[0].replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|") + ")(?![\\p{L}\\p{N}])", "giu") : null;
  const lookup = new Map(pairs.map(([a, b]) => [a.toLowerCase(), b]));
  return chat._alias = { re, lookup };
}
function mask(s, chat) {
  s = String(s ?? ""); chat = chat || activeChat();
  const ctx = R || { contacts: !can("unmasked"), names: !can("unmasked") && settings().viewerNames };
  if (ctx.names && chat) { const a = aliasMap(chat); if (a.re) s = s.replace(a.re, m => a.lookup.get(m.toLowerCase()) || m); }
  if (ctx.contacts) s = maskStr(s);
  return s;
}

/* ============================================================ message rendering */
function fmtText(t, q) {
  let s = esc(t);
  const codes = []; s = s.replace(/```([\s\S]+?)```/g, (m, c) => { codes.push(c); return `\u0000${codes.length - 1}\u0000`; });
  s = s.replace(/(^|[\s(>])\*(\S(?:[^*\n]*?\S)?)\*(?=$|[\s.,!?:;)<])/g, "$1<b>$2</b>")
       .replace(/(^|[\s(>])_(\S(?:[^_\n]*?\S)?)_(?=$|[\s.,!?:;)<])/g, "$1<i>$2</i>")
       .replace(/(^|[\s(>])~(\S(?:[^~\n]*?\S)?)~(?=$|[\s.,!?:;)<])/g, "$1<s>$2</s>")
       .replace(/\b(https?:\/\/[^\s<]+[^\s<.,:;"')\]])/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>')
       .replace(/(^|[\s(])(www\.[^\s<]+[^\s<.,:;"')\]])/g, '$1<a href="https://$2" target="_blank" rel="noopener noreferrer">$2</a>');
  s = s.replace(/\u0000(\d+)\u0000/g, (m, i) => `<code>${codes[+i]}</code>`);
  if (q) { const re = new RegExp("(" + q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi"); s = s.replace(/(<[^>]+>)|([^<]+)/g, (m, tag, txt) => tag || txt.replace(re, "<mark>$1</mark>")); }
  return s;
}
const extOf = n => (n.split(".").pop() || "").slice(0, 4).toLowerCase();
function waveBars(seed, n = 34) { let x = hueOf(seed) + 7; return Array.from({ length: n }, (_, i) => { x = (x * 9301 + 49297) % 233280; const v = 0.25 + (x / 233280) * 0.75 * (0.6 + 0.4 * Math.sin(i / 3)); return Math.max(.15, Math.min(1, v)); }); }

/* opts: {src(name)->url, me, isGroup, q, exportMode} */
function msgHTML(chat, m, prev, o) {
  if (m.type === "system") {
    const e2e = /end-to-end encrypted/i.test(m.text);
    return `<div class="sys${e2e ? " e2e" : ""}" data-id="${m.id}"><span>${e2e ? ic("lock") : ""}${esc(mask(m.text, chat))}</span></div>`;
  }
  const out = !!o.me && m.sender === o.me;
  const first = !prev || prev.type === "system" || prev.sender !== m.sender || (m.ts - prev.ts) > 6 * 60 * 1000 || isoDay(prev.ts) !== isoDay(m.ts);
  const p = chat.participants.find(x => x.name === m.sender);
  const nameTag = (o.isGroup && !out && first) ? `<span class="sender" style="--h:${p?.h ?? 0}">${esc(mask(m.sender, chat))}</span>` : "";
  const gone = m.goneIn != null ? `<span class="gone" title="Present in the ${esc(srcLabel(chat, m.seenIn[0]))}, absent from the ${esc(srcLabel(chat, m.goneIn))}">Not in later export</span>` : "";
  const starred = !!chat.stars?.[m.key], mnote = chat.mnotes?.[m.key];
  const meta = `<span class="meta">${starred ? `<span class="star" title="Starred">${ic("star", "i")}</span>` : ""}${gone}${m.edited ? '<span class="ed">Edited</span>' : ""}${fmtTime(m.ts)}</span>`;
  const extra = (m.recovered ? `<div class="recov"><span class="rl">${ic("restore")}Recovered from the ${esc(srcLabel(chat, m.recovered.src))}</span>${m.recovered.media ? `<span class="mono">${esc(m.recovered.media.name)}</span> ` : ""}${fmtText(mask(m.recovered.text || "", chat))}</div>` : "")
    + (m.history ? m.history.map(x => `<details class="hist"><summary>Earlier version · ${esc(srcLabel(chat, x.src))}</summary><span class="txt">${fmtText(mask(x.text || "", chat))}</span></details>`).join("") : "")
    + (mnote ? `<div class="mnote">${ic("pen", "i")}<span>${esc(mnote)}</span></div>` : "");
  let inner = "", cls = "";
  if (m.type === "deleted") { cls = " deleted"; inner = `${nameTag}<span class="txt">${ic("ban")}${out ? "You deleted this message" : "This message was deleted"}</span>${extra}${meta}`; }
  else if (m.type === "omitted") inner = `${nameTag}<div class="omitted">${ic("clip")}<span>${m.text === "media" ? "Media" : esc(m.text[0].toUpperCase() + m.text.slice(1))} not included · chat was exported without media</span></div>${extra}${meta}`;
  else if (m.type === "media") {
    const md = m.media, cap = (m.text ? `<span class="txt">${fmtText(mask(m.text, chat), o.q)}</span>` : "") + extra;
    if (md.missing) inner = `${nameTag}<div class="m-missing">${ic("clip")}<span>Attachment not in export<br><span class="mono">${esc(md.name)}</span></span></div>${cap}${meta}`;
    else {
      const url = o.src(md.file), f = chat.media.get(md.file);
      if (md.kind === "image") { cls = " has-img"; inner = `${nameTag}<button class="m-img${m.text ? " cap" : ""}" data-act="view" data-id="${m.id}" aria-label="Open photo"><img src="${url}" alt="Photo from ${esc(mask(m.sender, chat))}" loading="lazy">${(m.text || extra) ? "" : meta}</button>${(m.text || extra) ? cap + meta : ""}`; }
      else if (md.kind === "sticker") { cls = " m-sticker"; inner = `<img src="${url}" alt="Sticker" loading="lazy" style="width:150px;height:150px;object-fit:contain">${meta}`; }
      else if (md.kind === "video") { cls = " has-img"; inner = `${nameTag}<div class="m-vid"><video src="${url}" controls preload="metadata" playsinline></video></div>${cap}${meta}`; }
      else if (md.kind === "audio") {
        cls = " has-voice"; const bars = waveBars(md.file).map(v => `<i style="height:${Math.round(v * 100)}%"></i>`).join("");
        const av = p ? `<span class="avatar mic" style="--h:${p.h}">${esc(initials(mask(m.sender, chat)))}${ic("mic")}</span>` : "";
        inner = `${nameTag}<div class="voice" data-src="${url}">${out ? "" : av}<button class="play" data-act="play" aria-label="Play voice note">${ic("play")}</button><div class="wave" data-act="seek">${bars}</div>${out ? av : ""}<span class="vt">Voice note</span></div>${cap}${meta}`;
      } else {
        const ext = extOf(f.name); const sub = [ext.toUpperCase(), md.pages ? md.pages + (md.pages > 1 ? " pages" : " page") : "", f ? fmtBytes(f.size) : ""].filter(Boolean).join(" · ");
        inner = `${nameTag}<button class="m-doc" data-act="doc" data-id="${m.id}" data-href="${url}"><span class="ext ${esc(ext)}">${esc(ext.toUpperCase())}</span><span class="dn"><b>${esc(f.name.replace(/^\d{8}-/, ""))}</b><span>${esc(sub)}</span></span></button>${cap}${meta}`;
      }
    }
  } else inner = `${nameTag}<span class="txt">${fmtText(mask(m.text, chat), o.q)}</span>${extra}${meta}`;
  const act = o.archive ? "" : `<button class="msg-act" data-act="menu" aria-label="Message options">${ic("chevD")}</button>`;
  return `<div class="msg ${out ? "out" : "in"}${first ? " first" : ""}${starred ? " starred" : ""}" data-id="${m.id}"><div class="bubble${cls}">${act}${inner}</div></div>`;
}
function threadHTML(chat, o) {
  let html = "", day = null, prev = null;
  for (const m of chat.messages) {
    const d = isoDay(m.ts);
    if (d !== day) { if (day) html += "</section>"; html += `<section class="day" data-day="${d}"><div class="day-chip"><span data-act="jump">${fmtDay(m.ts)}</span></div>`; day = d; prev = null; }
    html += msgHTML(chat, m, prev, o); prev = m;
  }
  return html + (day ? "</section>" : "");
}

/* ============================================================ shell rendering */
const root = () => $("#app");
function renderAuth() {
  const first = users().length === 0;
  const demo = `<div class="demo-chat">
    <div class="msg in first"><div class="bubble"><span class="sender" style="--h:200">Rakesh Mehta</span><span class="txt">Sir, attaching the October purchase invoices</span><span class="meta">10:20 am</span></div></div>
    <div class="msg in"><div class="bubble"><button class="m-doc" tabindex="-1"><span class="ext pdf">PDF</span><span class="dn"><b>GSTR-2B Reconciliation.pdf</b><span>PDF · 2 pages · 3 KB</span></span></button><span class="meta">10:21 am</span></div></div>
    <div class="msg out first"><div class="bubble"><span class="txt">Received. Archived with SHA-256 fingerprint ✓</span><span class="meta">10:24 am</span></div></div></div>`;
  root().innerHTML = `<div class="auth"><div class="auth-card">
    <div class="auth-art"><div class="brand"><span class="logo">${ic("vault")}</span>ChatVault</div>
      <h1>WhatsApp chats, archived as records you can rely on.</h1>
      <p>Import an exported chat with its attachments. Read it the way it looked on the phone, search it, analyse it, and export a fingerprinted archive.</p>${demo}</div>
    <form class="auth-form" id="authForm" autocomplete="on" novalidate>
      ${first ? `<h2>Set up ChatVault</h2><p class="sub">Create the administrator account for this device.</p>
        <div class="field"><label for="fName">Full name</label><input class="input" id="fName" required autocomplete="name" placeholder="e.g. Vihit Vasani"></div>
        <div class="field"><label for="fUser">Username</label><input class="input" id="fUser" required autocomplete="username" placeholder="admin" value="admin"></div>
        <div class="field"><label for="fPw">Password</label><div class="pw-wrap"><input class="input" id="fPw" type="password" required autocomplete="new-password" placeholder="At least 8 characters, a letter and a number"><button type="button" class="icon-btn" data-act="pw" aria-label="Show password">${ic("eye")}</button></div></div>
        <label class="check"><input type="checkbox" id="fDemo" checked><span>Also create two demo accounts so you can try the other roles<br><span class="faint">reviewer / Review@123 · viewer / Viewer@123</span></span></label>
        <div class="err" id="fErr" role="alert"></div>
        <button class="btn btn-primary" type="submit">Create account and continue</button>
        ${FS_OK ? `<button class="btn btn-ghost" type="button" id="openArchive">${ic("db")}Open an existing archive folder</button>` : ""}`
      : `<h2>Sign in</h2><p class="sub">Access is limited to authorised users.</p>
        <div class="field"><label for="fUser">Username</label><input class="input" id="fUser" required autocomplete="username" autofocus></div>
        <div class="field"><label for="fPw">Password</label><div class="pw-wrap"><input class="input" id="fPw" type="password" required autocomplete="current-password"><button type="button" class="icon-btn" data-act="pw" aria-label="Show password">${ic("eye")}</button></div></div>
        <div class="err" id="fErr" role="alert"></div>
        <button class="btn btn-primary" type="submit">Sign in</button>
        ${FS_OK ? `<button class="btn btn-ghost btn-sm" type="button" id="openArchive" style="justify-self:start">${ic("db")}Open a different archive folder</button>` : ""}
        ${users().some(u => u.username === "reviewer") ? `<div class="demo-creds"><span class="faint">Demo accounts on this device</span><span>Reviewer: <b>reviewer</b> / <b>Review@123</b></span><span>Viewer: <b>viewer</b> / <b>Viewer@123</b></span></div>` : ""}`}
      <p class="note">${ic("shield", "i")}&nbsp;Passwords are stored only as salted PBKDF2-SHA-256 hashes. Saved chats are encrypted with AES-256 and unlock only with a valid password. Five wrong attempts lock the account for two minutes.</p>
    </form></div></div>`;
  $("[data-act=pw]").onclick = e => { const i = $("#fPw"); const show = i.type === "password"; i.type = show ? "text" : "password"; e.currentTarget.innerHTML = ic(show ? "eyeoff" : "eye"); };
  $("#openArchive") && ($("#openArchive").onclick = openArchiveFromAuth);
  $("#authForm").onsubmit = async e => {
    e.preventDefault(); const err = $("#fErr"); err.textContent = ""; const btn = e.target.querySelector("[type=submit]"); btn.disabled = true;
    try {
      if (first) {
        S.vaultKey = await newVaultKey();
        const u = await createUser({ name: $("#fName").value || "Administrator", username: $("#fUser").value, password: $("#fPw").value, role: "admin" });
        if ($("#fDemo").checked) { await createUser({ name: "Demo Reviewer", username: "reviewer", password: "Review@123", role: "reviewer" }); await createUser({ name: "Demo Viewer", username: "viewer", password: "Viewer@123", role: "viewer" }); }
        S.user = u; audit("Created administrator account", u.username); audit("Signed in");
      } else await login($("#fUser").value, $("#fPw").value);
      startApp();
    } catch (x) { err.textContent = x.message; e.target.classList.remove("shake"); void e.target.offsetWidth; e.target.classList.add("shake"); btn.disabled = false; }
  };
}

async function startApp() {
  S.locked = false; S.lastActivity = Date.now(); S.tagFilter = ""; S.globalHits = null;
  root().innerHTML = `<div class="app" id="shell">
    <aside class="side" aria-label="Chats">
      <div class="side-head"><div class="brand"><span class="logo">${ic("vault")}</span>ChatVault</div>
        <button class="icon-btn" data-privacy title="Privacy screen (Ctrl+.)" aria-label="Privacy screen">${ic("shade")}</button>
        <button class="icon-btn" id="btnImport" title="Import chats" aria-label="Import chats"${can("import") ? "" : " disabled"}>${ic("plus")}</button>
        <button class="icon-btn" id="btnMenu" title="Menu" aria-label="Menu">${ic("dots")}</button></div>
      <div class="side-search"><label class="search-box">${ic("search")}<input id="chatFilter" placeholder="Search chats, tags and messages" aria-label="Search chats, tags and messages"></label>
        <div class="tag-bar" id="tagBar"></div></div>
      <div class="chat-list" id="chatList"></div>
      <div class="user-bar"><span class="avatar sm" style="--h:${hueOf(S.user.username)}">${esc(initials(S.user.name))}</span><span class="who"><b>${esc(S.user.name)}</b><span><span class="pill ${S.user.role}">${ROLES[S.user.role].label}</span></span></span>
        <button class="icon-btn" id="btnLook" title="Appearance" aria-label="Appearance">${ic("palette")}</button>
        <button class="icon-btn" id="btnTour" title="Take the tour" aria-label="Take the tour">${ic("help")}</button>
        <button class="icon-btn" id="btnLock" title="Lock" aria-label="Lock">${ic("lock")}</button></div>
      <div class="side-foot" id="sideFoot">${ic("shield")}<span>Processed on this device · nothing is uploaded</span></div>
    </aside>
    <main class="main" id="main"></main>
    <aside class="drawer" id="drawer" aria-label="Details"><div class="drawer-inner" id="drawerInner"></div></aside>
    <input type="file" id="fileIn" accept=".zip,.txt,application/zip,text/plain" multiple hidden>
  </div><div class="toasts" role="status" aria-live="polite"></div>`;
  $("#btnImport").onclick = () => { S.importInto = null; $("#fileIn").click(); };
  $("#fileIn").onchange = e => { const fs = [...e.target.files]; e.target.value = ""; const into = S.importInto; S.importInto = null; if (fs.length > 1) bulkImport(fs); else if (fs[0]) importFile(fs[0], { into }); };
  $("#btnLook").onclick = e => { e.stopPropagation(); openAppearance(e.currentTarget); };
  $("#btnMenu").onclick = e => openMenu(e.currentTarget, mainMenu());
  $("#btnLock").onclick = lockScreen;
  $("#btnTour").onclick = () => startTour();
  let tmr; $("#chatFilter").oninput = () => { clearTimeout(tmr); tmr = setTimeout(onSideSearch, 120); };
  renderList(); renderEmpty();
  const n = (await loadSavedIndex()) + (await folderInit());
  updateFoot();
  if (!S.chats.some(c => !c.sample)) await loadSamples();
  else { renderList(); await openChat(sortedChats()[0].id); if (n) toast(`${n} saved chat${n > 1 ? "s" : ""} unlocked`); }
  if (!S.vaultKey && users().some(x => x.wsalt)) toast("Saved chats are locked for this account. Ask an admin to reset your password to unlock them.", "err");
  await maybeAskFolder();
  if (!sget(K.toured, {})[S.user.username]) setTimeout(() => startTour(), 500);
}
function updateFoot() {
  const f = $("#sideFoot"); if (!f) return;
  const saved = S.chats.filter(c => c.saved).length; const F = S.folder || {};
  let icon = "shield", t, btn = "";
  if (F.status === "ok") { icon = "db"; t = `${saved} saved · folder <b>${esc(F.label)}</b>${F.lastSync ? ` · synced ${ago(F.lastSync)}` : ""}`; }
  else if (F.status === "needs-permission") { icon = "db"; t = `Folder <b>${esc(F.label)}</b> needs permission`; btn = `<button class="btn btn-primary btn-sm" id="footRe">Reconnect</button>`; }
  else if (F.status === "error") { icon = "db"; t = `<span style="color:var(--danger)">Folder not reachable</span> · ${saved} saved in this browser`; btn = `<button class="btn btn-ghost btn-sm" id="footFix">Fix</button>`; }
  else t = S.vaultKey ? `${saved} saved chat${saved === 1 ? "" : "s"} · encrypted in this browser` : "Processed on this device · nothing is uploaded";
  f.innerHTML = `${ic(icon)}<span class="foot-t">${t}</span>${btn}`;
  $("#footRe") && ($("#footRe").onclick = reconnectFolder);
  $("#footFix") && ($("#footFix").onclick = () => openVault("storage"));
}
function mainMenu() {
  return [
    ["upload", "Import chat", () => { S.importInto = null; $("#fileIn").click(); }, !can("import")],
    ["db", "Saved chats and backup", openVault, !can("manage"), true],
    ["users", "Users and roles", openUsers, !can("users"), true],
    ["log", "Audit log", () => openUsers("audit"), !can("audit"), true],
    ["key", "Change password", changePassword],
    ["palette", "Appearance", () => openAppearance($("#btnMenu"))],
    ["keyboard", "Keyboard shortcuts", showShortcuts],
    ["help", "Take the tour", () => startTour()],
    ["restore", "Reload sample chats", loadSamples],
    "-",
    ["lock", "Lock screen", lockScreen],
    ["out", "Sign out", signOut]
  ];
}
function openMenu(anchor, items) {
  closeMenus();
  const r = anchor.getBoundingClientRect();
  const m = h(`<div class="menu" role="menu"></div>`);
  items.forEach(it => {
    if (it === "-") return m.append(h("<hr>"));
    const [icon, label, fn, disabled, lockedIco] = it;
    const b = h(`<button role="menuitem"${disabled ? " disabled" : ""}>${ic(icon)}<span>${label}</span>${disabled && lockedIco ? `<span class="lock-ico">${ic("lock")}</span>` : ""}</button>`);
    b.onclick = () => { closeMenus(); fn(); }; m.append(b);
  });
  document.body.append(m);
  const w = m.offsetWidth; m.style.top = Math.max(8, Math.min(r.bottom + 4, innerHeight - m.offsetHeight - 8)) + "px"; m.style.left = Math.max(8, Math.min(r.right - w, innerWidth - w - 8)) + "px";
  setTimeout(() => document.addEventListener("click", closeMenus, { once: true }), 0);
}
const closeMenus = () => $$(".menu").forEach(x => x.remove());

/* chat list: tags, sorting, cross-chat message search */
const lastTsOf = c => c.stub ? (c.lastTs || 0) : ([...c.messages].reverse().find(m => m.type !== "system")?.ts || 0);
function sortedChats() {
  const arr = S.chats.slice();
  if (S.sort === "name") arr.sort((a, b) => a.title.localeCompare(b.title));
  else if (S.sort === "client") arr.sort((a, b) => (a.matter?.client ? 0 : 1) - (b.matter?.client ? 0 : 1) || (a.matter?.client || "").localeCompare(b.matter?.client || "") || lastTsOf(b) - lastTsOf(a));
  else if (S.sort === "imported") arr.sort((a, b) => (b.importedAt || 0) - (a.importedAt || 0));
  else arr.sort((a, b) => lastTsOf(b) - lastTsOf(a));
  return arr;
}
const allTags = () => { const m = new Map(); S.chats.forEach(c => (c.tags || []).forEach(t => m.set(t, (m.get(t) || 0) + 1))); return [...m.entries()].sort((a, b) => a[0].localeCompare(b[0])); };
function renderTagBar() {
  const bar = $("#tagBar"); if (!bar) return;
  const tags = allTags();
  bar.innerHTML = `${tags.length ? `<button class="tchip${S.tagFilter ? "" : " on"}" data-tag="">All</button>${tags.map(([t, n]) => `<button class="tchip${S.tagFilter === t ? " on" : ""}" data-tag="${esc(t)}">${ic("tag")}${esc(t)} <span>${n}</span></button>`).join("")}` : ""}
    <label class="sort">${ic("sort")}<select id="sortSel" aria-label="Sort chats"><option value="recent"${S.sort === "recent" ? " selected" : ""}>Latest message</option><option value="client"${S.sort === "client" ? " selected" : ""}>Client</option><option value="name"${S.sort === "name" ? " selected" : ""}>Name</option><option value="imported"${S.sort === "imported" ? " selected" : ""}>Recently imported</option></select></label>`;
  bar.onclick = e => { const b = e.target.closest("[data-tag]"); if (b) { S.tagFilter = b.dataset.tag; renderList(); } };
  $("#sortSel").onchange = e => { S.sort = e.target.value; renderList(); };
}
async function onSideSearch() {
  const q = ($("#chatFilter")?.value || "").trim();
  S.globalHits = null; renderList();
  if (q.length < 3) return;
  if (S.chats.some(c => c.stub)) { S.globalHits = "loading"; renderList(); await hydrateAll(); if (($("#chatFilter")?.value || "").trim() !== q) return; }
  const ql = q.toLowerCase(), hits = [];
  for (const c of S.chats) for (const m of c.messages) {
    if (m.type === "system" || !m.sender) continue;
    const hay = (m.text || "") + " " + (m.media?.name || "") + " " + (m.recovered?.text || "");
    if (hay.toLowerCase().includes(ql)) hits.push({ c, m });
  }
  hits.sort((a, b) => b.m.ts - a.m.ts);
  S.globalHits = { q, hits }; renderList();
}
function previewOf(c) {
  if (c.stub) { const p = c.preview; if (!p) return { ts: 0, text: "" }; return { ts: p.ts, sender: p.sender, text: p.type === "media" ? ({ image: "Photo", video: "Video", audio: "Voice note", sticker: "Sticker" }[p.kind] || p.name) : p.type === "deleted" ? "This message was deleted" : p.text, kind: p.type === "media" ? p.kind : p.type }; }
  const last = [...c.messages].reverse().find(m => m.type !== "system") || c.messages[c.messages.length - 1];
  if (!last) return { ts: 0, text: "" };
  return { ts: last.ts, sender: last.sender, text: last.type === "media" ? ({ image: "Photo", video: "Video", audio: "Voice note", sticker: "Sticker" }[last.media.kind] || last.media.name) : last.type === "deleted" ? "This message was deleted" : last.text, kind: last.type === "media" ? last.media.kind : last.type };
}
const PV_IC = { image: "image", video: "video", audio: "mic", sticker: "image", doc: "doc", contact: "doc", deleted: "ban" };
function renderList() {
  renderTagBar();
  const q = ($("#chatFilter")?.value || "").trim().toLowerCase();
  const list = $("#chatList"); if (!list) return;
  const names = c => c.stub ? (c.pnames || []) : c.participants.map(p => p.name);
  const chats = sortedChats().filter(c => (!S.tagFilter || (c.tags || []).includes(S.tagFilter)) &&
    (!q || c.title.toLowerCase().includes(q) || names(c).some(n => n.toLowerCase().includes(q)) || (c.tags || []).some(t => t.toLowerCase().includes(q)) || (c.note || "").toLowerCase().includes(q) || Object.values(c.matter || {}).some(v => String(v).toLowerCase().includes(q))));
  let lastGroup = null;
  let html = chats.map(c => {
    let grp = "";
    if (S.sort === "client") { const g = c.matter?.client || "No client set"; if (g !== lastGroup) { grp = `<div class="list-sec">${ic("briefcase", "i")} ${esc(g)}</div>`; lastGroup = g; } }
    const pv = previewOf(c);
    const nm = pv.sender ? mask(pv.sender, c) : "";
    const who = pv.sender && c.isGroup ? (pv.sender === c.me ? "You" : /^Participant /.test(nm) ? nm : nm.split(" ")[0]) + ": " : "";
    return grp + `<button class="chat-item${c.id === S.active ? " on" : ""}" data-id="${c.id}"><span class="avatar${c.isGroup ? " group" : ""}" style="--h:${c.h}">${esc(initials(mask(c.title, c)))}</span>
      <span class="body"><span class="row"><span class="name">${esc(mask(c.title, c))}</span><span class="when">${pv.ts ? fmtDate(pv.ts) : ""}</span></span>
      <span class="row"><span class="prev">${PV_IC[pv.kind] ? ic(PV_IC[pv.kind], "i pvi") : ""}${esc(mask(who + (pv.text || ""), c))}</span>${c.sample ? '<span class="pill sample">Sample</span>' : c.saved ? `<span class="saved" title="Saved and encrypted on this device">${ic("lock")}</span>` : ""}</span>
      ${(c.tags || []).length || c.matter?.client ? `<span class="row ctags">${c.matter?.client && S.sort !== "client" ? `<span class="cl">${ic("briefcase", "i")}${esc(c.matter.client)}</span>` : ""}${(c.tags || []).map(t => `<span>${esc(t)}</span>`).join("")}</span>` : ""}</span></button>`;
  }).join("");
  if (!chats.length && !S.globalHits) html = `<div class="center faint" style="padding:40px 20px">${S.chats.length ? "No chats match" : "No chats yet"}</div>`;
  if (S.globalHits === "loading") html += `<div class="list-sec">Messages</div><div class="thinking" style="padding:12px 16px"><span class="dots"><i></i><i></i><i></i></span>Unlocking saved chats to search</div>`;
  else if (S.globalHits) {
    const { q: gq, hits } = S.globalHits;
    html += `<div class="list-sec">Messages · ${hits.length}</div>` + (hits.slice(0, 60).map(({ c, m }) => `<button class="hit" data-chat="${c.id}" data-mid="${m.id}"><span class="hd"><b style="--h:${c.h}">${esc(mask(c.title, c))}</b><span>${fmtDate(m.ts)} · ${esc(m.sender === c.me ? "You" : mask(m.sender, c))}</span></span><span class="sn">${fmtText(mask(m.text || m.media?.name || m.recovered?.text || "", c), gq)}</span></button>`).join("") || `<div class="note" style="padding:8px 16px">No messages contain “${esc(gq)}”</div>`);
  }
  list.innerHTML = html;
  list.onclick = async e => {
    const hit = e.target.closest(".hit"); if (hit) { await openChat(hit.dataset.chat); setTimeout(() => jumpTo(hit.dataset.mid), 150); return; }
    const b = e.target.closest(".chat-item"); if (b) openChat(b.dataset.id);
  };
}
function renderEmpty() {
  S.active = null;
  $("#main").innerHTML = `<div class="empty"><div class="empty-inner">
    <span class="avatar lg" style="--h:166">${ic("vault", "i")}</span>
    <h2>Import a WhatsApp chat</h2>
    <p>Export the chat from your phone, then drop the ZIP file anywhere on this page${can("import") ? "" : ". Your role can read chats that others have imported"}.</p>
    ${can("import") ? `<button class="btn btn-primary" id="emptyImport">${ic("upload")}Choose export file</button>` : ""}
    <div class="steps"><div class="tabs" role="tablist"><button class="chip on" data-os="a" role="tab">Android</button><button class="chip" data-os="i" role="tab">iPhone</button></div>
      <ol id="howTo"></ol></div>
    <button class="btn btn-ghost btn-sm" id="emptySample">Load sample chats</button></div></div>`;
  const how = { a: ["Open the chat and tap <b>⋮ More</b>", "Tap <b>More → Export chat</b>", "Choose <b>Include media</b>", "Save or share the <b>.zip</b> file to this computer"], i: ["Open the chat and tap the <b>contact or group name</b>", "Scroll down and tap <b>Export Chat</b>", "Choose <b>Attach Media</b>", "Save the <b>.zip</b> to Files, then move it to this computer"] };
  const setOS = k => { $("#howTo").innerHTML = how[k].map(s => `<li>${s}</li>`).join(""); $$("[data-os]").forEach(b => b.classList.toggle("on", b.dataset.os === k)); };
  setOS("a"); $$("[data-os]").forEach(b => b.onclick = () => setOS(b.dataset.os));
  $("#emptyImport") && ($("#emptyImport").onclick = () => $("#fileIn").click());
  $("#emptySample").onclick = loadSamples;
  $("#shell")?.classList.remove("show-chat");
}
async function loadSamples() {
  const samples = window.CV_SAMPLES || [];
  S.chats = S.chats.filter(c => !c.sample);
  let prev = null;
  for (const s of samples) {
    const file = new File([unb64(s.b64)], s.name, { type: "application/zip" });
    const c = await importFile(file, { sample: true, me: s.me, into: s.mergeWithPrevious ? prev?.id : null });
    if (c && s.tags) c.tags = s.tags;
    if (c && s.matter) c.matter = s.matter;
    if (c && s.stars) { const want = new Set(s.stars); c.messages.forEach(m => { if (want.has(m.id)) c.stars[m.key] = 1; }); }
    if (c && s.notes) Object.entries(s.notes).forEach(([id, t]) => { const m = c.messages.find(x => x.id === +id); if (m) c.mnotes[m.key] = t; });
    prev = c;
  }
  renderList(); const first = sortedChats()[0]; if (first) await openChat(first.id);
}

/* ============================================================ conversation view */
const activeChat = () => S.chats.find(c => c.id === S.active);
async function openChat(id) {
  const chat = S.chats.find(c => c.id === id); if (!chat) return;
  S.active = id; closeDrawer(true);
  $$(".chat-item").forEach(b => b.classList.toggle("on", b.dataset.id === id));
  if (chat.stub) {
    $("#main").innerHTML = `<div class="empty"><div class="thinking"><span class="dots"><i></i><i></i><i></i></span>Decrypting and verifying “${esc(mask(chat.title, chat))}”</div></div>`;
    $("#shell").classList.add("show-chat");
    try { await hydrate(chat); } catch (e) { console.error(e); $("#main").innerHTML = `<div class="empty"><div class="empty-inner"><h2>Could not open this chat</h2><p>${esc(e.message || "The saved copy could not be decrypted.")}</p></div></div>`; return; }
    if (S.active !== id) return;
    renderList();
  }
  const names = chat.participants.map(p => p.name === chat.me ? "You" : mask(p.name, chat));
  const span = chat.messages.length ? `${fmtDate(chat.messages[0].ts)} – ${fmtDate(chat.messages[chat.messages.length - 1].ts)}` : "";
  $("#main").innerHTML = `
    <header class="conv-head"><button class="icon-btn back" id="cBack" aria-label="Back to chats">${ic("back")}</button>
      <span class="avatar sm${chat.isGroup ? " group" : ""}" style="--h:${chat.h}">${esc(initials(mask(chat.title, chat)))}</span>
      <span class="t" id="cTitle" role="button" tabindex="0"><b>${esc(mask(chat.title, chat))}</b><span>${chat.isGroup ? esc(names.join(", ")) : esc(span)}</span></span>
      <span class="acts">
        <button class="icon-btn" data-d="search" title="Search (/)" aria-label="Search messages">${ic("search")}</button>
        <button class="icon-btn opt" id="cCal" title="Calendar (C)" aria-label="Jump to a date">${ic("calendar")}</button>
        <button class="icon-btn opt" data-d="media" title="Media, docs and links" aria-label="Media, docs and links">${ic("image")}</button>
        <button class="icon-btn opt" data-d="insights" title="Insights" aria-label="Insights"${can("insights") ? "" : " disabled"}>${ic("chart")}</button>
        <button class="icon-btn" id="cExport" title="Export (E)" aria-label="Export"${can("export") ? "" : " disabled"}>${ic("download")}</button>
        <button class="icon-btn" data-privacy title="Privacy screen (Ctrl+.)" aria-label="Privacy screen">${ic("shade")}</button>
        <button class="icon-btn" id="cMore" title="More" aria-label="More">${ic("dots")}</button></span></header>
    ${chat.omittedCount && !chat._noticeHidden ? `<div class="notice" id="noMediaNote">${ic("clip")}<span>${chat.noMedia ? `<b>This chat was exported without media.</b> ${chat.omittedCount} photo${chat.omittedCount === 1 ? "" : "s"}, documents or voice notes are mentioned but not included. To archive them, export again on the phone with <b>Include media</b> (Android) or <b>Attach Media</b> (iPhone), then use <b>Add a newer export</b>.` : `<b>${chat.omittedCount} attachment${chat.omittedCount === 1 ? " is" : "s are"} not included in this export.</b> WhatsApp sometimes leaves out media that was deleted from the phone or not downloaded. The messages are kept and marked.`}</span><button class="icon-btn" id="noMediaX" aria-label="Dismiss">${ic("close")}</button></div>` : ""}
    <div class="scroller" id="scroller"><div class="thread" id="thread"></div></div>
    <button class="fab-down hide" id="fabDown" aria-label="Scroll to latest">${ic("chevD")}</button>
    <div class="read-only-bar">${ic("lock")}<span>Archived conversation · ${chat.messages.length.toLocaleString("en-IN")} messages · ${chat.sources.length > 1 ? chat.sources.length + " exports merged" : chat.format + " export"}${chat.sample ? " · sample data" : chat.saved ? " · saved and encrypted" : ""}</span></div>`;
  $("#thread").innerHTML = threadHTML(chat, { src: n => mediaUrl(chat, n), me: chat.me, isGroup: chat.isGroup });
  const sc = $("#scroller");
  // Stay pinned to the latest message while lazily rendered days and images settle, until the reader scrolls.
  let pinned = true; const unpin = () => { pinned = false; };
  ["wheel", "touchstart", "keydown", "pointerdown"].forEach(ev => sc.addEventListener(ev, unpin, { once: true, passive: true }));
  const pin = () => { if (pinned) sc.scrollTop = sc.scrollHeight; };
  pin(); new ResizeObserver(pin).observe($("#thread"));
  $$("#thread img", sc).forEach(im => im.addEventListener("load", pin, { once: true }));
  setTimeout(unpin, 4000);
  sc.onscroll = () => $("#fabDown").classList.toggle("hide", sc.scrollHeight - sc.scrollTop - sc.clientHeight < 300);
  $("#fabDown").onclick = () => sc.scrollTo({ top: sc.scrollHeight, behavior: "smooth" });
  $("#cBack").onclick = () => { $("#shell").classList.remove("show-chat"); closeDrawer(); };
  $("#cTitle").onclick = () => toggleDrawer("info");
  $("#cTitle").onkeydown = e => { if (e.key === "Enter") toggleDrawer("info"); };
  $$("[data-d]").forEach(b => b.onclick = () => toggleDrawer(b.dataset.d));
  $("#cExport").onclick = openExport;
  $("#cCal").onclick = e => { e.stopPropagation(); openCalendar(e.currentTarget); };
  $("#noMediaX") && ($("#noMediaX").onclick = () => { chat._noticeHidden = true; $("#noMediaNote").remove(); });
  $("#thread").addEventListener("mouseover", e => { const el = e.target.closest(".msg"); S.hoverMsg = el ? +el.dataset.id : null; });
  $("#cMore").onclick = e => openMenu(e.currentTarget, [
    ["info", "Chat info and integrity", () => toggleDrawer("info")],
    ["image", "Media, docs and links", () => toggleDrawer("media")],
    ["chart", "Insights", () => toggleDrawer("insights"), !can("insights")],
    ["download", "Export", openExport, !can("export"), true],
    ["calendar", "Jump to a date", () => openCalendar($("#cMore"))],
    ["cert", "Draft Section 63 certificate", () => openCertificate(chat), !can("export"), true],
    ["merge", "Add a newer export of this chat", () => { S.importInto = chat.id; $("#fileIn").click(); }, !can("import"), true],
    ["diff", "Changes between exports", () => openDrawer("changes"), chat.sources.length < 2],
    "-",
    chat.saved ? ["trash", "Delete saved chat permanently", () => purgeChat(chat), !can("purge"), true]
      : ["trash", "Remove from this session", () => removeChat(chat), !can("import"), true]
  ]);
  $("#thread").onclick = onThreadClick;
  $("#shell").classList.add("show-chat");
}
function purgeChat(chat, after) {
  confirmModal(`Delete “${chat.title}” permanently?`, "The encrypted copy saved on this device and its fingerprints are deleted. This cannot be undone. Keep an exported archive or a backup if you may need it.", "Delete permanently", async () => {
    await idb.del(chat.id); await idb.delBlobs(chat.id + "/"); await folderDelete(chat.id);
    S.chats = S.chats.filter(c => c !== chat); if (chat.media) for (const f of chat.media.values()) if (f.url) URL.revokeObjectURL(f.url);
    audit("Deleted saved chat", chat.title); toast("Deleted"); renderList(); updateFoot();
    if (S.active === chat.id) { const n = sortedChats()[0]; n ? openChat(n.id) : renderEmpty(); }
    after?.();
  });
}
function removeChat(chat) {
  confirmModal(`Remove “${chat.title}”?`, "The chat is removed from this browser session only. The original export file is not affected.", "Remove", () => {
    S.chats = S.chats.filter(c => c !== chat); for (const f of chat.media.values()) if (f.url) URL.revokeObjectURL(f.url);
    audit("Removed chat from session", chat.sourceName); renderList(); S.chats[0] ? openChat(sortedChats()[0].id) : renderEmpty();
  });
}
function confirmModal(title, body, okLabel, fn) {
  const ov = h(`<div class="overlay"><div class="modal" role="alertdialog" aria-modal="true"><div class="modal-head"><h3>${esc(title)}</h3></div><div class="modal-body"><p class="muted" style="margin:0">${esc(body)}</p></div>
    <div class="modal-foot"><button class="btn btn-ghost" data-x>Cancel</button><button class="btn btn-danger" data-ok>${esc(okLabel)}</button></div></div></div>`);
  document.body.append(ov); $("[data-x]", ov).onclick = () => ov.remove(); $("[data-ok]", ov).onclick = () => { ov.remove(); fn(); };
  $("[data-ok]", ov).focus();
}
let audioEl = null, audioBtn = null;
function onThreadClick(e) {
  const chat = activeChat(); const t = e.target.closest("[data-act]"); if (!t) return;
  const act = t.dataset.act;
  if (act === "menu") { e.stopPropagation(); const m = chat.messages.find(x => x.id === +t.closest(".msg").dataset.id); return msgMenu(chat, m, t); }
  if (act === "view") openViewer(chat, +t.dataset.id);
  else if (act === "doc") openViewer(chat, +t.dataset.id);
  else if (act === "jump") openCalendar(t, t.closest(".day").dataset.day);
  else if (act === "play" || act === "seek") {
    const v = t.closest(".voice"); const src = v.dataset.src; const btn = $(".play", v);
    if (audioEl && audioEl.dataset.src === src && act === "play") { audioEl.paused ? audioEl.play() : audioEl.pause(); return; }
    if (!audioEl || audioEl.dataset.src !== src) {
      audioEl?.pause(); if (audioBtn) { audioBtn.innerHTML = ic("play"); $$(".wave i", audioBtn.closest(".voice")).forEach(i => i.classList.remove("p")); }
      audioEl = new Audio(src); audioEl.dataset.src = src; audioBtn = btn;
      const bars = $$(".wave i", v), vt = $(".vt", v);
      audioEl.onplay = () => btn.innerHTML = ic("pause"); audioEl.onpause = () => btn.innerHTML = ic("play");
      audioEl.onloadedmetadata = () => { if (isFinite(audioEl.duration)) vt.textContent = `0:${pad(Math.round(audioEl.duration))}`; };
      audioEl.ontimeupdate = () => { const f = audioEl.currentTime / (audioEl.duration || 1); bars.forEach((b, i) => b.classList.toggle("p", i / bars.length <= f)); vt.textContent = `${Math.floor(audioEl.currentTime / 60)}:${pad(Math.floor(audioEl.currentTime % 60))}`; };
      audioEl.onended = () => { bars.forEach(b => b.classList.remove("p")); btn.innerHTML = ic("play"); };
      audioEl.onerror = () => toast("This browser cannot play this audio format. Download it to listen.", "err");
    }
    if (act === "seek") { const r = t.getBoundingClientRect(); const f = (e.clientX - r.left) / r.width; const go = () => { audioEl.currentTime = f * audioEl.duration; audioEl.play(); }; isFinite(audioEl.duration) ? go() : audioEl.addEventListener("loadedmetadata", go, { once: true }); }
    else audioEl.play().catch(() => {});
  }
}
function jumpTo(id) {
  const el = $(`#thread [data-id="${id}"]`); if (!el) return;
  el.scrollIntoView({ block: "center", behavior: "smooth" });
  el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash");
  if (innerWidth <= 1100 && S.drawer) closeDrawer();
}
function jumpDatePicker(anchor) {
  const chat = activeChat(); const days = [...new Set(chat.messages.map(m => isoDay(m.ts)))];
  const inp = h(`<input type="date" class="input" style="position:fixed;opacity:0;pointer-events:none" min="${days[0]}" max="${days[days.length - 1]}" value="${anchor.closest(".day").dataset.day}">`);
  document.body.append(inp);
  inp.onchange = () => { const target = days.find(d => d >= inp.value) || days[days.length - 1]; $(`.day[data-day="${target}"]`)?.scrollIntoView({ block: "start", behavior: "smooth" }); inp.remove(); };
  inp.onblur = () => setTimeout(() => inp.remove(), 300);
  try { inp.showPicker(); } catch { inp.style.cssText = "position:fixed;top:80px;left:50%;transform:translateX(-50%);z-index:90;width:220px"; inp.focus(); }
}

/* ============================================================ message actions: star, note, citation */
function citationFor(chat, m) {
  const name = f => chat.media.get(f)?.name;
  const snippet = m.type === "media" ? (m.text || `[${kindLabel(m.media.kind)}: ${m.media.file ? name(m.media.file) : m.media.name}]`)
    : m.type === "deleted" ? (m.recovered ? `[Deleted later; original: ${m.recovered.text || m.recovered.media?.name || ""}]` : "[This message was deleted]")
    : m.type === "omitted" ? "[Media not included in export]" : m.text;
  let q = mask(snippet || "", chat).replace(/\s+/g, " ").trim(); if (q.length > 240) q = q.slice(0, 237) + "…";
  const src = chat.sources[Math.min(...(m.seenIn || [chat.sources.length - 1]))] || chat.sources[chat.sources.length - 1];
  const mt = chat.matter || {};
  return `“${q}”\n— ${mask(m.sender || "System message", chat)}, WhatsApp ${chat.isGroup ? "group" : "chat"} “${mask(chat.title, chat)}”, message #${m.id}, ${fmtDate(m.ts)} at ${fmtTime(m.ts)}${mt.client ? `. Client: ${mt.client}` : ""}${mt.matter ? `; matter: ${mt.matter}` : ""}. Source export SHA-256: ${src.hash}.`;
}
function rerenderMsg(chat, m) {
  const el = $(`#thread .msg[data-id="${m.id}"]`); if (!el) return;
  const i = chat.messages.indexOf(m); let prev = i > 0 ? chat.messages[i - 1] : null; if (prev && isoDay(prev.ts) !== isoDay(m.ts)) prev = null;
  el.outerHTML = msgHTML(chat, m, prev, { src: n => mediaUrl(chat, n), me: chat.me, isGroup: chat.isGroup });
}
async function saveChatMeta(chat) { if (chat.saved) await persistChat(chat, { metaOnly: true }); }
function toggleStar(chat, m) {
  if (!can("organise") || chat.sample && false) return;
  if (chat.stars[m.key]) delete chat.stars[m.key]; else chat.stars[m.key] = Date.now();
  audit(chat.stars[m.key] ? "Starred message" : "Unstarred message", `${chat.title} · #${m.id}`);
  rerenderMsg(chat, m); saveChatMeta(chat); if (S.drawer === "info") openDrawer("info");
  toast(chat.stars[m.key] ? `Starred #${m.id}` : `Removed star from #${m.id}`);
}
function editNote(chat, m) {
  if (!can("organise")) return;
  const cur = chat.mnotes[m.key] || "";
  const ov = h(`<div class="overlay"><form class="modal" role="dialog" aria-modal="true" aria-labelledby="mnT" novalidate><div class="modal-head"><h3 id="mnT">Note on message #${m.id}</h3></div>
    <div class="modal-body"><div class="quote-box">${fmtText(mask((m.text || m.media?.name || m.recovered?.text || "").slice(0, 300), chat))}<span class="faint"> — ${esc(mask(m.sender || "", chat))}, ${fmtDate(m.ts)}, ${fmtTime(m.ts)}</span></div>
      <textarea class="input note-in" id="mnText" rows="4" placeholder="e.g. Client's confirmation of fee; relied on in reply to notice dated…">${esc(cur)}</textarea>
      <p class="note" style="margin:0">Notes are private to ChatVault. They appear under the message, in the Excel index and in the PDFs, never in the original export.</p></div>
    <div class="modal-foot">${cur ? '<button class="btn btn-ghost" type="button" data-del style="margin-right:auto">Delete note</button>' : ""}<button class="btn btn-ghost" type="button" data-x>Cancel</button><button class="btn btn-primary" type="submit">Save note</button></div></form></div>`);
  document.body.append(ov); setTimeout(() => $("#mnText", ov).focus(), 30);
  const done = v => { if (v) chat.mnotes[m.key] = v; else delete chat.mnotes[m.key]; audit(v ? "Noted message" : "Deleted message note", `${chat.title} · #${m.id}`); rerenderMsg(chat, m); saveChatMeta(chat); ov.remove(); };
  $("[data-x]", ov).onclick = () => ov.remove();
  $("[data-del]", ov) && ($("[data-del]", ov).onclick = () => done(""));
  $("form", ov).onsubmit = e => { e.preventDefault(); done($("#mnText", ov).value.trim().slice(0, 2000)); };
}
function msgMenu(chat, m, anchor) {
  const org = can("organise");
  openMenu(anchor, [
    ["star", chat.stars[m.key] ? "Remove star" : "Star message", () => toggleStar(chat, m), !org, true],
    ["pen", chat.mnotes[m.key] ? "Edit note" : "Add note", () => editNote(chat, m), !org, true],
    "-",
    ["copy", "Copy text", () => copyText(mask(m.text || m.recovered?.text || (m.media?.file ? chat.media.get(m.media.file).name : m.media?.name) || "", chat))],
    ["quote", "Copy citation", () => copyText(citationFor(chat, m))]
  ]);
}

/* ============================================================ calendar */
function openCalendar(anchor, startDay) {
  closeMenus(); $$(".cal-pop").forEach(x => x.remove());
  const chat = activeChat(); if (!chat) return;
  const counts = {}; chat.messages.forEach(m => { const d = isoDay(m.ts); counts[d] = (counts[d] || 0) + 1; });
  const days = Object.keys(counts).sort(); const max = Math.max(...Object.values(counts));
  const firstM = days[0].slice(0, 7), lastM = days[days.length - 1].slice(0, 7);
  let cur = (startDay || days[days.length - 1]).slice(0, 7);
  const pop = h(`<div class="cal-pop" role="dialog" aria-label="Jump to a date"></div>`); document.body.append(pop);
  const lvl = n => n ? Math.min(4, Math.ceil(n / max * 4)) : 0;
  const draw = () => {
    const [y, mo] = cur.split("-").map(Number); const first = new Date(y, mo - 1, 1); const nd = new Date(y, mo, 0).getDate();
    const lead = (first.getDay() + 6) % 7; const mCount = days.filter(d => d.startsWith(cur)).reduce((a, d) => a + counts[d], 0);
    let cells = ""; for (let i = 0; i < lead; i++) cells += "<span></span>";
    for (let d = 1; d <= nd; d++) { const k = `${cur}-${pad(d)}`; const n = counts[k] || 0; cells += `<button class="cal-d l${lvl(n)}"${n ? ` data-day="${k}" title="${n} message${n > 1 ? "s" : ""}"` : " disabled"}>${d}</button>`; }
    pop.innerHTML = `<div class="cal-h"><button class="icon-btn" data-m="-1" aria-label="Previous month"${cur <= firstM ? " disabled" : ""}>${ic("chevL")}</button><div><b>${first.toLocaleDateString("en-IN", { month: "long", year: "numeric" })}</b><span>${mCount} messages</span></div><button class="icon-btn" data-m="1" aria-label="Next month"${cur >= lastM ? " disabled" : ""}>${ic("chevR")}</button></div>
      <div class="cal-g"><i>M</i><i>T</i><i>W</i><i>T</i><i>F</i><i>S</i><i>S</i>${cells}</div>
      <div class="cal-f"><button class="chip" data-go="first">First message</button><button class="chip" data-go="last">Latest</button><span class="cal-key"><i class="l1"></i><i class="l2"></i><i class="l3"></i><i class="l4"></i></span></div>`;
  };
  const step = dir => { let [y, mo] = cur.split("-").map(Number); mo += dir; if (mo < 1) { mo = 12; y--; } if (mo > 12) { mo = 1; y++; } cur = `${y}-${pad(mo)}`; draw(); };
  const go = d => { $(`.day[data-day="${d}"]`)?.scrollIntoView({ block: "start", behavior: "smooth" }); pop.remove(); };
  pop.onclick = e => {
    e.stopPropagation();
    const b = e.target.closest("[data-m]"); if (b) return step(+b.dataset.m);
    const d = e.target.closest("[data-day]"); if (d) return go(d.dataset.day);
    const g = e.target.closest("[data-go]"); if (g) return go(g.dataset.go === "first" ? days[0] : days[days.length - 1]);
  };
  draw();
  const r = anchor.getBoundingClientRect(); const w = pop.offsetWidth;
  pop.style.top = Math.min(r.bottom + 6, innerHeight - pop.offsetHeight - 8) + "px"; pop.style.left = Math.max(8, Math.min(r.left + r.width / 2 - w / 2, innerWidth - w - 8)) + "px";
  setTimeout(() => document.addEventListener("click", function off(e) { if (!pop.contains(e.target)) { pop.remove(); document.removeEventListener("click", off); } }), 0);
}

/* ============================================================ drawer panels */
function toggleDrawer(kind) { S.drawer === kind ? closeDrawer() : openDrawer(kind); }
function closeDrawer(silent) { S.drawer = null; $("#drawer")?.classList.remove("open"); $$("[data-d]").forEach(b => b.classList.remove("on")); }
function openDrawer(kind) {
  const chat = activeChat(); if (!chat) return;
  S.drawer = kind; $$("[data-d]").forEach(b => b.classList.toggle("on", b.dataset.d === kind));
  const titles = { info: "Chat info", search: "Search messages", media: "Media, docs and links", insights: "Insights", changes: "Changes between exports" };
  $("#drawerInner").innerHTML = `<div class="drawer-head"><button class="icon-btn" id="dClose" aria-label="Close">${ic("close")}</button><h3>${titles[kind]}</h3></div><div class="drawer-body" id="dBody"></div>`;
  $("#dClose").onclick = closeDrawer;
  ({ info: panelInfo, search: panelSearch, media: panelMedia, insights: panelInsights, changes: panelChanges })[kind](chat, $("#dBody"));
  $("#drawer").classList.add("open");
}
function hashRow(label, v) { return `<div class="field"><label>${label}</label><div class="hash"><span class="mono">${v}</span><button class="icon-btn" data-copy="${v}" aria-label="Copy">${ic("copy")}</button></div></div>`; }
function panelInfo(chat, body) {
  const first = chat.messages[0], last = chat.messages[chat.messages.length - 1];
  const edit = can("organise") && !chat.sample;
  const st = chat.sources.length > 1 ? changeStats(chat) : null;
  body.innerHTML = `<div class="center"><span class="avatar lg${chat.isGroup ? " group" : ""}" style="--h:${chat.h}">${esc(initials(mask(chat.title, chat)))}</span><h2>${esc(mask(chat.title, chat))}</h2>
      <span class="muted">${chat.isGroup ? "Group" : "Chat"} · ${chat.participants.length} participants · ${chat.messages.length.toLocaleString("en-IN")} messages</span>
      <span>${chat.sample ? '<span class="pill sample">Sample data</span>' : chat.saved ? '<span class="pill ok">Saved · AES-256 encrypted</span>' : '<span class="pill viewer">Not saved</span>'}</span></div>
    <div class="sec"><h4>${ic("tag")}<span class="grow">Tags and note</span></h4>
      <div class="tag-edit" id="tagEdit">${(chat.tags || []).map(t => `<span class="tchip on">${esc(t)}${edit ? `<button data-rm="${esc(t)}" aria-label="Remove tag ${esc(t)}">${ic("close")}</button>` : ""}</span>`).join("")}
        ${edit ? `<input class="input tag-in" id="tagIn" list="tagList" placeholder="Add tag, e.g. client name, FY 2026-27" aria-label="Add tag"><datalist id="tagList">${allTags().map(([t]) => `<option value="${esc(t)}">`).join("")}</datalist>` : (chat.tags || []).length ? "" : '<span class="faint">No tags</span>'}</div>
      ${edit ? `<textarea class="input note-in" id="noteIn" rows="3" placeholder="Private note about this chat (matter, purpose, reference number)">${esc(chat.note || "")}</textarea>` : chat.note ? `<p style="margin:0;white-space:pre-wrap">${esc(chat.note)}</p>` : ""}
      ${chat.sample ? '<p class="note" style="margin:0">Tags on sample chats are not saved.</p>' : ""}</div>
    <div class="sec"><h4>${ic("briefcase")}<span class="grow">Client and matter</span></h4>
      ${edit ? `<form class="matter-form" id="matterForm" novalidate>
        <div class="field"><label for="mtClient">Client</label><input class="input" id="mtClient" list="clientList" value="${esc(chat.matter.client || "")}" placeholder="e.g. Mehta Traders"><datalist id="clientList">${[...new Set(S.chats.map(c => c.matter?.client).filter(Boolean))].map(c => `<option value="${esc(c)}">`).join("")}</datalist></div>
        <div class="form-row"><div class="field"><label for="mtPan">PAN</label><input class="input mono-in" id="mtPan" maxlength="10" value="${esc(chat.matter.pan || "")}" placeholder="AAAAA9999A"></div>
          <div class="field"><label for="mtGstin">GSTIN</label><input class="input mono-in" id="mtGstin" maxlength="15" value="${esc(chat.matter.gstin || "")}" placeholder="24AAAAA0000A1Z5"></div></div>
        <div class="field"><label for="mtMatter">Matter</label><input class="input" id="mtMatter" value="${esc(chat.matter.matter || "")}" placeholder="e.g. GST audit, reply to notice u/s 143(2)"></div>
        <div class="form-row"><div class="field"><label for="mtFy">Financial year</label><input class="input" id="mtFy" value="${esc(chat.matter.fy || "")}" placeholder="2026-27"></div>
          <div class="field"><label for="mtRef">Reference no.</label><input class="input" id="mtRef" value="${esc(chat.matter.ref || "")}" placeholder="File / notice / DIN"></div></div>
        <div class="err" id="mtErr"></div></form>`
      : Object.values(chat.matter || {}).some(Boolean) ? `<dl class="kv">${[["Client", "client"], ["PAN", "pan"], ["GSTIN", "gstin"], ["Matter", "matter"], ["Financial year", "fy"], ["Reference", "ref"]].filter(([, k]) => chat.matter[k]).map(([l, k]) => `<dt>${l}</dt><dd>${esc(chat.matter[k])}</dd>`).join("")}</dl>` : '<span class="faint">Not set</span>'}</div>
    <div class="sec"><h4>${ic("star")}<span class="grow">Starred and notes</span></h4>
      <div class="tiles"><div class="tile"><b>${chat.messages.filter(m => chat.stars[m.key]).length}</b><span>starred messages</span></div><div class="tile"><b>${chat.messages.filter(m => chat.mnotes[m.key]).length}</b><span>messages with notes</span></div></div>
      <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-ghost btn-sm" id="seeStars">Show starred</button><button class="btn btn-ghost btn-sm" id="seeNotes">Show notes</button></div>
      <p class="note" style="margin:0">Hover a message and use its menu, or press S (star), N (note) and Q (copy citation).</p></div>
    <div class="sec"><h4>${ic("shield")}<span class="grow">Integrity</span>${chat.verified === false ? '<span class="pill off">Check failed</span>' : chat.verified ? '<span class="pill ok">Verified on open</span>' : '<span class="pill ok">SHA-256</span>'}</h4>
      ${chat.sources.map((s, i) => `<div class="src-card"><div class="src-top"><b>${esc(s.name)}</b><span class="faint">${i === chat.sources.length - 1 && chat.sources.length > 1 ? "Latest" : chat.sources.length > 1 ? "Earlier" : ""}</span></div>
        <dl class="kv"><dt>Period</dt><dd>${fmtDT(s.first)} to ${fmtDT(s.last)}</dd><dt>Messages</dt><dd>${s.count.toLocaleString("en-IN")} · ${s.format} · ${fmtBytes(s.size)}</dd><dt>Imported</dt><dd>${fmtDT(s.importedAt)} by ${esc(s.importedBy)}</dd></dl>
        ${hashRow("SHA-256 fingerprint", s.hash)}</div>`).join("")}
      <p class="note" style="margin:0">Any change to a file, even one character, produces a different fingerprint.${chat.saved ? " Saved copies are re-hashed every time they are opened and compared with these values." : ""}</p>
      <details><summary class="muted" style="cursor:pointer;font-size:13px">Fingerprints of all ${chat.fileHashes.length} files</summary>
        <div class="tbl-wrap" style="margin-top:10px"><table><thead><tr><th>File</th><th>Size</th><th>SHA-256</th></tr></thead><tbody>
        ${chat.fileHashes.map(f => `<tr><td>${esc(f.name)}</td><td>${fmtBytes(f.size)}</td><td class="mono" title="${f.hash}">${f.hash.slice(0, 16)}…</td></tr>`).join("")}</tbody></table></div></details>
      ${can("import") ? `<button class="btn btn-ghost btn-sm" id="addSrc">${ic("merge")}Add a newer export of this chat</button>` : ""}</div>
    <div class="sec"><h4>${ic("log")}<span class="grow">Chain of custody</span>${can("export") && !chat.sample ? `<button class="btn btn-ghost btn-sm" id="certBtn" style="text-transform:none;letter-spacing:0">${ic("cert")}Section 63 draft</button>` : ""}</h4>
      ${(chat.events || []).length ? `<ol class="timeline">${chat.events.slice().reverse().slice(0, 40).map(ev => `<li><span class="tl-t">${fmtDT(ev.t)} · ${esc(ev.user)}</span><b>${esc(ev.action)}</b>${ev.detail ? `<span>${esc(mask(ev.detail, chat))}</span>` : ""}${ev.hash ? `<span class="mono">${esc(ev.hash.split(" ").map(x => x.slice(0, 16) + "…").join("  "))}</span>` : ""}</li>`).join("")}</ol>` : `<span class="faint">${chat.sample ? "Not recorded for sample chats" : "No events yet"}</span>`}</div>
    ${st ? `<div class="sec"><h4>${ic("diff")}<span class="grow">Changes between exports</span></h4><div class="tiles">
      <div class="tile"><b>${st.recovered}</b><span>deleted later, recovered</span></div><div class="tile"><b>${st.edited}</b><span>edited later</span></div>
      <div class="tile"><b>${st.gone}</b><span>missing from later export</span></div><div class="tile"><b>${st.added.slice(1).reduce((a, b) => a + b, 0)}</b><span>new in later exports</span></div></div>
      <button class="btn btn-primary btn-sm" id="seeChanges">Review changes</button></div>` : ""}
    <div class="sec"><h4>Summary</h4><dl class="kv">
      <dt>Period</dt><dd>${first ? fmtDT(first.ts) + " to " + fmtDT(last.ts) : "-"}</dd>
      <dt>Attachments</dt><dd>${chat.linked} included${chat.omittedCount ? ` · <span style="color:var(--warn)">${chat.omittedCount} not included${chat.noMedia ? " (exported without media)" : ""}</span>` : ""}${chat.unlinkedFiles ? ` · ${chat.unlinkedFiles} unreferenced` : ""}</dd>
      <dt>First imported</dt><dd>${fmtDT(chat.importedAt)} by ${esc(chat.importedBy)}</dd></dl></div>
    <div class="sec"><h4><span class="grow">Participants</span><span class="faint" style="text-transform:none;letter-spacing:0">Your messages appear on the right</span></h4>
      <div class="field"><label for="meSel">You are</label><select class="select" id="meSel"><option value="">None of these</option>${chat.participants.map(p => `<option value="${esc(p.name)}"${p.name === chat.me ? " selected" : ""}>${esc(mask(p.name, chat))}</option>`).join("")}</select></div>
      ${chat.participants.map(p => `<div class="person"><span class="avatar sm" style="--h:${p.h}">${esc(initials(mask(p.name, chat)))}</span><span class="pn"><b>${esc(mask(p.name, chat))}${p.name === chat.me ? " (you)" : ""}</b><span>${p.n} messages · ${(() => { const inc = chat.messages.filter(m => m.sender === p.name && m.media?.file).length, out = chat.messages.filter(m => m.sender === p.name && (m.type === "omitted" || m.media?.missing)).length; return `${inc} attachments${out ? ` · ${out} not included` : ""}`; })()}</span></span></div>`).join("")}</div>`;
  const saveMeta = async () => { if (await persistChat(chat, { metaOnly: true })) updateFoot(); renderList(); };
  $("#meSel").onchange = async e => { chat.me = e.target.value || null; await saveMeta(); const d = S.drawer; await openChat(chat.id); openDrawer(d); };
  $("#addSrc") && ($("#addSrc").onclick = () => { S.importInto = chat.id; $("#fileIn").click(); });
  $("#seeChanges") && ($("#seeChanges").onclick = () => openDrawer("changes"));
  $("#seeStars").onclick = () => { openDrawer("search"); setTimeout(() => $('[data-t="starred"]')?.click(), 20); };
  $("#seeNotes").onclick = () => { openDrawer("search"); setTimeout(() => $('[data-t="notes"]')?.click(), 20); };
  $("#certBtn") && ($("#certBtn").onclick = () => openCertificate(chat));
  const mf = $("#matterForm");
  if (mf) mf.onchange = () => {
    const v = id => $(id).value.trim();
    const pan = v("#mtPan").toUpperCase(), gstin = v("#mtGstin").toUpperCase(); const errs = [];
    if (pan && !/^[A-Z]{5}[0-9]{4}[A-Z]$/.test(pan)) errs.push("PAN should look like AAAAA9999A.");
    if (gstin && !/^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/.test(gstin)) errs.push("GSTIN should be 15 characters, like 24AAAAA0000A1Z5.");
    if (gstin && pan && gstin.slice(2, 12) !== pan) errs.push("The PAN inside the GSTIN does not match the PAN.");
    $("#mtErr").textContent = errs.join(" ");
    $("#mtPan").value = pan; $("#mtGstin").value = gstin;
    chat.matter = { client: v("#mtClient"), pan, gstin, matter: v("#mtMatter"), fy: v("#mtFy"), ref: v("#mtRef") };
    saveMeta();
  };
  const tagIn = $("#tagIn");
  if (tagIn) {
    const add = () => { const t = tagIn.value.trim().replace(/\s+/g, " ").slice(0, 40); if (!t) return; if (!chat.tags.includes(t)) { chat.tags = [...chat.tags, t]; audit("Tagged chat", `${chat.title} · ${t}`); saveMeta(); } openDrawer("info"); setTimeout(() => $("#tagIn")?.focus(), 30); };
    tagIn.onkeydown = e => { if (e.key === "Enter" || e.key === ",") { e.preventDefault(); add(); } };
    tagIn.onchange = () => { if (allTags().some(([t]) => t === tagIn.value)) add(); };
    $("#tagEdit").onclick = e => { const b = e.target.closest("[data-rm]"); if (b) { chat.tags = chat.tags.filter(t => t !== b.dataset.rm); saveMeta(); openDrawer("info"); } };
    $("#noteIn").onchange = e => { chat.note = e.target.value.trim(); saveMeta(); toast("Note saved"); };
  }
  bindCopy(body);
}
function panelChanges(chat, body) {
  const groups = [
    ["Deleted later, recovered from an earlier export", chat.messages.filter(m => m.recovered), m => `<span class="faint">Original:</span> ${fmtText(mask(m.recovered.text || m.recovered.media?.name || "", chat))}`],
    ["Edited after the earlier export", chat.messages.filter(m => m.history), m => `${fmtText(mask(m.text, chat))}<br><span class="faint">Before:</span> ${fmtText(mask(m.history[m.history.length - 1].text || "", chat))}`],
    ["In an earlier export but missing from a later one", chat.messages.filter(m => m.goneIn != null), m => fmtText(mask(m.text || m.media?.name || "", chat)) + `<br><span class="faint">Absent from the ${esc(srcLabel(chat, m.goneIn))}. Usually “delete for me”.</span>`],
    ["New in later exports", chat.messages.filter(m => m.newIn > 0), m => fmtText(mask(m.text || m.media?.name || (m.type === "deleted" ? "This message was deleted" : ""), chat))]
  ];
  body.innerHTML = `<div class="sec"><p class="note" style="margin:0">Compares ${chat.sources.length} exports: ${chat.sources.map((s, i) => `<b>${esc(s.name)}</b> (${fmtDate(s.first)} – ${fmtDate(s.last)})`).join(", ")}. Messages are matched by minute, sender and order.</p></div>` +
    groups.map(([title, list, f]) => `<div class="sec"><h4><span class="grow">${title}</span><span class="faint" style="text-transform:none;letter-spacing:0">${list.length}</span></h4><div class="ins-list">${list.slice(0, 200).map(m => `<button class="ins-item" data-jump="${m.id}"><span class="hd"><span>${fmtDate(m.ts)}, ${fmtTime(m.ts)}</span><span>·</span><span>${esc(m.sender === chat.me ? "You" : mask(m.sender || "", chat))}</span></span><span class="bd">${f(m)}</span></button>`).join("") || '<span class="faint">None</span>'}</div></div>`).join("");
  body.onclick = e => { const j = e.target.closest("[data-jump]"); if (j) jumpTo(j.dataset.jump); };
}
function bindCopy(el) { el.addEventListener("click", e => { const b = e.target.closest("[data-copy]"); if (b) copyText(b.dataset.copy); }); }
function panelSearch(chat, body) {
  const st = { q: "", type: "all", who: "", from: "", to: "" };
  const days = chat.messages.length ? [isoDay(chat.messages[0].ts), isoDay(chat.messages[chat.messages.length - 1].ts)] : ["", ""];
  body.innerHTML = `<div class="s-top"><label class="search-box">${ic("search")}<input id="sQ" placeholder="Search text, names, file names" aria-label="Search text"></label>
    <div class="s-filters">${[["all", "All"], ["text", "Text"], ["image", "Photos"], ["video", "Videos"], ["audio", "Voice"], ["doc", "Docs"], ["link", "Links"], ["deleted", "Deleted"], ["recovered", "Recovered"], ["edited", "Edited"], ["starred", "Starred"], ["notes", "With notes"]].map(([k, l]) => `<button class="chip${k === "all" ? " on" : ""}" data-t="${k}">${l}</button>`).join("")}</div>
    <div class="s-row"><select class="select" id="sWho" aria-label="Sender"><option value="">Anyone</option>${chat.participants.map(p => `<option value="${esc(p.name)}">${esc(mask(p.name))}</option>`).join("")}</select>
      <span></span><input class="input" type="date" id="sFrom" aria-label="From date" min="${days[0]}" max="${days[1]}"><input class="input" type="date" id="sTo" aria-label="To date" min="${days[0]}" max="${days[1]}"></div></div>
    <div class="s-count" id="sCount"></div><div id="sRes"></div>`;
  const run = () => {
    const q = st.q.trim().toLowerCase();
    const res = chat.messages.filter(m => {
      if (m.type === "system") return false;
      if (st.who && m.sender !== st.who) return false;
      const d = isoDay(m.ts); if (st.from && d < st.from) return false; if (st.to && d > st.to) return false;
      if (st.type === "text" && m.type !== "text") return false;
      if (["image", "video", "audio", "doc"].includes(st.type) && !(m.type === "media" && (m.media.kind === st.type || (st.type === "image" && m.media.kind === "sticker")))) return false;
      if (st.type === "link" && !/https?:\/\/|www\./i.test(m.text)) return false;
      if (st.type === "deleted" && m.type !== "deleted") return false;
      if (st.type === "recovered" && !m.recovered) return false;
      if (st.type === "edited" && !m.edited) return false;
      if (st.type === "starred" && !chat.stars[m.key]) return false;
      if (st.type === "notes" && !chat.mnotes[m.key]) return false;
      if (q) { const hay = ((m.text || "") + " " + (m.media?.name || "") + " " + (m.sender || "") + " " + (m.recovered?.text || "") + " " + (m.history || []).map(x => x.text).join(" ") + " " + (chat.mnotes[m.key] || "")).toLowerCase(); if (!hay.includes(q)) return false; }
      return true;
    });
    const any = q || st.type !== "all" || st.who || st.from || st.to;
    $("#sCount").textContent = any ? `${res.length} result${res.length === 1 ? "" : "s"}` : `${res.length} messages — type to search`;
    const shown = res.slice(-300).reverse();
    $("#sRes").innerHTML = shown.map(m => {
      const p = chat.participants.find(x => x.name === m.sender);
      const snip = m.type === "media" ? (m.text || ({ image: "📷 Photo", video: "🎥 Video", audio: "🎤 Voice note", sticker: "Sticker" }[m.media.kind] || "📄 " + m.media.name)) : m.text;
      return `<button class="hit" data-id="${m.id}"><span class="hd"><b style="--h:${p?.h ?? 0}">${esc(m.sender === chat.me ? "You" : mask(m.sender))}</b><span>${fmtDate(m.ts)}, ${fmtTime(m.ts)}</span></span><span class="sn">${fmtText(mask(snip), q)}</span></button>`;
    }).join("") + (res.length > 300 ? `<div class="note" style="padding:12px 20px">Showing the latest 300. Narrow the search to see others.</div>` : "");
  };
  $("#sQ").oninput = e => { st.q = e.target.value; run(); };
  body.querySelector(".s-filters").onclick = e => { const b = e.target.closest("[data-t]"); if (!b) return; st.type = b.dataset.t; $$("[data-t]", body).forEach(x => x.classList.toggle("on", x === b)); run(); };
  $("#sWho").onchange = e => { st.who = e.target.value; run(); };
  $("#sFrom").onchange = e => { st.from = e.target.value; run(); };
  $("#sTo").onchange = e => { st.to = e.target.value; run(); };
  $("#sRes").onclick = e => { const b = e.target.closest(".hit"); if (b) jumpTo(b.dataset.id); };
  run(); setTimeout(() => $("#sQ")?.focus(), 250);
}
function panelMedia(chat, body) {
  const media = chat.messages.filter(m => m.type === "media" && !m.media.missing && ["image", "video", "sticker"].includes(m.media.kind));
  const docs = chat.messages.filter(m => m.type === "media" && !m.media.missing && ["doc", "audio", "contact"].includes(m.media.kind));
  const links = chat.messages.filter(m => m.type === "text" && /https?:\/\/|www\./i.test(m.text));
  body.innerHTML = `<div style="padding:12px 16px"><div class="seg" role="tablist"><button class="on" data-tab="m">Media ${media.length}</button><button data-tab="d">Docs ${docs.length}</button><button data-tab="l">Links ${links.length}</button></div></div><div id="mBody"></div>`;
  const tab = k => {
    $$("[data-tab]", body).forEach(b => b.classList.toggle("on", b.dataset.tab === k));
    const mb = $("#mBody");
    if (k === "m") mb.innerHTML = media.length ? `<div class="grid-media">${media.map(m => `<button data-view="${m.id}" aria-label="Open">${m.media.kind === "video" ? `<video src="${mediaUrl(chat, m.media.file)}" preload="metadata" muted></video><span class="vbadge">${ic("video", "i")}</span>` : `<img src="${mediaUrl(chat, m.media.file)}" alt="" loading="lazy">`}</button>`).join("")}</div>` : `<div class="center faint">No photos or videos</div>`;
    if (k === "d") mb.innerHTML = docs.length ? `<div class="list-docs">${docs.map(m => { const f = chat.media.get(m.media.file); const ext = extOf(f.name); return `<button class="m-doc" data-view="${m.id}"><span class="ext ${esc(ext)}">${esc(ext.toUpperCase())}</span><span class="dn"><b>${esc(f.name.replace(/^\d{8}-/, ""))}</b><span>${fmtBytes(f.size)} · ${fmtDate(m.ts)} · ${esc(mask(m.sender))}</span></span></button>`; }).join("")}</div>` : `<div class="center faint">No documents</div>`;
    if (k === "l") mb.innerHTML = links.length ? links.map(m => `<button class="hit" data-jump="${m.id}"><span class="hd"><span>${fmtDate(m.ts)} · ${esc(mask(m.sender))}</span></span><span class="sn">${fmtText(mask(m.text))}</span></button>`).join("") : `<div class="center faint">No links</div>`;
  };
  body.onclick = e => {
    const t = e.target.closest("[data-tab]"); if (t) return tab(t.dataset.tab);
    if (e.target.closest("a")) return;
    const v = e.target.closest("[data-view]"); if (v) { const m = chat.messages.find(x => x.id === +v.dataset.view); return m.media.kind === "audio" ? jumpTo(m.id) : openViewer(chat, m.id); }
    const j = e.target.closest("[data-jump]"); if (j) jumpTo(j.dataset.jump);
  };
  tab("m");
}

/* insights */
const ACTION_RE = /\b(please|pls|kindly|need to|needs to|will (?:send|share|sign|file|check|follow|call|meet|re-check|update|confirm)|send|share|sign and|file|follow up|by (?:today|tomorrow|tonight|eod|monday|tuesday|wednesday|thursday|friday|saturday|sunday|\d{1,2}(?:st|nd|rd|th)?)|before \d|deadline|due date)\b/i;
const AMT_RE = /(?:₹|\brs\.?\s?|\binr\s?)\s?(\d[\d,]*(?:\.\d+)?)(?:\s?(lakh|lakhs|crore|crores|cr|k))?/gi;
function offlineInsights(chat) {
  const acts = [], amts = [];
  for (const m of chat.messages) {
    if (!m.sender || !m.text) continue;
    if (ACTION_RE.test(m.text)) acts.push(m);
    for (const a of m.text.matchAll(AMT_RE)) amts.push({ m, amt: a[0].trim() });
  }
  return { acts, amts };
}
function responseStats(chat) {
  const per = {}, gaps = []; let prev = null;
  for (const m of chat.messages) {
    if (!m.sender) continue;
    if (prev) { const d = m.ts - prev.ts; if (prev.sender !== m.sender) (per[m.sender] ||= []).push(d); gaps.push({ d, from: prev, to: m }); }
    prev = m;
  }
  const med = a => { const b = a.slice().sort((x, y) => x - y); const k = b.length >> 1; return b.length % 2 ? b[k] : (b[k - 1] + b[k]) / 2; };
  const rows = Object.entries(per).map(([name, a]) => ({ name, n: a.length, median: med(a), avg: a.reduce((x, y) => x + y, 0) / a.length })).sort((a, b) => a.median - b.median);
  return { rows, gaps: gaps.sort((a, b) => b.d - a.d).slice(0, 3) };
}
function panelInsights(chat, body) {
  const msgs = chat.messages.filter(m => m.sender);
  const days = new Set(msgs.map(m => isoDay(m.ts))).size;
  const mediaN = msgs.filter(m => m.type === "media").length;
  const hours = Array(24).fill(0); msgs.forEach(m => hours[new Date(m.ts).getHours()]++); const hmax = Math.max(1, ...hours);
  const pmax = Math.max(1, ...chat.participants.map(p => p.n));
  const { acts, amts } = offlineInsights(chat);
  const rt = responseStats(chat);
  const item = (m, bd) => `<button class="ins-item" data-jump="${m.id}"><span class="hd"><span>${fmtDate(m.ts)}, ${fmtTime(m.ts)}</span><span>·</span><span>${esc(m.sender === chat.me ? "You" : mask(m.sender))}</span></span><span class="bd">${bd}</span></button>`;
  body.innerHTML = `
    <div class="sec"><h4>Overview</h4><div class="tiles">
      <div class="tile"><b>${msgs.length.toLocaleString("en-IN")}</b><span>messages</span></div><div class="tile"><b>${mediaN}</b><span>attachments</span></div>
      <div class="tile"><b>${chat.participants.length}</b><span>participants</span></div><div class="tile"><b>${days}</b><span>active days</span></div></div></div>
    <div class="sec" id="aiSec"><h4>${ic("spark")}<span class="grow">AI summary</span></h4><div id="aiBox"><div class="thinking"><span class="dots"><i></i><i></i><i></i></span>Checking availability</div></div></div>
    <div class="sec"><h4>Messages by participant</h4><div class="bars">${chat.participants.map(p => `<div class="bar-row" style="--h:${p.h}"><span class="bn">${esc(p.name === chat.me ? "You" : mask(p.name))}</span><span class="bt"><i style="width:${(p.n / pmax * 100).toFixed(1)}%"></i></span><span class="bv">${p.n}</span></div>`).join("")}</div></div>
    <div class="sec"><h4>Activity by hour of day</h4><div class="hours" role="img" aria-label="Messages by hour">${hours.map((n, i) => `<i style="height:${Math.max(3, n / hmax * 100)}%" title="${i}:00 · ${n} messages"></i>`).join("")}</div><div class="hours-ax"><span>12 am</span><span>6 am</span><span>12 pm</span><span>6 pm</span><span>11 pm</span></div></div>
    <div class="sec"><h4><span class="grow">Response times</span><span class="faint" style="text-transform:none;letter-spacing:0">time to reply to someone else</span></h4>
      ${rt.rows.length ? `<div class="tbl-wrap"><table><thead><tr><th>Participant</th><th>Replies</th><th>Median</th><th>Average</th></tr></thead><tbody>${rt.rows.map(r => `<tr><td>${esc(r.name === chat.me ? "You" : mask(r.name))}</td><td>${r.n}</td><td>${fmtDur(r.median)}</td><td>${fmtDur(r.avg)}</td></tr>`).join("")}</tbody></table></div>` : '<span class="faint">Not enough back-and-forth to measure</span>'}
      ${rt.gaps.length ? `<div class="ins-list"><span class="faint" style="font-size:12px">Longest silences</span>${rt.gaps.map(g => item(g.to, `<b>${fmtDur(g.d)}</b> after the message of ${fmtDate(g.from.ts)}, ${fmtTime(g.from.ts)}`)).join("")}</div>` : ""}</div>
    <div class="sec"><h4><span class="grow">Requests and commitments</span><span class="faint" style="text-transform:none;letter-spacing:0">${acts.length} found</span></h4><div class="ins-list">${acts.slice(0, 25).map(m => item(m, fmtText(mask(m.text.length > 180 ? m.text.slice(0, 180) + "…" : m.text)))).join("") || '<span class="faint">None detected</span>'}</div></div>
    <div class="sec"><h4><span class="grow">Amounts mentioned</span><span class="faint" style="text-transform:none;letter-spacing:0">${amts.length} found</span></h4><div class="ins-list">${amts.slice(0, 25).map(a => item(a.m, `<b>${esc(a.amt)}</b> — ${esc(a.m.text.length > 120 ? a.m.text.slice(0, 120) + "…" : a.m.text)}`)).join("") || '<span class="faint">None detected</span>'}</div></div>`;
  body.addEventListener("click", e => { const j = e.target.closest("[data-jump]"); if (j) jumpTo(j.dataset.jump); });
  setupAI(chat);
}
async function setupAI(chat) {
  const box = $("#aiBox"); if (!box) return;
  const sample = await cap.sample;
  if (!$("#aiBox")) return;
  if (!sample) { box.innerHTML = `<p class="note" style="margin:0">AI summaries run when ChatVault is opened inside Claude. The rule-based insights below work everywhere.</p>`; return; }
  if (!can("ai")) { box.innerHTML = `<p class="note" style="margin:0">${ic("lock", "i")} Your role does not include AI summaries.</p>`; return; }
  const draw = () => { box.innerHTML = `<div class="ai-card"><p>Claude reads the text of this chat (not the attachments) and returns a summary, action items, a timeline and amounts, each linked to the message it came from.</p><div><button class="btn btn-primary btn-sm" id="aiGo">${ic("spark")}Summarize with Claude</button></div></div>`; $("#aiGo").onclick = () => runAI(chat, sample); };
  if (chat.ai) renderAI(chat, chat.ai); else draw();
}
function transcriptForAI(chat) {
  const lines = chat.messages.filter(m => m.type !== "system").map(m => {
    const d = new Date(m.ts); const stamp = `${isoDay(m.ts)} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
    const body = m.type === "media" ? `[attachment: ${m.media.name}${m.media.missing ? " (missing)" : ""}] ${m.text}` : m.type === "deleted" ? "[deleted message]" : m.type === "omitted" ? "[media omitted]" : m.text;
    return `#${m.id} ${stamp} ${mask(m.sender)}: ${mask(body).replace(/\n/g, " / ")}`;
  });
  let out = lines.join("\n"); if (out.length > 150000) out = "[earlier messages omitted]\n" + out.slice(-150000);
  return out;
}
async function runAI(chat, sample) {
  const box = $("#aiBox"); let ctl = new AbortController();
  box.innerHTML = `<div class="thinking"><span class="dots"><i></i><i></i><i></i></span><span>Claude is reading ${chat.messages.length.toLocaleString("en-IN")} messages…</span><button class="btn btn-ghost btn-sm" id="aiStop" style="margin-left:auto">Stop</button></div>`;
  $("#aiStop").onclick = () => ctl.abort();
  const prompt = `You are analysing an exported WhatsApp conversation for a professional archive. Each line starts with #<message id>.
Reply with ONLY a JSON object of this shape:
{"summary":"3-5 plain sentences","key_points":["..."],"action_items":[{"owner":"name","task":"what","due":"when or empty","ref":<message id>}],"timeline":[{"date":"YYYY-MM-DD","event":"short","ref":<message id>}],"amounts":[{"amount":"₹...","context":"short","ref":<message id>}],"open_questions":["..."]}
Use only facts in the chat. Keep each item under 25 words. Use empty arrays when nothing applies.

Chat title: ${mask(chat.title)}
Participants: ${chat.participants.map(p => mask(p.name)).join(", ")}

${transcriptForAI(chat)}`;
  try {
    const res = await sample.json(prompt, { signal: ctl.signal });
    chat.ai = res; audit("AI summary generated", chat.title); renderAI(chat, res);
  } catch (e) {
    const msg = { cancelled: "Stopped.", not_granted: "AI access was not allowed for this page.", rate_limited: "Too many requests right now. Try again in a minute.", prompt_too_large: "This chat is too long to summarise in one pass.", invalid_json: "Claude's reply could not be read. Try again." }[e?.code] || "The summary could not be generated. Try again.";
    box.innerHTML = `<p class="note" style="margin:0 0 8px">${esc(msg)}</p>${["not_granted", "sampling_disabled"].includes(e?.code) ? "" : `<button class="btn btn-ghost btn-sm" id="aiRetry">Try again</button>`}`;
    $("#aiRetry") && ($("#aiRetry").onclick = () => runAI(chat, sample));
  }
}
function renderAI(chat, r) {
  const box = $("#aiBox"); if (!box) return;
  const ref = id => (id && chat.messages.some(m => m.id === +id)) ? `<button class="ref" data-jump="${+id}">#${+id}</button>` : "";
  const list = (arr, f) => Array.isArray(arr) && arr.length ? `<ul>${arr.map(f).join("")}</ul>` : `<span class="faint">None</span>`;
  box.innerHTML = `<div class="ai-out">
    <div><h5>Summary</h5><p style="margin:0">${esc(r.summary || "")}</p></div>
    <div><h5>Key points</h5>${list(r.key_points, x => `<li>${esc(x)}</li>`)}</div>
    <div><h5>Action items</h5>${list(r.action_items, x => `<li><b>${esc(x.owner || "")}</b>${x.owner ? ": " : ""}${esc(x.task || "")}${x.due ? ` <span class="faint">(${esc(x.due)})</span>` : ""}${ref(x.ref)}</li>`)}</div>
    <div><h5>Timeline</h5>${list(r.timeline, x => `<li><span class="faint">${esc(x.date || "")}</span> ${esc(x.event || "")}${ref(x.ref)}</li>`)}</div>
    <div><h5>Amounts</h5>${list(r.amounts, x => `<li><b>${esc(x.amount || "")}</b> ${esc(x.context || "")}${ref(x.ref)}</li>`)}</div>
    ${r.open_questions?.length ? `<div><h5>Open questions</h5>${list(r.open_questions, x => `<li>${esc(x)}</li>`)}</div>` : ""}
    <p class="note" style="margin:0">Generated by Claude from the chat text. Verify against the linked messages before relying on it.</p></div>`;
}

/* ============================================================ viewer (lightbox / documents) */
function openViewer(chat, id) {
  const m = chat.messages.find(x => x.id === id); if (!m?.media?.file) return;
  const visual = chat.messages.filter(x => x.type === "media" && !x.media.missing && ["image", "video"].includes(x.media.kind));
  let idx = visual.findIndex(x => x.id === id);
  const isVisual = idx >= 0;
  const lb = h(`<div class="lightbox" role="dialog" aria-modal="true" aria-label="Viewer"><div class="lb-head"><span class="avatar sm" id="lbAv"></span><span class="t"><b id="lbWho"></b><span id="lbWhen"></span></span>
    <button class="icon-btn" id="lbGo" title="Show in chat" aria-label="Show in chat">${ic("chevD")}</button>
    <button class="icon-btn" id="lbDl" title="Download" aria-label="Download"${can("media") ? "" : " disabled"}>${ic("download")}</button>
    <button class="icon-btn" id="lbX" title="Close" aria-label="Close">${ic("close")}</button></div>
    <div class="lb-stage" id="lbStage"></div><div class="lb-cap" id="lbCap"></div>${isVisual && visual.length > 1 ? `<div class="lb-strip" id="lbStrip">${visual.map((v, i) => `<button data-i="${i}" aria-label="Item ${i + 1}">${v.media.kind === "video" ? `<span style="display:grid;place-items:center;height:100%;background:#000;color:#fff">${ic("video")}</span>` : `<img src="${mediaUrl(chat, v.media.file)}" alt="">`}</button>`).join("")}</div>` : ""}</div>`);
  document.body.append(lb);
  let cur = m;
  const show = async (msg) => {
    cur = msg; const p = chat.participants.find(x => x.name === msg.sender);
    const av = $("#lbAv", lb); av.style.setProperty("--h", p?.h ?? 0); av.textContent = initials(mask(msg.sender, chat));
    $("#lbWho", lb).textContent = msg.sender === chat.me ? "You" : mask(msg.sender);
    $("#lbWhen", lb).textContent = `${fmtDate(msg.ts)}, ${fmtTime(msg.ts)} · ${chat.media.get(msg.media.file).name}`;
    $("#lbCap", lb).textContent = msg.text ? mask(msg.text) : "";
    const st = $("#lbStage", lb); const url = mediaUrl(chat, msg.media.file); const k = msg.media.kind;
    if (k === "image" || k === "sticker") { st.innerHTML = `<img src="${url}" alt="">`; const im = $("img", st); im.onclick = () => im.classList.toggle("zoom"); }
    else if (k === "video") st.innerHTML = `<video src="${url}" controls autoplay playsinline></video>`;
    else if (/\.pdf$/i.test(chat.media.get(msg.media.file).name)) {
      st.innerHTML = `<div class="thinking"><span class="dots"><i></i><i></i><i></i></span>Rendering PDF</div>`;
      try {
        await libs.pdf();
        const pdf = await pdfjsLib.getDocument({ data: await chat.media.get(msg.media.file).blob.arrayBuffer(), isEvalSupported: false }).promise;
        st.innerHTML = `<div class="pdf-pages" id="pdfPages"></div>`; const pages = $("#pdfPages", st);
        for (let i = 1; i <= Math.min(pdf.numPages, 50); i++) {
          const pg = await pdf.getPage(i); const vp = pg.getViewport({ scale: 1.6 });
          const cv = document.createElement("canvas"); cv.width = vp.width; cv.height = vp.height; pages.append(cv);
          await pg.render({ canvasContext: cv.getContext("2d"), viewport: vp }).promise;
        }
      } catch (e) { console.error(e); st.innerHTML = docCard(msg); }
    } else if (/\.(txt|csv|json|vcf)$/i.test(chat.media.get(msg.media.file).name)) {
      const t = await chat.media.get(msg.media.file).blob.text();
      st.innerHTML = `<pre class="mono" style="white-space:pre-wrap;max-width:800px;width:100%;max-height:100%;overflow:auto;background:var(--panel);padding:20px;border-radius:8px;box-shadow:var(--shadow-2)">${esc(mask(t.slice(0, 200000)))}</pre>`;
    } else st.innerHTML = docCard(msg);
    if (isVisual) $$("#lbStrip button", lb).forEach((b, i) => { b.classList.toggle("on", i === idx); if (i === idx) b.scrollIntoView({ inline: "center", block: "nearest" }); });
  };
  const docCard = msg => { const f = chat.media.get(msg.media.file); const ext = extOf(f.name); return `<div class="center" style="background:var(--panel);border-radius:16px;box-shadow:var(--shadow-2);padding:32px"><span class="ext ${esc(ext)}" style="width:56px;height:68px;font-size:13px">${esc(ext.toUpperCase())}</span><b style="font-size:16px;margin-top:8px">${esc(f.name)}</b><span class="muted">${fmtBytes(f.size)} · no preview for this file type</span>${can("media") ? `<button class="btn btn-primary btn-sm" data-dl style="margin-top:8px">${ic("download")}Download</button>` : `<span class="note">${ic("lock", "i")} Your role cannot download attachments</span>`}</div>`; };
  const nav = d => { if (!isVisual) return; idx = (idx + d + visual.length) % visual.length; show(visual[idx]); };
  if (isVisual && visual.length > 1) { lb.append(h(`<button class="lb-nav l" aria-label="Previous">${ic("chevL")}</button>`)); lb.append(h(`<button class="lb-nav r" aria-label="Next">${ic("chevR")}</button>`)); $(".lb-nav.l", lb).onclick = () => nav(-1); $(".lb-nav.r", lb).onclick = () => nav(1); }
  const close = () => { lb.remove(); document.removeEventListener("keydown", key); };
  const key = e => { if (e.key === "Escape") close(); if (e.key === "ArrowLeft") nav(-1); if (e.key === "ArrowRight") nav(1); };
  document.addEventListener("keydown", key);
  $("#lbX", lb).onclick = close;
  $("#lbGo", lb).onclick = () => { close(); jumpTo(cur.id); };
  const dl = () => { const f = chat.media.get(cur.media.file); audit("Downloaded attachment", `${chat.title} · ${f.name}`); saveFile(f.name, f.blob); };
  $("#lbDl", lb).onclick = dl;
  lb.addEventListener("click", e => { if (e.target.closest("[data-dl]")) dl(); const s = e.target.closest("#lbStrip button"); if (s) { idx = +s.dataset.i; show(visual[idx]); } });
  show(m);
}

/* ============================================================ exports */
/* ============================================================ export dialog, date range and PDF */
function sliceChat(chat, from, to) {
  if (!from && !to) return chat;
  const msgs = chat.messages.filter(m => { const d = isoDay(m.ts); return (!from || d >= from) && (!to || d <= to); });
  const used = new Set(msgs.filter(m => m.media?.file).map(m => m.media.file));
  const media = new Map([...chat.media].filter(([k]) => used.has(k)));
  const counts = {}; msgs.forEach(m => { if (m.sender) counts[m.sender] = (counts[m.sender] || 0) + 1; });
  const participants = chat.participants.filter(p => counts[p.name]).map(p => ({ ...p, n: counts[p.name] }));
  return { ...chat, messages: msgs, media, participants, _alias: aliasMap(chat), range: { from, to, total: chat.messages.length },
    linked: msgs.filter(m => m.media?.file).length, missing: msgs.filter(m => m.media?.missing).length, unlinkedFiles: 0 };
}
function rangeTranscript(chat) {
  return chat.messages.map(m => {
    const d = new Date(m.ts); const stamp = `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}, ${fmtTime(m.ts)}`;
    const body = m.type === "media" ? `<attached: ${m.media.file ? chat.media.get(m.media.file).name : m.media.name}>${m.text ? " " + m.text : ""}` : m.type === "omitted" ? "<Media omitted>" : m.text;
    return m.sender ? `${stamp} - ${mask(m.sender, chat)}: ${mask(body, chat)}` : `${stamp} - ${mask(body, chat)}`;
  }).join("\n") + "\n";
}

function openExport() {
  const chat = activeChat(); if (!chat || !can("export")) return;
  const d0 = isoDay(chat.messages[0].ts), d1 = isoDay(chat.messages[chat.messages.length - 1].ts);
  const fy = (() => { const t = new Date(chat.messages[chat.messages.length - 1].ts); const y = t.getMonth() >= 3 ? t.getFullYear() : t.getFullYear() - 1; return [`${y}-04-01`, `${y + 1}-03-31`]; })();
  const ov = h(`<div class="overlay"><div class="modal wide" role="dialog" aria-modal="true" aria-labelledby="expT"><div class="modal-head"><h3 id="expT">Export “${esc(mask(chat.title, chat))}”</h3><button class="icon-btn" data-x aria-label="Close">${ic("close")}</button></div>
    <div class="modal-body" id="expBody">
      <div class="steps" style="gap:10px"><b>Period</b>
        <div class="range-row"><div class="field"><label for="exFrom">From</label><input class="input" type="date" id="exFrom" min="${d0}" max="${d1}" value="${d0}"></div>
          <div class="field"><label for="exTo">To</label><input class="input" type="date" id="exTo" min="${d0}" max="${d1}" value="${d1}"></div></div>
        <div class="s-filters"><button class="chip on" data-rg="all">Whole chat</button><button class="chip" data-rg="30">Last 30 days</button><button class="chip" data-rg="fy">FY ${fy[0].slice(0, 4)}-${fy[1].slice(2, 4)}</button><button class="chip" data-rg="month">Latest month</button></div>
        <span class="note" id="exCount"></span></div>
      <div class="exp-grid">
        <button class="exp-opt" data-k="pdfb"><span class="ico">${ic("doc")}</span><div><b>PDF · Evidence transcript</b><span>Cover page with fingerprints, numbered table of messages with change flags, integrity statement, attachment fingerprints and signature lines.</span></div></button>
        <button class="exp-opt" data-k="bundle" data-needs-stars><span class="ico">${ic("star")}</span><div><b>PDF · Evidence bundle</b><span>Only your starred messages, each as a numbered annexure with its date, sender, photo, fingerprint, note and citation. <em id="starCount"></em></span></div></button>
        <button class="exp-opt" data-k="cert"><span class="ico">${ic("cert")}</span><div><b>Section 63 certificate · draft (.docx)</b><span>Part A pre-filled with the hash values, blank Part B for the expert, and a hash report annexure. Edit in Word, then sign.</span></div></button>
        <button class="exp-opt" data-k="pdfa"><span class="ico">${ic("doc")}</span><div><b>PDF · Chat view</b><span>Pages that look like the conversation on a phone, with photos inline and message numbers for citing.</span></div></button>
        <button class="exp-opt" data-k="zip"><span class="ico">${ic("zip")}</span><div><b>Complete archive (.zip)</b><span>Everything: PDFs, chat viewer, sorted media, Excel index, transcripts, fingerprint lists, integrity statement and output hashes.</span></div></button>
        <button class="exp-opt" data-k="html"><span class="ico">${ic("html")}</span><div><b>Chat viewer (.html)</b><span>One file that opens in any browser and looks like the chat, with photos and voice notes embedded.</span></div></button>
        <button class="exp-opt" data-k="xlsx"><span class="ico">${ic("sheet")}</span><div><b>Excel index (.xlsx)</b><span>Every message and attachment in rows, with change status and SHA-256 fingerprints.</span></div></button></div>
      <div class="steps" style="gap:10px"><b>Options</b>
        <label class="check"><input type="checkbox" id="expImgs" checked><span>Include photos in PDFs</span></label>
        <div class="bundle-opts"><label for="expPrefix">Annexure prefix</label><input class="input" id="expPrefix" value="A" maxlength="6" style="width:80px;height:34px"><label class="check" style="margin:0"><input type="checkbox" id="expPage" checked><span>Each annexure on a new page</span></label></div>
        <label class="check"><input type="checkbox" id="expBoth" checked><span>Archive ZIP: include both PDF styles</span></label>
        <label class="check"><input type="checkbox" id="expMask"><span>Mask phone numbers and email addresses</span></label>
        <label class="check"><input type="checkbox" id="expNames"><span>Replace participant names with Participant A, B, C… everywhere</span></label></div>
      <div class="note" id="expNote"></div></div></div></div>`);
  document.body.append(ov);
  $("[data-x]", ov).onclick = () => ov.remove();
  const count = () => {
    const f = $("#exFrom", ov).value, t = $("#exTo", ov).value;
    const n = chat.messages.filter(m => { const d = isoDay(m.ts); return d >= f && d <= t; }).length;
    const sc = chat.messages.filter(m => chat.stars[m.key] && isoDay(m.ts) >= f && isoDay(m.ts) <= t).length;
    $("#exCount", ov).textContent = f > t ? "The start date is after the end date." : `${n.toLocaleString("en-IN")} of ${chat.messages.length.toLocaleString("en-IN")} messages in this period · ${sc} starred`;
    $("#starCount", ov).textContent = sc ? `${sc} starred in this period.` : "Star messages first (hover a message → Star).";
    $$(".exp-opt", ov).forEach(b => b.disabled = !n || f > t || (b.hasAttribute("data-needs-stars") && !sc));
  };
  const setRange = (f, t, key) => { $("#exFrom", ov).value = f < d0 ? d0 : f > d1 ? d1 : f; $("#exTo", ov).value = t > d1 ? d1 : t < d0 ? d0 : t; $$("[data-rg]", ov).forEach(b => b.classList.toggle("on", b.dataset.rg === key)); count(); };
  ov.querySelector(".s-filters").onclick = e => {
    const b = e.target.closest("[data-rg]"); if (!b) return; const k = b.dataset.rg;
    if (k === "all") setRange(d0, d1, k);
    if (k === "30") setRange(isoDay(chat.messages[chat.messages.length - 1].ts - 29 * 864e5), d1, k);
    if (k === "fy") setRange(fy[0], fy[1], k);
    if (k === "month") { const t = new Date(chat.messages[chat.messages.length - 1].ts); setRange(`${t.getFullYear()}-${pad(t.getMonth() + 1)}-01`, d1, k); }
  };
  $("#exFrom", ov).onchange = $("#exTo", ov).onchange = () => { $$("[data-rg]", ov).forEach(b => b.classList.remove("on")); count(); };
  count();
  ov.addEventListener("click", async e => {
    const b = e.target.closest("[data-k]"); if (!b || b.disabled) return;
    const from = $("#exFrom", ov).value, to = $("#exTo", ov).value;
    const whole = from === d0 && to === d1;
    const view = whole ? chat : sliceChat(chat, from, to);
    const red = { contacts: $("#expMask", ov).checked, names: $("#expNames", ov).checked };
    const opts = { images: $("#expImgs", ov).checked, both: $("#expBoth", ov).checked, prefix: ($("#expPrefix", ov).value.trim() || "A").toUpperCase(), perPage: $("#expPage", ov).checked };
    if (b.dataset.k === "cert") { ov.remove(); return openCertificate(chat, view); }
    $$(".exp-opt", ov).forEach(x => x.disabled = true);
    const note = $("#expNote", ov);
    note.innerHTML = `<span class="thinking"><span class="dots"><i></i><i></i><i></i></span><span class="pmsg">Preparing ${b.querySelector("b").textContent}…</span></span>`;
    const prog = p => { const x = $(".pmsg", note); if (x) x.textContent = p; };
    R = red;
    try {
      const base = `${slug(mask(chat.title, chat))}_${whole ? isoDay(Date.now()) : from + "_to_" + to}`;
      const k = b.dataset.k; let name, blob;
      if (k === "pdfb") { name = base + "_evidence.pdf"; blob = await buildPDF(view, "evidence", opts, prog); }
      if (k === "bundle") { name = base + "_evidence-bundle.pdf"; blob = await buildPDF(view, "bundle", opts, prog); }
      if (k === "pdfa") { name = base + "_chat.pdf"; blob = await buildPDF(view, "chat", opts, prog); }
      if (k === "html") { name = base + ".html"; blob = new Blob([await buildArchiveHTML(view, { embed: true })], { type: "text/html" }); }
      if (k === "xlsx") { name = base + ".xlsx"; blob = await buildXLSX(view); }
      if (k === "zip") { name = base + "_archive.zip"; blob = await buildZip(view, opts, prog); }
      const hash = await sha256(blob);
      const ok = await saveFile(name, blob);
      audit("Exported chat", `${chat.title} · ${name} · ${whole ? "whole chat" : from + " to " + to} · SHA-256 ${hash}${red.contacts ? " · contacts masked" : ""}${red.names ? " · names replaced" : ""}${ok ? "" : " · not saved"}`);
      if (ok) logEvent(chat, "Exported", `${name} · ${whole ? "whole chat" : from + " to " + to}${red.contacts || red.names ? " · redacted" : ""}`, hash);
      note.innerHTML = `<div class="done-box"><b>${ic("check")}${esc(name)}</b><span class="faint">${fmtBytes(blob.size)} · SHA-256 of this file, recorded in the audit log:</span>
        <div class="hash"><span class="mono">${hash}</span><button class="icon-btn" data-copy="${hash}" aria-label="Copy">${ic("copy")}</button></div></div>`;
      $$(".exp-opt", ov).forEach(x => x.disabled = false); count();
    } catch (x) { console.error(x); note.textContent = "Export failed: " + (x.message || x); $$(".exp-opt", ov).forEach(y => y.disabled = false); }
    finally { R = null; }
  });
  bindCopy(ov);
}

/* ---- PDF (pdfmake) ---- */
libs.pdfmake = function () { return window.pdfMake?.vfs ? Promise.resolve() : (this._pm ||= loadScript(CDN + "pdfmake/0.2.7/pdfmake.min.js").then(() => loadScript(CDN + "pdfmake/0.2.7/vfs_fonts.js"))); };
const PC = { brand: "#0d7a65", fg: "#111b21", muted: "#667781", faint: "#8a979e", line: "#e1e7e4", band: "#f2f5f4", chat: "#efeae2", inb: "#ffffff", out: "#d9fdd3", sys: "#fff3c2", sysFg: "#5b5130", warn: "#a86a10", warnBg: "#fdf0d9", danger: "#c8382f", dangerBg: "#fbe3e1", link: "#027eb5" };
const pdfClean = s => String(s ?? "").replace(/\p{Extended_Pictographic}|[\u{1F1E6}-\u{1F1FF}\u{1F3FB}-\u{1F3FF}️‍‎‏ ]/gu, m => m === " " ? " " : "").replace(/[ \t]{2,}/g, " ");
function pdfRich(s, base = {}) {
  s = pdfClean(s); const out = []; const re = /(^|[\s(])([*_~])(\S(?:[^*_~\n]*?\S)?)\2(?=$|[\s.,!?:;)])|(https?:\/\/\S+[^\s.,:;"')\]])/g;
  let last = 0, m;
  while ((m = re.exec(s))) {
    if (m[4]) { if (m.index > last) out.push({ text: s.slice(last, m.index), ...base }); out.push({ text: m[4], color: PC.link, ...base }); last = m.index + m[4].length; continue; }
    const start = m.index + m[1].length; if (start > last) out.push({ text: s.slice(last, start), ...base });
    out.push({ text: m[3], ...base, ...(m[2] === "*" ? { bold: true } : m[2] === "_" ? { italics: true } : { decoration: "lineThrough" }) });
    last = start + m[3].length + 2;
  }
  if (last < s.length) out.push({ text: s.slice(last), ...base });
  return out.length ? out : [{ text: "", ...base }];
}
async function imgForPdf(f, max = 900) {
  try {
    const bmp = await createImageBitmap(f.blob);
    const sc = Math.min(1, max / Math.max(bmp.width, bmp.height));
    const c = document.createElement("canvas"); c.width = Math.max(1, Math.round(bmp.width * sc)); c.height = Math.max(1, Math.round(bmp.height * sc));
    const g = c.getContext("2d"); g.fillStyle = "#fff"; g.fillRect(0, 0, c.width, c.height); g.drawImage(bmp, 0, 0, c.width, c.height);
    return { url: c.toDataURL("image/jpeg", 0.82), w: c.width, h: c.height };
  } catch { return null; }
}
const kindLabel = k => ({ image: "Photo", sticker: "Sticker", video: "Video", audio: "Voice note", doc: "Document", contact: "Contact card" })[k] || "File";
const INDIC_RE = /[\u0900-\u097F\u0A80-\u0AFF]/;
function pdfFonts(needIndic) {
  const f = { Roboto: { normal: "Roboto-Regular.ttf", bold: "Roboto-Medium.ttf", italics: "Roboto-Italic.ttf", bolditalics: "Roboto-MediumItalic.ttf" } };
  if (needIndic && window.CV_FONTS) {
    if (!pdfMake.vfs["NotoSansGujarati-Regular.ttf"]) { pdfMake.vfs["NotoSansGujarati-Regular.ttf"] = CV_FONTS.guj; pdfMake.vfs["NotoSansDevanagari-Regular.ttf"] = CV_FONTS.deva; }
    const one = n => ({ normal: n, bold: n, italics: n, bolditalics: n });
    f.NotoGuj = one("NotoSansGujarati-Regular.ttf"); f.NotoDeva = one("NotoSansDevanagari-Regular.ttf");
  }
  return f;
}
/* Split text into runs so Gujarati and Devanagari use Noto fonts while Latin, digits and ₹ stay in Roboto. */
function splitScripts(t) {
  const cls = c => /[\u0A80-\u0AFF]/.test(c) ? "G" : /[\u0900-\u097F\u200C\u200D]/.test(c) ? "D" : /\s/.test(c) ? " " : "L";
  const runs = []; let cur = null;
  for (const ch of t) { let k = cls(ch); if (k === " ") k = cur ? cur.k : "L"; if (k === "D" && /[\u0964\u0965]/.test(ch) && cur?.k === "G") k = "G"; if (!cur || cur.k !== k) { cur = { k, text: "" }; runs.push(cur); } cur.text += ch; }
  return runs.map(r => r.k === "G" ? { text: r.text, font: "NotoGuj" } : r.k === "D" ? { text: r.text, font: "NotoDeva" } : { text: r.text });
}
function indicize(node) {
  if (Array.isArray(node)) return node.map(indicize);
  if (!node || typeof node !== "object") return node;
  if (typeof node.text === "string" && INDIC_RE.test(node.text)) node.text = splitScripts(node.text);
  else if (Array.isArray(node.text)) node.text = node.text.flatMap(t => typeof t === "string" ? (INDIC_RE.test(t) ? splitScripts(t) : [t]) : (t && typeof t.text === "string" && INDIC_RE.test(t.text) ? splitScripts(t.text).map(r => ({ ...t, ...r })) : [indicize(t)]));
  for (const k of ["stack", "columns", "content", "ul", "ol"]) if (node[k]) node[k] = indicize(node[k]);
  if (node.table?.body) node.table.body = node.table.body.map(r => r.map(indicize));
  return node;
}
async function buildPDF(chat, style, opts = {}, onProgress) {
  onProgress?.("Loading PDF engine…"); await libs.pdfmake();
  const M = s => pdfClean(mask(s || "", chat));
  const imgs = {};
  if (opts.images !== false) {
    const pool = style === "bundle" ? chat.messages.filter(m => chat.stars?.[m.key]) : chat.messages;
    const list = pool.filter(m => m.type === "media" && m.media.file && ["image", "sticker"].includes(m.media.kind));
    for (const [i, m] of list.entries()) { if (!imgs[m.media.file]) imgs[m.media.file] = await imgForPdf(chat.media.get(m.media.file), style === "evidence" ? 600 : 1000); if (i % 5 === 0) onProgress?.(`Preparing photos ${i + 1} of ${list.length}…`); }
  }
  onProgress?.("Laying out pages…");
  const first = chat.messages[0], last = chat.messages[chat.messages.length - 1];
  const who = m => m.sender === chat.me ? "You" : M(m.sender);
  const src0 = chat.sources[chat.sources.length - 1];
  const rangeTxt = chat.range ? `${fmtDate(first.ts)} – ${fmtDate(last.ts)} (selected period: ${chat.messages.length} of ${chat.range.total} messages)` : `${fmtDate(first.ts)} – ${fmtDate(last.ts)}`;
  const noteOf = m => chat.mnotes?.[m.key];
  const flags = m => [chat.stars?.[m.key] ? ["STARRED", PC.brand, "#dcefe8"] : null, m.recovered ? ["RECOVERED", PC.warn, PC.warnBg] : null, m.history ? ["EDITED", PC.warn, PC.warnBg] : null, m.goneIn != null ? ["MISSING LATER", PC.danger, PC.dangerBg] : null].filter(Boolean);
  const attLine = m => {
    if (m.media.missing) return { text: `[${kindLabel(m.media.kind)} not in export: ${M(m.media.name)}]`, color: PC.danger, fontSize: 8 };
    const f = chat.media.get(m.media.file);
    return { text: `[${kindLabel(m.media.kind)}: ${M(f.name)} · ${fmtBytes(f.size)} · SHA-256 ${f.hash.slice(0, 16)}…]`, color: PC.brand, fontSize: 8 };
  };
  const header = (cur) => ({ margin: [40, 18, 40, 0], stack: [{ columns: [{ stack: [{ text: M(chat.title), bold: true, fontSize: 11.5 }, { text: style === "chat" ? `WhatsApp ${chat.isGroup ? "group" : "chat"} · ${rangeTxt}` : style === "bundle" ? `Evidence bundle${chat.matter?.client ? " · " + pdfClean(chat.matter.client) : ""}` : `Transcript of WhatsApp electronic record${chat.matter?.client ? " · " + pdfClean(chat.matter.client) : ""}`, fontSize: 7.5, color: PC.muted }] }, { text: `ChatVault ${VERSION}`, alignment: "right", fontSize: 7.5, color: PC.muted, margin: [0, 6, 0, 0] }] },
    { canvas: [{ type: "line", x1: 0, y1: 6, x2: 515, y2: 6, lineWidth: 1.2, lineColor: PC.brand }] }] });
  const footer = (cur, total) => ({ margin: [40, 8, 40, 0], columns: [{ text: `Source SHA-256 ${src0.hash.slice(0, 16)}…${src0.hash.slice(-8)} · Generated ${fmtDT(Date.now())} by ${S.user.username}`, fontSize: 6.8, color: PC.faint }, { text: `Page ${cur} of ${total}`, alignment: "right", fontSize: 7, color: PC.faint, width: 70 }] });
  const doc = { pageSize: "A4", pageMargins: [40, 66, 40, 40], header, footer, defaultStyle: { font: "Roboto", fontSize: 9, color: PC.fg, lineHeight: 1.18 },
    info: { title: `${M(chat.title)} - WhatsApp ${style === "chat" ? "chat" : style === "bundle" ? "evidence bundle" : "transcript"}`, author: S.user.name, creator: `ChatVault ${VERSION}`, subject: `SHA-256 of source export: ${src0.hash}` }, content: [] };
  const C = doc.content;

  if (style === "chat") {
    doc.background = () => ({ canvas: [{ type: "rect", x: 0, y: 0, w: 595.28, h: 841.89, color: PC.chat }, { type: "rect", x: 0, y: 0, w: 595.28, h: 52, color: "#ffffff" }] });
    const chip = (text, fill, color) => ({ columns: [{ width: "*", text: "" }, { width: "auto", table: { body: [[{ text, fontSize: 7.5, color, alignment: "center" }]] }, layout: { fillColor: () => fill, hLineWidth: () => 0, vLineWidth: () => 0, paddingLeft: () => 8, paddingRight: () => 8, paddingTop: () => 3, paddingBottom: () => 3 } }, { width: "*", text: "" }], margin: [0, 6, 0, 4] });
    let day = null, prev = null;
    const MAXW = 330;
    for (const m of chat.messages) {
      const d = isoDay(m.ts);
      if (d !== day) { C.push(chip(fmtDay(m.ts).toUpperCase(), "#ffffff", "#54656f")); day = d; prev = null; }
      if (m.type === "system") { C.push(chip(M(m.text), PC.sys, PC.sysFg)); prev = m; continue; }
      const out = !!chat.me && m.sender === chat.me;
      const firstOf = !prev || prev.type === "system" || prev.sender !== m.sender || (m.ts - prev.ts) > 6 * 60000;
      const st = []; let w = 0; const est = s => Math.max(...pdfClean(s || "").split("\n").map(l => l.length)) * 4.75 + 18;
      if (chat.isGroup && !out && firstOf) { const p = chat.participants.find(x => x.name === m.sender); st.push({ text: M(m.sender), bold: true, fontSize: 8, color: hslHex(p?.h ?? 0, 55, 34), margin: [0, 0, 0, 1] }); w = Math.max(w, est(M(m.sender))); }
      if (m.type === "deleted") { st.push({ text: out ? "You deleted this message" : "This message was deleted", italics: true, color: PC.muted }); w = Math.max(w, 150); }
      else if (m.type === "omitted") { st.push({ text: `${m.text === "media" ? "Media" : m.text[0].toUpperCase() + m.text.slice(1)} not included (exported without media)`, italics: true, color: PC.muted }); w = Math.max(w, 170); }
      else if (m.type === "media") {
        const im = m.media.file && imgs[m.media.file];
        if (im) { const fw = Math.min(240, im.w), fh = Math.min(fw * im.h / im.w, 300); st.push({ image: im.url, fit: [fw, fh], margin: [0, 1, 0, 3] }); w = Math.max(w, Math.min(254, fw + 14)); st.push({ ...attLine(m), fontSize: 6.8, color: PC.muted }); }
        else { st.push(attLine(m)); w = Math.max(w, 250); }
      }
      if (m.text && !["deleted", "omitted"].includes(m.type)) { st.push({ text: pdfRich(mask(m.text, chat)), margin: [0, 1, 0, 0] }); w = Math.max(w, est(mask(m.text, chat))); }
      if (m.recovered) st.push({ table: { widths: ["*"], body: [[{ stack: [{ text: `RECOVERED FROM THE ${srcLabel(chat, m.recovered.src).toUpperCase()}`, bold: true, fontSize: 6.5, color: PC.warn }, { text: pdfRich(mask(m.recovered.text || m.recovered.media?.name || "", chat)), fontSize: 8.5 }] }]] }, layout: { fillColor: () => PC.warnBg, hLineWidth: () => 0, vLineWidth: i => i === 0 ? 2 : 0, vLineColor: () => PC.warn, paddingLeft: () => 6, paddingTop: () => 3, paddingBottom: () => 3 }, margin: [0, 3, 0, 1] }), w = Math.max(w, 220);
      if (m.history) m.history.forEach(x => { st.push({ text: [{ text: "Earlier version: ", color: PC.muted }, { text: M(x.text), decoration: "lineThrough", color: PC.muted }], fontSize: 7.5, margin: [0, 3, 0, 0] }); w = Math.max(w, Math.min(MAXW, est(x.text) * 0.85)); });
      if (noteOf(m)) { st.push({ table: { widths: ["*"], body: [[{ text: [{ text: "Note: ", bold: true, color: PC.brand }, { text: M(noteOf(m)) }], fontSize: 7.8 }]] }, layout: { fillColor: () => "#fffbe6", hLineWidth: () => 0, vLineWidth: () => 0, paddingLeft: () => 5, paddingTop: () => 2, paddingBottom: () => 2 }, margin: [0, 3, 0, 0] }); w = Math.max(w, Math.min(MAXW, est(noteOf(m)) * 0.85 + 30)); }
      const metaTxt = [chat.stars?.[m.key] ? "STARRED · " : "", m.goneIn != null ? "MISSING FROM LATER EXPORT · " : "", m.edited ? "Edited · " : "", fmtTime(m.ts)].join("");
      st.push({ columns: [{ text: `#${m.id}`, fontSize: 6.3, color: PC.faint }, { text: metaTxt, alignment: "right", fontSize: 6.6, color: m.goneIn != null ? PC.danger : PC.muted }], margin: [0, 2, 0, 0] });
      w = Math.min(MAXW, Math.max(w, 110 + (m.edited ? 30 : 0) + (m.goneIn != null ? 90 : 0) + (chat.stars?.[m.key] ? 40 : 0)));
      const bubble = { width: w, table: { widths: ["*"], body: [[{ stack: st }]] }, layout: { fillColor: () => out ? PC.out : PC.inb, hLineWidth: () => 0, vLineWidth: () => 0, paddingLeft: () => 7, paddingRight: () => 7, paddingTop: () => 5, paddingBottom: () => 4 } };
      C.push({ columns: out ? [{ width: "*", text: "" }, bubble] : [bubble, { width: "*", text: "" }], margin: [0, firstOf ? 5 : 2, 0, 0], unbreakable: true });
      prev = m;
    }
  } else {
    const isBundle = style === "bundle";
    const starredList = chat.messages.filter(m => chat.stars?.[m.key]);
    const mt = chat.matter || {};
    const kv = (k, v, mono) => [{ text: k, color: PC.muted }, mono ? { text: v, fontSize: 7.3, characterSpacing: 0.1 } : { text: v }];
    const st = chat.sources.length > 1 ? changeStats(chat) : null;
    const red = R || {};
    C.push({ text: isBundle ? "Evidence Bundle" : "WhatsApp Chat Transcript", fontSize: 20, bold: true, color: PC.brand, margin: [0, 6, 0, 2] });
    C.push({ text: isBundle ? `${starredList.length} selected message${starredList.length === 1 ? "" : "s"} from a WhatsApp ${chat.isGroup ? "group" : "chat"}, numbered as annexures ${opts.prefix || "A"}-1 to ${opts.prefix || "A"}-${starredList.length}` : chat.sources.length > 1 ? `Prepared from ${chat.sources.length} exports, merged and verified` : "Prepared from the original WhatsApp export", color: PC.muted, margin: [0, 0, 0, 12] });
    const rows = [
      ...(mt.client ? [kv("Client", `${pdfClean(mt.client)}${mt.pan ? ` · PAN ${mt.pan}` : ""}${mt.gstin ? ` · GSTIN ${mt.gstin}` : ""}`)] : []),
      ...(mt.matter || mt.fy || mt.ref ? [kv("Matter", [mt.matter && pdfClean(mt.matter), mt.fy && `FY ${mt.fy}`, mt.ref && `Ref. ${pdfClean(mt.ref)}`].filter(Boolean).join(" · "))] : []),
      kv("Chat", `${M(chat.title)} (${chat.isGroup ? "group" : "chat"}, ${chat.participants.length} participants)`),
      kv("Participants", chat.participants.map(p => (p.name === chat.me ? `${M(p.name)} (preparer's side)` : M(p.name))).join(", ")),
      kv("Period", `${fmtDT(first.ts)} to ${fmtDT(last.ts)}`),
      ...(chat.range ? [kv("Selection", `Messages from ${fmtDate(new Date(chat.range.from).getTime())} to ${fmtDate(new Date(chat.range.to).getTime())}: ${chat.messages.length} of ${chat.range.total}. Message numbers are those of the complete chat.`)] : []),
      kv("Messages", `${chat.messages.length} · ${chat.linked} attachments${st ? ` · ${chat.messages.filter(m => m.recovered).length} recovered · ${chat.messages.filter(m => m.history).length} edited · ${chat.messages.filter(m => m.goneIn != null).length} missing from later export` : ""}`),
      ...chat.sources.map((s, i) => kv(chat.sources.length > 1 ? `Export ${i + 1}` : "Source export", `${M(s.name)}\nSHA-256 ${s.hash}\n${s.count} messages · ${fmtDate(s.first)} – ${fmtDate(s.last)} · imported ${fmtDT(s.importedAt)} by ${s.importedBy}`, true)),
      kv("Redaction", [red.contacts ? "phone numbers and emails masked" : "", red.names ? "participant names replaced" : ""].filter(Boolean).join("; ") || "None"),
      kv("Prepared by", `${S.user.name} (${ROLES[S.user.role].label}) · ${fmtDT(Date.now())}`)
    ];
    C.push({ table: { widths: [92, "*"], body: rows }, layout: { hLineWidth: (i, n) => i === 0 || i === n.table.body.length ? 0 : 0.5, hLineColor: () => PC.line, vLineWidth: () => 0, paddingTop: () => 4, paddingBottom: () => 4, paddingLeft: () => 0 }, margin: [0, 0, 0, 14] });
    if (isBundle) {
      const P = opts.prefix || "A";
      C.push({ text: "Index of annexures", fontSize: 12, bold: true, color: PC.brand, margin: [0, 0, 0, 6] });
      C.push({ table: { headerRows: 1, widths: [52, 78, 80, "*"], body: [["Annexure", "Date and time", "From", "Message"].map(t => ({ text: t, bold: true, color: "#ffffff", fontSize: 8 })),
        ...starredList.map((m, i) => { const t = m.type === "media" ? `[${kindLabel(m.media.kind)}] ${m.text || ""}` : m.text || (m.recovered ? m.recovered.text : ""); const tt = M(t).replace(/\s+/g, " "); return [{ text: `${P}-${i + 1}`, bold: true, fontSize: 8 }, { text: `${fmtDate(m.ts)}\n${fmtTime(m.ts)} · #${m.id}`, fontSize: 7.5 }, { text: who(m), fontSize: 8 }, { text: tt.length > 110 ? tt.slice(0, 107) + "…" : tt, fontSize: 8 }]; })] },
        layout: { fillColor: r => r === 0 ? PC.brand : null, hLineWidth: (i, n) => i === 0 || i === n.table.body.length ? 0 : 0.5, hLineColor: () => PC.line, vLineWidth: () => 0, paddingTop: () => 4, paddingBottom: () => 4, paddingLeft: () => 5, paddingRight: () => 5 } });
      starredList.forEach((m, i) => {
        const blk = [];
        blk.push({ table: { widths: ["*", "auto"], body: [[{ text: `ANNEXURE ${P}-${i + 1}`, bold: true, color: "#ffffff", fontSize: 12 }, { text: `Message #${m.id}`, color: "#ffffff", fontSize: 9, alignment: "right", margin: [0, 2, 0, 0] }]] }, layout: { fillColor: () => PC.brand, hLineWidth: () => 0, vLineWidth: () => 0, paddingLeft: () => 8, paddingRight: () => 8, paddingTop: () => 6, paddingBottom: () => 6 }, margin: [0, 0, 0, 8] });
        blk.push({ table: { widths: [90, "*"], body: [kv("From", who(m) === "You" ? M(m.sender) : who(m)), kv("Date and time", `${new Date(m.ts).toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}, ${fmtTime(m.ts)} (IST)`), kv("Chat", `${M(chat.title)}`), ...(flags(m).filter(f => f[0] !== "STARRED").length ? [kv("Status", flags(m).filter(f => f[0] !== "STARRED").map(f => f[0].toLowerCase()).join(", "))] : [])] }, layout: { hLineWidth: (i, n) => i === n.table.body.length ? 0.5 : 0, hLineColor: () => PC.line, vLineWidth: () => 0, paddingLeft: () => 0, paddingTop: () => 2, paddingBottom: () => 2 }, margin: [0, 0, 0, 10] });
        if (m.type === "deleted") blk.push({ text: "This message was deleted", italics: true, color: PC.muted });
        if (m.type === "omitted") blk.push({ text: "Media not included in this export", italics: true, color: PC.muted });
        if (m.type === "media") { const im = m.media.file && imgs[m.media.file]; if (im) blk.push({ image: im.url, fit: [420, 420], alignment: "center", margin: [0, 2, 0, 8] }); if (m.media.file) { const f = chat.media.get(m.media.file); blk.push({ text: `${kindLabel(m.media.kind)}: ${M(f.name)} · ${fmtBytes(f.size)}\nSHA-256 ${f.hash}`, fontSize: 8, color: PC.brand, margin: [0, 0, 0, 6] }); } else blk.push(attLine(m)); }
        if (m.text && !["deleted", "omitted"].includes(m.type)) blk.push({ text: pdfRich(mask(m.text, chat)), fontSize: 11, lineHeight: 1.3 });
        if (m.recovered) blk.push({ text: [{ text: "Original text (recovered from the " + srcLabel(chat, m.recovered.src) + "): ", bold: true, color: PC.warn }, ...pdfRich(mask(m.recovered.text || m.recovered.media?.name || "", chat))], fontSize: 10.5, margin: [0, 6, 0, 0] });
        if (m.history) m.history.forEach(x => blk.push({ text: [{ text: "Earlier version: ", color: PC.muted }, { text: M(x.text), color: PC.muted }], fontSize: 9, margin: [0, 4, 0, 0] }));
        if (noteOf(m)) blk.push({ table: { widths: ["*"], body: [[{ text: [{ text: "Note: ", bold: true, color: PC.brand }, { text: M(noteOf(m)) }], fontSize: 9 }]] }, layout: { fillColor: () => "#fffbe6", hLineWidth: () => 0, vLineWidth: () => 0, paddingLeft: () => 6, paddingTop: () => 4, paddingBottom: () => 4 }, margin: [0, 10, 0, 0] });
        blk.push({ text: pdfClean(citationFor(chat, m)).replace("\n", " "), fontSize: 7.2, color: PC.faint, margin: [0, 12, 0, 0] });
        C.push({ stack: blk, pageBreak: opts.perPage === false ? undefined : "before", margin: opts.perPage === false ? [0, 18, 0, 0] : [0, 0, 0, 0], unbreakable: opts.perPage === false });
      });
    } else {
    const head = [["#", "Time", "From", "Message"].map(t => ({ text: t, bold: true, color: "#ffffff", fontSize: 8 }))];
    const body = [...head]; let day = null;
    for (const m of chat.messages) {
      const d = isoDay(m.ts);
      if (d !== day) { body.push([{ text: new Date(m.ts).toLocaleDateString("en-IN", { weekday: "long", day: "2-digit", month: "long", year: "numeric" }).toUpperCase(), colSpan: 4, alignment: "center", bold: true, fontSize: 7.5, color: "#54656f", fillColor: PC.band }, {}, {}, {}]); day = d; }
      if (m.type === "system") { body.push([{ text: String(m.id), color: PC.faint, fontSize: 7.5 }, { text: fmtTime(m.ts), fontSize: 8, color: PC.muted }, { text: "", }, { text: M(m.text), italics: true, color: PC.muted, fontSize: 8 }]); continue; }
      const cell = [];
      const fl = flags(m);
      if (m.type === "deleted") cell.push({ text: [{ text: "This message was deleted", italics: true, color: PC.muted }] });
      else if (m.type === "omitted") cell.push({ text: `${m.text === "media" ? "Media" : m.text[0].toUpperCase() + m.text.slice(1)} not included (exported without media)`, italics: true, color: PC.muted });
      else if (m.type === "media") { cell.push(attLine(m)); const im = m.media.file && imgs[m.media.file]; if (im) cell.push({ image: im.url, fit: [150, 110], margin: [0, 3, 0, 2] }); }
      if (m.text && !["deleted", "omitted"].includes(m.type)) cell.push({ text: pdfRich(mask(m.text, chat)) });
      if (m.recovered) cell.push({ text: [{ text: "Original (recovered): ", bold: true, color: PC.warn }, ...pdfRich(mask(m.recovered.text || m.recovered.media?.name || "", chat))], margin: [0, 2, 0, 0] });
      if (m.history) m.history.forEach(x => cell.push({ text: [{ text: "Earlier version: ", color: PC.muted }, { text: M(x.text), color: PC.muted }], fontSize: 8, margin: [0, 2, 0, 0] }));
      if (noteOf(m)) cell.push({ text: [{ text: "Note: ", bold: true, color: PC.brand }, { text: M(noteOf(m)) }], fontSize: 8, margin: [0, 2, 0, 0] });
      if (fl.length) cell.push({ text: fl.map(([t, c]) => ({ text: ` ${t} `, color: c, bold: true, fontSize: 6.5, background: c === PC.danger ? PC.dangerBg : c === PC.brand ? "#dcefe8" : PC.warnBg })).flatMap((x, i) => i ? [{ text: "  " }, x] : [x]), margin: [0, 2, 0, 0] });
      body.push([{ text: String(m.id), color: PC.faint, fontSize: 7.5 }, { text: fmtTime(m.ts), fontSize: 8 }, { text: who(m), bold: true, fontSize: 8 }, { stack: cell }]);
    }
    C.push({ table: { headerRows: 1, widths: [24, 44, 82, "*"], body, dontBreakRows: true }, layout: { fillColor: r => r === 0 ? PC.brand : null, hLineWidth: (i, n) => i === 0 || i === n.table.body.length ? 0 : 0.5, hLineColor: () => PC.line, vLineWidth: () => 0, paddingTop: () => 4, paddingBottom: () => 4, paddingLeft: () => 5, paddingRight: () => 5 } });
    }
    // integrity statement, attachment fingerprints, signature
    C.push({ text: "Integrity statement", fontSize: 14, bold: true, color: PC.brand, pageBreak: "before", margin: [0, 0, 0, 8] });
    C.push({ text: pdfClean(certificateText(chat)), font: "Roboto", fontSize: 7, lineHeight: 1.25, color: "#3b4a52" });
    const atts = (isBundle ? starredList : chat.messages).filter(m => m.media?.file);
    if (atts.length) {
      C.push({ text: "Attachment fingerprints", fontSize: 12, bold: true, color: PC.brand, margin: [0, 16, 0, 6] });
      C.push({ table: { headerRows: 1, widths: [24, 70, "*", 150], body: [["#", "Sent", "File", "SHA-256"].map(t => ({ text: t, bold: true, color: "#ffffff", fontSize: 7.5 })), ...atts.map(m => { const f = chat.media.get(m.media.file); return [{ text: String(m.id), fontSize: 7 }, { text: `${fmtDate(m.ts)}\n${who(m)}`, fontSize: 7 }, { text: M(f.name), fontSize: 7 }, { text: f.hash, fontSize: 6.3 }]; })] },
        layout: { fillColor: r => r === 0 ? PC.brand : null, hLineWidth: (i, n) => i === 0 || i === n.table.body.length ? 0 : 0.5, hLineColor: () => PC.line, vLineWidth: () => 0, paddingTop: () => 3, paddingBottom: () => 3 } });
    }
    C.push({ margin: [0, 40, 0, 0], unbreakable: true, stack: [{ text: isBundle ? "Certified that the annexures above are true reproductions of messages from the electronic record(s) identified on the cover page, whose SHA-256 values were computed at the time of import." : "Certified that this transcript was generated from the electronic record(s) identified above, whose SHA-256 values were computed at the time of import.", fontSize: 8, color: PC.muted, margin: [0, 0, 0, 34] },
      { columns: ["Signature", "Name and designation", "Date and place"].map(t => ({ stack: [{ canvas: [{ type: "line", x1: 0, y1: 0, x2: 150, y2: 0, lineWidth: 0.6, lineColor: "#54656f" }] }, { text: t, fontSize: 8, color: PC.muted, margin: [0, 3, 0, 0] }] })), columnGap: 20 }] });
  }
  onProgress?.("Writing PDF…");
  const fonts = pdfFonts(JSON.stringify(doc.content).match(INDIC_RE) || JSON.stringify(header(1)).match(INDIC_RE));
  if (fonts.NotoGuj || fonts.NotoDeva) { doc.content = indicize(doc.content); const h0 = doc.header, f0 = doc.footer; doc.header = (c, t) => indicize(h0(c, t)); doc.footer = (c, t) => indicize(f0(c, t)); }
  return new Promise((res, rej) => { try { pdfMake.createPdf(doc, null, fonts).getBlob(b => res(b)); } catch (e) { rej(e); } });
}
function hslHex(hh, s, l) { s /= 100; l /= 100; const k = n => (n + hh / 30) % 12, a = s * Math.min(l, 1 - l); const f = n => Math.round(255 * (l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1))))); return "#" + [f(0), f(8), f(4)].map(x => x.toString(16).padStart(2, "0")).join(""); }

function savedName(chat, m) {
  const d = new Date(m.ts); const stamp = `${isoDay(m.ts)}_${pad(d.getHours())}${pad(d.getMinutes())}`;
  const f = chat.media.get(m.media.file);
  return `${stamp}_${slug(mask(m.sender, chat))}_${mask(f.name, chat).replace(/^\d{8}-/, "")}`;
}
const FOLDER = { image: "Photos", sticker: "Photos", video: "Videos", audio: "Audio", doc: "Documents", contact: "Contacts" };
function certificateText(chat) {
  const first = chat.messages[0], last = chat.messages[chat.messages.length - 1];
  const red = R || {};
  const st = chat.sources.length > 1 ? changeStats(chat) : null;
  return [
    "ELECTRONIC RECORD INTEGRITY STATEMENT", "=".repeat(38), "",
    `Chat: ${mask(chat.title, chat)}`,
    `Tags: ${(chat.tags || []).join(", ") || "none"}`,
    ...(chat.matter?.client ? [`Client: ${chat.matter.client}`] : []),
    ...(chat.matter?.matter || chat.matter?.fy || chat.matter?.ref ? [`Matter: ${[chat.matter.matter, chat.matter.fy && "FY " + chat.matter.fy, chat.matter.ref && "Ref " + chat.matter.ref].filter(Boolean).join(" · ")}`] : []),
    `Source exports: ${chat.sources.length}`,
    ...chat.sources.flatMap((s, i) => [
      `  [${i + 1}] ${mask(s.name, chat)}`, `      Size: ${s.size.toLocaleString("en-IN")} bytes   Format: WhatsApp ${s.format}   Messages: ${s.count}`,
      `      Period: ${fmtDT(s.first)} to ${fmtDT(s.last)}`, `      SHA-256: ${s.hash}`, `      Imported: ${fmtDT(s.importedAt)} by user "${s.importedBy}"`]),
    `Period covered: ${first ? fmtDT(first.ts) : "-"} to ${last ? fmtDT(last.ts) : "-"}`,
    ...(chat.range ? [`Selection: messages dated ${chat.range.from} to ${chat.range.to} only (${chat.messages.length} of ${chat.range.total}). Message numbers are those of the complete chat; source hashes refer to the complete exports.`] : []),
    `Messages: ${chat.messages.length}   Participants: ${chat.participants.length}   Files in exports: ${chat.fileHashes.length}`,
    `Attachments linked: ${chat.linked}   Referenced but missing: ${chat.missing}`,
    ...(st ? [`Changes between exports: ${st.recovered} deleted later (recovered), ${st.edited} edited later, ${st.gone} missing from a later export`] : []),
    `Archive generated: ${fmtDT(Date.now())} by user "${S.user.username}" (${ROLES[S.user.role].label}) using ChatVault ${VERSION}`,
    `Redaction: ${[red.contacts ? "phone numbers and emails masked" : "", red.names ? "participant names replaced" : ""].filter(Boolean).join("; ") || "none"}`, "",
    "SHA-256 values of every file in the source exports:", ...chat.fileHashes.map(f => `  ${f.hash}  ${mask(f.name, chat)} (${f.size} bytes)`), "",
    "Hash values were computed on the device at the time of import. Any change to a file changes its value.",
    "This statement supports, and does not replace, the certificate required for electronic records",
    "under Section 63 of the Bharatiya Sakshya Adhiniyam, 2023."
  ].join("\n");
}
async function blobToDataURL(b) { return new Promise(r => { const fr = new FileReader(); fr.onload = () => r(fr.result); fr.readAsDataURL(b); }); }
async function buildArchiveHTML(chat, { embed, relPath }) {
  const urls = {};
  if (embed) { for (const [n, f] of chat.media) urls[n] = await blobToDataURL(f.blob.type ? f.blob : new Blob([f.blob], { type: mimeOf(f.name) })); }
  const body = threadHTML(chat, { src: n => embed ? urls[n] : relPath(n), me: chat.me, isGroup: chat.isGroup, archive: true });
  const css = $("#cv-css").textContent;
  const first = chat.messages[0], last = chat.messages[chat.messages.length - 1];
  const title = mask(chat.title, chat);
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(title)} · WhatsApp archive</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700&family=JetBrains+Mono&display=swap"><style>${css}
body{overflow:auto;height:auto} .arch{max-width:1000px;margin:0 auto;background:var(--chat-bg);position:relative;min-height:100vh}
.arch::before{content:"";position:absolute;inset:0;background:var(--doodle);-webkit-mask:var(--doodle-svg) 0 0/180px 180px;mask:var(--doodle-svg) 0 0/180px 180px;pointer-events:none}
.arch .thread{position:relative;padding-block:12px 40px} .cert{background:var(--panel);margin:0;padding:20px 24px;border-bottom:1px solid var(--line);position:relative}
.cert pre{white-space:pre-wrap;font-family:var(--font-mono);font-size:11.5px;color:var(--fg-2);margin:12px 0 0;max-height:220px;overflow:auto}
.top{position:sticky;top:0;z-index:5;display:flex;gap:12px;align-items:center;padding:10px 16px;background:var(--panel-2);border-bottom:1px solid var(--line)}
.top b{font-size:16px;font-weight:500} .top span{font-size:12.5px;color:var(--fg-2)} .day{content-visibility:visible}
.voice .play,.m-doc{cursor:default} .hist summary{cursor:pointer} @media print{.top{position:static}.cert pre{max-height:none}.day-chip{position:static}.msg{break-inside:avoid}}
</style></head><body><div class="arch"><div class="top"><span class="avatar sm" style="--h:${chat.h}">${esc(initials(title))}</span><div style="display:grid;min-width:0"><b>${esc(title)}</b><span>${first ? fmtDate(first.ts) : ""} – ${last ? fmtDate(last.ts) : ""} · ${chat.messages.length} messages · archived ${fmtDate(Date.now())}</span></div></div>
<details class="cert"><summary><b>Integrity statement</b> <span class="muted">· SHA-256 ${chat.zipHash.slice(0, 24)}…</span></summary><pre>${esc(certificateText(chat))}</pre></details>
<div class="thread">${body}</div></div>
<script>document.addEventListener("click",e=>{const v=e.target.closest(".voice");if(v&&e.target.closest("[data-act=play]")){let a=v._a||(v._a=new Audio(v.dataset.src));a.paused?a.play():a.pause();}
const i=e.target.closest(".m-img img");if(i){const w=document.createElement("div");w.style.cssText="position:fixed;inset:0;background:rgba(0,0,0,.85);display:grid;place-items:center;z-index:99;cursor:zoom-out";w.innerHTML='<img style="max-width:95vw;max-height:95vh" src="'+i.src+'">';w.onclick=()=>w.remove();document.body.append(w);}
const d=e.target.closest(".m-doc");if(d&&d.dataset.href){window.open(d.dataset.href,"_blank");}});<\/script></body></html>`;
}
function mimeOf(n) { const e = extOf(n); return ({ jpg: "image/jpeg", jpeg: "image/jpeg", png: "image/png", webp: "image/webp", gif: "image/gif", mp4: "video/mp4", opus: "audio/ogg", ogg: "audio/ogg", m4a: "audio/mp4", mp3: "audio/mpeg", pdf: "application/pdf" })[e] || "application/octet-stream"; }
const statusOf = (chat, m) => [m.recovered ? "Deleted later; original recovered" : "", m.history ? "Edited later" : "", m.goneIn != null ? "Missing from later export" : "", m.newIn > 0 ? "New in later export" : ""].filter(Boolean).join("; ");
async function buildXLSX(chat) {
  await libs.xlsx();
  const M = s => mask(s || "", chat);
  const rows = chat.messages.map(m => ({
    "No.": m.id, Date: isoDay(m.ts), Time: fmtTime(m.ts), Sender: m.sender ? M(m.sender) : "(system)",
    Type: m.type === "media" ? m.media.kind : m.type, Message: M(m.text),
    "Recovered original": m.recovered ? M(m.recovered.text || m.recovered.media?.name || "") : "",
    "Earlier version": m.history ? M(m.history.map(x => x.text).join(" | ")) : "",
    Attachment: m.media ? M(m.media.file ? chat.media.get(m.media.file).name : m.media.name) : "",
    "Saved as": m.media?.file ? `Media/${FOLDER[m.media.kind] || "Other"}/${savedName(chat, m)}` : "",
    "Attachment SHA-256": m.media?.file ? chat.media.get(m.media.file).hash : "", Edited: m.edited ? "Yes" : "", "Change status": statusOf(chat, m),
    Starred: chat.stars?.[m.key] ? "Yes" : "", "Note": M(chat.mnotes?.[m.key] || ""), Citation: citationFor(chat, m).replace("\n", " ")
  }));
  const files = chat.fileHashes.map(f => ({ File: M(f.name), "Size (bytes)": f.size, "SHA-256": f.hash }));
  const parts = chat.participants.map(p => ({ Participant: M(p.name), Messages: p.n, Attachments: chat.messages.filter(m => m.sender === p.name && m.type === "media").length }));
  const mt = chat.matter || {};
  const matterRows = [["Client", mt.client], ["PAN", mt.pan], ["GSTIN", mt.gstin], ["Matter", mt.matter], ["Financial year", mt.fy], ["Reference", mt.ref]].filter(r => r[1]);
  const srcs = chat.sources.map((s, i) => ({ "No.": i + 1, Export: M(s.name), Format: s.format, From: fmtDT(s.first), To: fmtDT(s.last), Messages: s.count, "Size (bytes)": s.size, "SHA-256": s.hash, Imported: fmtDT(s.importedAt), "Imported by": s.importedBy }));
  const wb = XLSX.utils.book_new();
  const ws1 = XLSX.utils.json_to_sheet(rows); ws1["!cols"] = [{ wch: 6 }, { wch: 11 }, { wch: 9 }, { wch: 22 }, { wch: 9 }, { wch: 70 }, { wch: 40 }, { wch: 40 }, { wch: 34 }, { wch: 50 }, { wch: 66 }, { wch: 7 }, { wch: 30 }, { wch: 8 }, { wch: 40 }, { wch: 60 }]; ws1["!autofilter"] = { ref: ws1["!ref"] };
  XLSX.utils.book_append_sheet(wb, ws1, "Messages");
  const ws2 = XLSX.utils.json_to_sheet(parts); ws2["!cols"] = [{ wch: 28 }, { wch: 10 }, { wch: 12 }]; XLSX.utils.book_append_sheet(wb, ws2, "Participants");
  const ws5 = XLSX.utils.json_to_sheet(srcs); ws5["!cols"] = [{ wch: 5 }, { wch: 46 }, { wch: 9 }, { wch: 22 }, { wch: 22 }, { wch: 10 }, { wch: 12 }, { wch: 66 }, { wch: 22 }, { wch: 12 }]; XLSX.utils.book_append_sheet(wb, ws5, "Source exports");
  const ws3 = XLSX.utils.json_to_sheet(files); ws3["!cols"] = [{ wch: 48 }, { wch: 12 }, { wch: 66 }]; XLSX.utils.book_append_sheet(wb, ws3, "File fingerprints");
  if (matterRows.length) { const wsm = XLSX.utils.aoa_to_sheet([["Field", "Value"], ...matterRows]); wsm["!cols"] = [{ wch: 16 }, { wch: 60 }]; XLSX.utils.book_append_sheet(wb, wsm, "Client and matter"); }
  if ((chat.events || []).length) { const wse = XLSX.utils.json_to_sheet(chat.events.map(e => ({ When: fmtDT(e.t), User: e.user, Event: e.action, Detail: M(e.detail), "SHA-256": e.hash }))); wse["!cols"] = [{ wch: 22 }, { wch: 12 }, { wch: 28 }, { wch: 60 }, { wch: 66 }]; XLSX.utils.book_append_sheet(wb, wse, "Chain of custody"); }
  const ws4 = XLSX.utils.aoa_to_sheet(certificateText(chat).split("\n").map(l => [l])); ws4["!cols"] = [{ wch: 110 }]; XLSX.utils.book_append_sheet(wb, ws4, "Integrity statement");
  return new Blob([XLSX.write(wb, { type: "array", bookType: "xlsx" })], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
}
async function buildZip(chat, opts = {}, onProgress) {
  await libs.zip();
  const z = new JSZip(); const root = z.folder(slug(mask(chat.title, chat)) + "_archive");
  const pathOf = {}; const sums = []; const outputs = [];
  for (const m of chat.messages) if (m.type === "media" && m.media.file && !pathOf[m.media.file]) {
    const f = chat.media.get(m.media.file); const p = `Media/${FOLDER[m.media.kind] || "Other"}/${savedName(chat, m)}`;
    pathOf[m.media.file] = p; root.file(p, f.blob); sums.push(`${f.hash}  ${p}`);
  }
  for (const [n, f] of chat.media) if (!pathOf[n]) { const p = `Media/Unreferenced/${mask(f.name, chat)}`; pathOf[n] = p; root.file(p, f.blob); sums.push(`${f.hash}  ${p}`); }
  const put = async (name, data) => { root.file(name, data); outputs.push(`${await sha256(data instanceof Blob ? data : data)}  ${name}`); };
  await put("Open chat.html", await buildArchiveHTML(chat, { embed: false, relPath: n => encodeURI(pathOf[n]) }));
  await put("Index.xlsx", await buildXLSX(chat));
  if (chat.range) await put(`Transcript ${chat.range.from} to ${chat.range.to}.txt`, rangeTranscript(chat));
  else for (const [i, s] of chat.sources.entries()) await put(chat.sources.length > 1 ? `Original transcripts/${i + 1} - ${slug(mask(s.name, chat))}.txt` : "Original transcript.txt", mask(s.rawText, chat));
  onProgress?.("Building evidence PDF…"); await put("Transcript (evidence).pdf", await buildPDF(chat, "evidence", opts, onProgress));
  if (opts.both !== false) { onProgress?.("Building chat-view PDF…"); await put("Transcript (chat view).pdf", await buildPDF(chat, "chat", opts, onProgress)); }
  if (chat.messages.some(m => chat.stars?.[m.key])) { onProgress?.("Building evidence bundle…"); await put("Evidence bundle (starred).pdf", await buildPDF(chat, "bundle", opts, onProgress)); }
  onProgress?.("Compressing archive…");
  await put("INTEGRITY STATEMENT.txt", certificateText(chat));
  const sumsTxt = `# SHA-256 of media files as placed in this archive (same bytes as in the original export)\n${sums.join("\n")}\n\n# Source export files\n${chat.sources.map(s => `${s.hash}  ${mask(s.name, chat)}`).join("\n")}\n`;
  await put("SHA256SUMS.txt", sumsTxt);
  root.file("OUTPUT HASHES.txt", `# SHA-256 of the files ChatVault generated for this archive, recorded at ${fmtDT(Date.now())}.\n# A file cannot contain its own hash, so these values are kept here, beside them.\n# Verify with:  sha256sum -c "OUTPUT HASHES.txt"   (Windows: certutil -hashfile <file> SHA256)\n${outputs.join("\n")}\n`);
  return z.generateAsync({ type: "blob", compression: "DEFLATE", compressionOptions: { level: 6 } });
}

/* ============================================================ Section 63 certificate (draft .docx) */
function openCertificate(chat, view) {
  if (!can("export")) return;
  view = view || chat;
  const key = "cv.cert." + S.user.username; const prev = sget(key, {});
  const DEV = ["Computer/Storage Media", "DVR", "Mobile", "Flash Drive", "CD/DVD", "Server", "Cloud", "Other"];
  const REL = ["Owned", "Maintained", "Managed", "Operated"];
  const d = Object.assign({ name: S.user.name, relation: "", address: "", device: ["Mobile"], devOther: "", make: "", colour: "", serial: "", imei: "", rel: ["Owned", "Operated"], place: "" }, prev);
  const ov = h(`<div class="overlay"><form class="modal wide" role="dialog" aria-modal="true" aria-labelledby="ceT" novalidate><div class="modal-head"><h3 id="ceT">Section 63 certificate · draft</h3><button class="icon-btn" type="button" data-x aria-label="Close">${ic("close")}</button></div>
    <div class="modal-body">
      <p class="muted" style="margin:0">Prepares the certificate in the form of the Schedule to the Bharatiya Sakshya Adhiniyam, 2023 as an editable Word file. Part A is pre-filled with the SHA-256 values of ${view.sources.length > 1 ? `all ${view.sources.length} exports` : "the export"} and a hash report is attached as Annexure H-1. Part B is left blank for the expert. Fields left empty here appear as blanks to fill by hand.</p>
      <div class="steps" style="gap:10px"><b>Person giving Part A</b><div class="form-row">
        <div class="field"><label for="ceName">Name</label><input class="input" id="ceName" value="${esc(d.name)}"></div>
        <div class="field"><label for="ceRel">Son / daughter / spouse of</label><input class="input" id="ceRel" value="${esc(d.relation)}" placeholder="e.g. son of Himanshu Vasani"></div></div>
        <div class="field"><label for="ceAddr">Residing at / employed at</label><input class="input" id="ceAddr" value="${esc(d.address)}"></div></div>
      <div class="steps" style="gap:10px"><b>Device the chat was exported from</b>
        <div class="tick-row">${DEV.map(x => `<label class="check"><input type="checkbox" name="dev" value="${x}"${d.device.includes(x) ? " checked" : ""}><span>${x}</span></label>`).join("")}</div>
        <div class="form-row"><div class="field"><label for="ceMake">Make and model</label><input class="input" id="ceMake" value="${esc(d.make)}" placeholder="e.g. Samsung Galaxy S24"></div>
          <div class="field"><label for="ceCol">Colour</label><input class="input" id="ceCol" value="${esc(d.colour)}"></div>
          <div class="field"><label for="ceSer">Serial number</label><input class="input" id="ceSer" value="${esc(d.serial)}"></div>
          <div class="field"><label for="ceImei">IMEI / UIN / UID / MAC / Cloud ID</label><input class="input" id="ceImei" value="${esc(d.imei)}"></div></div>
        <div class="field"><label>The device or source is, by me</label><div class="tick-row">${REL.map(x => `<label class="check"><input type="checkbox" name="rel" value="${x}"${d.rel.includes(x) ? " checked" : ""}><span>${x}</span></label>`).join("")}</div></div>
        <div class="field"><label for="cePlace">Place</label><input class="input" id="cePlace" value="${esc(d.place)}" placeholder="e.g. Mumbai" style="max-width:260px"></div></div>
      <p class="note" style="margin:0">ChatVault does not sign anything. Review the draft against the official Schedule, complete it, and sign it yourself. The expert completes Part B after verifying the hash values independently.</p>
      <div class="err" id="ceErr"></div></div>
    <div class="modal-foot"><button class="btn btn-ghost" type="button" data-x>Cancel</button><button class="btn btn-primary" type="submit">${ic("cert")}Create Word draft</button></div></form></div>`);
  document.body.append(ov); $$("[data-x]", ov).forEach(b => b.onclick = () => ov.remove());
  $("form", ov).onsubmit = async e => {
    e.preventDefault();
    const v = id => $(id, ov).value.trim();
    const data = { name: v("#ceName"), relation: v("#ceRel"), address: v("#ceAddr"), device: $$('input[name=dev]:checked', ov).map(x => x.value), make: v("#ceMake"), colour: v("#ceCol"), serial: v("#ceSer"), imei: v("#ceImei"), rel: $$('input[name=rel]:checked', ov).map(x => x.value), place: v("#cePlace") };
    sset(key, data);
    try {
      const blob = await buildCertDocx(view, data);
      const name = `${slug(chat.title)}_Section-63-certificate_DRAFT.docx`;
      const hash = await sha256(blob);
      if (await saveFile(name, blob)) { audit("Drafted Section 63 certificate", `${chat.title} · ${name} · SHA-256 ${hash}`); logEvent(chat, "Section 63 certificate drafted", name, hash); }
      ov.remove();
    } catch (x) { console.error(x); $("#ceErr", ov).textContent = "Could not create the draft: " + (x.message || x); }
  };
}
async function buildCertDocx(chat, d) {
  await libs.zip();
  const X = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const BL = "______________________________";
  const run = (t, o = {}) => `<w:r><w:rPr>${o.font ? `<w:rFonts w:ascii="${o.font}" w:hAnsi="${o.font}" w:cs="${o.font}"/>` : ""}${o.b ? "<w:b/>" : ""}${o.i ? "<w:i/>" : ""}${o.color ? `<w:color w:val="${o.color}"/>` : ""}${o.sz ? `<w:sz w:val="${o.sz}"/><w:szCs w:val="${o.sz}"/>` : ""}${o.u ? '<w:u w:val="single"/>' : ""}</w:rPr>${String(t).split("\n").map((l, i) => (i ? "<w:br/>" : "") + `<w:t xml:space="preserve">${X(l)}</w:t>`).join("")}</w:r>`;
  const P = (runs, o = {}) => `<w:p><w:pPr>${o.pb ? "<w:pageBreakBefore/>" : ""}${o.keep ? "<w:keepNext/>" : ""}<w:spacing w:before="${o.before || 0}" w:after="${o.after ?? 90}" w:line="${o.line || 252}" w:lineRule="auto"/>${o.ind ? `<w:ind w:left="${o.ind}" w:hanging="${o.hang || 0}"/>` : ""}<w:jc w:val="${o.align || "both"}"/></w:pPr>${[].concat(runs).map(r => r.startsWith("<w:r>") ? r : run(r)).join("")}</w:p>`;
  const box = (on) => run(on ? "☑" : "☐", { font: "Segoe UI Symbol" });
  const ticks = (opts, sel) => opts.flatMap((o, i) => [box(sel.includes(o)), run(` ${o}${i < opts.length - 1 ? "     " : ""}`)]);
  const cell = (content, w, o = {}) => `<w:tc><w:tcPr><w:tcW w:w="${w}" w:type="dxa"/>${o.fill ? `<w:shd w:val="clear" w:color="auto" w:fill="${o.fill}"/>` : ""}</w:tcPr>${[].concat(content).map(c => c.startsWith("<w:p>") ? c : P(run(c, { sz: o.sz || 18, b: o.b, font: o.mono ? "Consolas" : undefined, color: o.color }), { after: 0, line: 240, align: "left" })).join("")}</w:tc>`;
  const table = (rows, widths, head) => `<w:tbl><w:tblPr><w:tblW w:w="${widths.reduce((a, b) => a + b, 0)}" w:type="dxa"/><w:tblBorders>${["top", "left", "bottom", "right", "insideH", "insideV"].map(s => `<w:${s} w:val="single" w:sz="4" w:space="0" w:color="A6B3B0"/>`).join("")}</w:tblBorders><w:tblCellMar><w:top w:w="50" w:type="dxa"/><w:left w:w="90" w:type="dxa"/><w:bottom w:w="50" w:type="dxa"/><w:right w:w="90" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>${widths.map(w => `<w:gridCol w:w="${w}"/>`).join("")}</w:tblGrid>
    ${head ? `<w:tr><w:trPr><w:tblHeader/></w:trPr>${head.map((t, i) => cell(t, widths[i], { b: true, fill: "E3EFEC" })).join("")}</w:tr>` : ""}${rows.map(r => `<w:tr><w:trPr><w:cantSplit/></w:trPr>${r.map((c, i) => cell(c.t ?? c, widths[i], c)).join("")}</w:tr>`).join("")}</w:tbl>`;
  const first = chat.messages[0], last = chat.messages[chat.messages.length - 1];
  const omitted = chat.messages.filter(m => m.type === "omitted").length;
  const mt = chat.matter || {};
  const srcRows = chat.sources.map((s, i) => [String(i + 1), { t: s.name, sz: 17 }, { t: s.size.toLocaleString("en-IN") + " bytes", sz: 17 }, { t: s.hash, mono: true, sz: 16 }]);
  const other = `WhatsApp ${chat.isGroup ? "group" : "chat"} “${chat.title}”, exported from the WhatsApp application on the above device using its “Export chat” feature${omitted || chat.noMedia ? " (without media)" : " (with media)"}, as the file(s) listed in paragraph 4 below. The record contains ${chat.messages.length} messages dated ${fmtDT(first.ts)} to ${fmtDT(last.ts)}${chat.range ? ` (selected period of a chat of ${chat.range.total} messages)` : ""}.${mt.client ? ` Client: ${mt.client}${mt.matter ? `; matter: ${mt.matter}` : ""}${mt.ref ? `; reference: ${mt.ref}` : ""}.` : ""}`;
  const sig = (label) => [
    P([run("\n" + BL), run(`\n(${label})`, { i: true })], { before: 120, align: "right", after: 60, keep: true }),
    P([run("Date (DD/MM/YYYY): "), run("____/____/________")], { align: "left", after: 40, keep: true }),
    P([run("Time (IST): "), run("________"), run(" hours (in 24-hour format)")], { align: "left", after: 40, keep: true }),
    P([run("Place: "), run(d.place || BL)], { align: "left" })
  ].join("");
  const body = [
    P(run("DRAFT prepared with ChatVault on " + fmtDT(Date.now()) + ". Check every paragraph against the Schedule to the Bharatiya Sakshya Adhiniyam, 2023, complete the blanks, then delete this line before signing.", { i: true, sz: 17, color: "B42318" }), { align: "left", after: 240 }),
    P(run("THE SCHEDULE", { b: true, sz: 24 }), { align: "center", after: 40 }),
    P(run("[See section 63(4)(c)]", { sz: 20 }), { align: "center", after: 40 }),
    P(run("CERTIFICATE", { b: true, sz: 26 }), { align: "center", after: 240 }),
    P(run("PART A", { b: true, sz: 22 }), { align: "center", after: 20 }),
    P(run("(To be filled by the Party)", { i: true }), { align: "center", after: 240 }),
    P([run("I, "), run(d.name || BL, { b: !!d.name }), run(` ${d.relation || "(son/daughter/spouse of) " + BL}, residing/employed at `), run(d.address || BL), run(" do hereby solemnly affirm and sincerely state and submit as follows:")]),
    P([run("1.  ", { b: true }), run("I have produced electronic record/output of the digital record taken from the following device/digital record source (tick mark):")], { ind: 360, hang: 360 }),
    P([...ticks(["Computer/Storage Media", "DVR", "Mobile", "Flash Drive"], d.device)], { ind: 360, align: "left", after: 60 }),
    P([...ticks(["CD/DVD", "Server", "Cloud", "Other"], d.device), run("   Other: " + (d.device.includes("Other") ? "" : "") + BL.slice(0, 18))], { ind: 360, align: "left" }),
    P([run("Make & Model: "), run(d.make || BL.slice(0, 20)), run("     Colour: "), run(d.colour || BL.slice(0, 12)), run("     Serial Number: "), run(d.serial || BL.slice(0, 18))], { ind: 360, align: "left" }),
    P([run("IMEI/UIN/UID/MAC/Cloud ID: "), run(d.imei || BL), run(" (as applicable) and any other relevant information, if any, about the device/digital record: "), run(other)], { ind: 360 }),
    P([run("2.  ", { b: true }), run("The digital device or the digital record source was under the lawful control for regularly creating, storing or processing information for the purposes of carrying out regular activities and during this period, the computer or the communication device was working properly and the relevant information was regularly fed into the computer during the ordinary course of business. If the computer/digital device at any point of time was not working properly or out of operation, then it has not affected the electronic/digital record or its accuracy.")], { ind: 360, hang: 360 }),
    P([run("3.  ", { b: true }), run("The digital device or the source of the digital record is:   "), ...ticks(["Owned", "Maintained", "Managed", "Operated"], d.rel), run("   by me (select as applicable).")], { ind: 360, hang: 360 }),
    P([run("4.  ", { b: true }), run("I state that the HASH value(s) of the electronic/digital record(s) is/are as follows:")], { ind: 360, hang: 360, keep: true }),
    table(srcRows, [500, 3700, 1500, 3938], ["No.", "Electronic record (file)", "Size", "SHA-256 hash value"]),
    P([run("obtained through the following algorithm:   "), ...ticks(["SHA1", "SHA256", "MD5"], ["SHA256"]), run("   "), box(false), run(" Other " + BL.slice(0, 12) + " (Legally acceptable standard)")], { before: 160, align: "left" }),
    P(run("(Hash report enclosed with this certificate as Annexure H-1.)", { i: true }), { align: "left", after: 0 }),
    sig("Name and signature"),
    P(run("PART B", { b: true, sz: 22 }), { align: "center", after: 20, pb: true }),
    P(run("(To be filled by the Expert)", { i: true }), { align: "center", after: 240 }),
    P([run("I, " + BL + " (son/daughter/spouse of) " + BL + ", residing/employed at " + BL + " do hereby solemnly affirm and sincerely state and submit as follows:")]),
    P([run("1.  ", { b: true }), run("The produced electronic record/output of the digital record are obtained from the following device/digital record source (tick mark):")], { ind: 360, hang: 360 }),
    P([...ticks(["Computer/Storage Media", "DVR", "Mobile", "Flash Drive"], [])], { ind: 360, align: "left", after: 60 }),
    P([...ticks(["CD/DVD", "Server", "Cloud", "Other"], []), run("   Other: " + BL.slice(0, 18))], { ind: 360, align: "left" }),
    P([run("Make & Model: " + BL.slice(0, 20) + "     Colour: " + BL.slice(0, 12) + "     Serial Number: " + BL.slice(0, 18))], { ind: 360, align: "left" }),
    P([run("IMEI/UIN/UID/MAC/Cloud ID: " + BL + " (as applicable) and any other relevant information, if any, about the device/digital record: " + BL + BL)], { ind: 360 }),
    P([run("2.  ", { b: true }), run("I state that the HASH value(s) of the electronic/digital record(s) is/are " + BL + BL + ", obtained through the following algorithm:")], { ind: 360, hang: 360 }),
    P([...ticks(["SHA1", "SHA256", "MD5"], []), run("   "), box(false), run(" Other " + BL.slice(0, 12) + " (Legally acceptable standard)")], { ind: 360, align: "left" }),
    P(run("(Hash report to be enclosed with the certificate)", { i: true }), { ind: 360, align: "left" }),
    sig("Name, designation and signature"),
    P(run("ANNEXURE H-1 — HASH REPORT", { b: true, sz: 24 }), { align: "center", pb: true, after: 80 }),
    P(run(`Electronic record: WhatsApp ${chat.isGroup ? "group" : "chat"} “${chat.title}”${mt.client ? ` · Client: ${mt.client}` : ""}`, { sz: 19 }), { align: "center", after: 240 }),
    P(run("1. Source export files", { b: true }), { align: "left", keep: true }),
    table(chat.sources.map((s, i) => [String(i + 1), { t: `${s.name}\nWhatsApp ${s.format} export · ${s.count} messages · ${fmtDate(s.first)} to ${fmtDate(s.last)}`, sz: 16 }, { t: `${s.hash}\nComputed ${fmtDT(s.importedAt)} by user “${s.importedBy}”`, mono: true, sz: 15 }]), [500, 3600, 5538], ["No.", "File", "SHA-256 and when it was computed"]),
    P(run("2. Files contained in the export(s)", { b: true }), { align: "left", before: 240, keep: true }),
    table(chat.fileHashes.map((f, i) => [String(i + 1), { t: f.name, sz: 16 }, { t: f.size.toLocaleString("en-IN"), sz: 16 }, { t: f.hash, mono: true, sz: 15 }]), [500, 3900, 1100, 4138], ["No.", "File", "Bytes", "SHA-256"]),
    ...(chat.events?.length ? [P(run("3. Chain of custody recorded by ChatVault", { b: true }), { align: "left", before: 240, keep: true }),
      table(chat.events.map(ev => [{ t: fmtDT(ev.t), sz: 16 }, { t: ev.user, sz: 16 }, { t: ev.action + (ev.detail ? "\n" + ev.detail : ""), sz: 16 }, { t: ev.hash ? ev.hash.split(" ").join("\n") : "", mono: true, sz: 14 }]), [1900, 1100, 3300, 3338], ["Date and time", "User", "Event", "SHA-256"])] : []),
    P(run(`${chat.events?.length ? "4" : "3"}. How to verify`, { b: true }), { align: "left", before: 240 }),
    P(run("Recompute the SHA-256 value of each source file and compare it with the values above. Windows: certutil -hashfile \"<file>\" SHA256   ·   macOS/Linux: shasum -a 256 \"<file>\". Identical values show the file is unchanged since it was hashed."), { align: "left" }),
    P(run(`Report generated by ChatVault ${VERSION} on ${fmtDT(Date.now())} by user “${S.user.username}”.`, { i: true, sz: 17, color: "667781" }), { align: "left", before: 200 })
  ].join("");
  const doc = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body>${body}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="964" w:right="1134" w:bottom="907" w:left="1134" w:header="567" w:footer="567" w:gutter="0"/></w:sectPr></w:body></w:document>`;
  const styles = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman" w:eastAsia="Times New Roman"/><w:sz w:val="22"/><w:szCs w:val="22"/><w:lang w:val="en-IN"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="288" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style></w:styles>`;
  const z = new JSZip();
  z.file("[Content_Types].xml", `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>`);
  z.file("_rels/.rels", `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/></Relationships>`);
  z.file("word/_rels/document.xml.rels", `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`);
  z.file("word/document.xml", doc); z.file("word/styles.xml", styles);
  z.file("docProps/core.xml", `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>${X("Section 63 certificate (draft) - " + chat.title)}</dc:title><dc:creator>${X(S.user.name)}</dc:creator><dcterms:created xsi:type="dcterms:W3CDTF">${new Date().toISOString().slice(0, 19)}Z</dcterms:created></cp:coreProperties>`);
  return z.generateAsync({ type: "blob", mimeType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" });
}

/* ============================================================ users & audit */
function openUsers(tab = "users") {
  if (!can("users") && !can("audit")) return;
  const ov = h(`<div class="overlay"><div class="modal wide" role="dialog" aria-modal="true" aria-labelledby="uT"><div class="modal-head"><h3 id="uT">Access control</h3><button class="icon-btn" data-x aria-label="Close">${ic("close")}</button></div>
    <div style="padding:0 20px 8px"><div class="seg"><button data-u="users">Users</button><button data-u="roles">Roles</button><button data-u="audit">Audit log</button><button data-u="settings">Settings</button></div></div>
    <div class="modal-body" id="uBody"></div></div></div>`);
  document.body.append(ov); $("[data-x]", ov).onclick = () => ov.remove();
  const show = k => { $$("[data-u]", ov).forEach(b => b.classList.toggle("on", b.dataset.u === k)); ({ users: uUsers, roles: uRoles, audit: uAudit, settings: uSettings })[k]($("#uBody", ov)); };
  $$("[data-u]", ov).forEach(b => b.onclick = () => show(b.dataset.u)); show(tab);
}
function uUsers(el) {
  const list = users();
  el.innerHTML = `<div class="tbl-wrap"><table><thead><tr><th>Name</th><th>Username</th><th>Role</th><th>Status</th><th>Last sign-in</th><th></th></tr></thead><tbody>
    ${list.map(u => `<tr data-id="${u.id}"><td>${esc(u.name)}${u.id === S.user.id ? ' <span class="faint">(you)</span>' : ""}</td><td class="mono">${esc(u.username)}</td>
      <td><select class="select" data-role${u.id === S.user.id ? " disabled" : ""} aria-label="Role">${Object.keys(ROLES).map(r => `<option value="${r}"${r === u.role ? " selected" : ""}>${ROLES[r].label}</option>`).join("")}</select></td>
      <td>${u.active ? '<span class="pill ok">Active</span>' : '<span class="pill off">Disabled</span>'}</td><td>${u.lastLogin ? fmtDT(u.lastLogin) : '<span class="faint">Never</span>'}</td>
      <td>${u.id === S.user.id ? "" : `<span class="inline-confirm"><button class="btn btn-ghost btn-sm" data-toggle>${u.active ? "Disable" : "Enable"}</button><button class="btn btn-ghost btn-sm" data-reset>Reset password</button><button class="icon-btn" data-del aria-label="Delete user">${ic("trash")}</button></span>`}</td></tr>`).join("")}</tbody></table></div>
    <form id="addU" class="steps" novalidate><b>Add a user</b><div class="form-row">
      <div class="field"><label for="nName">Full name</label><input class="input" id="nName" required></div>
      <div class="field"><label for="nUser">Username</label><input class="input" id="nUser" required autocomplete="off"></div>
      <div class="field"><label for="nPw">Temporary password</label><input class="input" id="nPw" type="text" required autocomplete="off" placeholder="8+ characters, letter and number"></div>
      <div class="field"><label for="nRole">Role</label><select class="select" id="nRole">${Object.keys(ROLES).map(r => `<option value="${r}"${r === "viewer" ? " selected" : ""}>${ROLES[r].label} — ${ROLES[r].desc}</option>`).join("")}</select></div></div>
      <div class="err" id="nErr"></div><div><button class="btn btn-primary btn-sm" type="submit">${ic("plus")}Add user</button></div></form>
    <p class="note" style="margin:0">Accounts and the audit log are stored in this browser. For a shared, multi-device deployment, connect a server-side identity provider.</p>`;
  const upd = (id, f) => { saveUsers(users().map(u => u.id === id ? f(u) : u)); };
  el.onchange = e => { const s = e.target.closest("[data-role]"); if (!s) return; const id = s.closest("tr").dataset.id; const u = users().find(x => x.id === id); upd(id, x => ({ ...x, role: s.value })); audit("Changed role", `${u.username}: ${u.role} → ${s.value}`); toast(`${u.username} is now ${ROLES[s.value].label}`); };
  el.onclick = async e => {
    const tr = e.target.closest("tr[data-id]"); if (!tr) return; const id = tr.dataset.id; const u = users().find(x => x.id === id);
    if (e.target.closest("[data-toggle]")) { upd(id, x => ({ ...x, active: !x.active })); audit(u.active ? "Disabled user" : "Enabled user", u.username); uUsers(el); }
    if (e.target.closest("[data-reset]")) { const pw = "Tmp" + Math.random().toString(36).slice(2, 7) + Math.floor(Math.random() * 90 + 10); const { salt, hash } = await pbkdf2(pw); const w = await wrapFor(pw); upd(id, x => ({ ...x, salt, hash, ...w })); audit("Reset password", u.username); const cell = e.target.closest("td"); cell.innerHTML = `<span class="inline-confirm"><span>New password: <b class="mono">${pw}</b></span><button class="icon-btn" data-copy="${pw}" aria-label="Copy">${ic("copy")}</button></span>`; }
    if (e.target.closest("[data-del]")) { const cell = e.target.closest("td"); cell.innerHTML = `<span class="inline-confirm"><span>Delete ${esc(u.username)}?</span><button class="btn btn-danger btn-sm" data-yes>Delete</button><button class="btn btn-ghost btn-sm" data-no>Keep</button></span>`; }
    if (e.target.closest("[data-yes]")) { saveUsers(users().filter(x => x.id !== id)); audit("Deleted user", u.username); uUsers(el); }
    if (e.target.closest("[data-no]")) uUsers(el);
    const c = e.target.closest("[data-copy]"); if (c) copyText(c.dataset.copy);
  };
  $("#addU").onsubmit = async e => {
    e.preventDefault(); $("#nErr").textContent = "";
    try { const u = await createUser({ name: $("#nName").value, username: $("#nUser").value, password: $("#nPw").value, role: $("#nRole").value }); audit("Created user", `${u.username} (${ROLES[u.role].label})`); toast(`Added ${u.username}`); uUsers(el); }
    catch (x) { $("#nErr").textContent = x.message; }
  };
}
function uRoles(el) {
  el.innerHTML = `<div class="tbl-wrap"><table class="matrix"><thead><tr><th>Permission</th>${Object.keys(ROLES).map(r => `<th>${ROLES[r].label}</th>`).join("")}</tr></thead><tbody>
    ${PERMS.map(([k, l]) => `<tr><td>${l}</td>${Object.keys(ROLES).map(r => GRANTS[r].includes(k) ? `<td class="yes">${ic("check")}</td>` : `<td class="no">–</td>`).join("")}</tr>`).join("")}</tbody></table></div>
    <div class="ins-list">${Object.entries(ROLES).map(([k, r]) => `<div class="ins-item" style="cursor:default"><span><span class="pill ${k}">${r.label}</span></span><span class="bd muted">${r.desc}</span></div>`).join("")}</div>`;
}
function uAudit(el) {
  if (!can("audit")) { el.innerHTML = '<p class="muted">Your role cannot view the audit log.</p>'; return; }
  const log = sget(K.audit, []);
  el.innerHTML = `<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><label class="search-box" style="flex:1;min-width:200px">${ic("search")}<input id="aQ" placeholder="Filter by user, action or detail" aria-label="Filter audit log"></label><button class="btn btn-ghost btn-sm" id="aCsv">${ic("download")}Export CSV</button></div>
    <div class="tbl-wrap"><table><thead><tr><th>When</th><th>User</th><th>Action</th><th>Detail</th></tr></thead><tbody id="aRows"></tbody></table></div>`;
  const draw = () => { const q = $("#aQ").value.toLowerCase(); const rows = log.filter(r => !q || (r.user + r.action + r.detail).toLowerCase().includes(q)); $("#aRows").innerHTML = rows.slice(0, 300).map(r => `<tr><td>${fmtDT(r.t)}</td><td class="mono">${esc(r.user)}</td><td>${esc(r.action)}</td><td style="white-space:normal;min-width:260px;overflow-wrap:anywhere">${esc(r.detail)}</td></tr>`).join("") || `<tr><td colspan="4" class="faint">No entries</td></tr>`; };
  $("#aQ").oninput = draw; draw();
  $("#aCsv").onclick = () => { const q = s => `"${String(s).replace(/"/g, '""')}"`; const csv = "When,User,Role,Action,Detail\n" + log.map(r => [new Date(r.t).toISOString(), r.user, r.role, r.action, r.detail].map(q).join(",")).join("\n"); audit("Exported audit log"); saveFile(`chatvault_audit_${isoDay(Date.now())}.csv`, csv, "text/csv"); };
}
function uSettings(el) {
  const st = settings();
  el.innerHTML = `<div class="field" style="max-width:320px"><label for="idle">Lock the screen after inactivity</label><select class="select" id="idle">${[5, 10, 15, 30].map(n => `<option value="${n}"${n === st.idleMin ? " selected" : ""}>${n} minutes</option>`).join("")}</select></div>
    <p class="note" style="margin:0">The lock screen asks for the signed-in user's password. Chats stay loaded underneath.</p>
    <div class="src-card"><div class="src-top"><b>Storage folder</b><span class="faint">${S.folder?.handle ? esc(S.folder.label) : FS_OK ? "Not set" : "Not available in this copy"}</span></div><div><button class="btn btn-ghost btn-sm" id="setFolder">${ic("db")}${S.folder?.handle ? "Change or manage folder" : "Choose a folder"}</button></div></div>
    <label class="check"><input type="checkbox" id="setSave"${st.autoSave ? " checked" : ""}><span><b>Save imported chats on this device</b><br>Chats are encrypted with AES-256 and stored in this browser, so they are available after a reload. Each user unlocks them with their own password.</span></label>
    <label class="check"><input type="checkbox" id="setBlur"${st.privacyOnBlur ? " checked" : ""}><span><b>Turn on the privacy screen when you switch to another window</b><br>Useful in shared offices. Press any key or click to continue.</span></label>
    <label class="check"><input type="checkbox" id="setNames"${st.viewerNames ? " checked" : ""}><span><b>Viewer role: also replace participant names</b><br>Viewers see Participant A, B, C… instead of names, in addition to masked phone numbers and emails.</span></label>`;
  $("#setSave").onchange = e => { sset(K.settings, { ...settings(), autoSave: e.target.checked }); audit("Changed setting", "Save imported chats: " + (e.target.checked ? "on" : "off")); toast("Saved"); };
  $("#setFolder").onclick = () => { $$(".overlay").forEach(x => x.remove()); openVault("storage"); };
  $("#setBlur").onchange = e => { sset(K.settings, { ...settings(), privacyOnBlur: e.target.checked }); toast("Saved"); };
  $("#setNames").onchange = e => { sset(K.settings, { ...settings(), viewerNames: e.target.checked }); audit("Changed setting", "Viewer name redaction: " + (e.target.checked ? "on" : "off")); toast("Saved"); };
  $("#idle").onchange = e => { sset(K.settings, { ...settings(), idleMin: +e.target.value }); audit("Changed auto-lock", e.target.value + " minutes"); toast("Saved"); };
}
function changePassword() {
  const ov = h(`<div class="overlay"><form class="modal" role="dialog" aria-modal="true" aria-labelledby="cpT" novalidate><div class="modal-head"><h3 id="cpT">Change password</h3></div>
    <div class="modal-body"><div class="field"><label for="cp0">Current password</label><input class="input" id="cp0" type="password" autocomplete="current-password"></div>
    <div class="field"><label for="cp1">New password</label><input class="input" id="cp1" type="password" autocomplete="new-password" placeholder="8+ characters, letter and number"></div>
    <div class="field"><label for="cp2">Confirm new password</label><input class="input" id="cp2" type="password" autocomplete="new-password"></div><div class="err" id="cpErr"></div></div>
    <div class="modal-foot"><button class="btn btn-ghost" type="button" data-x>Cancel</button><button class="btn btn-primary" type="submit">Update password</button></div></form></div>`);
  document.body.append(ov); $("[data-x]", ov).onclick = () => ov.remove();
  $("form", ov).onsubmit = async e => {
    e.preventDefault(); const err = $("#cpErr", ov); err.textContent = "";
    const u = users().find(x => x.id === S.user.id);
    if ((await pbkdf2($("#cp0", ov).value, u.salt)).hash !== u.hash) return err.textContent = "Current password is incorrect.";
    const p = $("#cp1", ov).value; const pr = pwProblem(p); if (pr) return err.textContent = pr;
    if (p !== $("#cp2", ov).value) return err.textContent = "The new passwords do not match.";
    const { salt, hash } = await pbkdf2(p); const w = await wrapFor(p); saveUsers(users().map(x => x.id === u.id ? { ...x, salt, hash, ...w } : x));
    audit("Changed own password"); ov.remove(); toast("Password updated");
  };
}

/* ============================================================ storage folder (local or cloud-synced) */
const FS_OK = (() => { try { return "showDirectoryPicker" in window && window.self === window.top && window.isSecureContext !== false; } catch { return false; } })();
const FOLDER_KEY = "__folder";
const MAGIC = "CVLT1";
S.folder = { status: FS_OK ? "none" : "unsupported" };
const vaultId = () => { let v = sget("cv.vaultId", ""); if (!v) { v = hex(crypto.getRandomValues(new Uint8Array(12))); sset("cv.vaultId", v); } return v; };
const README_TXT = `ChatVault archive folder
========================

This folder is kept up to date by ChatVault.

  vault.json          archive identity and the user accounts that may open it
  chats/<id>/         one folder per chat
    meta.cvault       chat details, tags, client, stars and notes (encrypted)
    <sha256>.cvault   the original WhatsApp export (encrypted); the file name is its SHA-256

Everything except this file and vault.json is encrypted with AES-256-GCM. Only ChatVault,
with a valid username and password, can open it. vault.json holds salted password hashes
and wrapped keys, not passwords.

To open this archive on another computer: open ChatVault.html in Chrome or Edge, choose
"Open an existing archive folder" on the first screen, pick this folder and sign in.

Do not edit or rename the files. If this folder is inside Google Drive, OneDrive or Dropbox,
let the drive finish syncing before opening it on another computer.
`;
async function encFile(data) {
  const { iv, ct } = await aesEnc(S.vaultKey, data);
  const out = new Uint8Array(5 + 12 + ct.byteLength);
  out.set(new TextEncoder().encode(MAGIC)); out.set(iv, 5); out.set(new Uint8Array(ct), 17);
  return out;
}
async function decFile(buf) {
  const u = new Uint8Array(buf);
  if (new TextDecoder().decode(u.slice(0, 5)) !== MAGIC) throw new Error("Not a ChatVault file");
  return crypto.subtle.decrypt({ name: "AES-GCM", iv: u.slice(5, 17) }, S.vaultKey, u.slice(17));
}
const fsx = {
  miss: e => e && (e.name === "NotFoundError" || e.name === "TypeMismatchError"),
  async dir(d, name, create = false) { try { return await d.getDirectoryHandle(name, { create }); } catch (e) { if (fsx.miss(e)) return null; throw e; } },
  async file(d, name) { try { return await (await d.getFileHandle(name)).getFile(); } catch (e) { if (fsx.miss(e)) return null; throw e; } },
  async write(d, name, data) { const fh = await d.getFileHandle(name, { create: true }); const w = await fh.createWritable(); await w.write(data); await w.close(); },
  async list(d) { const out = []; for await (const [n, hd] of d.entries()) out.push([n, hd]); return out; }
};
async function readVaultFile(root) {
  const f = await fsx.file(root, "vault.json"); if (!f) return null;
  try { const v = JSON.parse(await f.text()); return v.app === "ChatVault" ? v : null; } catch { return null; }
}
async function writeVaultFile() {
  const root = S.folder.handle; if (!root || S.folder.status !== "ok") return;
  const cur = await readVaultFile(root) || {};
  const tomb = sget("cv.tomb", []);
  const v = {
    app: "ChatVault", kind: "archive-folder", version: 1, vaultId: vaultId(), created: cur.created || new Date().toISOString(), updated: new Date().toISOString(),
    note: "Chats in this folder are encrypted with AES-256-GCM. Open them in ChatVault with an account listed here. Password hashes are salted PBKDF2-SHA-256.",
    users: users().filter(u => u.wsalt).map(({ id, name, username, role, salt, hash, wsalt, wiv, wct, active, created }) => ({ id, name, username, role, salt, hash, wsalt, wiv, wct, active, created })),
    deleted: [...new Set([...(cur.deleted || []), ...tomb])]
  };
  await fsx.write(root, "vault.json", JSON.stringify(v, null, 2));
  sset("cv.tomb", []);
}
async function pickFolderRoot({ create = true } = {}) {
  const parent = await window.showDirectoryPicker({ id: "chatvault", mode: "readwrite" });
  if (await fsx.file(parent, "vault.json")) return { root: parent, label: parent.name };
  const sub = await fsx.dir(parent, "ChatVault");
  if (sub && await fsx.file(sub, "vault.json")) return { root: sub, label: `${parent.name}/ChatVault` };
  if (!create) return { root: null, label: parent.name };
  return { root: await parent.getDirectoryHandle("ChatVault", { create: true }), label: `${parent.name}/ChatVault`, fresh: true };
}
function showFolderUnsupported() {
  const ov = h(`<div class="overlay"><div class="modal" role="dialog" aria-modal="true"><div class="modal-head"><h3>Folder storage is not available here</h3></div>
    <div class="modal-body"><p style="margin:0">Saving to a folder needs <b>Google Chrome</b> or <b>Microsoft Edge</b>, with <b>ChatVault.html opened from your computer</b>. ${window.self !== window.top ? "This copy is running inside another page, which blocks folder access." : "This browser does not support it."}</p>
      <p class="muted" style="margin:0">Your chats are still saved, encrypted, in this browser. Use <b>Backup</b> to keep a copy elsewhere.</p></div>
    <div class="modal-foot"><button class="btn btn-primary" data-x>OK</button></div></div></div>`);
  document.body.append(ov); $("[data-x]", ov).onclick = () => ov.remove();
  return false;
}
async function chooseFolder() {
  if (!FS_OK) return showFolderUnsupported();
  let pick;
  try { pick = await pickFolderRoot(); } catch (e) { if (e.name !== "AbortError") toast("Could not open that folder: " + (e.message || e.name), "err"); return false; }
  const v = await readVaultFile(pick.root);
  if (v && v.vaultId && v.vaultId !== vaultId()) return adoptArchivePrompt(pick, v, true);
  return connectFolder(pick.root, pick.label);
}
async function connectFolder(root, label) {
  await idb.putBlob(FOLDER_KEY, { handle: root, label, vaultId: vaultId(), connectedAt: Date.now() });
  S.folder = { handle: root, label, status: "ok" };
  sset(K.settings, { ...settings(), folderAsked: true });
  try { await fsx.write(root, "README.txt", README_TXT); } catch {}
  audit("Connected storage folder", label);
  const r = await folderSync();
  toast(`Storage folder connected: ${label}${r ? ` · ${r.pushed} saved there${r.pulled ? `, ${r.pulled} restored` : ""}` : ""}`);
  updateFoot(); return true;
}
async function disconnectFolder() {
  await idb.delBlob(FOLDER_KEY); audit("Disconnected storage folder", S.folder.label || "");
  S.folder = { status: "none" }; updateFoot();
}
async function folderInit() {
  if (!FS_OK || !S.vaultKey) { updateFoot(); return 0; }
  let rec; try { rec = await idb.blob(FOLDER_KEY); } catch { rec = null; }
  if (!rec?.handle) { S.folder = { status: "none" }; updateFoot(); return 0; }
  S.folder = { handle: rec.handle, label: rec.label, status: "checking" };
  let p = "denied"; try { p = await rec.handle.queryPermission({ mode: "readwrite" }); } catch {}
  if (p !== "granted") { S.folder.status = "needs-permission"; updateFoot(); return 0; }
  S.folder.status = "ok";
  const r = await folderSync();
  return r?.pulled || 0;
}
async function reconnectFolder() {
  try {
    const p = await S.folder.handle.requestPermission({ mode: "readwrite" });
    if (p !== "granted") return toast("Permission to use the folder was not given", "err");
    S.folder.status = "ok"; const r = await folderSync();
    toast(`Storage folder reconnected${r?.pulled ? ` · ${r.pulled} chat${r.pulled > 1 ? "s" : ""} restored` : ""}`);
  } catch (e) { S.folder.status = "error"; S.folder.error = e.message; updateFoot(); toast("The folder could not be reached. It may have been moved, renamed or disconnected.", "err"); }
}
let _fsTimer = null;
function scheduleFolderSync() { if (S.folder?.status !== "ok") return; clearTimeout(_fsTimer); _fsTimer = setTimeout(() => folderSync(), 1200); }
async function folderDelete(id) {
  const t = sget("cv.tomb", []); if (!t.includes(id)) sset("cv.tomb", [...t, id]);
  if (S.folder?.status !== "ok") return;
  try { const cd = await fsx.dir(S.folder.handle, "chats"); if (cd) await cd.removeEntry(id, { recursive: true }); } catch (e) { if (!fsx.miss(e)) console.error(e); }
  try { await writeVaultFile(); } catch (e) { console.error(e); }
}
async function folderSync() {
  const F = S.folder;
  if (!F?.handle || F.status !== "ok" || !S.vaultKey) return null;
  if (F.syncing) return F.syncing;
  F.syncing = (async () => {
    const res = { pushed: 0, pulled: 0, updated: 0, removed: 0 };
    try {
      const root = F.handle;
      const v = await readVaultFile(root);
      if (v && v.vaultId && v.vaultId !== vaultId()) throw new Error("This folder now holds a different ChatVault archive.");
      const tomb = new Set([...(v?.deleted || [])]);
      const chatsDir = await root.getDirectoryHandle("chats", { create: true });
      const remote = new Map();
      for (const [name, hd] of await fsx.list(chatsDir)) if (hd.kind === "directory") remote.set(name, hd);
      const local = new Map((await idb.all()).map(r => [r.id, r]));
      // deletions made on another computer
      for (const id of tomb) if (local.has(id)) {
        await idb.del(id); await idb.delBlobs(id + "/"); S.chats = S.chats.filter(x => x.id !== id); local.delete(id); res.removed++;
      }
      // pull what is newer in the folder
      const remoteSaved = new Map();
      for (const [id, d] of remote) {
        if (tomb.has(id)) continue;
        const mf = await fsx.file(d, "meta.cvault"); if (!mf) continue;
        let w; try { w = JSON.parse(new TextDecoder().decode(await decFile(await mf.arrayBuffer()))); } catch { continue; }
        remoteSaved.set(id, w.savedAt || 0);
        const lr = local.get(id);
        if (lr && (lr.savedAt || 0) >= (w.savedAt || 0)) continue;
        let ok = true;
        for (const s of w.meta.sources) {
          if (await idb.blob(`${id}/${s.hash}`)) continue;
          const sf = await fsx.file(d, s.hash + ".cvault"); if (!sf) { ok = false; break; }   // the drive may still be syncing
          const buf = await decFile(await sf.arrayBuffer());
          if (await sha256(buf) !== s.hash) { ok = false; audit("Integrity check failed", `Folder copy of ${s.name}`); break; }
          await idb.putBlob(`${id}/${s.hash}`, await aesEnc(S.vaultKey, buf));
        }
        if (!ok) continue;
        const size = w.meta.sources.reduce((a, s) => a + s.size, 0);
        await idb.put({ id, m: await aesEnc(S.vaultKey, w.meta), savedAt: w.savedAt, size });
        const stub = { ...w.meta, id, stub: true, saved: true, savedAt: w.savedAt, size, h: hueOf(w.meta.title), participants: [], messages: [] };
        const c = S.chats.find(x => x.id === id);
        if (c) { if (c.media) for (const f of c.media.values()) if (f.url) URL.revokeObjectURL(f.url); Object.keys(c).forEach(k => delete c[k]); Object.assign(c, stub); res.updated++; }
        else { S.chats.push(stub); res.pulled++; }
        local.set(id, { id, savedAt: w.savedAt, pulled: true });
      }
      // push what is newer or missing in the folder
      for (const [id, lr] of local) {
        if (lr.pulled || !lr.m) continue;
        const d = remote.get(id) || await chatsDir.getDirectoryHandle(id, { create: true });
        const meta = await aesDec(S.vaultKey, lr.m, true);
        let wrote = false;
        for (const s of meta.sources || []) {
          if (await fsx.file(d, s.hash + ".cvault")) continue;
          const rec = await idb.blob(`${id}/${s.hash}`); if (!rec) continue;
          await fsx.write(d, s.hash + ".cvault", await encFile(await aesDec(S.vaultKey, rec))); wrote = true;
        }
        if (!remoteSaved.has(id) || remoteSaved.get(id) < (lr.savedAt || 0) || wrote) {
          await fsx.write(d, "meta.cvault", await encFile(new TextEncoder().encode(JSON.stringify({ savedAt: lr.savedAt || Date.now(), meta })))); res.pushed++;
        }
      }
      await writeVaultFile();
      F.lastSync = Date.now(); F.error = "";
    } catch (e) {
      console.error(e); F.error = e.message || String(e);
      if (e.name === "NotAllowedError" || e.name === "SecurityError") F.status = "needs-permission";
      else if (fsx.miss(e) || e.name === "InvalidStateError") F.status = "error";
    }
    return res;
  })();
  const r = await F.syncing; F.syncing = null;
  if (r.pulled || r.updated || r.removed) {
    renderList();
    if (S.active && !S.chats.some(c => c.id === S.active)) { const n = sortedChats()[0]; n ? openChat(n.id) : renderEmpty(); }
    else if (S.active && activeChat()?.stub) openChat(S.active);
  }
  updateFoot(); return r;
}
function adoptArchivePrompt(pick, v, inApp) {
  return new Promise(res => {
    const ov = h(`<div class="overlay"><div class="modal" role="dialog" aria-modal="true" aria-labelledby="adT"><div class="modal-head"><h3 id="adT">Open this ChatVault archive?</h3></div>
      <div class="modal-body"><div class="src-card"><b>${esc(pick.label)}</b><dl class="kv"><dt>Created</dt><dd>${v.created ? fmtDT(Date.parse(v.created)) : "–"}</dd><dt>Last updated</dt><dd>${v.updated ? fmtDT(Date.parse(v.updated)) : "–"}</dd><dt>Accounts</dt><dd>${(v.users || []).map(u => `${esc(u.username)} (${esc(ROLES[u.role]?.label || u.role)})`).join(", ") || "none"}</dd></dl></div>
        <p style="margin:0">ChatVault will use the accounts stored in this folder. Sign in with your account from that archive and its chats are restored into this browser. New work is saved back to the folder.</p>
        ${users().length ? `<p class="muted" style="margin:0"><b>The accounts currently on this device will be replaced.</b> Chats saved only in this browser under those accounts will no longer open. Make a backup first if you need them.</p>` : ""}</div>
      <div class="modal-foot"><button class="btn btn-ghost" data-x>Cancel</button><button class="btn btn-primary" data-ok>Open this archive</button></div></div></div>`);
    document.body.append(ov);
    $("[data-x]", ov).onclick = () => { ov.remove(); res(false); };
    $("[data-ok]", ov).onclick = async () => {
      if (S.user) audit("Switched to archive folder", pick.label);
      saveUsers(v.users || []); sset("cv.vaultId", v.vaultId);
      await idb.putBlob(FOLDER_KEY, { handle: pick.root, label: pick.label, vaultId: v.vaultId, connectedAt: Date.now() });
      sset(K.settings, { ...settings(), folderAsked: true });
      ov.remove();
      if (inApp && S.user) signOut(); else renderAuth();
      toast("Archive opened. Sign in with your account from that archive.");
      res(true);
    };
  });
}
async function openArchiveFromAuth() {
  if (!FS_OK) return showFolderUnsupported();
  let pick; try { pick = await pickFolderRoot({ create: false }); } catch (e) { if (e.name !== "AbortError") toast("Could not open that folder", "err"); return; }
  const v = pick.root && await readVaultFile(pick.root);
  if (!v) return toast(`No ChatVault archive found in “${pick.label}”. Pick the folder that contains vault.json, or the folder above it.`, "err");
  adoptArchivePrompt(pick, v, false);
}
function maybeAskFolder() {
  if (!FS_OK || !S.vaultKey || !can("manage") || settings().folderAsked || S.folder?.handle) return Promise.resolve();
  sset(K.settings, { ...settings(), folderAsked: true });
  return new Promise(res => {
    const ov = h(`<div class="overlay"><div class="modal" role="dialog" aria-modal="true" aria-labelledby="afT"><div class="modal-head"><h3 id="afT">Where should ChatVault keep your archive?</h3></div>
      <div class="modal-body"><p class="muted" style="margin:0">Chats are always encrypted. Keeping them in a folder means they stay safe if this browser's data is cleared, and they can be opened on another computer.</p>
        <button class="exp-opt" data-f="local"><span class="ico">${ic("db")}</span><div><b>A folder on this computer</b><span>For example D:\\Client Records. ChatVault creates a “ChatVault” folder inside the one you pick.</span></div></button>
        <button class="exp-opt" data-f="cloud"><span class="ico">${ic("cloud")}</span><div><b>A folder in Google Drive, OneDrive or Dropbox</b><span>Pick a folder inside the drive's folder on this computer. The drive app keeps a copy online and on your other computers.</span></div></button>
        <button class="exp-opt" data-f="none"><span class="ico">${ic("lock")}</span><div><b>Only in this browser for now</b><span>You can choose a folder any time in ⋮ → Saved chats and backup → Storage folder.</span></div></button></div></div></div>`);
    document.body.append(ov);
    ov.addEventListener("click", async e => {
      const b = e.target.closest("[data-f]"); if (!b) return;
      if (b.dataset.f === "none") { ov.remove(); return res(); }
      const ok = await chooseFolder();
      if (ok) { ov.remove(); res(); }
    });
  });
}
const ago = ts => { const m = Math.round((Date.now() - ts) / 60000); return m < 1 ? "just now" : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : fmtDate(ts); };
function vStorage(el) {
  const F = S.folder || {};
  if (!FS_OK) {
    el.innerHTML = `<div class="src-card"><b>Folder storage is not available in this copy</b><p class="muted" style="margin:0">It needs Google Chrome or Microsoft Edge with ChatVault.html opened from your computer${window.self !== window.top ? ". This copy runs inside another page, which blocks folder access" : ""}. Chats are still saved, encrypted, in this browser; use Backup to keep a copy elsewhere.</p></div>`;
    return;
  }
  const pill = { ok: '<span class="pill ok">Connected</span>', "needs-permission": '<span class="pill reviewer">Needs permission</span>', error: '<span class="pill off">Not reachable</span>', checking: '<span class="pill viewer">Checking</span>' }[F.status] || '<span class="pill viewer">Not set</span>';
  el.innerHTML = `<div class="src-card"><div class="src-top"><b>${F.handle ? esc(F.label) : "No folder chosen"}</b>${pill}</div>
      ${F.handle ? `<dl class="kv"><dt>Last saved</dt><dd>${F.lastSync ? fmtDT(F.lastSync) : "–"}</dd><dt>Chats</dt><dd>${S.chats.filter(c => c.saved).length} saved</dd>${F.error ? `<dt>Problem</dt><dd style="color:var(--danger)">${esc(F.error)}</dd>` : ""}</dl>` : `<p class="muted" style="margin:0">Chats are saved only in this browser.</p>`}
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn btn-primary btn-sm" id="stChoose">${ic("db")}${F.handle ? "Change folder" : "Choose folder"}</button>
        ${F.status === "needs-permission" ? `<button class="btn btn-primary btn-sm" id="stRe">Reconnect</button>` : ""}
        ${F.status === "ok" ? `<button class="btn btn-ghost btn-sm" id="stSync">${ic("restore")}Sync now</button>` : ""}
        ${F.handle ? `<button class="btn btn-ghost btn-sm" id="stOff">Disconnect</button>` : ""}</div></div>
    <div class="steps" style="gap:8px"><b>How it works</b><ol>
      <li>Every saved chat is written to the folder as encrypted files, together with its original export. Changes to tags, notes, stars and client details are saved there too.</li>
      <li><b>Online drive:</b> pick a folder inside Google Drive, OneDrive or Dropbox on this computer. The drive app uploads it; ChatVault never sends anything over the internet itself.</li>
      <li><b>Another computer:</b> open ChatVault.html in Chrome or Edge, choose <b>Open an existing archive folder</b> on the first screen, pick the same folder and sign in with your usual account.</li>
      <li>When this browser opens again, it may ask once for permission to use the folder.</li></ol></div>
    <p class="note" style="margin:0">vault.json in the folder holds salted password hashes and wrapped keys (never passwords), so anyone with the folder can attempt to guess passwords. Use strong passwords and keep the folder private.</p>`;
  const again = () => vStorage(el);
  $("#stChoose", el).onclick = async () => { await chooseFolder(); again(); };
  $("#stRe", el) && ($("#stRe", el).onclick = async () => { await reconnectFolder(); again(); });
  $("#stSync", el) && ($("#stSync", el).onclick = async () => { const r = await folderSync(); toast(r ? `Synced · ${r.pushed} saved, ${r.pulled + r.updated} updated from the folder` : "Sync could not run"); again(); });
  $("#stOff", el) && ($("#stOff", el).onclick = () => confirmModal("Disconnect the storage folder?", "Chats stay in this browser and in the folder. New changes will no longer be written to the folder.", "Disconnect", async () => { await disconnectFolder(); again(); }));
}
setInterval(() => { if (S.user && !S.locked && S.folder?.status === "ok" && document.visibilityState === "visible") folderSync(); }, 120000);

/* ============================================================ saved chats manager, backup and restore */
async function verifyChat(chat) {
  for (const s of chat.sources) {
    const rec = await idb.blob(`${chat.id}/${s.hash}`); if (!rec) return false;
    if (await sha256(await aesDec(S.vaultKey, rec)) !== s.hash) return false;
  }
  return true;
}
async function openVault(start = "list") {
  if (!can("manage")) return;
  const ov = h(`<div class="overlay"><div class="modal wide" role="dialog" aria-modal="true" aria-labelledby="vT"><div class="modal-head"><h3 id="vT">Saved chats and backup</h3><button class="icon-btn" data-x aria-label="Close">${ic("close")}</button></div>
    <div style="padding:0 20px 8px"><div class="seg"><button data-v="list">Saved chats</button><button data-v="backup">Backup</button><button data-v="restore">Restore</button><button data-v="storage">Storage folder</button></div></div>
    <div class="modal-body" id="vBody"></div></div></div>`);
  document.body.append(ov); $("[data-x]", ov).onclick = () => ov.remove();
  const show = k => { $$("[data-v]", ov).forEach(b => b.classList.toggle("on", b.dataset.v === k)); ({ list: vList, backup: vBackup, restore: vRestore, storage: vStorage })[k]($("#vBody", ov), ov); };
  $$("[data-v]", ov).forEach(b => b.onclick = () => show(b.dataset.v)); show(start);
}
async function vList(el, ov) {
  if (!S.vaultKey) { el.innerHTML = `<p class="muted">Saved chats are locked for this account. Ask an admin to reset your password; the new password will unlock them.</p>`; return; }
  const saved = S.chats.filter(c => c.saved);
  let est = ""; try { const e = await navigator.storage?.estimate?.(); if (e) est = `${fmtBytes(e.usage || 0)} used of about ${fmtBytes(e.quota || 0)} available to this browser`; } catch {}
  const total = saved.reduce((a, c) => a + (c.size || c.sources.reduce((x, s) => x + s.size, 0)), 0);
  el.innerHTML = `<div class="tiles" style="grid-template-columns:repeat(3,1fr)"><div class="tile"><b>${saved.length}</b><span>saved chats</span></div><div class="tile"><b>${fmtBytes(total)}</b><span>original export size</span></div><div class="tile"><b>${settings().autoSave ? "On" : "Off"}</b><span>auto-save on import</span></div></div>
    ${est ? `<p class="note" style="margin:0">${est}.</p>` : ""}
    <div class="tbl-wrap"><table><thead><tr><th>Chat</th><th>Tags</th><th>Exports</th><th>Messages</th><th>Latest message</th><th>Integrity</th><th></th></tr></thead><tbody>
    ${saved.map(c => `<tr data-id="${c.id}"><td><b>${esc(c.title)}</b></td><td>${(c.tags || []).map(t => `<span class="pill viewer">${esc(t)}</span>`).join(" ") || '<span class="faint">–</span>'}</td>
      <td>${c.sources.length}</td><td>${(c.stub ? c.msgCount : c.messages.length) || 0}</td><td>${lastTsOf(c) ? fmtDate(lastTsOf(c)) : "–"}</td>
      <td data-ver>${c.verified === true ? '<span class="pill ok">Verified</span>' : c.verified === false ? '<span class="pill off">Failed</span>' : '<span class="faint">Not checked</span>'}</td>
      <td><span class="inline-confirm"><button class="btn btn-ghost btn-sm" data-open>Open</button><button class="btn btn-ghost btn-sm" data-verify>Verify</button>${can("purge") ? `<button class="icon-btn" data-purge aria-label="Delete permanently">${ic("trash")}</button>` : ""}</span></td></tr>`).join("") || `<tr><td colspan="7" class="faint">No saved chats yet. Imported chats are saved here automatically.</td></tr>`}</tbody></table></div>
    <div style="display:flex;gap:8px;flex-wrap:wrap">${saved.length ? `<button class="btn btn-ghost btn-sm" id="verifyAll">${ic("shield")}Verify all</button>` : ""}</div>
    <p class="note" style="margin:0">Saved chats live in this browser on this device. Clearing the browser's site data deletes them, so keep a backup.</p>`;
  const verifyRow = async (tr) => {
    const c = S.chats.find(x => x.id === tr.dataset.id); const cell = $("[data-ver]", tr);
    cell.innerHTML = '<span class="dots"><i></i><i></i><i></i></span>';
    let ok = false; try { ok = await verifyChat(c); } catch { ok = false; }
    c.verified = ok; cell.innerHTML = ok ? '<span class="pill ok">Verified</span>' : '<span class="pill off">Failed</span>';
    audit(ok ? "Integrity verified" : "Integrity check failed", c.title); return ok;
  };
  el.onclick = async e => {
    const tr = e.target.closest("tr[data-id]");
    if (e.target.closest("#verifyAll")) { let bad = 0; for (const r of $$("tr[data-id]", el)) if (!(await verifyRow(r))) bad++; toast(bad ? `${bad} chat${bad > 1 ? "s" : ""} failed verification` : "All saved chats verified", bad ? "err" : ""); return; }
    if (!tr) return; const c = S.chats.find(x => x.id === tr.dataset.id);
    if (e.target.closest("[data-open]")) { ov.remove(); openChat(c.id); }
    if (e.target.closest("[data-verify]")) verifyRow(tr);
    if (e.target.closest("[data-purge]")) purgeChat(c, () => vList(el, ov));
  };
}
async function backupKey(pass, saltHex) { return pwKey(pass, saltHex); }
function vBackup(el) {
  if (!S.vaultKey) { el.innerHTML = `<p class="muted">Saved chats are locked for this account.</p>`; return; }
  const saved = S.chats.filter(c => c.saved);
  el.innerHTML = `<p class="muted" style="margin:0">Creates one encrypted file containing all ${saved.length} saved chats with their original exports, tags and notes. It can be restored on any computer running ChatVault with the passphrase you set here.</p>
    <form id="bkForm" class="steps" novalidate><div class="form-row">
      <div class="field"><label for="bk1">Backup passphrase</label><input class="input" id="bk1" type="password" autocomplete="new-password" placeholder="At least 8 characters, a letter and a number"></div>
      <div class="field"><label for="bk2">Confirm passphrase</label><input class="input" id="bk2" type="password" autocomplete="new-password"></div></div>
      <div class="err" id="bkErr"></div><div><button class="btn btn-primary btn-sm" type="submit"${saved.length ? "" : " disabled"}>${ic("download")}Create encrypted backup</button></div></form>
    <p class="note" style="margin:0">Without the passphrase the backup cannot be opened by anyone, including you. Store it separately from the file.</p>`;
  $("#bkForm").onsubmit = async e => {
    e.preventDefault(); const err = $("#bkErr"); err.textContent = "";
    const p = $("#bk1").value; const pr = pwProblem(p); if (pr) return err.textContent = pr;
    if (p !== $("#bk2").value) return err.textContent = "The passphrases do not match.";
    err.innerHTML = '<span class="thinking"><span class="dots"><i></i><i></i><i></i></span>Encrypting backup</span>';
    try {
      const payload = { chats: [] };
      for (const c of saved) {
        const meta = c.stub ? (({ id, stub, saved, savedAt, size, h, participants, messages, verified, ...m }) => m)(c) : chatMeta(c);
        const sources = [];
        for (const s of c.sources) { const rec = await idb.blob(`${c.id}/${s.hash}`); sources.push({ hash: s.hash, b64: b64(await aesDec(S.vaultKey, rec)) }); }
        payload.chats.push({ id: c.id, meta, sources });
      }
      const salt = hex(crypto.getRandomValues(new Uint8Array(16))); const k = await backupKey(p, salt);
      const { iv, ct } = await aesEnc(k, payload);
      const file = JSON.stringify({ app: "ChatVault", kind: "encrypted-backup", version: 1, created: new Date().toISOString(), createdBy: S.user.username, chats: saved.length, kdf: "PBKDF2-SHA256-150000", cipher: "AES-256-GCM", salt, iv: hex(iv), data: b64(ct) });
      audit("Created backup", `${saved.length} chats`);
      err.textContent = "";
      await saveFile(`ChatVault_backup_${isoDay(Date.now())}.json`, file, "application/json");
    } catch (x) { console.error(x); err.textContent = "Backup failed: " + (x.message || x); }
  };
}
function vRestore(el) {
  if (!S.vaultKey) { el.innerHTML = `<p class="muted">Saved chats are locked for this account, so a backup cannot be restored into it.</p>`; return; }
  el.innerHTML = `<p class="muted" style="margin:0">Restores chats from a ChatVault backup file. Chats that are already saved here are skipped.</p>
    <form id="rsForm" class="steps" novalidate><div class="form-row">
      <div class="field"><label for="rsFile">Backup file</label><input class="input" id="rsFile" type="file" accept=".json,application/json" style="padding-top:8px"></div>
      <div class="field"><label for="rsPw">Backup passphrase</label><input class="input" id="rsPw" type="password" autocomplete="off"></div></div>
      <div class="err" id="rsErr"></div><div><button class="btn btn-primary btn-sm" type="submit">${ic("restore")}Restore</button></div></form>`;
  $("#rsForm").onsubmit = async e => {
    e.preventDefault(); const err = $("#rsErr"); err.textContent = "";
    const f = $("#rsFile").files[0]; if (!f) return err.textContent = "Choose a backup file.";
    let bk; try { bk = JSON.parse(await f.text()); } catch { return err.textContent = "This is not a ChatVault backup file."; }
    if (bk.app !== "ChatVault" || bk.kind !== "encrypted-backup") return err.textContent = "This is not a ChatVault backup file.";
    err.innerHTML = '<span class="thinking"><span class="dots"><i></i><i></i><i></i></span>Decrypting backup</span>';
    let payload;
    try { payload = await aesDec(await backupKey($("#rsPw").value, bk.salt), { iv: fromHex(bk.iv), ct: unb64(bk.data) }, true); }
    catch { return err.textContent = "Wrong passphrase, or the file has been altered."; }
    let added = 0, skipped = 0, bad = 0;
    for (const c of payload.chats) {
      if (S.chats.some(x => x.id === c.id)) { skipped++; continue; }
      let ok = true;
      for (const s of c.sources) { const bytes = unb64(s.b64); if (await sha256(bytes.buffer) !== s.hash) { ok = false; break; } await idb.putBlob(`${c.id}/${s.hash}`, await aesEnc(S.vaultKey, bytes.buffer)); }
      if (!ok) { bad++; await idb.delBlobs(c.id + "/"); continue; }
      await idb.put({ id: c.id, m: await aesEnc(S.vaultKey, c.meta), savedAt: Date.now(), size: c.meta.sources.reduce((a, s) => a + s.size, 0) });
      added++;
    }
    await loadSavedIndex(); renderList(); updateFoot(); scheduleFolderSync();
    audit("Restored backup", `${f.name} · ${added} added · ${skipped} already present${bad ? ` · ${bad} failed hash check` : ""}`);
    err.textContent = ""; toast(`Restored ${added} chat${added === 1 ? "" : "s"}${skipped ? ` · ${skipped} already here` : ""}${bad ? ` · ${bad} failed the fingerprint check` : ""}`, bad ? "err" : "");
    if (added && !S.active) openChat(sortedChats()[0].id);
  };
}

/* ============================================================ guided tour */
const TOUR = [
  { sel: "#chatList", pane: "list", title: "Your archive", body: "Every imported chat appears here. A lock icon means it is saved on this device, encrypted with AES-256, and comes back after a reload." },
  { sel: ".side-search", pane: "list", title: "Find anything", body: "Search chat names, tags and notes. Type three or more letters to search the messages of every chat at once. Filter by tag and change the sort order underneath." },
  { sel: "#scroller", pane: "chat", title: "Reads like the phone", body: "Bubbles, photos, voice notes and documents appear as they did in WhatsApp. Click a date chip to jump to any day." },
  { sel: '[data-d="search"]', pane: "chat", title: "Search this chat", body: "Filter by text, sender, date and type, including deleted, recovered and edited messages." },
  { sel: '[data-d="insights"]', pane: "chat", title: "Insights", body: "Participation, response times, longest silences, activity by hour, requests and amounts. An AI summary is available when ChatVault is opened inside Claude." },
  { sel: "#cTitle", pane: "chat", title: "Info, tags and integrity", body: "Click the chat name for SHA-256 fingerprints, tags and notes. Add a newer export here: ChatVault merges it and shows what was deleted or edited in between." },
  { sel: "#cExport", pane: "chat", title: "Export", body: "A complete archive ZIP, a phone-style HTML viewer or an Excel index, with optional redaction of contact details and names, an integrity statement and output hashes." },
  { sel: "#btnMenu", pane: "list", title: "Administration", body: "Saved chats, encrypted backup and restore, users and roles, the audit log and settings, depending on your role." },
  { sel: "#btnLock", pane: "list", title: "Lock when you step away", body: "Locks immediately. ChatVault also locks itself after a period of inactivity. You can replay this tour from the ? button." }
];
let tour = null;
function endTour(done) {
  if (!tour) return; tour.hole.remove(); tour.card.remove(); removeEventListener("resize", tour.onResize); document.removeEventListener("keydown", tour.onKey);
  if (done !== false && S.user) { const t = sget(K.toured, {}); t[S.user.username] = true; sset(K.toured, t); }
  tour = null;
}
function startTour() {
  endTour(false); closeMenus(); closeDrawer();
  const steps = TOUR.filter(s => s.pane !== "chat" || S.active);
  const hole = h('<div class="tour-hole" aria-hidden="true"></div>');
  const card = h('<div class="tour-card" role="dialog" aria-modal="true" aria-labelledby="tourT"></div>');
  document.body.append(hole, card);
  tour = { i: 0, hole, card, steps };
  const place = () => {
    const st = steps[tour.i]; const el = $(st.sel);
    const r = el && el.offsetParent !== null ? el.getBoundingClientRect() : null;
    const vis = r && r.width > 0 && r.height > 0;
    if (vis) { const p = 6; Object.assign(hole.style, { left: r.left - p + "px", top: r.top - p + "px", width: r.width + 2 * p + "px", height: r.height + 2 * p + "px", opacity: 1 }); }
    else Object.assign(hole.style, { left: "50%", top: "50%", width: "0px", height: "0px" });
    const cw = card.offsetWidth, ch = card.offsetHeight, m = 14;
    let x, y;
    if (!vis) { x = (innerWidth - cw) / 2; y = (innerHeight - ch) / 2; }
    else if (r.right + m + cw < innerWidth && r.height > 120) { x = r.right + m; y = r.top + 8; }
    else if (r.bottom + m + ch < innerHeight) { x = r.left + r.width / 2 - cw / 2; y = r.bottom + m; }
    else if (r.top - m - ch > 0) { x = r.left + r.width / 2 - cw / 2; y = r.top - m - ch; }
    else if (r.left - m - cw > 0) { x = r.left - m - cw; y = r.top + 8; }
    else { x = (innerWidth - cw) / 2; y = innerHeight - ch - 16; }
    card.style.left = Math.max(12, Math.min(x, innerWidth - cw - 12)) + "px"; card.style.top = Math.max(12, Math.min(y, innerHeight - ch - 12)) + "px";
  };
  const go = async i => {
    tour.i = i; const st = steps[i];
    if (innerWidth <= 760) { $("#shell")?.classList.toggle("show-chat", st.pane === "chat"); await sleep(300); }
    card.innerHTML = `<div class="tour-step">${i + 1} of ${steps.length}</div><h3 id="tourT">${st.title}</h3><p>${st.body}</p>
      <div class="tour-foot"><button class="btn btn-ghost btn-sm" data-t="skip">${i === steps.length - 1 ? "Close" : "Skip tour"}</button><span style="flex:1"></span>
      ${i ? '<button class="btn btn-ghost btn-sm" data-t="back">Back</button>' : ""}<button class="btn btn-primary btn-sm" data-t="next">${i === steps.length - 1 ? "Finish" : "Next"}</button></div>`;
    place(); $("[data-t=next]", card).focus();
  };
  card.onclick = e => { const b = e.target.closest("[data-t]"); if (!b) return; const t = b.dataset.t; if (t === "skip") endTour(); else if (t === "back") go(tour.i - 1); else if (tour.i === steps.length - 1) endTour(); else go(tour.i + 1); };
  tour.onResize = () => tour && place(); addEventListener("resize", tour.onResize);
  tour.onKey = e => { if (!tour) return; if (e.key === "Escape") endTour(); if (e.key === "ArrowRight" && tour.i < steps.length - 1) go(tour.i + 1); if (e.key === "ArrowLeft" && tour.i > 0) go(tour.i - 1); };
  document.addEventListener("keydown", tour.onKey);
  go(0);
}

/* ============================================================ session: lock, idle, sign out */
function lockScreen() {
  if (S.locked || !S.user) return; S.locked = true; audit("Screen locked");
  closeMenus(); $$(".lightbox,.overlay").forEach(x => x.remove()); audioEl?.pause();
  const ov = h(`<div class="auth" style="z-index:95;background:color-mix(in srgb,var(--bg) 82%,transparent);backdrop-filter:blur(18px)"><form class="modal" style="width:min(380px,100%)" novalidate>
    <div class="center"><span class="avatar lg" style="--h:${hueOf(S.user.username)}">${esc(initials(S.user.name))}</span><h2>${esc(S.user.name)}</h2><span class="muted">${ic("lock", "i")} ChatVault is locked</span></div>
    <div class="modal-body"><div class="field"><label for="lkPw">Password</label><input class="input" id="lkPw" type="password" autocomplete="current-password"></div><div class="err" id="lkErr"></div>
    <button class="btn btn-primary" type="submit">Unlock</button><button class="btn btn-ghost" type="button" id="lkOut">Sign out instead</button></div></form></div>`);
  document.body.append(ov); setTimeout(() => $("#lkPw", ov)?.focus(), 50);
  $("#lkOut", ov).onclick = () => { ov.remove(); S.locked = false; signOut(); };
  $("form", ov).onsubmit = async e => {
    e.preventDefault();
    try { const name = S.user.username; await login(name, $("#lkPw", ov).value); S.locked = false; S.lastActivity = Date.now(); ov.remove(); }
    catch (x) { $("#lkErr", ov).textContent = x.message; const f = $("form", ov); f.classList.remove("shake"); void f.offsetWidth; f.classList.add("shake"); }
  };
}
function signOut() {
  audit("Signed out"); S.user = null; S.vaultKey = null; S.drawer = null; audioEl?.pause(); endTour();
  $$(".lightbox,.overlay,.menu").forEach(x => x.remove());
  // drop decrypted media from memory on sign-out
  for (const c of S.chats) for (const f of (c.media ? c.media.values() : [])) if (f.url) { URL.revokeObjectURL(f.url); f.url = null; }
  S.chats = []; S.active = null; renderAuth();
}
["pointerdown", "keydown", "wheel", "touchstart"].forEach(ev => addEventListener(ev, () => { if (!S.locked) S.lastActivity = Date.now(); }, { passive: true }));
setInterval(() => { if (S.user && !S.locked && Date.now() - S.lastActivity > settings().idleMin * 60000) lockScreen(); }, 15000);

/* drag and drop anywhere */
let dz = null, dragDepth = 0;
addEventListener("dragenter", e => { if (!S.user || S.locked || !can("import") || !e.dataTransfer?.types?.includes("Files")) return; e.preventDefault(); dragDepth++; if (!dz) { dz = h(`<div class="dropzone"><div>${ic("upload")}<span>Drop the WhatsApp export</span><span class="faint" style="font-weight:400;font-size:13px">.zip with media, or .txt</span></div></div>`); document.body.append(dz); } });
addEventListener("dragover", e => { if (dz) e.preventDefault(); });
addEventListener("dragleave", () => { if (dz && --dragDepth <= 0) { dz.remove(); dz = null; dragDepth = 0; } });
addEventListener("drop", e => { if (!dz) return; e.preventDefault(); dz.remove(); dz = null; dragDepth = 0; const fs = [...e.dataTransfer.files]; if (fs.length > 1) bulkImport(fs); else if (fs[0]) importFile(fs[0]); });
/* ============================================================ bulk import */
async function bulkImport(files) {
  if (!can("import")) return toast("Your role cannot import chats", "err");
  files = files.filter(f => /\.(zip|txt)$/i.test(f.name));
  if (!files.length) return toast("Choose .zip or .txt files exported from WhatsApp", "err");
  const ov = h(`<div class="overlay"><div class="modal wide" role="dialog" aria-modal="true" aria-labelledby="bqT"><div class="modal-head"><h3 id="bqT">Import ${files.length} chats</h3><button class="icon-btn" data-x aria-label="Close">${ic("close")}</button></div>
    <div class="modal-body"><label class="check"><input type="checkbox" id="bqMerge" checked><span><b>Merge repeat exports automatically</b><br>Exports of a chat you already have, or of the same chat within this batch, are merged instead of imported twice.</span></label>
      <div class="bq-list">${files.map((f, i) => `<div class="bq-row" data-i="${i}"><span class="ext zip">${/\.txt$/i.test(f.name) ? "TXT" : "ZIP"}</span><span class="bq-n"><b>${esc(f.name)}</b><span>${fmtBytes(f.size)}</span></span><span class="bq-s faint">Waiting</span></div>`).join("")}</div>
      <p class="note" style="margin:0">Your side of each chat is detected automatically. You can change it later in chat info.</p></div>
    <div class="modal-foot"><button class="btn btn-ghost" data-x>Cancel</button><button class="btn btn-primary" id="bqGo">${ic("upload")}Start import</button></div></div></div>`);
  document.body.append(ov);
  let running = false;
  $$("[data-x]", ov).forEach(b => b.onclick = () => { if (!running) ov.remove(); });
  $("#bqGo", ov).onclick = async () => {
    running = true; const auto = $("#bqMerge", ov).checked; $("#bqGo", ov).disabled = true; $$("[data-x]", ov).forEach(b => b.disabled = true);
    let ok = 0, merged = 0, bad = 0;
    for (const [i, f] of files.entries()) {
      const row = $(`.bq-row[data-i="${i}"] .bq-s`, ov); row.className = "bq-s"; row.innerHTML = `<span class="dots"><i></i><i></i><i></i></span>`;
      const r = await importFile(f, { bulk: true, autoMerge: auto });
      if (!r) { bad++; row.className = "bq-s err-t"; row.textContent = S.lastImportError || "Failed"; }
      else if (r._lastAction === "merged") { merged++; row.className = "bq-s ok-t"; row.textContent = `Merged into “${r.title}”`; }
      else if (r._lastAction === "duplicate") { row.className = "bq-s faint"; row.textContent = "Already imported"; }
      else { ok++; row.className = "bq-s ok-t"; row.textContent = `${r.messages.length} messages · ${r.linked} attachments`; }
    }
    $("#bqT", ov).textContent = `Imported ${ok} · merged ${merged}${bad ? ` · ${bad} failed` : ""}`;
    $(".modal-foot", ov).innerHTML = `<button class="btn btn-primary" data-x>Done</button>`; $$("[data-x]", ov).forEach(b => { b.disabled = false; b.onclick = () => ov.remove(); });
    audit("Bulk import", `${files.length} files · ${ok} new · ${merged} merged · ${bad} failed`);
    renderList(); updateFoot(); running = false;
  };
}

/* ============================================================ appearance */
const ACCENTS = [["teal", "Vault teal", "#0d7a65"], ["indigo", "Indigo", "#4b4fc4"], ["ocean", "Ocean", "#0a6fb0"], ["maroon", "Maroon", "#9b2747"], ["saffron", "Saffron", "#b8620d"], ["graphite", "Graphite", "#3d4a52"]];
const HOST_THEME = document.documentElement.getAttribute("data-theme");
const appearance = () => Object.assign({ mode: "system", accent: "teal", wallpaper: "classic" }, sget("cv.appearance", {}));
function applyAppearance() {
  const a = appearance(), r = document.documentElement;
  if (a.mode === "system") { HOST_THEME ? r.setAttribute("data-theme", HOST_THEME) : r.removeAttribute("data-theme"); } else r.setAttribute("data-theme", a.mode);
  a.accent === "teal" ? r.removeAttribute("data-accent") : r.setAttribute("data-accent", a.accent);
  a.wallpaper === "classic" ? r.removeAttribute("data-wall") : r.setAttribute("data-wall", a.wallpaper);
}
function openAppearance(anchor) {
  closeMenus(); $$(".cal-pop").forEach(x => x.remove());
  const pop = h(`<div class="cal-pop look-pop" role="dialog" aria-label="Appearance"></div>`); document.body.append(pop);
  const draw = () => {
    const a = appearance();
    pop.innerHTML = `<b class="lp-h">Appearance</b>
      <span class="lp-l">Theme</span><div class="seg">${[["system", "System"], ["light", "Light"], ["dark", "Dark"]].map(([k, l]) => `<button data-mode="${k}" class="${a.mode === k ? "on" : ""}">${l}</button>`).join("")}</div>
      <span class="lp-l">Colour</span><div class="swatches">${ACCENTS.map(([k, l, c]) => `<button data-acc="${k}" class="sw${a.accent === k ? " on" : ""}" style="--sw:${c}" title="${l}" aria-label="${l}"><i></i><span>${l}</span></button>`).join("")}</div>
      <span class="lp-l">Chat background</span><div class="seg">${[["classic", "Pattern"], ["plain", "Plain"], ["tint", "Tinted"]].map(([k, l]) => `<button data-wall="${k}" class="${a.wallpaper === k ? "on" : ""}">${l}</button>`).join("")}</div>`;
  };
  pop.onclick = e => {
    e.stopPropagation(); const a = appearance();
    const m = e.target.closest("[data-mode]"), c = e.target.closest("[data-acc]"), w = e.target.closest("[data-wall]");
    if (m) a.mode = m.dataset.mode; if (c) a.accent = c.dataset.acc; if (w) a.wallpaper = w.dataset.wall;
    if (m || c || w) { sset("cv.appearance", a); applyAppearance(); draw(); }
  };
  draw();
  const r = anchor.getBoundingClientRect();
  pop.style.left = Math.max(8, Math.min(r.left, innerWidth - pop.offsetWidth - 8)) + "px";
  pop.style.top = (r.top - pop.offsetHeight - 8 > 8 ? r.top - pop.offsetHeight - 8 : Math.min(r.bottom + 8, innerHeight - pop.offsetHeight - 8)) + "px";
  setTimeout(() => document.addEventListener("click", function off(e) { if (!pop.contains(e.target)) { pop.remove(); document.removeEventListener("click", off); } }), 0);
}
applyAppearance();

/* ============================================================ privacy screen */
function privacyOn() {
  if ($(".privacy")) return;
  audioEl?.pause(); $$("video").forEach(v => v.pause());
  const p = h(`<div class="privacy" role="dialog" aria-modal="true" aria-label="Privacy screen" tabindex="-1"><div class="pv-card">${ic("shade")}<b>Privacy screen</b><span>Click anywhere or press any key to continue</span></div></div>`);
  document.body.append(p); p.focus();
  const off = () => { p.remove(); removeEventListener("keydown", key, true); };
  const key = e => { e.preventDefault(); e.stopPropagation(); off(); };
  p.onclick = off; setTimeout(() => addEventListener("keydown", key, true), 50);
}
document.addEventListener("click", e => { if (e.target.closest("[data-privacy]")) privacyOn(); });
addEventListener("blur", () => { if (S.user && !S.locked && settings().privacyOnBlur) privacyOn(); });

/* ============================================================ keyboard shortcuts */
const SHORTCUTS = [["Ctrl + K", "Search all chats"], ["/", "Search in this chat"], ["C", "Calendar: jump to a date"], ["E", "Export"], ["S", "Star the message under the pointer"], ["N", "Note on the message under the pointer"],
  ["Q", "Copy citation of the message under the pointer"], ["I", "Chat info and integrity"], ["Ctrl + .", "Privacy screen"], ["Ctrl + Shift + L", "Lock"], ["Esc", "Close panel"], ["?", "This list"]];
function showShortcuts() {
  const ov = h(`<div class="overlay"><div class="modal" role="dialog" aria-modal="true" aria-labelledby="kbT"><div class="modal-head"><h3 id="kbT">Keyboard shortcuts</h3><button class="icon-btn" data-x aria-label="Close">${ic("close")}</button></div>
    <div class="modal-body"><div class="kb-list">${SHORTCUTS.map(([k, d]) => `<span class="kb">${k.split(" + ").map(x => `<kbd>${x}</kbd>`).join(" + ")}</span><span>${d}</span>`).join("")}</div></div></div></div>`);
  document.body.append(ov); $("[data-x]", ov).onclick = () => ov.remove(); ov.onclick = e => { if (e.target === ov) ov.remove(); };
}
addEventListener("keydown", e => {
  if (!S.user || S.locked || $(".privacy")) return;
  const k = e.key, typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName) || document.activeElement?.isContentEditable;
  const modal = $(".overlay,.lightbox,.tour-card");
  if ((e.ctrlKey || e.metaKey) && k === ".") { e.preventDefault(); return privacyOn(); }
  if ((e.ctrlKey || e.metaKey) && e.shiftKey && k.toLowerCase() === "l") { e.preventDefault(); return lockScreen(); }
  if ((e.ctrlKey || e.metaKey) && k.toLowerCase() === "k") { e.preventDefault(); $("#shell")?.classList.remove("show-chat"); return $("#chatFilter")?.focus(); }
  if ((e.ctrlKey || e.metaKey) && k.toLowerCase() === "f" && S.active) { e.preventDefault(); return openDrawer("search"); }
  if (k === "Escape") { $$(".cal-pop").forEach(x => x.remove()); if (S.drawer && !modal) closeDrawer(); return; }
  if (typing || modal || e.ctrlKey || e.metaKey || e.altKey) return;
  const chat = activeChat(); const hm = chat && S.hoverMsg ? chat.messages.find(m => m.id === S.hoverMsg) : null;
  if (k === "?") { e.preventDefault(); showShortcuts(); }
  else if (!chat) return;
  else if (k === "/") { e.preventDefault(); openDrawer("search"); }
  else if (k === "c" || k === "C") openCalendar($("#cCal")?.offsetParent ? $("#cCal") : $("#cMore"));
  else if (k === "e" || k === "E") openExport();
  else if (k === "i" || k === "I") toggleDrawer("info");
  else if ((k === "s" || k === "S") && hm) toggleStar(chat, hm);
  else if ((k === "n" || k === "N") && hm) { e.preventDefault(); editNote(chat, hm); }
  else if ((k === "q" || k === "Q") && hm) copyText(citationFor(chat, hm));
});


/* boot */
window.ChatVault = { parseChat }; // exposed for testing
renderAuth();
})();
