import React, { useState } from 'react';
import {
  SlidersHorizontal,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Sparkles,
  RefreshCw,
  Layers,
  ArrowRight,
  Shield,
  CheckCircle2,
  Users,
  AlertTriangle,
  Grid,
  Calendar,
  Zap,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { FinancialModel, ScenarioDrivers, ScenarioResult, ClientProfile } from '../../types';
import { ForecastingEngine } from '../../services/forecastingEngine';
import { FirmReportHeader, FirmReportFooter } from '../common/FirmHeaderFooter';
import { SensitivityHeatmap } from './SensitivityHeatmap';
import { CashFlowForecastSchedule } from './CashFlowForecastSchedule';

interface WhatIfScenarioViewProps {
  model: FinancialModel;
  firmName?: string;
}

export const WhatIfScenarioView: React.FC<WhatIfScenarioViewProps> = ({
  model,
  firmName = 'Jasleen Daswal & Associates',
}) => {
  const client = model.client;

  // Primary view mode tab: 'simulator' | 'sensitivity_heatmap' | 'cash_forecast'
  const [activeTab, setActiveTab] = useState<'simulator' | 'sensitivity_heatmap' | 'cash_forecast'>('sensitivity_heatmap');

  // Base preset
  const basePreset = ForecastingEngine.getPrebuiltScenarios(model)[0].driverConfig;

  const [activePreset, setActivePreset] = useState<string>('custom');
  const [drivers, setDrivers] = useState<ScenarioDrivers>({
    name: 'Custom What-If Scenario',
    description: 'Management defined sensitivity test',
    revenueGrowthRateDelta: 8,
    priceAdjustmentPercent: 0,
    grossMarginDelta: 0,
    opexInflationPercent: 4,
    headcountDelta: 2,
    averageSalaryNewHires: 85000,
    marketingBudgetDeltaMonthly: 5000,
    dsoImprovementDays: 0,
    dpoExtensionDays: 0,
  } as any);

  const baseResult = ForecastingEngine.generateRolling12MonthForecast(model, basePreset);
  const currentScenarioResult = ForecastingEngine.generateRolling12MonthForecast(model, drivers);

  const formatCurrency = (val: number) => {
    if (Math.abs(val) >= 1_000_000) {
      return `${client.currencySymbol}${(val / 1_000_000).toFixed(2)}M`;
    }
    return `${client.currencySymbol}${(val / 1_000).toFixed(0)}k`;
  };

  const handleApplyPreset = (presetName: string) => {
    setActivePreset(presetName);
    const presets = ForecastingEngine.getPrebuiltScenarios(model);
    const matched = presets.find(p => p.driverConfig.name.toLowerCase().includes(presetName.toLowerCase()));
    if (matched) {
      setDrivers(matched.driverConfig);
    }
  };

  // Comparative Data for Chart
  const comparisonData = [
    {
      metric: 'Projected Revenue',
      'Base Case': baseResult.totalProjectedRevenue,
      'Scenario Case': currentScenarioResult.totalProjectedRevenue,
    },
    {
      metric: 'Projected Gross Profit',
      'Base Case': baseResult.totalProjectedGrossProfit,
      'Scenario Case': currentScenarioResult.totalProjectedGrossProfit,
    },
    {
      metric: 'Projected EBITDA',
      'Base Case': baseResult.totalProjectedEbitda,
      'Scenario Case': currentScenarioResult.totalProjectedEbitda,
    },
    {
      metric: 'Ending Cash Balance',
      'Base Case': baseResult.endingCashBalance,
      'Scenario Case': currentScenarioResult.endingCashBalance,
    },
  ];

  const revenueDelta = currentScenarioResult.totalProjectedRevenue - baseResult.totalProjectedRevenue;
  const ebitdaDelta = currentScenarioResult.totalProjectedEbitda - baseResult.totalProjectedEbitda;
  const cashDelta = currentScenarioResult.endingCashBalance - baseResult.endingCashBalance;

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <FirmReportHeader client={client} reportTitle="Strategic What-If Scenario, Sensitivity & Cash Flow Modeling" firmName={firmName} />

      {/* Main View Mode Selector / Sensitivity Toggle */}
      <div className="bg-white p-2 rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-xl">
          <button
            onClick={() => setActiveTab('sensitivity_heatmap')}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
              activeTab === 'sensitivity_heatmap'
                ? 'bg-white text-indigo-700 shadow-xs font-extrabold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Grid className="w-4 h-4 text-indigo-600" />
            <span>Sensitivity Matrix & Heat Map</span>
            <span className="text-[10px] bg-indigo-100 text-indigo-800 px-1.5 py-0.2 rounded font-mono">
              Multi-Driver
            </span>
          </button>

          <button
            onClick={() => setActiveTab('simulator')}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
              activeTab === 'simulator'
                ? 'bg-white text-indigo-700 shadow-xs font-extrabold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <SlidersHorizontal className="w-4 h-4 text-indigo-600" />
            <span>Interactive Scenario Simulator</span>
          </button>

          <button
            onClick={() => setActiveTab('cash_forecast')}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
              activeTab === 'cash_forecast'
                ? 'bg-white text-sky-700 shadow-xs font-extrabold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Calendar className="w-4 h-4 text-sky-600" />
            <span>Cash Flow Forecast (Weekly / Monthly)</span>
          </button>
        </div>

        <div className="hidden lg:flex items-center gap-2 px-3 text-xs text-slate-500">
          <Shield className="w-3.5 h-3.5 text-emerald-600" />
          <span>Deterministic Pro-Forma Engine Active</span>
        </div>
      </div>

      {/* TAB 1: SENSITIVITY MATRIX & VISUAL HEAT MAP */}
      {activeTab === 'sensitivity_heatmap' && (
        <SensitivityHeatmap model={model} />
      )}

      {/* TAB 2: CASH FLOW FORECAST (WEEKLY & MONTHLY) */}
      {activeTab === 'cash_forecast' && (
        <CashFlowForecastSchedule model={model} drivers={drivers} />
      )}

      {/* TAB 3: INTERACTIVE SCENARIO SIMULATOR (Single Scenario Fine-Tuning) */}
      {activeTab === 'simulator' && (
        <div className="space-y-6">
          {/* Preset Scenario Selector Buttons */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
            <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
              <button
                onClick={() => handleApplyPreset('base')}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                  activePreset === 'base'
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                Base Case (Historical Run-Rate)
              </button>
              <button
                onClick={() => handleApplyPreset('conservative')}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                  activePreset === 'conservative'
                    ? 'bg-amber-600 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                Conservative / Downturn (-6% Rev)
              </button>
              <button
                onClick={() => handleApplyPreset('growth')}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                  activePreset === 'growth'
                    ? 'bg-emerald-600 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                Aggressive Expansion (+16% Rev)
              </button>
              <button
                onClick={() => setActivePreset('custom')}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                  activePreset === 'custom'
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                Custom Sensitivity Sliders
              </button>
            </div>
          </div>

          {/* Main Grid: Interactive Sliders (Left) vs Real-Time Impact & Chart (Right) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Interactive Scenario Sliders (5 cols) */}
            <div className="lg:col-span-5 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-5">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <SlidersHorizontal className="w-4 h-4 text-indigo-600" />
                  Scenario Driver Assumptions
                </h4>
                <span className="text-[11px] font-mono bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded font-semibold">
                  Deterministic FP&A
                </span>
              </div>

              {/* Slider 1: Revenue Growth Rate */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
                  <span>Annual Revenue Growth Delta</span>
                  <span className="text-indigo-600 font-bold font-mono">
                    {drivers.revenueGrowthRateDelta > 0 ? `+${drivers.revenueGrowthRateDelta}%` : `${drivers.revenueGrowthRateDelta}%`}
                  </span>
                </div>
                <input
                  type="range"
                  min="-20"
                  max="40"
                  step="1"
                  value={drivers.revenueGrowthRateDelta}
                  onChange={e => {
                    setDrivers({ ...drivers, revenueGrowthRateDelta: Number(e.target.value) });
                    setActivePreset('custom');
                  }}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                />
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>-20% (Contraction)</span>
                  <span>0%</span>
                  <span>+40% (High Growth)</span>
                </div>
              </div>

              {/* Slider 2: Price Increase */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
                  <span>Price Hike / (Discount)</span>
                  <span className="text-indigo-600 font-bold font-mono">
                    {drivers.priceAdjustmentPercent > 0 ? `+${drivers.priceAdjustmentPercent}%` : `${drivers.priceAdjustmentPercent}%`}
                  </span>
                </div>
                <input
                  type="range"
                  min="-10"
                  max="15"
                  step="0.5"
                  value={drivers.priceAdjustmentPercent}
                  onChange={e => {
                    setDrivers({ ...drivers, priceAdjustmentPercent: Number(e.target.value) });
                    setActivePreset('custom');
                  }}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                />
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>-10%</span>
                  <span>0%</span>
                  <span>+15%</span>
                </div>
              </div>

              {/* Slider 3: Gross Margin Shift */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
                  <span>Gross Margin Point Shift</span>
                  <span className="text-emerald-600 font-bold font-mono">
                    {drivers.grossMarginDelta > 0 ? `+${drivers.grossMarginDelta}% pts` : `${drivers.grossMarginDelta}% pts`}
                  </span>
                </div>
                <input
                  type="range"
                  min="-8"
                  max="8"
                  step="0.5"
                  value={drivers.grossMarginDelta}
                  onChange={e => {
                    setDrivers({ ...drivers, grossMarginDelta: Number(e.target.value) });
                    setActivePreset('custom');
                  }}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-emerald-600"
                />
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>-8% pts</span>
                  <span>0%</span>
                  <span>+8% pts</span>
                </div>
              </div>

              {/* Slider 4: Headcount Additions */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
                  <span>Net New Hires</span>
                  <span className="text-violet-600 font-bold font-mono">+{drivers.headcountDelta} employees</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="12"
                  step="1"
                  value={drivers.headcountDelta}
                  onChange={e => {
                    setDrivers({ ...drivers, headcountDelta: Number(e.target.value) });
                    setActivePreset('custom');
                  }}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-violet-600"
                />
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>0 hires</span>
                  <span>Avg $85k fully burdened</span>
                  <span>+12 hires</span>
                </div>
              </div>

              {/* Slider 5: OPEX Inflation */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
                  <span>Overhead / OPEX Inflation</span>
                  <span className="text-amber-600 font-bold font-mono">+{drivers.opexInflationPercent}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="15"
                  step="0.5"
                  value={drivers.opexInflationPercent}
                  onChange={e => {
                    setDrivers({ ...drivers, opexInflationPercent: Number(e.target.value) });
                    setActivePreset('custom');
                  }}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-amber-600"
                />
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>0%</span>
                  <span>+15%</span>
                </div>
              </div>

              {/* Slider 6: DSO Collections */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
                  <span>DSO Collection Speed</span>
                  <span className="text-sky-600 font-bold font-mono">
                    {drivers.dsoImprovementDays > 0 ? `+${drivers.dsoImprovementDays} days faster` : `${drivers.dsoImprovementDays} days`}
                  </span>
                </div>
                <input
                  type="range"
                  min="-10"
                  max="15"
                  step="1"
                  value={drivers.dsoImprovementDays}
                  onChange={e => {
                    setDrivers({ ...drivers, dsoImprovementDays: Number(e.target.value) });
                    setActivePreset('custom');
                  }}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-sky-600"
                />
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>-10d (Slower)</span>
                  <span>0d (Baseline)</span>
                  <span>+15d (Faster)</span>
                </div>
              </div>
            </div>

            {/* Right Column: Comparative Variance & Chart (7 cols) */}
            <div className="lg:col-span-7 space-y-6">
              {/* Top Impact Summary Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
                  <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                    Revenue Variance
                  </span>
                  <div className={`mt-1 text-xl font-black ${revenueDelta >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                    {revenueDelta >= 0 ? `+${formatCurrency(revenueDelta)}` : `-${formatCurrency(Math.abs(revenueDelta))}`}
                  </div>
                  <span className="text-[11px] text-slate-500 font-medium">vs Base 12M Pro-Forma</span>
                </div>

                <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
                  <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                    EBITDA Impact
                  </span>
                  <div className={`mt-1 text-xl font-black ${ebitdaDelta >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                    {ebitdaDelta >= 0 ? `+${formatCurrency(ebitdaDelta)}` : `-${formatCurrency(Math.abs(ebitdaDelta))}`}
                  </div>
                  <span className="text-[11px] text-slate-500 font-medium">Net Profitability Shift</span>
                </div>

                <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
                  <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                    Ending Cash Delta
                  </span>
                  <div className={`mt-1 text-xl font-black ${cashDelta >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                    {cashDelta >= 0 ? `+${formatCurrency(cashDelta)}` : `-${formatCurrency(Math.abs(cashDelta))}`}
                  </div>
                  <span className="text-[11px] text-slate-500 font-medium">12-Month Liquidity Buffer</span>
                </div>
              </div>

              {/* Bar Chart: Base Case vs Scenario Case */}
              <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-4">
                <h4 className="text-sm font-bold text-slate-900">
                  Side-by-Side Financial Impact Comparison
                </h4>
                <div className="h-64 w-full pt-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={comparisonData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                      <XAxis dataKey="metric" stroke="#94a3b8" fontSize={11} />
                      <YAxis stroke="#94a3b8" fontSize={11} tickFormatter={v => `${client.currencySymbol}${(v / 1000).toFixed(0)}k`} />
                      <Tooltip
                        formatter={(value: any) => [`${client.currencySymbol}${Number(value).toLocaleString()}`, '']}
                        contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', color: '#fff', fontSize: '12px' }}
                      />
                      <Legend wrapperStyle={{ fontSize: '12px' }} />
                      <Bar dataKey="Base Case" fill="#94a3b8" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="Scenario Case" fill="#4f46e5" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Strategic Sensitivity Insights Card */}
              <div className="p-4 bg-indigo-50/70 border border-indigo-200/80 rounded-2xl flex items-start gap-3">
                <div className="p-2 bg-indigo-600 text-white rounded-xl shadow-xs shrink-0">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div className="text-xs text-indigo-950 space-y-1">
                  <span className="font-bold text-indigo-900 block">
                    Virtual CFO Strategic Assessment:
                  </span>
                  <p className="leading-relaxed text-indigo-900/90">
                    Under these assumptions, the business delivers{' '}
                    <span className="font-bold text-slate-900">{formatCurrency(currentScenarioResult.totalProjectedEbitda)}</span>{' '}
                    in EBITDA over 12 months. Net ending cash is projected at{' '}
                    <span className="font-bold text-slate-900">{formatCurrency(currentScenarioResult.endingCashBalance)}</span>, maintaining an unencumbered operating runway of{' '}
                    <span className="font-bold text-slate-900">{currentScenarioResult.runwayMonths.toFixed(1)} months</span>.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <FirmReportFooter firmName={firmName} />
    </div>
  );
};
