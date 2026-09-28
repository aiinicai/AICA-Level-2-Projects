/* ==================================================================
   App shell: navigation, rendering, events
   ================================================================== */
const VIEWS = [
  { id: "dashboard", label: "Dashboard", group: "Portfolio", fn: () => vDashboard() },
  { id: "holdings", label: "Holdings & returns", group: "Portfolio", fn: () => vHoldings() },
  { id: "lookthrough", label: "Look-through exposure", group: "Portfolio", fn: () => vLookthrough() },
  { id: "allocation", label: "Allocation & rebalancing", group: "Portfolio", fn: () => vAllocation() },
  { id: "overlap", label: "Fund overlap", group: "Funds", fn: () => vOverlap() },
  { id: "funds", label: "Performance & risk", group: "Funds", fn: () => vFunds() },
  { id: "activity", label: "Fund-manager activity", group: "Funds", fn: () => vActivity() },
  { id: "concentration", label: "Concentration & limits", group: "Risk", fn: () => vConcentration() },
  { id: "stress", label: "Stress testing", group: "Risk", fn: () => vStress() },
  { id: "screener", label: "Stock screener", group: "Equity research", fn: () => vScreener() },
  { id: "company", label: "Company analyser", group: "Equity research", fn: () => vCompany() },
  { id: "extract", label: "AI data extraction", group: "Equity research", fn: () => vExtract() },
  { id: "data", label: "Data & controls", group: "Controls", fn: () => vData() },
  { id: "method", label: "Methodology", group: "Controls", fn: () => vMethod() },
  { id: "report", label: "Family report", group: "Controls", fn: () => vReport() },
];
function renderNav() {
  const crit = alerts(state.member).filter(a => a.sev === "crit").length;
  let g = "", html = "";
  VIEWS.forEach(v => {
    if (v.group !== g) { g = v.group; html += `<div class="nav-g">${esc(g)}</div>`; }
    html += `<button class="nav-i" data-view="${v.id}" ${state.view === v.id ? 'aria-current="page"' : ""}><svg viewBox="0 0 16 16" aria-hidden="true">${NI[v.id === "funds" ? "funds" : v.id] || NI.dashboard}</svg>${esc(v.label)}${v.id === "concentration" && crit ? `<span class="badge" title="${crit} policy breaches">${crit}</span>` : ""}</button>`;
  });
  $("#nav").innerHTML = html;
}
function renderTop() {
  const v = VIEWS.find(x => x.id === state.view);
  $("#crumb").innerHTML = `${esc(v.group)} <span aria-hidden="true">/</span> <b>${esc(v.label)}</b>`;
  $("#entSel").innerHTML = [["ALL", "Whole family"], ...DB.members.map(m => [m.member_id, m.name])].map(([k, n]) => `<option value="${k}" ${k === state.member ? "selected" : ""}>${esc(n)}</option>`).join("");
  $("#unitSeg").innerHTML = seg("units", [["cr", "₹ Cr"], ["lakh", "₹ L"], ["inr", "₹"]], state.units, { label: "Amount units" });
  const dark = document.documentElement.dataset.theme === "dark" || (!document.documentElement.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);
  $("#themeBtn").innerHTML = dark ? ICON.sun : ICON.moon; $("#themeBtn").setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
  $("#asOn").textContent = DB.meta.as_on ? `Valuation date ${fmtDate(DB.meta.as_on)}` : "No data yet";
  const lv = $("#liveChip");
  if (lv) lv.innerHTML = BRIDGE.live
    ? `<span class="row" style="gap:6px;flex-wrap:nowrap"><button class="live on" data-go="data" title="Connected to the LookThrough Data Bridge">● Live</button>${BRIDGE.me ? `<span class="who" title="Signed in"><span>${esc(BRIDGE.me.user)}</span><span class="tag">${esc(BRIDGE.me.role[0].toUpperCase() + BRIDGE.me.role.slice(1))}</span></span><button class="btn ghost sm" id="signOut">Sign out</button>` : ""}</span>`
    : `<button class="live" data-go="data" title="Read-only snapshot. Start_LookThrough.bat enables sign-in and data entry.">${hasData() ? "Snapshot (read-only)" : "No data"}</button>`;
}
function render() {
  hideTip();
  Object.keys(CHARTS).forEach(k => delete CHARTS[k]);
  renderNav(); renderTop(); measure();
  const v = VIEWS.find(x => x.id === state.view) || VIEWS[0];
  try { $("#content").innerHTML = (!hasData() && !["data", "method"].includes(v.id)) ? vEmpty() : v.fn(); renderJob(); }
  catch (e) { console.error(e); $("#content").innerHTML = card("This screen could not be drawn", `<p class="muted">Something in the data prevented this screen from being drawn. Check Data &amp; controls → Reconciliation.</p><details class="small muted"><summary>Technical detail</summary>${esc(e.message)}</details><div class="row" style="margin-top:12px"><button class="btn primary" data-reset-screen="1">Reset this screen</button><button class="btn" data-view="dashboard">Back to dashboard</button></div>`); }
  if (state.view === "extract" && hasData() && $("#srcText")) {
    const el = $("#srcText"); el.value = state.srcText ?? sampleText();
    $("#llmPrompt").value = llmPrompt(IX.co[$("#exCo").value].name, $("#exFy").value);
    if (!state.extracted) state.extracted = extract(el.value);
    renderExtractOut();
  }
}
function go(view, arg) {
  if (view === "company" && arg) state.company = arg;
  if (view === "overlap" && arg) state.pair = arg.split("|");
  state.view = view; setNav(false); render(); window.scrollTo(0, 0);
  try { history.replaceState(null, "", "#" + view); } catch (e) { /* ignore */ }
}
/** The slide-out navigation (tablets and phones): a dimmed backdrop behind it; a tap outside or Escape closes it. */
function setNav(open) { $("#side").classList.toggle("open", open); document.body.classList.toggle("nav-open", open); }
document.addEventListener("click", e => { if (document.body.classList.contains("nav-open") && !(e.target.closest && e.target.closest("#side, #menuBtn"))) setNav(false); });
document.addEventListener("keydown", e => { if (e.key === "Escape" && document.body.classList.contains("nav-open")) setNav(false); });
function setTheme(t) { document.documentElement.dataset.theme = t; prefs.set("theme", t); renderTop(); render(); }

