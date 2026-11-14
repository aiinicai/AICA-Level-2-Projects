import React from 'react';
import {
  TrendingUp,
  TrendingDown,
  Wallet,
  CreditCard,
  PiggyBank,
  AlertTriangle,
  Sparkles,
  ShieldAlert,
  ArrowUpRight,
  ArrowRight,
  CheckCircle2,
  Calendar,
  Layers,
  ChevronRight,
  BookOpen,
  Mic,
  Cpu,
  MessageSquare,
  Zap
} from 'lucide-react';
import { Account, CategoryBudget, ExpenseCategory, Transaction } from '../types/finance';
import { NotificationSimulator } from './NotificationSimulator';
import { DashboardCharts } from './DashboardCharts';

interface DashboardProps {
  transactions: Transaction[];
  accounts: Account[];
  budgets: CategoryBudget[];
  onRecordTransaction: (tx: Partial<Transaction>) => void;
  onOpenAndroidCode: () => void;
  onOpenAndroidGuide: () => void;
  onOpenAppGuide?: () => void;
  onOpenQrModal: () => void;
  onOpenAddModal: () => void;
  onOpenAddAccountModal: () => void;
  onViewAllTransactions: (category?: string) => void;
  onUpdateTransaction: (tx: Transaction) => void;
  onOpenVoiceModal?: () => void;
  onOpenFraudModal?: () => void;
  onOpenForecastModal?: () => void;
  onOpenAssistantModal?: () => void;
  onOpenKeyFeaturesModal?: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  transactions,
  accounts,
  budgets,
  onRecordTransaction,
  onOpenAndroidCode,
  onOpenAndroidGuide,
  onOpenAppGuide,
  onOpenQrModal,
  onOpenAddModal,
  onOpenAddAccountModal,
  onViewAllTransactions,
  onUpdateTransaction,
  onOpenVoiceModal,
  onOpenFraudModal,
  onOpenForecastModal,
  onOpenAssistantModal,
  onOpenKeyFeaturesModal
}) => {
  // Financial computations
  const expenses = transactions.filter(t => t.type === 'expense');
  const incomes = transactions.filter(t => t.type === 'income');

  const totalExpense = expenses.reduce((s, t) => s + t.amount, 0);
  const totalIncome = incomes.reduce((s, t) => s + t.amount, 0);
  const netSavings = totalIncome - totalExpense;
  const savingsRate = totalIncome > 0 ? (netSavings / totalIncome) * 100 : 0;

  // Credit Card Metrics
  const creditCards = accounts.filter(a => a.type === 'credit_card');
  const totalCreditDebt = creditCards.reduce((s, a) => s + a.balance, 0);
  const totalCreditLimit = creditCards.reduce((s, a) => s + (a.creditLimit || 0), 0);
  const availableCredit = Math.max(0, totalCreditLimit - totalCreditDebt);

  // Bank & Cash Balance
  const bankAccounts = accounts.filter(a => a.type === 'bank' || a.type === 'cash');
  const totalBankBalance = bankAccounts.reduce((s, a) => s + a.balance, 0);

  // Investment metrics & Net Worth
  const investmentAccounts = accounts.filter(a => a.type === 'investment');
  const totalInvestments = investmentAccounts.reduce((s, a) => s + (a.currentValuation ?? a.balance), 0);
  const totalNetWorth = totalBankBalance + totalInvestments - totalCreditDebt;

  // Budget calculations
  const totalBudgetLimit = budgets.reduce((s, b) => s + b.monthlyLimit, 0);
  const remainingBudget = Math.max(0, totalBudgetLimit - totalExpense);

  // Red flags count
  const redFlagCount = transactions.filter(t => t.isRedFlag && !t.isVerifiedByUser).length;

  return (
    <div className="space-y-4 sm:space-y-6 pb-2 sm:pb-4">
      {/* Red Flag Floating Alert if any pending review */}
      {redFlagCount > 0 && (
        <div className="p-4 rounded-2xl bg-gradient-to-r from-rose-950/60 to-slate-900 border border-rose-500/40 flex items-center justify-between gap-4 shadow-lg shadow-rose-950/30">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-rose-500/20 text-rose-400 flex items-center justify-center shrink-0">
              <ShieldAlert className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                🔴 Security Alert: {redFlagCount} International / High Transaction(s)
              </h4>
              <p className="text-xs text-rose-300">
                Foreign currencies converted to AED. Review under Red Flags, alter FX rates/amounts, and confirm genuine transactions.
              </p>
            </div>
          </div>
          <button
            onClick={() => onViewAllTransactions()}
            className="px-3.5 py-1.5 bg-rose-500 hover:bg-rose-400 text-white font-bold text-xs rounded-xl transition whitespace-nowrap cursor-pointer shadow"
          >
            Review &amp; Alter
          </button>
        </div>
      )}

      {/* Financial KPI Cards Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        {/* Income */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold">Monthly Income</span>
            <div className="w-7 h-7 rounded-lg bg-emerald-500/15 text-emerald-400 flex items-center justify-center">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl sm:text-2xl font-black text-white tabular-nums tracking-tight">
            AED {totalIncome.toLocaleString('en-AE', { minimumFractionDigits: 0 })}
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-emerald-400 mt-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Salary Credited</span>
          </div>
        </div>

        {/* Expenses */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold">Total Expenses</span>
            <div className="w-7 h-7 rounded-lg bg-rose-500/15 text-rose-400 flex items-center justify-center">
              <TrendingDown className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl sm:text-2xl font-black text-white tabular-nums tracking-tight">
            AED {totalExpense.toLocaleString('en-AE', { minimumFractionDigits: 0 })}
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-slate-400 mt-1.5">
            <span>Budget: AED {totalBudgetLimit.toLocaleString()}</span>
          </div>
        </div>

        {/* Net Savings */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold">Net Savings</span>
            <div className="w-7 h-7 rounded-lg bg-teal-500/15 text-teal-400 flex items-center justify-center">
              <PiggyBank className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl sm:text-2xl font-black text-teal-400 tabular-nums tracking-tight">
            AED {netSavings.toLocaleString('en-AE', { minimumFractionDigits: 0 })}
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-teal-300 mt-1.5">
            <span className="font-semibold">{savingsRate.toFixed(0)}% Savings Rate</span>
          </div>
        </div>

        {/* Credit Card Outstanding */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold">Cards Outstanding</span>
            <div className="w-7 h-7 rounded-lg bg-indigo-500/15 text-indigo-400 flex items-center justify-center">
              <CreditCard className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl sm:text-2xl font-black text-white tabular-nums tracking-tight">
            AED {totalCreditDebt.toLocaleString('en-AE', { minimumFractionDigits: 0 })}
          </div>
          <div className="flex items-center justify-between text-[11px] text-slate-400 mt-1.5">
            <span>Avail: AED {availableCredit.toLocaleString()}</span>
          </div>
        </div>
      </div>

      {/* DirhamTrack Intelligence: Compact Quick Bar (Shifted Down & Compact) */}
      <div className="bg-slate-900/70 border border-slate-800/90 hover:border-slate-700/80 rounded-2xl p-2.5 sm:p-3 shadow-md transition">
        <div className="flex items-center justify-between mb-2 px-1">
          <div className="flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5 text-teal-400" />
            <span className="text-xs font-bold text-white tracking-tight">DirhamTrack Intelligence</span>
            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-teal-500/15 text-teal-300 border border-teal-500/30">
              ML + Gemini
            </span>
          </div>
          <span className="text-[10px] text-slate-400 hidden sm:inline">
            Voice • Gemini Insights • Cash Flow • Core Tools
          </span>
        </div>

        {/* 4 Compact Action Items */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {/* Card 1: Voice Entry */}
          <button
            onClick={onOpenVoiceModal}
            className="group flex items-center gap-2 p-2 sm:p-2.5 rounded-xl bg-slate-950/70 hover:bg-slate-950 border border-teal-500/25 hover:border-teal-400 text-left transition shadow-xs cursor-pointer min-h-[44px]"
            title="Voice Expense Entry"
          >
            <div className="w-7 h-7 rounded-lg bg-teal-500/20 text-teal-400 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
              <Mic className="w-3.5 h-3.5" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-white group-hover:text-teal-300 truncate">Voice Entry</span>
                <ChevronRight className="w-3 h-3 text-teal-400 opacity-60 group-hover:opacity-100 group-hover:translate-x-0.5 transition shrink-0" />
              </div>
              <p className="text-[9px] text-slate-400 truncate">Speak expense</p>
            </div>
          </button>

          {/* Card 2: AI Chatbot */}
          <button
            onClick={onOpenAssistantModal}
            className="group flex items-center gap-2 p-2 sm:p-2.5 rounded-xl bg-slate-950/70 hover:bg-slate-950 border border-indigo-500/25 hover:border-indigo-400 text-left transition shadow-xs cursor-pointer min-h-[44px]"
            title="AI Insights Chatbot"
          >
            <div className="w-7 h-7 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
              <MessageSquare className="w-3.5 h-3.5" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-white group-hover:text-indigo-300 truncate">AI Chatbot</span>
                <ChevronRight className="w-3 h-3 text-indigo-400 opacity-60 group-hover:opacity-100 group-hover:translate-x-0.5 transition shrink-0" />
              </div>
              <p className="text-[9px] text-slate-400 truncate">Ask finances</p>
            </div>
          </button>

          {/* Card 3: Cash Flow Forecast */}
          <button
            onClick={onOpenForecastModal}
            className="group flex items-center gap-2 p-2 sm:p-2.5 rounded-xl bg-slate-950/70 hover:bg-slate-950 border border-amber-500/25 hover:border-amber-400 text-left transition shadow-xs cursor-pointer min-h-[44px]"
            title="Cash Flow Forecast"
          >
            <div className="w-7 h-7 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
              <TrendingUp className="w-3.5 h-3.5" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-white group-hover:text-amber-300 truncate">Forecast</span>
                <ChevronRight className="w-3 h-3 text-amber-400 opacity-60 group-hover:opacity-100 group-hover:translate-x-0.5 transition shrink-0" />
              </div>
              <p className="text-[9px] text-slate-400 truncate">Cash burn pace</p>
            </div>
          </button>

          {/* Card 4: Key Features */}
          <button
            onClick={onOpenKeyFeaturesModal}
            className="group flex items-center gap-2 p-2 sm:p-2.5 rounded-xl bg-slate-950/70 hover:bg-slate-950 border border-emerald-500/25 hover:border-emerald-400 text-left transition shadow-xs cursor-pointer min-h-[44px]"
            title="Key Features & Core Tools"
          >
            <div className="w-7 h-7 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
              <Zap className="w-3.5 h-3.5" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-white group-hover:text-emerald-300 truncate">All Features</span>
                <ChevronRight className="w-3 h-3 text-emerald-400 opacity-60 group-hover:opacity-100 group-hover:translate-x-0.5 transition shrink-0" />
              </div>
              <p className="text-[9px] text-slate-400 truncate">SMS &amp; guides</p>
            </div>
          </button>
        </div>
      </div>

      {/* Main Grid: Visual Donut Analytics & Notification Listener */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Interactive 3D Donut Chart & Notification Simulator */}
        <div className="lg:col-span-2 space-y-6">
          {/* Interactive Recharts Financial Analytics & 3D Donut Breakdown */}
          <DashboardCharts
            transactions={transactions}
            onSelectCategory={(cat) => onViewAllTransactions(cat)}
          />

          <NotificationSimulator
            transactions={transactions}
            onRecordTransaction={onRecordTransaction}
            onOpenAndroidCode={onOpenAndroidCode}
            onOpenAndroidGuide={onOpenAndroidGuide}
          />
        </div>

        {/* Right Col: Accounts Overview & Quick Navigation */}
        <div className="space-y-6">
          {/* Quick Account Balances Glance */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-sm font-bold text-white">Accounts Overview</h3>
                <p className="text-[11px] text-teal-300 font-medium">
                  Net Worth: <strong className="text-white font-bold tabular-nums">AED {totalNetWorth.toLocaleString('en-AE', { minimumFractionDigits: 0 })}</strong>
                </p>
              </div>
              <button
                onClick={onOpenAddAccountModal}
                className="text-xs text-teal-400 hover:text-teal-300 font-semibold cursor-pointer"
              >
                + Add Account
              </button>
            </div>
            <div className="space-y-2.5">
              {accounts.slice(0, 5).map(acc => (
                <div
                  key={acc.id}
                  className="p-3 rounded-xl bg-slate-950 border border-slate-850 flex items-center justify-between text-xs hover:border-slate-700 transition"
                >
                  <div className="min-w-0 pr-2">
                    <p className="font-bold text-white truncate">{acc.name}</p>
                    <p className="text-[10px] text-slate-500">{acc.accountNumberMasked || acc.type.toUpperCase()}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <p
                      className={`font-bold tabular-nums ${
                        acc.type === 'credit_card'
                          ? 'text-rose-400'
                          : acc.type === 'investment'
                          ? 'text-emerald-400'
                          : 'text-teal-400'
                      }`}
                    >
                      AED {acc.balance.toLocaleString('en-AE', { minimumFractionDigits: 2 })}
                    </p>
                    <p className="text-[10px] text-slate-500">
                      {acc.type === 'credit_card'
                        ? 'Due Debt'
                        : acc.type === 'investment'
                        ? 'Invested Portfolio'
                        : 'Liquid'}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-4 pt-3 border-t border-slate-850 flex flex-col gap-2">
              <button
                onClick={() => onViewAllTransactions()}
                className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-750 text-teal-300 hover:text-teal-200 font-semibold text-xs flex items-center justify-center gap-1.5 transition cursor-pointer"
              >
                <span>Explore All Transactions</span>
                <ChevronRight className="w-4 h-4" />
              </button>
              {onOpenKeyFeaturesModal && (
                <button
                  onClick={onOpenKeyFeaturesModal}
                  className="w-full py-2 rounded-xl bg-slate-950 hover:bg-slate-900 border border-emerald-500/30 text-emerald-300 hover:text-emerald-200 font-semibold text-xs flex items-center justify-center gap-1.5 transition cursor-pointer"
                >
                  <Zap className="w-3.5 h-3.5 text-emerald-400" />
                  <span>View All Key Features</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
