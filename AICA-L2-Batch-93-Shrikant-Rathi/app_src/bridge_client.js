/* ==================================================================
   Data bridge client — talks to the local LookThrough Data Bridge
   (python bridge/lookthrough_bridge.py) when the app is opened from it.
   Offline copies and the published web version simply stay in snapshot mode.
   ================================================================== */
const BRIDGE = { live: false, checked: false, status: null, job: null, results: [], searching: false, scan: null, assign: {}, polling: false };

async function api(path, opts = {}) {
  const ctl = new AbortController(), t = setTimeout(() => ctl.abort(), opts.timeout || 15000);
  try {
    const headers = {};
    if (opts.body && !(opts.body instanceof FormData)) headers["Content-Type"] = "application/json";
    if (opts.background) headers["X-LT-Background"] = "1";  // an automatic poll: does not count as activity for the idle sign-out
    const r = await fetch(path, { ...opts, signal: ctl.signal, credentials: "same-origin", headers });
    if (r.status === 401 && BRIDGE.checked) { location.href = "/login"; throw new Error("Signed out. Please sign in again."); }
    const j = await r.json().catch(() => ({}));
    if (!r.ok && r.status !== 202 && r.status !== 409) throw new Error(j.error || `HTTP ${r.status}`);
    return j;
  } finally { clearTimeout(t); }
}
async function bridgeDetect() {
  if (!/^https?:$/.test(location.protocol) || !/^(localhost|127\.0\.0\.1)$/.test(location.hostname)) { BRIDGE.checked = true; renderTop(); return; }
  try {
    BRIDGE.status = await api("/api/status", { timeout: 4000 });
    // A bridge that answers without naming the signed-in user predates sign-in; treat it as read-only, not as a viewer.
    BRIDGE.outdated = !!BRIDGE.status.ok && !BRIDGE.status.role;
    BRIDGE.live = !!BRIDGE.status.ok && !BRIDGE.outdated;
    BRIDGE.me = BRIDGE.live ? { user: BRIDGE.status.user, role: BRIDGE.status.role } : null;
  } catch (e) { BRIDGE.live = false; }
  if (BRIDGE.outdated) toast("An older Data Bridge is running, so sign-in and data entry are unavailable. Close every 'LookThrough Data Bridge' window and run Start_LookThrough.bat again.", "warn");
  BRIDGE.checked = true;
  if (BRIDGE.live) {
    await entryLoad();
    if (BRIDGE.status.built_at && BRIDGE.status.built_at !== DB.meta.built_at) await reloadDataset();
    if (BRIDGE.status.job?.running) pollJob();
    loadQuotes();  // latest prices, shown beside the valuation-date figures
    startIdleWatch(BRIDGE.status.idle_seconds);
    pwaInit();
  }
  render();
}
/* ---------- idle sign-out: after the bridge's idle limit with no click, tap, key or scroll, the session is ended and the
   page returns to the sign-in screen, so figures are not left on an unattended screen. A warning comes a minute before.
   While the viewer is active, a light keep-alive (at most once a minute) keeps the server-side session alive. ---------- */
function startIdleWatch(idleSec) {
  if (!idleSec || BRIDGE.idleWatch) return; BRIDGE.idleWatch = true;
  // sign out a little BEFORE the server limit (keep-alives go at most once a minute), so the app always ends the session itself
  const limit = Math.max(30, idleSec - 75), mins = Math.round(idleSec / 60);
  let last = Date.now(), lastPing = Date.now(), warned = false;
  const active = () => {
    last = Date.now();
    if (warned) { warned = false; toast("Still signed in.", "ok"); }
    if (last - lastPing > 60e3) { lastPing = last; api("/api/me").catch(() => {}); }
  };
  ["pointerdown", "keydown", "wheel", "touchstart", "scroll"].forEach(ev => addEventListener(ev, active, { passive: true, capture: true }));
  setInterval(async () => {
    const idle = (Date.now() - last) / 1000;
    if (idle >= limit) {
      try { await api("/api/logout", { method: "POST", background: true, body: JSON.stringify({ reason: "idle" }) }); } catch (e) { /* already expired */ }
      location.href = "/login?idle=" + mins;
    } else if (idle >= limit - 60 && !warned) {
      warned = true; toast("You will be signed out in 1 minute without activity. Click or tap anywhere to stay signed in.", "warn");
    }
  }, 5000);
}
/* ---------- installable app (PWA): manifest, icons and a service worker that caches only the offline page and icons.
   Only when served by the bridge (a file:// copy cannot register a worker, and has no manifest to link). ---------- */
