/* ==================================================================
   Data entry: entities, transactions and users, through the local data bridge.
   Everything is validated again and stored by the bridge (bridge/ledger.py, bridge/auth.py);
   the browser only collects input. The offline snapshot shows the same tables read-only.
   ================================================================== */
const ENTRY = { ledger: null, users: null, audit: null, editEnt: null, editTxn: null, confirm: null, busy: false, resetUser: null, tx: { asset: "EQ" },
  cn: null, cnMember: null, cnBasis: "charges", cnReading: false, imp: "cn", cas: null, casBasis: "charges",
  sch: { q: "", res: null, cats: null, bms: null, pick: null, searching: false },
  eq: { q: "", res: null, pick: null, searching: false, origin: "all" } };
const canEnter = () => BRIDGE.live && ["analyst", "admin"].includes(BRIDGE.me?.role);
const isAdmin = () => BRIDGE.live && BRIDGE.me?.role === "admin";
const memName = id => IX.mem[id]?.name || id;
const entryInstName = (asset, code) => asset === "MF" ? (IX.sch[code]?.name || code) : (IX.co[code]?.name || code);

async function entryLoad() {
  if (!BRIDGE.live) return;
  try {
    ENTRY.ledger = await api("/api/ledger");
    ENTRY.audit = await api("/api/audit?limit=300");
    ENTRY.users = isAdmin() ? await api("/api/users") : null;
  } catch (e) { toast("Could not load data entry: " + e.message, "warn"); }
}
async function entryPost(path, body, okMsg) {
  if (ENTRY.busy) return null;
  ENTRY.busy = true; render();
  try {
    const r = await api(path, { method: "POST", body: JSON.stringify(body), timeout: 120000 });
    if (r.error) throw new Error(r.error);
    await reloadDataset(); await entryLoad();
    toast(okMsg(r), "ok");
    return r;
  } catch (e) { toast(e.message, "warn"); return null; }
  finally { ENTRY.busy = false; render(); }
}
function readOnlyNote(what) {
  if (BRIDGE.outdated) return `<p class="note warn"><b>An older Data Bridge is running.</b> It has no sign-in, so you cannot ${what}. Close every <i>LookThrough Data Bridge</i> window (or end <span class="mono">python.exe</span> in Task Manager), then run <span class="mono">Start_LookThrough.bat</span> again.</p>`;
  if (!BRIDGE.live) return `<p class="note"><b>Read-only snapshot.</b> To ${what}, start the app with <span class="mono">Start_LookThrough.bat</span> and sign in. Entries are validated and saved on this PC, with an audit trail.</p>`;
  if (!canEnter()) return `<p class="note">Signed in as <b>${esc(BRIDGE.me?.user)}</b> (${esc(BRIDGE.me?.role)}). Viewers can read but not change data; ask an admin for the analyst role.</p>`;
  return "";
}
const delBtn = (kind, id) => ENTRY.confirm === `${kind}|${id}`
  ? `<button class="btn sm" data-edel="${kind}|${id}" style="color:var(--crit)">Confirm delete</button><button class="btn ghost sm" data-ecancel="1">Keep</button>`
  : `<button class="btn ghost sm" data-eask="${kind}|${id}" aria-label="Delete ${esc(id)}">Delete</button>`;

/* ---------------- entities ---------------- */
function entitiesTab() {
  const rows = DB.members.map(m => ({ ...m, src: m.source || "demo", ntx: DB.transactions.filter(t => t.member_id === m.member_id).length,
    value: holdings(m.member_id).reduce((s, h) => s + h.value, 0) }));
  const cols = [
    { k: "member_id", label: "ID", fmt: v => `<span class="mono">${esc(v)}</span>` },
    { k: "name", label: "Entity", fmt: v => `<span class="nm">${esc(v)}</span>` },
    { k: "type", label: "Type" }, { k: "relationship", label: "Relationship" },
    { k: "ntx", label: "Transactions", num: true }, { k: "value", label: "Current value", num: true, fmt: v => fmtAmt(v) },
    { k: "src", label: "Source", fmt: v => tag(v === "user" ? "Entered" : "Demo") },
  ];
  if (canEnter()) cols.push({ k: "a", label: "", fmt: (v, r) => r.src === "user" ? `<span class="row" style="gap:4px"><button class="btn ghost sm" data-eedit="${esc(r.member_id)}">Edit</button>${delBtn("ent", r.member_id)}</span>` : `<span class="muted small">read-only</span>`, csv: () => "" });
  const types = ENTRY.ledger?.entity_types || ["Individual", "HUF", "LLP", "Company", "Partnership firm", "Trust"];
  const e = ENTRY.editEnt ? DB.members.find(m => m.member_id === ENTRY.editEnt) : null;
  const form = canEnter() ? `<form id="entForm" class="row" style="align-items:flex-end" autocomplete="off" novalidate>
      <label class="fld" for="ent_name">Entity name<input type="text" id="ent_name" maxlength="80" required value="${esc(e?.name || "")}" style="width:240px"></label>
      <label class="fld" for="ent_type">Type<select id="ent_type">${types.map(t => `<option ${t === (e?.type || "Individual") ? "selected" : ""}>${esc(t)}</option>`).join("")}</select></label>
      <label class="fld" for="ent_rel">Relationship or role<input type="text" id="ent_rel" maxlength="60" value="${esc(e?.relationship || "")}" placeholder="e.g. Daughter, investment LLP" style="width:220px"></label>
      <button class="btn primary" type="submit" ${ENTRY.busy ? "disabled" : ""}>${e ? "Save changes" : "Add entity"}</button>${e ? `<button class="btn ghost" type="button" data-ecancel="1">Cancel</button>` : ""}
    </form>
    <label class="row small muted" style="gap:6px;margin-top:10px"><input type="checkbox" id="demoToggle" ${ENTRY.ledger?.settings?.include_demo_family !== false ? "checked" : ""}> Include the demo (Mehta) family and its transactions</label>` : "";
  return readOnlyNote("add or edit entities") + form + table("entities", cols, rows, { sort: { k: "member_id", d: "asc" }, noun: "entities", search: r => `${r.name} ${r.type} ${r.relationship}`, placeholder: "Search entities" });
}

