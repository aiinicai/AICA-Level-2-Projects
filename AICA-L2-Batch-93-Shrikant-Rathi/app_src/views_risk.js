/* ==================================================================
   Risk views: concentration & limits, stress testing
   ================================================================== */
function vConcentration() {
  const M = state.member, P = DB.policy, lt = lookThrough(M), con = concentration(lt), al = alerts(M), secs = groupBy(lt, "sector");
  if (!con.top) return pageHead("Concentration &amp; policy limits", "") + card("", `<p class="muted" style="margin:0">No holdings to test yet.</p>`);
  const held = heldSchemes(M); let maxOv = 0; held.forEach((a, i) => held.slice(i + 1).forEach(b => maxOv = Math.max(maxOv, overlap(a, b).overlap)));
  const pledgeData = lt.rows.some(r => isNum(IX.co[r.code]?.pledge_pct));
  const pb = portBeta(lt), wt = weightedTer(M), pledged = lt.rows.filter(r => isNum(IX.co[r.code]?.pledge_pct) && IX.co[r.code].pledge_pct > P.max_pledge_pct);
  const st = (v, l) => v > l ? "crit" : v > l * 0.9 ? "warn" : "ok";
  const tests = [
    ["Largest single stock", IX.co[con.top.code]?.name || con.top.code, con.top.pct, P.max_single_stock_pct, v => fmtPct(v, 2)],
    ["Largest sector", secs[0].key, secs[0].pct, P.max_sector_pct, v => fmtPct(v, 2)],
    ["Top 10 stocks combined", `${con.n} stocks in total`, con.top10, P.max_top10_pct, v => fmtPct(v, 2)],
    ["Herfindahl-Hirschman Index", `Effective N = ${fmtN(con.effN, 1)}`, con.hhi, P.max_hhi, v => fmtHHI(v)],
    ["Highest overlap between held funds", `${held.length} funds held`, maxOv, P.max_pair_overlap_pct, v => fmtPct(v, 1)],
    ...(isNum(wt) ? [["Weighted expense ratio", "Mutual fund holdings", wt, P.max_weighted_ter_pct, v => fmtPct(v, 2)]] : []),
    ["Equity beta", `vs ${mktName()} · ${fmtPct(betaCoverage(lt), 0)} of equity has its own beta`, pb, P.max_portfolio_beta, v => fmtN(v, 2)],
    ["Holdings with pledge above limit", pledgeData ? (pledged.map(r => shortName(IX.co[r.code].name)).join(", ") || "None above the limit") : "No pledge data (not provided by the data source; enter from stock-exchange shareholding disclosures)", pledgeData ? pledged.length : null, 0, v => isNum(v) ? String(v) : "—"],
  ];
  const bw = benchWeights("sector");
  const aw = secs.map(s => ({ label: s.key, v: s.pct - (bw[s.key] || 0), tip: `Family ${fmtPct(s.pct)} · index ${fmtPct(bw[s.key] || 0)}` })).sort((a, b) => b.v - a.v);
  let cum = 0; const curve = lt.rows.map(r => (cum += r.pct));
  const eqCurve = lt.rows.map((_, i) => (i + 1) / lt.rows.length * 100);
  const perM = DB.members.filter(m => lookThrough(m.member_id).rows.length).map(m => { const l = lookThrough(m.member_id), k = concentration(l), a = alerts(m.member_id); return { name: m.name, eq: l.eq, top: shortName(IX.co[k.top.code]?.name || k.top.code), topPct: k.top.pct, top10: k.top10, hhi: k.hhi, effN: k.effN, crit: a.filter(x => x.sev === "crit").length, warn: a.filter(x => x.sev === "warn").length }; });
  return pageHead("Concentration &amp; policy limits", `${esc(memberName(M))} · look-through equity tested against the investment policy. Limits are editable in Data &amp; controls. ${basisLine(M)}`,
    `<button class="btn" data-export-alerts="1">${ICON.download} Export alerts</button>`) + holdingsLagNote(M) +
  card("Policy tests", table("ptests", [
    { k: "m", label: "Measure", fmt: v => `<span class="nm">${esc(v)}</span>` }, { k: "d", label: "Detail", cls: () => "wrap", fmt: v => `<span class="muted">${esc(v)}</span>` },
    { k: "a", label: "Actual", num: true, fmt: (v, r) => r.f(v) }, { k: "l", label: "Limit", num: true, fmt: (v, r) => r.f(v) },
    { k: "s", label: "Status", fmt: (v, r) => pill(v, r.lbl || (v === "crit" ? "Breach" : v === "warn" ? "Near limit" : "Within limit")) },
    { k: "u", label: "Use of limit", fmt: (v, r) => meter(r.a, r.l || 1, r.s), sortV: r => r.a / (r.l || 1) },
  ], tests.map(([m, d, a, l, f]) => { const soft = /overlap|expense|beta|pledge/i.test(m), s0 = m.startsWith("Holdings with pledge") ? (a == null ? "neutral" : a > 0 ? "warn" : "ok") : st(a, l); return { m, d, a, l, f, s: soft && s0 === "crit" ? "warn" : s0, lbl: m.startsWith("Holdings with pledge") ? (a == null ? "No data" : a > 0 ? "Review" : "None") : soft && a > l ? "Above limit" : null }; }), { export: false })) + latestLimitsCard(M) + `
  <div class="grid g2">
    ${card("Sector weights against the limit", barH({ rows: secs.map(s => ({ label: s.key, segs: [{ v: s.pct, color: s.pct > P.max_sector_pct ? "var(--neg)" : "var(--s1)" }] })), fmt: v => fmtPct(v, 1), limit: P.max_sector_pct, limitLabel: `limit ${P.max_sector_pct}%`, labelW: 200 }))}
    ${card(`Active sector weights vs ${esc(benchLabel())}`, `<p class="muted small" style="margin:0">Family weight minus index weight, percentage points. Blue is overweight, red underweight.</p>` + divBar({ rows: aw, fmt: v => fmtSPct(v, 1), labelW: 200 }))}
  </div>
  <div class="grid g2">
    ${card("Concentration curve", lineChart({ series: [{ name: "Family (cumulative weight)", values: curve, color: "var(--s1)" }, { name: "Equal weights", values: eqCurve, color: "var(--bench)", dash: true }], labels: lt.rows.map((_, i) => String(i + 1)), yFmt: v => fmtN(v, 0) + "%", xEvery: Math.max(1, Math.ceil(lt.rows.length / 10)), height: 240, yMin: 0, yMax: 100 }), { sub: "Cumulative share of equity held by the largest n stocks. A curve far above the dashed line means concentration." })}
    ${card(`All alerts <span class="muted" style="font-weight:400">(${al.length})</span>`, `<div class="alerts">${al.map(alertItem).join("") || pill("ok", "All limits met")}</div>`)}
  </div>
  ${card("By entity", table("concm", [
    { k: "name", label: "Entity", fmt: v => `<span class="nm">${esc(v)}</span>` }, { k: "eq", label: "Equity", num: true, fmt: v => fmtAmt(v) },
    { k: "top", label: "Largest stock", fmt: (v, r) => `${esc(v)} <span class="${r.topPct > P.max_single_stock_pct ? "neg" : "muted"}">${fmtPct(r.topPct)}</span>` },
    { k: "top10", label: "Top 10", num: true, fmt: v => fmtPct(v) }, { k: "hhi", label: "HHI", num: true, fmt: v => fmtHHI(v) }, { k: "effN", label: "Effective N", num: true, fmt: v => fmtN(v, 1) },
    { k: "crit", label: "Breaches", num: true, fmt: v => v ? `<b class="neg">${v}</b>` : "0" }, { k: "warn", label: "Warnings", num: true },
  ], perM, { dense: true }), { sub: "Each entity measured on its own holdings. The family view is what the investment policy tests." })}`;
}
/** The concentration limits re-tested at the latest prices, beside the valuation-date result (bridge only). */
function latestLimitsCard(M) {
  if (!BRIDGE.quotes) return "";
  const L = latestValue(M), a = limitTests(lookThrough(M)), b = limitTests(lookThroughLatest(M)), hb = holdingsBasis(M);
  const lbl = s => s === "crit" ? "Breach" : s === "warn" ? "Near limit" : "Within limit";
  const rows = b.map(x => { const y = a.find(z => z.k === x.k) || {}; return { ...x, a: y.v, who: x.who && y.who && y.who !== x.who ? `${x.who} (was ${y.who})` : x.who }; });
  return card("Limits at latest prices", table("ptests-latest", [
    { k: "t", label: "Measure", fmt: (v, r) => `<span class="nm">${esc(v)}</span>${r.who ? `<span class="sub">${esc(r.who)}</span>` : ""}` },
    { k: "a", label: `At ${fmtDate(DB.meta.as_on)}`, num: true, fmt: (v, r) => r.f(v) },
    { k: "v", label: "At latest prices", num: true, fmt: (v, r) => `<b>${r.f(v)}</b>` },
    { k: "lim", label: "Limit", num: true, fmt: (v, r) => r.f(v) },
    { k: "s", label: "Status now", fmt: v => pill(v, lbl(v)) },
  ], rows, { export: false, dense: true }),
  { sub: `Direct shares at their latest price; each fund at its latest NAV, spread over its disclosed holdings${hb.latest ? ` (${fmtDate(hb.oldest)}${hb.oldest === hb.latest ? "" : ` to ${fmtDate(hb.latest)}`})` : ""}. ${latestDates(L)}. Fund-overlap, beta and cost tests do not depend on today's prices.` });
}