function pwaInit() {
  if (BRIDGE.pwa) return; BRIDGE.pwa = true;
  const add = (tag, attrs) => { const e = document.createElement(tag); Object.entries(attrs).forEach(([k, v]) => e.setAttribute(k, v)); document.head.appendChild(e); };
  add("link", { rel: "manifest", href: "/manifest.webmanifest" });
  add("link", { rel: "icon", href: "/icons/icon-192.png" });
  add("link", { rel: "apple-touch-icon", href: "/icons/apple-touch-icon.png" });
  add("meta", { name: "theme-color", content: "#F4F5F7", media: "(prefers-color-scheme: light)" });
  add("meta", { name: "theme-color", content: "#0B0F16", media: "(prefers-color-scheme: dark)" });
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
  addEventListener("beforeinstallprompt", e => { e.preventDefault(); BRIDGE.installPrompt = e; const b = $("#installApp"); if (b) b.hidden = false; });
  addEventListener("appinstalled", () => { BRIDGE.installPrompt = null; const b = $("#installApp"); if (b) b.hidden = true; toast("LookThrough is installed. Open it from the Start menu or desktop while the bridge is running.", "ok"); });
}
async function installApp() {
  const p = BRIDGE.installPrompt; if (!p) return toast("Use the browser menu: Install LookThrough.", "warn");
  p.prompt(); const r = await p.userChoice.catch(() => null); BRIDGE.installPrompt = null; $("#installApp").hidden = true;
  if (r && r.outcome !== "accepted") toast("Not installed. You can install it later from the browser menu.", "");
}
/* ---------- latest prices (beside the valuation-date figures, never replacing them) ---------- */
const QUOTE_REFRESH_MS = 5 * 60 * 1000;  // Yahoo is about 15 minutes delayed anyway; AMFI publishes NAVs once a day
async function loadQuotes(extra = [], { background = false } = {}) {
  if (!BRIDGE.live || BRIDGE.quotesBusy || BRIDGE.quotesUnsupported) return;
  BRIDGE.quotesBusy = true;
  try {
    const q = await api("/api/quotes" + (extra.length ? "?codes=" + encodeURIComponent(extra.join(",")) : ""), { timeout: 60000, background });
    BRIDGE.quotes = { ...q, equity: { ...(BRIDGE.quotes?.equity || {}), ...q.equity } };
    BRIDGE.quotesAsked = new Set([...(BRIDGE.quotesAsked || []), ...extra]);
    // a timed refresh never redraws under someone typing (a redraw would drop what they have entered)
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName || "") || document.querySelector("dialog[open], .modal.open");
    if (!(background && typing)) render();
  } catch (e) {
    // an earlier build of the bridge has no /api/quotes: say so once instead of waiting
    if (/not found|HTTP 404/i.test(e.message)) { BRIDGE.quotesUnsupported = true; render(); }
    else if (!background) toast("Latest prices unavailable: " + e.message, "warn");
  }
  finally { BRIDGE.quotesBusy = false; }
  // refresh while the page is open and visible; a timed refresh is not user activity, so it does not delay idle sign-out
  if (!BRIDGE.quoteTimer && BRIDGE.live && !BRIDGE.quotesUnsupported)
    BRIDGE.quoteTimer = setInterval(() => { if (BRIDGE.live && document.visibilityState === "visible") loadQuotes([], { background: true }); }, QUOTE_REFRESH_MS);
}
/** {price, date} of the latest quote for a holding, or null (offline snapshot, no quote, or not later than the valuation date). */
function latestQuote(asset, inst, plan) {
  const q = BRIDGE.quotes; if (!q) return null;
  const x = asset === "MF" ? q.mf?.[inst + "|" + plan] : q.equity?.[inst];
  if (!x) return null;
  return { price: asset === "MF" ? x.nav : x.price, date: x.date, prev: x.prev_close ?? null };
}
/** Stamp of the quotes in hand: figures built from quotes are memoised under it, so new quotes recompute them. */
const quoteStamp = () => BRIDGE.quotes?.as_of || "";
/** Holdings revalued at the latest prices (value, gain, the price and its date). A holding without a quote keeps its
    valuation-date figures and is flagged (lpx null), so a missing quote never reads as "no change". */
