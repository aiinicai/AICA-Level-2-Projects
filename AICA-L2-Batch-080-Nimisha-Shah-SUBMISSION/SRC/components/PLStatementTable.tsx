import React from 'react';
import { 
  FileSpreadsheet, 
  TrendingUp, 
  TrendingDown, 
  ShieldCheck, 
  AlertCircle,
  HelpCircle,
  PieChart as PieIcon,
  CheckCircle2,
  Sparkles
} from 'lucide-react';
import { CompanyEntity, DeterministicMetrics, CurrencyUnit, PeriodId } from '../types/finance';
import { formatCurrency, formatPercent } from '../utils/financialCalculations';

interface PLStatementTableProps {
  company: CompanyEntity;
  metrics: DeterministicMetrics;
  periodId: PeriodId;
  currencyUnit: CurrencyUnit;
}

export const PLStatementTable: React.FC<PLStatementTableProps> = ({
  company,
  metrics,
  periodId,
  currencyUnit
}) => {
  const plData = company.periods[periodId]?.pl || company.periods['Q4 FY25'].pl;
  const rev = plData.revenueFromOperations;
  const prevRev = plData.prevYearRevenue || (rev * 0.9);

  // Helper to compute YoY line items
  const calcRow = (label: string, curVal: number, isNegativeCost: boolean = false, isSubtotal: boolean = false) => {
    const pctOfSales = rev > 0 ? (curVal / rev) * 100 : 0;
    // Approximated prior year for line item based on YoY trend
    const estPrevVal = curVal / (1 + (metrics.salesYoYGrowth / 100));
    const yoyGrowth = estPrevVal !== 0 ? ((curVal - estPrevVal) / Math.abs(estPrevVal)) * 100 : 0;

    return {
      label,
      curVal,
      estPrevVal,
      pctOfSales,
      yoyGrowth,
      isNegativeCost,
      isSubtotal
    };
  };

  const plRows = [
    calcRow('1. Revenue from Operations', plData.revenueFromOperations, false, true),
    calcRow('2. Other Income (Treasury / Non-Ops)', plData.otherIncome, false, false),
    calcRow('3. Total Revenue (1 + 2)', plData.totalRevenue || (plData.revenueFromOperations + plData.otherIncome), false, true),
    calcRow('4. EXPENSES:', 0, false, false),
    calcRow('   (a) Cost of Materials Consumed', plData.costOfMaterialsConsumed, true, false),
    calcRow('   (b) Purchase of Stock-in-Trade', plData.purchaseOfStockInTrade, true, false),
    calcRow('   (c) Changes in Inventories of Finished Goods', plData.changesInInventories, true, false),
    calcRow('   (d) Employee Benefit Expenses', plData.employeeBenefitExpenses, true, false),
    calcRow('   (e) Other Operating Expenses', plData.otherExpenses, true, false),
    calcRow('5. Total Operating Expenses (a + b + c + d + e)', metrics.totalOperatingCosts, true, true),
    calcRow('6. Operating EBITDA (1 - 5)', metrics.ebitda, false, true),
    calcRow('7. Depreciation and Amortization Expense', plData.depreciationAndAmortization, true, false),
    calcRow('8. Operating Profit / EBIT (6 + 2 - 7)', metrics.ebit, false, true),
    calcRow('9. Finance Costs (Gross Interest Charges)', plData.financeCosts, true, false),
    calcRow('10. Profit Before Exceptional Items and Tax (8 - 9)', metrics.ebt, false, true),
    calcRow('11. Tax Expense (Current + Deferred)', plData.taxExpense, true, false),
    calcRow('12. Net Profit for the Period (PAT) (10 - 11)', metrics.pat, false, true),
  ];

  const earningsQualityRating = () => {
    const otherIncShare = metrics.otherIncomeToPATShare;
    if (otherIncShare < 15) {
      return {
        label: 'HIGH QUALITY (Core Operating Dominant)',
        desc: 'Over 85% of bottomline generated from core operating operations. Strong cashflow sustainability.',
        color: 'text-emerald-400',
        badgeBg: 'bg-emerald-950/80 border-emerald-500/30'
      };
    } else if (otherIncShare < 35) {
      return {
        label: 'MODERATE QUALITY (Balanced Core & Treasury)',
        desc: 'Treasury / non-operating yields contribute moderate share to bottomline.',
        color: 'text-blue-400',
        badgeBg: 'bg-blue-950/80 border-blue-500/30'
      };
    } else {
      return {
        label: 'DILUTED QUALITY (Heavy Non-Operating Reliance)',
        desc: 'Substantial portion of quarterly earnings derived from other income rather than operations.',
        color: 'text-amber-400',
        badgeBg: 'bg-amber-950/80 border-amber-500/30'
      };
    }
  };

  const quality = earningsQualityRating();

  return (
    <div className="space-y-6">
      {/* Earnings Quality Diagnostic Panel */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 pb-4 border-b border-gray-800">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <PieIcon className="w-4 h-4 text-purple-400" />
              <span>Earnings Quality Diagnostic & Core Profit Integrity</span>
            </h2>
            <p className="text-xs text-gray-400">
              Evaluating core operating engine vs non-operating windfall dependence
            </p>
          </div>

          <div className={`px-3 py-1.5 rounded-lg border text-xs font-semibold ${quality.badgeBg} ${quality.color}`}>
            {quality.label}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
          <div className="bg-[#0B0F19] border border-gray-800 rounded-lg p-3.5 space-y-1">
            <span className="text-[11px] font-mono text-gray-400 uppercase">Core Operating EBITDA</span>
            <div className="text-xl font-bold text-white font-mono">
              {formatCurrency(metrics.ebitda, currencyUnit)}
            </div>
            <span className="text-[11px] text-cyan-400 font-mono">
              OPM: {formatPercent(metrics.opmPercent, 1)} of Sales
            </span>
          </div>

          <div className="bg-[#0B0F19] border border-gray-800 rounded-lg p-3.5 space-y-1">
            <span className="text-[11px] font-mono text-gray-400 uppercase">Other / Treasury Income</span>
            <div className="text-xl font-bold text-blue-400 font-mono">
              {formatCurrency(metrics.otherIncome, currencyUnit)}
            </div>
            <span className="text-[11px] text-gray-400 font-mono">
              {formatPercent(metrics.otherIncomeToPATShare, 1)} of Net Profit
            </span>
          </div>

          <div className="bg-[#0B0F19] border border-gray-800 rounded-lg p-3.5 space-y-1">
            <span className="text-[11px] font-mono text-gray-400 uppercase">Core Operating Share</span>
            <div className="text-xl font-bold text-emerald-400 font-mono">
              {formatPercent(metrics.coreOperatingProfitShare, 1)}
            </div>
            <span className="text-[11px] text-gray-400 font-mono">
              Operational engine ratio
            </span>
          </div>
        </div>

        {/* Quality breakdown progress bar */}
        <div className="mt-4 space-y-1.5">
          <div className="flex justify-between text-xs font-mono text-gray-400">
            <span className="text-cyan-400">Core Operating Profit: {formatPercent(metrics.coreOperatingProfitShare, 1)}</span>
            <span className="text-blue-400">Other Income: {formatPercent(100 - metrics.coreOperatingProfitShare, 1)}</span>
          </div>
          <div className="w-full h-2.5 bg-gray-800 rounded-full overflow-hidden flex">
            <div 
              className="bg-gradient-to-r from-cyan-500 to-blue-500 h-full" 
              style={{ width: `${Math.min(100, Math.max(5, metrics.coreOperatingProfitShare))}%` }}
            ></div>
            <div 
              className="bg-indigo-500 h-full" 
              style={{ width: `${Math.max(0, 100 - metrics.coreOperatingProfitShare)}%` }}
            ></div>
          </div>
          <p className="text-xs text-gray-400 font-sans italic pt-1">
            {quality.desc}
          </p>
        </div>
      </div>

      {/* Structured Multi-Column P&L Table */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg overflow-hidden">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-4 border-b border-gray-800">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <FileSpreadsheet className="w-4 h-4 text-blue-400" />
              <span>Multi-Period Profit & Loss Statement ({periodId})</span>
            </h2>
            <p className="text-xs text-gray-400">
              Deterministic line-item financial accounting table in ₹ Crores and % of Operations
            </p>
          </div>

          <span className="text-xs font-mono text-gray-400 bg-gray-900 px-2.5 py-1 rounded border border-gray-800">
            Entities: {company.name}
          </span>
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400 uppercase text-[10px] tracking-wider bg-gray-900/80">
                <th className="py-3 px-4">Line Item Description</th>
                <th className="py-3 px-4 text-right">{periodId} Amount ({currencyUnit === 'INR_CRORE' ? '₹ Cr' : currencyUnit === 'INR_LAKH' ? '₹ Lakh' : '$M'})</th>
                <th className="py-3 px-4 text-right">% of Sales</th>
                <th className="py-3 px-4 text-right">Prior Year Est.</th>
                <th className="py-3 px-4 text-right">YoY Delta %</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60">
              {plRows.map((r, idx) => {
                if (r.curVal === 0 && r.label.includes('EXPENSES:')) {
                  return (
                    <tr key={idx} className="bg-gray-900/40 font-bold text-gray-300">
                      <td colSpan={5} className="py-2.5 px-4 uppercase text-[11px] tracking-wider text-blue-300">
                        {r.label}
                      </td>
                    </tr>
                  );
                }

                return (
                  <tr 
                    key={idx} 
                    className={`hover:bg-gray-800/40 transition-colors ${
                      r.isSubtotal 
                        ? 'bg-gray-900/50 font-bold text-white border-t border-gray-700/60' 
                        : 'text-gray-300'
                    }`}
                  >
                    <td className={`py-2.5 px-4 font-sans ${r.isSubtotal ? 'font-semibold text-white' : 'text-gray-300'}`}>
                      {r.label}
                    </td>
                    <td className={`py-2.5 px-4 text-right font-bold ${
                      r.isSubtotal ? 'text-cyan-300' : 'text-slate-100'
                    }`}>
                      {formatCurrency(r.curVal, currencyUnit)}
                    </td>
                    <td className="py-2.5 px-4 text-right text-gray-400">
                      {r.pctOfSales.toFixed(1)}%
                    </td>
                    <td className="py-2.5 px-4 text-right text-gray-500">
                      {formatCurrency(r.estPrevVal, currencyUnit, false)}
                    </td>
                    <td className="py-2.5 px-4 text-right">
                      {r.yoyGrowth >= 0 ? (
                        <span className="text-emerald-400 flex items-center justify-end gap-0.5">
                          <TrendingUp className="w-3 h-3" />
                          +{r.yoyGrowth.toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-rose-400 flex items-center justify-end gap-0.5">
                          <TrendingDown className="w-3 h-3" />
                          {r.yoyGrowth.toFixed(1)}%
                        </span>
                      )}
                    </td>
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