/* ---------------- events ---------------- */
document.addEventListener("click", e => {
  const t = e.target.closest("button,[data-row],[data-click],[data-pair],[data-pal],a"); if (!t) return;
  const d = t.dataset;
  if (d.view) return go(d.view);
  if (d.go) { const [v, a] = d.go.split("|"); return go(v, a); }
  if (d.click) { const [k, v] = d.click.split("|"); if (k === "company") return go("company", v); if (k === "fund") { state.fund = v; return go("funds"); } }
  if (d.pal) return runPalette(d.pal);
  if (d.pair) { state.pair = d.pair.split("|"); state.sim = { ...(state.sim || {}), from: heldSchemes(state.member).includes(state.pair[0]) ? state.pair[0] : state.pair[1], to: state.pair[1] === state.sim?.from ? state.pair[0] : state.pair[1], frac: state.sim?.frac || 1 }; if (state.sim.from === state.sim.to) state.sim.to = "S03"; return state.view === "overlap" ? render() : go("overlap"); }
  if (d.company) { state.company = d.company; state.tab.company = state.view === "company" ? state.tab.company : "overview"; return go("company"); }
  if (d.fund) { state.fund = d.fund; return go("funds"); }
  if (d.openAdd) return openAdd();
  if (d.fetchCo) return fetchCompany(d.fetchCo);
  if (d.closeAdd) return closeAdd();
  if (d.member) { state.member = d.member; return render(); }
  if (d.sort) { const [id, k] = d.sort.split("|"), cur = state.sort[id] || TABLES[id]?.o.sort; state.sort[id] = { k, d: cur && cur.k === k && cur.d === "desc" ? "asc" : "desc" }; return render(); }
  if (d.showall) { state.sel["all-" + d.showall] = true; return render(); }
  if (d.resetScreen) { state.filters = []; state.screen = "quality"; state.sim = null; state.pair = null; state.custom = null; state.stressSc = null; return render(); }
  if (d.exportTable) return download(`lookthrough_${d.exportTable}.csv`, tableCSV(d.exportTable));
  if (d.exportDb) return download(`${d.exportDb}.csv`, toCSV(DB[d.exportDb]));
  if (d.exportAlerts) return download(`alerts_${state.member}.csv`, toCSV(alerts(state.member).map(a => ({ severity: a.sev === "crit" ? "Breach" : "Warning", type: a.kind, finding: a.title, detail: a.detail }))));
  if (d.seg) {
    const v = d.v;
    if (d.seg === "units") { state.units = v; prefs.set("units", v); }
    else if (d.seg === "heldOnly") state.heldOnly = v === "1";
    else if (d.seg === "simFrac") state.sim.frac = +v;
    else if (d.seg === "wiPreset") state.whatIf = +v;
    else if (d.seg === "fundScope") state.sel.fundScope = v;
    else state[d.seg] = v;
    return render();
  }
  if (d.tab) { state.tab[d.tab] = d.v; return render(); }
  if (d.stress) { state.stressSc = d.stress; return render(); }
  if (d.preset) { state.screen = d.preset; state.filters = PRESETS[d.preset].f.map(x => [...x]); return render(); }
  if (d.fdel != null) { state.filters.splice(+d.fdel, 1); state.screen = "custom"; return render(); }
  switch (t.id) {
    case "addFilter": state.filters.push(["roe", ">=", 15]); state.screen = "custom"; return render();
    case "menuBtn": return setNav(!$("#side").classList.contains("open"));
    case "installApp": return installApp();
    case "searchBtn": return openPalette();
    case "themeBtn": { const dark = document.documentElement.dataset.theme === "dark" || (!document.documentElement.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches); return setTheme(dark ? "light" : "dark"); }
    case "printBtn": return window.print();
    case "runCustom": {
      const clamp = x => Math.max(-100, Math.min(100, +x || 0)), m = clamp($("#cMkt").value), sh = clamp($("#cShock").value);
      if (m !== (+$("#cMkt").value || 0) || sh !== (+$("#cShock").value || 0)) toast("Moves are limited to between −100% and +100%.", "warn");
      state.custom = { market: m, sector: $("#cSec").value, shock: sh }; return render();
    }
    case "runExtract": {
      state.srcText = $("#srcText").value;
      if (state.srcText.trim().length < 40) return toast("Paste the results or annual-report text first (or use Reload sample).", "warn");
      state.extracted = extract(state.srcText); renderExtractOut();
      const found = Object.values(state.extracted?.fields || state.extracted || {}).filter(f => f && isNum(f.value ?? f)).length;
      return toast(found ? "Extraction complete. Review each figure before approving." : "No figures were recognised in this text. Check that it contains the results table.", found ? "" : "warn");
    }
    case "loadSample": state.srcText = sampleText(); $("#srcText").value = state.srcText; state.extracted = extract(state.srcText); return renderExtractOut();
    case "copyPrompt": { const v = $("#llmPrompt").value; return Promise.resolve().then(() => navigator.clipboard.writeText(v)).then(() => toast("Prompt copied.", "ok"), () => { $("#llmPrompt").select(); toast("Text selected. Press Ctrl+C to copy."); }); }
    case "checkJson": {
      const msg = $("#jsonMsg"); let j;
      try { j = JSON.parse($("#llmJson").value); } catch (err) { msg.textContent = "Not valid JSON: " + err.message; return; }
      const keys = FIELDS.map(F => F.key), miss = keys.filter(k => !(k in j)), nonNum = keys.filter(k => k in j && j[k] !== null && typeof j[k] !== "number");
      if (miss.length || nonNum.length) { msg.textContent = `Schema errors. Missing: ${miss.join(", ") || "none"}. Not numeric: ${nonNum.join(", ") || "none"}.`; return; }
      state.extracted = { unit: { unit: (j.source_unit || "crore") + " (from LLM)", assumed: !j.source_unit }, origin: "LLM JSON, schema-validated", fields: Object.fromEntries(FIELDS.map(F => [F.key, { value: j[F.key], line: j[F.key + "_evidence"] || null, conf: j[F.key] == null ? "Not found" : j[F.key + "_evidence"] ? "High" : "Medium" }])) };
      msg.textContent = "Schema valid. Review the figures."; renderExtractOut(); return log("LLM_JSON", `Validated for ${j.company || "?"} ${j.fy || ""}`);
    }
    case "approveEx": {
      const code = $("#exCo").value, fy = $("#exFy").value.trim();
      if (!/^FY\d{4}-\d{2}$/.test(fy)) return toast("Use the format FY2025-26 for the fiscal year.", "warn");
      const rec = {}; FIELDS.forEach(F => { const v = $("#ex_" + F.key).value; rec[F.key] = v === "" ? null : +v; });
      if (rec.revenue == null || rec.pat == null || rec.net_worth == null) return toast("Revenue, PAT and net worth are required before posting.", "warn");
      const i = DB.financials.findIndex(x => x.code === code && x.fy === fy), before = i >= 0 ? { ...DB.financials[i] } : null;
      if (!before) return toast(`No ${fy} record for ${code}. Add the full year through Data & controls → Import.`, "warn");
      const changed = FIELDS.filter(F => rec[F.key] != null && Math.abs(rec[F.key] - (before[F.key] ?? 0)) > 0.005);
      changed.forEach(F => DB.financials[i][F.key] = rec[F.key]);
      reindex(); log("POST_FINANCIALS", `${code} ${fy}: ${changed.map(F => `${F.key} ${before[F.key]} → ${rec[F.key]}`).join("; ") || "no change"}`);
      toast(changed.length ? `Posted ${changed.length} changed figures to ${code} ${fy}. Ratios and scores updated.` : "Figures already match the database. Nothing posted.", "ok");
      state.exCo = code; state.exFy = fy; return renderExtractOut();
    }
    case "savePolicy": {
      const old = { ...DB.policy }, bad = [];
      // Every limit has a sensible range; nothing is applied unless all fields pass.
      const RANGE = { max_hhi: [0.001, 1], max_portfolio_beta: [0.1, 3], lt_months: [1, 60], ltcg_exemption: [0, 1e8], large_cap_min_cr: [1, 1e8], mid_cap_min_cr: [1, 1e8] };
      POLICY_FIELDS.flatMap(g => g[1]).forEach(([k, l]) => {
        const el = $("#pol_" + k); if (!el) return;
        const v = el.value === "" ? NaN : +el.value, [lo, hi] = RANGE[k] || [0, 100];
        if (!isFinite(v) || v < lo || v > hi) { bad.push(`${l} (allowed ${lo}–${hi})`); el.setAttribute("aria-invalid", "true"); } else { el.removeAttribute("aria-invalid"); DB.policy[k] = v; }
      });
      if (!bad.length && DB.policy.large_cap_min_cr <= DB.policy.mid_cap_min_cr) bad.push("Large-cap threshold must be above the mid-cap threshold");
      if (bad.length) { Object.assign(DB.policy, old); return toast("Not applied. Check: " + bad.join("; ") + ".", "warn"); }
      const tgt = DB.policy.target_large_pct + DB.policy.target_mid_pct + DB.policy.target_small_pct;
      if (Math.abs(tgt - 100) > 0.01) { Object.assign(DB.policy, old); return toast(`Allocation targets add up to ${tgt}%. They must total 100%.`, "warn"); }
      const ch = Object.keys(old).filter(k => old[k] !== DB.policy[k]).map(k => `${k} ${old[k]} → ${DB.policy[k]}`);
      CACHE.clear(); log("POLICY", ch.join("; ") || "no change"); toast(ch.length ? `${ch.length} ${ch.length === 1 ? "limit" : "limits"} updated: ${ch.join("; ")}.` : "No change to limits.", "ok"); return render();
    }
    case "resetSample": DB = JSON.parse(JSON.stringify(SAMPLE)); reindex(); state.extracted = null; state.srcText = null; log("RESET", "Embedded snapshot reloaded"); toast("Snapshot reloaded.", "ok"); if (BRIDGE.live) reloadDataset().then(render); return render();
    case "refreshAll": return startRefresh();
    case "scanPort": return scanPortfolios();
    case "applyPort": return applyPortfolios();
  }
});
document.addEventListener("change", e => {
  const t = e.target;
  if (t.id === "entSel") { state.member = t.value; state.sim = null; state.pair = null; return render(); }
  if (t.id === "coSel") { state.company = t.value; return render(); }
  if (t.id === "fundSel") { state.fund = t.value; return render(); }
  if (t.id === "actSel") { state.actScheme = t.value; return render(); }
  if (t.id === "simFrom") { state.sim.from = t.value; if (state.sim.to === t.value) state.sim.to = DB.schemes.find(s => s.scheme_id !== t.value).scheme_id; return render(); }
  if (t.id === "simTo") { state.sim.to = t.value; return render(); }
  if (t.id === "scrSector") { state.sel.scrSector = t.value; return render(); }
  if (t.id === "wiAmt") { const v = +t.value; if (!(v > 0)) { toast("Enter an amount above zero to see the effect of a purchase.", "warn"); t.value = state.whatIf || ""; return; } state.whatIf = v; return render(); }
  if (t.dataset.f) { const [i, k] = t.dataset.f.split("|"); state.filters[+i][{ k: 0, op: 1, v: 2 }[k]] = k === "v" ? +t.value : t.value; state.screen = "custom"; return render(); }
  if (t.id === "exCo" || t.id === "exFy") { state.exCo = $("#exCo").value; state.exFy = $("#exFy").value; $("#llmPrompt").value = llmPrompt(IX.co[$("#exCo").value].name, $("#exFy").value); return renderExtractOut(); }
  if (t.id === "portFiles" && t.files.length) { const fs = [...t.files]; t.value = ""; return uploadPortfolios(fs); }
  if (t.dataset.asg) { const [id, k] = t.dataset.asg.split("|"); (BRIDGE.assign[id] ||= {})[k] = t.type === "checkbox" ? t.checked : t.value.trim(); if (k !== "include" && BRIDGE.assign[id].scheme_id && BRIDGE.assign[id].portfolio_date) { BRIDGE.assign[id].include = true; const cb = $(`[data-asg="${id}|include"]`); if (cb) cb.checked = true; } return; }
  if (t.dataset.import && t.files[0]) { const f = t.files[0], r = new FileReader(); r.onload = () => { t.value = ""; importCSV(t.dataset.import, r.result, f.name); }; r.readAsText(f); }
});
document.addEventListener("input", e => {
  const t = e.target;
  if (t.dataset.search) { state.search[t.dataset.search] = t.value; const pos = t.selectionStart, id = t.id; render(); const el = document.getElementById(id); if (el) { el.focus(); el.setSelectionRange(pos, pos); } }
  if (t.id === "pal-q") { state.palIdx = 0; renderPalette(); }
  if (t.id === "add-q") searchCompanies(t.value);
});
document.addEventListener("keydown", e => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); return $("#palette").hidden ? openPalette() : closePalette(); }
  if (e.key === "/" && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) { e.preventDefault(); return openPalette(); }
  if (e.key === "Escape" && !$("#addModal").hidden) return closeAdd();
  if (!$("#palette").hidden) {
    const items = $$("#pal-list li[data-pal]");
    if (e.key === "Escape") return closePalette();
    if (e.key === "ArrowDown") { e.preventDefault(); state.palIdx = Math.min(items.length - 1, (state.palIdx || 0) + 1); return renderPalette(); }
    if (e.key === "ArrowUp") { e.preventDefault(); state.palIdx = Math.max(0, (state.palIdx || 0) - 1); return renderPalette(); }
    if (e.key === "Enter" && items[state.palIdx || 0]) { e.preventDefault(); return runPalette(items[state.palIdx || 0].dataset.pal); }
  }
});
document.addEventListener("mousedown", e => { if (e.target.id === "palette") closePalette(); if (e.target.id === "addModal" && !BRIDGE.job?.running) closeAdd(); });

