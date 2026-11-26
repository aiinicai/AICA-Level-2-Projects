/* ===== RESOLVE 360 — app.js =====
   Loads the attached CSV, wires up filters and renders the dashboard. */

let data = [];      // all loaded records
let visible = [];   // records that pass the current filters

const $ = id => document.getElementById(id);

function showMessage(text, isError = false) {
  $('message').textContent = text;
  $('message').className = 'message' + (isError ? ' error' : '');
}

/* ---------- Loading data ---------- */

// Try the CSV file first (works on a local web server). If the page was
// opened by double-click (file://), browsers block fetch, so fall back to
// the copy of the same CSV embedded in js/data.js.
async function loadAttachedDataset() {
  let text, source;
  try {
    const res = await fetch(CONFIG.DATA_URL, { cache: 'no-store' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    text = await res.text();
    source = CONFIG.DATA_URL;
  } catch (e) {
    text = window.EMBEDDED_CSV;
    source = 'embedded copy (js/data.js)';
  }
  try {
    setData(parseCSV(text));
    showMessage('Loaded ' + data.length + ' records from smart_city_issues.csv - ' + source + '.');
  } catch (err) {
    showMessage('Could not load dataset: ' + err.message, true);
  }
}

function setData(records) {
  data = records;
  ['category', 'ward', 'status'].forEach(id => $(id).value = '');
  $('threshold').value = 0;
  populateFilters();
  render();
}

/* ---------- Filters ---------- */

function populateFilters() {
  for (const [id, key, label] of [['category', 'category', 'services'], ['ward', 'ward', 'wards']]) {
    const el = $(id), prior = el.value;
    const values = [...new Set(data.map(r => r[key]))].sort();
    el.innerHTML = '<option value="">All ' + label + '</option>' +
      values.map(v => `<option value="${esc(v)}">${esc(v)}</option>`).join('');
    el.value = prior;
  }
}

function applyFilters() {
  const c = $('category').value, w = $('ward').value, s = $('status').value;
  const t = +$('threshold').value;
  $('thresholdText').textContent = t;
  visible = data.filter(r =>
    (!c || r.category === c) &&
    (!w || r.ward === w) &&
    (!s || r.status === s) &&
    score(r) >= t);
}

/* ---------- Rendering ---------- */

function renderKPIs(active) {
  $('count').textContent = visible.length.toLocaleString('en-IN');
  $('high').textContent = active.filter(r => score(r) >= CONFIG.HIGH_RISK).length;
  const loss = visible.reduce((n, r) => n + r.estimated_loss_inr, 0);
  $('loss').textContent = '₹' + (loss / 100000).toFixed(2) + ' L';      // lakh
  $('people').textContent = visible.reduce((n, r) => n + r.people_affected, 0).toLocaleString('en-IN');
}

function renderBars(id, key) {
  const counts = {};
  visible.forEach(r => counts[r[key]] = (counts[r[key]] || 0) + 1);
  const max = Math.max(1, ...Object.values(counts));
  $(id).innerHTML = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(([k, v]) => `<div class="barrow"><span>${esc(k)}</span>
        <div class="track"><div class="fill" style="width:${100 * v / max}%"></div></div>
        <b>${v}</b></div>`)
    .join('') || '<span class="muted">No matching records</span>';
}

function renderQueue(active) {
  $('cases').innerHTML = active.slice(0, CONFIG.QUEUE_LIMIT).map(r => {
    const n = score(r), band = risk(n);
    return `<tr>
      <td>${esc(r.issue_id)}</td><td>${esc(r.ward)}</td><td>${esc(r.category)}</td>
      <td>${r.severity}</td><td>${r.people_affected}</td>
      <td>${r.estimated_loss_inr.toLocaleString('en-IN')}</td><td>${r.days_open}</td>
      <td>${n.toFixed(1)}</td><td><span class="risk ${band}">${band}</span></td>
      <td>${esc(ACTIONS[r.category] || 'Assign for human review.')}</td></tr>`;
  }).join('') || '<tr><td colspan="10">No unresolved cases match the filters.</td></tr>';
}

function renderActions() {
  $('actions').innerHTML = Object.entries(ACTIONS)
    .filter(([k]) => visible.some(r => r.category === k && r.status !== 'Resolved'))
    .map(([k, v]) => `<p><b>${esc(k)}:</b> ${esc(v)}</p>`)
    .join('') || 'No active interventions in the current selection.';
}

function render() {
  applyFilters();
  const active = visible.filter(r => r.status !== 'Resolved')
                        .sort((a, b) => score(b) - score(a));
  renderKPIs(active);
  renderBars('categories', 'category');
  renderBars('wards', 'ward');
  renderQueue(active);
  renderActions();
}

/* ---------- Events ---------- */

['category', 'ward', 'status', 'threshold'].forEach(id => $(id).addEventListener('input', render));

$('reload').onclick = loadAttachedDataset;

$('upload').onchange = async e => {
  const file = e.target.files[0];
  if (!file) return;
  try {
    setData(parseCSV(await file.text()));
    showMessage('Imported ' + data.length + ' records locally from ' + file.name + '.');
  } catch (err) {
    showMessage('Import error: ' + err.message, true);
  }
};

$('export').onclick = () => downloadText(toCSV(visible), 'resolve360_filtered_issues.csv');

/* ---------- Start ---------- */
loadAttachedDataset();
