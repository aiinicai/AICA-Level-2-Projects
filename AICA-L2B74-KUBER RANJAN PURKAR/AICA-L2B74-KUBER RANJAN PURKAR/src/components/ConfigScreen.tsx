import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Info, PlusCircle, Trash2 } from 'lucide-react';
import type { ClientRecord } from '../lib/store';
import { NumInput } from './NumInput';
import { MONTHS_FY } from '../lib/format';
import type { CustomHead, UnitMode } from '../types/cma';

interface Props {
  client: ClientRecord;
  onChange: (c: ClientRecord) => void;
}

export const ConfigScreen: React.FC<Props> = ({ client, onChange }) => {
  const cfg = client.config;
  const unit = cfg.unit;

  const setConfig = (patch: Partial<typeof cfg>) => onChange({ ...client, config: { ...cfg, ...patch } });
  const setLoan = (patch: Partial<typeof cfg.loan>) => setConfig({ loan: { ...cfg.loan, ...patch } });

  // Custom ledger head configurator state
  const [newHeadName, setNewHeadName] = React.useState('');
  const [newHeadKind, setNewHeadKind] = React.useState<CustomHead['kind']>('expense');
  const [newHeadCurrent, setNewHeadCurrent] = React.useState(true);

  const registerHead = () => {
    const name = newHeadName.trim();
    if (!name) return;
    const head: CustomHead = {
      id: `h${Date.now()}${Math.floor(Math.random() * 1e3)}`,
      name,
      kind: newHeadKind,
      current: newHeadKind === 'expense' ? true : newHeadCurrent,
    };
    setConfig({ customHeads: [...(cfg.customHeads || []), head] });
    setNewHeadName('');
  };

  const removeHead = (id: string) => {
    setConfig({ customHeads: (cfg.customHeads || []).filter(h => h.id !== id) });
  };

  return (
    <Tabs defaultValue="project" className="w-full">
      <TabsList className="grid w-full grid-cols-4">
        <TabsTrigger value="project">1. Project & Years</TabsTrigger>
        <TabsTrigger value="loan">2. Loan Details</TabsTrigger>
        <TabsTrigger value="assets">3. Depreciation Blocks</TabsTrigger>
        <TabsTrigger value="heads">4. Custom Ledger Heads</TabsTrigger>
      </TabsList>

      {/* ── Project ── */}
      <TabsContent value="project">
        <Card>
          <CardHeader><CardTitle>Project Configuration</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="col-span-2">
              <Label>Client / Company Name</Label>
              <Input value={cfg.clientName} onChange={e => setConfig({ clientName: e.target.value })} />
            </div>
            <div>
              <Label>Amounts shown in</Label>
              <Select value={unit} onValueChange={v => setConfig({ unit: v as UnitMode })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="rs">Rupees (₹)</SelectItem>
                  <SelectItem value="thousands">Thousands (₹ '000)</SelectItem>
                  <SelectItem value="lakhs">Lakhs (₹ L)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>First Actual Year (FY start)</Label>
              <NumInput raw value={cfg.startYear} onChange={v => setConfig({ startYear: Math.round(v) })} />
              <p className="text-xs text-muted-foreground mt-1">e.g. 2023 → FY 2023-24</p>
            </div>
            <div>
              <Label>No. of Actual / Audited Years (1–4)</Label>
              <NumInput raw value={cfg.actualYears} onChange={v => setConfig({ actualYears: Math.max(1, Math.min(4, Math.round(v))) })} />
            </div>
            <div>
              <Label>No. of Projected Years (1–10)</Label>
              <NumInput raw value={cfg.projectedYears} onChange={v => setConfig({ projectedYears: Math.max(1, Math.min(10, Math.round(v))) })} />
            </div>
            <Alert className="col-span-2 md:col-span-3">
              <Info className="h-4 w-4" />
              <AlertDescription>
                Structure: {cfg.actualYears} actual year(s) + 1 estimated (provisional) year + {cfg.projectedYears} projected years.
                The loan is assumed to be granted in the estimated year.
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </TabsContent>

      {/* ── Loan ── */}
      <TabsContent value="loan">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card>
            <CardHeader><CardTitle>Loan Type & Grant</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Facility Type</Label>
                <Select value={cfg.loan.loanType} onValueChange={v => setLoan({ loanType: v as any })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="cc">Cash Credit (CC) only</SelectItem>
                    <SelectItem value="tl">Term Loan only</SelectItem>
                    <SelectItem value="both">CC + Term Loan</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <Label>Grant Month (in estimated FY)</Label>
                  <Select value={String(cfg.loan.grantMonthIndex)} onValueChange={v => setLoan({ grantMonthIndex: +v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {MONTHS_FY.map((m, i) => <SelectItem key={i} value={String(i)}>{m}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Disbursal Day</Label>
                  <NumInput raw value={cfg.loan.grantDay} onChange={v => setLoan({ grantDay: Math.max(1, Math.min(28, Math.round(v))) })} />
                </div>
              </div>
            </CardContent>
          </Card>

          {cfg.loan.loanType !== 'tl' && (
            <Card>
              <CardHeader><CardTitle>Cash Credit (Working Capital)</CardTitle></CardHeader>
              <CardContent className="grid grid-cols-2 gap-4">
                <div><Label>CC Limit requested</Label><NumInput unit={unit} value={cfg.loan.ccLimit} onChange={v => setLoan({ ccLimit: v })} /></div>
                <div><Label>CC Interest Rate %</Label><NumInput raw step={0.05} value={cfg.loan.ccRate} onChange={v => setLoan({ ccRate: v })} /></div>
                <div><Label>Margin on Stock % (DP)</Label><NumInput raw value={cfg.loan.ccStockMarginPct} onChange={v => setLoan({ ccStockMarginPct: v })} /></div>
                <div><Label>Margin on Debtors % (DP)</Label><NumInput raw value={cfg.loan.ccDebtorMarginPct} onChange={v => setLoan({ ccDebtorMarginPct: v })} /></div>
                <div className="col-span-2"><Label>Debtor cover period for DP (days)</Label><NumInput raw value={cfg.loan.ccDebtorCoverDays} onChange={v => setLoan({ ccDebtorCoverDays: v })} /></div>
              </CardContent>
            </Card>
          )}

          {cfg.loan.loanType !== 'cc' && (
            <Card className="lg:col-span-2">
              <CardHeader><CardTitle>Term Loan</CardTitle></CardHeader>
              <CardContent className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div><Label>TL Amount</Label><NumInput unit={unit} value={cfg.loan.tlAmount} onChange={v => setLoan({ tlAmount: v })} /></div>
                <div><Label>TL Interest Rate %</Label><NumInput raw step={0.05} value={cfg.loan.tlRate} onChange={v => setLoan({ tlRate: v })} /></div>
                <div><Label>Tenure (months, incl. moratorium)</Label><NumInput raw value={cfg.loan.tlTenureMonths} onChange={v => setLoan({ tlTenureMonths: Math.round(v) })} /></div>
                <div><Label>Moratorium (months, interest only)</Label><NumInput raw value={cfg.loan.tlMoratoriumMonths} onChange={v => setLoan({ tlMoratoriumMonths: Math.round(v) })} /></div>
                <div><Label>EMI Day of Month</Label><NumInput raw value={cfg.loan.emiDay} onChange={v => setLoan({ emiDay: Math.max(1, Math.min(28, Math.round(v))) })} /></div>
                <div>
                  <Label>Asset block for TL purchase</Label>
                  <Select value={client.sim.tlAssetBlockId} onValueChange={v => onChange({ ...client, sim: { ...client.sim, tlAssetBlockId: v } })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {cfg.assetBlocks.map(b => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </TabsContent>

      {/* ── Asset blocks ── */}
      <TabsContent value="assets">
        <Card>
          <CardHeader><CardTitle>Depreciation Blocks (WDV method)</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                Enter opening WDV as on 1st April of the first actual year. The Term Loan amount is added
                automatically to the selected block in the grant year; per-year manual additions can be
                entered in the Simulator.
              </AlertDescription>
            </Alert>
            <div className="grid grid-cols-12 gap-2 font-medium text-sm text-muted-foreground">
              <div className="col-span-4">Block</div>
              <div className="col-span-3">Rate % (WDV)</div>
              <div className="col-span-5">Opening WDV</div>
            </div>
            {cfg.assetBlocks.map((b, idx) => (
              <div key={b.id} className="grid grid-cols-12 gap-2 items-center">
                <div className="col-span-4">
                  {b.id.startsWith('other') ? (
                    <Input value={b.name} onChange={e => {
                      const assetBlocks = cfg.assetBlocks.map((x, j) => j === idx ? { ...x, name: e.target.value } : x);
                      setConfig({ assetBlocks });
                    }} />
                  ) : <span className="text-sm font-medium">{b.name}</span>}
                </div>
                <div className="col-span-3">
                  <NumInput raw step={0.5} value={b.rate} onChange={v => {
                    const assetBlocks = cfg.assetBlocks.map((x, j) => j === idx ? { ...x, rate: v } : x);
                    setConfig({ assetBlocks });
                  }} />
                </div>
                <div className="col-span-5">
                  <NumInput unit={unit} value={b.opening} onChange={v => {
                    const assetBlocks = cfg.assetBlocks.map((x, j) => j === idx ? { ...x, opening: v } : x);
                    setConfig({ assetBlocks });
                  }} />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </TabsContent>

      {/* ── Custom ledger heads ── */}
      <TabsContent value="heads">
        <Card>
          <CardHeader><CardTitle>Overhead / Ledger Head Configurator</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                Register extra ledger rows for the P&L or Balance Sheet. They appear in the Audited Ledgers
                grid, flow into estimates/projections, and show up in the Operating Statement / Balance Sheet
                reports. "Current" items are included in the Current Ratio.
              </AlertDescription>
            </Alert>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
              <div className="md:col-span-2">
                <Label>Ledger head name</Label>
                <Input
                  placeholder="e.g. Packing Charges, Job Work, GST Payable"
                  value={newHeadName}
                  onChange={e => setNewHeadName(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && registerHead()}
                />
              </div>
              <div>
                <Label>Appears in</Label>
                <Select value={newHeadKind} onValueChange={v => setNewHeadKind(v as CustomHead['kind'])}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="expense">P&L — Expense</SelectItem>
                    <SelectItem value="asset">Balance Sheet — Asset</SelectItem>
                    <SelectItem value="liability">Balance Sheet — Liability</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex gap-2 items-center">
                {newHeadKind !== 'expense' && (
                  <Select value={newHeadCurrent ? 'cur' : 'noncur'} onValueChange={v => setNewHeadCurrent(v === 'cur')}>
                    <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="cur">Current</SelectItem>
                      <SelectItem value="noncur">Non-current</SelectItem>
                    </SelectContent>
                  </Select>
                )}
                <Button onClick={registerHead} className="bg-indigo-600 hover:bg-indigo-500">
                  <PlusCircle className="mr-2 h-4 w-4" /> Register Row
                </Button>
              </div>
            </div>

            {(cfg.customHeads || []).length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">No customized ledger rows created yet. Standard CMA heads are always available.</p>
            ) : (
              <div className="divide-y divide-slate-800 border border-slate-800 rounded-xl overflow-hidden">
                {(cfg.customHeads || []).map(h => (
                  <div key={h.id} className="flex items-center justify-between px-4 py-2.5 bg-slate-900/50">
                    <div className="flex items-center gap-3">
                      <span className="font-medium text-sm">{h.name}</span>
                      <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border border-indigo-500/30 bg-indigo-500/10 text-indigo-300">
                        {h.kind === 'expense' ? 'P&L Expense' : h.kind === 'asset' ? `Asset · ${h.current ? 'Current' : 'Non-current'}` : `Liability · ${h.current ? 'Current' : 'Non-current'}`}
                      </span>
                    </div>
                    <Button variant="ghost" size="icon" onClick={() => removeHead(h.id)}>
                      <Trash2 className="h-4 w-4 text-red-400" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  );
};
