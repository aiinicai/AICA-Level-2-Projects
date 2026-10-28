import React, { useState } from 'react';
import { X, Plus, Trash2, AlertCircle, CheckCircle2, FileSpreadsheet, ShieldAlert } from 'lucide-react';
import { getDb, updateDb, addAuditLog } from '../../core/storage';
import { getActiveUser } from '../../core/auth';
import { getNextSequenceNumber, peekNextSequenceNumber } from '../../core/sequences';
import { APInvoice, APInvoiceLine, TaxCode } from '../../core/types';
import { TAX_CODES, getTaxRate } from '../../data/taxCodes';
import { BUSINESS_UNITS } from '../../data/businessUnits';
import { DEPARTMENTS } from '../../data/chartOfAccounts';
import { round2, addMoney, formatAED } from '../../core/currency';
import { checkDatePeriodStatus } from '../../core/periods';
import { DEMO_TODAY } from '../../core/dates';

interface CreateInvoiceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (invoice: APInvoice) => void;
}

export const CreateInvoiceModal: React.FC<CreateInvoiceModalProps> = ({
  isOpen,
  onClose,
  onCreated,
}) => {
  const db = getDb();
  const currentUser = getActiveUser();

  const [businessUnit, setBusinessUnit] = useState('H01');
  const [supplierId, setSupplierId] = useState(db.suppliers[0]?.id || '');
  const [supplierSite, setSupplierSite] = useState('HQ');
  const [supplierInvoiceNumber, setSupplierInvoiceNumber] = useState('');
  const [invoiceType, setInvoiceType] = useState<'Standard' | 'Credit Memo' | 'Prepayment'>('Standard');
  const [invoiceDate, setInvoiceDate] = useState(DEMO_TODAY);
  const [glDate, setGlDate] = useState(DEMO_TODAY);
  const [dueDate, setDueDate] = useState('2026-11-18');
  const [description, setDescription] = useState('');
  const [selectedPO, setSelectedPO] = useState('');
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  // Line items
  const [lines, setLines] = useState<APInvoiceLine[]>([
    {
      lineNumber: 1,
      poNumber: 'PO-2026-000001',
      description: 'Pharmaceuticals & IV Infusions replenishment',
      quantity: 1,
      unitPrice: 24500,
      lineAmount: 24500,
      taxCode: 'STANDARD_5',
      taxAmount: 1225,
      distributionAccount: '2010', // GRNI
      department: 'Pharmacy',
      isCapital: false,
    },
  ]);

  if (!isOpen) return null;

  const currentSupplier = db.suppliers.find((s) => s.id === supplierId);
  const nextNumberPreview = peekNextSequenceNumber('PINV', 2026);

  // Quick PO Line import
  const handleSelectPO = (poNum: string) => {
    setSelectedPO(poNum);
    if (!poNum) return;
    const po = db.purchaseOrders.find((p) => p.number === poNum);
    if (po && po.lines.length > 0) {
      const firstLine = po.lines[0];
      setBusinessUnit(po.businessUnit);
      setSupplierId(po.supplierId);
      setDescription(`PO Match: ${po.number} - ${firstLine.description}`);
      setLines([
        {
          lineNumber: 1,
          poNumber: po.number,
          poLineNumber: firstLine.lineNumber,
          itemCode: firstLine.itemCode,
          description: firstLine.description,
          quantity: firstLine.quantity,
          unitPrice: firstLine.unitPrice,
          lineAmount: firstLine.lineAmount,
          taxCode: firstLine.taxCode,
          taxAmount: round2(firstLine.lineAmount * getTaxRate(firstLine.taxCode)),
          distributionAccount: firstLine.isCapital ? '1610' : firstLine.account || '2010',
          department: firstLine.department,
          isCapital: firstLine.isCapital,
          assetCategory: firstLine.assetCategory,
        },
      ]);
    }
  };

  const handleAddLine = () => {
    setLines([
      ...lines,
      {
        lineNumber: lines.length + 1,
        poNumber: selectedPO || undefined,
        description: 'Hospital operating goods/services line',
        quantity: 1,
        unitPrice: 0,
        lineAmount: 0,
        taxCode: 'STANDARD_5',
        taxAmount: 0,
        distributionAccount: '2010',
        department: 'Clinical',
        isCapital: false,
      },
    ]);
  };

  const handleRemoveLine = (idx: number) => {
    if (lines.length <= 1) {
      setErrorBanner('Invoice must have at least one line.');
      return;
    }
    const updated = [...lines];
    updated.splice(idx, 1);
    setLines(updated.map((l, i) => ({ ...l, lineNumber: i + 1 })));
  };

  const updateLine = (idx: number, field: keyof APInvoiceLine, val: any) => {
    const updated = [...lines];
    updated[idx] = { ...updated[idx], [field]: val };

    if (field === 'quantity' || field === 'unitPrice') {
      const q = parseFloat(String(updated[idx].quantity)) || 0;
      const p = parseFloat(String(updated[idx].unitPrice)) || 0;
      const amt = round2(q * p);
      updated[idx].lineAmount = amt;
      const taxRate = getTaxRate(updated[idx].taxCode);
      updated[idx].taxAmount = round2(amt * taxRate);
    } else if (field === 'taxCode') {
      const taxRate = getTaxRate(val as TaxCode);
      updated[idx].taxAmount = round2(updated[idx].lineAmount * taxRate);
    } else if (field === 'isCapital') {
      if (val === true) {
        updated[idx].distributionAccount = '1610'; // Asset Clearing
        updated[idx].assetCategory = updated[idx].assetCategory || 'Medical Equipment';
      } else {
        updated[idx].distributionAccount = '2010'; // GRNI
      }
    }

    setLines(updated);
    if (errorBanner) setErrorBanner(null);
  };

  // Totals
  let subtotal = 0;
  let totalTax = 0;
  lines.forEach((l) => {
    subtotal = addMoney(subtotal, l.lineAmount);
    totalTax = addMoney(totalTax, l.taxAmount);
  });
  const totalAmount = addMoney(subtotal, totalTax);

  const handleSave = (statusToSet: 'Draft' | 'Pending Approval') => {
    setErrorBanner(null);

    // Period check
    const periodCheck = checkDatePeriodStatus(glDate);
    if (!periodCheck.isOpen) {
      setErrorBanner(periodCheck.error || `GL Date ${glDate} is in a closed period.`);
      return;
    }

    if (!supplierInvoiceNumber.trim()) {
      setErrorBanner('Supplier Invoice Number is required.');
      return;
    }

    // Duplicate invoice detection (same supplier + same supplierInvoiceNumber)
    const duplicate = db.apInvoices.find(
      (inv) =>
        inv.supplierId === supplierId &&
        inv.supplierInvoiceNumber.toLowerCase() === supplierInvoiceNumber.trim().toLowerCase()
    );
    if (duplicate) {
      setErrorBanner(
        `Duplicate Invoice Block: Supplier already has an invoice registered with number '${supplierInvoiceNumber}'.`
      );
      return;
    }

    if (subtotal <= 0) {
      setErrorBanner('Invoice lines total amount must be greater than zero.');
      return;
    }

    const assignedNumber = getNextSequenceNumber('PINV', 2026);
    const invoice: APInvoice = {
      id: `AP-INV-${Date.now()}`,
      number: assignedNumber,
      businessUnit,
      invoiceType,
      supplierId,
      supplierName: currentSupplier?.name || 'Supplier',
      supplierSite,
      supplierInvoiceNumber: supplierInvoiceNumber.trim(),
      invoiceDate,
      glDate,
      dueDate,
      currency: 'AED',
      description: description || `Supplier Invoice from ${currentSupplier?.name}`,
      lines,
      subtotal,
      taxAmount: totalTax,
      totalAmount,
      paidAmount: 0,
      status: statusToSet,
      holds: [],
      createdBy: currentUser.userId,
      createdAt: new Date().toISOString(),
    };

    updateDb((state) => {
      state.apInvoices.unshift(invoice);
    });

    addAuditLog({
      entityType: 'APInvoice',
      entityId: invoice.id,
      action: statusToSet === 'Pending Approval' ? 'SUBMIT' : 'CREATE',
      userId: currentUser.userId,
      userName: currentUser.name,
      comments: `Created AP invoice ${invoice.number} (${statusToSet})`,
    });

    onCreated(invoice);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs" onClick={onClose} />

      <div className="relative bg-white rounded-xl shadow-2xl border border-gray-200 w-full max-w-5xl max-h-[92vh] flex flex-col z-10 animate-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="bg-[#3F1D5C] text-white px-6 py-4 rounded-t-xl flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <FileSpreadsheet className="w-5 h-5 text-amber-300" />
            <div>
              <h2 className="font-bold text-base">Create Payables Invoice</h2>
              <p className="text-xs text-plum-200">
                Assigned Sequence: <strong className="font-mono text-amber-300">{nextNumberPreview}</strong> | Currency: AED
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded-full hover:bg-[#5B2C83] text-gray-200">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {errorBanner && (
            <div className="mb-4 p-3 bg-rose-50 border border-rose-300 text-rose-800 rounded-lg text-xs flex items-start space-x-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{errorBanner}</span>
            </div>
          )}

          {/* PO Matching Shortcut */}
          <div className="p-3 bg-plum-50/70 border border-plum-200 rounded-lg mb-5 flex items-center justify-between gap-4 text-xs">
            <span className="font-semibold text-[#5B2C83]">
              3-Way Match Shortcut: Pull from Approved Purchase Order:
            </span>
            <select
              value={selectedPO}
              onChange={(e) => handleSelectPO(e.target.value)}
              className="bg-white border border-gray-300 rounded px-3 py-1 font-medium text-gray-800 focus:ring-1 focus:ring-[#5B2C83]"
            >
              <option value="">Select PO to match...</option>
              {db.purchaseOrders.map((po) => (
                <option key={po.id} value={po.number}>
                  {po.number} &bull; {po.supplierName} (AED {formatAED(po.totalAmount)})
                </option>
              ))}
            </select>
          </div>

          {/* Header Fields */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-5 p-4 bg-gray-50 rounded-lg border border-gray-200 text-xs">
            <div>
              <label className="block font-semibold text-gray-700 mb-1">
                Business Unit <span className="text-rose-500">*</span>
              </label>
              <select
                value={businessUnit}
                onChange={(e) => setBusinessUnit(e.target.value)}
                className="w-full p-2 bg-white border border-gray-300 rounded font-medium focus:ring-1 focus:ring-[#5B2C83]"
              >
                {BUSINESS_UNITS.map((b) => (
                  <option key={b.code} value={b.code}>
                    {b.code} - {b.name.replace('Meridian ', '')}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block font-semibold text-gray-700 mb-1">
                Supplier <span className="text-rose-500">*</span>
              </label>
              <select
                value={supplierId}
                onChange={(e) => setSupplierId(e.target.value)}
                className="w-full p-2 bg-white border border-gray-300 rounded font-medium focus:ring-1 focus:ring-[#5B2C83]"
              >
                {db.suppliers.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.category})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block font-semibold text-gray-700 mb-1">
                Supplier Invoice No. <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                placeholder="e.g. INV-90214"
                value={supplierInvoiceNumber}
                onChange={(e) => setSupplierInvoiceNumber(e.target.value)}
                className="w-full p-2 bg-white border border-gray-300 rounded font-medium focus:ring-1 focus:ring-[#5B2C83]"
                required
              />
            </div>

            <div>
              <label className="block font-semibold text-gray-700 mb-1">Invoice Type</label>
              <select
                value={invoiceType}
                onChange={(e) => setInvoiceType(e.target.value as any)}
                className="w-full p-2 bg-white border border-gray-300 rounded font-medium focus:ring-1 focus:ring-[#5B2C83]"
              >
                <option value="Standard">Standard Invoice</option>
                <option value="Credit Memo">Credit Memo</option>
                <option value="Prepayment">Prepayment / Advance</option>
              </select>
            </div>

            <div>
              <label className="block font-semibold text-gray-700 mb-1">Invoice Date</label>
              <input
                type="date"
                value={invoiceDate}
                onChange={(e) => setInvoiceDate(e.target.value)}
                className="w-full p-2 bg-white border border-gray-300 rounded font-medium focus:ring-1 focus:ring-[#5B2C83]"
              />
            </div>

            <div>
              <label className="block font-semibold text-gray-700 mb-1">GL Date (Posting)</label>
              <input
                type="date"
                value={glDate}
                onChange={(e) => setGlDate(e.target.value)}
                className="w-full p-2 bg-white border border-gray-300 rounded font-medium focus:ring-1 focus:ring-[#5B2C83]"
              />
            </div>

            <div>
              <label className="block font-semibold text-gray-700 mb-1">Due Date</label>
              <input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="w-full p-2 bg-white border border-gray-300 rounded font-medium focus:ring-1 focus:ring-[#5B2C83]"
              />
            </div>

            <div>
              <label className="block font-semibold text-gray-700 mb-1">Description</label>
              <input
                type="text"
                placeholder="Invoice header description..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full p-2 bg-white border border-gray-300 rounded font-medium focus:ring-1 focus:ring-[#5B2C83]"
              />
            </div>
          </div>

          {/* Lines Table */}
          <div className="border border-gray-200 rounded-lg overflow-hidden mb-4">
            <table className="w-full text-xs text-left">
              <thead className="bg-[#EDE4F5] text-[#3F1D5C] font-semibold uppercase tracking-wider border-b border-plum-200">
                <tr>
                  <th className="py-2.5 px-3 w-8 text-center">#</th>
                  <th className="py-2.5 px-3">Description</th>
                  <th className="py-2.5 px-3 w-16 text-center">Qty</th>
                  <th className="py-2.5 px-3 w-24 text-right">Unit Price</th>
                  <th className="py-2.5 px-3 w-28 text-right">Line Amount</th>
                  <th className="py-2.5 px-3 w-32">Tax Code</th>
                  <th className="py-2.5 px-3 w-28">Dist. Account</th>
                  <th className="py-2.5 px-3 w-28 text-center">Capital Item?</th>
                  <th className="py-2.5 px-2 w-8 text-center"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {lines.map((l, idx) => (
                  <tr key={idx} className="hover:bg-plum-50/20">
                    <td className="py-2 px-3 text-center text-gray-400 font-semibold">{idx + 1}</td>
                    <td className="py-2 px-2">
                      <input
                        type="text"
                        value={l.description}
                        onChange={(e) => updateLine(idx, 'description', e.target.value)}
                        className="w-full p-1.5 border border-gray-300 rounded text-xs"
                      />
                    </td>
                    <td className="py-2 px-2">
                      <input
                        type="number"
                        min="1"
                        value={l.quantity}
                        onChange={(e) => updateLine(idx, 'quantity', e.target.value)}
                        className="w-full p-1.5 border border-gray-300 rounded text-xs text-center"
                      />
                    </td>
                    <td className="py-2 px-2">
                      <input
                        type="number"
                        step="0.01"
                        value={l.unitPrice}
                        onChange={(e) => updateLine(idx, 'unitPrice', e.target.value)}
                        className="w-full p-1.5 border border-gray-300 rounded text-xs text-right font-mono"
                      />
                    </td>
                    <td className="py-2 px-2 text-right font-mono font-medium text-gray-900">
                      {formatAED(l.lineAmount)}
                    </td>
                    <td className="py-2 px-2">
                      <select
                        value={l.taxCode}
                        onChange={(e) => updateLine(idx, 'taxCode', e.target.value)}
                        className="w-full p-1.5 border border-gray-300 rounded text-xs"
                      >
                        <option value="STANDARD_5">VAT 5% Standard</option>
                        <option value="ZERO_0">VAT 0% Zero</option>
                        <option value="EXEMPT">Exempt</option>
                      </select>
                    </td>
                    <td className="py-2 px-2">
                      <input
                        type="text"
                        value={l.distributionAccount}
                        onChange={(e) => updateLine(idx, 'distributionAccount', e.target.value)}
                        className="w-full p-1.5 border border-gray-300 rounded text-xs font-mono"
                        placeholder="2010"
                      />
                    </td>
                    <td className="py-2 px-2 text-center">
                      <input
                        type="checkbox"
                        checked={l.isCapital || false}
                        onChange={(e) => updateLine(idx, 'isCapital', e.target.checked)}
                        className="rounded text-[#5B2C83] focus:ring-[#5B2C83]"
                        title="Flag as Capital Asset (Routes to Fixed Assets additions queue upon approval)"
                      />
                    </td>
                    <td className="py-2 px-2 text-center">
                      <button
                        type="button"
                        onClick={() => handleRemoveLine(idx)}
                        className="p-1 text-gray-400 hover:text-rose-600 rounded"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between mb-4">
            <button
              type="button"
              onClick={handleAddLine}
              className="px-3 py-1.5 rounded bg-gray-100 hover:bg-gray-200 text-gray-800 text-xs font-semibold flex items-center space-x-1"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Invoice Line</span>
            </button>

            {/* Totals Summary */}
            <div className="bg-plum-50/60 border border-plum-200 rounded-lg p-3 text-xs w-72 space-y-1">
              <div className="flex justify-between text-gray-600">
                <span>Subtotal:</span>
                <span className="font-mono">{formatAED(subtotal)}</span>
              </div>
              <div className="flex justify-between text-gray-600">
                <span>VAT (5% Recoverable):</span>
                <span className="font-mono">{formatAED(totalTax)}</span>
              </div>
              <div className="flex justify-between font-bold text-gray-900 border-t border-plum-200 pt-1 text-sm">
                <span>Total Invoice (AED):</span>
                <span className="font-mono text-[#5B2C83]">{formatAED(totalAmount)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="bg-gray-50 px-6 py-3 rounded-b-xl border-t border-gray-200 flex items-center justify-between">
          <div className="text-[11px] text-gray-500">
            Maker: <strong>{currentUser.name}</strong> ({currentUser.role})
          </div>
          <div className="flex space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-lg text-xs font-semibold text-gray-700 hover:bg-gray-100"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => handleSave('Draft')}
              className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-800 rounded-lg text-xs font-semibold"
            >
              Save as Draft
            </button>
            <button
              type="button"
              onClick={() => handleSave('Pending Approval')}
              className="px-5 py-2 bg-[#5B2C83] hover:bg-[#3F1D5C] text-white rounded-lg text-xs font-semibold shadow-xs"
            >
              Submit for Approval &rarr;
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
