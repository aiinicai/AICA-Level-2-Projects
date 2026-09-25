import React, { useState, useMemo } from 'react';
import {
  Scale,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Sparkles,
  ArrowRight,
  Filter,
  Eye,
  Split,
  ChevronRight,
  Layers,
  FileText,
  Landmark,
  ShieldCheck,
  CheckCheck
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { ReconciliationMatch, BankTransaction, Invoice } from '../../types';
import { formatINR, formatDate } from '../../utils/formatters';

export const ReconciliationCentreView: React.FC = () => {
  const {
    suggestedMatches,
    bankTransactions,
    invoices,
    approveMatch,
    rejectMatch,
    autoApproveHighConfidence,
    currentUser
  } = useApp();

  const [activeSubTab, setActiveSubTab] = useState<'suggested' | 'unallocated_tx' | 'unmatched_inv' | 'history'>('suggested');
  const [selectedMatch, setSelectedMatch] = useState<ReconciliationMatch | null>(null);
  const [selectedTxForSplit, setSelectedTxForSplit] = useState<BankTransaction | null>(null);

  const canEdit = currentUser.role !== 'Viewer';

  // High confidence count
  const highConfidenceMatches = suggestedMatches.filter(m => m.confidenceScore >= 90);

  // Unallocated bank transactions (Credit deposits with balance > 0)
  const unallocatedReceipts = bankTransactions.filter(
    tx => tx.isCredit && tx.unallocatedAmount > 0
  );

  // Unmatched open invoices (Balance > 0)
  const openInvoices = invoices.filter(inv => inv.balance > 0);

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Payment Reconciliation Centre</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Automated multi-rule matching engine for Indian SME receipts, TDS adjustments, and UTR clearing.
          </p>
        </div>

        {canEdit && highConfidenceMatches.length > 0 && (
          <button
            onClick={() => {
              if (window.confirm(`Auto-reconcile and approve all ${highConfidenceMatches.length} High-Confidence (>90%) matches?`)) {
                autoApproveHighConfidence();
              }
            }}
            className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-bold transition-all shadow-xs flex items-center gap-2"
          >
            <CheckCheck className="w-4 h-4" />
            <span>Auto-Approve {highConfidenceMatches.length} High Confidence Matches</span>
          </button>
        )}
      </div>

      {/* Sub-Tab Navigation */}
      <div className="flex border-b border-slate-200 bg-white rounded-t-xl px-4 text-xs font-semibold gap-2 shadow-xs">
        <button
          onClick={() => setActiveSubTab('suggested')}
          className={`py-3.5 px-3 border-b-2 transition-colors flex items-center gap-1.5 ${
            activeSubTab === 'suggested'
              ? 'border-emerald-600 text-emerald-700 font-bold'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Sparkles className="w-4 h-4 text-emerald-600" />
          <span>Suggested Matches</span>
          {suggestedMatches.length > 0 && (
            <span className="ml-1 px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
              {suggestedMatches.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveSubTab('unallocated_tx')}
          className={`py-3.5 px-3 border-b-2 transition-colors flex items-center gap-1.5 ${
            activeSubTab === 'unallocated_tx'
              ? 'border-emerald-600 text-emerald-700 font-bold'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Landmark className="w-4 h-4 text-amber-600" />
          <span>Unallocated Receipts</span>
          {unallocatedReceipts.length > 0 && (
            <span className="ml-1 px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">
              {unallocatedReceipts.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveSubTab('unmatched_inv')}
          className={`py-3.5 px-3 border-b-2 transition-colors flex items-center gap-1.5 ${
            activeSubTab === 'unmatched_inv'
              ? 'border-emerald-600 text-emerald-700 font-bold'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <FileText className="w-4 h-4 text-blue-600" />
          <span>Open Invoices ({openInvoices.length})</span>
        </button>
      </div>

      {/* Suggested Matches Table */}
      {activeSubTab === 'suggested' && (
        <div className="bg-white rounded-b-xl border border-t-0 border-slate-200 overflow-hidden shadow-xs">
          {suggestedMatches.length === 0 ? (
            <div className="p-12 text-center text-slate-400 space-y-2">
              <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto" />
              <h3 className="font-bold text-slate-800 text-base">All Suggested Matches Reconciled!</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                The engine has matched all available bank credits against invoices. Check Unallocated Receipts or import new bank statements.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                  <tr>
                    <th className="p-3.5">Bank Credit (Date / Ref)</th>
                    <th className="p-3.5">Deposit Amount</th>
                    <th className="p-3.5">Suggested Invoice</th>
                    <th className="p-3.5">Outstanding</th>
                    <th className="p-3.5">Rule & TDS Details</th>
                    <th className="p-3.5">Confidence</th>
                    <th className="p-3.5 text-center">Reconcile</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {suggestedMatches.map((match) => (
                    <tr key={match.id} className="hover:bg-slate-50/80 transition-colors">
                      {/* Bank Transaction */}
                      <td className="p-3.5 max-w-xs">
                        <div className="font-mono text-slate-900 font-semibold truncate">
                          {match.bankTransaction.narration}
                        </div>
                        <div className="text-[10px] text-slate-400 mt-0.5">
                          {formatDate(match.bankTransaction.transactionDate)} • Ref: {match.bankTransaction.referenceNumber || 'N/A'}
                        </div>
                      </td>

                      {/* Deposit Amount */}
                      <td className="p-3.5 font-mono font-bold text-emerald-700">
                        {formatINR(match.allocatedAmount, false)}
                      </td>

                      {/* Suggested Invoice */}
                      <td className="p-3.5">
                        <span className="font-mono font-bold text-slate-900 block">{match.invoice.invoiceNumber}</span>
                        <span className="font-medium text-slate-700 text-[11px] block truncate max-w-[160px]">
                          {match.invoice.customerName}
                        </span>
                      </td>

                      {/* Invoice Outstanding */}
                      <td className="p-3.5 font-mono text-slate-800">
                        {formatINR(match.invoice.balance, false)}
                      </td>

                      {/* Rule & TDS */}
                      <td className="p-3.5">
                        <span className="inline-block font-semibold text-slate-800 text-[11px] block">
                          {match.ruleApplied}
                        </span>
                        {match.tdsAdjustment > 0 && (
                          <span className="inline-block text-[10px] font-bold text-purple-700 bg-purple-50 px-1.5 py-0.5 rounded border border-purple-200 mt-0.5">
                            + {formatINR(match.tdsAdjustment, false)} TDS adj
                          </span>
                        )}
                        {match.differenceAmount !== 0 && (
                          <span className="inline-block text-[10px] font-bold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200 mt-0.5 ml-1">
                            ₹{match.differenceAmount} {match.differenceReason || 'diff'}
                          </span>
                        )}
                      </td>

                      {/* Confidence Badge */}
                      <td className="p-3.5">
                        <div className="flex items-center gap-1.5">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              match.confidenceScore >= 95
                                ? 'bg-emerald-100 text-emerald-800'
                                : match.confidenceScore >= 80
                                ? 'bg-blue-100 text-blue-800'
                                : 'bg-amber-100 text-amber-800'
                            }`}
                          >
                            {match.confidenceScore}%
                          </span>
                        </div>
                      </td>

                      {/* Actions */}
                      <td className="p-3.5 text-center">
                        <div className="flex items-center justify-center gap-1">
                          <button
                            onClick={() => setSelectedMatch(match)}
                            className="p-1.5 text-slate-500 hover:text-slate-900 rounded hover:bg-slate-100"
                            title="Inspect Match Logic"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          {canEdit && (
                            <>
                              <button
                                onClick={() => approveMatch(match)}
                                className="px-2.5 py-1 bg-emerald-700 hover:bg-emerald-800 text-white rounded font-bold text-[11px] shadow-xs flex items-center gap-1 transition-colors"
                              >
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                <span>Accept</span>
                              </button>
                              <button
                                onClick={() => rejectMatch(match)}
                                className="p-1 text-slate-400 hover:text-rose-600 rounded hover:bg-rose-50"
                                title="Reject / Dismiss"
                              >
                                <XCircle className="w-4 h-4" />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Unallocated Receipts Tab */}
      {activeSubTab === 'unallocated_tx' && (
        <div className="bg-white rounded-b-xl border border-t-0 border-slate-200 overflow-hidden shadow-xs">
          <div className="p-4 bg-amber-50/50 border-b border-amber-200/60 text-xs text-amber-900">
            <strong>Manual Allocation Workflow:</strong> These bank credits did not meet deterministic auto-match thresholds. Click "Allocate to Invoices" to match against open customer balances.
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-[10px] uppercase font-bold text-slate-500">
                <tr>
                  <th className="p-3.5">Date</th>
                  <th className="p-3.5">Bank Narration</th>
                  <th className="p-3.5">Reference / UTR</th>
                  <th className="p-3.5 text-right">Receipt Amount</th>
                  <th className="p-3.5 text-right">Unallocated</th>
                  <th className="p-3.5 text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {unallocatedReceipts.map((tx) => (
                  <tr key={tx.id} className="hover:bg-slate-50">
                    <td className="p-3.5 font-semibold text-slate-800">{formatDate(tx.transactionDate)}</td>
                    <td className="p-3.5 font-mono text-slate-900 font-medium max-w-sm break-words">{tx.narration}</td>
                    <td className="p-3.5 font-mono text-slate-500">{tx.referenceNumber || 'N/A'}</td>
                    <td className="p-3.5 text-right font-mono font-bold text-emerald-700">{formatINR(tx.amount, false)}</td>
                    <td className="p-3.5 text-right font-mono font-bold text-amber-700">{formatINR(tx.unallocatedAmount, false)}</td>
                    <td className="p-3.5 text-center">
                      <button
                        onClick={() => setSelectedTxForSplit(tx)}
                        className="px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300 rounded font-bold text-[11px] flex items-center gap-1 mx-auto"
                      >
                        <Split className="w-3.5 h-3.5 text-emerald-600" />
                        <span>Allocate to Invoices</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Open Invoices Tab */}
      {activeSubTab === 'unmatched_inv' && (
        <div className="bg-white rounded-b-xl border border-t-0 border-slate-200 overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-[10px] uppercase font-bold text-slate-500">
                <tr>
                  <th className="p-3.5">Invoice No</th>
                  <th className="p-3.5">Date & Due Date</th>
                  <th className="p-3.5">Customer Name</th>
                  <th className="p-3.5 text-right">Invoice Total</th>
                  <th className="p-3.5 text-right">Expected TDS</th>
                  <th className="p-3.5 text-right">Outstanding Due</th>
                  <th className="p-3.5">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {openInvoices.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-50">
                    <td className="p-3.5 font-mono font-bold text-slate-900">{inv.invoiceNumber}</td>
                    <td className="p-3.5 text-slate-600">
                      {formatDate(inv.invoiceDate)} • Due: {formatDate(inv.dueDate)}
                    </td>
                    <td className="p-3.5 font-semibold text-slate-800">{inv.customerName}</td>
                    <td className="p-3.5 text-right font-mono">{formatINR(inv.totalInvoiceValue, false)}</td>
                    <td className="p-3.5 text-right font-mono text-purple-700">{formatINR(inv.expectedTds, false)}</td>
                    <td className="p-3.5 text-right font-mono font-bold text-rose-600">{formatINR(inv.balance, false)}</td>
                    <td className="p-3.5">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        inv.status === 'Overdue' ? 'bg-rose-100 text-rose-800' : 'bg-amber-100 text-amber-800'
                      }`}>
                        {inv.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Match Inspection Modal */}
      {selectedMatch && (
        <MatchInspectorModal
          match={selectedMatch}
          onClose={() => setSelectedMatch(null)}
          onApprove={() => {
            approveMatch(selectedMatch);
            setSelectedMatch(null);
          }}
          canEdit={canEdit}
        />
      )}

      {/* Manual Split Allocation Modal */}
      {selectedTxForSplit && (
        <ManualSplitAllocationModal
          transaction={selectedTxForSplit}
          invoices={openInvoices}
          onClose={() => setSelectedTxForSplit(null)}
        />
      )}
    </div>
  );
};

interface MatchInspectorModalProps {
  match: ReconciliationMatch;
  onClose: () => void;
  onApprove: () => void;
  canEdit: boolean;
}

const MatchInspectorModal: React.FC<MatchInspectorModalProps> = ({ match, onClose, onApprove, canEdit }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="bg-white w-full max-w-xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Scale className="w-5 h-5 text-emerald-700" />
            <h3 className="font-bold text-slate-900 text-sm">Match Logic & Accounting Impact</h3>
          </div>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg">
            ✕
          </button>
        </div>

        <div className="p-5 space-y-4 text-xs">
          {/* Rule Header */}
          <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-200">
            <div className="flex items-center justify-between">
              <span className="font-bold text-emerald-950 text-sm">{match.ruleApplied}</span>
              <span className="px-2 py-0.5 rounded font-bold text-xs bg-emerald-700 text-white">
                {match.confidenceScore}% Confidence
              </span>
            </div>
            <p className="text-[11px] text-emerald-800 mt-1">{match.remarks}</p>
          </div>

          {/* Side by Side comparison */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Bank Receipt</span>
              <p className="font-mono font-bold text-slate-900 text-sm">{formatINR(match.allocatedAmount)}</p>
              <p className="font-mono text-[10px] text-slate-500 break-words">{match.bankTransaction.narration}</p>
              <p className="text-[10px] text-slate-400">Date: {formatDate(match.bankTransaction.transactionDate)}</p>
            </div>

            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Target Invoice</span>
              <p className="font-mono font-bold text-slate-900 text-sm">{formatINR(match.invoice.balance)} due</p>
              <p className="font-mono text-xs font-bold text-slate-800">{match.invoice.invoiceNumber}</p>
              <p className="text-[10px] text-slate-600 truncate">{match.invoice.customerName}</p>
            </div>
          </div>

          {/* Tax & Deduction Settlement Preview */}
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1.5 font-mono text-slate-700 text-xs">
            <div className="font-bold text-slate-900 text-[11px] uppercase tracking-wider mb-1 font-sans">
              Accounting Entry Settlement Preview:
            </div>
            <div className="flex justify-between">
              <span>Debit: Bank A/c (Actual Credit Received):</span>
              <span className="font-bold text-emerald-700">₹{match.allocatedAmount.toLocaleString('en-IN')}</span>
            </div>
            {match.tdsAdjustment > 0 && (
              <div className="flex justify-between text-purple-700">
                <span>Debit: TDS Receivable A/c (Sec {match.invoice.tdsSection || '194C'}):</span>
                <span className="font-bold">₹{match.tdsAdjustment.toLocaleString('en-IN')}</span>
              </div>
            )}
            {match.differenceAmount !== 0 && (
              <div className="flex justify-between text-amber-700">
                <span>Round-off / Difference ({match.differenceReason}):</span>
                <span className="font-bold">₹{match.differenceAmount.toLocaleString('en-IN')}</span>
              </div>
            )}
            <div className="flex justify-between text-slate-900 font-bold pt-1 border-t border-slate-200">
              <span>Credit: Customer Ledger ({match.invoice.customerName}):</span>
              <span>₹{(match.allocatedAmount + match.tdsAdjustment + match.differenceAmount).toLocaleString('en-IN')}</span>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button onClick={onClose} className="px-4 py-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100">
              Close
            </button>
            {canEdit && (
              <button
                onClick={onApprove}
                className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg font-bold shadow-xs flex items-center gap-1.5"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Confirm & Post Reconciliation</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const ManualSplitAllocationModal: React.FC<{
  transaction: BankTransaction;
  invoices: Invoice[];
  onClose: () => void;
}> = ({ transaction, invoices, onClose }) => {
  const { allocatePaymentManually } = useApp();
  const [selectedInvId, setSelectedInvId] = useState(invoices[0]?.id || '');
  const [amountToAllocate, setAmountToAllocate] = useState(transaction.unallocatedAmount);
  const [tdsDeducted, setTdsDeducted] = useState(0);

  const selectedInv = invoices.find(i => i.id === selectedInvId);

  const handleAllocate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInv) return;

    allocatePaymentManually(transaction.id, selectedInv.id, amountToAllocate, tdsDeducted);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="bg-white w-full max-w-lg rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div>
            <h3 className="font-bold text-slate-900 text-sm">Manual Payment Allocation</h3>
            <p className="text-xs text-slate-500">Receipt Ref: {transaction.referenceNumber}</p>
          </div>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg">✕</button>
        </div>

        <form onSubmit={handleAllocate} className="p-5 space-y-4 text-xs">
          <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-200">
            <span className="text-[10px] font-bold text-emerald-800 uppercase">Available for Allocation</span>
            <p className="font-mono font-bold text-emerald-950 text-base">{formatINR(transaction.unallocatedAmount)}</p>
            <p className="text-[11px] text-emerald-800 font-mono mt-0.5 truncate">{transaction.narration}</p>
          </div>

          <div>
            <label className="font-semibold text-slate-700 block mb-1">Select Open Invoice to Settle *</label>
            <select
              value={selectedInvId}
              onChange={e => {
                setSelectedInvId(e.target.value);
                const inv = invoices.find(i => i.id === e.target.value);
                if (inv) {
                  setAmountToAllocate(Math.min(transaction.unallocatedAmount, inv.balance));
                  setTdsDeducted(inv.expectedTds);
                }
              }}
              className="w-full p-2 rounded-lg border border-slate-200 bg-white"
            >
              {invoices.map(inv => (
                <option key={inv.id} value={inv.id}>
                  {inv.invoiceNumber} - {inv.customerName} (Bal: {formatINR(inv.balance)})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="font-semibold text-slate-700 block mb-1">Allocated Amount (₹) *</label>
              <input
                type="number"
                required
                max={transaction.unallocatedAmount}
                value={amountToAllocate}
                onChange={e => setAmountToAllocate(parseFloat(e.target.value) || 0)}
                className="w-full p-2 font-mono font-bold rounded-lg border border-slate-200"
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">TDS Claimed (₹)</label>
              <input
                type="number"
                value={tdsDeducted}
                onChange={e => setTdsDeducted(parseFloat(e.target.value) || 0)}
                className="w-full p-2 font-mono rounded-lg border border-slate-200"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100">
              Cancel
            </button>
            <button type="submit" className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg font-bold shadow-xs">
              Commit Allocation
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