function latestHoldings(member = "ALL") {
  return memo("lh|" + member + "|" + quoteStamp(), () => holdings(member).map(h => {
    const q = latestQuote(h.asset_type, h.instrument, h.plan), ok = q && isNum(q.price) && q.price > 0, value = ok ? h.units * q.price : h.value;
    return { ...h, value, unrealised: value - h.cost, lpx: ok ? q.price : null, ldate: ok ? q.date : null };
  }));
}
/** Totals at the latest prices, with the price dates kept apart: share prices (Yahoo) and NAVs (AMFI, once a business day). */
function latestValue(member = "ALL") {
  const L = latestHoldings(member), q = L.filter(h => h.lpx != null), span = a => a.length ? [a[0], a[a.length - 1]] : null;
  const eqD = [...new Set(q.filter(h => h.asset_type === "EQ").map(h => h.ldate))].sort(), navD = [...new Set(q.filter(h => h.asset_type === "MF").map(h => h.ldate))].sort();
  const v = L.reduce((s, h) => s + h.value, 0), cost = L.reduce((s, h) => s + h.cost, 0);
  return { v, cost, gain: v - cost, quoted: q.length, missing: L.length - q.length, eq: span(eqD), nav: span(navD),
    olderNav: navD.length > 1 ? q.filter(h => h.asset_type === "MF" && h.ldate < navD[navD.length - 1]).length : 0,
    dates: [...new Set(q.map(h => h.ldate))].sort() };
}
/** "prices 26 Sep 2026 · NAVs 25 Sep 2026" (a range when the dates differ), for every figure at latest prices. */
function latestDates(L, short = false) {
  // short form for KPI cards: "prices 26 Sep · NAVs 24–25 Sep" (the year is the valuation date's, shown beside it)
  const d = s => short ? fmtDate(s).slice(0, -5) : fmtDate(s);
  const rng = ([a, b]) => a === b ? d(b) : short && a.slice(0, 7) === b.slice(0, 7) ? `${+a.slice(8)}–${d(b)}` : `${d(a)} to ${d(b)}`;
  const r = (a, n) => a ? `${n} ${rng(a)}` : "";
  return [r(L.eq, "prices"), r(L.nav, "NAVs")].filter(Boolean).join(" · ") + (L.missing ? ` · ${L.missing} ${short ? "unquoted" : "at valuation-date price (no quote)"}` : "");
}
/** Look-through at the latest prices: direct shares at the latest price, each fund at its latest NAV spread over its
    last disclosed weights. Weights are not re-drifted with prices (the AMC discloses them monthly). */
function lookThroughLatest(member = "ALL") { return memo("ltL|" + member + "|" + quoteStamp(), () => lookThroughOf(latestHoldings(member))); }
const QUOTE_NOTE = "Latest prices: equities from Yahoo Finance (NSE, about 15 minutes delayed in market hours, last close otherwise); fund NAVs as last published by AMFI (once each business day, late evening). Returns, risk and benchmark figures stay at the valuation date.";

