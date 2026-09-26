import React, { useState } from 'react';
import {
  ShoppingCart,
  Plus,
  Sparkles,
  Search,
  CheckCircle2,
  AlertCircle,
  Eye,
  FileCheck,
  Building,
  ShieldCheck,
  Clock,
  ExternalLink,
} from 'lucide-react';
import { SystemSettings, Vendor, VendorBill } from '../../types';
import { formatINR, formatLakhs } from '../../services/accountingEngine';

interface ProcurementViewProps {
  vendorBills: VendorBill[];
  vendors: Vendor[];
  settings: SystemSettings;
  onPostBill: (bill: VendorBill) => void;
  onApproveBillReviewQueue: (billId: string) => void;
  onOpenUpload: () => void;
}

export const ProcurementView: React.FC<ProcurementViewProps> = ({
  vendorBills,
  vendors,
  settings,
  onPostBill,
  onApproveBillReviewQueue,
  onOpenUpload,
}) => {
  const [activeTab, setActiveTab] = useState<'bills' | 'review_queue' | 'vendors' | 'msme_43b' | 'three_way_match'>('bills');
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedBillForDetail, setSelectedBillForDetail] = useState<VendorBill | null>(null);

  // New Vendor Bill form state
  const [newBillVendorId, setNewBillVendorId] = useState(vendors[0]?.id || '');
  const [newBillTaxable, setNewBillTaxable] = useState(150000);
  const [newBillCategory, setNewBillCategory] = useState<'INVENTORY_PURCHASE' | 'EXPENSE'>('INVENTORY_PURCHASE');
  const [newBillInvoiceNum, setNewBillInvoiceNum] = useState(`VB-2026-${Math.floor(1000 + Math.random() * 9000)}`);

  const reviewQueueBills = vendorBills.filter((b) => b.status === 'REVIEW_QUEUE');
  const activeBills = vendorBills.filter((b) => b.status !== 'REVIEW_QUEUE');

  const filteredBills = activeBills.filter(
    (b) =>
      b.billNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
      b.vendorName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      b.vendorGstin.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleCreateSystemBill = (e: React.FormEvent) => {
    e.preventDefault();
    const vendor = vendors.find((v) => v.id === newBillVendorId) || vendors[0];
    const isInterState = vendor.stateCode !== '27';
    const gstRate = 18;

    const cgst = isInterState ? 0 : Math.round(newBillTaxable * (gstRate / 200) * 100) / 100;
    const sgst = isInterState ? 0 : Math.round(newBillTaxable * (gstRate / 200) * 100) / 100;
    const igst = isInterState ? Math.round(newBillTaxable * (gstRate / 100) * 100) / 100 : 0;
    const totalTax = cgst + sgst + igst;
    const totalAmount = newBillTaxable + totalTax;

    // TDS Calculation
    const tdsRate = vendor.tdsSection ? vendor.tdsRate : 0;
    const tdsDeducted = Math.round(newBillTaxable * (tdsRate / 100) * 100) / 100;
    const netPayable = totalAmount - tdsDeducted;

    const newBill: VendorBill = {
      id: `BILL-${Date.now()}`,
      billNumber: newBillInvoiceNum,
      date: new Date().toISOString().split('T')[0],
      dueDate: new Date(Date.now() + (vendor.isMsme ? 45 : 60) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      vendorId: vendor.id,
      vendorName: vendor.name,
      vendorGstin: vendor.gstin,
      branchGstin: settings.activeGstin,
      category: newBillCategory,
      items: [
        {
          id: `BI-${Date.now()}`,
          description: newBillCategory === 'INVENTORY_PURCHASE' ? 'Synthetic Polymers Grade 5' : 'Factory Maintenance Services',
          hsnSac: newBillCategory === 'INVENTORY_PURCHASE' ? '3901' : '9987',
          quantity: 1,
          rate: newBillTaxable,
          amount: newBillTaxable,
          gstRate,
          cgst,
          sgst,
          igst,
          isItcEligible: true,
        },
      ],
      taxableAmount: newBillTaxable,
      cgst,
      sgst,
      igst,
      totalAmount,
      tdsSection: vendor.tdsSection,
      tdsRate,
      tdsDeducted,
      netPayable,
      status: 'UNPAID',
      paymentMade: 0,
      confidenceScore: 100,
      isMsme: vendor.isMsme,
      msmeType: vendor.msmeType,
      isDisputed: false,
      poReference: 'PO-2026-081',
      grnReference: 'GRN-2026-042',
    };

    onPostBill(newBill);
    setShowCreateModal(false);
  };

  return (
    <div id="procurement-module-container" className="space-y-6">
      {/* Header & Sub Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-slate-100 tracking-tight">Procurement & Accounts Payable</h2>
            <span className="text-[11px] bg-indigo-500/10 text-indigo-300 font-medium px-2 py-0.5 rounded-full border border-indigo-500/20">
              Section 43B(h) & TDS Automated
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Auto-post purchase invoices: Dr Inventory/Expense, Dr Input GST ITC, Cr TDS Payable, Cr Trade Payables.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onOpenUpload}
            className="flex items-center gap-1.5 bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white text-xs font-semibold px-3 py-1.5 rounded-lg shadow-sm cursor-pointer"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Upload Vendor Bill (OCR)</span>
          </button>

          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium px-3 py-1.5 rounded-lg border border-slate-700 cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5 text-indigo-400" />
            <span>Enter Vendor Bill</span>
          </button>
        </div>
      </div>

      {/* Sub Tabs */}
      <div className="flex items-center bg-slate-900 p-1 rounded-lg border border-slate-800 text-xs w-fit">
        <button
          onClick={() => setActiveTab('bills')}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer ${
            activeTab === 'bills' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Vendor Bills ({activeBills.length})
        </button>
        <button
          onClick={() => setActiveTab('review_queue')}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 cursor-pointer ${
            activeTab === 'review_queue' ? 'bg-amber-600 text-white shadow-sm' : 'text-amber-400/90 hover:text-amber-300'
          }`}
        >
          <span>OCR Review Queue</span>
          {reviewQueueBills.length > 0 && (
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-amber-950 text-amber-200 border border-amber-500/40 font-bold">
              {reviewQueueBills.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('vendors')}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer ${
            activeTab === 'vendors' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Vendor Master ({vendors.length})
        </button>
        <button
          onClick={() => setActiveTab('msme_43b')}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer ${
            activeTab === 'msme_43b' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Section 43B(h) MSME Tracker
        </button>
        <button
          onClick={() => setActiveTab('three_way_match')}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer ${
            activeTab === 'three_way_match' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          3-Way Match (PO/GRN/Bill)
        </button>
      </div>

      {/* TAB 1: BILLS LIST */}
      {activeTab === 'bills' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-3 bg-slate-900/90 p-3 rounded-xl border border-slate-800">
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search vendor bills by bill number, supplier or GSTIN..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none"
              />
            </div>
            <span className="text-xs text-slate-400 font-mono">Showing {filteredBills.length} posted bills</span>
          </div>

          <div className="bg-slate-900/90 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950 text-slate-400 font-mono border-b border-slate-800 uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="py-3 px-4">Bill # / Date</th>
                    <th className="py-3 px-4">Vendor / GSTIN</th>
                    <th className="py-3 px-4">MSME Status</th>
                    <th className="py-3 px-4 text-right">Taxable</th>
                    <th className="py-3 px-4 text-right">Input ITC</th>
                    <th className="py-3 px-4 text-right">TDS (₹)</th>
                    <th className="py-3 px-4 text-right">Net Payable</th>
                    <th className="py-3 px-4 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80 font-mono text-slate-300">
                  {filteredBills.map((bill) => (
                    <tr key={bill.id} className="hover:bg-slate-800/40">
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-100">{bill.billNumber}</div>
                        <div className="text-[10px] text-slate-400">Date: {bill.date} • Due: {bill.dueDate}</div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-sans font-medium text-slate-200">{bill.vendorName}</div>
                        <div className="text-[10px] text-slate-400">{bill.vendorGstin}</div>
                      </td>
                      <td className="py-3 px-4 font-sans">
                        {bill.isMsme ? (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20">
                            MSME ({bill.msmeType})
                          </span>
                        ) : (
                          <span className="text-[10px] text-slate-400">Others</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">{formatINR(bill.taxableAmount)}</td>
                      <td className="py-3 px-4 text-right text-emerald-400 font-bold">
                        {formatINR(bill.cgst + bill.sgst + bill.igst)}
                      </td>
                      <td className="py-3 px-4 text-right text-rose-300">
                        {bill.tdsDeducted > 0 ? (
                          <div>
                            <div>-{formatINR(bill.tdsDeducted)}</div>
                            <div className="text-[9px] text-slate-400">{bill.tdsSection} @ {bill.tdsRate}%</div>
                          </div>
                        ) : '-'}
                      </td>
                      <td className="py-3 px-4 text-right font-bold text-slate-100">
                        {formatINR(bill.netPayable)}
                      </td>
                      <td className="py-3 px-4 text-center font-sans">
                        <button
                          onClick={() => setSelectedBillForDetail(bill)}
                          className="text-xs text-indigo-400 hover:text-indigo-300 font-medium px-2 py-1 rounded bg-indigo-500/10 hover:bg-indigo-500/20 cursor-pointer"
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

      {/* TAB 2: OCR REVIEW QUEUE */}
      {activeTab === 'review_queue' && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-500/30 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div className="text-xs">
              <h4 className="font-semibold text-amber-200 text-sm">Vendor Bill Low-Confidence Review Queue</h4>
              <p className="text-slate-300 mt-1 leading-relaxed">
                Source vendor bills scanned with OCR confidence below threshold ({settings.ocrAutoPostThreshold}%) require human accountant confirmation to verify Input Tax Credit eligibility and TDS deductions before posting.
              </p>
            </div>
          </div>

          {reviewQueueBills.length === 0 ? (
            <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-10 text-center text-slate-400">
              <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto mb-2" />
              <div className="font-semibold text-slate-200">Review Queue is Clear</div>
              <p className="text-xs text-slate-400 mt-1">All vendor bills have been reviewed and posted.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {reviewQueueBills.map((b) => (
                <div key={b.id} className="bg-slate-900/90 border border-amber-500/40 rounded-xl p-5 shadow-lg">
                  <div className="flex flex-col md:flex-row md:items-center justify-between pb-3 border-b border-slate-800 gap-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 font-bold">
                        {b.confidenceScore}%
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-100 text-sm">{b.billNumber}</span>
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
                            Verification Required
                          </span>
                        </div>
                        <div className="text-xs text-slate-400 mt-0.5">
                          Supplier: <strong className="text-slate-200">{b.vendorName}</strong> ({b.vendorGstin})
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={() => onApproveBillReviewQueue(b.id)}
                      className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-4 py-2 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer shadow-md"
                    >
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Verify & Auto-Post to AP Ledger</span>
                    </button>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 text-xs font-mono">
                    <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                      <div className="font-sans font-semibold text-slate-300 mb-2">Source Document Scan</div>
                      {b.documentUrl ? (
                        <div className="h-40 rounded overflow-hidden border border-slate-800">
                          <img src={b.documentUrl} alt="Bill scan" className="w-full h-full object-cover" referrerPolicy="no-referrer" />
                        </div>
                      ) : (
                        <div className="h-40 rounded bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-400 font-sans">
                          Raw OCR Vendor Bill Scanned Image
                        </div>
                      )}
                    </div>

                    <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 flex flex-col justify-between">
                      <div className="space-y-1.5">
                        <div className="flex justify-between py-1 border-b border-slate-800">
                          <span className="text-slate-400">Taxable Value:</span>
                          <span className="text-slate-100">{formatINR(b.taxableAmount)}</span>
                        </div>
                        <div className="flex justify-between py-1 border-b border-slate-800">
                          <span className="text-slate-400">CGST (9%):</span>
                          <span className="text-slate-200">{formatINR(b.cgst)}</span>
                        </div>
                        <div className="flex justify-between py-1 border-b border-slate-800">
                          <span className="text-slate-400">SGST (9%):</span>
                          <span className="text-slate-200">{formatINR(b.sgst)}</span>
                        </div>
                        <div className="flex justify-between py-1.5 text-xs font-bold text-indigo-300">
                          <span>Net Payable:</span>
                          <span>{formatINR(b.netPayable)}</span>
                        </div>
                      </div>

                      <button
                        onClick={() => onApproveBillReviewQueue(b.id)}
                        className="w-full mt-3 bg-emerald-600 hover:bg-emerald-500 text-white font-sans text-xs font-semibold py-2 rounded cursor-pointer"
                      >
                        Approve & Post to General Ledger
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: VENDOR MASTER */}
      {activeTab === 'vendors' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl overflow-hidden shadow-sm text-xs">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <h3 className="font-semibold text-slate-100 text-sm">Vendor Master (GSTIN & MSME Register)</h3>
            <span className="text-xs text-slate-400 font-mono">{vendors.length} Vendors</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-slate-950 text-slate-400 font-mono border-b border-slate-800 uppercase text-[10px]">
                <tr>
                  <th className="py-3 px-4">Vendor Entity</th>
                  <th className="py-3 px-4">GSTIN / State</th>
                  <th className="py-3 px-4">MSME Category</th>
                  <th className="py-3 px-4">TDS Section</th>
                  <th className="py-3 px-4 text-right">Current Payable</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 font-mono text-slate-300">
                {vendors.map((v) => (
                  <tr key={v.id} className="hover:bg-slate-800/40">
                    <td className="py-3 px-4">
                      <div className="font-sans font-medium text-slate-100">{v.name}</div>
                      <div className="text-[10px] text-slate-400">{v.id} • {v.city}</div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="text-slate-200">{v.gstin}</div>
                      <div className="text-[10px] text-slate-400">{v.stateName}</div>
                    </td>
                    <td className="py-3 px-4 font-sans">
                      {v.isMsme ? (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20 font-semibold">
                          {v.msmeType} ({v.msmeRegNumber})
                        </span>
                      ) : (
                        <span className="text-[10px] text-slate-400">Large Enterprise</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      {v.tdsSection ? (
                        <span className="text-slate-200">{v.tdsSection} ({v.tdsRate}%)</span>
                      ) : (
                        <span className="text-slate-400">Nil</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right font-bold text-slate-100">{formatINR(v.currentOutstanding)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: SECTION 43B(H) MSME TRACKER */}
      {activeTab === 'msme_43b' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 space-y-4 text-xs">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div>
              <h3 className="font-semibold text-slate-100 text-sm">Income Tax Section 43B(h) MSME Statutory Compliance</h3>
              <p className="text-slate-400 text-[11px]">
                Payments to Micro & Small enterprises must be settled within 45 days (if written agreement) or 15 days (without agreement), or expense is disallowed in tax computation.
              </p>
            </div>
            <span className="text-emerald-400 font-mono text-xs flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" /> 100% On-Time Disbursal
            </span>
          </div>

          <div className="space-y-3 font-mono">
            {vendorBills
              .filter((b) => b.isMsme && b.status !== 'REVIEW_QUEUE')
              .map((b) => (
                <div key={b.id} className="p-3.5 bg-slate-950 rounded-lg border border-purple-500/30 flex items-center justify-between">
                  <div>
                    <div className="font-sans font-semibold text-slate-100">{b.vendorName}</div>
                    <div className="text-[11px] text-slate-400">
                      Bill #{b.billNumber} • MSME Type: {b.msmeType} • Due by: <strong className="text-purple-300">{b.dueDate}</strong>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-slate-100">{formatINR(b.netPayable)}</div>
                    <div className="text-[10px] text-emerald-400 font-sans">Compliant with Sec 43B(h)</div>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* TAB 5: 3-WAY MATCH */}
      {activeTab === 'three_way_match' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 space-y-4 text-xs">
          <h3 className="font-semibold text-slate-100 text-sm">Three-Way Matching Verification (PO vs GRN vs Vendor Bill)</h3>
          <p className="text-slate-400 text-[11px]">Internal Financial Control (IFC) verification audit check</p>

          <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-200">Bill #VB-2026-081 (Shree Ganesh Precision)</span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-semibold border border-emerald-500/20">
                100% 3-WAY MATCHED
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2 pt-2 text-[11px] font-mono text-slate-400 border-t border-slate-800">
              <div>PO: PO-2026-081 (1,200 kg @ ₹85)</div>
              <div>GRN: GRN-2026-042 (1,200 kg Received)</div>
              <div>Invoice: VB-2026-081 (1,200 kg Billed)</div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: ENTER VENDOR BILL */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4 text-xs">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-slate-100 text-sm">Record Vendor Bill / Expense</h3>
              <button onClick={() => setShowCreateModal(false)} className="text-slate-400 cursor-pointer">✕</button>
            </div>

            <form onSubmit={handleCreateSystemBill} className="space-y-3">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Select Supplier</label>
                <select
                  value={newBillVendorId}
                  onChange={(e) => setNewBillVendorId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
                >
                  {vendors.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.name} ({v.gstin} - {v.isMsme ? `MSME ${v.msmeType}` : 'Large'})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Bill Number</label>
                  <input
                    type="text"
                    value={newBillInvoiceNum}
                    onChange={(e) => setNewBillInvoiceNum(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Classification</label>
                  <select
                    value={newBillCategory}
                    onChange={(e) => setNewBillCategory(e.target.value as any)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
                  >
                    <option value="INVENTORY_PURCHASE">Raw Material / Stock In</option>
                    <option value="EXPENSE">Operating Expense</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Taxable Value (₹)</label>
                <input
                  type="number"
                  value={newBillTaxable}
                  onChange={(e) => setNewBillTaxable(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200 font-mono"
                />
              </div>

              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-[11px] font-mono space-y-1">
                <div className="flex justify-between text-slate-400">
                  <span>Input GST (18%):</span>
                  <span className="text-emerald-400">{formatINR(newBillTaxable * 0.18)}</span>
                </div>
                <div className="flex justify-between font-bold text-slate-100 pt-1 border-t border-slate-800">
                  <span>Net Payable to Vendor:</span>
                  <span>{formatINR(newBillTaxable * 1.18)}</span>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold cursor-pointer shadow-md"
                >
                  Post Bill to AP Ledger
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* DETAIL MODAL: VIEW VENDOR BILL VOUCHER */}
      {selectedBillForDetail && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 font-mono text-xs">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-xl w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 font-sans">
              <h3 className="font-bold text-slate-100 text-sm">Vendor Voucher: {selectedBillForDetail.billNumber}</h3>
              <button onClick={() => setSelectedBillForDetail(null)} className="text-slate-400 cursor-pointer">✕</button>
            </div>

            <div className="space-y-3 font-mono text-[11px]">
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-1">
                <div className="flex justify-between">
                  <span className="text-slate-400">Supplier:</span>
                  <span className="text-slate-100 font-sans font-medium">{selectedBillForDetail.vendorName}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">GSTIN:</span>
                  <span className="text-slate-200">{selectedBillForDetail.vendorGstin}</span>
                </div>
              </div>

              <table className="w-full text-left border border-slate-800 rounded-lg overflow-hidden">
                <thead className="bg-slate-950 text-slate-400 text-[10px] uppercase">
                  <tr>
                    <th className="p-2">Account Code & Name</th>
                    <th className="p-2 text-right">Debit (₹)</th>
                    <th className="p-2 text-right">Credit (₹)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80 text-slate-300">
                  <tr>
                    <td className="p-2 font-sans">{selectedBillForDetail.category === 'INVENTORY_PURCHASE' ? '1101 Raw Materials Inventory' : '4203 Operating Expenses'}</td>
                    <td className="p-2 text-right font-bold text-slate-100">{formatINR(selectedBillForDetail.taxableAmount)}</td>
                    <td className="p-2 text-right">-</td>
                  </tr>
                  <tr>
                    <td className="p-2 font-sans">1301/02 Input Tax Credit (ITC)</td>
                    <td className="p-2 text-right font-bold text-emerald-400">{formatINR(selectedBillForDetail.cgst + selectedBillForDetail.sgst + selectedBillForDetail.igst)}</td>
                    <td className="p-2 text-right">-</td>
                  </tr>
                  {selectedBillForDetail.tdsDeducted > 0 && (
                    <tr>
                      <td className="p-2 font-sans">2201 TDS Payable ({selectedBillForDetail.tdsSection})</td>
                      <td className="p-2 text-right">-</td>
                      <td className="p-2 text-right text-rose-300 font-bold">{formatINR(selectedBillForDetail.tdsDeducted)}</td>
                    </tr>
                  )}
                  <tr className="bg-slate-950/40">
                    <td className="p-2 font-sans">2101 Trade Payables (Creditors)</td>
                    <td className="p-2 text-right">-</td>
                    <td className="p-2 text-right font-bold text-indigo-300">{formatINR(selectedBillForDetail.netPayable)}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="flex justify-end pt-2 font-sans">
              <button
                onClick={() => setSelectedBillForDetail(null)}
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
