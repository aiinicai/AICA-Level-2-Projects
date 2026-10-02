/** A list of company names: the first 12, the rest folded under "and N more". */
function nameList(codes, n = 12) {
  if (!codes.length) return `<div class="small muted">None</div>`;
  const names = codes.map(c => esc(shortName(IX.co[c]?.name || c)));
  return `<div class="small">${names.slice(0, n).join(", ")}${names.length > n ? `<details class="more"><summary class="small">and ${names.length - n} more</summary><div class="small">${names.slice(n).join(", ")}</div></details>` : ""}</div>`;
}
/* ==================================================================
   Fund views: overlap & consolidation, performance & risk, activity
   ================================================================== */
function schemeOpts(list, cur) { return list.map(s => `<option value="${s}" ${s === cur ? "selected" : ""}>${esc(IX.sch[s].name)}</option>`).join(""); }

function vOverlap() {
  const M = state.member, P = DB.policy, withPort = s => !!latestPort()[s], heldAll = heldSchemes(M), held = heldAll.filter(withPort);
  const list = (state.heldOnly ? heldAll : DB.schemes.map(s => s.scheme_id)).filter(withPort), noFile = (state.heldOnly ? heldAll : DB.schemes.map(s => s.scheme_id)).filter(s => !withPort(s));
  if (list.length < 2) return pageHead("Fund overlap &amp; consolidation", "") + card("", `<p style="margin:0">Overlap needs the monthly portfolio file of at least two schemes. Apply AMC portfolio files in <button class="alert-t" data-go="data" style="display:inline">Data &amp; controls → Live data</button>.</p>`);
  if (!state.pair || !list.includes(state.pair[0]) || !list.includes(state.pair[1])) {
    let best = null; list.forEach((a, i) => list.slice(i + 1).forEach(b => { const o = overlap(a, b).overlap; if (!best || o > best[2]) best = [a, b, o]; }));
    state.pair = best ? [best[0], best[1]] : null;
  }
  const short = s => shortName(IX.sch[s].name);
  let pairHtml = "";
  if (state.pair) {
    const [a, b] = state.pair, o = overlap(a, b), s = o.overlap > P.max_pair_overlap_pct ? "crit" : o.overlap > P.max_pair_overlap_pct * 0.8 ? "warn" : "ok";
    pairHtml = card(`${esc(IX.sch[a].name)} × ${esc(IX.sch[b].name)}`, `<div class="row" style="gap:14px"><span class="big">${fmtPct(o.overlap)}</span>${pill(s, s === "crit" ? `Above the ${P.max_pair_overlap_pct}% limit` : "Within limit")}</div><p class="muted small" style="margin:0">${o.common.length} common stocks · ${o.onlyA.length} only in ${esc(short(a))} · ${o.onlyB.length} only in ${esc(short(b))}</p>
      ${table("paircommon", [{ k: "name", label: "Common stock", fmt: v => `<span class="nm">${esc(v)}</span>` }, { k: "a", label: a, num: true, fmt: v => fmtPct(v, 2), tip: IX.sch[a].name }, { k: "b", label: b, num: true, fmt: v => fmtPct(v, 2), tip: IX.sch[b].name }, { k: "min", label: "Overlap", num: true, fmt: v => `<b>${fmtPct(v, 2)}</b>`, tip: "The lower of the two weights, which is what overlaps." }], o.common.map(c => ({ ...c, name: shortName(IX.co[c.code]?.name || c.code) })), { dense: true, maxH: 300, export: false, sort: { k: "min", d: "desc" } })}
      <div class="grid g2" style="gap:10px"><div><div class="small muted" style="font-weight:600">Only in ${esc(short(a))}</div>${nameList(o.onlyA)}</div><div><div class="small muted" style="font-weight:600">Only in ${esc(short(b))}</div>${nameList(o.onlyB)}</div></div>
      <p class="note">Overlap = Σ over common stocks of the lower of the two weights. It is the share of one fund's money invested exactly as the other fund invests it.</p>`);
  }
  // consolidation simulator
  const sim = state.sim || (held.length ? { from: state.pair && held.includes(state.pair[0]) ? state.pair[0] : held[0], to: list.find(s => s === "S03") || list.find(s => s !== held[0]), frac: 1 } : null);
  state.sim = sim;
  let simHtml = "";
  if (sim && held.includes(sim.from)) {
    const r = simulateSwitch(M, sim.from, sim.to, sim.frac), dlt = (a, b, f, good) => { const d = b - a; return `<span class="${d === 0 ? "" : (good ? d < 0 : d > 0) ? "pos" : "neg"}">${f(b)}</span>`; };
    simHtml = card("Consolidation simulator", `<div class="row">
      <label class="fld" for="simFrom">Exit from (held)<select id="simFrom">${schemeOpts(held, sim.from)}</select></label>
      <label class="fld" for="simTo">Switch into<select id="simTo">${schemeOpts(DB.schemes.map(s => s.scheme_id).filter(s => s !== sim.from && withPort(s)), sim.to)}</select></label>
      <div class="fld">Portion switched${seg("simFrac", [[0.25, "25%"], [0.5, "50%"], [0.75, "75%"], [1, "100%"]], sim.frac, { label: "Portion" })}</div></div>
      <div class="kpis k2">
        ${kpi("Amount switched", fmtAmt(r.amount), "", { cls: "flat" })}
        ${kpi("Annual expense saving", fmtAuto(r.terSaving), `Basis: ${r.terBasis}`, { cls: "flat", vcls: clsNum(r.terSaving), tip: "With TERs entered in the scheme master: TER difference. Otherwise: the Regular-plan cost gap measured from NAVs (applies only to Regular-plan units being switched)." })}
        ${kpi("Gain realised on exit", fmtAuto(r.gainLT + r.gainST, { sign: true }), `Long-term ${fmtAuto(r.gainLT)} · short-term ${fmtAuto(r.gainST)}`, { cls: "flat" })}
        ${kpi("Indicative tax on exit", fmtAuto(r.tax), `Break-even ${r.terSaving > 0 ? fmtN(r.tax / r.terSaving, 1) + " years" : "n.a."}`, { cls: "flat", tip: "Tax ÷ annual expense saving. Exit load, if any, is not included. Exemption assumed unused." })}
      </div>
      ${table("simt", [{ k: "m", label: "Measure" }, { k: "b", label: "Before", num: true, fmt: v => v }, { k: "a", label: "After", num: true, fmt: v => v }], [
        { m: "Funds held", b: r.before.funds, a: dlt(r.before.funds, r.after.funds, v => v, true) },
        { m: "Highest overlap between held funds", b: fmtPct(r.before.maxOv), a: dlt(r.before.maxOv, r.after.maxOv, v => fmtPct(v), true) },
        { m: "HHI (look-through equity)", b: fmtHHI(r.before.hhi), a: dlt(r.before.hhi, r.after.hhi, v => fmtHHI(v), true) },
        { m: "Effective number of stocks", b: fmtN(r.before.effN, 1), a: dlt(r.before.effN, r.after.effN, v => fmtN(v, 1), false) },
        { m: "Top 10 share", b: fmtPct(r.before.top10), a: dlt(r.before.top10, r.after.top10, v => fmtPct(v), true) },
      ], { export: false, dense: true })}
      <p class="note">Green means the measure moves toward the investment policy (lower concentration, lower overlap). Switching between two schemes is a redemption and a fresh purchase for tax purposes.</p>`, { sub: "Illustrates the effect of moving money between two schemes, for committee discussion." });
  }
  const lim = P.max_pair_overlap_pct;
  const matrix = `<div class="tbl-wrap"><table class="tbl heat"><thead><tr><th><span class="th">Fund</span></th>${list.map(s => `<th class="num" title="${esc(IX.sch[s].name)}"><span class="th" style="justify-content:center">${s}</span></th>`).join("")}</tr></thead><tbody>
    ${list.map(a => `<tr><td class="rowh" title="${esc(IX.sch[a].name)}"><span class="nm">${a} · ${esc(short(a))}</span><span class="sub">${esc(IX.sch[a].category)}</span></td>${list.map(b => {
      if (a === b) return `<td class="cell-heat muted">—</td>`;
      const o = overlap(a, b).overlap || 0, t = o / 100, sel = state.pair && [a, b].sort().join() === [...state.pair].sort().join();
      return `<td class="cell-heat ${sel ? "sel" : ""}" data-pair="${a}|${b}" style="background:${seqFill(t)};color:${seqInk(t)};font-weight:${o > lim ? 700 : 400}" ${tipAttr(`${esc(IX.sch[a].name)} × ${esc(IX.sch[b].name)}: ${fmtPct(o)}`)}>${o.toFixed(0)}</td>`;
    }).join("")}</tr>`).join("")}</tbody></table></div>`;
  let pairsAbove = 0; held.forEach((a, i) => held.slice(i + 1).forEach(b => { if (overlap(a, b).overlap > lim) pairsAbove++; }));
  const miss = noFile.length ? `<p class="note">No portfolio file applied yet for: ${noFile.map(s => esc(IX.sch[s].name)).join(", ")}. They are left out of the matrix.</p>` : "";
  return pageHead("Fund overlap &amp; consolidation", "How much of each fund's portfolio duplicates another's, based on the latest monthly disclosures, and what consolidating would change. " + basisLine(state.member),
    (heldSchemes(state.member).length < DB.schemes.length ? seg("heldOnly", [[1, "Funds held"], [0, "All tracked funds"]], state.heldOnly ? 1 : 0, { label: "Scope" }) : `<span class="muted small">All ${DB.schemes.length} tracked funds are held</span>`)) + holdingsLagNote(state.member) + `
  <div class="kpis k4">
    ${kpi("Funds held", heldAll.length, `${held.length} with portfolio files`)}
    ${kpi("Pairs above the overlap limit", `${pairsAbove} of ${held.length * (held.length - 1) / 2}`, `Limit ${fmtPct(lim)}`, { vcls: pairsAbove ? "neg" : "pos" })}
    ${kpi("Regular-plan holdings", fmtAmt(holdings(M).filter(h => h.asset_type === "MF" && h.plan === "Regular").reduce((s, h) => s + h.value, 0)), "Cost more than Direct plans")}
    ${kpi("Direct-plan saving", fmtAuto(directSaving(M)) + "<span class='muted small'> /yr</span>", "Measured from Regular vs Direct NAVs")}
  </div>
  ${card("Overlap matrix", `<div class="legend"><span><i class="sw" style="background:${seqFill(0.15)}"></i>Low</span><span><i class="sw" style="background:${seqFill(0.5)}"></i>Moderate</span><span><i class="sw" style="background:${seqFill(0.9)}"></i>High</span><span class="muted">% overlap; bold cells exceed the ${lim}% limit. Select a cell for detail.</span></div>${matrix}${miss}`)}
  <div class="grid g2">${pairHtml}${simHtml}</div>`;
}

