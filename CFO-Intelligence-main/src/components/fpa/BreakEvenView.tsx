import React, { useState } from 'react';
import {
  Scale,
  DollarSign,
  TrendingUp,
  Shield,
  Target,
  Sparkles,
  Layers,
  ArrowRight,
  Info,
  CheckCircle2,
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ReferenceDot,
} from 'recharts';
import { FinancialModel, ClientProfile } from '../../types';
import { FinancialEngine } from '../../services/financialEngine';
import { FirmReportHeader, FirmReportFooter } from '../common/FirmHeaderFooter';

interface BreakEvenViewProps {
  model: FinancialModel;
  firmName?: string;
}

export const BreakEvenView: React.FC<BreakEvenViewProps> = ({
  model,
  firmName = 'Jasleen Daswal & Associates',
}) => {
  const client = model.client;
  const latest = model.historicalMonthly[model.historicalMonthly.length - 1];

  const [unitPrice, setUnitPrice] = useState<number>(client.industry === 'medical' ? 220 : client.industry === 'restaurant' ? 45 : 1850);
  const [unitVariableCost, setUnitVariableCost] = useState<number>(client.industry === 'medical' ? 44 : client.industry === 'restaurant' ? 13 : 1100);

  const breakEven = FinancialEngine.calculateBreakEvenAnalysis(model, unitPrice, unitVariableCost);

  const formatCurrency = (val: number) => {
    if (Math.abs(val) >= 1_000_000) {
      return `${client.currencySymbol}${(val / 1_000_000).toFixed(2)}M`;
    }
    return `${client.currencySymbol}${(val / 1_000).toFixed(0)}k`;
  };

  // Generate Break-Even Curve Data
  const curvePoints = [];
  const maxRev = latest.revenue * 1.6;
  const step = maxRev / 10;
  
  for (let rev = 0; rev <= maxRev; rev += step) {
    const varCost = rev * breakEven.variableCostRatio;
    const totalCost = breakEven.fixedCosts + varCost;
    curvePoints.push({
      revenueInput: rev,
      Revenue: Math.round(rev),
      TotalCosts: Math.round(totalCost),
      FixedCosts: Math.round(breakEven.fixedCosts),
    });
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <FirmReportHeader client={client} reportTitle="Break-Even & Unit Economics Analysis" firmName={firmName} />

      {/* Top 4 Metric Strip */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Monthly Break-Even Revenue
          </span>
          <div className="mt-2 text-2xl font-black text-slate-900">
            {formatCurrency(breakEven.breakEvenRevenueMonthly)}
          </div>
          <div className="text-xs text-indigo-700 font-semibold mt-1">
            Zero Profit / Zero Loss Threshold
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Current Monthly Revenue
          </span>
          <div className="mt-2 text-2xl font-black text-slate-900">
            {formatCurrency(breakEven.currentRevenueMonthly)}
          </div>
          <div className="text-xs text-emerald-700 font-semibold mt-1">
            Active Baseline Performance
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Margin of Safety ($)
          </span>
          <div className="mt-2 text-2xl font-black text-emerald-600">
            {formatCurrency(breakEven.marginOfSafetyDollars)}
          </div>
          <div className="text-xs text-emerald-700 font-semibold mt-1">
            Revenue buffer before incurring loss
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Margin of Safety (%)
          </span>
          <div className="mt-2 text-2xl font-black text-emerald-600">
            {breakEven.marginOfSafetyPercent.toFixed(1)}%
          </div>
          <div className="text-xs text-slate-500 font-medium mt-1">
            Revenues can fall {breakEven.marginOfSafetyPercent.toFixed(1)}% before break-even
          </div>
        </div>
      </div>

      {/* Main Grid: Interactive Unit Economics (Left) vs Break-Even Curve (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Unit Economics Calculator */}
        <div className="lg:col-span-5 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-5">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Scale className="w-4 h-4 text-indigo-600" />
              Unit Economics & Contribution
            </h4>
            <span className="text-[11px] font-mono bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded font-semibold">
              Unit Model
            </span>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">
                Average Selling Price per Unit / Service Encounter ({client.currencySymbol})
              </label>
              <input
                type="number"
                value={unitPrice}
                onChange={e => setUnitPrice(Math.max(1, Number(e.target.value)))}
                className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2 text-sm font-bold text-slate-900 focus:outline-hidden focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">
                Direct Variable Cost per Unit / Encounter ({client.currencySymbol})
              </label>
              <input
                type="number"
                value={unitVariableCost}
                onChange={e => setUnitVariableCost(Math.max(0, Number(e.target.value)))}
                className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2 text-sm font-bold text-slate-900 focus:outline-hidden focus:border-indigo-500"
              />
            </div>

            {/* Calculated Contribution Margin Strip */}
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-500 font-medium">Unit Contribution Margin:</span>
                <span className="font-bold text-slate-900">
                  {client.currencySymbol}{breakEven.contributionMarginPerUnit?.toFixed(2) || (unitPrice - unitVariableCost).toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 font-medium">Contribution Margin Ratio:</span>
                <span className="font-bold text-emerald-700">
                  {(breakEven.contributionMarginRatio * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between pt-2 border-t border-slate-200">
                <span className="text-slate-700 font-bold">Monthly Units to Break Even:</span>
                <span className="font-black text-indigo-700 text-sm">
                  {breakEven.breakEvenUnitsMonthly?.toLocaleString() || Math.round(breakEven.breakEvenRevenueMonthly / (unitPrice || 1)).toLocaleString()} units
                </span>
              </div>
            </div>

            {/* Cost Breakdown */}
            <div className="space-y-2 pt-2">
              <span className="text-xs font-bold text-slate-700 block">
                Deterministic Cost Structure
              </span>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-3 bg-indigo-50/50 rounded-xl border border-indigo-100">
                  <span className="text-[10px] text-indigo-700 uppercase font-bold">Fixed Monthly OPEX</span>
                  <div className="text-sm font-bold text-slate-900">{formatCurrency(breakEven.fixedCosts)}</div>
                </div>
                <div className="p-3 bg-violet-50/50 rounded-xl border border-violet-100">
                  <span className="text-[10px] text-violet-700 uppercase font-bold">Variable Cost %</span>
                  <div className="text-sm font-bold text-slate-900">{(breakEven.variableCostRatio * 100).toFixed(1)}%</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Break-Even Visual Graph */}
        <div className="lg:col-span-7 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h4 className="text-sm font-bold text-slate-900">
                Break-Even Crossover Chart
              </h4>
              <p className="text-xs text-slate-500">
                Intersection of Total Revenue (indigo) and Total Costs (rose) defines the break-even operating volume.
              </p>
            </div>
          </div>

          <div className="h-72 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={curvePoints} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="Revenue" stroke="#94a3b8" fontSize={11} tickFormatter={v => `${client.currencySymbol}${(v / 1000).toFixed(0)}k`} />
                <YAxis stroke="#94a3b8" fontSize={11} tickFormatter={v => `${client.currencySymbol}${(v / 1000).toFixed(0)}k`} />
                <Tooltip
                  formatter={(value: any) => [`${client.currencySymbol}${Number(value).toLocaleString()}`, '']}
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', color: '#fff', fontSize: '12px' }}
                />
                <Legend wrapperStyle={{ fontSize: '12px' }} />
                <Line type="monotone" dataKey="Revenue" stroke="#4f46e5" strokeWidth={2.5} name="Total Sales Revenue" />
                <Line type="monotone" dataKey="TotalCosts" stroke="#f43f5e" strokeWidth={2.5} name="Total Costs (Fixed + Var)" />
                <Line type="monotone" dataKey="FixedCosts" stroke="#94a3b8" strokeWidth={1.5} strokeDasharray="4 4" name="Fixed Overhead" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-200 text-xs text-emerald-900 flex items-center justify-between">
            <span className="font-medium">Current Revenue provides a generous margin of safety buffer.</span>
            <span className="font-bold">{breakEven.marginOfSafetyPercent.toFixed(1)}% Safe</span>
          </div>
        </div>
      </div>

      <FirmReportFooter firmName={firmName} />
    </div>
  );
};
