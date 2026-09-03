/* AuditLens — front end.
   Renders what the engine returns. It never computes a figure of its own;
   every number on screen came from the Python engine, so what the auditor
   sees is what the tests cover. */

'use strict';

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

let state = { engagementId: null, data: null };

/* ---------- Indian digit grouping, matching the engine ---------- */
function inr(value, decimals = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  const negative = value < 0;
  const fixed = Math.abs(Number(value)).toFixed(decimals);
  const [whole, fraction] = fixed.split('.');
  let grouped;
  if (whole.length > 3) {
    const lastThree = whole.slice(-3);
    let rest = whole.slice(0, -3);
    const groups = [];
    while (rest.length > 2) {
      groups.unshift(rest.slice(-2));
      rest = rest.slice(0, -2);
    }
    if (rest) groups.unshift(rest);
    grouped = groups.join(',') + ',' + lastThree;
  } else {
    grouped = whole;
  }
  return (negative ? '-' : '') + grouped + (fraction ? '.' + fraction : '');
}

function compact(value) {
  if (value === null || value === undefined) return '—';
  const magnitude = Math.abs(value);
  if (magnitude >= 1e7) return `₹${(value / 1e7).toFixed(2)} cr`;
  if (magnitude >= 1e5) return `₹${(value / 1e5).toFixed(2)} lakh`;
  return '₹' + inr(value, 0);
}

