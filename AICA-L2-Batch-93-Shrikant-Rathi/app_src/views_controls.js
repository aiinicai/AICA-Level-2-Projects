/* ==================================================================
   Controls: data & reconciliation, methodology, family report
   ================================================================== */
function isinValid(s) {
  if (!/^[A-Z]{2}[A-Z0-9]{9}[0-9]$/.test(s || "")) return false;
  const digits = s.slice(0, 11).split("").map(ch => parseInt(ch, 36)).join("");
  let tot = 0; digits.split("").reverse().forEach((d, i) => { let n = +d; if (i % 2 === 0) { n *= 2; if (n > 9) n -= 9; } tot += n; });
  return (10 - tot % 10) % 10 === +s[11];
}
function reconciliation() {
  const out = [], add = (t, ok, d, sev = "fail") => out.push({ t, s: ok ? "ok" : sev, d });
  const AS = DB.meta.as_on;
  const off = [];
  DB.schemes.forEach(s => (IX.portDates[s.scheme_id] || []).forEach(d => { const w = IX.portBy[s.scheme_id][d].reduce((a, p) => a + p.w, 0); if (w > 101.5 || w < 40) off.push(`${s.scheme_id}@${fmtMon(d)} ${fmtPct(w)}`); }));
  add("Scheme equity weights plausible (40–101.5% of NAV)", !off.length, off.length ? "Check " + off.join(", ") : `${Object.values(IX.portDates).reduce((a, x) => a + x.length, 0)} portfolio disclosures within range`);
  const noPort = DB.schemes.filter(s => heldSchemes().includes(s.scheme_id) && !latestPort()[s.scheme_id]);
  add("Every held scheme has a portfolio file", !noPort.length, noPort.length ? `Missing: ${noPort.map(s => s.name).join(", ")}` : "All held schemes looked through", "warn");
  const hb = holdingsBasis();
  add("Fund holdings are for the valuation month", !hb.behind.length, hb.behind.length ? `${hb.behind.length} of ${hb.held.length} held funds on an earlier disclosure: ${hb.behind.map(s => `${IX.sch[s].name} (${fmtDate(portOf(s).date)})`).join(", ")}. Expected until the AMCs publish (within about 10 days of month-end).` : hb.latest ? `All ${hb.held.length} held funds disclosed for ${fmtMon(AS)}` : "No portfolio files yet", "warn");
  const stalePort = DB.schemes.filter(s => s.portfolio_date && daysBetween(s.portfolio_date, AS) > 45);
  add("Portfolio files are recent (≤ 45 days before valuation date)", !stalePort.length, stalePort.length ? stalePort.map(s => `${s.name} (${fmtDate(s.portfolio_date)})`).join(", ") : "All current", "warn");
  const badMap = DB.transactions.filter(t => !IX.mem[t.member_id] || (t.asset_type === "MF" ? !IX.nav[t.instrument + "|" + t.plan] : !IX.px[t.instrument]));
  add("Transactions map to entity and priced instrument", !badMap.length, badMap.length ? `${badMap.length} unmapped: ${badMap.slice(0, 3).map(t => t.txn_id).join(", ")}` : `${DB.transactions.length} transactions mapped`);
  const orphan = [...DB.scheme_portfolios, ...DB.index_constituents].filter(r => !IX.co[r.code]);
  add("Portfolio securities map to the security master", !orphan.length, orphan.length ? `${orphan.length} unknown codes` : "All codes found");
  const withIsin = DB.companies.filter(c => c.isin), badIsin = withIsin.filter(c => !isinValid(c.isin));
  add("ISIN check digits valid (ISO 6166)", !badIsin.length, badIsin.length ? badIsin.map(c => c.code).slice(0, 8).join(", ") : `${withIsin.length} ISINs verified`, "warn");
  const noIsin = DB.companies.filter(c => c.in_universe && !c.isin);
  add("Research universe has ISINs (NSE list)", !noIsin.length, noIsin.length ? noIsin.map(c => c.code).join(", ") : "All matched to the NSE equity list", "warn");
  const badAmt = DB.transactions.filter(t => Math.abs(t.units * t.price - t.amount) > 1);
  add("Transaction amount = units × price", !badAmt.length, badAmt.length ? `${badAmt.length} rows differ by more than ₹1` : "All rows agree within ₹1", "warn");
  const units = {}, over = [];
  [...DB.transactions].sort((a, b) => a.date.localeCompare(b.date)).forEach(t => { const k = [t.member_id, t.instrument, t.plan].join("|"); units[k] = (units[k] || 0) + (t.txn_type === "Sell" ? -t.units : +t.units); if (units[k] < -1e-6) over.push(t.txn_id); });
  add("No sale exceeds units held", !over.length, over.length ? `Oversold: ${over.join(", ")}` : "Every sale covered by earlier purchases");
  const fut = DB.transactions.filter(t => t.date > AS);
  add("No transactions after the valuation date", !fut.length, fut.length ? `${fut.length} future-dated` : `All on or before ${fmtDate(AS)}`);
  const ids = new Set(), dup = DB.transactions.filter(t => ids.has(t.txn_id) || !ids.add(t.txn_id));
  add("Transaction references unique", !dup.length, dup.length ? `${dup.length} duplicates` : "No duplicates");
  const noPx = holdings().filter(h => h.asset_type === "EQ" && !isNum(curPrice("EQ", h.instrument, ""))).length + DB.transactions.filter(t => t.asset_type === "MF" && !isNum(curPrice("MF", t.instrument, t.plan))).length;
  add("Every holding has a price or NAV on the valuation date", !noPx, noPx ? `${noPx} holdings unpriced` : `Priced as on ${fmtDate(AS)}`);
  const lt = lookThrough("ALL"), cov = lt.eq ? lt.rows.filter(r => IX.px[r.code]).reduce((s, r) => s + r.total, 0) / lt.eq * 100 : 0;
  add("Look-through equity with its own price history", cov >= 90, `${fmtPct(cov)} of look-through equity (others assumed to move with the market in stress tests)`, "warn");
  const finBad = DB.financials.filter(f => isNum(f.pat) && isNum(f.revenue) && f.revenue > 0 && Math.abs(f.pat) > 2 * f.revenue);
  add("Financial statements pass arithmetic checks", !finBad.length, finBad.length ? `${finBad.length} company-years need review` : `${DB.financials.length} company-years checked`, "warn");
  const absurd = DB.companies.filter(c => { const r = ratios(c.code); return r && ((isNum(r.pe) && r.pe > 300) || (isNum(r.pb) && r.pb > 100)); });
  add("Valuation ratios in a plausible range (P/E ≤ 300×, P/B ≤ 100×)", !absurd.length, absurd.length ? `Check units or currency: ${absurd.map(c => c.code).join(", ")}` : "No company outside the range (a currency or unit error shows up here)");
  const capCov = 100 - (allocation("ALL").other || 0);
  add(`Market-cap class known for ≥ ${ALLOC_MIN_COVERAGE}% of look-through equity`, capCov >= ALLOC_MIN_COVERAGE, `${fmtPct(capCov)} classified; allocation gaps are withheld below ${ALLOC_MIN_COVERAGE}%`, "warn");
  const diff = lt.eq + lt.debt + lt.cash + lt.unmapped - lt.mfTotal - lt.directTotal;
  add("Look-through equity + fund debt + fund cash & other + not looked through = MF + direct", Math.abs(diff) < 1, `Difference ₹${Math.abs(diff) < 0.005 ? "0.00" : diff.toFixed(2)}`);
  const negRes = DB.schemes.filter(s => latestPort()[s.scheme_id] && latestPort()[s.scheme_id].reduce((a, p) => a + p.w, 0) + (s.debt_pct || 0) > 101.5);
  add("Fund equity + debt do not exceed 100% of NAV", !negRes.length, negRes.length ? negRes.map(s => s.name).join(", ") + " (check for derivatives or a mis-read column)" : "Cash & other residual is non-negative for every scheme", "warn");
  return out;
}
const TABLE_DEFS = {
  transactions: ["Transactions", ["txn_id", "date", "member_id", "asset_type", "instrument", "plan", "txn_type", "units", "price", "amount"]],
  scheme_portfolios: ["Scheme portfolios", ["portfolio_date", "scheme_id", "code", "weight_pct"]],
  nav_history: ["NAV history", ["date", "scheme_id", "plan", "nav"]],
  prices: ["Stock prices", ["date", "code", "close"]],
  schemes: ["Scheme master", ["scheme_id", "name", "amc", "category", "benchmark"]],
  companies: ["Security master", ["code", "isin", "name", "sector", "cap"]],
  financials: ["Financials", ["code", "fy", "revenue", "pat", "net_worth", "total_assets"]],
  members: ["Entities", ["member_id", "name", "type"]],
  indices: ["Benchmark indices", ["date", "index_code", "index_name", "level"]],
  index_constituents: ["Index weights", ["index_code", "code", "weight_pct"]],
};
const POLICY_FIELDS = [
  ["Concentration limits", [["max_single_stock_pct", "Single stock, % of equity"], ["max_sector_pct", "Single sector, % of equity"], ["max_top10_pct", "Top 10 stocks, % of equity"], ["max_hhi", "HHI ceiling"], ["max_pair_overlap_pct", "Overlap between held funds, %"], ["max_pledge_pct", "Promoter pledge, %"]]],
  ["Allocation targets", [["target_large_pct", "Large cap target, %"], ["target_mid_pct", "Mid cap target, %"], ["target_small_pct", "Small cap target, %"], ["band_pct", "Tolerance band, ± points"], ["large_cap_min_cr", "Large cap from, ₹ Cr market cap"], ["mid_cap_min_cr", "Mid cap from, ₹ Cr market cap"]]],
  ["Risk and cost", [["max_portfolio_beta", "Maximum equity beta"], ["max_weighted_ter_pct", "Maximum weighted TER, %"], ["risk_free_pct", "Risk-free rate, %"]]],
  ["Tax assumptions (indicative)", [["stcg_rate_pct", "Short-term rate, %"], ["ltcg_rate_pct", "Long-term rate, %"], ["ltcg_exemption", "Long-term exemption, ₹"], ["lt_months", "Long-term after, months"]]],
];
function vData() {
  const tab = state.tab.data || "live", rc = hasData() ? reconciliation() : [], fails = rc.filter(r => r.s !== "ok").length;
  let body = "";
  if (tab === "live") body = liveDataPanel();
  else if (tab === "entities") body = entitiesTab();
  else if (tab === "schemes") body = schemesTab();
  else if (tab === "securities") body = securitiesTab();
  else if (tab === "txns") body = transactionsTab();
  else if (tab === "users") body = usersTab();
  else if (tab === "audit" && BRIDGE.live) body = auditTabLive();
  else if (tab === "recon") body = table("recon", [{ k: "t", label: "Control", fmt: v => `<span class="nm">${esc(v)}</span>` }, { k: "s", label: "Result", fmt: v => pill(v === "ok" ? "ok" : v === "warn" ? "warn" : "crit", v === "ok" ? "Pass" : v === "warn" ? "Review" : "Fail") }, { k: "d", label: "Detail", cls: () => "wrap", fmt: v => `<span class="muted">${esc(v)}</span>` }], rc, { export: true });
  else if (tab === "import") body = `<p class="note">Replace any table with your own CSV for <b>what-if analysis in this session only</b>: nothing here is saved, and reloading the page restores the data. To record entities and transactions permanently, use the <b>Entities</b> and <b>Transactions</b> tabs (signed in through the data bridge). Column names must match; download the current table as a template. Files are read in this browser and are not uploaded. Reconciliation reruns after every import.</p>
    <div class="grid g3">${Object.entries(TABLE_DEFS).map(([k, [l, cols]]) => `<div class="field"><b>${l}</b><span class="src mono" ${tipAttr(esc(cols.join(", ")))}>${esc(cols.join(", "))}</span><input type="file" accept=".csv,text/csv" data-import="${k}" id="imp_${k}" aria-label="Import ${l}"><div class="row"><button class="btn sm" data-export-db="${k}">${ICON.download} Current</button><span class="muted small">${DB[k].length.toLocaleString("en-IN")} rows</span></div></div>`).join("")}</div>
    <div class="row"><button class="btn" id="resetSample">Discard imports and changes (reload snapshot)</button></div>`;
  else if (tab === "policy") body = `<div class="grid g2">${POLICY_FIELDS.map(([g, fs]) => `<div class="stack"><h3 style="margin:0;font-size:13.5px">${g}</h3><div class="fieldgrid">${fs.map(([k, l]) => `<label class="field" for="pol_${k}"><span class="k">${l}</span><input type="number" step="any" id="pol_${k}" value="${DB.policy[k]}"></label>`).join("")}</div></div>`).join("")}</div>
    <div class="row"><button class="btn primary" id="savePolicy">Apply limits</button><span class="muted small">Applies to every screen immediately and is written to the audit trail.</span></div>`;
  else body = table("audit", [{ k: "ts", label: "Time (UTC)", fmt: v => `<span class="mono small">${esc(v.replace("T", " ").slice(0, 19))}</span>` }, { k: "action", label: "Action", fmt: v => tag(v) }, { k: "detail", label: "Detail", cls: () => "wrap", fmt: v => esc(v) }], AUDIT, { sort: { k: "ts", d: "desc" }, empty: "No entries yet." });
  return pageHead("Data &amp; controls", "Fetch live data, reconcile it before relying on it, maintain the investment policy, and keep an audit trail of every change.") + `
  <div class="kpis k4">
    ${kpi("Controls passed", `${rc.length - fails} / ${rc.length}`, fails ? `${fails} need attention` : "All controls pass", { vcls: fails ? "neg" : "pos" })}
    ${kpi("Transactions", DB.transactions.length.toLocaleString("en-IN"), `${DB.members.length} entities`)}
    ${kpi("Market data", `${DB.companies.filter(c => c.in_universe || IX.fin[c.code]).length} · ${DB.schemes.length}`, `researched companies · funds · ${DB.companies.length} securities in total`)}
    ${kpi("Valuation date", DB.meta.as_on ? fmtDate(DB.meta.as_on) : "—", BRIDGE.live ? "Live · bridge connected" : "Snapshot")}
  </div>` + card("", tabs("data", [["entities", "Entities", DB.members.length], ["schemes", "Schemes", DB.schemes.length], ["securities", "Securities", DB.companies.length], ["txns", "Transactions", DB.transactions.length], ["live", "Live data"], ["recon", "Reconciliation", rc.length],
    ["import", "Import & export"], ["policy", "Investment policy"], ["audit", "Audit trail", BRIDGE.live ? (ENTRY.audit || []).length : AUDIT.length], ...(isAdmin() ? [["users", "Users"]] : [])], tab) + body);
}
function importCSV(kind, text, fname) {
  const rows = parseCSV(text), need = TABLE_DEFS[kind][1], miss = need.filter(k => !rows.length || !(k in rows[0]));
  if (!rows.length || miss.length) { toast(`Import stopped: ${fname} is missing ${miss.join(", ") || "rows"}.`, "warn"); log("IMPORT_REJECTED", `${kind} ← ${fname}: missing ${miss.join(", ")}`); return; }
  const numeric = { transactions: ["units", "price", "amount"], scheme_portfolios: ["weight_pct"], nav_history: ["nav"], prices: ["close"] }[kind] || [];
  const bad = rows.filter(r => numeric.some(k => typeof r[k] !== "number" || r[k] < 0));
  if (bad.length) { toast(`Import stopped: ${bad.length} rows have blank or negative amounts.`, "warn"); log("IMPORT_REJECTED", `${kind} ← ${fname}: ${bad.length} bad rows`); return; }
  const backup = DB[kind]; DB[kind] = rows;
  try { reindex(); reconciliation(); } catch (e) { DB[kind] = backup; reindex(); toast(`Import rolled back: ${e.message}`, "warn"); log("IMPORT_ROLLBACK", `${kind} ← ${fname}: ${e.message}`); return; }
  log("IMPORT", `${kind} ← ${fname} (${rows.length} rows)`);
  const f = reconciliation().filter(r => r.s === "fail").length;
  toast(f ? `Imported ${rows.length} rows. ${f} controls fail; review before use.` : `Imported ${rows.length} rows. All controls pass.`, f ? "warn" : "ok");
  render();
}

