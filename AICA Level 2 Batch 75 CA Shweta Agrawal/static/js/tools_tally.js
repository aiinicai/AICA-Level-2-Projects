/* ═══════════════════════════════════════════════════════════════════════════
   TOOLS  →  Tally Multi-Source Import (React, no build step)
   Stages Bank/Journal/GSTR-2B/GSTR-1 rows and posts approved vouchers to
   Tally via the tally_import Flask blueprint, which talks to Tally's
   XML/HTTP gateway (localhost:9000 by default). Nothing posts until rows
   are explicitly selected and "Approve & post" is clicked.
   ═══════════════════════════════════════════════════════════════════════════ */

const TALLY_API = '/api/tools/tally';

// Standalone build: mount straight to the page on load, no dashboard shell to toggle.
window.addEventListener('DOMContentLoaded', () => {
  ReactDOM.createRoot(document.getElementById('tally-root')).render(React.createElement(TallyImportApp));
});

async function tallyApi(path, opts) {
  const r = await fetch(TALLY_API + path, opts);
  const text = await r.text();
  let data;
  try { data = JSON.parse(text); }
  catch {
    throw new Error(r.status === 404
      ? 'Route not found -- restart the server, then try again.'
      : `Server error ${r.status}.`);
  }
  if (!r.ok) throw new Error(data.error || `Server error ${r.status}`);
  return data;
}

const h = React.createElement;

function newId() {
  return 'r' + Math.random().toString(36).slice(2) + Date.now().toString(36);
}

const SOURCES = [
  { key: 'journal', label: 'Journal Entry' },
  { key: 'gstr2b', label: 'GSTR-2B', templateUrl: TALLY_API + '/template/gstr2b' },
  { key: 'gstr1', label: 'GSTR-1' },
];

const DISPLAY_COLS = [
  ['select', 'Sel'], ['status', 'Status'], ['source', 'Source'],
  ['voucher_type', 'Type'], ['date', 'Date'], ['reference', 'Ref'],
  ['narration', 'Narration'], ['primary_ledger', 'Primary Ledger'],
  ['contra_ledger', 'Vendor/Contra Ledger'], ['contra_raw', 'Raw'],
  ['expense_ledger', 'Purchase/Expense/Asset'], ['itc_eligible', 'ITC'],
  ['amount', 'Amount'], ['taxable_value', 'Taxable'],
  ['duplicate_hint', 'Duplicate?'], ['error', 'Error'],
];

const SEARCHABLE_COLS = ['narration', 'reference', 'primary_ledger', 'contra_ledger', 'contra_raw', 'expense_ledger', 'error', 'source', 'voucher_type'];

