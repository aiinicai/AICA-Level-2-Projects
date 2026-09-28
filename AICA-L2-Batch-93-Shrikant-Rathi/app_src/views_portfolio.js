/* ==================================================================
   Portfolio views: dashboard, holdings, look-through, allocation
   ================================================================== */
function pageHead(title, desc, acts = "") {
  return `<div class="ph"><div><h1>${title}</h1>${desc ? `<p>${desc}</p>` : ""}</div>${acts ? `<div class="acts">${acts}</div>` : ""}</div>`;
}
const amtTick = v => (v / unitDiv()).toLocaleString("en-IN", { maximumFractionDigits: state.units === "inr" ? 0 : 1 });

function vDashboard() {
  const M = state.member, H = holdings(M), lt = lookThrough(M), con = concentration(lt), al = alerts(M);
  const value = H.reduce((s, h) => s + h.value, 0), cost = H.reduce((s, h) => s + h.cost, 0), x = memberXirr(M);
  const vh = valueHistory(M), first = DB.transactions.filter(t => M === "ALL" || t.member_id === M).map(t => t.date).sort()[0];
  const crit = al.filter(a => a.sev === "crit").length, warn = al.length - crit;
  const lim = lt.eq * DB.policy.max_single_stock_pct / 100;
  const top = lt.rows.slice(0, 12).map(r => ({ label: shortName(IX.co[r.code]?.name || r.code), segs: [{ v: r.direct / unitDiv(), color: "var(--s1)", name: "Direct" }, { v: r.viaMF / unitDiv(), color: "var(--s2)", name: "Through funds" }], pct: r.pct, tip: `${fmtPct(r.pct, 2)} of look-through equity` }));
  const mix = [["Equity held directly", lt.directTotal, "var(--s1)"], ["Equity through funds", lt.eq - lt.directTotal, "var(--s2)"], ["Debt in funds", lt.debt, "var(--s3)"], ["Cash & other in funds", Math.max(0, lt.cash), "var(--s4)"], ...(lt.unmapped ? [["Funds not looked through", lt.unmapped, "var(--bench)"]] : [])];
  const act = activity(), buys = Object.values(act.stock).filter(s => s.adding > s.reducing).sort((a, b) => b.adding - a.adding || b.netW - a.netW).slice(0, 4);
  const sells = Object.values(act.stock).filter(s => s.reducing > s.adding).sort((a, b) => b.reducing - a.reducing || a.netW - b.netW).slice(0, 4);
  const held = heldSchemes(M);
  const byMember = DB.members.map(m => ({ m, v: holdings(m.member_id).reduce((s, h) => s + h.value, 0) })).filter(x => x.v > 0);
  return pageHead(`${esc(memberName(M))}`, `Consolidated view of mutual funds and direct equity, looked through to underlying stocks. ${basisLine(M)}`,
    `<button class="btn" data-go="report">${ICON.report} Family report</button>`) + holdingsLagNote(M) + `
  <div class="kpis ${BRIDGE.quotes ? "k7" : ""}">
    ${kpi(`Portfolio value · ${fmtDate(DB.meta.as_on)}`, fmtAmt(value), `Cost ${fmtAmt(cost)}`)}
    ${BRIDGE.quotes ? (() => { const L = latestValue(M); return kpi("At latest prices", fmtAmt(L.v), `<span class="${clsNum(L.v - value)}">${fmtSPct((L.v / value - 1) * 100)}</span> since ${fmtDate(DB.meta.as_on).slice(0, -5)} · gain ${fmtAmt(L.gain, { sign: true })}<br>${latestDates(L, true)}`, { tip: QUOTE_NOTE }); })() : ""}
    ${kpi("Unrealised gain", fmtAmt(value - cost, { sign: true }), `${fmtSPct((value - cost) / cost * 100)} on cost`, { vcls: clsNum(value - cost) })}
    ${kpi("XIRR", fmtPct(x * 100, 2), `Since ${fmtDate(first)}`, { tip: "Money-weighted annualised return on every purchase, SIP and sale, valued at today's prices." })}
    ${kpi("Look-through equity", fmtAmt(lt.eq), `${con.n} stocks · ${fmtAmt(lt.debt + lt.cash)} debt & cash in funds`)}
    ${kpi("Effective stocks", fmtN(con.effN, 1), `HHI ${fmtHHI(con.hhi)} · top 10 ${fmtPct(con.top10)}`, { tip: "1 ÷ HHI. The number of equally weighted stocks that would give the same concentration." })}
    ${kpi("Policy status", `<span class="${crit ? "neg" : "pos"}">${crit} breach${crit === 1 ? "" : "es"}</span>`, `${warn} warnings · equity beta ${fmtN(portBeta(lt), 2)}`)}
  </div>
  <div class="grid g21">
    ${card("Portfolio value and money invested", lineChart({ series: [{ name: "Portfolio value", values: vh.map(p => p.value), color: "var(--s1)" }, { name: "Net amount invested", values: vh.map(p => p.invested), color: "var(--bench)", dash: true }], labels: vh.map(p => fmtMon(p.d)), yFmt: v => amtTick(v), area: true, yTitle: unitLabel(), height: 300, W: CW.two }), { sub: "Month-end values from NAV and price history. The gap between the lines is the cumulative gain." })}
    ${card(`Policy alerts`, `<div class="alerts">${al.slice(0, 4).map(alertItem).join("") || pill("ok", "All limits met")}</div>${al.length > 4 ? `<button class="btn sm" data-go="concentration">View all ${al.length} alerts</button>` : ""}`, { sub: `${crit} breaches · ${warn} warnings against the investment policy` })}
  </div>
  <div class="grid g2">
    ${card("Largest look-through exposures", `<div class="legend"><span><i class="sw" style="background:var(--s1)"></i>Direct</span><span><i class="sw" style="background:var(--s2)"></i>Through funds</span><span class="muted">Axis in ${unitLabel()}; label shows % of equity</span></div>` +
      barH({ rows: top, fmt: v => amtTick(v * unitDiv()), limit: lim / unitDiv(), limitLabel: `single-stock limit ${DB.policy.max_single_stock_pct}%`, valueText: r => fmtPct(r.pct) }), { sub: "The same company held directly and inside funds, added together.", actions: `<button class="btn ghost sm" data-go="lookthrough">Open</button>` })}
    <div class="stack">
      ${card("Where the money sits", `<div class="stack100">${mix.map(([l, v, c]) => `<i style="width:${v / lt.total * 100}%;background:${c}" ${tipAttr(`${esc(l)}: ${fmtAmt(v)} (${fmtPct(v / lt.total * 100)})`)}></i>`).join("")}</div>
        <div class="grid g2" style="gap:8px 16px">${mix.map(([l, v, c]) => `<div class="row" style="justify-content:space-between;flex-wrap:nowrap"><span class="legend"><span><i class="sw" style="background:${c}"></i>${l}</span></span><b class="num">${fmtAmt(v)} <span class="muted small">${fmtPct(v / lt.total * 100)}</span></b></div>`).join("")}</div>`)}
      ${card("By entity", table("dash-mem", [
        { k: "name", label: "Entity", fmt: (v, r) => `<span class="nm">${esc(v)}</span><span class="sub">${esc(r.type)}</span>` },
        { k: "value", label: BRIDGE.quotes ? `Value · ${fmtDate(DB.meta.as_on)}` : "Value", num: true, fmt: v => fmtAmt(v) },
        ...(BRIDGE.quotes ? [{ k: "latest", label: "At latest prices", num: true, tip: QUOTE_NOTE, fmt: (v, r) => `${fmtAmt(v)}<span class="sub ${clsNum(v - r.value)}">${fmtSPct((v / r.value - 1) * 100)}</span>` }] : []),
        { k: "xirr", label: "XIRR", num: true, fmt: v => fmtPct(v, 2) },
        { k: "top", label: "Largest stock", fmt: (v, r) => `${esc(v)}<span class="sub">${fmtPct(r.topPct)} of its equity</span>` },
      ], byMember.map(({ m, v }) => { const k = concentration(lookThrough(m.member_id)); return { name: m.name, type: m.type, id: m.member_id, value: v, latest: BRIDGE.quotes ? latestValue(m.member_id).v : null, xirr: memberXirr(m.member_id) * 100, top: k.top ? shortName(IX.co[k.top.code]?.name || k.top.code) : "—", topPct: k.top ? k.top.pct : null }; }), { export: false, dense: true, rowAttr: r => `data-member="${r.id}" data-row="1" title="Switch to ${esc(r.name)}"` }))}
    </div>
  </div>
  <div class="grid g2">
    ${card("Funds held: performance snapshot", table("dash-funds", [
      { k: "name", label: "Fund", fmt: (v, r) => `<span class="nm">${esc(shortName(v))}</span><span class="sub">${esc(r.cat)}</span>` },
      { k: "value", label: "Value", num: true, fmt: v => fmtAmt(v) },
      { k: "cagr3", label: "3Y CAGR", num: true, fmt: v => fmtPct(v) },
      { k: "ex", label: "vs benchmark*", num: true, fmt: v => `<span class="${clsNum(v)}">${fmtSPct(v)}</span>`, tip: "3-year CAGR minus benchmark 3-year CAGR, in percentage points. Benchmarks are price indices (no dividends) while fund NAVs include them, so this flatters every fund by roughly the index dividend yield, about 1 to 1.5 points a year. Total-return indices are not yet loaded." },
    ], held.map(s => { const hs = holdings(M).filter(h => h.instrument === s), v = hs.reduce((a, h) => a + h.value, 0), reg = hs.filter(h => h.plan === "Regular").reduce((a, h) => a + h.value, 0), plan = reg > v - reg ? "Regular" : "Direct", f = fundStats(s, plan) || {}; return { id: s, name: IX.sch[s].name + " · " + plan, cat: IX.sch[s].category, value: v, cagr3: isNum(f.cagr3) ? f.cagr3 * 100 : null, ex: isNum(f.cagr3) && isNum(f.bench3) ? (f.cagr3 - f.bench3) * 100 : null }; }), { export: false, dense: true, limit: 7, sort: { k: "value", d: "desc" }, rowAttr: r => `data-fund="${r.id}" data-row="1"` }), { actions: `<button class="btn ghost sm" data-go="funds">Open</button>` })}
    ${card("What fund managers did last month", !act.schemes ? `<p class="muted" style="margin:0">Apply two consecutive months of AMC portfolio files (Data &amp; controls → Live data) to see which stocks the fund managers bought and sold.</p>` : `<p class="muted small" style="margin:0">Changes between the ${fmtDate(act.from)} and ${fmtDate(act.to)} portfolio disclosures of ${act.schemes} schemes.</p>
      <div class="grid g2" style="gap:14px">
      <div><h3 class="small muted" style="margin:0 0 6px">Most funds adding</h3>${buys.map(s => `<div class="sig"><button class="alert-t" data-company="${s.code}">${esc(shortName(IX.co[s.code]?.name || s.code))}</button><span>${pill("ok", `${s.adding} adding`)}</span></div>`).join("")}</div>
      <div><h3 class="small muted" style="margin:0 0 6px">Most funds reducing</h3>${sells.map(s => `<div class="sig"><button class="alert-t" data-company="${s.code}">${esc(shortName(IX.co[s.code]?.name || s.code))}</button><span>${pill("warn", `${s.reducing} reducing`)}</span></div>`).join("")}</div>
      </div>`, { actions: `<button class="btn ghost sm" data-go="activity">Open</button>` })}
  </div>`;
}

