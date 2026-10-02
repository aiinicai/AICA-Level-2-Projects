/* ==================================================================
   Equity research: screener, company analyser, AI data extraction
   ================================================================== */
const METRICS = [
  ["score", "Fundamental score %", 0], ["roe", "ROE %", 1], ["roce", "ROCE %", 1], ["de", "Debt / equity ×", 2], ["pe", "P/E", 1], ["pb", "P/B", 2],
  ["ev_ebitda", "EV / EBITDA", 1], ["div_yield", "Dividend yield %", 2], ["rev_cagr3", "Revenue CAGR 3Y %", 1], ["pat_cagr3", "PAT CAGR 3Y %", 1],
  ["r1y", "1Y price return %", 1], ["cagr3", "3Y price CAGR %", 1], ["beta", "Beta", 2], ["offHigh", "% from 52-week high", 1], ["fscore", "F-score (0–9)", 0],
  ["holders", "Schemes holding", 0], ["mfNet", "Funds adding − reducing", 0], ["expPct", "Family exposure % of equity", 2], ["pledge", "Promoter pledge %", 2], ["mcap", "Market cap ₹ Cr", 0],
];
const PRESETS = {
  quality: { label: "Quality screen", f: [["roe", ">=", 18], ["rev_cagr3", ">=", 10], ["de", "<=", 0.6], ["fscore", ">=", 5]] },
  growth: { label: "High growth", f: [["rev_cagr3", ">=", 14], ["pat_cagr3", ">=", 14]] },
  value: { label: "Value & income", f: [["pe", "<=", 22], ["div_yield", ">=", 1.0], ["roe", ">=", 12]] },
  consensus: { label: "Funds buying", f: [["mfNet", ">=", 2]] },
  fresh: { label: "Passes screen, not held", f: [["score", ">=", 80], ["expPct", "<=", 0.5]] },
  flags: { label: "Fails most tests", f: [["score", "<", 60]] },
  all: { label: "All companies", f: [] },
};
function applyFilters(rows, fl) {
  const ops = { ">=": (a, b) => a >= b, "<=": (a, b) => a <= b, ">": (a, b) => a > b, "<": (a, b) => a < b, "=": (a, b) => Math.abs(a - b) < 1e-9 };
  return rows.filter(r => fl.every(([k, op, v]) => isNum(r[k]) && isNum(v) && ops[op](+r[k], +v)));
}
function vScreener() {
  const M = state.member; if (!state.filters.length && PRESETS[state.screen] && state.screen !== "all") state.filters = PRESETS[state.screen].f.map(x => [...x]);  // no filters after deleting them all = show every company
  const rows = screenerRows(M), res = applyFilters(rows, state.filters).filter(r => !state.sel.scrSector || r.sector === state.sel.scrSector);
  const sectors = [...new Set(DB.companies.map(c => c.sector))].sort();
  const frows = state.filters.map(([k, op, v], i) => `<div class="filter-row"><select data-f="${i}|k" aria-label="Metric">${METRICS.map(([m, l]) => `<option value="${m}" ${m === k ? "selected" : ""}>${esc(l)}</option>`).join("")}</select><select data-f="${i}|op" aria-label="Operator">${[[">=", "≥"], ["<=", "≤"], [">", ">"], ["<", "<"], ["=", "="]].map(([o, t]) => `<option value="${o}" ${o === op ? "selected" : ""}>${t}</option>`).join("")}</select><input type="number" step="any" data-f="${i}|v" value="${esc(v)}" aria-label="Value"><button class="btn icon ghost" data-fdel="${i}" aria-label="Remove filter">✕</button></div>`).join("");
  return pageHead("Stock screener", `${rows.length} companies with financial statements, screened on fundamentals, valuation, price behaviour, fund-manager activity and the family's existing exposure. Fetch any other listed company to add it.`, `<button class="btn" data-open-add="1">+ Add a listed company</button>`) +
  `<div class="chips" role="group" aria-label="Preset screens">${Object.entries(PRESETS).map(([k, p]) => `<button class="chip" data-preset="${k}" aria-pressed="${k === state.screen}">${esc(p.label)}</button>`).join("")}</div>` + `
  <div class="grid" style="grid-template-columns:minmax(400px,1fr) minmax(0,2.3fr)">
    ${card("Filters", `${frows || '<p class="muted small" style="margin:0">No filters. All companies are shown.</p>'}<div class="row"><button class="btn sm" id="addFilter">+ Add filter</button><label class="fld" for="scrSector" style="margin-left:auto">Sector<select id="scrSector"><option value="">All sectors</option>${sectors.map(s => `<option ${s === state.sel.scrSector ? "selected" : ""}>${esc(s)}</option>`).join("")}</select></label></div><p class="note">All conditions must hold. A company without the metric (for example debt/equity for a bank) is excluded by that condition.</p>`, { sub: `${res.length} of ${rows.length} companies match` })}
    ${card("Results", table("screener", [
      { k: "name", label: "Company", fmt: (v, r) => `<span class="nm">${esc(v)}</span><span class="sub">${esc(r.sector)} · ${r.cap}</span>` },
      { k: "score", label: "Score", num: true, fmt: (v, r) => isNum(v) ? pill(r.band === "Strong" ? "ok" : r.band === "Adequate" ? "warn" : r.band === "Weak" ? "crit" : "neutral", fmtN(v, 0)) : "—" },
      { k: "roe", label: "ROE", num: true, fmt: v => fmtPct(v) }, { k: "rev_cagr3", label: "Rev 3Y", num: true, fmt: v => fmtPct(v) },
      { k: "pe", label: "P/E", num: true, fmt: v => fmtN(v, 1) }, { k: "de", label: "D/E", num: true, fmt: v => fmtN(v, 2) },
      { k: "r1y", label: "1Y", num: true, fmt: v => `<span class="${clsNum(v)}">${fmtPct(v)}</span>` }, { k: "mcap", label: "Mkt cap (₹ Cr)", num: true, fmt: v => isNum(v) ? nf(v, 0) : "—" }, { k: "mfNet", label: "MF net", num: true, fmt: v => `<span class="${clsNum(v)}">${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v)}</span>`, tip: "Schemes adding minus schemes reducing last month." },
      { k: "expPct", label: "Family %", num: true, fmt: v => v ? fmtPct(v, 2) : "—" },
      { k: "decision", label: "Screen result", fmt: (v, r) => pill(r.decisionS, v) },
    ], res, { sort: { k: "score", d: "desc" }, noun: "companies", maxH: 620, rowAttr: r => `data-company="${r.code}" data-row="1"`, search: r => r.name + " " + r.sector, placeholder: "Search results" }))}
  </div>`;
}

