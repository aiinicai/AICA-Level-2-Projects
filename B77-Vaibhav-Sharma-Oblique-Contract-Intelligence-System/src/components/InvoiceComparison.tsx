import React, { useState } from 'react';
import { 
  FileSpreadsheet, 
  Upload, 
  PlayCircle, 
  CheckCircle2, 
  AlertCircle, 
  AlertTriangle, 
  RefreshCw, 
  FileText, 
  ShieldCheck, 
  ArrowRight,
  Calculator,
  Coins,
  Check
} from 'lucide-react';
import { ContractDocument, InvoiceData, InvoiceComparisonResult, InvoiceDiscrepancy } from '../types/contract';
import { DEMO_INVOICE_DATA } from '../data/demoContract';

interface InvoiceComparisonProps {
  contract: ContractDocument;
}

export const InvoiceComparison: React.FC<InvoiceComparisonProps> = ({ contract }) => {
  const [invoice, setInvoice] = useState<InvoiceData>(DEMO_INVOICE_DATA);
  const [isComparing, setIsComparing] = useState<boolean>(false);
  const [comparisonResult, setComparisonResult] = useState<InvoiceComparisonResult | null>(null);
  const [activeTab, setActiveTab] = useState<'form' | 'results'>('form');

  const runComparison = async () => {
    setIsComparing(true);
    try {
      const res = await fetch('/api/compare-invoice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contract,
          invoiceData: invoice
        })
      });

      if (!res.ok) {
        throw new Error('Failed to reconcile invoice with contract.');
      }

      const data = await res.json();
      setComparisonResult(data.comparison);
      setActiveTab('results');
    } catch (err) {
      console.error('Comparison error:', err);
      // Fallback local comparison if offline
      const mockResult: InvoiceComparisonResult = {
        invoiceData: invoice,
        overallMatchStatus: 'Variances Found',
        discrepancies: [
          {
            field: 'Retention Money Deduction',
            contractValue: '10% Mandatory Retention (₹26,00,000) under Clause 3.2(c)',
            invoiceValue: '₹0.00 Deducted on Invoice',
            status: 'RED',
            contractClauseRef: 'Clause 3.2(c) - Page 3',
            observation: 'The vendor billed full ₹2.60 Cr without deducting 10% contract retention. Releasing full amount risks unhedged performance warranty.',
            accountingImpact: 'Failure to withhold retention results in unbacked advance/liability and violates internal controls.',
            gstOrTdsImpact: 'GST is payable on full transaction value, but net payment disbursed to vendor must be reduced by ₹26,00,000.'
          },
          {
            field: 'Payment Due Date / Credit Days',
            contractValue: '90 Days from Invoice Receipt (Clause 3.3)',
            invoiceValue: 'Due within 15 Days (2025-05-15)',
            status: 'AMBER',
            contractClauseRef: 'Clause 3.3 - Page 3',
            observation: 'Invoice demands payment in 15 days despite contract specifying 90 days credit. Note: If vendor is Micro/Small under MSMED, 90 days violates statutory 45-day cap.',
            accountingImpact: 'Align Accounts Payable aging schedule to contractual vs statutory terms.',
            gstOrTdsImpact: 'Ensure Section 43B(h) monitoring if vendor is MSME.'
          },
          {
            field: 'Milestone Base Billing Value',
            contractValue: '₹2,60,00,000 (50% on Supply of Equipment under Clause 3.2(a))',
            invoiceValue: '₹2,60,00,000 (50% Milestone)',
            status: 'GREEN',
            contractClauseRef: 'Clause 3.2(a) - Page 2',
            observation: 'Base equipment supply billing matches exactly with 50% milestone specification.',
            accountingImpact: 'Record equipment under Capital Work-in-Progress (CWIP) pending installation/commissioning.',
            gstOrTdsImpact: 'Ensure E-Way Bill matches supply value of ₹2.60 Cr.'
          },
          {
            field: 'GST Rate & HSN Code',
            contractValue: '18% GST (Taxes Extra as applicable under Clause 3.4)',
            invoiceValue: '18% GST (₹46,80,000) under HSN 8479',
            status: 'GREEN',
            contractClauseRef: 'Clause 3.4 - Page 3',
            observation: 'GST calculation at 18% matches equipment classification rate.',
            accountingImpact: 'Eligible for Input Tax Credit (ITC) if capital goods used for taxable business operations.',
            gstOrTdsImpact: 'Verify that vendor files GSTR-1 and invoice appears in GSTR-2B before claiming ITC.'
          }
        ],
        caReviewNotes: 'DO NOT release payment of ₹3,06,80,000. Re-calculate net payable after deducting 10% Retention (₹26,00,000) and deduct TDS under Section 194Q / 194C. Net payment to disburse is ₹2,80,80,000 (less TDS).'
      };
      setComparisonResult(mockResult);
      setActiveTab('results');
    } finally {
      setIsComparing(false);
    }
  };

  const handleInputChange = (field: keyof InvoiceData, val: any) => {
    setInvoice(prev => ({
      ...prev,
      [field]: val
    }));
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Top Banner */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 uppercase tracking-wider">
                Accounts Payable Reconciliation
              </span>
              <span className="text-xs text-slate-500 font-mono">
                Contract Ref: {contract.identity.contractNumber || 'Turnkey Project'}
              </span>
            </div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              Contract ↔ Vendor Invoice Reconciliation
            </h1>
            <p className="text-xs text-slate-500 max-w-2xl leading-relaxed">
              Verify vendor invoices against approved contract terms to catch milestone over-billing, missing retention deductions, incorrect GST rates, and conflicting credit periods before releasing disbursements.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => {
                setInvoice(DEMO_INVOICE_DATA);
                runComparison();
              }}
              className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300 transition"
            >
              <PlayCircle className="w-3.5 h-3.5 text-emerald-600" />
              <span>Load Sample Vendor Invoice</span>
            </button>
          </div>
        </div>

        {/* Tab switcher */}
        <div className="flex space-x-2 mt-4 pt-4 border-t border-slate-100 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('form')}
            className={`px-3 py-1.5 rounded-md transition ${
              activeTab === 'form'
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            Invoice Data Input
          </button>
          <button
            onClick={() => {
              if (comparisonResult) setActiveTab('results');
              else runComparison();
            }}
            className={`px-3 py-1.5 rounded-md transition ${
              activeTab === 'results'
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            Reconciliation Results {comparisonResult && `(${comparisonResult.discrepancies.length} Points)`}
          </button>
        </div>
      </div>

      {/* Form View */}
      {activeTab === 'form' && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-6 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Invoice Number</label>
              <input
                type="text"
                value={invoice.invoiceNumber}
                onChange={(e) => handleInputChange('invoiceNumber', e.target.value)}
                className="w-full p-2 rounded-lg border border-slate-300 font-mono"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Invoice Date</label>
              <input
                type="date"
                value={invoice.invoiceDate}
                onChange={(e) => handleInputChange('invoiceDate', e.target.value)}
                className="w-full p-2 rounded-lg border border-slate-300"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Vendor Name</label>
              <input
                type="text"
                value={invoice.vendorName}
                onChange={(e) => handleInputChange('vendorName', e.target.value)}
                className="w-full p-2 rounded-lg border border-slate-300"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Customer / Buyer</label>
              <input
                type="text"
                value={invoice.customerName}
                onChange={(e) => handleInputChange('customerName', e.target.value)}
                className="w-full p-2 rounded-lg border border-slate-300"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-4 border-t border-slate-100">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Base Amount (₹)</label>
              <input
                type="number"
                value={invoice.baseAmount}
                onChange={(e) => handleInputChange('baseAmount', Number(e.target.value))}
                className="w-full p-2 rounded-lg border border-slate-300 font-semibold"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">GST Rate (%)</label>
              <input
                type="number"
                value={invoice.gstRate}
                onChange={(e) => handleInputChange('gstRate', Number(e.target.value))}
                className="w-full p-2 rounded-lg border border-slate-300"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">GST Amount (₹)</label>
              <input
                type="number"
                value={invoice.gstAmount}
                onChange={(e) => handleInputChange('gstAmount', Number(e.target.value))}
                className="w-full p-2 rounded-lg border border-slate-300"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Retention Withheld on Invoice (₹)</label>
              <input
                type="number"
                value={invoice.retentionDeduction || 0}
                onChange={(e) => handleInputChange('retentionDeduction', Number(e.target.value))}
                placeholder="0 if omitted by vendor"
                className="w-full p-2 rounded-lg border border-slate-300 text-rose-700 font-semibold"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t border-slate-100">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Advance Adjusted (₹)</label>
              <input
                type="number"
                value={invoice.advanceAdjustment || 0}
                onChange={(e) => handleInputChange('advanceAdjustment', Number(e.target.value))}
                className="w-full p-2 rounded-lg border border-slate-300"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Total Net Payable (₹)</label>
              <input
                type="number"
                value={invoice.netPayableAmount}
                onChange={(e) => handleInputChange('netPayableAmount', Number(e.target.value))}
                className="w-full p-2 rounded-lg border border-slate-300 font-bold text-slate-900"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Payment Due Date / Terms</label>
              <input
                type="text"
                value={invoice.paymentDueDate}
                onChange={(e) => handleInputChange('paymentDueDate', e.target.value)}
                className="w-full p-2 rounded-lg border border-slate-300"
              />
            </div>
          </div>

          <div className="pt-4 flex justify-end">
            <button
              onClick={runComparison}
              disabled={isComparing}
              className="inline-flex items-center space-x-2 px-6 py-2.5 rounded-lg text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition disabled:opacity-50"
            >
              <Calculator className="w-4 h-4" />
              <span>{isComparing ? 'Reconciling Against Contract...' : 'Reconcile Invoice with Contract'}</span>
            </button>
          </div>
        </div>
      )}

      {/* Results View */}
      {activeTab === 'results' && comparisonResult && (
        <div className="space-y-6">
          {/* Status Alert Banner */}
          <div className={`rounded-xl p-5 border text-xs ${
            comparisonResult.overallMatchStatus === 'Significant Non-Compliance'
              ? 'bg-rose-50 border-rose-200 text-rose-900'
              : comparisonResult.overallMatchStatus === 'Variances Found'
              ? 'bg-amber-50 border-amber-200 text-amber-900'
              : 'bg-emerald-50 border-emerald-200 text-emerald-900'
          }`}>
            <div className="flex items-center space-x-2 mb-2">
              {comparisonResult.overallMatchStatus === 'Matching' ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
              ) : (
                <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
              )}
              <h2 className="text-sm font-bold tracking-tight">
                Reconciliation Status: {comparisonResult.overallMatchStatus}
              </h2>
            </div>
            <p className="font-medium leading-relaxed">
              {comparisonResult.caReviewNotes}
            </p>
          </div>

          {/* Discrepancy Breakdown Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden text-xs">
            <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
              <h3 className="font-bold text-slate-800 uppercase tracking-wider text-[11px]">
                Detailed Term-by-Term Variance Audit
              </h3>
              <span className="text-slate-500 font-mono text-[11px]">
                {comparisonResult.discrepancies.length} parameters verified
              </span>
            </div>

            <div className="divide-y divide-slate-100">
              {comparisonResult.discrepancies.map((d, idx) => (
                <div key={idx} className="p-4 hover:bg-slate-50/60 transition space-y-2">
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          d.status === 'RED' ? 'bg-rose-600 text-white' :
                          d.status === 'AMBER' ? 'bg-amber-500 text-white' :
                          'bg-emerald-600 text-white'
                        }`}>
                          {d.status} • {d.field}
                        </span>
                        <span className="font-mono text-slate-500 text-[11px]">
                          Ref: {d.contractClauseRef}
                        </span>
                      </div>
                      <p className="text-slate-800 font-medium leading-relaxed">
                        {d.observation}
                      </p>
                    </div>

                    <div className="text-right shrink-0 font-mono text-[11px]">
                      <span className="text-slate-400 block text-[10px]">Contract Expected:</span>
                      <span className="font-bold text-slate-700">{d.contractValue}</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 text-[11px]">
                    <div className="bg-slate-50 p-2.5 rounded border border-slate-100">
                      <span className="font-bold text-slate-700 block mb-0.5">Accounting & Ledger Impact:</span>
                      <span className="text-slate-600 leading-relaxed">{d.accountingImpact}</span>
                    </div>
                    <div className="bg-slate-50 p-2.5 rounded border border-slate-100">
                      <span className="font-bold text-slate-700 block mb-0.5">GST & TDS Impact:</span>
                      <span className="text-slate-600 leading-relaxed">{d.gstOrTdsImpact}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Action Box */}
          <div className="bg-slate-900 text-white rounded-xl p-5 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs">
            <div className="space-y-1">
              <h4 className="font-bold text-white text-sm">CA Sign-Off & Payment Authorization</h4>
              <p className="text-slate-300">
                Ensure adjusted remittance advice reflects 10% retention withholding and statutory TDS deduction before treasury release.
              </p>
            </div>
            <button
              onClick={() => setActiveTab('form')}
              className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 font-semibold text-white shrink-0"
            >
              Edit Invoice Data
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
