import React, { useState, useRef } from 'react';
import {
  X,
  Plus,
  CreditCard,
  Building,
  AlertTriangle,
  Sparkles,
  ArrowRightLeft,
  Camera,
  Upload,
  Image as ImageIcon,
  Trash2
} from 'lucide-react';
import { Account, ExpenseCategory, Transaction, TransactionType, ReceiptItem, CategorySplit } from '../types/finance';
import { cleanMerchantName, categorizeMerchant, detectRedFlag } from '../services/categorizer';
import { StorageService } from '../services/storage';
import { CategoryManagerModal } from './CategoryManagerModal';
import { ReceiptScannerModal } from './ReceiptScannerModal';

interface AddTransactionModalProps {
  accounts: Account[];
  onClose: () => void;
  onAddTransaction: (tx: Partial<Transaction>) => void;
  onOpenAddAccountModal?: () => void;
}

export const AddTransactionModal: React.FC<AddTransactionModalProps> = ({
  accounts,
  onClose,
  onAddTransaction,
  onOpenAddAccountModal
}) => {
  const [categories, setCategories] = useState<ExpenseCategory[]>(() =>
    StorageService.getAllExpenseCategories()
  );
  const [categoryModalOpen, setCategoryModalOpen] = useState(false);
  const [type, setType] = useState<TransactionType>('expense');
  const [amountStr, setAmountStr] = useState('');
  const [currency, setCurrency] = useState('USD');
  const [foreignAmountStr, setForeignAmountStr] = useState('');
  const [merchant, setMerchant] = useState('');
  const [category, setCategory] = useState<ExpenseCategory>('Food');
  const [accountId, setAccountId] = useState(accounts[0]?.id || '');
  const [toAccountId, setToAccountId] = useState(accounts[1]?.id || accounts[0]?.id || '');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [notes, setNotes] = useState('');
  const [isForeign, setIsForeign] = useState(false);
  const [receiptImage, setReceiptImage] = useState<string | null>(null);
  const [rememberedLedgerName, setRememberedLedgerName] = useState<string | null>(null);

  // Receipt OCR states
  const [ocrModalOpen, setOcrModalOpen] = useState(false);
  const [receiptItems, setReceiptItems] = useState<ReceiptItem[]>([]);
  const [categorySplits, setCategorySplits] = useState<CategorySplit[]>([]);

  const cameraInputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Compress image to Base64 to preserve storage
  const handleImageFile = (file: File) => {
    const reader = new FileReader();
    reader.onload = e => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        const maxDimension = 800;
        let width = img.width;
        let height = img.height;

        if (width > height) {
          if (width > maxDimension) {
            height = Math.round((height * maxDimension) / width);
            width = maxDimension;
          }
        } else {
          if (height > maxDimension) {
            width = Math.round((width * maxDimension) / height);
            height = maxDimension;
          }
        }

        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.drawImage(img, 0, 0, width, height);
          const compressedDataUrl = canvas.toDataURL('image/jpeg', 0.7);
          setReceiptImage(compressedDataUrl);
        }
      };
      if (typeof e.target?.result === 'string') {
        img.src = e.target.result;
      }
    };
    reader.readAsDataURL(file);
  };

  const handleCameraChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleImageFile(e.target.files[0]);
    }
  };

  const handleUploadChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleImageFile(e.target.files[0]);
    }
  };

  // Convert USD/FX to AED automatically
  const handleForeignAmountChange = (foreignVal: string, targetCurrency = currency) => {
    setForeignAmountStr(foreignVal);
    const parsed = parseFloat(foreignVal);
    if (!isNaN(parsed) && parsed > 0) {
      if (targetCurrency === 'USD') {
        // UAE Central Bank pegged rate
        setAmountStr((parsed * 3.6725).toFixed(2));
      } else if (targetCurrency === 'EUR') {
        setAmountStr((parsed * 3.98).toFixed(2));
      } else if (targetCurrency === 'GBP') {
        setAmountStr((parsed * 4.65).toFixed(2));
      } else if (targetCurrency === 'INR') {
        setAmountStr((parsed * 0.044).toFixed(2));
      } else if (targetCurrency === 'SAR' || targetCurrency === 'QAR') {
        setAmountStr((parsed * 0.98).toFixed(2));
      } else if (targetCurrency === 'OMR') {
        setAmountStr((parsed * 9.54).toFixed(2));
      } else if (targetCurrency === 'CAD') {
        setAmountStr((parsed * 2.70).toFixed(2));
      }
    }
  };

  const handleCurrencyChange = (newCurr: string) => {
    setCurrency(newCurr);
    if (foreignAmountStr) {
      handleForeignAmountChange(foreignAmountStr, newCurr);
    }
  };

  // Auto-categorize & Auto-select remembered ledger as user types merchant name
  const handleMerchantChange = (val: string) => {
    setMerchant(val);
    if (val.length >= 2) {
      if (type === 'expense') {
        const suggested = categorizeMerchant(val);
        if (suggested !== 'Other') {
          setCategory(suggested);
        }
      }

      // Check if this merchant was previously recorded in a particular ledger
      const rememberedAccId = StorageService.findRememberedLedger(val);
      if (rememberedAccId) {
        const matched = accounts.find(a => a.id === rememberedAccId);
        if (matched) {
          setAccountId(matched.id);
          setRememberedLedgerName(matched.name);
          return;
        }
      }
      setRememberedLedgerName(null);
    } else {
      setRememberedLedgerName(null);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const amt = parseFloat(amountStr);
    if (isNaN(amt) || amt <= 0 || !merchant.trim()) return;

    const isInternational = isForeign && currency !== 'AED';
    let originalAmount: number | undefined = undefined;
    let originalCurrency: string | undefined = undefined;
    let exchangeRate: number | undefined = undefined;

    if (isInternational) {
      originalAmount = parseFloat(foreignAmountStr) || (currency === 'USD' ? Number((amt / 3.6725).toFixed(2)) : amt);
      originalCurrency = currency;
      exchangeRate = originalAmount > 0 ? Number((amt / originalAmount).toFixed(4)) : (currency === 'USD' ? 3.6725 : undefined);
    }

    const redCheck = detectRedFlag({
      currency: isInternational ? currency : 'AED',
      amount: amt,
      merchant,
      highThresholdAED: 1500
    });

    const isFlagged = Boolean(redCheck.isRedFlag || isInternational);
    const flagReason = isInternational
      ? `International transaction (${currency} ${originalAmount?.toFixed(2) || ''}) - pending genuine confirmation`
      : redCheck.reason;

    onAddTransaction({
      amount: amt,
      originalAmount,
      originalCurrency,
      exchangeRate,
      currency: 'AED',
      merchant: merchant.trim(),
      category: type === 'income' ? 'Other' : category,
      date,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      accountId: accountId || accounts[0]?.id || 'acc-cash',
      toAccountId: type === 'transfer' || type === 'card_payment' ? toAccountId : undefined,
      type,
      source: 'manual',
      isRedFlag: isFlagged,
      redFlagReason: flagReason,
      // If international, must NOT be verified until user confirms genuine
      isVerifiedByUser: !isInternational,
      notes: notes.trim(),
      receiptImage: receiptImage || undefined,
      hasReceipt: Boolean(receiptImage || receiptItems.length > 0),
      items: receiptItems.length > 0 ? receiptItems : undefined,
      categorySplits: categorySplits.length > 0 ? categorySplits : undefined
    });

    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end sm:justify-center items-center bg-black/80 backdrop-blur-sm p-0 sm:p-4 overflow-hidden animate-fade-in">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-t-3xl sm:rounded-2xl shadow-2xl flex flex-col max-h-[92vh] sm:max-h-[90vh] overflow-hidden">
        {/* Header - Fixed & sticky */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800 bg-slate-950/70 shrink-0">
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            Record Transaction
          </h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
            title="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Modal Body */}
        <div className="overflow-y-auto px-5 py-4 flex-1 min-h-0 space-y-4">
          {/* Transaction Type Segmented Control */}
          <div className="grid grid-cols-4 gap-1 p-1 bg-slate-950 rounded-xl mb-4 text-xs font-semibold">
            {(['expense', 'income', 'transfer', 'card_payment'] as TransactionType[]).map(t => (
              <button
                key={t}
                type="button"
                onClick={() => setType(t)}
                className={`py-2 px-1 rounded-lg transition capitalize whitespace-nowrap cursor-pointer ${
                  type === t
                    ? 'bg-teal-500 text-slate-950 font-bold shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {t === 'card_payment' ? 'Card Pay' : t}
              </button>
            ))}
          </div>

        {/* Scan Receipt OCR Trigger Banner */}
        {type === 'expense' && (
          <div className="mb-3.5">
            <button
              type="button"
              onClick={() => setOcrModalOpen(true)}
              className="w-full p-3 rounded-2xl bg-gradient-to-r from-emerald-950/70 via-teal-950/60 to-slate-900 border border-emerald-500/40 hover:border-emerald-400 transition cursor-pointer text-left flex items-center justify-between group shadow-sm"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-xl bg-emerald-500/20 text-emerald-300 flex items-center justify-center shrink-0 group-hover:scale-105 transition">
                  <Camera className="w-4 h-4 text-emerald-400" />
                </div>
                <div>
                  <div className="text-xs font-bold text-white flex items-center gap-2">
                    📸 Scan Receipt / Bill (AI OCR)
                    <span className="text-[10px] font-bold text-emerald-300 bg-emerald-500/20 px-1.5 py-0.2 rounded-full border border-emerald-500/30">
                      Auto-Split
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400">
                    Extract items, allocate categories (e.g. Nesto Clothing + Groceries) without VAT
                  </div>
                </div>
              </div>
              <span className="text-xs font-bold text-emerald-400 group-hover:underline">
                Scan &rarr;
              </span>
            </button>

            {/* If receipt items are already attached, show split breakdown */}
            {categorySplits.length > 0 && (
              <div className="mt-2 p-2.5 rounded-xl bg-slate-950 border border-emerald-500/30 text-xs space-y-1.5">
                <div className="flex items-center justify-between text-[11px] font-bold text-emerald-400">
                  <span>🧾 Receipt Split ({receiptItems.length} items):</span>
                  <button
                    type="button"
                    onClick={() => setOcrModalOpen(true)}
                    className="text-[10px] text-teal-300 hover:underline cursor-pointer"
                  >
                    Edit Items
                  </button>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {categorySplits.map(s => (
                    <span
                      key={s.category}
                      className="px-2 py-0.5 rounded-lg bg-slate-900 border border-slate-700 text-slate-200 text-[10px] font-semibold"
                    >
                      {s.category}: <span className="text-emerald-400 font-bold">AED {s.amount.toFixed(2)}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
          {/* Amount Input */}
          <div>
            <div className="flex justify-between text-slate-400 mb-1">
              <span>Amount in AED:</span>
              <button
                type="button"
                onClick={() => setIsForeign(!isForeign)}
                className="text-teal-400 hover:underline cursor-pointer"
              >
                {isForeign ? 'Default AED' : '+ Foreign Currency?'}
              </button>
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
                value={amountStr}
                onChange={e => setAmountStr(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl pl-14 pr-4 py-2.5 text-base font-bold text-white focus:outline-none focus:border-teal-500"
                required
                autoFocus
              />
            </div>
          </div>

          {/* Foreign Currency Sub-field if toggled */}
          {isForeign && (
            <div className="p-3.5 rounded-xl bg-slate-950 border border-rose-500/30 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-rose-300 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
                  International Currency (Auto-Red Flagged):
                </span>
                {currency === 'USD' && (
                  <span className="text-[10px] text-teal-300 font-mono bg-teal-950/60 border border-teal-500/30 px-1.5 py-0.5 rounded">
                    1 USD = 3.6725 AED
                  </span>
                )}
              </div>
              <div className="flex gap-2">
                <select
                  value={currency}
                  onChange={e => handleCurrencyChange(e.target.value)}
                  className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-white font-medium focus:border-teal-500 focus:outline-none"
                >
                  <option value="USD">USD ($)</option>
                  <option value="EUR">EUR (€)</option>
                  <option value="GBP">GBP (£)</option>
                  <option value="INR">INR (₹)</option>
                  <option value="SAR">SAR</option>
                  <option value="OMR">OMR</option>
                  <option value="QAR">QAR</option>
                  <option value="CAD">CAD</option>
                </select>
                <div className="flex-1 relative">
                  <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-400">
                    {currency}
                  </span>
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Foreign amount"
                    value={foreignAmountStr}
                    onChange={e => handleForeignAmountChange(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-12 pr-3 py-1.5 text-white text-xs font-semibold focus:border-teal-500 focus:outline-none"
                  />
                </div>
              </div>
              <p className="text-[10px] text-slate-400 leading-normal">
                {currency === 'USD'
                  ? 'Automatically converted to AED at 3.6725. This foreign purchase will appear under Red Flags until you confirm it is genuine. You can use the "Alter" button to change foreign rates/amounts.'
                  : `Entered ${currency} amount will calculate AED. Foreign transactions are placed in Red Flags until confirmed genuine.`}
              </p>
            </div>
          )}

          {/* Merchant / Description with auto-categorization */}
          <div>
            <label className="block text-slate-400 mb-1">
              {type === 'income' ? 'Income Source / Employer:' : 'Merchant / Expense Description:'}
            </label>
            <input
              type="text"
              placeholder={
                type === 'income'
                  ? 'e.g. Salary, Consulting, Cash Deposit'
                  : 'e.g. Lunch Cafeteria, Taxi, Grocery, ENOC Petrol'
              }
              value={merchant}
              onChange={e => handleMerchantChange(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2 text-white text-xs focus:outline-none focus:border-teal-500"
              required
            />
          </div>

          {/* Category selection (if expense) */}
          {type === 'expense' && (
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-slate-400">
                  Category (Auto-selected by AI):
                </label>
                <button
                  type="button"
                  onClick={() => setCategoryModalOpen(true)}
                  className="text-teal-400 hover:text-teal-300 text-[11px] font-semibold flex items-center gap-1 cursor-pointer"
                >
                  <Plus className="w-3 h-3" />
                  <span>Add / Manage Category</span>
                </button>
              </div>
              <div className="grid grid-cols-3 gap-1.5 max-h-36 overflow-y-auto p-1 bg-slate-950 rounded-xl border border-slate-800">
                {categories.map(c => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setCategory(c)}
                    className={`py-1.5 px-2 rounded-lg text-[11px] font-semibold transition cursor-pointer truncate ${
                      category === c
                        ? 'bg-teal-500 text-slate-950 font-bold'
                        : 'text-slate-400 hover:text-white bg-slate-900'
                    }`}
                  >
                    {c}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Account Selection */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="text-slate-400 flex items-center gap-1.5 flex-wrap">
                  <span>{type === 'transfer' || type === 'card_payment' ? 'From Ledger:' : 'Ledger Account:'}</span>
                  {rememberedLedgerName && (
                    <span className="text-[10px] text-teal-300 font-medium bg-teal-500/15 px-1.5 py-0.5 rounded border border-teal-500/30 animate-fade-in flex items-center gap-1">
                      <span>⚡ Remembered</span>
                    </span>
                  )}
                </label>
                {onOpenAddAccountModal && (
                  <button
                    type="button"
                    onClick={onOpenAddAccountModal}
                    className="text-teal-400 hover:underline text-[10px]"
                  >
                    + Add Account
                  </button>
                )}
              </div>
              <select
                value={accountId}
                onChange={e => {
                  setAccountId(e.target.value);
                  setRememberedLedgerName(null);
                }}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white"
              >
                {accounts.length === 0 ? (
                  <option value="acc-cash">Cash Wallet</option>
                ) : (
                  accounts.map(a => (
                    <option key={a.id} value={a.id}>
                      {a.name} ({a.accountNumberMasked})
                    </option>
                  ))
                )}
              </select>
            </div>

            {(type === 'transfer' || type === 'card_payment') && (
              <div>
                <label className="block text-slate-400 mb-1">To Account:</label>
                <select
                  value={toAccountId}
                  onChange={e => setToAccountId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white"
                >
                  {accounts.map(a => (
                    <option key={a.id} value={a.id}>
                      {a.name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {!(type === 'transfer' || type === 'card_payment') && (
              <div>
                <label className="block text-slate-400 mb-1">Transaction Date:</label>
                <input
                  type="date"
                  value={date}
                  onChange={e => setDate(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white"
                />
              </div>
            )}
          </div>

          {/* Photo Capture & Upload Receipt Section */}
          <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl">
            <label className="block text-slate-300 font-semibold mb-2 flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Camera className="w-3.5 h-3.5 text-teal-400" />
                Receipt Photo / Cash Bill (Optional)
              </span>
              {receiptImage && (
                <button
                  type="button"
                  onClick={() => setReceiptImage(null)}
                  className="text-rose-400 hover:text-rose-300 text-[10px] flex items-center gap-1"
                >
                  <Trash2 className="w-3 h-3" />
                  Remove
                </button>
              )}
            </label>

            {receiptImage ? (
              <div className="relative rounded-lg overflow-hidden border border-teal-500/40 max-h-44 flex items-center justify-center bg-black">
                <img
                  src={receiptImage}
                  alt="Receipt Preview"
                  className="max-h-44 w-auto object-contain"
                />
              </div>
            ) : (
              <div className="flex gap-2">
                {/* Mobile Camera Capture Button */}
                <button
                  type="button"
                  onClick={() => cameraInputRef.current?.click()}
                  className="flex-1 py-2 px-3 rounded-lg bg-slate-900 border border-slate-700 hover:border-teal-500/50 hover:bg-slate-850 text-slate-300 text-xs font-medium flex items-center justify-center gap-1.5 transition cursor-pointer"
                >
                  <Camera className="w-4 h-4 text-teal-400" />
                  <span>Take Photo</span>
                </button>
                <input
                  ref={cameraInputRef}
                  type="file"
                  accept="image/*"
                  capture="environment"
                  className="hidden"
                  onChange={handleCameraChange}
                />

                {/* File Upload from Gallery Button */}
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="flex-1 py-2 px-3 rounded-lg bg-slate-900 border border-slate-700 hover:border-teal-500/50 hover:bg-slate-850 text-slate-300 text-xs font-medium flex items-center justify-center gap-1.5 transition cursor-pointer"
                >
                  <Upload className="w-4 h-4 text-sky-400" />
                  <span>Upload Image</span>
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={handleUploadChange}
                />
              </div>
            )}
          </div>

          {/* Notes */}
          <div>
            <label className="block text-slate-400 mb-1">Notes / Tag (Optional):</label>
            <input
              type="text"
              placeholder="e.g. Cash grocery, receipt attached"
              value={notes}
              onChange={e => setNotes(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2 text-white text-xs"
            />
          </div>

          {/* Action Buttons: Cancel and Save Transaction */}
          <div className="pt-3 pb-3 flex items-center gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-3 px-4 bg-slate-800 hover:bg-slate-700 active:bg-slate-700 text-slate-300 hover:text-white font-bold text-xs rounded-xl border border-slate-700 transition cursor-pointer text-center"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 py-3 px-4 bg-teal-500 hover:bg-teal-400 active:bg-teal-300 text-slate-950 font-extrabold text-xs rounded-xl shadow-lg shadow-teal-500/20 transition cursor-pointer text-center"
            >
              Save Transaction
            </button>
          </div>
        </form>
        </div>
      </div>

      {categoryModalOpen && (
        <CategoryManagerModal
          onClose={() => setCategoryModalOpen(false)}
          onCategoriesUpdated={updated => setCategories(updated)}
          onSelectCategory={chosen => {
            setCategory(chosen);
            setCategoryModalOpen(false);
          }}
        />
      )}

      {ocrModalOpen && (
        <ReceiptScannerModal
          initialMerchant={merchant || 'Nesto Hypermarket'}
          initialAmount={parseFloat(amountStr) || 100}
          onClose={() => setOcrModalOpen(false)}
          onSaveReceiptData={(result) => {
            setMerchant(result.merchant);
            setAmountStr(result.amount.toFixed(2));
            setDate(result.date);
            setReceiptItems(result.items);
            setCategorySplits(result.categorySplits);
            if (result.receiptImage) {
              setReceiptImage(result.receiptImage);
            }
            if (result.categorySplits.length > 0) {
              setCategory(result.categorySplits[0].category);
            }
            if (!notes) {
              setNotes(`Receipt attached: ${result.categorySplits.map(s => `${s.category} AED ${s.amount.toFixed(2)}`).join(', ')}`);
            }
            setOcrModalOpen(false);
          }}
        />
      )}
    </div>
  );
};