/** One cell of the company figure strip: label, value and a sub-line on fixed rows, so the strip lines up. */
function coStat(label, value, sub = "", o = {}) {
  return `<div class="co-stat ${o.cls || ""}" ${o.tip ? tipAttr(o.tip) : ""}><span class="co-l">${label}</span><b class="co-v ${o.vcls || ""}">${value}</b><span class="co-s">${sub}</span></div>`;
}
function vCompany() {
  const M = state.member;
  const withFin = DB.companies.filter(c => IX.fin[c.code]?.length >= 2);
  if (!IX.co[state.company]) state.company = (withFin[0] || DB.companies[0] || {}).code;
  const code = state.company, c = IX.co[code];
  if (!c) return pageHead("Company analyser", "") + card("", `<p class="muted" style="margin:0">No companies loaded yet.</p>`);
  const sc = scorecard(code, M), r = ratios(code) || {}, ss = stockStats(code), g = IX.fin[code] || [];
  const tab = state.tab.company || "overview";
  const opts = [...DB.companies].filter(x => x.in_universe || IX.fin[x.code] || x.code === code).sort((a, b) => a.name.localeCompare(b.name)).map(x => `<option value="${x.code}" ${x.code === code ? "selected" : ""}>${esc(x.name)}</option>`).join("");
  const addBtn = `<button class="btn" data-open-add="1">+ Add a listed company</button>`;
  const lt = lookThrough(M), row = lt.rows.find(x => x.code === code);
  let body = "";
  if (!sc && tab !== "price") {
    const held = !row ? "is in the research universe" : row.direct > 0 && row.viaMF > 0 ? "is held directly and through funds" : row.direct > 0 ? "is held directly" : "is held through funds";
    body = c.fin_excluded
      // statements were fetched but are not in rupees: fetching again cannot help; the INR figures come from its results
      ? card("Financial ratios not available", `<p style="margin:0">${esc(c.name)} ${held}. Its statements on Yahoo Finance are reported in ${esc(c.fin_excluded)}, not rupees, so its ratios are left out rather than mis-stated. To analyse it, enter the rupee figures from its annual results in AI data extraction. <button class="btn primary sm" data-go="extract">Open AI data extraction</button></p>`)
      : card("Financial data not loaded", `<p style="margin:0">${esc(c.name)} ${held}, but its financial statements have not been fetched. ${BRIDGE.live ? `<button class="btn primary sm" data-fetch-co="${esc(c.code)}">Fetch financials for ${esc(c.code)}</button>` : "Start the data bridge to fetch them."}</p>`);
  } else if (tab === "overview") {
    const amt = state.whatIf, w = whatIfBuy(code, amt, M), P = DB.policy;
    const groups = [...new Set(sc.tests.map(t => t.grp))];
    body = `<div class="grid g3">
      <div class="stack">${card("Screening result · for committee review, not a recommendation", `<div class="decision ${sc.decision.s}"><span class="t">${esc(sc.decision.t)}</span><p>${esc(sc.decision.d)}</p></div>${sc.signals.map(s => `<div class="sig"><span>${esc(s.k)}<span class="sub">${esc(s.v)}</span></span>${pill(s.s, s.s === "ok" ? "Positive" : s.s === "warn" ? "Caution" : s.s === "crit" ? "Negative" : "Neutral")}</div>`).join("")}<p class="note">Screening aid for the adviser, based on the rules in Methodology. It is not investment advice.</p>`, { sub: `Portfolio: ${esc(memberName(M))} · financials to ${esc(r.fy || "")}` })}</div>
      ${card(`Fundamental scorecard <span class="muted" style="font-weight:400">${sc.passed}/${sc.tests.length}</span>`, groups.map(gp => `<div><div class="small muted" style="font-weight:600;margin:4px 0">${esc(gp)}</div>${sc.tests.filter(t => t.grp === gp).map(t => `<div class="sig"><span>${esc(t.k)}<span class="sub">${esc(t.v)}</span></span>${pill(t.pass ? "ok" : "crit", t.pass ? "Pass" : "Fail")}</div>`).join("")}</div>`).join("") + `<p class="muted small" style="margin:0">Tests without source data are skipped, not failed.${c.is_financial ? " Asset-quality tests need NPA and capital data, which Yahoo does not provide." : ""}</p>`, { sub: `${sc.band} · ${fmtN(sc.score, 0)}% of available tests passed` })}
      ${card("What if the family buys?", lt.eq ? `<div class="row"><label class="fld" for="wiAmt">Amount (₹)<input type="number" id="wiAmt" value="${amt}" step="100000" min="0" style="width:150px"></label>${seg("wiPreset", [[1000000, "₹10 L"], [2500000, "₹25 L"], [5000000, "₹50 L"], [10000000, "₹1 Cr"]], amt, { label: "Preset amounts" })}</div>
        ${[["This stock", w.before.pct, w.after.pct, P.max_single_stock_pct, v => fmtPct(v, 2)], [c.sector, w.before.sector, w.after.sector, P.max_sector_pct, v => fmtPct(v, 2)], ["Top 10 share", w.before.top10, w.after.top10, P.max_top10_pct, v => fmtPct(v, 1)], ["HHI", w.before.hhi, w.after.hhi, P.max_hhi, v => fmtHHI(v)]].map(([m, b0, a0, l, f]) => `<div class="wi"><span>${esc(m)}<span class="sub">Limit ${f(l)}</span></span>${a0 <= l ? pill("ok", "Within") : b0 > l && a0 < b0 ? pill("warn", "Above, improves") : pill("crit", b0 > l ? "Breach worsens" : "Breach")}<span class="ch muted small" style="grid-column:1/-1">${f(b0)} now → <b style="color:var(--ink)">${f(a0)}</b> after</span></div>`).join("")}
        <p class="muted small" style="margin:0">Headroom before the single-stock limit: <b>${isNum(sc.headroom) ? (sc.headroom > 0 ? fmtAmt(sc.headroom) : "none") : "—"}</b>. Assumes the purchase is added to direct holdings.</p>` : `<p class="muted">No family holdings yet.</p>`)}
    </div>`;
  } else if (tab === "fin") {
    const fin = c.is_financial, yrs = g.map(y => y.fy.replace("FY20", "FY"));
    const lines = fin ? [["revenue", "Total revenue"], ["interest", "Interest expense"], ["pbt", "Profit before tax"], ["tax", "Tax"], ["pat", "Profit after tax"], ["eps", "EPS (₹)"], ["total_assets", "Total assets"], ["net_worth", "Net worth"], ["total_debt", "Borrowings"], ["dividend_ps", "Dividend per share (₹)"]]
      : [["revenue", "Revenue"], ["ebitda", "EBITDA"], ["depreciation", "Depreciation"], ["interest", "Finance costs"], ["pbt", "Profit before tax"], ["tax", "Tax"], ["pat", "Profit after tax"], ["eps", "EPS (₹)"], ["total_assets", "Total assets"], ["net_worth", "Net worth"], ["total_debt", "Borrowings"], ["cash_eq", "Cash & equivalents"], ["cfo", "Cash from operations"], ["capex", "Capital expenditure"], ["fcf", "Free cash flow"], ["dividend_ps", "Dividend per share (₹)"]];
    const val = (y, k) => k === "eps" ? ratio(y.pat, y.shares_cr || c.shares_cr) : k === "fcf" ? (isNum(y.cfo) && isNum(y.capex) ? y.cfo - y.capex : null) : y[k];
    const bold = new Set(["revenue", "pat", "net_worth", "cfo", "ebitda"]);
    const off = c.fin_official, offK = new Set((off && off.fields) || []), dag = k => offK.has(k) || (k === "eps" && offK.has("pat")) ? "<sup>†</sup>" : "";
    const offLinks = off ? [...new Map(g.filter(y => y.official_source).map(y => [y.official_source, y.fy])).entries()]
      .map(([u, fy]) => `<a href="${esc(u)}" target="_blank" rel="noopener noreferrer">${esc(g.filter(y => y.official_source === u).map(y => y.fy.replace("FY20", "FY")).join(", "))} filing</a>`).join(" · ") : "";
    const offNote = off ? `<p class="small" style="margin:0 0 6px"><b>† Audited figures.</b> ${esc([["pbt", "profit before tax"], ["tax", "tax"], ["pat", "profit after tax"], ["net_worth", "net worth"], ["total_assets", "total assets"], ["total_debt", "borrowings"]].filter(([k]) => offK.has(k)).map(([, n]) => n).join(", ").replace(/, ([^,]+)$/, " and $1").replace(/^./, x => x.toUpperCase()))} are ${esc(c.name)}'s own audited figures (${esc(off.basis || "")}) from its filing (${offLinks}), not Yahoo Finance. ${esc(off.reason || "")}</p>` : "";
    body = card("Financial statements", `<div class="tbl-wrap"><table class="tbl"><thead><tr><th><span class="th">₹ crore</span></th>${yrs.map(y => `<th class="num"><span class="th" style="justify-content:flex-end">${y}</span></th>`).join("")}</tr></thead><tbody>${lines.map(([k, l]) => `<tr><td class="${bold.has(k) ? "nm" : ""}">${l}${dag(k)}</td>${g.map(y => { const v = val(y, k); return `<td class="num ${bold.has(k) ? "nm" : ""}">${isNum(v) ? fmtN(v, /_ps|eps/.test(k) ? 2 : 0) : "—"}</td>`; }).join("")}</tr>`).join("")}</tbody></table></div>${offNote}<p class="muted small" style="margin:0">${off ? "Other lines: annual" : "Consolidated annual"} figures as reported to Yahoo Finance, converted to ₹ crore. Fiscal years end on the dates shown by the company (usually 31 March). Verify material figures against the annual report.</p>`, { sub: `Source: ${esc(c.source || "Yahoo Finance")}${off ? " · † lines from the company's audited filing" : ""}` }) + `
    <div class="grid g2">${card("Revenue and profit", colChart({ labels: yrs, series: [{ name: fin ? "Total revenue" : "Revenue", values: g.map(y => y.revenue), color: "var(--s1)" }, { name: "PAT", values: g.map(y => y.pat), color: "var(--s2)" }], fmt: v => nf(v, 0) }), { sub: "₹ crore" })}
    ${card(fin ? "Profitability" : "Margins", lineChart({ series: fin ? [{ name: "PAT margin", values: g.map(y => ratio(y.pat, y.revenue) != null ? y.pat / y.revenue * 100 : null), color: "var(--s1)" }] : [{ name: "EBITDA margin", values: g.map(y => ratio(y.ebitda, y.revenue) != null ? y.ebitda / y.revenue * 100 : null), color: "var(--s1)" }, { name: "PAT margin", values: g.map(y => ratio(y.pat, y.revenue) != null ? y.pat / y.revenue * 100 : null), color: "var(--s2)" }], labels: yrs, yFmt: v => fmtN(v, 0) + "%", zero: true, height: 220 }))}</div>`;
  } else if (tab === "ratios") {
    const fld = (k, v, med) => `<div class="field"><span class="k">${k}</span><b class="num" style="text-align:left">${v}</b>${med != null ? `<span class="src">Sector median ${med}</span>` : ""}</div>`;
    const md = k => { const m = sectorMedian(c.sector, k); return m == null ? null : m; };
    const common = [fld("ROE", fmtPct(r.roe), isNum(md("roe")) ? fmtPct(md("roe")) : null), fld("ROA", fmtPct(r.roa, 2)), fld("P/E", fmtN(r.pe, 1), isNum(sc.medPE) ? fmtN(sc.medPE, 1) : null), fld("P/B", fmtN(r.pb, 2), isNum(sc.medPB) ? fmtN(sc.medPB, 2) : null), fld("Earnings yield", fmtPct(r.earn_yield, 2)), fld("Dividend yield", fmtPct(r.div_yield, 2)), fld("Payout ratio", fmtPct(r.payout)), fld("Revenue CAGR 3Y", fmtPct(r.rev_cagr3)), fld("PAT CAGR 3Y", fmtPct(r.pat_cagr3)), fld("Revenue growth, latest year", fmtSPct(r.rev_growth1)), fld("PAT margin", fmtPct(r.pat_margin))];
    const nonfin = c.is_financial ? [] : [fld("ROCE", fmtPct(r.roce), isNum(md("roce")) ? fmtPct(md("roce")) : null), fld("EBITDA margin", fmtPct(r.ebitda_margin)), fld("Debt / equity", fmtX(r.de)), fld("Interest cover", r.int_cover == null ? "—" : fmtX(r.int_cover, 1)), fld("Current ratio", fmtX(r.current_ratio)), fld("EV / EBITDA", fmtN(r.ev_ebitda, 1)), fld("Free cash flow", isNum(r.fcf) ? "₹" + nf(r.fcf, 0) + " Cr" : "—"), fld("FCF yield", fmtPct(r.fcf_yield, 2)), fld("CFO / PAT", fmtX(r.cfo_pat))];
    body = card("Key ratios", `<div class="fieldgrid">${[...common, ...nonfin].join("")}</div>`, { sub: `${esc(r.fy || "")} · averages use opening and closing balances · sector medians need at least three peers${c.fin_official ? " · profit, net worth and total assets from the company's audited filing (see Financials)" : ""}` }) +
      (c.is_financial || !r.fscoreTests ? "" : `<div class="grid g2">${card("DuPont analysis", `<div class="formula">ROE = net margin × asset turnover × equity multiplier\n${fmtPct(r.roe)} = ${fmtPct(r.dupont_margin)} × ${fmtN(r.dupont_turnover, 2)} × ${fmtN(r.dupont_leverage, 2)}</div><div class="grid g3">${kpi("Net margin", fmtPct(r.dupont_margin), "Profitability", { cls: "flat" })}${kpi("Asset turnover", fmtX(r.dupont_turnover), "Efficiency", { cls: "flat" })}${kpi("Equity multiplier", fmtX(r.dupont_leverage), "Leverage", { cls: "flat" })}</div>`, { sub: "Where the return on equity comes from." })}
      ${card(`Piotroski F-score <span class="muted" style="font-weight:400">${isNum(r.fscore) ? r.fscore + "/9" : "incomplete data"}</span>`, r.fscoreTests.map(([k, p]) => `<div class="sig"><span>${esc(k)}</span>${p === null ? pill("neutral", "No data") : pill(p ? "ok" : "crit", p ? "1" : "0")}</div>`).join(""), { sub: "Nine yes/no tests of financial strength, latest year vs prior year. Scored when at least 7 tests have data." })}</div>`);
  } else if (tab === "price") {
    const px = IX.px[code], bx = IX.mkt, labels = DB.meta.dates.map(fmtMon);
    const holders = DB.schemes.map(s => { const L = portOf(s.scheme_id, 0), Pv = portOf(s.scheme_id, 1); const now = L ? (L.rows.find(p => p.code === code)?.w || 0) : 0, prev = Pv ? (Pv.rows.find(p => p.code === code)?.w || 0) : null; return { name: s.name, id: s.scheme_id, now, prev, dw: isNum(prev) ? now - prev : null, held: heldSchemes(M).includes(s.scheme_id) }; }).filter(x => x.now || x.prev);
    const i0 = px ? px.findIndex(isNum) : -1;
    body = `<div class="grid g21">${card("Price vs market", px && bx ? lineChart({ series: [{ name: shortName(c.name), values: px.map(v => isNum(v) ? v / px[i0] * 100 : null), color: "var(--s1)" }, { name: mktName(), values: bx.map(v => isNum(v) && isNum(bx[i0]) ? v / bx[i0] * 100 : null), color: "var(--bench)", dash: true }], labels, yFmt: v => fmtN(v, 0), W: CW.two }) : `<p class="muted">No price history.</p>`, { sub: `Rebased to 100; month-end closes. Source: ${esc(c.source || "")}` })}
      ${card("Price statistics", ss ? `<dl class="dl"><dt>Price (${fmtDate(DB.meta.as_on)})</dt><dd>₹${fmtN(c.price)}</dd><dt>3-month return</dt><dd class="${clsNum(ss.r3m)}">${fmtSPct(isNum(ss.r3m) ? ss.r3m * 100 : null)}</dd><dt>1-year return</dt><dd class="${clsNum(ss.r1y)}">${fmtSPct(isNum(ss.r1y) ? ss.r1y * 100 : null)}</dd><dt>3-year CAGR</dt><dd>${fmtPct(isNum(ss.cagr3) ? ss.cagr3 * 100 : null)}</dd><dt>Volatility</dt><dd>${fmtPct(isNum(ss.vol) ? ss.vol * 100 : null)}</dd><dt>Beta vs ${esc(mktName())}</dt><dd>${fmtN(ss.beta, 2)}</dd><dt>From 12-month high</dt><dd class="neg">${fmtPct(ss.offHigh * 100)}</dd></dl>${rangeBar(ss.lo52, ss.hi52, c.price)}` : `<p class="muted">No price history.</p>`)}</div>
      <div class="grid g2">${card(`Mutual fund ownership <span class="muted" style="font-weight:400">${holders.filter(h => h.now).length} tracked schemes</span>`, holders.length ? table("mfown", [
        { k: "name", label: "Scheme", fmt: (v, r) => `<span class="nm">${esc(shortName(v))}</span>${r.held ? tag("held") : ""}` },
        { k: "now", label: "% of NAV", num: true, fmt: v => v ? fmtPct(v, 2) : "—" }, { k: "dw", label: "Change", num: true, fmt: v => isNum(v) ? `<span class="${clsNum(v)}">${fmtSPct(v, 2)}</span>` : "—" },
      ], holders, { sort: { k: "now", d: "desc" }, dense: true, maxH: 360, export: false }) : `<p class="muted" style="margin:0">None of the tracked schemes holds this stock (based on the portfolio files applied).</p>`)}
      ${card("Ownership & family exposure", `<dl class="dl"><dt>Held by insiders / promoters</dt><dd>${fmtPct(c.promoter_pct)}</dd><dt>Held by institutions</dt><dd>${fmtPct(c.institutions_pct)}</dd><dt>Promoter shares pledged</dt><dd>${isNum(c.pledge_pct) ? fmtPct(c.pledge_pct) : "Not in source"}</dd><dt>Market cap</dt><dd>${isNum(c.mcap_cr) ? "₹" + nf(c.mcap_cr, 0) + " Cr" : "—"}</dd><dt>ISIN</dt><dd class="mono">${esc(c.isin || "—")}</dd></dl>
        <p class="muted small" style="margin:0">Holding percentages are Yahoo Finance's insider and institutional figures, which approximate the exchange shareholding pattern. Use the latest NSE/BSE filing for advice.</p>
        <h3 class="small muted" style="margin:6px 0 0">Family exposure by entity</h3>${row ? Object.entries(row.members).sort((a, b) => b[1] - a[1]).map(([m, v]) => `<div class="sig"><span>${esc(IX.mem[m].name)}</span><b class="num">${fmtAmt(v)}</b></div>`).join("") + `<div class="sig"><b>Total</b><b class="num">${fmtAmt(row.total)} · ${fmtPct(row.pct, 2)}</b></div>` : '<p class="muted small">Not held by the family.</p>'}`)}</div>`;
  } else {
    const peers = screenerRows(M).filter(x => x.sector === c.sector);
    body = card(`${esc(c.sector)} peers`, table("peers", [
      { k: "name", label: "Company", fmt: (v, r) => `<span class="nm">${esc(v)}</span><span class="sub">${r.cap} cap</span>` }, { k: "mcap", label: "Mkt cap (₹ Cr)", num: true, fmt: v => isNum(v) ? nf(v, 0) : "—" },
      { k: "roe", label: "ROE", num: true, fmt: v => fmtPct(v) }, { k: "roce", label: "ROCE", num: true, fmt: v => fmtPct(v) }, { k: "rev_cagr3", label: "Rev 3Y", num: true, fmt: v => fmtPct(v) },
      { k: "pe", label: "P/E", num: true, fmt: v => fmtN(v, 1) }, { k: "pb", label: "P/B", num: true, fmt: v => fmtN(v, 2) }, { k: "r1y", label: "1Y", num: true, fmt: v => `<span class="${clsNum(v)}">${fmtPct(v)}</span>` },
      { k: "score", label: "Score", num: true, fmt: (v, r) => isNum(v) ? pill(r.band === "Strong" ? "ok" : r.band === "Adequate" ? "warn" : r.band === "Weak" ? "crit" : "neutral", fmtN(v, 0)) : "—" }, { k: "expPct", label: "Family %", num: true, fmt: v => v ? fmtPct(v, 2) : "—" },
    ], peers, { sort: { k: "mcap", d: "desc" }, rowAttr: x => `data-company="${x.code}" data-row="1" ${x.code === code ? 'style="background:var(--accent-soft)"' : ""}` }), { sub: "Companies in the research universe with the same sector" + (c.is_financial ? ". ROCE is not meaningful for banks, lenders and insurers (borrowing is their raw material), so it is left blank." : "") });
  }
  return `<div class="co-head"><div><div class="crumb" style="margin:0 0 4px">${esc(c.sector)} · ${esc(c.industry || "")} · ${esc(c.cap)} cap · <span class="mono">${esc(c.isin || "")}</span> · NSE ${esc(c.code)}</div><h1>${esc(c.name)}</h1></div><div class="acts">${addBtn}<select id="coSel" aria-label="Select company">${opts}</select></div></div>
  <div class="co-meta">${[
      coStat(`Price · ${fmtDate(DB.meta.as_on)}`, isNum(c.price) ? "₹" + fmtN(c.price) : "—", "Valuation date"),
      ...(BRIDGE.live ? [(() => {
        if (BRIDGE.quotesUnsupported) return coStat("Latest", "Restart the app", "The running bridge is an earlier build", { vcls: "muted sm", tip: "Close the LookThrough Data Bridge window and run Start_LookThrough.bat again." });
        const q = latestQuote("EQ", c.code, "");
        if (!q) { if (isNum(c.price) && !BRIDGE.quotesAsked?.has(c.code) && !BRIDGE.quotesBusy) setTimeout(() => loadQuotes([c.code]), 0); return coStat("Latest", "…", "Fetching"); }
        return coStat(`Latest · ${fmtDate(q.date)}`, "₹" + fmtN(q.price), `<span class="${clsNum(q.price - c.price)}">${fmtSPct((q.price / c.price - 1) * 100)}</span> since ${fmtDate(DB.meta.as_on).slice(0, 6)}`, { tip: QUOTE_NOTE });
      })()] : []),
      coStat("1-year return", ss && isNum(ss.r1y) ? fmtSPct(ss.r1y * 100) : "—", `Price, to ${fmtDate(DB.meta.as_on).slice(0, 6)}`, { vcls: clsNum(ss?.r1y) }),
      coStat("Market cap", isNum(c.mcap_cr) ? "₹" + nf(c.mcap_cr, 0) + " Cr" : "—", c.cap && c.cap !== "Unclassified" ? `${esc(c.cap)} cap` : ""),
      coStat("P/E · P/B", `${fmtN(r.pe, 1)} · ${fmtN(r.pb, 2)}`, "Trailing"),
      coStat("Family exposure", row ? fmtAmt(row.total) : "Not held", row ? `${fmtPct(row.pct, 2)} of equity` : ""),
      ...(ss ? [coStat("12-month range", rangeBar(ss.lo52, ss.hi52, c.price), "", { cls: "co-range" })] : []),
      coStat("Screen result", sc ? pill(sc.decision.s, sc.decision.t) : pill("neutral", "No financials"), "For review, not advice"),
    ].join("")}</div>` +
    tabs("company", [["overview", "Overview"], ["fin", "Financials"], ["ratios", "Ratios"], ["price", "Price & ownership"], ["peers", "Peers"]], tab) + body;
}

