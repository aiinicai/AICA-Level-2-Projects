import { useMemo } from 'react';
import { useApp } from '../ctx';
import type { Row } from '../types';
import { itc, rcmRegister } from '../lib/engine';
import { amt, short } from '../lib/format';
import { downloadWorkbook, stamp } from '../lib/excel';
import { rowCols } from '../lib/exports';
import { Badge, Card, DataTable, ExportBtn, Grid, Notice, PageHead, Stat, type Col } from '../components/ui';

export default function RcmTab() {
  const { ds } = useApp();
  const rows = useMemo(() => rcmRegister(ds), [ds]);
  const sum = (f: (r: Row) => number) => rows.reduce((a, r) => a + f(r), 0);
  const cols: Col<Row & { origin: string }>[] = [
    { h: 'Source', cell: (r) => <Badge tone={r.origin === 'RCM file' ? 'violet' : 'slate'}>{r.origin}</Badge> },
    { h: 'GSTIN', cell: (r) => <span className="font-mono">{r.gstin}</span> },
    { h: 'Supplier', cell: (r) => (
      <span>
        {r.name || '—'}
        {r.rcmReason && <span className="block text-[0.65rem] text-violet-600">{r.rcmReason}</span>}
      </span>
    ), wrap: true },
    { h: 'Invoice no.', cell: (r) => <span className="font-mono">{r.inv}</span>, foot: 'Total' },
    { h: 'Date', cell: (r) => r.date || '—' },
    { h: 'Taxable', cell: (r) => amt(r.taxable), num: true, foot: amt(sum((r) => r.taxable)) },
    { h: 'IGST', cell: (r) => amt(r.igst), num: true, foot: amt(sum((r) => r.igst)) },
    { h: 'CGST', cell: (r) => amt(r.cgst), num: true, foot: amt(sum((r) => r.cgst)) },
    { h: 'SGST', cell: (r) => amt(r.sgst), num: true, foot: amt(sum((r) => r.sgst)) },
    { h: 'RCM tax', cell: (r) => <b>{amt(itc(r))}</b>, num: true, foot: amt(sum(itc)) },
  ];
  return (
    <div className="flex flex-col gap-3">
      <PageHead
        title="RCM Purchase Bills"
        sub="Reverse-charge bills under Section 9(3) / 9(4): from the separate RCM file, plus invoices marked reverse charge (or whose supplier name suggests GTA, advocate, security or insurance agent) in GSTR-2B or books."
        right={<ExportBtn onClick={() => downloadWorkbook(`RCM_bills_${stamp()}`, [{ name: 'RCM bills', rows: rows.map((r) => ({ Source: r.origin, ...rowCols(r), Reason: r.rcmReason ?? '' })) }])} />}
      />
      <Grid cols={3}>
        <Stat label="RCM bills" value={rows.length} tone="violet" />
        <Stat label="Taxable value" value={short(sum((r) => r.taxable))} tone="sky" />
        <Stat label="Tax payable under RCM" value={short(sum(itc))} sub="pay in 3.1(d), claim in 4(A)(3)" tone="teal" />
      </Grid>
      <Notice>Name-based detection is a prompt to check, not a decision. Pay the tax in cash in Table 3.1(d) and claim the same amount as ITC in Table 4(A)(3).</Notice>
      <Card pad={false}>
        <DataTable cols={cols} rows={rows} empty="No reverse-charge bills found. Upload an RCM file in Import & Settings, or mark the Reverse Charge column in your registers." />
      </Card>
    </div>
  );
}
