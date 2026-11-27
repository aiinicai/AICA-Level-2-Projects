(function(){const o=Element.prototype.replaceChildren;Element.prototype.replaceChildren=function(...a){return o.apply(this,a.flat(Infinity).filter(x=>x!=null&&x!==false&&x!==""))};})();
/* CA Task Mitra front-end core. Each module has web/modules/<key>.js and registers itself with WD.mod(). */
const WD = { mods: {}, hooks: { assignment: [] }, S: null, route: null };
const $ = (s, e = document) => e.querySelector(s);
function h(tag, a, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(a || {})) {
    if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (k === "class") e.className = v;
    else if (v !== false && v != null) e.setAttribute(k, v === true ? "" : v);
  }
  kids.flat(9).forEach(c => e.append(c != null && c.nodeType ? c : c == null || c === false ? "" : String(c)));
  return e;
}
async function api(path, o = {}) {
  const r = await fetch("/api/" + path, { method: o.method || (o.body ? "POST" : "GET"), headers: { "Content-Type": "application/json" }, body: o.body ? JSON.stringify(o.body) : undefined });
  const t = await r.text(); let j = {}; try { j = JSON.parse(t) } catch (e) { j = { raw: t } }
  if (!r.ok) { if (r.status === 401 && WD.S) { WD.S = null; boot(); } throw new Error(j.error || r.statusText); }
  return j;
}
const post = (p, body = {}) => api(p, { body }), put = (p, body) => api(p, { method: "PUT", body });
function toast(m, err) { const t = h("div", { class: err ? "err" : "" }, m); $("#toast").append(t); setTimeout(() => t.remove(), err ? 6000 : 3000); }
async function act(fn, ok) { try { const r = await fn(); if (ok) toast(ok); return r; } catch (e) { toast(e.message, true); } }
const money = n => "₹" + Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 });
const badge = s => h("span", { class: "badge b-" + String(s).replace(/ /g, "-") }, s);
const on = (mod, sub) => { const m = WD.S.modules.find(x => x.key === mod); return !!(m && m.enabled && (!sub || m.subs[sub])); };
const isBoss = () => ["ca", "manager"].includes(WD.S.user.role), isCA = () => WD.S.user.role === "ca";
const opt = (rows, v = "id", l = "name") => rows.map(r => [r[v], r[l]]);

function modal(title, body, { wide } = {}) {
  const m = h("div", { class: "modal", onclick: e => e.target === m && m.remove() }, h("div", { class: "box" + (wide ? " wide" : "") }, h("div", { class: "row" }, h("h2", { style: "margin:0" }, title), h("span", { class: "sp" }), h("button", { class: "btn sec sm", onclick: () => m.remove() }, "Close")), body));
  document.body.append(m); m.close = () => m.remove(); return m;
}
/* fields: [{k,l,t:'text|number|date|select|textarea|checkbox|password',o:[[v,label]],req}] */
function formModal(title, fields, vals, onSave, saveLabel = "Save") {
  vals = vals || {}; const inputs = {};
  const body = h("div", {}, fields.map(f => {
    let i;
    if (f.t === "select") i = h("select", {}, h("option", { value: "" }, "—"), (f.o || []).map(([v, l]) => h("option", { value: v, selected: String(vals[f.k] ?? "") === String(v) }, l)));
    else if (f.t === "textarea") { i = h("textarea", {}); i.value = vals[f.k] ?? ""; }
    else if (f.t === "checkbox") i = h("input", { type: "checkbox", checked: vals[f.k] === undefined ? !!f.d : !!vals[f.k] });
    else { i = h("input", { type: f.t || "text", value: vals[f.k] ?? "" }); }
    inputs[f.k] = i; return h("div", { class: "f" }, h("label", {}, f.l + (f.req ? " *" : "")), i);
  }), h("button", { class: "btn", onclick: async () => {
    const d = {}; for (const f of fields) { const i = inputs[f.k]; d[f.k] = f.t === "checkbox" ? i.checked : i.value; if (f.req && !d[f.k]) return toast(f.l + " is required", true); }
    try { await onSave(d); m.close(); } catch (e) { toast(e.message, true); }
  } }, saveLabel));
  const m = modal(title, body); return m;
}
function table(cols, rows, onrow) {
  return h("div", { class: "tw" }, h("table", {}, h("thead", {}, h("tr", {}, cols.map(c => h("th", {}, c.l)))),
    h("tbody", {}, rows.length ? rows.map(r => h("tr", { class: onrow ? "click" : "", onclick: onrow ? e => { if (!e.target.closest("button,a,input")) onrow(r); } : null },
      cols.map(c => h("td", {}, c.f ? c.f(r) : r[c.k] ?? "")))) : h("tr", {}, h("td", { colspan: cols.length, class: "mut" }, "Nothing here yet.")))));
}
function stat(l, v) { return h("div", { class: "stat" }, h("b", {}, v), h("span", {}, l)); }
/* generic list + add/edit screen */
async function crud(el, { title, load, cols, fields, save, canEdit = true, extra }) {
  const draw = async () => {
    const rows = await load(); el.replaceChildren(h("div", { class: "row" }, h("h2", { style: "margin:0" }, title), h("span", { class: "sp" }), extra ? extra(draw) : "",
      canEdit && fields ? h("button", { class: "btn", onclick: () => formModal("Add " + title.toLowerCase(), fields, {}, async d => { await save(d); toast("Saved"); draw(); }) }, "+ Add") : ""),
      table(cols, rows, canEdit && fields ? r => formModal("Edit", fields, r, async d => { await save(d, r); toast("Saved"); draw(); }) : null));
  }; await draw();
}
/* dashboard box: wide = full width, order = position in the grid */
function dbox(title, kids, { wide, order = 5, right } = {}) { return h("div", { class: "dbox" + (wide ? " wide" : ""), style: "order:" + order }, h("h3", {}, title, h("span", { class: "sp" }), right || ""), kids); }
const kpi = (l, v, c = "") => h("div", { class: "kpi " + c }, h("b", {}, v), h("span", {}, l));
/* read a chosen CSV file as text (UTF-8, or Windows-1252 if Excel saved it that way) */
async function readCsv(file) { const buf = await file.arrayBuffer(); try { return new TextDecoder("utf-8", { fatal: true }).decode(buf); } catch (e) { return new TextDecoder("windows-1252").decode(buf); } }
const download = (name, text, type = "text/csv") => { const a = h("a", { href: URL.createObjectURL(new Blob([text], { type })), download: name }); a.click(); };

