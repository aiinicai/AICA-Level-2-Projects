// Reconciles the app's JavaScript engine with the independent pandas engine (v3, real-data model).
// 1) python verify/recompute.py [dataset.json]   2) node verify/reconcile_app.js [app.html]
// Null agreement is checked too: where one engine cannot compute a figure, the other must also return null.
const { chromium } = require("playwright");
const path = require("path"), fs = require("fs");
(async () => {
  const ref = JSON.parse(fs.readFileSync(path.join(__dirname, "reference_metrics.json")));
  const appFile = path.resolve(process.argv[2] || path.join(__dirname, "../app/LookThrough.html"));
  const b = await chromium.launch(), p = await b.newPage();
  const errs = []; p.on("pageerror", e => errs.push(e.message));
  await p.goto("file://" + appFile);
  await p.waitForTimeout(300);
  const app = await p.evaluate(() => {
    const N = v => (v === undefined || (typeof v === "number" && !isFinite(v))) ? null : v;
    const H = holdings("ALL"), lt = lookThrough("ALL"), con = concentration(lt);
    const hold = Object.fromEntries(H.map(h => [`${h.member_id}|${h.asset_type}|${h.instrument}|${h.plan}`, { units: h.units, cost: h.cost, value: h.value, unrealised: h.unrealised, lt_gain: h.lt_gain, st_gain: h.st_gain, xirr: N(h.xirr) }]));
    const ids = DB.schemes.map(s => s.scheme_id).sort(), ov = {}, corr = {};
    ids.forEach((a, i) => ids.slice(i + 1).forEach(c => { ov[`${a}|${c}`] = N(overlap(a, c).overlap); }));
    const fids = ids.filter(s => fundStats(s));
    fids.forEach((a, i) => fids.slice(i + 1).forEach(c => { const [x, y] = pairedRets(IX.nav[a + "|Direct"], IX.nav[c + "|Direct"]); corr[`${a}|${c}`] = x.length > 12 ? corrOf(x, y) : null; }));
    const fund = Object.fromEntries(fids.map(s => { const f = fundStats(s); return [s, { r1y: N(f.r1y), cagr3: N(f.cagr3), bench3: N(f.bench3), vol: N(f.vol), sharpe: N(f.sharpe), sortino: N(f.sortino), mdd: N(f.mdd), beta: N(f.beta), alpha: N(f.alpha), te: N(f.te), ir: N(f.ir), up_capture: N(f.upCap), down_capture: N(f.downCap), roll_beat: N(f.rollBeat) }]; }));
    const act = activity(), activityOut = Object.fromEntries(ids.map(s => { const a = act.perScheme[s]; return [s, a ? { entries: a.entries.length, exits: a.exits.length, turnover: a.turnover } : null]; }));
    const cons = Object.fromEntries(Object.values(act.stock).map(x => [x.code, { adding: x.adding, reducing: x.reducing, holders: x.holders, net_w: x.netW }]));
    const K = ["roe", "roa", "pe", "pb", "rev_cagr3", "pat_cagr3", "rev_cagr5", "div_yield", "roce", "de", "int_cover", "current_ratio", "ev_ebitda", "fcf_yield", "cfo_pat", "dupont_margin", "dupont_turnover", "dupont_leverage", "fscore", "gnpa", "nnpa", "car", "nim"];
    const rat = {}; DB.companies.forEach(c => { const r = ratios(c.code); if (!r) return; const o = {}; K.forEach(k => { if (k in r) o[k] = N(r[k]); }); rat[c.code] = o; });
    const tax = Object.fromEntries(DB.members.map(m => { const t = taxView(m.member_id); return [m.member_id, { realised_st: t.rST, realised_lt: t.rLT, unrealised_st: t.uST, unrealised_lt: t.uLT, locked_value: t.lockedValue, exemption_left: t.exemptLeft, tax_if_all_sold: t.taxIfSold, harvest_headroom: t.harvest }]; }));
    const sb = {}, s1 = {}; Object.keys(IX.px).forEach(c => { const s = stockStats(c); if (s) { sb[c] = N(s.beta); s1[c] = N(s.r1y); } });
    const sectors = Object.fromEntries(groupBy(lt, "sector").map(x => [x.key, x.pct]));
    return {
      hold, realised_count: realised("ALL").length, realised_gain_total: realised("ALL").reduce((s, r) => s + r.gain, 0),
      member_xirr: Object.fromEntries(DB.members.map(m => [m.member_id, N(memberXirr(m.member_id))])), family_xirr: memberXirr("ALL"),
      family: { value: H.reduce((s, h) => s + h.value, 0), cost: H.reduce((s, h) => s + h.cost, 0), mf: lt.mfTotal, eq: lt.directTotal, debt_in_funds: lt.debt, cash_in_funds: lt.cash, unmapped: lt.unmapped, equity: lt.eq, hhi: con.hhi, eff_n: con.effN, top10: con.top10, top_pct: con.top ? con.top.pct : null, n: con.n, port_beta: portBeta(lt) },
      per_member: Object.fromEntries(DB.members.map(m => { const k = concentration(lookThrough(m.member_id)); return [m.member_id, { value: holdings(m.member_id).reduce((s, h) => s + h.value, 0), hhi: k.hhi, top10: k.top10, eff_n: k.effN }]; })),
      top10: Object.fromEntries(lt.rows.slice(0, 10).map(r => [r.code, r.total])), sectors, weighted_ter: N(weightedTer("ALL")), direct_switch_saving: directSaving("ALL"),
      tax, overlap: ov, fund, corr, activity: activityOut, consensus: cons, stock_beta: sb, stock_1y: s1, ratios: rat, market_index: IX.mktCode,
      stress: { market_minus20: stress("ALL", { type: "market", market: -0.2 }).loss, fin_minus20: stress("ALL", { type: "sector", sector: "Financial Services", shock: -0.2 }).loss, hist_correction: stress("ALL", { type: "hist", t0: 13, t1: 18 }).loss },
    };
  });
  await b.close();
  const res = [];
  function cmp(name, a, r, relTol = 1e-6, absTol = 1e-6) {
    let n = 0, nulls = 0, worst = 0, where = "";
    const bad = [];
    (function walk(x, y, k) {
      if (y !== null && typeof y === "object") {
        if (x === null || typeof x !== "object") { bad.push(`${k}: app ${JSON.stringify(x)} vs ref object`); return; }
        const keys = new Set([...Object.keys(y), ...Object.keys(x)]);
        keys.forEach(key => walk(key in x ? x[key] : null, key in y ? y[key] : null, k + "." + key));
        return;
      }
      if (y === null || x === null || typeof y === "string") {
        if (x === y) { if (y === null) nulls++; else n++; return; }
        bad.push(`${k}: app ${JSON.stringify(x)} vs ref ${JSON.stringify(y)}`); return;
      }
      n++; const d = Math.abs(x - y), tol = Math.max(absTol, relTol * Math.abs(y));
      if (d / tol > worst) { worst = d / tol; where = `${k}: app ${x} vs ref ${y}`; }
    })(a, r, name);
    res.push({ name, n, nulls, ok: worst <= 1 && !bad.length, where: bad.length ? bad.slice(0, 4).join("; ") : where });
  }
  cmp("Holdings (units, cost, value, gains, XIRR)", app.hold, ref.holdings, 1e-7, 1e-4);
  cmp("Realised lots count", app.realised_count, ref.realised_count, 0, 0);
  cmp("Realised gain total", app.realised_gain_total, ref.realised_gain_total, 1e-9, 1e-3);
  cmp("Entity XIRR", app.member_xirr, ref.member_xirr, 1e-6, 1e-7);
  cmp("Family XIRR", app.family_xirr, ref.family_xirr, 1e-6, 1e-7);
  cmp("Market index used for beta", app.market_index, ref.market_index);
  cmp("Family totals, look-through & concentration", app.family, ref.family, 1e-8, 1e-4);
  cmp("Per-entity value & concentration", app.per_member, ref.per_member, 1e-8, 1e-4);
  cmp("Top 10 exposures", app.top10, ref.top10, 1e-9, 1e-3);
  cmp("Sector weights", app.sectors, ref.sectors, 1e-8, 1e-8);
  cmp("Weighted TER & implied Direct saving", { t: app.weighted_ter, s: app.direct_switch_saving }, { t: ref.weighted_ter, s: ref.direct_switch_saving }, 1e-9, 1e-6);
  cmp("Indicative tax by entity", app.tax, ref.tax, 1e-8, 1e-3);
  cmp("Fund overlap matrix", app.overlap, ref.overlap, 1e-9, 1e-9);
  cmp("Fund returns & risk (14 metrics)", app.fund, ref.fund, 1e-7, 1e-9);
  cmp("Fund return correlations", app.corr, ref.corr, 1e-6, 1e-7);
  cmp("Portfolio activity by scheme", app.activity, ref.activity, 1e-9, 1e-9);
  cmp("Fund-manager consensus by stock", app.consensus, ref.consensus, 1e-8, 1e-8);
  cmp("Stock betas & 1Y returns", { b: app.stock_beta, r: app.stock_1y }, { b: ref.stock_beta, r: ref.stock_1y }, 1e-8, 1e-9);
  cmp("Company ratios incl. F-score", app.ratios, ref.ratios, 1e-8, 1e-8);
  cmp("Stress scenarios", app.stress, ref.stress, 1e-9, 1e-3);
  if (errs.length) res.push({ name: "Runtime errors", n: errs.length, nulls: 0, ok: false, where: errs.join("; ") });
  const pass = res.filter(r => r.ok).length, values = res.reduce((s, r) => s + (r.n || 0), 0), nulls = res.reduce((s, r) => s + (r.nulls || 0), 0);
  const lines = res.map(r => `${r.ok ? "PASS" : "FAIL"}  ${r.name.padEnd(46)} ${String(r.n).padStart(5)} values${r.nulls ? ` + ${r.nulls} agreed n/a` : ""}${r.ok ? "" : "   " + r.where}`);
  lines.push(`\n${pass}/${res.length} check groups passed · ${values.toLocaleString("en-IN")} values compared · ${nulls} not-computable cases agreed`);
  console.log(lines.join("\n"));
  fs.writeFileSync(path.join(__dirname, "reconciliation_result.txt"), lines.join("\n") + "\n");
  process.exit(pass === res.length ? 0 : 1);
})();
