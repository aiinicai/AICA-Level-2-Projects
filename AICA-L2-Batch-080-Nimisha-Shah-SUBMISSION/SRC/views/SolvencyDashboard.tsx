import React from 'react';
import { 
  Scale, 
  ShieldCheck, 
  ShieldAlert, 
  Layers, 
  CheckCircle2, 
  XCircle,
  TrendingUp,
  AlertTriangle,
  Calendar
} from 'lucide-react';
import { ListedCompany, CurrencyCode, UnitScale } from '../types/financial';
import { getResolvedCompanyFinancials } from '../data/listedCompaniesDataset';
import { formatFinancialValue, getCurrencyUnitLabel } from '../utils/formatUtils';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from 'recharts';

interface SolvencyDashboardProps {
  company: ListedCompany;
  selectedPeriod?: string;
  currency?: CurrencyCode;
  scale?: UnitScale;
}

export const SolvencyDashboard: React.FC<SolvencyDashboardProps> = ({ 
  company,
  selectedPeriod = 'latest',
  currency = 'INR',
  scale = 'crores'
}) => {
  const fin = getResolvedCompanyFinancials(company, selectedPeriod);
  const isHighLeverage = fin.debtToEquity > 2.0;
  const isWeakCoverage = fin.interestCoverage < 1.5 && fin.debt > 10;
  const isSafeCoverage = fin.interestCoverage >= 3.0;

  const formatVal = (val: number) => formatFinancialValue(val, 'INR', scale);

  const stackData = [
    {
      category: 'Capital Employed',
      NetWorth: scale === 'millions' ? fin.netWorth * 10 : fin.netWorth,
      TotalDebt: scale === 'millions' ? fin.debt * 10 : fin.debt
    }
  ];

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Solvency Health Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Scale className="w-4 h-4 text-blue-600" />
              <span>Solvency, Leverage & Debt Servicing Capacity: {company.name}</span>
              <span className="text-xs font-mono font-bold bg-purple-50 text-purple-700 border border-purple-200 px-2 py-0.5 rounded-full flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                <span>{fin.periodLabel}</span>
              </span>
              <span className="text-xs font-mono font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full">
                {getCurrencyUnitLabel('INR', scale)}
              </span>
            </h2>
            <p className="text-xs text-slate-500">
              Balance sheet gearing, debt-to-equity and interest coverage buffer assessment
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono text-slate-500">Solvency Status:</span>
            <span className={`px-2.5 py-1 rounded-lg border text-xs font-bold font-mono ${
              !isHighLeverage && !isWeakCoverage
                ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                : 'bg-red-50 text-red-700 border-red-300'
            }`}>
              {!isHighLeverage && !isWeakCoverage ? 'PRUDENT / INVESTMENT GRADE' : 'LEVERAGE WATCHLIST'}
            </span>
          </div>
        </div>

        {/* 3 Solvency KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
            <div className="flex items-center justify-between text-slate-500">
              <span className="uppercase text-[10px]">Debt-to-Equity (D/E)</span>
              {isHighLeverage ? <ShieldAlert className="w-4 h-4 text-rose-600" /> : <ShieldCheck className="w-4 h-4 text-emerald-600" />}
            </div>
            <div className={`text-2xl font-bold ${isHighLeverage ? 'text-rose-600' : 'text-slate-900'}`}>
              {fin.debtToEquity.toFixed(2)}x
            </div>
            <p className="text-[11px] text-slate-500 font-sans">
              Threshold: ≤ 2.0x ({isHighLeverage ? 'Elevated leverage' : 'Healthy capital cushion'})
            </p>
          </div>

          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
            <div className="flex items-center justify-between text-slate-500">
              <span className="uppercase text-[10px]">Interest Coverage Ratio</span>
              {isWeakCoverage ? <ShieldAlert className="w-4 h-4 text-rose-600" /> : <ShieldCheck className="w-4 h-4 text-emerald-600" />}
            </div>
            <div className={`text-2xl font-bold ${isWeakCoverage ? 'text-rose-600' : isSafeCoverage ? 'text-emerald-600' : 'text-amber-600'}`}>
              {fin.interestCoverage.toFixed(1)}x
            </div>
            <p className="text-[11px] text-slate-500 font-sans">
              {isSafeCoverage ? 'Safe servicing capacity (> 3.0x)' : isWeakCoverage ? 'Critical servicing distress (< 1.5x)' : 'Adequate buffer (1.5x–3.0x)'}
            </p>
          </div>

          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
            <div className="flex items-center justify-between text-slate-500">
              <span className="uppercase text-[10px]">Return on Capital (ROCE)</span>
              <TrendingUp className="w-4 h-4 text-purple-600" />
            </div>
            <div className="text-2xl font-bold text-purple-600">
              {fin.roce.toFixed(1)}%
            </div>
            <p className="text-[11px] text-slate-500 font-sans">
              Economic spread: {(fin.roce - 10.0) >= 0 ? '+' : ''}{(fin.roce - 10.0).toFixed(1)}% vs 10% hurdle
            </p>
          </div>
        </div>
      </div>

      {/* Capital Structure Stack Chart & Details */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Stack Bar Chart */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-900 pb-2 border-b border-slate-100">
            Capital Employed Distribution (Debt vs Net Worth)
          </h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stackData} layout="vertical" margin={{ top: 20, right: 30, left: 40, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                <XAxis 
                  type="number" 
                  tick={{ fontSize: 10, fill: '#64748b' }} 
                  tickFormatter={(v) => scale === 'millions' ? `₹${v.toLocaleString()}M` : `₹${v}Cr`} 
                />
                <YAxis type="category" dataKey="category" tick={{ fontSize: 11, fill: '#64748b' }} />
                <Tooltip
                  formatter={(value: any) => [
                    scale === 'millions' ? `₹ ${Number(value).toLocaleString('en-IN')} Million` : `₹ ${Number(value).toLocaleString('en-IN')} Cr`
                  ]}
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                />
                <Legend />
                <Bar dataKey="NetWorth" name="Shareholders Net Worth" stackId="a" fill="#3b82f6" radius={[4, 0, 0, 4]} />
                <Bar dataKey="TotalDebt" name="Total Borrowings / Debt" stackId="a" fill="#f43f5e" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Detailed Solvency Metrics List */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-900 pb-2 border-b border-slate-100">
            Solvency Breakdown Schedule ({fin.periodLabel})
          </h3>
          <div className="space-y-3 text-xs font-mono">
            <div className="flex justify-between p-2.5 bg-slate-50 rounded-lg">
              <span className="text-slate-600">Total Net Worth:</span>
              <span className="font-bold text-slate-900">{formatVal(fin.netWorth)}</span>
            </div>
            <div className="flex justify-between p-2.5 bg-slate-50 rounded-lg">
              <span className="text-slate-600">Total Debt / Borrowings:</span>
              <span className="font-bold text-slate-900">{formatVal(fin.debt)}</span>
            </div>
            <div className="flex justify-between p-2.5 bg-slate-50 rounded-lg">
              <span className="text-slate-600">Total Capital Employed:</span>
              <span className="font-bold text-blue-600">{formatVal(fin.capitalEmployed)}</span>
            </div>
            <div className="flex justify-between p-2.5 bg-slate-50 rounded-lg">
              <span className="text-slate-600">Finance Cost (Interest):</span>
              <span className="font-bold text-slate-900">{formatVal(fin.financeCosts)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
