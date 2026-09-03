import React, { useState, useMemo } from 'react';
import {
  Clock,
  Coins,
  TrendingUp,
  Layers,
  ShieldCheck,
  RotateCcw,
  Sliders,
  DollarSign,
  Download,
  Calendar
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell
} from 'recharts';
import { ListedCompany, CurrencyCode, UnitScale } from '../types/financial';
import { formatFinancialValue, getCurrencyUnitLabel } from '../utils/formatUtils';
import { getResolvedCompanyFinancials } from '../data/listedCompaniesDataset';

interface WorkingCapitalViewProps {
  company: ListedCompany;
  companies: ListedCompany[];
  selectedPeriod?: string;
  currency?: CurrencyCode;
  scale?: UnitScale;
  onSelectCompany?: (code: string) => void;
}

export const WorkingCapitalView: React.FC<WorkingCapitalViewProps> = ({
  company,
  companies,
  selectedPeriod = 'latest',
  currency = 'INR',
  scale = 'crores',
  onSelectCompany
}) => {
  const fin = getResolvedCompanyFinancials(company, selectedPeriod);

  // Baseline Working Capital variables
  const sales = fin.sales;
  const annualSales = sales * 4;
  const cogs = (fin.costOfMaterials || Math.round(sales * 0.44)) + (fin.otherOperatingExpenses || Math.round(sales * 0.15));
  const annualCogs = Math.max(1, cogs * 4);

  const baselineReceivables = company.tradeReceivables ?? Math.round(sales * 0.16);
  const baselineInventory = company.inventory ?? Math.round(sales * 0.12);
  const baselinePayables = company.tradePayables ?? Math.round(sales * 0.14);
  const baselineCapex = company.capex ?? Math.round(sales * 0.05);

  const baselineDSO = company.dso ?? (annualSales > 0 ? Math.round((baselineReceivables / annualSales) * 365) : 45);
  const baselineDIO = company.dio ?? (annualCogs > 0 ? Math.round((baselineInventory / annualCogs) * 365) : 35);
  const baselineDPO = company.dpo ?? (annualCogs > 0 ? Math.round((baselinePayables / annualCogs) * 365) : 40);
  const baselineCCC = baselineDSO + baselineDIO - baselineDPO;

  // Simulator State (Delta adjustments in days)
  const [deltaDSO, setDeltaDSO] = useState<number>(-5); // default 5 days faster collections
  const [deltaDIO, setDeltaDIO] = useState<number>(-4); // default 4 days leaner inventory
  const [deltaDPO, setDeltaDPO] = useState<number>(3);  // default 3 days extended vendor credit
  const [costOfDebtPct, setCostOfDebtPct] = useState<number>(8.5); // 8.5% borrowing rate

  const formatVal = (val: number) => formatFinancialValue(val, currency, scale);

  // Computed Sim Values
  const simDSO = Math.max(1, baselineDSO + deltaDSO);
  const simDIO = Math.max(0, baselineDIO + deltaDIO);
  const simDPO = Math.max(1, baselineDPO + deltaDPO);
  const simCCC = simDSO + simDIO - simDPO;
  const deltaCCC = simCCC - baselineCCC;

  // Cash Impact calculation
  const cashFromDSO = (-deltaDSO / 365) * annualSales;
  const cashFromDIO = (-deltaDIO / 365) * annualCogs;
  const cashFromDPO = (deltaDPO / 365) * annualCogs;
  const totalCashUnlocked = Math.round(cashFromDSO + cashFromDIO + cashFromDPO);

  // Interest Savings on Unlocked Cash
  const annualizedInterestSavings = Math.round(totalCashUnlocked * (costOfDebtPct / 100));
  const newPATRunRate = (fin.pat * 4) + annualizedInterestSavings;
  const patBoostPct = (fin.pat * 4) > 0 ? (annualizedInterestSavings / (fin.pat * 4)) * 100 : 0;

  // Baseline Free Cash Flow Waterfall (Annualized)
  const annualEbitda = fin.ebitda * 4;
  const annualTax = fin.taxExpense * 4;
  const annualNWC = (baselineReceivables + baselineInventory - baselinePayables);
  const annualDeltaWC = Math.round(annualNWC * 0.05);
  const annualCapex = baselineCapex * 4;
  const baselineFCFF = Math.round(annualEbitda - annualTax - annualDeltaWC - annualCapex);
  const annualInterest = fin.financeCosts * 4;
  const baselineFCFE = Math.round(baselineFCFF - annualInterest);

  const fcfWaterfallData = useMemo(() => {
    return [
      { step: 'EBITDA (Run-rate)', amount: annualEbitda, isTotal: false, color: '#10B981' },
      { step: '(-) Cash Taxes', amount: -annualTax, isTotal: false, color: '#EF4444' },
      { step: '(±) Working Cap Reinvestment', amount: -annualDeltaWC, isTotal: false, color: '#F59E0B' },
      { step: '(-) Capital Expenditure', amount: -annualCapex, isTotal: false, color: '#8B5CF6' },
      { step: '(=) Free Cash Flow (FCFF)', amount: baselineFCFF, isTotal: true, color: baselineFCFF >= 0 ? '#059669' : '#DC2626' },
      { step: '(-) Net Interest Paid', amount: -annualInterest, isTotal: false, color: '#F43F5E' },
      { step: '(=) FCF to Equity (FCFE)', amount: baselineFCFE, isTotal: true, color: baselineFCFE >= 0 ? '#2563EB' : '#991B1B' },
    ];
  }, [annualEbitda, annualTax, annualDeltaWC, annualCapex, baselineFCFF, annualInterest, baselineFCFE]);

  // Sector Peers ranked by Cash Conversion Cycle
  const sectorPeers = useMemo(() => {
    return companies
      .filter((c) => c.sector === company.sector)
      .map((c) => {
        const cDso = c.dso ?? 45;
        const cDio = c.dio ?? 35;
        const cDpo = c.dpo ?? 40;
        const cCcc = c.ccc ?? (cDso + cDio - cDpo);
        const cNwc = (c.tradeReceivables || 0) + (c.inventory || 0) - (c.tradePayables || 0);
        const nwcToSales = (c.salesLatestQuarter * 4) > 0 ? (cNwc / (c.salesLatestQuarter * 4)) * 100 : 0;
        return {
          ...c,
          dsoVal: cDso,
          dioVal: cDio,
          dpoVal: cDpo,
          cccVal: cCcc,
          nwcVal: cNwc,
          nwcToSales
        };
      })
      .sort((a, b) => a.cccVal - b.cccVal);
  }, [companies, company.sector]);

  const handleResetSimulator = () => {
    setDeltaDSO(0);
    setDeltaDIO(0);
    setDeltaDPO(0);
    setCostOfDebtPct(8.5);
  };

  const getCCCHealthBadge = (cccDays: number) => {
    if (cccDays <= 15) {
      return {
        label: 'Hyper Lean & Cash Generative',
        bg: 'bg-emerald-500/10 text-emerald-600 border-emerald-500/30'
      };
    }
    if (cccDays <= 60) {
      return {
        label: 'Healthy Working Capital Cycle',
        bg: 'bg-blue-500/10 text-blue-600 border-blue-500/30'
      };
    }
    if (cccDays <= 100) {
      return {
        label: 'Moderate Working Capital Cycle',
        bg: 'bg-amber-500/10 text-amber-600 border-amber-500/30'
      };
    }
    return {
      label: 'Capital Intensive / Stretched',
      bg: 'bg-rose-500/10 text-rose-600 border-rose-500/30'
    };
  };

  const cccBadge = getCCCHealthBadge(baselineCCC);

  // Export report to CSV
  const handleExportCSV = () => {
    const csvContent = [
      ['Metric', 'Baseline (Reported)', 'Optimized (Simulated)', 'Unit / Impact'],
      ['Days Sales Outstanding (DSO)', `${baselineDSO} days`, `${simDSO} days`, `${deltaDSO > 0 ? '+' : ''}${deltaDSO} days`],
      ['Days Inventory Outstanding (DIO)', `${baselineDIO} days`, `${simDIO} days`, `${deltaDIO > 0 ? '+' : ''}${deltaDIO} days`],
      ['Days Payables Outstanding (DPO)', `${baselineDPO} days`, `${simDPO} days`, `${deltaDPO > 0 ? '+' : ''}${deltaDPO} days`],
      ['Cash Conversion Cycle (CCC)', `${baselineCCC} days`, `${simCCC} days`, `${deltaCCC > 0 ? '+' : ''}${deltaCCC} days`],
      ['Total Liquidity Unlocked', '-', `₹ ${totalCashUnlocked} Cr`, 'Direct Cash Flow'],
      ['Annualized Interest Cost Savings', '-', `₹ ${annualizedInterestSavings} Cr`, `@ ${costOfDebtPct}% Cost of Debt`],
      ['Run-Rate Net Profit (PAT)', `₹ ${fin.pat * 4} Cr`, `₹ ${newPATRunRate} Cr`, `+${patBoostPct.toFixed(2)}% Expansion`]
    ].map(e => e.join(',')).join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `${company.nseCode}_Working_Capital_Optimization_Report.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Top Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Clock className="w-5 h-5 text-emerald-600" />
              <span>Working Capital & Cash Conversion Cycle Suite: {company.name}</span>
              <span className="text-xs font-mono font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                <span>{fin.periodLabel}</span>
              </span>
              <span className="text-xs font-mono font-bold bg-purple-50 text-purple-700 border border-purple-200 px-2 py-0.5 rounded-full">
                {getCurrencyUnitLabel(currency, scale)}
              </span>
            </h2>
            <p className="text-xs text-slate-500">
              Cash Conversion Cycle (DSO + DIO - DPO), trapped liquidity simulator, and Free Cash Flow (FCFF/FCFE) engine
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className={`px-3 py-1 rounded-lg border text-xs font-bold font-mono ${cccBadge.bg}`}>
              {cccBadge.label}
            </span>
            <button
              onClick={handleExportCSV}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 text-white rounded-lg text-xs font-semibold hover:bg-slate-800 transition-colors shadow-xs cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export Report</span>
            </button>
          </div>
        </div>

        {/* 4 Summary Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
            <div className="flex items-center justify-between text-slate-500 text-xs font-medium mb-1">
              <span>Cash Conversion Cycle</span>
              <Clock className="w-4 h-4 text-emerald-600" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-black font-mono text-slate-900">{baselineCCC}</span>
              <span className="text-xs font-bold text-slate-500">Days</span>
            </div>
            <div className="mt-2 flex items-center gap-2 text-[11px] text-slate-500 font-mono">
              <span>DSO {baselineDSO}d</span>
              <span>+</span>
              <span>DIO {baselineDIO}d</span>
              <span>-</span>
              <span>DPO {baselineDPO}d</span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
            <div className="flex items-center justify-between text-slate-500 text-xs font-medium mb-1">
              <span>Net Working Capital</span>
              <Coins className="w-4 h-4 text-blue-600" />
            </div>
            <div className="text-2xl font-black font-mono text-slate-900">
              {formatVal(baselineReceivables + baselineInventory - baselinePayables)}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">
              {annualSales > 0 ? `${(((baselineReceivables + baselineInventory - baselinePayables) / annualSales) * 100).toFixed(1)}% of Annualized Revenue` : '0%'}
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
            <div className="flex items-center justify-between text-slate-500 text-xs font-medium mb-1">
              <span>Free Cash Flow (FCFF)</span>
              <TrendingUp className="w-4 h-4 text-purple-600" />
            </div>
            <div className={`text-2xl font-black font-mono ${baselineFCFF >= 0 ? 'text-emerald-700' : 'text-rose-600'}`}>
              {formatVal(baselineFCFF)}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">
              Run-Rate: {annualEbitda > 0 ? `${((baselineFCFF / annualEbitda) * 100).toFixed(1)}% EBITDA Conversion` : '0%'}
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
            <div className="flex items-center justify-between text-slate-500 text-xs font-medium mb-1">
              <span>Free Cash to Equity (FCFE)</span>
              <DollarSign className="w-4 h-4 text-emerald-600" />
            </div>
            <div className={`text-2xl font-black font-mono ${baselineFCFE >= 0 ? 'text-slate-900' : 'text-rose-600'}`}>
              {formatVal(baselineFCFE)}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">
              Post-Debt Service Cash Yield
            </p>
          </div>
        </div>
      </div>

      {/* Trapped Cash Unlock Simulator Section */}
      <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-950 text-white rounded-2xl p-6 shadow-lg border border-slate-700 space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-700/80 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <div className="h-7 w-7 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                <Sliders className="w-4 h-4" />
              </div>
              <h3 className="text-base font-bold text-white">Trapped Liquidity & Working Capital Unlock Simulator</h3>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                Interactive Engine
              </span>
            </div>
            <p className="text-xs text-slate-300 mt-1">
              Adjust working capital levers to test real-time liquid cash release, borrowing cost savings, and bottom-line PAT expansion.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 bg-slate-800/80 px-2.5 py-1 rounded-lg border border-slate-700 text-xs">
              <span className="text-slate-400">Borrowing Rate:</span>
              <input
                type="number"
                min="1"
                max="25"
                step="0.5"
                value={costOfDebtPct}
                onChange={(e) => setCostOfDebtPct(Math.max(1, Number(e.target.value)))}
                className="w-12 bg-slate-900 text-emerald-400 text-right px-1 py-0.5 rounded font-mono font-bold border border-slate-700 focus:outline-none"
              />
              <span className="text-slate-400">%</span>
            </div>
            <button
              onClick={handleResetSimulator}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg border border-slate-600 transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset</span>
            </button>
          </div>
        </div>

        {/* Sliders Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Slider 1: DSO */}
          <div className="bg-slate-800/70 border border-slate-700/90 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-slate-200">1. Receivables DSO Lever</span>
                <p className="text-[11px] text-slate-400">Collections velocity acceleration</p>
              </div>
              <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                deltaDSO < 0 ? 'bg-emerald-500/20 text-emerald-300' : deltaDSO > 0 ? 'bg-rose-500/20 text-rose-300' : 'bg-slate-700 text-slate-300'
              }`}>
                {deltaDSO > 0 ? `+${deltaDSO}` : deltaDSO} Days ({simDSO}d)
              </span>
            </div>

            <input
              type="range"
              min="-30"
              max="30"
              step="1"
              value={deltaDSO}
              onChange={(e) => setDeltaDSO(Number(e.target.value))}
              className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
            />
            <div className="flex justify-between text-[10px] text-slate-400 font-mono">
              <span>-30d (Faster Collection)</span>
              <span>0d</span>
              <span>+30d (Delayed)</span>
            </div>

            <div className="pt-2 border-t border-slate-700/60 flex items-center justify-between text-xs font-mono">
              <span className="text-slate-400">Liquidity Impact:</span>
              <span className={`font-bold ${cashFromDSO >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {cashFromDSO >= 0 ? `+₹ ${Math.round(cashFromDSO)} Cr Released` : `-₹ ${Math.abs(Math.round(cashFromDSO))} Cr Trapped`}
              </span>
            </div>
          </div>

          {/* Slider 2: DIO */}
          <div className="bg-slate-800/70 border border-slate-700/90 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-slate-200">2. Inventory DIO Lever</span>
                <p className="text-[11px] text-slate-400">Lean manufacturing & JIT turnover</p>
              </div>
              <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                deltaDIO < 0 ? 'bg-emerald-500/20 text-emerald-300' : deltaDIO > 0 ? 'bg-rose-500/20 text-rose-300' : 'bg-slate-700 text-slate-300'
              }`}>
                {deltaDIO > 0 ? `+${deltaDIO}` : deltaDIO} Days ({simDIO}d)
              </span>
            </div>

            <input
              type="range"
              min="-30"
              max="30"
              step="1"
              value={deltaDIO}
              onChange={(e) => setDeltaDIO(Number(e.target.value))}
              className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
            />
            <div className="flex justify-between text-[10px] text-slate-400 font-mono">
              <span>-30d (Lean Stock)</span>
              <span>0d</span>
              <span>+30d (Buildup)</span>
            </div>

            <div className="pt-2 border-t border-slate-700/60 flex items-center justify-between text-xs font-mono">
              <span className="text-slate-400">Liquidity Impact:</span>
              <span className={`font-bold ${cashFromDIO >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {cashFromDIO >= 0 ? `+₹ ${Math.round(cashFromDIO)} Cr Released` : `-₹ ${Math.abs(Math.round(cashFromDIO))} Cr Trapped`}
              </span>
            </div>
          </div>

          {/* Slider 3: DPO */}
          <div className="bg-slate-800/70 border border-slate-700/90 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-slate-200">3. Payables DPO Lever</span>
                <p className="text-[11px] text-slate-400">Vendor payment terms & trade credit</p>
              </div>
              <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                deltaDPO > 0 ? 'bg-emerald-500/20 text-emerald-300' : deltaDPO < 0 ? 'bg-rose-500/20 text-rose-300' : 'bg-slate-700 text-slate-300'
              }`}>
                {deltaDPO > 0 ? `+${deltaDPO}` : deltaDPO} Days ({simDPO}d)
              </span>
            </div>

            <input
              type="range"
              min="-30"
              max="30"
              step="1"
              value={deltaDPO}
              onChange={(e) => setDeltaDPO(Number(e.target.value))}
              className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-purple-500"
            />
            <div className="flex justify-between text-[10px] text-slate-400 font-mono">
              <span>-30d (Early Payment)</span>
              <span>0d</span>
              <span>+30d (Extended Terms)</span>
            </div>

            <div className="pt-2 border-t border-slate-700/60 flex items-center justify-between text-xs font-mono">
              <span className="text-slate-400">Liquidity Impact:</span>
              <span className={`font-bold ${cashFromDPO >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {cashFromDPO >= 0 ? `+₹ ${Math.round(cashFromDPO)} Cr Released` : `-₹ ${Math.abs(Math.round(cashFromDPO))} Cr Trapped`}
              </span>
            </div>
          </div>
        </div>

        {/* Live Simulation Results Banner */}
        <div className="bg-slate-900/90 border border-emerald-500/40 rounded-xl p-5 grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <div className="text-[11px] text-slate-400 font-medium">New Simulated CCC</div>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-2xl font-black font-mono text-emerald-400">{simCCC}</span>
              <span className="text-xs font-bold text-slate-400">Days</span>
              <span className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded ${
                deltaCCC < 0 ? 'bg-emerald-500/20 text-emerald-300' : deltaCCC > 0 ? 'bg-rose-500/20 text-rose-300' : 'text-slate-400'
              }`}>
                {deltaCCC < 0 ? `${deltaCCC}d` : `+${deltaCCC}d`}
              </span>
            </div>
            <p className="text-[10px] text-slate-400 mt-1">Baseline was {baselineCCC} days</p>
          </div>

          <div>
            <div className="text-[11px] text-slate-400 font-medium">Total Liquidity Unlocked</div>
            <div className="flex items-baseline gap-2 mt-1">
              <span className={`text-2xl font-black font-mono ${totalCashUnlocked >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {totalCashUnlocked >= 0 ? `+₹ ${totalCashUnlocked.toLocaleString('en-IN')}` : `-₹ ${Math.abs(totalCashUnlocked).toLocaleString('en-IN')}`}
              </span>
              <span className="text-xs font-bold text-slate-400">Cr</span>
            </div>
            <p className="text-[10px] text-slate-400 mt-1">Direct liquid cash released into treasury</p>
          </div>

          <div>
            <div className="text-[11px] text-slate-400 font-medium">Annual Interest Savings (@ {costOfDebtPct}%)</div>
            <div className="flex items-baseline gap-2 mt-1">
              <span className={`text-2xl font-black font-mono ${annualizedInterestSavings >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {annualizedInterestSavings >= 0 ? `+₹ ${annualizedInterestSavings.toLocaleString('en-IN')}` : `-₹ ${Math.abs(annualizedInterestSavings).toLocaleString('en-IN')}`}
              </span>
              <span className="text-xs font-bold text-slate-400">Cr / yr</span>
            </div>
            <p className="text-[10px] text-slate-400 mt-1">Reduction in working capital debt service</p>
          </div>

          <div>
            <div className="text-[11px] text-slate-400 font-medium">Net Profit (PAT) Expansion</div>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-2xl font-black font-mono text-purple-300">
                ₹ {newPATRunRate.toLocaleString('en-IN')}
              </span>
              <span className="text-xs font-bold text-purple-400">Cr</span>
              <span className="text-xs font-mono font-bold bg-purple-500/20 text-purple-300 px-1.5 py-0.5 rounded">
                +{patBoostPct.toFixed(1)}%
              </span>
            </div>
            <p className="text-[10px] text-slate-400 mt-1">Enhanced bottom-line earnings power</p>
          </div>
        </div>
      </div>

      {/* Free Cash Flow Waterfall Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Layers className="w-4 h-4 text-emerald-600" />
                <span>Free Cash Flow to Firm (FCFF) & Equity (FCFE) Waterfall Bridge</span>
              </h3>
              <p className="text-xs text-slate-500">
                Annualized cash conversion step-through from Operating EBITDA to FCFE
              </p>
            </div>
            <span className="text-xs font-mono font-bold bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
              Run-Rate Annualized
            </span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={fcfWaterfallData} margin={{ top: 15, right: 20, left: 20, bottom: 25 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                <XAxis
                  dataKey="step"
                  tick={{ fontSize: 10, fill: '#64748B' }}
                  interval={0}
                  angle={-15}
                  textAnchor="end"
                />
                <YAxis
                  tick={{ fontSize: 10, fill: '#64748B' }}
                  tickFormatter={(v) => `₹${v}`}
                />
                <Tooltip
                  formatter={(val: any) => [`₹ ${Number(val).toLocaleString('en-IN')} Cr`, 'Value']}
                  contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                />
                <Bar dataKey="amount" radius={[4, 4, 0, 0]}>
                  {fcfWaterfallData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-3 gap-3 pt-3 border-t border-slate-100 text-center text-xs font-mono">
            <div className="bg-slate-50 p-2 rounded-lg">
              <span className="text-slate-500 block text-[10px]">Operating EBITDA</span>
              <span className="font-bold text-slate-900">{formatVal(annualEbitda)}</span>
            </div>
            <div className="bg-emerald-50 p-2 rounded-lg">
              <span className="text-emerald-700 block text-[10px]">FCFF (Firm Cash Flow)</span>
              <span className="font-bold text-emerald-800">{formatVal(baselineFCFF)}</span>
            </div>
            <div className="bg-blue-50 p-2 rounded-lg">
              <span className="text-blue-700 block text-[10px]">FCFE (Equity Cash Flow)</span>
              <span className="font-bold text-blue-800">{formatVal(baselineFCFE)}</span>
            </div>
          </div>
        </div>

        {/* Diagnostics & Risk Warnings Card */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4">
          <div className="border-b border-slate-100 pb-3">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-blue-600" />
              <span>Working Capital Health Diagnostics</span>
            </h3>
            <p className="text-xs text-slate-500">Automated liquidity & stress alerts</p>
          </div>

          <div className="space-y-3">
            <div className={`p-3 rounded-lg border text-xs ${
              baselineDSO > 75 ? 'bg-amber-50 border-amber-200 text-amber-900' : 'bg-emerald-50 border-emerald-200 text-emerald-900'
            }`}>
              <div className="flex items-center justify-between font-bold">
                <span>Receivables Velocity (DSO)</span>
                <span>{baselineDSO} Days</span>
              </div>
              <p className="text-[11px] mt-1 opacity-90">
                {baselineDSO > 75 ? 'DSO is stretched above 75 days. Active focus needed on customer collections.' : 'Debtors turnaround is within efficient norms (<75 days).'}
              </p>
            </div>

            <div className={`p-3 rounded-lg border text-xs ${
              baselineDIO > 60 ? 'bg-amber-50 border-amber-200 text-amber-900' : 'bg-emerald-50 border-emerald-200 text-emerald-900'
            }`}>
              <div className="flex items-center justify-between font-bold">
                <span>Inventory Holding (DIO)</span>
                <span>{baselineDIO} Days</span>
              </div>
              <p className="text-[11px] mt-1 opacity-90">
                {baselineDIO > 60 ? 'Inventory holding cycle is elevated. Monitor raw material hoarding and obsolescence.' : 'Lean inventory turnover supporting quick cash generation.'}
              </p>
            </div>

            <div className={`p-3 rounded-lg border text-xs ${
              baselineDPO > 90 ? 'bg-blue-50 border-blue-200 text-blue-900' : 'bg-slate-50 border-slate-200 text-slate-700'
            }`}>
              <div className="flex items-center justify-between font-bold">
                <span>Supplier Credit Leverage (DPO)</span>
                <span>{baselineDPO} Days</span>
              </div>
              <p className="text-[11px] mt-1 opacity-90">
                {baselineDPO > 90 ? 'High trade payable terms provides strong non-interest financing.' : 'Standard vendor credit settlement cycle.'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Sector Peer Working Capital Benchmarking Table */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Coins className="w-4 h-4 text-emerald-600" />
              <span>{company.sector} Sector: Cash Conversion Cycle Peer Benchmarks</span>
            </h3>
            <p className="text-xs text-slate-500">
              Ranked from lowest Cash Conversion Cycle (fastest cash generator) to highest
            </p>
          </div>
          <span className="text-xs font-mono font-bold bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
            {sectorPeers.length} Peer Companies
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3">Company</th>
                <th className="py-2.5 px-3">NSE Ticker</th>
                <th className="py-2.5 px-3 text-right">DSO (Days)</th>
                <th className="py-2.5 px-3 text-right">DIO (Days)</th>
                <th className="py-2.5 px-3 text-right">DPO (Days)</th>
                <th className="py-2.5 px-3 text-right">CCC (Days)</th>
                <th className="py-2.5 px-3 text-right">Net Working Capital</th>
                <th className="py-2.5 px-3 text-right">NWC / Sales %</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono">
              {sectorPeers.map((peer, idx) => {
                const isSelected = peer.bseCode === company.bseCode;
                return (
                  <tr
                    key={peer.bseCode}
                    onClick={() => onSelectCompany && onSelectCompany(peer.bseCode)}
                    className={`cursor-pointer transition-colors ${
                      isSelected ? 'bg-emerald-50/80 font-bold text-emerald-950' : 'hover:bg-slate-50 text-slate-700'
                    }`}
                  >
                    <td className="py-2 px-3 flex items-center gap-2">
                      <span className="text-[10px] w-4 text-slate-400 font-normal">#{idx + 1}</span>
                      <span className="font-sans font-medium">{peer.name}</span>
                      {isSelected && (
                        <span className="text-[9px] bg-emerald-600 text-white px-1.5 py-0.2 rounded font-bold">
                          ACTIVE
                        </span>
                      )}
                    </td>
                    <td className="py-2 px-3 font-semibold text-slate-900">{peer.nseCode}</td>
                    <td className="py-2 px-3 text-right">{peer.dsoVal}d</td>
                    <td className="py-2 px-3 text-right">{peer.dioVal}d</td>
                    <td className="py-2 px-3 text-right">{peer.dpoVal}d</td>
                    <td className="py-2 px-3 text-right font-bold">
                      <span className={`px-2 py-0.5 rounded ${
                        peer.cccVal <= 30 ? 'bg-emerald-100 text-emerald-800' : peer.cccVal <= 75 ? 'bg-blue-100 text-blue-800' : 'bg-rose-100 text-rose-800'
                      }`}>
                        {peer.cccVal}d
                      </span>
                    </td>
                    <td className="py-2 px-3 text-right">{formatVal(peer.nwcVal)}</td>
                    <td className="py-2 px-3 text-right">{peer.nwcToSales.toFixed(1)}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
