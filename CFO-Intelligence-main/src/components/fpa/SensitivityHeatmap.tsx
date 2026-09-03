import React, { useState, useMemo } from 'react';
import {
  Grid,
  Sparkles,
  Sliders,
  TrendingUp,
  TrendingDown,
  Info,
  DollarSign,
  Percent,
  Layers,
  ArrowRight,
  Maximize2,
  RefreshCw,
  Zap,
} from 'lucide-react';
import { FinancialModel, SensitivityMatrixData, SensitivityMatrixCell, ScenarioDrivers } from '../../types';
import { ForecastingEngine } from '../../services/forecastingEngine';

interface SensitivityHeatmapProps {
  model: FinancialModel;
  onApplyDrivers?: (drivers: Partial<ScenarioDrivers>) => void;
}

export const SensitivityHeatmap: React.FC<SensitivityHeatmapProps> = ({
  model,
  onApplyDrivers,
}) => {
  const client = model.client;
  
  // Matrix mode
  const [matrixMode, setMatrixMode] = useState<'rev_vs_opex' | 'rev_vs_cogs' | 'price_vs_volume'>('rev_vs_opex');
  const [targetMetric, setTargetMetric] = useState<'netIncome' | 'netMarginPercent' | 'ebitda' | 'endingCash'>('netIncome');

  // Simultaneous multi-driver adjustment sliders
  const [revDriverDelta, setRevDriverDelta] = useState<number>(0);
  const [cogsDriverDelta, setCogsDriverDelta] = useState<number>(0);
  const [opexDriverDelta, setOpexDriverDelta] = useState<number>(0);

  // Selected cell for drill-down inspection
  const [selectedCell, setSelectedCell] = useState<SensitivityMatrixCell | null>(null);

  // Generate Matrix data
  const matrixData: SensitivityMatrixData = useMemo(() => {
    return ForecastingEngine.generateSensitivityMatrix(model, matrixMode);
  }, [model, matrixMode]);

  // Format currency helper
  const formatCurrency = (val: number) => {
    if (Math.abs(val) >= 1_000_000) {
      return `${client.currencySymbol}${(val / 1_000_000).toFixed(2)}M`;
    }
    return `${client.currencySymbol}${(val / 1_000).toFixed(0)}k`;
  };

  // Preset Multi-Driver Stress-Tests
  const handleApplyPreset = (preset: 'stagflation' | 'efficiency' | 'supply_shock' | 'boom' | 'reset') => {
    if (preset === 'stagflation') {
      setRevDriverDelta(-10);
      setCogsDriverDelta(6);
      setOpexDriverDelta(8);
      setMatrixMode('rev_vs_opex');
    } else if (preset === 'efficiency') {
      setRevDriverDelta(8);
      setCogsDriverDelta(-4);
      setOpexDriverDelta(-5);
      setMatrixMode('rev_vs_opex');
    } else if (preset === 'supply_shock') {
      setRevDriverDelta(-5);
      setCogsDriverDelta(10);
      setOpexDriverDelta(4);
      setMatrixMode('rev_vs_cogs');
    } else if (preset === 'boom') {
      setRevDriverDelta(15);
      setCogsDriverDelta(-2);
      setOpexDriverDelta(5);
      setMatrixMode('rev_vs_opex');
    } else {
      setRevDriverDelta(0);
      setCogsDriverDelta(0);
      setOpexDriverDelta(0);
    }
  };

  // Simultaneous Combined Impact on Bottom Line Net Income
  const combinedImpact = useMemo(() => {
    const historical = model.historicalMonthly;
    const latest = historical.length > 0 ? historical[historical.length - 1] : null;
    const baseRevenue = latest ? latest.revenue * 12 : 5000000;
    const baseMargin = latest ? latest.grossMarginPercent : 45;
    const baseOpex = latest ? latest.totalOpex * 12 : 1400000;

    const adjustedRev = baseRevenue * (1 + revDriverDelta / 100);
    const adjustedMargin = Math.max(5, Math.min(95, baseMargin - cogsDriverDelta));
    const adjustedGrossProfit = adjustedRev * (adjustedMargin / 100);
    const adjustedCogs = adjustedRev - adjustedGrossProfit;
    const adjustedOpex = baseOpex * (1 + opexDriverDelta / 100);
    const adjustedEbitda = adjustedGrossProfit - adjustedOpex;
    const taxAndInterest = adjustedEbitda > 0 ? adjustedEbitda * 0.22 + 25000 : 25000;
    const adjustedNetIncome = adjustedEbitda - taxAndInterest;

    // Baseline calculation
    const baseGp = baseRevenue * (baseMargin / 100);
    const baseEbitda = baseGp - baseOpex;
    const baseTax = baseEbitda > 0 ? baseEbitda * 0.22 + 25000 : 25000;
    const baseNetIncome = baseEbitda - baseTax;

    const netIncomeDelta = adjustedNetIncome - baseNetIncome;
    const netMargin = adjustedRev > 0 ? (adjustedNetIncome / adjustedRev) * 100 : 0;

    return {
      adjustedRev,
      adjustedGrossProfit,
      adjustedCogs,
      adjustedOpex,
      adjustedEbitda,
      adjustedNetIncome,
      baseNetIncome,
      netIncomeDelta,
      netMargin,
    };
  }, [model, revDriverDelta, cogsDriverDelta, opexDriverDelta]);

  // Dynamic Heat Map Cell Background Color generator
  const getCellColorClass = (cell: SensitivityMatrixCell) => {
    let val = cell.netIncome;
    if (targetMetric === 'netMarginPercent') val = cell.netMarginPercent;
    if (targetMetric === 'ebitda') val = cell.ebitda;
    if (targetMetric === 'endingCash') val = cell.endingCash;

    if (targetMetric === 'netMarginPercent') {
      if (val < 0) return 'bg-rose-600/90 text-white font-bold';
      if (val < 5) return 'bg-rose-100 text-rose-900 border border-rose-200';
      if (val < 12) return 'bg-amber-100 text-amber-900 border border-amber-200';
      if (val < 20) return 'bg-emerald-100 text-emerald-900 border border-emerald-200';
      return 'bg-emerald-600 text-white font-bold';
    }

    // Default Net Income thresholds
    if (cell.netIncome < -100000) return 'bg-rose-700 text-white font-bold';
    if (cell.netIncome < 0) return 'bg-rose-200 text-rose-950 font-semibold border border-rose-300';
    if (cell.netIncome < 150000) return 'bg-amber-100 text-amber-950 font-semibold border border-amber-300';
    if (cell.netIncome < 400000) return 'bg-emerald-100 text-emerald-950 font-semibold border border-emerald-300';
    if (cell.netIncome < 750000) return 'bg-emerald-600 text-white font-bold';
    return 'bg-emerald-700 text-white font-bold';
  };

  const getCellDisplayValue = (cell: SensitivityMatrixCell) => {
    if (targetMetric === 'netMarginPercent') return `${cell.netMarginPercent.toFixed(1)}%`;
    if (targetMetric === 'ebitda') return formatCurrency(cell.ebitda);
    if (targetMetric === 'endingCash') return formatCurrency(cell.endingCash);
    return formatCurrency(cell.netIncome);
  };

  return (
    <div className="space-y-6">
      {/* 1. Simultaneous Multi-Driver Adjustment Bar */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <div className="p-1.5 bg-indigo-50 text-indigo-700 rounded-lg">
                <Sliders className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-bold text-slate-900">
                Simultaneous Multi-Driver Sensitivity Controls
              </h3>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Adjust Revenue, COGS, and OpEx concurrently to simulate multidimensional bottom-line stress
            </p>
          </div>

          {/* Quick Stress Test Presets */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[11px] font-semibold text-slate-500 mr-1">Stress Presets:</span>
            <button
              onClick={() => handleApplyPreset('stagflation')}
              className="px-2.5 py-1 text-[11px] font-bold rounded-lg bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200 transition-colors cursor-pointer"
            >
              Stagflation
            </button>
            <button
              onClick={() => handleApplyPreset('supply_shock')}
              className="px-2.5 py-1 text-[11px] font-bold rounded-lg bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200 transition-colors cursor-pointer"
            >
              Supply Shock
            </button>
            <button
              onClick={() => handleApplyPreset('efficiency')}
              className="px-2.5 py-1 text-[11px] font-bold rounded-lg bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200 transition-colors cursor-pointer"
            >
              Efficiency Lift
            </button>
            <button
              onClick={() => handleApplyPreset('boom')}
              className="px-2.5 py-1 text-[11px] font-bold rounded-lg bg-sky-50 text-sky-700 hover:bg-sky-100 border border-sky-200 transition-colors cursor-pointer"
            >
              Boom Cycle
            </button>
            <button
              onClick={() => handleApplyPreset('reset')}
              className="px-2 py-1 text-[11px] font-medium rounded-lg bg-slate-100 text-slate-600 hover:bg-slate-200 transition-colors cursor-pointer flex items-center gap-1"
              title="Reset sliders"
            >
              <RefreshCw className="w-3 h-3" />
              Reset
            </button>
          </div>
        </div>

        {/* 3 Simultaneous Sliders */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Driver 1: Revenue Shift */}
          <div className="space-y-2 bg-slate-50/80 p-3.5 rounded-xl border border-slate-200/80">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-800">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-indigo-600"></span>
                1. Revenue Trajectory
              </span>
              <span className={`font-bold font-mono ${revDriverDelta >= 0 ? 'text-indigo-600' : 'text-rose-600'}`}>
                {revDriverDelta >= 0 ? `+${revDriverDelta}%` : `${revDriverDelta}%`}
              </span>
            </div>
            <input
              type="range"
              min="-25"
              max="30"
              step="1"
              value={revDriverDelta}
              onChange={e => setRevDriverDelta(Number(e.target.value))}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
            />
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>-25% (Contraction)</span>
              <span>0% (Base)</span>
              <span>+30% (Growth)</span>
            </div>
          </div>

          {/* Driver 2: COGS & Direct Cost Shift */}
          <div className="space-y-2 bg-slate-50/80 p-3.5 rounded-xl border border-slate-200/80">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-800">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-amber-600"></span>
                2. COGS / Margin Squeeze
              </span>
              <span className={`font-bold font-mono ${cogsDriverDelta <= 0 ? 'text-emerald-600' : 'text-amber-600'}`}>
                {cogsDriverDelta > 0 ? `+${cogsDriverDelta}% pts cost` : `${cogsDriverDelta}% pts cost`}
              </span>
            </div>
            <input
              type="range"
              min="-8"
              max="15"
              step="1"
              value={cogsDriverDelta}
              onChange={e => setCogsDriverDelta(Number(e.target.value))}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-amber-600"
            />
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>-8% (Margin Gain)</span>
              <span>0% (Base)</span>
              <span>+15% (Severe Inflation)</span>
            </div>
          </div>

          {/* Driver 3: OpEx & Overhead Inflation */}
          <div className="space-y-2 bg-slate-50/80 p-3.5 rounded-xl border border-slate-200/80">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-800">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-violet-600"></span>
                3. OpEx & Payroll Inflation
              </span>
              <span className={`font-bold font-mono ${opexDriverDelta <= 0 ? 'text-emerald-600' : 'text-violet-600'}`}>
                {opexDriverDelta > 0 ? `+${opexDriverDelta}%` : `${opexDriverDelta}%`}
              </span>
            </div>
            <input
              type="range"
              min="-15"
              max="25"
              step="1"
              value={opexDriverDelta}
              onChange={e => setOpexDriverDelta(Number(e.target.value))}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-violet-600"
            />
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>-15% (Lean OpEx)</span>
              <span>0% (Base)</span>
              <span>+25% (High Expansion)</span>
            </div>
          </div>
        </div>

        {/* Live Combined Impact Strip */}
        <div className="p-4 bg-slate-900 text-white rounded-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">
              Combined Bottom-Line Net Income Impact
            </div>
            <div className="flex items-baseline gap-3">
              <span className="text-2xl font-black text-white">
                {formatCurrency(combinedImpact.adjustedNetIncome)}
              </span>
              <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                combinedImpact.netIncomeDelta >= 0 ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'
              }`}>
                {combinedImpact.netIncomeDelta >= 0 ? `+${formatCurrency(combinedImpact.netIncomeDelta)}` : `-${formatCurrency(Math.abs(combinedImpact.netIncomeDelta))}`} vs Base
              </span>
              <span className="text-xs text-slate-400">
                ({combinedImpact.netMargin.toFixed(1)}% Net Margin)
              </span>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3 text-center sm:text-right w-full sm:w-auto">
            <div className="bg-slate-800/80 px-3 py-2 rounded-lg">
              <span className="text-[10px] text-slate-400 block">Pro-Forma Rev</span>
              <span className="text-xs font-bold text-slate-200">{formatCurrency(combinedImpact.adjustedRev)}</span>
            </div>
            <div className="bg-slate-800/80 px-3 py-2 rounded-lg">
              <span className="text-[10px] text-slate-400 block">Pro-Forma EBITDA</span>
              <span className="text-xs font-bold text-slate-200">{formatCurrency(combinedImpact.adjustedEbitda)}</span>
            </div>
            <div className="bg-slate-800/80 px-3 py-2 rounded-lg">
              <span className="text-[10px] text-slate-400 block">Total OpEx</span>
              <span className="text-xs font-bold text-slate-200">{formatCurrency(combinedImpact.adjustedOpex)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Visual Heat Map Section */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-5">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-100 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <div className="p-1.5 bg-emerald-50 text-emerald-700 rounded-lg">
                <Grid className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-bold text-slate-900">
                Multi-Variable Sensitivity Heat Map (Bottom-Line Net Income Matrix)
              </h3>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Intersection matrix displaying how simultaneous driver variations affect overall profitability
            </p>
          </div>

          {/* Controls: Matrix Dimensions & Displayed Metric */}
          <div className="flex items-center gap-3 flex-wrap">
            {/* Axis Switcher */}
            <div className="flex items-center bg-slate-100 p-1 rounded-xl text-xs font-semibold">
              <button
                onClick={() => setMatrixMode('rev_vs_opex')}
                className={`px-3 py-1 rounded-lg transition-all ${
                  matrixMode === 'rev_vs_opex' ? 'bg-white text-slate-900 shadow-xs font-bold' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Revenue vs OpEx
              </button>
              <button
                onClick={() => setMatrixMode('rev_vs_cogs')}
                className={`px-3 py-1 rounded-lg transition-all ${
                  matrixMode === 'rev_vs_cogs' ? 'bg-white text-slate-900 shadow-xs font-bold' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Revenue vs Margin
              </button>
              <button
                onClick={() => setMatrixMode('price_vs_volume')}
                className={`px-3 py-1 rounded-lg transition-all ${
                  matrixMode === 'price_vs_volume' ? 'bg-white text-slate-900 shadow-xs font-bold' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Price vs Volume
              </button>
            </div>

            {/* Target Metric Selector */}
            <select
              value={targetMetric}
              onChange={e => setTargetMetric(e.target.value as any)}
              className="text-xs font-semibold bg-slate-50 border border-slate-200 rounded-xl px-3 py-1.5 text-slate-700 outline-hidden focus:ring-2 focus:ring-indigo-500 cursor-pointer"
            >
              <option value="netIncome">Show: Net Income ($)</option>
              <option value="netMarginPercent">Show: Net Margin (%)</option>
              <option value="ebitda">Show: EBITDA ($)</option>
              <option value="endingCash">Show: Ending Cash ($)</option>
            </select>
          </div>
        </div>

        {/* The Visual Heat Map Grid */}
        <div className="overflow-x-auto pb-2">
          <div className="min-w-[650px] inline-block w-full">
            {/* Top Column Header Label */}
            <div className="text-center font-bold text-xs text-slate-700 uppercase tracking-wider mb-2 flex items-center justify-center gap-2">
              <span>{matrixData.colAxisName} ({matrixData.colUnit})</span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-400 inline" />
            </div>

            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <th className="p-2 text-left text-[11px] font-bold text-slate-500 uppercase tracking-wider w-36 bg-slate-50/80 border border-slate-200 rounded-tl-lg">
                    {matrixData.rowAxisName} ({matrixData.rowUnit})
                  </th>
                  {matrixData.colValues.map((colVal, cIdx) => (
                    <th
                      key={cIdx}
                      className={`p-2.5 text-center text-xs font-bold border border-slate-200 ${
                        colVal === 0 ? 'bg-slate-200/80 text-slate-900 font-extrabold' : 'bg-slate-50 text-slate-700'
                      }`}
                    >
                      {colVal > 0 ? `+${colVal}${matrixData.colUnit}` : `${colVal}${matrixData.colUnit}`}
                      {colVal === 0 && <span className="block text-[9px] text-slate-500 font-normal uppercase">Base</span>}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrixData.grid.map((rowCells, rIdx) => {
                  const rowVal = matrixData.rowValues[rIdx];
                  const isBaseRow = rowVal === 0;

                  return (
                    <tr key={rIdx}>
                      {/* Row Header */}
                      <td
                        className={`p-2.5 text-xs font-bold border border-slate-200 whitespace-nowrap ${
                          isBaseRow ? 'bg-slate-200/80 text-slate-900 font-extrabold' : 'bg-slate-50 text-slate-700'
                        }`}
                      >
                        {rowVal > 0 ? `+${rowVal}${matrixData.rowUnit}` : `${rowVal}${matrixData.rowUnit}`}
                        {isBaseRow && <span className="ml-1.5 text-[9px] bg-slate-800 text-white px-1.5 py-0.5 rounded font-mono">BASE</span>}
                      </td>

                      {/* Heat Map Cells */}
                      {rowCells.map((cell, cIdx) => {
                        const isSelected = selectedCell === cell;
                        const isBaselineCell = cell.isBaseline;

                        return (
                          <td
                            key={cIdx}
                            onClick={() => setSelectedCell(cell)}
                            className={`p-3 text-center text-xs border border-slate-200/60 transition-all cursor-pointer relative group ${getCellColorClass(cell)} ${
                              isSelected ? 'ring-3 ring-indigo-600 ring-offset-1 z-10 scale-[1.03] shadow-md' : 'hover:scale-[1.02] hover:z-5'
                            }`}
                          >
                            <div className="relative">
                              <span>{getCellDisplayValue(cell)}</span>
                              {isBaselineCell && (
                                <span className="absolute -top-2.5 -right-2 text-[8px] bg-slate-900 text-white px-1 py-0.2 rounded font-mono shadow-xs">
                                  BASE
                                </span>
                              )}
                            </div>

                            {/* Floating Hover Tooltip */}
                            <div className="hidden group-hover:block absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2.5 bg-slate-900 text-white text-[11px] rounded-xl shadow-xl z-50 pointer-events-none text-left space-y-1">
                              <div className="font-bold text-white border-b border-slate-700 pb-1">
                                {matrixData.rowAxisName}: {cell.rowValue > 0 ? `+${cell.rowValue}` : cell.rowValue}{matrixData.rowUnit} | {matrixData.colAxisName}: {cell.colValue > 0 ? `+${cell.colValue}` : cell.colValue}{matrixData.colUnit}
                              </div>
                              <div className="flex justify-between text-slate-300">
                                <span>Revenue:</span> <span className="font-mono text-white">{formatCurrency(cell.revenue)}</span>
                              </div>
                              <div className="flex justify-between text-slate-300">
                                <span>Gross Profit:</span> <span className="font-mono text-white">{formatCurrency(cell.grossProfit)}</span>
                              </div>
                              <div className="flex justify-between text-slate-300">
                                <span>Total OpEx:</span> <span className="font-mono text-white">{formatCurrency(cell.opex)}</span>
                              </div>
                              <div className="flex justify-between text-slate-300">
                                <span>EBITDA:</span> <span className="font-mono text-white">{formatCurrency(cell.ebitda)}</span>
                              </div>
                              <div className="flex justify-between font-bold text-sky-400 pt-1 border-t border-slate-700">
                                <span>Net Income:</span> <span>{formatCurrency(cell.netIncome)} ({cell.netMarginPercent.toFixed(1)}%)</span>
                              </div>
                            </div>
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Heat Map Legend */}
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs pt-3 border-t border-slate-100">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-slate-500 font-semibold">Heat Legend:</span>
            <div className="flex items-center gap-1.5">
              <span className="w-3.5 h-3.5 rounded bg-rose-700 inline-block"></span>
              <span className="text-slate-600">&lt; -$100k (Heavy Loss)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3.5 h-3.5 rounded bg-rose-200 border border-rose-300 inline-block"></span>
              <span className="text-slate-600">$0 - $100k Loss</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3.5 h-3.5 rounded bg-amber-100 border border-amber-300 inline-block"></span>
              <span className="text-slate-600">$0 - $150k (Tight)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3.5 h-3.5 rounded bg-emerald-100 border border-emerald-300 inline-block"></span>
              <span className="text-slate-600">$150k - $400k (Healthy)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3.5 h-3.5 rounded bg-emerald-600 inline-block"></span>
              <span className="text-slate-600">&gt; $400k (Strong)</span>
            </div>
          </div>

          <span className="text-[11px] text-slate-400">
            Click any cell to inspect detailed scenario financial statements
          </span>
        </div>

        {/* Cell Detail Drill-Down Drawer (If selected) */}
        {selectedCell && (
          <div className="mt-4 p-4 bg-indigo-50/80 border border-indigo-200 rounded-xl space-y-3 animate-in fade-in duration-150">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-indigo-600" />
                <h4 className="text-xs font-bold text-indigo-950 uppercase tracking-wide">
                  Inspected Sensitivity Cell Scenario ({matrixData.rowAxisName}: {selectedCell.rowValue > 0 ? `+${selectedCell.rowValue}` : selectedCell.rowValue}{matrixData.rowUnit} / {matrixData.colAxisName}: {selectedCell.colValue > 0 ? `+${selectedCell.colValue}` : selectedCell.colValue}{matrixData.colUnit})
                </h4>
              </div>
              <button
                onClick={() => setSelectedCell(null)}
                className="text-xs font-semibold text-slate-500 hover:text-slate-800 cursor-pointer"
              >
                Close
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 text-xs">
              <div className="bg-white p-2.5 rounded-lg border border-indigo-100 shadow-2xs">
                <span className="text-[10px] text-slate-500 block">Pro-Forma Rev</span>
                <span className="font-bold text-slate-900 font-mono">{formatCurrency(selectedCell.revenue)}</span>
              </div>
              <div className="bg-white p-2.5 rounded-lg border border-indigo-100 shadow-2xs">
                <span className="text-[10px] text-slate-500 block">COGS</span>
                <span className="font-bold text-slate-900 font-mono">{formatCurrency(selectedCell.cogs)}</span>
              </div>
              <div className="bg-white p-2.5 rounded-lg border border-indigo-100 shadow-2xs">
                <span className="text-[10px] text-slate-500 block">Gross Profit</span>
                <span className="font-bold text-emerald-700 font-mono">{formatCurrency(selectedCell.grossProfit)}</span>
              </div>
              <div className="bg-white p-2.5 rounded-lg border border-indigo-100 shadow-2xs">
                <span className="text-[10px] text-slate-500 block">Total OpEx</span>
                <span className="font-bold text-slate-900 font-mono">{formatCurrency(selectedCell.opex)}</span>
              </div>
              <div className="bg-white p-2.5 rounded-lg border border-indigo-100 shadow-2xs">
                <span className="text-[10px] text-slate-500 block">EBITDA</span>
                <span className="font-bold text-indigo-700 font-mono">{formatCurrency(selectedCell.ebitda)}</span>
              </div>
              <div className="bg-white p-2.5 rounded-lg border border-indigo-100 shadow-2xs">
                <span className="text-[10px] text-slate-500 block">Net Income</span>
                <span className={`font-bold font-mono ${selectedCell.netIncome >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                  {formatCurrency(selectedCell.netIncome)} ({selectedCell.netMarginPercent.toFixed(1)}%)
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
