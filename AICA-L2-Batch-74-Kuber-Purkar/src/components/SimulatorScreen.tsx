import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { CheckCircle2, XCircle, Wand2, TrendingUp, Banknote, Gauge } from 'lucide-react';
import type { ClientRecord } from '../lib/store';
import type { CmaResult } from '../types/cma';
import { NumInput } from './NumInput';
import { autoFixParams } from '../engine/cmaEngine';
import { fmt, fmtRatio } from '../lib/format';

interface Props {
  client: ClientRecord;
  onChange: (c: ClientRecord) => void;
  result: CmaResult;
}

export const SimulatorScreen: React.FC<Props> = ({ client, onChange, result }) => {
  const sim = client.sim;
  const unit = client.config.unit;
  const estYear = result.years[client.config.actualYears];
  const setSim = (patch: Partial<typeof sim>) => onChange({ ...client, sim: { ...sim, ...patch } });

  const doAutoFix = () => {
    const fixed = autoFixParams(client.config, client.sim);
    onChange({ ...client, sim: fixed });
  };

  const f = result.feasibility;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* ── Parameters ── */}
      <Card className="lg:col-span-1">
        <CardHeader className="pb-2"><CardTitle className="flex items-center gap-2"><Gauge className="h-5 w-5" /> Assumptions</CardTitle></CardHeader>
        <CardContent className="space-y-5 pt-2">
          <div className="space-y-2">
            <Label>Sales Growth — {sim.salesGrowth}% p.a.</Label>
            <Slider value={[sim.salesGrowth]} min={-20} max={60} step={0.5} onValueChange={v => setSim({ salesGrowth: v[0] })} />
          </div>
          <div className="space-y-2">
            <Label>Cost Efficiency Boost — {sim.marginAdj}%</Label>
            <Slider value={[sim.marginAdj]} min={0} max={20} step={0.5} onValueChange={v => setSim({ marginAdj: v[0] })} />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div><Label>Stock Days</Label><NumInput raw value={sim.inventoryDays} onChange={v => setSim({ inventoryDays: v })} /></div>
            <div><Label>Debtor Days</Label><NumInput raw value={sim.debtorDays} onChange={v => setSim({ debtorDays: v })} /></div>
            <div><Label>Creditor Days</Label><NumInput raw value={sim.creditorDays} onChange={v => setSim({ creditorDays: v })} /></div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div><Label>Tax Rate %</Label><NumInput raw step={0.5} value={sim.taxRate} onChange={v => setSim({ taxRate: v })} /></div>
            <div><Label>Dividend % PAT</Label><NumInput raw value={sim.dividendPct} onChange={v => setSim({ dividendPct: v })} /></div>
            <div><Label>Min Cash</Label><NumInput unit={unit} value={sim.minCashBalance} onChange={v => setSim({ minCashBalance: v })} /></div>
          </div>

          <Button className="w-full" variant={f.feasible ? 'outline' : 'default'} onClick={doAutoFix}>
            <Wand2 className="mr-2 h-4 w-4" /> {f.feasible ? 'Re-run Auto-Match' : 'Auto-Match All Ratios'}
          </Button>

          {/* Manual asset additions */}
          <div className="space-y-2">
            <Label className="font-semibold">Extra Asset Additions (per year)</Label>
            {result.years.map((y, i) => {
              if (i < client.config.actualYears) return null;
              const blockId = sim.tlAssetBlockId;
              const val = sim.manualAssetAdditions[blockId]?.[i] || 0;
              return (
                <div key={i} className="flex items-center gap-2">
                  <span className="text-sm w-20">{y.year}</span>
                  <NumInput unit={unit} value={val} onChange={v => {
                    const manualAssetAdditions = { ...sim.manualAssetAdditions, [blockId]: { ...(sim.manualAssetAdditions[blockId] || {}), [i]: v } };
                    setSim({ manualAssetAdditions });
                  }} />
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* ── Feasibility ── */}
      <div className="lg:col-span-2 space-y-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2">
              {f.feasible ? <CheckCircle2 className="h-5 w-5 text-green-600" /> : <XCircle className="h-5 w-5 text-red-600" />}
              Feasibility — Estimated Year {estYear?.year}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {f.checks.map(c => (
                <div key={c.key} className={`p-3 rounded border text-center ${c.pass ? 'bg-emerald-500/10 border-emerald-500/40' : 'bg-red-500/10 border-red-500/40'}`}>
                  <div className="text-xs text-muted-foreground">{c.name}</div>
                  <div className={`text-2xl font-bold ${c.pass ? 'text-emerald-300' : 'text-red-300'}`}>
                    {c.key === 'dp' ? fmt(c.value, unit) : fmtRatio(c.value)}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {c.direction === 'min' ? 'min' : 'max'} {c.key === 'dp' ? fmt(c.target, unit) : c.target}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-1"><CardTitle className="text-sm flex items-center gap-2"><Banknote className="h-4 w-4" /> Max CC Supportable</CardTitle></CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-800">{fmt(f.maxCcSupportable, unit)}</div>
              <p className="text-xs text-muted-foreground">lower of DP / MPBF (Tandon) / MPBF (turnover)</p>
              {client.config.loan.ccLimit > 0 && (
                <p className={`text-sm mt-1 ${f.maxCcSupportable >= client.config.loan.ccLimit ? 'text-emerald-300' : 'text-red-300'}`}>
                  Requested: {fmt(client.config.loan.ccLimit, unit)} {f.maxCcSupportable >= client.config.loan.ccLimit ? '✓ covered' : '✗ exceeds supportable'}
                </p>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-1"><CardTitle className="text-sm flex items-center gap-2"><Banknote className="h-4 w-4" /> Max TL Supportable</CardTitle></CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-800">{fmt(f.maxTlSupportable, unit)}</div>
              <p className="text-xs text-muted-foreground">at DSCR ≥ 1.75 over the tenure</p>
              {client.config.loan.tlAmount > 0 && (
                <p className={`text-sm mt-1 ${f.maxTlSupportable >= client.config.loan.tlAmount ? 'text-emerald-300' : 'text-red-300'}`}>
                  Requested: {fmt(client.config.loan.tlAmount, unit)} {f.maxTlSupportable >= client.config.loan.tlAmount ? '✓ covered' : '✗ exceeds supportable'}
                </p>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-1"><CardTitle className="text-sm flex items-center gap-2"><TrendingUp className="h-4 w-4" /> Min Growth Needed</CardTitle></CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-800">
                {f.minGrowthNeeded === null ? '—' : `${f.minGrowthNeeded}%`}
              </div>
              <p className="text-xs text-muted-foreground">sales growth at which every check passes</p>
            </CardContent>
          </Card>
        </div>

        {!f.feasible && (
          <Alert variant="destructive">
            <XCircle className="h-4 w-4" />
            <AlertTitle>Not feasible at current assumptions</AlertTitle>
            <AlertDescription>
              Failing: {f.checks.filter(c => !c.pass).map(c => c.name).join(', ')}.
              Use Auto-Match, raise growth/efficiency, reduce working-capital days, or lower the requested limits.
            </AlertDescription>
          </Alert>
        )}

        {/* Drawing power quick view */}
        {client.config.loan.loanType !== 'tl' && estYear && (
          <Card>
            <CardHeader className="pb-1"><CardTitle className="text-sm">Drawing Power — {estYear.year}</CardTitle></CardHeader>
            <CardContent className="text-sm grid grid-cols-2 md:grid-cols-4 gap-3">
              <div>Stock after margin<br /><b>{fmt(estYear.dpStock, unit)}</b></div>
              <div>Debtors after margin<br /><b>{fmt(estYear.dpDebtors, unit)}</b></div>
              <div>Total DP<br /><b>{fmt(estYear.dpTotal, unit)}</b></div>
              <div>CC Limit vs DP<br />
                <b className={estYear.dpShortfall > 0 ? 'text-red-300' : 'text-emerald-300'}>
                  {estYear.dpShortfall > 0 ? `Shortfall ${fmt(estYear.dpShortfall, unit)}` : 'Covered'}
                </b>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};
