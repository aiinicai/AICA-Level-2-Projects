import { useMemo, useState } from 'react';
import { Ban, StickyNote } from 'lucide-react';
import { useApp } from '../ctx';
import type { FinalStatus, Row } from '../types';
import { itc, PASS_LABEL, type LedgerLine } from '../lib/engine';
import { amt, signed } from '../lib/format';
import { downloadWorkbook, stamp } from '../lib/excel';
import { excludedRows, ledgerRows } from '../lib/exports';
import { Badge, Btn, Card, DataTable, Empty, ExportBtn, PageHead, Pills, SearchBox, type BadgeTone, type Col } from '../components/ui';
import { matchText } from './G2bTab';

type Filter = 'all' | FinalStatus | 'excl';

export const STATUS_BADGE: Record<FinalStatus, [BadgeTone, string]> = {
  exact: ['green', 'Matched'],
  tol: ['teal', 'Within tolerance'],
  mismatch: ['orange', 'ITC mismatch'],
  smart: ['violet', 'Smart matched'],
  missBooks: ['red', 'Missing in books'],
  miss2b: ['red', 'Missing in 2B'],
};

export default function LedgerTab() {
  const { ds, recon, remarks, openBlock, openRemark, goto, eng } = useApp();
  const [f, setF] = useState<Filter>('all');
  const [q, setQ] = useState('');
  const c = recon.counts;
  const excluded = useMemo(() => [...ds.g2b_excl, ...ds.bks_excl], [ds]);
  const ql = q.trim().toLowerCase();

  const lines = useMemo(
    () => recon.lines.filter((l) => (f === 'all' || l.status === f) && ((l.g2b && matchText(l.g2b, ql)) || (l.bk && matchText(l.bk, ql)))),
    [recon.lines, f, ql]
  );
  const excl = useMemo(() => excluded.filter((r) => matchText(r, ql)), [excluded, ql]);

  if (!ds.g2b.length && !ds.bks.length)
    return (
      <>
        <PageHead title="Reconciliation Ledger" />
        <Card>
          <Empty title="Nothing to reconcile yet">
            Import both files in{' '}
            <button className="underline text-teal-700" onClick={() => goto('imp')}>
              Import & Settings
            </button>
            .
          </Empty>
        </Card>
      </>
    );

  const label = (l: LedgerLine) => {
    const r = (l.g2b || l.bk)!;
    return `${r.name || r.gstin} — invoice ${r.inv}`;
  };

  const cols: Col<LedgerLine>[] = [
    {
      h: 'Status',
      cell: (l) => {
        const [tone, text] = STATUS_BADGE[l.status];
        const ref = (l.g2b || l.bk)!;
        return (
          <span className="flex flex-wrap gap-1">
            <Badge tone={tone} title={l.pass ? PASS_LABEL[l.pass] : undefined}>
              {text}
            </Badge>
            {recon.activeBlocked.has(l.key) && <Badge tone="red">Blocked 17(5)</Badge>}
            {ref.rcm && (
              <Badge tone="violet" title={ref.rcmReason}>
                RCM
              </Badge>
            )}
          </span>
        );
      },
    },
    { h: 'GSTIN', cell: (l) => <span className="font-mono">{(l.g2b || l.bk)!.gstin}</span> },
    { h: 'Supplier', cell: (l) => (l.g2b || l.bk)!.name || '—', wrap: true },
    { h: 'Invoice (2B)', cell: (l) => <span className="font-mono">{l.g2b?.inv ?? '—'}</span> },
    { h: 'Invoice (books)', cell: (l) => <span className="font-mono">{l.bk?.inv ?? '—'}</span> },
    { h: 'Date', cell: (l) => (l.g2b || l.bk)!.date || '—' },
    { h: 'ITC (2B)', cell: (l) => (l.g2b ? amt(itc(l.g2b)) : '—'), num: true },
    { h: 'ITC (books)', cell: (l) => (l.bk ? amt(itc(l.bk)) : '—'), num: true },
    {
      h: 'Difference',
      cell: (l) => (l.g2b && l.bk ? <span className={Math.abs(l.diff) > eng.tolerance ? 'text-orange-600 font-semibold' : 'text-slate-400'}>{signed(l.diff)}</span> : '—'),
      num: true,
    },
    {
      h: 'Note',
      cell: (l) => <span className="text-slate-600 text-[0.7rem]">{remarks[l.key] ?? ''}</span>,
      wrap: true,
    },
    {
      h: 'Actions',
      cell: (l) => {
        const ref: Row = (l.g2b || l.bk)!;
        const isBlocked = recon.activeBlocked.has(l.key);
        return (
          <span className="flex gap-1">
            <Btn small kind={isBlocked ? 'ghost' : 'secondary'} disabled={isBlocked} icon={<Ban className="w-3 h-3" />} onClick={() => openBlock(ref)} title="Block this credit under Section 17(5)">
              {isBlocked ? 'Blocked' : 'Block'}
            </Btn>
            <Btn small icon={<StickyNote className="w-3 h-3" />} onClick={() => openRemark(l.key, label(l))}>
              {remarks[l.key] ? 'Edit note' : 'Note'}
            </Btn>
          </span>
        );
      },
    },
  ];

  const exclCols: Col<Row>[] = [
    { h: 'Register', cell: (r) => (r.source === 'g2b' ? 'GSTR-2B' : 'Books') },
    { h: 'Sheet / row', cell: (r) => `${r.sheet} · row ${r.rowNum}` },
    { h: 'Reason', cell: (r) => <Badge tone="red">{r.reason}</Badge> },
    { h: 'GSTIN', cell: (r) => <span className="font-mono">{r.gstin || '—'}</span> },
    { h: 'Supplier', cell: (r) => r.name || '—', wrap: true },
    { h: 'Invoice no.', cell: (r) => r.inv || '—' },
    { h: 'Date', cell: (r) => r.date || '—' },
    { h: 'Taxable', cell: (r) => amt(r.taxable), num: true },
    { h: 'ITC', cell: (r) => amt(itc(r)), num: true },
  ];

  return (
    <div className="flex flex-col gap-3">
      <PageHead
        title="Reconciliation Ledger"
        sub={`Every invoice from both files, once, in its final status. Differences up to ₹${eng.tolerance} count as matched. Double-click a row to add a note.`}
        right={
          <ExportBtn
            onClick={() =>
              downloadWorkbook(`Recon_ledger_${f}_${stamp()}`, [f === 'excl' ? { name: 'Excluded rows', rows: excludedRows(excl) } : { name: 'Reconciliation ledger', rows: ledgerRows(lines, remarks, recon.activeBlocked) }])
            }
          />
        }
      />
      <Pills
        value={f}
        onChange={setF}
        options={[
          { id: 'all', label: 'All', count: c.total },
          { id: 'exact', label: 'Matched', count: c.exact },
          { id: 'tol', label: 'Within tolerance', count: c.tol },
          { id: 'mismatch', label: 'ITC mismatch', count: c.mismatch },
          { id: 'smart', label: 'Smart matched', count: c.smart },
          { id: 'missBooks', label: 'Missing in books', count: c.missBooks },
          { id: 'miss2b', label: 'Missing in 2B', count: c.miss2b },
          { id: 'excl', label: 'Excluded rows', count: excluded.length },
        ]}
      />
      <SearchBox value={q} onChange={setQ} />
      <Card pad={false}>
        {f === 'excl' ? (
          <DataTable cols={exclCols} rows={excl} empty="No rows were excluded — every row had a GSTIN and invoice no." />
        ) : (
          <DataTable cols={cols} rows={lines} empty="No invoices in this group." onRowDoubleClick={(l) => openRemark(l.key, label(l))} />
        )}
      </Card>
    </div>
  );
}
