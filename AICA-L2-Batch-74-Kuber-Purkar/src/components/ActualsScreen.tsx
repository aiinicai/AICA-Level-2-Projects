import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { CheckCircle2, AlertTriangle } from 'lucide-react';
import type { ClientRecord } from '../lib/store';
import type { CustomHead, YearActual } from '../types/cma';
import { NumInput } from './NumInput';
import { ImportDialog } from './ImportDialog';
import { fmt } from '../lib/format';

interface Props {
  client: ClientRecord;
  onChange: (c: ClientRecord) => void;
}

type HeadDef = { key: keyof YearActual; label: string; indent?: boolean };

const SECTIONS: { title: string; heads: HeadDef[] }[] = [
  {
    title: 'Income',
    heads: [
      { key: 'salesDomestic', label: 'Sales — Domestic' },
      { key: 'salesExport', label: 'Sales — Export' },
      { key: 'otherIncome', label: 'Other Income' },
    ],
  },
  {
    title: 'Cost of Sales',
    heads: [
      { key: 'rmOpening', label: 'Opening Stock (RM/FG/WIP)' },
      { key: 'rmPurchases', label: 'Purchases / Raw Material' },
      { key: 'rmClosing', label: 'Closing Stock (RM/FG/WIP)' },
      { key: 'powerFuel', label: 'Power & Fuel' },
      { key: 'directLabour', label: 'Direct Labour & Wages' },
    ],
  },
  {
    title: 'Expenses',
    heads: [
      { key: 'salary', label: 'Salary & Employee Benefits' },
      { key: 'freight', label: 'Freight & Cartage' },
      { key: 'salesPromo', label: 'Sales Promotion & Distribution' },
      { key: 'travelAdmin', label: 'Travelling & Conveyance' },
      { key: 'repairs', label: 'Repairs & Maintenance' },
      { key: 'professionalFees', label: 'Professional Fees' },
      { key: 'operatingExp', label: 'Operating Expenses (General)' },
      { key: 'otherExp', label: 'Other Expenses' },
      { key: 'customExp1', label: '— Custom Expense 1 —' },
      { key: 'customExp2', label: '— Custom Expense 2 —' },
    ],
  },
  {
    title: 'Financials',
    heads: [
      { key: 'depreciation', label: 'Depreciation (0 = use schedule)' },
      { key: 'interestCC', label: 'Interest — Cash Credit' },
      { key: 'interestTL', label: 'Interest — Term Loan' },
      { key: 'bankCharges', label: 'Bank Charges' },
      { key: 'tax', label: 'Provision for Tax' },
      { key: 'dividend', label: 'Dividend Paid' },
    ],
  },
  {
    title: 'Balance Sheet — Assets',
    heads: [
      { key: 'fixedAssets', label: 'Fixed Assets (Net Block)' },
      { key: 'deposits', label: 'Deposits & Advances' },
      { key: 'investments', label: 'Investments' },
      { key: 'debtors', label: 'Debtors / Receivables' },
      { key: 'cash', label: 'Cash & Bank Balance' },
      { key: 'otherCurrentAssets', label: 'Other Current Assets' },
    ],
  },
  {
    title: 'Balance Sheet — Liabilities',
    heads: [
      { key: 'shareCapital', label: 'Share Capital' },
      { key: 'reserves', label: 'Reserves & Surplus' },
      { key: 'termLoan', label: 'Term Loan (closing, incl. CPLTD)' },
      { key: 'cc', label: 'Cash Credit / Bank WC Borrowing' },
      { key: 'unsecured', label: 'Unsecured Loans' },
      { key: 'creditors', label: 'Creditors / Payables' },
      { key: 'otherCurrentLiab', label: 'Other Current Liabilities' },
    ],
  },
];

function totals(a: YearActual, customHeads: CustomHead[]) {
  const cv = a.customValues || {};
  const custA = customHeads.filter(h => h.kind === 'asset').reduce((s, h) => s + (cv[h.id] || 0), 0);
  const custL = customHeads.filter(h => h.kind === 'liability').reduce((s, h) => s + (cv[h.id] || 0), 0);
  const assets = a.fixedAssets + a.rmClosing + a.debtors + a.cash + a.deposits + a.investments + a.otherCurrentAssets + custA;
  const liab = a.shareCapital + a.reserves + a.termLoan + a.cc + a.unsecured + a.creditors + a.otherCurrentLiab + custL;
  return { assets, liab, diff: liab - assets };
}

