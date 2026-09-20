/* =============================================================================
 * engine.js — Legal decision engine, AY 2026-27 (FY 2025-26)
 * Income-tax Act, 1961 as amended up to and including the Finance Act, 2025
 * -----------------------------------------------------------------------------
 * OUTCOMES
 *   APPLICABLE            at least one limb of s.44AB requires audit
 *   NOT APPLICABLE        no limb requires audit, or the first proviso takes
 *                         the person outside s.44AB altogether
 *   INFORMATION REQUIRED  a fact the law needs on THIS path has not been
 *                         entered. The engine names each one, says why it is
 *                         needed, and the interface takes the user to it.
 *
 * There is no "could not be concluded" outcome. Every question the law turns on
 * is asked explicitly, so once the answers are in, a conclusion follows.
 *
 * ASKS ONLY WHAT MATTERS
 * A fact is requested only when it can change the answer on these facts. A
 * trader with ₹60 lakh turnover is not asked for the cash split of receipts and
 * payments: at that turnover the s.44AB(a) limit cannot be crossed whichever
 * limit applies. Each shortcut below is a strict bound, noted where it is taken.
 *
 * STATUTORY BASIS (verified — see ruleset.js and legal/sources.md)
 *   s.44AB(a)  business turnover > ₹1 cr; ₹10 cr where cash receipts <= 5% of
 *              all receipts AND cash payments <= 5% of all payments
 *   s.44AB(b)  professional gross receipts > ₹50 lakh
 *   s.44AB(c)  s.44AE / 44BB / 44BBB income declared lower than deemed
 *   s.44AB(d)  s.44ADA applies and profit declared below 50%, and total income
 *              exceeds the basic exemption — NO prior-year condition
 *   s.44AB(e)  s.44AD(4) applicable and total income exceeds the basic exemption
 *   First proviso (FA 2023 s.15): s.44AB does not apply to a person who
 *              declares profits under s.44AD(1) or s.44ADA(1)
 *   s.44AD     ceiling ₹2 cr; ₹3 cr where cash receipts <= 5% of TURNOVER
 *              (FA 2023 s.16); deemed 6% of banking-channel turnover, 8% of rest
 *   s.44ADA    ceiling ₹50 lakh; ₹75 lakh where cash receipts <= 5% of GROSS
 *              RECEIPTS (FA 2023 s.17); deemed 50%; individual or non-LLP firm
 * ========================================================================== */

