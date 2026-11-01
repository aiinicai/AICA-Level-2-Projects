import React, { useState } from 'react';
import {
  X,
  Plus,
  Trash2,
  Tag,
  Home,
  Check,
  ShoppingBag,
  Sparkles,
  Info
} from 'lucide-react';
import { ExpenseCategory } from '../types/finance';
import { StorageService } from '../services/storage';

interface CategoryManagerModalProps {
  onClose: () => void;
  onCategoriesUpdated: (categories: ExpenseCategory[]) => void;
  onSelectCategory?: (category: ExpenseCategory) => void;
}

const PRESET_COLORS = [
  '#6366f1', // Indigo
  '#f97316', // Orange
  '#10b981', // Emerald
  '#06b6d4', // Cyan
  '#ec4899', // Pink
  '#eab308', // Amber
  '#8b5cf6', // Violet
  '#ef4444', // Red
  '#14b8a6', // Teal
  '#3b82f6'  // Blue
];

const SUGGESTED_CATEGORIES = [
  'Rent & Housing',
  'Maintenance & Repairs',
  'Gym & Fitness',
  'Maid & Cleaning',
  'Insurance',
  'Zakat & Charity',
  'Kids & School',
  'Pets & Vet',
  'Gifts & Donations',
  'Car EMI & Loan',
  'Office & Work'
];

export const CategoryManagerModal: React.FC<CategoryManagerModalProps> = ({
  onClose,
  onCategoriesUpdated,
  onSelectCategory
}) => {
  const [categories, setCategories] = useState<ExpenseCategory[]>(() =>
    StorageService.getAllExpenseCategories()
  );
  const [customCategories, setCustomCategories] = useState<string[]>(() =>
    StorageService.getCustomCategories()
  );
  const [newCatName, setNewCatName] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const handleAddCategory = (nameToAdd?: string) => {
    const raw = (nameToAdd || newCatName).trim();
    if (!raw) {
      setErrorMsg('Please enter a category name.');
      return;
    }

    if (categories.some(c => c.toLowerCase() === raw.toLowerCase())) {
      setErrorMsg(`"${raw}" category already exists.`);
      return;
    }

    setErrorMsg('');
    const updatedCustom = StorageService.addCustomCategory(raw);
    setCustomCategories(updatedCustom);
    const updatedAll = StorageService.getAllExpenseCategories();
    setCategories(updatedAll);
    onCategoriesUpdated(updatedAll);
    setNewCatName('');
    setSuccessMsg(`Added category "${raw}" successfully!`);
    setTimeout(() => setSuccessMsg(''), 2500);

    if (onSelectCategory) {
      onSelectCategory(raw);
    }
  };

  const handleDeleteCustom = (cat: string) => {
    const updatedCustom = StorageService.deleteCustomCategory(cat);
    setCustomCategories(updatedCustom);
    const updatedAll = StorageService.getAllExpenseCategories();
    setCategories(updatedAll);
    onCategoriesUpdated(updatedAll);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto animate-fade-in">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden my-6 flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-5 bg-slate-950 border-b border-slate-800 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-teal-500/20 text-teal-400 border border-teal-500/30 flex items-center justify-center shrink-0">
              <Tag className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Expense Categories</h3>
              <p className="text-xs text-slate-400">Add Rent, Housing, and custom expense categories</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-5 space-y-5 text-xs overflow-y-auto">
          {/* Add Input Form */}
          <div className="p-4 bg-slate-950 rounded-2xl border border-slate-800 space-y-3">
            <label className="block text-slate-300 font-semibold">
              Add New Expense Category:
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="e.g. Rent Expense, Maid, Gym, Zakat..."
                value={newCatName}
                onChange={e => {
                  setNewCatName(e.target.value);
                  setErrorMsg('');
                }}
                onKeyDown={e => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddCategory();
                  }
                }}
                className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-white text-xs placeholder-slate-500 focus:outline-none focus:border-teal-500 font-medium"
              />
              <button
                type="button"
                onClick={() => handleAddCategory()}
                className="px-4 py-2 bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs rounded-xl flex items-center gap-1.5 transition cursor-pointer shadow"
              >
                <Plus className="w-4 h-4" />
                <span>Add</span>
              </button>
            </div>

            {errorMsg && (
              <p className="text-[11px] text-rose-400 font-semibold animate-shake">
                {errorMsg}
              </p>
            )}

            {successMsg && (
              <p className="text-[11px] text-emerald-400 font-semibold">
                {successMsg}
              </p>
            )}

            {/* Quick Suggested Categories */}
            <div className="pt-2 border-t border-slate-800/80">
              <span className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1.5 font-bold">
                Quick Add Suggestions:
              </span>
              <div className="flex flex-wrap gap-1.5">
                {SUGGESTED_CATEGORIES.filter(s => !categories.includes(s)).slice(0, 6).map(sug => (
                  <button
                    key={sug}
                    type="button"
                    onClick={() => handleAddCategory(sug)}
                    className="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 text-teal-300 border border-slate-750 text-[11px] flex items-center gap-1 transition cursor-pointer"
                  >
                    <Plus className="w-3 h-3 text-teal-400" />
                    <span>{sug}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Current Categories List */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                All Available Categories ({categories.length})
              </h4>
              {customCategories.length > 0 && (
                <span className="text-[10px] text-teal-400 font-semibold">
                  {customCategories.length} Custom Added
                </span>
              )}
            </div>

            <div className="grid grid-cols-2 gap-2">
              {categories.map(c => {
                const isCustom = customCategories.includes(c);
                const isRent = c.toLowerCase().includes('rent') || c.toLowerCase().includes('housing');
                return (
                  <div
                    key={c}
                    className={`p-2.5 rounded-xl border flex items-center justify-between ${
                      isRent
                        ? 'bg-indigo-950/30 border-indigo-500/30 text-indigo-200'
                        : isCustom
                        ? 'bg-teal-950/20 border-teal-500/30 text-teal-200'
                        : 'bg-slate-950 border-slate-850 text-slate-300'
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate">
                      {isRent ? (
                        <Home className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                      ) : (
                        <div className="w-2 h-2 rounded-full bg-teal-400 shrink-0" />
                      )}
                      <span className="font-semibold truncate">{c}</span>
                    </div>

                    {isCustom && (
                      <button
                        type="button"
                        onClick={() => handleDeleteCustom(c)}
                        className="p-1 text-slate-500 hover:text-rose-400 transition cursor-pointer shrink-0"
                        title="Delete custom category"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 bg-slate-950 border-t border-slate-800 flex justify-end shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="px-5 py-2 bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs rounded-xl transition cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
