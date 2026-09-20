/* =============================================================================
 * state.js — Application state, fact normalisation, theme, audit trail
 * -----------------------------------------------------------------------------
 * The UI owns raw form values. The engine only ever sees the normalised FACTS
 * object produced here.
 * ========================================================================== */

(function (global) {
  'use strict';

  var TAS = global.TAS || (global.TAS = {});
  var calc = TAS.calc;

  var THEME_KEY = 'trs.taxaudit.theme';
  var THEMES = ['light', 'dark', 'executive'];

  /* Amount fields are strings so that "not entered" survives round trips.
     Yes/no questions use 'yes' | 'no' | '' (not yet answered). */
  function blankInput() {
    return {
      clientName: '',
      pan: '',
      assessmentYear: 'AY 2026-27',
      constitution: 'individual',
      residentialStatus: 'resident',
      nature: 'business',
      professionCategory: '',

      turnover: '',
      turnoverNonBanking: '',
      totalReceipts: '',
      cashReceipts: '',
      totalPayments: '',
      cashPayments: '',
      profit: '',
      totalIncome: '',
      exemptionOption: 'new-regime',

      bar44AD: '',
      prior44AD: '',
      declarePresumptive: '',

      flags: [],

      preparedBy: '',
      reviewedBy: ''
    };
  }

  var input = blankInput();

  function get() { return input; }
  function set(patch) { Object.keys(patch).forEach(function (k) { input[k] = patch[k]; }); }
  function replace(next) { input = Object.assign(blankInput(), next); input.flags = (next.flags || []).slice(); }
  function reset() { input = blankInput(); }

  function toggleFlag(id, on) {
    var i = input.flags.indexOf(id);
    if (on && i === -1) input.flags.push(id);
    if (!on && i !== -1) input.flags.splice(i, 1);
  }

  /* ---------------------------------------------------------------------------
   * FACTS — the normalised object handed to the engine
   * ------------------------------------------------------------------------ */
  function facts() {
    var rs = TAS.ruleset;
    var params = rs.forAssessmentYear(input.assessmentYear);
    var c = rs.constitutionById(input.constitution) || rs.constitutions[0];
    var isBusiness = input.nature === 'business';

    /* The basic exemption only exists for an individual or HUF. For every
       other constitution it is nil, and the selector is not shown. */
    var option = null;
    if (c.hasBEL) {
      params.basicExemption.options.forEach(function (o) {
        if (o.id === input.exemptionOption && o.appliesTo.indexOf(c.id) !== -1 &&
            (!o.residentOnly || input.residentialStatus === 'resident')) option = o;
      });
      if (!option) option = params.basicExemption.options[0];
    }

    return {
      clientName: input.clientName,
      pan: input.pan,
      assessmentYear: input.assessmentYear,
      financialYear: params.financialYear,
      constitution: c.id,
      constitutionMeta: c,
      residentialStatus: input.residentialStatus,
      nature: input.nature,
      professionCategory: isBusiness ? '' : input.professionCategory,

      turnover: calc.amount(input.turnover),
      turnoverNonBanking: isBusiness ? calc.amount(input.turnoverNonBanking) : null,
      totalReceipts: isBusiness ? calc.amount(input.totalReceipts) : null,
      cashReceipts: calc.amount(input.cashReceipts),
      totalPayments: isBusiness ? calc.amount(input.totalPayments) : null,
      cashPayments: isBusiness ? calc.amount(input.cashPayments) : null,
      profit: calc.amount(input.profit),
      totalIncome: calc.amount(input.totalIncome),

      exemptionOption: option ? option.id : null,
      exemptionLabel: option ? option.label : 'Nil — no slab exemption for this constitution',
      exemptionAmount: option ? option.amount : 0,

      bar44AD: isBusiness ? input.bar44AD : '',
      prior44AD: isBusiness ? input.prior44AD : '',
      declarePresumptive: input.declarePresumptive,

      flags: input.flags.slice(),

      preparedBy: input.preparedBy,
      reviewedBy: input.reviewedBy
    };
  }

  function evaluate() {
    return TAS.engine.evaluate(facts(), TAS.ruleset);
  }

  /* ---------------------------------------------------------------------------
   * THEME — persisted per browser; the app renders without storage too.
   * ------------------------------------------------------------------------ */
  function readTheme() {
    try {
      var t = global.localStorage.getItem(THEME_KEY);
      if (t && THEMES.indexOf(t) !== -1) return t;
    } catch (e) { /* storage unavailable */ }
    return 'light';
  }
  function applyTheme(t) {
    if (THEMES.indexOf(t) === -1) return;
    document.documentElement.setAttribute('data-theme', t);
    try { global.localStorage.setItem(THEME_KEY, t); } catch (e) { /* ignore */ }
  }

  /* ---------------------------------------------------------------------------
   * AUDIT TRAIL
   * ------------------------------------------------------------------------ */
  function auditTrail(result) {
    var f = result.facts, rs = TAS.ruleset;
    return {
      document: 'Tax Audit Applicability — calculation audit trail',
      firm: 'T R S & Associates, Chartered Accountants',
      application: 'Tax Audit Applicability Decision System',
      generatedAt: new Date().toISOString(),
      law: {
        act: result.params.act,
        period: f.financialYear + ' / ' + f.assessmentYear,
        verification: rs.verificationStatement(f.assessmentYear),
        caSignOff: rs.verification.caSignOff
      },
      assessee: {
        name: f.clientName || null,
        pan: f.pan || null,
        constitution: f.constitutionMeta.label,
        residentialStatus: f.residentialStatus,
        nature: f.nature,
        profession: f.nature === 'profession' ? f.professionCategory || null : null
      },
      inputs: {
        turnoverOrGrossReceipts: f.turnover,
        turnoverNotThroughBankingByDueDate: f.turnoverNonBanking,
        totalAmountsReceived: f.totalReceipts,
        amountsReceivedInCash: f.cashReceipts,
        totalPayments: f.totalPayments,
        paymentsInCash: f.cashPayments,
        declaredProfit: f.profit,
        totalIncome: f.totalIncome,
        basicExemption: { basis: f.exemptionLabel, amount: f.exemptionAmount },
        barredUnder44AD4: f.bar44AD || null,
        used44ADInPrecedingFiveYears: f.prior44AD || null,
        declaringUnderPresumptive: f.declarePresumptive || null,
        conditionsTicked: f.flags
      },
      computed: {
        cashReceiptPct: result.derived.cashReceiptRatio.value,
        cashPaymentPct: result.derived.cashPaymentRatio.value,
        profitPct: result.derived.profitRatio.value,
        presumptiveIncome: result.derived.presumptiveIncome
      },
      testsEvaluated: result.tests.map(function (t) {
        return { id: t.id, provision: t.provision, input: t.inputValue, threshold: t.thresholdLabel,
                 status: t.status, finding: t.reason };
      }),
      groundsForAudit: result.triggers.map(function (t) { return t.provision + ' — ' + t.reason; }),
      outstanding: result.required.map(function (r) { return r.label; }),
      notes: result.notes.map(function (n) { return n.heading + ': ' + n.text; }),
      result: {
        status: result.status,
        reason: result.statusReason,
        form: result.form.form,
        formReason: result.form.reason,
        auditReportDue: result.dueDates.auditReport,
        returnDue: result.dueDates.itr
      },
      signOff: { preparedBy: f.preparedBy || null, reviewedBy: f.reviewedBy || null },
      disclaimer: 'Decision-support output. Not a substitute for independent examination of the Act, Rules, ' +
                  'Finance Act amendments, CBDT notifications and circulars, judicial precedents, ICAI Guidance ' +
                  'Notes and the facts of the assessee.'
    };
  }

  TAS.state = {
    blankInput: blankInput, get: get, set: set, replace: replace, reset: reset,
    toggleFlag: toggleFlag, facts: facts, evaluate: evaluate,
    readTheme: readTheme, applyTheme: applyTheme, THEMES: THEMES,
    auditTrail: auditTrail
  };

})(window);
