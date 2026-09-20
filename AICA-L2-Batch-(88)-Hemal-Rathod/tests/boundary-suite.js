/* =============================================================================
 * boundary-suite.js — QA suite for the decision engine, AY 2026-27
 * -----------------------------------------------------------------------------
 * Run: open app/index.html, open the browser console, paste this file, Enter.
 * Returns a JSON string: { summary, groups: { name: [ {name, got, want, ok} ] } }
 *
 * Expected values were worked out from the provisions (Finance Act 2023 ss.15-17
 * and the consolidated s.44AB), not recorded from the engine.
 * ========================================================================== */
(function () {
  var groups = {}, pass = 0, fail = 0;
  var APP = 'APPLICABLE', NA = 'NOT APPLICABLE', INC = 'INFORMATION REQUIRED';

  function run(patch) {
    var b = TAS.state.blankInput();
    Object.keys(patch).forEach(function (k) { b[k] = patch[k]; });
    TAS.state.replace(b);
    return TAS.state.evaluate();
  }
  function check(group, name, got, want) {
    var ok = JSON.stringify(got) === JSON.stringify(want);
    if (ok) pass++; else fail++;
    (groups[group] = groups[group] || []).push({ name: name, got: got, want: want, ok: ok });
  }
  function grounds(r) { return r.triggers.map(function (t) { return t.provision; }); }
  function req(r) { return r.required.map(function (x) { return x.field; }); }

  /* ---- 1. Sample cases ------------------------------------------------- */
  TAS.samples.cases.forEach(function (c) {
    var r = run(c.input);
    check('Sample cases', c.id + ' ' + c.title, r.status, c.expect);
  });

  /* ---- 2. The boundary case that exposed the 0/0 stall -------------------
   * Turnover ₹1,00,00,000; receipts, payments and cash all 0; profit and total
   * income ₹5,00,000. The old engine stalled on 0/0. It must now ask only the
   * questions the law needs, then decide.                                   */
  var U = { turnover: '10000000', totalReceipts: '0', cashReceipts: '0', totalPayments: '0',
            cashPayments: '0', profit: '500000', totalIncome: '500000', clientName: 'Test Assessee' };
  var u1 = run(U);
  check('Nil-receipts boundary', 'As entered: asks only the s.44AD(4) bar question', req(u1), ['bar44AD']);
  check('Nil-receipts boundary', 'As entered: nil receipts treated as satisfying the cash test', u1.analysis.recOk, true);
  var u2 = run(Object.assign({}, U, { bar44AD: 'no' }));
  check('Nil-receipts boundary', 'Bar = no: profit 5% < 6% deemed, income > ₹4L, so asks prior-year use', req(u2), ['prior44AD']);
  var u3 = run(Object.assign({}, U, { bar44AD: 'no', prior44AD: 'no' }));
  check('Nil-receipts boundary', 'Never used s.44AD: NOT APPLICABLE', u3.status, NA);
  var u4 = run(Object.assign({}, U, { bar44AD: 'no', prior44AD: 'yes' }));
  check('Nil-receipts boundary', 'Used s.44AD earlier: APPLICABLE under s.44AB(e)', [u4.status].concat(grounds(u4)), [APP, 's. 44AB(e) with s. 44AD(4)']);

  /* ---- 3. s.44AB(a) boundaries (company — no presumptive route) -------- */
  function co(T, extra) {
    return run(Object.assign({ constitution: 'company', turnover: String(T),
      totalReceipts: String(T), cashReceipts: '0', totalPayments: String(T), cashPayments: '0' }, extra || {}));
  }
  check('s.44AB(a)', 'Exactly ₹1 crore, no cash figures needed', [co(10000000, { totalReceipts: '', cashReceipts: '', totalPayments: '', cashPayments: '' }).status], [NA]);
  check('s.44AB(a)', '₹1 crore + ₹1, cash 9% → ₹1 cr limit → APPLICABLE',
    co(10000001, { cashReceipts: '900000', cashPayments: '900000' }).status, APP);
  check('s.44AB(a)', '₹1 crore + ₹1, cash within 5% → ₹10 cr limit → NOT APPLICABLE', co(10000001).status, NA);
  check('s.44AB(a)', 'Exactly ₹10 crore, cash within 5%', co(100000000).status, NA);
  check('s.44AB(a)', '₹10 crore + ₹1 → APPLICABLE, cash test not needed',
    co(100000001, { totalReceipts: '', cashReceipts: '', totalPayments: '', cashPayments: '' }).status, APP);
  check('s.44AB(a)', '₹9,99,99,999 within ₹10 cr', co(99999999).status, NA);
  check('s.44AB(a)', 'Cash receipts exactly 5.00% keeps ₹10 cr limit',
    co(50000000, { cashReceipts: '2500000' }).status, NA);
  check('s.44AB(a)', 'Cash receipts 5.01% drops to ₹1 cr → APPLICABLE',
    co(50000000, { cashReceipts: '2505000' }).status, APP);
  check('s.44AB(a)', 'Cash payments 5.01% alone drops to ₹1 cr → APPLICABLE',
    co(50000000, { cashPayments: '2505000' }).status, APP);
  check('s.44AB(a)', 'Nil receipts and nil payments with turnover ₹5 cr → cash test met',
    co(50000000, { totalReceipts: '0', totalPayments: '0' }).status, NA);
  check('s.44AB(a)', '₹5 cr turnover, cash figures missing → asks exactly those four',
    req(co(50000000, { totalReceipts: '', cashReceipts: '', totalPayments: '', cashPayments: '' })),
    ['totalReceipts', 'cashReceipts', 'totalPayments', 'cashPayments']);

  /* ---- 4. First proviso — s.44AD (Finance Act 2023 s.15, s.16) ---------- */
  function trader(T, extra) {
    return run(Object.assign({ turnover: String(T), totalReceipts: String(T), cashReceipts: String(Math.round(T * 0.04)),
      totalPayments: String(T), cashPayments: String(Math.round(T * 0.12)),
      profit: String(Math.round(T * 0.09)), totalIncome: String(Math.round(T * 0.09)), bar44AD: 'no' }, extra || {}));
  }
  check('First proviso: s.44AD', '₹2.5 cr, cash rec 4% of turnover, pays 12%: asks whether declaring',
    req(trader(25000000)), ['declarePresumptive']);
  check('First proviso: s.44AD', '₹2.5 cr declaring under s.44AD(1) → NOT APPLICABLE',
    trader(25000000, { declarePresumptive: 'yes' }).status, NA);
  check('First proviso: s.44AD', '₹2.5 cr not declaring → APPLICABLE s.44AB(a)',
    grounds(trader(25000000, { declarePresumptive: 'no' })), ['s. 44AB(a)']);
  check('First proviso: s.44AD', 'Exactly ₹3 cr declaring → NOT APPLICABLE',
    trader(30000000, { declarePresumptive: 'yes' }).status, NA);
  check('First proviso: s.44AD', '₹3 cr + ₹1 → outside s.44AD → APPLICABLE, no declare question',
    [trader(30000001).status, req(trader(30000001)).length], [APP, 0]);
  check('First proviso: s.44AD', 'Ceiling uses cash RECEIPTS only: payments 12% do not block ₹3 cr',
    trader(28000000, { declarePresumptive: 'yes' }).analysis.ceilingLabel, '₹3 crore');
  check('First proviso: s.44AD', 'Cash receipts 5.01% of turnover → ₹2 cr ceiling → ₹2.5 cr APPLICABLE',
    trader(25000000, { cashReceipts: String(Math.round(25000000 * 0.0501)) }).status, APP);

  /* ---- 5. s.44AD deemed income (6% / 8% split) ---------------------------- */
  function small(profit, nonBanking) {
    return run({ turnover: '5000000', profit: String(profit), totalIncome: '900000', bar44AD: 'no',
                 turnoverNonBanking: nonBanking === undefined ? '' : String(nonBanking), prior44AD: 'yes' });
  }
  check('s.44AD deemed income', 'Profit exactly 8% → meets without the split', [small(400000).status, small(400000).analysis.meets], [NA, true]);
  check('s.44AD deemed income', 'Profit 7% → asks for the non-banking turnover', req(small(350000)), ['turnoverNonBanking']);
  check('s.44AD deemed income', 'Profit 7%, all turnover banked → deemed 6% → meets', small(350000, 0).analysis.meets, true);
  check('s.44AD deemed income', 'Profit 7%, all turnover in cash → deemed 8% → below → APPLICABLE (prior use)',
    small(350000, 5000000).status, APP);
  check('s.44AD deemed income', 'Profit ₹1 below 6% → below without the split', small(299999).analysis.meets, false);
  check('s.44AD deemed income', 'Deemed = 8% × non-banking + 6% × rest',
    small(350000, 1000000).analysis.deemed, 1000000 * 0.08 + 4000000 * 0.06);

  /* ---- 6. s.44AB(e) and the s.44AD(4) bar ----------------------------------- */
  check('s.44AB(e)', 'Opting out after prior use, income > exemption → APPLICABLE',
    grounds(run({ turnover: '9000000', profit: '200000', totalIncome: '900000', bar44AD: 'no', prior44AD: 'yes' })),
    ['s. 44AB(e) with s. 44AD(4)']);
  check('s.44AB(e)', 'Below deemed, never used s.44AD → NOT APPLICABLE',
    run({ turnover: '9000000', profit: '200000', totalIncome: '900000', bar44AD: 'no', prior44AD: 'no' }).status, NA);
  check('s.44AB(e)', 'Below deemed but income ≤ ₹4L → prior-year not asked, NOT APPLICABLE',
    [run({ turnover: '9000000', profit: '200000', totalIncome: '400000', bar44AD: 'no' }).status], [NA]);
  check('s.44AB(e)', 'Barred, turnover ₹40 lakh, income ₹4,00,001 → APPLICABLE',
    run({ turnover: '4000000', profit: '400001', totalIncome: '400001', bar44AD: 'yes' }).status, APP);
  check('s.44AB(e)', 'Barred, income exactly ₹4,00,000 → NOT APPLICABLE',
    run({ turnover: '4000000', profit: '400000', totalIncome: '400000', bar44AD: 'yes' }).status, NA);
  check('s.44AB(e)', 'Barred firm (nil exemption), income ₹1 → APPLICABLE',
    run({ constitution: 'firm', turnover: '4000000', profit: '1', totalIncome: '1', bar44AD: 'yes' }).status, APP);
  check('s.44AB(e)', 'Old regime below 60 (₹2.5L): income ₹3L after prior use → APPLICABLE',
    run({ turnover: '9000000', profit: '200000', totalIncome: '300000', exemptionOption: 'old-below-60', bar44AD: 'no', prior44AD: 'yes' }).status, APP);

  /* ---- 7. Profession: s.44AB(b), s.44AB(d), first proviso (FA 2023 s.17) --- */
  function prof(GR, extra) {
    return run(Object.assign({ nature: 'profession', professionCategory: 'medical', turnover: String(GR),
      cashReceipts: '0', profit: String(Math.round(GR * 0.6)), totalIncome: String(Math.round(GR * 0.6)) }, extra || {}));
  }
  check('Profession', 'Exactly ₹50 lakh, profit 60% → NOT APPLICABLE', prof(5000000).status, NA);
  check('Profession', '₹50 lakh + ₹1, cash nil → asks whether declaring', req(prof(5000001)), ['declarePresumptive']);
  check('Profession', '₹60 lakh declaring under s.44ADA(1) → NOT APPLICABLE', prof(6000000, { declarePresumptive: 'yes' }).status, NA);
  check('Profession', '₹60 lakh not declaring → APPLICABLE s.44AB(b)', grounds(prof(6000000, { declarePresumptive: 'no' })), ['s. 44AB(b)']);
  check('Profession', 'Exactly ₹75 lakh, cash ≤5%, declaring → NOT APPLICABLE', prof(7500000, { declarePresumptive: 'yes' }).status, NA);
  check('Profession', '₹75 lakh + ₹1 → APPLICABLE, no declare question', [prof(7500001).status, req(prof(7500001)).length], [APP, 0]);
  check('Profession', '₹60 lakh, cash 6% → ₹50L ceiling → APPLICABLE', prof(6000000, { cashReceipts: '360000' }).status, APP);
  check('Profession', 'REGRESSION: profit below 50%, no prior use → APPLICABLE s.44AB(d)',
    grounds(prof(3800000, { profit: '1500000', totalIncome: '1600000' })), ['s. 44AB(d) with s. 44ADA(4)']);
  check('Profession', 'Exactly ₹50 lakh, profit 40%, income > exemption → APPLICABLE s.44AB(d)',
    grounds(prof(5000000, { profit: '2000000', totalIncome: '2000000' })), ['s. 44AB(d) with s. 44ADA(4)']);
  check('Profession', 'Profit exactly 50% → NOT APPLICABLE', prof(4000000, { profit: '2000000' }).status, NA);
  check('Profession', 'Profit below 50%, income ≤ ₹4L → NOT APPLICABLE', prof(1000000, { profit: '300000', totalIncome: '400000' }).status, NA);
  check('Profession', 'Firm (nil exemption) below 50% → APPLICABLE s.44AB(d)',
    prof(3000000, { constitution: 'firm', profit: '1200000', totalIncome: '1200000' }).status, APP);
  check('Profession', 'REGRESSION: HUF cannot use s.44ADA → profit below 50% NOT APPLICABLE',
    prof(4000000, { constitution: 'huf', profit: '400000', totalIncome: '900000' }).status, NA);
  check('Profession', 'HUF ₹60 lakh → APPLICABLE s.44AB(b), no declare question',
    [prof(6000000, { constitution: 'huf' }).status, req(prof(6000000, { constitution: 'huf' })).length], [APP, 0]);
  check('Profession', 'Non-specified profession, below 50% → NOT APPLICABLE',
    prof(3000000, { professionCategory: 'other', profit: '300000', totalIncome: '900000' }).status, NA);
  check('Profession', 'Profession not classified → asks for it', req(prof(3000000, { professionCategory: '' })), ['professionCategory']);
  check('Profession', 'Non-resident individual → no s.44ADA', prof(3000000, { residentialStatus: 'non-resident', profit: '300000', totalIncome: '900000' }).status, NA);

  /* ---- 8. Eligibility exclusions for s.44AD --------------------------------- */
  ['commission-brokerage', 'agency-business', 'goods-carriage', 'chapter-via-deduction'].forEach(function (flag) {
    check('s.44AD exclusions', flag + ': below deemed after prior use → NOT APPLICABLE',
      run({ turnover: '9000000', profit: '200000', totalIncome: '900000', bar44AD: 'no', prior44AD: 'yes', flags: [flag] }).status, NA);
  });
  check('s.44AD exclusions', 'LLP ₹2.5 cr, cash > 5% → APPLICABLE, no bar question',
    [run({ constitution: 'llp', turnover: '25000000', totalReceipts: '25000000', cashReceipts: '2500000',
           totalPayments: '20000000', cashPayments: '100000' }).status],
    [APP]);
  check('s.44AB(c)', 's.44AE/44BB/44BBB declared lower → APPLICABLE',
    grounds(run({ constitution: 'company', turnover: '5000000', flags: ['lower-than-44ae-44bb'] })), ['s. 44AB(c)']);

  /* ---- 9. Decisive answers and validation ---------------------------------- */
  check('Flow', 'Individual ₹12 cr, nothing else answered → APPLICABLE at once',
    [run({ turnover: '120000000' }).status, run({ turnover: '120000000' }).required.length], [APP, 0]);
  /* With turnover unknown the presumptive path cannot yet be ruled out, so profit
     and total income are needed too — listed in page order. */
  check('Flow', 'Blank form → turnover, profit, income, bar question, in page order',
    req(run({})), ['turnover', 'profit', 'totalIncome', 'bar44AD']);
  check('Flow', 'Negative turnover → correction requested', run({ constitution: 'company', turnover: '-1' }).status, INC);
  var bad = run({ constitution: 'company', turnover: '50000000', totalReceipts: '100', cashReceipts: '200', totalPayments: '100', cashPayments: '0' });
  check('Flow', 'Cash > total → correction requested at cashReceipts', [bad.status, bad.required[0].field, !!bad.required[0].error], [INC, 'cashReceipts', true]);

  /* ---- 10. Forms and due dates ---------------------------------------------- */
  check('Forms & dates', 'Company → Form 3CA + 3CD', co(100000001).form.form, 'Form 3CA + Form 3CD');
  check('Forms & dates', 'Individual → Form 3CB + 3CD', run({ turnover: '120000000' }).form.form, 'Form 3CB + Form 3CD');
  check('Forms & dates', 'LLP audited under LLP Act → Form 3CA', run({ constitution: 'llp', turnover: '120000000', flags: ['audit-other-law'] }).form.form, 'Form 3CA + Form 3CD');
  var tp = run({ turnover: '120000000', flags: ['transfer-pricing'] });
  check('Forms & dates', 'Transfer pricing: report 31 Oct 2026, return 30 Nov 2026', [tp.dueDates.auditReport, tp.dueDates.itr], ['31 October 2026', '30 November 2026']);
  var nt = run({ turnover: '120000000' });
  check('Forms & dates', 'Otherwise: report 30 Sep 2026, return 31 Oct 2026', [nt.dueDates.auditReport, nt.dueDates.itr], ['30 September 2026', '31 October 2026']);

  /* ---- 11. Themes ----------------------------------------------------------- */
  ['light', 'dark', 'executive'].forEach(function (t) {
    TAS.state.applyTheme(t);
    check('Themes', t, document.documentElement.getAttribute('data-theme'), t);
  });
  TAS.state.applyTheme('light');

  return JSON.stringify({ summary: { pass: pass, fail: fail, total: pass + fail }, groups: groups });
})()
