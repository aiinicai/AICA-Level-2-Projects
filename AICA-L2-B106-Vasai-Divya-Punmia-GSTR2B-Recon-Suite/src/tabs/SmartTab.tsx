import { useMemo, useState } from 'react';
import { useApp } from '../ctx';
import type { SmartResult } from '../types';
import { itc, PASS_LABEL } from '../lib/engine';
import { amt, signed } from '../lib/format';
import { downloadWorkbook, stamp } from '../lib/excel';
import { rowCols } from '../lib/exports';
import { Badge, Card, DataTable, Empty, ExportBtn, Notice, PageHead, Pills, type Col } from '../components/ui';

type View = 'p1' | 'p2' | 'p3' | 'unr';

const HELP: Record<View, React.ReactNode> = {
  p1: (
    <>
      <b>Pass 1 — invoice core.</b> Same GSTIN, and the invoice numbers have the same digits once prefixes, financial-year tags (2025-26) and leading zeros are removed. Example:{' '}
      <code>ST/2025-26/0091</code> matches <code>INV/91</code>.
    </>
  ),
  p2: (
    <>
      <b>Pass 2 — amount + date.</b> Same GSTIN, same total ITC and same invoice date, even though the invoice numbers look different (e.g. <code>ACME-402</code> vs <code>402/AC</code>).
    </>
  ),
  p3: (
    <>
      <b>Pass 3 — tax values.</b> Same GSTIN, taxable value, IGST, CGST and SGST; invoice no. and date are ignored. Check these before claiming.
    </>
  ),
  unr: (
    <>
      <b>Unresolved.</b> Not matched by the primary match or any smart pass. Book missing purchases, or follow up with the supplier for invoices missing from GSTR-2B.
    </>
  ),
};

export default function SmartTab() {
  const { recon, goto, ds } = useApp();
  const [v, setV] = useState<View>('p1');
  const groups = useMemo(() => {
    const s = recon.smart;
    return {
      p1: s.filter((x) => x.s === 'cm' || x.s === 'cx'),
      p2: s.filter((x) => x.s === 'ad'),
      p3: s.filter((x) => x.s === 'ti'),
      unr: s.filter((x) => x.s === 'smb' || x.s === 'sm2'),
    };
  }, [recon.smart]);
  const rows = groups[v];

  if (!ds.g2b.length || !ds.bks.length)
    return (
      <>
        <PageHead title="Smart Match Runs" />
        <Card>
          <Empty title="Load both files first">
            Smart matching runs on invoices the primary match could not pair.{' '}
            <button className="underline text-teal-700" onClick={() => goto('imp')}>
              Import files
            </button>
          </Empty>
        </Card>
      </>
    );

  const matchCols: Col<SmartResult>[] = [
    { h: 'Pass', cell: (r) => <Badge tone={r.s === 'cx' ? 'orange' : 'violet'}>{PASS_LABEL[r.s]}</Badge> },
    { h: 'GSTIN', cell: (r) => <span className="font-mono">{r.g2b!.gstin}</span> },
    { h: 'Supplier', cell: (r) => r.g2b!.name || '—', wrap: true },
    { h: 'Invoice (2B)', cell: (r) => <span className="font-mono">{r.g2b!.inv}</span> },
    { h: 'Invoice (books)', cell: (r) => <span className="font-mono">{r.bk!.inv}</span> },
    ...(v === 'p1' ? [{ h: 'Core', cell: (r: SmartResult) => <span className="font-mono text-violet-700">{r.gc}</span> }] : []),
    { h: 'Date (2B)', cell: (r) => r.g2b!.date || '—' },
    { h: 'Date (books)', cell: (r) => <span className={r.g2b!.date !== r.bk!.date ? 'text-amber-700 font-semibold' : ''}>{r.bk!.date || '—'}</span> },
    { h: 'ITC (2B)', cell: (r) => amt(itc(r.g2b!)), num: true },
    { h: 'ITC (books)', cell: (r) => amt(itc(r.bk!)), num: true },
    { h: 'Difference', cell: (r) => signed(r.diff), num: true },
  ];

  const unrCols: Col<SmartResult>[] = [
    { h: 'Status', cell: (r) => <Badge tone="red">{r.s === 'smb' ? 'Missing in books' : 'Missing in 2B'}</Badge> },
    { h: 'GSTIN', cell: (r) => <span className="font-mono">{(r.g2b || r.bk)!.gstin}</span> },
    { h: 'Supplier', cell: (r) => (r.g2b || r.bk)!.name || '—', wrap: true },
    { h: 'Invoice no.', cell: (r) => <span className="font-mono">{(r.g2b || r.bk)!.inv}</span> },
    { h: 'Core', cell: (r) => <span className="font-mono text-slate-500">{r.gc || r.bc || '—'}</span> },
    { h: 'Date', cell: (r) => (r.g2b || r.bk)!.date || '—' },
    { h: 'ITC', cell: (r) => amt(itc((r.g2b || r.bk)!)), num: true },
    { h: 'Next step', cell: (r) => (r.s === 'smb' ? 'Book the purchase (if yours)' : 'Ask supplier to file GSTR-1'), wrap: true },
  ];

  const exportRows = () =>
    rows.map((r) => {
      const ref = (r.g2b || r.bk)!;
      return {
        Result: r.s === 'smb' ? 'Missing in books' : r.s === 'sm2' ? 'Missing in 2B' : PASS_LABEL[r.s],
        ...rowCols(ref),
        'Invoice no. (books)': r.bk?.inv ?? '',
        'Date (books)': r.bk?.date ?? '',
        'ITC (books)': r.bk ? itc(r.bk) : '',
        Difference: r.diff,
      };
    });

  return (
    <div className="flex flex-col gap-3">
      <PageHead
        title="Smart Match Runs"
        sub="Invoices left over by the primary match (GSTIN + invoice no.) go through three more passes. An invoice matched here is no longer counted as missing anywhere."
        right={<ExportBtn onClick={() => downloadWorkbook(`Smart_match_${v}_${stamp()}`, [{ name: { p1: 'Pass 1 core', p2: 'Pass 2 amount+date', p3: 'Pass 3 tax values', unr: 'Unresolved' }[v], rows: exportRows() }])} />}
      />
      <Pills
        value={v}
        onChange={setV}
        options={[
          { id: 'p1', label: 'Pass 1: invoice core', count: groups.p1.length },
          { id: 'p2', label: 'Pass 2: amount + date', count: groups.p2.length },
          { id: 'p3', label: 'Pass 3: tax values', count: groups.p3.length },
          { id: 'unr', label: 'Unresolved', count: groups.unr.length },
        ]}
      />
      <Notice tone={v === 'p3' ? 'warn' : 'info'}>{HELP[v]}</Notice>
      <Card pad={false}>
        <DataTable cols={v === 'unr' ? unrCols : matchCols} rows={rows} empty={v === 'unr' ? 'Everything was matched.' : 'No matches in this pass.'} />
      </Card>
    </div>
  );
}
