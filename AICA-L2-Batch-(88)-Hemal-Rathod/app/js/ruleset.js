/* =============================================================================
 * ruleset.js — Legal parameter set
 * Tax Audit Applicability Decision System | T R S & Associates
 * -----------------------------------------------------------------------------
 * Every statutory threshold, rate, percentage and due date used anywhere in this
 * application lives in this file and nowhere else.
 *
 * VERIFICATION STATUS — AY 2026-27 (FY 2025-26)
 * ---------------------------------------------
 * Cross-checked on 18 September 2026 against primary and official sources:
 *
 *   Finance Act, 2023 (Act 8 of 2023), Gazette text, sections 15, 16 and 17 —
 *     s.15  substitutes the first proviso to s.44AB (44AD / 44ADA declarers
 *           outside s.44AB), w.e.f. 1-4-2024
 *     s.16  inserts the Rs 3 crore proviso in s.44AD, Explanation (b) —
 *           condition is cash RECEIPTS not exceeding 5% of TURNOVER
 *     s.17  inserts the Rs 75 lakh proviso in s.44ADA(1) — cash RECEIPTS not
 *           exceeding 5% of GROSS RECEIPTS
 *   Finance (No. 2) Act, 2024 — full text searched: no amendment to ss.44AB,
 *     44AD or 44ADA
 *   Finance Act, 2025 (Act 7 of 2025) — full text searched: no amendment to
 *     ss.44AB, 44AD or 44ADA; s.115BAC(1A)(iii) nil slab up to Rs 4,00,000 for
 *     AY 2026-27 onwards; First Schedule old-regime nil slab Rs 2,50,000
 *   Income Tax Department e-filing portal — the Income-tax Act, 1961 continues
 *     to govern FY 2025-26 / AY 2026-27; s.44AD open to resident individual,
 *     HUF and firm (not LLP); s.44ADA open to resident individual and firm
 *     (not LLP) — an HUF is NOT eligible for s.44ADA
 *
 * Full citation record: legal/sources.md.
 *
 * The final professional sign-off remains with the Chartered Accountant using
 * this tool — complete `caSignOff` below once satisfied.
 * ========================================================================== */

