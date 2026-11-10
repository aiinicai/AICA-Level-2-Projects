import { useMemo, useState } from 'react';
import { useApp } from '../ctx';
import { nonFilers, summarise, type SummaryRow } from '../lib/engine';
import { amt, money, pct, short, signed } from '../lib/format';
import { downloadWorkbook, stamp } from '../lib/excel';
import { summaryRows } from '../lib/exports';
import { Badge, Card, DataTable, ExportBtn, Grid, Notice, PageHead, Pills, SearchBox, Stat, type Col } from '../components/ui';

type View = 'gstin' | 'month' | 'nonfiler';

export default function ReportsTab() {
  const { recon, ds, openSupplier } = useApp();
  const [v, setV] = useState<View>('gstin');
  const [q, setQ] = useState('');
  const by = v === 'month' ? 'month' : 'gstin';
  const all = useMemo(() => summarise(recon.lines, by), [recon.lines, by]);
  const rows = useMemo(() => {
    const s = q.trim().toLowerCase();
    return s ? all.filter((r) => r.label.toLowerCase().includes(s) || r.name.toLowerCase().includes(s)) : all;
  }, [all, q]);
  const nf = useMemo(() => nonFilers(ds.g2b, ds.bks), [ds]);
  const tot = rows.reduce(
    (a, r) => ({ g: a.g + r.g2bInv, b: a.b + r.bksInv, m: a.m + r.matched, s: a.s + r.smart, mm: a.mm + r.mismatch, mb: a.mb + r.missBooks, m2: a.m2 + r.miss2b, i2: a.i2 + r.itc2b, ib: a.ib + r.itcBooks }),
    { g: 0, b: 0, m: 0, s: 0, mm: 0, mb: 0, m2: 0, i2: 0, ib: 0 }
  );
  const rate = (r: SummaryRow) => pct(r.matched + r.smart, Math.max(r.g2bInv, r.bksInv));

  const cols: Col<SummaryRow>[] = [
    { h: by === 'gstin' ? 'GSTIN' : 'Month', cell: (r) => <span className={by === 'gstin' ? 'font-mono' : 'font-semibold'}>{r.label}</span>, foot: 'Total' },
    ...(by === 'gstin' ? [{ h: 'Supplier', cell: (r: SummaryRow) => r.name || '—', wrap: true }] : []),
    { h: '2B inv.', cell: (r) => r.g2bInv || '—', num: true, foot: tot.g },
    { h: 'Books inv.', cell: (r) => r.bksInv || '—', num: true, foot: tot.b },
    { h: 'Matched', cell: (r) => r.matched || '—', num: true, foot: tot.m },
    { h: 'Smart', cell: (r) => r.smart || '—', num: true, foot: tot.s },
    { h: 'Mismatch', cell: (r) => r.mismatch || '—', num: true, foot: tot.mm },
    { h: 'Miss books', cell: (r) => r.missBooks || '—', num: true, foot: tot.mb },
    { h: 'Miss 2B', cell: (r) => r.miss2b || '—', num: true, foot: tot.m2 },
    {
      h: 'Match %',
      cell: (r) => {
        const p = rate(r);
        return <Badge tone={p >= 95 ? 'green' : p >= 75 ? 'amber' : 'red'}>{p}%</Badge>;
      },
    },
    { h: 'ITC (2B)', cell: (r) => amt(r.itc2b), num: true, foot: amt(tot.i2) },
    { h: 'ITC (books)', cell: (r) => amt(r.itcBooks), num: true, foot: amt(tot.ib) },
    { h: 'Difference', cell: (r) => signed(r.itcBooks - r.itc2b), num: true, foot: signed(tot.ib - tot.i2) },
  ];

  const nfCols: Col<(typeof nf)[number]>[] = [
    { h: '#', cell: (_r, i) => i + 1 },
    { h: 'GSTIN', cell: (r) => <span className="font-mono">{r.gstin}</span> },
    { h: 'Supplier', cell: (r) => r.name || '—', wrap: true },
    { h: 'Invoices in books', cell: (r) => r.invCount, num: true },
    { h: 'ITC at risk', cell: (r) => <b className="text-red-600">{money(r.itc)}</b>, num: true },
    {
      h: 'Next step',
      cell: (r) => (
        <button className="text-teal-700 underline text-[0.7rem]" onClick={() => openSupplier(r.gstin, r.name)}>
          Check filing status on the GST portal, hold payment, save e-mail
        </button>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-3">
      <PageHead
        title="Filing Reports"
        sub="Supplier-wise and month-wise summaries (months from the invoice date, read as dd/mm/yyyy), and suppliers in your books who have not filed any invoice in GSTR-2B."
        right={
          <ExportBtn
            onClick={() =>
              downloadWorkbook(
                `Report_${v}_${stamp()}`,
                v === 'nonfiler'
                  ? [{ name: 'Non-filers', rows: nf.map((r) => ({ GSTIN: r.gstin, 'Supplier name': r.name, 'Invoices in books': r.invCount, 'ITC at risk': r.itc })) }]
                  : [{ name: by === 'gstin' ? 'By GSTIN' : 'By month', rows: summaryRows(rows, by) }]
              )
            }
          />
        }
      />
      <div className="flex flex-col sm:flex-row gap-2 sm:items-center justify-between">
        <Pills
          value={v}
          onChange={(x) => {
            setV(x);
            setQ('');
          }}
          options={[
            { id: 'gstin', label: 'By GSTIN' },
            { id: 'month', label: 'By month' },
            { id: 'nonfiler', label: 'Non-filer risk', count: nf.length },
          ]}
        />
        {v !== 'nonfiler' && <SearchBox value={q} onChange={setQ} placeholder={by === 'gstin' ? 'Search GSTIN or supplier' : 'Search month, e.g. Oct-2026'} />}
      </div>
      {v === 'nonfiler' ? (
        <>
          <Grid cols={3}>
            <Stat label="Suppliers at risk" value={nf.length} tone="red" />
            <Stat label="Invoices at risk" value={nf.reduce((a, r) => a + r.invCount, 0)} tone="orange" />
            <Stat label="ITC at risk" value={short(nf.reduce((a, r) => a + r.itc, 0))} tone="red" />
          </Grid>
          <Notice tone="warn">
            These suppliers appear in your purchase books but have <b>no invoice at all</b> in GSTR-2B. ITC on their invoices cannot be claimed until they file (Section 16(2)(aa)). If
            credit has been taken and the supplier has not paid the tax to the government, it must be reversed (Section 16(2)(c), Rule 37A).
          </Notice>
          <Card pad={false}>
            <DataTable cols={nfCols} rows={nf} empty="Every supplier in your books has filed at least one invoice in GSTR-2B." />
          </Card>
        </>
      ) : (
        <Card pad={false}>
          <DataTable cols={cols} rows={rows} empty="No data yet." />
        </Card>
      )}
    </div>
  );
}
