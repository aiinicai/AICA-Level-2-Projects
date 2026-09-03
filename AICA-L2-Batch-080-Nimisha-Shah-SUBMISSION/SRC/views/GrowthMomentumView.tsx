import React from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  Scissors, 
  AlertTriangle, 
  CheckCircle2, 
  ArrowUpRight, 
  ArrowDownRight,
  Info,
  Calendar
} from 'lucide-react';
import { ListedCompany, CurrencyCode, UnitScale } from '../types/financial';
import { getResolvedCompanyFinancials } from '../data/listedCompaniesDataset';
import { formatFinancialValue, getCurrencyUnitLabel } from '../utils/formatUtils';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from 'recharts';

interface GrowthMomentumViewProps {
  company: ListedCompany;
  selectedPeriod?: string;
  currency?: CurrencyCode;
  scale?: UnitScale;
}

export const GrowthMomentumView: React.FC<GrowthMomentumViewProps> = ({ 
  company,
  selectedPeriod = 'latest',
  currency = 'INR',
  scale = 'crores'
}) => {
  const fin = getResolvedCompanyFinancials(company, selectedPeriod);
  const isAdverse = fin.hasOperatingScissors;

  const formatVal = (val: number) => formatFinancialValue(val, currency, scale);

  const comparisonData = [
    {
      metric: 'YoY Growth Rate %',
      SalesGrowth: fin.salesGrowthYoY,
      ProfitGrowth: fin.netProfitGrowthYoY
    }
  ];

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Operating Scissors Diagnostic Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Scissors className="w-4 h-4 text-amber-600" />
              <span>Operating Scissors & Growth Momentum: {company.name}</span>
              <span className="text-xs font-mono font-bold bg-purple-50 text-purple-700 border border-purple-200 px-2 py-0.5 rounded-full flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                <span>{fin.periodLabel}</span>
              </span>
              <span className="text-xs font-mono font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full">
                {getCurrencyUnitLabel(currency, scale)}
              </span>
            </h2>
            <p className="text-xs text-slate-500">
              Topline revenue volume growth vs bottomline profit conversion sync
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono text-slate-500">Scissors Assessment:</span>
            <span className={`px-2.5 py-1 rounded-lg border text-xs font-bold font-mono ${
              !isAdverse ? 'bg-emerald-50 text-emerald-700 border-emerald-300' : 'bg-red-50 text-red-700 border-red-300'
            }`}>
              {!isAdverse ? 'POSITIVE OPERATING LEVERAGE' : 'ADVERSE OPERATING SCISSORS'}
            </span>
          </div>
        </div>

        {/* 3 Metric Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
            <div className="flex items-center justify-between text-slate-500">
              <span className="uppercase text-[10px]">Topline Sales YoY Growth</span>
              {fin.salesGrowthYoY >= 0 ? <ArrowUpRight className="w-4 h-4 text-emerald-600" /> : <ArrowDownRight className="w-4 h-4 text-rose-600" />}
            </div>
            <div className={`text-2xl font-bold ${fin.salesGrowthYoY >= 0 ? 'text-blue-600' : 'text-rose-600'}`}>
              {fin.salesGrowthYoY >= 0 ? '+' : ''}{fin.salesGrowthYoY.toFixed(1)}%
            </div>
            <p className="text-[11px] text-slate-500 font-sans">
              Revenue: {formatVal(fin.sales)}
            </p>
          </div>

          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
            <div className="flex items-center justify-between text-slate-500">
              <span className="uppercase text-[10px]">Bottomline PAT YoY Growth</span>
              {fin.netProfitGrowthYoY >= 0 ? <ArrowUpRight className="w-4 h-4 text-emerald-600" /> : <ArrowDownRight className="w-4 h-4 text-rose-600" />}
            </div>
            <div className={`text-2xl font-bold ${fin.netProfitGrowthYoY >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
              {fin.netProfitGrowthYoY >= 0 ? '+' : ''}{fin.netProfitGrowthYoY.toFixed(1)}%
            </div>
            <p className="text-[11px] text-slate-500 font-sans">
              Net Profit: {formatVal(fin.pat)}
            </p>
          </div>

          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
            <div className="flex items-center justify-between text-slate-500">
              <span className="uppercase text-[10px]">Operating Scissors Gap</span>
              <Scissors className="w-4 h-4 text-amber-600" />
            </div>
            <div className={`text-2xl font-bold ${isAdverse ? 'text-rose-600' : 'text-slate-900'}`}>
              {fin.scissorsGap.toFixed(1)}%
            </div>
            <p className="text-[11px] text-slate-500 font-sans">
              {isAdverse ? 'Revenue expanding while profit shrinks' : 'Profits growing in lockstep'}
            </p>
          </div>
        </div>
      </div>

      {/* Growth Comparison Chart & Cost Driver Attribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Growth Comparison Bar Chart */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-900 pb-2 border-b border-slate-100">
            Topline vs Bottomline YoY Velocity Comparison ({fin.periodLabel})
          </h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={comparisonData} margin={{ top: 20, right: 30, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="metric" tick={{ fontSize: 11, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={(v) => `${v}%`} />
                <Tooltip
                  formatter={(value: any) => [`${Number(value).toFixed(1)}% YoY`]}
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                />
                <Legend />
                <Bar dataKey="SalesGrowth" name="Revenue YoY Growth %" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="ProfitGrowth" name="PAT Net Profit YoY %" fill={fin.netProfitGrowthYoY >= 0 ? '#10b981' : '#f43f5e'} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Cost Structure Drivers Attribution */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-900 pb-2 border-b border-slate-100">
            Cost Structure Drivers (% of Sales)
          </h3>
          <div className="space-y-3 text-xs font-mono">
            <div className="flex justify-between p-2.5 bg-slate-50 rounded-lg">
              <span className="text-slate-600">Raw Materials & COGS:</span>
              <span className="font-bold text-slate-900">
                {formatVal(fin.costOfMaterials)} ({((fin.costOfMaterials / Math.max(1, fin.sales)) * 100).toFixed(1)}%)
              </span>
            </div>
            <div className="flex justify-between p-2.5 bg-slate-50 rounded-lg">
              <span className="text-slate-600">Employee Benefit Overhead:</span>
              <span className="font-bold text-slate-900">
                {formatVal(fin.employeeExpenses)} ({((fin.employeeExpenses / Math.max(1, fin.sales)) * 100).toFixed(1)}%)
              </span>
            </div>
            <div className="flex justify-between p-2.5 bg-slate-50 rounded-lg">
              <span className="text-slate-600">Other SG&A Operating Costs:</span>
              <span className="font-bold text-slate-900">
                {formatVal(fin.otherOperatingExpenses)} ({((fin.otherOperatingExpenses / Math.max(1, fin.sales)) * 100).toFixed(1)}%)
              </span>
            </div>
            <div className="flex justify-between p-2.5 bg-slate-50 rounded-lg">
              <span className="text-slate-600">Annualized PAT Run-Rate:</span>
              <span className="font-bold text-blue-600">
                {formatVal(fin.pat * (selectedPeriod === 'RunRate' ? 1 : selectedPeriod === 'PY' ? 1 : 4))} / Year
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
