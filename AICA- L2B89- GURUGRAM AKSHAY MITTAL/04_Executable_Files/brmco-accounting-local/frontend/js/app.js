// BRMCo Accounting Hub — Local Host UI (no framework, no build step).
const view = document.getElementById("view");

const KINDS = {
  sales:    { label: "Sales",        base: "/api/sales",         desc: "Sales invoices → Tally Sales vouchers" },
  purchase: { label: "Purchase",     base: "/api/purchase",      desc: "Supplier invoices → Tally Purchase vouchers" },
  journal:  { label: "Journal",      base: "/api/journal",       desc: "Journal entries (Debit must equal Credit)" },
  receipt:  { label: "Bank Receipt", base: "/api/bank/receipt",  desc: "Bank A/c Dr — To Party A/c" },
  payment:  { label: "Bank Payment", base: "/api/bank/payment",  desc: "Party/Expense A/c Dr — To Bank A/c" },
};

// ------------------------------------------------------------------ helpers
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const inrFmt = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const inr = (v) => (v === null || v === undefined || v === "") ? "" : "₹" + inrFmt.format(Number(v));
const fmtDate = (iso) => { if (!iso) return ""; const [y, m, d] = iso.slice(0, 10).split("-"); return `${d}-${m}-${y}`; };
const fmtTime = (iso) => iso ? `${fmtDate(iso)} ${iso.slice(11, 16)}` : "";
const badge = (text, cls) => `<span class="badge ${esc(cls || text)}">${esc(text)}</span>`;

function toast(msg, isError = false) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "toast" + (isError ? " error" : "");
  t.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (t.hidden = true), isError ? 7000 : 3500);
}

async function busy(button, fn) {
  const original = button.innerHTML;
  button.disabled = true;
  button.innerHTML = `<span class="spinner"></span> ${original}`;
  try { return await fn(); }
  catch (e) { toast(e.message, true); }
  finally { button.disabled = false; button.innerHTML = original; }
}

async function refreshChrome() {
  try {
    const info = await API.get("/api/app");
    document.getElementById("demo-banner").hidden = !info.demo_mode;
    document.getElementById("company-foot").innerHTML =
      `${esc(info.company_name || "Company not set")}<br>FY ${esc(info.financial_year)}<br>v${esc(info.version)}`;
  } catch (e) { /* shown elsewhere */ }
}

// ------------------------------------------------------------------ router
const routes = {
  dashboard: renderDashboard, tally: renderTally, masters: renderMasters, ledgers: renderLedgers,
  history: renderHistory, audit: renderAudit, settings: renderSettings,
};
Object.keys(KINDS).forEach((k) => (routes[k] = () => renderVoucherPage(k)));

