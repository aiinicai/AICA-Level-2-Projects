import React from 'react';
import { 
  Building2, 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Percent, 
  Scale, 
  Activity, 
  Layers, 
  ArrowUpRight, 
  ArrowDownRight,
  ShieldCheck,
  AlertTriangle,
  Info,
  Calendar,
  Clock,
  Coins,
  PieChart as PieIcon,
  ShieldAlert,
  BarChart3,
  CheckCircle2,
  Sparkles,
  Zap,
  ArrowRight,
  Gauge,
  Wallet,
  Landmark,
  CircleDollarSign,
  LineChart,
  SplitSquareVertical,
  Sliders
} from 'lucide-react';
import { ListedCompany, CurrencyCode, UnitScale, NavTabId } from '../types/financial';
import { getResolvedCompanyFinancials, convertCompanyToFinancialPeriods } from '../data/listedCompaniesDataset';
import { formatFinancialValue, getCurrencyUnitLabel } from '../utils/formatUtils';
import { 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid, 
  Cell,
  PieChart,
  Pie,
  Legend,
  AreaChart,
  Area,
  Line
} from 'recharts';

interface ExecutiveDashboardProps {
  company: ListedCompany;
  currency: CurrencyCode;
  scale: UnitScale;
  onNavigateTab: (tab: NavTabId) => void;
  selectedPeriod?: string;
}

