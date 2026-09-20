/* =============================================================================
 * workingpaper.js — Working paper model and document rendering
 * -----------------------------------------------------------------------------
 * Builds a document MODEL from the engine result, then renders it. The model is
 * shared by every output channel (screen preview, print/PDF, Word), so the three
 * can never drift apart.
 *
 * Ten sections, per the firm's working paper standard:
 *   1  Executive conclusion      6  Section-wise legal references
 *   2  Assessee profile          7  Applicability analysis
 *   3  Financial data            8  Professional notes
 *   4  Statutory tests           9  Conclusion
 *   5  Detailed reasoning       10  Disclaimer
 * ========================================================================== */

(function (global) {
  'use strict';

  var TAS = global.TAS || (global.TAS = {});
  var calc = TAS.calc;

  function esc(s) {
    if (s === null || s === undefined) return '';
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function today() {
    var d = new Date();
    var months = ['January','February','March','April','May','June',
                  'July','August','September','October','November','December'];
    return d.getDate() + ' ' + months[d.getMonth()] + ' ' + d.getFullYear();
  }

  function statusClass(status) {
    var S = TAS.engine.STATUS;
    if (status === S.APPLICABLE) return 'applicable';
    if (status === S.NOT_APPLICABLE) return 'not-applicable';
    return 'review';
  }

  function matrixCellClass(status) {
    if (status === 'TRIGGERS AUDIT') return 'bad';
    if (status === 'NO AUDIT' || status === 'CONDITION MET' || status === 'EXCLUDED BY PROVISO') return 'ok';
    if (status === 'CONDITION NOT MET' || status === 'AWAITING INPUT') return 'warn';
    return 'neutral';
  }

  /* ===========================================================================
   * MODEL
   * ======================================================================== */
  function generateWorkingPaper(result) {
    var f = result.facts;
    var d = result.derived;

    return {
      firm: 'T R S & Associates',
      firmSub: 'Chartered Accountants',
      documentTitle: 'Tax Audit Applicability — Working Paper',
      documentSub: 'Section 44AB | 44AD | 44ADA  ·  Professional decision record',
      capstoneNote: 'Prepared using the Tax Audit Applicability Decision System, developed by ' +
                    'T R S & Associates as an ICAI AICA Level 2 Capstone Project.',

      preparedOn: today(),
      preparedBy: f.preparedBy || '',
      reviewedBy: f.reviewedBy || '',

      assessee: {
        name: f.clientName || 'Not entered',
        pan: f.pan || 'Not recorded',
        constitution: f.constitutionMeta ? f.constitutionMeta.label : 'Not selected',
        nature: result.isBusiness ? 'Business' : 'Profession',
        professionCategory: result.isBusiness ? null : f.professionCategory,
        assessmentYear: f.assessmentYear,
        financialYear: f.financialYear
      },

      result: {
        status: result.status,
        statusClass: statusClass(result.status),
        reason: result.statusReason
      },

      conclusion: TAS.reasoning.generateConclusion(result),
      reasoning: TAS.reasoning.generateReasoning(result),
      references: TAS.reasoning.generateLegalReferences(result),
      matrix: TAS.reasoning.generateMatrix(result),
      reviewPoints: result.notes,
      outstanding: result.required,

      metrics: [
        { k: 'Audit status', v: result.status, cls: result.status === 'NOT APPLICABLE' ? 'ok' : (result.status === 'APPLICABLE' ? 'bad' : ''), sm: true },
        { k: result.isBusiness ? 'Turnover' : 'Gross receipts', v: calc.inr(f.turnover) },
        { k: 'Cash receipts %', v: nilPct(d.cashReceiptRatio.value, f.cashReceipts, result.isBusiness ? f.totalReceipts : f.turnover),
          cls: d.cashReceiptRatio.value !== null ? (d.cashReceiptRatio.value <= 5 ? 'ok' : 'bad') : '' },
        { k: 'Cash payments %', v: result.isBusiness ? nilPct(d.cashPaymentRatio.value, f.cashPayments, f.totalPayments) : 'Not applicable',
          cls: result.isBusiness && d.cashPaymentRatio.value !== null ? (d.cashPaymentRatio.value <= 5 ? 'ok' : 'bad') : '',
          sm: !result.isBusiness },
        { k: 'Profit %', v: calc.pct(d.profitRatio.value) },
        { k: 'Applicable limit', v: result.thresholdTest.thresholdLabel, sm: true },
        { k: 'Applicable form', v: result.form.form, sm: true },
        { k: 'Presumptive income', v: d.presumptiveIncome !== null ? calc.inr(d.presumptiveIncome) : 'Not applicable', sm: true }
      ],

      financials: [
        { k: result.isBusiness ? 'Turnover' : 'Gross receipts', v: calc.inr(f.turnover) },
        { k: 'Turnover not via banking by due date', v: result.isBusiness ? calc.inr(f.turnoverNonBanking) : 'Not applicable' },
        { k: 'Total amounts received', v: result.isBusiness ? calc.inr(f.totalReceipts) : 'Not applicable' },
        { k: 'Cash receipts', v: calc.inr(f.cashReceipts) },
        { k: 'Non-cash receipts', v: calc.inr(d.nonCashReceipts) },
        { k: 'Total payments', v: result.isBusiness ? calc.inr(f.totalPayments) : 'Not applicable' },
        { k: 'Cash payments', v: result.isBusiness ? calc.inr(f.cashPayments) : 'Not applicable' },
        { k: 'Non-cash payments', v: result.isBusiness ? calc.inr(d.nonCashPayments) : 'Not applicable' },
        { k: 'Declared profit', v: calc.inr(f.profit) },
        { k: 'Profit percentage', v: calc.pct(d.profitRatio.value) },
        { k: 'Total income', v: calc.inr(f.totalIncome) },
        { k: 'Basic exemption applied', v: f.exemptionAmount === 0 ? 'Nil' : calc.inr(f.exemptionAmount) },
        { k: 'Exemption basis', v: f.exemptionLabel }
      ],

      presumptiveData: presumptiveRows(result),

      compliance: [
        { k: 'Applicable form', v: result.form.form },
        { k: 'Form determination', v: result.form.reason },
        { k: 'Tax audit report due', v: result.dueDates.auditReport },
        { k: 'Return of income due', v: result.dueDates.itr }
      ].concat(result.form.additional.map(function (a) { return { k: 'Additional requirement', v: a }; })),

      specialConditions: f.flags.map(function (id) {
        var c = TAS.ruleset.conditionById(id);
        return c ? { label: c.label, note: c.note } : { label: id, note: '' };
      }),

      verification: {
        verified: TAS.ruleset.isSignedOff(),
        statement: TAS.ruleset.verificationStatement(f.assessmentYear),
        dueDateNote: result.dueDates.note
      },

      disclaimer:
        'This application is a professional decision-support and documentation tool. It is not a ' +
        'substitute for independent examination of the Income-tax Act, Rules, Finance Act ' +
        'amendments, CBDT notifications and circulars, judicial precedents, ICAI Guidance Notes ' +
        'and the facts of the particular assessee. Final professional conclusion should be made ' +
        'after verification of complete facts and applicable law. The conclusion recorded above ' +
        'is drawn only on the limbs modelled by the application and only on the figures entered.'
    };
  }

  /* A nil total with nil cash reads as "Nil", not a dash: the test is met. */
  function nilPct(value, cash, total) {
    if (value === null && cash === 0 && total === 0) return 'Nil';
    return calc.pct(value);
  }

  function yn(v) { return v === 'yes' ? 'Yes' : v === 'no' ? 'No' : 'Not answered'; }

  function presumptiveRows(result) {
    var f = result.facts, an = result.analysis;
    var rows = [
      { k: 'Presumptive scheme', v: result.isBusiness ? 'Section 44AD' : 'Section 44ADA' },
      { k: 'Residential status', v: f.residentialStatus === 'resident' ? 'Resident' : 'Non-resident' },
      { k: 'Eligible', v: an.eligible === true ? 'Yes' : an.eligible === false ? 'No — ' + an.exclusions.join('; ') : 'Not determined' },
      { k: 'Applicable ceiling', v: an.ceilingLabel || 'Not applicable' },
      { k: 'Deemed income', v: an.deemed ? calc.inr(an.deemed) : (an.deemedLow ? calc.inr(an.deemedLow) + ' to ' + calc.inr(an.deemedHigh) : 'Not applicable') },
      { k: 'Declaring under the scheme', v: an.canDeclare ? yn(f.declarePresumptive) : 'Not available' }
    ];
    if (result.isBusiness && f.constitutionMeta.can44AD) {
      rows.push({ k: 'Within s. 44AD(4) bar', v: yn(f.bar44AD) });
      if (f.prior44AD) rows.push({ k: 'Used s. 44AD in preceding five AYs', v: yn(f.prior44AD) });
    }
    if (!result.isBusiness && f.professionCategory) {
      var pc = TAS.ruleset.professionById(f.professionCategory);
      rows.push({ k: 'Profession', v: pc ? pc.label : f.professionCategory });
    }
    return rows;
  }


  /* ===========================================================================
   * RENDER — print / PDF document
   * `mode` is 'executive' (one page) or 'detailed' (full working paper).
   * The detailed-only sections carry a class the print stylesheet suppresses.
   * ======================================================================== */
  function renderDocument(wp, mode) {
    return mode === 'executive' ? renderExecutive(wp) : renderDetailed(wp);
  }

  /* ---------------------------------------------------------------------------
   * EXECUTIVE ONE-PAGER
   * Composed independently rather than being the detailed paper with sections
   * hidden. A one-page document has a fixed budget; the only honest way to hold
   * it is to decide what earns its place, not to hide overflow.
   * ------------------------------------------------------------------------ */
  function renderExecutive(wp) {
    var h = [];

    h.push(letterhead(wp));
    h.push('<div class="pr-doctitle">Tax Audit Applicability — Executive Summary</div>');

    /* The letterhead already carries the assessee and the year. On a one-page
       budget nothing is printed twice, so only the two remaining identifiers
       are repeated here. */
    h.push('<div class="pr-ident" style="grid-template-columns:repeat(2,1fr)">');
    h.push(ident('Constitution', wp.assessee.constitution));
    h.push(ident('Nature of activity', wp.assessee.nature));
    h.push('</div>');

    h.push('<div class="pr-alert" style="border-color:#D4D9DE;background:#F7F9FA;border-left-color:#14304F;color:#2E3740;">' +
      '<b>Legal basis:</b> Income-tax Act, 1961 as amended to the Finance Act 2025; thresholds cross-checked on ' +
      esc(TAS.ruleset.verification.researchedOn) + '.' +
      (wp.verification.verified ? '' : ' CA sign-off pending.') + '</div>');

    /* Result */
    h.push('<div class="pr-result ' + wp.result.statusClass + '">');
    h.push('<div class="rlabel">Tax audit applicability</div>');
    h.push('<div class="rstatus">' + esc(wp.result.status) + '</div>');
    h.push('<div class="rlead">' + esc(wp.conclusion.lead) + '</div>');
    h.push('</div>');

    /* Key figures — one metric row, then a compact grid */
    h.push('<div class="pr-metrics">');
    [wp.metrics[1], wp.metrics[2], wp.metrics[3], wp.metrics[4]].forEach(function (m) { h.push(metric(m)); });
    h.push('</div>');
    h.push('<div class="pr-grid" style="grid-template-columns:repeat(4,1fr)">');
    h.push(kv('Applicable limit', wp.metrics[5].v));
    h.push(kv('Applicable form', wp.metrics[6].v));
    wp.compliance.slice(2, 4).forEach(function (c) { h.push(kv(c.k, c.v)); });
    h.push('</div>');

    /* Key tests only */
    h.push('<div class="pr-h">Key statutory tests</div>');
    /* The other-law row is dropped here: the grid above already states the
       applicable form, which is the only thing that row decides. */
    /* The one-pager carries only tests that were actually engaged. Rows that
       "do not arise" on these facts stay in the detailed working paper. */
    var rows = wp.matrix.filter(function (r) { return r.status !== 'DOES NOT ARISE'; });
    h.push('<table class="pr-table"><thead><tr>' +
           '<th style="width:24%">Test</th><th style="width:15%">Input</th>' +
           '<th style="width:20%">Threshold</th><th style="width:15%">Status</th>' +
           '<th style="width:26%">Provision</th></tr></thead><tbody>');
    rows.forEach(function (r) {
      h.push('<tr><td class="name">' + esc(r.test) + '</td>' +
        '<td class="num">' + esc(r.input) + '</td>' +
        '<td>' + esc(r.threshold) + '</td>' +
        '<td class="st ' + matrixCellClass(r.status) + '">' + esc(r.status) + '</td>' +
        '<td>' + esc(r.provision) + '</td></tr>');
    });
    h.push('</tbody></table>');

    /* Reason */
    h.push('<div class="pr-h">Reason</div>');
    var reasons = (wp.conclusion.grounds && wp.conclusion.grounds.length)
      ? wp.conclusion.grounds.map(function (g) { return g.provision + ' — ' + g.reason; })
      : (wp.conclusion.reasons || [wp.result.reason]);
    h.push('<ol style="margin:0 0 6pt 14pt;font-size:8pt;line-height:1.45;">');
    reasons.slice(0, 4).forEach(function (r) { h.push('<li>' + esc(r) + '</li>'); });
    h.push('</ol>');

    /* Notes — only substantive ones (medium / low) earn a place on the
       one-pager. Informational notes stay in the detailed working paper; the
       s. 44AA point, which every conclusion must carry, is in "Important". */
    var order = { high: 0, medium: 1, low: 2 };
    var sorted = wp.reviewPoints.filter(function (p) { return p.severity !== 'info'; }).sort(function (a, b) {
      return (order[a.severity] === undefined ? 3 : order[a.severity]) -
             (order[b.severity] === undefined ? 3 : order[b.severity]);
    });
    if (sorted.length) {
      h.push('<div class="pr-h">Points for the reviewer</div>');
      h.push('<div class="pr-review">');
      sorted.slice(0, 2).forEach(function (p) {
        h.push('<div class="item"><div class="sev ' + esc(p.severity) + '"></div><div>' +
               '<div class="ih">' + esc(p.heading) + '</div>' +
               '<div class="it">' + esc(p.text) + '</div></div></div>');
      });
      h.push('</div>');
      if (sorted.length > 2) {
        h.push('<div style="font-size:7pt;color:#5A6672;margin-top:3pt;">' +
               (sorted.length - 2) + ' further review point(s) are set out in the detailed working paper.</div>');
      }
    }

    /* One closing block. The sign-off deliberately lives on the detailed working
       paper, which is the document that actually gets signed; repeating it here
       would invite the summary to be treated as the signed record. */
    h.push('<div class="pr-h">Important</div>');
    h.push('<div style="font-size:7.6pt;line-height:1.45;color:#3A434C;">' + esc(wp.conclusion.caveat) +
           ' Section 44AA (books of account) is a separate obligation and is not evaluated.' +
           ' Decision-support output only: not a substitute for independent examination of the Act, ' +
           'Finance Act amendments, CBDT notifications and circulars, judicial precedents, ICAI ' +
           'Guidance Notes and the facts of the assessee. The complete reasoning, the statutory ' +
           'references and the sign-off block are in the detailed working paper.</div>');

    return h.join('\n');
  }

  /* ---------------------------------------------------------------------------
   * DETAILED WORKING PAPER — the full ten-section record
   * ------------------------------------------------------------------------ */
  function renderDetailed(wp) {
    var h = [];

    /* ---- Cover (detailed only) ---------------------------------------- */
    {
      h.push('<div class="pr-cover cover-only">');
      h.push(letterhead(wp));
      h.push('<div class="ctitle">' + esc(wp.documentTitle) + '</div>');
      h.push('<div class="csub">' + esc(wp.documentSub) + '</div>');
      h.push('<div class="cgrid">');
      h.push(cover('Assessee', wp.assessee.name));
      h.push(cover('Constitution', wp.assessee.constitution));
      h.push(cover('Financial year', wp.assessee.financialYear));
      h.push(cover('Assessment year', wp.assessee.assessmentYear));
      h.push(cover('Nature of activity', wp.assessee.nature));
      h.push(cover('Date of preparation', wp.preparedOn));
      h.push(cover('Prepared by', wp.preparedBy || '—'));
      h.push(cover('Reviewed by', wp.reviewedBy || '—'));
      h.push('</div>');
      if (!wp.verification.verified) h.push(verificationAlert(wp));
      h.push('<div class="cnote">' + esc(wp.capstoneNote) + '</div>');
      h.push('</div>');
    }

    /* ---- Running head + identification --------------------------------- */
    h.push(letterhead(wp));
    h.push('<div class="pr-doctitle">' + esc(wp.documentTitle) + '</div>');
    h.push('<div class="pr-docsub">' + esc(wp.documentSub) + '</div>');

    h.push('<div class="pr-ident">');
    h.push(ident('Assessee', wp.assessee.name));
    h.push(ident('Constitution', wp.assessee.constitution));
    h.push(ident('Nature', wp.assessee.nature));
    h.push(ident('FY / AY', wp.assessee.financialYear + ' / ' + wp.assessee.assessmentYear));
    h.push('</div>');

    if (!wp.verification.verified) h.push(verificationAlert(wp));

    /* ---- 1. Executive conclusion --------------------------------------- */
    h.push('<div class="pr-h"><span class="n">1</span>Executive conclusion</div>');
    h.push('<div class="pr-result ' + wp.result.statusClass + '">');
    h.push('<div class="rlabel">Tax audit applicability</div>');
    h.push('<div class="rstatus">' + esc(wp.result.status) + '</div>');
    h.push('<div class="rlead">' + esc(wp.conclusion.lead) + '</div>');
    h.push('</div>');

    h.push('<div class="pr-metrics">');
    wp.metrics.slice(0, 4).forEach(function (m) { h.push(metric(m)); });
    h.push('</div>');
    h.push('<div class="pr-metrics">');
    wp.metrics.slice(4, 8).forEach(function (m) { h.push(metric(m)); });
    h.push('</div>');

    /* ---- 2. Assessee profile ------------------------------------------- */
    h.push('<div class="pr-h detailed-only"><span class="n">2</span>Assessee profile</div>');
    h.push('<div class="pr-grid detailed-only">');
    h.push(kv('Assessee', wp.assessee.name));
    h.push(kv('PAN', wp.assessee.pan));
    h.push(kv('Constitution', wp.assessee.constitution));
    h.push(kv('Nature of activity', wp.assessee.nature));
    if (wp.assessee.professionCategory) h.push(kv('Profession classification', wp.assessee.professionCategory));
    h.push(kv('Financial year', wp.assessee.financialYear));
    h.push(kv('Assessment year', wp.assessee.assessmentYear));
    h.push('</div>');

    /* ---- 3. Financial data --------------------------------------------- */
    h.push('<div class="pr-h detailed-only"><span class="n">3</span>Financial data as entered</div>');
    h.push('<div class="pr-grid detailed-only">');
    wp.financials.forEach(function (r) { h.push(kv(r.k, r.v)); });
    h.push('</div>');
    h.push('<div class="pr-h detailed-only">Presumptive taxation particulars</div>');
    h.push('<div class="pr-grid detailed-only">');
    wp.presumptiveData.forEach(function (r) { h.push(kv(r.k, r.v)); });
    h.push('</div>');

    /* ---- 4. Statutory tests --------------------------------------------
     * The executive sheet drops the Finding column. It is the tallest column by
     * far, and on a one-page document the reader wants the test result, not the
     * prose — which is on the detailed paper if they need it.                */
    h.push('<div class="pr-h"><span class="n">4</span>Statutory tests applied</div>');
    h.push('<table class="pr-table"><thead><tr>' +
           '<th style="width:20%">Test</th><th style="width:14%">Input</th>' +
           '<th style="width:17%">Threshold</th><th style="width:14%">Status</th>' +
           '<th style="width:15%">Provision</th><th>Finding</th>' +
           '</tr></thead><tbody>');
    wp.matrix.forEach(function (r) {
      h.push('<tr>' +
        '<td class="name">' + esc(r.test) + '</td>' +
        '<td class="num">' + esc(r.input) + '</td>' +
        '<td>' + esc(r.threshold) + '</td>' +
        '<td class="st ' + matrixCellClass(r.status) + '">' + esc(r.status) + '</td>' +
        '<td>' + esc(r.provision) + '</td>' +
        '<td>' + esc(r.reason) + '</td>' +
        '</tr>');
    });
    h.push('</tbody></table>');

    /* ---- 5. Detailed reasoning ----------------------------------------- */
    h.push('<div class="pr-h detailed-only pr-pagebreak"><span class="n">5</span>Detailed reasoning</div>');
    h.push('<div class="pr-steps detailed-only">');
    wp.reasoning.forEach(function (s) {
      h.push('<div class="pr-step"><div class="sh">' + s.number + '. ' + esc(s.heading) +
             (s.value ? ' &mdash; <span class="sv">' + esc(s.value) + '</span>' : '') +
             (s.provision ? ' <span class="sp">' + esc(s.provision) + '</span>' : '') +
             '</div><div class="st">' + esc(s.text) + '</div></div>');
    });
    h.push('</div>');

    /* ---- 6. Legal references ------------------------------------------- */
    h.push('<div class="pr-h detailed-only"><span class="n">6</span>Section-wise legal references</div>');
    h.push('<div class="detailed-only">');
    wp.references.forEach(function (r) {
      h.push('<div class="pr-ref">');
      h.push('<div class="rp">' + esc(r.provision) + ' &mdash; ' + esc(r.title) + '</div>');
      h.push('<div class="rblk"><div class="rk">Applicability</div><div class="rv">' + esc(r.applicability) + '</div></div>');
      h.push('<div class="rblk"><div class="rk">Relevant statutory text</div>');
      if (r.statutoryText) {
        h.push('<div class="rquote">' + esc(r.statutoryText) + '</div>');
        h.push('<div class="rv" style="font-size:6.8pt;color:#78838E;margin-top:2pt;">Source: ' + esc(r.statutorySource) + '</div>');
      } else {
        h.push('<div class="rmissing"><b>Not reproduced.</b> The verbatim text of ' + esc(r.provision) + ' was not retrieved for this tool. Read it from the bare Act.</div>');
      }
      h.push('</div>');
      h.push('<div class="rblk"><div class="rk">Practical interpretation &mdash; simplified professional explanation</div>' +
             '<div class="rv">' + esc(r.practicalInterpretation) + '</div></div>');
      h.push('<div class="rblk"><div class="rk">Application to the present case</div>' +
             '<div class="rv">' + esc(r.applicationToFacts) + '</div></div>');
      h.push('<div class="rblk"><div class="rk">Conclusion</div><div class="rv">' + esc(r.conclusion) + '</div></div>');
      h.push('</div>');
    });
    h.push('</div>');

    /* ---- 7. Applicability analysis ------------------------------------- */
    h.push('<div class="pr-h"><span class="n">7</span>' +
           (wp.result.status === 'NOT APPLICABLE' ? 'Non-applicability analysis' : 'Applicability analysis') + '</div>');
    h.push('<div class="pr-keep">');
    wp.conclusion.body.forEach(function (p) { h.push('<div class="rv" style="font-size:8pt;margin-bottom:4pt;">' + esc(p) + '</div>'); });
    if (wp.conclusion.grounds && wp.conclusion.grounds.length) {
      h.push('<ol style="margin:0 0 6pt 14pt;font-size:8pt;line-height:1.5;">');
      wp.conclusion.grounds.forEach(function (g) {
        h.push('<li><b>' + esc(g.provision) + '</b> &mdash; ' + esc(g.reason) + '</li>');
      });
      h.push('</ol>');
    }
    if (wp.conclusion.reasons && wp.conclusion.reasons.length) {
      h.push('<ol style="margin:0 0 6pt 14pt;font-size:8pt;line-height:1.5;">');
      wp.conclusion.reasons.forEach(function (r) { h.push('<li>' + esc(r) + '</li>'); });
      h.push('</ol>');
    }
    h.push('<div class="rk" style="font-size:6.2pt;letter-spacing:.12em;text-transform:uppercase;color:#78838E;font-weight:700;margin:6pt 0 2pt;">Consequences</div>');
    h.push('<ul style="margin:0 0 6pt 14pt;font-size:8pt;line-height:1.5;">');
    wp.conclusion.consequences.forEach(function (c) { h.push('<li>' + esc(c) + '</li>'); });
    h.push('</ul>');
    h.push('</div>');

    h.push('<div class="pr-h detailed-only">Compliance particulars</div>');
    h.push('<div class="pr-grid detailed-only">');
    wp.compliance.forEach(function (r) { h.push(kv(r.k, r.v)); });
    h.push('</div>');

    /* ---- 8. Professional notes --------------------------------- */
    h.push('<div class="pr-h"><span class="n">8</span>Professional notes</div>');
    if (wp.reviewPoints.length) {
      /* The one-pager carries the three most severe points and says how many
         more there are, rather than silently dropping the rest. */
      var order = { high: 0, medium: 1, low: 2 };
      var sorted = wp.reviewPoints.slice().sort(function (a, b) {
        return (order[a.severity] === undefined ? 3 : order[a.severity]) -
               (order[b.severity] === undefined ? 3 : order[b.severity]);
      });
      var shown = sorted;
      h.push('<div class="pr-review">');
      shown.forEach(function (p) {
        h.push('<div class="item"><div class="sev ' + esc(p.severity) + '"></div><div>' +
               '<div class="ih">' + esc(p.heading) + '</div>' +
               '<div class="it">' + esc(p.text) + '</div></div></div>');
      });
      h.push('</div>');
    } else {
      h.push('<div class="rv" style="font-size:8pt;">No review point was raised by the application on ' +
             'the information entered. This does not displace the reviewer’s own judgement.</div>');
    }

    if (wp.specialConditions.length) {
      h.push('<div class="pr-h detailed-only">Special conditions flagged</div>');
      h.push('<div class="pr-review detailed-only">');
      wp.specialConditions.forEach(function (c) {
        h.push('<div class="item"><div class="sev medium"></div><div>' +
               '<div class="ih">' + esc(c.label) + '</div>' +
               '<div class="it">' + esc(c.note) + '</div></div></div>');
      });
      h.push('</div>');
    }

    /* ---- 9. Conclusion -------------------------------------------------- */
    h.push('<div class="pr-h"><span class="n">9</span>Conclusion</div>');
    h.push('<div class="pr-result ' + wp.result.statusClass + '">');
    h.push('<div class="rstatus" style="font-size:12pt;">' + esc(wp.conclusion.headline) + '</div>');
    h.push('<div class="rlead">' + esc(wp.conclusion.caveat) + '</div>');
    h.push('</div>');

    h.push('<div class="pr-signoff">');
    h.push('<div class="slot"><div class="role">Prepared by</div><div class="who">' + esc(wp.preparedBy) +
           '</div><div class="date">Date</div></div>');
    h.push('<div class="slot"><div class="role">Reviewed by</div><div class="who">' + esc(wp.reviewedBy) +
           '</div><div class="date">Date</div></div>');
    h.push('<div class="slot"><div class="role">Partner</div><div class="who"></div><div class="date">Date &amp; UDIN</div></div>');
    h.push('</div>');

    /* ---- 10. Disclaimer ------------------------------------------------- */
    h.push('<div class="pr-h"><span class="n">10</span>Disclaimer</div>');
    h.push('<div class="pr-disclaimer">' + esc(wp.disclaimer) + '<br><br>' +
           esc(wp.verification.statement) + '<br><br>' + esc(wp.capstoneNote) + '</div>');

    return h.join('\n');
  }

  function letterhead(wp) {
    return '<div class="pr-letterhead"><div>' +
      '<div class="pr-firm">' + esc(wp.firm) + '</div>' +
      '<div class="pr-firm-sub">' + esc(wp.firmSub) + '</div>' +
      '</div><div class="pr-meta">' +
      '<div class="ay">' + esc(wp.assessee.financialYear) + ' &middot; ' + esc(wp.assessee.assessmentYear) + '</div>' +
      '<div>' + esc(wp.assessee.name) + '</div>' +
      '<div>' + esc(wp.preparedOn) + '</div>' +
      '</div></div>';
  }

  function verificationAlert(wp) {
    return '<div class="pr-alert" style="border-color:#D4D9DE;background:#F7F9FA;border-left-color:#14304F;color:#2E3740;">' +
      '<b>Legal basis.</b> ' + esc(wp.verification.statement) + '</div>';
  }


  function ident(k, v) { return '<div><div class="k">' + esc(k) + '</div><div class="v">' + esc(v) + '</div></div>'; }
  function cover(k, v) { return '<div><div class="k">' + esc(k) + '</div><div class="v">' + esc(v) + '</div></div>'; }
  function kv(k, v)    { return '<div><div class="k">' + esc(k) + '</div><div class="v">' + esc(v) + '</div></div>'; }
  function metric(m) {
    return '<div><div class="k">' + esc(m.k) + '</div><div class="v' +
      (m.sm ? ' sm' : '') + (m.cls ? ' ' + m.cls : '') + '">' + esc(m.v) + '</div></div>';
  }

  TAS.workingpaper = {
    generateWorkingPaper: generateWorkingPaper,
    renderDocument: renderDocument,
    esc: esc,
    today: today,
    statusClass: statusClass
  };

})(window);