/* ---------------- extraction ---------------- */
const FIELDS = [
  { key: "revenue", label: "Revenue from operations", pats: [/revenue from operations/i, /net sales/i, /income from operations/i, /total income from operations/i] },
  { key: "ebitda", label: "EBITDA", pats: [/\bebitda\b/i, /operating profit before depreciation/i] },
  { key: "pat", label: "Profit after tax", pats: [/profit after tax/i, /net profit for the (?:year|period)/i, /profit for the (?:year|period)/i] },
  { key: "net_worth", label: "Net worth (total equity)", pats: [/total equity(?! and)/i, /net worth/i, /shareholders'? funds/i] },
  { key: "total_debt", label: "Total borrowings", pats: [/total borrowings/i, /total debt/i, /^\s*borrowings\b/i] },
  { key: "cfo", label: "Cash from operating activities", pats: [/net cash (?:generated )?(?:from|used in) operating activities/i, /cash flow from operations/i] },
];
function detectUnit(text) {
  const t = text.toLowerCase();
  if (/(₹|rs\.?|inr)\s*(in\s*)?(crores?|cr\b)|in\s*crores?|crore/.test(t)) return { unit: "crore", f: 1 };
  if (/lakhs?|\blacs?\b/.test(t)) return { unit: "lakh", f: 0.01 };
  if (/millions?|\bmn\b/.test(t)) return { unit: "million", f: 0.1 };
  if (/billions?|\bbn\b/.test(t)) return { unit: "billion", f: 100 };
  return { unit: "crore (assumed)", f: 1, assumed: true };
}
function parseNum(s) { const neg = /^\(.*\)$/.test(s) || s.startsWith("-") || s.startsWith("−"); const v = parseFloat(s.replace(/[()\s,−-]/g, "")); return neg ? -v : v; }
function extract(text) {
  const u = detectUnit(text), lines = text.split(/\r?\n/), out = {};
  FIELDS.forEach(F => {
    let hit = null;
    for (const re of F.pats) {
      for (const ln of lines) {
        const m = ln.match(re); if (!m) continue;
        if (F.key === "total_debt" && /(cost|finance|current|non-current)/i.test(ln) && !/total/i.test(ln)) continue;
        const after = ln.slice(m.index + m[0].length).replace(/\((?:note|refer)[^)]*\)/ig, "").replace(/\bnote\s*\d+\b/ig, "");
        const nm = after.match(/\(?[−-]?\d[\d,]*\.?\d*\)?/);
        if (!nm) continue;
        hit = { value: +(parseNum(nm[0]) * u.f).toFixed(2), raw: nm[0], line: ln.trim(), conf: u.assumed ? "Medium" : re === F.pats[0] ? "High" : "Medium" };
        break;
      }
      if (hit) break;
    }
    out[F.key] = hit || { value: null, raw: null, line: null, conf: "Not found" };
  });
  return { unit: u, fields: out };
}
function sanityChecks(f) {
  const v = k => f[k]?.value, out = [];
  if (v("revenue") != null && v("pat") != null) out.push({ t: "PAT below revenue", pass: v("pat") < v("revenue") });
  if (v("ebitda") != null && v("pat") != null) out.push({ t: "EBITDA at or above PAT", pass: v("ebitda") >= v("pat") });
  if (v("net_worth") != null) out.push({ t: "Net worth positive", pass: v("net_worth") > 0 });
  if (v("cfo") != null && v("pat") != null) out.push({ t: "CFO within 0.3×–3× of PAT", pass: v("cfo") / v("pat") > 0.3 && v("cfo") / v("pat") < 3 });
  if (v("total_debt") != null && v("net_worth") != null) out.push({ t: "Debt/equity below 5×", pass: v("total_debt") / v("net_worth") < 5 });
  return out;
}
function sampleCode() { return (state.exCo && IX.fin[state.exCo]?.length >= 2) ? state.exCo : (IX.fin.INFY ? "INFY" : Object.keys(IX.fin).find(k => IX.fin[k].length >= 2 && !IX.co[k]?.is_financial)); }
function sampleText() {
  const code = sampleCode(), c = IX.co[code], g = IX.fin[code], f = g[g.length - 1], p = g[g.length - 2], n = v => nf(isNum(v) ? v : 0, 2);
  return `${c.name.toUpperCase()}  (test extract built from the figures already in the database)
Statement of Consolidated Financial Results for ${f.fy}
(₹ in crore, except per share data)

Particulars                                         ${f.fy.padEnd(16)} ${p.fy}
Revenue from operations (Note 3)               ${n(f.revenue).padStart(15)}  ${n(p.revenue).padStart(15)}
Other income                                          1,842.10         1,512.60
Total income                                   ${n(f.revenue + 1842.1).padStart(15)}  ${n(p.revenue + 1512.6).padStart(15)}
EBITDA                                         ${n(f.ebitda).padStart(15)}  ${n(p.ebitda).padStart(15)}
Finance costs                                  ${n(f.interest).padStart(15)}  ${n(p.interest).padStart(15)}
Profit after tax                               ${n(f.pat).padStart(15)}  ${n(p.pat).padStart(15)}

Statement of Assets and Liabilities (extract)
Non-current borrowings                         ${n(f.total_debt * 0.6).padStart(15)}  ${n(p.total_debt * 0.6).padStart(15)}
Total borrowings                               ${n(f.total_debt).padStart(15)}  ${n(p.total_debt).padStart(15)}
Total equity                                   ${n(f.net_worth).padStart(15)}  ${n(p.net_worth).padStart(15)}

Cash flow statement (extract)
Net cash generated from operating activities   ${n(f.cfo * 1.04).padStart(15)}  ${n(p.cfo).padStart(15)}`;
}
function llmPrompt(company, fy) {
  return `You are assisting a Chartered Accountant. Extract figures from the financial results pasted below for ${company}, ${fy}.

Rules:
1. Use only numbers that appear in the text. Do not estimate or compute missing values; return null instead.
2. Convert every amount to INR crore. State the unit you found in "source_unit".
3. Use the current-year column only. Ignore note references such as "(Note 3)".
4. "revenue" is revenue from operations, not total income.
5. For each field, quote the exact source line in "<field>_evidence".
6. Return valid JSON only, matching this schema:

{
  "company": "string",
  "fy": "${fy}",
  "source_unit": "crore | lakh | million",
  "revenue": number|null,     "revenue_evidence": "string",
  "ebitda": number|null,      "ebitda_evidence": "string",
  "pat": number|null,         "pat_evidence": "string",
  "net_worth": number|null,   "net_worth_evidence": "string",
  "total_debt": number|null,  "total_debt_evidence": "string",
  "cfo": number|null,         "cfo_evidence": "string"
}

TEXT:
<<paste results / annual report extract here>>`;
}
function vExtract() {
  const opts = [...DB.companies].filter(x => IX.fin[x.code]).sort((a, b) => a.name.localeCompare(b.name)).map(x => `<option value="${x.code}" ${x.code === sampleCode() ? "selected" : ""}>${esc(x.name)}</option>`).join("");
  return pageHead("AI data extraction", "Turn results or annual-report text into structured figures. Every value carries its source line, is checked, and must be approved before it enters the database.") + `
  <div class="grid g2">
    ${card("1 · Source text", `<textarea id="srcText" rows="20" spellcheck="false" wrap="off" aria-label="Source text"></textarea>
      <div class="row"><label class="fld" for="exCo">Company<select id="exCo">${opts}</select></label><label class="fld" for="exFy">Fiscal year<input type="text" id="exFy" value="${esc(state.exFy || (IX.fin[sampleCode()] || []).slice(-1)[0]?.fy || "")}" style="width:120px"></label>
      <button class="btn primary" id="runExtract" style="align-self:flex-end">Extract figures</button><button class="btn" id="loadSample" style="align-self:flex-end">Reload sample</button></div>`, { sub: "Paste an extract from a results announcement or annual report. A test extract is loaded, built from the database figures with a note reference, a total-income line, a non-current borrowings line and a planted +4% variance in operating cash flow." })}
    ${card("2 · Review and approve", `<div id="exOut"></div>`)}
  </div>
  ${card("Optional · Use an LLM for long PDFs", `<div class="grid g2"><div class="stack"><textarea id="llmPrompt" rows="14" readonly aria-label="LLM prompt"></textarea><div class="row"><button class="btn" id="copyPrompt">Copy prompt</button></div></div>
    <div class="stack"><textarea id="llmJson" rows="14" placeholder='{"company":"...","fy":"FY2025-26","revenue":110000, ...}' aria-label="LLM JSON reply"></textarea><div class="row"><button class="btn" id="checkJson">Validate JSON</button><span id="jsonMsg" class="muted small" role="status"></span></div></div></div>`, { sub: "Copy the prompt into ChatGPT, Claude or Gemini with the report text, then paste the JSON reply. It is schema-checked and goes through the same review." })}`;
}
function renderExtractOut() {
  const ex = state.extracted, el = $("#exOut"); if (!ex || !el) return;
  const code = $("#exCo").value, fy = $("#exFy").value.trim(), ref = (IX.fin[code] || []).find(x => x.fy === fy), checks = sanityChecks(ex.fields);
  el.innerHTML = `<div class="row">${pill(ex.unit.assumed ? "warn" : "ok", "Unit: " + ex.unit.unit)}<span class="muted small">${esc(ex.origin || "Rule-based parser")} · values in ₹ crore</span></div>
  <div class="fieldgrid">${FIELDS.map(F => { const x = ex.fields[F.key], dv = ref && isNum(ref[F.key]) && x.value != null ? (x.value - ref[F.key]) / Math.abs(ref[F.key]) * 100 : null;
    return `<div class="field"><label class="k" for="ex_${F.key}">${F.label}</label><input type="number" step="0.01" id="ex_${F.key}" value="${x.value ?? ""}"><span class="row" style="gap:6px">${pill(x.conf === "High" ? "ok" : x.conf === "Medium" ? "warn" : "crit", x.conf)}${dv == null ? "" : pill(Math.abs(dv) <= 0.5 ? "ok" : "warn", Math.abs(dv) <= 0.5 ? "Matches database" : `${fmtSPct(dv)} vs database`)}</span><span class="src" ${tipAttr(esc(x.line || ""))}>${x.line ? "Source: " + esc(x.line) : "No matching line"}</span></div>`; }).join("")}</div>
  <div style="margin-top:14px"><div class="small muted" style="font-weight:600;margin-bottom:6px">Arithmetic checks</div><div class="row">${checks.map(k => pill(k.pass ? "ok" : "crit", k.t)).join("")}</div></div>
  <div class="row" style="margin-top:14px"><button class="btn primary" id="approveEx">Approve and post to ${esc(code)} · ${esc(fy)}</button><span class="muted small">Posting updates ratios and scores, and is written to the audit trail.</span></div>`;
}
