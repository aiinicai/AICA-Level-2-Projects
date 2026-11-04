import React, { useState, useEffect } from 'react';
import { Purchase, MetalType, BullionForm } from '../../types';
import { X, AlertTriangle, Calculator } from 'lucide-react';
import { formatINR, getTodayKolkata } from '../../utils/formatters';

interface AddEditPurchaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (purchase: Purchase) => void;
  existingPurchases: Purchase[];
  editingPurchase?: Purchase | null;
}

export const AddEditPurchaseModal: React.FC<AddEditPurchaseModalProps> = ({
  isOpen,
  onClose,
  onSave,
  existingPurchases,
  editingPurchase,
}) => {
  const [holdingId, setHoldingId] = useState('');
  const [purchaseDate, setPurchaseDate] = useState(getTodayKolkata());
  const [seller, setSeller] = useState('');
  const [invoiceNumber, setInvoiceNumber] = useState('');
  const [metal, setMetal] = useState<MetalType>('GOLD');
  const [form, setForm] = useState<BullionForm>('COIN');
  const [purity, setPurity] = useState<number>(999);
  const [weightGrams, setWeightGrams] = useState<string>('10');
  const [purchaseRate, setPurchaseRate] = useState<string>('');
  const [taxesPaid, setTaxesPaid] = useState<string>('0');
  const [otherCharges, setOtherCharges] = useState<string>('0');
  const [notes, setNotes] = useState<string>('');

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [duplicateWarning, setDuplicateWarning] = useState<string | null>(null);

  // Initialize or reset form
  useEffect(() => {
    if (editingPurchase) {
      setHoldingId(editingPurchase.id);
      setPurchaseDate(editingPurchase.purchaseDate);
      setSeller(editingPurchase.seller);
      setInvoiceNumber(editingPurchase.invoiceNumber);
      setMetal(editingPurchase.metal);
      setForm(editingPurchase.form);
      setPurity(editingPurchase.purity);
      setWeightGrams(editingPurchase.weightGrams.toString());
      setPurchaseRate(editingPurchase.purchaseRate.toString());
      setTaxesPaid(editingPurchase.taxesPaid.toString());
      setOtherCharges(editingPurchase.otherCharges.toString());
      setNotes(editingPurchase.notes || '');
    } else {
      const randomSuffix = Math.floor(100 + Math.random() * 900);
      const year = new Date().getFullYear();
      setHoldingId(`HLD-${year}-${randomSuffix}`);
      setPurchaseDate(getTodayKolkata());
      setSeller('');
      setInvoiceNumber('');
      setMetal('GOLD');
      setForm('COIN');
      setPurity(999);
      setWeightGrams('10');
      setPurchaseRate('');
      setTaxesPaid('0');
      setOtherCharges('0');
      setNotes('');
    }
    setErrors({});
    setDuplicateWarning(null);
  }, [editingPurchase, isOpen]);

  // Handle purity options based on metal
  const handleMetalChange = (newMetal: MetalType) => {
    setMetal(newMetal);
    if (newMetal === 'GOLD') {
      setPurity(999);
    } else {
      setPurity(999);
    }
  };

  // Calculations
  const weightNum = parseFloat(weightGrams) || 0;
  const rateNum = parseFloat(purchaseRate) || 0;
  const taxesNum = parseFloat(taxesPaid) || 0;
  const chargesNum = parseFloat(otherCharges) || 0;

  const bullionValue = Math.round(weightNum * rateNum * 100) / 100;
  const investedAmount = Math.round((bullionValue + taxesNum + chargesNum) * 100) / 100;

  // Real-time duplicate check
  useEffect(() => {
    if (!purchaseDate || !seller || !invoiceNumber || weightNum <= 0) {
      setDuplicateWarning(null);
      return;
    }

    const isDup = existingPurchases.some(
      (p) =>
        (!editingPurchase || p.id !== editingPurchase.id) &&
        !p.deleted &&
        p.purchaseDate === purchaseDate &&
        p.seller.trim().toLowerCase() === seller.trim().toLowerCase() &&
        p.invoiceNumber.trim() === invoiceNumber.trim() &&
        p.metal === metal &&
        p.form === form &&
        Math.abs(p.weightGrams - weightNum) < 0.0001
    );

    if (isDup) {
      setDuplicateWarning(
        'Warning: A holding with the identical Date, Seller, Invoice #, Metal, Form, and Weight already exists in the ledger.'
      );
    } else {
      setDuplicateWarning(null);
    }
  }, [purchaseDate, seller, invoiceNumber, metal, form, weightNum, existingPurchases, editingPurchase]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const newErrors: Record<string, string> = {};

    if (!holdingId.trim()) newErrors.holdingId = 'Holding ID is required.';
    if (!purchaseDate) newErrors.purchaseDate = 'Valid purchase date is required.';
    if (!seller.trim()) newErrors.seller = 'Jeweller / Seller name is required.';
    if (!invoiceNumber.trim()) newErrors.invoiceNumber = 'Invoice number is required.';
    if (weightNum <= 0) newErrors.weightGrams = 'Weight must be greater than 0.';
    if (rateNum <= 0) newErrors.purchaseRate = 'Purchase rate must be greater than 0.';
    if (taxesNum < 0) newErrors.taxesPaid = 'Taxes paid cannot be negative.';
    if (chargesNum < 0) newErrors.otherCharges = 'Charges cannot be negative.';

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    const record: Purchase = {
      id: holdingId.trim(),
      purchaseDate,
      seller: seller.trim(),
      invoiceNumber: invoiceNumber.trim(), // string, preserving leading zeros
      metal,
      form,
      purity,
      weightGrams: weightNum,
      purchaseRate: rateNum,
      bullionValue,
      taxesPaid: taxesNum,
      otherCharges: chargesNum,
      investedAmount,
      notes: notes.trim() || undefined,
      createdAt: editingPurchase ? editingPurchase.createdAt : new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      deleted: false,
    };

    onSave(record);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-stone-900/60 backdrop-blur-2xs flex items-center justify-center p-3 sm:p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full border border-stone-200 overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-stone-200 bg-[#FAF7F2]">
          <div>
            <h2 className="text-base font-bold text-stone-900">
              {editingPurchase ? 'Edit Holding / Purchase Lot' : 'Record New Bullion Purchase'}
            </h2>
            <p className="text-xs text-stone-500">
              Track physical Gold or Silver with exact invoice details and taxes
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-stone-400 hover:text-stone-700 p-1 rounded-md"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4 max-h-[80vh] overflow-y-auto">
          {duplicateWarning && (
            <div className="bg-amber-50 border border-amber-300 rounded-lg p-3 text-xs text-amber-900 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">Possible Duplicate Detected:</span>
                <p className="mt-0.5">{duplicateWarning}</p>
                <p className="mt-1 text-[11px] text-amber-700">
                  Multiple items on the same invoice are allowed; confirm if this is an intentional second lot.
                </p>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
            {/* Holding ID */}
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Holding ID *
              </label>
              <input
                type="text"
                value={holdingId}
                onChange={(e) => setHoldingId(e.target.value)}
                className="w-full text-xs px-3 py-1.5 border border-stone-300 rounded-md focus:ring-1 focus:ring-[#B88B2A]"
                placeholder="e.g. HLD-2026-001"
              />
              {errors.holdingId && (
                <span className="text-[10px] text-rose-600">{errors.holdingId}</span>
              )}
            </div>

            {/* Purchase Date */}
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Purchase Date *
              </label>
              <input
                type="date"
                value={purchaseDate}
                onChange={(e) => setPurchaseDate(e.target.value)}
                className="w-full text-xs px-3 py-1.5 border border-stone-300 rounded-md focus:ring-1 focus:ring-[#B88B2A]"
              />
              {errors.purchaseDate && (
                <span className="text-[10px] text-rose-600">{errors.purchaseDate}</span>
              )}
            </div>

            {/* Invoice Number */}
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Invoice Number *
              </label>
              <input
                type="text"
                value={invoiceNumber}
                onChange={(e) => setInvoiceNumber(e.target.value)}
                className="w-full text-xs px-3 py-1.5 border border-stone-300 rounded-md focus:ring-1 focus:ring-[#B88B2A]"
                placeholder="Preserves leading 0s, e.g. 004921"
              />
              {errors.invoiceNumber && (
                <span className="text-[10px] text-rose-600">{errors.invoiceNumber}</span>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            {/* Seller */}
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Jeweller / Bullion Seller *
              </label>
              <input
                type="text"
                value={seller}
                onChange={(e) => setSeller(e.target.value)}
                className="w-full text-xs px-3 py-1.5 border border-stone-300 rounded-md focus:ring-1 focus:ring-[#B88B2A]"
                placeholder="e.g. Tanishq, MMTC-PAMP, Kundan, Malabar"
              />
              {errors.seller && (
                <span className="text-[10px] text-rose-600">{errors.seller}</span>
              )}
            </div>

            {/* Metal & Form */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-semibold text-stone-700 mb-1">
                  Metal *
                </label>
                <select
                  value={metal}
                  onChange={(e) => handleMetalChange(e.target.value as MetalType)}
                  className="w-full text-xs px-2.5 py-1.5 border border-stone-300 rounded-md focus:ring-1 focus:ring-[#B88B2A] bg-white"
                >
                  <option value="GOLD">Gold</option>
                  <option value="SILVER">Silver</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-stone-700 mb-1">
                  Form *
                </label>
                <select
                  value={form}
                  onChange={(e) => setForm(e.target.value as BullionForm)}
                  className="w-full text-xs px-2.5 py-1.5 border border-stone-300 rounded-md focus:ring-1 focus:ring-[#B88B2A] bg-white"
                >
                  <option value="VEDHANI">Vedhani</option>
                  <option value="COIN">Coin</option>
                  <option value="BAR">Bar</option>
                </select>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
            {/* Fineness / Purity */}
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Purity (Fineness) *
              </label>
              <select
                value={purity}
                onChange={(e) => setPurity(parseInt(e.target.value, 10))}
                className="w-full text-xs px-2.5 py-1.5 border border-stone-300 rounded-md focus:ring-1 focus:ring-[#B88B2A] bg-white"
              >
                {metal === 'GOLD' ? (
                  <>
                    <option value={999}>999 (24 Karat Standard)</option>
                    <option value={995}>995 (24 Karat Pure)</option>
                    <option value={916}>916 (22 Karat Standard)</option>
                    <option value={750}>750 (18 Karat)</option>
                  </>
                ) : (
                  <>
                    <option value={999}>999 (Pure Silver Standard)</option>
                    <option value={925}>925 (Sterling Silver)</option>
                  </>
                )}
              </select>
            </div>

            {/* Weight in Grams */}
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Weight in Grams *
              </label>
              <input
                type="number"
                step="0.001"
                min="0.001"
                value={weightGrams}
                onChange={(e) => setWeightGrams(e.target.value)}
                className="w-full text-xs px-3 py-1.5 border border-stone-300 rounded-md focus:ring-1 focus:ring-[#B88B2A]"
                placeholder="e.g. 10.000"
              />
              {errors.weightGrams && (
                <span className="text-[10px] text-rose-600">{errors.weightGrams}</span>
              )}
            </div>

            {/* Purchase Rate ₹/gram */}
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Purchase Rate (₹/g) *
              </label>
              <input
                type="number"
                step="0.01"
                min="1"
                value={purchaseRate}
                onChange={(e) => setPurchaseRate(e.target.value)}
                className="w-full text-xs px-3 py-1.5 border border-stone-300 rounded-md focus:ring-1 focus:ring-[#B88B2A]"
                placeholder="e.g. 7250"
              />
              {errors.purchaseRate && (
                <span className="text-[10px] text-rose-600">{errors.purchaseRate}</span>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            {/* Taxes Paid (₹) */}
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                GST / Taxes Paid (₹) *
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={taxesPaid}
                onChange={(e) => setTaxesPaid(e.target.value)}
                className="w-full text-xs px-3 py-1.5 border border-stone-300 rounded-md focus:ring-1 focus:ring-[#B88B2A]"
                placeholder="Enter exact rupee amount from invoice"
              />
              <span className="text-[10px] text-stone-500">
                Exact invoice tax amount (e.g. 3% GST)
              </span>
              {errors.taxesPaid && (
                <span className="text-[10px] text-rose-600 block">{errors.taxesPaid}</span>
              )}
            </div>

            {/* Other Charges (₹) */}
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Making / Other Charges (₹)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={otherCharges}
                onChange={(e) => setOtherCharges(e.target.value)}
                className="w-full text-xs px-3 py-1.5 border border-stone-300 rounded-md focus:ring-1 focus:ring-[#B88B2A]"
                placeholder="0.00"
              />
              <span className="text-[10px] text-stone-500">
                Making, hallmarking, or delivery charges
              </span>
              {errors.otherCharges && (
                <span className="text-[10px] text-rose-600 block">{errors.otherCharges}</span>
              )}
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-xs font-semibold text-stone-700 mb-1">
              Notes / Serial Number (Optional)
            </label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full text-xs px-3 py-1.5 border border-stone-300 rounded-md focus:ring-1 focus:ring-[#B88B2A]"
              placeholder="e.g. Assay cert #AA-99812, stored in Safe Deposit Locker #4"
            />
          </div>

          {/* Live Calculated Cost Summary */}
          <div className="bg-[#FAF7F2] p-3.5 rounded-lg border border-[#E7E2DA] space-y-1.5">
            <div className="flex items-center gap-1.5 text-xs font-bold text-stone-900">
              <Calculator className="w-3.5 h-3.5 text-[#B88B2A]" />
              <span>Investment Breakdown</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
              <div>
                <span className="text-stone-500 text-[11px] block">Bullion Value:</span>
                <span className="font-medium text-stone-800">
                  {formatINR(bullionValue)}
                </span>
                <span className="text-[10px] text-stone-400 block">
                  ({weightNum}g × ₹{rateNum}/g)
                </span>
              </div>
              <div>
                <span className="text-stone-500 text-[11px] block">Taxes & Charges:</span>
                <span className="font-medium text-stone-800">
                  {formatINR(taxesNum + chargesNum)}
                </span>
              </div>
              <div className="col-span-2 sm:col-span-1">
                <span className="text-stone-500 text-[11px] block">Total Invested Cost:</span>
                <span className="font-bold text-[#B88B2A] text-sm">
                  {formatINR(investedAmount)}
                </span>
              </div>
            </div>
          </div>

          {/* Modal Actions */}
          <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-stone-200">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-stone-600 hover:text-stone-900 bg-stone-100 hover:bg-stone-200 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 text-xs font-semibold text-white bg-[#B88B2A] hover:bg-[#8E6B1D] rounded-lg shadow-2xs transition-colors"
            >
              {editingPurchase ? 'Update Purchase' : 'Save to Ledger'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
