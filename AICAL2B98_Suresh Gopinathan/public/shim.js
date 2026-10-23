/* TickTrail self-hosted: provides the page's database, user, upload and download services from this server. */
(() => {
"use strict";
const BOOT = window.__TT_BOOT || {};
const err = (code, message) => Object.assign(new Error(message || code), { code });

async function api(method, url, body){
  const opt = { method, credentials: "same-origin", headers: { "X-TickTrail": "1" } };
  if(body !== undefined){ opt.headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(body); }
  let r;
  try{ r = await fetch(url, opt); }catch(e){ throw err("unavailable", "The server could not be reached. Check the connection."); }
  if(r.status === 401){ location.href = "/login?expired=1"; throw err("unauthenticated", "Please log in again."); }
  const j = await r.json().catch(() => ({}));
  if(!r.ok) throw err(j.code || "unavailable", j.message || "The server answered " + r.status + ".");
  return j;
}

// ------------------------------------------------------------ database
const SEG = /^[A-Za-z0-9_\-.~:@+]{1,200}$/;
function check(path, wantDoc){
  const s = String(path).split("/");
  if(!s.every(x => SEG.test(x) && x !== "." && x !== "..") || (wantDoc ? s.length % 2 : !(s.length % 2))) throw new TypeError("Bad " + (wantDoc ? "document" : "collection") + " path: " + path);
  return s;
}
const parentOf = p => p.split("/").slice(0, -1).join("/");
const lastOf = p => p.split("/").pop();
const META = Object.freeze({ fromCache: false, hasPendingWrites: false });
const clone = x => x === undefined ? undefined : JSON.parse(JSON.stringify(x));
function docSnap(id, data){
  const exists = data !== null && data !== undefined;
  return Object.freeze({ id, exists, data: () => exists ? clone(data) : undefined, metadata: META });
}
function querySnap(entries, prevIds){
  const ids = [...entries.keys()].sort();
  const docs = ids.map(id => docSnap(id, entries.get(id).data));
  return Object.freeze({ docs, size: docs.length, empty: !docs.length, metadata: META,
    docChanges: () => docs.map((d, i) => ({ type: prevIds && prevIds.includes(d.id) ? "modified" : "added", doc: d, oldIndex: prevIds ? prevIds.indexOf(d.id) : -1, newIndex: i })) });
}

const versions = new Map();          // path -> newest version seen
const docSubs = new Map();           // doc path -> Set of subscriptions
const collSubs = new Map();          // collection path -> Set of subscriptions

function fresh(path, v){ const cur = versions.get(path) || 0; if(v && v < cur) return false; if(v) versions.set(path, v); return true; }
function deliver(path, v, data){
  if(!fresh(path, v)) return;
  (docSubs.get(path) || []).forEach(s => s.apply(data));
  (collSubs.get(parentOf(path)) || []).forEach(s => s.apply(lastOf(path), data));
}

function subscribeDoc(path, next, onErr){
  const sub = { dead: false, last: undefined,
    apply(data){ if(this.dead) return; const t = JSON.stringify(data ?? null); if(t === this.last) return; this.last = t; try{ next(docSnap(lastOf(path), data)); }catch(e){ console.error(e); } },
    load(){ return api("GET", "/api/doc?p=" + encodeURIComponent(path)).then(r => { if(r.exists) fresh(path, r.v); this.apply(r.exists ? r.data : null); })
      .catch(e => { if(!this.dead && onErr){ this.dead = true; onErr(e); } }); } };
  if(!docSubs.has(path)) docSubs.set(path, new Set());
  docSubs.get(path).add(sub); sub.load();
  return () => { sub.dead = true; docSubs.get(path)?.delete(sub); };
}
function subscribeColl(path, next, onErr){
  const sub = { dead: false, entries: new Map(), ready: false, prevIds: null,
    emit(){ if(this.dead || !this.ready) return; const snap = querySnap(this.entries, this.prevIds); this.prevIds = snap.docs.map(d => d.id); try{ next(snap); }catch(e){ console.error(e); } },
    apply(id, data){ if(this.dead) return; const had = this.entries.get(id);
      if(data === null || data === undefined){ if(!had) return; this.entries.delete(id); }
      else { if(had && JSON.stringify(had.data) === JSON.stringify(data)) return; this.entries.set(id, { data }); }
      this.emit(); },
    load(){ return api("GET", "/api/list?c=" + encodeURIComponent(path)).then(r => {
        const m = new Map(); r.docs.forEach(d => { fresh(path + "/" + d.id, d.v); m.set(d.id, { data: d.data }); });
        const same = this.ready && m.size === this.entries.size && [...m].every(([k, x]) => JSON.stringify(this.entries.get(k)?.data) === JSON.stringify(x.data));
        this.entries = m; this.ready = true; if(!same) this.emit(); })
      .catch(e => { if(!this.dead && onErr){ this.dead = true; onErr(e); } }); } };
  if(!collSubs.has(path)) collSubs.set(path, new Set());
  collSubs.get(path).add(sub); sub.load();
  return () => { sub.dead = true; collSubs.get(path)?.delete(sub); };
}
function resyncAll(){ docSubs.forEach(set => set.forEach(s => s.load())); collSubs.forEach(set => set.forEach(s => s.load())); }

async function write(op, path, data){
  const r = await api("POST", "/api/write", { op, p: path, data });
  deliver(path, r.v, r.data);
}
function docRef(path){
  check(path, true);
  return Object.freeze({ id: lastOf(path), path,
    get: () => api("GET", "/api/doc?p=" + encodeURIComponent(path)).then(r => docSnap(lastOf(path), r.exists ? r.data : null)),
    set: data => write("set", path, data),
    update: data => write("update", path, data),
    delete: () => write("delete", path),
    onSnapshot: (next, onErr) => subscribeDoc(path, next, onErr),
    collection: sub => collRef(path + "/" + sub) });
}
function collRef(path){
  check(path, false);
  const get = () => api("GET", "/api/list?c=" + encodeURIComponent(path)).then(r => { const m = new Map(); r.docs.forEach(d => m.set(d.id, { data: d.data })); return querySnap(m, null); });
  const unsupported = () => { throw err("invalid_argument", "Filtered queries are not used by TickTrail."); };
  return Object.freeze({ path, get,
    doc: id => docRef(path + "/" + (id || crypto.randomUUID().replace(/-/g, "").slice(0, 20))),
    add: async data => { const ref = docRef(path + "/" + crypto.randomUUID().replace(/-/g, "").slice(0, 20)); await ref.set(data); return ref; },
    onSnapshot: (next, onErr) => subscribeColl(path, next, onErr),
    where: unsupported, orderBy: unsupported, limit: unsupported });
}
const DB = Object.freeze({ doc: docRef, collection: collRef });

// live updates from the server
let es = null, opened = false;
function connect(){
  es = new EventSource("/api/events", { withCredentials: true });
  es.addEventListener("open", () => { if(opened) resyncAll(); opened = true; });
  es.addEventListener("change", e => { try{ const m = JSON.parse(e.data); deliver(m.path, m.v, m.data); }catch(x){ console.error(x); } });
  es.addEventListener("resync", () => resyncAll());
  es.addEventListener("error", () => {
    // a lost session shows up as a failed stream: check once, and go to the login page if needed
    if(es.readyState === EventSource.CLOSED){ api("GET", "/api/me").then(() => setTimeout(connect, 3000)).catch(() => {}); }
  });
}
connect();
// when the tab wakes up after sleep, catch up on anything missed
document.addEventListener("visibilitychange", () => { if(document.visibilityState === "visible") api("GET", "/api/me").then(resyncAll).catch(() => {}); });

// ------------------------------------------------------------ people
const ME = Object.freeze({ ...BOOT.me });
const USER = Object.freeze({
  id: async () => ME.id,
  me: async () => ME,
  isOwner: () => !!ME.isOwner,
  canEdit: () => !!ME.canEdit,
  can: () => null,
  profiles: async ids => { ids = [...new Set(ids || [])]; if(!ids.length) return {}; return api("GET", "/api/profiles?ids=" + encodeURIComponent(ids.join(","))); },
  search: async () => [],
});

// ------------------------------------------------------------ PDF attachments
const ASSETS = Object.freeze({
  upload: async (blob, opts = {}) => {
    const type = opts.type || blob.type || "application/pdf";
    let r;
    try{ r = await fetch("/api/assets", { method: "POST", credentials: "same-origin", body: blob,
      headers: { "X-TickTrail": "1", "Content-Type": type, "X-Filename": encodeURIComponent(blob.name || "document.pdf") } }); }
    catch(e){ throw err("unavailable", "The server could not be reached."); }
    if(r.status === 401){ location.href = "/login?expired=1"; throw err("unauthenticated"); }
    const j = await r.json().catch(() => ({}));
    if(!r.ok) throw err(j.code || "unavailable", j.message);
    return j;
  },
  list: () => api("GET", "/api/assets"),
  delete: id => api("DELETE", "/api/assets/" + encodeURIComponent(id)),
});

// ------------------------------------------------------------ downloads
const DOWNLOADS = Object.freeze({
  save: async ({ filename, data }) => {
    const blob = data instanceof Blob ? data : new Blob([data]);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = filename || "download"; a.rel = "noopener";
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  },
});

const SERVICES = { db: DB, user: USER, assets: ASSETS, downloads: DOWNLOADS };
window.claude = Object.freeze({ use: name => new Promise(res => setTimeout(() => res(SERVICES[name] || null), 0)) });
window.__TT_SELF = Object.freeze({ ownerId: BOOT.ownerId, me: ME, post: (url, body) => api("POST", url, body) });
})();