export const ExecutiveDashboard: React.FC<ExecutiveDashboardProps> = ({
  company,
  currency,
  scale,
  onNavigateTab,
  selectedPeriod = 'latest'
}) => {
  const fin = getResolvedCompanyFinancials(company, selectedPeriod);
  const periods = convertCompanyToFinancialPeriods(company);
  const currentPeriod = periods[0];
  const precedingPeriod = periods[1];
  const priorYearPeriod = periods[2];

  const formatVal = (val: number) => formatFinancialValue(val, currency, scale);

  // Core calculations
  const annualSales = fin.sales * 4;
  const rawMaterials = fin.costOfMaterials || Math.round(fin.sales * 0.44);
  const employeeCost = fin.employeeExpenses || Math.round(fin.sales * 0.12);
  const otherOpex = fin.otherOperatingExpenses || Math.max(0, fin.sales - fin.ebitda - rawMaterials - employeeCost);
  const totalOpex = rawMaterials + employeeCost + otherOpex;

  const netWorth = fin.netWorth || 100;
  const debt = fin.debt || 0;
  const capitalEmployed = fin.capitalEmployed || (netWorth + debt);
  const cash = company.cashAndEquivalents ?? Math.round(netWorth * 0.14);
  const fixedAssets = company.fixedAssets ?? Math.round(capitalEmployed * 0.62);

  // Working Capital metrics
  const receivables = company.tradeReceivables ?? Math.round(fin.sales * 0.16);
  const inventory = company.inventory ?? Math.round(fin.sales * 0.12);
  const payables = company.tradePayables ?? Math.round(fin.sales * 0.14);
  const netWorkingCap = receivables + inventory - payables;

  const annualCogs = Math.max(1, (rawMaterials + otherOpex) * 4);
  const dso = company.dso ?? (annualSales > 0 ? Math.round((receivables / annualSales) * 365) : 45);
  const dio = company.dio ?? (annualCogs > 0 ? Math.round((inventory / annualCogs) * 365) : 35);
  const dpo = company.dpo ?? (annualCogs > 0 ? Math.round((payables / annualCogs) * 365) : 40);
  const ccc = dso + dio - dpo;

  // Free Cash Flow
  const capex = company.capex ?? Math.round(fin.sales * 0.05);
  const deltaWC = Math.round(netWorkingCap * 0.04);
  const fcff = company.fcff ?? Math.round(fin.ebitda - fin.taxExpense - deltaWC - capex);

  // Returns & DuPont
  const annualPat = fin.pat * 4;
  const roe = netWorth > 0 ? (annualPat / netWorth) * 100 : 0;
  const roce = fin.roce || (capitalEmployed > 0 ? (((fin.ebit || fin.ebitda * 0.8) * 4) / capitalEmployed) * 100 : 0);
  const assetTurnover = capitalEmployed > 0 ? annualSales / capitalEmployed : 1.0;
  const financialLeverage = netWorth > 0 ? capitalEmployed / netWorth : 1.0;

  // Composite Health Score
  let healthScore = 50;
  if (fin.ebitdaMargin > 20) healthScore += 12; else if (fin.ebitdaMargin > 12) healthScore += 6;
  if (fin.netProfitMargin > 10) healthScore += 10; else if (fin.netProfitMargin > 4) healthScore += 5;
  if (fin.debtToEquity < 0.5) healthScore += 15; else if (fin.debtToEquity < 1.0) healthScore += 8; else if (fin.debtToEquity > 2.0) healthScore -= 15;
  if (fin.interestCoverage > 5.0) healthScore += 12; else if (fin.interestCoverage > 2.5) healthScore += 6; else if (fin.interestCoverage < 1.5) healthScore -= 15;
  if (roce > 18) healthScore += 15; else if (roce > 12) healthScore += 8; else if (roce < 8) healthScore -= 8;
  if (ccc < 45) healthScore += 10; else if (ccc > 90) healthScore -= 5;
  healthScore = Math.max(10, Math.min(99, Math.round(healthScore)));

  // Waterfall Decomposition Bridge Data
  const waterfallData = [
    { name: 'Gross Revenue', amount: fin.sales, base: 0, fill: '#3B82F6', type: 'total' },
    { name: 'Materials', amount: rawMaterials, base: fin.sales - rawMaterials, fill: '#EF4444', type: 'sub' },
    { name: 'Employee Cost', amount: employeeCost, base: fin.sales - rawMaterials - employeeCost, fill: '#F97316', type: 'sub' },
    { name: 'Other Opex', amount: otherOpex, base: fin.ebitda, fill: '#F59E0B', type: 'sub' },
    { name: 'Operating EBITDA', amount: fin.ebitda, base: 0, fill: '#10B981', type: 'total' },
    { name: 'Depreciation & Fin.', amount: fin.depreciation + fin.financeCosts, base: Math.max(0, fin.ebitda - fin.depreciation - fin.financeCosts), fill: '#64748B', type: 'sub' },
    { name: 'Taxes', amount: fin.taxExpense, base: Math.max(0, fin.pat), fill: '#EC4899', type: 'sub' },
    { name: 'Net PAT', amount: Math.max(0, fin.pat), base: 0, fill: '#8B5CF6', type: 'total' }
  ];

  // Multi-Period Momentum Data
  const multiPeriodTrendData = [
    {
      period: 'Q4 FY24 (Prior Yr)',
      Revenue: priorYearPeriod.revenue,
      EBITDA: priorYearPeriod.ebitda,
      PAT: priorYearPeriod.pat,
      OPM: priorYearPeriod.opm
    },
    {
      period: 'Q3 FY25 (Preceding)',
      Revenue: precedingPeriod.revenue,
      EBITDA: precedingPeriod.ebitda,
      PAT: precedingPeriod.pat,
      OPM: precedingPeriod.opm
    },
    {
      period: 'Q4 FY25 (Latest)',
      Revenue: currentPeriod.revenue,
      EBITDA: currentPeriod.ebitda,
      PAT: currentPeriod.pat,
      OPM: currentPeriod.opm
    }
  ];

  // Capital Deployment Breakdown
  const capitalDeploymentData = [
    { name: 'Net Fixed Assets (PP&E)', value: Math.max(1, fixedAssets), color: '#3B82F6' },
    { name: 'Net Working Capital', value: Math.max(1, netWorkingCap), color: '#8B5CF6' },
    { name: 'Cash & Liquid Reserves', value: Math.max(1, cash), color: '#10B981' }
  ];

  return (
    <div className="space-y-6 animate-fadeIn font-sans pb-10">
      
      {/* 1. EXECUTIVE COCKPIT HERO HEADER */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-indigo-950 text-white rounded-2xl p-6 shadow-lg border border-slate-700/50 space-y-6">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6 pb-6 border-b border-slate-700/60">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white font-sans">
                {company.name}
              </h1>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-blue-500/20 text-blue-300 border border-blue-400/30">
                NSE: {company.nseCode}
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-slate-700/50 text-slate-300 border border-slate-600">
                BSE: {company.bseCode}
              </span>
              <span className="px-3 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                {company.sector}
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-purple-500/20 text-purple-300 border border-purple-400/30 flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                <span>{fin.periodLabel}</span>
              </span>
            </div>
            <p className="text-xs text-slate-300 max-w-4xl leading-relaxed">
              {company.description}
            </p>
          </div>

          {/* Composite Health Index Card */}
          <div className="flex items-center gap-4 bg-slate-800/90 border border-slate-700 p-4 rounded-xl shadow-inner shrink-0">
            <div className="text-right">
              <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Executive Health Index</div>
              <div className="text-sm font-bold text-emerald-400 mt-0.5">
                {healthScore >= 75 ? 'PRIME / STRONG' : healthScore >= 50 ? 'STABLE / MODERATE' : 'VULNERABLE / WATCH'}
              </div>
              <div className="text-[10px] text-slate-400 font-mono">Multi-Statement Score</div>
            </div>
            <div className="h-14 w-14 rounded-xl bg-gradient-to-br from-emerald-500/30 to-slate-800 border-2 border-emerald-400 flex items-center justify-center shadow-lg">
              <span className="text-2xl font-black font-mono text-emerald-300">{healthScore}</span>
            </div>
          </div>
        </div>

        {/* 5 Executive Vital Health Signs Gauges */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          
          {/* Sign 1: Topline Velocity */}
          <div className="bg-slate-800/70 border border-slate-700/80 p-3.5 rounded-xl space-y-1">
            <div className="flex items-center justify-between text-[11px] text-slate-400">
              <span>Topline Revenue</span>
              <DollarSign className="w-3.5 h-3.5 text-blue-400" />
            </div>
            <div className="text-lg font-bold font-mono text-white">{formatVal(fin.sales)}</div>
            <div className="flex items-center gap-1 text-[11px] font-mono">
              <span className={`font-bold flex items-center ${fin.salesGrowthYoY >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {fin.salesGrowthYoY >= 0 ? '+' : ''}{fin.salesGrowthYoY.toFixed(1)}% YoY
              </span>
            </div>
          </div>

          {/* Sign 2: Operating EBITDA & OPM */}
          <div className="bg-slate-800/70 border border-slate-700/80 p-3.5 rounded-xl space-y-1">
            <div className="flex items-center justify-between text-[11px] text-slate-400">
              <span>EBITDA (OPM %)</span>
              <Activity className="w-3.5 h-3.5 text-emerald-400" />
            </div>
            <div className="text-lg font-bold font-mono text-emerald-300">{formatVal(fin.ebitda)}</div>
            <div className="text-[11px] font-mono text-emerald-400 font-semibold">
              {fin.ebitdaMargin.toFixed(1)}% Operating Margin
            </div>
          </div>

          {/* Sign 3: Solvency & Leverage */}
          <div className="bg-slate-800/70 border border-slate-700/80 p-3.5 rounded-xl space-y-1">
            <div className="flex items-center justify-between text-[11px] text-slate-400">
              <span>Debt-to-Equity (D/E)</span>
              <ShieldCheck className="w-3.5 h-3.5 text-purple-400" />
            </div>
            <div className="text-lg font-bold font-mono text-white">{fin.debtToEquity.toFixed(2)}x</div>
            <div className="text-[11px] font-mono text-slate-300">
              ICR: <span className="font-bold text-emerald-400">{fin.interestCoverage >= 90 ? '>99x' : fin.interestCoverage.toFixed(1) + 'x'}</span>
            </div>
          </div>

          {/* Sign 4: Cash Conversion Velocity */}
          <div className="bg-slate-800/70 border border-slate-700/80 p-3.5 rounded-xl space-y-1">
            <div className="flex items-center justify-between text-[11px] text-slate-400">
              <span>Cash Cycle (CCC)</span>
              <Clock className="w-3.5 h-3.5 text-amber-400" />
            </div>
            <div className="text-lg font-bold font-mono text-amber-300">{ccc} Days</div>
            <div className="text-[11px] font-mono text-slate-300">
              FCFF: <span className="font-bold text-emerald-400">{formatVal(fcff)}</span>
            </div>
          </div>

          {/* Sign 5: Capital Efficiency (ROCE) */}
          <div className="bg-slate-800/70 border border-slate-700/80 p-3.5 rounded-xl space-y-1">
            <div className="flex items-center justify-between text-[11px] text-slate-400">
              <span>Return on Capital</span>
              <Scale className="w-3.5 h-3.5 text-cyan-400" />
            </div>
            <div className="text-lg font-bold font-mono text-cyan-300">{roce.toFixed(1)}%</div>
            <div className="text-[11px] font-mono text-slate-300">
              Spread: <span className={`font-bold ${(roce - 10) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {(roce - 10) >= 0 ? '+' : ''}{(roce - 10).toFixed(1)}% vs 10% WACC
              </span>
            </div>
          </div>

        </div>
      </div>

      {/* 2. PICTORIAL VISUAL COMMAND CENTER (2 High-Density Visual Modules) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Module A: P&L Margin Step-Down & Profit Conversion Waterfall */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-blue-600" />
                <span>P&L Profit Conversion Waterfall ({fin.periodLabel})</span>
              </h2>
              <p className="text-xs text-slate-500">Step-by-step margin erosion and net profit absorption</p>
            </div>
            <button
              onClick={() => onNavigateTab('profitability')}
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1 cursor-pointer"
            >
              <span>Full P&L Table</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={waterfallData} margin={{ top: 15, right: 10, left: -5, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#64748b' }} angle={-15} textAnchor="end" interval={0} />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={(v) => `₹${v}`} />
                <Tooltip
                  formatter={(val: any, name: any, item: any) => [
                    formatVal(Number(item.payload.amount)),
                    item.payload.name
                  ]}
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#fff', fontSize: '11px' }}
                />
                <Bar dataKey="base" stackId="a" fill="transparent" />
                <Bar dataKey="amount" stackId="a" radius={[4, 4, 0, 0]}>
                  {waterfallData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-100 text-center font-mono text-xs">
            <div className="bg-blue-50/60 p-2 rounded-lg">
              <span className="text-[10px] text-blue-600 block">Gross Sales</span>
              <span className="font-bold text-slate-900">{formatVal(fin.sales)}</span>
            </div>
            <div className="bg-emerald-50/60 p-2 rounded-lg">
              <span className="text-[10px] text-emerald-600 block">EBITDA ({fin.ebitdaMargin.toFixed(1)}%)</span>
              <span className="font-bold text-emerald-700">{formatVal(fin.ebitda)}</span>
            </div>
            <div className="bg-purple-50/60 p-2 rounded-lg">
              <span className="text-[10px] text-purple-600 block">Net PAT ({fin.netProfitMargin.toFixed(1)}%)</span>
              <span className="font-bold text-purple-700">{formatVal(fin.pat)}</span>
            </div>
          </div>
        </div>

        {/* Module B: Multi-Period Growth Momentum (Revenue vs EBITDA vs PAT) */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-purple-600" />
                <span>Multi-Period Revenue & Profit Momentum</span>
              </h2>
              <p className="text-xs text-slate-500">Quarterly growth trajectory across Q4 FY24, Q3 FY25 & Q4 FY25</p>
            </div>
            <span className="text-xs font-mono font-bold bg-purple-50 text-purple-700 px-2.5 py-0.5 rounded-full">
              3-Period Trend
            </span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={multiPeriodTrendData} margin={{ top: 15, right: 10, left: -5, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="period" tick={{ fontSize: 10, fill: '#64748b' }} interval={0} />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={(v) => `₹${v}`} />
                <Tooltip
                  formatter={(val: any) => [formatVal(Number(val)), '']}
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#fff', fontSize: '11px' }}
                />
                <Bar dataKey="Revenue" fill="#3B82F6" radius={[4, 4, 0, 0]} name="Topline Revenue" />
                <Bar dataKey="EBITDA" fill="#10B981" radius={[4, 4, 0, 0]} name="Operating EBITDA" />
                <Bar dataKey="PAT" fill="#8B5CF6" radius={[4, 4, 0, 0]} name="Net Profit (PAT)" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="flex items-center justify-center gap-6 text-xs font-mono pt-2 border-t border-slate-100">
            <span className="flex items-center gap-1.5 text-slate-700">
              <span className="w-3 h-3 rounded bg-blue-500"></span> Topline Revenue
            </span>
            <span className="flex items-center gap-1.5 text-slate-700">
              <span className="w-3 h-3 rounded bg-emerald-500"></span> Operating EBITDA
            </span>
            <span className="flex items-center gap-1.5 text-slate-700">
              <span className="w-3 h-3 rounded bg-purple-500"></span> Net PAT
            </span>
          </div>
        </div>

      </div>

      {/* 3. BALANCE SHEET EQUATION & APPLICATION OF CAPITAL (Visual Balance Sheet Cockpit) */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
          <div>
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Landmark className="w-4 h-4 text-emerald-600" />
              <span>Balance Sheet Architecture & Capital Employed Balance</span>
            </h2>
            <p className="text-xs text-slate-500">
              Sources of Capital (Equity + Debt) $=$ Deployment of Capital (Fixed Assets + Working Capital + Cash)
            </p>
          </div>
          <button
            onClick={() => onNavigateTab('solvency')}
            className="text-xs font-semibold text-emerald-600 hover:text-emerald-800 flex items-center gap-1 cursor-pointer"
          >
            <span>Solvency Suite</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-center">
          
          {/* Left: Sources of Capital */}
          <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200">
              <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">A. Sources of Funds (Capital Employed)</span>
              <span className="text-xs font-mono font-bold text-slate-900">{formatVal(capitalEmployed)}</span>
            </div>

            <div className="space-y-2.5">
              <div className="space-y-1">
                <div className="flex justify-between text-xs font-mono">
                  <span className="text-slate-600 font-medium">Net Worth (Shareholder Equity + Reserves):</span>
                  <span className="font-bold text-emerald-700">{formatVal(netWorth)} ({((netWorth / capitalEmployed) * 100).toFixed(0)}%)</span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                  <div className="bg-emerald-600 h-2 rounded-full" style={{ width: `${Math.min(100, (netWorth / capitalEmployed) * 100)}%` }}></div>
                </div>
              </div>

              <div className="space-y-1">
                <div className="flex justify-between text-xs font-mono">
                  <span className="text-slate-600 font-medium">Total Borrowings (Debt):</span>
                  <span className="font-bold text-rose-600">{formatVal(debt)} ({((debt / capitalEmployed) * 100).toFixed(0)}%)</span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                  <div className="bg-rose-500 h-2 rounded-full" style={{ width: `${Math.min(100, (debt / capitalEmployed) * 100)}%` }}></div>
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-200 flex justify-between items-center text-xs font-mono">
              <span className="text-slate-500">Debt-to-Equity: <strong className="text-slate-900">{fin.debtToEquity.toFixed(2)}x</strong></span>
              <span className="text-slate-500">Interest Coverage: <strong className="text-emerald-700">{fin.interestCoverage >= 90 ? '>99x' : fin.interestCoverage.toFixed(1) + 'x'}</strong></span>
            </div>
          </div>

          {/* Right: Application of Capital */}
          <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200">
              <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">B. Deployment of Capital (Assets)</span>
              <span className="text-xs font-mono font-bold text-slate-900">{formatVal(capitalEmployed)}</span>
            </div>

            <div className="space-y-2.5">
              <div className="space-y-1">
                <div className="flex justify-between text-xs font-mono">
                  <span className="text-slate-600 font-medium">Fixed Assets (Net PP&E Block):</span>
                  <span className="font-bold text-blue-700">{formatVal(fixedAssets)} ({((fixedAssets / capitalEmployed) * 100).toFixed(0)}%)</span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                  <div className="bg-blue-600 h-2 rounded-full" style={{ width: `${Math.min(100, (fixedAssets / capitalEmployed) * 100)}%` }}></div>
                </div>
              </div>

              <div className="space-y-1">
                <div className="flex justify-between text-xs font-mono">
                  <span className="text-slate-600 font-medium">Net Working Capital (Receivables + Inv - Pay):</span>
                  <span className="font-bold text-purple-700">{formatVal(netWorkingCap)} ({((netWorkingCap / capitalEmployed) * 100).toFixed(0)}%)</span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                  <div className="bg-purple-600 h-2 rounded-full" style={{ width: `${Math.min(100, Math.max(5, (netWorkingCap / capitalEmployed) * 100))}%` }}></div>
                </div>
              </div>

              <div className="space-y-1">
                <div className="flex justify-between text-xs font-mono">
                  <span className="text-slate-600 font-medium">Cash & Liquid Balances:</span>
                  <span className="font-bold text-emerald-700">{formatVal(cash)}</span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                  <div className="bg-emerald-500 h-2 rounded-full" style={{ width: `${Math.min(100, Math.max(5, (cash / capitalEmployed) * 100))}%` }}></div>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* 4. DUPONT ANALYSIS & VALUE CREATION TREE */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Scale className="w-4 h-4 text-purple-600" />
              <span>DuPont Shareholder Return Decomposition (ROE & ROCE)</span>
            </h2>
            <p className="text-xs text-slate-500">
              How operational efficiency, asset turnover, and financial leverage generate shareholder value
            </p>
          </div>
          <span className="text-xs font-mono font-bold bg-purple-50 text-purple-700 px-2.5 py-0.5 rounded-full">
            ROE: {roe.toFixed(1)}% | ROCE: {roce.toFixed(1)}%
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          
          {/* Component 1: Net Margin */}
          <div className="bg-gradient-to-b from-blue-50/70 to-white border border-blue-200 p-4 rounded-xl space-y-1 text-center">
            <span className="text-[11px] text-blue-700 font-semibold uppercase tracking-wider block">1. Net Profit Margin (NPM)</span>
            <div className="text-2xl font-black font-mono text-blue-900">{fin.netProfitMargin.toFixed(1)}%</div>
            <p className="text-[11px] text-slate-500 font-sans">Operational pricing power & cost discipline</p>
            <span className="text-[10px] font-mono text-blue-600 block pt-1 border-t border-blue-100">
              PAT / Revenue
            </span>
          </div>

          {/* Component 2: Capital Turnover */}
          <div className="bg-gradient-to-b from-emerald-50/70 to-white border border-emerald-200 p-4 rounded-xl space-y-1 text-center">
            <span className="text-[11px] text-emerald-700 font-semibold uppercase tracking-wider block">2. Capital Asset Turnover</span>
            <div className="text-2xl font-black font-mono text-emerald-900">{assetTurnover.toFixed(2)}x</div>
            <p className="text-[11px] text-slate-500 font-sans">Revenue generated per ₹ of capital deployed</p>
            <span className="text-[10px] font-mono text-emerald-600 block pt-1 border-t border-emerald-100">
              Annual Sales / Capital Employed
            </span>
          </div>

          {/* Component 3: Financial Leverage */}
          <div className="bg-gradient-to-b from-purple-50/70 to-white border border-purple-200 p-4 rounded-xl space-y-1 text-center">
            <span className="text-[11px] text-purple-700 font-semibold uppercase tracking-wider block">3. Equity Leverage Multiplier</span>
            <div className="text-2xl font-black font-mono text-purple-900">{financialLeverage.toFixed(2)}x</div>
            <p className="text-[11px] text-slate-500 font-sans">Balance sheet equity multiplier factor</p>
            <span className="text-[10px] font-mono text-purple-600 block pt-1 border-t border-purple-100">
              Capital Employed / Net Worth
            </span>
          </div>

        </div>
      </div>

      {/* 5. PICTORIAL CASH CONVERSION CYCLE FLOW */}
      <div className="bg-slate-900 text-white rounded-2xl p-5 shadow-sm border border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
          <div>
            <h3 className="text-xs font-bold text-slate-200 flex items-center gap-2">
              <Clock className="w-4 h-4 text-emerald-400" />
              <span>Working Capital & Cash Conversion Timeline Pipeline</span>
            </h3>
            <p className="text-[11px] text-slate-400">
              Pipeline from customer collections (DSO) & inventory turnaround (DIO) minus supplier credit (DPO)
            </p>
          </div>
          <button
            onClick={() => onNavigateTab('working_capital')}
            className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>Open WC Simulator</span>
          </button>
        </div>

        {/* Timeline Process Diagram */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-center">
          
          <div className="bg-slate-800/90 border border-slate-700 p-4 rounded-xl space-y-1 text-center">
            <span className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">1. Customer Receivables</span>
            <div className="text-2xl font-black font-mono text-blue-400">{dso} Days</div>
            <p className="text-[10px] text-slate-400">DSO: Collections speed</p>
            <span className="text-[11px] font-mono text-slate-300 block pt-1 border-t border-slate-700">
              {formatVal(receivables)}
            </span>
          </div>

          <div className="bg-slate-800/90 border border-slate-700 p-4 rounded-xl space-y-1 text-center">
            <span className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">2. Inventory Holding</span>
            <div className="text-2xl font-black font-mono text-amber-400">{dio} Days</div>
            <p className="text-[10px] text-slate-400">DIO: Stock holding duration</p>
            <span className="text-[11px] font-mono text-slate-300 block pt-1 border-t border-slate-700">
              {formatVal(inventory)}
            </span>
          </div>

          <div className="bg-slate-800/90 border border-slate-700 p-4 rounded-xl space-y-1 text-center">
            <span className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">3. Vendor Payables</span>
            <div className="text-2xl font-black font-mono text-purple-400">{dpo} Days</div>
            <p className="text-[10px] text-slate-400">DPO: Supplier credit terms</p>
            <span className="text-[11px] font-mono text-slate-300 block pt-1 border-t border-slate-700">
              {formatVal(payables)}
            </span>
          </div>

          <div className="bg-gradient-to-br from-emerald-950 to-slate-900 border-2 border-emerald-500/50 p-4 rounded-xl space-y-1 text-center shadow-lg">
            <span className="text-[10px] text-emerald-400 uppercase font-bold tracking-wider">(=) Net Cash Cycle</span>
            <div className="text-3xl font-black font-mono text-emerald-300">{ccc} Days</div>
            <p className="text-[10px] text-slate-400">DSO + DIO - DPO</p>
            <span className="text-[11px] font-mono text-emerald-400 block pt-1 border-t border-emerald-500/40 font-bold">
              NWC: {formatVal(netWorkingCap)}
            </span>
          </div>

        </div>
      </div>

    </div>
  );
};