async function route() {
  const name = (location.hash.replace(/^#\/?/, "").split("?")[0]) || "dashboard";
  document.querySelectorAll(".sidebar a").forEach((a) => a.classList.toggle("active", a.dataset.route === name));
  const render = routes[name] || renderDashboard;
  view.innerHTML = `<p class="muted"><span class="spinner"></span> Loading…</p>`;
  try { await render(); }
  catch (e) { view.innerHTML = `<div class="alert error">${esc(e.message)}</div>`; }
}
window.addEventListener("hashchange", route);

// ------------------------------------------------------------------ dashboard
async function renderDashboard() {
  const d = await API.get("/api/dashboard");
  const mc = d.master_counts || {};
  const hs = d.history_stats || {};
  view.innerHTML = `
    <h1>Dashboard</h1>
    <p class="sub">${esc(d.company_name || "Set up your company in Settings")} · FY ${esc(d.financial_year)}
      ${d.demo_mode ? badge("DEMO MODE", "demo") : ""}</p>
    <div class="grid">
      ${Object.entries(KINDS).map(([k, v]) => `
        <a class="tile" href="#/${k}"><div class="label">Accounting</div><div class="value">${esc(v.label)}</div>
        <div class="muted">${esc(v.desc)}</div></a>`).join("")}
      <a class="tile" href="#/tally"><div class="label">Tally Connection</div>
        <div class="value" id="dash-tally"><span class="spinner"></span></div>
        <div class="muted">${esc(d.demo_mode ? "Simulated (demo)" : d.tally_url)}</div></a>
      <a class="tile" href="#/masters"><div class="label">Cached masters</div>
        <div class="value">${(mc.ledger || {}).count || 0} ledgers</div>
        <div class="muted">${(mc.stock_item || {}).count || 0} items · ${(mc.group || {}).count || 0} groups</div></a>
      <a class="tile" href="#/history"><div class="label">Import History</div>
        <div class="value">${(hs.SUCCESS || 0)} ok · ${(hs.FAILED || 0) + (hs.PARTIAL || 0)} issues</div>
        <div class="muted">All posting attempts</div></a>
      <a class="tile" href="#/settings"><div class="label">Settings</div><div class="value">Configure</div>
        <div class="muted">Company, Tally, server, ledgers</div></a>
      <div class="tile"><div class="label">BRMCo Server</div><div class="value" id="dash-server"><span class="spinner"></span></div>
        <div class="muted" id="dash-server-sub"></div></div>
    </div>
    <div class="panel" style="margin-top:16px"><h2>Recent imports</h2>${historyTable(d.recent)}</div>`;
  API.get("/api/tally/status").then((s) => {
    document.getElementById("dash-tally").innerHTML = s.connected ? badge("Connected", "ok") : badge("Not connected", "error");
  }).catch(() => (document.getElementById("dash-tally").innerHTML = badge("Error", "error")));
  API.get("/api/server/status").then((s) => {
    document.getElementById("dash-server").innerHTML = s.reachable ? badge("Online", "ok") : badge("Offline", "warning");
    document.getElementById("dash-server-sub").textContent = s.reachable ? `v${(s.version || {}).version || ""}` : "Not needed in Phase 1";
  }).catch(() => (document.getElementById("dash-server").innerHTML = badge("Error", "error")));
}

// ------------------------------------------------------------------ voucher workflow
async function renderVoucherPage(kind) {
  const k = KINDS[kind];
  view.innerHTML = `
    <h1>${esc(k.label)}</h1>
    <p class="sub">${esc(k.desc)}</p>
    <div class="steps" id="steps"></div>
    <div class="panel">
      <h2>1. Download template</h2>
      <p class="muted">The template includes dropdowns for ledgers, items and units from the last Tally master sync.</p>
      <button class="secondary" id="btn-template">Download ${esc(k.label)} template</button>
      <button class="secondary" id="btn-sample" title="Filled example that matches the demo company's masters">Download filled sample</button>
    </div>
    <div class="panel">
      <h2>2. Upload filled Excel</h2>
      <div class="row">
        <input type="file" id="file" accept=".xlsx,.xlsm">
        <button id="btn-upload">Upload &amp; Validate</button>
      </div>
    </div>
    <div id="result"></div>`;
  setSteps(1);
  if (pendingBatch && pendingBatch.kind === kind) { showBatch(pendingBatch); }
  pendingBatch = null;
  document.getElementById("btn-template").onclick = (e) =>
    busy(e.currentTarget, async () => { await API.download(`${k.base}/template`); toast("Template downloaded"); });
  document.getElementById("btn-sample").onclick = (e) =>
    busy(e.currentTarget, async () => { await API.download(`${k.base}/sample`); toast("Sample downloaded"); });
  document.getElementById("btn-upload").onclick = (e) => busy(e.currentTarget, async () => {
    const f = document.getElementById("file").files[0];
    if (!f) throw new Error("Choose an Excel file first.");
    const batch = await API.upload(`${k.base}/upload`, f);
    showBatch(batch);
  });
}

function setSteps(current) {
  const names = ["Template", "Upload", "Validate", "Preview", "Post to Tally", "Result"];
  const el = document.getElementById("steps");
  if (el) el.innerHTML = names.map((n, i) =>
    `<span class="step ${i + 1 < current ? "done" : i + 1 === current ? "current" : ""}">${i + 1}. ${n}</span>`).join("");
}

function issuesTable(issues) {
  if (!issues.length) return `<div class="alert ok">No problems found.</div>`;
  return `<div class="table-wrap"><table>
    <thead><tr><th>Type</th><th>Row</th><th>Column</th><th>Voucher</th><th>Message</th></tr></thead>
    <tbody>${issues.map((i) => `<tr>
      <td>${badge(i.severity === "error" ? "Error" : "Warning", i.severity)}</td>
      <td>${esc(i.row ?? "")}</td><td>${esc(i.column ?? "")}</td><td>${esc(i.voucher ?? "")}</td>
      <td>${esc(i.message)}</td></tr>`).join("")}</tbody></table></div>`;
}

function voucherCard(v) {
  const head = [
    ["Voucher Type", v.voucher_type], ["Voucher No / Ref", v.label], ["Date", fmtDate(v.date)],
    v.party ? ["Party", v.party] : null, v.party_gstin ? ["GSTIN", v.party_gstin] : null,
    v.place_of_supply ? ["Place of Supply", v.place_of_supply] : null,
    v.taxable_value !== null ? ["Taxable Value", inr(v.taxable_value)] : null,
    Number(v.cgst) ? ["CGST", inr(v.cgst)] : null, Number(v.sgst) ? ["SGST", inr(v.sgst)] : null,
    Number(v.igst) ? ["IGST", inr(v.igst)] : null, Number(v.cess) ? ["Cess", inr(v.cess)] : null,
    Number(v.round_off) ? ["Round Off", inr(v.round_off)] : null,
    [v.taxable_value !== null ? "Invoice Total" : "Amount", inr(v.total)],
  ].filter(Boolean);
  return `<div class="voucher">
    <div class="voucher-head">${head.map(([k, val]) => `<div><span class="k">${esc(k)}</span><b>${esc(val)}</b></div>`).join("")}
      ${v.balanced ? "" : badge("Not balanced", "error")}</div>
    <table><thead><tr><th>Ledger / Item</th><th class="num">Debit</th><th class="num">Credit</th></tr></thead><tbody>
    ${v.entries.map((e) => `<tr>
      <td>${esc(e.ledger)}${e.stock_item ? ` <span class="muted">— ${esc(e.stock_item)} ${esc(e.quantity)} ${esc(e.unit)} @ ${esc(e.rate)}</span>` : ""}
        ${e.cost_centre ? ` <span class="muted">(CC: ${esc(e.cost_centre)})</span>` : ""}</td>
      <td class="num">${e.side === "Dr" ? inr(e.amount) : ""}</td>
      <td class="num">${e.side === "Cr" ? inr(e.amount) : ""}</td></tr>`).join("")}
    <tr><th>Total</th><th class="num">${inr(v.total_debit)}</th><th class="num">${inr(v.total_credit)}</th></tr>
    </tbody></table>
    ${v.narration ? `<div style="padding:6px 12px" class="muted">Narration: ${esc(v.narration)}</div>` : ""}
  </div>`;
}

function showBatch(b) {
  const box = document.getElementById("result");
  const ok = b.errors === 0;
  setSteps(ok ? 4 : 3);
  box.innerHTML = `
    <div class="panel">
      <h2>3. Validation — ${esc(b.file_name)}</h2>
      <p>${b.row_count} row(s) · ${b.voucher_count} voucher(s) ·
        ${badge(`${b.errors} error(s)`, b.errors ? "error" : "ok")} ${badge(`${b.warnings} warning(s)`, b.warnings ? "warning" : "ok")}</p>
      ${ok ? "" : `<div class="alert error">Fix the errors in Excel and upload again. Nothing can be posted from this file.</div>`}
      ${b.stale ? `<div class="alert warning">${esc(b.stale)}</div>` : ""}
      ${b.missing_ledgers ? `<div class="alert warning">Some ledgers used in this file don't exist in Tally.
        Review and create them in Tally, or correct the names in Excel.
        <div style="margin-top:8px"><a class="btn" href="#/ledgers?batch=${esc(b.id)}">Create missing ledgers in Tally</a></div></div>` : ""}
      ${issuesTable(b.issues)}
      ${ok ? "" : `<div style="margin-top:12px"><button class="secondary" id="btn-revalidate"
        title="Use after creating ledgers or changing Settings">Re-validate same file</button></div>`}
    </div>
    ${b.vouchers.length ? `<div class="panel">
      <h2>4. Preview accounting entries</h2>
      ${b.demo_mode ? `<div class="alert demo">DEMO MODE — No entry posted to Tally</div>` : ""}
      <p class="muted">Total Debit ${inr(b.totals.debit)} · Total Credit ${inr(b.totals.credit)}</p>
      ${b.vouchers.map(voucherCard).join("")}
      <div class="row" style="margin-top:12px">
        <button id="btn-post" ${b.can_post && !b.stale ? "" : "disabled"}>Confirm &amp; Post to Tally</button>
        <button class="secondary" id="btn-xml" ${ok ? "" : "disabled"}>Download XML</button>
      </div>
    </div>` : ""}
    <div id="post-result"></div>`;
  const reBtn = document.getElementById("btn-revalidate");
  if (reBtn) reBtn.onclick = (e) => busy(e.currentTarget, async () => showBatch(await API.post(`/api/batches/${b.id}/revalidate`)));
  const xmlBtn = document.getElementById("btn-xml");
  if (xmlBtn) xmlBtn.onclick = (e) => busy(e.currentTarget, async () => { await API.download(`/api/batches/${b.id}/xml`); toast("XML downloaded"); });
  const postBtn = document.getElementById("btn-post");
  if (postBtn) postBtn.onclick = (e) => {
    const where = b.demo_mode ? "the DEMO simulator (nothing reaches Tally)" : "TallyPrime";
    if (!confirm(`Post ${b.voucher_count} voucher(s) to ${where}?`)) return;
    busy(e.currentTarget, async () => {
      showPostResult(await API.post(`/api/batches/${b.id}/post`));
    });
  };
  box.scrollIntoView({ behavior: "smooth" });
}

function showPostResult(r) {
  setSteps(6);
  const cls = r.status === "SUCCESS" ? "ok" : r.status === "PARTIAL" ? "warning" : "error";
  document.getElementById("post-result").innerHTML = `
    <div class="panel">
      <h2>5. Tally response</h2>
      ${r.demo_mode ? `<div class="alert demo">DEMO MODE — No entry posted to Tally</div>` : ""}
      <div class="alert ${cls}"><b>Status: ${esc(r.status)}</b><br>${esc(r.message)}</div>
      <p>Created: <b>${r.created}</b> · Altered: <b>${r.altered}</b> · Ignored: <b>${r.ignored}</b> · Errors: <b>${r.errors}</b>
        · <a href="#/history">View in Import History</a></p>
      ${resultsTable(r.results)}
    </div>`;
}

function resultsTable(results) {
  return `<div class="table-wrap"><table><thead><tr><th>Voucher</th><th>Date</th><th class="num">Amount</th><th>Status</th><th>Tally message</th></tr></thead>
    <tbody>${(results || []).map((x) => `<tr><td>${esc(x.voucher)}</td><td>${fmtDate(x.date)}</td><td class="num">${inr(x.amount)}</td>
      <td>${badge(x.status)}</td><td>${esc(x.message)}</td></tr>`).join("")}</tbody></table></div>`;
}

// ------------------------------------------------------------------ create ledgers
let pendingBatch = null; // batch to show when returning to a voucher page after re-validation

async function renderLedgers() {
  const batchId = new URLSearchParams(location.hash.split("?")[1] || "").get("batch");
  const opts = await API.get("/api/tally/ledgers/options");
  const missing = batchId ? await API.get(`/api/batches/${encodeURIComponent(batchId)}/missing-ledgers`) : null;
  let rows = missing && missing.ledgers.length ? missing.ledgers : [{ name: "", parent: "", bill_wise: false }];
  const option = (list, sel, blank) => (blank ? `<option value="">${blank}</option>` : "") +
    list.map((v) => `<option ${v === sel ? "selected" : ""}>${esc(v)}</option>`).join("");

  view.innerHTML = `
    <h1>Create Ledgers</h1>
    <p class="sub">Ledgers are created in Tally only after you review them and click Create.
      ${missing ? `Pre-filled with the ledgers missing from <b>${esc(missing.file_name)}</b>. Check the group for each one.` : ""}</p>
    ${!opts.groups.length ? `<div class="alert warning">Groups are not synced yet. Go to <a href="#/masters">Master Sync</a> first so you can pick groups from a list.</div>` : ""}
    ${missing && !missing.ledgers.length ? `<div class="alert ok">No missing ledgers for this file. <button class="secondary" id="btn-back">Re-validate the file</button></div>` : ""}
    <div class="panel">
      <datalist id="groups">${opts.groups.map((g) => `<option value="${esc(g)}">`).join("")}</datalist>
      <div class="table-wrap"><table id="led-table">
        <thead><tr><th>Ledger name *</th><th>Under group *</th><th>Bill-wise</th><th>GST duty head<br><span class="muted">(tax ledgers)</span></th>
          <th>GST registration</th><th>GSTIN</th><th>State</th><th></th></tr></thead><tbody></tbody></table></div>
      <div class="row" style="margin-top:10px">
        <button class="secondary" id="btn-add">+ Add ledger</button>
        <button id="btn-create">Review &amp; Create in Tally</button>
      </div>
      <p class="muted" style="margin-top:10px">Tip: Output/Input GST ledgers go under <b>Duties &amp; Taxes</b> with duty head Central Tax / State Tax / Integrated Tax / Cess.
        Customers go under <b>Sundry Debtors</b>, suppliers under <b>Sundry Creditors</b>. If the ledger already exists in Tally under a different name,
        fix the name in Excel (or in Settings for GST/round-off ledgers) instead of creating a duplicate.</p>
    </div>
    <div id="led-result"></div>`;

  const tbody = document.querySelector("#led-table tbody");
  const draw = () => {
    tbody.innerHTML = rows.map((r, i) => `<tr data-i="${i}">
      <td><input data-f="name" value="${esc(r.name)}" style="min-width:200px">${r.used_in ? `<div class="muted" style="font-size:11px">used in: ${esc(r.used_in)}${r.row ? `, row ${r.row}` : ""}</div>` : ""}</td>
      <td><input data-f="parent" list="groups" value="${esc(r.parent)}" placeholder="Choose group" style="min-width:170px"></td>
      <td><input type="checkbox" data-f="bill_wise" ${r.bill_wise ? "checked" : ""}></td>
      <td><select data-f="gst_duty_head">${option(opts.duty_heads, r.gst_duty_head, "—")}</select></td>
      <td><select data-f="gst_registration_type">${option(opts.registration_types, r.gst_registration_type, "—")}</select></td>
      <td><input data-f="gstin" value="${esc(r.gstin)}" style="width:150px"></td>
      <td><select data-f="state">${option(opts.states, r.state, "—")}</select></td>
      <td><button class="secondary" data-del="${i}" title="Remove">✕</button></td></tr>`).join("");
    tbody.querySelectorAll("[data-del]").forEach((b) => (b.onclick = () => { collect(); rows.splice(+b.dataset.del, 1); draw(); }));
  };
  const collect = () => {
    rows = [...tbody.querySelectorAll("tr")].map((tr) => {
      const get = (f) => tr.querySelector(`[data-f="${f}"]`);
      return { ...rows[+tr.dataset.i], name: get("name").value.trim(), parent: get("parent").value.trim(),
        bill_wise: get("bill_wise").checked, gst_duty_head: get("gst_duty_head").value || null,
        gst_registration_type: get("gst_registration_type").value || null, gstin: get("gstin").value.trim() || null,
        state: get("state").value || null };
    });
    return rows;
  };
  draw();

  const revalidate = async () => {
    const batch = await API.post(`/api/batches/${encodeURIComponent(batchId)}/revalidate`);
    pendingBatch = batch;
    location.hash = `#/${batch.kind}`;
  };
  const back = document.getElementById("btn-back");
  if (back) back.onclick = () => busy(back, revalidate);
  document.getElementById("btn-add").onclick = () => { collect(); rows.push({ name: "", parent: "", bill_wise: false }); draw(); };
  document.getElementById("btn-create").onclick = (e) => {
    const list = collect().filter((r) => r.name);
    if (!list.length) return toast("Enter at least one ledger name.", true);
    const missingGroup = list.find((r) => !r.parent);
    if (missingGroup) return toast(`Choose a group for "${missingGroup.name}".`, true);
    const summary = list.map((r) => `• ${r.name}  →  ${r.parent}${r.gst_duty_head ? " (" + r.gst_duty_head + ")" : ""}`).join("\n");
    if (!confirm(`Create ${list.length} ledger(s) in ${opts.demo_mode ? "the demo company" : "Tally"}?\n\n${summary}`)) return;
    busy(e.currentTarget, async () => {
      const payload = list.map(({ name, parent, bill_wise, gst_duty_head, gst_registration_type, gstin, state }) =>
        ({ name, parent, bill_wise, gst_duty_head, gst_registration_type, gstin, state }));
      const r = await API.post("/api/tally/ledgers", { ledgers: payload });
      const cls = r.status === "SUCCESS" ? "ok" : r.status === "PARTIAL" ? "warning" : "error";
      document.getElementById("led-result").innerHTML = `<div class="panel"><h2>Tally response</h2>
        ${r.demo_mode ? `<div class="alert demo">DEMO MODE — created in the demo company only</div>` : ""}
        <div class="alert ${cls}"><b>Status: ${esc(r.status)}</b> — ${r.created} of ${r.results.length} ledger(s) created.
          ${r.resynced ? "Ledger list re-synced from Tally." : ""}</div>
        <table><thead><tr><th>Ledger</th><th>Status</th><th>Message</th></tr></thead><tbody>
        ${r.results.map((x) => `<tr><td>${esc(x.name)}</td><td>${badge(x.status)}</td><td>${esc(x.message)}</td></tr>`).join("")}</tbody></table>
        ${batchId && r.created ? `<div style="margin-top:12px"><button id="btn-reval">Re-validate ${esc(missing.file_name)}</button></div>` : ""}</div>`;
      const rv = document.getElementById("btn-reval");
      if (rv) rv.onclick = () => busy(rv, revalidate);
      const failedNames = new Set(r.results.filter((x) => x.status !== "SUCCESS").map((x) => x.name));
      rows = rows.filter((x) => failedNames.has(x.name));
      if (!rows.length) rows = [{ name: "", parent: "", bill_wise: false }];
      draw();
    });
  };
}

// ------------------------------------------------------------------ tally
async function renderTally() {
  const { settings: s } = await API.get("/api/settings");
  view.innerHTML = `
    <h1>Tally Connection</h1>
    <p class="sub">${s.demo_mode ? "Demo mode is ON — Tally is simulated." : `TallyPrime XML server at http://${esc(s.tally_host)}:${esc(s.tally_port)}`}</p>
    <div class="panel">
      <div class="status-line" id="tally-status"><span class="dot"></span> Not tested yet</div>
      <p id="tally-detail" class="muted"></p>
      <button id="btn-test">Test Tally Connection</button>
      <a class="btn secondary" href="#/settings">Change host / port</a>
    </div>
    <div class="panel"><h2>Checklist if not connected</h2><ol class="muted">
      <li>TallyPrime is open and the company <b>${esc(s.tally_company_name || "(any)")}</b> is loaded.</li>
      <li>In TallyPrime: F1 Help → Settings → Connectivity → Client/Server configuration: TallyPrime acts as <b>Both</b> (or Server), Enable ODBC <b>Yes</b>, Port <b>${esc(s.tally_port)}</b>.</li>
      <li>Restart TallyPrime after changing the port.</li>
      <li>Windows Firewall is not blocking the port (only needed if Tally runs on another computer).</li></ol></div>`;
  const run = (btn) => busy(btn, async () => {
    const r = await API.get("/api/tally/status");
    document.getElementById("tally-status").innerHTML =
      `<span class="dot ${r.connected ? "ok" : "err"}"></span> <b>${r.connected ? "Connected" : "Not Connected"}</b> ${r.demo_mode ? badge("DEMO", "demo") : ""}`;
    document.getElementById("tally-detail").innerHTML = esc(r.message) + (r.warning ? `<div class="alert warning" style="margin-top:8px">${esc(r.warning)}</div>` : "");
  });
  const btn = document.getElementById("btn-test");
  btn.onclick = () => run(btn);
  run(btn);
}

// ------------------------------------------------------------------ masters
async function renderMasters() {
  const d = await API.get("/api/tally/masters");
  const labels = { ledger: "Ledgers", group: "Groups", stock_item: "Stock Items", unit: "Units", voucher_type: "Voucher Types" };
  view.innerHTML = `
    <h1>Master Sync</h1>
    <p class="sub">Local cache of Tally masters for <b>${esc(d.company_key === "__DEMO__" ? "Demo company" : d.company_key === "__ACTIVE__" ? "the active Tally company" : d.company_key)}</b>.
      Ledgers in Excel are checked against this list. Nothing is ever created in Tally automatically.</p>
    <div class="panel">
      <table><thead><tr><th>Master</th><th class="num">Cached</th><th>Last synced</th></tr></thead><tbody>
      ${d.types.map((t) => `<tr><td>${labels[t] || t}</td><td class="num">${(d.counts[t] || {}).count || 0}</td>
        <td>${fmtTime((d.counts[t] || {}).synced_at)}</td></tr>`).join("")}</tbody></table>
      <div style="margin-top:12px"><button id="btn-sync">Sync all masters from Tally</button></div>
      <div id="sync-result" style="margin-top:12px"></div>
    </div>
    <div class="panel"><h2>Browse</h2>
      <div class="row"><select id="m-type">${d.types.map((t) => `<option value="${t}">${labels[t] || t}</option>`).join("")}</select>
      <input id="m-q" placeholder="Search name"><button class="secondary" id="btn-m">Search</button></div>
      <div id="m-list" style="margin-top:12px"></div></div>`;
  document.getElementById("btn-sync").onclick = (e) => busy(e.currentTarget, async () => {
    const r = await API.post("/api/tally/masters/sync", {});
    const bad = Object.entries(r.results).filter(([, v]) => v.status !== "ok");
    toast(bad.length ? "Sync finished with problems" : "Masters synced", bad.length > 0);
    await renderMasters();
    document.getElementById("sync-result").innerHTML = bad.length
      ? `<div class="alert error">${bad.map(([t, v]) => `${esc(labels[t] || t)}: ${esc(v.message)}`).join("<br>")}</div>`
      : `<div class="alert ok">All masters synced.</div>`;
  });
  const search = (btn) => busy(btn, async () => {
    const t = document.getElementById("m-type").value;
    const r = await API.get(`/api/tally/masters/${t}?q=${encodeURIComponent(document.getElementById("m-q").value)}`);
    document.getElementById("m-list").innerHTML = r.items.length
      ? `<table><thead><tr><th>Name</th><th>Parent</th></tr></thead><tbody>${r.items.map((i) => `<tr><td>${esc(i.name)}</td><td>${esc(i.parent)}</td></tr>`).join("")}</tbody></table>`
      : `<p class="muted">Nothing cached. Sync masters first.</p>`;
  });
  const b = document.getElementById("btn-m");
  b.onclick = () => search(b);
}

// ------------------------------------------------------------------ history
function historyTable(items) {
  if (!items || !items.length) return `<p class="muted">No imports yet.</p>`;
  return `<div class="table-wrap"><table><thead><tr><th>Date/time</th><th>Type</th><th>Vouchers</th><th>Excel file</th>
    <th class="num">Records</th><th>Status</th><th>Tally response</th></tr></thead><tbody>
    ${items.map((h) => `<tr style="cursor:pointer" onclick="location.hash='#/history?id=${h.id}'">
      <td>${fmtTime(h.created_at)}</td><td>${esc((KINDS[h.voucher_kind] || {}).label || h.voucher_kind)}</td>
      <td>${esc((h.voucher_numbers || "").slice(0, 60))}</td><td>${esc(h.excel_file_name)}</td><td class="num">${h.record_count}</td>
      <td>${badge(h.tally_status)} ${h.demo_mode ? badge("DEMO", "demo") : ""}</td><td>${esc((h.tally_response || "").slice(0, 140))}</td></tr>`).join("")}
    </tbody></table></div>`;
}

async function renderHistory() {
  const id = new URLSearchParams(location.hash.split("?")[1] || "").get("id");
  if (id) return renderHistoryDetail(id);
  view.innerHTML = `
    <h1>Import History</h1><p class="sub">Every attempt to post to Tally, with Tally's own response.</p>
    <div class="panel"><div class="row">
      <input id="h-q" placeholder="Search voucher no, file, response">
      <select id="h-kind"><option value="">All types</option>${Object.entries(KINDS).map(([k, v]) => `<option value="${k}">${v.label}</option>`).join("")}</select>
      <select id="h-status"><option value="">All statuses</option><option>SUCCESS</option><option>PARTIAL</option><option>FAILED</option></select>
      <label class="field">From<input type="date" id="h-from"></label><label class="field">To<input type="date" id="h-to"></label>
      <button id="h-go">Search</button></div></div>
    <div class="panel" id="h-list"></div>`;
  const load = async () => {
    const p = new URLSearchParams({ q: val("h-q"), kind: val("h-kind"), status: val("h-status"), date_from: val("h-from"), date_to: val("h-to") });
    const r = await API.get(`/api/history?${p}`);
    document.getElementById("h-list").innerHTML = historyTable(r.items);
  };
  document.getElementById("h-go").onclick = (e) => busy(e.currentTarget, load);
  await load();
}

async function renderHistoryDetail(id) {
  const h = await API.get(`/api/history/${encodeURIComponent(id)}`);
  view.innerHTML = `
    <h1>Import #${h.id} ${badge(h.tally_status)} ${h.demo_mode ? badge("DEMO", "demo") : ""}</h1>
    <p class="sub">${fmtTime(h.created_at)} · ${esc((KINDS[h.voucher_kind] || {}).label)} · ${esc(h.company_name)} · FY ${esc(h.financial_year)}</p>
    <div class="panel">
      <p>Excel: <b>${esc(h.excel_file_name)}</b> · XML: <b>${esc(h.xml_file_name)}</b> · Records: <b>${h.record_count}</b></p>
      <p>Created ${h.created_count} · Altered ${h.altered_count} · Ignored ${h.ignored_count} · Errors ${h.error_count}</p>
      <div class="alert ${h.tally_status === "SUCCESS" ? "ok" : "warning"}">${esc(h.tally_response)}</div>
      ${resultsTable(h.results)}
      <p><a href="#/history">← Back to history</a></p>
    </div>`;
}

// ------------------------------------------------------------------ audit
async function renderAudit() {
  view.innerHTML = `<h1>Audit Log</h1><p class="sub">Uploads, validations, XML downloads, posting attempts and settings changes.</p>
    <div class="panel"><div class="row"><input id="a-q" placeholder="Search"><button id="a-go">Search</button></div></div>
    <div class="panel" id="a-list"></div>`;
  const load = async () => {
    const r = await API.get(`/api/audit?q=${encodeURIComponent(val("a-q"))}`);
    document.getElementById("a-list").innerHTML = r.items.length ? `<div class="table-wrap"><table>
      <thead><tr><th>Date/time</th><th>Action</th><th>Type</th><th>Batch</th><th>Details</th></tr></thead><tbody>
      ${r.items.map((a) => `<tr><td>${fmtTime(a.created_at)}</td><td>${esc(a.action)}</td><td>${esc(a.voucher_kind)}</td>
        <td class="mono">${esc(a.batch_id)}</td><td class="mono">${esc((a.details || "").slice(0, 300))}</td></tr>`).join("")}
      </tbody></table></div>` : `<p class="muted">No entries.</p>`;
  };
  document.getElementById("a-go").onclick = (e) => busy(e.currentTarget, load);
  await load();
}

// ------------------------------------------------------------------ settings
const val = (id) => (document.getElementById(id) || {}).value || "";

async function renderSettings() {
  const { settings: s, states } = await API.get("/api/settings");
  const text = (key, label, extra = "") => `<label class="field">${label}<input id="s-${key}" value="${esc(s[key])}" ${extra}></label>`;
  const stateOpts = [""].concat(states).map((n) => `<option ${n === s.company_state ? "selected" : ""}>${esc(n)}</option>`).join("");
  view.innerHTML = `
    <h1>Settings</h1><p class="sub">Stored locally on this computer. No provider API keys or database passwords are ever stored here.</p>
    <div class="panel"><h2>Company</h2><div class="form-grid">
      ${text("company_name", "Company Name")}${text("company_gstin", "Company GSTIN")}
      <label class="field">Company State<select id="s-company_state">${stateOpts}</select></label>
      ${text("financial_year", "Financial Year (e.g. 2026-27)")}</div></div>
    <div class="panel"><h2>Tally</h2><div class="form-grid">
      ${text("tally_company_name", "Tally Company Name (blank = active company)")}
      ${text("tally_host", "Tally Server / Host")}${text("tally_port", "Tally Port", 'type="number" min="1" max="65535"')}</div>
      <p class="checkbox"><input type="checkbox" id="s-demo_mode" ${s.demo_mode ? "checked" : ""}> <label for="s-demo_mode"><b>Demo mode</b> — simulate Tally; nothing is posted</label></p>
      <p class="checkbox"><input type="checkbox" id="s-require_master_sync" ${s.require_master_sync ? "checked" : ""}> <label for="s-require_master_sync">Require synced masters before validating (recommended)</label></p></div>
    <div class="panel"><h2>Tally voucher types</h2><div class="form-grid">
      ${text("voucher_type_sales", "Sales")}${text("voucher_type_purchase", "Purchase")}${text("voucher_type_journal", "Journal")}
      ${text("voucher_type_receipt", "Receipt")}${text("voucher_type_payment", "Payment")}</div></div>
    <div class="panel"><h2>GST &amp; round-off ledgers</h2><div class="form-grid">
      ${["output_cgst_ledger", "output_sgst_ledger", "output_igst_ledger", "output_cess_ledger", "input_cgst_ledger", "input_sgst_ledger",
         "input_igst_ledger", "input_cess_ledger", "round_off_ledger", "cost_category"].map((k) => text(k, k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()))).join("")}
      ${text("tax_tolerance", "Tax calculation tolerance (₹)")}</div></div>
    <div class="panel"><h2>BRMCo Server Host</h2><div class="form-grid">${text("server_base_url", "Server URL (SERVER_BASE_URL)")}</div>
      <div class="row" style="margin-top:10px"><button class="secondary" id="btn-server">Test server connection</button><span id="server-result"></span></div></div>
    <button id="btn-save">Save settings</button>`;
  document.getElementById("btn-server").onclick = (e) => busy(e.currentTarget, async () => {
    const r = await API.get("/api/server/status");
    document.getElementById("server-result").innerHTML = (r.reachable ? badge("Online", "ok") : badge("Unavailable", "warning")) +
      ` <span class="muted">${esc(r.message)}${r.warnings.length ? " — " + esc(r.warnings.join(" ")) : ""}</span>`;
  });
  document.getElementById("btn-save").onclick = (e) => busy(e.currentTarget, async () => {
    const body = {};
    Object.keys(s).forEach((k) => {
      const el = document.getElementById(`s-${k}`);
      if (!el) return;
      body[k] = el.type === "checkbox" ? el.checked : el.type === "number" ? Number(el.value) : el.value;
    });
    await API.put("/api/settings", body);
    toast("Settings saved");
    refreshChrome();
  });
}

refreshChrome();
route();
