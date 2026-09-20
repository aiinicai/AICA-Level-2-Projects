/* =============================================================================
 * reasoning.js — Narrative and statutory reference generation
 * -----------------------------------------------------------------------------
 * Three kinds of content, never mixed:
 *   statutoryText            the words of the provision, with the source they
 *                            were taken from
 *   practicalInterpretation  the firm's plain-language explanation — always
 *                            labelled "Simplified professional explanation"
 *   applicationToFacts       how the entered figures meet or fail the condition
 *
 * STATUTORY TEXT — PROVENANCE
 * Text marked [Gazette] was read from the Finance Act, 2023 as published in
 * the Gazette of India. Text marked [Consolidated] was read from the
 * consolidated Income-tax Act, 1961 on Indian Kanoon. Where connecting words
 * could not be read cleanly, "[...]" marks the gap — nothing is filled in from
 * memory. Where no verbatim text was obtained, the value is null and the card
 * says "Not reproduced".
 * ========================================================================== */

(function (global) {
  'use strict';

  var TAS = global.TAS || (global.TAS = {});
  var calc = TAS.calc;

  var statutoryTexts = {
    '44AB(a)': {
      text: 'Clause (a): "carrying on business shall, if his total sales, turnover or gross receipts, as the case may be, ' +
            'in business exceed or exceeds one crore rupees in any previous year" [...] "Provided that in the case of a ' +
            'person whose— (a) aggregate of all amounts received including amount received for sales, turnover or gross ' +
            'receipts during the previous year, in cash, does not exceed five per cent of the said amount; and (b) ' +
            'aggregate of all payments made including amount incurred for expenditure, in cash, during the previous year ' +
            'does not exceed five per cent of the said payment" [...] "the words \'ten crore rupees\' had been ' +
            'substituted" [...] "Provided further that for the purposes of this clause, the payment or receipt, as the ' +
            'case may be, by a cheque drawn on a bank or by a bank draft, which is not account payee, shall be deemed to ' +
            'be the payment or receipt, as the case may be, in cash"',
      source: 'Income-tax Act, 1961, s. 44AB(a) and its provisos [Consolidated]. "[...]" marks words not reproduced.'
    },
    '44AB(b)': {
      text: 'Clause (b): "carrying on profession shall, if his gross receipts in profession exceed fifty lakh rupees in any previous year"',
      source: 'Income-tax Act, 1961, s. 44AB(b) [Consolidated].'
    },
    '44AB(c)': {
      text: 'Clause (c): "carrying on the business shall, if the profits and gains from the business are deemed to be the ' +
            'profits and gains of such person under section 44AE or section 44BB or section 44BBB, as the case may be, ' +
            'and he has claimed his income to be lower than the profits or gains so deemed to be the profits and gains of ' +
            'his business, as the case may be, in any previous year"',
      source: 'Income-tax Act, 1961, s. 44AB(c) [Consolidated].'
    },
    '44AB(d)': {
      text: 'Clause (d): "carrying on the profession shall, if the profits and gains from the profession are deemed to be ' +
            'the profits and gains of such person under section 44ADA and he has claimed such income to be lower than the ' +
            'profits and gains so deemed to be the profits and gains of his profession and his income exceeds the maximum ' +
            'amount which is not chargeable to income-tax in any previous year"',
      source: 'Income-tax Act, 1961, s. 44AB(d) [Consolidated].'
    },
    '44AB(e)': {
      text: 'Clause (e): "carrying on the business shall, if the provisions of sub-section (4) of section 44AD are ' +
            'applicable in his case and his income exceeds the maximum amount which is not chargeable to income-tax" [...]',
      source: 'Income-tax Act, 1961, s. 44AB(e) [Consolidated]. "[...]" marks words not reproduced.'
    },
    '44AB-first-proviso': {
      text: '"Provided that this section shall not apply to a person, who declares profits and gains for the previous ' +
            'year in accordance with the provisions of sub-section (1) of section 44AD or sub-section (1) of section 44ADA:"',
      source: 'Finance Act, 2023 (Act 8 of 2023), s. 15, substituting the first proviso to s. 44AB w.e.f. 1 April 2024 [Gazette].'
    },
    '44AD-ceiling': {
      text: '"Provided that where the amount or aggregate of the amounts received during the previous year, in cash, ' +
            'does not exceed five per cent. of the total turnover or gross receipts of such previous year, this ' +
            'sub-clause shall have effect as if for the words "two crore rupees", the words "three crore rupees" had been ' +
            'substituted: Provided further that for the purposes of the first proviso, the receipt of amount or aggregate ' +
            'of amounts by a cheque drawn on a bank or by a bank draft, which is not account payee, shall be deemed to be ' +
            'the receipt in cash."',
      source: 'Finance Act, 2023, s. 16, inserting provisos in s. 44AD, Explanation, clause (b), w.e.f. 1 April 2024 [Gazette].'
    },
    '44ADA-ceiling': {
      text: '"Provided that in case of an assessee where the amount or aggregate of the amounts received during the ' +
            'previous year, in cash, does not exceed five per cent. of the total gross receipts of such previous year, ' +
            'this sub-section shall have effect as if for the words "fifty lakh rupees", the words "seventy-five lakh ' +
            'rupees" had been substituted: Provided further that for the purposes of the first proviso, the receipt of ' +
            'amount or aggregate of amounts by a cheque drawn on a bank or by a bank draft, which is not account payee, ' +
            'shall be deemed to be the receipt in cash."',
      source: 'Finance Act, 2023, s. 17, inserting provisos in s. 44ADA(1), w.e.f. 1 April 2024 [Gazette].'
    }
  };

  function statutory(key) { return statutoryTexts[key] || null; }

  function find(tests, id) {
    for (var i = 0; i < tests.length; i++) if (tests[i].id === id) return tests[i];
    return null;
  }

  function withArticle(noun) {
    return ('aeiou'.indexOf(noun.charAt(0)) !== -1 ? 'an ' : 'a ') + noun;
  }

  /* ===========================================================================
   * REASONING CHAIN
   * ======================================================================== */
  var STEP_STATUS = { triggers: 'trigger', clear: 'ok', excluded: 'ok', na: 'info', pending: 'review',
                      met: 'ok', 'not-met': 'warn' };

  function generateReasoning(result) {
    var f = result.facts;
    var steps = [];
    var n = 0;
    function step(heading, value, provision, status, text) {
      n += 1;
      steps.push({ number: n, heading: heading, value: value, provision: provision, status: status || 'info', text: text });
    }

    step('Assessee and activity',
      (result.isBusiness ? 'Business' : 'Profession'),
      result.isBusiness ? 's. 44AB(a)' : 's. 44AB(b)', 'info',
      'The assessee is ' + withArticle(f.constitutionMeta.label.toLowerCase()) + ', ' +
      (f.residentialStatus === 'resident' ? 'resident' : 'non-resident') + ', carrying on ' +
      (result.isBusiness ? 'business' : 'a profession') + '. The Income-tax Act, 1961 governs ' +
      f.financialYear + ' (' + f.assessmentYear + ').');

    result.tests.forEach(function (t) {
      step(t.label, t.inputValue, t.provision, STEP_STATUS[t.status] || 'info',
           t.reason + (t.detail ? ' ' + t.detail : ''));
    });

    if (result.status === TAS.engine.STATUS.APPLICABLE) {
      step('Report form', result.form.form, null, 'info',
           result.form.reason + (result.form.additional.length ? ' ' + result.form.additional.join(' ') : ''));
    }
    return steps;
  }

  /* ===========================================================================
   * CONCLUSION
   * ======================================================================== */
  function generateConclusion(result) {
    var S = TAS.engine.STATUS;
    var f = result.facts;
    var an = result.analysis;
    var who = f.constitutionMeta.label.toLowerCase();
    var period = f.financialYear + ' (' + f.assessmentYear + ')';
    var scheme = result.isBusiness ? 's. 44AD(1)' : 's. 44ADA(1)';

    if (result.status === S.INCOMPLETE) {
      return {
        headline: 'Information required',
        lead: result.statusReason + ' Each item below says why it matters — select one to go straight to it.',
        grounds: [], reasons: [], body: [],
        consequences: [],
        caveat: ''
      };
    }

    if (result.status === S.APPLICABLE) {
      var grounds = result.triggers.map(function (t) { return { provision: t.provision, reason: t.reason }; });
      var cons = [
        'The accounts are required to be audited by a Chartered Accountant in practice.',
        'The report is to be furnished in ' + result.form.form + ' by ' + result.dueDates.auditReport + '.',
        'The return of income is due by ' + result.dueDates.itr + '.'
      ].concat(result.form.additional);
      if (result.triggers.some(function (t) { return t.id === 'lowprofit-44ab-e'; })) {
        cons.push('Under s. 44AD(4) the assessee is barred from s. 44AD for the next five assessment years; in each of them ' +
                  'audit applies where total income exceeds the basic exemption.');
      }
      return {
        headline: 'Tax audit is applicable',
        lead: 'On the information entered, tax audit under section 44AB of the Income-tax Act, 1961 is applicable to the ' +
              who + ' for ' + period + '.',
        grounds: grounds, reasons: [],
        body: ['Audit is required on the following ground' + (grounds.length > 1 ? 's' : '') + ':'],
        consequences: cons,
        caveat: 'This conclusion is drawn on the figures and answers entered. It is subject to the accuracy of those ' +
                'figures and to any fact not captured here.'
      };
    }

    /* NOT APPLICABLE */
    var reasons = [];
    if (an.firstProviso) {
      reasons.push('The assessee is eligible for ' + (result.isBusiness ? 's. 44AD' : 's. 44ADA') + ', and ' +
                   (result.isBusiness ? 'turnover' : 'gross receipts') + ' of ' + calc.inr(f.turnover) +
                   ' are within the ' + an.ceilingLabel + ' ceiling.');
      reasons.push('Declared profit of ' + calc.inr(f.profit) + ' is not lower than the deemed income' +
                   (an.deemed ? ' of ' + calc.inr(an.deemed) : '') + '.');
      reasons.push('Income is declared under ' + scheme + '. Under the first proviso to s. 44AB, as substituted by the ' +
                   'Finance Act, 2023, section 44AB does not apply to such a person.');
      return {
        headline: 'Tax audit is not applicable',
        lead: 'On the information entered, tax audit under section 44AB is not applicable to the ' + who + ' for ' +
              period + ', because income is declared under ' + scheme + '.',
        grounds: [], reasons: reasons,
        body: ['This conclusion rests on the following findings:'],
        consequences: [
          'Income must actually be offered under ' + scheme + ' in the return. If it is not, this conclusion does not hold.',
          result.isBusiness
            ? 'If, in any of the next five assessment years, profit is declared below the s. 44AD deemed rate, s. 44AD(4) will bar the scheme and require audit wherever total income exceeds the basic exemption.'
            : 'If, in a later year, profit below 50% of gross receipts is declared while s. 44ADA applies, audit will be required under s. 44AB(d) wherever total income exceeds the basic exemption.',
          'The obligation to maintain books of account under s. 44AA is separate and has not been evaluated.',
          'Retain this working paper with the supporting registers.'
        ],
        caveat: 'This conclusion is drawn on the figures and answers entered and depends on the presumptive declaration ' +
                'being made in the return.'
      };
    }

    result.tests.forEach(function (t) {
      if (t.status === 'clear' || (t.status === 'na' && t.kind === 'limb' && t.id !== 'first-proviso')) {
        reasons.push(t.provision + ': ' + t.reason);
      }
    });
    return {
      headline: 'Tax audit is not applicable',
      lead: 'On the information entered, tax audit under section 44AB of the Income-tax Act, 1961 is not applicable to the ' +
            who + ' for ' + period + '.',
      grounds: [], reasons: reasons,
      body: ['Each limb of section 44AB was examined:'],
      consequences: [
        'No tax audit report is required for this year.',
        'The obligation to maintain books of account under s. 44AA is separate and has not been evaluated.',
        'Retain this working paper with the supporting registers as evidence of the examination.'
      ],
      caveat: 'This conclusion is drawn on the figures and answers entered. If the figures change before the return is ' +
              'filed, re-run the determination.'
    };
  }

  /* ===========================================================================
   * STATUTORY REFERENCE CARDS
   * ======================================================================== */
  function conclusionFor(t) {
    if (!t) return { text: 'Not reached on these facts.', status: 'na' };
    if (t.status === 'triggers') return { text: 'Audit required on this limb.', status: 'breached' };
    if (t.status === 'excluded') return { text: 'Excluded by the first proviso.', status: 'satisfied' };
    if (t.status === 'clear') return { text: 'No audit on this limb.', status: 'satisfied' };
    if (t.status === 'pending') return { text: 'Awaiting information.', status: 'review' };
    if (t.status === 'met') return { text: 'Condition met.', status: 'satisfied' };
    if (t.status === 'not-met') return { text: 'Condition not met.', status: 'na' };
    return { text: 'Does not arise on these facts.', status: 'na' };
  }

  function generateLegalReferences(result) {
    var cards = [];
    var p = result.params, tests = result.tests, an = result.analysis;

    function card(o) {
      var st = statutory(o.key);
      var c = conclusionFor(o.test);
      /* On the proviso's own card, "excluded" means the proviso APPLIES. */
      if (o.key === '44AB-first-proviso' && o.test && o.test.status === 'excluded') {
        c = { text: 'The proviso applies — s. 44AB does not.', status: 'satisfied' };
      } else if (o.key === '44AB-first-proviso' && o.test && o.test.status === 'na') {
        c = { text: 'Does not apply on these facts.', status: 'na' };
      }
      cards.push({
        key: o.key, provision: o.provision, title: o.title,
        applicability: o.applicability,
        statutoryText: st ? st.text : null,
        statutorySource: st ? st.source : null,
        practicalInterpretation: o.practical,
        applicationToFacts: o.test ? (o.test.reason + (o.test.detail ? ' ' + o.test.detail : '')) : o.application,
        conclusion: o.conclusion || c.text,
        conclusionStatus: o.conclusionStatus || c.status
      });
    }

    var fp = find(tests, 'first-proviso');

    if (result.isBusiness) {
      card({ key: '44AB(a)', provision: 'Section 44AB(a)', title: 'Audit on turnover — business',
        test: find(tests, 'turnover-44ab-a'),
        applicability: 'A person carrying on business whose turnover in the previous year exceeds the limit.',
        practical: 'The limit is ' + p.business44AB.baseLimitLabel + '. It becomes ' + p.business44AB.enhancedLimitLabel +
                   ' only where BOTH cash received is within 5% of all amounts received AND cash paid is within 5% of all ' +
                   'payments. A cheque or draft that is not account payee counts as cash. A turnover exactly equal to the ' +
                   'limit does not exceed it.' });
      card({ key: '44AB-first-proviso', provision: 'First proviso to section 44AB', title: 'Presumptive declarants outside s. 44AB',
        test: fp,
        applicability: 'Any person who declares profits under s. 44AD(1) or s. 44ADA(1).',
        practical: 'Since AY 2024-25, a person declaring income under s. 44AD(1) is outside s. 44AB altogether — even if ' +
                   'turnover exceeds ₹1 crore — provided the business is within the s. 44AD ceiling (₹2 crore, or ₹3 crore ' +
                   'where cash receipts are within 5% of turnover) and the deemed income is declared.' });
      card({ key: '44AD-ceiling', provision: 'Section 44AD', title: 'Presumptive taxation — eligible business',
        test: find(tests, 'ceiling-44ad') || find(tests, 'eligibility-44ad'),
        applicability: 'A resident individual, HUF or partnership firm (not an LLP) carrying on an eligible business — ' +
                       'not commission or brokerage, not agency, not a s. 44AE goods-carriage business — and not claiming ' +
                       'the deductions listed in the Explanation.',
        practical: 'Deemed income is 6% of turnover received by account-payee cheque, draft or electronic mode during the ' +
                   'year or by the return due date, and 8% of the rest. The ceiling is ₹2 crore, raised to ₹3 crore where ' +
                   'cash received does not exceed 5% of turnover. Note the denominator here is TURNOVER, whereas the ' +
                   's. 44AB(a) test uses all amounts received.' });
      card({ key: '44AB(e)', provision: 'Section 44AB(e) with section 44AD(4)', title: 'Audit on leaving s. 44AD',
        test: find(tests, 'lowprofit-44ab-e') || find(tests, 'bar-44ab-e'),
        applicability: 'A person to whom s. 44AD(4) applies, where total income exceeds the basic exemption limit.',
        practical: 'Section 44AD(4) applies where the scheme was used in a year and, in any of the next five years, profit ' +
                   'is declared below the deemed rate. The assessee is then barred for five assessment years. Audit is ' +
                   'required in the year of opting out and — on the literal and conservative reading — in each barred ' +
                   'year, wherever total income exceeds the basic exemption, whatever the turnover. The verbatim text of ' +
                   's. 44AD(4) and (5) is not reproduced here; read it from the bare Act.' });
      if (find(tests, 'clause-c') && find(tests, 'clause-c').status !== 'na') {
        card({ key: '44AB(c)', provision: 'Section 44AB(c)', title: 'Audit on s. 44AE / 44BB / 44BBB income',
          test: find(tests, 'clause-c'),
          applicability: 'A person whose income is deemed under s. 44AE, 44BB or 44BBB and who declares a lower amount.',
          practical: 'Declaring less than the deemed income under these provisions requires audit, without any turnover limit.' });
      }
    } else {
      card({ key: '44AB(b)', provision: 'Section 44AB(b)', title: 'Audit on gross receipts — profession',
        test: find(tests, 'receipts-44ab-b'),
        applicability: 'A person carrying on a profession whose gross receipts in the previous year exceed the limit.',
        practical: 'The limit is a flat ' + p.profession44AB.limitLabel + ', with no cash relief in the clause itself. A ' +
                   'professional with receipts up to ₹75 lakh escapes audit only by declaring under s. 44ADA(1) — see the ' +
                   'first proviso.' });
      card({ key: '44AB-first-proviso', provision: 'First proviso to section 44AB', title: 'Presumptive declarants outside s. 44AB',
        test: fp,
        applicability: 'Any person who declares profits under s. 44AD(1) or s. 44ADA(1).',
        practical: 'Since AY 2024-25, a professional declaring under s. 44ADA(1) is outside s. 44AB altogether — even with ' +
                   'receipts above ₹50 lakh — provided receipts are within the s. 44ADA ceiling (₹50 lakh, or ₹75 lakh ' +
                   'where cash receipts are within 5%) and at least 50% is declared.' });
      card({ key: '44ADA-ceiling', provision: 'Section 44ADA', title: 'Presumptive taxation — specified profession',
        test: find(tests, 'ceiling-44ada') || find(tests, 'eligibility-44ada'),
        applicability: 'A resident individual or partnership firm (not an LLP) in a profession referred to in s. 44AA(1) ' +
                       'or notified under it. An HUF is not eligible.',
        practical: 'Deemed income is 50% of gross receipts. The ceiling is ₹50 lakh, raised to ₹75 lakh where cash received ' +
                   'does not exceed 5% of gross receipts.' });
      card({ key: '44AB(d)', provision: 'Section 44AB(d)', title: 'Audit on declaring below 50%',
        test: find(tests, 'lowprofit-44ab-d'),
        applicability: 'A professional within s. 44ADA who declares profit below 50% of gross receipts, where total income ' +
                       'exceeds the basic exemption.',
        practical: 'Unlike s. 44AB(e), this clause carries NO condition that the scheme was used in an earlier year. It bites ' +
                   'in the first year a lower profit is declared.' });
    }

    cards.push({
      key: '44AA', provision: 'Section 44AA', title: 'Maintenance of books of account',
      applicability: 'Requires specified persons to keep and maintain books of account.',
      statutoryText: null, statutorySource: null,
      practicalInterpretation: 'A separate obligation from audit, with different thresholds. Books may be required where audit is not.',
      applicationToFacts: 'Not evaluated by this tool. Determine the s. 44AA position separately.',
      conclusion: 'Not evaluated — determine separately.',
      conclusionStatus: 'review'
    });
    return cards;
  }

  /* ===========================================================================
   * MATRIX
   * ======================================================================== */
  var MATRIX_STATUS = {
    triggers: 'TRIGGERS AUDIT', clear: 'NO AUDIT', excluded: 'EXCLUDED BY PROVISO', na: 'DOES NOT ARISE',
    pending: 'AWAITING INPUT', met: 'CONDITION MET', 'not-met': 'CONDITION NOT MET'
  };

  function generateMatrix(result) {
    return result.tests.map(function (t) {
      return {
        test: t.label, input: String(t.inputValue), threshold: t.thresholdLabel,
        status: MATRIX_STATUS[t.status] || t.status.toUpperCase(),
        provision: t.provision || '—', reason: t.reason
      };
    });
  }

  TAS.reasoning = {
    generateReasoning: generateReasoning,
    generateConclusion: generateConclusion,
    generateLegalReferences: generateLegalReferences,
    generateMatrix: generateMatrix,
    statutoryTexts: statutoryTexts,
    MATRIX_STATUS: MATRIX_STATUS
  };

})(window);
