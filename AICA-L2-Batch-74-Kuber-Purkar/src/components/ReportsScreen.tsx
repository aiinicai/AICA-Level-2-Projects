import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Info } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer } from 'recharts';
import type { ClientRecord } from '../lib/store';
import type { CmaResult, RatioWorking, UnitMode, YearReport } from '../types/cma';
import { fmt, fmtRatio } from '../lib/format';

interface Props {
  client: ClientRecord;
  result: CmaResult;
}

type Row = { label: string; get: (y: YearReport) => number | null; bold?: boolean; section?: boolean; ratio?: boolean };

function YearTable({ years, rows, unit }: { years: YearReport[]; rows: Row[]; unit: UnitMode }) {
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow className="border-slate-700 bg-slate-800/60">
            <TableHead className="min-w-[240px] text-slate-300 font-bold">Particulars</TableHead>
            {years.map(y => (
              <TableHead key={y.yearIndex} className="text-right min-w-[110px] text-slate-300 font-bold">
                {y.year}<br /><span className="text-[10px] font-normal text-slate-500 uppercase tracking-wider">{y.type}</span>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((r, i) => r.section ? (
            <TableRow key={i} className="bg-indigo-500/10 border-slate-800">
              <TableCell colSpan={years.length + 1} className="font-bold text-indigo-300 text-[11px] uppercase tracking-widest">{r.label}</TableCell>
            </TableRow>
          ) : (
            <TableRow key={i} className={`border-slate-800/60 ${r.bold ? 'bg-slate-800/70 font-semibold border-t-2 border-t-slate-600' : ''}`}>
              <TableCell className="text-slate-200">{r.label}</TableCell>
              {years.map(y => {
                const v = r.get(y);
                return (
                  <TableCell key={y.yearIndex} className="text-right font-mono text-sm text-slate-100">
                    {r.ratio ? fmtRatio(v) : fmt(v, unit)}
                  </TableCell>
                );
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

const RATIO_DEFS: { key: string; name: string; target?: number; direction?: 'min' | 'max'; get: (y: YearReport) => number; pct?: boolean }[] = [
  { key: 'currentRatio', name: 'Current Ratio', target: 1.23, direction: 'min', get: y => y.currentRatio },
  { key: 'dscr', name: 'DSCR', target: 1.75, direction: 'min', get: y => y.dscr },
  { key: 'debtEquity', name: 'Debt / Equity', target: 3.0, direction: 'max', get: y => y.debtEquity },
  { key: 'tolTnw', name: 'TOL / TNW', target: 4.5, direction: 'max', get: y => y.tolTnw },
  { key: 'interestCoverage', name: 'Interest Coverage', target: 2.6, direction: 'min', get: y => y.interestCoverage },
  { key: 'netProfitRatio', name: 'Net Profit Ratio %', get: y => y.netProfitRatio, pct: true },
  { key: 'returnOnInvestment', name: 'Return on Investment %', get: y => y.returnOnInvestment, pct: true },
  { key: 'breakEvenPct', name: 'Break-Even % of Sales', get: y => y.breakEvenPct, pct: true },
  { key: 'debtorDaysActual', name: 'Debtor Days', get: y => y.debtorDaysActual },
  { key: 'inventoryDaysActual', name: 'Inventory Days', get: y => y.inventoryDaysActual },
  { key: 'creditorDaysActual', name: 'Creditor Days', get: y => y.creditorDaysActual },
];

function WorkingDialog({ name, working, unit }: { name: string; working?: RatioWorking; unit: UnitMode }) {
  if (!working) return null;
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" className="h-6 w-6"><Info className="h-4 w-4 text-indigo-400" /></Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader><DialogTitle>{name} — Working</DialogTitle></DialogHeader>
        <div className="space-y-3 text-sm">
          <div className="bg-slate-800 p-3 rounded font-mono text-xs">{working.formula}</div>
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-emerald-500/10 rounded space-y-1">
              <p className="font-semibold text-emerald-300">Numerator</p>
              {working.numerator.map((l, i) => (
                <div key={i} className="flex justify-between"><span>{l.label}</span><span className="font-mono">{fmt(l.value, unit)}</span></div>
              ))}
              <div className="flex justify-between font-bold border-t border-emerald-500/40 pt-1"><span>Total</span><span className="font-mono">{fmt(working.numeratorTotal, unit)}</span></div>
            </div>
            <div className="p-3 bg-red-500/10 rounded space-y-1">
              <p className="font-semibold text-red-300">Denominator</p>
              {working.denominator.map((l, i) => (
                <div key={i} className="flex justify-between"><span>{l.label}</span><span className="font-mono">{fmt(l.value, unit)}</span></div>
              ))}
              <div className="flex justify-between font-bold border-t border-red-500/40 pt-1"><span>Total</span><span className="font-mono">{fmt(working.denominatorTotal, unit)}</span></div>
            </div>
          </div>
          <div className="text-center text-xl font-bold">= {fmtRatio(working.result)}</div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function RatioChart({ def, years }: { def: typeof RATIO_DEFS[number]; years: YearReport[] }) {
  const data = years.map(y => ({ year: y.year, value: +def.get(y).toFixed(3) }));
  return (
    <div className="h-44 w-full">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="year" fontSize={11} />
          <YAxis fontSize={11} domain={['auto', 'auto']} />
          <Tooltip formatter={(v: any) => def.pct ? `${v}%` : v} />
          {def.target !== undefined && <ReferenceLine y={def.target} stroke="#dc2626" strokeDasharray="4 4" label={{ value: `norm ${def.target}`, fontSize: 10, fill: '#dc2626' }} />}
          <Line type="monotone" dataKey="value" stroke="#1d4ed8" strokeWidth={2} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export const ReportsScreen: React.FC<Props> = ({ client, result }) => {
  const unit = client.config.unit;
  const { years, emiSchedule, depSchedule } = result;

  const opRows: Row[] = [
    { label: 'INCOME', section: true, get: () => null },
    { label: 'Gross Sales', get: y => y.sales, bold: true },
    { label: '  — Domestic', get: y => y.salesDomestic },
    { label: '  — Export', get: y => y.salesExport },
    { label: '% rise / (fall) in sales', get: y => y.salesGrowthPct, ratio: true },
    { label: 'Other Income', get: y => y.otherIncome },
    { label: 'COST OF SALES', section: true, get: () => null },
    { label: 'Opening Stock', get: y => y.rmOpening },
    { label: 'Add: Purchases', get: y => y.rmPurchases },
    { label: 'Less: Closing Stock', get: y => -y.rmClosing },
    { label: 'Raw Material Consumed', get: y => y.rmConsumed, bold: true },
    { label: 'Power & Fuel', get: y => y.powerFuel },
    { label: 'Direct Labour & Wages', get: y => y.directLabour },
    { label: 'EXPENSES', section: true, get: () => null },
    { label: 'Salary & Employee Benefits', get: y => y.salary },
    { label: 'Freight & Cartage', get: y => y.freight },
    { label: 'Sales Promotion & Distribution', get: y => y.salesPromo },
    { label: 'Travelling & Conveyance', get: y => y.travelAdmin },
    { label: 'Repairs & Maintenance', get: y => y.repairs },
    { label: 'Professional Fees', get: y => y.professionalFees },
    { label: 'Operating Expenses (General)', get: y => y.operatingExp },
    { label: 'Other Expenses', get: y => y.otherExp },
    { label: client.config.actuals[0]?.customExp1Name || 'Other Expense 1', get: y => y.customExp1 },
    { label: client.config.actuals[0]?.customExp2Name || 'Other Expense 2', get: y => y.customExp2 },
    ...(client.config.customHeads || []).filter(h => h.kind === 'expense').map(h => ({
      label: h.name, get: (y: YearReport) => y.customHeadValues?.[h.id] || 0,
    })),
    { label: 'Total Expenses', get: y => y.totalExpenses, bold: true },
    { label: 'PROFITABILITY', section: true, get: () => null },
    { label: 'PBDIT / EBITDA', get: y => y.ebitda, bold: true },
    { label: 'Depreciation', get: y => y.depreciation },
    { label: 'Interest — Cash Credit', get: y => y.interestCC },
    { label: 'Interest — Term Loan', get: y => y.interestTL },
    { label: 'Bank Charges', get: y => y.bankCharges },
    { label: 'Profit Before Tax', get: y => y.pbt, bold: true },
    { label: 'Provision for Tax', get: y => y.tax },
    { label: 'Profit After Tax (Net Profit)', get: y => y.pat, bold: true },
    { label: 'Dividend', get: y => y.dividend },
    { label: 'Retained Profit', get: y => y.retained },
    { label: 'Net Cash Accrual (PAT + Dep)', get: y => y.netCashAccrual, bold: true },
  ];

  const bsRows: Row[] = [
    { label: 'LIABILITIES', section: true, get: () => null },
    { label: 'Share Capital', get: y => y.shareCapital },
    { label: 'Reserves & Surplus', get: y => y.reserves },
    { label: 'Net Worth', get: y => y.netWorth, bold: true },
    { label: 'Term Loan (total outstanding)', get: y => y.termLoan },
    { label: '  of which CPLTD (due next year)', get: y => y.cpltd },
    { label: 'Cash Credit', get: y => y.cc },
    { label: 'Unsecured Loans', get: y => y.unsecured },
    { label: 'Creditors / Payables', get: y => y.creditors },
    { label: 'Other Current Liabilities', get: y => y.otherCurrentLiab },
    ...(client.config.customHeads || []).filter(h => h.kind === 'liability').map(h => ({
      label: `${h.name} (${h.current ? 'current' : 'non-current'})`, get: (y: YearReport) => y.customHeadValues?.[h.id] || 0,
    })),
    { label: 'TOTAL LIABILITIES', get: y => y.totalLiabilities, bold: true },
    { label: 'ASSETS', section: true, get: () => null },
    { label: 'Fixed Assets (Net Block)', get: y => y.fixedAssets },
    { label: 'Deposits & Advances', get: y => y.deposits },
    { label: 'Investments', get: y => y.investments },
    { label: 'Stock / Inventory', get: y => y.stock },
    { label: 'Debtors / Receivables', get: y => y.debtors },
    { label: 'Cash & Bank', get: y => y.cash },
    { label: 'Other Current Assets', get: y => y.otherCurrentAssets },
    ...(client.config.customHeads || []).filter(h => h.kind === 'asset').map(h => ({
      label: `${h.name} (${h.current ? 'current' : 'non-current'})`, get: (y: YearReport) => y.customHeadValues?.[h.id] || 0,
    })),
    { label: 'TOTAL ASSETS', get: y => y.totalAssets, bold: true },
    { label: 'Difference (must be 0)', get: y => y.bsDifference },
  ];

  return (
    <div className="space-y-5">
      {/* Professional report title block */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl shadow-xl p-6 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-600/10 rounded-full blur-3xl -mr-20 -mt-20 pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-end justify-between gap-3">
          <div>
            <p className="text-[10px] uppercase tracking-[0.2em] text-indigo-400 font-bold">Credit Monitoring Arrangement</p>
            <h2 className="text-2xl font-bold text-white font-display mt-1">{client.config.clientName}</h2>
            <p className="text-xs text-slate-400 mt-1">
              {client.config.loan.loanType !== 'tl' && <>CC Limit {fmt(client.config.loan.ccLimit, unit)} @ {client.config.loan.ccRate}% · </>}
              {client.config.loan.loanType !== 'cc' && <>Term Loan {fmt(client.config.loan.tlAmount, unit)} @ {client.config.loan.tlRate}% / {client.config.loan.tlTenureMonths}m</>}
              {' '}· {client.config.actualYears}A + 1E + {client.config.projectedYears}P years · amounts in {unit === 'rs' ? 'Rupees' : unit === 'thousands' ? "₹ '000" : '₹ Lakhs'}
            </p>
          </div>
          <p className="text-[11px] text-slate-500">Generated {new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}</p>
        </div>
      </div>

      <Tabs defaultValue="op" className="w-full">
      <TabsList className="flex flex-wrap h-auto">
        <TabsTrigger value="op">Operating Statement</TabsTrigger>
        <TabsTrigger value="bs">Balance Sheet</TabsTrigger>
        <TabsTrigger value="dep">Depreciation</TabsTrigger>
        <TabsTrigger value="loan">Loan Schedule</TabsTrigger>
        <TabsTrigger value="ratios">Ratio Analysis</TabsTrigger>
        <TabsTrigger value="mpbf">MPBF & DP</TabsTrigger>
        <TabsTrigger value="be">Break-Even</TabsTrigger>
      </TabsList>

      <TabsContent value="op"><Card><CardContent className="pt-4"><YearTable years={years} rows={opRows} unit={unit} /></CardContent></Card></TabsContent>
      <TabsContent value="bs"><Card><CardContent className="pt-4"><YearTable years={years} rows={bsRows} unit={unit} /></CardContent></Card></TabsContent>

      <TabsContent value="dep">
        <Card><CardContent className="pt-4 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Block (rate)</TableHead>
                {years.map(y => <TableHead key={y.yearIndex} className="text-right">{y.year}</TableHead>)}
              </TableRow>
            </TableHeader>
            <TableBody>
              {client.config.assetBlocks.map((b, bi) => (
                <React.Fragment key={b.id}>
                  <TableRow className="bg-slate-800/50">
                    <TableCell className="font-semibold">{b.name} ({b.rate}%)</TableCell>
                    {depSchedule.map(d => <TableCell key={d.yearIndex} />)}
                  </TableRow>
                  {(['opening', 'addition', 'depreciation', 'closing'] as const).map(f => (
                    <TableRow key={f}>
                      <TableCell className="pl-8 text-sm text-muted-foreground capitalize">{f === 'closing' ? 'Closing WDV' : f}</TableCell>
                      {depSchedule.map(d => (
                        <TableCell key={d.yearIndex} className="text-right font-mono text-sm">{fmt(d.blocks[bi]?.[f] ?? 0, unit)}</TableCell>
                      ))}
                    </TableRow>
                  ))}
                </React.Fragment>
              ))}
              <TableRow className="bg-indigo-500/20 font-bold">
                <TableCell>Total Depreciation</TableCell>
                {depSchedule.map(d => <TableCell key={d.yearIndex} className="text-right font-mono">{fmt(d.totalDep, unit)}</TableCell>)}
              </TableRow>
              <TableRow className="bg-indigo-500/20 font-bold">
                <TableCell>Total Net Block</TableCell>
                {depSchedule.map(d => <TableCell key={d.yearIndex} className="text-right font-mono">{fmt(d.totalNetBlock, unit)}</TableCell>)}
              </TableRow>
            </TableBody>
          </Table>
        </CardContent></Card>
      </TabsContent>

      <TabsContent value="loan">
        <Card><CardContent className="pt-4 max-h-[600px] overflow-y-auto">
          {emiSchedule.length === 0 ? <p className="text-muted-foreground text-sm">No term loan configured.</p> : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>#</TableHead><TableHead>Date</TableHead><TableHead>FY</TableHead>
                  <TableHead className="text-right">Opening</TableHead><TableHead className="text-right">EMI</TableHead>
                  <TableHead className="text-right">Interest</TableHead><TableHead className="text-right">Principal</TableHead>
                  <TableHead className="text-right">Closing</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {emiSchedule.map(r => (
                  <TableRow key={r.month} className={r.moratorium ? 'bg-amber-500/10' : ''}>
                    <TableCell>{r.month}</TableCell>
                    <TableCell>{r.date}</TableCell>
                    <TableCell>{years[r.fyIndex]?.year ?? `Y${r.fyIndex + 1}`}</TableCell>
                    <TableCell className="text-right font-mono text-sm">{fmt(r.opening, unit)}</TableCell>
                    <TableCell className="text-right font-mono text-sm">{fmt(r.emi, unit)}</TableCell>
                    <TableCell className="text-right font-mono text-sm">{fmt(r.interest, unit)}</TableCell>
                    <TableCell className="text-right font-mono text-sm">{fmt(r.principal, unit)}</TableCell>
                    <TableCell className="text-right font-mono text-sm">{fmt(r.closing, unit)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent></Card>
      </TabsContent>

      <TabsContent value="ratios">
        <div className="space-y-4">
          {RATIO_DEFS.map(def => (
            <Card key={def.key}>
              <CardHeader className="pb-1">
                <CardTitle className="text-base flex items-center gap-2">
                  {def.name}
                  {def.target !== undefined && (
                    <span className="text-xs font-normal text-muted-foreground">
                      (norm: {def.direction === 'min' ? '≥' : '≤'} {def.target})
                    </span>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Year</TableHead>
                        <TableHead className="text-right">Value</TableHead>
                        {result.years.some(y => y.workings[def.key]) && <TableHead className="w-10">Working</TableHead>}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {years.map(y => {
                        const v = def.get(y);
                        const bad = def.target !== undefined && v !== 0 && (def.direction === 'min' ? v < def.target : v > def.target);
                        return (
                          <TableRow key={y.yearIndex}>
                            <TableCell>{y.year} <span className="text-xs text-muted-foreground">{y.type}</span></TableCell>
                            <TableCell className={`text-right font-mono font-semibold ${bad ? 'text-red-600' : ''}`}>
                              {def.pct ? `${fmtRatio(v)}%` : def.key.includes('Days') ? `${Math.round(v)}` : fmtRatio(v)}
                            </TableCell>
                            {result.years.some(yy => yy.workings[def.key]) && (
                              <TableCell><WorkingDialog name={`${def.name} — ${y.year}`} working={y.workings[def.key]} unit={unit} /></TableCell>
                            )}
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
                <RatioChart def={def} years={years} />
              </CardContent>
            </Card>
          ))}
        </div>
      </TabsContent>

      <TabsContent value="mpbf">
        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle className="text-base">MPBF — Tandon Method (Balance Sheet Method)</CardTitle></CardHeader>
            <CardContent>
              <YearTable years={years} unit={unit} rows={[
                { label: 'Total Current Assets', get: y => y.currentAssets },
                { label: 'Other Current Liabilities (excl. bank)', get: y => y.creditors + y.otherCurrentLiab },
                { label: 'Working Capital Gap', get: y => y.mpbfGap, bold: true },
                { label: 'Less: 25% minimum margin (of CA)', get: y => -y.mpbfMinNwc },
                { label: 'Maximum Permissible Bank Finance', get: y => y.mpbf, bold: true },
                { label: 'CC Limit / Drawing', get: y => y.cc },
                { label: 'Excess / (Shortfall)', get: y => y.mpbf - y.cc, bold: true },
              ]} />
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle className="text-base">MPBF — Turnover Method (Nayak Committee)</CardTitle></CardHeader>
            <CardContent>
              <YearTable years={years} unit={unit} rows={[
                { label: 'Sales Turnover', get: y => y.sales },
                { label: '25% of Turnover (WC requirement)', get: y => 0.25 * y.sales },
                { label: 'Less: 5% margin (promoter)', get: y => -0.05 * y.sales },
                { label: 'MPBF (20% of turnover)', get: y => y.mpbfTurnover, bold: true },
                { label: 'CC Limit / Drawing', get: y => y.cc },
                { label: 'Excess / (Shortfall)', get: y => y.mpbfTurnover - y.cc, bold: true },
              ]} />
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle className="text-base">Drawing Power Statement</CardTitle></CardHeader>
            <CardContent>
              <YearTable years={years} unit={unit} rows={[
                { label: `Stock (after ${client.config.loan.ccStockMarginPct}% margin)`, get: y => y.dpStock },
                { label: `Debtors ≤ ${client.config.loan.ccDebtorCoverDays} days (after ${client.config.loan.ccDebtorMarginPct}% margin)`, get: y => y.dpDebtors },
                { label: 'Total Drawing Power', get: y => y.dpTotal, bold: true },
                { label: 'CC Limit / Drawing', get: y => y.cc },
                { label: 'DP Shortfall / (Surplus)', get: y => y.dpShortfall, bold: true },
              ]} />
            </CardContent>
          </Card>
        </div>
      </TabsContent>

      <TabsContent value="be">
        <Card>
          <CardHeader><CardTitle className="text-base">Break-Even Analysis</CardTitle></CardHeader>
          <CardContent>
            <YearTable years={years} unit={unit} rows={[
              { label: 'Sales', get: y => y.sales },
              { label: 'Variable Costs (RM + Power + Labour + Freight + Selling)', get: y => y.rmConsumed + y.powerFuel + y.directLabour + y.freight + y.salesPromo },
              { label: 'Contribution', get: y => y.sales + y.otherIncome - (y.rmConsumed + y.powerFuel + y.directLabour + y.freight + y.salesPromo), bold: true },
              { label: 'Fixed Costs (incl. Dep & Interest)', get: y => y.totalExpenses - (y.powerFuel + y.directLabour + y.freight + y.salesPromo) + y.depreciation + y.interest },
              { label: 'Break-Even (% of sales)', get: y => y.breakEvenPct, bold: true },
              { label: 'Break-Even Sales', get: y => y.sales * y.breakEvenPct / 100, bold: true },
            ]} />
          </CardContent>
        </Card>
      </TabsContent>
      </Tabs>
    </div>
  );
};
