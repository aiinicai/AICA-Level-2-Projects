import { useMemo, useState } from 'react';
import { UserCog } from 'lucide-react';
import { useApp } from '../ctx';
import type { Row } from '../types';
import { crossPartyDuplicates, gstinRegister, itc, msmeLabel, nonFilers, timeBarred } from '../lib/engine';
import { amt, money, short } from '../lib/format';
import { downloadWorkbook, stamp } from '../lib/excel';
import { rowCols } from '../lib/exports';
import { Badge, Btn, Card, DataTable, Empty, ExportBtn, Grid, Notice, PageHead, Pills, Stat, type Col } from '../components/ui';

type View = 'gstin' | 'msme' | 'dup' | 'sec164' | 'nonfiler';

export default function HealthTab() {
  const { ds, suppliers, openSupplier, goto } = useApp();
  const [v, setV] = useState<View>('gstin');
  const gst = useMemo(() => gstinRegister(ds.g2b, ds.bks), [ds]);
  const bad = gst.filter((g) => !g.valid);
  const dups = useMemo(() => crossPartyDuplicates(ds.g2b, ds.bks), [ds]);
  const tb = useMemo(() => timeBarred(ds.g2b), [ds]);
  const nf = useMemo(() => nonFilers(ds.g2b, ds.bks), [ds]);
  const unchecked = gst.filter((g) => !suppliers[g.gstin] || suppliers[g.gstin].msmeStatus === 'unverified');
  const mse = gst.filter((g) => ['micro', 'small'].includes(suppliers[g.gstin]?.msmeStatus ?? ''));

  if (!ds.g2b.length && !ds.bks.length)
    return (
      <>
        <PageHead title="ITC Health Check" />
        <Card>
          <Empty title="No data yet">
            <button className="underline text-teal-700" onClick={() => goto('imp')}>
              Import the GSTR-2B or purchase register
            </button>{' '}
            to run the checks.
          </Empty>
        </Card>
      </>
    );

  type G = (typeof gst)[number];
  const gstCols: Col<G>[] = [
    { h: 'GSTIN', cell: (g) => <span className={g.valid ? 'font-mono' : 'font-mono text-red-700 font-bold'}>{g.gstin}</span> },
    { h: 'Supplier', cell: (g) => g.name || '—', wrap: true },
    { h: 'Found in', cell: (g) => g.src.join(', ') },
    { h: 'State', cell: (g) => `${g.state} (${g.gstin.slice(0, 2)})` },
    { h: 'Check', cell: (g) => (g.valid ? <Badge tone="green">Valid</Badge> : <Badge tone="red" title={g.error}>{g.error}</Badge>) },
    { h: 'MSME', cell: (g) => <Badge tone={suppliers[g.gstin] && suppliers[g.gstin].msmeStatus !== 'unverified' ? 'sky' : 'slate'}>{msmeLabel(suppliers[g.gstin])}</Badge> },
    {
      h: '',
      cell: (g) => (
        <Btn small icon={<UserCog className="w-3 h-3" />} onClick={() => openSupplier(g.gstin, g.name)}>
          Edit
        </Btn>
      ),
    },
  ];

  type D = (typeof dups)[number];
  const dupCols: Col<D>[] = [
    { h: 'Register', cell: (d) => <Badge tone={d.source === 'GSTR-2B' ? 'teal' : 'sky'}>{d.source}</Badge> },
    { h: 'Invoice no.', cell: (d) => <span className="font-mono font-bold text-amber-800">{d.inv}</span> },
    { h: 'Times', cell: (d) => d.rows.length, num: true },
    { h: 'GSTINs', cell: (d) => <span className="font-mono text-[0.68rem]">{d.rows.map((r) => r.gstin).join(', ')}</span>, wrap: true },
    { h: 'Suppliers', cell: (d) => d.rows.map((r) => r.name).join(', '), wrap: true },
    { h: 'Combined ITC', cell: (d) => amt(d.rows.reduce((a, r) => a + itc(r), 0)), num: true },
  ];

  const tbCols: Col<Row & { fy: string; deadline: string; daysOver: number }>[] = [
    { h: 'GSTIN', cell: (r) => <span className="font-mono">{r.gstin}</span> },
    { h: 'Supplier', cell: (r) => r.name || '—', wrap: true },
    { h: 'Invoice no.', cell: (r) => <span className="font-mono">{r.inv}</span> },
    { h: 'Date', cell: (r) => r.date },
    { h: 'FY', cell: (r) => r.fy },
    { h: 'Last date', cell: (r) => r.deadline },
    { h: 'Days past', cell: (r) => <span className="text-red-600 font-semibold">{r.daysOver}</span>, num: true },
    { h: 'ITC', cell: (r) => amt(itc(r)), num: true },
  ];

  const exportNow = () => {
    const sheet =
      v === 'gstin' || v === 'msme'
        ? {
            name: v === 'gstin' ? 'GSTIN check' : 'MSME',
            rows: (v === 'gstin' ? gst : gst).map((g) => ({
              GSTIN: g.gstin,
              'Supplier name': g.name,
              'Found in': g.src.join(', '),
              State: g.state,
              Valid: g.valid ? 'Yes' : 'No',
              Problem: g.error,
              MSME: msmeLabel(suppliers[g.gstin]),
              'Udyam no.': suppliers[g.gstin]?.udyamNumber ?? '',
              'E-mail': suppliers[g.gstin]?.email ?? '',
            })),
          }
        : v === 'dup'
          ? { name: 'Duplicates', rows: dups.flatMap((d) => d.rows.map((r) => ({ Register: d.source, 'Repeated invoice no.': d.inv, ...rowCols(r) }))) }
          : v === 'sec164'
            ? { name: 'Sec 16(4)', rows: tb.map((r) => ({ ...rowCols(r), FY: r.fy, 'Last date': r.deadline, 'Days past': r.daysOver })) }
            : { name: 'Non-filers', rows: nf.map((r) => ({ GSTIN: r.gstin, 'Supplier name': r.name, Invoices: r.invCount, 'ITC at risk': r.itc })) };
    downloadWorkbook(`Health_check_${v}_${stamp()}`, [sheet]);
  };

  return (
    <div className="flex flex-col gap-3">
      <PageHead title="ITC Health Check" sub="Checks that do not need the other file: GSTIN validity, MSME status, duplicate invoice numbers, the Section 16(4) time limit and non-filers." right={<ExportBtn onClick={exportNow} />} />
      <Grid cols={5}>
        <Stat label="GSTIN problems" value={bad.length} sub={`of ${gst.length} GSTINs`} tone={bad.length ? 'red' : 'green'} onClick={() => setV('gstin')} active={v === 'gstin'} />
        <Stat label="MSME not checked" value={unchecked.length} sub={`${mse.length} micro / small`} tone="amber" onClick={() => setV('msme')} active={v === 'msme'} />
        <Stat label="Duplicate inv. nos." value={dups.length} sub="across GSTINs" tone={dups.length ? 'amber' : 'green'} onClick={() => setV('dup')} active={v === 'dup'} />
        <Stat label="Sec 16(4) time-barred" value={tb.length} sub={short(tb.reduce((a, r) => a + itc(r), 0))} tone={tb.length ? 'red' : 'green'} onClick={() => setV('sec164')} active={v === 'sec164'} />
        <Stat label="Non-filers" value={nf.length} sub={short(nf.reduce((a, r) => a + r.itc, 0))} tone={nf.length ? 'red' : 'green'} onClick={() => setV('nonfiler')} active={v === 'nonfiler'} />
      </Grid>
      <Pills
        value={v}
        onChange={setV}
        options={[
          { id: 'gstin', label: 'GSTIN check', count: bad.length },
          { id: 'msme', label: 'MSME', count: unchecked.length },
          { id: 'dup', label: 'Duplicates', count: dups.length },
          { id: 'sec164', label: 'Sec 16(4)', count: tb.length },
          { id: 'nonfiler', label: 'Non-filers', count: nf.length },
        ]}
      />

      {v === 'gstin' && (
        <>
          <Notice>Each GSTIN is checked for format, state code and the mod-36 check digit. A failed check usually means a typing mistake in the books — it does not tell you whether the registration is active.</Notice>
          <Card pad={false}>
            <DataTable cols={gstCols} rows={[...bad, ...gst.filter((g) => g.valid)]} />
          </Card>
        </>
      )}
      {v === 'msme' && (
        <>
          <Notice>
            Record each supplier's MSME classification and Udyam number after checking their Udyam certificate. Payments to <b>micro and small</b> enterprises must be made within 15 days (45 days with
            a written agreement) to be allowed as an expense under Section 43B(h) of the Income-tax Act. The app does not look this up itself.
          </Notice>
          <Card pad={false}>
            <DataTable cols={gstCols} rows={[...unchecked, ...gst.filter((g) => !unchecked.includes(g))]} />
          </Card>
        </>
      )}
      {v === 'dup' && (
        <>
          <Notice tone="warn">The same invoice no. booked against different GSTINs can mean a bill posted to the wrong supplier. (Repeated lines for the same GSTIN + invoice are added together at import.)</Notice>
          <Card pad={false}>
            <DataTable cols={dupCols} rows={dups} empty="No invoice number appears under more than one GSTIN." />
          </Card>
        </>
      )}
      {v === 'sec164' && (
        <>
          <Notice tone="warn">
            Section 16(4): ITC on an invoice can be claimed only up to <b>30 November</b> after the end of its financial year (or the annual return date, if earlier). If credit on these invoices has not
            been claimed yet, the time limit has passed. Total: <b>{money(tb.reduce((a, r) => a + itc(r), 0))}</b>.
          </Notice>
          <Card pad={false}>
            <DataTable cols={tbCols} rows={tb} empty="No GSTR-2B invoice is past its Section 16(4) date." />
          </Card>
        </>
      )}
      {v === 'nonfiler' && (
        <Card pad={false}>
          <DataTable
            cols={[
              { h: 'GSTIN', cell: (r) => <span className="font-mono">{r.gstin}</span> },
              { h: 'Supplier', cell: (r) => r.name || '—', wrap: true },
              { h: 'Invoices in books', cell: (r) => r.invCount, num: true },
              { h: 'ITC at risk', cell: (r) => <b className="text-red-600">{money(r.itc)}</b>, num: true },
            ]}
            rows={nf}
            empty="Every supplier in your books has filed at least one invoice in GSTR-2B."
          />
        </Card>
      )}
    </div>
  );
}
