import React, { useState } from 'react';
import {
  CreditCard,
  CheckCircle2,
  X,
  DollarSign,
  Calendar,
  FileText,
  Building2,
  AlertCircle
} from 'lucide-react';
import { StorageService } from '../../services/storage';
import { Client, Voucher } from '../../types';

interface RecordPaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialClientId?: string;
  onPaymentRecorded: () => void;
}

export const RecordPaymentModal: React.FC<RecordPaymentModalProps> = ({
  isOpen,
  onClose,
  initialClientId,
  onPaymentRecorded,
}) => {
  const storage = StorageService.getInstance();
  const clients = storage.getClients();
  const allVouchers = storage.getVouchers().filter((v) => v.type === 'SALES');

  const [selectedClientId, setSelectedClientId] = useState<string>(initialClientId || (clients[0]?.id || ''));
  const [selectedVoucherId, setSelectedVoucherId] = useState<string>('');
  const [paymentAmount, setPaymentAmount] = useState<number>(0);
  const [paymentDate, setPaymentDate] = useState<string>(new Date().toISOString().slice(0, 10));
  const [paymentMethod, setPaymentMethod] = useState<'bank_transfer' | 'cheque' | 'cash' | 'mobile_money'>('bank_transfer');
  const [referenceNumber, setReferenceNumber] = useState<string>('');
  const [notes, setNotes] = useState<string>('');

  if (!isOpen) return null;

  const clientVouchers = allVouchers.filter(
    (v) => v.clientId === selectedClientId && v.status !== 'paid'
  );

  const selectedVoucher = allVouchers.find((v) => v.id === selectedVoucherId);

  const handleVoucherSelect = (vId: string) => {
    setSelectedVoucherId(vId);
    const vouch = allVouchers.find((v) => v.id === vId);
    if (vouch) {
      const remaining = (vouch.finalGrandTotal || vouch.grandTotal) - (vouch.paidAmount || 0);
      setPaymentAmount(remaining > 0 ? remaining : 0);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClientId) return;
    if (paymentAmount <= 0) return;

    storage.recordPayment({
      voucherId: selectedVoucherId || (clientVouchers[0]?.id || 'vouch_manual'),
      clientId: selectedClientId,
      amount: paymentAmount,
      paymentDate,
      paymentMethod,
      referenceNumber: referenceNumber.trim() || `REF-${Date.now().toString().slice(-6)}`,
      notes: notes.trim() || undefined,
    });

    onPaymentRecorded();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
      <div className="bg-white rounded-2xl p-6 w-full max-w-lg shadow-2xl border border-slate-200 animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center">
              <CreditCard className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">Record Client Payment Settlement</h3>
              <p className="text-[11px] text-slate-500">Apply cash, bank EFT, or cheque to outstanding invoice</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 p-1">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 pt-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Select Client *</label>
            <select
              value={selectedClientId}
              onChange={(e) => {
                setSelectedClientId(e.target.value);
                setSelectedVoucherId('');
                setPaymentAmount(0);
              }}
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-emerald-500 focus:outline-hidden"
            >
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.paymentTermsType.toUpperCase()})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Apply to Unsettled Invoice (Optional)
            </label>
            <select
              value={selectedVoucherId}
              onChange={(e) => handleVoucherSelect(e.target.value)}
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-emerald-500 focus:outline-hidden"
            >
              <option value="">-- General Account Settlement --</option>
              {clientVouchers.map((v) => {
                const remaining = (v.finalGrandTotal || v.grandTotal) - (v.paidAmount || 0);
                return (
                  <option key={v.id} value={v.id}>
                    {v.docNumber} - Due: {v.dueDate || 'N/A'} (Remaining: TZS {remaining.toLocaleString()})
                  </option>
                );
              })}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Payment Amount (TZS) *</label>
              <input
                type="number"
                required
                min={1}
                value={paymentAmount || ''}
                onChange={(e) => setPaymentAmount(parseFloat(e.target.value) || 0)}
                placeholder="0"
                className="w-full px-3 py-2 text-xs font-mono font-bold border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:outline-hidden"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Payment Date *</label>
              <input
                type="date"
                required
                value={paymentDate}
                onChange={(e) => setPaymentDate(e.target.value)}
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:outline-hidden"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Payment Channel *</label>
              <select
                value={paymentMethod}
                onChange={(e) => setPaymentMethod(e.target.value as any)}
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-emerald-500 focus:outline-hidden"
              >
                <option value="bank_transfer">Bank Wire / EFT / TISS</option>
                <option value="cheque">Company Cheque</option>
                <option value="mobile_money">Mobile Money (M-Pesa / Tigo)</option>
                <option value="cash">Direct Cash Deposit</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Bank / EFT Reference No *
              </label>
              <input
                type="text"
                required
                value={referenceNumber}
                onChange={(e) => setReferenceNumber(e.target.value)}
                placeholder="e.g. CRDB-EFT-99401"
                className="w-full px-3 py-2 text-xs font-mono border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:outline-hidden"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Notes</label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g., Verified in CRDB Corporate Account"
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:outline-hidden"
            />
          </div>

          <div className="flex justify-end space-x-2 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg shadow-sm flex items-center space-x-1.5 transition"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Record Settlement</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
