import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { fmtDate } from '@shared/format';
import { useCompanyQuery } from '../api';
import { BarsChart } from '../components/charts';
import { DataTable, ExportButtons, FLink, Money, Q } from '../components/ui';

export function LedgerPage() {
  const { lid } = useParams();
  const [page, setPage] = useState(1);
  const q = useCompanyQuery<any>(`/ledgers/${lid}`, { page: String(page) });
  return (
    <Q q={q}>
      {(d) => (
        <div>
          <div className="row">
            <div><h1>{d.ledger.name}</h1>
              <p className="small muted">{d.ledger.group ?? 'No group'} → {d.ledger.primaryGroup ?? '—'} · Class: <strong>{d.ledger.classLabel}</strong> ({d.ledger.status}{d.ledger.status !== 'verified' ? `, ${Math.round(d.ledger.confidence * 100)}% confidence` : ''}) · <FLink to="/settings/mapping">change</FLink></p>
              <p className="small muted">{d.ledger.rationale}</p>
            </div>
            <span className="spacer" /><ExportButtons report={`ledger-${d.ledger.id}`} />
          </div>
          <div className="kpis mb">
            <div className="card"><div className="small secondary">Opening (Dr+ / Cr−)</div><div style={{ fontSize: 20, fontWeight: 650 }}><Money v={d.opening} exact /></div></div>
            <div className="card"><div className="small secondary">Closing (Dr+ / Cr−)</div><div style={{ fontSize: 20, fontWeight: 650 }}><Money v={d.closing} exact /></div></div>
            <div className="card"><div className="small secondary">Transactions in period</div><div style={{ fontSize: 20, fontWeight: 650 }}>{d.total}</div></div>
          </div>
          {d.monthly.length > 0 && <div className="card mb"><BarsChart title="Monthly debits and credits" data={d.monthly} xKey="month" series={[{ key: 'debit', label: 'Debits' }, { key: 'credit', label: 'Credits' }]} /></div>}
          <div className="card">
            <DataTable rows={d.rows} pageSize={50} columns={[
              { key: 'date', label: 'Date', render: (r: any) => fmtDate(r.date) },
              { key: 'type', label: 'Type' },
              { key: 'number', label: 'No.', render: (r: any) => <FLink to={`/vouchers/${r.voucherId}`}>{r.number || 'view'}</FLink> },
              { key: 'party', label: 'Party' },
              { key: 'narration', label: 'Narration', render: (r: any) => <span className="small">{r.narration}</span> },
              { key: 'debit', label: 'Debit', num: true, render: (r: any) => (r.debit ? <Money v={r.debit} exact /> : '') },
              { key: 'credit', label: 'Credit', num: true, render: (r: any) => (r.credit ? <Money v={r.credit} exact /> : '') },
              { key: 'balance', label: 'Balance', num: true, render: (r: any) => <Money v={r.balance} exact /> },
            ]} />
            {d.total > d.pageSize && (
              <div className="row mt"><button className="btn sm" disabled={page === 1} onClick={() => setPage(page - 1)}>‹ Earlier</button>
                <span className="small">Page {page} of {Math.ceil(d.total / d.pageSize)} (server-side)</span>
                <button className="btn sm" disabled={page * d.pageSize >= d.total} onClick={() => setPage(page + 1)}>Later ›</button></div>
            )}
          </div>
        </div>
      )}
    </Q>
  );
}

export function VoucherPage() {
  const { vid } = useParams();
  const q = useCompanyQuery<any>(`/vouchers/${vid}`);
  return (
    <Q q={q}>
      {(v) => (
        <div>
          <h1>{v.type} {v.number}</h1>
          <p className="small muted">{fmtDate(v.date)} · base type {v.baseType}{v.party ? ` · party ${v.party}` : ''} · Tally GUID <span className="mono">{v.guid ?? '—'}</span> · AlterID {v.alterId ?? '—'}</p>
          {(!v.isAccounting) && <div className="banner warn">This voucher does not affect the accounts{v.isCancelled ? ' (cancelled)' : v.isOptional ? ' (optional)' : ` (${v.baseType} vouchers are non-posting)`}.</div>}
          {v.unbalancedBy !== 0 && <div className="banner error">Unbalanced: debits − credits = {v.unbalancedBy}</div>}
          {v.narration && <p>{v.narration}</p>}
          <div className="card mb"><h2>Ledger entries</h2>
            <table className="data"><thead><tr><th>Ledger</th><th>Class</th><th className="num">Debit</th><th className="num">Credit</th></tr></thead>
              <tbody>{v.lines.map((l: any, i: number) => <tr key={i}><td><FLink to={`/ledgers/${l.ledgerId}`}>{l.ledger}</FLink></td><td className="small muted">{l.classCode ?? 'unclassified'}</td><td className="num">{l.debit ? <Money v={l.debit} exact /> : ''}</td><td className="num">{l.credit ? <Money v={l.credit} exact /> : ''}</td></tr>)}</tbody></table>
          </div>
          {v.inventory.length > 0 && <div className="card mb"><h2>Inventory</h2>
            <table className="data"><thead><tr><th>Item</th><th>Direction</th><th className="num">Qty</th><th className="num">Value</th><th>Godown</th><th>Batch</th><th>Expiry</th></tr></thead>
              <tbody>{v.inventory.map((i: any, k: number) => <tr key={k}><td>{i.item}</td><td>{i.direction}</td><td className="num">{i.qty} {i.unit}</td><td className="num"><Money v={i.value} exact /></td><td>{i.godown}</td><td>{i.batch}</td><td>{fmtDate(i.expiry)}</td></tr>)}</tbody></table></div>}
          {v.bills.length > 0 && <div className="card mb"><h2>Bill allocations</h2>
            <table className="data"><thead><tr><th>Ledger</th><th>Bill</th><th>Type</th><th className="num">Amount (Dr+)</th><th>Due</th></tr></thead>
              <tbody>{v.bills.map((b: any, k: number) => <tr key={k}><td>{b.ledger}</td><td>{b.bill}</td><td>{b.type}</td><td className="num"><Money v={b.amount} exact /></td><td>{fmtDate(b.dueDate)}</td></tr>)}</tbody></table></div>}
          {v.costCentres.length > 0 && <div className="card"><h2>Cost-centre allocations</h2>
            <table className="data"><tbody>{v.costCentres.map((c: any, k: number) => <tr key={k}><td>{c.costCentre}</td><td>{c.ledger}</td><td className="num"><Money v={c.amount} exact /></td></tr>)}</tbody></table></div>}
        </div>
      )}
    </Q>
  );
}
