import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import type { ClientRecord } from '../lib/store';
import type { CmaResult, UnitMode } from '../types/cma';
import { fmt, fmtRatio } from '../lib/format';

interface Props {
  client: ClientRecord;
  result: CmaResult;
}

const RATIO_KEYS: { key: string; name: string; norm: string }[] = [
  { key: 'currentRatio', name: 'Current Ratio', norm: 'Benchmark ≥ 1.23' },
  { key: 'dscr', name: 'Debt Service Coverage Ratio (DSCR)', norm: 'Benchmark ≥ 1.75' },
  { key: 'debtEquity', name: 'Debt / Equity Ratio', norm: 'Benchmark ≤ 3.00' },
  { key: 'tolTnw', name: 'Total Outside Liabilities / Total Net Worth', norm: 'Benchmark ≤ 4.50' },
  { key: 'interestCoverage', name: 'Interest Coverage Ratio', norm: 'Benchmark ≥ 2.60' },
];

export const RatioWorkingsScreen: React.FC<Props> = ({ client, result }) => {
  const unit: UnitMode = client.config.unit;
  const { years } = result;

  return (
    <div className="space-y-6">
      <div className="bg-slate-900 border border-slate-800 p-5 rounded-3xl shadow-xl">
        <h3 className="text-base font-bold text-white font-display">Ratio Calculation Workings</h3>
        <p className="text-xs text-slate-400 mt-1">
          Year-wise numerator and denominator components behind every covenant ratio — the same working a bank
          officer traces in the CMA data.
        </p>
      </div>

      {RATIO_KEYS.map(rk => {
        // collect union of component labels across years
        const numLabels: string[] = [];
        const denLabels: string[] = [];
        years.forEach(y => {
          const w = y.workings[rk.key];
          if (!w) return;
          w.numerator.forEach(l => { if (!numLabels.includes(l.label)) numLabels.push(l.label); });
          w.denominator.forEach(l => { if (!denLabels.includes(l.label)) denLabels.push(l.label); });
        });
        const getNum = (yi: number, label: string) =>
          years[yi].workings[rk.key]?.numerator.find(l => l.label === label)?.value ?? 0;
        const getDen = (yi: number, label: string) =>
          years[yi].workings[rk.key]?.denominator.find(l => l.label === label)?.value ?? 0;

        return (
          <Card key={rk.key} className="bg-slate-900 border-slate-800 rounded-3xl shadow-xl overflow-hidden">
            <CardHeader className="border-b border-slate-800 bg-slate-900/80">
              <CardTitle className="text-sm font-display flex items-center justify-between">
                <span>{rk.name}</span>
                <span className="text-[10px] font-semibold uppercase tracking-wider text-indigo-300 bg-indigo-500/10 border border-indigo-500/25 px-2 py-0.5 rounded-full">{rk.norm}</span>
              </CardTitle>
              <p className="text-[11px] text-slate-500 font-mono mt-1">{years[0]?.workings[rk.key]?.formula}</p>
            </CardHeader>
            <CardContent className="p-0 overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-slate-800">
                    <TableHead className="min-w-[220px] text-slate-400">Component</TableHead>
                    {years.map(y => (
                      <TableHead key={y.yearIndex} className="text-right min-w-[105px] text-slate-300">
                        {y.year}<br /><span className="text-[10px] font-normal text-slate-500">{y.type}</span>
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow className="bg-emerald-500/5 border-slate-800">
                    <TableCell colSpan={years.length + 1} className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                      Numerator components
                    </TableCell>
                  </TableRow>
                  {numLabels.map(label => (
                    <TableRow key={label} className="border-slate-800/60">
                      <TableCell className="text-slate-300 text-sm pl-7">{label}</TableCell>
                      {years.map((_, yi) => (
                        <TableCell key={yi} className="text-right font-mono text-sm text-slate-200">{fmt(getNum(yi, label), unit)}</TableCell>
                      ))}
                    </TableRow>
                  ))}
                  <TableRow className="border-slate-800 bg-slate-800/40">
                    <TableCell className="font-semibold text-sm">Total (A)</TableCell>
                    {years.map((y, yi) => (
                      <TableCell key={yi} className="text-right font-mono text-sm font-semibold">{fmt(y.workings[rk.key]?.numeratorTotal ?? 0, unit)}</TableCell>
                    ))}
                  </TableRow>

                  <TableRow className="bg-red-500/5 border-slate-800">
                    <TableCell colSpan={years.length + 1} className="text-[10px] font-bold uppercase tracking-wider text-red-400">
                      Denominator components
                    </TableCell>
                  </TableRow>
                  {denLabels.map(label => (
                    <TableRow key={label} className="border-slate-800/60">
                      <TableCell className="text-slate-300 text-sm pl-7">{label}</TableCell>
                      {years.map((_, yi) => (
                        <TableCell key={yi} className="text-right font-mono text-sm text-slate-200">{fmt(getDen(yi, label), unit)}</TableCell>
                      ))}
                    </TableRow>
                  ))}
                  <TableRow className="border-slate-800 bg-slate-800/40">
                    <TableCell className="font-semibold text-sm">Total (B)</TableCell>
                    {years.map((y, yi) => (
                      <TableCell key={yi} className="text-right font-mono text-sm font-semibold">{fmt(y.workings[rk.key]?.denominatorTotal ?? 0, unit)}</TableCell>
                    ))}
                  </TableRow>

                  <TableRow className="bg-indigo-500/10 border-t-2 border-indigo-500/40">
                    <TableCell className="font-bold text-indigo-200">Ratio = (A) ÷ (B)</TableCell>
                    {years.map((y, yi) => (
                      <TableCell key={yi} className="text-right font-mono font-bold text-indigo-200">
                        {fmtRatio(y.workings[rk.key]?.result ?? 0)}
                      </TableCell>
                    ))}
                  </TableRow>
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
};
