import React, { useState, useMemo } from 'react';
import {
  Calendar,
  DollarSign,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle2,
  Sliders,
  Sparkles,
  Layers,
  ArrowUpRight,
  ArrowDownRight,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts';
import { FinancialModel, ScenarioDrivers, WeeklyCashForecastItem, MonthlyCashForecastItem } from '../../types';
import { ForecastingEngine } from '../../services/forecastingEngine';

interface CashFlowForecastScheduleProps {
  model: FinancialModel;
  drivers?: ScenarioDrivers;
}

export const CashFlowForecastSchedule: React.FC<CashFlowForecastScheduleProps> = ({
  model,
  drivers,
}) => {
  const client = model.client;

  // View frequency: 'weekly' (13-week) vs 'monthly' (12-month)
  const [viewMode, setViewMode] = useState<'weekly' | 'monthly'>('weekly');

  // Tuning knobs for cash forecast
  const [minCashBuffer, setMinCashBuffer] = useState<number>(150000);
  const [dsoSpeedDelta, setDsoSpeedDelta] = useState<number>(0);
  const [plannedCapexWeek, setPlannedCapexWeek] = useState<number>(6);
  const [plannedCapexAmount, setPlannedCapexAmount] = useState<number>(25000);
  const [showDetailedBreakdown, setShowDetailedBreakdown] = useState<boolean>(true);

  // 13-Week Data
  const weeklyForecast = useMemo(() => {
    return ForecastingEngine.generate13WeekCashForecast(model, {
      revenueGrowthDelta: drivers?.revenueGrowthRateDelta || 0,
      dsoCollectionSpeed: dsoSpeedDelta,
      plannedCapexWeek,
      plannedCapexAmount,
      minCashBuffer,
    });
  }, [model, drivers, dsoSpeedDelta, plannedCapexWeek, plannedCapexAmount, minCashBuffer]);

  // 12-Month Data
  const monthlyForecast = useMemo(() => {
    return ForecastingEngine.generate12MonthCashForecast(model, drivers);
  }, [model, drivers]);

  const formatCurrency = (val: number) => {
    if (Math.abs(val) >= 1_000_000) {
      return `${client.currencySymbol}${(val / 1_000_000).toFixed(2)}M`;
    }
    return `${client.currencySymbol}${(val / 1_000).toFixed(0)}k`;
  };

  const formatExactCurrency = (val: number) => {
    return `${client.currencySymbol}${val.toLocaleString()}`;
  };

  // Weekly Chart Data
  const weeklyChartData = weeklyForecast.weeks.map(w => ({
    week: `W${w.weekNumber}`,
    startDate: w.startDate,
    EndingCash: w.endingCash,
    TotalInflows: w.totalInflows,
    TotalOutflows: w.totalOutflows,
    NetCashFlow: w.netCashFlow,
    MinSafeBuffer: minCashBuffer,
  }));

  // Monthly Chart Data
  const monthlyChartData = monthlyForecast.months.map(m => ({
    month: m.monthLabel.split(' ')[0],
    fullMonth: m.monthLabel,
    EndingCash: m.endingCash,
    OperatingInflows: m.operatingCashInflows,
    OperatingOutflows: m.operatingCashOutflows,
    NetCashFlow: m.netCashFlow,
  }));

  return (
    <div className="space-y-6">
      {/* 1. Top Bar: Frequency Toggle & Knobs */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <div className="p-1.5 bg-sky-50 text-sky-700 rounded-lg">
                <Calendar className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-bold text-slate-900">
                Liquidity & Cash Flow Horizon Forecast
              </h3>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Simulate granular 13-week operational cash receipts/disbursements and 12-month forward liquidity
            </p>
          </div>

          {/* Timeframe Switcher */}
          <div className="flex items-center bg-slate-100 p-1 rounded-xl text-xs font-semibold self-start sm:self-auto">
            <button
              onClick={() => setViewMode('weekly')}
              className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
                viewMode === 'weekly' ? 'bg-white text-slate-900 shadow-xs font-bold' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-sky-500"></span>
              13-Week Rolling Cash
            </button>
            <button
              onClick={() => setViewMode('monthly')}
              className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
                viewMode === 'monthly' ? 'bg-white text-slate-900 shadow-xs font-bold' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-indigo-500"></span>
              12-Month Pro-Forma Cash
            </button>
          </div>
        </div>

        {/* Dynamic Knobs (Buffer & DSO) */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs font-semibold text-slate-700">
              <span>Minimum Safe Cash Buffer:</span>
              <span className="font-bold text-slate-900 font-mono">{formatCurrency(minCashBuffer)}</span>
            </div>
            <input
              type="range"
              min="50000"
              max="400000"
              step="25000"
              value={minCashBuffer}
              onChange={e => setMinCashBuffer(Number(e.target.value))}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-sky-600"
            />
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>$50k (Tight)</span>
              <span>$400k (Conservative)</span>
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex justify-between text-xs font-semibold text-slate-700">
              <span>AR Collection Acceleration (DSO):</span>
              <span className={`font-bold font-mono ${dsoSpeedDelta >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                {dsoSpeedDelta > 0 ? `+${dsoSpeedDelta}d faster` : dsoSpeedDelta < 0 ? `${Math.abs(dsoSpeedDelta)}d slower` : 'Baseline'}
              </span>
            </div>
            <input
              type="range"
              min="-10"
              max="15"
              step="1"
              value={dsoSpeedDelta}
              onChange={e => setDsoSpeedDelta(Number(e.target.value))}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-emerald-600"
            />
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>-10d (Slower)</span>
              <span>Baseline</span>
              <span>+15d (Faster)</span>
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex justify-between text-xs font-semibold text-slate-700">
              <span>Planned CapEx (Week {plannedCapexWeek}):</span>
              <span className="font-bold text-rose-600 font-mono">{formatCurrency(plannedCapexAmount)}</span>
            </div>
            <input
              type="range"
              min="0"
              max="100000"
              step="5000"
              value={plannedCapexAmount}
              onChange={e => setPlannedCapexAmount(Number(e.target.value))}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-rose-600"
            />
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>$0</span>
              <span>$100k Outlay</span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. WEEKLY 13-WEEK VIEW */}
      {viewMode === 'weekly' && (
        <div className="space-y-6">
          {/* Top KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                Current Opening Cash
              </span>
              <div className="text-xl font-black text-slate-900 mt-1">
                {formatCurrency(weeklyForecast.summary.initialCash)}
              </div>
              <span className="text-[11px] text-slate-500 font-medium">As of today</span>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                13-Week Ending Cash
              </span>
              <div className={`text-xl font-black mt-1 ${weeklyForecast.summary.endingCash >= weeklyForecast.summary.initialCash ? 'text-emerald-600' : 'text-slate-900'}`}>
                {formatCurrency(weeklyForecast.summary.endingCash)}
              </div>
              <span className="text-[11px] text-slate-500 font-medium">
                {weeklyForecast.summary.netCashGeneration13W >= 0 ? '+' : ''}
                {formatCurrency(weeklyForecast.summary.netCashGeneration13W)} 13W net delta
              </span>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                Trough Cash Low-Point
              </span>
              <div className={`text-xl font-black mt-1 ${weeklyForecast.summary.troughCash < minCashBuffer ? 'text-rose-600' : 'text-amber-600'}`}>
                {formatCurrency(weeklyForecast.summary.troughCash)}
              </div>
              <span className="text-[11px] text-slate-500 font-medium">
                Occurs in Week {weeklyForecast.summary.troughWeekIndex}
              </span>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                Safety Buffer Status
              </span>
              <div className="flex items-center gap-2 mt-1">
                {weeklyForecast.summary.weeksBelowThreshold === 0 ? (
                  <>
                    <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                    <span className="text-sm font-bold text-emerald-700">Healthy Buffer</span>
                  </>
                ) : (
                  <>
                    <AlertTriangle className="w-5 h-5 text-rose-600" />
                    <span className="text-sm font-bold text-rose-700">{weeklyForecast.summary.weeksBelowThreshold} Weeks Below Min</span>
                  </>
                )}
              </div>
              <span className="text-[11px] text-slate-500 font-medium">
                Min threshold: {formatCurrency(minCashBuffer)}
              </span>
            </div>
          </div>

          {/* 13-Week Cash Trajectory Chart */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-bold text-slate-900">
                13-Week Rolling Cash Liquidity Trajectory
              </h4>
              <div className="flex items-center gap-3 text-xs">
                <span className="flex items-center gap-1 text-slate-600">
                  <span className="w-3 h-3 rounded bg-sky-500 inline-block"></span> Ending Cash
                </span>
                <span className="flex items-center gap-1 text-slate-600">
                  <span className="w-3 h-0.5 bg-rose-500 inline-block border-t border-dashed border-rose-500"></span> Min Safe Buffer
                </span>
              </div>
            </div>

            <div className="h-64 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={weeklyChartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="week" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} tickFormatter={v => `${client.currencySymbol}${(v / 1000).toFixed(0)}k`} />
                  <Tooltip
                    formatter={(val: any, name: string) => [
                      `${client.currencySymbol}${Number(val).toLocaleString()}`,
                      name === 'EndingCash' ? 'Ending Cash' : name === 'TotalInflows' ? 'Weekly Inflow' : name === 'TotalOutflows' ? 'Weekly Outflow' : name
                    ]}
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', color: '#fff', fontSize: '12px' }}
                  />
                  <ReferenceLine y={minCashBuffer} stroke="#ef4444" strokeDasharray="4 4" label={{ value: 'Min Buffer', fill: '#ef4444', fontSize: 10, position: 'insideTopRight' }} />
                  <Area type="monotone" dataKey="EndingCash" stroke="#0ea5e9" fill="#0ea5e9" fillOpacity={0.15} strokeWidth={2.5} />
                  <Bar dataKey="TotalInflows" fill="#10b981" barSize={8} opacity={0.6} radius={[2, 2, 0, 0]} />
                  <Bar dataKey="TotalOutflows" fill="#f43f5e" barSize={8} opacity={0.6} radius={[2, 2, 0, 0]} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 13-Week Detailed Schedule Table */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <Layers className="w-4 h-4 text-sky-600" />
                13-Week Direct Cash Flow Schedule Table
              </h4>
              <button
                onClick={() => setShowDetailedBreakdown(!showDetailedBreakdown)}
                className="text-xs font-semibold text-slate-600 hover:text-slate-900 flex items-center gap-1 cursor-pointer"
              >
                {showDetailedBreakdown ? (
                  <>
                    <ChevronUp className="w-3.5 h-3.5" /> Collapse Line Items
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-3.5 h-3.5" /> Expand All Line Items
                  </>
                )}
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left border-collapse min-w-[900px]">
                <thead>
                  <tr className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                    <th className="p-2.5 sticky left-0 bg-slate-100 z-10 w-52">Line Item</th>
                    {weeklyForecast.weeks.map(w => (
                      <th key={w.weekNumber} className="p-2 text-right font-mono min-w-[70px]">
                        <div>{w.weekLabel.split(' ')[0]}</div>
                        <div className="text-[10px] text-slate-400 font-normal">{w.startDate}</div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {/* Beginning Cash */}
                  <tr className="bg-slate-50/50 font-bold text-slate-900">
                    <td className="p-2.5 sticky left-0 bg-slate-50/90 z-10">Beginning Cash</td>
                    {weeklyForecast.weeks.map(w => (
                      <td key={w.weekNumber} className="p-2 text-right font-mono text-slate-700">
                        {formatCurrency(w.beginningCash)}
                      </td>
                    ))}
                  </tr>

                  {/* Total Inflows Row */}
                  <tr className="bg-emerald-50/40 font-bold text-emerald-950">
                    <td className="p-2.5 sticky left-0 bg-emerald-50/90 z-10">Total Cash Inflows (+)</td>
                    {weeklyForecast.weeks.map(w => (
                      <td key={w.weekNumber} className="p-2 text-right font-mono text-emerald-700">
                        +{formatCurrency(w.totalInflows)}
                      </td>
                    ))}
                  </tr>

                  {showDetailedBreakdown && (
                    <>
                      <tr className="text-slate-600 text-[11px]">
                        <td className="p-2 pl-6 sticky left-0 bg-white z-10">AR Collections</td>
                        {weeklyForecast.weeks.map(w => (
                          <td key={w.weekNumber} className="p-2 text-right font-mono text-slate-600">
                            {formatCurrency(w.arCollections)}
                          </td>
                        ))}
                      </tr>
                      <tr className="text-slate-600 text-[11px]">
                        <td className="p-2 pl-6 sticky left-0 bg-white z-10">Cash Sales / Subscriptions</td>
                        {weeklyForecast.weeks.map(w => (
                          <td key={w.weekNumber} className="p-2 text-right font-mono text-slate-600">
                            {formatCurrency(w.cashSales)}
                          </td>
                        ))}
                      </tr>
                    </>
                  )}

                  {/* Total Outflows Row */}
                  <tr className="bg-rose-50/40 font-bold text-rose-950">
                    <td className="p-2.5 sticky left-0 bg-rose-50/90 z-10">Total Cash Outflows (-)</td>
                    {weeklyForecast.weeks.map(w => (
                      <td key={w.weekNumber} className="p-2 text-right font-mono text-rose-700">
                        -{formatCurrency(w.totalOutflows)}
                      </td>
                    ))}
                  </tr>

                  {showDetailedBreakdown && (
                    <>
                      <tr className="text-slate-600 text-[11px]">
                        <td className="p-2 pl-6 sticky left-0 bg-white z-10">Payroll & Benefits</td>
                        {weeklyForecast.weeks.map(w => (
                          <td key={w.weekNumber} className={`p-2 text-right font-mono ${w.payrollAndBenefits > 30000 ? 'font-bold text-slate-900' : 'text-slate-600'}`}>
                            {formatCurrency(w.payrollAndBenefits)}
                          </td>
                        ))}
                      </tr>
                      <tr className="text-slate-600 text-[11px]">
                        <td className="p-2 pl-6 sticky left-0 bg-white z-10">COGS / Supplier Payments</td>
                        {weeklyForecast.weeks.map(w => (
                          <td key={w.weekNumber} className="p-2 text-right font-mono text-slate-600">
                            {formatCurrency(w.cogsSupplierPayments)}
                          </td>
                        ))}
                      </tr>
                      <tr className="text-slate-600 text-[11px]">
                        <td className="p-2 pl-6 sticky left-0 bg-white z-10">Rent & Facilities</td>
                        {weeklyForecast.weeks.map(w => (
                          <td key={w.weekNumber} className="p-2 text-right font-mono text-slate-600">
                            {formatCurrency(w.rentAndFacilities)}
                          </td>
                        ))}
                      </tr>
                      <tr className="text-slate-600 text-[11px]">
                        <td className="p-2 pl-6 sticky left-0 bg-white z-10">Tax & Statutory</td>
                        {weeklyForecast.weeks.map(w => (
                          <td key={w.weekNumber} className="p-2 text-right font-mono text-slate-600">
                            {formatCurrency(w.taxAndStatutory)}
                          </td>
                        ))}
                      </tr>
                      <tr className="text-slate-600 text-[11px]">
                        <td className="p-2 pl-6 sticky left-0 bg-white z-10">CapEx Outlays</td>
                        {weeklyForecast.weeks.map(w => (
                          <td key={w.weekNumber} className={`p-2 text-right font-mono ${w.capexOutlays > 0 ? 'text-rose-600 font-bold' : 'text-slate-400'}`}>
                            {formatCurrency(w.capexOutlays)}
                          </td>
                        ))}
                      </tr>
                    </>
                  )}

                  {/* Net Weekly Cash Flow */}
                  <tr className="bg-slate-100 font-bold border-t border-slate-300">
                    <td className="p-2.5 sticky left-0 bg-slate-100 z-10">Net Weekly Cash Generation</td>
                    {weeklyForecast.weeks.map(w => (
                      <td
                        key={w.weekNumber}
                        className={`p-2 text-right font-mono font-black ${w.netCashFlow >= 0 ? 'text-emerald-700' : 'text-rose-600'}`}
                      >
                        {w.netCashFlow >= 0 ? `+${formatCurrency(w.netCashFlow)}` : `-${formatCurrency(Math.abs(w.netCashFlow))}`}
                      </td>
                    ))}
                  </tr>

                  {/* Ending Cash Balance */}
                  <tr className="bg-slate-900 text-white font-extrabold border-t border-slate-800">
                    <td className="p-3 sticky left-0 bg-slate-900 z-10 text-white flex items-center justify-between">
                      <span>Ending Cash Balance</span>
                    </td>
                    {weeklyForecast.weeks.map(w => (
                      <td
                        key={w.weekNumber}
                        className={`p-3 text-right font-mono text-xs ${
                          w.isBelowThreshold ? 'text-rose-300 bg-rose-950/60 font-black' : 'text-emerald-300'
                        }`}
                      >
                        {formatCurrency(w.endingCash)}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* 3. MONTHLY 12-MONTH VIEW */}
      {viewMode === 'monthly' && (
        <div className="space-y-6">
          {/* Top KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                Current Cash Balance
              </span>
              <div className="text-xl font-black text-slate-900 mt-1">
                {formatCurrency(monthlyForecast.summary.beginningCash)}
              </div>
              <span className="text-[11px] text-slate-500 font-medium">Opening Balance</span>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                12M Forward Ending Cash
              </span>
              <div className={`text-xl font-black mt-1 ${monthlyForecast.summary.endingCash >= monthlyForecast.summary.beginningCash ? 'text-emerald-600' : 'text-slate-900'}`}>
                {formatCurrency(monthlyForecast.summary.endingCash)}
              </div>
              <span className="text-[11px] text-slate-500 font-medium">
                {monthlyForecast.summary.totalNetCashFlow >= 0 ? '+' : ''}
                {formatCurrency(monthlyForecast.summary.totalNetCashFlow)} 12M net change
              </span>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                Lowest Cash Point
              </span>
              <div className="text-xl font-black text-amber-600 mt-1">
                {formatCurrency(monthlyForecast.summary.minCashValue)}
              </div>
              <span className="text-[11px] text-slate-500 font-medium">
                Occurs in {monthlyForecast.summary.minCashMonth}
              </span>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                Forward Cash Runway
              </span>
              <div className="text-xl font-black text-indigo-600 mt-1">
                {monthlyForecast.summary.cashRunwayMonths >= 24 ? '24+ Months' : `${monthlyForecast.summary.cashRunwayMonths.toFixed(1)} Months`}
              </div>
              <span className="text-[11px] text-slate-500 font-medium">
                Unencumbered runway
              </span>
            </div>
          </div>

          {/* 12-Month Cash Chart */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-4">
            <h4 className="text-sm font-bold text-slate-900">
              12-Month Pro-Forma Forward Cash Trajectory
            </h4>

            <div className="h-64 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={monthlyChartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="fullMonth" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} tickFormatter={v => `${client.currencySymbol}${(v / 1000).toFixed(0)}k`} />
                  <Tooltip
                    formatter={(val: any) => [`${client.currencySymbol}${Number(val).toLocaleString()}`, '']}
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', color: '#fff', fontSize: '12px' }}
                  />
                  <Legend wrapperStyle={{ fontSize: '12px' }} />
                  <Area type="monotone" dataKey="EndingCash" name="Ending Cash" stroke="#4f46e5" fill="#4f46e5" fillOpacity={0.12} strokeWidth={2.5} />
                  <Bar dataKey="OperatingInflows" name="Operating Inflows" fill="#10b981" barSize={10} radius={[2, 2, 0, 0]} />
                  <Bar dataKey="OperatingOutflows" name="Operating Outflows" fill="#f43f5e" barSize={10} radius={[2, 2, 0, 0]} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 12-Month Cash Statement Table */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="p-4 bg-slate-50 border-b border-slate-200">
              <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                12-Month Forward Pro-Forma Cash Statement
              </h4>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left border-collapse min-w-[850px]">
                <thead>
                  <tr className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                    <th className="p-2.5 sticky left-0 bg-slate-100 z-10 w-48">Month</th>
                    {monthlyForecast.months.map(m => (
                      <th key={m.monthIndex} className="p-2 text-right font-mono">
                        {m.monthLabel.split(' ')[0]}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  <tr className="font-semibold text-slate-800">
                    <td className="p-2.5 sticky left-0 bg-white z-10">Beginning Cash</td>
                    {monthlyForecast.months.map(m => (
                      <td key={m.monthIndex} className="p-2 text-right font-mono text-slate-600">
                        {formatCurrency(m.beginningCash)}
                      </td>
                    ))}
                  </tr>
                  <tr className="text-emerald-800 font-semibold bg-emerald-50/30">
                    <td className="p-2.5 sticky left-0 bg-emerald-50/90 z-10">Operating Cash Inflows</td>
                    {monthlyForecast.months.map(m => (
                      <td key={m.monthIndex} className="p-2 text-right font-mono text-emerald-700">
                        +{formatCurrency(m.operatingCashInflows)}
                      </td>
                    ))}
                  </tr>
                  <tr className="text-rose-800 font-semibold bg-rose-50/30">
                    <td className="p-2.5 sticky left-0 bg-rose-50/90 z-10">Operating Cash Outflows</td>
                    {monthlyForecast.months.map(m => (
                      <td key={m.monthIndex} className="p-2 text-right font-mono text-rose-700">
                        -{formatCurrency(m.operatingCashOutflows)}
                      </td>
                    ))}
                  </tr>
                  <tr className="text-slate-600">
                    <td className="p-2.5 sticky left-0 bg-white z-10">CapEx / Investing</td>
                    {monthlyForecast.months.map(m => (
                      <td key={m.monthIndex} className="p-2 text-right font-mono text-slate-600">
                        -{formatCurrency(m.capexAndInvesting)}
                      </td>
                    ))}
                  </tr>
                  <tr className="text-slate-600">
                    <td className="p-2.5 sticky left-0 bg-white z-10">Tax & Financing</td>
                    {monthlyForecast.months.map(m => (
                      <td key={m.monthIndex} className="p-2 text-right font-mono text-slate-600">
                        -{formatCurrency(m.taxPayments + m.financingAndDebt)}
                      </td>
                    ))}
                  </tr>
                  <tr className="bg-slate-100 font-bold">
                    <td className="p-2.5 sticky left-0 bg-slate-100 z-10">Net Monthly Cash Flow</td>
                    {monthlyForecast.months.map(m => (
                      <td
                        key={m.monthIndex}
                        className={`p-2 text-right font-mono font-bold ${m.netCashFlow >= 0 ? 'text-emerald-700' : 'text-rose-600'}`}
                      >
                        {m.netCashFlow >= 0 ? `+${formatCurrency(m.netCashFlow)}` : `-${formatCurrency(Math.abs(m.netCashFlow))}`}
                      </td>
                    ))}
                  </tr>
                  <tr className="bg-slate-900 text-white font-extrabold">
                    <td className="p-2.5 sticky left-0 bg-slate-900 z-10 text-white">Ending Cash Balance</td>
                    {monthlyForecast.months.map(m => (
                      <td key={m.monthIndex} className="p-2 text-right font-mono text-emerald-300">
                        {formatCurrency(m.endingCash)}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