/* ---------------- transactions ---------------- */
function priceHint(asset, inst, plan, date) {
  if (!inst || !date) return "";
  const arr = asset === "MF" ? IX.nav[inst + "|" + plan] : IX.px[inst];
  if (!arr) return "";
  let i = -1; DB.meta.dates.forEach((d, k) => { if (d <= date && isNum(arr[k])) i = k; });
  return i < 0 ? "No month-end price on or before this date." : `Month-end ${asset === "MF" ? "NAV" : "price"} on ${fmtDate(DB.meta.dates[i])}: ₹${nf(arr[i], 2)} (enter the actual trade price).`;
}
function unitsHeld(member, inst, plan, date, exceptId) {
  return DB.transactions.filter(t => t.member_id === member && t.instrument === inst && (t.plan || "") === (plan || "") && t.date <= date && t.txn_id !== exceptId)
    .reduce((s, t) => s + (t.txn_type === "Sell" ? -t.units : t.units), 0);
}
function txForm() {
  const e = ENTRY.editTxn ? DB.transactions.find(t => t.txn_id === ENTRY.editTxn) : null;
  const f = ENTRY.tx, asset = e?.asset_type || f.asset;  // values come from the draft (f); e only marks edit mode
  const types = { EQ: ["Buy", "Sell"], MF: ["Purchase", "SIP", "Sell"] }[asset];
  const eqs = DB.companies.filter(c => isNum(curPrice("EQ", c.code, ""))).sort((a, b) => a.name.localeCompare(b.name));
  const insts = asset === "MF" ? DB.schemes.map(s => [s.scheme_id, `${s.name}`]) : eqs.map(c => [c.code, `${c.name} (${c.code})`]);
  const v = k => f[k];
  const inst = v("instrument") || insts[0]?.[0], plan = asset === "MF" ? (v("plan") || "Direct") : "", date = v("date") || DB.meta.as_on, member = v("member_id") || (state.member !== "ALL" ? state.member : DB.members[0]?.member_id);
  const type = types.includes(v("txn_type")) ? v("txn_type") : types[0];
  const held = type === "Sell" && member && inst ? unitsHeld(member, inst, plan, date, e?.txn_id) : null;
  return `<form id="txForm" class="stack" autocomplete="off" novalidate>
    <div class="row" style="align-items:flex-end">
      <label class="fld" for="tx_member">Entity<select id="tx_member">${DB.members.map(m => `<option value="${esc(m.member_id)}" ${m.member_id === member ? "selected" : ""}>${esc(m.name)}</option>`).join("")}</select></label>
      <label class="fld" for="tx_asset">Asset<select id="tx_asset" ${e ? "disabled" : ""}><option value="EQ" ${asset === "EQ" ? "selected" : ""}>Listed equity</option><option value="MF" ${asset === "MF" ? "selected" : ""}>Mutual fund</option></select></label>
      <label class="fld" for="tx_inst">${asset === "MF" ? "Scheme" : "Company"}<select id="tx_inst" style="max-width:320px">${insts.map(([k, n]) => `<option value="${esc(k)}" ${k === inst ? "selected" : ""}>${esc(n)}</option>`).join("")}</select></label>
      ${asset === "MF" ? `<label class="fld" for="tx_plan">Plan<select id="tx_plan">${["Direct", "Regular"].map(p => `<option ${p === plan ? "selected" : ""}>${p}</option>`).join("")}</select></label>` : ""}
      <label class="fld" for="tx_type">Type<select id="tx_type">${types.map(t => `<option ${t === type ? "selected" : ""}>${t}</option>`).join("")}</select></label>
    </div>
    <div class="row" style="align-items:flex-end">
      <label class="fld" for="tx_date">Trade date<input type="date" id="tx_date" max="${DB.meta.as_on}" value="${esc(date)}"></label>
      <label class="fld" for="tx_units">${asset === "MF" ? "Units" : "Shares"}<input type="number" id="tx_units" min="0" step="${asset === "MF" ? "0.001" : "1"}" value="${esc(v("units") ?? "")}" style="width:130px"></label>
      <label class="fld" for="tx_price">${asset === "MF" ? "NAV (₹)" : "Price (₹)"}<input type="number" id="tx_price" min="0" step="any" value="${esc(v("price") ?? "")}" style="width:130px"></label>
      <div class="fld">Amount<b id="tx_amt" class="mono" style="height:34px;display:flex;align-items:center;font-size:14px;color:var(--ink)">${isNum(v("units")) && isNum(v("price")) ? "₹" + nf(v("units") * v("price"), 2) : "—"}</b></div>
      <button class="btn primary" type="submit" ${ENTRY.busy ? "disabled" : ""}>${e ? "Save changes" : "Record transaction"}</button>${e ? `<button class="btn ghost" type="button" data-ecancel="1">Cancel</button>` : ""}
    </div>
    <p class="muted small" id="tx_hint" style="margin:0">${esc(priceHint(asset, inst, plan, date))}${held != null ? ` Units held on this date: <b>${nf(held, asset === "MF" ? 3 : 0)}</b>.` : ""} Dates up to the valuation date ${fmtDate(DB.meta.as_on)}. The bridge checks every entry again, including that no sale exceeds the units held.</p>
  </form>`;
}
/* ---------------- contract-note import (PDF) ---------------- */
const CN_CHARGE_LABELS = { brokerage: "Brokerage", exchange: "Exchange charges", sebi: "SEBI fees", stamp: "Stamp duty", gst: "GST", stt: "STT" };
const cnPrice = t => ENTRY.cnBasis === "charges" ? t.price_with_charges : t.rate;
function cnProblems(c) {
  const sel = c.trades.filter(t => t.include);
  if (!sel.length) return "Select at least one trade.";
  if (!c.date) return "Enter the trade date.";
  if (c.date > DB.meta.as_on) return `The trade date is after the valuation date ${fmtDate(DB.meta.as_on)}; refresh the data first.`;
  const bad = sel.find(t => !t.instrument);
  if (bad) return `Choose the company for “${bad.name || bad.isin}”.`;
  return null;
}
function cnPanel() {
  const member = ENTRY.cnMember || (state.member !== "ALL" ? state.member : DB.members[0]?.member_id);
  const form = `<form id="cnForm" class="row" style="align-items:flex-end" autocomplete="off" novalidate>
      <label class="fld" for="cn_member">Entity (whose note)<select id="cn_member">${DB.members.map(m => `<option value="${esc(m.member_id)}" ${m.member_id === member ? "selected" : ""}>${esc(m.name)}</option>`).join("")}</select></label>
      <label class="fld" for="cn_file">Contract note (PDF)<input type="file" id="cn_file" accept=".pdf,application/pdf" style="width:260px"></label>
      <label class="fld" for="cn_pw">PDF password (if any)<input type="password" id="cn_pw" autocomplete="off" placeholder="usually PAN in capitals" style="width:190px"></label>
      <button class="btn primary" type="submit" ${ENTRY.cnReading ? "disabled" : ""}>${ENTRY.cnReading ? "Reading…" : "Read contract note"}</button>
    </form>
    <p class="muted small" style="margin:6px 0 0">Equity contract notes from any broker. The PDF is read on this PC and not kept; the password is not saved. Nothing is recorded until you check the trades below and confirm.</p>`;
  const c = ENTRY.cn;
  if (!c) return form;
  const rc = c.reconciliation, recon = rc.status === "reconciled"
    ? pill("ok", `Reconciled to the note's net amount ₹${nf(rc.stated_net, 2)}`)
    : rc.status === "difference" ? pill("crit", `Does not reconcile: difference ₹${nf(rc.difference, 2)}`) : pill("warn", "Net amount not found: not reconciled");
  const eqs = DB.companies.filter(x => isNum(curPrice("EQ", x.code, ""))).sort((a, b) => a.name.localeCompare(b.name));
  const rows = c.trades.map((t, i) => {
    const price = cnPrice(t), amt = price * t.qty;
    const pick = `<select data-cnpick="${i}" aria-label="Company for trade ${i + 1}" style="max-width:230px"><option value="">— choose —</option>${eqs.map(x => `<option value="${esc(x.code)}" ${x.code === t.instrument ? "selected" : ""}>${esc(x.name)} (${esc(x.code)})</option>`).join("")}</select>`;
    return `<tr${t.issues.length ? ' class="cn-issue"' : ""}>
      <td><input type="checkbox" data-cninc="${i}" ${t.include ? "checked" : ""} aria-label="Include trade ${i + 1}"></td>
      <td><span class="nm">${esc(t.name || "—")}</span>${t.isin ? `<span class="sub mono">${esc(t.isin)}</span>` : ""}${t.fills > 1 ? `<span class="sub">${t.fills} fills, averaged</span>` : ""}</td>
      <td>${pick}<span class="sub">${t.match ? "Matched by " + esc(t.match) : t.instrument ? "Chosen by you" : "Not matched"}</span></td>
      <td>${tag(t.side)}</td><td class="num">${nf(t.qty, 0)}</td><td class="num">₹${nf(t.rate, 2)}</td>
      <td class="num">₹${nf(t.charges, 2)}</td><td class="num"><b>₹${nf(price, 4)}</b></td><td class="num">₹${nf(amt, 2)}</td>
      <td class="wrap small">${t.issues.length ? t.issues.map(x => `<div style="color:var(--crit)">${esc(x)}</div>`).join("") : '<span class="muted">—</span>'}</td></tr>`;
  }).join("");
  const ch = Object.entries(c.charges).map(([k, v]) => `${CN_CHARGE_LABELS[k] || k} ₹${nf(v, 2)}`).join(" · ");
  const problem = cnProblems(c), nSel = c.trades.filter(t => t.include).length;
  return `${form}
    <div class="cn-preview">
      <div class="row" style="gap:10px;align-items:center;flex-wrap:wrap">
        <b>${esc(c.file)}</b><span class="muted small">Contract note ${esc(c.contract_note_no || "number not found")}</span>
        <label class="fld" for="cn_date" style="margin:0">Trade date<input type="date" id="cn_date" max="${DB.meta.as_on}" value="${esc(c.date || "")}"></label>${recon}
      </div>
      ${c.warnings.length ? `<ul class="small" style="margin:6px 0;color:var(--crit)">${c.warnings.map(w => `<li>${esc(w)}</li>`).join("")}</ul>` : ""}
      <p class="muted small" style="margin:6px 0">Buys ₹${nf(rc.buys, 2)} · Sells ₹${nf(rc.sells, 2)} · Charges ₹${nf(rc.charges, 2)}${ch ? ` (${ch})` : ""}</p>
      <div class="row small" style="gap:14px;margin:4px 0 8px">
        <label><input type="radio" name="cn_basis" value="charges" ${ENTRY.cnBasis === "charges" ? "checked" : ""}> Price including charges (brokerage, exchange, SEBI, stamp duty, GST, allocated by value; not STT) — the capital-gains cost basis</label>
        <label><input type="radio" name="cn_basis" value="rate" ${ENTRY.cnBasis === "rate" ? "checked" : ""}> Exchange rate only</label>
      </div>
      <div class="tbl-wrap"><table class="tbl dense"><thead><tr><th></th><th><span class="th">On the note</span></th><th><span class="th">Company</span></th><th><span class="th">Type</span></th><th class="num"><span class="th">Qty</span></th><th class="num"><span class="th">Rate</span></th><th class="num"><span class="th">Charges</span></th><th class="num"><span class="th">Price recorded</span></th><th class="num"><span class="th">Amount</span></th><th><span class="th">Check</span></th></tr></thead><tbody>${rows}</tbody></table></div>
      <div class="row" style="gap:8px;margin-top:10px;align-items:center">
        <button class="btn primary" data-cnrecord="1" ${problem || ENTRY.busy ? "disabled" : ""}>Record ${nSel} trade${nSel === 1 ? "" : "s"} for ${esc(memName(member))}</button>
        <button class="btn ghost" data-cndiscard="1">Discard</button>
        <span class="small ${problem ? "" : "muted"}" style="${problem ? "color:var(--crit)" : ""}">${esc(problem || "All selected trades are recorded together, or none is. Sales are checked against the units held.")}</span>
      </div>
    </div>`;
}
async function cnRead() {
  const f = $("#cn_file")?.files?.[0];
  if (!f) return toast("Choose the contract note PDF.", "warn");
  if (f.size > 10 * 1024 * 1024) return toast("The file is larger than 10 MB.", "warn");
  const fd = new FormData(); fd.append("file", f, f.name); fd.append("password", $("#cn_pw").value);
  ENTRY.cnMember = $("#cn_member").value; ENTRY.cnReading = true; render();
  try {
    const r = await api("/api/contract-note", { method: "POST", body: fd, timeout: 60000 });
    r.trades.forEach(t => { t.include = !t.issues.length; });
    r.date = r.trade_date;
    ENTRY.cn = r;
    toast(`${r.trades.length} trade${r.trades.length === 1 ? "" : "s"} read from ${r.file}. Check them before recording.`, "ok");
  } catch (e) { toast(e.message, "warn"); }
  finally { ENTRY.cnReading = false; render(); }
}
async function cnRecord() {
  const c = ENTRY.cn, err = cnProblems(c);
  if (err) return toast(err, "warn");
  const member = ENTRY.cnMember || $("#cn_member").value;
  const trades = c.trades.filter(t => t.include).map(t => ({ member_id: member, instrument: t.instrument, plan: "", txn_type: t.side, date: c.date, units: t.qty, price: +cnPrice(t).toFixed(4) }));
  const r = await entryPost("/api/transactions", { action: "import", trades, ref: { sha256: c.sha256, contract_note_no: c.contract_note_no, file: c.file } },
    x => `${x.record.length} trade${x.record.length === 1 ? "" : "s"} recorded from contract note ${c.contract_note_no || c.file}: ${x.record.map(t => t.txn_id).join(", ")}.`);
  if (r) { ENTRY.cn = null; render(); }
}

