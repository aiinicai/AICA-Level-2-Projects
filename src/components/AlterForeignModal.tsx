import React, { useState, useEffect } from 'react';
import {
  X,
  Globe,
  CheckCircle2,
  AlertOctagon,
  RefreshCw,
  ArrowRight,
  ShieldCheck,
  Calculator,
  Sliders,
  Check
} from 'lucide-react';
import { Account, ExpenseCategory, Transaction } from '../types/finance';

interface AlterForeignModalProps {
  transaction: Transaction;
  accounts: Account[];
  onClose: () => void;
  onSave: (updated: Transaction) => void;
}

const COMMON_CURRENCIES: { code: string; name: string; defaultRate: number; symbol: string }[] = [
  { code: 'USD', name: 'US Dollar', defaultRate: 3.6725, symbol: '$' },
  { code: 'EUR', name: 'Euro', defaultRate: 3.98, symbol: '€' },
  { code: 'GBP', name: 'British Pound', defaultRate: 4.65, symbol: '£' },
  { code: 'INR', name: 'Indian Rupee', defaultRate: 0.044, symbol: '₹' },
  { code: 'SAR', name: 'Saudi Riyal', defaultRate: 0.98, symbol: 'SAR' },
  { code: 'CAD', name: 'Canadian Dollar', defaultRate: 2.70, symbol: 'C$' },
  { code: 'AUD', name: 'Australian Dollar', defaultRate: 2.40, symbol: 'A$' },
  { code: 'SGD', name: 'Singapore Dollar', defaultRate: 2.75, symbol: 'S$' },
  { code: 'JPY', name: 'Japanese Yen', defaultRate: 0.024, symbol: '¥' },
  { code: 'CHF', name: 'Swiss Franc', defaultRate: 4.10, symbol: 'CHF' },
  { code: 'QAR', name: 'Qatari Riyal', defaultRate: 1.01, symbol: 'QAR' },
  { code: 'OMR', name: 'Omani Rial', defaultRate: 9.54, symbol: 'OMR' }
];

const CATEGORIES: ExpenseCategory[] = [
  'Petrol',
  'Food',
  'Groceries',
  'Utilities',
  'Telecom',
  'Shopping',
  'Transport',
  'Healthcare',
  'Entertainment',
  'Travel',
  'Education',
  'Salary',
  'Other'
];

