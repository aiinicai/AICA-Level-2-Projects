import React, { useState } from 'react';
import {
  PieChart,
  AlertTriangle,
  AlertOctagon,
  CheckCircle,
  PlusCircle,
  Plus,
  Edit3,
  X,
  TrendingUp,
  ShieldCheck,
  Calendar,
  Tag
} from 'lucide-react';
import { CategoryBudget, ExpenseCategory, Transaction } from '../types/finance';
import { CategoryManagerModal } from './CategoryManagerModal';

interface BudgetManagerProps {
  budgets: CategoryBudget[];
  transactions: Transaction[];
  onUpdateBudgets: (updated: CategoryBudget[]) => void;
}

export const BudgetManager: React.FC<BudgetManagerProps> = ({
  budgets,
  transactions,
  onUpdateBudgets
}) => {
  const [editingBudget, setEditingBudget] = useState<CategoryBudget | null>(null);
  const [newLimitInput, setNewLimitInput] = useState<string>('');
  const [categoryModalOpen, setCategoryModalOpen] = useState(false);

  // Calculate actual spending per category for current month
  const categorySpentMap = new Map<ExpenseCategory, number>();
  let totalSpentAcrossBudgets = 0;

  for (const t of transactions) {
    if (t.type === 'expense') {
      if (t.categorySplits && t.categorySplits.length > 0) {
        for (const split of t.categorySplits) {
          const current = categorySpentMap.get(split.category) || 0;
          categorySpentMap.set(split.category, current + split.amount);
        }
      } else {
        const current = categorySpentMap.get(t.category) || 0;
        categorySpentMap.set(t.category, current + t.amount);
      }
      totalSpentAcrossBudgets += t.amount;
    }
  }

  const totalBudgetLimit = budgets.reduce((acc, b) => acc + b.monthlyLimit, 0);
  const totalRemaining = Math.max(0, totalBudgetLimit - totalSpentAcrossBudgets);
  const overallPercentage = totalBudgetLimit > 0 ? (totalSpentAcrossBudgets / totalBudgetLimit) * 100 : 0;

  // Days remaining in current month
  const today = new Date();
  const daysInMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0).getDate();
  const daysRemaining = Math.max(1, daysInMonth - today.getDate());
  const dailyAllowance = totalRemaining / daysRemaining;

  const handleOpenEdit = (b: CategoryBudget) => {
    setEditingBudget(b);
    setNewLimitInput(b.monthlyLimit.toString());
  };

  const handleSaveBudget = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingBudget) return;
    const limitNum = parseFloat(newLimitInput);
    if (isNaN(limitNum) || limitNum < 0) return;

    const updated = budgets.map(b =>
      b.category === editingBudget.category ? { ...b, monthlyLimit: limitNum } : b
    );
    onUpdateBudgets(updated);
    setEditingBudget(null);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-3.5 sm:p-5 shadow-lg">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            Monthly Category Budgets
          </h3>
          <p className="text-xs text-slate-400">
            Automated alerts when spending reaches 80% or exceeds targets
          </p>
        </div>

        {/* Quick Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setCategoryModalOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs rounded-xl transition cursor-pointer shadow"
          >
            <Plus className="w-4 h-4" />
            <span>+ Add / Manage Categories</span>
          </button>

          {/* Daily safe allowance pill */}
          <div className="flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-xl border border-slate-800 text-xs">
            <Calendar className="w-4 h-4 text-teal-400" />
            <span className="text-slate-400">Daily Safe Spend:</span>
            <span className="font-bold text-white tabular-nums">
              AED {dailyAllowance.toFixed(0)}/day
            </span>
            <span className="text-[10px] text-slate-500">({daysRemaining}d left)</span>
          </div>
        </div>
      </div>

      {/* Aggregate Progress Overview Bar */}
      <div className="bg-slate-950 rounded-xl p-3.5 sm:p-4 border border-slate-800 mb-4">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-2 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-slate-400">Overall Budget:</span>
            <span className="font-bold text-white tabular-nums">
              AED {totalSpentAcrossBudgets.toLocaleString('en-AE', { minimumFractionDigits: 0 })} / AED {totalBudgetLimit.toLocaleString('en-AE', { minimumFractionDigits: 0 })}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-slate-400">Remaining:</span>
            <span className={`font-bold tabular-nums ${totalRemaining > 0 ? 'text-teal-400' : 'text-rose-400'}`}>
              AED {totalRemaining.toLocaleString('en-AE', { minimumFractionDigits: 0 })}
            </span>
            <span className="text-[11px] font-semibold text-slate-400">({overallPercentage.toFixed(0)}%)</span>
          </div>
        </div>

        {/* Master Progress Bar */}
        <div className="w-full h-3 bg-slate-800 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${
              overallPercentage >= 100
                ? 'bg-rose-500'
                : overallPercentage >= 80
                ? 'bg-amber-500'
                : 'bg-teal-500'
            }`}
            style={{ width: `${Math.min(100, overallPercentage)}%` }}
          />
        </div>
      </div>

      {/* Category Budgets Grid - 3D Floating Perspective Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 [perspective:1200px]">
        {budgets.map(b => {
          const spent = categorySpentMap.get(b.category) || 0;
          const ratio = b.monthlyLimit > 0 ? spent / b.monthlyLimit : 0;
          const percentage = Math.round(ratio * 100);
          const isOver = ratio >= 1.0;
          const isWarning = ratio >= 0.8 && ratio < 1.0;

          return (
            <div
              key={b.category}
              className={`group relative p-4 rounded-2xl border transition-all duration-300 transform-gpu hover:-translate-y-1.5 hover:[transform:rotateX(2deg)_translateY(-6px)] overflow-hidden ${
                isOver
                  ? 'bg-gradient-to-b from-rose-950/40 via-slate-900/95 to-slate-950/95 border-rose-500/40 shadow-[0_16px_32px_-8px_rgba(225,29,72,0.3),inset_0_1px_1px_rgba(255,255,255,0.12),inset_0_-2px_4px_rgba(0,0,0,0.7)]'
                  : isWarning
                  ? 'bg-gradient-to-b from-amber-950/40 via-slate-900/95 to-slate-950/95 border-amber-500/40 shadow-[0_16px_32px_-8px_rgba(217,119,6,0.3),inset_0_1px_1px_rgba(255,255,255,0.12),inset_0_-2px_4px_rgba(0,0,0,0.7)]'
                  : 'bg-gradient-to-b from-slate-900/90 via-slate-925/95 to-slate-950/98 border-slate-800/90 hover:border-teal-500/50 shadow-[0_16px_32px_-10px_rgba(0,0,0,0.75),0_6px_16px_rgba(0,0,0,0.5),inset_0_1px_1px_rgba(255,255,255,0.08),inset_0_-2px_4px_rgba(0,0,0,0.7)] hover:shadow-[0_22px_44px_-10px_rgba(20,184,166,0.22),inset_0_1px_2px_rgba(255,255,255,0.18)]'
              }`}
            >
              {/* 3D Specular Top Rim Accent Line */}
              <div
                className="absolute top-0 left-0 right-0 h-1 opacity-85 group-hover:opacity-100 transition-opacity"
                style={{
                  backgroundColor: b.color,
                  boxShadow: `0 0 10px ${b.color}88`
                }}
              />

              <div className="flex items-center justify-between mb-2.5 pt-0.5">
                <div className="flex items-center gap-2.5">
                  <div
                    className="w-3 h-3 rounded-full shadow-[0_0_8px_rgba(255,255,255,0.3)] transition-transform group-hover:scale-110"
                    style={{ backgroundColor: b.color, boxShadow: `0 0 8px ${b.color}` }}
                  />
                  <span className="text-xs font-extrabold text-white tracking-tight">{b.category}</span>
                </div>

                <div className="flex items-center gap-2">
                  {/* 3D Tactile Status Pills */}
                  {isOver && (
                    <span className="flex items-center gap-1 text-[10px] font-black text-rose-300 bg-rose-500/25 border border-rose-500/40 px-2 py-0.5 rounded-lg shadow-sm">
                      <AlertOctagon className="w-3 h-3 text-rose-400" />
                      Exceeded +AED {(spent - b.monthlyLimit).toFixed(0)}
                    </span>
                  )}
                  {isWarning && (
                    <span className="flex items-center gap-1 text-[10px] font-black text-amber-300 bg-amber-500/25 border border-amber-500/40 px-2 py-0.5 rounded-lg shadow-sm">
                      <AlertTriangle className="w-3 h-3 text-amber-400" />
                      80% Reached
                    </span>
                  )}
                  {!isOver && !isWarning && (
                    <span className="text-[10px] font-bold text-teal-300 bg-teal-500/15 border border-teal-500/30 px-2 py-0.5 rounded-lg shadow-sm">
                      AED {(b.monthlyLimit - spent).toFixed(0)} left
                    </span>
                  )}

                  {/* Edit limit button */}
                  <button
                    onClick={() => handleOpenEdit(b)}
                    className="p-1 text-slate-400 hover:text-teal-300 hover:bg-slate-800/80 rounded-lg transition cursor-pointer"
                    title={`Edit ${b.category} limit`}
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Numbers with High Legibility & Depth */}
              <div className="flex items-baseline justify-between text-xs mb-2 tabular-nums">
                <div className="flex items-center gap-1.5">
                  <span className="text-slate-400 text-[11px] font-medium">Spent:</span>
                  <span className="text-white font-extrabold text-sm drop-shadow-sm">
                    AED {spent.toLocaleString('en-AE', { minimumFractionDigits: 0 })}
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-slate-500 text-[11px]">Budget:</span>
                  <span className="text-slate-300 font-bold text-xs">
                    AED {b.monthlyLimit.toLocaleString('en-AE', { minimumFractionDigits: 0 })}
                  </span>
                </div>
              </div>

              {/* 3D Recessed Progress Track & Glowing Fill */}
              <div className="w-full h-2.5 bg-slate-950 rounded-full p-0.5 border border-slate-800/80 shadow-[inset_0_2px_4px_rgba(0,0,0,0.9)] overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 relative ${
                    isOver
                      ? 'bg-gradient-to-r from-rose-600 via-rose-500 to-red-400 shadow-[0_0_10px_rgba(244,63,94,0.6)]'
                      : isWarning
                      ? 'bg-gradient-to-r from-amber-600 via-amber-500 to-yellow-400 shadow-[0_0_10px_rgba(245,158,11,0.6)]'
                      : 'bg-gradient-to-r from-teal-600 via-teal-400 to-emerald-300 shadow-[0_0_10px_rgba(20,184,166,0.6)]'
                  }`}
                  style={{ width: `${Math.min(100, percentage)}%` }}
                >
                  {/* Subtle specular line inside progress */}
                  <div className="absolute inset-0 bg-gradient-to-b from-white/20 to-transparent rounded-full pointer-events-none" />
                </div>
              </div>

              {/* Bottom Percentage Footer */}
              <div className="flex items-center justify-between text-[10px] text-slate-500 mt-1.5 font-medium">
                <span>{percentage}% utilized</span>
                <span>{isOver ? 'Over budget' : `${100 - Math.min(100, percentage)}% available`}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Edit Budget Limit Modal */}
      {editingBudget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <form
            onSubmit={handleSaveBudget}
            className="w-full max-w-xs bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-2xl"
          >
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-bold text-white">
                Set Monthly Budget: {editingBudget.category}
              </h4>
              <button
                type="button"
                onClick={() => setEditingBudget(null)}
                className="p-1 text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <label className="block text-xs text-slate-400 mb-1">
              Monthly Limit in AED:
            </label>
            <div className="relative mb-4">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs font-bold text-teal-400">
                AED
              </span>
              <input
                type="number"
                min="0"
                step="50"
                value={newLimitInput}
                onChange={e => setNewLimitInput(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl pl-12 pr-4 py-2 text-sm text-white font-bold focus:outline-none focus:border-teal-500"
                autoFocus
              />
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setEditingBudget(null)}
                className="flex-1 py-2 rounded-xl bg-slate-800 text-xs font-semibold text-slate-300 hover:bg-slate-700 transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex-1 py-2 rounded-xl bg-teal-500 text-slate-950 text-xs font-bold hover:bg-teal-400 transition"
              >
                Save
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Category Manager Modal */}
      {categoryModalOpen && (
        <CategoryManagerModal
          onClose={() => setCategoryModalOpen(false)}
          onCategoriesUpdated={allCategories => {
            // Ensure every category has an entry in budgets
            const existingCategories = new Set(budgets.map(b => b.category));
            const newBudgets = [...budgets];
            const colors = ['#6366f1', '#ec4899', '#14b8a6', '#f59e0b', '#3b82f6', '#8b5cf6'];
            let colorIdx = 0;

            for (const cat of allCategories) {
              if (!existingCategories.has(cat)) {
                newBudgets.push({
                  category: cat,
                  monthlyLimit: cat === 'Rent & Housing' ? 5500 : 1500,
                  icon: cat === 'Rent & Housing' ? 'Home' : 'Tag',
                  color: colors[colorIdx % colors.length],
                  isCustom: true
                });
                colorIdx++;
              }
            }
            onUpdateBudgets(newBudgets);
          }}
        />
      )}
    </div>
  );
};