/* ---------------- CAS import (mutual funds, PDF) ---------------- */
const casPrice = t => ENTRY.casBasis === "charges" ? t.price_with_charges : t.nav;
const casRows = c => c.folios.flatMap((f, fi) => f.txns.map((t, ti) => ({ f, t, fi, ti })));
function casProblems(c) {
  const sel = casRows(c).filter(x => x.t.include);
  if (!sel.length) return "Select at least one transaction.";
  const late = sel.find(x => x.t.date > DB.meta.as_on);
  if (late) return `A selected transaction (${fmtDate(late.t.date)}) is after the valuation date; refresh the data first.`;
  return null;
}
function casAfter(c, member) {
  // per scheme + plan: units the app will hold at the statement end date after recording the selected rows, vs the statement
  const out = {};
  c.folios.filter(f => f.scheme_id).forEach(f => {
    const k = f.scheme_id + "|" + f.plan, o = out[k] || (out[k] = { closing: 0, add: 0, folios: 0 });
    o.closing += f.closing || 0; o.folios += 1;
    f.txns.filter(t => t.include).forEach(t => { o.add += t.txn_type === "Sell" ? -t.units : t.units; });
  });
  Object.entries(out).forEach(([k, o]) => { const [sid, plan] = k.split("|"); o.after = unitsHeld(member, sid, plan, c.period.to || DB.meta.as_on) + o.add; o.ok = Math.abs(o.after - o.closing) < 0.002; });
  return out;
}
function casPanel() {
  const member = ENTRY.cnMember || (state.member !== "ALL" ? state.member : DB.members[0]?.member_id);
  const form = `<form id="casForm" class="row" style="align-items:flex-end" autocomplete="off" novalidate>
      <label class="fld" for="cas_member">Entity (whose statement)<select id="cas_member">${DB.members.map(m => `<option value="${esc(m.member_id)}" ${m.member_id === member ? "selected" : ""}>${esc(m.name)}</option>`).join("")}</select></label>
      <label class="fld" for="cas_file">CAS statement (PDF)<input type="file" id="cas_file" accept=".pdf,application/pdf" style="width:260px"></label>
      <label class="fld" for="cas_pw">PDF password<input type="password" id="cas_pw" autocomplete="off" placeholder="set when you requested it" style="width:200px"></label>
      <button class="btn primary" type="submit" ${ENTRY.cnReading ? "disabled" : ""}>${ENTRY.cnReading ? "Reading…" : "Read CAS"}</button>
    </form>
    <p class="muted small" style="margin:6px 0 0">Detailed CAS from CAMS or KFintech (mutual funds, with transactions). Read on this PC and not kept; the password is not saved. Only the ${DB.schemes.length} schemes the app tracks can be recorded; each is matched by ISIN, so the plan is exact.</p>`;
  const c = ENTRY.cas;
  if (!c) return form;
  const sm = c.summary, after = casAfter(c, c.member_id);
  const blocks = c.folios.map((f, fi) => {
    const sch = f.scheme_id ? IX.sch[f.scheme_id] : null, a = f.scheme_id ? after[f.scheme_id + "|" + f.plan] : null;
    const head = `<div class="row" style="gap:8px;align-items:center;flex-wrap:wrap;margin:14px 0 4px">
        <b>${esc(f.name || f.isin)}</b><span class="muted small mono">${esc(f.isin)} · folio ${esc(f.folio || "—")}</span>
        ${sch ? tag(`${sch.name} · ${f.plan}`) : pill("neutral", "Not tracked by the app") + (canEnter() ? ` <button class="btn ghost sm" data-casaddsch="${esc(f.isin)}">Add this scheme</button>` : "")}
        ${f.reconciled ? pill("ok", `Units reconcile: opening ${nf(f.opening || 0, 3)} → closing ${nf(f.closing, 3)}`) : pill("crit", "Units do not reconcile")}
      </div>
      ${f.issues.map(x => `<div class="small" style="color:var(--crit)">${esc(x)}</div>`).join("")}
      ${a ? `<div class="small ${a.ok ? "muted" : ""}" style="${a.ok ? "" : "color:var(--crit)"}">After recording, the app will hold <b>${nf(a.after, 3)}</b> units on ${fmtDate(c.period.to || DB.meta.as_on)}; the statement's closing balance${a.folios > 1 ? ` (${a.folios} folios)` : ""} is <b>${nf(a.closing, 3)}</b>.${a.ok ? " ✓" : " Check for missing or already-recorded transactions."}</div>` : ""}`;
    const rows = f.txns.map((t, ti) => {
      const price = casPrice(t), iss = [...t.issues, ...(t.duplicate_of ? [`Already recorded as ${t.duplicate_of}.`] : [])];
      return `<tr${iss.length ? ' class="cn-issue"' : ""}>
        <td><input type="checkbox" data-casinc="${fi}|${ti}" ${t.include ? "checked" : ""} ${f.scheme_id ? "" : "disabled"} aria-label="Include ${esc(t.date)} ${esc(t.txn_type)}"></td>
        <td class="mono small">${fmtDate(t.date)}</td><td class="small">${esc(t.description)}</td><td>${tag(t.txn_type)}</td>
        <td class="num">${nf(t.units, 3)}</td><td class="num">₹${nf(t.nav, 4)}</td><td class="num">${t.charges.stamp ? "₹" + nf(t.charges.stamp, 2) : "—"}</td>
        <td class="num"><b>₹${nf(price, 4)}</b></td><td class="num">₹${nf(price * t.units, 2)}</td><td class="num small">${nf(t.balance, 3)}</td>
        <td class="wrap small">${iss.length ? iss.map(x => `<div style="color:var(--crit)">${esc(x)}</div>`).join("") : '<span class="muted">—</span>'}</td></tr>`;
    }).join("");
    return head + `<div class="tbl-wrap"><table class="tbl dense"><thead><tr><th></th><th><span class="th">Date</span></th><th><span class="th">Description</span></th><th><span class="th">Type</span></th><th class="num"><span class="th">Units</span></th><th class="num"><span class="th">NAV</span></th><th class="num"><span class="th">Stamp duty</span></th><th class="num"><span class="th">Price recorded</span></th><th class="num"><span class="th">Amount</span></th><th class="num"><span class="th">Balance</span></th><th><span class="th">Check</span></th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }).join("");
  const problem = casProblems(c), nSel = casRows(c).filter(x => x.t.include).length;
  return `${form}
    <div class="cn-preview">
      <div class="row" style="gap:10px;align-items:center;flex-wrap:wrap">
        <b>${esc(c.file)}</b><span class="muted small">${c.period.from ? `${fmtDate(c.period.from)} to ${fmtDate(c.period.to)}` : "period not found"} · for ${esc(memName(c.member_id))}</span>
        ${sm.reconciled === sm.folios ? pill("ok", `All ${sm.folios} folios reconcile`) : pill("crit", `${sm.folios - sm.reconciled} of ${sm.folios} folios do not reconcile`)}
        ${pill(sm.tracked === sm.folios ? "ok" : "neutral", `${sm.tracked} of ${sm.folios} folios in tracked schemes`)}
      </div>
      ${c.warnings.length ? `<ul class="small" style="margin:6px 0;color:var(--crit)">${c.warnings.map(w => `<li>${esc(w)}</li>`).join("")}</ul>` : ""}
      <div class="row small" style="gap:14px;margin:8px 0 0">
        <label><input type="radio" name="cas_basis" value="charges" ${ENTRY.casBasis === "charges" ? "checked" : ""}> Purchase price including stamp duty — the capital-gains cost (sales at NAV; STT not deducted)</label>
        <label><input type="radio" name="cas_basis" value="nav" ${ENTRY.casBasis === "nav" ? "checked" : ""}> NAV only</label>
      </div>
      ${blocks}
      <div class="row" style="gap:8px;margin-top:12px;align-items:center">
        <button class="btn primary" data-casrecord="1" ${problem || ENTRY.busy ? "disabled" : ""}>Record ${nSel} transaction${nSel === 1 ? "" : "s"} for ${esc(memName(c.member_id))}</button>
        <button class="btn ghost" data-casdiscard="1">Discard</button>
        <span class="small ${problem ? "" : "muted"}" style="${problem ? "color:var(--crit)" : ""}">${esc(problem || "Recorded together, or none. Rows already recorded are left unticked; the bridge refuses them again if ticked.")}</span>
      </div>
    </div>`;
}
async function casRead() {
  const f = $("#cas_file")?.files?.[0];
  if (!f) return toast("Choose the CAS statement PDF.", "warn");
  if (f.size > 10 * 1024 * 1024) return toast("The file is larger than 10 MB.", "warn");
  const fd = new FormData(); fd.append("file", f, f.name); fd.append("password", $("#cas_pw").value); fd.append("member_id", $("#cas_member").value);
  ENTRY.cnMember = $("#cas_member").value; ENTRY.cnReading = true; render();
  try {
    const r = await api("/api/cas", { method: "POST", body: fd, timeout: 60000 });
    r.folios.forEach(fo => {
      // opening units the app does not hold (purchases before the statement): sales would exceed the holding, so leave them unticked
      const heldBefore = fo.scheme_id && r.period.from ? DB.transactions.filter(t => t.member_id === r.member_id && t.instrument === fo.scheme_id && t.plan === fo.plan && t.date < r.period.from)
        .reduce((s, t) => s + (t.txn_type === "Sell" ? -t.units : t.units), 0) : 0;
      fo.opening_missing = (fo.opening || 0) - heldBefore > 0.002;
      fo.txns.forEach(t => { t.include = !!fo.scheme_id && !t.issues.length && !t.duplicate_of && !(fo.opening_missing && t.txn_type === "Sell"); });
    });
    ENTRY.cas = r;
    const s = r.summary;
    toast(`${s.transactions} transactions in ${s.folios} folios read from ${r.file}. Check them before recording.`, "ok");
  } catch (e) { toast(e.message, "warn"); }
  finally { ENTRY.cnReading = false; render(); }
}
async function casRecord() {
  const c = ENTRY.cas, err = casProblems(c);
  if (err) return toast(err, "warn");
  const trades = casRows(c).filter(x => x.t.include).map(({ f, t }) => ({ member_id: c.member_id, instrument: f.scheme_id, plan: f.plan, txn_type: t.txn_type,
    date: t.date, units: t.units, price: +casPrice(t).toFixed(4), folio: f.folio }));
  const r = await entryPost("/api/transactions", { action: "import", kind: "cas", trades, ref: { sha256: c.sha256, file: c.file } },
    x => `${x.record.length} mutual-fund transaction${x.record.length === 1 ? "" : "s"} recorded from ${c.file}: ${x.record[0].txn_id}–${x.record[x.record.length - 1].txn_id}.`);
  if (r) { ENTRY.cas = null; render(); }
}
function importPanel() {
  const sw = [["cn", "Contract note (equity)"], ["cas", "CAS statement (mutual funds)"]].map(([k, l]) => `<button type="button" class="btn ${ENTRY.imp === k ? "primary" : "ghost"} sm" data-impsw="${k}" aria-pressed="${ENTRY.imp === k}">${l}</button>`).join("");
  return `<div class="cn-panel"><div class="row" style="gap:8px;align-items:center;margin-bottom:10px"><b class="small">Import from PDF</b>${sw}</div>${ENTRY.imp === "cas" ? casPanel() : cnPanel()}</div>`;
}

/* ---------------- schemes (mutual-fund master) ---------------- */
const BM_LABEL = { NIFTY50: "Nifty 50", NIFTY500: "Nifty 500", NIFTYMID: "Nifty Midcap", NIFTYSMALL: "Nifty Smallcap", NIFTYBANK: "Nifty Bank", HYBRID: "65% Nifty 50 + 35% debt (composite)" };
function suggestCategory(n) {
  n = n.toLowerCase();
  const rules = [[/elss|tax saver/, "ELSS"], [/index|nifty|sensex/, "Index Fund"], [/large\s*(&|and)\s*mid/, "Large & Mid Cap"], [/large ?cap|bluechip/, "Large Cap"],
    [/mid ?cap/, "Mid Cap"], [/small ?cap/, "Small Cap"], [/multi ?cap/, "Multi Cap"], [/flexi ?cap/, "Flexi Cap"], [/focused/, "Focused"], [/value/, "Value"],
    [/contra/, "Contra"], [/dividend yield/, "Dividend Yield"], [/aggressive hybrid|equity (&|and) debt|equity hybrid|hybrid equity/, "Aggressive Hybrid"],
    [/bank|financ|pharma|health|infra|techno|digital|consum|psu|manufactur|thematic|sector|energy|auto|business cycle|momentum|quality|esg|innovation/, "Sectoral / Thematic"]];
  return (rules.find(([re]) => re.test(n)) || [null, ""])[1];
}
function suggestBenchmark(cat, n) {
  n = n.toLowerCase();
  if (cat === "Large Cap" || (cat === "Index Fund" && /nifty 50\b|sensex/.test(n) && !/next|500|midcap|smallcap/.test(n))) return "NIFTY50";
  if (cat === "Mid Cap" || /midcap/.test(n) && cat === "Index Fund") return "NIFTYMID";
  if (cat === "Small Cap" || /smallcap/.test(n) && cat === "Index Fund") return "NIFTYSMALL";
  if (cat === "Aggressive Hybrid") return "HYBRID";
  if (cat === "Sectoral / Thematic" && /bank|financ/.test(n)) return "NIFTYBANK";
  return "NIFTY500";
}
const schemeDisplayName = n => { const x = n.split(/\s*-\s*direct/i)[0].replace(/\s*\((erstwhile|formerly)[^)]*\)/i, "").trim(); return x === x.toUpperCase() ? x.toLowerCase().replace(/\b\w/g, c => c.toUpperCase()) : x; };
async function schemeSearch(q) {
  const S = ENTRY.sch; S.q = q; S.pick = null;
  if (q.trim().length < 3) return toast("Type at least 3 characters of the scheme name, its AMFI code or its ISIN.", "warn");
  S.searching = true; render();
  try { const r = await api("/api/amfi-search?q=" + encodeURIComponent(q.trim()), { timeout: 60000 }); S.res = r.results; S.cats = r.categories; S.bms = r.benchmarks; }
  catch (e) { toast(e.message, "warn"); }
  finally { S.searching = false; render(); }
}
function schemesTab() {
  const S = ENTRY.sch;
  const nTx = sid => DB.transactions.filter(t => t.instrument === sid).length;
  const looked = sid => DB.scheme_portfolios.some(p => p.scheme_id === sid);
  const cats = S.cats || ENTRY.ledger?.scheme_categories || [], bms = S.bms || Object.keys(BM_LABEL);
  const rows = DB.schemes.map(s => ({ ...s, ntx: nTx(s.scheme_id), lt: looked(s.scheme_id), src: s.source || "config" }));
  const cols = [
    { k: "scheme_id", label: "ID", fmt: v => `<span class="mono">${esc(v)}</span>` },
    { k: "name", label: "Scheme", fmt: (v, r) => `<span class="nm">${esc(v)}</span><span class="sub">${esc(r.amc || "")} · ${r.src === "user" ? "added by you" : "configured"}</span>` },
    { k: "category", label: "Category", fmt: (v, r) => r.src === "user" && canEnter() ? `<select data-schcat="${esc(r.scheme_id)}" aria-label="Category of ${esc(r.name)}">${(cats.length ? cats : [v]).map(c => `<option ${c === v ? "selected" : ""}>${esc(c)}</option>`).join("")}</select>` : esc(v) },
    { k: "benchmark", label: "Benchmark", fmt: (v, r) => r.src === "user" && canEnter() ? `<select data-schbm="${esc(r.scheme_id)}" aria-label="Benchmark of ${esc(r.name)}">${bms.map(c => `<option value="${c}" ${c === v ? "selected" : ""}>${esc(BM_LABEL[c] || c)}</option>`).join("")}</select>` : esc(BM_LABEL[v] || v) },
    { k: "amfi_code", label: "AMFI codes", fmt: (v, r) => `<span class="mono small">Direct ${esc(v || "—")}</span>${r.amfi_code_regular ? `<span class="sub mono">Regular ${esc(r.amfi_code_regular)}</span>` : ""}` },
    { k: "lt", label: "Look-through", fmt: v => v ? pill("ok", "Portfolio loaded") : pill("neutral", "No portfolio file") },
    { k: "ntx", label: "Transactions", num: true },
  ];
  // the source is on the name line; an action column appears only when there is something to act on
  if (canEnter() && rows.some(r => r.src === "user")) cols.push({ k: "a", label: "", fmt: (v, r) => r.src === "user" ? (r.ntx ? `<span class="muted small">in use</span>` : delBtn("sch", r.scheme_id)) : "", csv: () => "" });
  let add = "";
  if (canEnter()) {
    const res = S.res ? (S.res.length ? `<div class="stack" style="gap:6px;margin-top:10px">${S.res.map((g, i) => `<div class="row" style="gap:10px;align-items:center;border:1px solid var(--line);border-radius:8px;padding:8px 10px;${S.pick === i ? "outline:2px solid var(--acc,#0e7c86)" : ""}">
        <div style="flex:1;min-width:260px"><span class="nm">${esc(g.direct.name)}</span><span class="sub">${esc(g.amc)} · Direct ${esc(g.direct.code)} (${esc(g.direct.isin || "no ISIN")})${g.regular ? ` · Regular ${esc(g.regular.code)} (${esc(g.regular.isin || "no ISIN")})` : " · no Regular plan found"} · NAV ₹${esc(g.direct.nav)} on ${esc(g.direct.date)}</span></div>
        ${g.tracked_as ? pill("neutral", `Already tracked as ${g.tracked_as}`) : g.not_equity ? pill("warn", "Not equity-oriented: not supported") : `<button class="btn ${S.pick === i ? "primary" : ""} sm" data-schpick="${i}">${S.pick === i ? "Selected" : "Select"}</button>`}
      </div>`).join("")}</div>` : `<p class="muted small" style="margin:8px 0 0">No Growth-option scheme matches “${esc(S.q)}”. Try fewer words, the AMFI code or the ISIN (schemes are listed under their current names).</p>`) : "";
    const g = S.pick != null ? S.res[S.pick] : null;
    const form = g ? (() => {
      const nm = schemeDisplayName(g.direct.name), cat = suggestCategory(g.direct.name), bm = suggestBenchmark(cat, g.direct.name);
      return `<form id="schForm" class="row" style="align-items:flex-end;margin-top:12px" autocomplete="off" novalidate>
        <label class="fld" for="sch_name">Name in the app<input type="text" id="sch_name" maxlength="80" value="${esc(nm)}" style="width:300px"></label>
        <label class="fld" for="sch_cat">Category<select id="sch_cat"><option value="">— choose —</option>${cats.map(c => `<option ${c === cat ? "selected" : ""}>${esc(c)}</option>`).join("")}</select></label>
        <label class="fld" for="sch_bm">Benchmark<select id="sch_bm">${bms.map(c => `<option value="${c}" ${c === bm ? "selected" : ""}>${esc(BM_LABEL[c] || c)}</option>`).join("")}</select></label>
        <button class="btn primary" type="submit" ${ENTRY.busy ? "disabled" : ""}>${ENTRY.busy ? "Adding… (fetching NAV history)" : "Add scheme"}</button>
      </form>
      <p class="muted small" style="margin:6px 0 0">Category and benchmark are suggested from the name; check them. Adding fetches the NAV history of both plans (internet needed) and rebuilds the data; at least 13 month-end NAVs are required. For look-through, apply the AMC's monthly portfolio file under <b>Live data</b>.</p>`;
    })() : "";
    add = `<div class="cn-panel"><b class="small">Add a mutual-fund scheme</b>
      <form id="schSearch" class="row" style="align-items:flex-end;margin-top:8px" autocomplete="off" novalidate>
        <label class="fld" for="sch_q">Search AMFI's scheme list<input type="search" id="sch_q" value="${esc(S.q)}" placeholder="name, AMFI code or ISIN — e.g. parag parikh flexi" style="width:340px"></label>
        <button class="btn" type="submit" ${S.searching ? "disabled" : ""}>${S.searching ? "Searching…" : "Search"}</button>
      </form>
      <p class="muted small" style="margin:6px 0 0">Growth option only (Direct, with the Regular plan where it exists). Equity-oriented schemes only: the app's tax view and look-through model equity funds, so debt, liquid, gold, international, fund-of-funds and hedged (arbitrage, balanced advantage) schemes are not accepted.</p>
      ${res}${form}</div>`;
  }
  return readOnlyNote("add schemes") + add + table("schemes", cols, rows, { sort: { k: "scheme_id", d: "asc" }, noun: "schemes", search: r => `${r.scheme_id} ${r.name} ${r.amc} ${r.category}`, placeholder: "Search schemes" });
}