function vHoldings() {
  const M = state.member, tab = state.tab.holdings || "holdings", P = DB.policy;
  const H = holdings(M).filter(h => state.assetFilter === "ALL" || h.asset_type === state.assetFilter);
  const R = realised(M), tx = DB.transactions.filter(t => M === "ALL" || t.member_id === M);
  const tot = k => H.reduce((s, h) => s + h[k], 0);
  let body = "";
  if (tab === "holdings") {
    const LH = BRIDGE.quotes ? Object.fromEntries(latestHoldings(M).map(h => [h.member_id + "|" + h.asset_type + "|" + h.instrument + "|" + (h.plan || ""), h])) : {};
    const rows = H.map(h => ({ ...h, ...(() => { const l = LH[h.member_id + "|" + h.asset_type + "|" + h.instrument + "|" + (h.plan || "")]; return l ? { lvalue: l.value, lgain: l.unrealised, lpx: l.lpx } : {}; })(), name: instName(h), ent: IX.mem[h.member_id].name, ret: h.unrealised / h.cost * 100, x: h.xirr * 100, ltShare: h.lt_value / h.value * 100 }));
    body = `<div class="row">${seg("assetFilter", [["ALL", "All"], ["MF", "Mutual funds"], ["EQ", "Direct equity"]], state.assetFilter, { label: "Asset type" })}</div>` + table("holdings", [
      { k: "name", label: "Instrument", fmt: (v, r) => `<span class="nm">${esc(v)}</span><span class="sub">${r.asset_type === "MF" ? `${esc(IX.sch[r.instrument].category)} · ${esc(r.plan)} plan` : `${esc(IX.co[r.instrument]?.sector || "")} · ${esc(r.instrument)}`}</span>`, sortV: r => r.name, csv: r => r.name },
      { k: "ent", label: "Entity", fmt: v => esc(v) },
      { k: "units", label: "Units / qty", num: true, fmt: (v, r) => r.asset_type === "MF" ? fmtN(v, 3) : fmtN(v, 0) },
      { k: "avg", label: "Avg cost", num: true, fmt: v => "₹" + fmtN(v) },
      { k: "price", label: `NAV / price ${fmtDate(DB.meta.as_on)}`, num: true, fmt: v => "₹" + fmtN(v) },
      ...(BRIDGE.quotes ? [{ k: "latest", label: "Latest", num: true, tip: QUOTE_NOTE, fmt: (v, r) => { const q = latestQuote(r.asset_type, r.instrument, r.plan); return q ? `₹${fmtN(q.price)}<span class="sub ${clsNum(q.price - r.price)}">${fmtSPct((q.price / r.price - 1) * 100)} · ${fmtDate(q.date)}</span>` : `<span class="muted small">No quote</span>`; } },
        { k: "lvalue", label: "Value at latest", num: true, tip: QUOTE_NOTE, fmt: (v, r) => r.lpx == null ? `<span class="muted small">—</span>` : `${fmtAmt(v)}<span class="sub ${clsNum(r.lgain)}">${fmtAmt(r.lgain, { sign: true })}</span>` }] : []),
      { k: "cost", label: "Invested", num: true, fmt: v => fmtAmt(v) },
      { k: "value", label: "Value", num: true, fmt: v => `<b>${fmtAmt(v)}</b>` },
      { k: "unrealised", label: "Gain", num: true, fmt: v => `<span class="${clsNum(v)}">${fmtAmt(v, { sign: true })}</span>` },
      { k: "ret", label: "Return", num: true, fmt: v => `<span class="${clsNum(v)}">${fmtSPct(v)}</span>` },
      { k: "x", label: "XIRR", num: true, fmt: v => fmtPct(v, 1), tip: "Annualised money-weighted return for this holding." },
      { k: "first", label: "Since", fmt: v => fmtDate(v) },
      { k: "ltShare", label: "Long-term", num: true, fmt: v => fmtPct(v, 0), tip: `Share of current value in lots held more than ${P.lt_months} months.` },
    ], rows, { search: r => r.name + " " + r.ent + " " + r.instrument, placeholder: "Search holdings", sort: { k: "value", d: "desc" }, noun: "holdings", maxH: 560,
      totals: { name: "Total", cost: fmtAmt(tot("cost")), value: fmtAmt(tot("value")), ...(BRIDGE.quotes ? { lvalue: fmtAmt(rows.reduce((s, r) => s + (r.lvalue ?? r.value), 0)) } : {}), unrealised: fmtAmt(tot("unrealised"), { sign: true }), ret: fmtSPct(tot("unrealised") / tot("cost") * 100) },
      rowAttr: r => r.asset_type === "MF" ? `data-fund="${r.instrument}" data-row="1"` : `data-company="${r.instrument}" data-row="1"` });
  } else if (tab === "txns") {
    body = table("txns", [
      { k: "date", label: "Date", fmt: v => fmtDate(v), sortV: r => r.date },
      { k: "txn_id", label: "Ref", fmt: v => `<span class="mono small">${esc(v)}</span>` },
      { k: "ent", label: "Entity", fmt: v => esc(v) },
      { k: "txn_type", label: "Type", fmt: v => v === "Sell" ? pill("warn", "Sale") : v === "SIP" ? pill("neutral", "SIP") : pill("ok", "Purchase") },
      { k: "name", label: "Instrument", fmt: (v, r) => `${esc(v)}${r.plan ? tag(r.plan) : ""}` },
      { k: "units", label: "Units / qty", num: true, fmt: (v, r) => r.asset_type === "MF" ? fmtN(v, 3) : fmtN(v, 0) },
      { k: "price", label: "Price", num: true, fmt: v => "₹" + fmtN(v, 2) },
      { k: "amount", label: "Amount", num: true, fmt: (v, r) => `<span class="${r.txn_type === "Sell" ? "pos" : ""}">${fmtAmt(v)}</span>` },
    ], tx.map(t => ({ ...t, ent: IX.mem[t.member_id].name, name: t.asset_type === "MF" ? IX.sch[t.instrument].name : (IX.co[t.instrument]?.name || t.instrument) })), { search: r => r.name + " " + r.ent + " " + r.txn_type + " " + r.txn_id, sort: { k: "date", d: "desc" }, noun: "transactions", maxH: 560, limit: 60 });
  } else if (tab === "realised") {
    const rows = R.map(r => ({ ...r, ent: IX.mem[r.member_id].name, name: r.asset_type === "MF" ? IX.sch[r.instrument].name : (IX.co[r.instrument]?.name || r.instrument), ty: r.sell_date >= P.tax_year_start ? P.tax_year_label : "Earlier tax year" }));
    body = `<p class="note">Sales are matched to purchases first-in, first-out. A lot is long-term when it was held for more than ${P.lt_months} months.</p>` + table("realised", [
      { k: "sell_date", label: "Sold", fmt: v => fmtDate(v) }, { k: "ent", label: "Entity", fmt: v => esc(v) }, { k: "name", label: "Instrument", fmt: v => esc(v) },
      { k: "buy_date", label: "Bought", fmt: v => fmtDate(v) }, { k: "units", label: "Units / qty", num: true, fmt: (v, r) => r.asset_type === "MF" ? fmtN(v, 3) : fmtN(v, 0) },
      { k: "proceeds", label: "Proceeds", num: true, fmt: v => fmtAmt(v) }, { k: "cost", label: "Cost", num: true, fmt: v => fmtAmt(v) },
      { k: "gain", label: "Gain", num: true, fmt: v => `<span class="${clsNum(v)}">${fmtAmt(v, { sign: true })}</span>` },
      { k: "term", label: "Term", fmt: v => v === "LT" ? pill("neutral", "Long-term") : pill("neutral", "Short-term") }, { k: "ty", label: "Tax year", fmt: v => esc(v) },
    ], rows, { sort: { k: "sell_date", d: "desc" }, noun: "matched lots" });
  } else {
    const rows = (M === "ALL" ? DB.members : [IX.mem[M]]).map(m => ({ id: m.member_id, name: m.name, type: m.type, ...taxView(m.member_id) }));
    const sum = k => rows.reduce((s, r) => s + r[k], 0);
    body = `<div class="kpis k4">
      ${kpi("Realised gains, " + P.tax_year_label, fmtL(sum("rST") + sum("rLT"), { sign: true }), `Short-term ${fmtL(sum("rST"))} · long-term ${fmtL(sum("rLT"))}`, { cls: "flat" })}
      ${kpi("Unrealised long-term gain", fmtAmt(sum("uLT")), "Lots held beyond " + P.lt_months + " months", { cls: "flat" })}
      ${kpi("Indicative tax if all sold today", fmtL(sum("taxIfSold")), `At ${P.stcg_rate_pct}% short-term and ${P.ltcg_rate_pct}% long-term, before surcharge and 4% cess; ELSS units in lock-in excluded`, { cls: "flat" })}
      ${kpi("Exemption headroom", fmtL(sum("harvest")), `Long-term gains that could be booked tax-free this year: the ₹${nf(P.ltcg_exemption / 1e5, 2)} lakh exemption plus losses already booked`, { cls: "flat", tip: "Long-term gain each entity could realise this tax year without tax: the unused exemption plus any capital losses already booked this year, capped at the gains actually available (exit loads and transaction costs not included)." })}
    </div>` + table("tax", [
      { k: "name", label: state.units === "inr" ? "Entity (₹)" : "Entity (₹ lakh)", fmt: (v, r) => `<span class="nm">${esc(v)}</span><span class="sub">${esc(r.type)}</span>` },
      { k: "rST", label: "Realised ST", num: true, fmt: v => fmtL(v, { sign: true }) }, { k: "rLT", label: "Realised LT", num: true, fmt: v => fmtL(v, { sign: true }) },
      { k: "uST", label: "Unrealised ST", num: true, fmt: v => fmtL(v, { sign: true }) }, { k: "uLT", label: "Unrealised LT", num: true, fmt: v => fmtL(v, { sign: true }) },
      { k: "exemptLeft", label: "Exemption left", num: true, fmt: v => fmtL(v) },
      { k: "harvest", label: "Exemption headroom", num: true, fmt: v => v > 0 ? fmtL(v) : "—", tip: "Long-term gain that could be realised this tax year within the remaining exemption (after mandatory set-off of realised short-term losses; ELSS units in lock-in excluded)." },
      { k: "taxIfSold", label: "Tax if all sold", num: true, fmt: v => fmtL(v) },
    ], rows, { export: true }) + `<p class="note"><b>Indicative only.</b> Uses the rates and exemption in Data &amp; controls → Policy (currently ${P.stcg_rate_pct}% short-term, ${P.ltcg_rate_pct}% long-term above ₹${nf(P.ltcg_exemption, 0)}, long-term after ${P.lt_months} months) for listed equity shares and equity-oriented funds. Short-term losses are set off against long-term gains; long-term losses only against long-term gains. Surcharge, cess, brought-forward losses, the entity's tax status and the applicable provisions of the Income-tax Act, 2025 must be confirmed before advice is given.</p>`;
  }
  return pageHead("Holdings &amp; returns", `${esc(memberName(M))} · every holding built from the transaction ledger with first-in, first-out cost. Direct-equity returns are price-only: dividends received are not in the ledger.`) + `
  <div class="kpis ${BRIDGE.quotes ? "k6" : "k5"}">
    ${kpi(`Current value · ${fmtDate(DB.meta.as_on)}`, fmtAmt(holdings(M).reduce((s, h) => s + h.value, 0)))}
    ${BRIDGE.quotes ? (() => { const L = latestValue(M); return kpi("At latest prices", fmtAmt(L.v), `Gain ${fmtAmt(L.gain, { sign: true })} (${fmtSPct(L.gain / L.cost * 100)} on cost)<br>${latestDates(L, true)}`, { tip: QUOTE_NOTE }); })() : ""}
    ${kpi("Cost of holdings", fmtAmt(holdings(M).reduce((s, h) => s + h.cost, 0)))}
    ${kpi("Unrealised gain", fmtAmt(holdings(M).reduce((s, h) => s + h.unrealised, 0), { sign: true }), "", { vcls: "pos" })}
    ${kpi("XIRR", fmtPct(memberXirr(M) * 100, 2))}
    ${kpi("Regular-plan cost difference", fmtAuto(directSaving(M)) + "<span class='muted small'> /yr</span>", "Before exit load and the capital-gains tax a switch would trigger", { tip: "Regular-plan value × the gap between Direct and Regular NAV returns over the last 12 months (the extra expense ratio actually charged). Exit load and tax on switching are not deducted." })}
  </div>` + card("", tabs("holdings", [["holdings", "Holdings", holdings(M).length], ["txns", "Transactions", tx.length], ["realised", "Realised gains", R.length], ["tax", "Tax view (indicative)"]], tab) + body);
}

