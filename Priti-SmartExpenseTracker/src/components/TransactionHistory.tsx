import React, { useState, useMemo } from 'react';
import {
  Search,
  Filter,
  Download,
  Calendar,
  Sparkles,
  Edit2,
  Trash2,
  ChevronDown,
  ChevronUp,
  FileSpreadsheet,
  Layers,
  ArrowUpDown,
  Tag,
  PenTool,
  CheckCircle2,
} from 'lucide-react';
import { Transaction, TransactionCategory, PaymentMode, TransactionSource } from '../types';
import { CategoryIcon, CATEGORY_CONFIG } from './CategoryIcon';
import { formatINR, formatDate, exportTransactionsToCSV } from '../utils/formatters';

interface TransactionHistoryProps {
  transactions: Transaction[];
  onEdit: (transaction: Transaction) => void;
  onDelete: (id: string) => void;
  onOpenScanModal: () => void;
  onOpenManualModal: () => void;
}

export const TransactionHistory: React.FC<TransactionHistoryProps> = ({
  transactions,
  onEdit,
  onDelete,
  onOpenScanModal,
  onOpenManualModal,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [selectedSource, setSelectedSource] = useState<string>('ALL');
  const [selectedPaymentMode, setSelectedPaymentMode] = useState<string>('ALL');
  const [sortBy, setSortBy] = useState<'date-desc' | 'date-asc' | 'amount-desc' | 'amount-asc'>('date-desc');
  const [expandedTxId, setExpandedTxId] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  // Filter and sort transactions
  const filteredTransactions = useMemo(() => {
    return transactions
      .filter((t) => {
        // Search query
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const matchMerchant = (t.merchantName || '').toLowerCase().includes(q);
          const matchDesc = (t.description || '').toLowerCase().includes(q);
          const matchCategory = t.category.toLowerCase().includes(q);
          const matchAmount = t.amount.toString().includes(q);
          const matchLineItem = t.lineItems?.some((li) => li.item.toLowerCase().includes(q));
          if (!matchMerchant && !matchDesc && !matchCategory && !matchAmount && !matchLineItem) {
            return false;
          }
        }

        // Category filter
        if (selectedCategory !== 'ALL' && t.category !== selectedCategory) {
          return false;
        }

        // Source filter: manual vs image
        if (selectedSource !== 'ALL' && t.source !== selectedSource) {
          return false;
        }

        // Payment mode filter
        if (selectedPaymentMode !== 'ALL' && t.paymentMode !== selectedPaymentMode) {
          return false;
        }

        return true;
      })
      .sort((a, b) => {
        if (sortBy === 'date-desc') return new Date(b.date).getTime() - new Date(a.date).getTime();
        if (sortBy === 'date-asc') return new Date(a.date).getTime() - new Date(b.date).getTime();
        if (sortBy === 'amount-desc') return b.amount - a.amount;
        if (sortBy === 'amount-asc') return a.amount - b.amount;
        return 0;
      });
  }, [transactions, searchQuery, selectedCategory, selectedSource, selectedPaymentMode, sortBy]);

  const totalFilteredAmount = filteredTransactions.reduce((acc, t) => acc + t.amount, 0);

  const handleExportCSV = () => {
    exportTransactionsToCSV(filteredTransactions);
  };

  return (
    <div className="space-y-6 pb-24">
      {/* Top Header & Search Bar */}
      <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <span>Transaction History</span>
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                {filteredTransactions.length} of {transactions.length}
              </span>
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Search, filter, edit, or export receipts and records
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={handleExportCSV}
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700/60 text-slate-700 dark:text-slate-200 text-xs font-semibold transition active:scale-95 cursor-pointer shadow-xs"
              title="Export filtered transactions to CSV spreadsheet"
            >
              <FileSpreadsheet className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              <span>Export CSV</span>
            </button>
          </div>
        </div>

        {/* Search Input */}
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by merchant, description, category, or amount..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-hidden focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition"
          />
        </div>

        {/* Filter Pills and Dropdowns */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-1">
          {/* Category Filter */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1">
              Category
            </label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full text-xs font-medium py-2 px-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-hidden cursor-pointer"
            >
              <option value="ALL">All Categories</option>
              {Object.keys(CATEGORY_CONFIG).map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          {/* Source Filter (Manual vs Image Scan) */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1">
              Source
            </label>
            <select
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
              className="w-full text-xs font-medium py-2 px-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-hidden cursor-pointer"
            >
              <option value="ALL">All Sources</option>
              <option value="image">Invoice Scan (AI)</option>
              <option value="manual">Manual Entry</option>
            </select>
          </div>

          {/* Payment Mode Filter */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1">
              Payment Mode
            </label>
            <select
              value={selectedPaymentMode}
              onChange={(e) => setSelectedPaymentMode(e.target.value)}
              className="w-full text-xs font-medium py-2 px-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-hidden cursor-pointer"
            >
              <option value="ALL">All Modes</option>
              <option value="UPI">UPI</option>
              <option value="Card">Card</option>
              <option value="Cash">Cash</option>
              <option value="Bank Transfer">Bank Transfer</option>
            </select>
          </div>

          {/* Sort By */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1">
              Sort By
            </label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="w-full text-xs font-medium py-2 px-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-hidden cursor-pointer"
            >
              <option value="date-desc">Date (Newest First)</option>
              <option value="date-asc">Date (Oldest First)</option>
              <option value="amount-desc">Amount (High to Low)</option>
              <option value="amount-asc">Amount (Low to High)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Filter Summary & Total */}
      <div className="flex items-center justify-between px-2 text-xs text-slate-500 dark:text-slate-400">
        <span>
          Showing <strong className="text-slate-900 dark:text-white">{filteredTransactions.length}</strong> items
        </span>
        <span>
          Subtotal:{' '}
          <strong className="text-emerald-700 dark:text-emerald-400 text-sm">
            {formatINR(totalFilteredAmount)}
          </strong>
        </span>
      </div>

      {/* Transaction List */}
      {filteredTransactions.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-3">
          <div className="mx-auto w-12 h-12 rounded-2xl bg-slate-100 dark:bg-slate-800 text-slate-400 flex items-center justify-center">
            <Search className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">
            No transactions match your filters
          </h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Try adjusting your search keywords, clear category filters, or log a new transaction.
          </p>
          <div className="pt-2 flex justify-center gap-3">
            <button
              onClick={onOpenScanModal}
              className="px-4 py-2 rounded-xl bg-emerald-600 text-white text-xs font-semibold shadow-xs hover:bg-emerald-700 transition"
            >
              Scan Receipt
            </button>
            <button
              onClick={onOpenManualModal}
              className="px-4 py-2 rounded-xl border border-slate-200 text-slate-700 dark:text-slate-300 text-xs font-semibold hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            >
              Add Manually
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredTransactions.map((tx) => {
            const isExpanded = expandedTxId === tx.id;
            const isDeleting = deleteConfirmId === tx.id;
            const hasLineItems = tx.lineItems && tx.lineItems.length > 0;

            return (
              <div
                key={tx.id}
                className="group rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 shadow-xs hover:border-emerald-300 dark:hover:border-emerald-800 transition"
              >
                <div className="flex items-start sm:items-center justify-between gap-3">
                  {/* Left: Category Icon & Details */}
                  <div className="flex items-start sm:items-center gap-3.5 min-w-0">
                    <CategoryIcon category={tx.category} />

                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-bold text-slate-900 dark:text-white text-sm truncate">
                          {tx.merchantName || tx.description}
                        </span>

                        {/* Source Tag Badge (Image Scan vs Manual Entry) */}
                        {tx.source === 'image' ? (
                          <span
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900/60"
                            title="Created via AI Invoice Scan"
                          >
                            <Sparkles className="w-3 h-3" />
                            <span>Scan</span>
                          </span>
                        ) : (
                          <span
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700"
                            title="Created via Manual Entry"
                          >
                            <PenTool className="w-2.5 h-2.5" />
                            <span>Manual</span>
                          </span>
                        )}

                        {/* Payment Mode Badge */}
                        <span className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                          {tx.paymentMode}
                        </span>
                      </div>

                      <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400 mt-1">
                        <span>{formatDate(tx.date)}</span>
                        <span>•</span>
                        <span className="truncate">{tx.description}</span>
                        {hasLineItems && (
                          <>
                            <span>•</span>
                            <button
                              onClick={() => setExpandedTxId(isExpanded ? null : tx.id)}
                              className="text-emerald-600 hover:text-emerald-700 font-semibold inline-flex items-center gap-0.5 cursor-pointer"
                            >
                              <span>{tx.lineItems?.length} items</span>
                              {isExpanded ? (
                                <ChevronUp className="w-3 h-3" />
                              ) : (
                                <ChevronDown className="w-3 h-3" />
                              )}
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Right: Amount & Actions */}
                  <div className="flex items-center gap-3 shrink-0">
                    <div className="text-right">
                      <div
                        className={`text-base font-extrabold ${
                          tx.category === 'Investment'
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : 'text-slate-900 dark:text-white'
                        }`}
                      >
                        {formatINR(tx.amount)}
                      </div>
                      <span className="text-[10px] text-slate-400 font-medium">
                        {tx.category}
                      </span>
                    </div>

                    {/* Action buttons */}
                    <div className="flex items-center gap-1 pl-2">
                      <button
                        onClick={() => onEdit(tx)}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-emerald-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition cursor-pointer"
                        title="Edit transaction"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>

                      {isDeleting ? (
                        <div className="flex items-center gap-1 bg-rose-50 dark:bg-rose-950/60 p-1 rounded-lg">
                          <button
                            onClick={() => {
                              onDelete(tx.id);
                              setDeleteConfirmId(null);
                            }}
                            className="text-[11px] font-bold text-rose-600 hover:text-rose-700 px-2 py-0.5 cursor-pointer"
                          >
                            Delete?
                          </button>
                          <button
                            onClick={() => setDeleteConfirmId(null)}
                            className="text-[11px] text-slate-400 px-1 cursor-pointer"
                          >
                            ✕
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setDeleteConfirmId(tx.id)}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition cursor-pointer"
                          title="Delete transaction"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>

                {/* Line Items Accordion for Multi-item Invoices */}
                {isExpanded && hasLineItems && (
                  <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800 pl-12 pr-4 space-y-1.5 animate-in slide-in-from-top-1">
                    <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1">
                      Scanned Item Breakdown:
                    </p>
                    {tx.lineItems?.map((item, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between text-xs py-1 px-2.5 rounded-md bg-slate-50 dark:bg-slate-800/50"
                      >
                        <span className="text-slate-700 dark:text-slate-300 font-medium">
                          {item.item}
                        </span>
                        <span className="font-semibold text-slate-900 dark:text-white">
                          {formatINR(item.amount)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