export const AlterForeignModal: React.FC<AlterForeignModalProps> = ({
  transaction,
  accounts,
  onClose,
  onSave
}) => {
  const initialCurrency = transaction.originalCurrency || (transaction.currency !== 'AED' ? transaction.currency : 'USD');
  const initialForeignAmt = transaction.originalAmount || (transaction.originalCurrency === 'USD' ? transaction.amount / 3.6725 : transaction.amount);
  const initialRate = transaction.exchangeRate || (initialCurrency === 'USD' ? 3.6725 : transaction.amount / (initialForeignAmt || 1));

  const [foreignCurrency, setForeignCurrency] = useState(initialCurrency);
  const [foreignAmountStr, setForeignAmountStr] = useState(initialForeignAmt ? initialForeignAmt.toFixed(2) : '');
  const [exchangeRateStr, setExchangeRateStr] = useState(initialRate ? initialRate.toFixed(4) : '3.6725');
  const [convertedAedStr, setConvertedAedStr] = useState(transaction.amount.toFixed(2));
  const [merchant, setMerchant] = useState(transaction.merchant);
  const [category, setCategory] = useState<ExpenseCategory>(transaction.category);
  const [accountId, setAccountId] = useState(transaction.accountId);
  const [notes, setNotes] = useState(transaction.notes || '');
  const [markAsGenuine, setMarkAsGenuine] = useState(!transaction.isRedFlag || transaction.isVerifiedByUser);

  // Recalculate converted AED when foreign amount or exchange rate changes
  const handleForeignAmountChange = (val: string) => {
    setForeignAmountStr(val);
    const amt = parseFloat(val);
    const rate = parseFloat(exchangeRateStr);
    if (!isNaN(amt) && !isNaN(rate) && amt > 0 && rate > 0) {
      setConvertedAedStr((amt * rate).toFixed(2));
    }
  };

  const handleExchangeRateChange = (val: string) => {
    setExchangeRateStr(val);
    const rate = parseFloat(val);
    const amt = parseFloat(foreignAmountStr);
    if (!isNaN(amt) && !isNaN(rate) && amt > 0 && rate > 0) {
      setConvertedAedStr((amt * rate).toFixed(2));
    }
  };

  // If user inputs the exact billed AED amount from their credit card statement, calculate effective rate
  const handleConvertedAedChange = (val: string) => {
    setConvertedAedStr(val);
    const aed = parseFloat(val);
    const foreign = parseFloat(foreignAmountStr);
    if (!isNaN(aed) && !isNaN(foreign) && foreign > 0 && aed > 0) {
      setExchangeRateStr((aed / foreign).toFixed(4));
    }
  };

  const handleSelectCurrency = (code: string) => {
    setForeignCurrency(code);
    const found = COMMON_CURRENCIES.find(c => c.code === code);
    const defaultRate = found ? found.defaultRate : (code === 'USD' ? 3.6725 : 1.0);
    setExchangeRateStr(defaultRate.toFixed(4));

    const amt = parseFloat(foreignAmountStr);
    if (!isNaN(amt) && amt > 0) {
      setConvertedAedStr((amt * defaultRate).toFixed(2));
    }
  };

  const applyPresetRate = (rate: number) => {
    setExchangeRateStr(rate.toFixed(4));
    const amt = parseFloat(foreignAmountStr);
    if (!isNaN(amt) && amt > 0) {
      setConvertedAedStr((amt * rate).toFixed(2));
    }
  };

  const handleSave = (confirmAsGenuineChoice?: boolean) => {
    const finalAed = parseFloat(convertedAedStr);
    const foreignAmt = parseFloat(foreignAmountStr);
    const finalRate = parseFloat(exchangeRateStr);

    if (isNaN(finalAed) || finalAed <= 0) return;

    const willBeGenuine = confirmAsGenuineChoice !== undefined ? confirmAsGenuineChoice : markAsGenuine;

    const updated: Transaction = {
      ...transaction,
      amount: finalAed,
      originalAmount: !isNaN(foreignAmt) && foreignAmt > 0 ? foreignAmt : undefined,
      originalCurrency: foreignCurrency,
      exchangeRate: !isNaN(finalRate) && finalRate > 0 ? finalRate : 3.6725,
      currency: 'AED',
      merchant: merchant.trim() || transaction.merchant,
      category,
      accountId,
      isRedFlag: willBeGenuine ? false : true,
      isVerifiedByUser: willBeGenuine,
      redFlagReason: willBeGenuine
        ? undefined
        : `International foreign transaction (${foreignCurrency}) - pending confirmation`,
      notes: notes.trim()
    };

    onSave(updated);
    onClose();
  };

  const currentAcc = accounts.find(a => a.id === accountId);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="w-full max-w-lg bg-slate-900 border border-slate-700/80 rounded-2xl p-6 shadow-2xl my-6 animate-fade-in">
        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-teal-500/20 text-teal-400 flex items-center justify-center">
              <Globe className="w-5 h-5 text-teal-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">Alter Foreign Transaction</h3>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-teal-500/20 text-teal-300 border border-teal-500/30">
                  {foreignCurrency} → AED
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Adjust foreign currency amount, bank exchange rate markup, or final billed AED total
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Current Transaction Context */}
        <div className="my-4 p-3 bg-slate-950/80 rounded-xl border border-slate-800 text-xs flex items-center justify-between">
          <div>
            <span className="text-slate-400 block text-[10px]">Merchant &amp; Source:</span>
            <span className="text-white font-bold">{transaction.merchant}</span>
            <span className="text-slate-400 text-[11px] block">
              {transaction.bankName || currentAcc?.name || 'UAE Bank'} · {transaction.date}
            </span>
          </div>
          <div className="text-right">
            <span className="text-slate-400 block text-[10px]">Current Recorded:</span>
            <span className="text-teal-400 font-bold tabular-nums">AED {transaction.amount.toFixed(2)}</span>
            {transaction.originalAmount && (
              <span className="text-slate-400 text-[10px] block tabular-nums">
                ({transaction.originalCurrency} {transaction.originalAmount.toFixed(2)})
              </span>
            )}
          </div>
        </div>

        <div className="space-y-4 text-xs">
          {/* Currency and Foreign Amount */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-slate-300 font-medium mb-1">Foreign Currency:</label>
              <select
                value={foreignCurrency}
                onChange={e => handleSelectCurrency(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white font-semibold focus:outline-none focus:border-teal-500"
              >
                {COMMON_CURRENCIES.map(c => (
                  <option key={c.code} value={c.code}>
                    {c.code} - {c.name} ({c.symbol})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-slate-300 font-medium mb-1">
                Foreign Amount ({foreignCurrency}):
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-bold">
                  {COMMON_CURRENCIES.find(c => c.code === foreignCurrency)?.symbol || foreignCurrency}
                </span>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  placeholder="0.00"
                  value={foreignAmountStr}
                  onChange={e => handleForeignAmountChange(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl pl-8 pr-3 py-2 text-white font-bold tabular-nums focus:outline-none focus:border-teal-500"
                />
              </div>
            </div>
          </div>

          {/* Exchange Rate & FX Markup Preset Helper */}
          <div className="p-3.5 bg-slate-950 rounded-xl border border-slate-800 space-y-2.5">
            <div className="flex items-center justify-between">
              <label className="text-slate-300 font-medium flex items-center gap-1.5">
                <Calculator className="w-3.5 h-3.5 text-teal-400" />
                Exchange Rate (1 {foreignCurrency} = AED):
              </label>
              <span className="text-[10px] text-teal-400 font-mono">
                {foreignCurrency === 'USD' ? 'UAE Peg: 3.6725' : ''}
              </span>
            </div>

            <div className="flex gap-2">
              <input
                type="number"
                step="0.0001"
                min="0.0001"
                placeholder="3.6725"
                value={exchangeRateStr}
                onChange={e => handleExchangeRateChange(e.target.value)}
                className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white font-mono text-xs focus:outline-none focus:border-teal-500"
              />
            </div>

            {/* Quick Presets for USD (Pegged rate + standard UAE credit card FX spreads) */}
            {foreignCurrency === 'USD' && (
              <div className="pt-1">
                <span className="text-[10px] text-slate-400 block mb-1.5 font-medium">
                  UAE Bank / Card FX Spread Presets:
                </span>
                <div className="grid grid-cols-4 gap-1.5 text-[10px]">
                  <button
                    type="button"
                    onClick={() => applyPresetRate(3.6725)}
                    className="py-1 px-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-700 text-teal-300 rounded-lg text-center font-semibold transition"
                    title="Exact UAE Central Bank Pegged Rate"
                  >
                    3.6725 (Peg)
                  </button>
                  <button
                    type="button"
                    onClick={() => applyPresetRate(3.7276)}
                    className="py-1 px-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 rounded-lg text-center transition"
                    title="+1.5% Standard Bank Spread"
                  >
                    3.7276 (+1.5%)
                  </button>
                  <button
                    type="button"
                    onClick={() => applyPresetRate(3.7643)}
                    className="py-1 px-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 rounded-lg text-center transition"
                    title="+2.5% Typical Credit Card Spread"
                  >
                    3.7643 (+2.5%)
                  </button>
                  <button
                    type="button"
                    onClick={() => applyPresetRate(3.7827)}
                    className="py-1 px-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 rounded-lg text-center transition"
                    title="+3.0% International POS Fee"
                  >
                    3.7827 (+3.0%)
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Final Converted AED Amount */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-slate-300 font-bold flex items-center gap-1.5">
                <span>Final Converted Amount (AED):</span>
              </label>
              <span className="text-[10px] text-slate-400">
                Type directly to match bank SMS
              </span>
            </div>
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm font-bold text-teal-400">
                AED
              </span>
              <input
                type="number"
                step="0.01"
                min="0.01"
                placeholder="0.00"
                value={convertedAedStr}
                onChange={e => handleConvertedAedChange(e.target.value)}
                className="w-full bg-slate-950 border-2 border-teal-500/50 rounded-xl pl-14 pr-4 py-2.5 text-base font-black text-white tabular-nums focus:outline-none focus:border-teal-400"
              />
            </div>
          </div>

          {/* Merchant & Category Edit */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-slate-300 font-medium mb-1">Merchant / Service:</label>
              <input
                type="text"
                value={merchant}
                onChange={e => setMerchant(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white"
              />
            </div>

            <div>
              <label className="block text-slate-300 font-medium mb-1">Expense Category:</label>
              <select
                value={category}
                onChange={e => setCategory(e.target.value as ExpenseCategory)}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white"
              >
                {CATEGORIES.map(cat => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Red Flag & Genuine Confirmation Toggle Box */}
          <div className={`p-3.5 rounded-xl border transition ${
            markAsGenuine
              ? 'bg-emerald-950/30 border-emerald-500/40'
              : 'bg-rose-950/30 border-rose-500/40'
          }`}>
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={markAsGenuine}
                onChange={e => setMarkAsGenuine(e.target.checked)}
                className="mt-0.5 w-4 h-4 text-emerald-500 rounded focus:ring-0 focus:outline-none accent-emerald-500"
              />
              <div className="space-y-0.5">
                <span className={`text-xs font-bold block ${markAsGenuine ? 'text-emerald-300' : 'text-rose-300'}`}>
                  {markAsGenuine
                    ? '✅ Confirmed Genuine Transaction (Resolves Red Flag)'
                    : '🔴 Keep Under Red Flags (Pending Review)'}
                </span>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  International transactions remain under red flags until explicitly confirmed by you. Checking this verifies you authorized this foreign spend.
                </p>
              </div>
            </label>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="mt-6 flex flex-col sm:flex-row gap-2.5">
          <button
            type="button"
            onClick={onClose}
            className="py-2.5 px-4 bg-slate-800 hover:bg-slate-750 text-slate-300 font-semibold text-xs rounded-xl transition"
          >
            Cancel
          </button>

          {!markAsGenuine && (
            <button
              type="button"
              onClick={() => handleSave(false)}
              className="py-2.5 px-4 bg-slate-800 hover:bg-slate-700 text-rose-300 font-semibold text-xs rounded-xl border border-rose-800/50 transition"
            >
              Save (Keep Flagged)
            </button>
          )}

          <button
            type="button"
            onClick={() => handleSave(true)}
            className="flex-1 py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl shadow-lg flex items-center justify-center gap-1.5 transition cursor-pointer"
          >
            <ShieldCheck className="w-4 h-4" />
            <span>Confirm Genuine &amp; Save</span>
          </button>
        </div>
      </div>
    </div>
  );
};