let lastW = innerWidth;
addEventListener("resize", () => { clearTimeout(render._rt); render._rt = setTimeout(() => { if (Math.abs(innerWidth - lastW) > 40) { lastW = innerWidth; render(); } }, 180); });
/* ---------------- init ---------------- */
(function init() {
  const th = prefs.get("theme", ""); if (th) document.documentElement.dataset.theme = th;
  // following the system theme: redraw when it flips, so the header icon and heat-cell text colours (seqInk) follow it
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { if (!document.documentElement.dataset.theme) { renderTop(); render(); } });
  // printing always uses the light palette (CSS scopes dark to screen); redraw in light first so colours computed in JS
  // (heat-cell text, seqInk) match the printed fills, then put the viewer's theme back
  let printTheme = null;
  addEventListener("beforeprint", () => { printTheme = document.documentElement.dataset.theme ?? ""; document.documentElement.dataset.theme = "light"; render(); });
  addEventListener("afterprint", () => { if (printTheme === null) return; if (printTheme) document.documentElement.dataset.theme = printTheme; else delete document.documentElement.dataset.theme; printTheme = null; render(); });
  state.units = prefs.get("units", "cr");
  reindex();
  const h = (location.hash || "").slice(1); if (VIEWS.some(v => v.id === h)) state.view = h;
  log("SESSION", hasData() ? `Loaded snapshot of ${fmtDate(DB.meta.as_on)}: ${DB.transactions.length} transactions, ${DB.companies.length} securities, ${DB.schemes.length} schemes` : "Started without data");
  render();
  bridgeDetect();
})();
