import { useMemo, useState } from 'react';
import { RotateCcw, Undo2 } from 'lucide-react';
import { useApp } from '../ctx';
import type { BlockedCredit } from '../types';
import { amt, short } from '../lib/format';
import { downloadWorkbook, stamp } from '../lib/excel';
import { blockedRows } from '../lib/exports';
import { Badge, Btn, Card, DataTable, ExportBtn, Grid, Notice, PageHead, Pills, Stat, type Col } from '../components/ui';

const tax = (b: BlockedCredit) => b.igst + b.cgst + b.sgst;

export default function BlockedTab() {
  const { blocked, unblock, reblock } = useApp();
  const [v, setV] = useState<'active' | 'released'>('active');
  const rows = useMemo(() => blocked.filter((b) => b.active === (v === 'active')), [blocked, v]);
  const active = blocked.filter((b) => b.active);
  const auto = active.filter((b) => b.origin === 'auto').length;
  const cols: Col<BlockedCredit>[] = [
    { h: 'Section', cell: (b) => <Badge tone="red">{b.sec}</Badge> },
    { h: 'Category', cell: (b) => b.catLbl, wrap: true },
    { h: 'GSTIN', cell: (b) => <span className="font-mono">{b.gstin}</span> },
    {
      h: 'Supplier',
      cell: (b) => (
        <span>
          {b.name || '—'}
          {b.reason && <span className="block text-[0.65rem] text-slate-500">{b.reason}</span>}
        </span>
      ),
      wrap: true,
    },
    { h: 'Invoice no.', cell: (b) => <span className="font-mono">{b.inv}</span>, foot: 'Total' },
    { h: 'Date', cell: (b) => b.date || '—' },
    { h: 'Blocked ITC', cell: (b) => <b>{amt(tax(b))}</b>, num: true, foot: amt(rows.reduce((a, b) => a + tax(b), 0)) },
    { h: 'How', cell: (b) => <Badge tone={b.origin === 'auto' ? 'amber' : 'slate'}>{b.origin === 'auto' ? 'Name keywords' : 'Manual'}</Badge> },
    {
      h: '',
      cell: (b) =>
        b.active ? (
          <Btn small icon={<Undo2 className="w-3 h-3" />} onClick={() => unblock(b)}>
            Release
          </Btn>
        ) : (
          <Btn small icon={<RotateCcw className="w-3 h-3" />} onClick={() => reblock(b)}>
            Block again
          </Btn>
        ),
    },
  ];
  return (
    <div className="flex flex-col gap-3">
      <PageHead
        title="Blocked Credits — Section 17(5)"
        sub="Ineligible credit: motor vehicles, food and catering, beauty and health services, club membership, rent-a-cab and insurance, travel benefits, works contracts and construction, personal use. Reported as a reversal in GSTR-3B Table 4(B)(1)."
        right={<ExportBtn onClick={() => downloadWorkbook(`Blocked_17_5_${stamp()}`, [{ name: 'Blocked 17(5)', rows: blockedRows(blocked) }])} />}
      />
      <Grid cols={3}>
        <Stat label="Blocked invoices" value={active.length} tone="red" />
        <Stat label="Blocked ITC" value={short(active.reduce((a, b) => a + tax(b), 0))} tone="red" />
        <Stat label="From name keywords" value={auto} sub="check these" tone="amber" />
      </Grid>
      {auto > 0 && v === 'active' && (
        <Notice tone="warn">
          {auto} invoice{auto === 1 ? ' was' : 's were'} blocked because the supplier's name suggests a Section 17(5) item. Release any that are actually eligible (for example, a car dealer selling you spare
          parts for resale).
        </Notice>
      )}
      <Pills
        value={v}
        onChange={setV}
        options={[
          { id: 'active', label: 'Blocked', count: active.length },
          { id: 'released', label: 'Released', count: blocked.length - active.length },
        ]}
      />
      <Card pad={false}>
        <DataTable cols={cols} rows={rows} empty={v === 'active' ? 'No blocked credits. Use Block in the Reconciliation Ledger to add one.' : 'Nothing released.'} />
      </Card>
    </div>
  );
}
