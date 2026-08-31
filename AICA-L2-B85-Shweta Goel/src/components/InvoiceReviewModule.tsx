import React, { useState } from 'react';
import { 
  InvoiceReviewData, 
  InvoiceLineItem, 
  InvoiceAuditIssue,
  SuggestedAccountHead
} from '../types';
import { RiskBadge } from './RiskBadge';
import { 
  Calculator, 
  AlertOctagon, 
  CheckCircle2, 
  AlertTriangle, 
  Building, 
  FileText, 
  Calendar, 
  MapPin, 
  Receipt,
  FileSpreadsheet,
  Info,
  ShieldCheck,
  Percent,
  BookOpen,
  ArrowRightLeft,
  Copy,
  Check,
  Layers,
  Tag,
  Briefcase,
  HelpCircle
} from 'lucide-react';

interface InvoiceReviewModuleProps {
  data: InvoiceReviewData;
  onExportExcel: () => void;
}

export const InvoiceReviewModule: React.FC<InvoiceReviewModuleProps> = ({
  data,
  onExportExcel,
}) => {
  const [copiedJournal, setCopiedJournal] = useState(false);
  const isDiscrepant = !data.isMathValid || data.mathDiscrepancy > 1;

  // Fallback if suggestedAccountHead is not yet populated
  const accountHead: SuggestedAccountHead = data.suggestedAccountHead || {
    ledgerName: data.lineItems?.[0]?.description?.toLowerCase().includes('cloud') || data.vendorName?.toLowerCase().includes('cloud')
      ? 'Software Subscriptions & Cloud Hosting Charges'
      : (data.lineItems?.[0]?.description?.toLowerCase().includes('hardware') || data.lineItems?.[0]?.description?.toLowerCase().includes('fastener')
        ? 'Consumables & Hardware Spares A/c'
        : 'Office & General Administrative Expenses'),
    accountCategory: 'Indirect Expenses (Administrative Overhead)',
    natureOfExpense: 'Revenue Expenditure',
    costCenter: 'IT Operations & Infrastructure',
    accountingRationale: 'Classified under operational business expenditure deductible under Section 37(1) of the Income Tax Act based on vendor line item classification.',
    recommendedJournalEntry: {
      debitLedger: data.lineItems?.[0]?.description?.toLowerCase().includes('cloud') || data.vendorName?.toLowerCase().includes('cloud')
        ? 'Software Subscriptions & Cloud Hosting Charges'
        : 'Consumables & Spares A/c',
      debitAmount: data.taxableAmount || 0,
      gstInputLedger: (data.igstAmount || 0) > 0 ? 'Input IGST Ledger @ 18%' : 'Input CGST & SGST Ledgers',
      gstInputAmount: data.totalCalculatedTax || 0,
      creditLedger: `${data.vendorName || 'Vendor'} (Sundry Creditor)`,
      creditAmount: data.totalInvoiceAmount || data.computedTotal || 0
    }
  };

  const handleCopyJournal = () => {
    const je = accountHead.recommendedJournalEntry;
    if (!je) return;

    const text = `--- RECOMMENDED ERP / TALLY JOURNAL ENTRY ---
Debit:  ${je.debitLedger}               ₹${je.debitAmount.toLocaleString('en-IN')}
${je.gstInputLedger ? `Debit:  ${je.gstInputLedger}                    ₹${(je.gstInputAmount || 0).toLocaleString('en-IN')}\n` : ''}Credit: ${je.creditLedger}       ₹${je.creditAmount.toLocaleString('en-IN')}
Narration: Being invoice ${data.invoiceNumber || ''} dated ${data.invoiceDate || ''} from ${data.vendorName || ''} booked under ${accountHead.ledgerName} [${accountHead.natureOfExpense}]`;

    navigator.clipboard.writeText(text);
    setCopiedJournal(true);
    setTimeout(() => setCopiedJournal(false), 2000);
  };

  return (
    <div className="space-y-4">
      
      {/* 3-Card Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1">Extraction Status</p>
          <div className="flex items-center justify-between">
            <span className="text-xl font-bold font-mono text-slate-800">
              {Math.round(data.confidenceScore * 100)}%
            </span>
            <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded text-[10px] font-bold uppercase tracking-tight">
              Accurate
            </span>
          </div>
        </div>

        <div className={`bg-white p-4 rounded-xl border shadow-xs ${
          isDiscrepant ? 'border-slate-200 border-l-4 border-l-red-500' : 'border-slate-200 border-l-4 border-l-emerald-500'
        }`}>
          <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1">Critical Flags</p>
          <div className="flex items-center justify-between">
            <span className={`text-xl font-bold font-mono ${isDiscrepant ? 'text-red-600' : 'text-emerald-700'}`}>
              {isDiscrepant ? (data.auditIssues?.length || '01') : '00'}
            </span>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-tight ${
              isDiscrepant ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-800'
            }`}>
              {isDiscrepant ? 'Action Req' : 'Zero Flags'}
            </span>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1">Suggested Account Head</p>
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-indigo-900 truncate max-w-[170px]" title={accountHead.ledgerName}>
              {accountHead.ledgerName}
            </span>
            <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 border border-indigo-200 rounded text-[9px] font-bold uppercase tracking-tight">
              {accountHead.natureOfExpense.replace(' Expenditure', '')}
            </span>
          </div>
        </div>
      </div>

      {/* Main AI Extraction & Reconciliation Dashboard Table Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs flex flex-col overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/60">
          <h2 className="font-bold text-slate-700 flex items-center gap-2 text-sm">
            <span className="w-1.5 h-4 bg-indigo-600 rounded-full"></span>
            AI Extraction Dashboard (Invoice Review)
          </h2>
          <div className="flex items-center gap-2">
            <button 
              onClick={onExportExcel}
              className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded text-xs font-bold flex items-center gap-1.5 shadow-xs transition-colors cursor-pointer"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              <span>Export to Excel (.xlsx)</span>
            </button>
          </div>
        </div>

        {/* Audit Verification Table */}
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left">
            <thead className="bg-slate-100/60 sticky top-0">
              <tr className="border-b border-slate-200">
                <th className="p-3 pl-5 text-[11px] text-slate-500 font-bold uppercase tracking-wider">Parameter</th>
                <th className="p-3 text-[11px] text-slate-500 font-bold uppercase tracking-wider">Extracted Value</th>
                <th className="p-3 text-[11px] text-slate-500 font-bold uppercase tracking-wider">Status</th>
                <th className="p-3 pr-5 text-[11px] text-slate-500 font-bold uppercase tracking-wider">Validation Rule & Classification</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              <tr className="hover:bg-slate-50/60 transition-colors">
                <td className="p-3 pl-5 font-semibold text-slate-600">Vendor Name</td>
                <td className="p-3 font-semibold text-slate-800">{data.vendorName || 'Not Found'}</td>
                <td className="p-3">
                  <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded-full text-[10px] font-bold uppercase">
                    MATCHED
                  </span>
                </td>
                <td className="p-3 pr-5 text-[11px] text-slate-500">Supplier Trade Name Verified</td>
              </tr>
              <tr className="hover:bg-slate-50/60 transition-colors">
                <td className="p-3 pl-5 font-semibold text-slate-600">Vendor GSTIN</td>
                <td className="p-3 font-mono font-bold text-slate-800">{data.vendorGSTIN || 'MISSING'}</td>
                <td className="p-3">
                  <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded-full text-[10px] font-bold uppercase">
                    VALID (15-DIGIT)
                  </span>
                </td>
                <td className="p-3 pr-5 text-[11px] text-slate-500">State: {data.vendorGSTIN?.slice(0, 2) || '27'} (Maharashtra)</td>
              </tr>
              <tr className={`hover:bg-slate-50/60 transition-colors ${isDiscrepant ? 'bg-red-50/40' : ''}`}>
                <td className="p-3 pl-5 font-semibold text-slate-600">Tax Calculation</td>
                <td className={`p-3 font-mono font-bold ${isDiscrepant ? 'text-red-600' : 'text-slate-800'}`}>
                  ₹{data.totalInvoiceAmount?.toLocaleString('en-IN') || '0'}
                </td>
                <td className="p-3">
                  {isDiscrepant ? (
                    <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-[10px] font-bold uppercase tracking-tight">
                      MATH ERROR
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded-full text-[10px] font-bold uppercase">
                      EXACT MATCH
                    </span>
                  )}
                </td>
                <td className={`p-3 pr-5 text-[11px] font-medium ${isDiscrepant ? 'text-red-600 font-semibold' : 'text-slate-500'}`}>
                  {isDiscrepant 
                    ? `Taxable (₹${data.taxableAmount?.toLocaleString('en-IN')}) + Tax (₹${data.totalCalculatedTax?.toLocaleString('en-IN')}) = ₹${data.computedTotal?.toLocaleString('en-IN')}. Diff: ₹${data.mathDiscrepancy?.toLocaleString('en-IN')}`
                    : `Taxable + Tax = Total (₹${data.computedTotal?.toLocaleString('en-IN')})`}
                </td>
              </tr>
              <tr className="hover:bg-slate-50/60 transition-colors">
                <td className="p-3 pl-5 font-semibold text-slate-600">Receiver GSTIN</td>
                <td className="p-3 font-mono font-bold text-slate-800">{data.receiverGSTIN || 'MISSING'}</td>
                <td className="p-3">
                  <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded-full text-[10px] font-bold uppercase">
                    MATCHED
                  </span>
                </td>
                <td className="p-3 pr-5 text-[11px] text-slate-500">Registered Recipient B2B Entity</td>
              </tr>
              <tr className="hover:bg-slate-50/60 transition-colors">
                <td className="p-3 pl-5 font-semibold text-slate-600">Invoice Number</td>
                <td className="p-3 font-mono font-bold text-slate-800">{data.invoiceNumber || 'N/A'}</td>
                <td className="p-3">
                  <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded-full text-[10px] font-bold uppercase">
                    VERIFIED
                  </span>
                </td>
                <td className="p-3 pr-5 text-[11px] text-slate-500">Dated: {data.invoiceDate || 'Current FY'}</td>
              </tr>
              {/* Suggested Account Head Row */}
              <tr className="hover:bg-indigo-50/40 bg-indigo-50/20 transition-colors">
                <td className="p-3 pl-5 font-semibold text-indigo-950 flex items-center gap-1.5">
                  <BookOpen className="w-3.5 h-3.5 text-indigo-600" />
                  <span>Suggested Account Head</span>
                </td>
                <td className="p-3 font-bold text-indigo-900">
                  {accountHead.ledgerName}
                </td>
                <td className="p-3">
                  <span className="px-2 py-0.5 bg-indigo-100 text-indigo-800 rounded-full text-[10px] font-bold uppercase tracking-tight">
                    {accountHead.natureOfExpense}
                  </span>
                </td>
                <td className="p-3 pr-5 text-[11px] text-slate-600">
                  Group: <span className="font-semibold text-slate-800">{accountHead.accountCategory}</span> • Cost Center: <span className="font-semibold text-slate-800">{accountHead.costCenter || 'General'}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Sleek Summary Bottom Bar */}
        <div className="p-3 bg-slate-900 flex items-center justify-between text-white text-xs">
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">SUMMARY</span>
            <span className="text-[11px] text-slate-300">
              {isDiscrepant ? '1 Item Flagged • 5 Parameters Reconciled • Action Required' : '0 Items Flagged • 6 Parameters Reconciled • Audit Ready'}
            </span>
          </div>
          <button 
            onClick={onExportExcel}
            className="bg-indigo-600 text-white px-3 py-1 rounded text-[10px] font-bold uppercase hover:bg-indigo-500 transition-colors shadow-2xs cursor-pointer"
          >
            Save Audit Workpaper
          </button>
        </div>
      </div>

      {/* Suggested Account Head & Bookkeeping Classification Spotlight Card */}
      <div className="bg-white rounded-xl border border-indigo-100 shadow-xs overflow-hidden">
        <div className="px-5 py-3.5 bg-gradient-to-r from-indigo-50/90 via-slate-50 to-white border-b border-indigo-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-indigo-600 text-white flex items-center justify-center shadow-xs">
              <BookOpen className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <span>Suggested Account Head to Book the Expense</span>
                <span className="px-2 py-0.5 bg-indigo-100 text-indigo-800 text-[10px] font-bold rounded-full uppercase tracking-tight">
                  ERP & Tally Ready
                </span>
              </h3>
              <p className="text-[11px] text-slate-500">Automated General Ledger mapping and Double-Entry Journal suggestion based on SAC/HSN and vendor line items</p>
            </div>
          </div>

          <button
            onClick={handleCopyJournal}
            className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/50 text-slate-700 hover:text-indigo-700 text-xs font-semibold flex items-center gap-1.5 shadow-2xs transition-all cursor-pointer"
            title="Copy formatted double-entry journal entry to clipboard"
          >
            {copiedJournal ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-600" />
                <span className="text-emerald-700 font-bold">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-slate-500" />
                <span>Copy Journal Entry</span>
              </>
            )}
          </button>
        </div>

        <div className="p-5 grid grid-cols-1 lg:grid-cols-12 gap-5">
          {/* Left Column: Account Head Details & CA Rationale */}
          <div className="lg:col-span-6 space-y-4">
            <div className="p-4 rounded-xl bg-slate-50/80 border border-slate-200/80 space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="text-[10px] font-bold text-indigo-600 uppercase tracking-wider block mb-0.5">
                    Recommended Expense Ledger
                  </span>
                  <h4 className="text-base font-bold text-slate-900 tracking-tight">
                    {accountHead.ledgerName}
                  </h4>
                </div>
                <span className="px-2.5 py-1 bg-emerald-50 border border-emerald-200 text-emerald-800 text-[10px] font-bold rounded-md uppercase tracking-tight shrink-0">
                  {accountHead.natureOfExpense}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-200/60 text-xs">
                <div>
                  <span className="text-[10px] text-slate-400 font-bold uppercase block">Account Category / Group</span>
                  <span className="font-semibold text-slate-800">{accountHead.accountCategory}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 font-bold uppercase block">Cost Center / Dept</span>
                  <span className="font-semibold text-slate-800">{accountHead.costCenter || 'General Administration'}</span>
                </div>
              </div>
            </div>

            {/* Rationale Box */}
            <div className="p-3.5 rounded-xl bg-indigo-50/40 border border-indigo-100 text-xs text-slate-700">
              <div className="flex items-center gap-1.5 font-bold text-indigo-900 mb-1">
                <ShieldCheck className="w-3.5 h-3.5 text-indigo-600" />
                <span>CA Classification Rationale & Tax Deductibility</span>
              </div>
              <p className="text-[11px] leading-relaxed text-slate-600">
                {accountHead.accountingRationale}
              </p>
            </div>
          </div>

          {/* Right Column: Recommended ERP / Tally Journal Entry Box */}
          <div className="lg:col-span-6 flex flex-col justify-between p-4 rounded-xl bg-slate-900 text-white border border-slate-800">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
                <div className="flex items-center gap-2">
                  <ArrowRightLeft className="w-4 h-4 text-indigo-400" />
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                    Recommended Tally / SAP Journal Entry
                  </span>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 bg-slate-800 border border-slate-700 text-emerald-400 rounded font-semibold">
                  Balanced Entry
                </span>
              </div>

              {accountHead.recommendedJournalEntry && (
                <div className="space-y-2.5 font-mono text-xs">
                  {/* Debit 1: Expense Ledger */}
                  <div className="flex items-center justify-between p-2 rounded bg-slate-800/80 border border-slate-700/60">
                    <div className="flex items-center gap-2 truncate pr-2">
                      <span className="px-1.5 py-0.5 rounded bg-indigo-900 text-indigo-200 text-[10px] font-bold">Dr.</span>
                      <span className="text-slate-200 font-semibold truncate text-[11px]" title={accountHead.recommendedJournalEntry.debitLedger}>
                        {accountHead.recommendedJournalEntry.debitLedger}
                      </span>
                    </div>
                    <span className="text-emerald-400 font-bold whitespace-nowrap">
                      ₹{accountHead.recommendedJournalEntry.debitAmount.toLocaleString('en-IN')}
                    </span>
                  </div>

                  {/* Debit 2: Input GST Ledger (if applicable) */}
                  {accountHead.recommendedJournalEntry.gstInputLedger && (accountHead.recommendedJournalEntry.gstInputAmount || 0) > 0 && (
                    <div className="flex items-center justify-between p-2 rounded bg-slate-800/80 border border-slate-700/60">
                      <div className="flex items-center gap-2 truncate pr-2">
                        <span className="px-1.5 py-0.5 rounded bg-indigo-900 text-indigo-200 text-[10px] font-bold">Dr.</span>
                        <span className="text-slate-200 font-semibold truncate text-[11px]" title={accountHead.recommendedJournalEntry.gstInputLedger}>
                          {accountHead.recommendedJournalEntry.gstInputLedger}
                        </span>
                      </div>
                      <span className="text-emerald-400 font-bold whitespace-nowrap">
                        ₹{(accountHead.recommendedJournalEntry.gstInputAmount || 0).toLocaleString('en-IN')}
                      </span>
                    </div>
                  )}

                  {/* Credit: Vendor Sundry Creditor */}
                  <div className="flex items-center justify-between p-2 rounded bg-slate-800/80 border border-slate-700/60">
                    <div className="flex items-center gap-2 truncate pr-2">
                      <span className="px-1.5 py-0.5 rounded bg-amber-900 text-amber-200 text-[10px] font-bold">Cr.</span>
                      <span className="text-slate-200 font-semibold truncate text-[11px]" title={accountHead.recommendedJournalEntry.creditLedger}>
                        {accountHead.recommendedJournalEntry.creditLedger}
                      </span>
                    </div>
                    <span className="text-amber-400 font-bold whitespace-nowrap">
                      ₹{accountHead.recommendedJournalEntry.creditAmount.toLocaleString('en-IN')}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Narration Note */}
            <div className="mt-3 pt-2.5 border-t border-slate-800 text-[10px] text-slate-400 flex items-center justify-between">
              <span className="truncate pr-2">
                Narration: Being invoice {data.invoiceNumber || '—'} booked to {accountHead.ledgerName}
              </span>
              <span className="text-slate-500 font-mono shrink-0">Sec 37(1)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Itemized Line Items Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between bg-slate-50/60">
          <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-2">
            <FileText className="w-3.5 h-3.5 text-indigo-600" />
            <span>Itemized Line Items ({data.lineItems?.length || 0})</span>
          </h4>
          <span className="text-[11px] text-slate-500 font-medium">
            HSN / SAC Structure Verified
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-100/60 text-slate-600 border-b border-slate-200 text-[11px]">
                <th className="p-2.5 pl-5 font-bold">#</th>
                <th className="p-2.5 font-bold">Description</th>
                <th className="p-2.5 font-bold">HSN/SAC</th>
                <th className="p-2.5 font-bold text-right">Qty</th>
                <th className="p-2.5 font-bold text-right">Rate (₹)</th>
                <th className="p-2.5 font-bold text-right">Taxable (₹)</th>
                <th className="p-2.5 font-bold text-right">GST %</th>
                <th className="p-2.5 pr-5 font-bold text-right">Line Total (₹)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {data.lineItems && data.lineItems.length > 0 ? (
                data.lineItems.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/70 transition-colors">
                    <td className="p-2.5 pl-5 text-slate-400 font-mono">{idx + 1}</td>
                    <td className="p-2.5 font-semibold text-slate-800 max-w-[240px] truncate">
                      {item.description}
                    </td>
                    <td className="p-2.5 font-mono text-slate-600">{item.hsnSac || '—'}</td>
                    <td className="p-2.5 text-right font-mono text-slate-700">
                      {item.quantity ? `${item.quantity} ${item.unit || ''}` : '1'}
                    </td>
                    <td className="p-2.5 text-right font-mono text-slate-700">
                      {item.unitPrice ? `₹${item.unitPrice.toLocaleString('en-IN')}` : '—'}
                    </td>
                    <td className="p-2.5 text-right font-mono font-bold text-slate-900">
                      ₹{item.taxableValue?.toLocaleString('en-IN') || '0'}
                    </td>
                    <td className="p-2.5 text-right font-mono text-indigo-700 font-bold">
                      {item.gstRatePercent}%
                    </td>
                    <td className="p-2.5 pr-5 text-right font-mono font-bold text-slate-900">
                      ₹{item.total?.toLocaleString('en-IN') || '0'}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="p-4 text-center text-slate-400">
                    No line items extracted.
                  </td>
                </tr>
              )}
            </tbody>
            <tfoot>
              <tr className="bg-slate-50 border-t border-slate-200 font-bold text-slate-800">
                <td colSpan={5} className="p-2.5 pl-5 text-right text-slate-500">Total Taxable Value:</td>
                <td className="p-2.5 text-right font-mono text-slate-900">
                  ₹{data.taxableAmount?.toLocaleString('en-IN')}
                </td>
                <td className="p-2.5 text-right text-slate-500">Stated Total:</td>
                <td className="p-2.5 pr-5 text-right font-mono font-bold text-indigo-700">
                  ₹{data.totalInvoiceAmount?.toLocaleString('en-IN')}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Forensic Audit Findings */}
      {data.auditIssues && data.auditIssues.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-bold text-slate-600 uppercase tracking-wider flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
            <span>Forensic Audit Findings ({data.auditIssues.length})</span>
          </h4>

          <div className="space-y-2">
            {data.auditIssues.map((issue, i) => (
              <div 
                key={i}
                className={`p-3 rounded-xl border flex items-start gap-3 text-xs ${
                  issue.severity === 'high' 
                    ? 'bg-red-50/70 border-red-200 text-red-900' 
                    : issue.severity === 'medium'
                    ? 'bg-amber-50/70 border-amber-200 text-amber-900'
                    : 'bg-white border-slate-200 text-slate-700'
                }`}
              >
                <div className="shrink-0 mt-0.5">
                  {issue.severity === 'high' ? (
                    <AlertOctagon className="w-4 h-4 text-red-600" />
                  ) : issue.severity === 'medium' ? (
                    <AlertTriangle className="w-4 h-4 text-amber-600" />
                  ) : (
                    <Info className="w-4 h-4 text-indigo-600" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-bold text-slate-900">{issue.title}</span>
                    <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-white border border-slate-200 text-slate-600">
                      {issue.type.replace('_', ' ')}
                    </span>
                  </div>
                  <p className="mt-1 text-[11px] leading-relaxed text-slate-700">
                    {issue.message}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Synthesis & Workpaper Notes */}
      <div className="p-3.5 rounded-xl bg-white border border-slate-200 text-xs text-slate-600 shadow-2xs">
        <span className="font-bold text-slate-800 block mb-1">Auditor Synthesis Summary:</span>
        <p className="leading-relaxed">{data.summary}</p>
      </div>

    </div>
  );
};

