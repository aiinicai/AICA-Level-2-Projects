import React, { useState, useRef } from 'react';
import {
  X,
  Camera,
  Upload,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Trash2,
  Plus,
  ScanLine,
  Image as ImageIcon,
  Layers,
  ArrowRight
} from 'lucide-react';
import { CategorySplit, ExpenseCategory, ReceiptItem, Transaction } from '../types/finance';
import {
  SAMPLE_RECEIPT_PRESETS,
  calculateCategorySplits,
  reconcileItemSplits,
  performReceiptOCR,
  SampleReceiptPreset
} from '../services/receiptOcr';
import { StorageService } from '../services/storage';

interface ReceiptScannerModalProps {
  initialMerchant?: string;
  initialAmount?: number;
  existingTransaction?: Transaction | null;
  onClose: () => void;
  onSaveReceiptData: (result: {
    merchant: string;
    amount: number;
    date: string;
    items: ReceiptItem[];
    categorySplits: CategorySplit[];
    receiptImage?: string;
  }) => void;
}

export const ReceiptScannerModal: React.FC<ReceiptScannerModalProps> = ({
  initialMerchant = '',
  initialAmount = 100,
  existingTransaction = null,
  onClose,
  onSaveReceiptData
}) => {
  const categories = StorageService.getAllExpenseCategories();

  // Initial state derived from existing transaction if editing receipt
  const [merchant, setMerchant] = useState<string>(
    existingTransaction?.merchant || initialMerchant || 'Nesto Hypermarket'
  );
  const [totalAmountStr, setTotalAmountStr] = useState<string>(
    (existingTransaction?.amount || initialAmount || 100).toString()
  );
  const [receiptDate, setReceiptDate] = useState<string>(
    existingTransaction?.date || new Date().toISOString().split('T')[0]
  );
  const [receiptImage, setReceiptImage] = useState<string | null>(
    existingTransaction?.receiptImage || null
  );

  // Line items state
  const [items, setItems] = useState<ReceiptItem[]>(() => {
    if (existingTransaction?.items && existingTransaction.items.length > 0) {
      return existingTransaction.items;
    }
    // Default to the Nesto AED 100 split example (AED 50 Clothing + AED 50 Food & Groceries)
    const preset = SAMPLE_RECEIPT_PRESETS[0];
    return preset.items.map((it, idx) => ({
      id: `init-${Date.now()}-${idx}`,
      name: it.name,
      amount: it.amount,
      category: it.category
    }));
  });

  const [isScanning, setIsScanning] = useState(false);
  const [scanMessage, setScanMessage] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'review' | 'presets' | 'camera'>('review');

  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  // Calculate items sum and reconciliation
  const targetTotal = parseFloat(totalAmountStr) || 0;
  const itemsSum = items.reduce((sum, item) => sum + (Number(item.amount) || 0), 0);
  const roundedSum = Math.round(itemsSum * 100) / 100;
  const roundedTarget = Math.round(targetTotal * 100) / 100;
  const diff = Math.round((roundedTarget - roundedSum) * 100) / 100;
  const isBalanced = Math.abs(diff) < 0.01;

  // Category splits for display
  const categorySplits = calculateCategorySplits(items);

  // Compress image
  const compressImage = (file: File): Promise<string> => {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          const canvas = document.createElement('canvas');
          const maxDim = 900;
          let w = img.width;
          let h = img.height;
          if (w > h) {
            if (w > maxDim) {
              h = Math.round((h * maxDim) / w);
              w = maxDim;
            }
          } else {
            if (h > maxDim) {
              w = Math.round((w * maxDim) / h);
              h = maxDim;
            }
          }
          canvas.width = w;
          canvas.height = h;
          const ctx = canvas.getContext('2d');
          if (ctx) {
            ctx.drawImage(img, 0, 0, w, h);
            resolve(canvas.toDataURL('image/jpeg', 0.72));
          } else {
            resolve(e.target?.result as string);
          }
        };
        img.src = e.target?.result as string;
      };
      reader.readAsDataURL(file);
    });
  };

  // Run OCR on an image
  const processImageOCR = async (file: File) => {
    try {
      setIsScanning(true);
      setScanMessage('Compressing receipt photo for fast AI OCR scanning...');
      const base64 = await compressImage(file);
      setReceiptImage(base64);

      setScanMessage('AI OCR scanning receipt: Extracting merchant, line items & auto-categorizing...');
      const ocrResult = await performReceiptOCR(
        base64,
        file.type || 'image/jpeg',
        merchant,
        targetTotal > 0 ? targetTotal : undefined
      );

      setMerchant(ocrResult.merchant);
      setTotalAmountStr(ocrResult.total.toString());
      setReceiptDate(ocrResult.date);
      setItems(ocrResult.items);
      setActiveTab('review');
    } catch (err) {
      console.error('OCR processing error:', err);
    } finally {
      setIsScanning(false);
      setScanMessage('');
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processImageOCR(e.target.files[0]);
    }
  };

  const handleCameraChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processImageOCR(e.target.files[0]);
    }
  };

  // Apply a sample receipt preset (e.g. Nesto AED 100 with Clothing & Groceries)
  const handleApplyPreset = (preset: SampleReceiptPreset) => {
    setMerchant(preset.merchant);
    setTotalAmountStr(preset.total.toString());
    const newItems: ReceiptItem[] = preset.items.map((it, idx) => ({
      id: `preset-${Date.now()}-${idx}`,
      name: it.name,
      amount: it.amount,
      category: it.category
    }));
    setItems(newItems);
    setActiveTab('review');
  };

  // Edit item properties
  const handleUpdateItemName = (index: number, val: string) => {
    const updated = [...items];
    updated[index].name = val;
    setItems(updated);
  };

  const handleUpdateItemAmount = (index: number, valStr: string) => {
    const parsed = parseFloat(valStr) || 0;
    const updated = [...items];
    updated[index].amount = parsed;
    setItems(updated);
  };

  const handleUpdateItemCategory = (index: number, cat: ExpenseCategory) => {
    const updated = [...items];
    updated[index].category = cat;
    setItems(updated);
  };

  const handleRemoveItem = (index: number) => {
    const updated = items.filter((_, i) => i !== index);
    setItems(updated);
  };

  const handleAddItem = () => {
    const newItem: ReceiptItem = {
      id: `item-${Date.now()}-${items.length}`,
      name: 'New Item',
      amount: Math.max(0, diff),
      category: 'Food & Groceries'
    };
    setItems([...items, newItem]);
  };

  // Auto-reconcile to make sum equal receipt total
  const handleAutoReconcile = () => {
    if (targetTotal <= 0) return;
    const reconciled = reconcileItemSplits(items, targetTotal);
    setItems(reconciled);
  };

  // Save handler
  const handleSave = () => {
    const finalAmount = targetTotal > 0 ? targetTotal : itemsSum;
    if (finalAmount <= 0) return;

    // Reconcile items to ensure exact match with receipt total
    const finalItems = isBalanced ? items : reconcileItemSplits(items, finalAmount);
    const finalSplits = calculateCategorySplits(finalItems);

    onSaveReceiptData({
      merchant: merchant.trim() || 'UAE Merchant',
      amount: finalAmount,
      date: receiptDate,
      items: finalItems,
      categorySplits: finalSplits,
      receiptImage: receiptImage || undefined
    });

    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-2xl my-6 flex flex-col max-h-[92vh]">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-teal-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <ScanLine className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base sm:text-lg font-bold text-white flex items-center gap-2">
                Receipt &amp; Bill OCR Scanner
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  AI Itemizer
                </span>
              </h3>
              <p className="text-xs text-slate-400">
                Extract individual items, allocate categories, and split expenses without VAT.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Input Methods Navigation Bar */}
        <div className="grid grid-cols-3 gap-2 p-1.5 bg-slate-950/70 rounded-2xl my-4 text-xs font-semibold">
          <button
            type="button"
            onClick={() => cameraInputRef.current?.click()}
            className="flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-slate-800/60 hover:bg-slate-800 text-slate-200 transition cursor-pointer border border-slate-700/40"
          >
            <Camera className="w-4 h-4 text-emerald-400" />
            <span>Camera Photo</span>
          </button>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-slate-800/60 hover:bg-slate-800 text-slate-200 transition cursor-pointer border border-slate-700/40"
          >
            <Upload className="w-4 h-4 text-teal-400" />
            <span>Upload Bill / Image</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab(activeTab === 'presets' ? 'review' : 'presets')}
            className={`flex items-center justify-center gap-2 py-2 px-3 rounded-xl transition cursor-pointer border ${
              activeTab === 'presets'
                ? 'bg-emerald-500 text-white border-emerald-400 shadow-md shadow-emerald-950/40'
                : 'bg-slate-800/60 hover:bg-slate-800 text-slate-200 border-slate-700/40'
            }`}
          >
            <Sparkles className="w-4 h-4 text-amber-300" />
            <span>UAE Sample Bills</span>
          </button>
        </div>

        {/* Hidden File / Camera Inputs */}
        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleCameraChange}
          className="hidden"
        />
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileChange}
          className="hidden"
        />

        {/* Scanning Animated Overlay */}
        {isScanning && (
          <div className="p-6 rounded-2xl bg-gradient-to-r from-emerald-950/40 to-teal-950/40 border border-emerald-500/40 mb-4 flex flex-col items-center justify-center text-center space-y-3 relative overflow-hidden">
            <div className="w-12 h-12 rounded-2xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center animate-bounce">
              <ScanLine className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <h4 className="text-sm font-bold text-white flex items-center justify-center gap-2">
                Scanning Receipt with AI Vision
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              </h4>
              <p className="text-xs text-emerald-200 max-w-md">{scanMessage}</p>
            </div>
            {/* Visual Laser Beam */}
            <div className="w-full h-1 bg-gradient-to-r from-transparent via-emerald-400 to-transparent animate-pulse" />
          </div>
        )}

        {/* Preset Selector View */}
        {activeTab === 'presets' && (
          <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 mb-4 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-amber-400" />
                Select UAE Sample Receipt to Test OCR &amp; Split
              </h4>
              <button
                type="button"
                onClick={() => setActiveTab('review')}
                className="text-xs text-slate-400 hover:text-white"
              >
                Back to Review
              </button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {SAMPLE_RECEIPT_PRESETS.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => handleApplyPreset(p)}
                  className="p-3 rounded-xl bg-slate-900 hover:bg-slate-850 border border-slate-800 hover:border-emerald-500/50 text-left transition cursor-pointer group"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-white text-xs group-hover:text-emerald-400">
                      {p.title}
                    </span>
                    <span className="text-xs font-black text-emerald-400 tabular-nums">
                      AED {p.total.toFixed(2)}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    {p.tag}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Scrollable Content Body */}
        <div className="flex-1 overflow-y-auto space-y-4 pr-1">
          {/* Receipt Image Thumbnail & Extracted Top Header */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3.5 rounded-2xl bg-slate-950/80 border border-slate-800">
            {/* Merchant */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                Merchant / Store
              </label>
              <input
                type="text"
                value={merchant}
                onChange={(e) => setMerchant(e.target.value)}
                placeholder="e.g. Nesto Hypermarket"
                className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-3 py-2 text-xs text-white font-medium focus:outline-none focus:border-emerald-500"
              />
            </div>

            {/* Receipt Date */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                Receipt Date
              </label>
              <input
                type="date"
                value={receiptDate}
                onChange={(e) => setReceiptDate(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-3 py-2 text-xs text-white font-medium focus:outline-none focus:border-emerald-500"
              />
            </div>

            {/* Receipt Total */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                Receipt Total (AED)
              </label>
              <div className="relative">
                <span className="absolute left-3 top-2 text-xs font-bold text-emerald-400">
                  AED
                </span>
                <input
                  type="number"
                  step="0.01"
                  value={totalAmountStr}
                  onChange={(e) => setTotalAmountStr(e.target.value)}
                  placeholder="100.00"
                  className="w-full bg-slate-900 border border-slate-700/80 rounded-xl pl-11 pr-3 py-2 text-xs text-white font-bold tabular-nums focus:outline-none focus:border-emerald-500"
                />
              </div>
            </div>
          </div>

          {/* Receipt Photo Preview Bar if attached */}
          {receiptImage && (
            <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <img
                  src={receiptImage}
                  alt="Scanned Receipt"
                  className="w-10 h-10 object-cover rounded-lg border border-slate-700"
                />
                <span className="text-xs text-slate-300 font-medium">
                  📸 Receipt image captured &amp; attached
                </span>
              </div>
              <button
                type="button"
                onClick={() => setReceiptImage(null)}
                className="text-[11px] text-rose-400 hover:text-rose-300 cursor-pointer"
              >
                Remove Photo
              </button>
            </div>
          )}

          {/* Itemized Lines Review & Allocation Table */}
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <Layers className="w-4 h-4 text-emerald-400" />
                Itemized Items &amp; Categories ({items.length})
              </h4>
              <button
                type="button"
                onClick={handleAddItem}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30 text-xs font-bold transition cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                Add Item
              </button>
            </div>

            <div className="space-y-2">
              {items.map((item, idx) => (
                <div
                  key={item.id || idx}
                  className="p-2.5 rounded-2xl bg-slate-950 border border-slate-800/90 flex flex-col sm:flex-row items-stretch sm:items-center gap-2 group hover:border-slate-700 transition"
                >
                  {/* Line Item Description */}
                  <div className="flex-1">
                    <input
                      type="text"
                      value={item.name}
                      onChange={(e) => handleUpdateItemName(idx, e.target.value)}
                      placeholder="Item name (e.g. Casual T-Shirt)"
                      className="w-full bg-slate-900 border border-slate-700/60 rounded-xl px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                    />
                  </div>

                  {/* Category Dropdown */}
                  <div className="w-full sm:w-44">
                    <select
                      value={item.category}
                      onChange={(e) => handleUpdateItemCategory(idx, e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700/60 rounded-xl px-2.5 py-1.5 text-xs text-slate-200 font-semibold focus:outline-none focus:border-emerald-500 cursor-pointer"
                    >
                      {categories.map((c) => (
                        <option key={c} value={c} className="bg-slate-900 text-white">
                          {c}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Amount */}
                  <div className="w-full sm:w-28 relative">
                    <span className="absolute left-2.5 top-1.5 text-[11px] font-bold text-slate-400">
                      AED
                    </span>
                    <input
                      type="number"
                      step="0.01"
                      value={item.amount || ''}
                      onChange={(e) => handleUpdateItemAmount(idx, e.target.value)}
                      placeholder="0.00"
                      className="w-full bg-slate-900 border border-slate-700/60 rounded-xl pl-10 pr-2 py-1.5 text-xs text-white font-black tabular-nums focus:outline-none focus:border-emerald-500"
                    />
                  </div>

                  {/* Delete Button */}
                  <button
                    type="button"
                    onClick={() => handleRemoveItem(idx)}
                    disabled={items.length <= 1}
                    className="p-1.5 rounded-xl text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed self-end sm:self-center"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Reconciliation Balance Checker */}
          <div
            className={`p-3.5 rounded-2xl border flex flex-col sm:flex-row items-center justify-between gap-3 text-xs ${
              isBalanced
                ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-200'
                : 'bg-amber-950/30 border-amber-500/40 text-amber-200'
            }`}
          >
            <div className="flex items-center gap-2.5">
              {isBalanced ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
              ) : (
                <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
              )}
              <div>
                <div className="font-bold">
                  {isBalanced
                    ? `Itemized amounts match receipt total exactly (AED ${roundedTarget.toFixed(2)})`
                    : `Discrepancy: Items sum (AED ${roundedSum.toFixed(2)}) ≠ Total (AED ${roundedTarget.toFixed(2)})`}
                </div>
                <div className="text-[11px] opacity-80">
                  {isBalanced
                    ? '100% balanced across categories with zero VAT calculation.'
                    : `Difference of AED ${Math.abs(diff).toFixed(2)}. Click Reconcile to balance to receipt total.`}
                </div>
              </div>
            </div>

            {!isBalanced && (
              <button
                type="button"
                onClick={handleAutoReconcile}
                className="px-3.5 py-1.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-black text-xs transition cursor-pointer whitespace-nowrap shadow"
              >
                Auto-Reconcile Balance
              </button>
            )}
          </div>

          {/* Category Split Distribution Badges */}
          <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 space-y-2">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
              <span>Category Allocation Breakdown</span>
              <span className="text-[11px] text-emerald-400 font-semibold">
                {categorySplits.length} split categories
              </span>
            </div>

            <div className="flex flex-wrap gap-2">
              {categorySplits.map((split) => {
                const percent = targetTotal > 0 ? (split.amount / targetTotal) * 100 : 0;
                return (
                  <div
                    key={split.category}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700/60 text-xs font-semibold"
                  >
                    <span className="text-white">{split.category}:</span>
                    <span className="font-black text-emerald-400 tabular-nums">
                      AED {split.amount.toFixed(2)}
                    </span>
                    <span className="text-[10px] text-slate-400">
                      ({percent.toFixed(0)}%)
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Modal Footer Actions */}
        <div className="pt-4 mt-3 border-t border-slate-800 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-750 text-slate-300 font-semibold text-xs transition cursor-pointer"
          >
            Cancel
          </button>

          <button
            type="button"
            onClick={handleSave}
            disabled={targetTotal <= 0 || items.length === 0}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-black text-xs transition cursor-pointer shadow-lg shadow-emerald-950/40 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <span>Save &amp; Itemize Transaction</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