export const ActualsScreen: React.FC<Props> = ({ client, onChange }) => {
  const cfg = client.config;
  const unit = cfg.unit;

  const setField = (yearIdx: number, key: keyof YearActual, value: number) => {
    const actuals = cfg.actuals.map((a, i) => (i === yearIdx ? { ...a, [key]: value } : a));
    onChange({ ...client, config: { ...cfg, actuals } });
  };

  const setCustom = (yearIdx: number, headId: string, value: number) => {
    const actuals = cfg.actuals.map((a, i) =>
      i === yearIdx ? { ...a, customValues: { ...(a.customValues || {}), [headId]: value } } : a);
    onChange({ ...client, config: { ...cfg, actuals } });
  };

  const customRows = (kind: 'expense' | 'asset' | 'liability') =>
    (cfg.customHeads || []).filter(h => h.kind === kind).map(h => (
      <TableRow key={h.id} className="bg-indigo-500/5">
        <TableCell>{h.name} <span className="text-[10px] text-indigo-400 uppercase">custom</span></TableCell>
        {cfg.actuals.map((a, i) => (
          <TableCell key={i} className="p-1">
            <NumInput
              unit={unit}
              value={a.customValues?.[h.id] || 0}
              onChange={v => setCustom(i, h.id, v)}
              className="h-8 text-right"
            />
          </TableCell>
        ))}
      </TableRow>
    ));

  const applyImport = (yearIdx: number, values: Partial<YearActual>) => {
    const actuals = cfg.actuals.map((a, i) => (i === yearIdx ? { ...a, ...values } : a));
    onChange({ ...client, config: { ...cfg, actuals } });
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Actual / Audited Data — {cfg.actuals.length} year(s)</h3>
        <ImportDialog client={client} onApply={applyImport} />
      </div>

      {/* BS tally indicators */}
      <div className="flex gap-3 flex-wrap">
        {cfg.actuals.map((a, i) => {
          const t = totals(a, cfg.customHeads || []);
          const ok = Math.abs(t.diff) < 1;
          return (
            <Alert key={i} variant={ok ? 'default' : 'destructive'} className="flex-1 min-w-[220px] py-2">
              {ok ? <CheckCircle2 className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
              <AlertDescription className="text-sm">
                <b>{a.label}</b> BS {ok ? 'tallies' : `difference: ${fmt(t.diff, unit)}`} — Assets {fmt(t.assets, unit)} vs Liabilities {fmt(t.liab, unit)}
              </AlertDescription>
            </Alert>
          );
        })}
      </div>

      <Card>
        <CardContent className="pt-4 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="min-w-[240px]">Particulars</TableHead>
                {cfg.actuals.map((a, i) => (
                  <TableHead key={i} className="min-w-[130px] text-right">{a.label}<br /><span className="text-xs font-normal">Audited</span></TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {SECTIONS.map(sec => (
                <React.Fragment key={sec.title}>
                  <TableRow className="bg-indigo-500/10">
                    <TableCell colSpan={cfg.actuals.length + 1} className="font-bold text-indigo-300">{sec.title}</TableCell>
                  </TableRow>
                  {sec.heads.map(h => (
                    <TableRow key={h.key}>
                      <TableCell className={h.indent ? 'pl-8' : ''}>{h.label}</TableCell>
                      {cfg.actuals.map((a, i) => (
                        <TableCell key={i} className="p-1">
                          <NumInput
                            unit={unit}
                            value={(a[h.key] as number) || 0}
                            onChange={v => setField(i, h.key, v)}
                            className="h-8 text-right"
                          />
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                  {sec.title === 'Expenses' && customRows('expense')}
                  {sec.title === 'Balance Sheet — Assets' && customRows('asset')}
                  {sec.title === 'Balance Sheet — Liabilities' && customRows('liability')}
                </React.Fragment>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
};
