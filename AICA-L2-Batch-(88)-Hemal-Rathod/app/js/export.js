/* =============================================================================
 * export.js — Output channels
 * -----------------------------------------------------------------------------
 *   PDF    : renders the working paper model into #print-root and calls print().
 *            Two documents share the model — an executive one-pager and the full
 *            working paper — selected by a data attribute the print stylesheet reads.
 *   Word   : builds a genuine Word document (WordSection page setup, running
 *            header, footer with page numbers, styled heading levels, bordered
 *            tables, explicit page breaks) from the same model. It is not a dump
 *            of the screen markup.
 *   JSON   : the calculation audit trail.
 *
 * All three are generated from TAS.workingpaper.generateWorkingPaper(), so no
 * output can quietly disagree with another.
 * ========================================================================== */

(function (global) {
  'use strict';

  var TAS = global.TAS || (global.TAS = {});
  var esc = TAS.workingpaper.esc;

  /* ===========================================================================
   * FILE DOWNLOAD
   * ======================================================================== */
  function download(filename, mime, content) {
    var blob = new Blob([content], { type: mime });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1500);
  }

  function safeName(wp, suffix, ext) {
    var name = (wp.assessee.name || 'Assessee').replace(/[^A-Za-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
    var ay = wp.assessee.assessmentYear.replace(/[^A-Za-z0-9]+/g, '');
    return 'TRS_TaxAudit_' + name + '_' + ay + '_' + suffix + '.' + ext;
  }

  /* ===========================================================================
   * PDF / PRINT
   * ======================================================================== */
  function printDocument(result, mode) {
    var wp = TAS.workingpaper.generateWorkingPaper(result);
    var root = document.getElementById('print-root');
    root.innerHTML = TAS.workingpaper.renderDocument(wp, mode);
    document.documentElement.setAttribute('data-print-mode', mode);
    /* Let the DOM settle before handing over to the print engine, otherwise the
       first print of a session can capture a half-rendered document. */
    global.setTimeout(function () { global.print(); }, 60);
  }

  /* ===========================================================================
   * WORD
   * ======================================================================== */
  function wordDocument(wp) {
    var W = [];

    /* ---- Word page setup: A4, margins, running header and footer -------- */
    var head =
      '<html xmlns:o="urn:schemas-microsoft-com:office:office" ' +
            'xmlns:w="urn:schemas-microsoft-com:office:word" ' +
            'xmlns="http://www.w3.org/TR/REC-html40">' +
      '<head><meta charset="utf-8">' +
      '<title>' + esc(wp.documentTitle) + '</title>' +
      '<!--[if gte mso 9]><xml><w:WordDocument>' +
      '<w:View>Print</w:View><w:Zoom>100</w:Zoom><w:DoNotOptimizeForBrowser/>' +
      '</w:WordDocument></xml><![endif]-->' +
      '<style>' +
      '@page WordSection1 {' +
      '  size: 21.0cm 29.7cm;' +
      '  margin: 2.2cm 1.9cm 2.2cm 1.9cm;' +
      '  mso-header-margin: 1.1cm;' +
      '  mso-footer-margin: 1.1cm;' +
      '  mso-header: h1;' +
      '  mso-footer: f1;' +
      '  mso-paper-source: 0;' +
      '}' +
      'div.WordSection1 { page: WordSection1; }' +
      'body { font-family: Calibri, Arial, sans-serif; font-size: 10.5pt; color: #101418; line-height: 1.4; }' +
      'h1 { font-size: 18pt; font-weight: bold; color: #101418; margin: 0 0 4pt 0; }' +
      'h2 { font-size: 11pt; font-weight: bold; color: #14304F; margin: 16pt 0 6pt 0;' +
      '     border-bottom: 1pt solid #14304F; padding-bottom: 3pt; }' +
      'h3 { font-size: 10pt; font-weight: bold; color: #2E3740; margin: 11pt 0 4pt 0; }' +
      'p  { margin: 0 0 6pt 0; }' +
      '.small { font-size: 8.5pt; color: #5A6672; }' +
      '.micro { font-size: 7.5pt; color: #78838E; text-transform: uppercase; letter-spacing: 1pt; }' +
      'table { border-collapse: collapse; width: 100%; margin: 0 0 10pt 0; }' +
      'table th { background: #EDF1F4; border: 0.75pt solid #B9C2CA; padding: 4pt 5pt;' +
      '           font-size: 8pt; text-align: left; color: #3A434C; }' +
      'table td { border: 0.75pt solid #B9C2CA; padding: 4pt 5pt; font-size: 8.5pt; vertical-align: top; }' +
      'td.num { text-align: right; }' +
      '.statusbox { border: 1pt solid #B9C2CA; padding: 9pt 11pt; margin: 0 0 10pt 0; }' +
      '.statusbox.applicable     { border-color: #A0322A; background: #FCF2F0; }' +
      '.statusbox.not-applicable { border-color: #146A46; background: #F0F8F3; }' +
      '.statusbox.review         { border-color: #8A5D0F; background: #FCF6E9; }' +
      '.statusword { font-size: 17pt; font-weight: bold; }' +
      '.applicable     .statusword { color: #A0322A; }' +
      '.not-applicable .statusword { color: #146A46; }' +
      '.review         .statusword { color: #8A5D0F; }' +
      '.alert { border: 0.75pt solid #C9A45A; background: #FCF6E9; padding: 7pt 9pt; margin: 0 0 10pt 0; font-size: 8.5pt; color: #4A3C18; }' +
      '.quote { border-left: 3pt solid #14304F; padding-left: 8pt; margin: 0 0 6pt 0; font-size: 9pt; }' +
      '.missing { border: 0.75pt dashed #C9A45A; background: #FCF6E9; padding: 5pt 7pt; font-size: 8pt; color: #5A4718; }' +
      '.pagebreak { page-break-before: always; mso-special-character: line-break; }' +
      '.disclaimer { font-size: 8pt; color: #5A6672; border-top: 0.75pt solid #B9C2CA; padding-top: 7pt; }' +
      '</style></head><body><div class="WordSection1">';

    W.push(head);

    /* ---- Running header and footer (Word elements) ---------------------- */
    W.push(
      '<div style="mso-element:header" id="h1"><p class="small" style="border-bottom:0.75pt solid #B9C2CA;padding-bottom:3pt;">' +
      '<b>' + esc(wp.firm) + '</b> &nbsp;|&nbsp; ' + esc(wp.documentTitle) +
      ' &nbsp;|&nbsp; ' + esc(wp.assessee.name) + ' &nbsp;|&nbsp; ' +
      esc(wp.assessee.financialYear) + '</p></div>');

    W.push(
      '<div style="mso-element:footer" id="f1"><p class="small" style="border-top:0.75pt solid #B9C2CA;padding-top:3pt;">' +
      esc(wp.firm) + ' &nbsp;&middot;&nbsp; Chartered Accountants &nbsp;&middot;&nbsp; ' +
      'Page <span style="mso-field-code:PAGE"></span> of <span style="mso-field-code:NUMPAGES"></span>' +
      ' &nbsp;&middot;&nbsp; Internal working paper</p></div>');

    /* ---- Cover ---------------------------------------------------------- */
    W.push('<p class="micro">' + esc(wp.firmSub) + '</p>');
    W.push('<h1>' + esc(wp.firm) + '</h1>');
    W.push('<p class="small">' + esc(wp.documentSub) + '</p>');
    W.push('<p>&nbsp;</p>');
    W.push('<h1 style="font-size:15pt;">' + esc(wp.documentTitle) + '</h1>');

    W.push('<table><tr>' +
      '<th style="width:25%">Assessee</th><td>' + esc(wp.assessee.name) + '</td>' +
      '<th style="width:22%">PAN</th><td>' + esc(wp.assessee.pan) + '</td></tr>' +
      '<tr><th>Constitution</th><td>' + esc(wp.assessee.constitution) + '</td>' +
      '<th>Nature of activity</th><td>' + esc(wp.assessee.nature) + '</td></tr>' +
      '<tr><th>Financial year</th><td>' + esc(wp.assessee.financialYear) + '</td>' +
      '<th>Assessment year</th><td>' + esc(wp.assessee.assessmentYear) + '</td></tr>' +
      '<tr><th>Prepared by</th><td>' + esc(wp.preparedBy || '—') + '</td>' +
      '<th>Reviewed by</th><td>' + esc(wp.reviewedBy || '—') + '</td></tr>' +
      '<tr><th>Date of preparation</th><td colspan="3">' + esc(wp.preparedOn) + '</td></tr>' +
      '</table>');

    if (!wp.verification.verified) {
      W.push('<div class="alert"><b>Legal basis.</b> ' +
             esc(wp.verification.statement) + '</div>');
    }

    W.push('<p class="small">' + esc(wp.capstoneNote) + '</p>');
    W.push('<div class="pagebreak"></div>');

    /* ---- 1. Executive conclusion ---------------------------------------- */
    W.push('<h2>1. Executive conclusion</h2>');
    W.push('<div class="statusbox ' + wp.result.statusClass + '">' +
           '<p class="micro">Tax audit applicability</p>' +
           '<p class="statusword">' + esc(wp.result.status) + '</p>' +
           '<p>' + esc(wp.conclusion.lead) + '</p></div>');

    W.push('<table><tr>');
    wp.metrics.slice(0, 4).forEach(function (m) { W.push('<th>' + esc(m.k) + '</th>'); });
    W.push('</tr><tr>');
    wp.metrics.slice(0, 4).forEach(function (m) { W.push('<td><b>' + esc(m.v) + '</b></td>'); });
    W.push('</tr><tr>');
    wp.metrics.slice(4, 8).forEach(function (m) { W.push('<th>' + esc(m.k) + '</th>'); });
    W.push('</tr><tr>');
    wp.metrics.slice(4, 8).forEach(function (m) { W.push('<td><b>' + esc(m.v) + '</b></td>'); });
    W.push('</tr></table>');

    /* ---- 2. Assessee profile -------------------------------------------- */
    W.push('<h2>2. Assessee profile</h2>');
    W.push(twoColTable([
      ['Assessee', wp.assessee.name],
      ['PAN', wp.assessee.pan],
      ['Constitution', wp.assessee.constitution],
      ['Nature of activity', wp.assessee.nature],
      ['Financial year', wp.assessee.financialYear],
      ['Assessment year', wp.assessee.assessmentYear]
    ]));

    /* ---- 3. Financial data ---------------------------------------------- */
    W.push('<h2>3. Financial data as entered</h2>');
    W.push(twoColTable(wp.financials.map(function (r) { return [r.k, r.v]; }), true));
    W.push('<h3>Presumptive taxation particulars</h3>');
    W.push(twoColTable(wp.presumptiveData.map(function (r) { return [r.k, r.v]; })));

    /* ---- 4. Statutory tests --------------------------------------------- */
    W.push('<h2>4. Statutory tests applied</h2>');
    W.push('<table><thead><tr><th>Test</th><th>Input</th><th>Threshold</th>' +
           '<th>Status</th><th>Provision</th><th>Finding</th></tr></thead><tbody>');
    wp.matrix.forEach(function (r) {
      W.push('<tr><td><b>' + esc(r.test) + '</b></td><td class="num">' + esc(r.input) + '</td>' +
             '<td>' + esc(r.threshold) + '</td><td><b>' + esc(r.status) + '</b></td>' +
             '<td>' + esc(r.provision) + '</td><td>' + esc(r.reason) + '</td></tr>');
    });
    W.push('</tbody></table>');

    /* ---- 5. Detailed reasoning ------------------------------------------ */
    W.push('<div class="pagebreak"></div>');
    W.push('<h2>5. Detailed reasoning</h2>');
    wp.reasoning.forEach(function (s) {
      W.push('<h3>' + s.number + '. ' + esc(s.heading) +
             (s.value ? ' &mdash; ' + esc(s.value) : '') + '</h3>');
      if (s.provision) W.push('<p class="micro">' + esc(s.provision) + '</p>');
      W.push('<p>' + esc(s.text) + '</p>');
    });

    /* ---- 6. Legal references -------------------------------------------- */
    W.push('<div class="pagebreak"></div>');
    W.push('<h2>6. Section-wise legal references</h2>');
    wp.references.forEach(function (r) {
      W.push('<h3>' + esc(r.provision) + ' &mdash; ' + esc(r.title) + '</h3>');
      W.push('<p class="micro">Applicability</p><p>' + esc(r.applicability) + '</p>');
      W.push('<p class="micro">Relevant statutory text</p>');
      if (r.statutoryText) {
        W.push('<p class="quote">' + esc(r.statutoryText) + '</p>');
        W.push('<p class="small">Source: ' + esc(r.statutorySource) + '</p>');
      } else {
        W.push('<p class="missing"><b>Not reproduced.</b> The verbatim text of ' + esc(r.provision) + ' was not retrieved for this tool. Read it from the bare Act.</p>');
      }
      W.push('<p class="micro">Practical interpretation &mdash; simplified professional explanation</p>' +
             '<p>' + esc(r.practicalInterpretation) + '</p>');
      W.push('<p class="micro">Application to the present case</p><p>' + esc(r.applicationToFacts) + '</p>');
      W.push('<p class="micro">Conclusion</p><p><b>' + esc(r.conclusion) + '</b></p>');
    });

    /* ---- 7. Applicability analysis -------------------------------------- */
    W.push('<div class="pagebreak"></div>');
    W.push('<h2>7. ' + (wp.result.status === 'NOT APPLICABLE' ? 'Non-applicability analysis' : 'Applicability analysis') + '</h2>');
    wp.conclusion.body.forEach(function (p) { W.push('<p>' + esc(p) + '</p>'); });
    if (wp.conclusion.grounds && wp.conclusion.grounds.length) {
      W.push('<ol>');
      wp.conclusion.grounds.forEach(function (g) {
        W.push('<li><b>' + esc(g.provision) + '</b> &mdash; ' + esc(g.reason) + '</li>');
      });
      W.push('</ol>');
    }
    if (wp.conclusion.reasons && wp.conclusion.reasons.length) {
      W.push('<ol>');
      wp.conclusion.reasons.forEach(function (r) { W.push('<li>' + esc(r) + '</li>'); });
      W.push('</ol>');
    }
    W.push('<h3>Consequences</h3><ul>');
    wp.conclusion.consequences.forEach(function (c) { W.push('<li>' + esc(c) + '</li>'); });
    W.push('</ul>');
    W.push('<h3>Compliance particulars</h3>');
    W.push(twoColTable(wp.compliance.map(function (r) { return [r.k, r.v]; })));

    /* ---- 8. Review points ------------------------------------------------ */
    W.push('<h2>8. Professional notes</h2>');
    if (wp.reviewPoints.length) {
      W.push('<table><thead><tr><th style="width:16%">Type</th><th style="width:30%">Note</th>' +
             '<th>Explanation</th></tr></thead><tbody>');
      wp.reviewPoints.forEach(function (p) {
        W.push('<tr><td>' + esc(p.severity.toUpperCase()) + '</td><td><b>' + esc(p.heading) +
               '</b></td><td>' + esc(p.text) + '</td></tr>');
      });
      W.push('</tbody></table>');
    } else {
      W.push('<p>No review point was raised by the application on the information entered. ' +
             'This does not displace the reviewer’s own judgement.</p>');
    }

    /* ---- 9. Conclusion --------------------------------------------------- */
    W.push('<h2>9. Conclusion</h2>');
    W.push('<div class="statusbox ' + wp.result.statusClass + '">' +
           '<p class="statusword" style="font-size:13pt;">' + esc(wp.conclusion.headline) + '</p>' +
           '<p>' + esc(wp.conclusion.caveat) + '</p></div>');

    W.push('<table><tr>' +
      '<th style="width:33%">Prepared by</th><th style="width:33%">Reviewed by</th><th>Partner</th></tr>' +
      '<tr><td style="height:46pt;">' + esc(wp.preparedBy || '') + '</td>' +
      '<td>' + esc(wp.reviewedBy || '') + '</td><td></td></tr>' +
      '<tr><td class="small">Date</td><td class="small">Date</td><td class="small">Date &amp; UDIN</td></tr>' +
      '</table>');

    /* ---- 10. Disclaimer -------------------------------------------------- */
    W.push('<h2>10. Disclaimer</h2>');
    W.push('<p class="disclaimer">' + esc(wp.disclaimer) + '</p>');
    W.push('<p class="disclaimer">' + esc(wp.verification.statement) + '</p>');
    W.push('<p class="disclaimer">' + esc(wp.capstoneNote) + '</p>');

    W.push('</div></body></html>');
    return W.join('\n');
  }

  function twoColTable(rows, numeric) {
    var t = ['<table>'];
    rows.forEach(function (r) {
      t.push('<tr><th style="width:36%">' + esc(r[0]) + '</th><td' +
             (numeric ? ' class="num"' : '') + '>' + esc(r[1]) + '</td></tr>');
    });
    t.push('</table>');
    return t.join('');
  }

  function exportWord(result) {
    var wp = TAS.workingpaper.generateWorkingPaper(result);
    /* The BOM matters: without it Word mis-reads the rupee sign and the en dashes. */
    download(safeName(wp, 'WorkingPaper', 'doc'),
             'application/msword;charset=utf-8',
             '﻿' + wordDocument(wp));
    return wp;
  }

  /* ===========================================================================
   * JSON AUDIT TRAIL
   * ======================================================================== */
  function exportAuditTrail(result) {
    var wp = TAS.workingpaper.generateWorkingPaper(result);
    var trail = TAS.state.auditTrail(result);
    download(safeName(wp, 'AuditTrail', 'json'),
             'application/json;charset=utf-8',
             JSON.stringify(trail, null, 2));
    return trail;
  }

  TAS.exporter = {
    printDocument: printDocument,
    exportWord: exportWord,
    exportAuditTrail: exportAuditTrail,
    wordDocument: wordDocument,
    download: download
  };

})(window);
