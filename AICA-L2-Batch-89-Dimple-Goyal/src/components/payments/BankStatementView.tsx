import React, { useState, useMemo } from 'react';
import {
  Landmark,
  Search,
  Download,
  Plus,
  ArrowDownLeft,
  ArrowUpRight,
  CheckCircle2,
  Clock,
  AlertCircle,
  FileSpreadsheet,
  X
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { BankTransaction } from '../../types';
import { formatINR, formatDate } from '../../utils/formatters';
import { exportToCSV, exportToExcel } from '../../utils/excelEngine';
import { BankStatementImportWizard } from './BankStatementImportWizard';
import { ROLE_DEFINITIONS } from '../../utils/rbac';

export const BankStatementView: React.FC = () => {
  const { bankTransactions, addBankTransaction, importBankTransactionsBatch, customers, currentUser } = useApp();

  const [searchTerm, setSearchTerm] = useState('');
  const [allocationFilter, setAllocationFilter] = useState('All');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);

  const rolePerms = ROLE_DEFINITIONS[currentUser.role];
  const canUpload = rolePerms?.canUploadBankStatements ?? false;
  const canCreate = rolePerms?.canCreateBankEntries ?? false;

  const filteredTransactions = useMemo(() => {
    return bankTransactions.filter(t => {
      const matchSearch =
        t.narration.toLowerCase().includes(searchTerm.toLowerCase()) ||
        t.referenceNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (t.customerName && t.customerName.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (t.extractedInvoiceNumber && t.extractedInvoiceNumber.toLowerCase().includes(searchTerm.toLowerCase()));

      const matchStatus = allocationFilter === 'All' || t.allocationStatus === allocationFilter;
      return matchSearch && matchStatus;
    });
  }, [bankTransactions, searchTerm, allocationFilter]);

  const handleExport = (type: 'csv' | 'excel') => {
    const exportData = filteredTransactions.map(t => ({
      'Date': t.transactionDate,
      'Value Date': t.valueDate,
      'Narration': t.narration,
      'Reference / UTR': t.referenceNumber,
      'Type': t.isCredit ? 'Credit (Deposit)' : 'Debit (Withdrawal)',
      'Amount': t.amount,
      'Bank': t.bankAccount,
      'Extracted Customer': t.customerName || 'N/A',
      'Extracted Inv No': t.extractedInvoiceNumber || 'N/A',
      'Allocated': t.allocatedAmount,
      'Unallocated': t.unallocatedAmount,
      'Status': t.allocationStatus
    }));

    if (type === 'csv') {
      exportToCSV(exportData, 'Bank_Statement_FinRecon');
    } else {
      exportToExcel(exportData, 'Bank_Statement_FinRecon', 'Bank Statement');
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Bank Statements & Collections</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            NEFT, RTGS, IMPS, and UPI bank credits, narration parsing, and invoice allocation statuses.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`hidden sm:inline-flex px-2.5 py-1 text-[11px] font-bold rounded-lg border ${rolePerms.badgeClass}`}>
            {currentUser.role}
          </span>
          <button
            onClick={() => handleExport('excel')}
            className="px-3 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200/80 rounded-lg transition-colors flex items-center gap-1.5"
            title="Export to Excel"
          >
            <Download className="w-4 h-4 text-slate-500" />
            <span>Export</span>
          </button>
          {canUpload && (
            <button
              onClick={() => setIsImportModalOpen(true)}
              className="px-3 py-2 text-xs font-semibold text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 rounded-lg transition-colors flex items-center gap-1.5"
            >
              <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
              <span>Upload Statement (Excel, CSV, PDF)</span>
            </button>
          )}
          {canCreate && (
            <button
              onClick={() => setIsAddModalOpen(true)}
              className="px-3.5 py-2 text-xs font-bold text-white bg-emerald-700 hover:bg-emerald-800 rounded-lg transition-colors flex items-center gap-1.5 shadow-xs"
            >
              <Plus className="w-4 h-4" />
              <span>Record Bank Entry</span>
            </button>
          )}
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center gap-3 bg-white p-4 rounded-xl border border-slate-200">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search by narration, UTR reference number, customer, or invoice..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs rounded-lg border border-slate-200 focus:outline-hidden focus:border-emerald-600 bg-slate-50/50"
          />
        </div>
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <label className="text-xs font-medium text-slate-500 whitespace-nowrap">Allocation:</label>
          <select
            value={allocationFilter}
            onChange={(e) => setAllocationFilter(e.target.value)}
            className="text-xs rounded-lg border border-slate-200 py-2 px-3 bg-slate-50/50 text-slate-700"
          >
            <option value="All">All Transactions</option>
            <option value="Unallocated">Unallocated (Action Needed)</option>
            <option value="Partially Allocated">Partially Allocated</option>
            <option value="Fully Allocated">Fully Allocated</option>
          </select>
        </div>
      </div>

      {/* Bank Statement Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-[10px] uppercase font-bold text-slate-500 tracking-wider">
              <tr>
                <th className="p-3.5">Date & Bank</th>
                <th className="p-3.5">Narration & UTR Reference</th>
                <th className="p-3.5">Extracted Entity</th>
                <th className="p-3.5 text-right">Amount (₹)</th>
                <th className="p-3.5 text-right">Unallocated</th>
                <th className="p-3.5">Allocation Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {filteredTransactions.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-slate-400">
                    No bank transactions found.
                  </td>
                </tr>
              ) : (
                filteredTransactions.map((tx) => (
                  <tr key={tx.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="p-3.5">
                      <span className="font-semibold text-slate-800 block">{formatDate(tx.transactionDate)}</span>
                      <span className="text-[10px] text-slate-400 font-mono">{tx.bankAccount}</span>
                    </td>

                    <td className="p-3.5 max-w-sm">
                      <p className="font-mono text-xs font-semibold text-slate-900 break-words">{tx.narration}</p>
                      <div className="text-[10px] text-slate-400 mt-0.5">
                        Ref / UTR: <span className="font-mono text-slate-600 font-medium">{tx.referenceNumber || 'N/A'}</span>
                      </div>
                    </td>

                    <td className="p-3.5">
                      {tx.customerName ? (
                        <div>
                          <span className="font-bold text-slate-800 block">{tx.customerName}</span>
                          {tx.extractedInvoiceNumber && (
                            <span className="inline-block px-1.5 py-0.2 rounded text-[10px] font-mono font-bold bg-blue-50 text-blue-800 border border-blue-200">
                              Inv #{tx.extractedInvoiceNumber}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-[11px] text-slate-400 italic">No customer tagged</span>
                      )}
                    </td>

                    <td className="p-3.5 text-right">
                      <span className={`font-mono font-bold text-xs ${tx.isCredit ? 'text-emerald-700' : 'text-slate-900'}`}>
                        {tx.isCredit ? '+' : '-'} {formatINR(tx.amount, false)}
                      </span>
                      <span className="block text-[10px] text-slate-400 font-medium">
                        {tx.isCredit ? 'Credit (Deposit)' : 'Debit'}
                      </span>
                    </td>

                    <td className="p-3.5 text-right">
                      {tx.unallocatedAmount > 0 ? (
                        <span className="font-mono font-bold text-amber-700">
                          {formatINR(tx.unallocatedAmount, false)}
                        </span>
                      ) : (
                        <span className="text-slate-400 font-mono text-[11px]">₹0.00</span>
                      )}
                    </td>

                    <td className="p-3.5">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                          tx.allocationStatus === 'Fully Allocated'
                            ? 'bg-emerald-100 text-emerald-800'
                            : tx.allocationStatus === 'Partially Allocated'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-rose-100 text-rose-800'
                        }`}
                      >
                        {tx.allocationStatus}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Manual Record Transaction Modal */}
      {isAddModalOpen && (
        <CreateTransactionModal
          onClose={() => setIsAddModalOpen(false)}
          onSave={(txData) => {
            addBankTransaction(txData);
            setIsAddModalOpen(false);
          }}
        />
      )}

      {/* Bank Statement Import Wizard (CSV, Excel, PDF) */}
      {isImportModalOpen && (
        <BankStatementImportWizard
          isOpen={isImportModalOpen}
          customers={customers}
          existingTransactions={bankTransactions}
          onClose={() => setIsImportModalOpen(false)}
          onImportComplete={(imported) => {
            importBankTransactionsBatch(imported);
            setIsImportModalOpen(false);
          }}
        />
      )}
    </div>
  );
};

interface CreateTransactionModalProps {
  onClose: () => void;
  onSave: (data: Omit<BankTransaction, 'id' | 'createdAt'>) => void;
}

const CreateTransactionModal: React.FC<CreateTransactionModalProps> = ({ onClose, onSave }) => {
  const [transactionDate, setTransactionDate] = useState('2026-09-15');
  const [narration, setNarration] = useState('');
  const [referenceNumber, setReferenceNumber] = useState(`CMS${Math.floor(100000000 + Math.random() * 900000000)}`);
  const [amount, setAmount] = useState(50000);
  const [bankAccount, setBankAccount] = useState('HDFC Bank - Current A/c 50200012345678');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!narration.trim()) return;

    onSave({
      transactionDate,
      valueDate: transactionDate,
      narration: narration.trim(),
      referenceNumber: referenceNumber.trim(),
      isCredit: true,
      amount,
      debit: 0,
      credit: amount,
      type: 'Customer Receipt',
      runningBalance: 1500000,
      bankAccount,
      allocatedAmount: 0,
      unallocatedAmount: amount,
      allocationStatus: 'Unallocated',
      matchedInvoiceNumbers: []
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="bg-white w-full max-w-md rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <h3 className="font-bold text-slate-900 text-sm">Record Bank Deposit Entry</h3>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4 text-xs">
          <div>
            <label className="font-semibold text-slate-700 block mb-1">Transaction Date *</label>
            <input
              type="date"
              required
              value={transactionDate}
              onChange={e => setTransactionDate(e.target.value)}
              className="w-full p-2 rounded-lg border border-slate-200 focus:border-emerald-600 outline-hidden"
            />
          </div>

          <div>
            <label className="font-semibold text-slate-700 block mb-1">Bank Narration *</label>
            <textarea
              required
              rows={2}
              value={narration}
              onChange={e => setNarration(e.target.value)}
              placeholder="e.g. NEFT/CMS/INFOSYS/INV-2026-001/HDFC0001"
              className="w-full p-2 font-mono text-xs rounded-lg border border-slate-200 focus:border-emerald-600 outline-hidden"
            />
            <span className="text-[10px] text-slate-400 mt-0.5 block">
              Tip: Include party name or invoice number for automatic reconciliation.
            </span>
          </div>

          <div>
            <label className="font-semibold text-slate-700 block mb-1">Reference / UTR Number</label>
            <input
              type="text"
              value={referenceNumber}
              onChange={e => setReferenceNumber(e.target.value)}
              className="w-full p-2 font-mono rounded-lg border border-slate-200 focus:border-emerald-600 outline-hidden"
            />
          </div>

          <div>
            <label className="font-semibold text-slate-700 block mb-1">Deposit Amount (₹) *</label>
            <input
              type="number"
              required
              value={amount}
              onChange={e => setAmount(parseFloat(e.target.value) || 0)}
              className="w-full p-2 font-mono font-bold rounded-lg border border-slate-200 focus:border-emerald-600 outline-hidden"
            />
          </div>

          <div>
            <label className="font-semibold text-slate-700 block mb-1">Bank Account</label>
            <select
              value={bankAccount}
              onChange={e => setBankAccount(e.target.value)}
              className="w-full p-2 rounded-lg border border-slate-200 bg-white"
            >
              <option value="HDFC Bank - Current A/c 50200012345678">HDFC Bank - Current A/c 50200012345678</option>
              <option value="ICICI Bank - Current A/c 000405001234">ICICI Bank - Current A/c 000405001234</option>
              <option value="State Bank of India - CA 38291029384">State Bank of India - CA 38291029384</option>
            </select>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg font-bold shadow-xs"
            >
              Save Bank Receipt
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
