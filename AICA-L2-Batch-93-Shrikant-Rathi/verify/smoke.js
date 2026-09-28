// Smoke test: open every screen/tab for every entity, in light & dark, desktop & phone.
// Usage: node smoke.js [--shots]
const { chromium } = require("playwright");
const path = require("path"), fs = require("fs");
(async () => {
  const shots = process.argv.includes("--shots"), dir = path.join(__dirname, "shots");
  if (shots) fs.mkdirSync(dir, { recursive: true });
  const b = await chromium.launch(), p = await b.newPage({ viewport: { width: 1440, height: 1000 } });
  const errs = [];
  p.on("pageerror", e => errs.push("pageerror: " + e.message));
  p.on("console", m => { if (m.type() === "error" && !/fonts\.g|ERR_TUNNEL|ERR_CONNECTION|net::/.test(m.text())) errs.push("console: " + m.text()); });
  await p.goto("file://" + path.resolve(process.argv.find(a => a.endsWith(".html")) || path.join(__dirname, "../app/LookThrough.html")));
  const views = await p.evaluate(() => VIEWS.map(v => v.id));
  const errorCards = [];
  for (const v of views) {
    await p.click(`.nav-i[data-view="${v}"]`);
    const bad = await p.evaluate(() => document.querySelector("#content").innerText.includes("could not be drawn"));
    if (bad) errorCards.push(v + ": " + await p.evaluate(() => document.querySelector("#content").innerText.slice(0, 200)));
    if (shots) await p.screenshot({ path: path.join(dir, `${v}.png`), fullPage: true });
    const tabs = await p.$$eval("[data-tab]", els => els.map(e => e.dataset.tab + "|" + e.dataset.v));
    for (const t of tabs) { const [id, val] = t.split("|"); await p.click(`[data-tab="${id}"][data-v="${val}"]`); if (await p.evaluate(() => document.querySelector("#content").innerText.includes("could not be drawn"))) errorCards.push(`${v}/${val}`); if (shots) await p.screenshot({ path: path.join(dir, `${v}-${val}.png`), fullPage: true }); }
  }
  // every entity × every screen
  const mems = await p.evaluate(() => ["ALL", ...DB.members.map(m => m.member_id)]);
  for (const m of mems) { await p.selectOption("#entSel", m); for (const v of views) { await p.click(`.nav-i[data-view="${v}"]`); if (await p.evaluate(() => document.querySelector("#content").innerText.includes("could not be drawn"))) errorCards.push(`${m}/${v}`); } }
  await p.selectOption("#entSel", "ALL");
  // interactions
  await p.click('.nav-i[data-view="stress"]'); for (const k of ["m10", "fin", "top", "hist", "custom"]) await p.click(`[data-stress="${k}"]`); await p.click("#runCustom");
  await p.click('.nav-i[data-view="screener"]'); for (const k of ["growth", "value", "consensus", "fresh", "flags", "all", "quality"]) await p.click(`[data-preset="${k}"]`); await p.click("#addFilter");
  await p.click('.nav-i[data-view="overlap"]'); await p.click('[data-seg="simFrac"][data-v="0.5"]'); if (await p.$('[data-seg="heldOnly"][data-v="0"]')) await p.click('[data-seg="heldOnly"][data-v="0"]');  // shown only when some tracked fund is not held
  await p.click('.nav-i[data-view="extract"]'); await p.click("#runExtract"); await p.click("#approveEx");
  for (const u of ["lakh", "inr", "cr"]) await p.click(`[data-seg="units"][data-v="${u}"]`);
  await p.click('.nav-i[data-view="holdings"]'); await p.click('[data-tab="holdings"][data-v="holdings"]'); await p.click('[data-sort="holdings|unrealised"]'); await p.fill("#q-holdings", "arya");
  await p.keyboard.press("Control+k"); await p.keyboard.type("infosys"); await p.keyboard.press("Enter");
  const onCompany = await p.evaluate(() => state.view === "company" && state.company === "INFY");
  // dark theme
  await p.click("#themeBtn"); await p.click('.nav-i[data-view="dashboard"]'); if (shots) await p.screenshot({ path: path.join(dir, "dashboard-dark.png"), fullPage: false });
  await p.click("#themeBtn");
  // phone width
  await p.setViewportSize({ width: 390, height: 860 });
  const hs = [];
  for (const v of views) { await p.evaluate(v => go(v), v); const o = await p.evaluate(() => document.documentElement.scrollWidth - innerWidth); if (o > 1) hs.push(`${v}:${o}px`); }
  if (shots) { await p.evaluate(() => go("dashboard")); await p.screenshot({ path: path.join(dir, "mobile.png") }); }
  await b.close();
  console.log(JSON.stringify({ views: views.length, errs, errorCards, paletteNav: onCompany, hScroll: hs }, null, 1));
  process.exit(errs.length || errorCards.length || hs.length || !onCompany ? 1 : 0);
})();
