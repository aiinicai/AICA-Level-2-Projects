/* UAE Corporate Tax workpaper engine (shared by the web app and the Node test).
   Educational tool: rates and rules must be verified against current FTA guidance. */
(function (root) {
  "use strict";

  const RULES = {
    rate: 0.09,
    zeroBand: 375000,          // 0% up to AED 375,000
    entertainmentDeductible: 0.5,
    lossOffsetCap: 0.75,
    interestSafeHarbour: 12000000,
    interestEbitdaPct: 0.30,
    sbrRevenueCap: 3000000     // Small Business Relief (limited-period relief, verify validity)
  };

  // category -> label, sign (+1 income, -1 expense)
  const CATS = {
    revenue: ["Revenue", 1],
    other_income: ["Other income", 1],
    dividend_income: ["Dividend income (exempt)", 1],
    interest_income: ["Interest income", 1],
    cogs: ["Cost of sales", -1],
    opex: ["Operating expense (deductible)", -1],
    depreciation: ["Depreciation / amortisation", -1],
    interest_expense: ["Interest expense", -1],
    entertainment_client: ["Client entertainment (50%)", -1],
    fines: ["Fines and penalties (non-deductible)", -1],
    donations: ["Donations (non-approved)", -1],
    donations_approved: ["Donations (approved)", -1],
    personal: ["Personal / owner expense", -1],
    mixed: ["Mixed-use expense", -1],
    bs: ["Balance sheet (ignored)", 0]
  };

  const KEYWORDS = [
    [/dividend/i, "dividend_income"],
    [/interest\s*(income|received)/i, "interest_income"],
    [/interest|finance (cost|charge)|bank charge/i, "interest_expense"],
    [/depreciation|amorti[sz]ation/i, "depreciation"],
    [/fine|penalt/i, "fines"],
    [/donation|charity/i, "donations"],
    [/entertain|client (meal|gift|hospitality)|hospitality/i, "entertainment_client"],
    [/owner|director.*personal|personal|drawings/i, "personal"],
    [/vehicle|car |motor|internet|mobile|telephone/i, "mixed"],
    [/cost of (goods|sales)|cogs|purchases/i, "cogs"],
    [/revenue|sales|service income|fee income/i, "revenue"]
  ];

  const num = x => parseFloat(String(x == null ? "0" : x).replace(/,/g, "")) || 0;

  function parseCSV(text) {
    const rows = []; let row = [], cur = "", q = false;
    text = text.replace(/^﻿/, "");
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (q) { if (c === '"') { if (text[i + 1] === '"') { cur += '"'; i++; } else q = false; } else cur += c; }
      else if (c === '"') q = true;
      else if (c === ",") { row.push(cur); cur = ""; }
      else if (c === "\n" || c === "\r") { if (c === "\r" && text[i + 1] === "\n") i++; row.push(cur); rows.push(row); row = []; cur = ""; }
      else cur += c;
    }
    if (cur || row.length) { row.push(cur); rows.push(row); }
    const clean = rows.filter(r => r.some(x => x.trim()));
    const head = clean.shift().map(h => h.trim().toLowerCase());
    return clean.map(r => Object.fromEntries(head.map((h, i) => [h, (r[i] || "").trim()])));
  }

  // Build TB rows with a category. Blank category -> keyword guess, then account-code fallback.
  function loadTB(text) {
    return parseCSV(text).map(r => {
      const code = r.account_code || "", name = r.account_name || "";
      let cat = (r.category || "").trim().toLowerCase(), auto = false;
      if (!CATS[cat]) {
        auto = true; cat = "";
        const first = code.charAt(0);
        if (["1", "2", "3"].includes(first)) cat = "bs";
        if (!cat) for (const [re, c] of KEYWORDS) { if (re.test(name)) { cat = c; break; } }
        if (!cat) cat = first === "4" ? "other_income" : "opex";
      }
      const debit = num(r.debit), credit = num(r.credit);
      return {
        code, name, debit, credit, cat, auto,
        usePct: r.business_use_pct === "" || r.business_use_pct == null ? 100 : num(r.business_use_pct)
      };
    });
  }

  function amount(r) { // positive amount in the natural direction of the category
    const sign = CATS[r.cat][1];
    return sign === 1 ? r.credit - r.debit : sign === -1 ? r.debit - r.credit : 0;
  }
  const sumCat = (rows, cat) => rows.filter(r => r.cat === cat).reduce((s, r) => s + amount(r), 0);

  function compute(rows, opt) {
    opt = Object.assign({lossBF: 0, sbr: false, deductDonationsApproved: true}, opt || {});
    const S = c => sumCat(rows, c);
    const revenue = S("revenue"), otherInc = S("other_income"), divInc = S("dividend_income"), intInc = S("interest_income");
    const cogs = S("cogs"), opex = S("opex"), dep = S("depreciation"), intExp = S("interest_expense");
    const ent = S("entertainment_client"), fines = S("fines"), don = S("donations"), donOk = S("donations_approved");
    const pers = S("personal");
    const mixedTotal = S("mixed");
    const mixedPrivate = rows.filter(r => r.cat === "mixed").reduce((s, r) => s + amount(r) * (1 - r.usePct / 100), 0);

    const profit = revenue + otherInc + divInc + intInc - cogs - opex - dep - intExp - ent - fines - don - donOk - pers - mixedTotal;

    const adj = [];
    const add = (label, v, basis) => { v = Math.round(v * 100) / 100; if (Math.abs(v) > 0.004) adj.push({label, amount: v, basis}); };
    add("Client entertainment: non-deductible 50%", ent * (1 - RULES.entertainmentDeductible), "50% of client entertainment disallowed");
    add("Fines and penalties", fines, "100% disallowed");
    add("Donations to non-approved entities", don, "100% disallowed");
    add("Personal / owner expenses", pers, "Not wholly and exclusively for business");
    add("Mixed-use expenses: private share", mixedPrivate, "Private-use % disallowed");
    add("Dividend income (exempt, assumes participation exemption met)", -divInc, "Exempt income deducted");

    // interest limitation
    const netInterest = intExp - intInc;
    const ebitda = profit + netInterest + dep;
    const allowedInterest = Math.max(RULES.interestSafeHarbour, RULES.interestEbitdaPct * Math.max(ebitda, 0));
    const interestDisallowed = Math.max(0, netInterest - allowedInterest);
    add("Net interest above limit (greater of AED 12m / 30% EBITDA)", interestDisallowed, "Excess carried forward, not deducted this period");

    const adjTotal = adj.reduce((s, a) => s + a.amount, 0);
    const taxableBeforeLoss = profit + adjTotal;
    const lossUsed = Math.min(Math.max(opt.lossBF, 0), RULES.lossOffsetCap * Math.max(taxableBeforeLoss, 0));
    const taxableIncome = taxableBeforeLoss - lossUsed;
    const lossCF = Math.max(opt.lossBF - lossUsed, 0) + Math.max(-taxableBeforeLoss, 0);
    const sbrApplied = !!opt.sbr && revenue <= RULES.sbrRevenueCap;
    const taxBase = Math.max(0, taxableIncome - RULES.zeroBand);
    const tax = sbrApplied ? 0 : taxBase * RULES.rate;

    return {
      revenue, profit, adjustments: adj, adjTotal, taxableBeforeLoss, lossUsed, taxableIncome, lossCF,
      sbrRequested: !!opt.sbr, sbrApplied, sbrBlocked: !!opt.sbr && !sbrApplied,
      taxBase, tax, effectiveRate: profit > 0 ? tax / profit : 0,
      netInterest, ebitda, allowedInterest,
      reviewCount: rows.filter(r => r.auto && r.cat !== "bs").length,
      tbDiff: rows.reduce((s, r) => s + r.debit - r.credit, 0)
    };
  }

  const api = {RULES, CATS, parseCSV, loadTB, compute, amount};
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.CT = api;
})(typeof window !== "undefined" ? window : globalThis);