function vLookthrough() {
  const M = state.member, lt = lookThrough(M), g = state.ltGroup, P = DB.policy, sch = IX.sch;
  let body = "";
  if (g === "stock") {
    const TM_N = 24, top = lt.rows.slice(0, TM_N), rest = lt.rows.slice(TM_N), mx2 = (top.find(r => r.pct <= P.max_single_stock_pct) || top[0]).pct;
    const restV = rest.reduce((a, r) => a + r.total, 0), restP = rest.reduce((a, r) => a + r.pct, 0);
    body = card("Exposure map", `<div class="row small muted" style="gap:14px;margin:0 0 4px"><span>Box size is look-through exposure. Select a box to open the company.</span><span class="lg"><i style="background:var(--tm-neg)"></i>Above the ${fmtPct(P.max_single_stock_pct, 0)} single-stock limit</span><span class="lg"><i style="background:${tmFill(0.9)}"></i>Stronger blue: larger weight</span>${rest.length ? `<span>Largest ${top.length} stocks shown (${fmtPct(100 - restP, 1)} of equity); the other ${rest.length} are in the table below.</span>` : ""}</div>` + treemap({ items: [...top.map(r => ({ label: shortName(IX.co[r.code]?.name || r.code), value: r.total, pct: r.pct, code: r.code, tip: `<b>${esc(shortName(IX.co[r.code]?.name || r.code))}</b><br>${fmtAmt(r.total)} · ${fmtPct(r.pct, 2)} of equity<br>Direct ${fmtAmt(r.direct)} · through funds ${fmtAmt(r.viaMF)}`, click: "company|" + r.code })),
      ],
      colorFn: r => r.other ? "var(--surface-3)" : r.pct > P.max_single_stock_pct ? "var(--tm-neg)" : tmFill(Math.sqrt(r.pct / mx2)), labelFn: r => [r.label, fmtPct(r.pct, 1)] })) +
      card("All underlying stocks", table("lt", [
        { k: "name", label: "Company", fmt: (v, r) => `<span class="nm">${esc(v)}</span><span class="sub">${esc(r.sector)} · ${r.cap} cap</span>` },
        { k: "direct", label: "Direct", num: true, fmt: v => v ? fmtAmt(v) : "—" },
        { k: "viaMF", label: "Through funds", num: true, fmt: v => v ? fmtAmt(v) : "—" },
        { k: "total", label: "Total", num: true, fmt: v => `<b>${fmtAmt(v)}</b>` },
        { k: "pct", label: "% of equity", num: true, fmt: v => v > P.max_single_stock_pct ? pill("crit", fmtPct(v, 2)) : fmtPct(v, 2) },
        { k: "nf", label: "Funds", num: true, fmt: v => v || "—", tip: "Number of held funds that own the stock." },
        { k: "via", label: "Held through (funds)", cls: () => "wrap", amt: false, fmt: (v, r) => v ? `<span class="small muted" ${tipAttr(r.viaTip)}>${v}</span>` : `<span class="small muted">Direct only</span>`, csv: r => r.viaText },
      ], lt.rows.map(r => { const c = IX.co[r.code] || { name: r.code, sector: "Others", cap: "Unclassified" }, parts = Object.entries(r.contrib).sort((a, b) => b[1] - a[1]); return { ...r, name: c.name, sector: c.sector, cap: c.cap, nf: parts.length, via: parts.slice(0, 2).map(([s]) => esc(compactName(shortName(sch[s].name)))).join(", ") + (parts.length > 2 ? ` <b>+${parts.length - 2}</b>` : ""),
          viaTip: parts.map(([s, v]) => `${esc(shortName(sch[s].name))}: ${fmtAmt(v)}`).join("<br>"), viaText: [r.direct ? "Direct" : null, ...parts.map(([s]) => sch[s].name)].filter(Boolean).join("; ") }; }),
        { search: r => r.name + " " + r.sector + " " + r.code, placeholder: "Search company or sector", sort: { k: "total", d: "desc" }, noun: "stocks", maxH: 620, rowAttr: r => `data-company="${r.code}" data-row="1"` }));
  } else if (g === "sector" || g === "cap" || g === "industry") {
    const field = g, rows = groupBy(lt, field), bench = IX.idxW.BENCH ? benchWeights(field) : null;
    body = card(`Exposure by ${field === "cap" ? "market cap" : field}`, `<div class="legend"><span><i class="sw" style="background:var(--s1)"></i>Family</span>${bench ? `<span><i class="sw" style="background:var(--bench)"></i>${esc(benchLabel())}</span>` : ""}</div>` +
      barH({ rows: rows.slice(0, 16).map(r => ({ label: r.key, segs: [{ v: r.pct, color: "var(--s1)", name: "Family" }], tip: bench ? `Benchmark ${fmtPct(bench[r.key] || 0)}` : "" })), fmt: v => fmtPct(v, 1), limit: field === "sector" ? P.max_sector_pct : null, limitLabel: `sector limit ${P.max_sector_pct}%`, labelW: 200, W: CW.full }) +
      table("ltg", [
        { k: "key", label: field === "cap" ? "Market cap" : field === "sector" ? "Sector" : "Industry", fmt: v => `<span class="nm">${esc(v)}</span>` },
        { k: "v", label: "Exposure", num: true, fmt: v => fmtAmt(v) }, { k: "pct", label: "% of equity", num: true, fmt: v => fmtPct(v, 2) },
        ...(bench ? [{ k: "b", label: "Benchmark", num: true, fmt: v => fmtPct(v, 2) }, { k: "aw", label: "Active weight", num: true, fmt: v => `<span class="${clsNum(v)}">${fmtSPct(v, 2)}</span>`, tip: "Family weight minus benchmark weight, in percentage points." }] : []),
        { k: "n", label: "Stocks", num: true },
      ], rows.map(r => ({ ...r, b: bench ? bench[r.key] || 0 : null, aw: bench ? r.pct - (bench[r.key] || 0) : null, n: lt.rows.filter(x => coField(x.code, field) === r.key).length })), { sort: { k: "v", d: "desc" }, dense: true }));
  } else {
    const top = lt.rows.slice(0, 20), mems = DB.members, mx = Math.max(...top.flatMap(r => mems.map(m => r.members[m.member_id] || 0)));
    body = card("Who holds what", `<p class="muted small" style="margin:0">Top 20 look-through exposures split by entity, including each entity's share through its own funds. Darker cells are larger amounts.</p>
      <div class="tbl-wrap"><table class="tbl heat"><thead><tr><th><span class="th">Company</span></th>${mems.map(m => `<th class="num"><span class="th" style="justify-content:flex-end">${esc(m.name.replace("Mehta Family Investments LLP", "Family LLP"))}</span></th>`).join("")}<th class="num"><span class="th" style="justify-content:flex-end">Total</span></th></tr></thead><tbody>
      ${top.map(r => `<tr><td><span class="nm">${esc(shortName(IX.co[r.code]?.name || r.code))}</span></td>${mems.map(m => { const v = r.members[m.member_id] || 0, t = v / mx; return `<td class="num cell-heat" style="background:${v ? seqFill(t) : "transparent"};color:${v ? seqInk(t) : "var(--ink)"}" ${tipAttr(`${esc(m.name)} · ${esc(IX.co[r.code]?.name || r.code)}: ${fmtAmt(v)}`)}>${v ? amtTick(v) : "—"}</td>`; }).join("")}<td class="num"><b>${fmtAmt(r.total)}</b></td></tr>`).join("")}
      </tbody></table></div><p class="muted small" style="margin:0">Cells in ${unitLabel()}.</p>`);
  }
  return pageHead("Look-through exposure", "Direct shares plus each fund's disclosed holdings in proportion to the family's units. " + basisLine(state.member), seg("ltGroup", [["stock", "By stock"], ["sector", "By sector"], ["industry", "By industry"], ["cap", "By market cap"], ["entity", "By entity"]], g, { label: "Group by" })) + holdingsLagNote(state.member) + `
  <div class="kpis k5">
    ${kpi("Look-through equity", fmtAmt(lt.eq), `${lt.rows.length} stocks`)}
    ${kpi("Held directly", fmtAmt(lt.directTotal), fmtPct(lt.directTotal / lt.eq * 100) + " of equity")}
    ${kpi("Held through funds", fmtAmt(lt.eq - lt.directTotal), fmtPct((lt.eq - lt.directTotal) / lt.eq * 100) + " of equity")}
    ${kpi(lt.unmapped ? "Not looked through" : "Debt & cash inside funds", fmtAmt(lt.unmapped || lt.debt + lt.cash), lt.unmapped ? `${lt.unmappedSchemes.length} funds lack a portfolio file` : `Debt ${fmtAmt(lt.debt)} · cash & other ${fmtAmt(lt.cash)}`)}
    ${kpi("Largest stock", fmtPct(lt.rows[0].pct, 2), esc(IX.co[lt.rows[0].code]?.name || lt.rows[0].code), { vcls: lt.rows[0].pct > P.max_single_stock_pct ? "neg" : "" })}
  </div>` + body;
}