async function reloadDataset() {
  try {
    const ds = await api("/api/dataset", { timeout: 60000 });
    if (ds && ds.meta) { DB = ds; reindex(); log("LIVE_DATA", `Dataset loaded from the bridge (built ${ds.meta.built_at}, valuation date ${ds.meta.as_on})`); }
  } catch (e) { toast("Could not load the latest data from the bridge: " + e.message, "warn"); }
}
async function pollJob() {
  if (BRIDGE.polling) return; BRIDGE.polling = true;
  try {
    for (;;) {
      BRIDGE.job = await api("/api/job", { background: true });
      renderJob();
      if (!BRIDGE.job.running) break;
      await new Promise(r => setTimeout(r, 1500));
    }
    if (BRIDGE.job.error) toast("The update failed: " + BRIDGE.job.error, "warn");
    else { BRIDGE.status = await api("/api/status"); await reloadDataset(); toast("Data updated.", "ok"); render(); }
  } catch (e) { toast("Lost contact with the bridge: " + e.message, "warn"); }
  BRIDGE.polling = false;
}
function renderJob() {
  const el = $("#jobLog"); if (!el || !BRIDGE.job) return;
  el.textContent = (BRIDGE.job.lines || []).slice(-14).join("\n") || "Waiting…";
  el.scrollTop = el.scrollHeight;
  const b = $("#jobState"); if (b) b.innerHTML = BRIDGE.job.running ? pill("warn", "Working… keep this page open") : BRIDGE.job.error ? pill("crit", "Failed") : pill("ok", "Finished");
}
async function startRefresh() { const r = await api("/api/refresh", { method: "POST" }); if (!r.started) toast("An update is already running.", "warn"); log("REFRESH", "Full refresh requested"); render(); pollJob(); }
let searchTimer = null;
function searchCompanies(q) {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(async () => {
    if (q.trim().length < 2) { BRIDGE.results = []; renderAddResults(); return; }
    BRIDGE.searching = true; renderAddResults();
    try { BRIDGE.results = await api("/api/search?q=" + encodeURIComponent(q), { timeout: 20000 }); } catch (e) { BRIDGE.results = []; toast("Search failed: " + e.message, "warn"); }
    BRIDGE.searching = false; renderAddResults();
  }, 300);
}
async function fetchCompany(symbol) {
  const r = await api("/api/company", { method: "POST", body: JSON.stringify({ symbol }) });
  if (!r.started) return toast("Another update is running. Try again when it finishes.", "warn");
  log("FETCH_COMPANY", symbol); state.company = symbol; state.pendingCompany = symbol;
  renderAddModal(true); pollJob().then(() => { if (IX.co[symbol]) { closeAdd(); go("company"); } });
}
async function uploadPortfolios(files) {
  const fd = new FormData(); [...files].forEach(f => fd.append("files", f, f.name));
  toast(`Uploading ${files.length} file(s)…`);
  try { const r = await api("/api/portfolios/upload", { method: "POST", body: fd, timeout: 120000 }); BRIDGE.scan = r.scan; defaultAssign(); log("PORTFOLIO_UPLOAD", r.saved.join(", ")); render(); }
  catch (e) { toast("Upload failed: " + e.message, "warn"); }
}
async function scanPortfolios() {
  try {
    BRIDGE.scan = await api("/api/portfolios/scan", { timeout: 120000 }); defaultAssign(); render();
    const n = (BRIDGE.scan || []).filter(r => r.n).length;
    toast(n ? `Folder scanned: ${n} portfolio sheet${n === 1 ? "" : "s"} found. Review them below before applying.` : "Folder scanned: no new portfolio files found.", n ? "ok" : "");
  } catch (e) { toast("Scan failed: " + e.message, "warn"); }
}
function defaultAssign() { BRIDGE.assign = {}; (BRIDGE.scan || []).forEach(r => { if (r.n) BRIDGE.assign[r.id] = { scheme_id: r.scheme_id || "", portfolio_date: r.portfolio_date || "", include: !!(r.scheme_id && r.portfolio_date) }; }); }
async function applyPortfolios() {
  const assign = Object.entries(BRIDGE.assign).filter(([, a]) => a.include && a.scheme_id && a.portfolio_date).map(([id, a]) => ({ id: +id, scheme_id: a.scheme_id, portfolio_date: a.portfolio_date }));
  if (!assign.length) return toast("Tick at least one sheet with a scheme and a date.", "warn");
  const r = await api("/api/portfolios/apply", { method: "POST", body: JSON.stringify({ assign }) });
  log("PORTFOLIO_APPLY", `${r.applied} portfolio sheets applied`); toast(`${r.applied} portfolios applied. Rebuilding the data…`, "ok");
  if (r.started) pollJob();
}

