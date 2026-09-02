import React, { useState } from 'react';
import {
  Clock,
  Download,
  FileSpreadsheet,
  FileText,
  AlertTriangle,
  Building2,
  Calendar,
  Layers,
  ChevronRight,
  ShieldAlert,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { formatINR, formatDate } from '../../utils/formatters';
import { exportTableToExcel } from '../../utils/excelService';
import { exportAgeingSchedulePDF } from '../../utils/pdfService';

export const AgeingAnalysisView: React.FC = () => {
  const { ageingSummary, invoiceCalculations, asOfDate, metrics } = useApp();
  const [selectedBucketKey, setSelectedBucketKey] = useState<string>('ALL');

  const { buckets, totalPrincipal, totalInterest, totalPayable } = ageingSummary;

  // Invoices filtered by selected bucket
  const filteredInvoices = invoiceCalculations.filter((c) => {
    if (selectedBucketKey === 'ALL') return true;
    if (selectedBucketKey === 'not_due') return !c.isOverdue;
    if (selectedBucketKey === '0_30') return c.totalDelayDays > 0 && c.totalDelayDays <= 30;
    if (selectedBucketKey === '31_45') return c.totalDelayDays >= 31 && c.totalDelayDays <= 45;
    if (selectedBucketKey === '46_90') return c.totalDelayDays >= 46 && c.totalDelayDays <= 90;
    if (selectedBucketKey === '91_180') return c.totalDelayDays >= 91 && c.totalDelayDays <= 180;
    if (selectedBucketKey === 'above_180') return c.totalDelayDays > 180;
    return true;
  });

  const handleExportExcel = () => {
    const exportData = buckets.map((b) => ({
      'Ageing Bucket': b.bucketName,
      'Invoice Count': b.invoiceCount,
      'Total Principal Outstanding (₹)': b.totalPrincipal,
      'Accrued Compounded Interest (₹)': b.totalInterest,
      'Total Payable (₹)': b.totalPayable,
      'Vendor Count': b.vendorCount,
    }));
    exportTableToExcel(exportData, 'MSME_Statutory_Ageing_Matrix', 'Ageing Matrix');
  };

  const handleExportPDF = () => {
    exportAgeingSchedulePDF(ageingSummary, asOfDate);
  };

  // Cross category statistics
  const categories = ['Micro', 'Small', 'Medium'] as const;
  const crossCategoryRows = categories.map((cat) => {
    const catInvoices = invoiceCalculations.filter((c) => c.msmeCategory === cat);
    const notDue = catInvoices.filter((c) => !c.isOverdue).reduce((s, c) => s + c.outstandingPrincipal, 0);
    const d0_30 = catInvoices.filter((c) => c.totalDelayDays > 0 && c.totalDelayDays <= 30).reduce((s, c) => s + c.outstandingPrincipal, 0);
    const d31_45 = catInvoices.filter((c) => c.totalDelayDays >= 31 && c.totalDelayDays <= 45).reduce((s, c) => s + c.outstandingPrincipal, 0);
    const d46_90 = catInvoices.filter((c) => c.totalDelayDays >= 46 && c.totalDelayDays <= 90).reduce((s, c) => s + c.outstandingPrincipal, 0);
    const d90_plus = catInvoices.filter((c) => c.totalDelayDays > 90).reduce((s, c) => s + c.outstandingPrincipal, 0);
    const catPrincipal = catInvoices.reduce((s, c) => s + c.outstandingPrincipal, 0);
    const catInterest = catInvoices.reduce((s, c) => s + c.totalInterestPayable, 0);

    return {
      category: cat,
      notDue,
      d0_30,
      d31_45,
      d46_90,
      d90_plus,
      totalPrincipal: catPrincipal,
      totalInterest: catInterest,
    };
  });

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900">MSME Statutory Ageing & Delay Matrix</h2>
          <p className="text-xs text-slate-500">
            Categorized outstanding principal and compounded interest distribution as of {formatDate(asOfDate)}
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={handleExportExcel}
            className="px-3.5 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg shadow-xs flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
            Export Excel
          </button>
          <button
            onClick={handleExportPDF}
            className="px-3.5 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold rounded-lg shadow-xs flex items-center gap-1.5 transition-all cursor-pointer"
          >
            <FileText className="w-3.5 h-3.5 text-rose-400" />
            Export PDF Schedule
          </button>
        </div>
      </div>

      {/* High-Level Ageing Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {buckets.map((b) => {
          const isSelected = selectedBucketKey === b.bucketKey;
          const principalPct = totalPrincipal > 0 ? (b.totalPrincipal / totalPrincipal) * 100 : 0;

          return (
            <button
              key={b.bucketKey}
              onClick={() => setSelectedBucketKey(isSelected ? 'ALL' : b.bucketKey)}
              className={`p-4 rounded-xl text-left border transition-all cursor-pointer ${
                isSelected
                  ? 'border-slate-900 ring-2 ring-slate-900/10 bg-slate-900 text-white shadow-md'
                  : 'bg-white border-slate-200 hover:border-slate-300 shadow-xs'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className={`text-xs font-bold ${isSelected ? 'text-slate-200' : 'text-slate-600'}`}>
                  {b.bucketName}
                </span>
                <span
                  className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                    isSelected ? 'bg-white/20 text-white' : 'bg-slate-100 text-slate-700'
                  }`}
                >
                  {b.invoiceCount} inv
                </span>
              </div>

              <div className="mt-2.5">
                <div className={`text-base font-extrabold ${isSelected ? 'text-white' : 'text-slate-900'}`}>
                  {formatINR(b.totalPrincipal)}
                </div>
                <div className={`text-[11px] mt-0.5 ${isSelected ? 'text-rose-300' : 'text-rose-700 font-semibold'}`}>
                  Int: {formatINR(b.totalInterest)}
                </div>
              </div>

              {/* Mini visual fill */}
              <div className="mt-2.5 w-full bg-slate-100 dark:bg-white/20 h-1.5 rounded-full overflow-hidden">
                <div
                  className={`h-full ${isSelected ? 'bg-emerald-400' : 'bg-emerald-600'}`}
                  style={{ width: `${Math.min(100, Math.max(5, principalPct))}%` }}
                />
              </div>
            </button>
          );
        })}
      </div>

      {/* Category vs Ageing Comprehensive Matrix Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
          <div>
            <h3 className="font-bold text-slate-800 text-sm">Cross-Category Statutory Ageing Schedule</h3>
            <p className="text-xs text-slate-500">Cross-tabulation of Enterprise Classification vs Delay Buckets</p>
          </div>
          <span className="text-xs font-semibold text-slate-600 bg-white border border-slate-200 px-2.5 py-1 rounded-lg">
            Total Outstanding: <strong className="text-slate-900">{formatINR(totalPrincipal)}</strong>
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100/80 text-slate-700 font-bold uppercase text-[10px] tracking-wider border-b border-slate-200">
              <tr>
                <th className="px-4 py-3">MSME Classification</th>
                <th className="px-4 py-3 text-right">Not Due</th>
                <th className="px-4 py-3 text-right">0–30 Days</th>
                <th className="px-4 py-3 text-right">31–45 Days</th>
                <th className="px-4 py-3 text-right">46–90 Days</th>
                <th className="px-4 py-3 text-right">90+ Days</th>
                <th className="px-4 py-3 text-right bg-slate-200/60">Total Principal</th>
                <th className="px-4 py-3 text-right bg-rose-50 text-rose-900">Total Interest</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {crossCategoryRows.map((row) => (
                <tr key={row.category} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3.5">
                    <div className="font-bold text-slate-900 flex items-center gap-2">
                      <span
                        className={`w-2.5 h-2.5 rounded-full ${
                          row.category === 'Micro'
                            ? 'bg-blue-600'
                            : row.category === 'Small'
                            ? 'bg-teal-600'
                            : 'bg-amber-600'
                        }`}
                      />
                      <span>{row.category} Enterprises</span>
                    </div>
                  </td>
                  <td className="px-4 py-3.5 text-right font-mono text-slate-700">{formatINR(row.notDue)}</td>
                  <td className="px-4 py-3.5 text-right font-mono text-slate-700">{formatINR(row.d0_30)}</td>
                  <td className="px-4 py-3.5 text-right font-mono text-slate-700">{formatINR(row.d31_45)}</td>
                  <td className="px-4 py-3.5 text-right font-mono text-slate-700">{formatINR(row.d46_90)}</td>
                  <td className="px-4 py-3.5 text-right font-mono text-rose-700 font-bold">{formatINR(row.d90_plus)}</td>
                  <td className="px-4 py-3.5 text-right font-mono font-bold text-slate-900 bg-slate-50">
                    {formatINR(row.totalPrincipal)}
                  </td>
                  <td className="px-4 py-3.5 text-right font-mono font-bold text-rose-700 bg-rose-50/50">
                    {formatINR(row.totalInterest)}
                  </td>
                </tr>
              ))}

              {/* Total Summary Row */}
              <tr className="bg-slate-900 text-white font-bold text-xs">
                <td className="px-4 py-3.5">Grand Total ({invoiceCalculations.length} Invoices)</td>
                <td className="px-4 py-3.5 text-right font-mono">
                  {formatINR(buckets.find((b) => b.bucketKey === 'not_due')?.totalPrincipal || 0)}
                </td>
                <td className="px-4 py-3.5 text-right font-mono">
                  {formatINR(buckets.find((b) => b.bucketKey === '0_30')?.totalPrincipal || 0)}
                </td>
                <td className="px-4 py-3.5 text-right font-mono">
                  {formatINR(buckets.find((b) => b.bucketKey === '31_45')?.totalPrincipal || 0)}
                </td>
                <td className="px-4 py-3.5 text-right font-mono">
                  {formatINR(buckets.find((b) => b.bucketKey === '46_90')?.totalPrincipal || 0)}
                </td>
                <td className="px-4 py-3.5 text-right font-mono text-rose-300">
                  {formatINR(
                    (buckets.find((b) => b.bucketKey === '91_180')?.totalPrincipal || 0) +
                    (buckets.find((b) => b.bucketKey === 'above_180')?.totalPrincipal || 0)
                  )}
                </td>
                <td className="px-4 py-3.5 text-right font-mono text-emerald-300 text-sm">
                  {formatINR(totalPrincipal)}
                </td>
                <td className="px-4 py-3.5 text-right font-mono text-rose-400 text-sm">
                  {formatINR(totalInterest)}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Drill-down Invoices for selected bucket */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="font-bold text-slate-800 text-sm">
              Invoice Drill-Down {selectedBucketKey !== 'ALL' && `– Bucket: ${selectedBucketKey}`}
            </h3>
            <p className="text-xs text-slate-500">{filteredInvoices.length} invoices in selected scope</p>
          </div>
          {selectedBucketKey !== 'ALL' && (
            <button
              onClick={() => setSelectedBucketKey('ALL')}
              className="text-xs font-semibold text-emerald-700 hover:text-emerald-800 cursor-pointer"
            >
              Reset to All Invoices
            </button>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase text-[10px] font-bold">
              <tr>
                <th className="px-4 py-2.5">Invoice No</th>
                <th className="px-4 py-2.5">Vendor</th>
                <th className="px-4 py-2.5">Category</th>
                <th className="px-4 py-2.5">Final Due Date</th>
                <th className="px-4 py-2.5 text-right">Delay (Days)</th>
                <th className="px-4 py-2.5 text-right">Principal Outstanding</th>
                <th className="px-4 py-2.5 text-right">Accrued Interest</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredInvoices.map((c) => (
                <tr key={c.invoiceId} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-bold text-slate-900">{c.invoiceNumber}</td>
                  <td className="px-4 py-3 text-slate-700">{c.vendorName}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700">
                      {c.msmeCategory}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{formatDate(c.finalDueDate)}</td>
                  <td className="px-4 py-3 text-right">
                    {c.isOverdue ? (
                      <span className="font-bold text-rose-700">{c.totalDelayDays}d</span>
                    ) : (
                      <span className="text-emerald-700">0d (Not Due)</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right font-bold text-slate-900">{formatINR(c.outstandingPrincipal)}</td>
                  <td className="px-4 py-3 text-right font-bold text-rose-700">{formatINR(c.totalInterestPayable)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