function vFunds() {
  const M = state.member, held = heldSchemes(M), scope = state.sel.fundScope || "held";
  const ids = (scope === "held" ? held : DB.schemes.map(s => s.scheme_id)).filter(id => fundStats(id));
  if (!ids.length) return pageHead("Fund performance &amp; risk", "") + card("", `<p class="muted" style="margin:0">No NAV history is available yet. Run a refresh from Data &amp; controls → Live data.</p>`);
  if (!ids.includes(state.fund)) state.fund = ids[0];
  const sid = state.fund, s = IX.sch[sid], f = fundStats(sid), rk = categoryRank(sid), bn = IX.idx[s.benchmark] || IX.mkt, n = IX.nav[sid + "|Direct"];
  const P100 = x => isNum(x) ? x * 100 : null;
  const rows = ids.map(id => { const x = fundStats(id), sc = IX.sch[id], r = categoryRank(id); return { id, name: sc.name, cat: sc.category, r1y: P100(x.r1y), cagr3: P100(x.cagr3), ex: isNum(x.cagr3) && isNum(x.bench3) ? (x.cagr3 - x.bench3) * 100 : null, alpha: P100(x.alpha), vol: P100(x.vol), sharpe: x.sharpe, sortino: x.sortino, mdd: isNum(x.mdd) ? -x.mdd * 100 : null, beta: x.beta, te: P100(x.te), ir: x.ir, gap: impliedGap(id), rank: r.rank ? `${r.rank}/${r.of}` : "—", held: held.includes(id) }; });
  const labels = DB.meta.dates.map(fmtMon), i0 = n.findIndex(isNum);
  const nav100 = n.map(v => isNum(v) ? v / n[i0] * 100 : null), bn100 = bn ? bn.map(v => isNum(v) && isNum(bn[i0]) ? v / bn[i0] * 100 : null) : [];
  const rollLabels = DB.meta.dates.slice(12).map(fmtMon);
  const pts = DB.schemes.map(x => ({ x, q: fundStats(x.scheme_id) })).filter(o => o.q && isNum(o.q.vol) && isNum(o.q.cagr3)).map(({ x, q }) => ({ x: q.vol * 100, y: q.cagr3 * 100, label: shortName(x.name), color: held.includes(x.scheme_id) ? "var(--s1)" : "var(--bench)", hl: x.scheme_id === sid, tip: `${esc(x.category)} · Sharpe ${fmtN(q.sharpe, 2)}`, click: "fund|" + x.scheme_id }));
  const H = holdings(M).filter(h => h.asset_type === "MF");
  const corrIds = (held.length > 1 ? held : ids).filter(id => fundStats(id));
  const corrM = corrIds.map(a => corrIds.map(b => { if (a === b) return 1; const [x, y] = pairedRets(IX.nav[a + "|Direct"], IX.nav[b + "|Direct"]); return x.length > 12 ? corrOf(x, y) : null; }));
  const cmin = Math.min(...corrM.flat().filter(isNum)), lo = Math.min(0.8, Math.floor(cmin * 10) / 10);
  return pageHead("Fund performance &amp; risk", `Returns and risk from month-end NAVs published by AMFI (Direct plans), measured against each fund's benchmark index. Risk-free rate ${fmtPct(DB.policy.risk_free_pct)}.`,
    (heldSchemes(state.member).length < DB.schemes.length ? seg("fundScope", [["held", "Funds held"], ["all", "All tracked funds"]], scope, { label: "Scope" }) : `<span class="muted small">All ${DB.schemes.length} tracked funds are held</span>`)) +
  card("Scorecard", table("funds", [
    { k: "name", label: "Fund", fmt: (v, r) => `<span class="nm">${esc(shortName(v))}</span><span class="sub">${esc(r.cat)}${r.held ? " · held" : ""}</span>`, csv: r => r.name },
    { k: "r1y", label: "1Y", num: true, fmt: v => `<span class="${clsNum(v)}">${fmtPct(v)}</span>` },
    { k: "cagr3", label: "3Y CAGR", num: true, fmt: v => `<b>${fmtPct(v)}</b>` },
    { k: "ex", label: "vs bench*", num: true, fmt: v => `<span class="${clsNum(v)}">${fmtSPct(v)}</span>`, tip: "3Y CAGR minus benchmark 3Y change (percentage points). Benchmarks are price indices (no dividends) while fund NAVs include them, so this flatters every fund by roughly the index dividend yield, about 1 to 1.5 points a year. Total-return indices are not yet loaded." },
    { k: "alpha", label: "Alpha", num: true, fmt: v => `<span class="${clsNum(v)}">${fmtSPct(v)}</span>`, tip: "Jensen's alpha: CAGR minus [Rf + beta x (benchmark CAGR minus Rf)]. Benchmarks are price indices (no dividends) while fund NAVs include them, so this flatters every fund by roughly the index dividend yield, about 1 to 1.5 points a year. Total-return indices are not yet loaded." },
    { k: "vol", label: "Volatility", num: true, fmt: v => fmtPct(v), tip: "Annualised standard deviation of monthly returns." },
    { k: "sharpe", label: "Sharpe", num: true, fmt: v => fmtN(v, 2), tip: "(CAGR − risk-free rate) ÷ volatility." },
    { k: "sortino", label: "Sortino", num: true, fmt: v => fmtN(v, 2), tip: "(CAGR − risk-free rate) ÷ downside deviation." },
    { k: "mdd", label: "Max drawdown", num: true, fmt: v => `<span class="neg">${fmtPct(v)}</span>` },
    { k: "beta", label: "Beta", num: true, fmt: v => fmtN(v, 2) },
    { k: "ir", label: "Info ratio", num: true, fmt: v => fmtN(v, 2), tip: "(CAGR − benchmark CAGR) ÷ tracking error." },
    { k: "gap", label: "Regular cost gap", num: true, fmt: v => fmtPct(v, 2), tip: "Direct-plan 1-year return minus Regular-plan 1-year return: the extra annual expense ratio of the Regular plan, measured from actual NAVs." },
    { k: "rank", label: "Category rank", num: true, sortV: r => r.rank === "—" ? 99 : +r.rank.split("/")[0] },
  ], rows, { sort: { k: "cagr3", d: "desc" }, rowAttr: r => `data-fund="${r.id}" data-row="1" ${r.id === sid ? 'style="background:var(--accent-soft)"' : ""}`, maxH: 460 }), { sub: "Select a fund to see its detail below." }) + `
  <div class="ph" style="margin-top:4px"><div><h1 style="font-size:20px">${esc(s.name)}</h1><p>${esc(s.amc)} · ${esc(s.category)} · benchmark ${esc(s.benchmark_name || "")}</p></div><div class="acts"><select id="fundSel" aria-label="Select fund">${schemeOpts(ids, sid)}</select></div></div>
  <div class="kpis">
    ${kpi("3Y CAGR", fmtPct(P100(f.cagr3)), `Benchmark ${fmtPct(P100(f.bench3))}`)}
    ${kpi("1Y return", fmtPct(P100(f.r1y)), `Benchmark ${fmtPct(P100(f.bench1y))}`, { vcls: clsNum(f.r1y) })}
    ${kpi("Sharpe / Sortino", `${fmtN(f.sharpe, 2)} / ${fmtN(f.sortino, 2)}`, `Volatility ${fmtPct(P100(f.vol))}`)}
    ${kpi("Maximum drawdown", fmtPct(isNum(f.mdd) ? -f.mdd * 100 : null), "Peak to trough, month-end", { vcls: "neg" })}
    ${kpi("Up / down capture", `${fmtN(P100(f.upCap), 0)} / ${fmtN(P100(f.downCap), 0)}`, "Higher up and lower down is better", { tip: "Average fund return in months the benchmark rose (fell) ÷ average benchmark return in those months × 100." })}
    ${kpi("Beat benchmark", fmtPct(P100(f.rollBeat), 0), "of rolling 1-year periods")}
  </div>
  <div class="grid g2">
    ${card("Growth of ₹100", lineChart({ series: [{ name: shortName(s.name), values: nav100, color: "var(--s1)" }, ...(bn ? [{ name: s.benchmark_name || "Benchmark", values: bn100, color: "var(--bench)", dash: true }] : [])], labels, yFmt: v => fmtN(v, 0) }), { sub: `Direct plan NAV (dividends reinvested) vs benchmark price index (no dividends), rebased to 100 on ${fmtDate(DB.meta.dates[i0])}` })}
    ${card("Rolling 1-year returns", lineChart({ series: [{ name: shortName(s.name), values: f.roll.map(x => isNum(x) ? x * 100 : null), color: "var(--s1)" }, { name: "Benchmark", values: f.rollB.map(x => isNum(x) ? x * 100 : null), color: "var(--bench)", dash: true }], labels: rollLabels, yFmt: v => fmtN(v, 0) + "%", zero: true }), { sub: "Each point is the return over the 12 months ending that month." })}
  </div>
  <div class="grid g21">
    ${card("Risk and return, all tracked funds", pts.length > 2 ? scatter({ points: pts, xFmt: v => fmtN(v, 0) + "%", yFmt: v => fmtN(v, 0) + "%", xTitle: "Volatility (annualised)", yTitle: "3Y CAGR" }) + `<div class="legend"><span><i class="sw" style="background:var(--s1)"></i>Held</span><span><i class="sw" style="background:var(--bench)"></i>Not held</span><span class="muted">Up and to the left is better. Select a dot to open the fund.</span></div>` : `<p class="muted">Needs at least three funds with three years of NAVs.</p>`)}
    ${card("Fund facts", `<dl class="dl"><dt>AMFI code (Direct)</dt><dd class="mono">${esc(s.amfi_code || "—")}</dd><dt>AMFI code (Regular)</dt><dd class="mono">${esc(s.amfi_code_regular || "—")}</dd><dt>AMFI name</dt><dd style="white-space:normal">${esc(s.amfi_name || "—")}</dd><dt>Latest NAV</dt><dd>₹${fmtN(n[IX.T], 4)}</dd><dt>Portfolio date</dt><dd>${s.portfolio_date ? fmtDate(s.portfolio_date) : "No file applied"}</dd><dt>Equity / debt & other / cash</dt><dd>${fmtPct(s.equity_pct)} / ${fmtPct(s.debt_pct)} / ${fmtPct(s.cash_pct)}</dd><dt>Stocks held</dt><dd>${(latestPort()[sid] || []).length || "—"}</dd><dt>Regular-plan cost gap</dt><dd>${fmtPct(impliedGap(sid), 2)}</dd><dt>Category rank (3Y)</dt><dd>${rk.rank ? `${rk.rank} of ${rk.of}` : "—"}</dd><dt>Tracking error</dt><dd>${fmtPct(P100(f.te))}</dd><dt>Beta</dt><dd>${fmtN(f.beta, 2)}</dd><dt>Alpha</dt><dd>${fmtSPct(P100(f.alpha))}</dd></dl>`, { sub: "Source: AMFI NAVs and the AMC's portfolio disclosure" })}
  </div>
  <div class="stack">
    ${card("Return correlation between funds", `<div class="tbl-wrap"><table class="tbl heat"><thead><tr><th><span class="th">Fund</span></th>${corrIds.map(a => `<th class="num"><span class="th" style="justify-content:center">${a}</span></th>`).join("")}</tr></thead><tbody>${corrIds.map((a, i) => `<tr><td><span class="nm">${a}</span> <span class="muted small">${esc(shortName(IX.sch[a].name))}</span></td>${corrM[i].map((v, j) => `<td class="cell-heat" style="background:${i === j || !isNum(v) ? "var(--surface-3)" : seqFill(Math.max(0, (v - lo) / (1 - lo)))};color:${i !== j && isNum(v) ? seqInk(Math.max(0, (v - lo) / (1 - lo))) : "var(--ink)"}" ${tipAttr(`${esc(IX.sch[a].name)} vs ${esc(IX.sch[corrIds[j]].name)}: ${fmtN(v, 2)}`)}>${fmtN(v, 2)}</td>`).join("")}</tr>`).join("")}</tbody></table></div><p class="muted small" style="margin:0">Pearson correlation of monthly returns; the stronger the blue, the higher the correlation (scale ${fmtN(lo, 1)} to 1.00). Pairs above 0.95 add little diversification.</p>`)}
  </div>
  <div class="grid g2">
    ${card("What the Regular plans cost", table("cost", [
      { k: "name", label: "Holding", fmt: (v, r) => `<span class="nm">${esc(shortName(v))}</span><span class="sub">${esc(r.ent)} · ${r.plan}</span>` },
      { k: "value", label: "Value", num: true, fmt: v => fmtAmt(v) }, { k: "gap", label: "Cost gap", num: true, fmt: v => fmtPct(v, 2), tip: "Direct minus Regular 1-year NAV return." },
      { k: "save", label: "Saving if Direct", num: true, fmt: v => v > 0 ? `<b class="pos">${fmtAuto(v)}</b>` : "—" },
    ], H.filter(h => h.plan === "Regular").map(h => { const g = impliedGap(h.instrument); return { name: IX.sch[h.instrument].name, ent: IX.mem[h.member_id].name, plan: h.plan, value: h.value, gap: g, save: isNum(g) ? h.value * g / 100 : 0 }; }), { sort: { k: "save", d: "desc" }, dense: true, maxH: 380, empty: "No Regular-plan holdings.",
      totals: { name: "Total", value: fmtAmt(H.filter(h => h.plan === "Regular").reduce((a, h) => a + h.value, 0)), save: fmtAuto(directSaving(M)) } }), { sub: "Measured from the actual gap between Direct and Regular NAVs over the last 12 months." })}
    ${(() => {
      // the other side of the decision: what a switch to Direct would realise (a switch is a redemption and a fresh purchase)
      const R = H.filter(h => h.plan === "Regular"), mf = H.filter(h => h.asset_type === "MF").reduce((a, h) => a + h.value, 0);
      const rv = R.reduce((a, h) => a + h.value, 0), gain = R.reduce((a, h) => a + h.unrealised, 0), ltv = R.reduce((a, h) => a + (h.lt_value || 0), 0);
      if (!R.length) return card("Switching to Direct: what to weigh", `<p class="muted" style="margin:0">No Regular-plan holdings for ${esc(memberName(M))}.</p>`);
      return card("Switching to Direct: what to weigh", `<div class="kpis k3">
          ${kpi("Regular-plan holdings", fmtAmt(rv), `${fmtPct(mf ? rv / mf * 100 : null, 1)} of fund holdings · ${R.length} holding${R.length === 1 ? "" : "s"}`)}
          ${kpi("Saving if switched", fmtAuto(directSaving(M)) + "<span class='muted small'> /yr</span>", "At today's values, before growth", { vcls: "pos" })}
          ${kpi("Gain a switch would realise", fmtAmt(gain, { sign: true }), `${fmtPct(rv ? ltv / rv * 100 : null, 0)} of the value is in lots held over 12 months`, { vcls: clsNum(gain) })}
        </div>
        <p class="note" style="margin:12px 0 0">A switch from Regular to Direct is a redemption and a fresh purchase: capital-gains tax and any exit load apply, and ELSS units in lock-in cannot be switched. The Consolidation simulator on <button class="btn ghost sm" data-go="overlap">Fund overlap</button> estimates the tax for a chosen fund. For committee discussion, not a recommendation.</p>`,
        { sub: "The saving recurs every year; the tax is paid once, on the gain realised." });
    })()}
  </div>`;
}