const escapeHtml = (s) =>
  String(s ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function table(el, columns, rows, rowClass) {
  if (!rows.length) {
    el.innerHTML = `<tbody><tr><td class="empty">Nothing to show.</td></tr></tbody>`;
    return;
  }
  const head = columns.map((c) =>
    `<th class="${c.numeric ? 'num' : ''}">${escapeHtml(c.label)}</th>`).join('');
  const body = rows.map((row) => {
    const cls = rowClass ? rowClass(row) : '';
    const cells = columns.map((c) => {
      const raw = c.get(row);
      const text = c.numeric && typeof raw === 'number' ? inr(raw, c.decimals ?? 2) : raw;
      return `<td class="${c.numeric ? 'num' : ''} ${c.cellClass ? c.cellClass(row) : ''}">${
        c.html ? (text ?? '') : escapeHtml(text ?? '—')}</td>`;
    }).join('');
    return `<tr class="${cls}">${cells}</tr>`;
  }).join('');
  el.innerHTML = `<thead><tr>${head}</tr></thead><tbody>${body}</tbody>`;
}


/* Read a response safely.
   A server error returns plain text, not JSON, and calling response.json()
   on it throws "Unexpected token 'I'" - which tells the user nothing and
   hides the real fault. This reads the body once as text, then parses it
   only if it actually looks like JSON. */
async function readResponse(response) {
  const body = await response.text();
  let payload = null;
  try {
    payload = body ? JSON.parse(body) : null;
  } catch {
    payload = null;
  }
  if (response.ok) {
    if (payload === null) {
      throw new Error(
        `The server replied with something that is not a result (HTTP ${response.status}). ` +
        `Check the terminal window running AuditLens.`);
    }
    return payload;
  }
  const detail = payload?.detail
    || (body ? body.slice(0, 300).trim() : `HTTP ${response.status}`);
  const reference = payload?.reference ? ` (reference ${payload.reference})` : '';
  const error = new Error(`${detail}${reference}`);
  error.hint = payload?.hint || '';
  throw error;
}

/* ================= tiles ================= */
function renderTiles(d) {
  const h = d.headlines;
  const tiles = [
    { label: 'Revenue', value: compact(h.revenue), sub: h.financial_year },
    { label: 'Profit before tax', value: compact(h.profit_before_tax) },
    { label: 'Total assets', value: compact(h.total_assets) },
    {
      label: 'Overall materiality', value: compact(h.overall_materiality),
      sub: `Performance ${compact(h.performance_materiality)}`,
    },
    {
      label: 'Ratios to explain', value: h.ratios_requiring_explanation,
      sub: 'Movement beyond 25%',
      tone: h.ratios_requiring_explanation > 0 ? 'is-flag' : 'is-ok',
    },
    {
      label: 'Entries selected', value: h.je_entries_flagged,
      sub: `of ${h.je_total_entries} under SA 240`,
      tone: h.je_entries_flagged > 0 ? 'is-flag' : 'is-ok',
    },
    {
      label: 'Mapping coverage', value: (h.mapping_coverage * 100).toFixed(1) + '%',
      sub: `${h.ledgers_for_review} awaiting review`,
      tone: h.ledgers_for_review > 0 ? 'is-flag' : 'is-ok',
    },
    {
      label: 'Trial balance', value: h.trial_balance_tallies ? 'Tallies' : 'Out',
      sub: h.trial_balance_tallies ? '' : `by ₹${inr(h.trial_balance_difference)}`,
      tone: h.trial_balance_tallies ? 'is-ok' : 'is-crit',
    },
  ];
  $('#tiles').innerHTML = tiles.map((t) => `
    <dl class="tile ${t.tone || ''}">
      <dt>${escapeHtml(t.label)}</dt>
      <dd>${escapeHtml(t.value)}${t.sub ? `<div class="sub">${escapeHtml(t.sub)}</div>` : ''}</dd>
    </dl>`).join('');

  const banner = $('#reconciliation');
  banner.textContent = d.statements.reconciliation;
  banner.classList.toggle('is-ok', d.statements.tallies);
  banner.hidden = false;
}

/* ================= ratios ================= */
function renderRatios(d) {
  const toExplain = d.ratios.filter((r) => r.requires_explanation).length;
  const notComputable = d.ratios.filter((r) => r.value === null).length;
  const summary = `
    <div class="ratio summary">
      <span class="ratio-name">Disclosure position</span>
      <span class="ratio-value">${toExplain} of ${d.ratios.length}</span>
      <span class="ratio-basis">${toExplain === 0
        ? 'No ratio moved beyond 25 per cent, so no explanation is required in the notes.'
        : `${toExplain} ratio${toExplain === 1 ? '' : 's'} moved beyond 25 per cent and must be
           explained in the notes under Schedule III.`}${notComputable
        ? ` ${notComputable} could not be computed.` : ''}</span>
    </div>`;

  $('#ratios-grid').innerHTML = d.ratios.map((r) => {
    const delta = r.variance === null || r.variance === undefined
      ? '<span class="ratio-compare">No comparative</span>'
      : `<span class="ratio-compare">Previous ${r.prior_value}${r.unit === '%' ? '%' : ''} ·
           <span class="ratio-delta ${r.requires_explanation ? 'beyond-threshold' : ''}">${
             r.variance >= 0 ? '+' : ''}${(r.variance * 100).toFixed(1)}%</span></span>`;
    const chip = r.requires_explanation
      ? '<span class="chip">Explanation required</span>'
      : (r.value === null ? '<span class="chip crit">Not computable</span>' : '');
    return `
      <div class="ratio ${r.requires_explanation ? 'is-flag' : ''}">
        <span class="ratio-name">${escapeHtml(r.name)}</span>
        <span class="ratio-value">${escapeHtml(r.formatted)}</span>
        ${delta}
        <span class="ratio-basis">${escapeHtml(r.numerator_label)} ÷ ${
          escapeHtml(r.denominator_label)}<br>${compact(r.numerator)} ÷ ${compact(r.denominator)}${
          r.note ? '<br>' + escapeHtml(r.note) : ''}</span>
        ${chip}
      </div>`;
  }).join('') + summary;
}

/* ================= statements ================= */
function renderStatements(d) {
  const columns = [
    { label: 'Particulars', get: (r) => r.label, html: true,
      cellClass: (r) => `indent-${r.level}` },
    { label: 'Current year', get: (r) => r.current, numeric: true },
    { label: 'Previous year', get: (r) => r.prior, numeric: true },
  ];
  const render = (el, lines) => table(
    el,
    columns.map((c) => ({ ...c, get: (r) => (c.html ? escapeHtml(c.get(r)) : c.get(r)) })),
    lines,
    (r) => (r.is_total ? 'is-total' : ''),
  );
  render($('#bs-table'), d.statements.balance_sheet);
  render($('#pl-table'), d.statements.profit_and_loss);
}

/* ================= mapping queue ================= */
function renderMapping(d) {
  table($('#mapping-table'), [
    { label: 'Code', get: (r) => r.account_code },
    { label: 'Ledger name', get: (r) => r.account_name },
    { label: 'Suggested head', get: (r) => r.head },
    { label: 'Mapped on', get: (r) => (r.basis === 'unmapped' ? 'could not map' : r.basis.replace('_', ' ')) },
    { label: 'Confidence', get: (r) => (r.confidence ? (r.confidence * 100).toFixed(0) + '%' : '—') },
    { label: 'Matched on', get: (r) => r.matched_on || '—' },
  ], d.mapping.review, (r) => (r.basis === 'unmapped' ? 'is-flag' : ''));
}

/* ================= journal entries ================= */
function renderJE(d) {
  if (!d.je) {
    $('#je-tests').innerHTML = '<tbody><tr><td class="empty">No general ledger was supplied.</td></tr></tbody>';
    $('#benford').innerHTML = '';
    $('#je-flags').innerHTML = '';
    return;
  }
  table($('#je-tests'), [
    { label: 'Routine', get: (r) => r.name },
    { label: 'Reference', get: (r) => r.reference },
    { label: 'Flagged', get: (r) => r.flagged, numeric: true, decimals: 0 },
    { label: 'Rate', get: (r) => (r.rate * 100).toFixed(1) + '%' },
  ], d.je.tests);

  const b = d.je.benford;
  const maxPct = Math.max(...Object.values(b.observed_pct), ...Object.values(b.expected));
  const rows = [1, 2, 3, 4, 5, 6, 7, 8, 9].map((digit) => {
    const observed = b.observed_pct[digit] || 0;
    const expected = b.expected[digit] || 0;
    return `<div class="benford-row">
      <span class="benford-digit">${digit}</span>
      <span class="bar bar-observed" style="width:${(observed / maxPct) * 100}%"></span>
      <span class="bar bar-expected" style="width:${(expected / maxPct) * 100}%"></span>
      <span class="benford-pct">${(observed * 100).toFixed(1)}%</span>
    </div>`;
  }).join('');
  $('#benford').innerHTML = `
    <div class="benford-legend">
      <span><i class="bar-observed" style="background:var(--accent)"></i>Observed</span>
      <span><i class="bar-expected" style="background:var(--rule-strong)"></i>Expected</span>
    </div>
    ${rows}
    <p class="ratio-basis">Mean absolute deviation ${b.mad.toFixed(5)} across ${
      b.total} entries. ${escapeHtml(b.conclusion)}</p>`;

  table($('#je-flags'), [
    { label: 'Entry', get: (r) => r.entry_id },
    { label: 'Date', get: (r) => r.posting_date || '—' },
    { label: 'Amount', get: (r) => r.amount, numeric: true },
    { label: 'Routine', get: (r) => r.test },
    { label: 'Selected because', get: (r) => r.reason },
    { label: 'Posted by', get: (r) => r.posted_by },
  ], d.je.flags, (r) => (r.severity === 'elevated' ? 'is-flag' : ''));
}

/* ================= sample ================= */
function renderSample(d) {
  if (!d.sample) {
    const note = d.headlines?.sampling_note || 'No population to sample.';
    $('#sample-params').innerHTML = `<tbody><tr><td class="empty">${escapeHtml(note)}</td></tr></tbody>`;
    $('#sample-items').innerHTML = '';
    $('#sample-warnings').innerHTML = '';
    return;
  }
  const s = d.sample;
  $('#sample-warnings').innerHTML = s.warnings.map(
    (w) => `<div class="banner">${escapeHtml(w)}</div>`).join('');

  table($('#sample-params'), [
    { label: 'Parameter', get: (r) => r[0] },
    { label: 'Value', get: (r) => r[1] },
  ], [
    ['Population size', inr(s.population_size, 0) + ' items'],
    ['Population value', '₹' + inr(s.population_value)],
    ['Sampling interval', '₹' + inr(s.sampling_interval)],
    ['Random start', '₹' + inr(s.random_start)],
    ['Seed (for re-performance)', String(s.seed)],
    ['Sample size', inr(s.sample_size, 0) + ' items'],
    ['Value coverage', (s.coverage * 100).toFixed(1) + '%'],
  ]);

  table($('#sample-items'), [
    { label: '#', get: (r, i) => r.index },
    { label: 'Identifier', get: (r) => r.identifier },
    { label: 'Description', get: (r) => r.description },
    { label: 'Amount', get: (r) => r.amount, numeric: true },
    { label: 'Selected because', get: (r) => r.reason },
  ], s.items);
}

/* ================= CARO ================= */
function renderCaro(d) {
  if (!d.caro) return;
  $('#caro-applicability').textContent =
    (d.caro.applies
      ? 'CARO 2020 applies to this company. '
      : 'CARO 2020 does not apply to this company. ') + d.caro.reasons.join(' ');

  $('#caro-list').innerHTML = d.caro.clauses.map((c) => `
    <div class="clause">
      <span class="clause-no">${escapeHtml(c.number)}</span>
      <div>
        <div class="clause-title">${escapeHtml(c.title)}</div>
        <div class="clause-req">${escapeHtml(c.requirement)}</div>
        ${c.evidence ? `<div class="clause-evidence">${escapeHtml(c.evidence)}</div>` : ''}
        <div class="clause-status">${escapeHtml(c.suggested_status)}</div>
      </div>
    </div>`).join('');
}

/* ================= drafts ================= */
async function generateDrafts() {
  const button = $('#generate-drafts');
  const status = $('#drafts-status');
  button.disabled = true;
  status.className = 'status';
  status.textContent = 'Drafting…';
  try {
    const response = await fetch(`/api/engagements/${state.engagementId}/drafts`, { method: 'POST' });
    const drafts = await readResponse(response);
    const blocks = [drafts.memorandum, ...drafts.ratio_notes, drafts.je_enquiry];
    $('#drafts').innerHTML = blocks.map((dr) => `
      <article class="draft">
        <h3>${escapeHtml(dr.title)}</h3>
        <div class="draft-meta">${dr.source === 'model'
          ? 'Drafted by the model'
          : 'Drafted from the offline template — no API key configured'} ·
          ${escapeHtml(dr.prompt_file || 'built in')}</div>
        <pre>${escapeHtml(dr.body)}</pre>
      </article>`).join('');
    status.textContent = `${blocks.length} draft(s) ready for your review.`;
  } catch (error) {
    status.className = 'status error';
    status.textContent = `Could not generate drafts — ${error.message}`
      + (error.hint ? ` ${error.hint}` : '');
  } finally {
    button.disabled = false;
  }
}

/* ================= run ================= */
function render(data) {
  state.data = data;
  renderTiles(data);
  renderRatios(data);
  renderStatements(data);
  renderMapping(data);
  renderJE(data);
  renderSample(data);
  renderCaro(data);
  $('#disclaimer').textContent = data.disclaimer;
  $('#results').hidden = false;
  $('#download-workbook').hidden = false;
  const label = $('#engagement-label');
  label.textContent = `${data.headlines.client} · ${data.headlines.financial_year}`;
  label.hidden = false;
  $('#results').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function runReview(useSamples) {
  const form = $('#engagement-form');
  const status = $('#setup-status');
  const submit = $('button[type="submit"]', form);

  const body = new FormData(form);
  body.set('use_samples', useSamples ? 'true' : 'false');
  if (!body.get('materiality_percentage')) body.set('materiality_percentage', '0');

  if (!useSamples && !body.get('trial_balance')?.size) {
    status.className = 'status error';
    status.textContent = 'Attach a trial balance, or run the sample client.';
    return;
  }

  submit.disabled = true;
  status.className = 'status';
  status.textContent = 'Running the review…';
  try {
    const response = await fetch('/api/engagements', { method: 'POST', body });
    const payload = await readResponse(response);
    state.engagementId = payload.engagement_id;
    status.textContent = 'Review complete.';
    render(payload);
  } catch (error) {
    status.className = 'status error';
    status.textContent = error.message + (error.hint ? ` ${error.hint}` : '');
  } finally {
    submit.disabled = false;
  }
}

/* ================= wiring ================= */
document.addEventListener('DOMContentLoaded', () => {
  $('#engagement-form').addEventListener('submit', (event) => {
    event.preventDefault();
    runReview(false);
  });
  $('#use-samples').addEventListener('click', () => runReview(true));
  $('#generate-drafts').addEventListener('click', generateDrafts);
  $('#download-workbook').addEventListener('click', () => {
    if (state.engagementId) {
      window.location.href = `/api/engagements/${state.engagementId}/workbook`;
    }
  });

  $$('.tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      $$('.tab').forEach((t) => t.classList.toggle('is-active', t === tab));
      $$('.tabpanel').forEach((panel) =>
        panel.classList.toggle('is-active', panel.dataset.panel === tab.dataset.tab));
    });
  });

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js').catch(() => {
      /* Offline support is a convenience; the app works without it. */
    });
  }
});
