import { workflow, node, trigger, sticky, newCredential, ifElse, expr } from '@n8n/workflow-sdk';

const receiveRun = trigger({
  type: 'n8n-nodes-base.webhook',
  version: 2.1,
  config: {
    name: 'Receive Monitor Run',
    parameters: {
      httpMethod: 'POST',
      path: 'lookthrough-monitor',
      authentication: 'headerAuth',
      responseMode: 'responseNode',
      options: {}
    },
    credentials: { httpHeaderAuth: newCredential('LookThrough monitor token') },
    position: [0, 300]
  },
  output: [{ body: { schema: 'lookthrough.monitor/1', as_on: '2026-08-31', built_at: '2026-09-25T00:19:24', summary: { value_cr: 47.17, xirr_pct: 7.96, not_looked_through_cr: 0 }, exposure: { largest: 'HDFC Bank', largest_pct: 12.56 }, policy: { tests: [{ test: 'Single stock: HDFC Bank', value: 12.56, limit: 10, status: 'BREACH', detail: '' }] }, provenance: { warnings: ['x'], schemes_without_disclosure: [] }, payload_sha256: 'abc' } }]
});

const validatePayload = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Validate Payload',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: `const items = $input.all();
if (items.length !== 1) { throw new Error('Expected exactly one monitor run, received ' + items.length); }
const req = items[0].json;
const p = (req.body && typeof req.body === 'object') ? req.body : req;
const errs = [];
const STATUSES = ['BREACH', 'ABOVE LIMIT', 'within limit', 'NOT COMPUTABLE'];  // ABOVE LIMIT: a warning-grade limit (fund overlap), not a breach
if (p.schema !== 'lookthrough.monitor/1') { errs.push('schema must be lookthrough.monitor/1'); }
if (typeof p.as_on !== 'string' || !/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(p.as_on)) { errs.push('as_on must be YYYY-MM-DD'); }
const s = p.summary || {};
if (typeof s.value_cr !== 'number' || !isFinite(s.value_cr)) { errs.push('summary.value_cr must be a finite number'); }
const tests = (p.policy && Array.isArray(p.policy.tests)) ? p.policy.tests : null;
if (!tests || tests.length === 0) { errs.push('policy.tests must be a non-empty array'); }
else {
  tests.forEach(function (t, i) {
    if (!t || typeof t.test !== 'string' || STATUSES.indexOf(t.status) < 0) { errs.push('policy.tests[' + i + '] has no test name or an unknown status'); }
  });
}
if (typeof p.payload_sha256 !== 'string' || p.payload_sha256.length !== 64) { errs.push('payload_sha256 missing'); }
if (errs.length) { throw new Error('Rejected monitor payload: ' + errs.join('; ')); }
return [{ json: p }];`
    },
    position: [240, 300]
  },
  output: [{ schema: 'lookthrough.monitor/1', as_on: '2026-08-31', summary: { value_cr: 47.17 }, policy: { tests: [] } }]
});

const getLastRun = node({
  type: 'n8n-nodes-base.dataTable',
  version: 1.1,
  config: {
    name: 'Get Last Run',
    alwaysOutputData: true,
    parameters: {
      resource: 'row',
      operation: 'get',
      dataTableId: { __rl: true, mode: 'id', value: 'A0EotPxYEHuglyNC', cachedResultName: 'lookthrough_monitor_runs' },
      returnAll: false,
      limit: 1,
      orderBy: true,
      orderByColumn: 'createdAt',
      orderByDirection: 'DESC'
    },
    position: [480, 300]
  },
  output: [{ id: 1, as_on: '2026-07-31', value_cr: 46.5, breach_list: 'Single stock: HDFC Bank', breaches: 1 }]
});

const compareRuns = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Compare With Last Run',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: `const cur = $('Validate Payload').first().json;
const prevRows = $input.all().map(function (i) { return i.json; }).filter(function (r) { return r && r.as_on; });
const prev = prevRows.length ? prevRows[0] : null;
function esc(v) { return String(v === null || v === undefined ? '-' : v).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
function num(v, d) { return (typeof v === 'number' && isFinite(v)) ? v.toFixed(d) : '-'; }
const tests = cur.policy.tests;
const breaches = tests.filter(function (t) { return t.status === 'BREACH'; });
const notComputable = tests.filter(function (t) { return t.status === 'NOT COMPUTABLE'; });
const warnTests = tests.filter(function (t) { return t.status === 'ABOVE LIMIT'; });
const names = breaches.map(function (t) { return t.test; });
const prevNames = (prev && prev.breach_list) ? String(prev.breach_list).split(' | ').filter(function (x) { return x; }) : [];
const added = names.filter(function (n) { return prevNames.indexOf(n) < 0; });
const resolved = prevNames.filter(function (n) { return names.indexOf(n) < 0; });
const changes = [];
if (!prev) { changes.push('First recorded run.'); }
else {
  if (prev.as_on !== cur.as_on) { changes.push('Valuation date moved from ' + prev.as_on + ' to ' + cur.as_on + '.'); }
  added.forEach(function (n) { changes.push('NEW breach: ' + n + '.'); });
  resolved.forEach(function (n) { changes.push('Resolved: ' + n + '.'); });
  if (typeof prev.value_cr === 'number' && prev.value_cr) {
    const d = cur.summary.value_cr - prev.value_cr;
    changes.push('Portfolio value ' + (d >= 0 ? 'up' : 'down') + ' Rs ' + num(Math.abs(d), 2) + ' cr (' + num(d / prev.value_cr * 100, 2) + '%) since the last run.');
  }
}
const warnings = (cur.provenance && Array.isArray(cur.provenance.warnings)) ? cur.provenance.warnings : [];
const missing = (cur.provenance && Array.isArray(cur.provenance.schemes_without_disclosure)) ? cur.provenance.schemes_without_disclosure : [];
const needsAlert = breaches.length > 0 || resolved.length > 0;
const rowsHtml = tests.map(function (t) {
  const colour = t.status === 'BREACH' ? '#b42318' : t.status === 'ABOVE LIMIT' ? '#b54708' : (t.status === 'NOT COMPUTABLE' ? '#8a6100' : '#067647');
  return '<tr><td>' + esc(t.test) + '</td><td style="text-align:right">' + esc(t.value) + '</td><td style="text-align:right">' + esc(t.limit) + '</td><td style="color:' + colour + ';font-weight:600">' + esc(t.status) + '</td></tr>';
}).join('');
const li = function (arr) { return arr.length ? '<ul>' + arr.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>' : '<p>None.</p>'; };
const html = '<div style="font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#1d2939">'
  + '<h2 style="margin:0 0 4px">LookThrough monthly monitor</h2>'
  + '<p style="margin:0 0 12px;color:#475467">Valuation date ' + esc(cur.as_on) + ' &middot; dataset built ' + esc(cur.built_at) + '</p>'
  + '<p><b>Portfolio value:</b> Rs ' + num(cur.summary.value_cr, 2) + ' cr &middot; <b>XIRR:</b> ' + num(cur.summary.xirr_pct, 2) + '% &middot; <b>Not looked through:</b> Rs ' + num(cur.summary.not_looked_through_cr, 2) + ' cr</p>'
  + '<h3>Investment-policy tests</h3>'
  + '<table cellpadding="6" style="border-collapse:collapse;border:1px solid #d0d5dd"><tr style="background:#f2f4f7"><th align="left">Test</th><th>Value</th><th>Limit</th><th align="left">Status</th></tr>' + rowsHtml + '</table>'
  + '<h3>Changes since the last run</h3>' + li(changes)
  + '<h3>Data completeness</h3>' + li(missing.map(function (m) { return 'No AMC portfolio disclosure: ' + m; }).concat(warnings))
  + '<p style="color:#475467;font-size:12px">Figures were computed on the family-office PC by the LookThrough engine (reconciled against the app) and sent to this workflow; n8n did not recalculate any figure. Payload SHA-256 ' + esc(cur.payload_sha256) + '. Decision support for the investment committee, not investment advice.</p></div>';
const subject = 'LookThrough ' + cur.as_on + ': ' + breaches.length + ' policy breach' + (breaches.length === 1 ? '' : 'es') + (added.length ? ' (' + added.length + ' new)' : '') + (resolved.length ? ', ' + resolved.length + ' resolved' : '') + (warnTests.length ? ', ' + warnTests.length + ' warning' + (warnTests.length === 1 ? '' : 's') : '');
return [{ json: {
  needsAlert: needsAlert,
  subject: subject,
  html: html,
  row: {
    as_on: cur.as_on,
    built_at: cur.built_at || '',
    value_cr: cur.summary.value_cr,
    xirr_pct: (typeof cur.summary.xirr_pct === 'number') ? cur.summary.xirr_pct : null,
    not_looked_through_cr: (typeof cur.summary.not_looked_through_cr === 'number') ? cur.summary.not_looked_through_cr : null,
    breaches: breaches.length,
    not_computable: notComputable.length,
    breach_list: names.join(' | '),
    largest_exposure: (cur.exposure && cur.exposure.largest) || '',
    largest_exposure_pct: (cur.exposure && typeof cur.exposure.largest_pct === 'number') ? cur.exposure.largest_pct : null,
    warnings: warnings.length + missing.length,
    changes: changes.join(' '),
    alert_sent: needsAlert,
    payload_sha256: cur.payload_sha256
  }
} }];`
    },
    position: [720, 300]
  },
  output: [{ needsAlert: true, subject: 'LookThrough 2026-08-31: 2 policy breaches, 3 warnings', html: '<p>x</p>', row: { as_on: '2026-08-31', built_at: '2026-09-25T00:19:24', value_cr: 47.17, xirr_pct: 7.96, not_looked_through_cr: 0, breaches: 2, not_computable: 1, breach_list: 'Single stock: HDFC Bank | Sector: Financial Services', largest_exposure: 'HDFC Bank', largest_exposure_pct: 12.56, warnings: 6, changes: 'First recorded run.', alert_sent: true, payload_sha256: 'abc' } }]
});

const logRun = node({
  type: 'n8n-nodes-base.dataTable',
  version: 1.1,
  config: {
    name: 'Log Run',
    parameters: {
      resource: 'row',
      operation: 'insert',
      dataTableId: { __rl: true, mode: 'id', value: 'A0EotPxYEHuglyNC', cachedResultName: 'lookthrough_monitor_runs' },
      columns: {
        mappingMode: 'defineBelow',
        value: {
          as_on: expr('{{ $json.row.as_on }}'),
          built_at: expr('{{ $json.row.built_at }}'),
          value_cr: expr('{{ $json.row.value_cr }}'),
          xirr_pct: expr('{{ $json.row.xirr_pct }}'),
          not_looked_through_cr: expr('{{ $json.row.not_looked_through_cr }}'),
          breaches: expr('{{ $json.row.breaches }}'),
          not_computable: expr('{{ $json.row.not_computable }}'),
          breach_list: expr('{{ $json.row.breach_list }}'),
          largest_exposure: expr('{{ $json.row.largest_exposure }}'),
          largest_exposure_pct: expr('{{ $json.row.largest_exposure_pct }}'),
          warnings: expr('{{ $json.row.warnings }}'),
          changes: expr('{{ $json.row.changes }}'),
          alert_sent: expr('{{ $json.row.alert_sent }}'),
          payload_sha256: expr('{{ $json.row.payload_sha256 }}')
        },
        schema: [
          { id: 'as_on', displayName: 'as_on', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
          { id: 'built_at', displayName: 'built_at', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
          { id: 'value_cr', displayName: 'value_cr', required: false, defaultMatch: false, display: true, type: 'number', canBeUsedToMatch: true },
          { id: 'xirr_pct', displayName: 'xirr_pct', required: false, defaultMatch: false, display: true, type: 'number', canBeUsedToMatch: true },
          { id: 'not_looked_through_cr', displayName: 'not_looked_through_cr', required: false, defaultMatch: false, display: true, type: 'number', canBeUsedToMatch: true },
          { id: 'breaches', displayName: 'breaches', required: false, defaultMatch: false, display: true, type: 'number', canBeUsedToMatch: true },
          { id: 'not_computable', displayName: 'not_computable', required: false, defaultMatch: false, display: true, type: 'number', canBeUsedToMatch: true },
          { id: 'breach_list', displayName: 'breach_list', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
          { id: 'largest_exposure', displayName: 'largest_exposure', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
          { id: 'largest_exposure_pct', displayName: 'largest_exposure_pct', required: false, defaultMatch: false, display: true, type: 'number', canBeUsedToMatch: true },
          { id: 'warnings', displayName: 'warnings', required: false, defaultMatch: false, display: true, type: 'number', canBeUsedToMatch: true },
          { id: 'changes', displayName: 'changes', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
          { id: 'alert_sent', displayName: 'alert_sent', required: false, defaultMatch: false, display: true, type: 'boolean', canBeUsedToMatch: true },
          { id: 'payload_sha256', displayName: 'payload_sha256', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true }
        ]
      }
    },
    position: [980, 140]
  },
  output: [{ id: 1, createdAt: '2026-09-25T00:40:00.000Z', updatedAt: '2026-09-25T00:40:00.000Z' }]
});

const alertNeeded = ifElse({
  version: 2.3,
  config: {
    name: 'Breach Or Resolution?',
    parameters: {
      conditions: {
        combinator: 'and',
        options: { caseSensitive: true, leftValue: '', typeValidation: 'strict', version: 2 },
        conditions: [{ leftValue: expr('{{ $json.needsAlert }}'), rightValue: '', operator: { type: 'boolean', operation: 'true', singleValue: true } }]
      }
    },
    position: [980, 320]
  }
});

const emailCommittee = node({
  type: 'n8n-nodes-base.gmail',
  version: 2.2,
  config: {
    name: 'Email Investment Committee',
    parameters: {
      resource: 'message',
      operation: 'send',
      sendTo: 'investment-committee@example.com',
      subject: expr('{{ $json.subject }}'),
      emailType: 'html',
      message: expr('{{ $json.html }}'),
      options: { appendAttribution: false, senderName: 'LookThrough Monitor' }
    },
    credentials: { gmailOAuth2: newCredential('Gmail account') },
    onError: 'continueRegularOutput',
    position: [1220, 320]
  },
  output: [{ id: 'msg-1', threadId: 'thr-1', labelIds: ['SENT'] }]
});

const acknowledge = node({
  type: 'n8n-nodes-base.respondToWebhook',
  version: 1.5,
  config: {
    name: 'Acknowledge Run',
    parameters: {
      respondWith: 'json',
      responseBody: expr('{{ JSON.stringify({ received: true, as_on: $json.row.as_on, breaches: $json.row.breaches, alert: $json.needsAlert, execution: $execution.id }) }}'),
      options: { responseCode: 200 }
    },
    position: [980, 500]
  }
});

const note = sticky('## LookThrough monthly monitor\nThe family-office PC refreshes market data, runs the reconciled LookThrough engine and POSTs the results here (bridge/monitor_push.py). This workflow validates the payload, compares it with the last run, logs every run to the data table, and emails the committee when a policy limit is breached or a breach is resolved. n8n never recalculates a figure. The alert recipient is fixed here and never taken from the payload.', [receiveRun, validatePayload, getLastRun, compareRuns], { color: 4 });

export default workflow('lookthrough-monitor', 'LookThrough - Monthly Policy Monitor')
  .add(receiveRun)
  .to(validatePayload)
  .to(getLastRun)
  .to(compareRuns)
  .to(logRun)
  .add(compareRuns)
  .to(alertNeeded.onTrue(emailCommittee))
  .add(compareRuns)
  .to(acknowledge)
  .add(note);
