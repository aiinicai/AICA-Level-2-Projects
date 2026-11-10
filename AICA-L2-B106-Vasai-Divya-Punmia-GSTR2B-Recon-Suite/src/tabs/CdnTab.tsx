import { useMemo, useState } from 'react';
import { useApp } from '../ctx';
import type { Row } from '../types';
import { cdnRecon, itc } from '../lib/engine';
import { amt, short, signed } from '../lib/format';
import { downloadWorkbook, stamp } from '../lib/excel';
import { rowCols } from '../lib/exports';
import { Badge, Card, DataTable, ExportBtn, Grid, Notice, PageHead, Pills, Stat, type Col } from '../components/ui';

type CdnLine = ReturnType<typeof cdnRecon>[number];
const S = { ok: ['green', 'Matched'], am: ['orange', 'Tax mismatch'], mb: ['red', 'Missing in books'], m2: ['red', 'Missing in 2B'] } as const;

export default function CdnTab() {
  const { ds, eng } = useApp();
  const [v, setV] = useState<'recon' | 'list'>('recon');
  const lines = useMemo(() => cdnRecon(ds, eng.tolerance), [ds, eng.tolerance]);
  const all = useMemo(
    () => [
      ...ds.g2b_cdn.map((r) => ({ ...r, src: 'GSTR-2B file' })),
      ...ds.cdn_g2b.map((r) => ({ ...r, src: 'GSTR-2B notes file' })),
      ...ds.bks_cdn.map((r) => ({ ...r, src: 'Books file' })),
      ...ds.cdn_bks.map((r) => ({ ...r, src: 'Books notes file' })),
    ],
    [ds]
  );
  const n = (s: CdnLine['s']) => lines.filter((l) => l.s === s).length;

  const reconCols: Col<CdnLine>[] = [
    { h: 'Status', cell: (l) => <Badge tone={S[l.s][0]}>{S[l.s][1]}</Badge> },
    { h: 'GSTIN', cell: (l) => <span className="font-mono">{(l.g2b || l.bk)!.gstin}</span> },
    { h: 'Supplier', cell: (l) => (l.g2b || l.bk)!.name || '—', wrap: true },
    { h: 'Note no.', cell: (l) => <span className="font-mono">{(l.g2b || l.bk)!.inv}</span> },
    { h: 'Date', cell: (l) => (l.g2b || l.bk)!.date || '—' },
    { h: 'ITC (2B)', cell: (l) => (l.g2b ? amt(itc(l.g2b)) : '—'), num: true },
    { h: 'ITC (books)', cell: (l) => (l.bk ? amt(itc(l.bk)) : '—'), num: true },
    { h: 'Difference', cell: (l) => (l.g2b && l.bk ? signed(l.diff) : '—'), num: true },
  ];
  const listCols: Col<Row & { src: string }>[] = [
    { h: 'Source', cell: (r) => <Badge tone={r.src.startsWith('GSTR') ? 'teal' : 'sky'}>{r.src}</Badge> },
    { h: 'GSTIN', cell: (r) => <span className="font-mono">{r.gstin}</span> },
    { h: 'Supplier', cell: (r) => r.name || '—', wrap: true },
    { h: 'Note no.', cell: (r) => <span className="font-mono">{r.inv}</span> },
    { h: 'Sheet', cell: (r) => r.sheet },
    { h: 'Date', cell: (r) => r.date || '—' },
    { h: 'Taxable', cell: (r) => amt(r.taxable), num: true },
    { h: 'IGST', cell: (r) => amt(r.igst), num: true },
    { h: 'CGST', cell: (r) => amt(r.cgst), num: true },
    { h: 'SGST', cell: (r) => amt(r.sgst), num: true },
    { h: 'ITC', cell: (r) => <b>{amt(itc(r))}</b>, num: true },
  ];

  return (
    <div className="flex flex-col gap-3">
      <PageHead
        title="CDN Registry"
        sub="Credit and debit notes are kept out of invoice matching and reconciled separately. They are picked up from CDNR sheets, rows with negative tax, or the separate notes files."
        right={
          <ExportBtn
            onClick={() =>
              downloadWorkbook(`CDN_${v}_${stamp()}`, [
                v === 'recon'
                  ? {
                      name: 'CDN reconciliation',
                      rows: lines.map((l) => ({ Status: S[l.s][1], ...rowCols((l.g2b || l.bk)!), 'ITC (2B)': l.g2b ? itc(l.g2b) : '', 'ITC (books)': l.bk ? itc(l.bk) : '', Difference: l.diff })),
                    }
                  : { name: 'All notes', rows: all.map((r) => ({ Source: r.src, ...rowCols(r), Sheet: r.sheet })) },
              ])
            }
          />
        }
      />
      <Grid>
        <Stat label="Matched" value={n('ok')} sub={`within ₹${eng.tolerance}`} tone="green" />
        <Stat label="Tax mismatch" value={n('am')} tone="orange" />
        <Stat label="Missing in books" value={n('mb')} sub="only in GSTR-2B" tone="red" />
        <Stat label="Missing in 2B" value={n('m2')} sub={`net ${short(all.reduce((a, r) => a + itc(r), 0))}`} tone="red" />
      </Grid>
      <Pills
        value={v}
        onChange={setV}
        options={[
          { id: 'recon', label: 'Note reconciliation', count: lines.length },
          { id: 'list', label: 'All notes', count: all.length },
        ]}
      />
      {all.length === 0 && <Notice>No credit or debit notes loaded. GSTR-2B files with a CDNR sheet are picked up automatically when "Import all sheets" is ticked.</Notice>}
      <Card pad={false}>{v === 'recon' ? <DataTable cols={reconCols} rows={lines} empty="No notes to reconcile." /> : <DataTable cols={listCols} rows={all} empty="No notes loaded." />}</Card>
    </div>
  );
}
