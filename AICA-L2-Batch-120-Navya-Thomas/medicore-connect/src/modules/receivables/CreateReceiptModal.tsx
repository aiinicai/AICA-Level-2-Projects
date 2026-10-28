import React, { useState } from 'react';
import { X, CreditCard, CheckCircle2, AlertCircle } from 'lucide-react';
import { getDb, updateDb, addAuditLog } from '../../core/storage';
import { getActiveUser } from '../../core/auth';
import { getNextSequenceNumber } from '../../core/sequences';
import { ARTransaction, ARReceipt } from '../../core/types';
import { buildARReceiptAccounting, postToGL } from '../../core/postingEngine';
import { round2, subMoney, addMoney, formatAED } from '../../core/currency';
import { DEMO_TODAY } from '../../core/dates';

interface CreateReceiptModalProps {
  isOpen: boolean;
  onClose: () => void;
  transaction: ARTransaction;
  onCreated: (receipt: ARReceipt) => void;
}

export const CreateReceiptModal: React.FC<CreateReceiptModalProps> = ({
  isOpen,
  onClose,
  transaction,
  onCreated,
}) => {
  const currentUser = getActiveUser();
  const outstanding = round2(transaction.totalAmount - (transaction.paidAmount || 0));

  const [amount, setAmount] = useState<number>(outstanding);
  const [bankAccountCode, setBankAccountCode] = useState('1030'); // Collections
  const [receiptMethod, setReceiptMethod] = useState<'Bank Transfer' | 'Credit Card' | 'Cash'>('Bank Transfer');
  const [referenceNumber, setReferenceNumber] = useState(`WIRE-IN-${Date.now().toString().slice(-6)}`);
  const [receiptDate, setReceiptDate] = useState(DEMO_TODAY);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (amount <= 0 || amount > outstanding) {
      setErrorBanner(`Amount must be between 0.01 and outstanding balance of AED ${formatAED(outstanding)}.`);
      return;
    }

    const assignedSeq = getNextSequenceNumber('RCT', 2026);
    const receipt: ARReceipt = {
      id: `RCT-ID-${Date.now()}`,
      number: assignedSeq,
      businessUnit: transaction.businessUnit,
      customerId: transaction.customerId,
      customerName: transaction.customerName,
      receiptDate,
      glDate: receiptDate,
      receiptMethod,
      bankAccountCode,
      amount,
      unappliedAmount: 0,
      referenceNumber,
      applications: [{ transactionId: transaction.id, transactionNumber: transaction.number, amountApplied: amount }],
      status: 'Posted',
      createdBy: currentUser.userId,
      createdAt: new Date().toISOString(),
      approvedBy: currentUser.userId,
      approvedAt: new Date().toISOString(),
    };

    // Subledger Posting: Dr Bank 1030 / Cr AR Control
    const subEntry = buildARReceiptAccounting(receipt, transaction.customerType);
    const postRes = postToGL(subEntry, {
      createdBy: currentUser.userId,
      approvedBy: currentUser.userId,
      category: 'Receipts',
    });

    if (postRes.success && postRes.journal) {
      receipt.glJournalId = postRes.journal.id;

      updateDb((state) => {
        state.arReceipts.unshift(receipt);
        const target = state.arTransactions.find((i) => i.id === transaction.id);
        if (target) {
          target.paidAmount = addMoney(target.paidAmount || 0, amount);
        }
      });

      addAuditLog({
        entityType: 'ARReceipt',
        entityId: receipt.id,
        action: 'POST',
        userId: currentUser.userId,
        userName: currentUser.name,
        comments: `Applied payment receipt ${receipt.number} to AR invoice ${transaction.number}. Posted GL ${postRes.journal.number}`,
      });

      onCreated(receipt);
    } else {
      setErrorBanner(`Receipt Posting Failed: ${postRes.errors?.join('; ')}`);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs" onClick={onClose} />

      <div className="relative bg-white rounded-xl shadow-2xl border border-gray-200 max-w-lg w-full p-6 z-10 animate-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between pb-3 border-b border-gray-100 mb-4">
          <div className="flex items-center space-x-2">
            <CreditCard className="w-5 h-5 text-[#5B2C83]" />
            <h3 className="font-bold text-base text-gray-900">Record Customer Receipt</h3>
          </div>
          <button onClick={onClose} className="p-1 rounded text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        {errorBanner && (
          <div className="mb-4 p-3 bg-rose-50 border border-rose-300 text-rose-800 rounded-lg text-xs flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{errorBanner}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div className="p-3 bg-plum-50 rounded-lg text-xs space-y-1">
            <div className="flex justify-between">
              <span className="text-gray-500">Invoice Reference:</span>
              <span className="font-mono font-bold text-[#5B2C83]">{transaction.number}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Customer:</span>
              <span className="font-semibold text-gray-800">{transaction.customerName}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Outstanding Balance:</span>
              <span className="font-mono font-bold text-gray-900">AED {formatAED(outstanding)}</span>
            </div>
          </div>

          <div>
            <label className="block font-semibold text-gray-700 mb-1">Receipt Amount (AED)</label>
            <input
              type="number"
              step="0.01"
              max={outstanding}
              value={amount}
              onChange={(e) => setAmount(parseFloat(e.target.value) || 0)}
              className="w-full p-2 border border-gray-300 rounded font-mono font-bold text-sm"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-gray-700 mb-1">Receipt Method</label>
              <select
                value={receiptMethod}
                onChange={(e) => setReceiptMethod(e.target.value as any)}
                className="w-full p-2 border border-gray-300 rounded"
              >
                <option value="Bank Transfer">Bank Wire Transfer</option>
                <option value="Credit Card">Credit Card Terminal</option>
                <option value="Cash">Cash at Counter</option>
              </select>
            </div>
            <div>
              <label className="block font-semibold text-gray-700 mb-1">Deposit Account</label>
              <select
                value={bankAccountCode}
                onChange={(e) => setBankAccountCode(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded font-mono"
              >
                <option value="1030">1030 - Collections Bank</option>
                <option value="1000">1000 - Main Cash Safe</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-gray-700 mb-1">Bank Reference / Auth</label>
              <input
                type="text"
                value={referenceNumber}
                onChange={(e) => setReferenceNumber(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded font-medium"
                required
              />
            </div>
            <div>
              <label className="block font-semibold text-gray-700 mb-1">Receipt Date</label>
              <input
                type="date"
                value={receiptDate}
                onChange={(e) => setReceiptDate(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded"
              />
            </div>
          </div>

          <div className="pt-3 border-t border-gray-100 flex justify-end space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 font-semibold"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-[#5B2C83] hover:bg-[#3F1D5C] text-white rounded-lg font-semibold"
            >
              Post Receipt & Relieve AR &rarr;
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