(function (global) {
  'use strict';

  var TAS = global.TAS || (global.TAS = {});
  var calc = TAS.calc;

  var STATUS = {
    APPLICABLE: 'APPLICABLE',
    NOT_APPLICABLE: 'NOT APPLICABLE',
    INCOMPLETE: 'INFORMATION REQUIRED'
  };

  /* Where each input lives in the interface, so a requirement can take the
     user straight to it. */
  var PANEL = {
    clientName: 'profile', constitution: 'profile', residentialStatus: 'profile',
    nature: 'profile', professionCategory: 'profile',
    turnover: 'financials', turnoverNonBanking: 'financials',
    totalReceipts: 'financials', cashReceipts: 'financials',
    totalPayments: 'financials', cashPayments: 'financials',
    profit: 'financials', totalIncome: 'financials', exemptionOption: 'financials',
    bar44AD: 'tests', prior44AD: 'tests', declarePresumptive: 'tests'
  };

  /* ===========================================================================
   * TEST RECORD
   *   kind    'limb'      — a clause of s.44AB that can itself require audit
   *           'condition' — a finding that feeds a limb (cash test, eligibility)
   *   status  limb:      'triggers' | 'clear' | 'excluded' | 'na' | 'pending'
   *           condition: 'met' | 'not-met' | 'na' | 'pending'
   * ======================================================================== */
  function test(o) {
    return {
      id: o.id, kind: o.kind, label: o.label, provision: o.provision || null,
      inputValue: o.inputValue === undefined || o.inputValue === null ? '—' : o.inputValue,
      thresholdLabel: o.thresholdLabel || '—',
      status: o.status,
      triggersAudit: o.kind === 'limb' && o.status === 'triggers',
      reason: o.reason, detail: o.detail || ''
    };
  }

  function Ctx(f, p) {
    this.f = f; this.p = p;
    this.required = []; this.notes = [];
  }
  Ctx.prototype.need = function (field, label, why) {
    for (var i = 0; i < this.required.length; i++) if (this.required[i].field === field) return;
    this.required.push({ field: field, panel: PANEL[field], label: label, why: why });
  };
  Ctx.prototype.note = function (heading, text, severity) {
    this.notes.push({ heading: heading, text: text, severity: severity || 'info' });
  };

  function hasFlag(f, id) { return f.flags.indexOf(id) !== -1; }
  function pct(n) { return calc.pct(n); }

  /* ===========================================================================
   * RATIO CALCULATIONS (display only — decisions use calc.cashWithin)
   * ======================================================================== */
  function calculateCashReceiptRatio(f) {
    var denom = f.nature === 'business' ? f.totalReceipts : f.turnover;
    return { value: calc.ratio(f.cashReceipts, denom) };
  }
  function calculateCashPaymentRatio(f) {
    return { value: calc.ratio(f.cashPayments, f.totalPayments) };
  }
  function calculateProfitRatio(f) {
    return { value: calc.ratio(f.profit, f.turnover) };
  }

  /* ===========================================================================
   * BUSINESS
   * ======================================================================== */
  function evaluateBusiness(ctx) {
    var f = ctx.f, p = ctx.p, c = f.constitutionMeta;
    var A = p.business44AB, D = p.section44AD;
    var T = f.turnover;
    var tests = [];
    var out = { tests: tests };

    if (T === null) ctx.need('turnover', 'Turnover', 'Every limb of s. 44AB(a) and s. 44AD is measured against turnover.');

    /* ---- 44AD eligibility — facts only, no figures ------------------------ */
    var exclusions = [];
    if (!c.can44AD) exclusions.push('a ' + c.label.toLowerCase() + ' is not an eligible assessee (resident individual, HUF or partnership firm other than LLP only)');
    if (c.can44AD && f.residentialStatus !== 'resident') exclusions.push('a non-resident is not an eligible assessee');
    TAS.ruleset.businessConditions.forEach(function (bc) {
      if (bc.effect === 'excludes44AD' && hasFlag(f, bc.id)) exclusions.push(bc.label.toLowerCase() + ' (' + bc.cite + ')');
    });
    var eligible = exclusions.length === 0;
    out.eligible = eligible;
    out.exclusions = exclusions;

    /* ---- s.44AB(a): which limit, and is it crossed ------------------------
     * Only a turnover strictly between ₹1 cr and ₹10 cr needs the cash test:
     * at or below ₹1 cr neither limit is crossed; above ₹10 cr both are.     */
    var needCashTestA = T !== null && T > A.baseLimit && T <= A.enhancedLimit;
    var recOk = calc.cashWithin(f.cashReceipts, f.totalReceipts, A.cashReceiptPct);
    var payOk = calc.cashWithin(f.cashPayments, f.totalPayments, A.cashPaymentPct);
    var cashMet = (recOk === null || payOk === null) ? null : (recOk && payOk);

    if (needCashTestA) {
      var why = 'Turnover of ' + calc.inr(T) + ' lies between ' + A.baseLimitLabel + ' and ' +
                A.enhancedLimitLabel + '. Which limit applies depends on the 5% cash test.';
      if (f.totalReceipts === null) ctx.need('totalReceipts', 'Total amounts received during the year', why);
      if (f.cashReceipts === null)  ctx.need('cashReceipts', 'Amounts received in cash', why);
      if (f.totalPayments === null) ctx.need('totalPayments', 'Total payments made during the year', why);
      if (f.cashPayments === null)  ctx.need('cashPayments', 'Payments made in cash', why);
    }

    var limit = null, limitLabel = null, breachA = null;
    if (T !== null) {
      if (T <= A.baseLimit) {
        breachA = false; limitLabel = A.baseLimitLabel + ' / ' + A.enhancedLimitLabel;
      } else if (T > A.enhancedLimit) {
        breachA = true; limitLabel = A.baseLimitLabel + ' / ' + A.enhancedLimitLabel;
      } else if (cashMet !== null) {
        limit = cashMet ? A.enhancedLimit : A.baseLimit;
        limitLabel = cashMet ? A.enhancedLimitLabel : A.baseLimitLabel;
        breachA = T > limit;
      }
    }
    out.cashMet = cashMet; out.recOk = recOk; out.payOk = payOk;
    out.limitLabel = limitLabel; out.breachA = breachA;
    out.limitValue = limit !== null ? limit : (T !== null && T <= A.baseLimit ? A.baseLimit : (T !== null && T > A.enhancedLimit ? A.enhancedLimit : null));

    tests.push(cashConditionTest('cash-receipt', 'Cash receipt condition', 'Proviso (a) to s. 44AB(a)',
      recOk, f.cashReceipts, f.totalReceipts, A.cashReceiptPct, 'all amounts received', needCashTestA, T, A));
    tests.push(cashConditionTest('cash-payment', 'Cash payment condition', 'Proviso (b) to s. 44AB(a)',
      payOk, f.cashPayments, f.totalPayments, A.cashPaymentPct, 'all payments made', needCashTestA, T, A));

    /* ---- s.44AB(c) -------------------------------------------------------- */
    var clauseC = hasFlag(f, 'lower-than-44ae-44bb');

    /* ---- 44AD ceiling ------------------------------------------------------
     * Only a turnover strictly between ₹2 cr and ₹3 cr needs the cash test.  */
    var needCeilingTest = eligible && T !== null && T > D.baseCeiling && T <= D.enhancedCeiling;
    var enhancedCeilingOk = calc.cashWithin(f.cashReceipts, T, D.enhancedCashPctOfTurnover);
    if (needCeilingTest && f.cashReceipts === null) {
      ctx.need('cashReceipts', 'Amounts received in cash',
        'Turnover of ' + calc.inr(T) + ' lies between ' + D.baseCeilingLabel + ' and ' + D.enhancedCeilingLabel +
        '. The s. 44AD ceiling depends on whether cash received is within 5% of turnover.');
    }
    var ceiling = null, ceilingLabel = null, withinCeiling = null;
    if (T !== null) {
      if (T <= D.baseCeiling) { withinCeiling = true; ceilingLabel = D.baseCeilingLabel + ' / ' + D.enhancedCeilingLabel; }
      else if (T > D.enhancedCeiling) { withinCeiling = false; ceilingLabel = D.baseCeilingLabel + ' / ' + D.enhancedCeilingLabel; }
      else if (enhancedCeilingOk !== null) {
        ceiling = enhancedCeilingOk ? D.enhancedCeiling : D.baseCeiling;
        ceilingLabel = enhancedCeilingOk ? D.enhancedCeilingLabel : D.baseCeilingLabel;
        withinCeiling = T <= ceiling;
      }
    }
    out.ceilingLabel = ceilingLabel; out.withinCeiling = withinCeiling;

    /* ---- s.44AD(4) bar ------------------------------------------------------ */
    var barred = false;
    if (c.can44AD) {
      if (!f.bar44AD) {
        ctx.need('bar44AD', 'Is AY 2026-27 within a five-year bar under s. 44AD(4)?',
          'If the assessee is barred, audit applies under s. 44AB(e) whenever total income exceeds the basic exemption — whatever the turnover.');
        barred = null;
      } else {
        barred = f.bar44AD === 'yes';
      }
    }
    out.barred = barred;

    /* ---- Is the presumptive scheme available this year? ------------------- */
    var live = null;
    if (!eligible || barred === true || withinCeiling === false) live = false;
    else if (withinCeiling === true && barred === false) live = true;
    out.live = live;

    /* ---- Profit and income are needed only where a low-profit limb can bite  */
    var incomeNeeded = c.can44AD && (live !== false || barred !== false);
    if (incomeNeeded && f.totalIncome === null) {
      ctx.need('totalIncome', 'Total income for the year',
        'The s. 44AB(e) limb applies only where total income exceeds the basic exemption limit.');
    }
    if (live !== false && c.can44AD && f.profit === null) {
      ctx.need('profit', 'Declared net profit',
        'Needed to test declared profit against the s. 44AD deemed income.');
    }

    var incomeOverBEL = f.totalIncome === null ? null : f.totalIncome > f.exemptionAmount;
    out.incomeOverBEL = incomeOverBEL;

    /* ---- Deemed income -----------------------------------------------------
     * 8% of turnover not received through banking channels by the s.139(1) due
     * date, 6% of the rest. The deemed amount therefore lies between 6% and 8%
     * of turnover. Where profit is at or above 8%, or below 6%, the comparison
     * is settled without the split, and it is not asked for.                 */
    var deemed = null, deemedLow = null, deemedHigh = null, meets = null;
    if (live === true && T !== null) {
      deemedLow = T * D.rateBanking / 100;
      deemedHigh = T * D.rateOther / 100;
      if (f.turnoverNonBanking !== null && f.turnoverNonBanking <= T) {
        deemed = f.turnoverNonBanking * D.rateOther / 100 + (T - f.turnoverNonBanking) * D.rateBanking / 100;
      }
      if (f.profit !== null) {
        if (deemed !== null) meets = f.profit >= deemed;
        else if (f.profit >= deemedHigh) meets = true;
        else if (f.profit < deemedLow) meets = false;
        else {
          ctx.need('turnoverNonBanking', 'Turnover not received through banking channels by the return due date',
            'Declared profit of ' + calc.inr(f.profit) + ' lies between 6% and 8% of turnover. Whether it meets the ' +
            's. 44AD deemed income depends on how much turnover was received other than by account-payee cheque, ' +
            'draft or electronic mode by the due date.');
        }
      }
    }
    out.deemed = deemed; out.deemedLow = deemedLow; out.deemedHigh = deemedHigh; out.meets = meets;

    /* ---- s.44AB(e), route 1: barred under s.44AD(4) ----------------------- */
    var eBarred = barred === true ? incomeOverBEL : false;

    /* ---- s.44AB(e), route 2: opting out THIS year after an earlier opt-in -- */
    var prior = null, eOptOut = false;
    if (live === true && meets === false && incomeOverBEL === true) {
      if (!f.prior44AD) {
        ctx.need('prior44AD', 'Was income declared under s. 44AD for any of ' + D.lookbackFrom + ' to ' + D.lookbackTo + '?',
          'Declared profit is below the s. 44AD deemed income and total income exceeds the basic exemption. If ' +
          's. 44AD was used in any of the five preceding assessment years, declaring less now attracts s. 44AD(4) ' +
          'and audit under s. 44AB(e).');
      } else {
        prior = f.prior44AD === 'yes';
        eOptOut = prior;
      }
    }
    out.prior = prior;

    /* ---- First proviso: declaring under s.44AD(1) takes the person out of
       s.44AB altogether. The choice is asked only where it changes the answer. */
    var canDeclare = live === true && meets === true;
    var firstProviso = false, declareMatters = false;
    if (canDeclare) {
      declareMatters = breachA === true || clauseC;
      if (declareMatters) {
        if (!f.declarePresumptive) {
          ctx.need('declarePresumptive', 'Will income be declared under s. 44AD(1) in the return?',
            (breachA === true ? 'Turnover exceeds the s. 44AB(a) limit' : 'A s. 44AB(c) trigger is present') +
            ', but declared profit meets the s. 44AD deemed income. Under the first proviso to s. 44AB, audit is ' +
            'excluded only if income is actually declared under s. 44AD(1).');
        } else {
          firstProviso = f.declarePresumptive === 'yes';
        }
      } else {
        firstProviso = f.declarePresumptive === 'yes';
      }
    }
    out.canDeclare = canDeclare; out.declareMatters = declareMatters; out.firstProviso = firstProviso;

    /* ---- Build the limb records ------------------------------------------- */
    tests.push(test({
      id: 'turnover-44ab-a', kind: 'limb', label: 'Turnover limb', provision: 's. 44AB(a)',
      inputValue: calc.inr(T), thresholdLabel: limitLabel || 'Depends on cash test',
      status: breachA === null ? 'pending' : (firstProviso && breachA ? 'excluded' : (breachA ? 'triggers' : 'clear')),
      reason: breachA === null ? 'Awaiting the cash test figures.'
        : T <= A.baseLimit ? 'Turnover of ' + calc.inr(T) + ' does not exceed ' + A.baseLimitLabel + ', so neither limit is crossed.'
        : T > A.enhancedLimit ? 'Turnover of ' + calc.inr(T) + ' exceeds ' + A.enhancedLimitLabel + ', so both limits are crossed.'
        : breachA ? 'Turnover of ' + calc.inr(T) + ' exceeds the applicable limit of ' + limitLabel + '.'
        : 'Turnover of ' + calc.inr(T) + ' is within the applicable limit of ' + limitLabel + '.',
      detail: breachA === null ? ''
        : (T > A.baseLimit && T <= A.enhancedLimit)
          ? (cashMet ? 'Both cash limbs are within 5%, so the ' + A.enhancedLimitLabel + ' limit applies.'
                     : 'A cash limb exceeds 5%, so the ' + A.baseLimitLabel + ' limit applies.')
          : 'The cash test cannot change the result at this turnover.'
    }));

    tests.push(test({
      id: 'clause-c', kind: 'limb', label: 's. 44AE / 44BB / 44BBB income', provision: 's. 44AB(c)',
      inputValue: clauseC ? 'Declared lower than deemed' : 'Not applicable', thresholdLabel: 'Deemed amount',
      status: clauseC ? (firstProviso ? 'excluded' : 'triggers') : 'na',
      reason: clauseC ? 'Income under s. 44AE / 44BB / 44BBB is declared lower than the deemed amount.'
                      : 'No s. 44AE, 44BB or 44BBB income is declared lower than the deemed amount.'
    }));

    tests.push(test({
      id: 'eligibility-44ad', kind: 'condition', label: 's. 44AD eligibility', provision: 's. 44AD, Explanation',
      inputValue: eligible ? 'Eligible' : 'Not eligible', thresholdLabel: 'Eligible assessee and business',
      status: eligible ? 'met' : 'not-met',
      reason: eligible ? 'The assessee and the business meet the s. 44AD eligibility conditions.'
                       : 'Not eligible for s. 44AD: ' + exclusions.join('; ') + '.',
      detail: eligible ? '' : 'Neither the presumptive scheme nor its low-profit limb applies. Only s. 44AB(a) governs.'
    }));

    if (eligible) {
      tests.push(test({
        id: 'ceiling-44ad', kind: 'condition', label: 's. 44AD turnover ceiling', provision: 's. 44AD, Explanation (b)',
        inputValue: calc.inr(T), thresholdLabel: ceilingLabel || 'Depends on cash receipts',
        status: withinCeiling === null ? 'pending' : (withinCeiling ? 'met' : 'not-met'),
        reason: withinCeiling === null ? 'Awaiting cash receipts.'
          : withinCeiling ? 'Turnover of ' + calc.inr(T) + ' is within the s. 44AD ceiling.'
          : 'Turnover of ' + calc.inr(T) + ' exceeds the s. 44AD ceiling, so the scheme is not available this year.',
        detail: (T !== null && T > D.baseCeiling && T <= D.enhancedCeiling && enhancedCeilingOk !== null)
          ? (enhancedCeilingOk ? 'Cash received is within 5% of turnover, so the ' + D.enhancedCeilingLabel + ' ceiling applies (Finance Act 2023).'
                               : 'Cash received exceeds 5% of turnover, so the ' + D.baseCeilingLabel + ' ceiling applies.')
          : ''
      }));
    }

    if (c.can44AD) {
      tests.push(test({
        id: 'bar-44ab-e', kind: 'limb', label: 's. 44AD(4) five-year bar', provision: 's. 44AB(e) with s. 44AD(4), (5)',
        inputValue: barred === null ? 'Not answered' : (barred ? 'Barred' : 'Not barred'),
        thresholdLabel: 'Total income over ' + (f.exemptionAmount === 0 ? 'nil' : calc.inr(f.exemptionAmount)),
        status: barred === null ? 'pending' : (!barred ? 'na' : (eBarred === null ? 'pending' : (eBarred ? 'triggers' : 'clear'))),
        reason: barred === null ? 'Awaiting the answer on the s. 44AD(4) bar.'
          : !barred ? 'AY 2026-27 is not within a s. 44AD(4) bar.'
          : eBarred === null ? 'Barred — awaiting total income.'
          : eBarred ? 'AY 2026-27 falls within a s. 44AD(4) bar and total income of ' + calc.inr(f.totalIncome) + ' exceeds the basic exemption.'
          : 'AY 2026-27 falls within a s. 44AD(4) bar, but total income does not exceed the basic exemption.',
        detail: barred ? 'During the five-year bar, audit applies in each year in which total income exceeds the basic ' +
          'exemption limit, whatever the turnover. This follows the literal reading of ss. 44AD(4), 44AD(5) and ' +
          '44AB(e), and the conservative professional position.' : ''
      }));
    }

    if (live === true) {
      var deemedText = deemed !== null ? calc.inr(deemed)
        : (deemedLow !== null ? calc.inr(deemedLow) + ' to ' + calc.inr(deemedHigh) : '—');
      /* When the exact split was not needed, name the bound that settled it. */
      var belowText = deemed !== null ? 'below the deemed income of ' + calc.inr(deemed)
        : 'below even the lowest possible deemed income, ' + calc.inr(deemedLow) + ' (6% of turnover)';
      var meetsText = deemed !== null ? 'meets the s. 44AD deemed income of ' + calc.inr(deemed)
        : 'is at least 8% of turnover (' + calc.inr(deemedHigh) + '), the highest the s. 44AD deemed income can be';
      tests.push(test({
        id: 'lowprofit-44ab-e', kind: 'limb', label: 'Low-profit limb (opting out)', provision: 's. 44AB(e) with s. 44AD(4)',
        inputValue: f.profit === null ? '—' : calc.inr(f.profit),
        thresholdLabel: 'Deemed ' + deemedText,
        status: meets === null ? 'pending'
          : meets ? 'clear'
          : incomeOverBEL === null ? 'pending'
          : !incomeOverBEL ? 'clear'
          : prior === null ? 'pending'
          : prior ? 'triggers' : 'clear',
        reason: meets === null ? 'Awaiting figures to compare declared profit with the deemed income.'
          : meets ? 'Declared profit of ' + calc.inr(f.profit) + ' ' + meetsText + '.'
          : !incomeOverBEL ? 'Declared profit is below the deemed income, but total income does not exceed the basic exemption.'
          : prior === null ? 'Declared profit is below the deemed income and total income exceeds the basic exemption — awaiting prior-year history.'
          : prior ? 'Income was declared under s. 44AD in an earlier year. Declaring ' + calc.inr(f.profit) +
                    ' now, ' + belowText + ', attracts s. 44AD(4). Total income exceeds the basic exemption.'
          : 's. 44AD was not used in any of the five preceding years, so declaring below the deemed income does not attract s. 44AD(4).',
        detail: (meets === false && prior === true)
          ? 'Audit is required under s. 44AB(e). The assessee is also barred from s. 44AD for the next five assessment years.'
          : (meets === false && prior === false)
            ? 'Caution for the client: opting into s. 44AD in a later year and then declaring below the deemed rate would attract s. 44AD(4).'
            : ''
      }));
    }

    tests.push(test({
      id: 'first-proviso', kind: 'limb', label: 'Declared under s. 44AD(1)', provision: 'First proviso to s. 44AB',
      inputValue: !canDeclare ? 'Not available' : (f.declarePresumptive === 'yes' ? 'Yes' : f.declarePresumptive === 'no' ? 'No' : 'Not answered'),
      thresholdLabel: 'Declared under s. 44AD(1)',
      status: !canDeclare ? 'na' : (firstProviso ? 'excluded' : (declareMatters && !f.declarePresumptive ? 'pending' : 'na')),
      reason: !canDeclare ? (live === false
          ? 'The s. 44AD scheme is not available on these facts.'
          : 'Declared profit does not meet the s. 44AD deemed income, so income cannot be declared under s. 44AD(1).')
        : firstProviso ? 'Income is declared under s. 44AD(1). Section 44AB does not apply to the assessee (Finance Act 2023).'
        : declareMatters && !f.declarePresumptive ? 'Awaiting the choice of whether to declare under s. 44AD(1).'
        : declareMatters ? 'Income will not be declared under s. 44AD(1), so the first proviso does not apply.'
        : 'Declaring under s. 44AD(1) is available but does not change the outcome here.'
    }));

    return out;
  }

  function cashConditionTest(id, label, provision, ok, cash, total, pctCap, of, needed, T, A) {
    var value = (cash !== null && total !== null) ? (total > 0 ? pct(cash / total * 100) : (cash === 0 ? '0.00% (nil of nil)' : '—')) : '—';
    if (ok === null) {
      return test({ id: id, kind: 'condition', label: label, provision: provision,
        inputValue: value, thresholdLabel: 'Not exceeding ' + pctCap + '% of ' + of,
        status: needed ? 'pending' : 'na',
        reason: needed ? 'Awaiting figures.'
          : (T !== null && T <= A.baseLimit)
            ? 'Not required: turnover does not exceed ' + A.baseLimitLabel + ', so the cash test cannot change the result.'
            : (T !== null && T > A.enhancedLimit)
              ? 'Not required: turnover exceeds ' + A.enhancedLimitLabel + ', so the cash test cannot change the result.'
              : 'Not required on these facts.' });
    }
    return test({ id: id, kind: 'condition', label: label, provision: provision,
      inputValue: value, thresholdLabel: 'Not exceeding ' + pctCap + '% of ' + of,
      status: ok ? 'met' : 'not-met',
      reason: ok ? 'Cash of ' + calc.inr(cash) + ' does not exceed ' + pctCap + '% of ' + of + ' (' + calc.inr(total) + ').'
                 : 'Cash of ' + calc.inr(cash) + ' exceeds ' + pctCap + '% of ' + of + ' (' + calc.inr(total) + ').',
      detail: ok ? '' : 'The enhanced ' + A.enhancedLimitLabel + ' limit is not available.' });
  }

  /* ===========================================================================
   * PROFESSION
   * ======================================================================== */
  function evaluateProfession(ctx) {
    var f = ctx.f, p = ctx.p, c = f.constitutionMeta;
    var B = p.profession44AB, P = p.section44ADA;
    var GR = f.turnover;
    var tests = [];
    var out = { tests: tests };

    if (GR === null) ctx.need('turnover', 'Gross receipts', 'Both s. 44AB(b) and s. 44ADA are measured against gross receipts.');

    /* ---- s.44AB(b) --------------------------------------------------------- */
    var breachB = GR === null ? null : GR > B.limit;
    out.breachB = breachB;

    /* ---- 44ADA eligibility -------------------------------------------------- */
    var exclusions = [];
    if (!c.can44ADA) exclusions.push('a ' + c.label.toLowerCase() + ' cannot use s. 44ADA (resident individual or partnership firm other than LLP only)');
    if (c.can44ADA && f.residentialStatus !== 'resident') exclusions.push('a non-resident cannot use s. 44ADA');
    var prof = TAS.ruleset.professionById(f.professionCategory);
    if (c.can44ADA && f.residentialStatus === 'resident') {
      if (!prof) {
        ctx.need('professionCategory', 'Classification of the profession',
          'Only a profession referred to in s. 44AA(1), or notified under it, can use s. 44ADA.');
      } else if (!prof.specified) {
        exclusions.push('the profession is not one referred to in s. 44AA(1) or notified under it');
      }
    }
    var eligible = exclusions.length === 0 && (!!prof || !c.can44ADA || f.residentialStatus !== 'resident');
    if (c.can44ADA && f.residentialStatus === 'resident' && !prof) eligible = null;
    out.eligible = eligible; out.exclusions = exclusions;

    /* ---- 44ADA ceiling — only ₹50–75 lakh needs the cash test ------------- */
    var needCeilingTest = eligible !== false && GR !== null && GR > P.baseCeiling && GR <= P.enhancedCeiling;
    var enhancedOk = calc.cashWithin(f.cashReceipts, GR, P.enhancedCashPct);
    if (needCeilingTest && f.cashReceipts === null) {
      ctx.need('cashReceipts', 'Amounts received in cash',
        'Gross receipts of ' + calc.inr(GR) + ' lie between ' + P.baseCeilingLabel + ' and ' + P.enhancedCeilingLabel +
        '. The s. 44ADA ceiling depends on whether cash received is within 5% of gross receipts.');
    }
    var withinCeiling = null, ceilingLabel = null;
    if (GR !== null) {
      if (GR <= P.baseCeiling) { withinCeiling = true; ceilingLabel = P.baseCeilingLabel + ' / ' + P.enhancedCeilingLabel; }
      else if (GR > P.enhancedCeiling) { withinCeiling = false; ceilingLabel = P.baseCeilingLabel + ' / ' + P.enhancedCeilingLabel; }
      else if (enhancedOk !== null) {
        ceilingLabel = enhancedOk ? P.enhancedCeilingLabel : P.baseCeilingLabel;
        withinCeiling = GR <= (enhancedOk ? P.enhancedCeiling : P.baseCeiling);
      }
    }
    out.withinCeiling = withinCeiling; out.ceilingLabel = ceilingLabel;

    var live = null;
    if (eligible === false || withinCeiling === false) live = false;
    else if (eligible === true && withinCeiling === true) live = true;
    out.live = live;

    /* ---- Deemed income and the s.44AB(d) limb ----------------------------- */
    if (live !== false && c.can44ADA) {
      if (f.profit === null) ctx.need('profit', 'Declared net profit', 'Needed to test declared profit against 50% of gross receipts under s. 44ADA.');
      if (f.totalIncome === null) ctx.need('totalIncome', 'Total income for the year', 'The s. 44AB(d) limb applies only where total income exceeds the basic exemption limit.');
    }
    var deemed = GR === null ? null : GR * P.rate / 100;
    var meets = (live === true && f.profit !== null && deemed !== null) ? f.profit >= deemed : null;
    var incomeOverBEL = f.totalIncome === null ? null : f.totalIncome > f.exemptionAmount;
    out.deemed = live === true ? deemed : null; out.meets = meets; out.incomeOverBEL = incomeOverBEL;

    var dTrigger = (live === true && meets === false) ? incomeOverBEL : false;

    /* ---- First proviso ------------------------------------------------------ */
    var canDeclare = live === true && meets === true;
    var declareMatters = canDeclare && breachB === true;
    var firstProviso = false;
    if (canDeclare) {
      if (declareMatters && !f.declarePresumptive) {
        ctx.need('declarePresumptive', 'Will income be declared under s. 44ADA(1) in the return?',
          'Gross receipts exceed ' + B.limitLabel + ', but are within the s. 44ADA ceiling and profit meets 50%. Under the ' +
          'first proviso to s. 44AB, audit is excluded only if income is actually declared under s. 44ADA(1).');
      }
      firstProviso = f.declarePresumptive === 'yes';
    }
    out.canDeclare = canDeclare; out.declareMatters = declareMatters; out.firstProviso = firstProviso;

    /* ---- Limb records ------------------------------------------------------- */
    tests.push(test({
      id: 'receipts-44ab-b', kind: 'limb', label: 'Gross receipts limb', provision: 's. 44AB(b)',
      inputValue: calc.inr(GR), thresholdLabel: B.limitLabel,
      status: breachB === null ? 'pending' : (firstProviso && breachB ? 'excluded' : (breachB ? 'triggers' : 'clear')),
      reason: breachB === null ? 'Awaiting gross receipts.'
        : breachB ? 'Gross receipts of ' + calc.inr(GR) + ' exceed ' + B.limitLabel + '.'
        : 'Gross receipts of ' + calc.inr(GR) + ' do not exceed ' + B.limitLabel + '.',
      detail: 'No cash-percentage relief applies to this limb. Relief up to ' + P.enhancedCeilingLabel +
              ' is available only by declaring under s. 44ADA(1) — first proviso to s. 44AB.'
    }));

    var elig = live === null && eligible === null ? 'pending' : (eligible ? 'met' : 'not-met');
    tests.push(test({
      id: 'eligibility-44ada', kind: 'condition', label: 's. 44ADA eligibility', provision: 's. 44ADA(1)',
      inputValue: eligible === null ? 'Not answered' : (eligible ? 'Eligible' : 'Not eligible'),
      thresholdLabel: 'Resident individual / non-LLP firm; s. 44AA(1) profession',
      status: eligible === null ? 'pending' : elig,
      reason: eligible === null ? 'Awaiting the classification of the profession.'
        : eligible ? 'Eligible for s. 44ADA: ' + (prof ? prof.label.toLowerCase() + ' profession' : '') + '.'
        : 'Not eligible for s. 44ADA: ' + exclusions.join('; ') + '.',
      detail: eligible === false ? 'Neither the presumptive scheme nor s. 44AB(d) applies. Only s. 44AB(b) governs.' : ''
    }));

    if (eligible === true) {
      tests.push(test({
        id: 'ceiling-44ada', kind: 'condition', label: 's. 44ADA gross receipts ceiling', provision: 's. 44ADA(1) and proviso',
        inputValue: calc.inr(GR), thresholdLabel: ceilingLabel || 'Depends on cash receipts',
        status: withinCeiling === null ? 'pending' : (withinCeiling ? 'met' : 'not-met'),
        reason: withinCeiling === null ? 'Awaiting cash receipts.'
          : withinCeiling ? 'Gross receipts are within the s. 44ADA ceiling.'
          : 'Gross receipts exceed the s. 44ADA ceiling, so the scheme is not available.',
        detail: (GR !== null && GR > P.baseCeiling && GR <= P.enhancedCeiling && enhancedOk !== null)
          ? (enhancedOk ? 'Cash received is within 5% of gross receipts, so the ' + P.enhancedCeilingLabel + ' ceiling applies (Finance Act 2023).'
                        : 'Cash received exceeds 5% of gross receipts, so the ' + P.baseCeilingLabel + ' ceiling applies.')
          : ''
      }));

      tests.push(test({
        id: 'lowprofit-44ab-d', kind: 'limb', label: 'Low-profit limb', provision: 's. 44AB(d) with s. 44ADA(4)',
        inputValue: f.profit === null ? '—' : calc.inr(f.profit),
        thresholdLabel: live === true ? '50% = ' + calc.inr(deemed) : 'Scheme not available',
        status: live === false ? 'na' : meets === null ? 'pending' : meets ? 'clear' : (dTrigger === null ? 'pending' : (dTrigger ? 'triggers' : 'clear')),
        reason: live === false ? 'The s. 44ADA scheme is not available, so this limb does not arise.'
          : meets === null ? 'Awaiting declared profit.'
          : meets ? 'Declared profit of ' + calc.inr(f.profit) + ' is not lower than 50% of gross receipts (' + calc.inr(deemed) + ').'
          : dTrigger === null ? 'Declared profit is below 50% — awaiting total income.'
          : dTrigger ? 'Declared profit of ' + calc.inr(f.profit) + ' is lower than 50% of gross receipts (' + calc.inr(deemed) +
                       ') and total income of ' + calc.inr(f.totalIncome) + ' exceeds the basic exemption.'
          : 'Declared profit is below 50%, but total income does not exceed the basic exemption.',
        detail: dTrigger ? 'Audit is required under s. 44AB(d). This limb has no prior-year condition: it applies in the first ' +
                           'year a lower profit is declared.' : ''
      }));
    }

    tests.push(test({
      id: 'first-proviso', kind: 'limb', label: 'Declared under s. 44ADA(1)', provision: 'First proviso to s. 44AB',
      inputValue: !canDeclare ? 'Not available' : (f.declarePresumptive === 'yes' ? 'Yes' : f.declarePresumptive === 'no' ? 'No' : 'Not answered'),
      thresholdLabel: 'Declared under s. 44ADA(1)',
      status: !canDeclare ? 'na' : (firstProviso ? 'excluded' : (declareMatters && !f.declarePresumptive ? 'pending' : 'na')),
      reason: !canDeclare ? (live === false ? 'The s. 44ADA scheme is not available on these facts.'
            : 'Declared profit is below 50% of gross receipts, so income cannot be declared under s. 44ADA(1).')
        : firstProviso ? 'Income is declared under s. 44ADA(1). Section 44AB does not apply to the assessee (Finance Act 2023).'
        : declareMatters && !f.declarePresumptive ? 'Awaiting the choice of whether to declare under s. 44ADA(1).'
        : declareMatters ? 'Income will not be declared under s. 44ADA(1), so the first proviso does not apply.'
        : 'Declaring under s. 44ADA(1) is available but does not change the outcome here.'
    }));

    return out;
  }

  /* ===========================================================================
   * FORM, DATES, OTHER-LAW
   * ======================================================================== */
  function evaluateOtherLawAudit(f) {
    var byConstitution = !!(f.constitutionMeta && f.constitutionMeta.auditedOtherLaw);
    var byDeclaration = hasFlag(f, 'audit-other-law');
    return { audited: byConstitution || byDeclaration, source: byConstitution ? 'constitution' : (byDeclaration ? 'declared' : null) };
  }

  function determineAuditForm(f, p, otherLaw) {
    var form = otherLaw.audited ? p.forms.auditedUnderOtherLaw : p.forms.otherCases;
    var reason = otherLaw.audited
      ? (otherLaw.source === 'constitution'
          ? 'The accounts of a ' + f.constitutionMeta.label.toLowerCase() + ' are audited under another law, so the report is furnished in ' + form + '.'
          : 'The accounts are audited under another law, so the report is furnished in ' + form + '.')
      : 'The accounts are not audited under any other law, so the report is furnished in ' + form + '.';
    var additional = hasFlag(f, 'transfer-pricing')
      ? [p.forms.transferPricing + ' applies in addition, on account of transfer pricing.'] : [];
    return { form: form, reason: reason, additional: additional };
  }

  /* ===========================================================================
   * TOP LEVEL
   * ======================================================================== */
  function evaluate(facts, ruleset) {
    var p = ruleset.forAssessmentYear(facts.assessmentYear);
    var ctx = new Ctx(facts, p);
    var isBusiness = facts.nature === 'business';
    var validation = TAS.validation.validate(facts);

    var an = isBusiness ? evaluateBusiness(ctx) : evaluateProfession(ctx);
    var tests = an.tests;

    /* Validation errors are also requirements: the user is taken to the field. */
    validation.errors.forEach(function (e) {
      ctx.required.unshift({ field: e.field, panel: PANEL[e.field] || 'financials', label: 'Correct this figure', why: e.message, error: true });
    });

    /* Present what is still needed in the order the fields appear on the page,
       corrections first, so "Go to" walks the user down the form. */
    var ORDER = ['clientName', 'constitution', 'residentialStatus', 'nature', 'professionCategory',
                 'turnover', 'turnoverNonBanking', 'totalReceipts', 'cashReceipts', 'totalPayments', 'cashPayments',
                 'profit', 'totalIncome', 'exemptionOption', 'bar44AD', 'prior44AD', 'declarePresumptive'];
    ctx.required.sort(function (a, b) {
      if (!!a.error !== !!b.error) return a.error ? -1 : 1;
      return ORDER.indexOf(a.field) - ORDER.indexOf(b.field);
    });

    var triggers = tests.filter(function (t) { return t.triggersAudit; });
    var otherLaw = evaluateOtherLawAudit(facts);
    var form = determineAuditForm(facts, p, otherLaw);
    var tp = hasFlag(facts, 'transfer-pricing');

    /* A trigger is DECISIVE when nothing still unanswered could remove it. The
       only thing that removes a trigger is the first proviso, which needs the
       presumptive scheme to be available AND declared profit to meet the deemed
       income. Once either is ruled out, the remaining questions can only add
       further grounds — so the answer is given now and they become notes. */
    var decisive = triggers.length > 0 && validation.errors.length === 0 &&
                   (an.live === false || an.meets === false);
    if (decisive && ctx.required.length) {
      ctx.note('Further grounds not examined',
        'Audit already applies on the ground stated. These were not needed for the conclusion and were not answered: ' +
        ctx.required.map(function (r) { return r.label.replace(/\?$/, ''); }).join('; ') +
        '. Answer them if every ground is to be recorded in the working paper.', 'info');
      ctx.required = [];
    }

    var status, statusReason;
    if (ctx.required.length) {
      status = STATUS.INCOMPLETE;
      statusReason = ctx.required.length === 1
        ? 'One more answer is needed to reach the decision.'
        : ctx.required.length + ' more answers are needed to reach the decision.';
    } else if (an.firstProviso) {
      status = STATUS.NOT_APPLICABLE;
      statusReason = 'Income is declared under ' + (isBusiness ? 's. 44AD(1)' : 's. 44ADA(1)') +
                     ', so under the first proviso section 44AB does not apply to the assessee.';
    } else if (triggers.length) {
      status = STATUS.APPLICABLE;
      statusReason = 'Audit is required under ' + triggers.map(function (t) { return t.provision; }).join(' and ') + '.';
    } else {
      status = STATUS.NOT_APPLICABLE;
      statusReason = 'No limb of section 44AB applies on these facts.';
    }

    /* Professional notes — never block the decision. */
    validation.cautions.forEach(function (w) { ctx.note('Confirm', w.message, 'low'); });
    if (facts.constitutionMeta && facts.constitutionMeta.note) ctx.note(facts.constitutionMeta.label, facts.constitutionMeta.note, 'info');
    TAS.ruleset.generalConditions.forEach(function (gc) {
      if (hasFlag(facts, gc.id) && gc.effect === 'note') ctx.note(gc.label, gc.note, 'medium');
    });
    if (an.barred === true) {
      ctx.note('Five-year bar under s. 44AD(4)',
        'Audit is treated as required in every barred year in which total income exceeds the basic exemption, whatever the ' +
        'turnover. This is the literal reading and the conservative professional position; record the years of the bar on file.', 'medium');
    }
    if (isBusiness && an.canDeclare && !an.declareMatters) {
      ctx.note('Presumptive option', 'Income may be declared under s. 44AD(1), but the outcome is the same either way on these facts.', 'info');
    }
    if (!isBusiness && an.canDeclare && !an.declareMatters) {
      ctx.note('Presumptive option', 'Income may be declared under s. 44ADA(1), but the outcome is the same either way on these facts.', 'info');
    }
    ctx.note('Section 44AA', 'The obligation to maintain books of account under s. 44AA is separate from audit and is not evaluated here.', 'info');

    var d = {
      cashReceiptRatio: calculateCashReceiptRatio(facts),
      cashPaymentRatio: calculateCashPaymentRatio(facts),
      profitRatio: calculateProfitRatio(facts),
      nonCashReceipts: calc.residual(isBusiness ? facts.totalReceipts : facts.turnover, facts.cashReceipts),
      nonCashPayments: calc.residual(facts.totalPayments, facts.cashPayments),
      presumptiveIncome: an.live === true ? (an.deemed !== null && an.deemed !== undefined ? an.deemed : null) : null,
      deemedLow: an.deemedLow || null, deemedHigh: an.deemedHigh || null
    };

    var thresholdTest = tests.filter(function (t) { return t.id === 'turnover-44ab-a' || t.id === 'receipts-44ab-b'; })[0];
    var lowProfitTest = tests.filter(function (t) { return t.id === 'lowprofit-44ab-e' || t.id === 'lowprofit-44ab-d'; })[0] || null;

    return {
      status: status,
      statusReason: statusReason,
      isBusiness: isBusiness,
      facts: facts,
      params: p,
      validation: validation,
      required: ctx.required,
      tests: tests,
      triggers: an.firstProviso ? [] : triggers,
      notes: ctx.notes,
      analysis: an,
      thresholdTest: thresholdTest,
      lowProfitTest: lowProfitTest,
      otherLaw: otherLaw,
      form: form,
      dueDates: {
        auditReport: tp ? p.dueDates.auditReportTP : p.dueDates.auditReport,
        itr: tp ? p.dueDates.itrTP : p.dueDates.itr,
        note: p.dueDates.note
      },
      derived: d,
      evaluatedAt: new Date().toISOString()
    };
  }

  TAS.engine = {
    STATUS: STATUS,
    PANEL: PANEL,
    evaluate: evaluate,
    evaluateBusiness: evaluateBusiness,
    evaluateProfession: evaluateProfession,
    calculateCashReceiptRatio: calculateCashReceiptRatio,
    calculateCashPaymentRatio: calculateCashPaymentRatio,
    calculateProfitRatio: calculateProfitRatio,
    evaluateOtherLawAudit: evaluateOtherLawAudit,
    determineAuditForm: determineAuditForm
  };

})(window);