function vMethod() {
  const P = DB.policy, sec = (t, items) => card(t, items.map(([h, f, d]) => `<div class="stack" style="gap:6px"><b>${h}</b>${f ? `<div class="formula">${esc(f)}</div>` : ""}<p class="muted small" style="margin:0">${d}</p></div>`).join(""));
  return pageHead("Methodology", "Every figure in LookThrough, how it is calculated, and where the data comes from. All formulas are independently recomputed in Python (verify/recompute.py) and reconciled.") + `
  <div class="grid g2">
    ${sec("Holdings and returns", [
      ["Cost and gains (FIFO)", "Sale units are matched to the oldest purchase lots first\nUnrealised gain = Σ lots units × (price today − lot price)", `A lot is long-term when held more than ${P.lt_months} months (purchase date + ${P.lt_months} months &lt; valuation date).`],
      ["Two price bases", "Valuation date: month-end prices and NAVs\nAt latest prices: units × latest price (shares) or latest NAV (funds)", `Returns, XIRR, risk, benchmarks and the reconciliation use the month-end valuation date, so every figure can be reproduced. With the Data Bridge running, value, gain and the concentration limits are also shown at the latest prices: shares from Yahoo Finance (NSE, about 15 minutes delayed in market hours, the last close otherwise) and NAVs as last published by AMFI (once each business day). Each fund's latest value is spread over its last disclosed holdings; the weights are not re-drifted for price moves since that date. Every such figure names its price and NAV dates; a holding without a quote stays at its valuation-date price and is counted. The offline file has no latest prices.`],
      ["XIRR", "Σ CFᵢ ÷ (1 + r)^((dᵢ − d₀)/365) = 0", "Purchases and SIPs are outflows, sales are inflows, and today's value is the final inflow. Solved by Newton–Raphson with a bisection fallback."],
      ["Indicative tax", "Tax = STCG × short-term rate + max(0, LTCG − exemption) × long-term rate", "Short-term losses set off against long-term gains. Rates and exemption are editable. Not a computation of tax liability."],
    ])}
    ${sec("Look-through and concentration", [
      ["Look-through exposure", "Exposure(s) = Direct(s) + Σ_k MF value(k) × weight(k, s) ÷ 100", "Weight is the stock's % of net assets in the scheme's latest monthly portfolio disclosure (AMC file). Debt, REITs and other non-equity lines, and cash, are tracked separately. Funds without a file are shown as not looked through."],
      ["Herfindahl-Hirschman Index", "HHI = Σ wᵢ²      Effective N = 1 ÷ HHI", "wᵢ is each stock's share of look-through equity."],
      ["Fund overlap", "Overlap(A, B) = Σ over common stocks of min(w_A, w_B)", "0% means no common stock; 100% means identical portfolios."],
      ["Concentration headroom", "(Current + H) ÷ (Equity + H) = L   ⇒   H = (L × Equity − Current) ÷ (1 − L)", "The amount that can be bought before a stock reaches the single-stock limit L."],
    ])}
    ${sec("Fund performance and risk", [
      ["Returns", "CAGR 3Y = (NAV_t ÷ NAV_t−36)^(1/3) − 1", "Month-end Direct-plan NAVs from AMFI. Benchmarks are price indices from Yahoo Finance, which exclude dividends, so funds carry a small built-in advantage (roughly the index dividend yield)."],
      ["Regular-plan cost gap", "Gap = (Direct NAV_t ÷ Direct NAV_t−12) ÷ (Regular NAV_t ÷ Regular NAV_t−12) − 1", "Both plans hold the same portfolio, so the difference in their returns is the extra expense ratio charged to Regular-plan investors."],
      ["Risk", "Volatility = σ(monthly returns) × √12\nSharpe = (CAGR − Rf) ÷ volatility\nSortino = (CAGR − Rf) ÷ downside deviation", `Rf = ${fmtPct(P.risk_free_pct)}. Downside deviation uses months below the monthly risk-free rate.`],
      ["Benchmark-relative", "β = cov(r_f, r_b) ÷ var(r_b)\nAlpha = CAGR − [Rf + β(CAGR_b − Rf)]\nTracking error = σ(r_f − r_b) × √12\nInformation ratio = (CAGR − CAGR_b) ÷ TE", "Up/down capture compares average returns in months when the benchmark rose or fell."],
      ["Maximum drawdown", "MDD = max_t (1 − NAV_t ÷ max NAV up to t)", "Measured on month-end values, so intra-month falls are understated."],
    ])}
    ${sec("Company analysis", [
      ["Returns on capital", "ROE = PAT ÷ average net worth\nROCE = (PBT + finance costs) ÷ average (net worth + borrowings)\nROA = PAT ÷ average total assets", "Averages use opening and closing balances."],
      ["DuPont", "ROE = (PAT ÷ revenue) × (revenue ÷ avg assets) × (avg assets ÷ avg equity)", "Splits ROE into margin, efficiency and leverage."],
      ["Valuation", "P/E = price ÷ (PAT ÷ shares)   EV/EBITDA = (market cap + debt − cash) ÷ EBITDA", "Compared with the median of sector peers in the database."],
      ["Piotroski F-score", "9 binary tests: ROA > 0, CFO > 0, ΔROA > 0, CFO > PAT, Δleverage ≤ 0, Δcurrent ratio > 0, no dilution, Δmargin > 0, Δasset turnover > 0", "EBITDA margin is used in place of gross margin. Scored only when at least 7 tests have data. Not applied to financial companies."],
      ["Market-cap class", `Large ≥ ₹${nf(P.large_cap_min_cr, 0)} Cr · Mid ≥ ₹${nf(P.mid_cap_min_cr, 0)} Cr · otherwise Small`, "Thresholds approximate AMFI's half-yearly rank-based list (top 100 large, 101–250 mid). Update them in the investment policy when AMFI publishes a new list."],
      ["Screening rule", "Headroom ≤ 0 → Policy limit breached;  Weak → Fails screen;  Strong & valuation ≤ 1.15× sector median → Passes screen;  Strong & above peers → Passes screen · valuation above peers;  else Mixed result. Screening output for committee review, not a recommendation.", "Score bands: Strong ≥ 80% of tests, Adequate 60–79%, Weak below 60%. Lenders use asset-quality and capital tests instead of debt tests."],
    ])}
    ${sec("Stress tests", [
      ["Market scenario", "Loss = Σ exposureᵢ × βᵢ × market move", "βᵢ is each stock's 36-month beta against the Nifty 500 (price index). Stocks without price history use β = 1."],
      ["Sector, stock and custom scenarios", "Loss = Σ exposureᵢ × shockᵢ", "Custom combines a beta-adjusted market move with an extra sector move."],
      ["Historical replay", "Loss = Σ exposureᵢ × (Price_end ÷ Price_start − 1)", "Applies each stock's actual move over a past window to today's holdings."],
    ])}
    ${card("Data sources", table("msources", [{ k: "t", label: "Data" }, { k: "s", label: "Source", cls: () => "wrap" }, { k: "f", label: "Frequency", cls: () => "wrap" }], [
      { t: "Scheme codes and NAVs", s: "AMFI NAVAll.txt (scheme codes); NAV history from api.mfapi.in, a public mirror of AMFI data", f: "Daily → month-end" },
      { t: "Scheme portfolios", s: "Monthly portfolio disclosures published by each AMC (Excel files added by the user)", f: "Monthly" },
      { t: "Share prices, indices", s: "Yahoo Finance through the open-source yfinance library (unofficial; split-adjusted closes)", f: "Daily → month-end" },
      { t: "Financial statements", s: "Yahoo Finance annual statements (usually 4 years); AI extraction for other figures", f: "Annual" },
      { t: "Audited figures where Yahoo is wrong", s: `The company's own audited filing, replacing the Yahoo line item (${DB.companies.filter(c => c.fin_official).map(c => c.name).join(", ") || "none at present"}); marked † on the company's Financials tab with a link to the filing`, f: "Annual" },
      { t: "ISIN ↔ symbol", s: "NSE equity list (EQUITY_L.csv)", f: "Weekly" },
      { t: "Family holdings", s: "Dummy family and transactions, priced at the real NAVs and prices above", f: "—" },
    ], { export: false, dense: true }) + `<p class="note"><b>Real market data, dummy family.</b> Company, fund and market figures are real and fetched from the sources above as on the valuation date. The family, its entities and transactions are fictitious. Yahoo data is unofficial: verify figures used for advice against exchange filings.</p>`)}
  </div>`;
}

function vReport() {
  const M = state.member, H = holdings(M), lt = lookThrough(M), con = concentration(lt), al = alerts(M), value = H.reduce((s, h) => s + h.value, 0), cost = H.reduce((s, h) => s + h.cost, 0);
  const tv = M === "ALL" ? DB.members.map(m => taxView(m.member_id)) : [taxView(M)], ts = k => tv.reduce((s, x) => s + x[k], 0);
  return `<div class="ph noprint"><div><h1>Family report</h1><p>A one-page summary for the family, ready to print or save as PDF.</p></div><div class="acts">${inFrame ? `<span class="muted small">Printing is available in the offline file.</span>` : `<button class="btn primary" id="printBtn">${ICON.report} Print / save PDF</button>`}</div></div>
  <article class="report">
    <div class="rh"><div><div class="small muted">Portfolio review · ${esc(memberName(M))}</div><h1>Mehta Family Office</h1></div><div class="small muted" style="text-align:right">Valuation date ${fmtDate(DB.meta.as_on)}${holdingsBasis(M).latest ? `<br>Fund holdings ${holdingsBasis(M).oldest === holdingsBasis(M).latest ? fmtDate(holdingsBasis(M).latest) : `${fmtDate(holdingsBasis(M).oldest)} to ${fmtDate(holdingsBasis(M).latest)}`}` : ""}<br>Prepared with LookThrough · real market data, dummy family</div></div>
    <div class="kpis k4">${kpi("Portfolio value", fmtCr(value), `Cost ${fmtCr(cost)}`, { cls: "flat" })}${kpi("Unrealised gain", fmtCr(value - cost), fmtSPct((value - cost) / cost * 100), { cls: "flat" })}${kpi("XIRR", fmtPct(memberXirr(M) * 100, 2), "Since first investment", { cls: "flat" })}${kpi("Policy", `${al.filter(a => a.sev === "crit").length} breaches`, `${al.filter(a => a.sev === "warn").length} warnings`, { cls: "flat" })}</div>
    ${holdingsLagNote(M)}${BRIDGE.quotes ? (() => { const L = latestValue(M), t = limitTests(lookThroughLatest(M)), st = t.find(x => x.k === "stock"), se = t.find(x => x.k === "sector"); return `<p class="note"><b>At latest prices</b> (${latestDates(L)}): value ${fmtCr(L.v)} (${fmtSPct((L.v / value - 1) * 100)} since ${fmtDate(DB.meta.as_on)}), unrealised gain ${fmtCr(L.gain)}.${st ? ` Largest single stock ${esc(st.who)} ${st.f(st.v)} (limit ${st.f(st.lim)}); largest sector ${esc(se.who)} ${se.f(se.v)} (limit ${se.f(se.lim)}).` : ""} Returns and risk figures below stay at ${fmtDate(DB.meta.as_on)}.</p>`; })() : ""}
    <div class="grid g2"><div><h2>Key findings</h2>${al.slice(0, 6).map(a => `<div class="sig"><span>${esc(a.title)}</span>${pill(a.sev, a.sev === "crit" ? "Breach" : "Warning")}</div>`).join("")}</div>
      <div><h2>Largest look-through exposures</h2>${lt.rows.slice(0, 8).map(r => `<div class="sig"><span>${esc(IX.co[r.code]?.name || r.code)}</span><span class="num">${fmtCr(r.total)} · <b>${fmtPct(r.pct, 2)}</b></span></div>`).join("")}</div></div>
    <div class="grid g2"><div><h2>Concentration</h2><dl class="dl"><dt>Look-through equity</dt><dd>${fmtCr(lt.eq)}</dd><dt>Stocks</dt><dd>${con.n}</dd><dt>HHI / effective N</dt><dd>${fmtHHI(con.hhi)} / ${fmtN(con.effN, 1)}</dd><dt>Top 10</dt><dd>${fmtPct(con.top10)}</dd><dt>Equity beta</dt><dd>${fmtN(portBeta(lt), 2)}</dd>${isNum(weightedTer(M)) ? `<dt>Weighted TER</dt><dd>${fmtPct(weightedTer(M), 2)}</dd>` : ""}</dl></div>
      <div><h2>Tax position (indicative, ${esc(DB.policy.tax_year_label)})</h2><dl class="dl"><dt>Realised short-term</dt><dd>${fmtAuto(ts("rST"))}</dd><dt>Realised long-term</dt><dd>${fmtAuto(ts("rLT"))}</dd><dt>Unrealised long-term</dt><dd>${fmtAuto(ts("uLT"))}</dd><dt>Indicative tax if all sold (before surcharge and cess; locked ELSS excluded)</dt><dd>${fmtAuto(ts("taxIfSold"))}</dd><dt>Tax-free harvesting room</dt><dd>${fmtAuto(ts("harvest"))}</dd><dt>Direct-plan saving a year</dt><dd>${fmtAuto(directSaving(M))}</dd></dl></div></div>
    <div><h2>Entities</h2>${table("rep-m", [{ k: "n", label: "Entity" }, { k: "v", label: "Value", num: true, fmt: v => fmtCr(v) }, { k: "g", label: "Unrealised gain", num: true, fmt: v => fmtCr(v) }, { k: "x", label: "XIRR", num: true, fmt: v => fmtPct(v, 2) }], DB.members.filter(m => holdings(m.member_id).length).map(m => { const h = holdings(m.member_id); return { n: m.name, v: h.reduce((s, x) => s + x.value, 0), g: h.reduce((s, x) => s + x.unrealised, 0), x: memberXirr(m.member_id) * 100 }; }), { export: false, dense: true })}</div>
    <p class="small muted" style="margin:0">${basisLine(M)} Tax figures are indicative and must be confirmed against the applicable provisions before any action. This report is a decision-support summary, not investment advice.</p>
  </article>`;
}
