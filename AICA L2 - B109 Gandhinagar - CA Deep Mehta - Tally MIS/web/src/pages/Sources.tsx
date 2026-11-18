import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';
import { DataTable, Modal, Q } from '../components/ui';
import { useApp } from '../state';
import { TallySyncCard } from '../components/TallySync';

export function SourcesPage() {
  const { companies, companyId } = useApp();
  const qc = useQueryClient();
  const runs = useQuery<any[]>({ queryKey: ['runs'], queryFn: () => api('/api/sync/runs'), refetchInterval: (q) => (q.state.data?.some((r: any) => r.status === 'running') ? 1500 : false) });
  const [msg, setMsg] = useState<{ kind: 'info' | 'error'; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [detail, setDetail] = useState<number | null>(null);
  const act = async (fn: () => Promise<any>, ok?: (r: any) => string) => {
    setBusy(true);
    setMsg(null);
    try {
      const r = await fn();
      if (ok) setMsg({ kind: 'info', text: ok(r) });
      qc.invalidateQueries();
    } catch (e: any) {
      setMsg({ kind: 'error', text: e.message });
    } finally {
      setBusy(false);
    }
  };
  return (
    <div>
      <h1>Data sources &amp; synchronisation</h1>
      <p className="small muted">Bring a company in from TallyPrime over its local XML connection, from Tally XML exports, or load the fictional demo company. Everything stays in memory and is removed when you close the app.</p>
      {msg && <div className={`banner ${msg.kind === 'error' ? 'error' : 'info'}`} role="status">{msg.text}</div>}
      {!companies.length && <div className="banner info">No company data yet. Sync from Tally, import an export, or load the demo company to explore.</div>}

      <TallySyncCard />
      <FileImport companies={companies} companyId={companyId} onDone={(t, kind) => { setMsg({ kind, text: t }); qc.invalidateQueries(); }} />

      <div className="card mt">
        <h2>Demo company</h2>
        <p className="small">Loads a <strong>fictional</strong> distribution company (Apr 2024 – Sep 2026, about 3,900 vouchers) that ships with the app. It is clearly labelled as demo data and never mixed with real companies.</p>
        <button className="btn" disabled={busy} onClick={() => act(() => api('/api/demo/load', { method: 'POST' }), () => 'Demo company loaded. It is selected in the company picker.')}>{busy ? 'Working…' : 'Load demo company'}</button>
      </div>

      <div className="card mt">
        <h2>Synchronisation &amp; import history</h2>
        <Q q={runs}>
          {(rs) => rs.length === 0 ? <p className="muted">Nothing synced in this session yet.</p> : (
            <DataTable rows={rs} pageSize={15} search={false} columns={[
              { key: 'id', label: '#', num: true },
              { key: 'started_at', label: 'Started', render: (r: any) => new Date(r.started_at).toLocaleString() },
              { key: 'mode', label: 'Mode' },
              { key: 'company', label: 'Company', value: (r: any) => companies.find((c) => c.id === r.company_id)?.name ?? '—' },
              { key: 'status', label: 'Status', render: (r: any) => <span style={{ color: r.status === 'succeeded' ? 'var(--good)' : r.status === 'running' ? 'var(--accent)' : 'var(--critical)' }}>{r.status === 'succeeded' ? '●' : r.status === 'running' ? '◌' : '▲'} {r.status}{r.status === 'running' && r.progress?.steps ? ` (${r.progress.done}/${r.progress.steps} steps)` : ''}</span> },
              { key: 'duration', label: 'Duration', value: (r: any) => (r.finished_at ? Math.round((Date.parse(r.finished_at) - Date.parse(r.started_at)) / 100) / 10 : null), render: (r: any) => (r.finished_at ? `${((Date.parse(r.finished_at) - Date.parse(r.started_at)) / 1000).toFixed(1)}s` : '…') },
              { key: 'records', label: 'Records', value: (r: any) => Object.values(r.counts as Record<string, number>).reduce((a, b) => a + b, 0), num: true },
              { key: 'source_label', label: 'Source', render: (r: any) => <span className="small">{r.source_label}</span> },
              { key: 'act', label: '', render: (r: any) => (
                <span className="row">
                  <button className="btn sm" onClick={() => setDetail(r.id)}>Details</button>
                  {r.status === 'running' && <button className="btn sm danger" onClick={() => act(() => api(`/api/sync/runs/${r.id}/cancel`, { method: 'POST' }), () => 'Cancellation requested')}>Cancel</button>}
                </span>) },
            ]} />
          )}
        </Q>
      </div>
      {detail && <RunDetail id={detail} onClose={() => setDetail(null)} />}
    </div>
  );
}

function RunDetail({ id, onClose }: { id: number; onClose: () => void }) {
  const q = useQuery<any>({ queryKey: ['run', id], queryFn: () => api(`/api/sync/runs/${id}`) });
  return (
    <Modal title={`Run #${id}`} onClose={onClose}>
      <Q q={q}>
        {(r) => (
          <div className="small">
            {r.error && <div className="banner error">{r.error}</div>}
            <h3>Record counts</h3>
            <table className="data"><tbody>{Object.entries(r.counts).map(([k, v]) => <tr key={k}><td>{k.replace(/_/g, ' ')}</td><td className="num">{String(v)}</td></tr>)}</tbody></table>
            {r.warnings.length > 0 && <><h3 className="mt">Warnings</h3><ul>{r.warnings.map((w: string, i: number) => <li key={i}>{w}</li>)}</ul></>}
            <h3 className="mt">Steps</h3>
            <table className="data"><thead><tr><th>Step</th><th>Range</th><th>Status</th><th className="num">Records</th><th className="num">Seconds</th><th>Error</th></tr></thead>
              <tbody>{r.batches.map((b: any, i: number) => <tr key={i}><td>{b.entity}</td><td>{b.from_date ? `${b.from_date} → ${b.to_date}` : ''}</td><td>{b.status}</td><td className="num">{b.records}</td><td className="num">{b.seconds}</td><td>{b.error}</td></tr>)}</tbody></table>
          </div>
        )}
      </Q>
    </Modal>
  );
}

function FileImport({ companies, companyId, onDone }: { companies: any[]; companyId: number | null; onDone: (t: string, kind: 'info' | 'error') => void }) {
  const real = companies.filter((c) => !c.is_demo);
  const [target, setTarget] = useState<string>(real.find((c) => c.id === companyId) ? String(companyId) : real[0] ? String(real[0].id) : 'new');
  const [newName, setNewName] = useState('');
  const [asOf, setAsOf] = useState('');
  const [replace, setReplace] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    if (!file) return;
    setBusy(true);
    const p = new URLSearchParams({ filename: file.name });
    if (target === 'new') p.set('newCompany', newName); else p.set('companyId', target);
    if (asOf) p.set('asOf', asOf);
    if (replace) p.set('replaceRange', 'true');
    try {
      const r = await api(`/api/import/xml?${p}`, { raw: file, contentType: 'application/xml' });
      const total = Object.entries(r.counts ?? {}).map(([k, v]) => `${k.replace(/_/g, ' ')}: ${v}`).join(', ');
      onDone(r.status === 'succeeded' ? `Imported ${file.name} — ${total}${r.warnings?.length ? `. ${r.warnings.length} warning(s); see run details.` : ''}` : `Import failed: ${r.error}`, r.status === 'succeeded' ? 'info' : 'error');
    } catch (e: any) {
      onDone(e.message, 'error');
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="card mt">
      <h2>Import a Tally XML export</h2>
      <p className="small muted">Export Day Book, List of Accounts (masters) and Stock Summary from Tally with format XML, then import the masters first. The file is read straight from memory; nothing is saved.</p>
      <div className="grid g4">
        <label className="field">Into company<select value={target} onChange={(e) => setTarget(e.target.value)}>{real.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}<option value="new">+ New company…</option></select></label>
        {target === 'new' && <label className="field">New company name<input value={newName} onChange={(e) => setNewName(e.target.value)} /></label>}
        <label className="field">Balances as of (optional)<input type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} /></label>
        <label className="field">File<input type="file" accept=".xml" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></label>
      </div>
      <label className="small row mt"><input type="checkbox" checked={replace} onChange={(e) => setReplace(e.target.checked)} /> This is a complete Day Book for its date range — remove vouchers in that range that are not in the file</label>
      <button className="btn primary mt" disabled={!file || busy || (target === 'new' && !newName)} onClick={submit}>{busy ? 'Importing…' : 'Import'}</button>
    </div>
  );
}