function vAllocation() {
  const M = state.member, P = DB.policy, al = allocation(M), lt = lookThrough(M), H = holdings(M);
  const lowCov = al.coverage < ALLOC_MIN_COVERAGE;
  const acts = lowCov
    ? `<p class="note" style="margin:0"><b>Gaps withheld.</b> The market-cap class is known for only ${fmtPct(al.coverage)} of look-through equity; ${fmtPct(al.other)} (${al.parts.map(x => `${esc(x.key)} ${fmtPct(x.pct)}`).join(", ")}) is mostly smaller companies held inside funds that have no market-cap data here. Any drift or amount shown would come from the missing data, so none is given until coverage reaches ${ALLOC_MIN_COVERAGE}%.</p>`
    : al.filter(a => a.status !== "ok").map(a => `<div class="stack" style="gap:4px;padding:10px 0;border-bottom:1px solid var(--line)"><div class="row" style="justify-content:space-between"><b>${a.key} cap: ${a.move > 0 ? "below" : "above"} target by ${fmtAmt(Math.abs(a.move))}</b>${pill(a.status, a.status === "crit" ? "Outside band" : "Near band edge")}</div><span class="muted small">Actual ${fmtPct(a.actual)} vs target ${fmtPct(a.target)}. For committee discussion; the route (which holdings or funds) is a committee decision.</span></div>`).join("");
  const byM = DB.members.filter(m => holdings(m.member_id).length).map(m => { const a = allocation(m.member_id), l = lookThrough(m.member_id); return { name: m.name, eq: l.eq, large: a[0].actual, mid: a[1].actual, small: a[2].actual, debt: (l.debt + l.cash) / l.total * 100, drift: a.coverage < ALLOC_MIN_COVERAGE ? null : Math.max(...a.map(x => Math.abs(x.drift))) }; });
  const mfShare = H.filter(h => h.asset_type === "MF").reduce((s, h) => s + h.value, 0) / H.reduce((s, h) => s + h.value, 0) * 100;
  return pageHead("Allocation &amp; rebalancing", `Market-cap mix of the look-through equity book against the family's targets (tolerance ±${P.band_pct} points). Targets are editable in Data &amp; controls.`) + `
  <div class="grid g21">
    ${card("Market-cap mix against target", `<p class="muted small" style="margin:0 0 8px">Market-cap class known for <b>${fmtPct(al.coverage)}</b> of look-through equity.${al.parts.length ? " Not classified: " + al.parts.map(x => `${esc(x.key)} ${fmtPct(x.pct)} (${fmtAmt(x.amt)})`).join(", ") + "." : ""}</p>` + al.map(a => `<div class="stack" style="gap:6px"><div class="row" style="justify-content:space-between"><b>${a.key} cap</b><span class="small">${pill(a.status, `Actual ${fmtPct(a.actual)} · target ${fmtPct(a.target)}`)}</span></div>
      <div class="band-bar" ${tipAttr(`Target band ${fmtPct(a.target - P.band_pct)}–${fmtPct(a.target + P.band_pct)}`)}><div class="band" style="left:${Math.max(0, a.target - P.band_pct)}%;width:${2 * P.band_pct}%"></div><div class="act" style="width:${a.actual}%"></div><div class="tgt" style="left:${a.target}%"></div></div>
      <div class="row small muted" style="justify-content:space-between"><span>${a.move == null ? "Drift withheld (coverage too low)" : "Drift " + fmtSPct(a.drift).replace("%", " pts")}</span><span>${a.move == null ? "" : (a.move > 0 ? "Below" : "Above") + " target by " + fmtAmt(Math.abs(a.move))}</span></div></div>`).join("") + `<div class="legend"><span><i class="sw" style="background:var(--s1)"></i>Actual</span><span><i class="sw" style="background:var(--ink);width:3px"></i>Target</span><span><i class="sw" style="background:color-mix(in srgb,var(--good) 25%,transparent)"></i>Tolerance band</span></div>`)}
    ${card("Gap to target", acts || `<p class="muted" style="margin:0">All buckets are within the tolerance band.</p>`, { sub: lowCov ? "Withheld: market-cap coverage too low." : "Amount that would bring each bucket back to its exact target. Not a recommendation." })}
  </div>
  <div class="grid g2">
    ${card("Asset mix", `<div class="grid g3" style="gap:10px">${kpi("Equity (look-through)", fmtPct(lt.eq / lt.total * 100), fmtAmt(lt.eq), { cls: "flat" })}${kpi("Debt & cash in funds", fmtPct((lt.debt + lt.cash) / lt.total * 100), fmtAmt(lt.debt + lt.cash), { cls: "flat" })}${kpi("Not looked through", fmtPct(lt.unmapped / lt.total * 100), fmtAmt(lt.unmapped), { cls: "flat" })}</div><div class="grid g2" style="gap:10px;margin-top:10px">${kpi("Held through mutual funds", fmtPct(mfShare), "of portfolio value", { cls: "flat" })}${kpi("Held directly", fmtPct(100 - mfShare), "of portfolio value", { cls: "flat" })}</div>`)}
    ${card("Mix by entity", table("allocm", [
      { k: "name", label: "Entity", fmt: v => `<span class="nm">${esc(v)}</span>` },
      { k: "large", label: "Large", num: true, fmt: v => fmtPct(v) }, { k: "mid", label: "Mid", num: true, fmt: v => fmtPct(v) }, { k: "small", label: "Small", num: true, fmt: v => fmtPct(v) },
      { k: "drift", label: "Max drift", num: true, fmt: v => v > P.band_pct ? pill("crit", fmtPct(v)) : fmtPct(v) },
    ], byM, { dense: true }))}
  </div>`;
}
