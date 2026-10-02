/* ==================================================================
   UI components — tables, KPIs, cards, segmented controls, palette
   ================================================================== */
const TABLES = {};
/**
 * Sortable, searchable, exportable table.
 * cols: [{k, label, fmt(v,row) -> html, num:bool, sortV(row), csv(row), w, tip}]
 */
function table(id, cols, rows, o = {}) {
  TABLES[id] = { cols, rows, o };
  const st = state.sort[id] || o.sort || null;
  let data = rows;
  const q = (state.search[id] || "").toLowerCase().trim();
  if (q && o.search) data = data.filter(r => o.search(r).toLowerCase().includes(q));
  if (st) {
    const c = cols.find(x => x.k === st.k);
    if (c) {
      const val = r => c.sortV ? c.sortV(r) : r[c.k];
      data = [...data].sort((a, b) => { const x = val(a), y = val(b); if (x == null || x === "") return 1; if (y == null || y === "") return -1; return (typeof x === "string" ? x.localeCompare(y) : x - y) * (st.d === "asc" ? 1 : -1); });
    }
  }
  const lim = o.limit && !state.sel["all-" + id] ? o.limit : Infinity, shown = data.slice(0, lim);
  // One unit per amount column: crore if the column holds an amount of Rs 1 crore or more, else lakh (in the crore view),
  // so small-value tables (realised gains, tax) keep lakh precision.
  // An amount column is one formatted with fmtAmt (or marked amt:true); a column of mixed Cr and L cannot be scanned.
  const unitOf = c => {
    if (state.units !== "cr" || c.amt === false || !(c.amt || /fmtAmt\(/.test(String(c.fmt || "")))) return null;
    const vals = data.map(r => r[c.k]).filter(isNum).map(Math.abs);
    return vals.length ? (Math.max(...vals) >= 1e7 ? "cr" : "lakh") : null;
  };
  const units = cols.map(unitOf);
  const cell = (c, i, r) => { AMT_UNIT = units[i]; try { return c.fmt ? c.fmt(r[c.k], r) : esc(r[c.k]); } finally { AMT_UNIT = null; } };
  const head = `<tr>${cols.map(c => !c.label ? `<th scope="col"><span class="sr-only">Actions</span></th>` : `<th class="${c.num ? "num" : ""}" ${c.w ? `style="width:${c.w}"` : ""} scope="col"><button class="th" data-sort="${id}|${c.k}" aria-sort="${st && st.k === c.k ? (st.d === "asc" ? "ascending" : "descending") : "none"}">${esc(c.label)}${c.tip ? ` <span class="i" ${tipAttr(esc(c.tip))}>i</span>` : ""}<span class="car">${st && st.k === c.k ? (st.d === "asc" ? "▲" : "▼") : ""}</span></button></th>`).join("")}</tr>`;
  const body = shown.map(r => `<tr ${o.rowAttr ? o.rowAttr(r) : ""}>${cols.map((c, i) => `<td class="${c.num ? "num" : ""} ${c.cls ? c.cls(r) : ""}">${cell(c, i, r)}</td>`).join("")}</tr>`).join("");
  const foot = o.totals ? `<tfoot><tr>${cols.map(c => `<td class="${c.num ? "num" : ""}">${o.totals[c.k] ?? ""}</td>`).join("")}</tr></tfoot>` : "";
  const tools = (o.search || o.export !== false) ? `<div class="tbl-tools">${o.search ? `<input type="search" class="tbl-search" id="q-${id}" data-search="${id}" placeholder="${esc(o.placeholder || "Search")}" value="${esc(state.search[id] || "")}" aria-label="Search table">` : `<span class="muted small">${data.length} ${o.noun || "rows"}</span>`}<span class="row" style="gap:8px">${o.search ? `<span class="muted small">${data.length} ${o.noun || "rows"}</span>` : ""}${o.export !== false ? `<button class="btn ghost sm" data-export-table="${id}">${ICON.download} CSV</button>` : ""}</span></div>` : "";
  const more = data.length > lim ? `<button class="btn ghost sm more" data-showall="${id}">Show all ${data.length}</button>` : "";
  return `${tools}<div class="tbl-wrap" ${o.maxH ? `style="max-height:${o.maxH}px"` : ""}><table class="tbl ${o.dense ? "dense" : ""} ${data.some(r => String(r[cols[0].k] ?? "").length > 14) ? "namecol" : ""}"><thead>${head}</thead><tbody>${body || `<tr><td colspan="${cols.length}" class="empty">${esc(o.empty || "No rows match.")}</td></tr>`}</tbody>${foot}</table></div>${more}`;
}
function tableCSV(id) {
  const t = TABLES[id]; if (!t) return "";
  const strip = h => String(h ?? "").replace(/<[^>]+>/g, "").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#39;/g, "'").trim();
  return toCSV(t.rows.map(r => Object.fromEntries(t.cols.map(c => [c.label, c.csv ? c.csv(r) : (typeof r[c.k] === "number" ? r[c.k] : strip(c.fmt ? c.fmt(r[c.k], r) : r[c.k]))]))));
}

function kpi(label, value, sub = "", o = {}) {
  return `<div class="kpi ${o.cls || ""}"><div class="kpi-l">${esc(label)}${o.tip ? ` <span class="i" ${tipAttr(esc(o.tip))}>i</span>` : ""}</div><div class="kpi-v ${o.vcls || ""}">${value}</div>${sub ? `<div class="kpi-s">${sub}</div>` : ""}</div>`;
}
function card(title, body, o = {}) {
  return `<section class="card ${o.cls || ""}" ${o.id ? `id="${o.id}"` : ""}>${title ? `<header class="card-h"><div><h2>${title}</h2>${o.sub ? `<p>${o.sub}</p>` : ""}</div>${o.actions ? `<div class="card-a">${o.actions}</div>` : ""}</header>` : ""}<div class="card-b">${body}</div></section>`;
}
function seg(id, opts, val, o = {}) {
  return `<div class="seg ${o.cls || ""}" role="group" aria-label="${esc(o.label || id)}">${opts.map(([v, l]) => `<button data-seg="${id}" data-v="${esc(v)}" aria-pressed="${String(v) === String(val)}">${esc(l)}</button>`).join("")}</div>`;
}
const pill = (s, t) => `<span class="pill ${s}">${s === "ok" ? ICON.ok : s === "crit" ? ICON.crit : s === "warn" ? ICON.warn : ""}${esc(t)}</span>`;
const info = t => `<span class="i" ${tipAttr(esc(t))}>i</span>`;
const tag = t => `<span class="tag">${esc(t)}</span>`;
function tabs(id, list, cur) { return `<div class="tabs" role="tablist">${list.map(([k, l, n]) => `<button role="tab" data-tab="${id}" data-v="${k}" aria-selected="${k === cur}">${esc(l)}${n != null ? `<span class="cnt">${n}</span>` : ""}</button>`).join("")}</div>`; }
function meter(v, max, s = "") { const p = Math.max(0, Math.min(100, v / max * 100)); return `<div class="meter ${s}"><i style="width:${p}%"></i></div>`; }
function alertItem(a) {
  const go = a.go ? `data-go="${esc(a.go.join("|"))}"` : "";
  return `<div class="alert sev-${a.sev}"><span class="alert-ic">${a.sev === "crit" ? ICON.crit : ICON.warn}</span><div><div class="alert-k">${a.sev === "crit" ? "Breach" : "Warning"} · ${esc(a.kind)}</div><button class="alert-t" ${go}>${esc(a.title)}</button><div class="alert-d">${esc(a.detail)}</div></div></div>`;
}

const ICON = {
  ok: `<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3.5 8.5l3 3 6-7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  warn: `<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 2l6.5 11.5h-13z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M8 6.5v3.2M8 11.6v.1" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>`,
  crit: `<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.3" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M5.8 5.8l4.4 4.4M10.2 5.8l-4.4 4.4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>`,
  download: `<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 2.5v7.5M4.8 7l3.2 3.2L11.2 7M3 13h10" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  search: `<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="7" cy="7" r="4.5" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M10.5 10.5L14 14" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>`,
  sun: `<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="3" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3 3l1.4 1.4M11.6 11.6L13 13M3 13l1.4-1.4M11.6 4.4L13 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  moon: `<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M13 9.5A5.5 5.5 0 016.5 3a5.5 5.5 0 106.5 6.5z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>`,
  report: `<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 1.8h5.5L12.5 5v9.2H4z M9.3 2v3.2h3" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><path d="M6 8.5h4.5M6 11h4.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`,
  menu: `<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2.5 4h11M2.5 8h11M2.5 12h11" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>`,
};
/* nav icons: tiny line glyphs */
const NI = {
  dashboard: `<path d="M2 2h5v6H2zM9 2h5v3H9zM9 7h5v7H9zM2 10h5v4H2z"/>`,
  holdings: `<path d="M2 4h12M2 8h12M2 12h8"/>`,
  lookthrough: `<circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5L14 14M5 7h4M7 5v4"/>`,
  allocation: `<path d="M8 2v6h6A6 6 0 118 2z"/><path d="M10 1.5A5 5 0 0114.5 6H10z"/>`,
  overlap: `<circle cx="6" cy="8" r="4"/><circle cx="10" cy="8" r="4"/>`,
  funds: `<path d="M2 13l4-5 3 3 5-7"/><path d="M2 14h12"/>`,
  activity: `<path d="M2 8h3l2-5 2 10 2-5h3"/>`,
  concentration: `<path d="M3 14V9M7 14V5M11 14V2M2 14h12"/>`,
  stress: `<path d="M8 2l6 11H2z"/><path d="M8 6.5v3M8 11.5v.2"/>`,
  screener: `<path d="M2 3h12l-4.5 5.5V13l-3 1V8.5z"/>`,
  company: `<path d="M3 14V4l5-2v12M8 6h5v8M5 6v.1M5 9v.1M5 12v.1M10.5 9v.1M10.5 12v.1"/>`,
  extract: `<path d="M3 2h7l3 3v9H3z"/><path d="M5.5 8h5M5.5 10.5h5M5.5 5.5h2"/>`,
  data: `<ellipse cx="8" cy="3.5" rx="5" ry="1.8"/><path d="M3 3.5v9c0 1 2.2 1.8 5 1.8s5-.8 5-1.8v-9M3 8c0 1 2.2 1.8 5 1.8s5-.8 5-1.8"/>`,
  method: `<path d="M3 2.5h8.5a1.5 1.5 0 011.5 1.5v10H4.5A1.5 1.5 0 013 12.5z"/><path d="M3 12.5A1.5 1.5 0 014.5 11H13"/>`,
  report: `<path d="M4 1.8h5.5L12.5 5v9.2H4z"/><path d="M6 8.5h4.5M6 11h4.5"/>`,
};

/* ---------- CSV ---------- */
function toCSV(rows) {
  if (!rows.length) return "";
  const cols = Object.keys(rows[0]);
  const q = v => { const s = v == null ? "" : String(v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
  return [cols.join(","), ...rows.map(r => cols.map(k => q(r[k])).join(","))].join("\n");
}
function parseCSV(text) {
  const rows = []; let f = "", row = [], inQ = false;
  text = text.replace(/^﻿/, "");
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (inQ) { if (ch === '"') { if (text[i + 1] === '"') { f += '"'; i++; } else inQ = false; } else f += ch; }
    else if (ch === '"') inQ = true; else if (ch === ",") { row.push(f); f = ""; }
    else if (ch === "\n" || ch === "\r") { if (ch === "\r" && text[i + 1] === "\n") i++; row.push(f); rows.push(row); row = []; f = ""; }
    else f += ch;
  }
  if (f || row.length) { row.push(f); rows.push(row); }
  const [h, ...body] = rows.filter(r => r.some(x => x.trim() !== ""));
  if (!h) return [];
  const TEXT = new Set(["fy", "date", "portfolio_date", "isin", "code", "scheme_id", "member_id", "txn_id", "instrument", "amfi_code", "plan", "inception", "sell_date", "buy_date"]);
  return body.map(r => Object.fromEntries(h.map((k, j) => {
    k = k.trim(); const v = (r[j] ?? "").trim();
    if (v === "") return [k, null];
    if (TEXT.has(k)) return [k, v];
    if (/^(true|false)$/i.test(v)) return [k, /^true$/i.test(v)];
    return [k, isFinite(v) ? +v : v];
  })));
}
function download(name, text, mime = "text/csv") {
  let ok = false;
  if (!inFrame) {
    try { const b = new Blob([text], { type: mime }), a = document.createElement("a"); a.href = URL.createObjectURL(b); a.download = name; document.body.appendChild(a); a.click(); a.remove(); ok = true; } catch (e) { ok = false; }
  }
  const copy = () => navigator.clipboard?.writeText(text);
  if (ok) toast(`Saved ${name}`, "ok");
  else Promise.resolve().then(copy).then(() => toast(`${name} copied to the clipboard. Paste it into Excel.`, "ok"), () => toast("Downloads are blocked in this viewer. Open the offline file to export.", "warn"));
}

/* ---------- command palette ---------- */
function paletteItems(q) {
  q = q.toLowerCase().trim();
  const items = [
    ...VIEWS.map(v => ({ kind: "Screen", label: v.label, sub: v.group, act: `view|${v.id}` })),
    ...DB.companies.filter(c => c.in_universe || IX.fin[c.code]).map(c => ({ kind: "Company", label: c.name, sub: `${c.sector} · ${c.code}`, act: `company|${c.code}` })),
    ...(BRIDGE.live ? [{ kind: "Action", label: "Add a listed company…", sub: "Search NSE", act: "add|1" }] : []),
    ...DB.schemes.map(s => ({ kind: "Fund", label: s.name, sub: `${s.category} · ${s.amc}`, act: `fund|${s.scheme_id}` })),
    ...[{ member_id: "ALL", name: "Whole family", type: "All entities" }, ...DB.members].map(m => ({ kind: "Entity", label: m.name, sub: m.type, act: `member|${m.member_id}` })),
  ];
  if (!q) return items.filter(i => i.kind === "Screen");
  return items.filter(i => (i.label + " " + i.sub).toLowerCase().includes(q)).slice(0, 12);
}
function openPalette() {
  const m = $("#palette"); m.hidden = false; const inp = $("#pal-q"); inp.value = ""; renderPalette(); inp.focus();
}
function closePalette() { $("#palette").hidden = true; }
function renderPalette() {
  const it = paletteItems($("#pal-q").value); state.palIdx = Math.min(state.palIdx || 0, Math.max(0, it.length - 1));
  $("#pal-list").innerHTML = it.map((x, i) => `<li role="option" aria-selected="${i === state.palIdx}" data-pal="${esc(x.act)}"><span class="pk">${esc(x.kind)}</span><span class="pl">${esc(x.label)}</span><span class="ps">${esc(x.sub)}</span></li>`).join("") || `<li class="empty">No matches</li>`;
}
function runPalette(act) {
  const [k, v] = act.split("|"); closePalette();
  if (k === "view") go(v);
  if (k === "company") { state.company = v; go("company"); }
  if (k === "fund") { state.fund = v; go("funds"); }
  if (k === "member") { state.member = v; render(); }
  if (k === "add") openAdd();
}
