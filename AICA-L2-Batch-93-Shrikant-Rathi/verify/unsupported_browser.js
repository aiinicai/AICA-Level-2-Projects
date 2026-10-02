// The unsupported-browser notice: shown (and the app hidden) when the page looks like IE / Edge IE mode,
// absent in a modern browser. IE is simulated by defining document.documentMode before any script runs.
// Usage: node verify/unsupported_browser.js [app.html] [--shot=path.png]
const { chromium } = require("playwright");
const path = require("path");
(async () => {
  const file = "file://" + path.resolve(process.argv.find(a => a.endsWith(".html")) || path.join(__dirname, "../app/LookThrough.html"));
  const shot = (process.argv.find(a => a.startsWith("--shot=")) || "").slice(7);
  const b = await chromium.launch(), results = [];
  const check = (name, ok, detail) => { results.push(ok); console.log((ok ? "PASS  " : "FAIL  ") + name + (ok ? "" : "  -> " + detail)); };
  const state = p => p.evaluate(() => ({ notice: !!document.getElementById("lt-unsupported"),
    appShown: getComputedStyle(document.querySelector(".app")).display !== "none", flag: !!window.__LT_UNSUPPORTED__ }));

  const modern = await b.newPage();
  await modern.goto(file);
  const m = await state(modern);
  check("Modern browser: no notice, app shown", !m.notice && m.appShown && !m.flag, JSON.stringify(m));

  const ie = await b.newPage({ viewport: { width: 1280, height: 720 } });
  await ie.addInitScript(() => Object.defineProperty(document, "documentMode", { value: 11 }));
  await ie.goto(file);
  const s = await state(ie);
  check("IE mode: notice shown and app hidden", s.notice && !s.appShown && s.flag, JSON.stringify(s));
  const txt = await ie.evaluate(() => document.getElementById("lt-unsupported")?.innerText || "");
  check("IE mode: notice tells the user what to do", /Chrome/.test(txt) && /Leave Internet Explorer mode/.test(txt), txt.slice(0, 120));
  if (shot) await ie.screenshot({ path: shot });
  await b.close();
  process.exit(results.every(Boolean) ? 0 : 1);
})();
