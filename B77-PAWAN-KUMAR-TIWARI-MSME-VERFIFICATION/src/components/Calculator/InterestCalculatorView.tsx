import React, { useState } from 'react';
import {
  Calculator,
  Search,
  Download,
  Calendar,
  Percent,
  FileSpreadsheet,
  FileText,
  AlertOctagon,
  Clock,
  Sparkles,
  ChevronDown,
  ChevronRight,
  ShieldCheck,
  Plus,
  Trash2,
  X,
  Info,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { InvoiceInterestResult } from '../../types';
import { formatINR, formatDate } from '../../utils/formatters';
import { calculateInvoiceInterest } from '../../utils/calculator';
import { exportTableToExcel } from '../../utils/excelService';
import { exportInterestCalculationPDF } from '../../utils/pdfService';

export const InterestCalculatorView: React.FC = () => {
  const {
    invoiceCalculations,
    vendors,
    asOfDate,
    rateMaster,
    statutoryRules,
    selectedFinancialYear,
  } = useApp();

  const [activeTabMode, setActiveTabMode] = useState<'register' | 'sandbox'>('register');
  const [searchTerm, setSearchTerm] = useState('');
  const [vendorFilter, setVendorFilter] = useState('ALL');
  const [selectedCalcModal, setSelectedCalcModal] = useState<InvoiceInterestResult | null>(null);

  const filteredCalculations = invoiceCalculations.filter((c) => {
    const matchesSearch =
      c.invoiceNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.vendorName.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesVendor = vendorFilter === 'ALL' || c.vendorId === vendorFilter;
    return matchesSearch && matchesVendor;
  });

  const totalCalculatedInterest = filteredCalculations.reduce((sum, c) => sum + c.totalInterestPayable, 0);
  const totalPrincipalOverdue = filteredCalculations.reduce((sum, c) => (c.isOverdue ? sum + c.outstandingPrincipal : sum), 0);

  const currentRate = rateMaster[0] || { referenceRate: 6.5, applicableMSMERate: 19.5 };

  const handleExportExcel = () => {
    const exportData = filteredCalculations.map((c) => ({
      'Invoice No': c.invoiceNumber,
      Vendor: c.vendorName,
      Category: c.msmeCategory,
      'Invoice Date': formatDate(c.invoiceDate),
      'Statutory Due Date': formatDate(c.finalDueDate),
      'Calculation As-Of Date': formatDate(c.asOfDate),
      'Delay (Days)': c.totalDelayDays,
      'Total Invoice Amount (₹)': c.totalInvoiceAmount,
      'Paid Amount (₹)': c.totalPaid,
      'Outstanding Principal (₹)': c.outstandingPrincipal,
      'Monthly Compounded Interest (₹)': c.totalInterestPayable,
      'Applicable Rate (%)': `${c.applicableAnnualRate}% (3x RBI)`,
      'Sec 43B(h) Risk': c.section43BHRisk ? 'YES' : 'NO',
      Status: c.isOverdue ? 'OVERDUE' : 'NOT OVERDUE',
    }));
    exportTableToExcel(exportData, 'MSME_Statutory_Interest_Schedule', 'Interest Schedule');
  };

  const handleExportPDF = () => {
    exportInterestCalculationPDF(
      filteredCalculations,
      asOfDate,
      `RBI ${currentRate.referenceRate}% × 3 = ${currentRate.applicableMSMERate}% p.a. (Monthly Compounding)`
    );
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900">
            MSME Statutory Delayed Payment Interest Calculator
          </h2>
          <p className="text-xs text-slate-500">
            MSMED Act 2006 (Section 15 & 16) compound interest engine with monthly rest & reducing tranche balances
          </p>
        </div>

        {/* View Switcher & Export */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="bg-slate-100 p-1 rounded-lg flex items-center gap-1 border border-slate-200">
            <button
              onClick={() => setActiveTabMode('register')}
              className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all cursor-pointer ${
                activeTabMode === 'register'
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Portfolio Schedule ({invoiceCalculations.length})
            </button>
            <button
              onClick={() => setActiveTabMode('sandbox')}
              className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all flex items-center gap-1 cursor-pointer ${
                activeTabMode === 'sandbox'
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
              Interactive What-If Sandbox
            </button>
          </div>

          <button
            onClick={handleExportExcel}
            className="px-3 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg shadow-xs flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
            Excel
          </button>
          <button
            onClick={handleExportPDF}
            className="px-3 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold rounded-lg shadow-xs flex items-center gap-1.5 transition-all cursor-pointer"
          >
            <FileText className="w-3.5 h-3.5 text-rose-400" />
            Statutory PDF
          </button>
        </div>
      </div>

      {activeTabMode === 'sandbox' ? (
        <InteractiveSandbox
          rateMaster={rateMaster}
          statutoryRules={statutoryRules}
          asOfDate={asOfDate}
        />
      ) : (
        <>
          {/* Statutory Formula Summary Banner */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs">
              <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">Applicable Rate (Sec 16)</div>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-2xl font-black text-slate-900">{currentRate.applicableMSMERate}%</span>
                <span className="text-xs text-slate-500 font-semibold">per annum</span>
              </div>
              <div className="text-[11px] text-emerald-700 mt-1 font-semibold">
                RBI Reference {currentRate.referenceRate}% × 3 (Monthly Compounding)
              </div>
            </div>

            <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs">
              <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">Overdue Principal Exposure</div>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-2xl font-black text-rose-700">{formatINR(totalPrincipalOverdue)}</span>
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                Across {filteredCalculations.filter((c) => c.isOverdue).length} overdue invoices as of {formatDate(asOfDate)}
              </div>
            </div>

            <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs">
              <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">Total Statutory Interest</div>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-2xl font-black text-rose-700">{formatINR(totalCalculatedInterest)}</span>
              </div>
              <div className="text-[11px] text-rose-600 mt-1 font-semibold flex items-center gap-1">
                <AlertOctagon className="w-3.5 h-3.5" /> Mandatory under Section 16 (Non-deductible)
              </div>
            </div>
          </div>

          {/* Search and Filters */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col md:flex-row items-center justify-between gap-3">
            <div className="relative w-full md:w-80">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search invoice number, vendor..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-hidden focus:bg-white focus:border-emerald-500"
              />
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-semibold">Vendor Filter:</span>
              <select
                value={vendorFilter}
                onChange={(e) => setVendorFilter(e.target.value)}
                className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-700 max-w-[220px]"
              >
                <option value="ALL">All MSME Vendors ({vendors.length})</option>
                {vendors.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.vendorName}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Calculations Master Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase text-[10px] font-bold tracking-wider">
                  <tr>
                    <th className="px-4 py-3">Invoice / Vendor</th>
                    <th className="px-4 py-3">Category</th>
                    <th className="px-4 py-3">Due Date & Delay</th>
                    <th className="px-4 py-3 text-right">Principal Outstanding</th>
                    <th className="px-4 py-3 text-right">Compounded Interest</th>
                    <th className="px-4 py-3 text-center">43B(h) Risk</th>
                    <th className="px-4 py-3 text-right">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredCalculations.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                        No invoice calculation records found.
                      </td>
                    </tr>
                  ) : (
                    filteredCalculations.map((calc) => (
                      <tr key={calc.invoiceId} className="hover:bg-slate-50/80 transition-colors">
                        <td className="px-4 py-3.5">
                          <div className="font-bold text-slate-900">{calc.invoiceNumber}</div>
                          <div className="text-[11px] text-slate-500 truncate max-w-[200px]">{calc.vendorName}</div>
                          <div className="text-[10px] text-slate-400">Inv Date: {formatDate(calc.invoiceDate)}</div>
                        </td>

                        <td className="px-4 py-3.5">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              calc.msmeCategory === 'Micro'
                                ? 'bg-blue-100 text-blue-800'
                                : calc.msmeCategory === 'Small'
                                ? 'bg-teal-100 text-teal-800'
                                : calc.msmeCategory === 'Medium'
                                ? 'bg-amber-100 text-amber-800'
                                : 'bg-slate-100 text-slate-600'
                            }`}
                          >
                            {calc.msmeCategory}
                          </span>
                        </td>

                        <td className="px-4 py-3.5">
                          <div className="font-semibold text-slate-800">{formatDate(calc.finalDueDate)}</div>
                          {calc.isOverdue ? (
                            <span className="text-[10px] font-bold text-rose-700 bg-rose-50 px-1.5 py-0.2 rounded inline-block mt-0.5">
                              🔴 {calc.totalDelayDays} Days Overdue
                            </span>
                          ) : (
                            <span className="text-[10px] font-semibold text-emerald-700 mt-0.5 inline-block">
                              🟢 Not Overdue
                            </span>
                          )}
                        </td>

                        <td className="px-4 py-3.5 text-right font-bold text-slate-900">
                          {formatINR(calc.outstandingPrincipal)}
                          {calc.totalPaid > 0 && (
                            <div className="text-[10px] text-emerald-600">Paid: {formatINR(calc.totalPaid)}</div>
                          )}
                        </td>

                        <td className="px-4 py-3.5 text-right">
                          <div className={`font-bold text-sm ${calc.totalInterestPayable > 0 ? 'text-rose-700' : 'text-slate-400'}`}>
                            {formatINR(calc.totalInterestPayable)}
                          </div>
                          <div className="text-[10px] text-slate-400 font-mono">
                            @{calc.applicableAnnualRate}% p.a.
                          </div>
                        </td>

                        <td className="px-4 py-3.5 text-center">
                          {calc.section43BHRisk ? (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-rose-100 text-rose-800 border border-rose-200">
                              Risk Active
                            </span>
                          ) : (
                            <span className="text-slate-400 text-[10px]">—</span>
                          )}
                        </td>

                        <td className="px-4 py-3.5 text-right">
                          <button
                            onClick={() => setSelectedCalcModal(calc)}
                            className="px-2.5 py-1 bg-white border border-slate-300 hover:bg-slate-100 text-slate-700 font-bold rounded-lg text-xs transition-colors cursor-pointer"
                          >
                            Breakdown
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* Step-by-Step Compounding Breakdown Modal */}
      {selectedCalcModal && (
        <CompoundingBreakdownModal
          calculation={selectedCalcModal}
          onClose={() => setSelectedCalcModal(null)}
        />
      )}
    </div>
  );
};

/* --- Interactive What-If Sandbox Component --- */
const InteractiveSandbox: React.FC<{
  rateMaster: any[];
  statutoryRules: any;
  asOfDate: string;
}> = ({ rateMaster, statutoryRules, asOfDate }) => {
  const [invoiceAmount, setInvoiceAmount] = useState(1000000);
  const [mrnDate, setMrnDate] = useState('2026-04-01');
  const [acceptanceDate, setAcceptanceDate] = useState('2026-04-05');
  const [hasAgreement, setHasAgreement] = useState(true);
  const [agreedDays, setAgreedDays] = useState(45);
  const [cutoffDate, setCutoffDate] = useState(asOfDate);
  const [category, setCategory] = useState<'Micro' | 'Small' | 'Medium'>('Micro');

  // Custom Tranches in sandbox
  const [payments, setPayments] = useState<{ id: string; date: string; amount: number; ref: string }[]>([
    { id: '1', date: '2026-06-15', amount: 400000, ref: 'Payment 1' },
    { id: '2', date: '2026-07-20', amount: 300000, ref: 'Payment 2' },
  ]);

  const addTranche = () => {
    setPayments([
      ...payments,
      {
        id: String(Date.now()),
        date: cutoffDate,
        amount: 200000,
        ref: `Payment ${payments.length + 1}`,
      },
    ]);
  };

  const removeTranche = (id: string) => {
    setPayments(payments.filter((p) => p.id !== id));
  };

  const updateTranche = (id: string, field: string, val: any) => {
    setPayments(payments.map((p) => (p.id === id ? { ...p, [field]: val } : p)));
  };

  // Mock invoice for calculator
  const mockInvoice: any = {
    id: 'SANDBOX-001',
    vendorId: 'V-SANDBOX',
    vendorName: 'Sandbox Simulated MSME Enterprise',
    vendorCode: 'V-SIM-01',
    msmeCategory: category,
    isMSME: true,
    invoiceNumber: 'SIM/INV/2026/01',
    invoiceDate: mrnDate,
    invoiceAmount: invoiceAmount,
    gstAmount: Math.round(invoiceAmount * 0.18),
    totalInvoiceAmount: Math.round(invoiceAmount * 1.18),
    poNumber: 'SIM/PO/01',
    poDate: mrnDate,
    materialDescription: 'Simulation Test Batch',
    mrnDate,
    acceptanceDate,
    deemedAcceptanceDate: acceptanceDate,
    hasWrittenAgreement: hasAgreement,
    agreedPaymentTerms: `${agreedDays} Days`,
    creditDays: agreedDays,
    statutoryLimitDays: hasAgreement ? statutoryRules.maxCreditDaysWithAgreement : statutoryRules.maxCreditDaysWithoutAgreement,
    finalDueDate: '2026-05-20',
    amountPaid: payments.reduce((s, p) => s + p.amount, 0),
    outstandingAmount: Math.max(0, Math.round(invoiceAmount * 1.18) - payments.reduce((s, p) => s + p.amount, 0)),
    status: 'Unpaid',
    payments: payments.map((p) => ({
      id: p.id,
      invoiceId: 'SANDBOX-001',
      paymentDate: p.date,
      amount: p.amount,
      paymentMode: 'NEFT',
      paymentReference: p.ref,
      recordedBy: 'Simulation Engine',
      recordedAt: new Date().toISOString(),
    })),
    disputeFlag: false,
    financialYear: '2026-27',
  };

  const result = calculateInvoiceInterest(mockInvoice, rateMaster, statutoryRules, cutoffDate);

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-emerald-600" />
            <h3 className="font-bold text-slate-800 text-base">What-If MSME Interest Sandbox</h3>
          </div>
          <span className="text-xs text-slate-500">Test hypothetical scenarios with part payments</span>
        </div>

        {/* Inputs */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
          <div>
            <label className="block font-bold text-slate-700 mb-1">Invoice Basic Amount (₹)</label>
            <input
              type="number"
              value={invoiceAmount}
              onChange={(e) => setInvoiceAmount(Number(e.target.value))}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono font-bold"
            />
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">MSME Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value as any)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg font-semibold"
            >
              <option value="Micro">Micro Enterprise</option>
              <option value="Small">Small Enterprise</option>
              <option value="Medium">Medium Enterprise</option>
            </select>
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">Material Receipt / MRN Date</label>
            <input
              type="date"
              value={mrnDate}
              onChange={(e) => setMrnDate(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg"
            />
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">Acceptance Date</label>
            <input
              type="date"
              value={acceptanceDate}
              onChange={(e) => setAcceptanceDate(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs bg-slate-50 p-4 rounded-xl border border-slate-200">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="sbAgr"
              checked={hasAgreement}
              onChange={(e) => setHasAgreement(e.target.checked)}
              className="rounded border-slate-300 text-emerald-600"
            />
            <label htmlFor="sbAgr" className="font-semibold text-slate-800 cursor-pointer">
              Has Written Agreement / PO
            </label>
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">Agreed Credit Days</label>
            <input
              type="number"
              value={agreedDays}
              onChange={(e) => setAgreedDays(Number(e.target.value))}
              className="w-full px-3 py-1.5 border border-slate-300 rounded-lg"
            />
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">Calculation As-of Date</label>
            <input
              type="date"
              value={cutoffDate}
              onChange={(e) => setCutoffDate(e.target.value)}
              className="w-full px-3 py-1.5 border border-slate-300 rounded-lg font-bold text-slate-800"
            />
          </div>
        </div>

        {/* Part Payments in Sandbox */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-800">Part Payments / Tranches ({payments.length})</span>
            <button
              onClick={addTranche}
              className="px-2.5 py-1 bg-emerald-100 hover:bg-emerald-200 text-emerald-800 text-xs font-bold rounded-md flex items-center gap-1 cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" /> Add Tranche
            </button>
          </div>

          {payments.map((p) => (
            <div key={p.id} className="grid grid-cols-1 sm:grid-cols-4 gap-2 items-center text-xs bg-slate-50 p-2 rounded-lg border border-slate-200">
              <input
                type="text"
                value={p.ref}
                onChange={(e) => updateTranche(p.id, 'ref', e.target.value)}
                className="px-2 py-1 bg-white border border-slate-300 rounded"
              />
              <input
                type="date"
                value={p.date}
                onChange={(e) => updateTranche(p.id, 'date', e.target.value)}
                className="px-2 py-1 bg-white border border-slate-300 rounded"
              />
              <input
                type="number"
                value={p.amount}
                onChange={(e) => updateTranche(p.id, 'amount', Number(e.target.value))}
                className="px-2 py-1 bg-white border border-slate-300 rounded font-mono"
              />
              <div className="flex justify-end">
                <button
                  onClick={() => removeTranche(p.id)}
                  className="p-1 text-rose-600 hover:bg-rose-50 rounded cursor-pointer"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Real-time Calculation Result Box */}
      <div className="bg-gradient-to-br from-slate-900 to-slate-800 text-white p-6 rounded-xl border border-slate-700 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-700 pb-3">
          <div>
            <h4 className="font-bold text-base text-white">Sandbox Statutory Computation</h4>
            <p className="text-xs text-slate-400">Monthly rest compound interest under Section 16</p>
          </div>
          <div className="text-right">
            <span className="text-xs text-slate-400 block">Total Calculated Interest</span>
            <span className="text-2xl font-black text-rose-400">{formatINR(result.totalInterestPayable)}</span>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs pt-1">
          <div>
            <span className="text-slate-400 block">Statutory Due Date:</span>
            <strong className="text-white text-sm">{formatDate(result.finalDueDate)}</strong>
          </div>
          <div>
            <span className="text-slate-400 block">Total Days Delayed:</span>
            <strong className="text-rose-300 text-sm">{result.totalDelayDays} Days</strong>
          </div>
          <div>
            <span className="text-slate-400 block">Outstanding Balance:</span>
            <strong className="text-slate-300">{formatINR(result.outstandingPrincipal)}</strong>
          </div>
          <div>
            <span className="text-slate-400 block">Applicable MSME Rate:</span>
            <strong className="text-emerald-300">{result.applicableAnnualRate}% p.a.</strong>
          </div>
        </div>
      </div>
    </div>
  );
};

/* --- Compounding Breakdown Modal --- */
const CompoundingBreakdownModal: React.FC<{ calculation: InvoiceInterestResult; onClose: () => void }> = ({
  calculation,
  onClose,
}) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-4xl overflow-hidden animate-in fade-in zoom-in-95 max-h-[90vh] flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-slate-900 text-base">
                Invoice {calculation.invoiceNumber} – Compounding Breakdown
              </h3>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">
                {calculation.msmeCategory}
              </span>
            </div>
            <p className="text-xs text-slate-500">{calculation.vendorName}</p>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-slate-600 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6 text-xs">
          {/* Summary Box */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-4 rounded-xl border border-slate-200">
            <div>
              <span className="text-slate-400 block">Invoice Total Amount:</span>
              <strong className="text-slate-900 text-sm font-mono">{formatINR(calculation.totalInvoiceAmount)}</strong>
            </div>
            <div>
              <span className="text-slate-400 block">Statutory Due Date:</span>
              <strong className="text-slate-900 text-sm font-mono">{formatDate(calculation.finalDueDate)}</strong>
            </div>
            <div>
              <span className="text-slate-400 block">Delay Beyond Due:</span>
              <strong className="text-rose-700 text-sm font-bold">{calculation.totalDelayDays} Days</strong>
            </div>
            <div>
              <span className="text-slate-400 block">Total MSME Interest:</span>
              <strong className="text-rose-700 text-sm font-black font-mono">{formatINR(calculation.totalInterestPayable)}</strong>
            </div>
          </div>

          {/* Tranches Table */}
          <div>
            <h4 className="font-bold text-slate-800 text-xs uppercase tracking-wider mb-2">
              Tranche-by-Tranche Delay & Monthly Rest Schedule (Section 16)
            </h4>
            <div className="border border-slate-200 rounded-xl overflow-hidden">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-100 text-slate-700 font-bold text-[10px] uppercase">
                  <tr>
                    <th className="px-3 py-2.5">Tranche #</th>
                    <th className="px-3 py-2.5">Delay Period</th>
                    <th className="px-3 py-2.5 text-center">Days</th>
                    <th className="px-3 py-2.5 text-right">Principal Base</th>
                    <th className="px-3 py-2.5 text-center">Applicable Rate</th>
                    <th className="px-3 py-2.5 text-right">Payment Made</th>
                    <th className="px-3 py-2.5 text-right bg-rose-50 text-rose-900">Interest Accrued</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {calculation.tranches.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-6 text-center text-slate-400">
                        No delay recorded for this invoice. Payment was made on or before the statutory due date.
                      </td>
                    </tr>
                  ) : (
                    calculation.tranches.map((t) => (
                      <tr key={t.trancheNumber} className="hover:bg-slate-50">
                        <td className="px-3 py-2.5 font-bold text-slate-700">Tranche {t.trancheNumber}</td>
                        <td className="px-3 py-2.5 text-slate-600 font-mono text-[11px]">
                          {formatDate(t.periodStart)} to {formatDate(t.periodEnd)}
                        </td>
                        <td className="px-3 py-2.5 text-center font-bold text-slate-800">{t.delayDays}d</td>
                        <td className="px-3 py-2.5 text-right font-mono font-bold text-slate-900">
                          {formatINR(t.principalBase)}
                        </td>
                        <td className="px-3 py-2.5 text-center font-mono text-emerald-700 font-bold">
                          {t.applicableRate}% (3x RBI)
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono text-slate-600">
                          {t.paymentApplied > 0 ? formatINR(t.paymentApplied) : '—'}
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono font-black text-rose-700 bg-rose-50/40">
                          {formatINR(t.interestAmount)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Statutory Law Citation Note */}
          <div className="bg-amber-50 p-4 rounded-xl border border-amber-200 text-amber-900 space-y-1">
            <h5 className="font-bold flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-amber-700" />
              Statutory Basis – Micro, Small and Medium Enterprises Development Act, 2006
            </h5>
            <p className="text-[11px] leading-relaxed text-amber-800">
              <strong>Section 16:</strong> Where any buyer fails to make payment of the amount to the supplier, he shall, notwithstanding anything contained in any agreement, be liable to pay compound interest with monthly rests to the supplier at three times of the bank rate notified by the Reserve Bank of India.
            </p>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
          <span className="text-[11px] text-slate-500">
            Computed under statutory compound monthly rest standard
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-900 hover:bg-slate-800 text-white font-bold rounded-lg text-xs cursor-pointer"
          >
            Close Breakdown
          </button>
        </div>
      </div>
    </div>
  );
};
