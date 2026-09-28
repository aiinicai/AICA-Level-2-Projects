// Functional tests (v3): data-independent, so they run on the mock build, the gap fixture and the real snapshot.
// Usage: node functional.js [app.html]
const { chromium } = require("playwright");
const path = require("path"), fs = require("fs");
(async () => {
  const appFile = path.resolve(process.argv[2] || path.join(__dirname, "../app/LookThrough.html"));
  const b = await chromium.launch(), p = await b.newPage({ viewport: { width: 1440, height: 1000 } });
  const errs = []; p.on("pageerror", e => errs.push(e.message));
  await p.goto("file://" + appFile); await p.waitForTimeout(300);
  const T = [], check = (name, ok, detail = "") => T.push({ name, ok: !!ok, detail });
  const drawn = () => p.evaluate(() => !document.querySelector("#content").innerText.includes("could not be drawn"));

  // ---- financial-statement parser edge cases
  const px = await p.evaluate(() => {
    const t1 = extract(`XYZ Ltd\n(Rs. in lakhs)\nRevenue from operations (Note 21)   12,34,567.00   11,00,000.00\nTotal income  12,50,000.00\nProfit for the year   (4,500.50)   2,000\nTotal equity and liabilities  99,99,999\nTotal equity  5,00,000\nNon-current borrowings 70,000\nTotal borrowings 1,20,000\nNet cash used in operating activities (2,345.00)`);
    const t2 = extract(`ABC Ltd (USD in million)\nNet sales 1,200.5\nEBITDA 300\nNet profit for the period 150\nNet worth 900\nBorrowings 400\nCash flow from operations 180`);
    const t3 = extract(`No units stated\nRevenue from operations 500\nProfit after tax 50`);
    const V = t => Object.fromEntries(Object.entries(t.fields).map(([k, v]) => [k, v.value]));
    return { t1: V(t1), t2: V(t2), u3: t3.unit, c3: t3.fields.revenue.conf };
  });
  check("Parser: lakh → crore, '(Note 21)' ignored, 'Total income' not revenue", Math.abs(px.t1.revenue - 12345.67) < 0.01, JSON.stringify(px.t1));
  check("Parser: bracketed loss and negative cash flow", Math.abs(px.t1.pat + 45.005) < 0.01 && Math.abs(px.t1.cfo + 23.45) < 0.01);
  check("Parser: 'Total equity and liabilities' skipped; total borrowings preferred", Math.abs(px.t1.net_worth - 5000) < 0.01 && Math.abs(px.t1.total_debt - 1200) < 0.01);
  check("Parser: million → crore and synonyms", Math.abs(px.t2.revenue - 120.05) < 0.01 && Math.abs(px.t2.total_debt - 40) < 0.01 && Math.abs(px.t2.cfo - 18) < 0.01, JSON.stringify(px.t2));
  check("Parser: missing unit flagged as assumed", px.u3.assumed === true && px.c3 === "Medium");

  // ---- CSV export → import round trip
  const snap = () => p.evaluate(() => ({ v: holdings("ALL").reduce((s, h) => s + h.value, 0), x: memberXirr("ALL"), hhi: concentration(lookThrough("ALL")).hhi, n: DB.transactions.length }));
  const before = await snap(), tmp = path.join(__dirname, "tmp_txn.csv");
  fs.writeFileSync(tmp, await p.evaluate(() => toCSV(DB.transactions)));
  await p.evaluate(() => go("data")); await p.click('[data-tab="data"][data-v="import"]');
  await p.setInputFiles("#imp_transactions", tmp); await p.waitForTimeout(400);
  const after = await snap(), lastLog = await p.evaluate(() => AUDIT[0].action);
  check("Import round-trip leaves value, XIRR and HHI unchanged", Math.abs(after.v - before.v) < 1e-6 && Math.abs(after.x - before.x) < 1e-12 && Math.abs(after.hhi - before.hhi) < 1e-12 && lastLog === "IMPORT", JSON.stringify({ before, after, lastLog }));
  fs.writeFileSync(tmp, "date,member_id\n2026-01-01,M1\n");
  await p.setInputFiles("#imp_transactions", tmp); await p.waitForTimeout(300);
  const rej = await p.evaluate(() => ({ a: AUDIT[0].action, n: DB.transactions.length }));
  check("Import: file with missing columns rejected, data kept", rej.a === "IMPORT_REJECTED" && rej.n === before.n, JSON.stringify(rej));
  const badTx = await p.evaluate(() => { const h = holdings("ALL").find(x => x.asset_type === "EQ"), t = JSON.parse(JSON.stringify(DB.transactions)); t.push({ txn_id: "T99999", date: DB.meta.as_on, member_id: h.member_id, asset_type: "EQ", instrument: h.instrument, plan: "", txn_type: "Sell", units: h.units * 10, price: h.price, amount: h.units * 10 * h.price }); return toCSV(t); });
  fs.writeFileSync(tmp, badTx); await p.setInputFiles("#imp_transactions", tmp); await p.waitForTimeout(400);
  const rc = await p.evaluate(() => (reconciliation().find(r => /exceeds/i.test(r.t)) || {}).s);
  check("Reconciliation: oversold sale detected", rc === "fail", rc);
  await p.click("#resetSample"); fs.unlinkSync(tmp);
  check("Reset restores the snapshot", (await snap()).n === before.n);

  // ---- reconciliation controls pass on the shipped snapshot
  const rcAll = await p.evaluate(() => reconciliation().map(r => [r.t, r.s]));
  check("Reconciliation: no control fails on the snapshot", rcAll.every(r => r[1] !== "fail"), JSON.stringify(rcAll.filter(r => r[1] !== "ok")));

  // ---- policy edits
  await p.evaluate(() => go("data")); await p.click('[data-tab="data"][data-v="policy"]');
  await p.fill("#pol_max_single_stock_pct", "100"); await p.click("#savePolicy");
  const pol = await p.evaluate(() => ({ a: alerts("ALL").some(x => x.kind === "Single stock"), log: AUDIT[0].action }));
  check("Policy: raising single-stock limit to 100% clears single-stock alerts", !pol.a && pol.log === "POLICY", JSON.stringify(pol));
  await p.click('[data-tab="data"][data-v="policy"]'); await p.fill("#pol_max_single_stock_pct", "0.5"); await p.click("#savePolicy");
  const tight = await p.evaluate(() => alerts("ALL").filter(x => x.kind === "Single stock" && x.sev === "crit").length);
  check("Policy: a 0.5% limit flags breaches", tight > 0, "crit alerts " + tight);
  await p.click('[data-tab="data"][data-v="policy"]'); await p.fill("#pol_target_large_pct", "95"); await p.click("#savePolicy");
  const tgt = await p.evaluate(() => DB.policy.target_large_pct + DB.policy.target_mid_pct + DB.policy.target_small_pct);
  check("Policy: targets not totalling 100% are refused", Math.abs(tgt - 100) < 1e-9, "sum " + tgt);
  await p.evaluate(() => { DB = JSON.parse(JSON.stringify(SAMPLE)); reindex(); });

  // ---- what-if headroom and switch simulator
  const wi = await p.evaluate(() => { const c = DB.companies.map(c => scorecard(c.code)).find(s => s && s.headroom > 0); if (!c) return null; const w = whatIfBuy(c.c.code, c.headroom); return { code: c.c.code, after: w.after.pct, limit: DB.policy.max_single_stock_pct }; });
  check("Headroom: buying exactly the headroom lands on the limit", wi && Math.abs(wi.after - wi.limit) < 1e-9, JSON.stringify(wi));
  const sim = await p.evaluate(() => { const held = heldSchemes("ALL").filter(s => latestPort()[s]); if (held.length < 2) return null; const r = simulateSwitch("ALL", held[0], held[1], 1), v = holdings("ALL").filter(h => h.instrument === held[0]).reduce((s, h) => s + h.value, 0); return { amt: r.amount, exp: v, funds: r.after.funds, before: r.before.funds }; });
  check("Simulator: full switch moves the whole holding and removes one fund", sim && Math.abs(sim.amt - sim.exp) < 1e-6 && sim.funds === sim.before - 1, JSON.stringify(sim));

  // ---- screener and decision engine
  const scr = await p.evaluate(() => { const rows = screenerRows("ALL"); return { all: applyFilters(rows, PRESETS.all.f).length, rows: rows.length, each: Object.fromEntries(Object.entries(PRESETS).map(([k, v]) => [k, applyFilters(rows, v.f).length])) }; });
  check("Screener: 'All companies' returns every company with statements", scr.all === scr.rows && scr.rows > 0, JSON.stringify(scr));
  const dec = await p.evaluate(() => { const c = {}; screenerRows("ALL").forEach(r => c[r.decision] = (c[r.decision] || 0) + 1); return c; });
  check("Decision engine: at least three different outcomes on real data", Object.keys(dec).length >= 3, JSON.stringify(dec));

  // ---- incomplete data is handled, never guessed
  const gap = await p.evaluate(() => {
    const held = heldSchemes("ALL").find(s => latestPort()[s]); if (!held) return null;
    const u0 = lookThrough("ALL").unmapped, saved = DB.scheme_portfolios; DB.scheme_portfolios = saved.filter(r => r.scheme_id !== held); reindex();
    const lt = lookThrough("ALL"), a = alerts("ALL").find(x => x.kind === "Data");
    const out = { held, unmapped: lt.unmapped - u0, value: holdings("ALL").filter(h => h.instrument === held).reduce((s, h) => s + h.value, 0), alert: !!a, ov: overlap(held, DB.schemes.find(s => s.scheme_id !== held).scheme_id).overlap };
    DB.scheme_portfolios = saved; reindex(); return out;
  });
  check("Missing AMC file: fund value reported as not looked through, overlap n/a, alert raised", gap && Math.abs(gap.unmapped - gap.value) < 1e-6 && gap.alert && gap.ov === null, JSON.stringify(gap));
  const nofin = await p.evaluate(() => { const c = DB.companies.find(c => !IX.fin[c.code]); if (!c) return "none"; go("company", c.code); return c.code; });
  check("Company without statements opens cleanly", nofin === "none" || await drawn(), nofin);
  const nobeta = await p.evaluate(() => { const lt = lookThrough("ALL"); return { pb: portBeta(lt), cov: betaCoverage(lt) }; });
  check("Portfolio beta computed with coverage disclosed", typeof nobeta.pb === "number" && nobeta.cov > 0 && nobeta.cov <= 100 + 1e-9, JSON.stringify(nobeta));

  // ---- units and identifiers
  const units = await p.evaluate(() => { const out = {}; ["cr", "lakh", "inr"].forEach(u => { state.units = u; out[u] = fmtAmt(12345678.9); }); state.units = "cr"; return out; });
  check("Unit switch formats ₹ Cr / ₹ L / ₹", /1\.23/.test(units.cr) && /123\.46/.test(units.lakh) && /1,23,45,679/.test(units.inr), JSON.stringify(units));
  const isin = await p.evaluate(() => [isinValid("INE002A01018"), isinValid("INE002A01019"), DB.companies.filter(c => c.isin && !isinValid(c.isin)).map(c => c.code)]);
  check("ISIN check digit: known valid/invalid and every company ISIN", isin[0] && !isin[1] && !isin[2].length, JSON.stringify(isin));

  check("No runtime errors", !errs.length, errs.join("; "));
  await b.close();
  const out = T.map(t => `${t.ok ? "PASS" : "FAIL"}  ${t.name}${t.ok ? "" : "   → " + t.detail}`);
  out.push(`\n${T.filter(t => t.ok).length}/${T.length} functional tests passed`);
  console.log(out.join("\n")); fs.writeFileSync(path.join(__dirname, "functional_result.txt"), out.join("\n") + "\n");
  process.exit(T.every(t => t.ok) ? 0 : 1);
})();
