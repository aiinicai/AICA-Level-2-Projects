import React, { useState } from 'react';
import {
  TrendingUp,
  Calendar,
  DollarSign,
  Sparkles,
  Layers,
  ArrowRight,
  Shield,
  Download,
  Sliders,
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
} from 'recharts';
import { FinancialModel, ScenarioResult, ClientProfile, BudgetForecastBasisConfig } from '../../types';
import { ForecastingEngine } from '../../services/forecastingEngine';
import { FirmReportHeader, FirmReportFooter } from '../common/FirmHeaderFooter';
import { BudgetForecastBasisView } from './BudgetForecastBasisView';

interface ForecastingViewProps {
  model: FinancialModel;
  firmName?: string;
}

export const ForecastingView: React.FC<ForecastingViewProps> = ({
  model,
  firmName = 'Jasleen Daswal & Associates',
}) => {
  const [activeTab, setActiveTab] = useState<'schedule' | 'basis_config'>('schedule');

  const [basisConfig, setBasisConfig] = useState<BudgetForecastBasisConfig>(() => {
    return model.budgetBasisConfig || ForecastingEngine.getDefaultBasisConfig(model.client);
  });

  const client = model.client;
  const forecastResult: ScenarioResult = ForecastingEngine.project12MonthsWithBasis(model, basisConfig);

  const formatCurrency = (val: number) => {
    if (Math.abs(val) >= 1_000_000) {
      return `${client.currencySymbol}${(val / 1_000_000).toFixed(2)}M`;
    }
    return `${client.currencySymbol}${(val / 1_000).toFixed(0)}k`;
  };

  // Combine historical and forecasted data for continuous trajectory
  const trajectoryChartData = [
    ...model.historicalMonthly.map(m => ({
      period: m.periodLabel,
      type: 'Actual',
      HistoricalRevenue: m.revenue,
      HistoricalEbitda: m.ebitda,
      ForecastRevenue: null,
      ForecastEbitda: null,
      CashBalance: m.cashAndEquivalents,
    })),
    ...forecastResult.monthlyProjections.map(m => ({
      period: m.month,
      type: 'Forecast',
      HistoricalRevenue: null,
      HistoricalEbitda: null,
      ForecastRevenue: m.revenue,
      ForecastEbitda: m.ebitda,
      CashBalance: m.cashBalance,
    })),
  ];

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <FirmReportHeader client={client} reportTitle="12-Month Pro-Forma Rolling Forecast & Strategic Budget" firmName={firmName} />

      {/* Main Tab Switcher */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-3 flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab('schedule')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
              activeTab === 'schedule'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'
            }`}
          >
            <TrendingUp className="w-4 h-4" />
            12-Month Forecast Schedule & Trajectory
          </button>

          <button
            onClick={() => setActiveTab('basis_config')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
              activeTab === 'basis_config'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'
            }`}
          >
            <Sliders className="w-4 h-4 text-emerald-400" />
            Budget & Forecast Basis Settings
            <span className="text-[10px] bg-emerald-100 text-emerald-800 px-1.5 py-0.2 rounded-full font-extrabold">DRIVERS</span>
          </button>
        </div>

        <div className="text-xs text-slate-500 font-medium">
          Driver Method: <span className="font-bold text-slate-800 capitalize">{basisConfig.revenueBasis.method.replace('_', ' ')}</span>
        </div>
      </div>

      {activeTab === 'basis_config' ? (
        <BudgetForecastBasisView
          client={client}
          model={model}
          currentConfig={basisConfig}
          onUpdateConfig={(updated) => setBasisConfig(updated)}
          onApplyAndRecalculate={() => setActiveTab('schedule')}
        />
      ) : (
        <>
          {/* Top Strip Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="card-geometric p-4 hover:border-slate-300 transition-colors">
              <span className="metric-label">
                12M Projected Revenue
              </span>
              <div className="metric-value mt-2">
                {formatCurrency(forecastResult.annualRevenue)}
              </div>
              <div className="text-[10px] text-sky-700 font-semibold mt-2">
                Basis: {basisConfig.revenueBasis.method === 'growth_rate' ? `+${basisConfig.revenueBasis.growthRatePercent}% Annual Rate` : basisConfig.revenueBasis.method.replace('_', ' ').toUpperCase()}
              </div>
            </div>

            <div className="card-geometric p-4 hover:border-slate-300 transition-colors">
              <span className="metric-label">
                12M Projected EBITDA
              </span>
              <div className="metric-value mt-2">
                {formatCurrency(forecastResult.annualEbitda)}
              </div>
              <div className="text-[10px] text-slate-500 font-medium mt-2">
                {((forecastResult.annualEbitda / (forecastResult.annualRevenue || 1)) * 100).toFixed(1)}% Forward Margin
              </div>
            </div>

            <div className="card-geometric p-4 hover:border-slate-300 transition-colors">
              <span className="metric-label">
                12M Net Cash Flow
              </span>
              <div className="metric-value mt-2">
                {formatCurrency(forecastResult.monthlyProjections.reduce((sum, m) => sum + m.netCashFlow, 0))}
              </div>
              <div className="text-[10px] text-emerald-700 font-semibold mt-2">
                Working Capital: {basisConfig.workingCapitalBasis.targetDsoDays}d DSO
              </div>
            </div>

            <div className="card-geometric p-4 hover:border-slate-300 transition-colors">
              <span className="metric-label">
                Projected Ending Cash (12M)
              </span>
              <div className="metric-value mt-2">
                {formatCurrency(forecastResult.endingCash)}
              </div>
              <div className="text-[10px] text-slate-500 font-medium mt-2">
                Min Cushion: {basisConfig.workingCapitalBasis.minimumCashReserveMonths} Months OPEX
              </div>
            </div>
          </div>

          {/* Chart: Historical Actuals to 12-Month Forward Forecast */}
          <div className="card-geometric p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
              <div>
                <h4 className="text-sm font-bold text-slate-900">
                  12-Month Rolling Pro-Forma Revenue & EBITDA Trajectory
                </h4>
                <p className="text-xs text-slate-500">
                  Solid lines represent Historical Actuals; dashed lines represent Rolling 12-Month Projections computed from active drivers.
                </p>
              </div>
              <button
                onClick={() => setActiveTab('basis_config')}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold transition-colors"
              >
                <Sliders className="w-3.5 h-3.5" /> Edit Driver Basis
              </button>
            </div>

            <div className="h-72 w-full pt-4">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trajectoryChartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="period" stroke="#94a3b8" fontSize={10} tickLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} tickFormatter={v => `${client.currencySymbol}${(v / 1000).toFixed(0)}k`} />
                  <Tooltip
                    formatter={(value: any) => [value ? `${client.currencySymbol}${Number(value).toLocaleString()}` : '-', '']}
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                  <Line type="monotone" dataKey="HistoricalRevenue" stroke="#0284C7" strokeWidth={2} name="Historical Revenue" />
                  <Line type="monotone" dataKey="ForecastRevenue" stroke="#0284C7" strokeWidth={2} strokeDasharray="4 4" name="Projected Revenue" />
                  <Line type="monotone" dataKey="HistoricalEbitda" stroke="#64748B" strokeWidth={2} name="Historical EBITDA" />
                  <Line type="monotone" dataKey="ForecastEbitda" stroke="#64748B" strokeWidth={2} strokeDasharray="4 4" name="Projected EBITDA" />
                  <Line type="monotone" dataKey="CashBalance" stroke="#10B981" strokeWidth={2} name="Cash Balance" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Pro-Forma 12-Month Monthly Projection Table */}
          <div className="card-geometric overflow-hidden">
            <div className="p-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                Pro-Forma Monthly Forecast Schedule
              </h4>
              <span className="pill pill-info text-[10px]">Rolling 12M Pro-Forma</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider font-semibold text-[10px] border-b border-slate-200/80">
                  <tr>
                    <th className="px-4 py-2.5">Forecast Period</th>
                    <th className="px-4 py-2.5 text-right">Projected Revenue</th>
                    <th className="px-4 py-2.5 text-right">Gross Margin</th>
                    <th className="px-4 py-2.5 text-right">EBITDA</th>
                    <th className="px-4 py-2.5 text-right">EBITDA %</th>
                    <th className="px-4 py-2.5 text-right">Monthly Cash Flow</th>
                    <th className="px-4 py-2.5 text-right">Ending Cash Reserve</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {forecastResult.monthlyProjections.map((m, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-4 py-2.5 font-semibold text-slate-900">{m.month}</td>
                      <td className="px-4 py-2.5 text-right font-medium text-slate-700">{formatCurrency(m.revenue)}</td>
                      <td className="px-4 py-2.5 text-right font-medium text-slate-700">{formatCurrency(m.grossProfit)}</td>
                      <td className="px-4 py-2.5 text-right font-semibold text-sky-700">{formatCurrency(m.ebitda)}</td>
                      <td className="px-4 py-2.5 text-right font-medium text-slate-700">{((m.ebitda / m.revenue) * 100).toFixed(1)}%</td>
                      <td className="px-4 py-2.5 text-right font-medium text-emerald-700">{formatCurrency(m.netCashFlow)}</td>
                      <td className="px-4 py-2.5 text-right font-bold text-slate-900">{formatCurrency(m.cashBalance)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      <FirmReportFooter firmName={firmName} />
    </div>
  );
};

