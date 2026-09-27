import React, { useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  HelpCircle,
  MessageSquare,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { BudgetExecutiveSummary } from '../engine/budgetEngine';
import { UserSession } from '../types';
import { formatINR } from '../utils/formatters';
import { EmptyWorkspaceState } from './EmptyWorkspaceState';

interface BudgetVsActualViewProps {
  summary: BudgetExecutiveSummary;
  currentUser?: UserSession;
  onSelectMonth?: (month: string) => void;
  onNavigateToTab?: (tab: string) => void;
}

export const BudgetVsActualView: React.FC<BudgetVsActualViewProps> = ({
  summary,
  currentUser,
  onSelectMonth,
  onNavigateToTab,
}) => {
  const [selectedMonth, setSelectedMonth] = useState(summary.month);
  // Persist commentary per reporting period using localStorage
  const COMMENTARY_KEY = `cfo_budget_commentary_${summary.month}`;
  const [managementCommentary, setManagementCommentary] = useState(
    () =>
      localStorage.getItem(COMMENTARY_KEY) ||
      'Departmental revenue variances are strictly traced to inpatient billing records and verified clinical services for the active reporting period.'
  );
  const [savedCommentary, setSavedCommentary] = useState(false);

  const handleMonthChange = (m: string) => {
    setSelectedMonth(m);
    onSelectMonth?.(m);
  };

  const handleSaveNotes = () => {
    // Persist to localStorage so commentary survives page refresh (F17 audit fix)
    localStorage.setItem(COMMENTARY_KEY, managementCommentary);
    setSavedCommentary(true);
    setTimeout(() => setSavedCommentary(false), 3000);
  };

  // Chart data for Department Revenue Variance
  const deptVarianceChartData = summary.departmentSummaries.map((d) => ({
    department: d.department,
    budget: d.revenueBudget,
    actual: d.revenueActual,
    variance: d.revenueVariance,
    variancePct: d.revenueVariancePercent,
    isSignificant: d.isSignificant,
  }));

  const userDisplayName = currentUser?.name || 'Authenticated Finance Officer';
  const userRoleDisplay = currentUser?.role || 'Finance User';

  if (summary.totalRevenueBudget === 0 && summary.totalRevenueActual === 0 && (!summary.departmentSummaries || summary.departmentSummaries.length === 0)) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">
            Budget vs Actual Operating Performance
          </h1>
          <p className="mt-1 text-xs text-slate-500">
            Departmental fiscal variances and actual billed hospital revenues benchmarked against verified budget records.
          </p>
        </div>
        <EmptyWorkspaceState
          title="No budget data available."
          description="Budget vs actual variance benchmarking requires both approved departmental budget allocations and actual billing extracts. Upload your fiscal budgets and billing records to analyze performance."
          badge="Budget Inactive"
          actionText="Upload Hospital Financial Extracts"
          onAction={() => onNavigateToTab?.('data-intelligence')}
          suggestedDatasets={[
            'Approved Departmental Budgets (Department, Month, Revenue_Budget, Expense_Budget)',
            'Billing Register & Invoices (Invoice_ID, Billed_Amount, Bill_Date)',
            'Clinical Services with Revenue Attribution',
          ]}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-slate-900">
                Budget vs Actual Operating Performance
              </h1>
              <span className="rounded bg-teal-50 px-2 py-0.5 text-[10px] font-bold tracking-wider text-teal-800 border border-teal-200 uppercase">
                Period: {summary.month}
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              Departmental fiscal variances and actual billed hospital revenues benchmarked against verified budget records.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 font-medium">Reporting Period:</span>
            <select
              value={selectedMonth}
              onChange={(e) => handleMonthChange(e.target.value)}
              className="border border-slate-300 rounded-md px-2.5 py-1 text-xs bg-white text-slate-900 font-semibold focus:outline-teal-600"
            >
              {summary.availableMonths && summary.availableMonths.length > 0 ? (
                summary.availableMonths.map((m) => (
                  <option key={m} value={m}>
                    {m} {m === summary.month ? '(Active)' : ''}
                  </option>
                ))
              ) : (
                <option value={summary.month}>{summary.month}</option>
              )}
            </select>
          </div>
        </div>

        {/* Executive Summary Cards */}
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4 border-t border-slate-100 text-xs">
          {/* Revenue Variance */}
          <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
            <div className="text-[10px] uppercase font-bold text-slate-500">Revenue Variance</div>
            <div className={`text-xl font-bold ${summary.totalRevenueVariance >= 0 ? 'text-emerald-700' : 'text-red-700'}`}>
              {summary.totalRevenueVariance >= 0 ? `+${formatINR(summary.totalRevenueVariance)}` : formatINR(summary.totalRevenueVariance)}
            </div>
            <div className="mt-0.5 text-[10px] text-slate-500">
              Plan: {formatINR(summary.totalRevenueBudget)} | Actual Billed: {formatINR(summary.totalRevenueActual)}
            </div>
          </div>

          {/* Expense Variance */}
          <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
            <div className="text-[10px] uppercase font-bold text-slate-500">Expense Variance</div>
            {summary.hasExpenseActuals && summary.totalExpenseVariance !== null ? (
              <>
                <div className={`text-xl font-bold ${summary.totalExpenseVariance <= 0 ? 'text-emerald-700' : 'text-amber-800'}`}>
                  {summary.totalExpenseVariance > 0 ? `+${formatINR(summary.totalExpenseVariance)}` : formatINR(summary.totalExpenseVariance)}
                </div>
                <div className="mt-0.5 text-[10px] text-slate-500">
                  Plan: {formatINR(summary.totalExpenseBudget)} | Actual: {formatINR(summary.totalExpenseActual || 0)}
                </div>
              </>
            ) : (
              <>
                <div className="text-sm font-semibold text-slate-500 mt-1">
                  Actual expense data not available.
                </div>
                <div className="mt-0.5 text-[10px] text-slate-400">
                  Expense variance not calculated
                </div>
              </>
            )}
          </div>

          {/* Significant Variances */}
          <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
            <div className="text-[10px] uppercase font-bold text-slate-500">Significant Variances (&gt;10%)</div>
            <div className="text-xl font-bold text-amber-900">{summary.significantVariancesCount} Departments</div>
            <div className="mt-0.5 text-[10px] text-amber-700">Flagged for financial review</div>
          </div>

          {/* YTD Revenue Variance */}
          <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
            <div className="text-[10px] uppercase font-bold text-slate-500">YTD Revenue Variance</div>
            <div className={`text-xl font-bold ${summary.ytdRevenueVariance >= 0 ? 'text-teal-800' : 'text-red-700'}`}>
              {summary.ytdRevenueVariance >= 0 ? `+${formatINR(summary.ytdRevenueVariance)}` : formatINR(summary.ytdRevenueVariance)}
            </div>
            <div className="mt-0.5 text-[10px] text-slate-500">
              YTD Plan: {formatINR(summary.ytdRevenueBudget)} | YTD Actual: {formatINR(summary.ytdRevenueActual)}
            </div>
          </div>
        </div>
      </div>

      {/* Visual Comparison: Budget vs Actual by Department */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900">Department Revenue: Budget vs Actual</h2>
            <p className="text-[11px] text-slate-500">Comparison across operating units with recorded transactions</p>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="flex items-center gap-1 text-teal-800 font-semibold">
              <span className="h-3 w-3 bg-teal-800 rounded-sm" /> Actual Billed
            </span>
            <span className="flex items-center gap-1 text-slate-400 font-semibold ml-3">
              <span className="h-3 w-3 bg-slate-300 rounded-sm" /> Budget Target
            </span>
          </div>
        </div>

        {deptVarianceChartData.length > 0 ? (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={deptVarianceChartData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                <XAxis dataKey="department" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis
                  tick={{ fontSize: 10, fill: '#64748b' }}
                  tickFormatter={(val) => `₹${(val / 100000).toFixed(1)}L`}
                />
                <Tooltip
                  formatter={(val: any) => [formatINR(Number(val) || 0)]}
                  contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', fontSize: '11px' }}
                />
                <Bar dataKey="actual" name="Actual Billed Revenue" fill="#0f766e" radius={[3, 3, 0, 0]} />
                <Bar dataKey="budget" name="Budget Plan" fill="#cbd5e1" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="py-12 text-center text-slate-400 text-xs">
            Data not available for the selected period
          </div>
        )}
      </div>

      {/* DETAILED BUDGET VS ACTUAL VARIANCE MATRIX */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50/60 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900">
              Departmental Variance Schedule (Revenue &amp; Operating Expenses)
            </h2>
            <p className="text-[11px] text-slate-500">
              Lineage: Derived strictly from uploaded budget records and patient billing registers.
            </p>
          </div>
          <span className="text-xs text-slate-500">
            Threshold: Variances &gt; &plusmn;10% flagged with alert indicator
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
            <thead className="bg-slate-50 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
              <tr>
                <th className="py-2.5 px-3">Department</th>
                <th className="py-2.5 px-3 text-right">Rev. Budget</th>
                <th className="py-2.5 px-3 text-right">Rev. Actual</th>
                <th className="py-2.5 px-3 text-right">Rev. Variance</th>
                <th className="py-2.5 px-3 text-right">Rev. Var %</th>
                <th className="py-2.5 px-3 text-right">Exp. Budget</th>
                <th className="py-2.5 px-3 text-right">Exp. Actual</th>
                <th className="py-2.5 px-3 text-right">Exp. Var %</th>
                <th className="py-2.5 px-3 text-right">YTD Actual</th>
                <th className="py-2.5 px-3 text-center">Alert</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {summary.departmentSummaries.length > 0 ? (
                summary.departmentSummaries.map((row) => (
                  <tr key={row.department} className="hover:bg-slate-50/80 transition">
                    <td className="py-2.5 px-3 font-semibold text-slate-900">{row.department}</td>
                    <td className="py-2.5 px-3 text-right text-slate-600 font-medium">
                      {formatINR(row.revenueBudget)}
                    </td>
                    <td className="py-2.5 px-3 text-right font-bold text-teal-800">
                      {formatINR(row.revenueActual)}
                    </td>
                    <td className="py-2.5 px-3 text-right font-semibold">
                      <span className={row.revenueVariance >= 0 ? 'text-emerald-700' : 'text-red-700'}>
                        {row.revenueVariance >= 0 ? `+${formatINR(row.revenueVariance)}` : formatINR(row.revenueVariance)}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right font-bold">
                      <span className={row.revenueVariancePercent >= 0 ? 'text-emerald-700' : 'text-red-700'}>
                        {row.revenueVariancePercent >= 0 ? `+${row.revenueVariancePercent}%` : `${row.revenueVariancePercent}%`}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right text-slate-600 font-medium">
                      {formatINR(row.expenseBudget)}
                    </td>
                    <td className="py-2.5 px-3 text-right text-slate-500">
                      {row.expenseActual !== null ? (
                        <span className="font-semibold text-slate-800">{formatINR(row.expenseActual)}</span>
                      ) : (
                        <span className="italic text-slate-400 text-[11px]">Not available</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      {row.expenseVariancePercent !== null ? (
                        <span className={row.expenseVariancePercent <= 0 ? 'text-emerald-700 font-semibold' : 'text-amber-800 font-semibold'}>
                          {row.expenseVariancePercent > 0 ? `+${row.expenseVariancePercent}%` : `${row.expenseVariancePercent}%`}
                        </span>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono font-medium text-slate-800">
                      {formatINR(row.ytdRevenueActual)}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      {row.isSignificant ? (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
                          ⚠ Significant
                        </span>
                      ) : (
                        <span className="text-slate-300">Normal</span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={10} className="py-8 text-center text-slate-400">
                    Data not available for the selected period
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* CFO MANAGEMENT COMMENTARY NOTEBOX */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-5">
        <div className="flex items-center gap-2 mb-2">
          <MessageSquare className="h-4 w-4 text-teal-700" />
          <h2 className="text-sm font-bold text-slate-900">
            CFO Management Commentary &amp; Operational Explanations
          </h2>
        </div>
        <p className="text-xs text-slate-500 mb-3">
          Document rationale for departmental deviations to accompany monthly board and investor governance packs.
        </p>

        <textarea
          rows={3}
          value={managementCommentary}
          onChange={(e) => setManagementCommentary(e.target.value)}
          className="w-full border border-slate-300 rounded-lg p-3 text-xs text-slate-800 focus:outline-teal-600 focus:ring-1 focus:ring-teal-600"
        />

        <div className="mt-3 flex items-center justify-between">
          <span className="text-[11px] text-slate-400">
            {savedCommentary ? '✓ Commentary saved (persisted for this reporting period)' : `Recorded for ${userDisplayName} (${userRoleDisplay})`}
          </span>
          <button
            onClick={handleSaveNotes}
            className="rounded-lg bg-teal-700 hover:bg-teal-800 text-white font-semibold px-4 py-1.5 text-xs transition cursor-pointer"
          >
            Save Commentary
          </button>
        </div>
      </div>
    </div>
  );
};