WD.mod = (key, def) => { WD.mods[key] = def; };
function loadScript(src) { return new Promise((res, rej) => { const s = h("script", { src }); s.onload = res; s.onerror = () => rej(new Error("load " + src)); document.body.append(s); }); }

/* ---------- login / setup ---------- */
async function boot() {
  const st = await api("auth/status");
  if (st.setup_needed) return setupScreen(st);
  try { WD.S = await api("auth/session"); } catch (e) { return loginScreen(st); }
  for (const m of WD.S.modules) if (m.status === "ready" && m.enabled && !WD.mods[m.key]) await loadScript(`/static/modules/${m.key}.js`).catch(() => {});
  shell();
}
function loginScreen(st) {
  const u = h("input", { placeholder: "Username", autofocus: true }), p = h("input", { type: "password", placeholder: "Password" });
  const go = async () => { try { await post("auth/login", { username: u.value, password: p.value }); boot(); } catch (e) { toast(e.message, true); } };
  p.addEventListener("keydown", e => e.key === "Enter" && go());
  $("#app").replaceChildren(h("div", { class: "login" }, h("h1", {}, "CA Task Mitra"), h("div", { class: "mut" }, st.firm), h("p", {}), h("div", { class: "f" }, u), h("div", { class: "f" }, p),
    h("button", { class: "btn", style: "width:100%", onclick: go }, "Sign in"), st.hint ? h("div", { class: "hint" }, st.hint) : ""));
}
function setupScreen() {
  const f = {}; const fld = (k, l, t = "text") => h("div", { class: "f" }, h("label", {}, l), f[k] = h("input", { type: t }));
  const demo = h("input", { type: "checkbox", checked: true });
  $("#app").replaceChildren(h("div", { class: "login" }, h("h1", {}, "Set up your office"), h("div", { class: "mut" }, "First launch – create the firm and its CA account."), h("p", {}),
    fld("firm", "Firm name"), fld("name", "Your name"), fld("username", "CA username"), fld("password", "Password (6+ characters)", "password"),
    h("div", { class: "f" }, h("label", {}, demo, " Load fictional demo data (recommended for testing)")),
    h("button", { class: "btn", style: "width:100%", onclick: async () => { try { await post("auth/setup", { firm: f.firm.value, name: f.name.value, username: f.username.value, password: f.password.value, demo: demo.checked }); toast("Office created – sign in"); boot(); } catch (e) { toast(e.message, true); } } }, "Create office"),
    h("div", { class: "hint" }, "Staff on other PCs do not install anything: they open this PC's address in a browser (shown in the black start window).")));
}