function vActivity() {
  const act = activity(), M = state.member, lt = lookThrough(M);
  if (!act.schemes) return pageHead("Fund-manager activity", "What professional fund managers bought and sold between two consecutive monthly portfolio disclosures.") + card("", `<p style="margin:0">This screen needs <b>two consecutive months</b> of AMC portfolio files for at least one scheme. Upload them in <button class="alert-t" data-go="data" style="display:inline">Data &amp; controls → Live data</button>.</p>`);
  const ids = DB.schemes.map(s => s.scheme_id).filter(s => act.perScheme[s]);
  if (!ids.includes(state.actScheme)) state.actScheme = ids[0];
  const st = Object.values(act.stock).map(s => ({ ...s, name: IX.co[s.code]?.name || s.code, sector: IX.co[s.code]?.sector || "", net: s.adding - s.reducing, fam: lt.rows.find(r => r.code === s.code)?.total || 0 }));
  const top = [...st].sort((a, b) => b.netW - a.netW), flows = [...top.slice(0, 8), ...top.slice(-6).filter(x => x.netW < 0)].map(s => ({ label: shortName(s.name), v: s.netW, tip: `${s.adding} adding · ${s.reducing} reducing` }));
  const ps = act.perScheme[state.actScheme], sch = IX.sch[state.actScheme];
  const turn = ids.map(s => ({ label: shortName(IX.sch[s].name), segs: [{ v: act.perScheme[s].turnover, color: "var(--s1)" }] })).sort((a, b) => b.segs[0].v - a.segs[0].v);
  return pageHead("Fund-manager activity", `What professional fund managers bought and sold between consecutive monthly portfolio disclosures of ${act.schemes} schemes (latest ${fmtDate(act.to)}). Signals are net of price movement; they describe what managers did, not what the family should do.`) + `
  <div class="grid g2">
    ${card("Net weight change by stock", `<p class="muted small" style="margin:0">Sum of each scheme's change in % of net assets. Positive means funds added.</p>` + divBar({ rows: flows, fmt: v => fmtSPct(v, 2) }))}
    ${card("Portfolio turnover last month", `<p class="muted small" style="margin:0">Half the sum of absolute weight changes. Index funds should be near zero.</p>` + barH({ rows: turn, fmt: v => fmtPct(v, 1), labelW: 220 }))}
  </div>
  ${card("Consensus across schemes", table("consensus", [
    { k: "name", label: "Company", fmt: (v, r) => `<span class="nm">${esc(v)}</span><span class="sub">${esc(r.sector)}</span>` },
    { k: "holders", label: "Schemes holding", num: true }, { k: "adding", label: "Adding", num: true, fmt: v => v ? `<b class="pos">${v}</b>` : "0" },
    { k: "reducing", label: "Reducing", num: true, fmt: v => v ? `<b class="neg">${v}</b>` : "0" }, { k: "entries", label: "New entries", num: true }, { k: "exits", label: "Full exits", num: true },
    { k: "netW", label: "Net change (pp)", num: true, fmt: v => `<span class="${clsNum(v)}">${fmtSPct(v, 2)}</span>` },
    { k: "fam", label: "Family exposure", num: true, fmt: v => v ? fmtAmt(v) : "—" },
  ], st, { search: r => r.name + " " + r.sector, sort: { k: "adding", d: "desc" }, noun: "stocks", maxH: 480, rowAttr: r => `data-company="${r.code}" data-row="1"`, limit: 25 }), { sub: "A weight change counts when it exceeds 0.25 percentage points." })}
  ${card("Scheme detail", `<div class="row"><label class="fld" for="actSel">Scheme<select id="actSel">${schemeOpts(ids, state.actScheme)}</select></label><span class="muted small">${fmtDate(ps.from)} → ${fmtDate(ps.to)} · ${ps.entries.length} new entries · ${ps.exits.length} exits · turnover ${fmtPct(ps.turnover, 1)}</span></div>` +
    table("actdet", [
      { k: "name", label: "Stock", fmt: (v, r) => `<span class="nm">${esc(v)}</span>` }, { k: "prev", label: fmtMon(ps.from), num: true, fmt: v => v ? fmtPct(v, 2) : "—" },
      { k: "now", label: fmtMon(ps.to), num: true, fmt: v => v ? fmtPct(v, 2) : "—" }, { k: "dw", label: "Change", num: true, fmt: v => `<span class="${clsNum(v)}">${fmtSPct(v, 2)}</span>` },
      { k: "st", label: "Action", fmt: v => v },
    ], ps.changes.filter(x => Math.abs(x.dw) > 0.001).map(x => ({ ...x, name: IX.co[x.code]?.name || x.code, st: x.prev === 0 ? pill("ok", "New entry") : x.now === 0 ? pill("crit", "Exited") : x.dw > 0 ? pill("neutral", "Increased") : pill("neutral", "Reduced") })), { sort: { k: "dw", d: "desc" }, dense: true, maxH: 420, rowAttr: r => `data-company="${r.code}" data-row="1"` }), { sub: esc(sch.name) })}`;
}
