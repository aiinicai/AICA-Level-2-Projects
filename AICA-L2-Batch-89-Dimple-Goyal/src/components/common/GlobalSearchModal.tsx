import React, { useState, useMemo } from 'react';
import { Search, X, FileText, Users, Landmark, ShieldCheck, AlertOctagon, ArrowRight } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { formatINR, formatDate } from '../../utils/formatters';
import { ActiveTab } from '../layout/Sidebar';

interface GlobalSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (tab: ActiveTab, targetId?: string) => void;
}

export const GlobalSearchModal: React.FC<GlobalSearchModalProps> = ({
  isOpen,
  onClose,
  onNavigate
}) => {
  const { customers, invoices, bankTransactions, tdsRecords, exceptions } = useApp();
  const [searchTerm, setSearchTerm] = useState('');

  const results = useMemo(() => {
    if (!searchTerm || searchTerm.trim().length < 2) {
      return { invoices: [], customers: [], payments: [], tds: [], exceptions: [] };
    }
    const term = searchTerm.trim().toLowerCase();

    const matchedInvoices = invoices.filter(
      i =>
        i.invoiceNumber.toLowerCase().includes(term) ||
        i.customerName.toLowerCase().includes(term) ||
        i.customerGstin.toLowerCase().includes(term) ||
        i.customerPan.toLowerCase().includes(term)
    ).slice(0, 5);

    const matchedCustomers = customers.filter(
      c =>
        c.name.toLowerCase().includes(term) ||
        c.gstin.toLowerCase().includes(term) ||
        c.pan.toLowerCase().includes(term) ||
        c.aliases.some(a => a.toLowerCase().includes(term))
    ).slice(0, 5);

    const matchedPayments = bankTransactions.filter(
      p =>
        p.narration.toLowerCase().includes(term) ||
        p.referenceNumber.toLowerCase().includes(term) ||
        (p.customerName && p.customerName.toLowerCase().includes(term))
    ).slice(0, 5);

    const matchedTds = tdsRecords.filter(
      t =>
        t.deductorName.toLowerCase().includes(term) ||
        t.pan.toLowerCase().includes(term) ||
        t.tan.toLowerCase().includes(term) ||
        (t.matchedInvoiceNumber && t.matchedInvoiceNumber.toLowerCase().includes(term))
    ).slice(0, 5);

    const matchedExceptions = exceptions.filter(
      e =>
        e.category.toLowerCase().includes(term) ||
        e.remarks.toLowerCase().includes(term) ||
        (e.customerName && e.customerName.toLowerCase().includes(term)) ||
        (e.invoiceNumber && e.invoiceNumber.toLowerCase().includes(term))
    ).slice(0, 5);

    return {
      invoices: matchedInvoices,
      customers: matchedCustomers,
      payments: matchedPayments,
      tds: matchedTds,
      exceptions: matchedExceptions
    };
  }, [searchTerm, invoices, customers, bankTransactions, tdsRecords, exceptions]);

  if (!isOpen) return null;

  const totalResults =
    results.invoices.length +
    results.customers.length +
    results.payments.length +
    results.tds.length +
    results.exceptions.length;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-16 px-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white w-full max-w-2xl rounded-xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[80vh]">
        {/* Search Input Bar */}
        <div className="p-4 border-b border-slate-200 flex items-center gap-3">
          <Search className="w-5 h-5 text-emerald-600 shrink-0" />
          <input
            type="text"
            autoFocus
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search invoice number (e.g. INV-2026-001), customer, UTR, PAN, GSTIN..."
            className="flex-1 text-sm bg-transparent outline-hidden text-slate-800 placeholder:text-slate-400"
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm('')}
              className="p-1 text-slate-400 hover:text-slate-600 rounded"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={onClose}
            className="text-xs px-2 py-1 rounded bg-slate-100 text-slate-600 hover:bg-slate-200 font-medium"
          >
            Esc
          </button>
        </div>

        {/* Results Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
          {searchTerm.length < 2 && (
            <div className="text-center py-8 text-slate-400">
              <Search className="w-8 h-8 mx-auto mb-2 text-slate-300" />
              <p className="font-medium text-slate-600">Global Financial Search</p>
              <p className="text-xs text-slate-400 max-w-xs mx-auto mt-1">
                Type an invoice number, party name, GSTIN, PAN, bank reference, or exception code.
              </p>
            </div>
          )}

          {searchTerm.length >= 2 && totalResults === 0 && (
            <div className="text-center py-8 text-slate-500">
              <p className="font-semibold text-slate-700">No records found for "{searchTerm}"</p>
              <p className="text-xs text-slate-400 mt-1">Try searching by partial invoice number or party name.</p>
            </div>
          )}

          {/* Invoices */}
          {results.invoices.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 text-slate-400 font-bold uppercase text-[10px] tracking-wider mb-2">
                <FileText className="w-3.5 h-3.5 text-emerald-600" />
                <span>Invoices ({results.invoices.length})</span>
              </div>
              <div className="space-y-1.5">
                {results.invoices.map((inv) => (
                  <div
                    key={inv.id}
                    onClick={() => {
                      onNavigate('invoices');
                      onClose();
                    }}
                    className="p-2.5 rounded-lg border border-slate-200 hover:border-emerald-300 hover:bg-emerald-50/40 cursor-pointer flex items-center justify-between transition-colors"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-slate-900">{inv.invoiceNumber}</span>
                        <span className="text-slate-400">•</span>
                        <span className="font-medium text-slate-700">{inv.customerName}</span>
                      </div>
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        Dated {formatDate(inv.invoiceDate)} • Balance: <span className="font-semibold text-slate-800">{formatINR(inv.balance)}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        inv.status === 'Fully Paid' ? 'bg-emerald-100 text-emerald-800' :
                        inv.status === 'Overdue' ? 'bg-rose-100 text-rose-800' : 'bg-amber-100 text-amber-800'
                      }`}>
                        {inv.status}
                      </span>
                      <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Customers */}
          {results.customers.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 text-slate-400 font-bold uppercase text-[10px] tracking-wider mb-2">
                <Users className="w-3.5 h-3.5 text-blue-600" />
                <span>Customers ({results.customers.length})</span>
              </div>
              <div className="space-y-1.5">
                {results.customers.map((c) => (
                  <div
                    key={c.id}
                    onClick={() => {
                      onNavigate('customers', c.id);
                      onClose();
                    }}
                    className="p-2.5 rounded-lg border border-slate-200 hover:border-blue-300 hover:bg-blue-50/40 cursor-pointer flex items-center justify-between transition-colors"
                  >
                    <div>
                      <span className="font-bold text-slate-900">{c.name}</span>
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        GSTIN: <span className="font-mono">{c.gstin}</span> • State: {c.state} • Terms: {c.paymentTerms} Days
                      </div>
                    </div>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Bank Receipts */}
          {results.payments.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 text-slate-400 font-bold uppercase text-[10px] tracking-wider mb-2">
                <Landmark className="w-3.5 h-3.5 text-purple-600" />
                <span>Bank Transactions ({results.payments.length})</span>
              </div>
              <div className="space-y-1.5">
                {results.payments.map((p) => (
                  <div
                    key={p.id}
                    onClick={() => {
                      onNavigate('payments');
                      onClose();
                    }}
                    className="p-2.5 rounded-lg border border-slate-200 hover:border-purple-300 hover:bg-purple-50/40 cursor-pointer flex items-center justify-between transition-colors"
                  >
                    <div className="truncate max-w-md">
                      <div className="font-mono text-xs font-semibold text-slate-900 truncate">
                        {p.narration}
                      </div>
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        Ref: <span className="font-mono">{p.referenceNumber || 'N/A'}</span> • Dated {formatDate(p.transactionDate)}
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <span className="font-bold text-emerald-700">{formatINR(p.amount)}</span>
                      <div className="text-[10px] text-slate-500">{p.allocationStatus}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TDS / 26AS */}
          {results.tds.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 text-slate-400 font-bold uppercase text-[10px] tracking-wider mb-2">
                <ShieldCheck className="w-3.5 h-3.5 text-amber-600" />
                <span>TDS 26AS Records ({results.tds.length})</span>
              </div>
              <div className="space-y-1.5">
                {results.tds.map((t) => (
                  <div
                    key={t.id}
                    onClick={() => {
                      onNavigate('tds');
                      onClose();
                    }}
                    className="p-2.5 rounded-lg border border-slate-200 hover:border-amber-300 hover:bg-amber-50/40 cursor-pointer flex items-center justify-between transition-colors"
                  >
                    <div>
                      <div className="font-semibold text-slate-900">{t.deductorName}</div>
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        Sec {t.section} • PAN: {t.pan} • Matched Inv: {t.matchedInvoiceNumber || 'Unmatched'}
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="font-bold text-slate-900">{formatINR(t.tdsDeposited)}</span>
                      <div className={`text-[10px] font-bold ${t.status === 'Matched' ? 'text-emerald-600' : 'text-rose-600'}`}>
                        {t.status}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Exceptions */}
          {results.exceptions.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 text-slate-400 font-bold uppercase text-[10px] tracking-wider mb-2">
                <AlertOctagon className="w-3.5 h-3.5 text-rose-600" />
                <span>Exceptions ({results.exceptions.length})</span>
              </div>
              <div className="space-y-1.5">
                {results.exceptions.map((e) => (
                  <div
                    key={e.id}
                    onClick={() => {
                      onNavigate('exceptions');
                      onClose();
                    }}
                    className="p-2.5 rounded-lg border border-rose-200 hover:bg-rose-50/40 cursor-pointer flex items-center justify-between transition-colors"
                  >
                    <div>
                      <div className="font-semibold text-slate-900">{e.category} - {e.customerName || 'Direct Txn'}</div>
                      <div className="text-[11px] text-slate-500 mt-0.5 truncate max-w-sm">
                        {e.remarks}
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="font-bold text-rose-700">{formatINR(e.amount)}</span>
                      <div className="text-[10px] font-bold text-rose-600">{e.status}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
