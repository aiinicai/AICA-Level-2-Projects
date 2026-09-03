import React from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle, 
  CheckCircle2, 
  Scissors, 
  BarChart2, 
  Layers, 
  Lightbulb,
  ArrowRight
} from 'lucide-react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  Cell, 
  Legend 
} from 'recharts';
import { CompanyEntity, DeterministicMetrics, CurrencyUnit, PeriodId } from '../types/finance';
import { formatCurrency, formatPercent } from '../utils/financialCalculations';

interface OperatingScissorsViewProps {
  company: CompanyEntity;
  metrics: DeterministicMetrics;
  periodId: PeriodId;
  currencyUnit: CurrencyUnit;
}

export const OperatingScissorsView: React.FC<OperatingScissorsViewProps> = ({
  company,
  metrics,
  periodId,
  currencyUnit
}) => {
  const pl = company.periods[periodId]?.pl || company.periods['Q4 FY25'].pl;

  const salesGrowth = metrics.salesYoYGrowth;
  const patGrowth = metrics.patYoYGrowth;
  const ebitdaGrowth = metrics.ebitdaYoYGrowth;
  const scissorsGap = metrics.operatingScissorsGap;
  const hasNegativeScissors = metrics.hasNegativeScissors;

  const growthComparisonData = [
    { metric: 'Topline Revenue', growth: salesGrowth, color: '#3B82F6' },
    { metric: 'Operating EBITDA', growth: ebitdaGrowth, color: '#06B6D4' },
    { metric: 'Bottomline PAT', growth: patGrowth, color: patGrowth >= 0 ? '#10B981' : '#EF4444' }
  ];

  // Cost Drivers Analysis
  const costDrivers = [
    {
      driver: 'Raw Materials & Input COGS',
      amount: metrics.rawMaterialCost,
      share: (metrics.rawMaterialCost / Math.max(1, metrics.revenue)) * 100,
      riskImpact: metrics.rawMaterialCost > metrics.revenue * 0.5 ? 'HIGH SENSITIVITY' : 'CONTROLLED',
      commentary: 'Direct sensitivity to global commodity price swings and supply chain freight.'
    },
    {
      driver: 'Employee & Talent Overhead',
      amount: metrics.employeeCost,
      share: (metrics.employeeCost / Math.max(1, metrics.revenue)) * 100,
      riskImpact: metrics.employeeCost > metrics.revenue * 0.18 ? 'ELEVATED' : 'MODERATE',
      commentary: 'Wage increments, performance bonuses, and skill retention overhead.'
    },
    {
      driver: 'Other Operating Expenses (SG&A)',
      amount: metrics.otherOperatingExpenses,
      share: (metrics.otherOperatingExpenses / Math.max(1, metrics.revenue)) * 100,
      riskImpact: metrics.otherOperatingExpenses > metrics.revenue * 0.15 ? 'WATCHLIST' : 'OPTIMAL',
      commentary: 'Power & utilities, brand marketing, logistical freight, admin overhead.'
    },
    {
      driver: 'Gross Finance Costs',
      amount: metrics.financeCosts,
      share: (metrics.financeCosts / Math.max(1, metrics.revenue)) * 100,
      riskImpact: metrics.financeCosts > metrics.ebit * 0.4 ? 'HEAVY BURDEN' : 'SAFE',
      commentary: 'Debt servicing drag reducing conversion of operating profit into net profit.'
    }
  ];

  return (
    <div className="space-y-6">
      {/* Operating Scissors Diagnostic Banner */}
      <div className={`border rounded-xl p-5 shadow-lg relative overflow-hidden ${
        hasNegativeScissors 
          ? 'bg-gradient-to-r from-red-950/40 via-red-900/20 to-[#111827] border-red-500/40' 
          : 'bg-gradient-to-r from-emerald-950/40 via-emerald-900/20 to-[#111827] border-emerald-500/40'
      }`}>
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <Scissors className={`w-5 h-5 ${hasNegativeScissors ? 'text-red-400 rotate-90' : 'text-emerald-400'}`} />
              <h2 className="text-lg font-bold text-white">
                {hasNegativeScissors ? 'CRITICAL ALERT: Negative Operating Scissors Detected' : 'POSITIVE: Operating Scissors In Sync / Margin Expansion'}
              </h2>
            </div>
            <p className="text-xs text-gray-300 max-w-3xl">
              {hasNegativeScissors
                ? `Revenue is expanding at ${formatPercent(salesGrowth, 1, true)} YoY while PAT is contracting/diverging at ${formatPercent(patGrowth, 1, true)} YoY (Scissors Gap: ${scissorsGap.toFixed(1)}%). Indicates severe operational margin compression or escalating cost overhead.`
                : `Topline revenue growth (${formatPercent(salesGrowth, 1, true)}) and bottomline PAT growth (${formatPercent(patGrowth, 1, true)}) reflect healthy operating leverage and profit conversion.`}
            </p>
          </div>

          <div className={`px-4 py-2 rounded-lg border text-xs font-mono font-bold shrink-0 ${
            hasNegativeScissors
              ? 'bg-red-900/80 text-red-200 border-red-500'
              : 'bg-emerald-900/80 text-emerald-200 border-emerald-500'
          }`}>
            Gap: {scissorsGap.toFixed(1)}% {hasNegativeScissors ? 'Adverse' : 'Favorable'}
          </div>
        </div>
      </div>

      {/* Growth Comparison Chart & Strategic Attribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* YoY Growth Comparison Bar Chart */}
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <BarChart2 className="w-4 h-4 text-blue-400" />
            <span>YoY Growth Breakdown: Topline vs EBITDA vs Bottomline</span>
          </h3>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={growthComparisonData} margin={{ top: 20, right: 20, left: 10, bottom: 20 }}>
                <XAxis dataKey="metric" stroke="#9CA3AF" fontSize={11} tickLine={false} />
                <YAxis stroke="#9CA3AF" fontSize={11} tickFormatter={(v) => `${v}%`} />
                <Tooltip 
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      return (
                        <div className="bg-[#0B0F19] border border-gray-700 p-2.5 rounded shadow-lg text-xs font-mono">
                          <div className="text-white font-bold">{data.metric}</div>
                          <div className="text-sm font-bold mt-1" style={{ color: data.color }}>
                            YoY Growth: {formatPercent(data.growth, 2, true)}
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Bar dataKey="growth" radius={[4, 4, 0, 0]}>
                  {growthComparisonData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-3 gap-2 pt-2 border-t border-gray-800 text-center font-mono">
            <div className="p-2 bg-[#0B0F19] rounded">
              <span className="text-[10px] text-gray-400 block">Sales YoY</span>
              <span className="text-xs font-bold text-blue-400">{formatPercent(salesGrowth, 1, true)}</span>
            </div>
            <div className="p-2 bg-[#0B0F19] rounded">
              <span className="text-[10px] text-gray-400 block">EBITDA YoY</span>
              <span className="text-xs font-bold text-cyan-400">{formatPercent(ebitdaGrowth, 1, true)}</span>
            </div>
            <div className="p-2 bg-[#0B0F19] rounded">
              <span className="text-[10px] text-gray-400 block">PAT YoY</span>
              <span className={`text-xs font-bold ${patGrowth >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {formatPercent(patGrowth, 1, true)}
              </span>
            </div>
          </div>
        </div>

        {/* CFO Strategic Remediation Plan */}
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Lightbulb className="w-4 h-4 text-amber-400" />
            <span>CFO Margin Defense & Remediation Playbook</span>
          </h3>

          <div className="space-y-3 text-xs">
            <div className="p-3 bg-[#0B0F19] border border-gray-800 rounded-lg space-y-1">
              <div className="font-semibold text-blue-300 flex items-center gap-1.5">
                <ArrowRight className="w-3.5 h-3.5" />
                1. Value Pricing & Product Mix Optimization
              </div>
              <p className="text-gray-400 text-[11px] leading-relaxed">
                Pass through input price inflation via indexed customer pricing contracts and accelerate higher-margin premium product lines.
              </p>
            </div>

            <div className="p-3 bg-[#0B0F19] border border-gray-800 rounded-lg space-y-1">
              <div className="font-semibold text-cyan-300 flex items-center gap-1.5">
                <ArrowRight className="w-3.5 h-3.5" />
                2. Direct Procurement & Vendor Rationalization
              </div>
              <p className="text-gray-400 text-[11px] leading-relaxed">
                Consolidate supplier volumes, establish long-term fixed hedging contracts for volatile raw materials, and streamline inbound logistics.
              </p>
            </div>

            <div className="p-3 bg-[#0B0F19] border border-gray-800 rounded-lg space-y-1">
              <div className="font-semibold text-purple-300 flex items-center gap-1.5">
                <ArrowRight className="w-3.5 h-3.5" />
                3. Fixed Cost & SG&A Discipline
              </div>
              <p className="text-gray-400 text-[11px] leading-relaxed">
                Enforce strict zero-based budgeting (ZBB) on non-sales administrative costs and automate repetitive back-office workflows.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Cost Drivers Sensitivity Table */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg overflow-hidden">
        <h3 className="text-sm font-bold text-white flex items-center gap-2 pb-4 border-b border-gray-800">
          <Layers className="w-4 h-4 text-purple-400" />
          <span>Operational Cost Drivers & Margin Squeeze Attribution</span>
        </h3>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400 uppercase text-[10px] tracking-wider bg-gray-900/60">
                <th className="py-2.5 px-3">Expense Head / Driver</th>
                <th className="py-2.5 px-3 text-right">Quarterly Value</th>
                <th className="py-2.5 px-3 text-right">% of Revenue</th>
                <th className="py-2.5 px-3">Risk Sensitivity Status</th>
                <th className="py-2.5 px-3">Driver Attribution Insight</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60">
              {costDrivers.map((cd, idx) => (
                <tr key={idx} className="hover:bg-gray-800/40 transition-colors">
                  <td className="py-2.5 px-3 font-sans font-medium text-white">
                    {cd.driver}
                  </td>
                  <td className="py-2.5 px-3 text-right font-bold text-cyan-300">
                    {formatCurrency(cd.amount, currencyUnit)}
                  </td>
                  <td className="py-2.5 px-3 text-right text-gray-300">
                    {cd.share.toFixed(1)}%
                  </td>
                  <td className="py-2.5 px-3">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-gray-800 text-amber-300 border border-gray-700">
                      {cd.riskImpact}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-[11px] text-gray-400 font-sans">
                    {cd.commentary}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
