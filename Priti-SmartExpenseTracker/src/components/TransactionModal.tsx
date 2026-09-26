import React, { useState, useEffect } from 'react';
import { X, AlertTriangle, Check, Calendar, Tag, CreditCard, FileText, Store } from 'lucide-react';
import { Transaction, TransactionCategory, PaymentMode } from '../types';
import { CATEGORY_CONFIG } from './CategoryIcon';
import { checkDuplicateTransaction } from '../utils/storage';
import { formatINR } from '../utils/formatters';

interface TransactionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (transactionData: Omit<Transaction, 'id' | 'createdAt'>) => void;
  editingTransaction?: Transaction | null;
}

const CATEGORIES: TransactionCategory[] = [
  'Food',
  'Travel',
  'Shopping',
  'Bills',
  'Investment',
  'Healthcare',
  'Entertainment',
  'Other',
];

const PAYMENT_MODES: PaymentMode[] = ['UPI', 'Card', 'Cash', 'Bank Transfer'];

export const TransactionModal: React.FC<TransactionModalProps> = ({
  isOpen,
  onClose,
  onSave,
  editingTransaction,
}) => {
  const [date, setDate] = useState<string>(new Date().toISOString().slice(0, 10));
  const [amount, setAmount] = useState<string>('');
  const [category, setCategory] = useState<TransactionCategory>('Food');
  const [merchantName, setMerchantName] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [paymentMode, setPaymentMode] = useState<PaymentMode>('UPI');
  const [duplicates, setDuplicates] = useState<Transaction[]>([]);
  const [acknowledgedDuplicate, setAcknowledgedDuplicate] = useState(false);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    if (editingTransaction) {
      setDate(editingTransaction.date);
      setAmount(editingTransaction.amount.toString());
      setCategory(editingTransaction.category);
      setMerchantName(editingTransaction.merchantName || '');
      setDescription(editingTransaction.description || '');
      setPaymentMode(editingTransaction.paymentMode);
    } else {
      setDate(new Date().toISOString().slice(0, 10));
      setAmount('');
      setCategory('Food');
      setMerchantName('');
      setDescription('');
      setPaymentMode('UPI');
    }
    setDuplicates([]);
    setAcknowledgedDuplicate(false);
    setError('');
  }, [editingTransaction, isOpen]);

  // Check for duplicates when date or amount changes
  useEffect(() => {
    const numAmount = parseFloat(amount);
    if (date && !isNaN(numAmount) && numAmount > 0) {
      const found = checkDuplicateTransaction(date, numAmount, editingTransaction?.id);
      setDuplicates(found);
    } else {
      setDuplicates([]);
    }
  }, [date, amount, editingTransaction]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const numAmount = parseFloat(amount);

    if (isNaN(numAmount) || numAmount <= 0) {
      setError('Please enter a valid amount greater than ₹0');
      return;
    }
    if (!description.trim() && !merchantName.trim()) {
      setError('Please provide a description or merchant name');
      return;
    }

    // Edge case: Duplicate detection warning
    if (duplicates.length > 0 && !acknowledgedDuplicate) {
      setError('A transaction with the exact same date and amount already exists. Check the warning below and confirm to proceed.');
      return;
    }

    onSave({
      date,
      amount: numAmount,
      category,
      merchantName: merchantName.trim() || undefined,
      description: description.trim() || merchantName.trim() || 'Expense',
      paymentMode,
      source: editingTransaction ? editingTransaction.source : 'manual',
      lineItems: editingTransaction?.lineItems,
    });

    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 overflow-y-auto animate-in fade-in">
      <div className="relative w-full max-w-lg rounded-2xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden my-8">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              {editingTransaction ? 'Edit Transaction' : 'Add New Transaction'}
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              {category === 'Investment'
                ? 'Track contributions, mutual funds, gold or SIPs'
                : 'Log personal or household expenditure'}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-xs font-medium text-rose-700 dark:text-rose-300">
              {error}
            </div>
          )}

          {/* Duplicate Detection Warning Banner */}
          {duplicates.length > 0 && (
            <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800 text-amber-900 dark:text-amber-200">
              <div className="flex items-start gap-2.5">
                <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                <div className="text-xs space-y-1">
                  <p className="font-semibold text-amber-900 dark:text-amber-300">
                    Potential Duplicate Detected!
                  </p>
                  <p className="text-amber-700 dark:text-amber-300">
                    Found {duplicates.length} existing entry with {formatINR(parseFloat(amount))} on{' '}
                    {date}:
                  </p>
                  <ul className="list-disc list-inside space-y-0.5 font-medium pl-1">
                    {duplicates.map((d) => (
                      <li key={d.id}>
                        {d.merchantName || d.description} ({d.category})
                      </li>
                    ))}
                  </ul>
                  <label className="flex items-center gap-2 mt-2 pt-1 font-medium cursor-pointer">
                    <input
                      type="checkbox"
                      checked={acknowledgedDuplicate}
                      onChange={(e) => setAcknowledgedDuplicate(e.target.checked)}
                      className="rounded text-emerald-600 focus:ring-emerald-500 w-4 h-4 cursor-pointer"
                    />
                    <span>Yes, this is a separate valid transaction, not a duplicate</span>
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* Amount & Date Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Amount (₹) <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 font-semibold text-base">
                  ₹
                </span>
                <input
                  type="number"
                  step="any"
                  placeholder="0.00"
                  required
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="w-full pl-8 pr-4 py-2.5 text-base font-bold rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-hidden focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Date <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <Calendar className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                <input
                  type="date"
                  required
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  className="w-full pl-10 pr-3 py-2.5 text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-hidden focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition"
                />
              </div>
            </div>
          </div>

          {/* Category Selector */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 flex items-center gap-1.5">
              <Tag className="w-3.5 h-3.5" />
              <span>Category</span>
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {CATEGORIES.map((cat) => {
                const config = CATEGORY_CONFIG[cat];
                const isSelected = category === cat;
                const Icon = config.icon;
                return (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => setCategory(cat)}
                    className={`flex items-center gap-2 p-2 rounded-xl border text-xs font-medium transition cursor-pointer text-left ${
                      isSelected
                        ? 'border-emerald-600 bg-emerald-50 dark:bg-emerald-950/50 text-emerald-800 dark:text-emerald-300 font-semibold shadow-xs ring-1 ring-emerald-600'
                        : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/60 text-slate-700 dark:text-slate-300 hover:border-slate-300 dark:hover:border-slate-600'
                    }`}
                  >
                    <div
                      className={`p-1 rounded-lg ${
                        isSelected ? 'bg-emerald-600 text-white' : `${config.bg} ${config.color}`
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <span className="truncate">{cat}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Merchant / Store */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 flex items-center gap-1.5">
              <Store className="w-3.5 h-3.5" />
              <span>Merchant / Entity Name</span>
            </label>
            <input
              type="text"
              placeholder="e.g. Swiggy, Uber, Tata Power, HDFC AMC"
              value={merchantName}
              onChange={(e) => setMerchantName(e.target.value)}
              className="w-full px-3.5 py-2.5 text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-hidden focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5" />
              <span>Description / Items</span>
            </label>
            <input
              type="text"
              placeholder="e.g. Dinner with team, Grocery essentials"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3.5 py-2.5 text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-hidden focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition"
            />
          </div>

          {/* Payment Mode */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 flex items-center gap-1.5">
              <CreditCard className="w-3.5 h-3.5" />
              <span>Payment Mode</span>
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {PAYMENT_MODES.map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setPaymentMode(mode)}
                  className={`py-2 px-3 text-xs font-medium rounded-xl border transition cursor-pointer text-center ${
                    paymentMode === mode
                      ? 'border-emerald-600 bg-emerald-50 dark:bg-emerald-950/50 text-emerald-800 dark:text-emerald-300 font-semibold ring-1 ring-emerald-600'
                      : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/60 text-slate-700 dark:text-slate-300 hover:border-slate-300'
                  }`}
                >
                  {mode}
                </button>
              ))}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold rounded-xl text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="inline-flex items-center gap-2 px-5 py-2.5 text-xs font-semibold rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition active:scale-98 cursor-pointer"
            >
              <Check className="w-4 h-4" />
              <span>{editingTransaction ? 'Save Changes' : 'Add Transaction'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
