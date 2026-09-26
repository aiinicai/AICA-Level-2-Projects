import React, { useState } from 'react';
import {
  Receipt,
  Plus,
  Sparkles,
  Search,
  CheckCircle2,
  Clock,
  AlertCircle,
  Eye,
  FileSpreadsheet,
  Building,
  ShieldCheck,
  FileCheck,
  ExternalLink,
  ChevronRight,
} from 'lucide-react';
import { Customer, SalesInvoice, StockItem, SystemSettings } from '../../types';
import { formatINR, formatLakhs } from '../../services/accountingEngine';

interface SalesViewProps {
  salesInvoices: SalesInvoice[];
  customers: Customer[];
  stockItems: StockItem[];
  settings: SystemSettings;
  onPostInvoice: (invoice: SalesInvoice) => void;
  onApproveReviewQueue: (invoiceId: string) => void;
  onOpenUpload: () => void;
}

export const SalesView: React.FC<SalesViewProps> = ({
  salesInvoices,
  customers,
  stockItems,
  settings,
  onPostInvoice,
  onApproveReviewQueue,
  onOpenUpload,
}) => {
  const [activeTab, setActiveTab] = useState<'invoices' | 'review_queue' | 'customers' | 'orders_returns' | 'debtors_ledger'>('invoices');
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedInvoiceForDetail, setSelectedInvoiceForDetail] = useState<SalesInvoice | null>(null);

  // New Invoice form state
  const [newInvCustomer, setNewInvCustomer] = useState(customers[0]?.id || '');
  const [newInvSku, setNewInvSku] = useState(stockItems[0]?.id || '');
  const [newInvQty, setNewInvQty] = useState(10);
  const [newInvRate, setNewInvRate] = useState(22000);

  const reviewQueueItems = salesInvoices.filter((i) => i.status === 'REVIEW_QUEUE');
  const activeInvoices = salesInvoices.filter((i) => i.status !== 'REVIEW_QUEUE');

  const filteredInvoices = activeInvoices.filter(
    (inv) =>
      inv.invoiceNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inv.customerName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inv.customerGstin.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleCreateSystemInvoice = (e: React.FormEvent) => {
    e.preventDefault();
    const customer = customers.find((c) => c.id === newInvCustomer) || customers[0];
    const sku = stockItems.find((s) => s.id === newInvSku) || stockItems[0];

    const taxable = newInvQty * newInvRate;
    const isInterState = customer.stateCode !== '27';
    const gstRate = sku.gstRate || 18;

    const cgst = isInterState ? 0 : Math.round((taxable * (gstRate / 200)) * 100) / 100;
    const sgst = isInterState ? 0 : Math.round((taxable * (gstRate / 200)) * 100) / 100;
    const igst = isInterState ? Math.round((taxable * (gstRate / 100)) * 100) / 100 : 0;
    const total = taxable + cgst + sgst + igst;
    const cogs = newInvQty * sku.weightedAvgCost;

    const newInv: SalesInvoice = {
      id: `INV-${Date.now()}`,
      invoiceNumber: `INV-2026-0${Math.floor(100 + Math.random() * 900)}`,
      date: new Date().toISOString().split('T')[0],
      dueDate: new Date(Date.now() + customer.creditPeriodDays * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      customerId: customer.id,
      customerName: customer.name,
      customerGstin: customer.gstin,
      branchGstin: settings.activeGstin,
      branchName: 'Pune Central Plant (HQ)',
      items: [
        {
          id: `ITEM-${Date.now()}`,
          skuId: sku.id,
          skuCode: sku.sku,
          description: sku.name,
          hsnSac: sku.hsnSac,
          quantity: newInvQty,
          unit: sku.uom,
          rate: newInvRate,
          amount: taxable,
          gstRate,
          cgst,
          sgst,
          igst,
          costPrice: sku.weightedAvgCost,
        },
      ],
      taxableAmount: taxable,
      cgst,
      sgst,
      igst,
      totalAmount: total,
      totalCogs: cogs,
      status: 'UNPAID',
      paymentReceived: 0,
      confidenceScore: 100,
      irnNumber: '9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b',
      ewayBillNumber: `241098${Math.floor(100000 + Math.random() * 900000)}`,
      isDisputed: false,
      isConsideredDoubtful: false,
      documentUrl: undefined,
    };

    onPostInvoice(newInv);
    setShowCreateModal(false);
  };

  return (
    <div id="sales-module-container" className="space-y-6">
      {/* Header & Sub Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-slate-100 tracking-tight">Sales & Receivables Engine</h2>
            <span className="text-[11px] bg-indigo-500/10 text-indigo-300 font-medium px-2 py-0.5 rounded-full border border-indigo-500/20">
              Auto-Posting & COGS Integrated
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time double entry: Dr Trade Receivables, Cr Sales, Cr Output GST, Dr COGS / Cr Perpetual Inventory.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Action buttons */}
          <button
            onClick={onOpenUpload}
            className="flex items-center gap-1.5 bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white text-xs font-semibold px-3 py-1.5 rounded-lg shadow-sm cursor-pointer"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Upload Invoice Photo (OCR)</span>
          </button>

          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium px-3 py-1.5 rounded-lg border border-slate-700 cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5 text-indigo-400" />
            <span>Create Invoice</span>
          </button>
        </div>
      </div>

      {/* Sub Tabs */}
      <div className="flex items-center bg-slate-900 p-1 rounded-lg border border-slate-800 text-xs w-fit">
        <button
          onClick={() => setActiveTab('invoices')}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer ${
            activeTab === 'invoices' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Sales Invoices ({activeInvoices.length})
        </button>
        <button
          onClick={() => setActiveTab('review_queue')}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 cursor-pointer ${
            activeTab === 'review_queue'
              ? 'bg-amber-600 text-white shadow-sm'
              : 'text-amber-400/90 hover:text-amber-300'
          }`}
        >
          <span>OCR Review Queue</span>
          {reviewQueueItems.length > 0 && (
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-amber-950 text-amber-200 border border-amber-500/40 font-bold">
              {reviewQueueItems.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('customers')}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer ${
            activeTab === 'customers' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Customer Master ({customers.length})
        </button>
        <button
          onClick={() => setActiveTab('debtors_ledger')}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer ${
            activeTab === 'debtors_ledger' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Debtors Sub-Ledger
        </button>
      </div>

      {/* TAB 1: SALES INVOICES LIST */}
      {activeTab === 'invoices' && (
        <div className="space-y-4">
          {/* Filter / Search Bar */}
          <div className="flex items-center justify-between gap-3 bg-slate-900/90 p-3 rounded-xl border border-slate-800">
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search by invoice number, customer name, or GSTIN..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="text-xs text-slate-400 font-mono">
              Showing {filteredInvoices.length} posted invoices
            </div>
          </div>

          {/* Invoices Table */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950 text-slate-400 font-mono border-b border-slate-800 uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="py-3 px-4">Invoice # / Date</th>
                    <th className="py-3 px-4">Customer / GSTIN</th>
                    <th className="py-3 px-4 text-right">Taxable</th>
                    <th className="py-3 px-4 text-right">GST (CGST/SGST/IGST)</th>
                    <th className="py-3 px-4 text-right">Total (INR)</th>
                    <th className="py-3 px-4">E-Invoice (IRN)</th>
                    <th className="py-3 px-4">OCR / GL Status</th>
                    <th className="py-3 px-4 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80 font-mono text-slate-300">
                  {filteredInvoices.map((inv) => (
                    <tr key={inv.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-100">{inv.invoiceNumber}</div>
                        <div className="text-[10px] text-slate-400">Date: {inv.date} • Due: {inv.dueDate}</div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-sans font-medium text-slate-200">{inv.customerName}</div>
                        <div className="text-[10px] text-slate-400">{inv.customerGstin}</div>
                      </td>
                      <td className="py-3 px-4 text-right">{formatINR(inv.taxableAmount)}</td>
                      <td className="py-3 px-4 text-right">
                        <div className="text-slate-200">{formatINR(inv.cgst + inv.sgst + inv.igst)}</div>
                        <div className="text-[9px] text-slate-400">
                          {inv.igst > 0 ? `IGST: ${formatINR(inv.igst)}` : `C+S: ${formatINR(inv.cgst * 2)}`}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-right font-bold text-slate-100">
                        {formatINR(inv.totalAmount)}
                      </td>
                      <td className="py-3 px-4 font-sans">
                        {inv.irnNumber ? (
                          <span className="text-[10px] text-emerald-400 flex items-center gap-1 font-mono font-medium">
                            <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />
                            <span>IRN Generated</span>
                          </span>
                        ) : (
                          <span className="text-[10px] text-slate-400">B2C / Exempt</span>
                        )}
                      </td>
                      <td className="py-3 px-4 font-sans">
                        <div className="flex items-center gap-1.5">
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            Auto-Posted
                          </span>
                          <span className="text-[10px] text-slate-400 font-mono" title="OCR Extraction Confidence">
                            {inv.confidenceScore}%
                          </span>
                        </div>
                        {inv.journalEntryId && (
                          <div className="text-[9px] font-mono text-indigo-400 mt-0.5">
                            Linked {inv.journalEntryId}
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-4 text-center font-sans">
                        <button
                          onClick={() => setSelectedInvoiceForDetail(inv)}
                          className="text-xs text-indigo-400 hover:text-indigo-300 font-medium px-2 py-1 rounded bg-indigo-500/10 hover:bg-indigo-500/20 transition-colors cursor-pointer"
                        >
                          View Voucher
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: OCR REVIEW QUEUE (CONFIDENCE < THRESHOLD) */}
      {activeTab === 'review_queue' && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-500/30 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div className="text-xs">
              <h4 className="font-semibold text-amber-200 text-sm">Low-Confidence OCR Maker-Checker Queue</h4>
              <p className="text-slate-300 mt-1 leading-relaxed">
                Per CFO Internal Financial Control (IFC) policy, source documents extracted with confidence score below{' '}
                <strong className="text-amber-300">{settings.ocrAutoPostThreshold}%</strong> are suspended from auto-posting to prevent general ledger pollution.
                Review the side-by-side extracted figures, tax calculations, and party GSTIN before approving to the General Ledger.
              </p>
            </div>
          </div>

          {reviewQueueItems.length === 0 ? (
            <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-10 text-center text-slate-400">
              <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto mb-2" />
              <div className="font-semibold text-slate-200">Review Queue is Completely Clean</div>
              <p className="text-xs text-slate-400 mt-1">All uploaded invoices met the confidence criteria and were auto-posted.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {reviewQueueItems.map((inv) => (
                <div key={inv.id} className="bg-slate-900/90 border border-amber-500/40 rounded-xl p-5 shadow-lg">
                  <div className="flex flex-col md:flex-row md:items-center justify-between pb-3 border-b border-slate-800 gap-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 font-bold">
                        {inv.confidenceScore}%
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-100 text-sm">{inv.invoiceNumber}</span>
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
                            Requires Verification
                          </span>
                        </div>
                        <div className="text-xs text-slate-400 mt-0.5">
                          Party: <strong className="text-slate-200">{inv.customerName}</strong> ({inv.customerGstin})
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => onApproveReviewQueue(inv.id)}
                        className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-4 py-2 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer shadow-md shadow-emerald-950/50"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Verify & Auto-Post to GL</span>
                      </button>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4 text-xs">
                    {/* Left: Document Inspection */}
                    <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                      <div className="font-semibold text-slate-300 mb-2 flex items-center justify-between">
                        <span>Source Document Artifact</span>
                        <span className="text-[10px] text-slate-400 font-mono">Image scan archive</span>
                      </div>
                      {inv.documentUrl ? (
                        <div className="h-48 rounded overflow-hidden border border-slate-800 relative group">
                          <img
                            src={inv.documentUrl}
                            alt="Invoice Scan"
                            className="w-full h-full object-cover"
                            referrerPolicy="no-referrer"
                          />
                          <div className="absolute inset-0 bg-slate-950/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                            <span className="text-xs text-indigo-300 font-medium flex items-center gap-1">
                              <Eye className="w-3.5 h-3.5" /> Full Resolution Scan
                            </span>
                          </div>
                        </div>
                      ) : (
                        <div className="h-48 rounded bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-400">
                          Digital OCR Text Extraction Payload
                        </div>
                      )}
                      {inv.confidenceReasons && inv.confidenceReasons.length > 0 && (
                        <div className="mt-2.5 p-2 rounded bg-amber-950/20 border border-amber-500/20 text-[11px] text-amber-300/90">
                          <strong>Ambiguity flags flagged by AI model:</strong>
                          <ul className="list-disc list-inside mt-0.5 space-y-0.5">
                            {inv.confidenceReasons.map((r, idx) => (
                              <li key={idx}>{r}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>

                    {/* Right: Extracted Data & Proposed Double Entry */}
                    <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 flex flex-col justify-between">
                      <div>
                        <div className="font-semibold text-slate-300 mb-2">Extracted Financial Breakdown</div>
                        <div className="space-y-1.5 font-mono text-[11px]">
                          <div className="flex justify-between py-1 border-b border-slate-800">
                            <span className="text-slate-400">Taxable Value:</span>
                            <span className="text-slate-100 font-bold">{formatINR(inv.taxableAmount)}</span>
                          </div>
                          <div className="flex justify-between py-1 border-b border-slate-800">
                            <span className="text-slate-400">Output CGST (9%):</span>
                            <span className="text-slate-200">{formatINR(inv.cgst)}</span>
                          </div>
                          <div className="flex justify-between py-1 border-b border-slate-800">
                            <span className="text-slate-400">Output SGST (9%):</span>
                            <span className="text-slate-200">{formatINR(inv.sgst)}</span>
                          </div>
                          <div className="flex justify-between py-1 border-b border-slate-800">
                            <span className="text-slate-400">Output IGST (18%):</span>
                            <span className="text-slate-200">{formatINR(inv.igst)}</span>
                          </div>
                          <div className="flex justify-between py-1.5 text-xs">
                            <span className="text-indigo-300 font-semibold font-sans">Total Gross Receivable:</span>
                            <span className="text-indigo-400 font-bold">{formatINR(inv.totalAmount)}</span>
                          </div>
                        </div>

                        <div className="mt-3 p-2 rounded bg-slate-900 border border-slate-800 text-[10px] font-mono text-slate-300">
                          <div className="font-bold text-slate-400 mb-1">Pre-Computed Journal Lines (Pending Approval):</div>
                          <div>Dr 1201 Trade Receivables: {formatINR(inv.totalAmount)}</div>
                          <div>Cr 3001 Revenue from Operations: {formatINR(inv.taxableAmount)}</div>
                          <div>Cr 2301/02 Output GST: {formatINR(inv.cgst + inv.sgst + inv.igst)}</div>
                          <div>Dr 4001 COGS / Cr 1102 Inventory: {formatINR(inv.totalCogs)}</div>
                        </div>
                      </div>

                      <div className="mt-3 pt-2 border-t border-slate-800 flex justify-end">
                        <button
                          onClick={() => onApproveReviewQueue(inv.id)}
                          className="w-full bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold py-2 rounded transition-colors cursor-pointer"
                        >
                          Approve and Commit to General Ledger
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: CUSTOMER MASTER */}
      {activeTab === 'customers' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <h3 className="font-semibold text-slate-100 text-sm">Customer Master Register (Statutory & Credit Terms)</h3>
            <span className="text-xs text-slate-400 font-mono">{customers.length} Registered Accounts</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 font-mono border-b border-slate-800 uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="py-3 px-4">Customer Entity</th>
                  <th className="py-3 px-4">GSTIN / State</th>
                  <th className="py-3 px-4 text-right">Credit Limit</th>
                  <th className="py-3 px-4">Credit Period</th>
                  <th className="py-3 px-4 text-right">Current Outstanding</th>
                  <th className="py-3 px-4">Contact</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 font-mono text-slate-300">
                {customers.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-800/40">
                    <td className="py-3 px-4">
                      <div className="font-sans font-medium text-slate-100">{c.name}</div>
                      <div className="text-[10px] text-slate-400">{c.id} • {c.city}</div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="text-slate-200">{c.gstin}</div>
                      <div className="text-[10px] text-slate-400">{c.stateName} (Code {c.stateCode})</div>
                    </td>
                    <td className="py-3 px-4 text-right font-bold text-slate-200">{formatINR(c.creditLimit)}</td>
                    <td className="py-3 px-4 font-sans">{c.creditPeriodDays} Days Net</td>
                    <td className="py-3 px-4 text-right font-bold text-indigo-400">{formatINR(c.currentOutstanding)}</td>
                    <td className="py-3 px-4 font-sans text-slate-400">
                      <div>{c.email}</div>
                      <div className="text-[10px]">{c.phone}</div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: DEBTORS SUB-LEDGER */}
      {activeTab === 'debtors_ledger' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div>
              <h3 className="font-semibold text-slate-100 text-sm">Debtors / Trade Receivables Ledger</h3>
              <p className="text-[11px] text-slate-400">Control Account #1201 reconciled against all customer sub-ledgers</p>
            </div>
            <span className="text-xs font-mono font-bold text-indigo-400 bg-indigo-500/10 px-3 py-1 rounded-md border border-indigo-500/20">
              GL Control Balance: {formatINR(5890000)}
            </span>
          </div>

          <div className="space-y-3">
            {customers.map((cust) => (
              <div key={cust.id} className="p-3.5 bg-slate-950 rounded-lg border border-slate-800">
                <div className="flex items-center justify-between text-xs">
                  <div>
                    <span className="font-semibold text-slate-100 font-sans">{cust.name}</span>
                    <span className="text-[10px] font-mono text-slate-400 ml-2">({cust.gstin})</span>
                  </div>
                  <div className="text-right">
                    <span className="text-[11px] text-slate-400 mr-2">Closing Debit Balance:</span>
                    <span className="font-mono font-bold text-slate-100">{formatINR(cust.currentOutstanding)}</span>
                  </div>
                </div>
                <div className="mt-2 text-[11px] text-slate-400 flex items-center justify-between font-mono">
                  <span>Credit Terms: {cust.creditPeriodDays} days</span>
                  <span className={cust.disputedAmount > 0 ? 'text-rose-400 font-semibold' : 'text-emerald-400'}>
                    {cust.disputedAmount > 0 ? `Disputed: ${formatINR(cust.disputedAmount)}` : 'Considered 100% Good'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* MODAL: CREATE SYSTEM INVOICE */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Receipt className="w-5 h-5 text-indigo-400" />
                <h3 className="font-bold text-slate-100 text-base">Generate System Sales Invoice</h3>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-slate-200 text-sm cursor-pointer"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateSystemInvoice} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Select Customer Party</label>
                <select
                  value={newInvCustomer}
                  onChange={(e) => setNewInvCustomer(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg p-2 focus:outline-none focus:border-indigo-500"
                >
                  {customers.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.gstin} - {c.stateName})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Product / SKU</label>
                <select
                  value={newInvSku}
                  onChange={(e) => setNewInvSku(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg p-2 focus:outline-none focus:border-indigo-500"
                >
                  {stockItems.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.sku} - Stock: {s.currentStock} {s.uom})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Quantity</label>
                  <input
                    type="number"
                    min="1"
                    value={newInvQty}
                    onChange={(e) => setNewInvQty(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg p-2 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Unit Rate (₹)</label>
                  <input
                    type="number"
                    value={newInvRate}
                    onChange={(e) => setNewInvRate(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg p-2 focus:outline-none"
                  />
                </div>
              </div>

              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-[11px] font-mono space-y-1">
                <div className="flex justify-between text-slate-400">
                  <span>Taxable:</span>
                  <span className="text-slate-100">{formatINR(newInvQty * newInvRate)}</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Applicable GST (18%):</span>
                  <span className="text-slate-100">{formatINR(newInvQty * newInvRate * 0.18)}</span>
                </div>
                <div className="flex justify-between font-bold text-indigo-400 pt-1 border-t border-slate-800">
                  <span>Gross Invoice Total:</span>
                  <span>{formatINR(newInvQty * newInvRate * 1.18)}</span>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold flex items-center gap-1.5 cursor-pointer shadow-md"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Generate & Auto-Post to Ledger</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* DETAIL DRAWER / MODAL: VIEW VOUCHER DETAILS */}
      {selectedInvoiceForDetail && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-xl w-full p-6 shadow-2xl space-y-4 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 font-sans">
              <div className="flex items-center gap-2">
                <Receipt className="w-5 h-5 text-indigo-400" />
                <div>
                  <h3 className="font-bold text-slate-100 text-base">{selectedInvoiceForDetail.invoiceNumber}</h3>
                  <p className="text-xs text-slate-400 font-mono">IRN: {selectedInvoiceForDetail.irnNumber?.substring(0, 24)}...</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedInvoiceForDetail(null)}
                className="text-slate-400 hover:text-slate-200 text-sm cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 font-mono text-[11px]">
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-1">
                <div className="flex justify-between">
                  <span className="text-slate-400">Customer:</span>
                  <span className="text-slate-100 font-sans font-medium">{selectedInvoiceForDetail.customerName}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">GSTIN:</span>
                  <span className="text-slate-200">{selectedInvoiceForDetail.customerGstin}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Date / Due:</span>
                  <span className="text-slate-200">{selectedInvoiceForDetail.date} / {selectedInvoiceForDetail.dueDate}</span>
                </div>
              </div>

              <div className="border border-slate-800 rounded-lg overflow-hidden">
                <table className="w-full text-left">
                  <thead className="bg-slate-950 text-slate-400 text-[10px] uppercase">
                    <tr>
                      <th className="p-2">Account Code & Name</th>
                      <th className="p-2 text-right">Debit (₹)</th>
                      <th className="p-2 text-right">Credit (₹)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/80 text-slate-300">
                    <tr>
                      <td className="p-2">1201 Trade Receivables (Customer)</td>
                      <td className="p-2 text-right font-bold text-slate-100">{formatINR(selectedInvoiceForDetail.totalAmount)}</td>
                      <td className="p-2 text-right">-</td>
                    </tr>
                    <tr>
                      <td className="p-2">3001 Revenue from Operations</td>
                      <td className="p-2 text-right">-</td>
                      <td className="p-2 text-right">{formatINR(selectedInvoiceForDetail.taxableAmount)}</td>
                    </tr>
                    {selectedInvoiceForDetail.cgst > 0 && (
                      <>
                        <tr>
                          <td className="p-2">2301 Output CGST Payable (9%)</td>
                          <td className="p-2 text-right">-</td>
                          <td className="p-2 text-right">{formatINR(selectedInvoiceForDetail.cgst)}</td>
                        </tr>
                        <tr>
                          <td className="p-2">2302 Output SGST Payable (9%)</td>
                          <td className="p-2 text-right">-</td>
                          <td className="p-2 text-right">{formatINR(selectedInvoiceForDetail.sgst)}</td>
                        </tr>
                      </>
                    )}
                    {selectedInvoiceForDetail.igst > 0 && (
                      <tr>
                        <td className="p-2">2303 Output IGST Payable (18%)</td>
                        <td className="p-2 text-right">-</td>
                        <td className="p-2 text-right">{formatINR(selectedInvoiceForDetail.igst)}</td>
                      </tr>
                    )}
                    <tr className="bg-slate-950/40">
                      <td className="p-2 text-indigo-300">4001 Cost of Goods Sold (COGS)</td>
                      <td className="p-2 text-right font-bold text-indigo-300">{formatINR(selectedInvoiceForDetail.totalCogs)}</td>
                      <td className="p-2 text-right">-</td>
                    </tr>
                    <tr className="bg-slate-950/40">
                      <td className="p-2 text-indigo-300">1102 Finished Goods Inventory</td>
                      <td className="p-2 text-right">-</td>
                      <td className="p-2 text-right font-bold text-indigo-300">{formatINR(selectedInvoiceForDetail.totalCogs)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div className="flex justify-end pt-2 font-sans">
              <button
                onClick={() => setSelectedInvoiceForDetail(null)}
                className="px-4 py-1.5 rounded-lg bg-slate-800 text-slate-200 hover:bg-slate-700 cursor-pointer"
              >
                Close Voucher
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
