import React from 'react';
import {
  LayoutDashboard,
  Plus,
  Target,
  Wallet
} from 'lucide-react';

interface BottomNavBarProps {
  activeTab: 'dashboard' | 'transactions' | 'budgets' | 'accounts' | 'subscriptions';
  onSelectTab: (tab: 'dashboard' | 'transactions' | 'budgets' | 'accounts' | 'subscriptions') => void;
  onOpenAddModal: () => void;
}

export const BottomNavBar: React.FC<BottomNavBarProps> = ({
  activeTab,
  onSelectTab,
  onOpenAddModal
}) => {
  return (
    <nav className="sm:hidden fixed bottom-0 left-0 right-0 z-40 bg-slate-950/95 backdrop-blur-xl border-t border-slate-800 shadow-2xl pb-safe">
      <div className="grid grid-cols-5 items-center h-16 max-w-md mx-auto px-1">
        {/* Tab 1: Dashboard */}
        <button
          type="button"
          onClick={() => onSelectTab('dashboard')}
          className={`flex flex-col items-center justify-center h-full transition cursor-pointer ${
            activeTab === 'dashboard' ? 'text-teal-400 font-bold' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <LayoutDashboard className="w-5 h-5" />
          <span className="text-[10px] font-medium tracking-tight mt-1">Dashboard</span>
        </button>

        {/* Tab 2: Activity with UAE Dirham Receipt Icon */}
        <button
          type="button"
          onClick={() => onSelectTab('transactions')}
          className={`flex flex-col items-center justify-center h-full transition cursor-pointer ${
            activeTab === 'transactions' ? 'text-teal-400 font-bold' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <svg
            className="w-5 h-5"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z" />
            <text
              x="12"
              y="14.5"
              textAnchor="middle"
              fontSize="7.5"
              fontWeight="bold"
              fill="currentColor"
              stroke="none"
              fontFamily="system-ui, -apple-system, sans-serif"
            >
              د.إ
            </text>
          </svg>
          <span className="text-[10px] font-medium tracking-tight mt-1">Activity</span>
        </button>

        {/* Center Action: Add Transaction */}
        <button
          type="button"
          onClick={onOpenAddModal}
          className="flex flex-col items-center justify-center h-full -mt-3.5 group cursor-pointer"
          title="Add Expense or Receipt"
          aria-label="Add Expense"
        >
          <div className="w-11 h-11 rounded-full bg-gradient-to-tr from-teal-400 to-emerald-400 text-slate-950 flex items-center justify-center shadow-lg shadow-teal-500/40 group-active:scale-95 transition-transform border-2 border-slate-950">
            <Plus className="w-5 h-5 stroke-[2.5]" />
          </div>
          <span className="text-[10px] font-bold text-teal-400 tracking-tight mt-0.5">Add</span>
        </button>

        {/* Tab 3: Budgets */}
        <button
          type="button"
          onClick={() => onSelectTab('budgets')}
          className={`flex flex-col items-center justify-center h-full transition cursor-pointer ${
            activeTab === 'budgets' ? 'text-teal-400 font-bold' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Target className="w-5 h-5" />
          <span className="text-[10px] font-medium tracking-tight mt-1">Budgets</span>
        </button>

        {/* Tab 4: Accounts */}
        <button
          type="button"
          onClick={() => onSelectTab('accounts')}
          className={`flex flex-col items-center justify-center h-full transition cursor-pointer ${
            activeTab === 'accounts' ? 'text-teal-400 font-bold' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Wallet className="w-5 h-5" />
          <span className="text-[10px] font-medium tracking-tight mt-1">Accounts</span>
        </button>
      </div>
    </nav>
  );
};