(function (global) {
  'use strict';

  var TAS = global.TAS || (global.TAS = {});

  var verification = {
    researchedOn: '18 September 2026',
    researchSummary:
      'Cross-checked against the Finance Act 2023 (ss. 15-17), the Finance (No. 2) ' +
      'Act 2024 and the Finance Act 2025 (no amendment to ss. 44AB, 44AD or 44ADA), ' +
      'and the Income Tax Department e-filing portal.',
    caSignOff: {
      signedOn: null,     // e.g. '20 September 2026'
      signedBy: null      // e.g. 'CA <Name>, M.No. <xxxxxx>'
    }
  };

  var byAssessmentYear = {

    'AY 2026-27': {
      financialYear: 'FY 2025-26',
      act: 'Income-tax Act, 1961',

      /* ---- s.44AB(a) — business ------------------------------------------
       * Proviso to clause (a): Rs 10 crore where BOTH (a) all amounts received
       * in cash do not exceed 5% of all amounts received, AND (b) all payments
       * made in cash do not exceed 5% of all payments. A cheque or draft that is
       * not account payee is deemed cash.                                     */
      business44AB: {
        baseLimit: 10000000,
        enhancedLimit: 100000000,
        baseLimitLabel: '₹1 crore',
        enhancedLimitLabel: '₹10 crore',
        cashReceiptPct: 5,
        cashPaymentPct: 5
      },

      /* ---- s.44AB(b) — profession ---------------------------------------- */
      profession44AB: {
        limit: 5000000,
        limitLabel: '₹50 lakh'
      },

      /* ---- s.44AD — presumptive, business --------------------------------
       * Explanation (b) + FA 2023 proviso: ceiling Rs 3 crore where amounts
       * received in cash do not exceed 5% of total turnover; else Rs 2 crore.
       * s.44AD(1): 6% on turnover received by account-payee cheque / draft /
       * ECS / prescribed electronic mode during the year or before the s.139(1)
       * due date; 8% on the rest.                                             */
      section44AD: {
        baseCeiling: 20000000,
        enhancedCeiling: 30000000,
        baseCeilingLabel: '₹2 crore',
        enhancedCeilingLabel: '₹3 crore',
        enhancedCashPctOfTurnover: 5,
        rateBanking: 6,
        rateOther: 8,
        barYears: 5,
        lookbackFrom: 'AY 2021-22',
        lookbackTo: 'AY 2025-26'
      },

      /* ---- s.44ADA — presumptive, profession ------------------------------
       * s.44ADA(1) + FA 2023 proviso: Rs 75 lakh where amounts received in
       * cash do not exceed 5% of gross receipts; else Rs 50 lakh. 50% deemed. */
      section44ADA: {
        baseCeiling: 5000000,
        enhancedCeiling: 7500000,
        baseCeilingLabel: '₹50 lakh',
        enhancedCeilingLabel: '₹75 lakh',
        enhancedCashPct: 5,
        rate: 50
      },

      /* ---- Maximum amount not chargeable to tax -------------------------
       * Used only on the low-profit limbs, s.44AB(d) and (e).
       * FA 2025: s.115BAC(1A)(iii) nil up to Rs 4,00,000 (AY 2026-27 onwards).
       * First Schedule (old regime): Rs 2,50,000; resident individual 60-79
       * Rs 3,00,000; 80 and above Rs 5,00,000.
       * Firms have no slab exemption.                                        */
      basicExemption: {
        options: [
          { id: 'new-regime',   label: 'New regime (s. 115BAC, default)', amount: 400000, appliesTo: ['individual', 'huf'] },
          { id: 'old-below-60', label: 'Old regime',                      amount: 250000, appliesTo: ['individual', 'huf'] },
          { id: 'old-60-79',    label: 'Old regime, resident aged 60-79', amount: 300000, appliesTo: ['individual'], residentOnly: true },
          { id: 'old-80-plus',  label: 'Old regime, resident aged 80+',   amount: 500000, appliesTo: ['individual'], residentOnly: true }
        ]
      },

      /* ---- Due dates ------------------------------------------------------
       * s.139(1) Explanation 2; s.44AB Explanation — "specified date" is one
       * month before the s.139(1) due date. No CBDT extension for AY 2026-27
       * was reported as on 16 September 2026.                                */
      dueDates: {
        auditReport: '30 September 2026',
        auditReportTP: '31 October 2026',
        itr: '31 October 2026',
        itrTP: '30 November 2026',
        note: 'Statutory dates. No CBDT extension had been reported for AY 2026-27 as on 16 September 2026 — confirm before filing.'
      },

      forms: {
        auditedUnderOtherLaw: 'Form 3CA + Form 3CD',
        otherCases: 'Form 3CB + Form 3CD',
        transferPricing: 'Form 3CEB'
      }
    }
  };

  /* ---------------------------------------------------------------------------
   * CONSTITUTIONS
   * ------------------------------------------------------------------------ */
  var constitutions = [
    { id: 'individual', label: 'Individual',
      can44AD: true,  can44ADA: true,  hasBEL: true,  auditedOtherLaw: false },
    { id: 'huf', label: 'Hindu Undivided Family (HUF)',
      can44AD: true,  can44ADA: false, hasBEL: true,  auditedOtherLaw: false,
      note: 'An HUF may use s. 44AD, but not s. 44ADA — that scheme is open only to a resident individual or a partnership firm other than an LLP.' },
    { id: 'firm', label: 'Partnership firm (not LLP)',
      can44AD: true,  can44ADA: true,  hasBEL: false, auditedOtherLaw: false,
      note: 'A firm has no basic exemption. On the low-profit limbs, any positive total income exceeds the limit.' },
    { id: 'llp', label: 'Limited Liability Partnership (LLP)',
      can44AD: false, can44ADA: false, hasBEL: false, auditedOtherLaw: false,
      note: 'An LLP is excluded from ss. 44AD and 44ADA. Only the turnover / gross receipts limb of s. 44AB applies. Tick "audited under another law" if an LLP Act audit applies.' },
    { id: 'company', label: 'Company',
      can44AD: false, can44ADA: false, hasBEL: false, auditedOtherLaw: true,
      note: 'A company is outside ss. 44AD and 44ADA. Its accounts are audited under the Companies Act, 2013, so the report is in Form 3CA.' },
    { id: 'aop', label: 'AOP / BOI / Trust / AJP',
      can44AD: false, can44ADA: false, hasBEL: false, auditedOtherLaw: false,
      note: 'Outside ss. 44AD and 44ADA. Only the turnover / gross receipts limb applies. A trust or institution may have a separate audit requirement under its own provisions, which this tool does not evaluate.' },
    { id: 'coop', label: 'Co-operative society',
      can44AD: false, can44ADA: false, hasBEL: false, auditedOtherLaw: true,
      note: 'Outside ss. 44AD and 44ADA. Audited under the co-operative societies law, so the report is in Form 3CA.' }
  ];

  /* ---------------------------------------------------------------------------
   * PROFESSIONS — s.44AA(1) and those notified under it.
   * Only these can use s.44ADA.
   * ------------------------------------------------------------------------ */
  var professionCategories = [
    { id: 'legal',                label: 'Legal',                          specified: true },
    { id: 'medical',              label: 'Medical',                        specified: true },
    { id: 'engineering',          label: 'Engineering',                    specified: true },
    { id: 'architectural',        label: 'Architectural',                  specified: true },
    { id: 'accountancy',          label: 'Accountancy',                    specified: true },
    { id: 'technical-consultancy', label: 'Technical consultancy',         specified: true },
    { id: 'interior-decoration',  label: 'Interior decoration',            specified: true },
    { id: 'authorised-representative', label: 'Authorised representative (notified)', specified: true },
    { id: 'film-artist',          label: 'Film artist (notified)',         specified: true },
    { id: 'company-secretary',    label: 'Company secretary (notified)',   specified: true },
    { id: 'information-technology', label: 'Information technology (notified)', specified: true },
    { id: 'other',                label: 'Any other profession (not specified in s. 44AA(1))', specified: false }
  ];

  /* ---------------------------------------------------------------------------
   * BUSINESS CONDITIONS
   * `excludes44AD` — the business or assessee falls outside s.44AD.
   * `clauseC`      — triggers s.44AB(c).
   * `note`         — informational only; does not change the decision.
   * ------------------------------------------------------------------------ */
  var businessConditions = [
    { id: 'commission-brokerage', label: 'Income in the nature of commission or brokerage',
      effect: 'excludes44AD', cite: 's. 44AD(6)(ii)',
      note: 'Excluded from s. 44AD. The presumptive scheme and its low-profit limb do not apply.' },
    { id: 'agency-business', label: 'Agency business',
      effect: 'excludes44AD', cite: 's. 44AD(6)(iii)',
      note: 'Excluded from s. 44AD. The presumptive scheme and its low-profit limb do not apply.' },
    { id: 'goods-carriage', label: 'Plying, hiring or leasing of goods carriages (s. 44AE business)',
      effect: 'excludes44AD', cite: 's. 44AD, Explanation (b)(ii)',
      note: 'A s. 44AE business is not an "eligible business" for s. 44AD.' },
    { id: 'chapter-via-deduction', label: 'Deduction claimed u/s 10A, 10AA, 10B, 10BA or Chapter VI-A Part C (80-IA to 80-RRB)',
      effect: 'excludes44AD', cite: 's. 44AD, Explanation (a)(ii)',
      note: 'An assessee claiming these deductions is not an "eligible assessee" for s. 44AD.' },
    { id: 'lower-than-44ae-44bb', label: 'Income under s. 44AE / 44BB / 44BBB declared lower than the deemed amount',
      effect: 'clauseC', cite: 's. 44AB(c)',
      note: 'Audit is required under s. 44AB(c).' }
  ];

  var generalConditions = [
    { id: 'audit-other-law', label: 'Accounts audited under another law (e.g. LLP Act, a State law)',
      effect: 'form3CA',
      note: 'Where accounts are audited under another law, the tax audit report is furnished in Form 3CA with Form 3CD.' },
    { id: 'transfer-pricing', label: 'International / specified domestic transaction — Form 3CEB applies',
      effect: 'tp',
      note: 'Form 3CEB applies in addition. The audit report is due one month later and the return by 30 November 2026.' },
    { id: 'derivatives', label: 'Futures & options, derivatives or speculative transactions',
      effect: 'note',
      note: 'Enter turnover computed as prescribed in the ICAI Guidance Note on Tax Audit, not the contract value.' },
    { id: 'multiple-activities', label: 'More than one business, or business and profession together',
      effect: 'note',
      note: 'Enter aggregate figures for all businesses. Where the assessee also carries on a profession, evaluate the business and the profession separately — s. 44AB(a) and (b) are tested independently.' }
  ];

  /* ---------------------------------------------------------------------------
   * ACCESSORS
   * ------------------------------------------------------------------------ */
  function assessmentYears() { return Object.keys(byAssessmentYear); }

  function forAssessmentYear(ay) {
    var set = byAssessmentYear[ay];
    if (!set) {
      throw new Error('No legal parameter set is defined for ' + ay +
        '. Add a block to app/js/ruleset.js before preparing a working paper for that year.');
    }
    return set;
  }

  function find(list, id) {
    for (var i = 0; i < list.length; i++) if (list[i].id === id) return list[i];
    return null;
  }

  function isSignedOff() {
    return !!(verification.caSignOff.signedOn && verification.caSignOff.signedBy);
  }

  function verificationStatement(ay) {
    var set = ay ? byAssessmentYear[ay] : null;
    var s = (set ? set.financialYear + ' / ' + ay + ' under the ' + set.act + '. ' : '') +
            'Thresholds cross-checked on ' + verification.researchedOn + ' against the Finance Act 2023 (ss. 15-17), ' +
            'the Finance (No. 2) Act 2024 and the Finance Act 2025 (no amendment to ss. 44AB, 44AD or 44ADA), and the ' +
            'Income Tax Department e-filing portal.';
    s += isSignedOff()
      ? ' Signed off by ' + verification.caSignOff.signedBy + ' on ' + verification.caSignOff.signedOn + '.'
      : ' CA sign-off: pending.';
    return s;
  }

  TAS.ruleset = {
    verification: verification,
    assessmentYears: assessmentYears,
    forAssessmentYear: forAssessmentYear,
    constitutions: constitutions,
    constitutionById: function (id) { return find(constitutions, id); },
    professionCategories: professionCategories,
    professionById: function (id) { return find(professionCategories, id); },
    businessConditions: businessConditions,
    generalConditions: generalConditions,
    conditionById: function (id) { return find(businessConditions, id) || find(generalConditions, id); },
    isSignedOff: isSignedOff,
    verificationStatement: verificationStatement
  };

})(window);