const SCENARIOS = {
  m10: { label: "Market −10%", type: "market", market: -0.10, desc: "Broad market falls 10%. Each stock moves by its beta × −10%." },
  m20: { label: "Market −20%", type: "market", market: -0.20, desc: "Broad market falls 20%. Each stock moves by its beta × −20%." },
  m30: { label: "Market −30%", type: "market", market: -0.30, desc: "Severe bear market. Each stock moves by its beta × −30%." },
  fin: { label: "Financials −20%", type: "sector", sector: "Financial Services", shock: -0.20, desc: "Banking and financial stocks fall 20%; others unchanged." },
  top: { label: "Largest stock −30%", type: "stock", shock: -0.30, desc: "The single largest look-through holding falls 30%." },
  hist: { label: "Sep 2024 – Feb 2025 replay", type: "hist", d0: "2024-09-30", d1: "2025-02-28", desc: "Each stock's actual price change between the 30 Sep 2024 and 28 Feb 2025 month-ends (the correction of late 2024), applied to today's holdings." },
  custom: { label: "Custom", type: "custom", desc: "Market move (beta-adjusted) plus an extra sector shock." },
};
function vStress() {
  const M = state.member, key = state.stressSc, base = SCENARIOS[key], lt = lookThrough(M);
  const scen = Object.fromEntries(Object.entries(SCENARIOS).filter(([k, s]) => s.type !== "hist" || (s.d0 in IX.t && s.d1 in IX.t)).map(([k, s]) => [k, s.type === "hist" ? { ...s, t0: IX.t[s.d0], t1: IX.t[s.d1] } : s]));
  if (!lt.rows.length) return pageHead("Stress testing", "") + card("", `<p class=\"muted\" style=\"margin:0\">No look-through equity yet.</p>`);
  const sc = { ...(scen[key] || scen.m20) };
  if (key === "top") sc.code = lt.rows[0].code;
  if (key === "custom") Object.assign(sc, { market: state.custom.market / 100, sector: state.custom.sector, shock: state.custom.shock / 100 });
  const r = stress(M, sc), secImpact = {};
  r.rows.forEach(x => { const s = x.assumption ? "Funds not looked through" : IX.co[x.code]?.sector || "Others"; secImpact[s] = (secImpact[s] || 0) + x.loss; });
  const perM = DB.members.filter(m => lookThrough(m.member_id).rows.length).map(m => { const q = stress(m.member_id, key === "top" ? { ...sc } : sc); return { name: m.name, eq: q.lt.eq, total: q.lt.total, loss: q.loss, pctEq: q.pctEq, pctTot: q.pctTotal }; });
  const all = Object.entries(scen).map(([k, s]) => { const q = stress(M, k === "top" ? { ...s, code: lt.rows[0].code } : k === "custom" ? { ...s, market: state.custom.market / 100, sector: state.custom.sector, shock: state.custom.shock / 100 } : s); return { k, label: s.label, loss: q.loss, pct: q.pctTotal }; });
  const sectors = [...new Set(DB.companies.map(c => c.sector))].sort();
  return pageHead("Stress testing", `${esc(memberName(M))} · what the look-through equity book would lose in each scenario. Stock betas are measured against the ${esc(mktName())} over 36 months; stocks without price history are assumed to move with the market. ${basisLine(M)}`) + holdingsLagNote(M) +
  `<div class="chips" role="group" aria-label="Scenario">${Object.entries(scen).map(([k, s]) => `<button class="chip" data-stress="${k}" aria-pressed="${k === key}">${esc(s.label)}</button>`).join("")}</div>` +
  (key === "custom" ? card("", `<div class="row"><label class="fld" for="cMkt">Market move %<input type="number" id="cMkt" value="${state.custom.market}" step="1" style="width:110px"></label><label class="fld" for="cSec">Sector<select id="cSec">${sectors.map(s => `<option ${s === state.custom.sector ? "selected" : ""}>${esc(s)}</option>`).join("")}</select></label><label class="fld" for="cShock">Extra sector move %<input type="number" id="cShock" value="${state.custom.shock}" step="1" style="width:110px"></label><button class="btn primary" id="runCustom" style="align-self:flex-end">Run scenario</button></div>`) : "") + `
  <div class="kpis k4">
    ${kpi(r.loss > 0 ? "Estimated gain" : "Estimated loss", fmtAmt(r.loss), esc(sc.desc), { vcls: "neg" })}
    ${kpi("Loss as % of equity", fmtPct(r.pctEq), `Equity ${fmtAmt(lt.eq)}`, { vcls: "neg" })}
    ${kpi("Loss as % of portfolio", fmtPct(r.pctTotal), "Debt and cash in funds assumed unchanged", { vcls: "neg" })}
    ${kpi("Portfolio after shock", fmtAmt(lt.total + r.loss), `From ${fmtAmt(lt.total)}`)}
  </div>
  <div class="grid g2">
    ${card("Biggest contributors to the loss", divBar({ rows: r.rows.slice(0, 12).map(x => ({ label: x.assumption ? "Funds not looked through" : shortName(IX.co[x.code]?.name || x.code), v: x.loss / unitDiv(), tip: `Exposure ${fmtAmt(x.exp)} · move ${fmtSPct(x.shock * 100)}${x.assumption ? "<br>Holdings not disclosed: assumed to move with the market (beta 1)" : ""}` })), fmt: v => (v > 0 ? "+" : v < 0 ? "−" : "") + nf(Math.abs(v), state.units === "inr" ? 0 : 2), neg: "var(--neg)" }) + `<p class="muted small" style="margin:0">${unitLabel()}${r.rows.slice(0, 12).some(x => x.assumption) ? " · Funds not looked through: holdings not disclosed, assumed to move with the market (beta 1)." : ""}</p>`)}
    ${card("All scenarios compared", barH({ rows: all.map(a => ({ label: a.label, segs: [{ v: -a.pct, color: a.k === key ? "var(--neg)" : "var(--bench)" }] })), fmt: v => v ? "−" + fmtPct(v, 1) : "0", labelW: 210 }) + `<p class="muted small" style="margin:0">Loss as % of total portfolio.</p>`)}
  </div>
  <div class="grid g2">
    ${card("Impact by entity", table("stressm", [
      { k: "name", label: "Entity", cls: () => "wrap", fmt: v => `<span class="nm">${esc(v)}</span>` }, { k: "total", label: "Portfolio", num: true, fmt: v => fmtAmt(v) },
      { k: "loss", label: "Loss", num: true, fmt: v => `<span class="neg">${fmtAmt(v)}</span>` }, { k: "pctEq", label: "% equity", num: true, fmt: v => fmtPct(v), tip: "Loss as % of the entity's look-through equity." }, { k: "pctTot", label: "% total", num: true, fmt: v => fmtPct(v), tip: "Loss as % of the entity's whole portfolio (debt and cash in funds held constant)." },
    ], perM, { dense: true }))}
    ${card("Impact by sector", table("stresss", [
      { k: "s", label: "Sector", fmt: v => esc(v) }, { k: "loss", label: "Loss", num: true, fmt: v => v < 0 ? `<span class="neg">${fmtAmt(v)}</span>` : fmtAmt(v) }, { k: "share", label: "Share of loss", num: true, fmt: v => fmtPct(v) },
    ], Object.entries(secImpact).map(([s, v]) => ({ s, loss: v, share: r.loss ? v / r.loss * 100 : 0 })), { sort: { k: "loss", d: "asc" }, dense: true, maxH: 320 }))}
  </div>
  <p class="note">Scenario results are estimates. Beta is a historical average and actual moves in a crisis are often larger. Funds' cash and debt are held constant.</p>`;
}