/* ---------- add-company modal ---------- */
// "+ Fetch any company" now opens the security master (Data & controls > Securities), the one place companies are added
function openAdd() { if (!BRIDGE.live) toast("Start the LookThrough Data Bridge (Start_LookThrough.bat) and sign in to add companies.", "warn"); state.tab.data = "securities"; go("data"); setTimeout(() => $("#eq_q")?.focus(), 50); }
function closeAdd() { $("#addModal").hidden = true; }
function renderAddModal(working) {
  $("#addBody").innerHTML = working ? `<p style="margin:0 0 8px">Fetching <b>${esc(state.pendingCompany)}</b> from Yahoo Finance and rebuilding the data. This takes 20–60 seconds.</p><div class="row" id="jobState"></div><pre class="log" id="jobLog">Starting…</pre>`
    : `<p class="muted small" style="margin:0 0 6px">Search any company listed on NSE by name or symbol. Its prices, financial statements and market cap are fetched and it is added to the screener and company analyser.</p><ul id="addList" class="pick"></ul>`;
  if (!working) renderAddResults(); else renderJob();
}
function renderAddResults() {
  const el = $("#addList"); if (!el) return;
  if (BRIDGE.searching) { el.innerHTML = `<li class="muted">Searching…</li>`; return; }
  el.innerHTML = BRIDGE.results.map(h => `<li><div><b>${esc(h.name)}</b><span class="sub">${esc(h.exchange)} · ${esc(h.symbol)}${h.isin ? " · " + esc(h.isin) : ""}${IX.co[h.symbol] ? " · already loaded" : ""}</span></div><button class="btn sm ${IX.co[h.symbol]?.in_universe || IX.fin[h.symbol] ? "" : "primary"}" data-fetch-co="${esc(h.symbol)}">${IX.fin[h.symbol] ? "Refresh" : "Fetch"}</button></li>`).join("") || `<li class="muted">Type at least two letters.</li>`;
}

