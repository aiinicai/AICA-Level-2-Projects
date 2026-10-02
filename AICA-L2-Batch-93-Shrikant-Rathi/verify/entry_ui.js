// UI flow: first-run admin setup -> app -> add entity -> record a purchase -> see both -> sign out.
// Run through verify/entry_ui_check.py (which starts an isolated bridge). Usage: node entry_ui.js <port> [--shots DIR]
const { chromium } = require("playwright");
const path = require("path"), fs = require("fs");
(async () => {
  const port = process.argv[2], base = `http://localhost:${port}`;
  const si = process.argv.indexOf("--shots"), shots = si > 0 ? process.argv[si + 1] : null;
  if (shots) fs.mkdirSync(shots, { recursive: true });
  const shot = async (p, n) => { if (shots) await p.screenshot({ path: path.join(shots, n + ".png"), fullPage: false }); };
  const b = await chromium.launch({ channel: "chrome" }), p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  const errs = [], res = [];
  p.on("pageerror", e => errs.push(e.message));
  p.on("pageerror", e => errs.push("pageerror " + e.message));
  const bad = [];  // failed HTTP responses, with URL, so resource errors can be judged
  p.on("response", r => { if (r.status() >= 400 && !/favicon\.ico$/.test(r.url())) bad.push(`${r.status()} ${r.request().method()} ${new URL(r.url()).pathname}`); });
  const check = (name, ok, d = "") => { res.push(!!ok); console.log((ok ? "PASS  " : "FAIL  ") + name + (ok ? "" : "  -> " + d)); };
  const toastText = async () => { await p.waitForTimeout(400); return p.evaluate(() => document.querySelector("#toast")?.innerText || ""); };

  await p.goto(base + "/");
  check("Unauthenticated visit lands on the sign-in page", p.url().endsWith("/login"), p.url());
  await p.waitForSelector("#c2:not([hidden])");
  await shot(p, "01-setup");
  await p.fill("#u", "cio"); await p.fill("#p", "Look2026"); await p.fill("#p2", "Look2026");
  await p.click("#b");
  await p.waitForURL(base + "/", { timeout: 20000 }); await p.waitForSelector("#signOut", { timeout: 20000 });
  check("First-run setup creates the admin and opens the app", await p.isVisible("#signOut"));
  const who = await p.evaluate(() => document.querySelector("#liveChip").innerText);
  check("Top bar shows the signed-in user and role", /cio/.test(who) && /admin/i.test(who) && !/cio\s*·\s*admin/.test(who), who);

  await p.evaluate(() => { state.tab.data = "entities"; go("data"); });
  await p.waitForSelector("#entForm");
  await p.fill("#ent_name", "Kavya Mehta"); await p.selectOption("#ent_type", "Individual"); await p.fill("#ent_rel", "Daughter");
  await p.click("#entForm button[type=submit]");
  await p.waitForFunction(() => DB.members.some(m => m.name === "Kavya Mehta"), null, { timeout: 30000 });
  check("Entity added through the form appears in the data", true);
  check("Confirmation shown", /added as M6/.test(await toastText()), await toastText());
  await shot(p, "02-entities");
  const inSelector = await p.evaluate(() => [...document.querySelectorAll("#entSel option")].some(o => o.textContent === "Kavya Mehta"));
  check("New entity is selectable in the entity switcher", inSelector);

  await p.evaluate(() => { state.tab.data = "txns"; go("data"); });
  await p.waitForSelector("#txForm");
  await p.selectOption("#tx_member", "M6");
  await p.selectOption("#tx_inst", "HDFCBANK");
  await p.fill("#tx_date", "2026-02-10"); await p.fill("#tx_units", "200"); await p.fill("#tx_price", "850");
  const amt = await p.evaluate(() => document.querySelector("#tx_amt").innerText);
  check("Amount is computed live (200 x 850)", /1,70,000/.test(amt), amt);
  await p.fill("#tx_units", "0"); await p.click("#txForm button[type=submit]");
  check("Form refuses zero units before sending", /greater than zero/.test(await toastText()), await toastText());
  await p.fill("#tx_units", "200"); await p.click("#txForm button[type=submit]");
  await p.waitForFunction(() => DB.transactions.some(t => t.txn_id === "U00001"), null, { timeout: 30000 });
  check("Purchase recorded through the form (U00001)", /U00001 recorded/.test(await toastText()), await toastText());
  const held = await p.evaluate(() => holdings("M6").find(h => h.instrument === "HDFCBANK")?.units);
  check("Holdings now include 200 HDFC Bank shares for the new entity", held === 200, held);
  check("Form keeps the instrument for the next entry", await p.evaluate(() => document.querySelector("#tx_inst").value) === "HDFCBANK");
  await p.selectOption("#tx_type", "Sell"); await p.fill("#tx_date", "2026-05-10"); await p.fill("#tx_units", "500"); await p.fill("#tx_price", "900");
  await p.click("#txForm button[type=submit]");
  check("Form blocks a sale larger than the units held", /Only 200 units are held/.test(await toastText()), await toastText());
  await shot(p, "03-transactions");

  // contract-note import: password-protected PDF -> preview -> record
  await p.setInputFiles("#cn_file", process.env.CN_PDF);
  await p.fill("#cn_pw", "Wrong999"); await p.click("#cnForm button[type=submit]");
  check("Contract note: a wrong PDF password is reported", /password is not correct/.test(await toastText()), await toastText());
  await p.setInputFiles("#cn_file", process.env.CN_PDF);
  await p.selectOption("#cn_member", "M6"); await p.fill("#cn_pw", process.env.CN_PW); await p.click("#cnForm button[type=submit]");
  await p.waitForSelector(".cn-preview", { timeout: 30000 });
  const prev = await p.evaluate(() => ({ n: ENTRY.cn.trades.length, sel: ENTRY.cn.trades.filter(t => t.include).length, date: document.querySelector("#cn_date").value,
    recon: document.querySelector(".cn-preview").innerText.includes("Reconciled to the note"), pw: document.querySelector("#cn_pw").value }));
  check("Contract note: 3 trades previewed, all selected, trade date filled, reconciled", prev.n === 3 && prev.sel === 3 && prev.date === "2026-08-14" && prev.recon, JSON.stringify(prev));
  check("Contract note: nothing is saved by reading it", await p.evaluate(() => !DB.transactions.some(t => t.txn_id === "U00002")));
  await shot(p, "03b-contract-note");
  await p.click("[data-cnrecord]");
  await p.waitForFunction(() => DB.transactions.filter(t => t.member_id === "M6").length === 4, null, { timeout: 30000 });
  check("Contract note: confirmed trades recorded (U00002-U00004)", /3 trades recorded from contract note DSL\/2026\/004512/.test(await toastText()), await toastText());
  const imp = await p.evaluate(() => DB.transactions.filter(t => t.member_id === "M6" && /Contract note/.test(t.note || "")).map(t => t.instrument).sort().join(",") + "|" + (holdings("M6").find(h => h.instrument === "TCS")?.units ?? 0));
  check("Contract note: imported trades carry the note and show in holdings", imp === "HDFCBANK,ICICIBANK,TCS|25", imp);

  // CAS import (mutual funds): encrypted PDF -> preview -> default selection -> record -> holdings match the statement
  await p.click('[data-impsw="cas"]');
  await p.waitForSelector("#casForm");
  await p.setInputFiles("#cas_file", process.env.CAS_PDF);
  await p.selectOption("#cas_member", "M6"); await p.fill("#cas_pw", process.env.CAS_PW); await p.click("#casForm button[type=submit]");
  await p.waitForSelector(".cn-preview", { timeout: 30000 });
  const cas = await p.evaluate(() => {
    const f = ENTRY.cas.folios, sel = f.flatMap(x => x.txns.filter(t => t.include).map(t => x.scheme_id || "X"));
    return { folios: f.length, sel: sel.length, untracked: sel.includes("X"), sbiSell: f.find(x => x.scheme_id === "S12").txns[0].include,
             allRecon: document.querySelector(".cn-preview").innerText.includes("All 4 folios reconcile") };
  });
  check("CAS: 4 folios, all reconcile; 7 rows ticked; untracked scheme and pre-statement sale left unticked",
    cas.folios === 4 && cas.allRecon && cas.sel === 7 && !cas.untracked && cas.sbiSell === false, JSON.stringify(cas));
  const afterOk = await p.evaluate(() => [...document.querySelectorAll(".cn-preview .small")].filter(e => /After recording, the app will hold/.test(e.innerText) && /✓/.test(e.innerText)).length);
  check("CAS: preview shows the app will hold exactly the closing balance for both imported schemes", afterOk === 2, afterOk);
  await shot(p, "03c-cas");
  await p.click("[data-casrecord]");
  await p.waitForFunction(() => DB.transactions.filter(t => t.member_id === "M6" && /^CAS/.test(t.note || "")).length === 7, null, { timeout: 30000 });
  const mf = await p.evaluate(() => { const h = holdings("M6"); return [h.find(x => x.instrument === "S01" && x.plan === "Direct")?.units, h.find(x => x.instrument === "S05" && x.plan === "Regular")?.units].map(v => Math.round((v || 0) * 1000) / 1000).join(","); });
  check("CAS: 7 transactions recorded; holdings equal the statement (310.204 and 506.03 units)", mf === "310.204,506.03", mf);

  // add a mutual-fund scheme from AMFI's list, then use it
  await p.evaluate(() => { state.tab.data = "schemes"; go("data"); });
  await p.waitForSelector("#schSearch");
  await p.fill("#sch_q", "quant small cap"); await p.click("#schSearch button[type=submit]");
  await p.waitForSelector("[data-schpick]", { timeout: 60000 });
  const pickIdx = await p.evaluate(() => ENTRY.sch.res.findIndex(g => g.direct.code === "120828"));
  await p.click(`[data-schpick="${pickIdx}"]`);
  await p.waitForSelector("#schForm");
  const sug = await p.evaluate(() => [$("#sch_name").value, $("#sch_cat").value, $("#sch_bm").value].join("|"));
  check("Schemes: search finds the fund; name, category and benchmark are suggested", sug === "Quant Small Cap Fund|Small Cap|NIFTYSMALL", sug);
  await shot(p, "03d-scheme-add");
  await p.click("#schForm button[type=submit]");
  await p.waitForFunction(() => DB.schemes.some(s => s.scheme_id === "S13"), null, { timeout: 60000 });
  check("Schemes: added as S13 and listed as 'Added'", /added as S13/.test(await toastText()) && await p.evaluate(() => DB.schemes.find(s => s.scheme_id === "S13").source === "user"), await toastText());
  await p.evaluate(() => { state.tab.data = "txns"; ENTRY.tx = { asset: "MF" }; go("data"); });
  await p.waitForSelector("#txForm");
  check("Schemes: the new scheme can be chosen for a transaction", await p.evaluate(() => [...document.querySelectorAll("#tx_inst option")].some(o => o.value === "S13")));

  const cap = await p.evaluate(() => { const r = stress("ALL", { type: "market", market: -5 }), eq = lookThrough("ALL"); return [r.loss, eq.eq + eq.unmapped]; });
  check("Stress: an impossible -500% market move loses at most the whole equity (beta x move floored at -100%)", -cap[0] > 0 && -cap[0] <= cap[1] + 1, JSON.stringify(cap));

  // latest prices beside the valuation-date figures (test quotes are +5% on every holding)
  await p.evaluate(() => go("dashboard"));
  await p.waitForFunction(() => BRIDGE.quotes && document.body.innerText.includes("At latest prices"), null, { timeout: 30000 });
  const lat = await p.evaluate(() => { const k = [...document.querySelectorAll(".kpi")].find(e => /At latest prices/.test(e.innerText)); return k ? k.innerText : ""; });
  check("Latest prices: the dashboard shows the value at latest prices, +5.0% since the valuation date, dated", /\+5\.0%/.test(lat) && /prices 25 Sep/.test(lat), lat);
  await shot(p, "03f-latest-dashboard");
  await p.evaluate(() => go("holdings")); await p.waitForTimeout(300);
  check("Latest prices: holdings show a Latest column beside the valuation-date price", await p.evaluate(() => [...document.querySelectorAll("th")].some(t => /Latest/.test(t.innerText)) && [...document.querySelectorAll("th")].some(t => /31 Aug 2026/.test(t.innerText))));
  await p.evaluate(() => { state.company = "HDFCBANK"; go("company"); });
  await p.waitForFunction(() => /Latest · 25 Sep 2026/.test(document.querySelector(".co-meta")?.innerText || ""), null, { timeout: 30000 });
  const coMeta = await p.evaluate(() => document.querySelector(".co-meta").innerText);
  check("Latest prices: the company page shows the latest price, its date and the change since the valuation date", /Price · 31 Aug 2026/.test(coMeta) && /\+5\.0%\s*since 31 Aug/.test(coMeta), coMeta.slice(0, 200).replace(/\n/g, " | "));
  await shot(p, "03g-latest-company");

  // add a listed company to the security master, from the screener's button
  await p.evaluate(() => go("screener")); await p.waitForTimeout(300);
  await p.click("[data-open-add]");
  await p.waitForSelector("#eqSearch", { timeout: 10000 });
  check("Securities: the screener's '+ Add a listed company' opens the security master", await p.evaluate(() => state.tab.data === "securities"));
  await p.fill("#eq_q", process.env.EQ_SYM); await p.click("#eqSearch button[type=submit]");
  await p.waitForSelector("[data-eqpick]", { timeout: 60000 });
  const eqIdx = await p.evaluate(sym => ENTRY.eq.res.findIndex(r => r.symbol === sym), process.env.EQ_SYM);
  await p.click(`[data-eqpick="${eqIdx}"]`); await p.waitForSelector("#eqForm");
  await shot(p, "03e-security-add");
  await p.click("#eqForm button[type=submit]");
  await p.waitForFunction(sym => DB.companies.some(c => c.code === sym && c.origin === "user" && c.price), process.env.EQ_SYM, { timeout: 60000 });
  const eqMsg = await toastText();
  check("Securities: added, priced, sector from Yahoo, and flagged as valued-not-scored", new RegExp(`added as ${process.env.EQ_SYM} \\(Capital Goods, no statements`).test(eqMsg), eqMsg);
  await p.evaluate(() => { state.tab.data = "txns"; ENTRY.tx = { asset: "EQ" }; go("data"); });
  await p.waitForSelector("#txForm");
  check("Securities: the new company can be chosen for a transaction", await p.evaluate(sym => [...document.querySelectorAll("#tx_inst option")].some(o => o.value === sym), process.env.EQ_SYM));

  await p.evaluate(() => { state.tab.data = "users"; go("data"); });
  await p.waitForSelector("#userForm");
  await p.fill("#u_name", "analyst.rao"); await p.selectOption("#u_role", "analyst"); await p.fill("#u_pw", "Anly2026");
  await p.click("#userForm button[type=submit]");
  await p.waitForFunction(() => (ENTRY.users || []).some(u => u.user === "analyst.rao"), null, { timeout: 20000 });
  check("Admin creates a user from the Users tab", true);
  await shot(p, "04-users");

  await p.evaluate(() => { state.tab.data = "audit"; go("data"); });
  await p.waitForTimeout(500);
  const audit = await p.evaluate(() => document.querySelector("#content").innerText);
  check("Audit trail tab shows the saved entries", /ENTITY_ADD/.test(audit) && /TXN_ADD/.test(audit) && /USER_CREATE/.test(audit) && /TXN_IMPORT/.test(audit) && /CAS_READ/.test(audit) && /SCHEME_ADD/.test(audit) && /COMPANY_ADD/.test(audit), audit.slice(0, 200));
  await shot(p, "05-audit");

  await p.click("#signOut");
  await p.waitForURL(/\/login$/, { timeout: 10000 });
  check("Sign out returns to the sign-in page", p.url().endsWith("/login"));
  await p.goto(base + "/");
  check("After sign-out the app is not reachable without signing in", p.url().endsWith("/login"), p.url());
  check("No page errors during the flow", !errs.filter(e => e.startsWith("pageerror")).length, errs.join(" | "));
  // The only acceptable failed request is the sign-in probe after sign-out (a 401 is how "not signed in" is reported).
  // The deliberate wrong-password read of the contract note is refused with a 400 (one only).
  const cnRefusals = bad.filter(x => x === "400 POST /api/contract-note").length;
  const unexpected = bad.filter(x => !/^401 GET \/api\/(status|me|auth-state)$/.test(x) && x !== "400 POST /api/contract-note").concat(cnRefusals > 1 ? ["400 POST /api/contract-note x" + cnRefusals] : []);
  check("No unexpected failed requests", !unexpected.length, bad.join(" | "));
  await b.close();
  console.log(`\n${res.filter(Boolean).length}/${res.length} entry UI checks passed`);
  process.exit(res.every(Boolean) ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
