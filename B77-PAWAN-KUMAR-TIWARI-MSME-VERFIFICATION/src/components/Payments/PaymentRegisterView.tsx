import React, { useState } from 'react';
import {
  CreditCard,
  Search,
  Plus,
  Calendar,
  CheckCircle2,
  Clock,
  Trash2,
  Download,
  Building2,
  FileText,
  AlertTriangle,
  ArrowRight,
  TrendingDown,
  X,
  FileSpreadsheet,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { Invoice, PartPayment } from '../../types';
import { formatINR, formatDate, getDaysDifference } from '../../utils/formatters';
import { exportTableToExcel } from '../../utils/excelService';
import { ExcelUploadModal } from '../Common/ExcelUploadModal';

export const PaymentRegisterView: React.FC = () => {
  const { invoices, addPartPayment, deletePartPayment, currentUserRole, asOfDate } = useApp();

  const [searchTerm, setSearchTerm] = useState('');
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string>('ALL');
  const [isAddPaymentModalOpen, setIsAddPaymentModalOpen] = useState(false);
  const [isExcelModalOpen, setIsExcelModalOpen] = useState(false);
  const [selectedInvoiceForPayment, setSelectedInvoiceForPayment] = useState<Invoice | null>(null);

  // Flatten all part payments with invoice metadata
  const allPayments = invoices.flatMap((inv) =>
    (inv.payments || []).map((pmt) => ({
      ...pmt,
      invoiceNumber: inv.invoiceNumber,
      vendorName: inv.vendorName,
      vendorCode: inv.vendorCode,
      msmeCategory: inv.msmeCategory,
      finalDueDate: inv.finalDueDate,
      totalInvoiceAmount: inv.totalInvoiceAmount,
    }))
  );

  const filteredPayments = allPayments.filter((pmt) => {
    const matchesSearch =
      pmt.paymentReference.toLowerCase().includes(searchTerm.toLowerCase()) ||
      pmt.invoiceNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
      pmt.vendorName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (pmt.bankReferenceNo || '').toLowerCase().includes(searchTerm.toLowerCase());

    const matchesInvoice = selectedInvoiceId === 'ALL' || pmt.invoiceId === selectedInvoiceId;
    return matchesSearch && matchesInvoice;
  });

  // Invoices with outstanding balances or active part-payments
  const outstandingInvoices = invoices.filter((inv) => inv.outstandingAmount > 0);

  const handleExportPayments = () => {
    const exportData = filteredPayments.map((p) => ({
      'Payment Ref': p.paymentReference,
      'Payment Date': formatDate(p.paymentDate),
      'Invoice Number': p.invoiceNumber,
      'Vendor Name': p.vendorName,
      'Amount Paid (₹)': p.amount,
      'Payment Mode': p.paymentMode,
      'Bank Ref / UTR': p.bankReferenceNo || '—',
      'Statutory Due Date': formatDate(p.finalDueDate),
      'Recorded By': p.recordedBy,
      'Recorded At': formatDate(p.recordedAt),
      Remarks: p.remarks || '—',
    }));
    exportTableToExcel(exportData, 'MSME_Part_Payment_Register', 'Payments');
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900">Part Payment & Tranche Settlement Register</h2>
          <p className="text-xs text-slate-500">
            Record multi-tranche partial settlements against invoices with dynamic interest truncation
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setIsExcelModalOpen(true)}
            className="px-3.5 py-2 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300 text-xs font-bold rounded-lg shadow-xs flex items-center gap-1.5 transition-colors cursor-pointer"
            title="Bulk Import Bank Payments / UTR Clearing via Excel"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-700" />
            Import Payments Excel
          </button>

          <button
            onClick={handleExportPayments}
            className="px-3.5 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg shadow-xs flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <Download className="w-3.5 h-3.5 text-slate-600" />
            Export Payments
          </button>

          {currentUserRole !== 'Auditor' && (
            <button
              disabled={outstandingInvoices.length === 0}
              onClick={() => {
                setSelectedInvoiceForPayment(outstandingInvoices[0] || null);
                setIsAddPaymentModalOpen(true);
              }}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold rounded-lg shadow-xs flex items-center gap-1.5 transition-all cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              Record Part Payment
            </button>
          )}
        </div>
      </div>

      {/* Part Payment Methodology Example Banner */}
      <div className="p-4 bg-gradient-to-r from-blue-900 to-slate-900 text-white rounded-xl shadow-xs space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingDown className="w-4 h-4 text-emerald-400" />
            <h3 className="font-bold text-xs uppercase tracking-wider text-emerald-300">
              Statutory Multi-Tranche Reducing Balance Methodology
            </h3>
          </div>
          <span className="text-[10px] bg-white/10 px-2 py-0.5 rounded font-mono">MSMED Act Sec 16</span>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed">
          When an invoice (e.g. ₹10,00,000) is settled in multiple payments (e.g. ₹4L on Day 15, ₹3L on Day 30, ₹3L on Day 60), the calculation engine automatically splits the delay into sequential tranches, calculating interest only on the reducing balance for the exact delay duration of that tranche.
        </p>
      </div>

      {/* Quick Action: Invoices Pending Payment */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3">
        <h3 className="font-bold text-slate-800 text-sm flex items-center justify-between">
          <span>Invoices Pending Full Settlement ({outstandingInvoices.length})</span>
          <span className="text-xs font-normal text-slate-500">Click to record part payment</span>
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {outstandingInvoices.slice(0, 6).map((inv) => {
            const isOverdue = new Date(asOfDate) > new Date(inv.finalDueDate);
            const delayDays = Math.max(0, getDaysDifference(inv.finalDueDate, asOfDate));

            return (
              <div
                key={inv.id}
                className="p-3.5 rounded-lg border border-slate-200 hover:border-emerald-500 bg-slate-50/50 hover:bg-emerald-50/20 transition-all flex flex-col justify-between"
              >
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900 text-xs truncate max-w-[150px]">{inv.invoiceNumber}</span>
                    <span
                      className={`text-[10px] font-extrabold px-1.5 py-0.5 rounded ${
                        isOverdue ? 'bg-rose-100 text-rose-800' : 'bg-emerald-100 text-emerald-800'
                      }`}
                    >
                      {isOverdue ? `${delayDays}d Overdue` : 'Within Term'}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-600 truncate">{inv.vendorName}</div>
                  <div className="text-[11px] text-slate-500 flex justify-between pt-1">
                    <span>Outstanding:</span>
                    <strong className="text-rose-700 font-bold">{formatINR(inv.outstandingAmount)}</strong>
                  </div>
                  <div className="text-[10px] text-slate-400">
                    Paid: {formatINR(inv.amountPaid)} / {formatINR(inv.totalInvoiceAmount)} ({inv.payments.length} tranches)
                  </div>
                </div>

                {currentUserRole !== 'Auditor' && (
                  <button
                    onClick={() => {
                      setSelectedInvoiceForPayment(inv);
                      setIsAddPaymentModalOpen(true);
                    }}
                    className="mt-3 w-full py-1.5 bg-white border border-slate-300 hover:bg-emerald-700 hover:text-white hover:border-emerald-700 text-slate-700 font-bold text-xs rounded-md shadow-xs transition-all cursor-pointer"
                  >
                    + Add Part Payment
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Filter and Search */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search payment reference, invoice, vendor..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-hidden focus:bg-white focus:border-emerald-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 font-semibold">Filter Invoice:</span>
          <select
            value={selectedInvoiceId}
            onChange={(e) => setSelectedInvoiceId(e.target.value)}
            className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-700 max-w-[200px]"
          >
            <option value="ALL">All Invoices ({allPayments.length} payments)</option>
            {invoices.map((inv) => (
              <option key={inv.id} value={inv.id}>
                {inv.invoiceNumber} ({inv.vendorName.substring(0, 15)}...)
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Payment Tranches Log Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase text-[10px] font-bold tracking-wider">
              <tr>
                <th className="px-4 py-3">Payment Reference</th>
                <th className="px-4 py-3">Payment Date</th>
                <th className="px-4 py-3">Invoice Number</th>
                <th className="px-4 py-3">Vendor</th>
                <th className="px-4 py-3">Mode & Bank Ref</th>
                <th className="px-4 py-3 text-right">Amount Paid</th>
                <th className="px-4 py-3">Recorded By</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredPayments.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-slate-400">
                    No payment tranches recorded yet.
                  </td>
                </tr>
              ) : (
                filteredPayments.map((pmt) => {
                  const delayAgainstDueDate = getDaysDifference(pmt.finalDueDate, pmt.paymentDate);
                  const isPaidLate = delayAgainstDueDate > 0;

                  return (
                    <tr key={pmt.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="px-4 py-3.5">
                        <div className="font-bold text-slate-900 font-mono">{pmt.paymentReference}</div>
                        {pmt.remarks && <div className="text-[10px] text-slate-400 mt-0.5">{pmt.remarks}</div>}
                      </td>

                      <td className="px-4 py-3.5">
                        <div className="font-semibold text-slate-800">{formatDate(pmt.paymentDate)}</div>
                        <div className="text-[10px] mt-0.5">
                          {isPaidLate ? (
                            <span className="text-rose-700 font-semibold">
                              Delayed by {delayAgainstDueDate}d vs Due Date
                            </span>
                          ) : (
                            <span className="text-emerald-700 font-semibold">Settled on/before due date</span>
                          )}
                        </div>
                      </td>

                      <td className="px-4 py-3.5">
                        <span className="font-bold text-slate-800">{pmt.invoiceNumber}</span>
                        <div className="text-[10px] text-slate-400">
                          Total Inv: {formatINR(pmt.totalInvoiceAmount)}
                        </div>
                      </td>

                      <td className="px-4 py-3.5">
                        <div className="font-bold text-slate-800">{pmt.vendorName}</div>
                        <div className="text-[10px] text-slate-400 font-mono">{pmt.vendorCode}</div>
                      </td>

                      <td className="px-4 py-3.5 text-[11px]">
                        <span className="px-1.5 py-0.5 bg-slate-100 rounded font-semibold text-slate-700">
                          {pmt.paymentMode}
                        </span>
                        {pmt.bankReferenceNo && (
                          <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                            Ref: {pmt.bankReferenceNo}
                          </div>
                        )}
                      </td>

                      <td className="px-4 py-3.5 text-right font-bold text-emerald-700 text-sm">
                        {formatINR(pmt.amount)}
                      </td>

                      <td className="px-4 py-3.5 text-[11px] text-slate-500">
                        <div>{pmt.recordedBy.split(' ')[0]}</div>
                        <div className="text-[10px] text-slate-400">{formatDate(pmt.recordedAt)}</div>
                      </td>

                      <td className="px-4 py-3.5 text-right">
                        {currentUserRole !== 'Auditor' && (
                          <button
                            onClick={() => deletePartPayment(pmt.invoiceId, pmt.id)}
                            className="p-1.5 text-rose-600 hover:bg-rose-50 rounded-lg transition-colors cursor-pointer"
                            title="Delete Payment Tranche"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Record Payment Modal */}
      {isAddPaymentModalOpen && selectedInvoiceForPayment && (
        <RecordPaymentModal
          invoice={selectedInvoiceForPayment}
          onClose={() => {
            setIsAddPaymentModalOpen(false);
            setSelectedInvoiceForPayment(null);
          }}
          onSave={(paymentData) => {
            addPartPayment(selectedInvoiceForPayment.id, paymentData);
            setIsAddPaymentModalOpen(false);
            setSelectedInvoiceForPayment(null);
          }}
        />
      )}

      {/* Excel Upload Modal */}
      <ExcelUploadModal
        isOpen={isExcelModalOpen}
        onClose={() => setIsExcelModalOpen(false)}
        type="payments"
      />
    </div>
  );
};

/* --- Record Payment Modal --- */
interface RecordPaymentModalProps {
  invoice: Invoice;
  onClose: () => void;
  onSave: (paymentData: any) => void;
}

const RecordPaymentModal: React.FC<RecordPaymentModalProps> = ({ invoice, onClose, onSave }) => {
  const [paymentReference, setPaymentReference] = useState(`NEFT/AXIS/${Math.floor(10000000 + Math.random() * 90000000)}`);
  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().split('T')[0]);
  const [amount, setAmount] = useState(invoice.outstandingAmount);
  const [paymentMode, setPaymentMode] = useState<any>('NEFT');
  const [bankReferenceNo, setBankReferenceNo] = useState(`AXISN${new Date().getFullYear()}${Math.floor(1000000 + Math.random() * 9000000)}`);
  const [remarks, setRemarks] = useState(`Part settlement tranche against invoice ${invoice.invoiceNumber}`);

  const delayDays = getDaysDifference(invoice.finalDueDate, paymentDate);
  const isDelayed = delayDays > 0;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (amount <= 0) {
      alert('Payment amount must be greater than zero.');
      return;
    }
    if (amount > invoice.outstandingAmount) {
      if (!confirm(`Entered amount (${formatINR(amount)}) exceeds current outstanding (${formatINR(invoice.outstandingAmount)}). Proceed anyway?`)) {
        return;
      }
    }

    onSave({
      paymentReference,
      paymentDate,
      amount: Number(amount),
      paymentMode,
      bankReferenceNo,
      remarks,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50">
          <div className="flex items-center gap-2">
            <CreditCard className="w-5 h-5 text-emerald-700" />
            <div>
              <h3 className="font-bold text-slate-800 text-sm">Record Invoice Payment Tranche</h3>
              <p className="text-[11px] text-slate-500">Invoice: {invoice.invoiceNumber} ({invoice.vendorName})</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-slate-600 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4 text-xs">
          {/* Invoice Summary Box */}
          <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-200 grid grid-cols-2 gap-2 text-[11px]">
            <div>
              <span className="text-slate-400 block">Total Invoice:</span>
              <strong className="text-slate-800 text-xs">{formatINR(invoice.totalInvoiceAmount)}</strong>
            </div>
            <div>
              <span className="text-slate-400 block">Current Outstanding:</span>
              <strong className="text-rose-700 text-xs">{formatINR(invoice.outstandingAmount)}</strong>
            </div>
            <div>
              <span className="text-slate-400 block">Statutory Due Date:</span>
              <strong className="text-slate-800">{formatDate(invoice.finalDueDate)}</strong>
            </div>
            <div>
              <span className="text-slate-400 block">Previously Paid:</span>
              <strong className="text-emerald-700">{formatINR(invoice.amountPaid)} ({invoice.payments.length} tranches)</strong>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block font-bold text-slate-700 mb-1">Payment Date *</label>
              <input
                type="date"
                required
                value={paymentDate}
                onChange={(e) => setPaymentDate(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-hidden"
              />
              {isDelayed ? (
                <span className="text-[10px] text-rose-700 font-semibold mt-0.5 block">
                  🔴 {delayDays} days delay vs due date
                </span>
              ) : (
                <span className="text-[10px] text-emerald-700 font-semibold mt-0.5 block">
                  🟢 Paid on / before due date
                </span>
              )}
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">Amount Paid (₹) *</label>
              <input
                type="number"
                required
                min={1}
                value={amount}
                onChange={(e) => setAmount(Number(e.target.value))}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono font-bold text-slate-900 focus:outline-hidden"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block font-bold text-slate-700 mb-1">Payment Mode</label>
              <select
                value={paymentMode}
                onChange={(e) => setPaymentMode(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg font-medium focus:outline-hidden"
              >
                <option value="NEFT">NEFT (Electronic Fund Transfer)</option>
                <option value="RTGS">RTGS (Real Time Gross Settlement)</option>
                <option value="Direct Debit">Direct Bank Debit</option>
                <option value="Cheque">Corporate Cheque</option>
                <option value="UPI">UPI / Corporate Virtual Account</option>
              </select>
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">Payment Reference No. *</label>
              <input
                type="text"
                required
                value={paymentReference}
                onChange={(e) => setPaymentReference(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono uppercase focus:outline-hidden"
              />
            </div>
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">Bank UTR / Transaction Reference</label>
            <input
              type="text"
              value={bankReferenceNo}
              onChange={(e) => setBankReferenceNo(e.target.value)}
              placeholder="e.g. HDFCR2617654321"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono uppercase"
            />
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">Voucher Remarks</label>
            <input
              type="text"
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 bg-emerald-700 hover:bg-emerald-800 text-white font-bold rounded-lg shadow-xs"
            >
              Record Payment
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