/* ---------- Live data panel (Data & controls) ---------- */
function liveDataPanel() {
  const m = DB.meta, src = m.sources || {};
  const status = BRIDGE.live ? pill("ok", "Bridge connected") : pill("neutral", "Offline snapshot");
  const how = `<ol class="small" style="margin:0;padding-left:18px;line-height:1.8"><li>Open the folder <span class="mono">lookthrough_app</span> on your PC.</li><li>Double-click <b>Start_LookThrough.bat</b>. The first run installs Python packages (1–3 minutes).</li><li>The app opens at <span class="mono">http://localhost:8765</span> with live controls on this tab.</li></ol>`;
  const srcRows = Object.entries(src).map(([k, v]) => ({ k, v }));
  const scan = BRIDGE.scan, schemes = DB.schemes.length ? DB.schemes : [];
  const scanTable = scan ? (scan.length ? `<div class="tbl-wrap"><table class="tbl dense"><thead><tr><th><span class="th">Use</span></th><th><span class="th">File / sheet</span></th><th><span class="th">Scheme</span></th><th><span class="th">Portfolio date</span></th><th class="num"><span class="th" style="justify-content:flex-end">Holdings</span></th><th class="num"><span class="th" style="justify-content:flex-end">Equity %</span></th><th class="num"><span class="th" style="justify-content:flex-end">Listed %</span></th><th><span class="th">Checks</span></th></tr></thead><tbody>${scan.map(r => { const a = BRIDGE.assign[r.id] || {}; return `<tr><td>${r.n ? `<input type="checkbox" data-asg="${r.id}|include" ${a.include ? "checked" : ""} aria-label="Use this sheet">` : ""}</td><td class="wrap"><span class="nm">${esc(r.file)}</span><span class="sub">${esc(r.sheet || "")} · ${esc((r.title || "").slice(0, 70))}</span></td><td>${r.n ? `<select data-asg="${r.id}|scheme_id" aria-label="Scheme"><option value="">Choose…</option>${schemes.map(s => `<option value="${s.scheme_id}" ${a.scheme_id === s.scheme_id ? "selected" : ""}>${esc(s.name)}</option>`).join("")}</select>` : "—"}</td><td>${r.n ? `<input type="text" data-asg="${r.id}|portfolio_date" value="${esc(a.portfolio_date || "")}" placeholder="YYYY-MM-DD" style="width:110px" aria-label="Portfolio date">` : ""}</td><td class="num">${r.n || "—"}</td><td class="num">${fmtPct(r.equity_pct)}</td><td class="num">${fmtPct(r.listed_total_pct)}</td><td class="wrap small">${r.error ? pill("crit", r.error) : (r.warnings || []).map(w => `<div class="muted">${esc(w)}</div>`).join("") || pill("ok", "OK")}${r.top?.length ? `<div class="muted">Top: ${r.top.slice(0, 3).map(t => esc(t.name) + " " + fmtPct(t.weight)).join(", ")}</div>` : ""}</td></tr>`; }).join("")}</tbody></table></div><div class="row"><button class="btn primary" id="applyPort">Apply ticked portfolios and rebuild</button><span class="muted small">Listed % should be close to 100 minus cash. Weights far from that suggest sub-totals were read as holdings.</span></div>` : `<p class="muted">No portfolio files found in the folder.</p>`) : "";
  return `<div class="grid g2">
    ${card("Data status", `<div class="row">${status}<span class="muted small">Valuation date ${fmtDate(m.as_on)} · built ${esc((m.built_at || "—").replace("T", " "))}</span></div>
      ${BRIDGE.live ? `<div class="row"><button class="btn primary" id="refreshAll">Refresh all data now</button><button class="btn" data-open-add="1">+ Add a listed company</button><span class="muted small">Refresh downloads prices, NAVs and financials (2–6 minutes).</span></div><div class="row" id="jobState">${BRIDGE.job ? "" : ""}</div><pre class="log" id="jobLog">${esc((BRIDGE.job?.lines || []).slice(-14).join("\n") || "No update running.")}</pre>` : `<p style="margin:0">Live fetching runs through the <b>LookThrough Data Bridge</b> on your PC, because browsers and this published page are not allowed to download data from NSE, AMFI or Yahoo directly.</p>${how}`}`)}
    ${card("Where the data comes from", table("sources", [{ k: "k", label: "Data", fmt: v => esc({ navs: "NAVs", isin: "ISIN" }[v] || v.charAt(0).toUpperCase() + v.slice(1)) }, { k: "v", label: "Source", cls: () => "wrap" }], srcRows, { export: false, dense: true }) + ((m.warnings || []).length ? `<details><summary class="small">${m.warnings.length} data warnings from the last build</summary><ul class="small muted">${m.warnings.map(w => `<li>${esc(w)}</li>`).join("")}</ul></details>` : ""))}
  </div>
  ${card("Fund portfolios (AMC monthly disclosures)", `<p style="margin:0">Look-through, overlap and fund-manager activity use each scheme's official monthly portfolio. Download it from the AMC's website (usually <i>Downloads → Portfolio / Monthly portfolio disclosure</i>) for the latest two months, then add the Excel files here. The parser finds the ISIN and “% to NAV” columns, recognises the scheme and date, and shows what it read before anything is used.</p>
    ${BRIDGE.live ? `<div class="row"><label class="btn" for="portFiles">Add AMC files…</label><input type="file" id="portFiles" multiple accept=".xlsx,.xls,.xlsm,.csv" hidden><button class="btn" id="scanPort">Re-scan folder</button><span class="muted small">Files are saved in <span class="mono">data/amc_portfolios</span> on your PC.</span></div>` : `<p class="muted small" style="margin:0">Available when the app is opened from the data bridge.</p>`}
    ${scanTable}
    ${table("schemecov", [{ k: "name", label: "Scheme", fmt: (v, r) => `<span class="nm">${esc(v)}</span><span class="sub">${esc(r.amc)}</span>` }, { k: "code", label: "AMFI code", fmt: v => `<span class="mono">${esc(v || "—")}</span>` }, { k: "dates", label: "Portfolio months applied", fmt: v => v.length ? v.map(fmtMon).join(", ") : pill("warn", "None yet") }, { k: "n", label: "Stocks", num: true }], DB.schemes.map(s => ({ name: s.name, amc: s.amc, code: s.amfi_code, dates: IX.portDates[s.scheme_id] || [], n: (latestPort()[s.scheme_id] || []).length })), { export: false, dense: true })}`)}`;
}

function vEmpty() {
  return pageHead("Welcome to LookThrough", "Real market data for a family office: companies, funds, prices and financials fetched from public sources, with a dummy family portfolio on top.") +
    card("Get the data", `<p style="margin:0">This copy of the app does not contain any market data yet.</p>
    <ol style="margin:0;padding-left:18px;line-height:1.9"><li>Open the <span class="mono">lookthrough_app</span> folder on your PC.</li><li>Double-click <b>Start_LookThrough.bat</b>. The first run installs the Python packages it needs (1–3 minutes) and downloads the data (3–6 minutes).</li><li>The app opens at <span class="mono">http://localhost:8765</span>. Add the AMC portfolio files under Data &amp; controls → Live data.</li><li>After that, <span class="mono">app/LookThrough.html</span> carries a snapshot of the real data and works offline.</li></ol>
    ${BRIDGE.live ? `<div class="row"><span id="jobState"></span></div><pre class="log" id="jobLog">${esc((BRIDGE.job?.lines || []).join("\n") || "Waiting for the first refresh…")}</pre>${BRIDGE.job?.running ? "" : `<button class="btn primary" id="refreshAll">Fetch the data now</button>`}` : ""}`);
}
