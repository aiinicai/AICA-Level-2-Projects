import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { fmtDate, fmtMoney } from '@shared/format';
import { api, useCompanyQuery } from '../api';
import { BarsChart, TrendChart } from '../components/charts';
import { DataTable, ExportButtons, FLink, Modal, Money, Notes, Pct, Q, Share, Tabs, useTab } from '../components/ui';
import { can, useApp } from '../state';

export function ArApPage() {
  const tab = useTab('receivables');
  const kind = tab === 'payables' ? 'payable' : 'receivable';
  return (
    <div>
      <div className="row"><h1>Receivables &amp; payables</h1><span className="spacer" /><ExportButtons report={`ageing-${kind}`} /></div>
      <Tabs tabs={[{ key: 'receivables', label: 'Receivables' }, { key: 'payables', label: 'Payables' }, { key: 'recon', label: 'Reconciliation & comparison' }]} />
      {tab === 'recon' ? <Recon /> : <Ageing kind={kind} />}
    </div>
  );
}

function BucketEditor() {
  const { company } = useApp();
  return <span className="small muted">Buckets: {(company?.settings.ageingBuckets ?? [30, 60, 90, 180]).join(' / ')} days (change in Company settings)</span>;
}

function Ageing({ kind }: { kind: 'receivable' | 'payable' }) {
  const q = useCompanyQuery<any>('/ageing', { kind });
  const [note, setNote] = useState<any>(null);
  const { user } = useApp();
  const party = kind === 'receivable' ? 'Customer' : 'Supplier';
  return (
    <Q q={q}>
      {(d) => {
        const t = d.totals;
        const top = d.parties.filter((p: any) => p.ledgerBalance > 0).slice(0, 20);
        return (
          <div>
            <div className="row mb"><span className="small muted">As at {fmtDate(d.asOf)} · ageing by due date where recorded</span><span className="spacer" /><BucketEditor /></div>
            <div className="kpis mb">
              <Stat label={`Total trade ${kind}s`} v={t.ledgerBalance} prev={d.previousTotals?.ledgerBalance} />
              <Stat label="Overdue (bill-wise)" v={t.overdue} prev={d.previousTotals?.overdue} />
              <Stat label="Not yet due" v={t.notDue} />
              <Stat label="Advances / unadjusted credits" v={t.advances} />
              <Stat label="On-account (unallocated)" v={t.onAccount} />
              <div className="card"><div className="small secondary">Bill-wise coverage</div><div style={{ fontSize: 20, fontWeight: 650 }}><Pct v={t.billwiseCoveragePct} dp={0} /></div><div className="small muted">{t.parties} parties</div></div>
            </div>
            <Notes notes={d.notes} />
            <div className="grid g2">
              <div className="card"><BarsChart title="Ageing distribution" data={d.bucketLabels.map((b: string) => ({ label: b, value: t.buckets[b] ?? 0 })).filter((x: any) => x.value)} series={[{ key: 'value', label: 'Outstanding' }]} colorBySign /></div>
              <div className="card"><TrendChart title="Outstanding and overdue trend" data={d.trend} xKey="month" series={[{ key: 'total', label: 'Total' }, { key: 'overdue', label: 'Overdue' }]} /></div>
            </div>
            <div className="card mt">
              <h2>Top 20 {party.toLowerCase()}s by outstanding</h2>
              <DataTable rows={top} search={false} pageSize={20} columns={[
                { key: 'party', label: party, render: (r: any) => <FLink to={`/ledgers/${r.ledgerId}`}>{r.party}</FLink> },
                { key: 'ledgerBalance', label: 'Outstanding', num: true, render: (r: any) => <Money v={r.ledgerBalance} /> },
                { key: 'overdue', label: 'Overdue', num: true, render: (r: any) => <Money v={r.overdue} /> },
                ...d.bucketLabels.slice(1, -2).map((b: string) => ({ key: b, label: b, num: true, value: (r: any) => r.buckets[b] ?? 0, render: (r: any) => (r.buckets[b] ? <Money v={r.buckets[b]} /> : <span className="muted">—</span>) })),
                { key: 'share', label: 'Share', value: (r: any) => r.ledgerBalance, render: (r: any) => <Share v={t.ledgerBalance ? (r.ledgerBalance / t.ledgerBalance) * 100 : null} /> },
                { key: 'creditUtilisationPct', label: 'Credit limit used', num: true, render: (r: any) => (r.creditUtilisationPct === null ? <span className="muted">no limit</span> : <span style={{ color: r.creditUtilisationPct > 100 ? 'var(--critical)' : undefined }}>{r.creditUtilisationPct.toFixed(0)}%</span>) },
                { key: 'billwise', label: 'Basis', render: (r: any) => (r.billwise ? 'bill-wise' : <span className="muted" title="No bill allocations: ledger-level exposure only, not aged">ledger only</span>) },
              ]} />
            </div>
            {kind === 'receivable' && (
              <div className="card mt">
                <h2>Collection priorities</h2>
                <p className="small muted">{d.priorityRule}</p>
                <DataTable rows={d.priority} search={false} pageSize={10} empty="No overdue bills" columns={[
                  { key: 'party', label: 'Customer', render: (r: any) => <FLink to={`/ledgers/${r.ledgerId}`}>{r.party}</FLink> },
                  { key: 'bill', label: 'Bill' },
                  { key: 'amount', label: 'Outstanding', num: true, render: (r: any) => <Money v={r.amount} /> },
                  { key: 'daysOverdue', label: 'Days overdue', num: true },
                  { key: 'act', label: '', render: (r: any) => can(user, 'analyst') ? <button className="btn sm" onClick={() => setNote(r)}>Add note</button> : null },
                ]} />
              </div>
            )}
            {kind === 'payable' && (
              <div className="card mt">
                <h2>Upcoming payments (next 60 days)</h2>
                <p className="small muted">Cash requirement: {fmtMoney(d.upcoming.reduce((a: number, u: any) => a + u.amount, 0))} plus overdue {fmtMoney(t.overdue)}.</p>
                <DataTable rows={d.upcoming} search={false} pageSize={10} empty="No bills falling due" columns={[
                  { key: 'dueDate', label: 'Due', render: (r: any) => fmtDate(r.dueDate) }, { key: 'party', label: 'Supplier' }, { key: 'bill', label: 'Bill' },
                  { key: 'amount', label: 'Amount', num: true, render: (r: any) => <Money v={r.amount} /> },
                ]} />
              </div>
            )}
            <div className="card mt">
              <h2>Bill-wise outstanding</h2>
              <DataTable rows={d.bills} columns={[
                { key: 'party', label: party }, { key: 'billName', label: 'Bill' },
                { key: 'billDate', label: 'Bill date', render: (r: any) => fmtDate(r.billDate) },
                { key: 'dueDate', label: 'Due date', render: (r: any) => fmtDate(r.dueDate) },
                { key: 'daysOverdue', label: 'Days overdue', num: true, render: (r: any) => r.daysOverdue === null ? <span className="muted">—</span> : Math.max(0, r.daysOverdue) },
                { key: 'bucket', label: 'Bucket' },
                { key: 'original', label: 'Original', num: true, render: (r: any) => <Money v={r.original} /> },
                { key: 'amount', label: 'Outstanding', num: true, render: (r: any) => <Money v={r.amount} /> },
                { key: 'notes', label: 'Notes', value: (r: any) => r.notes.join('; '), render: (r: any) => <span className="small muted">{r.notes.join('; ')}</span> },
              ]} />
            </div>
            {kind === 'receivable' && d.collectionNotes.length > 0 && (
              <div className="card mt"><h2>Collection notes</h2>
                <DataTable rows={d.collectionNotes} search={false} pageSize={10} columns={[
                  { key: 'created_at', label: 'Date', render: (r: any) => fmtDate(r.created_at) }, { key: 'bill_name', label: 'Bill' }, { key: 'status', label: 'Status' },
                  { key: 'note', label: 'Note' }, { key: 'author', label: 'By' }]} />
              </div>
            )}
            {note && <NoteDialog item={note} onClose={() => setNote(null)} />}
          </div>
        );
      }}
    </Q>
  );
}

