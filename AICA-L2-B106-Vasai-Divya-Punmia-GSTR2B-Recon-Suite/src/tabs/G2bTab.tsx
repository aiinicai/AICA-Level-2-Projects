import { useMemo, useState } from 'react';
import { useApp } from '../ctx';
import type { Row } from '../types';
import { itc } from '../lib/engine';
import { amt, short } from '../lib/format';
import { downloadWorkbook, stamp } from '../lib/excel';
import { registerRows } from '../lib/exports';
import { Badge, Card, DataTable, Empty, ExportBtn, Grid, PageHead, Pills, SearchBox, Stat, type Col } from '../components/ui';

export const matchText = (r: Row, q: string) => !q || r.gstin.toLowerCase().includes(q) || r.name.toLowerCase().includes(q) || r.inv.toLowerCase().includes(q);

export default function G2bTab() {
  const { ds, goto } = useApp();
  const [q, setQ] = useState('');
  const [view, setView] = useState<'g2b' | 'bks'>('g2b');
  const rows = view === 'g2b' ? ds.g2b : ds.bks;
  const shown = useMemo(() => rows.filter((r) => matchText(r, q.trim().toLowerCase())), [rows, q]);
  const sum = (f: (r: Row) => number) => shown.reduce((a, r) => a + f(r), 0);

  const cols: Col<Row>[] = [
    { h: 'GSTIN', cell: (r) => <span className="font-mono">{r.gstin}</span> },
    { h: 'Supplier', cell: (r) => r.name || '—', wrap: true },
    { h: 'Invoice no.', cell: (r) => <span className="font-mono">{r.inv}</span>, foot: 'Total' },
    { h: 'Date', cell: (r) => r.date || '—' },
    { h: 'Sheet', cell: (r) => <span className="text-slate-500">{r.sheet}</span> },
    { h: 'Taxable', cell: (r) => amt(r.taxable), num: true, foot: amt(sum((r) => r.taxable)) },
    { h: 'IGST', cell: (r) => amt(r.igst), num: true, foot: amt(sum((r) => r.igst)) },
    { h: 'CGST', cell: (r) => amt(r.cgst), num: true, foot: amt(sum((r) => r.cgst)) },
    { h: 'SGST', cell: (r) => amt(r.sgst), num: true, foot: amt(sum((r) => r.sgst)) },
    { h: 'ITC', cell: (r) => <b>{amt(itc(r))}</b>, num: true, foot: amt(sum(itc)) },
    {
      h: 'Flags',
      cell: (r) => (
        <span className="flex gap-1">
          {r.isAmendment && <Badge tone="sky">Amended</Badge>}
          {r.rcm && (
            <Badge tone="violet" title={r.rcmReason}>
              RCM?
            </Badge>
          )}
          {r.blocked && (
            <Badge tone="red" title={r.blockedReason}>
              17(5)?
            </Badge>
          )}
        </span>
      ),
    },
  ];

  if (!ds.g2b.length && !ds.bks.length)
    return (
      <>
        <PageHead title="GSTR-2B Invoices" />
        <Card>
          <Empty title="No invoices loaded yet">
            Load the GSTR-2B file in{' '}
            <button className="underline text-teal-700" onClick={() => goto('imp')}>
              Import & Settings
            </button>
            .
          </Empty>
        </Card>
      </>
    );

  return (
    <div className="flex flex-col gap-3">
      <PageHead
        title="GSTR-2B Invoices"
        sub="Invoices as read from the files, after adding up split lines of the same invoice and applying amendments. RCM? and 17(5)? are guesses from supplier names — check them in the RCM and Blocked Credits tabs."
        right={<ExportBtn onClick={() => downloadWorkbook(`${view === 'g2b' ? 'GSTR2B' : 'Purchase_register'}_${stamp()}`, [{ name: view === 'g2b' ? 'GSTR-2B' : 'Purchase register', rows: registerRows(shown) }])} />}
      />
      <Grid>
        <Stat label="Invoices" value={shown.length.toLocaleString('en-IN')} sub={q ? `of ${rows.length}` : 'after merging split lines'} tone="teal" />
        <Stat label="Taxable value" value={short(sum((r) => r.taxable))} tone="sky" />
        <Stat label="Total ITC" value={short(sum(itc))} sub={`IGST ${short(sum((r) => r.igst))}`} tone="green" />
        <Stat label="Amended (B2BA)" value={shown.filter((r) => r.isAmendment).length} tone="violet" />
      </Grid>
      <div className="flex flex-col sm:flex-row gap-2 sm:items-center justify-between">
        <Pills
          value={view}
          onChange={setView}
          options={[
            { id: 'g2b', label: 'GSTR-2B', count: ds.g2b.length },
            { id: 'bks', label: 'Purchase register', count: ds.bks.length },
          ]}
        />
        <SearchBox value={q} onChange={setQ} />
      </div>
      <Card pad={false}>
        <DataTable cols={cols} rows={shown} empty="No invoices match your search." />
      </Card>
    </div>
  );
}