/* ---------- shell ---------- */
function shell() {
  const nav = []; const role = WD.S.user.role;
  for (const m of WD.S.modules) {
    const d = WD.mods[m.key]; if (!d || !m.enabled) continue;
    const items = (d.nav || []).filter(n => (!n.sub || m.subs[n.sub]) && (!n.roles || n.roles.includes(role)) && (!n.when || n.when()));
    if (items.length) nav.push([m, items]);
  }
  const first = nav[0] && nav[0][1][0];
  const side = h("div", { class: "side" },
    nav.map(([m, items]) => [h("div", { class: "grp" }, m.name), items.map(n => h("a", { "data-r": m.key + "/" + n.id, onclick: () => go(m.key, n.id) }, n.l))]));
  const top = h("div", { class: "top" }, h("span", { class: "brand" }, "CA Task Mitra"), h("span", { class: "firm" }, WD.S.firm),
    h("span", { class: "usr" }, h("span", {}, "👤 ", h("b", {}, WD.S.user.name), " (" + role + ")"),
      h("button", { class: "btn sec sm", onclick: () => startTour(true) }, "? Guide"), h("button", { class: "btn sec sm", onclick: changePw }, "Change password"),
      h("button", { class: "btn sec sm", onclick: async () => { await post("auth/logout"); WD.S = null; boot(); } }, "Sign out")));
  $("#app").replaceChildren(h("div", { class: "shell" }, top, h("div", { class: "body" }, side, h("div", { class: "content", id: "view" }))));
  const hash = location.hash.slice(1).split("/"); const ok = nav.some(([m, it]) => m.key === hash[0] && it.some(n => n.id === hash[1]));
  if (ok) go(hash[0], hash[1]); else if (first) go(nav[0][0].key, first.id);
  setTimeout(() => startTour(false), 700);
}
async function go(mod, id) {
  location.hash = mod + "/" + id; WD.route = [mod, id];
  document.querySelectorAll(".side a").forEach(a => a.classList.toggle("on", a.dataset.r === mod + "/" + id));
  const v = $("#view"); v.replaceChildren(h("p", { class: "mut" }, "Loading…"));
  try { await WD.mods[mod].views[id](v); } catch (e) { v.replaceChildren(h("div", { class: "card" }, h("b", {}, "Could not open this screen: "), e.message)); }
}
function changePw() {
  formModal("Change password", [{ k: "old", l: "Current password", t: "password", req: 1 }, { k: "new", l: "New password", t: "password", req: 1 }], {}, async d => { await post("admin/password", d); toast("Password changed"); });
}
window.addEventListener("load", boot);

/* ---------- first-run guide (skippable; restart from "? Guide") ---------- */
const TOUR_CA = [
  ["Welcome to CA Task Mitra", "A short guided tour of the main areas. You can skip at any time and restart it later with the “? Guide” button at the top.", null],
  ["1. Module manager", "Every feature is a module with switches. Turn modules and single features on or off here. Planned modules appear as “coming soon”.", ["admin", "modules"]],
  ["2. Firm settings", "Enter your firm name, the CA e-mail for alerts, the firm mailbox (SMTP), the n8n webhook and your Tally company here.", ["admin", "settings"]],
  ["3. Bulk import – set up a new office fast", "Upload CSV files for clients, employees, pending assignments and compliance applicability. Download the template, fill it in Excel, upload.", ["admin", "import"]],
  ["4. Create employee logins", "Create a username and password for each employee here. Use “Generate” for a strong password and share it with them.", ["admin", "users"]],
  ["5. Compliance", "Choose which compliance applies to which client (or import it), then generate assignments for a period. Duplicates are never created.", ["compliance", "gen"]],
  ["6. Assignments", "All work, grouped by status, service, employee or client. Click a group to open its list. Tick several tasks to submit, approve or close them together.", ["work", "assign"]],
  ["7. Billing", "When work is closed an invoice is created automatically and sent to Tally. If Tally is off, entries wait and go with the next bill.", ["finance", "inv"]],
  ["8. Dashboard", "Your morning view: work, employees in office, fees, compliance calendar, e-mails awaiting approval and announcements.", ["work", "dash"]],
  ["You are ready", "Tip: use “Load demo data” only for practice. Press “? Guide” whenever you need this tour again.", null]];
const TOUR_EMP = [
  ["Welcome", "A quick look at your workspace. Skip any time; restart with “? Guide”.", null],
  ["Your dashboard", "Your own work, new tasks from the CA, your compliance dates, e-mails and announcements.", ["work", "dash"]],
  ["My assignments", "Open a task to see the checklist and documents, update status, and submit it for review.", ["work", "assign"]],
  ["Attendance & timesheet", "Check in when you reach the office and log hours against tasks.", ["employee", "att"]]];
function startTour(force) {
  const key = "wd_tour_" + WD.S.user.id; if (!force && localStorage.getItem(key)) return;
  const steps = isCA() ? TOUR_CA : TOUR_EMP; let i = 0, t;
  const end = () => { try { localStorage.setItem(key, "1"); } catch (e) { } t && t.remove(); document.querySelectorAll(".pulse").forEach(x => x.classList.remove("pulse")); };
  const draw = () => {
    const [ti, tx, r] = steps[i]; if (r && WD.mods[r[0]]) go(r[0], r[1]);
    document.querySelectorAll(".pulse").forEach(x => x.classList.remove("pulse")); if (r) { const a = document.querySelector(`.side a[data-r="${r[0]}/${r[1]}"]`); a && (a.classList.add("pulse"), a.scrollIntoView({ block: "nearest" })); }
    t && t.remove(); t = h("div", { class: "tour" }, h("div", { class: "dots" }, `Step ${i + 1} of ${steps.length}`), h("h3", {}, ti), h("p", {}, tx),
      h("div", { class: "row", style: "margin:0" }, h("button", { class: "btn sec sm", onclick: end }, "Skip tour"), h("span", { class: "sp" }),
        i ? h("button", { class: "btn sec sm", onclick: () => { i--; draw(); } }, "Back") : "", h("button", { class: "btn sm", onclick: () => { if (i < steps.length - 1) { i++; draw(); } else end(); } }, i < steps.length - 1 ? "Next" : "Finish")));
    document.body.append(t);
  }; draw();
}