function Stat({ label, v, prev }: { label: string; v: number; prev?: number | null }) {
  return (
    <div className="card">
      <div className="small secondary">{label}</div>
      <div style={{ fontSize: 20, fontWeight: 650 }}><Money v={v} /></div>
      {prev !== undefined && prev !== null && <div className="small muted">vs {fmtMoney(prev)}</div>}
    </div>
  );
}

function NoteDialog({ item, onClose }: { item: any; onClose: () => void }) {
  const { companyId } = useApp();
  const qc = useQueryClient();
  const [status, setStatus] = useState('note');
  const [text, setText] = useState('');
  const [err, setErr] = useState<string | null>(null);
  return (
    <Modal title={`Collection note — ${item.party} / ${item.bill}`} onClose={onClose}>
      <label className="field">Status<select value={status} onChange={(e) => setStatus(e.target.value)}>{['note', 'disputed', 'promised', 'escalated', 'resolved'].map((s) => <option key={s}>{s}</option>)}</select></label>
      <label className="field mt">Note<textarea rows={4} value={text} onChange={(e) => setText(e.target.value)} /></label>
      {err && <div className="banner error mt">{err}</div>}
      <button className="btn primary mt" disabled={!text.trim()} onClick={async () => {
        try {
          await api(`/api/c/${companyId}/collection-notes`, { body: { ledgerId: item.ledgerId, billName: item.bill, status, note: text } });
          qc.invalidateQueries();
          onClose();
        } catch (e: any) { setErr(e.message); }
      }}>Save note</button>
    </Modal>
  );
}