function TallyImportApp() {
  const [gatewayUrl, setGatewayUrl] = React.useState('http://localhost:9000');
  const [connMsg, setConnMsg] = React.useState(null);
  const [connOk, setConnOk] = React.useState(null);
  const [ledgers, setLedgers] = React.useState([]);
  const [bankLedgerNames, setBankLedgerNames] = React.useState([]);
  const [expenseLedgers, setExpenseLedgers] = React.useState([]);
  const [purchaseLedger, setPurchaseLedger] = React.useState('Purchase');
  const [salesLedger, setSalesLedger] = React.useState('Sales');
  const [gstr1Mode, setGstr1Mode] = React.useState('source_of_truth');
  const [rows, setRows] = React.useState([]);
  const [busy, setBusy] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState('');
  const [searchText, setSearchText] = React.useState('');
  const [sortField, setSortField] = React.useState('');
  const [sortDir, setSortDir] = React.useState('asc');
  const [dupFrom, setDupFrom] = React.useState(isoDaysAgo(90));
  const [dupTo, setDupTo] = React.useState(isoDaysAgo(0));
  const [runResults, setRunResults] = React.useState([]);
  const [toast, setToast] = React.useState(null);
  const [readiness, setReadiness] = React.useState(null);
  const [bankContraGroups, setBankContraGroups] = React.useState({});

  function say(msg, ok) { setToast({ msg, ok }); setTimeout(() => setToast(null), 6000); }

  const ledgerNames = ledgers.map(l => l.name);

  async function checkConnection() {
    setBusy('conn');
    try {
      const d = await tallyApi('/connection', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ gateway_url: gatewayUrl }) });
      setConnOk(d.ok); setConnMsg(d.message);
    } catch (e) { setConnOk(false); setConnMsg(e.message); }
    setBusy('');
  }

  async function refreshLedgers() {
    setBusy('ledgers');
    try {
      const d = await tallyApi('/ledgers', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ gateway_url: gatewayUrl }) });
      if (d.ok) {
        setLedgers(d.ledgers); setBankLedgerNames(d.bank_ledger_names); setExpenseLedgers(d.expense_ledgers || []);
        say(`Loaded ${d.ledgers.length} ledgers.`, true);
        return d; // callers that immediately chain another action need this, not stale state
      }
      say(d.error || 'Could not load ledgers.', false);
      return null;
    } catch (e) {
      say(e.message, false);
      return null;
    } finally {
      setBusy('');
    }
  }

  async function uploadFile(source, file, mode) {
    setBusy('upload-' + source);
    try {
      const fd = new FormData();
      fd.append('file', file);
      if (mode) fd.append('mode', mode);
      const d = await tallyApi('/parse/' + source, { method: 'POST', body: fd });
      const newRows = d.rows.map(r => ({ ...r, row_id: r.row_id || newId() }));
      setRows(prev => [...prev, ...newRows]);
      say(`Parsed ${newRows.length} row(s) from ${source}.`, true);
    } catch (e) { say(e.message, false); }
    setBusy('');
  }

  function appendRows(newRowsRaw, skippedBadDates) {
    const newRows = newRowsRaw.map(r => ({ ...r, row_id: r.row_id || newId() }));
    setRows(prev => [...prev, ...newRows]);
    const skipNote = skippedBadDates ? ` (${skippedBadDates} row(s) skipped — unreadable date, likely a stray extracted cell)` : '';
    say(`Parsed ${newRows.length} row(s) from Bank Statement.${skipNote}`, true);
  }

  async function resolveLedgers(overrideLedgers, overrideBankNames) {
    // Accepts fresh data explicitly, rather than relying on `ledgers` state --
    // when called right after refreshLedgers() in the same handler, React
    // hasn't re-rendered yet so the state variable would still be stale.
    const ledgersToUse = overrideLedgers || ledgers;
    const bankNamesToUse = overrideBankNames || bankLedgerNames;
    const namesToUse = ledgersToUse.map(l => l.name);
    if (!namesToUse.length) { say('Load the Tally ledger list first.', false); return null; }
    setBusy('resolve');
    try {
      const d = await tallyApi('/resolve', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rows, ledgers: ledgersToUse, ledger_names: namesToUse, bank_ledger_names: bankNamesToUse, default_purchase_ledger: purchaseLedger }),
      });
      // Never leave an unresolved row selected -- LedgerNotFound/UnMatched rows
      // have no valid ledger to post against yet, so posting them would fail.
      const unresolved = new Set(['LedgerNotFound', 'UnMatched']);
      const rowsOut = d.rows.map(r => unresolved.has(r.status) ? { ...r, select: false } : r);
      setRows(rowsOut);
      const blocked = rowsOut.filter(r => unresolved.has(r.status)).length;
      say(blocked ? `Ledger resolution complete. ${blocked} row(s) need a ledger created before they can be posted.` : 'Ledger resolution pass complete.', blocked === 0);
      return rowsOut; // callers chaining checkReadiness() need this, not stale state
    } catch (e) {
      say(e.message, false);
      return null;
    } finally {
      setBusy('');
    }
  }

  async function runDupCheck() {
    setBusy('dup');
    try {
      const d = await tallyApi('/dupcheck', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rows, gateway_url: gatewayUrl, from_date: dupFrom, to_date: dupTo }),
      });
      setRows(d.rows);
      (d.warnings || []).forEach(w => say(w, false));
      say('Duplicate check complete.', true);
    } catch (e) { say(e.message, false); }
    setBusy('');
  }

  async function checkReadiness(overrideRows) {
    const rowsToUse = overrideRows || rows;
    setBusy('readiness');
    try {
      const d = await tallyApi('/readiness', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rows: rowsToUse, gateway_url: gatewayUrl, purchase_ledger: purchaseLedger, sales_ledger: salesLedger, bank_contra_groups: bankContraGroups }),
      });
      setReadiness(d);
      say(d.ready ? 'Everything required is already in Tally.' : 'Some masters need to be created in Tally before importing.', d.ready);
    } catch (e) { say(e.message, false); }
    setBusy('');
  }

  async function downloadMastersXml() {
    try {
      const r = await fetch(TALLY_API + '/masters-xml', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rows, gateway_url: gatewayUrl, purchase_ledger: purchaseLedger, sales_ledger: salesLedger, bank_contra_groups: bankContraGroups }),
      });
      if (!r.ok) { const d = await r.json().catch(() => ({})); say(d.error || 'Could not build the masters file.', false); return; }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'tally_import_missing_masters.xml';
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      say('Downloaded. In Tally: Gateway of Tally → Import Data → Masters, then pick this file.', true);
    } catch (e) { say(e.message, false); }
  }

  async function mapTaxLedger(rawTaxName, chosenLedger) {
    if (!chosenLedger) return;
    setBusy('tax-map');
    try {
      const current = await tallyApi('/mapping', { method: 'GET' });
      const merged = { ...(current.mapping || {}), [rawTaxName]: chosenLedger };
      await tallyApi('/mapping', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mapping: merged }),
      });
      say(`Mapped ${rawTaxName} → ${chosenLedger}.`, true);
      const rowsOut = await resolveLedgers();
      await checkReadiness(rowsOut || undefined);
    } catch (e) { say(e.message, false); }
    setBusy('');
  }

  async function createMastersLive() {
    setBusy('create-masters');
    try {
      const d = await tallyApi('/create-masters', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rows, gateway_url: gatewayUrl, purchase_ledger: purchaseLedger, sales_ledger: salesLedger, bank_contra_groups: bankContraGroups }),
      });
      say(`Created ${d.created}, failed ${d.failed}. Refreshing ledgers and re-resolving rows…`, d.failed === 0);
      const freshLedgers = await refreshLedgers();
      const freshRows = freshLedgers ? await resolveLedgers(freshLedgers.ledgers, freshLedgers.bank_ledger_names) : null;
      await checkReadiness(freshRows || undefined);
    } catch (e) { say(e.message, false); }
    setBusy('');
  }

  async function postSelected() {
    const selected = rows.filter(r => r.select);
    if (!selected.length) return;
    setBusy('post');
    try {
      const d = await tallyApi('/post', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rows, gateway_url: gatewayUrl, purchase_ledger: purchaseLedger, sales_ledger: salesLedger }),
      });
      const byId = Object.fromEntries(d.results.map(r => [r.row_id, r]));
      setRows(prev => prev.map(r => byId[r.row_id] ? { ...r, status: byId[r.row_id].status, error: byId[r.row_id].error } : r));
      setRunResults(prev => [...prev, ...d.results]);
      say(`Run complete: ${d.posted} posted, ${d.failed} failed.`, d.failed === 0);
    } catch (e) { say(e.message, false); }
    setBusy('');
  }

  async function downloadLog() {
    if (!runResults.length) return;
    const r = await fetch(TALLY_API + '/log.xlsx', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ results: runResults }),
    });
    if (!r.ok) { say('Could not build log file.', false); return; }
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `tally_import_log_${Date.now()}.xlsx`;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
  }

  function updateRow(rowId, field, value) {
    setRows(prev => prev.map(r => r.row_id === rowId ? { ...r, [field]: value } : r));
  }

  function bulkSelect(val) {
    setRows(prev => prev.map(r => (!statusFilter || r.status === statusFilter) ? { ...r, select: val } : r));
  }

  function toggleSort(field) {
    if (sortField === field) setSortDir(d => (d === 'asc' ? 'desc' : 'asc'));
    else { setSortField(field); setSortDir('asc'); }
  }

  let view = statusFilter ? rows.filter(r => r.status === statusFilter) : rows;
  if (searchText.trim()) {
    const needle = searchText.trim().toLowerCase();
    view = view.filter(r => SEARCHABLE_COLS.some(k => String(r[k] ?? '').toLowerCase().includes(needle)));
  }
  if (sortField) {
    view = [...view].sort((a, b) => {
      const av = a[sortField], bv = b[sortField];
      const an = Number(av), bn = Number(bv);
      const cmp = (!isNaN(an) && !isNaN(bn) && av !== null && bv !== null)
        ? an - bn
        : String(av ?? '').localeCompare(String(bv ?? ''));
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }
  const nSelected = rows.filter(r => r.select).length;
  const statuses = [...new Set(rows.map(r => r.status).filter(Boolean))].sort();

  return h('div', { style: { display: 'flex', gap: 20, alignItems: 'flex-start' } },
    // sidebar
    h('div', { style: { width: 260, flexShrink: 0 } },
      h('div', { className: 'card' },
        h('h4', null, h('i', { className: 'fa fa-plug', style: { color: '#16a34a', marginRight: 6 } }), 'Tally Connection'),
        h('label', { style: labelStyle }, 'Gateway URL'),
        h('input', { className: 'input', style: inputStyle, value: gatewayUrl, onChange: e => setGatewayUrl(e.target.value) }),
        h('button', { className: 'btn btn-sm', style: { marginTop: 8, width: '100%' }, disabled: busy === 'conn', onClick: checkConnection }, busy === 'conn' ? 'Checking…' : 'Check connection'),
        connMsg && h('div', { style: { marginTop: 8, fontSize: 12, padding: 8, borderRadius: 6, background: connOk ? '#dcfce7' : '#fef2f2', color: connOk ? '#166534' : '#b91c1c' } }, connMsg),
        h('button', { className: 'btn btn-sm', style: { marginTop: 8, width: '100%' }, disabled: busy === 'ledgers', onClick: refreshLedgers }, busy === 'ledgers' ? 'Loading…' : 'Refresh ledger list'),
        h('div', { style: { fontSize: 11, color: '#6b7280', marginTop: 6 } }, ledgerNames.length ? `${ledgerNames.length} ledgers loaded.` : 'No ledgers loaded yet.'),
      ),
      h('div', { className: 'card', style: { marginTop: 14 } },
        h('h4', null, 'Default P&L Ledgers'),
        h('label', { style: labelStyle }, 'Purchase ledger'),
        h('input', { className: 'input', style: inputStyle, value: purchaseLedger, onChange: e => setPurchaseLedger(e.target.value) }),
        h('label', { style: { ...labelStyle, marginTop: 8 } }, 'Sales ledger'),
        h('input', { className: 'input', style: inputStyle, value: salesLedger, onChange: e => setSalesLedger(e.target.value) }),
      ),
      h(BankRulesPanel, {}),
    ),

    // main
    h('div', { style: { flex: 1, minWidth: 0 } },
      toast && h('div', { style: { padding: '8px 12px', borderRadius: 8, marginBottom: 12, fontSize: 13, background: toast.ok ? '#dcfce7' : '#fef2f2', color: toast.ok ? '#166534' : '#b91c1c' } }, toast.msg),

      h('div', { className: 'card' },
        h('h4', null, 'Upload source files'),
        h('div', { style: { display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'flex-start' } },
          h(BankUpload, { bankLedgerNames, onRows: newRows => appendRows(newRows) }),
          SOURCES.map(s => h(SourceUpload, {
            key: s.key, source: s, busy: busy === 'upload-' + s.key,
            onUpload: (file, mode) => uploadFile(s.key, file, mode),
            gstr1Mode, setGstr1Mode,
          })),
        ),
      ),

      h('div', { className: 'card', style: { marginTop: 14 } },
        h('h4', null, 'Readiness check'),
        h('div', { style: { fontSize: 11.5, color: '#6b7280', marginBottom: 10 } },
          'Checks whether the vendor ledgers, expense/asset ledgers, and the "Indirect Expense" / "Capital Asset" ' +
          'voucher types this run needs already exist in Tally. Nothing is created automatically — create ' +
          'anything missing directly in Tally, then re-check.'),
        h('button', { className: 'btn btn-sm', disabled: busy === 'readiness', onClick: () => checkReadiness() }, busy === 'readiness' ? 'Checking…' : 'Check readiness'),
        readiness && h(ReadinessPanel, {
          readiness, onDownloadMasters: downloadMastersXml, onCreateMasters: createMastersLive, creating: busy === 'create-masters',
          bankContraGroups, setBankContraGroups,
          taxLedgerNames: ledgers.filter(l => l.category === 'Duties & Taxes').map(l => l.name),
          onMapTaxLedger: mapTaxLedger,
        }),
      ),

      h('div', { className: 'card', style: { marginTop: 14 } },
        h('h4', null, 'Staging'),
        h('div', { style: { display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', marginBottom: 10 } },
          h('button', { className: 'btn btn-sm', disabled: busy === 'resolve', onClick: () => resolveLedgers() }, busy === 'resolve' ? 'Resolving…' : 'Resolve ledgers (fuzzy match)'),
          h('span', null, 'Dup-check:'),
          h('input', { type: 'date', className: 'input', value: dupFrom, onChange: e => setDupFrom(e.target.value) }),
          h('span', null, 'to'),
          h('input', { type: 'date', className: 'input', value: dupTo, onChange: e => setDupTo(e.target.value) }),
          h('button', { className: 'btn btn-sm', disabled: busy === 'dup', onClick: runDupCheck }, busy === 'dup' ? 'Checking…' : 'Run duplicate check'),
        ),
        h('div', { style: { fontSize: 11, color: '#94a3b8', marginBottom: 10 } },
          'Best-effort: on some Tally configurations this report returns no data even when vouchers exist — verify manually before posting if unsure.'),

        rows.length === 0
          ? h('div', { style: { color: '#64748b', fontSize: 13 } }, 'Upload and parse at least one source above to populate the staging table.')
          : h(React.Fragment, null,
              h('div', { style: { display: 'flex', gap: 10, alignItems: 'center', marginBottom: 8, flexWrap: 'wrap' } },
                h('select', { className: 'input', value: statusFilter, onChange: e => setStatusFilter(e.target.value) },
                  h('option', { value: '' }, 'All statuses'),
                  statuses.map(s => h('option', { key: s, value: s }, s)),
                ),
                h('input', {
                  className: 'input', placeholder: 'Search narration, ledger, error…', value: searchText,
                  onChange: e => setSearchText(e.target.value), style: { minWidth: 220 },
                }),
                h('button', { className: 'btn btn-sm', onClick: () => bulkSelect(true) }, 'Select all shown'),
                h('button', { className: 'btn btn-sm', onClick: () => bulkSelect(false) }, 'Deselect all shown'),
                h('span', { style: { fontSize: 12, color: '#6b7280' } }, `${nSelected} row(s) selected (${view.length} shown)`),
              ),
              h(StagingTable, { rows: view, ledgerNames, expenseLedgers, onChange: updateRow, sortField, sortDir, onSort: toggleSort }),
              h('button', {
                className: 'btn btn-primary', style: { marginTop: 12 },
                disabled: nSelected === 0 || busy === 'post', onClick: postSelected,
              }, busy === 'post' ? 'Posting…' : `Approve & post ${nSelected} selected row(s)`),
            ),
      ),

      runResults.length > 0 && h('div', { className: 'card', style: { marginTop: 14 } },
        h('h4', null, 'Run summary'),
        h('div', { style: { fontSize: 13 } },
          `Posted: ${runResults.filter(r => r.result === 'Posted').length} · Failed: ${runResults.filter(r => r.result === 'Failed').length}`),
        h('button', { className: 'btn btn-sm', style: { marginTop: 8 }, onClick: downloadLog }, 'Download posting log (xlsx)'),
      ),
    ),
  );
}

const BANK_CONTRA_GROUP_OPTIONS = [
  'Sundry Creditors', 'Sundry Debtors', 'Indirect Expenses', 'Direct Expenses',
  'Purchase Accounts', 'Sales Accounts', 'Bank Accounts', 'Current Liabilities',
  'Current Assets', 'Suspense A/c',
];

function ReadinessPanel({ readiness, onDownloadMasters, onCreateMasters, creating, bankContraGroups, setBankContraGroups, taxLedgerNames, onMapTaxLedger }) {
  const okColor = '#166534', badColor = '#b91c1c';
  const row = (label, ok, detail, key) => h('div', {
    key, style: { display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', fontSize: 12.5 },
  },
    h('i', { className: `fa ${ok ? 'fa-circle-check' : 'fa-circle-xmark'}`, style: { color: ok ? okColor : badColor } }),
    h('span', { style: { fontWeight: 600 } }, label),
    detail && h('span', { style: { color: '#6b7280' } }, detail),
  );

  return h('div', { style: { marginTop: 12, paddingTop: 10, borderTop: '1px solid #f1f5f9' } },
    h('div', { style: { fontWeight: 700, fontSize: 12.5, marginBottom: 4, color: readiness.ready ? okColor : badColor } },
      readiness.ready ? 'Ready to import' : 'Missing masters — create these in Tally first'),

    Object.entries(readiness.voucher_types || {}).map(([name, exists]) =>
      row(`Voucher Type: ${name}`, exists, exists ? '' : '(create under Purchase base type)', name)),

    Object.entries(readiness.default_ledgers || {}).map(([key, v]) =>
      row(`Ledger: ${v.name}`, v.exists, v.exists ? '' : '(missing default ledger)', key)),

    (readiness.row_issues || []).map((issue, i) => issue.kind === 'bank_contra'
      ? h('div', { key: i, style: { display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', fontSize: 12.5 } },
          h('i', { className: 'fa fa-circle-xmark', style: { color: badColor } }),
          h('span', { style: { fontWeight: 600 } }, `Bank contra ledger: ${issue.name}`),
          h('select', {
            style: { fontSize: 12 }, value: bankContraGroups[issue.name] || '',
            onChange: e => setBankContraGroups(prev => ({ ...prev, [issue.name]: e.target.value })),
          },
            h('option', { value: '' }, 'Pick a group to create it…'),
            BANK_CONTRA_GROUP_OPTIONS.map(g => h('option', { key: g, value: g }, g)),
          ),
        )
      : issue.kind === 'tax_ledger'
      ? h('div', { key: i, style: { display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', fontSize: 12.5 } },
          h('i', { className: 'fa fa-circle-xmark', style: { color: badColor } }),
          h('span', { style: { fontWeight: 600 } }, `Tax ledger: ${issue.name}`),
          h('span', { style: { color: '#6b7280' } }, '— already in Tally under a different name?'),
          h('select', {
            style: { fontSize: 12 }, value: '',
            onChange: e => onMapTaxLedger(issue.name, e.target.value),
          },
            h('option', { value: '' }, 'Map to existing ledger…'),
            (taxLedgerNames || []).map(n => h('option', { key: n, value: n }, n)),
          ),
        )
      : row(
          issue.kind === 'vendor' ? `Vendor ledger: ${issue.name}`
            : issue.kind === 'bank_ledger' ? `Bank ledger: ${issue.name}`
            : `Expense/asset ledger: ${issue.name}`,
          false,
          issue.kind === 'vendor' ? `(GSTIN ${issue.gstin || '—'} — not found by GSTIN or name)`
            : issue.kind === 'bank_ledger' ? '(not yet in Tally — will be created under Bank Accounts)'
            : `(${issue.category || 'Purchase'} — not yet in Tally)`,
          i,
        )),

    (readiness.row_issues || []).length === 0 && Object.keys(readiness.voucher_types || {}).length === 0 && Object.keys(readiness.default_ledgers || {}).length === 0 &&
      h('div', { style: { fontSize: 12, color: '#6b7280' } }, 'Nothing to check yet — upload and resolve rows first for a full picture.'),

    !readiness.ready && h('div', { style: { marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' } },
      h('button', { className: 'btn btn-sm', style: { background: '#dcfce7', color: '#166534' }, disabled: creating, onClick: onCreateMasters },
        h('i', { className: 'fa fa-bolt', style: { marginRight: 4 } }), creating ? 'Creating…' : 'Create in Tally now'),
      h('button', { className: 'btn btn-sm', onClick: onDownloadMasters },
        h('i', { className: 'fa fa-download', style: { marginRight: 4 } }), 'Download as Tally import file instead'),
    ),
  );
}

function BankRulesPanel() {
  const [open, setOpen] = React.useState(false);
  const [rules, setRules] = React.useState([]);
  const [loaded, setLoaded] = React.useState(false);
  const [busy, setBusy] = React.useState(false);

  async function load() {
    setBusy(true);
    try {
      const r = await fetch(TALLY_API + '/bank/rules');
      const d = await r.json();
      setRules(d.rules || []);
      setLoaded(true);
    } catch (e) { /* silent -- non-critical panel */ }
    setBusy(false);
  }

  async function save(next) {
    setRules(next);
    await fetch(TALLY_API + '/bank/rules', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rules: next }),
    });
  }

  function toggle() {
    setOpen(o => !o);
    if (!loaded) load();
  }

  return h('div', { className: 'card', style: { marginTop: 14 } },
    h('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }, onClick: toggle },
      h('h4', { style: { margin: 0 } }, 'Bank narration rules'),
      h('i', { className: `fa fa-chevron-${open ? 'up' : 'down'}`, style: { color: '#94a3b8' } }),
    ),
    open && h('div', { style: { marginTop: 10 } },
      h('div', { style: { fontSize: 11, color: '#6b7280', marginBottom: 8 } },
        'If a bank narration contains this text, auto-assign this ledger as the contra on import. First match wins.'),
      busy && h('div', { style: { fontSize: 12, color: '#6b7280' } }, 'Loading…'),
      rules.map((rule, i) => h('div', { key: i, style: { display: 'flex', gap: 6, marginBottom: 6, alignItems: 'center' } },
        h('input', {
          className: 'input', style: { flex: 1, fontSize: 12 }, placeholder: 'text in narration', value: rule.contains,
          onChange: e => { const next = [...rules]; next[i] = { ...next[i], contains: e.target.value }; setRules(next); },
        }),
        h('span', { style: { fontSize: 11, color: '#94a3b8' } }, '→'),
        h('input', {
          className: 'input', style: { flex: 1, fontSize: 12 }, placeholder: 'Tally ledger name', value: rule.ledger,
          onChange: e => { const next = [...rules]; next[i] = { ...next[i], ledger: e.target.value }; setRules(next); },
        }),
        h('button', {
          className: 'btn btn-sm', style: { padding: '2px 8px' },
          onClick: () => save(rules.filter((_, j) => j !== i)),
        }, h('i', { className: 'fa fa-trash' })),
      )),
      h('div', { style: { display: 'flex', gap: 6, marginTop: 8 } },
        h('button', { className: 'btn btn-sm', onClick: () => setRules([...rules, { contains: '', ledger: '' }]) }, 'Add rule'),
        h('button', { className: 'btn btn-sm', style: { background: '#dcfce7', color: '#166534' }, onClick: () => save(rules) }, 'Save'),
      ),
    ),
  );
}

function BankUpload({ bankLedgerNames, onRows }) {
  const inputRef = React.useRef(null);
  const [file, setFile] = React.useState(null);
  const [preview, setPreview] = React.useState(null); // {headers, sample_rows}
  const [busy, setBusy] = React.useState(false);
  const [err, setErr] = React.useState(null);
  const [bankLedger, setBankLedger] = React.useState('');
  const [amountMode, setAmountMode] = React.useState('separate'); // 'separate' | 'single'
  const [mapping, setMapping] = React.useState({
    date_col: '', narration_col: '', debit_col: '', credit_col: '', amount_col: '', dr_cr_col: '', contra_col: '',
  });
  const [pdfPassword, setPdfPassword] = React.useState('');
  const isPdf = !!file && file.name.toLowerCase().endsWith('.pdf');

  async function handleFile(f, password) {
    setFile(f); setPreview(null); setErr(null); setBusy(true);
    try {
      const fd = new FormData();
      fd.append('file', f);
      if (password) fd.append('password', password);
      const r = await fetch(TALLY_API + '/bank/preview', { method: 'POST', body: fd });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || 'Could not read this file.');
      setPreview(d);
      // best-effort auto-guess so the form isn't empty -- never guess the same
      // column twice (e.g. a lone "Debit/Credit" indicator column shouldn't
      // fill both the debit and credit slots)
      const used = new Set();
      const guess = (needle) => {
        const found = d.headers.find(h => !used.has(h) && h.toLowerCase().includes(needle));
        if (found) used.add(found);
        return found || '';
      };
      setMapping({
        date_col: guess('date'),
        narration_col: guess('narration') || guess('description') || guess('particulars'),
        debit_col: guess('debit') || guess('withdrawal'),
        credit_col: guess('credit') || guess('deposit'),
        amount_col: guess('amount'), dr_cr_col: guess('dr/cr') || guess('type'),
        contra_col: guess('contra') || guess('party') || guess('payee') || guess('vendor'),
      });
    } catch (e) { setErr(e.message); }
    setBusy(false);
  }

  async function handleParse() {
    if (!file) return;
    setBusy(true); setErr(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('bank_ledger', bankLedger);
      if (isPdf && pdfPassword) fd.append('password', pdfPassword);
      const m = { date_col: mapping.date_col, narration_col: mapping.narration_col };
      if (amountMode === 'separate') { m.debit_col = mapping.debit_col; m.credit_col = mapping.credit_col; }
      else { m.amount_col = mapping.amount_col; if (mapping.dr_cr_col) m.dr_cr_col = mapping.dr_cr_col; }
      if (mapping.contra_col) m.contra_col = mapping.contra_col;
      fd.append('mapping', JSON.stringify(m));
      const r = await fetch(TALLY_API + '/bank/parse-mapped', { method: 'POST', body: fd });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || 'Could not parse this file.');
      onRows(d.rows, d.skipped_bad_dates || 0);
      setFile(null); setPreview(null);
      if (inputRef.current) inputRef.current.value = '';
    } catch (e) { setErr(e.message); }
    setBusy(false);
  }

  const colSelect = (label, key) => h('div', { style: { marginBottom: 6 } },
    h('label', { style: { display: 'block', fontSize: 11, color: '#6b7280' } }, label),
    h('select', {
      className: 'input', style: { width: '100%' }, value: mapping[key],
      onChange: e => setMapping(prev => ({ ...prev, [key]: e.target.value })),
    },
      h('option', { value: '' }, '—'),
      (preview?.headers || []).map(hh => h('option', { key: hh, value: hh }, hh)),
    ),
  );

  return h('div', { style: { border: '1px solid #e2e8f0', borderRadius: 8, padding: 10, minWidth: 260, maxWidth: 340 } },
    h('div', { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 } },
      h('span', { style: { fontWeight: 600, fontSize: 13 } }, 'Bank Statement'),
      h('a', {
        href: TALLY_API + '/template/bank', style: { fontSize: 11, color: '#16a34a', textDecoration: 'none' },
        title: 'Download a blank Excel template in the expected format',
      }, h('i', { className: 'fa fa-download', style: { marginRight: 3 } }), 'Template'),
    ),
    h('div', { style: { fontSize: 11, color: '#6b7280', marginBottom: 6 } },
      'Upload any real bank export (Excel, CSV, or PDF) -- pick which column is which below, no fixed template needed.'),

    !preview && !isPdf && h('input', {
      ref: inputRef, type: 'file', accept: '.xlsx,.xls,.csv,.pdf', disabled: busy,
      onChange: e => {
        const f = e.target.files[0];
        if (!f) return;
        if (f.name.toLowerCase().endsWith('.pdf')) { setFile(f); setErr(null); } // wait for password before previewing
        else handleFile(f);
      },
    }),

    !preview && isPdf && h('div', null,
      h('div', { style: { fontSize: 12, marginBottom: 6 } }, `PDF selected: ${file.name}`),
      h('label', { style: { display: 'block', fontSize: 11, color: '#6b7280' } }, 'PDF password (leave blank if none)'),
      h('input', {
        type: 'password', className: 'input', style: { width: '100%', marginBottom: 6 }, value: pdfPassword,
        onChange: e => setPdfPassword(e.target.value),
      }),
      err && h('div', { style: { color: '#b91c1c', fontSize: 11, marginBottom: 6 } }, err),
      h('div', { style: { display: 'flex', gap: 6 } },
        h('button', { className: 'btn btn-sm btn-primary', disabled: busy, onClick: () => handleFile(file, pdfPassword) }, busy ? 'Unlocking…' : 'Unlock & preview'),
        h('button', { className: 'btn btn-sm', disabled: busy, onClick: () => { setFile(null); setPdfPassword(''); setErr(null); } }, 'Cancel'),
      ),
    ),

    preview && h('div', null,
      h('div', { style: { marginBottom: 6 } },
        h('label', { style: { display: 'block', fontSize: 11, color: '#6b7280' } }, 'This statement is for which bank ledger?'),
        h('select', {
          className: 'input', style: { width: '100%' }, value: bankLedger,
          onChange: e => setBankLedger(e.target.value),
        },
          h('option', { value: '' }, '— pick a bank ledger —'),
          (bankLedgerNames || []).map(n => h('option', { key: n, value: n }, n)),
        ),
      ),
      colSelect('Date column', 'date_col'),
      colSelect('Narration column', 'narration_col'),
      colSelect('Contra/Vendor ledger column (optional -- leave blank to rely on narration rules)', 'contra_col'),
      h('div', { style: { marginBottom: 6 } },
        h('label', { style: { display: 'block', fontSize: 11, color: '#6b7280', marginBottom: 2 } }, 'Amount columns'),
        h('select', {
          className: 'input', style: { width: '100%', marginBottom: 6 }, value: amountMode,
          onChange: e => setAmountMode(e.target.value),
        },
          h('option', { value: 'separate' }, 'Separate Debit / Credit columns'),
          h('option', { value: 'single' }, 'One Amount column'),
        ),
      ),
      amountMode === 'separate'
        ? h(React.Fragment, null, colSelect('Debit column', 'debit_col'), colSelect('Credit column', 'credit_col'))
        : h(React.Fragment, null, colSelect('Amount column', 'amount_col'), colSelect('Dr/Cr indicator column (optional)', 'dr_cr_col')),

      err && h('div', { style: { color: '#b91c1c', fontSize: 11, marginBottom: 6 } }, err),
      h('div', { style: { display: 'flex', gap: 6 } },
        h('button', { className: 'btn btn-sm btn-primary', disabled: busy, onClick: handleParse }, busy ? 'Parsing…' : 'Parse'),
        h('button', { className: 'btn btn-sm', disabled: busy, onClick: () => { setFile(null); setPreview(null); } }, 'Cancel'),
      ),
    ),
    !preview && !isPdf && err && h('div', { style: { color: '#b91c1c', fontSize: 11, marginTop: 6 } }, err),
    !preview && !isPdf && busy && h('div', { style: { fontSize: 11, color: '#6b7280', marginTop: 4 } }, 'Reading file…'),
  );
}

function SourceUpload({ source, busy, onUpload, gstr1Mode, setGstr1Mode }) {
  const inputRef = React.useRef(null);
  return h('div', { style: { border: '1px solid #e2e8f0', borderRadius: 8, padding: 10, minWidth: 200 } },
    h('div', { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 } },
      h('span', { style: { fontWeight: 600, fontSize: 13 } }, source.label),
      source.templateUrl && h('a', {
        href: source.templateUrl, style: { fontSize: 11, color: '#16a34a', textDecoration: 'none' },
        title: 'Download a blank template in the expected format',
      }, h('i', { className: 'fa fa-download', style: { marginRight: 3 } }), 'Template'),
    ),
    source.key === 'gstr1' && h('select', {
      className: 'input', style: { marginBottom: 6, width: '100%' },
      value: gstr1Mode, onChange: e => setGstr1Mode(e.target.value),
    },
      h('option', { value: 'source_of_truth' }, 'Source of truth (posts Sales)'),
      h('option', { value: 'cross_check_only' }, 'Cross-check only (stage, no post)'),
    ),
    h('input', {
      ref: inputRef, type: 'file', accept: '.xlsx,.xls,.csv', disabled: busy,
      onChange: e => { const f = e.target.files[0]; if (f) onUpload(f, source.key === 'gstr1' ? gstr1Mode : undefined); if (inputRef.current) inputRef.current.value = ''; },
    }),
    busy && h('div', { style: { fontSize: 11, color: '#6b7280', marginTop: 4 } }, 'Parsing…'),
  );
}

const SORTABLE_COLS = new Set(['status', 'source', 'voucher_type', 'date', 'reference', 'narration', 'primary_ledger', 'contra_ledger', 'amount', 'taxable_value']);

function StagingTable({ rows, ledgerNames, expenseLedgers, onChange, sortField, sortDir, onSort }) {
  return h('div', { style: { overflowX: 'auto', border: '1px solid #e2e8f0', borderRadius: 8 } },
    h('table', { style: { width: '100%', borderCollapse: 'collapse', fontSize: 12 } },
      h('thead', null,
        h('tr', null, DISPLAY_COLS.map(([k, label]) => {
          const sortable = SORTABLE_COLS.has(k);
          const active = sortField === k;
          return h('th', {
            key: k, style: { ...thStyle, cursor: sortable ? 'pointer' : 'default', userSelect: 'none' },
            onClick: sortable ? () => onSort(k) : undefined,
          },
            label,
            active && h('i', { className: `fa fa-caret-${sortDir === 'asc' ? 'up' : 'down'}`, style: { marginLeft: 4, color: '#4f46e5' } }),
          );
        })),
      ),
      h('tbody', null,
        rows.map(row => h('tr', { key: row.row_id, style: { borderTop: '1px solid #f1f5f9' } },
          DISPLAY_COLS.map(([k]) => h('td', { key: k, style: tdStyle }, renderCell(row, k, ledgerNames, expenseLedgers, onChange))),
        )),
      ),
    ),
  );
}

const EXPENSE_CATEGORY_ORDER = ['Purchase', 'Direct Expense', 'Indirect Expense', 'Capital Asset'];

function renderCell(row, field, ledgerNames, expenseLedgers, onChange) {
  if (field === 'select') {
    return h('input', { type: 'checkbox', checked: !!row.select, onChange: e => onChange(row.row_id, 'select', e.target.checked) });
  }
  if (field === 'contra_ledger') {
    return h('select', { style: { fontSize: 12, width: 160 }, value: row.contra_ledger || '', onChange: e => onChange(row.row_id, 'contra_ledger', e.target.value) },
      h('option', { value: '' }, '—'),
      ledgerNames.map(n => h('option', { key: n, value: n }, n)),
    );
  }
  if (field === 'expense_ledger') {
    if (row.source !== 'GSTR2B') return '';
    const byCategory = {};
    const catOf = {};
    (expenseLedgers || []).forEach(l => {
      const label = l.exists_in_tally === false ? `${l.name} (new)` : l.name;
      (byCategory[l.category] = byCategory[l.category] || []).push({ name: l.name, label });
      catOf[l.name] = l.category;
    });
    return h('select', {
      style: { fontSize: 12, width: 180 }, value: row.expense_ledger || '',
      onChange: e => {
        onChange(row.row_id, 'expense_ledger', e.target.value);
        onChange(row.row_id, 'expense_category', catOf[e.target.value] || 'Purchase');
      },
    },
      h('option', { value: '' }, '—'),
      EXPENSE_CATEGORY_ORDER.filter(cat => byCategory[cat]).map(cat =>
        h('optgroup', { key: cat, label: cat }, byCategory[cat].map(o => h('option', { key: o.name, value: o.name }, o.label)))),
    );
  }
  if (field === 'itc_eligible') {
    if (row.source !== 'GSTR2B') return '';
    const val = row.itc_eligible === false ? 'ineligible' : 'eligible';
    return h('select', {
      style: { fontSize: 12, width: 90, color: val === 'ineligible' ? '#b91c1c' : '#166534' },
      value: val, onChange: e => onChange(row.row_id, 'itc_eligible', e.target.value !== 'ineligible'),
    },
      h('option', { value: 'eligible' }, 'Eligible'),
      h('option', { value: 'ineligible' }, 'Ineligible'),
    );
  }
  if (field === 'status') {
    const color = { Ready: '#166534', UnMatched: '#b45309', LedgerNotFound: '#c2410c', Duplicate: '#b91c1c', Posted: '#166534', Failed: '#b91c1c', CrossCheckOnly: '#6b7280' }[row.status] || '#374151';
    return h('span', { style: { color, fontWeight: 600 } }, row.status || '');
  }
  const val = row[field];
  return val === null || val === undefined ? '' : String(val);
}

function isoDaysAgo(n) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

const labelStyle = { display: 'block', fontSize: 11, color: '#6b7280', marginTop: 6, marginBottom: 2 };
const inputStyle = { width: '100%', boxSizing: 'border-box' };
const thStyle = { textAlign: 'left', padding: '6px 8px', background: '#f8fafc', whiteSpace: 'nowrap', position: 'sticky', top: 0 };
const tdStyle = { padding: '6px 8px', whiteSpace: 'nowrap', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis' };