/* ---------------- securities (listed-equity master) ---------------- */
const ORIGIN_LABEL = { user: "Added", universe: "Research universe", family: "Demo family", fund: "Held via funds" };
async function equitySearch(q) {
  const E = ENTRY.eq; E.q = q; E.pick = null;
  if (q.trim().length < 2) return toast("Type at least 2 characters of the company name or NSE symbol.", "warn");
  E.searching = true; render();
  try { E.res = await api("/api/search?q=" + encodeURIComponent(q.trim()), { timeout: 30000 }); }
  catch (e) { toast(e.message, "warn"); }
  finally { E.searching = false; render(); }
}
function securitiesTab() {
  const E = ENTRY.eq, sectors = ENTRY.ledger?.sectors || [...new Set(DB.companies.map(c => c.sector))].sort();
  const nTx = code => DB.transactions.filter(t => t.asset_type === "EQ" && t.instrument === code).length;
  const inMaster = r => DB.companies.find(c => c.code === r.symbol || (r.isin && c.isin === r.isin));
  const rows = DB.companies.filter(c => E.origin === "all" || (c.origin || "fund") === E.origin)
    .map(c => ({ ...c, px: curPrice("EQ", c.code, ""), ntx: nTx(c.code), org: c.origin || "fund" }));
  const cols = [
    { k: "code", label: "Symbol", fmt: v => `<span class="mono">${esc(v)}</span>` },
    { k: "name", label: "Company", fmt: (v, r) => `<span class="nm">${esc(v)}</span><span class="sub mono">${esc(r.isin || "")}</span>` },
    { k: "sector", label: "Sector", fmt: (v, r) => r.org === "user" && canEnter() ? `<select data-eqsec="${esc(r.code)}" aria-label="Sector of ${esc(r.name)}">${sectors.map(s => `<option ${s === v ? "selected" : ""}>${esc(s)}</option>`).join("")}</select>` : esc(v) },
    { k: "cap", label: "Size" },
    { k: "px", label: `Price ${fmtDate(DB.meta.as_on)}`, num: true, fmt: v => isNum(v) ? "₹" + nf(v, 2) : `<span class="muted small">not priced</span>` },
    { k: "has_fin", label: "Statements", fmt: v => v ? pill("ok", "Yes") : pill("neutral", "No") },
    { k: "ntx", label: "Transactions", num: true },
    { k: "org", label: "Source", fmt: v => tag(ORIGIN_LABEL[v] || v) },
  ];
  if (canEnter() && rows.some(r => r.org === "user")) cols.push({ k: "a", label: "", fmt: (v, r) => r.org === "user" ? (r.ntx ? `<span class="muted small">in use</span>` : delBtn("eq", r.code)) : "", csv: () => "" });
  let add = "";
  if (canEnter()) {
    const res = E.res ? (E.res.length ? `<div class="stack" style="gap:6px;margin-top:10px">${E.res.map((r, i) => {
        const m = inMaster(r), bse = r.exchange === "BSE";
        return `<div class="row" style="gap:10px;align-items:center;border:1px solid var(--line);border-radius:8px;padding:8px 10px;${E.pick === i ? "outline:2px solid var(--acc,#0e7c86)" : ""}">
          <div style="flex:1;min-width:240px"><span class="nm">${esc(r.name)}</span><span class="sub mono">${esc(r.exchange || "NSE")}: ${esc(r.symbol)}${r.isin ? " · " + esc(r.isin) : ""}</span></div>
          ${m && isNum(curPrice("EQ", m.code, "")) ? pill("ok", `Priced as ${m.code}: use it directly`) : bse ? pill("warn", "BSE only: cannot be priced") : `${m ? `<span class="muted small">Held via funds, not priced yet</span>` : ""}<button class="btn ${E.pick === i ? "primary" : ""} sm" data-eqpick="${i}">${E.pick === i ? "Selected" : m ? "Select to price it" : "Select"}</button>`}
        </div>`; }).join("")}</div>` : `<p class="muted small" style="margin:8px 0 0">No NSE-listed company matches “${esc(E.q)}”.</p>`) : "";
    const r = E.pick != null ? E.res[E.pick] : null;
    const form = r ? `<form id="eqForm" class="row" style="align-items:flex-end;margin-top:12px" autocomplete="off" novalidate>
        <div class="fld">Company<b style="height:34px;display:flex;align-items:center">${esc(r.name)} (${esc(r.symbol)})</b></div>
        <label class="fld" for="eq_sec">Sector<select id="eq_sec"><option value="">Automatic (from Yahoo's classification)</option>${sectors.map(s => `<option>${esc(s)}</option>`).join("")}</select></label>
        <button class="btn primary" type="submit" ${ENTRY.busy ? "disabled" : ""}>${ENTRY.busy ? "Adding… (fetching prices)" : "Add company"}</button>
      </form>
      <p class="muted small" style="margin:6px 0 0">Adding fetches this company's prices and annual statements (internet needed) and rebuilds the data; at least 13 month-end prices are required. Statements are optional: without them the company is valued but not scored. The sector counts toward the sector limit, so check it after adding.</p>` : "";
    add = `<div class="cn-panel"><b class="small">Add a listed company</b>
      <form id="eqSearch" class="row" style="align-items:flex-end;margin-top:8px" autocomplete="off" novalidate>
        <label class="fld" for="eq_q">Search NSE's equity list<input type="search" id="eq_q" value="${esc(E.q)}" placeholder="name or NSE symbol — e.g. 3M India, TITAN" style="width:320px"></label>
        <button class="btn" type="submit" ${E.searching ? "disabled" : ""}>${E.searching ? "Searching…" : "Search"}</button>
      </form>
      <p class="muted small" style="margin:6px 0 0">A company already priced here can be used in transactions directly. The ${DB.companies.filter(c => c.origin === "fund" && !isNum(curPrice("EQ", c.code, ""))).length} stocks known only from the funds' portfolios are listed for look-through but have no price; selecting one fetches its price so it can be recorded.</p>
      ${res}${form}</div>`;
  }
  const filt = `<div class="row small" style="gap:6px;margin:12px 0 6px">${[["all", "All"], ...Object.entries(ORIGIN_LABEL).filter(([k]) => k === E.origin || DB.companies.some(c => (c.origin || "fund") === k))].map(([k, l]) => `<button class="btn ${E.origin === k ? "primary" : "ghost"} sm" data-eqorigin="${k}">${l} (${k === "all" ? DB.companies.length : DB.companies.filter(c => (c.origin || "fund") === k).length})</button>`).join("")}</div>`;
  return readOnlyNote("add companies") + add + filt + table("securities", cols, rows, { sort: { k: "code", d: "asc" }, limit: 60, noun: "companies", search: r => `${r.code} ${r.name} ${r.isin} ${r.sector}`, placeholder: "Search the security master" });
}

function transactionsTab() {
  const M = state.member, rows = DB.transactions.filter(t => M === "ALL" || t.member_id === M).map(t => ({ ...t, ent: memName(t.member_id), inst: entryInstName(t.asset_type, t.instrument), src: t.source || "demo" }));
  const cols = [
    { k: "txn_id", label: "Ref", fmt: v => `<span class="mono small">${esc(v)}</span>` }, { k: "date", label: "Date", fmt: v => fmtDate(v) },
    { k: "ent", label: "Entity" }, { k: "inst", label: "Instrument", fmt: (v, r) => `<span class="nm">${esc(v)}</span>${r.plan ? ` <span class="muted small">${esc(r.plan)}</span>` : ""}${r.note ? `<span class="sub">${esc(r.note)}</span>` : ""}` },
    { k: "txn_type", label: "Type", fmt: v => tag(v) }, { k: "units", label: "Units", num: true, fmt: (v, r) => nf(v, r.asset_type === "MF" ? 3 : 0) },
    { k: "price", label: "Price", num: true, fmt: v => "₹" + nf(v, 2) }, { k: "amount", label: "Amount", num: true, fmt: v => fmtAuto(v) },
    { k: "src", label: "Source", fmt: v => tag(v === "user" ? "Entered" : "Demo") },
  ];
  if (canEnter() && rows.some(r => r.src === "user")) cols.push({ k: "a", label: "", fmt: (v, r) => r.src === "user" ? `<span class="row" style="gap:4px"><button class="btn ghost sm" data-tedit="${esc(r.txn_id)}">Edit</button>${delBtn("txn", r.txn_id)}</span>` : "", csv: () => "" });
  return readOnlyNote("record transactions") + (canEnter() ? importPanel() + txForm() : "")
    + `<h3 style="margin:18px 0 6px;font-size:13.5px">${M === "ALL" ? "All entities" : esc(memName(M))} · ${rows.length} transactions</h3>`
    + table("txns", cols, rows, { sort: { k: "date", d: "desc" }, limit: 60, noun: "transactions", search: r => `${r.txn_id} ${r.ent} ${r.inst} ${r.txn_type} ${r.note || ""}`, placeholder: "Search transactions" });
}
function txRead() {
  return { member_id: $("#tx_member").value, asset_type: $("#tx_asset").value, instrument: $("#tx_inst").value, plan: $("#tx_plan")?.value || "",
    txn_type: $("#tx_type").value, date: $("#tx_date").value, units: $("#tx_units").value === "" ? null : +$("#tx_units").value, price: $("#tx_price").value === "" ? null : +$("#tx_price").value };
}
function txCheck(t) {
  if (!t.date || t.date > DB.meta.as_on) return `Choose a date on or before the valuation date (${fmtDate(DB.meta.as_on)}).`;
  if (!(t.units > 0)) return "Enter units greater than zero.";
  if (t.asset_type === "EQ" && !Number.isInteger(t.units)) return "Equity is recorded in whole shares.";
  if (!(t.price > 0)) return "Enter a price greater than zero.";
  if (t.txn_type === "Sell") { const h = unitsHeld(t.member_id, t.instrument, t.plan, t.date, ENTRY.editTxn); if (t.units > h + 1e-9) return `Only ${nf(h, t.asset_type === "MF" ? 3 : 0)} units are held on that date.`; }
  return null;
}

/* ---------------- users (admin) ---------------- */
function usersTab() {
  if (!isAdmin()) return `<p class="note">Only an admin can manage users.</p>`;
  const roles = ["viewer", "analyst", "admin"], me = BRIDGE.me.user;
  const cols = [
    { k: "user", label: "User", fmt: v => `<span class="nm mono">${esc(v)}</span>${v === me ? ` <span class="muted small">(you)</span>` : ""}` },
    { k: "role", label: "Role", fmt: (v, r) => r.user === me ? tag(v) : `<select data-urole="${esc(r.user)}" aria-label="Role for ${esc(r.user)}">${roles.map(x => `<option ${x === v ? "selected" : ""}>${x}</option>`).join("")}</select>` },
    { k: "active", label: "Status", fmt: (v, r) => r.locked ? pill("warn", "Locked (15 min)") : v ? pill("ok", "Active") : pill("neutral", "Disabled") },
    { k: "last_login", label: "Last sign-in", fmt: v => v ? `<span class="small">${esc(v.replace("T", " "))}</span>` : "—" },
    { k: "a", label: "", fmt: (v, r) => r.user === me ? "" : `<span class="row" style="gap:4px"><button class="btn ghost sm" data-uact="toggle|${esc(r.user)}">${r.active ? "Disable" : "Enable"}</button><button class="btn ghost sm" data-uact="reset|${esc(r.user)}">Reset password</button></span>`, csv: () => "" },
  ];
  const reset = ENTRY.resetUser ? `<form id="resetForm" class="row" style="align-items:flex-end;margin:10px 0" novalidate><label class="fld" for="ureset_pw">New password for ${esc(ENTRY.resetUser)}<input type="password" id="ureset_pw" autocomplete="new-password" minlength="6" maxlength="8" style="width:220px"></label><button class="btn primary" type="submit">Set password</button><button class="btn ghost" type="button" data-ecancel="1">Cancel</button></form>` : "";
  return `<form id="userForm" class="row" style="align-items:flex-end" autocomplete="off" novalidate>
      <label class="fld" for="u_name">User name<input type="text" id="u_name" maxlength="32" placeholder="e.g. analyst.rao" style="width:180px"></label>
      <label class="fld" for="u_role">Role<select id="u_role">${roles.map(x => `<option ${x === "analyst" ? "selected" : ""}>${x}</option>`).join("")}</select></label>
      <label class="fld" for="u_pw">Initial password<input type="password" id="u_pw" autocomplete="new-password" minlength="6" maxlength="8" style="width:200px"></label>
      <button class="btn primary" type="submit">Create user</button>
    </form>
    <p class="muted small">Passwords: 6 to 8 characters with upper- and lower-case letters and a digit. Stored only as salted PBKDF2 hashes. Five wrong attempts lock an account for 15 minutes. Viewer: read only · Analyst: + entities, transactions, data refresh · Admin: + users.</p>
    ${reset}${table("users", cols, ENTRY.users || [], { noun: "users", export: false })}`;
}

/* ---------------- audit (saved on the PC) ---------------- */
function auditTabLive() {
  const brief = x => x == null ? "" : typeof x === "object" ? Object.entries(x).filter(([k]) => !/^(created|updated)_/.test(k)).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : v}`).join(" · ") : String(x);
  const rows = (ENTRY.audit || []).map(a => ({ ...a, change: [a.before != null ? "was " + brief(a.before) : "", a.after != null ? "now " + brief(a.after) : "", a.detail || ""].filter(Boolean).join(" → ") }));
  return `<p class="note">Saved on this PC in <span class="mono">data/user/audit.jsonl</span> (append-only). Every entry, edit, deletion, sign-in and user change, with who and when.</p>`
    + table("auditLive", [{ k: "at", label: "Time", fmt: v => `<span class="mono small">${esc(String(v).replace("T", " "))}</span>` }, { k: "user", label: "User", fmt: v => `<span class="mono">${esc(v)}</span>` }, { k: "action", label: "Action", fmt: v => tag(v) }, { k: "change", label: "Change", cls: () => "wrap", fmt: v => `<span class="small">${esc(v)}</span>` }],
      rows, { sort: { k: "at", d: "desc" }, limit: 100, noun: "entries", search: r => `${r.user} ${r.action} ${r.change}`, placeholder: "Search the audit trail" });
}

/* ---------------- events ---------------- */
document.addEventListener("submit", async e => {
  const f = e.target;
  if (!["entForm", "txForm", "userForm", "resetForm", "cnForm", "casForm", "schSearch", "schForm", "eqSearch", "eqForm"].includes(f.id)) return;
  e.preventDefault();
  if (f.id === "schSearch") return schemeSearch($("#sch_q").value);
  if (f.id === "eqSearch") return equitySearch($("#eq_q").value);
  if (f.id === "eqForm") {
    const r = ENTRY.eq.res[ENTRY.eq.pick];
    const x = await entryPost("/api/equities", { action: "add", symbol: r.symbol, sector: $("#eq_sec").value || null },
      y => `${y.record.name} added as ${y.record.code} (${y.record.sector}${y.record.has_fin ? "" : ", no statements: valued, not scored"}). It can now be used in transactions.`);
    if (x) { ENTRY.eq = { ...ENTRY.eq, res: null, pick: null, q: "", origin: "user" }; render(); }
    return;
  }
  if (f.id === "schForm") {
    const g = ENTRY.sch.res[ENTRY.sch.pick];
    const body = { action: "add", amfi_code_direct: g.direct.code, amfi_code_regular: g.regular?.code || "", name: $("#sch_name").value.trim(), category: $("#sch_cat").value, benchmark: $("#sch_bm").value };
    if (!body.category) return toast("Choose the category.", "warn");
    const r = await entryPost("/api/schemes", body, x => `${x.record.name} added as ${x.record.scheme_id}. It can now be used in transactions and CAS imports.`);
    if (r) { ENTRY.sch = { ...ENTRY.sch, res: null, pick: null, q: "" }; render(); }
    return;
  }
  if (f.id === "cnForm") return cnRead();
  if (f.id === "casForm") return casRead();
  if (f.id === "entForm") {
    const body = { name: $("#ent_name").value.trim(), type: $("#ent_type").value, relationship: $("#ent_rel").value.trim() };
    if (body.name.length < 2) return toast("Enter the entity name (at least 2 characters).", "warn");
    const r = ENTRY.editEnt
      ? await entryPost("/api/entities", { action: "update", member_id: ENTRY.editEnt, ...body }, x => `${x.record.name} updated.`)
      : await entryPost("/api/entities", { action: "add", ...body }, x => `${x.record.name} added as ${x.record.member_id}.`);
    if (r) { ENTRY.editEnt = null; render(); }
  } else if (f.id === "txForm") {
    const t = txRead(), err = txCheck(t);
    if (err) return toast(err, "warn");
    const r = ENTRY.editTxn
      ? await entryPost("/api/transactions", { action: "update", txn_id: ENTRY.editTxn, ...t }, x => `${x.record.txn_id} updated.`)
      : await entryPost("/api/transactions", { action: "add", ...t }, x => `${x.record.txn_id} recorded: ${x.record.txn_type} ${nf(x.record.units, t.asset_type === "MF" ? 3 : 0)} ${entryInstName(t.asset_type, t.instrument)}.`);
    // keep entity, instrument, plan and date for the next entry; clear only the amounts
    if (r) { ENTRY.editTxn = null; ENTRY.tx = { asset: t.asset_type, member_id: t.member_id, instrument: t.instrument, plan: t.plan, date: t.date, txn_type: t.txn_type }; render(); }
  } else if (f.id === "userForm") {
    const body = { action: "create", user: $("#u_name").value.trim().toLowerCase(), role: $("#u_role").value, password: $("#u_pw").value };
    if (!body.user || !body.password) return toast("Enter a user name and an initial password.", "warn");
    await entryPost("/api/users", body, () => `User ${body.user} created.`);
  } else if (f.id === "resetForm") {
    const pw = $("#ureset_pw").value;
    if (!pw) return toast("Enter the new password.", "warn");
    const r = await entryPost("/api/users", { action: "update", user: ENTRY.resetUser, password: pw }, () => `Password reset for ${ENTRY.resetUser}; their sessions were signed out.`);
    if (r) { ENTRY.resetUser = null; render(); }
  }
});
document.addEventListener("click", async e => {
  const t = e.target.closest("button"); if (!t) return;
  const d = t.dataset;
  if (d.impsw) { ENTRY.imp = d.impsw; return render(); }
  if (d.schpick) { ENTRY.sch.pick = +d.schpick; return render(); }
  if (d.eqpick) { ENTRY.eq.pick = +d.eqpick; return render(); }
  if (d.eqorigin) { ENTRY.eq.origin = d.eqorigin; return render(); }
  if (d.casaddsch) { state.tab.data = "schemes"; go("data"); return schemeSearch(d.casaddsch); }
  if (d.casrecord) return casRecord();
  if (d.casdiscard) { ENTRY.cas = null; return render(); }
  if (d.cnrecord) return cnRecord();
  if (d.cndiscard) { ENTRY.cn = null; return render(); }
  if (d.ecancel) { if (ENTRY.editTxn) ENTRY.tx = { asset: ENTRY.tx.asset }; ENTRY.editEnt = ENTRY.editTxn = ENTRY.confirm = ENTRY.resetUser = null; return render(); }
  if (d.eedit) { ENTRY.editEnt = d.eedit; return render(); }
  if (d.tedit) { const x = DB.transactions.find(r => r.txn_id === d.tedit); ENTRY.editTxn = d.tedit; ENTRY.tx = { ...x, asset: x.asset_type }; window.scrollTo(0, 0); return render(); }
  if (d.eask) { ENTRY.confirm = d.eask; return render(); }
  if (d.edel) {
    const [kind, id] = d.edel.split("|"); ENTRY.confirm = null;
    if (kind === "sch") return entryPost("/api/schemes", { action: "delete", scheme_id: id }, () => `${id} removed.`);
    if (kind === "eq") return entryPost("/api/equities", { action: "delete", symbol: id }, () => `${id} removed from the security master.`);
    return kind === "ent" ? entryPost("/api/entities", { action: "delete", member_id: id }, () => `${id} deleted.`) : entryPost("/api/transactions", { action: "delete", txn_id: id }, () => `${id} deleted.`);
  }
  if (d.uact) {
    const [act, user] = d.uact.split("|");
    if (act === "reset") { ENTRY.resetUser = user; return render(); }
    const cur = (ENTRY.users || []).find(u => u.user === user);
    return entryPost("/api/users", { action: "update", user, active: !cur.active }, () => `${user} ${cur.active ? "disabled" : "enabled"}.`);
  }
  if (t.id === "signOut") { try { await api("/api/logout", { method: "POST", body: "{}" }); } catch (err) { /* already signed out */ } location.href = "/login"; }
});
document.addEventListener("change", e => {
  const t = e.target;
  if (ENTRY.cn && (t.dataset.cninc || t.dataset.cnpick || t.name === "cn_basis" || t.id === "cn_date")) {
    const c = ENTRY.cn;
    if (t.dataset.cninc) c.trades[+t.dataset.cninc].include = t.checked;
    if (t.dataset.cnpick) { const x = c.trades[+t.dataset.cnpick]; x.instrument = t.value || null; x.match = null; }
    if (t.name === "cn_basis") ENTRY.cnBasis = t.value;
    if (t.id === "cn_date") c.date = t.value || null;
    return render();
  }
  if (t.id === "cn_member" || t.id === "cas_member") { ENTRY.cnMember = t.value; return; }
  if (t.dataset.eqsec) return entryPost("/api/equities", { action: "update", symbol: t.dataset.eqsec, sector: t.value }, () => `${t.dataset.eqsec} sector set to ${t.value}.`);
  if (t.dataset.schcat) return entryPost("/api/schemes", { action: "update", scheme_id: t.dataset.schcat, category: t.value }, () => `${t.dataset.schcat} category set to ${t.value}.`);
  if (t.dataset.schbm) return entryPost("/api/schemes", { action: "update", scheme_id: t.dataset.schbm, benchmark: t.value }, () => `${t.dataset.schbm} benchmark set to ${BM_LABEL[t.value] || t.value}.`);
  if (ENTRY.cas && (t.dataset.casinc || t.name === "cas_basis")) {
    if (t.dataset.casinc) { const [fi, ti] = t.dataset.casinc.split("|").map(Number); ENTRY.cas.folios[fi].txns[ti].include = t.checked; }
    if (t.name === "cas_basis") ENTRY.casBasis = t.value;
    return render();
  }
  if (t.id === "demoToggle") return entryPost("/api/settings", { include_demo_family: t.checked }, () => t.checked ? "Demo family included." : "Demo family hidden.");
  if (t.dataset.urole) return entryPost("/api/users", { action: "update", user: t.dataset.urole, role: t.value }, () => `${t.dataset.urole} is now ${t.value}.`);
  if (["tx_member", "tx_asset", "tx_inst", "tx_plan", "tx_type", "tx_date"].includes(t.id)) {
    const cur = txRead(); ENTRY.tx = { ...ENTRY.tx, ...cur, asset: cur.asset_type };
    if (t.id === "tx_asset") { ENTRY.tx.instrument = null; ENTRY.tx.txn_type = null; ENTRY.tx.plan = null; }
    return render();  // edits live in ENTRY.tx (a draft); DB changes only after the bridge saves
  }
});
document.addEventListener("input", e => {
  if (e.target.id !== "tx_units" && e.target.id !== "tx_price") return;
  const u = +$("#tx_units").value, p = +$("#tx_price").value, el = $("#tx_amt");
  if (el) el.textContent = u > 0 && p > 0 ? "₹" + nf(u * p, 2) : "—";
  ENTRY.tx.units = $("#tx_units").value === "" ? null : u; ENTRY.tx.price = $("#tx_price").value === "" ? null : p;
});
