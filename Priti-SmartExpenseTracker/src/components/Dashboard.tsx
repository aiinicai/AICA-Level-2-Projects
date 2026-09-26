import React from 'react';
import {
  TrendingUp,
  TrendingDown,
  Wallet,
  PiggyBank,
  Receipt,
  Calendar,
  Sparkles,
  ArrowRight,
  Zap,
} from 'lucide-react';
import { Transaction, TransactionCategory } from '../types';
import { CategoryDonutChart, SpendingTrendChart } from './DashboardCharts';
import { AIInsightsSection } from './AIInsightsSection';
import { formatINR, formatMonthYear } from '../utils/formatters';

interface DashboardProps {
  transactions: Transaction[];
  currentMonth: string; // YYYY-MM
  onMonthChange: (month: string) => void;
  onOpenScanModal: () => void;
  onOpenManualModal: () => void;
  onNavigateToHistory: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  transactions,
  currentMonth,
  onMonthChange,
  onOpenScanModal,
  onOpenManualModal,
  onNavigateToHistory,
}) => {
  // Compute previous month string (e.g. '2026-08' if current is '2026-09')
  const [currYear, currMonthNum] = currentMonth.split('-').map(Number);
  const prevDate = new Date(currYear, currMonthNum - 2, 1);
  const prevMonth = `${prevDate.getFullYear()}-${String(prevDate.getMonth() + 1).padStart(2, '0')}`;

  // Filter current month transactions
  const currentMonthTx = transactions.filter((t) => t.date.startsWith(currentMonth));
  const prevMonthTx = transactions.filter((t) => t.date.startsWith(prevMonth));

  // Current Month Total Spend (excluding Investments per requirement: separate running total for investments)
  const currentMonthSpend = currentMonthTx
    .filter((t) => t.category !== 'Investment')
    .reduce((sum, t) => sum + t.amount, 0);

  // Previous Month Total Spend (excluding Investments)
  const prevMonthSpend = prevMonthTx
    .filter((t) => t.category !== 'Investment')
    .reduce((sum, t) => sum + t.amount, 0);

  // Percentage change vs previous month
  let spendPctChange = 0;
  if (prevMonthSpend > 0) {
    spendPctChange = ((currentMonthSpend - prevMonthSpend) / prevMonthSpend) * 100;
  }

  // Running total for "Investments" distinct from "Expenses"
  const currentMonthInvestments = currentMonthTx
    .filter((t) => t.category === 'Investment')
    .reduce((sum, t) => sum + t.amount, 0);

  const allTimeInvestments = transactions
    .filter((t) => t.category === 'Investment')
    .reduce((sum, t) => sum + t.amount, 0);

  // Category breakdown for current month (excluding Investment)
  const categoryTotals: Record<TransactionCategory, number> = {
    Food: 0,
    Travel: 0,
    Shopping: 0,
    Bills: 0,
    Investment: 0,
    Healthcare: 0,
    Entertainment: 0,
    Other: 0,
  };

  currentMonthTx.forEach((t) => {
    categoryTotals[t.category] = (categoryTotals[t.category] || 0) + t.amount;
  });

  // Daily spending trend data for current month
  const daysInMonth = new Date(currYear, currMonthNum, 0).getDate();
  const dailySpendingMap: Record<number, number> = {};
  for (let d = 1; d <= daysInMonth; d++) {
    dailySpendingMap[d] = 0;
  }

  currentMonthTx
    .filter((t) => t.category !== 'Investment')
    .forEach((t) => {
      const day = parseInt(t.date.split('-')[2], 10);
      if (day >= 1 && day <= daysInMonth) {
        dailySpendingMap[day] += t.amount;
      }
    });

  const dailySpendingList = Object.entries(dailySpendingMap).map(([day, amount]) => ({
    date: `${currentMonth}-${String(day).padStart(2, '0')}`,
    dayLabel: `Day ${day}`,
    amount,
  }));

  // Average daily spend for days elapsed so far
  const activeDaysWithData = Math.max(
    ...currentMonthTx.map((t) => parseInt(t.date.split('-')[2], 10)),
    1
  );
  const avgDailySpend = currentMonthSpend / activeDaysWithData;

  // Month selector options
  const availableMonths = Array.from(
    new Set(transactions.map((t) => t.date.slice(0, 7)))
  ).sort().reverse();
  if (!availableMonths.includes(currentMonth)) {
    availableMonths.unshift(currentMonth);
  }

  return (
    <div className="space-y-6 pb-20">
      {/* Month Selector & Quick Actions Top Bar with Vibrant Gradient Accent */}
      <div className="relative overflow-hidden bg-white dark:bg-slate-900 p-4 rounded-2xl border border-slate-200/90 dark:border-slate-800 shadow-md">
        {/* Colorful top border line */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-500 via-teal-500 via-indigo-500 to-rose-500" />

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 text-white shadow-md shadow-emerald-500/20">
              <Calendar className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                Viewing Financial Period
              </span>
              <div className="flex items-center gap-2">
                <select
                  value={currentMonth}
                  onChange={(e) => onMonthChange(e.target.value)}
                  className="text-base font-extrabold text-slate-900 dark:text-white bg-transparent border-none focus:outline-hidden cursor-pointer hover:text-emerald-600 transition"
                >
                  {availableMonths.map((m) => (
                    <option key={m} value={m} className="text-slate-900 dark:text-white bg-white dark:bg-slate-800">
                      {formatMonthYear(m)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Quick action buttons with rich colors */}
          <div className="flex items-center gap-2.5">
            <button
              onClick={onOpenScanModal}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold shadow-md shadow-emerald-600/20 transition active:scale-95 cursor-pointer"
            >
              <Sparkles className="w-4 h-4 text-amber-200" />
              <span>Scan Invoice</span>
            </button>
            <button
              onClick={onOpenManualModal}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700/60 text-slate-800 dark:text-slate-200 text-xs font-bold transition active:scale-95 cursor-pointer shadow-xs"
            >
              <span>+ Add Manual</span>
            </button>
          </div>
        </div>
      </div>

      {/* CORE DASHBOARD METRIC CARDS - RICH COLORFUL GRADIENTS */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {/* 1. Current Month Total Spend (Warm Rose-Coral Card) */}
        <div className="relative overflow-hidden p-5 rounded-2xl bg-gradient-to-br from-rose-50/80 via-orange-50/40 to-white dark:from-rose-950/25 dark:via-orange-950/15 dark:to-slate-900 border border-rose-200/90 dark:border-rose-900/60 shadow-sm flex flex-col justify-between">
          <div className="absolute top-0 right-0 w-32 h-32 bg-rose-400/10 rounded-full blur-2xl pointer-events-none" />

          <div className="flex items-center justify-between">
            <span className="text-xs font-extrabold text-rose-700 dark:text-rose-400 uppercase tracking-wider">
              Total Spending ({formatMonthYear(currentMonth)})
            </span>
            <div className="p-2.5 rounded-xl bg-gradient-to-tr from-rose-500 to-orange-400 text-white shadow-md shadow-rose-500/25">
              <Wallet className="w-4 h-4" />
            </div>
          </div>

          <div className="my-3">
            <div className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white tracking-tight">
              {formatINR(currentMonthSpend)}
            </div>
          </div>

          {/* Month-over-month percentage change indicator */}
          <div className="flex items-center gap-2 pt-2 border-t border-rose-200/60 dark:border-rose-900/40 text-xs">
            {prevMonthSpend > 0 ? (
              <>
                <span
                  className={`inline-flex items-center gap-1 font-extrabold px-2.5 py-0.5 rounded-full text-xs shadow-xs ${
                    spendPctChange > 0
                      ? 'bg-rose-500 text-white'
                      : 'bg-emerald-500 text-white'
                  }`}
                >
                  {spendPctChange > 0 ? (
                    <TrendingUp className="w-3.5 h-3.5" />
                  ) : (
                    <TrendingDown className="w-3.5 h-3.5" />
                  )}
                  {spendPctChange > 0 ? `+${spendPctChange.toFixed(1)}%` : `${spendPctChange.toFixed(1)}%`}
                </span>
                <span className="text-slate-600 dark:text-slate-400 font-medium">
                  vs {formatMonthYear(prevMonth)} ({formatINR(prevMonthSpend)})
                </span>
              </>
            ) : (
              <span className="text-slate-400 text-xs italic">
                Initial month of tracked expenses
              </span>
            )}
          </div>
        </div>

        {/* 2. Separate Running Total for "Investments" (Lush Emerald-Teal-Gold Card) */}
        <div className="relative overflow-hidden p-5 rounded-2xl bg-gradient-to-br from-emerald-50/80 via-teal-50/40 to-white dark:from-emerald-950/25 dark:via-teal-950/15 dark:to-slate-900 border border-emerald-300 dark:border-emerald-800 shadow-sm flex flex-col justify-between">
          <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-400/15 rounded-full blur-2xl pointer-events-none" />

          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs font-extrabold text-emerald-800 dark:text-emerald-400 uppercase tracking-wider block">
                Total Investments
              </span>
              <span className="text-[10px] text-teal-600 dark:text-teal-400 font-bold">
                Wealth Building (Distinct from Expenses)
              </span>
            </div>
            <div className="p-2.5 rounded-xl bg-gradient-to-tr from-emerald-600 via-teal-600 to-cyan-500 text-white shadow-md shadow-emerald-600/25">
              <PiggyBank className="w-4 h-4" />
            </div>
          </div>

          <div className="my-3">
            <div className="text-2xl sm:text-3xl font-black text-emerald-700 dark:text-emerald-400 tracking-tight">
              {formatINR(currentMonthInvestments)}
            </div>
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-emerald-200/60 dark:border-emerald-900/40 text-xs">
            <span className="text-slate-600 dark:text-slate-400 font-medium">
              Cumulative Wealth:
            </span>
            <span className="font-extrabold text-emerald-800 dark:text-emerald-300 bg-emerald-100/70 dark:bg-emerald-950 px-2 py-0.5 rounded-md">
              {formatINR(allTimeInvestments)}
            </span>
          </div>
        </div>

        {/* 3. Transaction Count & Daily Pace (Vibrant Indigo-Purple Card) */}
        <div className="relative overflow-hidden p-5 rounded-2xl bg-gradient-to-br from-indigo-50/80 via-purple-50/40 to-white dark:from-indigo-950/25 dark:via-purple-950/15 dark:to-slate-900 border border-indigo-200/90 dark:border-indigo-900/60 shadow-sm flex flex-col justify-between">
          <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-400/10 rounded-full blur-2xl pointer-events-none" />

          <div className="flex items-center justify-between">
            <span className="text-xs font-extrabold text-indigo-700 dark:text-indigo-400 uppercase tracking-wider">
              Activity & Pace
            </span>
            <div className="p-2.5 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-500 text-white shadow-md shadow-indigo-500/25">
              <Receipt className="w-4 h-4" />
            </div>
          </div>

          <div className="my-3 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white">
              {currentMonthTx.length}
            </span>
            <span className="text-xs text-indigo-600 dark:text-indigo-400 font-bold">
              entries this month
            </span>
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-indigo-200/60 dark:border-indigo-900/40 text-xs">
            <span className="text-slate-600 dark:text-slate-400 font-medium">
              Avg Daily Outflow:
            </span>
            <span className="font-extrabold text-indigo-800 dark:text-indigo-300 bg-indigo-100/70 dark:bg-indigo-950 px-2 py-0.5 rounded-md">
              {formatINR(avgDailySpend)}/day
            </span>
          </div>
        </div>
      </div>

      {/* CHARTS SECTION */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Category-wise Breakdown (Donut + Legend) */}
        <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-extrabold text-slate-900 dark:text-white flex items-center gap-2">
                <span>Category Breakdown</span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300">
                  Interactive
                </span>
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Expenditure distribution for {formatMonthYear(currentMonth)}
              </p>
            </div>
          </div>
          <CategoryDonutChart categoryTotals={categoryTotals} totalSpend={currentMonthSpend} />
        </div>

        {/* Daily Spending Trend (SVG Line Chart) */}
        <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-extrabold text-slate-900 dark:text-white flex items-center gap-2">
                <span>Daily Spending Trend</span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-cyan-100 dark:bg-cyan-950 text-cyan-800 dark:text-cyan-300">
                  Daily Peaks
                </span>
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Outflow progression across days this month
              </p>
            </div>
            <span className="text-xs font-bold text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 px-2.5 py-1 rounded-full border border-emerald-200 dark:border-emerald-800">
              {currentMonth}
            </span>
          </div>
          <SpendingTrendChart dailySpending={dailySpendingList} />
        </div>
      </div>

      {/* AI-GENERATED INSIGHTS SECTION */}
      <AIInsightsSection
        currentMonthTransactions={currentMonthTx}
        previousMonthTransactions={prevMonthTx}
        monthName={formatMonthYear(currentMonth)}
      />

      {/* RECENT TRANSACTIONS PREVIEW BANNER WITH COLORFUL STYLING */}
      <div className="p-4 rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white flex flex-col sm:flex-row items-center justify-between gap-3 shadow-lg">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-white/10 backdrop-blur-md text-emerald-400">
            <Zap className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-xs font-extrabold uppercase tracking-wider text-emerald-300">
              Inspect logs, receipts & search entries
            </h4>
            <p className="text-xs text-slate-300 font-medium">
              View itemized line items, edit past expenses, or export your full financial history to CSV.
            </p>
          </div>
        </div>
        <button
          onClick={onNavigateToHistory}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-extrabold transition active:scale-95 cursor-pointer shrink-0 shadow-md"
        >
          <span>View All Transactions</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