function Recon() {
  const ar = useCompanyQuery<any>('/ageing', { kind: 'receivable' });
  const ap = useCompanyQuery<any>('/ageing', { kind: 'payable' });
  return (
    <div>
      <Q q={ar}>{(a) => <Q q={ap}>{(p) => (
        <div>
          <div className="card mb">
            <h2>Receivables vs payables</h2>
            <table className="data"><thead><tr><th></th><th className="num">Receivables</th><th className="num">Payables</th></tr></thead><tbody>
              {[['Ledger balance', 'ledgerBalance'], ['Bill-wise outstanding', 'billTotal'], ['On-account / unallocated', 'onAccount'], ['Unreconciled', 'unreconciled'], ['Overdue', 'overdue'], ['Not yet due', 'notDue']].map(([l, k]) => (
                <tr key={k}><td>{l}</td><td className="num"><Money v={a.totals[k]} exact /></td><td className="num"><Money v={p.totals[k]} exact /></td></tr>
              ))}
            </tbody></table>
            <p className="small muted">Ledger balance = bill-wise outstanding + on-account + unreconciled. Ledgers without bill-wise details are shown at ledger level and excluded from reconciliation.</p>
          </div>
          {[['Receivables', a], ['Payables', p]].map(([label, x]: any) => (
            <div className="card mb" key={label}>
              <h2>{label}: parties whose bills do not reconcile to the ledger</h2>
              <DataTable rows={x.parties.filter((r: any) => Math.abs(r.unreconciled) > 0.5 || r.onAccount)} search={false} pageSize={10} empty="All bill-wise parties reconcile" columns={[
                { key: 'party', label: 'Party', render: (r: any) => <FLink to={`/ledgers/${r.ledgerId}`}>{r.party}</FLink> },
                { key: 'ledgerBalance', label: 'Ledger', num: true, render: (r: any) => <Money v={r.ledgerBalance} exact /> },
                { key: 'billTotal', label: 'Bills', num: true, render: (r: any) => <Money v={r.billTotal} exact /> },
                { key: 'onAccount', label: 'On account', num: true, render: (r: any) => <Money v={r.onAccount} exact /> },
                { key: 'unreconciled', label: 'Difference', num: true, render: (r: any) => <Money v={r.unreconciled} exact /> },
              ]} />
              <h3 className="mt">Abnormal balances</h3>
              <DataTable rows={x.parties.filter((r: any) => r.abnormalSign)} search={false} pageSize={10} empty="None" columns={[
                { key: 'party', label: 'Party', render: (r: any) => <FLink to={`/ledgers/${r.ledgerId}`}>{r.party}</FLink> },
                { key: 'ledgerBalance', label: 'Balance (opposite to normal side)', num: true, render: (r: any) => <Money v={r.ledgerBalance} exact /> },
              ]} />
            </div>
          ))}
        </div>
      )}</Q>}</Q>
    </div>
  );
}
