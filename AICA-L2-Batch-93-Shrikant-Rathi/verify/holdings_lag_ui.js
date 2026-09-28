/*
 * UI half of holdings_lag_check.py: reads what each look-through screen says about the fund-holdings date.
 * Usage: node verify/holdings_lag_ui.js <LookThrough.html>   -> JSON on stdout
 */
const { chromium } = require("playwright");
(async () => {
  const b = await chromium.launch({ channel: "chrome" });
  const p = await b.newPage({ viewport: { width: 1400, height: 900 } });
  const errors = []; p.on("pageerror", e => errors.push(String(e)));
  await p.goto("file:///" + process.argv[2].replace(/\\/g, "/")); await p.waitForTimeout(1200);
  const out = await p.evaluate(() => {
    const r = { screens: {}, asOn: DB.meta.as_on };
    for (const v of ["dashboard", "lookthrough", "overlap", "concentration", "stress", "report"]) {
      go(v); const c = document.querySelector("#content");
      r.screens[v] = { note: c.querySelector(".lag-note")?.innerText || "", head: (c.querySelector(".ph p") || c.querySelector(".report"))?.innerText.slice(0, 600) || "" };
    }
    r.report = (() => { go("report"); return document.querySelector(".report .rh")?.innerText || ""; })();
    r.alerts = alerts("ALL").filter(a => a.kind === "Data").map(a => a.title);
    r.check = reconciliation().find(x => x.t === "Fund holdings are for the valuation month") || null;
    return r;
  });
  out.errors = errors;
  console.log(JSON.stringify(out));
  await b.close();
})();
