import React, { useState } from 'react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  Cell, 
  ReferenceLine 
} from 'recharts';
import { 
  ArrowDownRight, 
  ArrowUpRight, 
  Layers, 
  Percent, 
  HelpCircle, 
  Info,
  CheckCircle2
} from 'lucide-react';
import { DeterministicMetrics, CurrencyUnit } from '../types/finance';
import { formatCurrency, formatPercent } from '../utils/financialCalculations';

interface WaterfallBridgeProps {
  metrics: DeterministicMetrics;
  currencyUnit: CurrencyUnit;
}

export const WaterfallBridge: React.FC<WaterfallBridgeProps> = ({
  metrics,
  currencyUnit
}) => {
  const [viewMode, setViewMode] = useState<'chart' | 'table'>('chart');

  // Construct waterfall bridge steps
  const steps = [
    {
      name: 'Revenue (Ops)',
      category: 'start',
      amount: metrics.revenue,
      delta: metrics.revenue,
      pctOfSales: 100,
      color: '#3B82F6', // Blue
      tooltip: 'Gross revenue from operational business activities'
    },
    {
      name: 'Material & COGS',
      category: 'deduction',
      amount: -metrics.rawMaterialCost,
      delta: -metrics.rawMaterialCost,
      pctOfSales: (metrics.rawMaterialCost / Math.max(1, metrics.revenue)) * 100,
      color: '#EF4444', // Red
      tooltip: 'Raw material consumed, purchases of stock-in-trade & inventory adjustments'
    },
    {
      name: 'Employee Costs',
      category: 'deduction',
      amount: -metrics.employeeCost,
      delta: -metrics.employeeCost,
      pctOfSales: (metrics.employeeCost / Math.max(1, metrics.revenue)) * 100,
      color: '#F97316', // Orange
      tooltip: 'Salaries, wages, PF contributions, and staff welfare'
    },
    {
      name: 'Other Opex / SG&A',
      category: 'deduction',
      amount: -metrics.otherOperatingExpenses,
      delta: -metrics.otherOperatingExpenses,
      pctOfSales: (metrics.otherOperatingExpenses / Math.max(1, metrics.revenue)) * 100,
      color: '#EAB308', // Amber
      tooltip: 'Freight, power & fuel, repairs, sales commissions, admin overhead'
    },
    {
      name: 'EBITDA (Core)',
      category: 'subtotal',
      amount: metrics.ebitda,
      delta: metrics.ebitda,
      pctOfSales: (metrics.ebitda / Math.max(1, metrics.revenue)) * 100,
      color: '#06B6D4', // Cyan
      tooltip: 'Core operational earnings before other income, interest, tax & depreciation'
    },
    {
      name: 'Other Income',
      category: 'addition',
      amount: metrics.otherIncome,
      delta: metrics.otherIncome,
      pctOfSales: (metrics.otherIncome / Math.max(1, metrics.revenue)) * 100,
      color: '#10B981', // Green
      tooltip: 'Treasury yields, dividend from subsidiaries, forex gains'
    },
    {
      name: 'Depreciation (D&A)',
      category: 'deduction',
      amount: -metrics.depreciation,
      delta: -metrics.depreciation,
      pctOfSales: (metrics.depreciation / Math.max(1, metrics.revenue)) * 100,
      color: '#F43F5E', // Rose
      tooltip: 'Non-cash amortisation of tangible plant, property, equipment and intangibles'
    },
    {
      name: 'Finance Costs',
      category: 'deduction',
      amount: -metrics.financeCosts,
      delta: -metrics.financeCosts,
      pctOfSales: (metrics.financeCosts / Math.max(1, metrics.revenue)) * 100,
      color: '#DC2626', // Deep Red
      tooltip: 'Gross interest servicing charges on bank loans, bonds & working capital'
    },
    {
      name: 'Tax Provision',
      category: 'deduction',
      amount: -metrics.tax,
      delta: -metrics.tax,
      pctOfSales: (metrics.tax / Math.max(1, metrics.revenue)) * 100,
      color: '#A855F7', // Purple
      tooltip: `Effective corporate income tax (${formatPercent(metrics.effectiveTaxRate, 1)})`
    },
    {
      name: 'PAT (Bottomline)',
      category: 'end',
      amount: metrics.pat,
      delta: metrics.pat,
      pctOfSales: (metrics.pat / Math.max(1, metrics.revenue)) * 100,
      color: metrics.pat >= 0 ? '#10B981' : '#EF4444', // Green / Red
      tooltip: 'Net profit after all operating, financial and statutory tax deductions'
    }
  ];

  // Prepare chart data with base offset for Recharts waterfall floating effect
  let runningTotal = 0;
  const chartData = steps.map((item, idx) => {
    let base = 0;
    let barVal = Math.abs(item.amount);

    if (item.category === 'start' || item.category === 'subtotal' || item.category === 'end') {
      base = 0;
      barVal = Math.max(0, item.amount);
      if (item.category === 'start') runningTotal = item.amount;
      if (item.category === 'subtotal') runningTotal = item.amount;
      if (item.category === 'end') runningTotal = item.amount;
    } else if (item.category === 'deduction') {
      runningTotal += item.amount; // amount is negative
      base = runningTotal;
    } else if (item.category === 'addition') {
      base = runningTotal;
      runningTotal += item.amount;
    }

    return {
      name: item.name,
      base: Math.max(0, base),
      value: barVal,
      displayAmount: item.amount,
      pctOfSales: item.pctOfSales,
      color: item.color,
      category: item.category,
      tooltip: item.tooltip
    };
  });

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-4 border-b border-gray-800">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Layers className="w-4 h-4 text-blue-400" />
            <span>P&L Waterfall Bridge: Revenue to Net Profit Walk</span>
          </h2>
          <p className="text-xs text-gray-400">
            Step-by-step cost decomposition, operating margins, and profit retention
          </p>
        </div>

        {/* View mode toggle */}
        <div className="flex items-center bg-[#0B0F19] border border-gray-800 rounded-lg p-1 text-xs">
          <button
            onClick={() => setViewMode('chart')}
            className={`px-3 py-1 rounded transition-colors ${
              viewMode === 'chart'
                ? 'bg-blue-600 text-white font-medium shadow'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Visual Bridge
          </button>
          <button
            onClick={() => setViewMode('table')}
            className={`px-3 py-1 rounded transition-colors ${
              viewMode === 'table'
                ? 'bg-blue-600 text-white font-medium shadow'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Decomposition Table
          </button>
        </div>
      </div>

      {viewMode === 'chart' ? (
        <div className="mt-4">
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 20, right: 20, left: 20, bottom: 40 }}>
                <XAxis 
                  dataKey="name" 
                  stroke="#6B7280" 
                  fontSize={11} 
                  tickLine={false}
                  interval={0}
                  angle={-25}
                  textAnchor="end"
                />
                <YAxis 
                  stroke="#6B7280" 
                  fontSize={11}
                  tickFormatter={(val) => `₹${Math.round(val).toLocaleString('en-IN')}`}
                />
                <Tooltip 
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      return (
                        <div className="bg-[#0B0F19] border border-gray-700 p-3 rounded-lg shadow-xl text-xs font-mono">
                          <div className="font-bold text-white border-b border-gray-800 pb-1 mb-1.5 flex items-center justify-between gap-4">
                            <span>{data.name}</span>
                            <span className="text-[10px] px-1.5 py-0.5 rounded uppercase font-sans bg-gray-800 text-gray-300">
                              {data.category}
                            </span>
                          </div>
                          <div className="text-sm font-bold text-cyan-300">
                            {formatCurrency(data.displayAmount, currencyUnit)}
                          </div>
                          <div className="text-gray-400 text-[11px] mt-1">
                            % of Revenue: <strong className="text-white">{data.pctOfSales.toFixed(1)}%</strong>
                          </div>
                          <div className="text-[10px] text-gray-400 mt-1 font-sans italic">
                            {data.tooltip}
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                {/* Floating stack base */}
                <Bar dataKey="base" stackId="waterfall" fill="transparent" />
                {/* Visual bar element */}
                <Bar dataKey="value" stackId="waterfall" radius={[3, 3, 0, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Quick Bridge Legend */}
          <div className="flex flex-wrap items-center justify-center gap-4 text-xs text-gray-400 font-mono mt-2 pt-2 border-t border-gray-800/60">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-blue-500"></span> Topline Revenue
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-red-500"></span> Operating Costs
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-cyan-400"></span> Operating EBITDA
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-emerald-500"></span> Net Profit (PAT)
            </span>
          </div>
        </div>
      ) : (
        /* Detailed Decomposition Table */
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400 uppercase text-[10px] tracking-wider">
                <th className="py-2.5 px-3">Waterfall Stage</th>
                <th className="py-2.5 px-3">Nature / Class</th>
                <th className="py-2.5 px-3 text-right">Value ({currencyUnit === 'INR_CRORE' ? '₹ Cr' : currencyUnit === 'INR_LAKH' ? '₹ Lakh' : '$M'})</th>
                <th className="py-2.5 px-3 text-right">% of Revenue</th>
                <th className="py-2.5 px-3">Executive CFO Commentary</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60">
              {steps.map((s, idx) => (
                <tr 
                  key={idx} 
                  className={`hover:bg-gray-800/40 transition-colors ${
                    s.category === 'start' || s.category === 'subtotal' || s.category === 'end' 
                      ? 'bg-gray-900/60 font-semibold text-white' 
                      : 'text-gray-300'
                  }`}
                >
                  <td className="py-2.5 px-3 font-sans font-medium flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: s.color }}></span>
                    {s.name}
                  </td>
                  <td className="py-2.5 px-3 text-[11px] text-gray-400 uppercase font-sans">
                    {s.category}
                  </td>
                  <td className={`py-2.5 px-3 text-right font-bold ${
                    s.amount >= 0 ? 'text-emerald-400' : 'text-rose-400'
                  }`}>
                    {formatCurrency(s.amount, currencyUnit)}
                  </td>
                  <td className="py-2.5 px-3 text-right text-gray-300">
                    {s.pctOfSales.toFixed(1)}%
                  </td>
                  <td className="py-2.5 px-3 text-[11px] text-gray-400 font-sans">
                    {s.tooltip}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
