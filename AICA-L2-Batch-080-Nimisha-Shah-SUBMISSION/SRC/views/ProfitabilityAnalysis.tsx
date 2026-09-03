import React from 'react';
import { 
  FileSpreadsheet, 
  Layers, 
  TrendingUp, 
  TrendingDown, 
  AlertCircle, 
  CheckCircle2, 
  Sparkles,
  HelpCircle,
  Calendar
} from 'lucide-react';
import { ListedCompany, CurrencyCode, UnitScale } from '../types/financial';
import { convertCompanyToFinancialPeriods, getResolvedCompanyFinancials } from '../data/listedCompaniesDataset';
import { formatFinancialValue, getCurrencyUnitLabel } from '../utils/formatUtils';

interface ProfitabilityAnalysisProps {
  company: ListedCompany;
  selectedPeriod?: string;
  currency?: CurrencyCode;
  scale?: UnitScale;
}

export const ProfitabilityAnalysis: React.FC<ProfitabilityAnalysisProps> = ({ 
  company,
  selectedPeriod = 'latest',
  currency = 'INR',
  scale = 'crores'
}) => {
  const fin = getResolvedCompanyFinancials(company, selectedPeriod);
  const periods = convertCompanyToFinancialPeriods(company);
  const current = periods[0];
  const priorYear = periods[2];

  const formatVal = (val: number) => formatFinancialValue(val, currency, scale);

  const plRows = [
    { label: 'Revenue from Operations', key: 'revenue', activeVal: fin.sales, isHeader: true, isBold: true, isTotal: true },
    { label: 'Other Operating Income', key: 'otherIncome', activeVal: fin.otherIncome, indent: true },
    { label: 'Total Revenue / Income', key: 'totalIncome', activeVal: fin.sales + fin.otherIncome, isBold: true, isTotal: true },
    { label: 'Cost of Materials Consumed', key: 'rawMaterialCosts', activeVal: fin.costOfMaterials, indent: true },
    { label: 'Employee Benefit Expenses', key: 'employeeCosts', activeVal: fin.employeeExpenses, indent: true },
    { label: 'Other Operating Expenses', key: 'otherOperatingExpenses', activeVal: fin.otherOperatingExpenses, indent: true },
    { label: 'Operating EBITDA (Excl. Other Income)', key: 'ebitda', activeVal: fin.ebitda, isBold: true, isTotal: true, highlight: 'bg-emerald-50 text-emerald-900' },
    { label: 'Depreciation & Amortization', key: 'depreciation', activeVal: fin.depreciation, indent: true },
    { label: 'EBIT (Operating Profit)', key: 'ebit', activeVal: fin.ebit, isBold: true },
    { label: 'Finance Costs (Interest)', key: 'interest', activeVal: fin.financeCosts, indent: true },
    { label: 'Profit Before Tax (PBT)', key: 'ebt', activeVal: fin.pbt, isBold: true },
    { label: 'Tax Expense (Current & Deferred)', key: 'tax', activeVal: fin.taxExpense, indent: true },
    { label: 'Net Profit After Tax (PAT)', key: 'pat', activeVal: fin.pat, isBold: true, isTotal: true, highlight: 'bg-blue-50 text-blue-900' },
  ];

  const otherIncomeRatio = fin.otherIncomeShareOfEbidt;
  const isHighOtherIncome = otherIncomeRatio > 25;

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Earnings Quality Diagnostic Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Layers className="w-4 h-4 text-purple-600" />
              <span>Earnings Quality Diagnostic: {company.name}</span>
              <span className="text-xs font-mono font-bold bg-purple-50 text-purple-700 border border-purple-200 px-2 py-0.5 rounded-full flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                <span>{fin.periodLabel}</span>
              </span>
              <span className="text-xs font-mono font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full">
                {getCurrencyUnitLabel(currency, scale)}
              </span>
            </h2>
            <p className="text-xs text-slate-500">
              Core operating earnings vs non-operating treasury income sustainability
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono text-slate-500">Earnings Quality Rating:</span>
            <span className={`px-2.5 py-1 rounded-lg border text-xs font-bold font-mono ${
              !isHighOtherIncome ? 'bg-emerald-50 text-emerald-700 border-emerald-300' : 'bg-amber-50 text-amber-700 border-amber-300'
            }`}>
              {!isHighOtherIncome ? 'HIGH QUALITY (Core-Led)' : 'MODERATE QUALITY (Treasury Reliance)'}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
          <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg space-y-1">
            <span className="text-slate-500 uppercase text-[10px]">Operating EBITDA Margin</span>
            <div className="text-lg font-bold text-emerald-700">{fin.ebitdaMargin.toFixed(1)}%</div>
            <span className="text-[11px] text-slate-500">Pure operational throughput</span>
          </div>
          <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg space-y-1">
            <span className="text-slate-500 uppercase text-[10px]">Net Profit Margin (NPM)</span>
            <div className="text-lg font-bold text-blue-700">{fin.netProfitMargin.toFixed(1)}%</div>
            <span className="text-[11px] text-slate-500">Conversion after tax & interest</span>
          </div>
          <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg space-y-1">
            <span className="text-slate-500 uppercase text-[10px]">Other Income Share of EBITDA</span>
            <div className={`text-lg font-bold ${isHighOtherIncome ? 'text-amber-700' : 'text-slate-800'}`}>
              {otherIncomeRatio.toFixed(1)}%
            </div>
            <span className="text-[11px] text-slate-500">{isHighOtherIncome ? 'High treasury contribution' : 'Sustainable organic base'}</span>
          </div>
        </div>
      </div>

      {/* Multi-Period Ind-AS P&L Statement Table */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <FileSpreadsheet className="w-4 h-4 text-blue-600" />
              <span>Multi-Period Profit & Loss Statement (Ind-AS Format)</span>
            </h3>
            <p className="text-xs text-slate-500">
              Comparative financials in {getCurrencyUnitLabel(currency, scale)} and as % of Revenue
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 uppercase text-[10px] tracking-wider bg-slate-50">
                <th className="py-3 px-3">P&L Line Item</th>
                <th className="py-3 px-3 text-right bg-blue-50/50 text-blue-900 font-bold">
                  {fin.periodLabel}
                </th>
                <th className="py-3 px-3 text-right">% of Sales</th>
                <th className="py-3 px-3 text-right">Latest Quarter</th>
                <th className="py-3 px-3 text-right">Preceding Qtr</th>
                <th className="py-3 px-3 text-right">Prior Year Qtr</th>
                <th className="py-3 px-3 text-right">YoY Growth %</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {plRows.map((row, idx) => {
                const currentVal = row.activeVal;
                const latestQuarterVal = (current as any)[row.key] || 0;
                const prevVal = (periods[1] as any)[row.key] || 0;
                const pyVal = (priorYear as any)[row.key] || 0;
                const pctSales = fin.sales > 0 ? ((currentVal / fin.sales) * 100).toFixed(1) : '0.0';
                const yoyGrowth = pyVal > 0 ? (((latestQuarterVal - pyVal) / pyVal) * 100).toFixed(1) : '-';

                return (
                  <tr key={idx} className={`hover:bg-slate-50 transition-colors ${row.highlight || ''}`}>
                    <td className={`py-2.5 px-3 font-sans ${row.indent ? 'pl-6 text-slate-600 text-[11px]' : 'text-slate-900 font-semibold'}`}>
                      {row.label}
                    </td>
                    <td className="py-2.5 px-3 text-right font-bold text-slate-900 bg-blue-50/30">
                      {formatVal(currentVal)}
                    </td>
                    <td className="py-2.5 px-3 text-right text-slate-500">
                      {pctSales}%
                    </td>
                    <td className="py-2.5 px-3 text-right text-slate-600">
                      {formatVal(latestQuarterVal)}
                    </td>
                    <td className="py-2.5 px-3 text-right text-slate-600">
                      {formatVal(prevVal)}
                    </td>
                    <td className="py-2.5 px-3 text-right text-slate-600">
                      {formatVal(pyVal)}
                    </td>
                    <td className={`py-2.5 px-3 text-right font-bold ${
                      Number(yoyGrowth) >= 0 ? 'text-emerald-600' : 'text-rose-600'
                    }`}>
                      {yoyGrowth !== '-' ? `${Number(yoyGrowth) >= 0 ? '+' : ''}${yoyGrowth}%` : '-'}
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
