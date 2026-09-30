import React, { useState } from 'react';
import { X, Building2, Mail, Phone, MapPin, FileText, Landmark, Clock, ShieldCheck, Scale, AlertCircle } from 'lucide-react';
import { Customer, Invoice, BankTransaction, PaymentAllocation, TDS26ASRecord } from '../../types';
import { formatINR, formatDate } from '../../utils/formatters';
import { calculateOverdueDays } from '../../utils/ageingEngine';

interface Customer360ModalProps {
  customer: Customer | null;
  invoices: Invoice[];
  bankTransactions: BankTransaction[];
  allocations: PaymentAllocation[];
  tdsRecords: TDS26ASRecord[];
  onClose: () => void;
}

export const Customer360Modal: React.FC<Customer360ModalProps> = ({
  customer,
  invoices,
  bankTransactions,
  allocations,
  tdsRecords,
  onClose
}) => {
  const [activeTab, setActiveTab] = useState<'summary' | 'invoices' | 'payments' | 'ageing' | 'tds'>('summary');

  if (!customer) return null;

  // Customer specific items
  const custInvoices = invoices.filter(i => i.customerId === customer.id);
  const custPayments = bankTransactions.filter(p => p.customerId === customer.id);
  const custAllocations = allocations.filter(a => a.customerId === customer.id);
  const custTds = tdsRecords.filter(t => t.customerId === customer.id);

  const totalSales = custInvoices.reduce((s, i) => s + (i.status !== 'Cancelled' ? i.totalInvoiceValue : 0), 0);
  const totalReceived = custInvoices.reduce((s, i) => s + i.amountReceived, 0);
  const totalOutstanding = custInvoices.reduce((s, i) => s + (i.balance > 0 ? i.balance : 0), 0);
  const totalOverdue = custInvoices.filter(i => i.status === 'Overdue').reduce((s, i) => s + i.balance, 0);
  const totalTdsExpected = custInvoices.reduce((s, i) => s + i.expectedTds, 0);
  const totalTdsDeposited = custTds.reduce((s, t) => s + t.tdsDeposited, 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white w-full max-w-4xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-5 border-b border-slate-200 bg-slate-50 flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-slate-900 text-white flex items-center justify-center font-bold text-xl shadow-xs">
              {customer.name.charAt(0)}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-slate-900">{customer.name}</h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                  {customer.customerType}
                </span>
                <span className="text-xs font-mono font-semibold text-slate-500">{customer.customerId}</span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">{customer.legalName}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 px-5 bg-white text-xs font-semibold gap-4">
          {[
            { id: 'summary', label: 'Customer 360 Summary' },
            { id: 'invoices', label: `Invoices (${custInvoices.length})` },
            { id: 'payments', label: `Bank Receipts (${custPayments.length})` },
            { id: 'ageing', label: 'Ageing Analysis' },
            { id: 'tds', label: `TDS 26AS (${custTds.length})` }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-3 border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-emerald-600 text-emerald-700 font-bold'
                  : 'border-transparent text-slate-500 hover:text-slate-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Body Content */}
        <div className="p-5 overflow-y-auto flex-1 text-xs space-y-5">
          {activeTab === 'summary' && (
            <div className="space-y-5">
              {/* Top Financial Highlights */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="text-slate-400 text-[10px] font-bold uppercase">Total Billed</span>
                  <div className="text-base font-bold text-slate-900 mt-0.5">{formatINR(totalSales)}</div>
                </div>
                <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-200">
                  <span className="text-emerald-700 text-[10px] font-bold uppercase">Collections</span>
                  <div className="text-base font-bold text-emerald-900 mt-0.5">{formatINR(totalReceived)}</div>
                </div>
                <div className="p-3 bg-amber-50 rounded-xl border border-amber-200">
                  <span className="text-amber-700 text-[10px] font-bold uppercase">Outstanding</span>
                  <div className="text-base font-bold text-amber-900 mt-0.5">{formatINR(totalOutstanding)}</div>
                </div>
                <div className="p-3 bg-rose-50 rounded-xl border border-rose-200">
                  <span className="text-rose-700 text-[10px] font-bold uppercase">Overdue</span>
                  <div className="text-base font-bold text-rose-900 mt-0.5">{formatINR(totalOverdue)}</div>
                </div>
              </div>

              {/* Master Details & Tax Profile */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-white rounded-xl border border-slate-200 space-y-2">
                  <h4 className="font-bold text-slate-900 mb-2 flex items-center gap-1.5 text-xs">
                    <Building2 className="w-4 h-4 text-slate-500" />
                    <span>Company & Tax Master</span>
                  </h4>
                  <div className="grid grid-cols-2 gap-2 text-slate-600">
                    <div>
                      <span className="text-slate-400 text-[10px] block">GSTIN</span>
                      <span className="font-mono font-bold text-slate-800">{customer.gstin}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 text-[10px] block">PAN</span>
                      <span className="font-mono font-bold text-slate-800">{customer.pan}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 text-[10px] block">Payment Terms</span>
                      <span className="font-semibold text-slate-800">{customer.paymentTerms} Days</span>
                    </div>
                    <div>
                      <span className="text-slate-400 text-[10px] block">Credit Limit</span>
                      <span className="font-semibold text-slate-800">{formatINR(customer.creditLimit, false)}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 text-[10px] block">TDS Section</span>
                      <span className="font-semibold text-slate-800">{customer.tdsApplicable ? `${customer.tdsSection} (${customer.tdsRate}%)` : 'Not Applicable'}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 text-[10px] block">State</span>
                      <span className="font-semibold text-slate-800">{customer.state}</span>
                    </div>
                  </div>
                </div>

                <div className="p-4 bg-white rounded-xl border border-slate-200 space-y-2">
                  <h4 className="font-bold text-slate-900 mb-2 flex items-center gap-1.5 text-xs">
                    <Mail className="w-4 h-4 text-slate-500" />
                    <span>Contact & Known Aliases</span>
                  </h4>
                  <div className="space-y-1.5 text-slate-600">
                    <p className="flex items-center gap-2">
                      <span className="text-slate-400 text-[10px] w-20">Contact:</span>
                      <strong className="text-slate-800">{customer.contactPerson}</strong>
                    </p>
                    <p className="flex items-center gap-2">
                      <span className="text-slate-400 text-[10px] w-20">Email:</span>
                      <span className="text-slate-800">{customer.email}</span>
                    </p>
                    <p className="flex items-center gap-2">
                      <span className="text-slate-400 text-[10px] w-20">Phone:</span>
                      <span className="text-slate-800">{customer.phone}</span>
                    </p>
                    <div className="pt-2">
                      <span className="text-slate-400 text-[10px] block mb-1">Bank Narration Aliases:</span>
                      <div className="flex flex-wrap gap-1">
                        {customer.aliases.map((alias, i) => (
                          <span key={i} className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded text-[10px] font-mono">
                            {alias}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'invoices' && (
            <div className="border border-slate-200 rounded-xl overflow-hidden">
              <table className="w-full text-left">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 text-[10px] uppercase font-bold">
                  <tr>
                    <th className="p-3">Invoice No</th>
                    <th className="p-3">Date</th>
                    <th className="p-3">Due Date</th>
                    <th className="p-3 text-right">Total</th>
                    <th className="p-3 text-right">TDS Exp</th>
                    <th className="p-3 text-right">Received</th>
                    <th className="p-3 text-right">Balance</th>
                    <th className="p-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {custInvoices.map((inv) => (
                    <tr key={inv.id} className="hover:bg-slate-50">
                      <td className="p-3 font-mono font-bold text-slate-900">{inv.invoiceNumber}</td>
                      <td className="p-3 text-slate-600">{formatDate(inv.invoiceDate)}</td>
                      <td className="p-3 text-slate-600">{formatDate(inv.dueDate)}</td>
                      <td className="p-3 text-right font-mono font-semibold">{formatINR(inv.totalInvoiceValue)}</td>
                      <td className="p-3 text-right font-mono text-slate-500">{formatINR(inv.expectedTds)}</td>
                      <td className="p-3 text-right font-mono text-emerald-700 font-semibold">{formatINR(inv.amountReceived)}</td>
                      <td className="p-3 text-right font-mono font-bold text-slate-900">{formatINR(inv.balance)}</td>
                      <td className="p-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          inv.status === 'Fully Paid' ? 'bg-emerald-100 text-emerald-800' :
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
          )}

          {activeTab === 'payments' && (
            <div className="border border-slate-200 rounded-xl overflow-hidden">
              <table className="w-full text-left">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 text-[10px] uppercase font-bold">
                  <tr>
                    <th className="p-3">Date</th>
                    <th className="p-3">Narration / UTR</th>
                    <th className="p-3">Bank A/c</th>
                    <th className="p-3 text-right">Amount</th>
                    <th className="p-3 text-right">Allocated</th>
                    <th className="p-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {custPayments.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="p-6 text-center text-slate-400">No bank deposits tagged to this customer yet.</td>
                    </tr>
                  ) : (
                    custPayments.map((p) => (
                      <tr key={p.id} className="hover:bg-slate-50">
                        <td className="p-3 text-slate-600">{formatDate(p.transactionDate)}</td>
                        <td className="p-3">
                          <p className="font-mono font-semibold text-slate-900">{p.narration}</p>
                          <p className="text-[10px] text-slate-400">Ref: {p.referenceNumber}</p>
                        </td>
                        <td className="p-3 text-slate-600">{p.bankAccount}</td>
                        <td className="p-3 text-right font-mono font-bold text-emerald-700">{formatINR(p.amount)}</td>
                        <td className="p-3 text-right font-mono text-slate-700">{formatINR(p.allocatedAmount)}</td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                            {p.allocationStatus}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === 'ageing' && (
            <div className="space-y-4">
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
                <h4 className="font-bold text-slate-900 mb-1">Overdue Aging Summary for {customer.name}</h4>
                <p className="text-slate-500 text-xs">Standard credit terms: {customer.paymentTerms} days from invoice date.</p>
              </div>

              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <table className="w-full text-left">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 text-[10px] uppercase font-bold">
                    <tr>
                      <th className="p-3">Invoice</th>
                      <th className="p-3">Due Date</th>
                      <th className="p-3">Days Overdue</th>
                      <th className="p-3 text-right">Invoice Total</th>
                      <th className="p-3 text-right">Outstanding</th>
                      <th className="p-3">Bucket</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {custInvoices.filter(i => i.balance > 0).map(inv => {
                      const od = calculateOverdueDays(inv.dueDate);
                      return (
                        <tr key={inv.id} className="hover:bg-slate-50">
                          <td className="p-3 font-mono font-bold text-slate-900">{inv.invoiceNumber}</td>
                          <td className="p-3 text-slate-600">{formatDate(inv.dueDate)}</td>
                          <td className="p-3">
                            {od <= 0 ? (
                              <span className="text-emerald-600 font-semibold">Not Due yet ({Math.abs(od)}d left)</span>
                            ) : (
                              <span className="text-rose-600 font-bold">{od} days overdue</span>
                            )}
                          </td>
                          <td className="p-3 text-right font-mono">{formatINR(inv.totalInvoiceValue)}</td>
                          <td className="p-3 text-right font-mono font-bold text-slate-900">{formatINR(inv.balance)}</td>
                          <td className="p-3">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              od <= 0 ? 'bg-emerald-100 text-emerald-800' :
                              od <= 30 ? 'bg-amber-100 text-amber-800' :
                              od <= 90 ? 'bg-orange-100 text-orange-800' : 'bg-rose-100 text-rose-800'
                            }`}>
                              {od <= 0 ? 'Not Due' : od <= 30 ? '0-30 Days' : od <= 60 ? '31-60 Days' : od <= 90 ? '61-90 Days' : '> 90 Days'}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'tds' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-purple-50 rounded-xl border border-purple-200">
                <div>
                  <h4 className="font-bold text-purple-950">Form 26AS Deductions: {customer.name}</h4>
                  <p className="text-xs text-purple-700">PAN: {customer.pan} • Expected TDS Rate: {customer.tdsRate || 2}%</p>
                </div>
                <div className="text-right">
                  <span className="text-xs text-purple-600 font-medium">Deposited in 26AS:</span>
                  <div className="text-base font-bold text-purple-900">{formatINR(totalTdsDeposited)}</div>
                </div>
              </div>

              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <table className="w-full text-left">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 text-[10px] uppercase font-bold">
                    <tr>
                      <th className="p-3">TAN</th>
                      <th className="p-3">Section</th>
                      <th className="p-3">Date</th>
                      <th className="p-3 text-right">Gross Credited</th>
                      <th className="p-3 text-right">TDS Deposited</th>
                      <th className="p-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {custTds.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="p-6 text-center text-slate-400">No 26AS entries loaded for this deductor yet.</td>
                      </tr>
                    ) : (
                      custTds.map((t) => (
                        <tr key={t.id} className="hover:bg-slate-50">
                          <td className="p-3 font-mono font-bold text-slate-900">{t.tan}</td>
                          <td className="p-3 text-slate-700 font-semibold">{t.section}</td>
                          <td className="p-3 text-slate-600">{formatDate(t.transactionDate)}</td>
                          <td className="p-3 text-right font-mono">{formatINR(t.amountPaidCredited)}</td>
                          <td className="p-3 text-right font-mono font-bold text-purple-700">{formatINR(t.tdsDeposited)}</td>
                          <td className="p-3">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              t.status === 'Matched' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                            }`}>
                              {t.status}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
