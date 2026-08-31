import React, { useState } from 'react';
import {
  FileSpreadsheet,
  FileText,
  Download,
  Building2,
  Calendar,
  Layers,
  AlertTriangle,
  Scale,
  ShieldCheck,
  CheckCircle2,
  FileCheck,
  TrendingDown,
  Printer,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { formatINR, formatDate } from '../../utils/formatters';
import { exportTableToExcel } from '../../utils/excelService';
import {
  exportInterestCalculationPDF,
  exportAgeingSchedulePDF,
  exportMSME1ReturnPDF,
  exportSection43BHReportPDF,
  exportSection22DisclosuresPDF,
} from '../../utils/pdfService';

export const ReportsHubView: React.FC = () => {
  const {
    vendors,
    invoices,
    invoiceCalculations,
    ageingSummary,
    asOfDate,
    selectedFinancialYear,
    statutoryRules,
    rateMaster,
    metrics,
  } = useApp();

  const [activeReportId, setActiveReportId] = useState<
    'msme1' | 'sec43bh' | 'sec22' | 'interest' | 'ageing' | 'vendor_summary'
  >('msme1');

  const [returnPeriod, setReturnPeriod] = useState<'H1' | 'H2'>('H2');

  const currentRate = rateMaster[0] || { referenceRate: 6.5, applicableMSMERate: 19.5 };

  // Section 43B(h) disallowance items: Micro & Small with overdue status as of FY close / asOfDate
  const sec43BHInvoices = invoiceCalculations.filter(
    (c) => c.section43BHRisk && c.outstandingPrincipal > 0
  );

  // MSME-1 Delayed items (unpaid > 45 days)
  const msme1DelayedInvoices = invoiceCalculations.filter(
    (c) => c.isOverdue && c.outstandingPrincipal > 0
  );

  /* --- Export Handlers --- */
  const handleExportMSME1 = (type: 'excel' | 'pdf') => {
    if (type === 'pdf') {
      exportMSME1ReturnPDF(
        msme1DelayedInvoices,
        returnPeriod === 'H1' ? 'April 2026 – September 2026 (H1)' : 'October 2026 – March 2027 (H2)',
        selectedFinancialYear === 'All' ? '2026-27' : selectedFinancialYear
      );
    } else {
      const data = msme1DelayedInvoices.map((c) => ({
        'Vendor Name': c.vendorName,
        PAN: c.pan,
        'Udyam Reg No': c.udyamNumber || 'N/A',
        'Invoice No': c.invoiceNumber,
        'Invoice Date': formatDate(c.invoiceDate),
        'Statutory Due Date': formatDate(c.finalDueDate),
        'Delay (Days)': c.daysDelayed,
        'Amount Due (₹)': c.outstandingPrincipal,
        'Reason for Delay': 'Cashflow working capital prioritization / ongoing reconciliation',
      }));
      exportTableToExcel(data, `MCA_Form_MSME1_Return_${returnPeriod}_FY${selectedFinancialYear}`, 'MSME-1 Return');
    }
  };

  const handleExportSection43BH = (type: 'excel' | 'pdf') => {
    if (type === 'pdf') {
      exportSection43BHReportPDF(sec43BHInvoices, selectedFinancialYear, asOfDate);
    } else {
      const data = sec43BHInvoices.map((c) => ({
        'Vendor Name': c.vendorName,
        PAN: c.pan,
        Category: c.msmeCategory,
        'Invoice Number': c.invoiceNumber,
        'Invoice Date': formatDate(c.invoiceDate),
        'Statutory Due Date': formatDate(c.finalDueDate),
        'Disallowance Exposure Amount (₹)': c.outstandingPrincipal,
        'Accrued MSME Interest (₹)': c.totalInterestPayable,
        'Tax Impact (Est. @ 25.17%)': Math.round(c.outstandingPrincipal * 0.2517),
      }));
      exportTableToExcel(data, `Tax_Audit_Sec_43Bh_Disallowance_FY${selectedFinancialYear}`, 'Sec 43B(h)');
    }
  };

  const handleExportSection22 = (type: 'excel' | 'pdf') => {
    if (type === 'pdf') {
      exportSection22DisclosuresPDF(metrics, selectedFinancialYear, asOfDate);
    } else {
      const data = [
        {
          Particulars: '(i) Principal amount remaining unpaid to MSME suppliers at year end',
          'Amount (₹)': metrics.totalMSMEOutstanding,
        },
        {
          Particulars: '(ii) Interest due on above principal remaining unpaid at year end',
          'Amount (₹)': metrics.estimatedInterestLiability,
        },
        {
          Particulars: '(iii) Amount of interest paid under Section 16 beyond appointed day',
          'Amount (₹)': 0,
        },
        {
          Particulars: '(iv) Interest due and payable for delay in making payment',
          'Amount (₹)': metrics.estimatedInterestLiability,
        },
        {
          Particulars: '(v) Interest accrued and remaining unpaid at year end',
          'Amount (₹)': metrics.estimatedInterestLiability,
        },
      ];
      exportTableToExcel(data, `MSMED_Act_Sec22_Audit_Disclosures_FY${selectedFinancialYear}`, 'Sec 22 Disclosure');
    }
  };

  const reportsList = [
    {
      id: 'msme1',
      title: 'MCA Form MSME-1 Half-Yearly Return',
      subtitle: 'Statutory filing under Ministry of Corporate Affairs for delays > 45 days',
      badge: `${msme1DelayedInvoices.length} Delayed Invoices`,
      badgeColor: 'bg-rose-100 text-rose-800',
    },
    {
      id: 'sec43bh',
      title: 'Income Tax Sec 43B(h) Disallowance Audit Schedule',
      subtitle: 'Micro & Small unpaid dues subject to Tax Audit disallowance',
      badge: `${sec43BHInvoices.length} Risk Items`,
      badgeColor: 'bg-amber-100 text-amber-800',
    },
    {
      id: 'sec22',
      title: 'Section 22 MSMED Act Financial Statements Disclosure',
      subtitle: 'Mandatory note for Balance Sheet, P&L and Statutory Auditor report',
      badge: 'Auditor Format',
      badgeColor: 'bg-blue-100 text-blue-800',
    },
    {
      id: 'interest',
      title: 'Delayed Payment Compound Interest Ledger',
      subtitle: 'Complete invoice-by-invoice Section 16 calculation register',
      badge: `${formatINR(metrics.estimatedInterestLiability)}`,
      badgeColor: 'bg-purple-100 text-purple-800',
    },
    {
      id: 'ageing',
      title: 'Statutory Ageing Matrix Schedule',
      subtitle: 'Bucketed breakdown (Not Due, 0-30, 31-45, 46-90, 90+ days)',
      badge: `${formatINR(metrics.totalMSMEOutstanding)}`,
      badgeColor: 'bg-teal-100 text-teal-800',
    },
  ];

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div>
        <h2 className="text-lg font-bold text-slate-900">
          Statutory Compliance & Audit Reports Hub
        </h2>
        <p className="text-xs text-slate-500">
          One-click generation of MCA Form MSME-1, Income Tax Section 43B(h), and Section 22 Financial Statements Disclosures
        </p>
      </div>

      {/* Report Selector Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-3">
        {reportsList.map((rep) => {
          const isSelected = activeReportId === rep.id;

          return (
            <button
              key={rep.id}
              onClick={() => setActiveReportId(rep.id as any)}
              className={`p-4 rounded-xl text-left border transition-all cursor-pointer flex flex-col justify-between ${
                isSelected
                  ? 'bg-slate-900 text-white border-slate-900 shadow-md ring-2 ring-slate-900/10'
                  : 'bg-white text-slate-800 border-slate-200 hover:border-slate-300 shadow-xs'
              }`}
            >
              <div>
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full inline-block mb-2 ${
                    isSelected ? 'bg-white/20 text-white' : rep.badgeColor
                  }`}
                >
                  {rep.badge}
                </span>
                <h4 className="font-bold text-xs leading-snug">{rep.title}</h4>
              </div>
              <p className={`text-[10px] mt-2 ${isSelected ? 'text-slate-300' : 'text-slate-500'}`}>
                {rep.subtitle}
              </p>
            </button>
          );
        })}
      </div>

      {/* Active Report Preview Panel */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-6">
        {/* REPORT 1: MCA FORM MSME-1 */}
        {activeReportId === 'msme1' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-extrabold text-slate-900">
                    Ministry of Corporate Affairs – Form MSME-1 Return
                  </h3>
                  <span className="px-2 py-0.5 bg-rose-100 text-rose-800 text-[10px] font-bold rounded">
                    MCA E-Filing Form
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Half-yearly return of outstanding dues to Micro & Small Enterprises exceeding 45 days
                </p>
              </div>

              {/* Period Selector & Download Actions */}
              <div className="flex items-center gap-2 flex-wrap">
                <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs">
                  <button
                    onClick={() => setReturnPeriod('H1')}
                    className={`px-2.5 py-1 rounded font-bold transition-all ${
                      returnPeriod === 'H1' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
                    }`}
                  >
                    Apr–Sep (H1)
                  </button>
                  <button
                    onClick={() => setReturnPeriod('H2')}
                    className={`px-2.5 py-1 rounded font-bold transition-all ${
                      returnPeriod === 'H2' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
                    }`}
                  >
                    Oct–Mar (H2)
                  </button>
                </div>

                <button
                  onClick={() => handleExportMSME1('excel')}
                  className="px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 font-bold text-xs rounded-lg shadow-xs flex items-center gap-1.5"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
                  Excel
                </button>
                <button
                  onClick={() => handleExportMSME1('pdf')}
                  className="px-3.5 py-1.5 bg-rose-700 hover:bg-rose-800 text-white font-bold text-xs rounded-lg shadow-xs flex items-center gap-1.5"
                >
                  <FileText className="w-3.5 h-3.5" />
                  Printable Form MSME-1 PDF
                </button>
              </div>
            </div>

            {/* MCA Statutory Header */}
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div>
                <span className="text-slate-400 block">Company Name:</span>
                <strong className="text-slate-900">BHARAT INDUSTRIAL MANUFACTURING LIMITED</strong>
              </div>
              <div>
                <span className="text-slate-400 block">Corporate Identity No (CIN):</span>
                <strong className="text-slate-900 font-mono">L28100MH2012PLC123456</strong>
              </div>
              <div>
                <span className="text-slate-400 block">Return Filing Period:</span>
                <strong className="text-slate-900 font-mono">
                  {returnPeriod === 'H1' ? '01-Apr-2026 to 30-Sep-2026' : '01-Oct-2026 to 31-Mar-2027'}
                </strong>
              </div>
            </div>

            {/* Delayed Invoices Table */}
            <div className="border border-slate-200 rounded-xl overflow-hidden">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-100 text-slate-700 font-bold text-[10px] uppercase">
                  <tr>
                    <th className="px-4 py-3">Vendor / Entity Name</th>
                    <th className="px-4 py-3">PAN</th>
                    <th className="px-4 py-3">Udyam Registration</th>
                    <th className="px-4 py-3">Invoice Details</th>
                    <th className="px-4 py-3">Due Date</th>
                    <th className="px-4 py-3 text-right">Delay (Days)</th>
                    <th className="px-4 py-3 text-right">Amount Due (₹)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {msme1DelayedInvoices.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                        Zero overdue MSME payments! Full statutory compliance under MCA guidelines.
                      </td>
                    </tr>
                  ) : (
                    msme1DelayedInvoices.map((inv) => (
                      <tr key={inv.invoiceId} className="hover:bg-slate-50">
                        <td className="px-4 py-3">
                          <div className="font-bold text-slate-900">{inv.vendorName}</div>
                          <span className="text-[10px] text-slate-500 font-semibold">{inv.msmeCategory}</span>
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-700">{inv.pan}</td>
                        <td className="px-4 py-3 font-mono text-emerald-800 font-semibold">{inv.udyamNumber || 'N/A'}</td>
                        <td className="px-4 py-3">
                          <div className="font-semibold text-slate-800">{inv.invoiceNumber}</div>
                          <div className="text-[10px] text-slate-400">{formatDate(inv.invoiceDate)}</div>
                        </td>
                        <td className="px-4 py-3 text-slate-700 font-semibold">{formatDate(inv.finalDueDate)}</td>
                        <td className="px-4 py-3 text-right font-bold text-rose-700">{inv.daysDelayed}d</td>
                        <td className="px-4 py-3 text-right font-bold text-slate-900">{formatINR(inv.outstandingPrincipal)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* REPORT 2: SECTION 43B(h) TAX AUDIT DISALLOWANCE */}
        {activeReportId === 'sec43bh' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-extrabold text-slate-900">
                    Income Tax Act – Section 43B(h) Disallowance Audit Report
                  </h3>
                  <span className="px-2 py-0.5 bg-amber-100 text-amber-800 text-[10px] font-bold rounded">
                    Tax Audit Form 3CD
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Identification of expenses from Micro & Small enterprises unpaid beyond statutory limits on FY closing
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleExportSection43BH('excel')}
                  className="px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 font-bold text-xs rounded-lg shadow-xs flex items-center gap-1.5"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
                  Excel
                </button>
                <button
                  onClick={() => handleExportSection43BH('pdf')}
                  className="px-3.5 py-1.5 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-lg shadow-xs flex items-center gap-1.5"
                >
                  <FileText className="w-3.5 h-3.5 text-amber-400" />
                  Printable Tax Audit PDF
                </button>
              </div>
            </div>

            {/* Tax Impact Summary */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl">
                <span className="text-xs font-bold text-rose-800 uppercase tracking-wider">Total Disallowance Risk</span>
                <div className="text-2xl font-black text-rose-700 mt-1">
                  {formatINR(sec43BHInvoices.reduce((s, c) => s + c.outstandingPrincipal, 0))}
                </div>
                <p className="text-[11px] text-rose-600 mt-1">Added back to taxable income under PGBP</p>
              </div>

              <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl">
                <span className="text-xs font-bold text-amber-800 uppercase tracking-wider">Estimated Corporate Tax Impact</span>
                <div className="text-2xl font-black text-amber-800 mt-1">
                  {formatINR(sec43BHInvoices.reduce((s, c) => s + c.outstandingPrincipal, 0) * 0.2517)}
                </div>
                <p className="text-[11px] text-amber-700 mt-1">Computed at base 25.17% effective corporate tax</p>
              </div>

              <div className="p-4 bg-purple-50 border border-purple-200 rounded-xl">
                <span className="text-xs font-bold text-purple-800 uppercase tracking-wider">Non-Deductible MSME Interest</span>
                <div className="text-2xl font-black text-purple-800 mt-1">
                  {formatINR(sec43BHInvoices.reduce((s, c) => s + c.totalInterestPayable, 0))}
                </div>
                <p className="text-[11px] text-purple-700 mt-1">Barred under Section 23 of MSMED Act</p>
              </div>
            </div>

            {/* Table */}
            <div className="border border-slate-200 rounded-xl overflow-hidden">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-100 text-slate-700 font-bold text-[10px] uppercase">
                  <tr>
                    <th className="px-4 py-3">Vendor / Entity</th>
                    <th className="px-4 py-3">PAN</th>
                    <th className="px-4 py-3">Category</th>
                    <th className="px-4 py-3">Invoice Details</th>
                    <th className="px-4 py-3">Due Date</th>
                    <th className="px-4 py-3 text-right">Disallowed Principal (₹)</th>
                    <th className="px-4 py-3 text-right">Estimated Tax Hit (₹)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {sec43BHInvoices.map((inv) => (
                    <tr key={inv.invoiceId} className="hover:bg-slate-50">
                      <td className="px-4 py-3 font-bold text-slate-900">{inv.vendorName}</td>
                      <td className="px-4 py-3 font-mono text-slate-700">{inv.pan}</td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">
                          {inv.msmeCategory}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-semibold text-slate-800">{inv.invoiceNumber}</div>
                        <div className="text-[10px] text-slate-400">{formatDate(inv.invoiceDate)}</div>
                      </td>
                      <td className="px-4 py-3 font-semibold text-rose-700">{formatDate(inv.finalDueDate)}</td>
                      <td className="px-4 py-3 text-right font-bold text-slate-900">{formatINR(inv.outstandingPrincipal)}</td>
                      <td className="px-4 py-3 text-right font-bold text-rose-700">{formatINR(inv.outstandingPrincipal * 0.2517)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* REPORT 3: SECTION 22 FINANCIAL STATEMENTS DISCLOSURE */}
        {activeReportId === 'sec22' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-extrabold text-slate-900">
                    Section 22 MSMED Act – Statutory Notes to Financial Statements
                  </h3>
                  <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 text-[10px] font-bold rounded">
                    Annual Report & Audit Note
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Mandatory disclosures required in the annual audited accounts of buyer companies
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleExportSection22('excel')}
                  className="px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 font-bold text-xs rounded-lg shadow-xs flex items-center gap-1.5"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
                  Excel
                </button>
                <button
                  onClick={() => handleExportSection22('pdf')}
                  className="px-3.5 py-1.5 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-lg shadow-xs flex items-center gap-1.5"
                >
                  <FileText className="w-3.5 h-3.5 text-emerald-400" />
                  Export Statutory Audit Note PDF
                </button>
              </div>
            </div>

            {/* Statutory Schedule Table */}
            <div className="border border-slate-200 rounded-xl overflow-hidden">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-100 text-slate-700 font-bold text-[10px] uppercase">
                  <tr>
                    <th className="px-4 py-3 w-16">Sr. No.</th>
                    <th className="px-4 py-3">Statutory Particulars / Disclosure Item</th>
                    <th className="px-4 py-3 text-right">As at 31-Mar-2027 (₹)</th>
                    <th className="px-4 py-3 text-right">As at 31-Mar-2026 (₹)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-xs">
                  <tr className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-bold text-slate-400">(i)</td>
                    <td className="px-4 py-3 text-slate-800">
                      <strong>Principal amount</strong> remaining unpaid to any supplier as at the end of accounting year
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-bold text-slate-900">
                      {formatINR(metrics.totalMSMEOutstanding)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-slate-500">₹1,24,50,000</td>
                  </tr>

                  <tr className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-bold text-slate-400">(ii)</td>
                    <td className="px-4 py-3 text-slate-800">
                      <strong>Interest due on above principal</strong> remaining unpaid to any supplier as at the end of accounting year
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-bold text-rose-700">
                      {formatINR(metrics.estimatedInterestLiability)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-slate-500">₹8,45,200</td>
                  </tr>

                  <tr className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-bold text-slate-400">(iii)</td>
                    <td className="px-4 py-3 text-slate-800">
                      The amount of interest paid by the buyer in terms of <strong>Section 16</strong>, along with the amounts of the payment made to the supplier beyond the appointed day
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-bold text-slate-700">₹0</td>
                    <td className="px-4 py-3 text-right font-mono text-slate-500">₹0</td>
                  </tr>

                  <tr className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-bold text-slate-400">(iv)</td>
                    <td className="px-4 py-3 text-slate-800">
                      The amount of interest due and payable for the period of delay in making payment (which has been paid but beyond the appointed day during the year) but without adding the interest specified under the MSMED Act
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-bold text-slate-900">
                      {formatINR(metrics.estimatedInterestLiability)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-slate-500">₹8,45,200</td>
                  </tr>

                  <tr className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-bold text-slate-400">(v)</td>
                    <td className="px-4 py-3 text-slate-800">
                      The amount of interest <strong>accrued and remaining unpaid</strong> at the end of each accounting year
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-bold text-rose-700">
                      {formatINR(metrics.estimatedInterestLiability)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-slate-500">₹8,45,200</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* REPORT 4 & 5: Interest & Ageing summaries */}
        {(activeReportId === 'interest' || activeReportId === 'ageing') && (
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-base">
                {activeReportId === 'interest' ? 'Delayed Payment Interest Ledger' : 'Statutory Ageing Schedule'}
              </h3>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    if (activeReportId === 'interest') {
                      exportInterestCalculationPDF(invoiceCalculations, asOfDate, `RBI 6.5% x 3 = 19.5% p.a.`);
                    } else {
                      exportAgeingSchedulePDF(ageingSummary, asOfDate);
                    }
                  }}
                  className="px-3.5 py-1.5 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-lg flex items-center gap-1.5"
                >
                  <FileText className="w-3.5 h-3.5" />
                  Download PDF Report
                </button>
              </div>
            </div>

            <p className="text-xs text-slate-500">
              Please refer to the interactive tabs in the top navigation or click the export buttons above to download formal accounting schedules.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
