/*
 * UI half of latest_prices_check.py: loads the offline app, hands it a fixed set of quotes (as the bridge's
 * /api/quotes would), and reads back the figures at latest prices from the engine and from the rendered screens.
 * Usage: node verify/latest_prices_ui.js <LookThrough.html> <quotes.json>   -> JSON on stdout
 */
const fs = require("fs");
const { chromium } = require("playwright");
(async () => {
  const quotes = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
  const b = await chromium.launch({ channel: "chrome" });
  const p = await b.newPage({ viewport: { width: 1400, height: 900 } });
  const errors = []; p.on("pageerror", e => errors.push(String(e)));
  await p.goto("file:///" + process.argv[2].replace(/\\/g, "/")); await p.waitForTimeout(1200);
  const out = await p.evaluate(q => {
    const r = { before: { top: lookThrough("ALL").rows[0].pct, value: holdings("ALL").reduce((s, h) => s + h.value, 0) } };
    BRIDGE.quotes = q; CACHE.clear();
    const L = latestValue("ALL");
    r.total = { v: L.v, gain: L.gain, missing: L.missing, quoted: L.quoted, eq: L.eq, nav: L.nav, dates: latestDates(L) };
    r.members = Object.fromEntries(DB.members.map(m => [m.member_id, latestValue(m.member_id).v]));
    r.tests = limitTests(lookThroughLatest("ALL")).map(t => ({ k: t.k, who: t.who, code: t.code || null, v: t.v, s: t.s }));
    r.after = { top: lookThrough("ALL").rows[0].pct, value: holdings("ALL").reduce((s, h) => s + h.value, 0) };
    const txt = v => { go(v); return document.querySelector("#content").innerText; };
    r.screens = { dashboard: txt("dashboard"), holdings: txt("holdings"), concentration: txt("concentration"), report: txt("report"), method: txt("method") };
    r.fmt = { total: fmtAmt(L.v), totalCr: fmtCr(L.v), top: fmtPct(r.tests[0].v, 2), dates: latestDates(L), short: latestDates(L, true) };
    BRIDGE.quotes = null; CACHE.clear();
    r.off = { dashboard: txt("dashboard"), concentration: txt("concentration"), holdings: txt("holdings") };
    return r;
  }, quotes);
  out.errors = errors;
  console.log(JSON.stringify(out));
  await b.close();
})();
