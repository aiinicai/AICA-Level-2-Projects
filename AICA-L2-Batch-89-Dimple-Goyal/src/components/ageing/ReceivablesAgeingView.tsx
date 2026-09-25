import React, { useState, useMemo } from 'react';
import {
  Clock,
  Download,
  Calendar,
  AlertTriangle,
  FileSpreadsheet,
  TrendingDown,
  Info,
  ChevronRight,
  Filter
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import {
  buildCustomerAgeingMatrix,
  computeBucketSummaries,
  calculateOverdueDays,
  getAgeingBucket
} from '../../utils/ageingEngine';
import { formatINR, formatDate } from '../../utils/formatters';
import { exportToCSV, exportToExcel } from '../../utils/excelEngine';

export const ReceivablesAgeingView: React.FC = () => {
  const { invoices, customers, kpis } = useApp();
  const [viewMode, setViewMode] = useState<'customer' | 'invoice'>('customer');
  const [selectedBucketFilter, setSelectedBucketFilter] = useState<string>('All');

  const customerMatrix = useMemo(() => {
    return buildCustomerAgeingMatrix(invoices, customers);
  }, [invoices, customers]);

  const bucketSummaries = useMemo(() => {
    return computeBucketSummaries(invoices);
  }, [invoices]);

  const openInvoicesWithAgeing = useMemo(() => {
    return invoices
      .filter(i => i.balance > 0)
      .map(i => {
        const daysOverdue = calculateOverdueDays(i.dueDate);
        const bucket = getAgeingBucket(daysOverdue);
        return {
          ...i,
          daysOverdue,
          bucket
        };
      })
      .filter(i => selectedBucketFilter === 'All' || i.bucket === selectedBucketFilter);
  }, [invoices, selectedBucketFilter]);

  const handleExport = (type: 'csv' | 'excel') => {
    if (viewMode === 'customer') {
      const data = customerMatrix.map(c => ({
        'Customer': c.customerName,
        'Not Due': c.notDue,
        '0-30 Days': c.days0_30,
        '31-60 Days': c.days31_60,
        '61-90 Days': c.days61_90,
        '91-180 Days': c.days91_180,
        '181-365 Days': c.days181_365,
        '> 365 Days': c.days365Plus,
        'Total Outstanding': c.totalOutstanding
      }));
      if (type === 'csv') exportToCSV(data, 'Customer_Ageing_Report');
      else exportToExcel(data, 'Customer_Ageing_Report', 'Customer Ageing');
    } else {
      const data = openInvoicesWithAgeing.map(i => ({
        'Invoice No': i.invoiceNumber,
        'Customer': i.customerName,
        'Invoice Date': i.invoiceDate,
        'Due Date': i.dueDate,
        'Days Overdue': i.daysOverdue,
        'Ageing Bucket': i.bucket,
        'Invoice Total': i.totalInvoiceValue,
        'Received': i.amountReceived,
        'Outstanding Balance': i.balance
      }));
      if (type === 'csv') exportToCSV(data, 'Invoice_Ageing_Report');
      else exportToExcel(data, 'Invoice_Ageing_Report', 'Invoice Ageing');
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Receivables Ageing Analysis</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Days Sales Outstanding (DSO), ageing buckets (0-30, 31-60, 61-90, 90+ days), and risk breakdown.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs font-semibold">
            <button
              onClick={() => setViewMode('customer')}
              className={`px-3 py-1.5 rounded-md transition-colors ${
                viewMode === 'customer' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              Customer-wise
            </button>
            <button
              onClick={() => setViewMode('invoice')}
              className={`px-3 py-1.5 rounded-md transition-colors ${
                viewMode === 'invoice' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              Invoice-wise
            </button>
          </div>
          <button
            onClick={() => handleExport('excel')}
            className="px-3 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200/80 rounded-lg transition-colors flex items-center gap-1.5"
          >
            <Download className="w-4 h-4 text-slate-500" />
            <span>Export</span>
          </button>
        </div>
      </div>

      {/* DSO & Bucket Distribution Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        {bucketSummaries.map((b) => (
          <div
            key={b.bucketName}
            onClick={() => {
              setViewMode('invoice');
              setSelectedBucketFilter(b.bucketName === selectedBucketFilter ? 'All' : b.bucketName);
            }}
            className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
              selectedBucketFilter === b.bucketName
                ? 'bg-slate-900 text-white border-slate-900 shadow-md'
                : 'bg-white text-slate-800 border-slate-200 hover:border-slate-300 shadow-xs'
            }`}
          >
            <span className={`text-[10px] uppercase font-bold block truncate ${selectedBucketFilter === b.bucketName ? 'text-slate-300' : 'text-slate-400'}`}>
              {b.bucketName}
            </span>
            <p className="font-mono font-bold text-sm mt-1">{formatINR(b.amount, false)}</p>
            <div className="flex items-center justify-between text-[10px] mt-1 opacity-80">
              <span>{b.invoiceCount} bills</span>
              <span>{b.percentage.toFixed(0)}%</span>
            </div>
          </div>
        ))}
      </div>

      {/* DSO Metric Callout Banner */}
      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-600 text-white flex items-center justify-center font-bold text-base shrink-0">
            {kpis.dsoDays}
          </div>
          <div>
            <h4 className="font-bold text-emerald-950">Days Sales Outstanding (DSO): {kpis.dsoDays} Days</h4>
            <p className="text-emerald-800 text-[11px] mt-0.5">
              Standard Indian SME benchmark: 45–60 days. Calculated as (Total Receivables ÷ Total Credit Sales) × 365.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3 font-semibold text-slate-700">
          <div>
            <span className="text-slate-400 text-[10px] block">Total Outstanding:</span>
            <span className="font-mono font-bold text-slate-900">{formatINR(kpis.totalOutstanding)}</span>
          </div>
          <div className="border-l border-emerald-200 pl-3">
            <span className="text-rose-500 text-[10px] block">Total Overdue:</span>
            <span className="font-mono font-bold text-rose-700">{formatINR(kpis.totalOverdue)}</span>
          </div>
        </div>
      </div>

      {/* Tables based on viewMode */}
      {viewMode === 'customer' ? (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
          <div className="p-4 border-b border-slate-200 font-bold text-xs text-slate-800 flex justify-between items-center">
            <span>Customer-Wise Ageing Matrix</span>
            <span className="text-[11px] text-slate-500 font-normal">{customerMatrix.length} Debtors with open balances</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                <tr>
                  <th className="p-3.5">Customer Name</th>
                  <th className="p-3.5 text-right">Not Due</th>
                  <th className="p-3.5 text-right">0–30 Days</th>
                  <th className="p-3.5 text-right">31–60 Days</th>
                  <th className="p-3.5 text-right">61–90 Days</th>
                  <th className="p-3.5 text-right">91–180 Days</th>
                  <th className="p-3.5 text-right">&gt; 180 Days</th>
                  <th className="p-3.5 text-right font-bold text-slate-900">Total Outstanding</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {customerMatrix.map((cust) => (
                  <tr key={cust.customerId} className="hover:bg-slate-50">
                    <td className="p-3.5 font-sans font-bold text-slate-900">
                      {cust.customerName}
                    </td>
                    <td className="p-3.5 text-right text-emerald-700">
                      {cust.notDue > 0 ? formatINR(cust.notDue, false) : '-'}
                    </td>
                    <td className="p-3.5 text-right text-amber-700">
                      {cust.days0_30 > 0 ? formatINR(cust.days0_30, false) : '-'}
                    </td>
                    <td className="p-3.5 text-right text-amber-800">
                      {cust.days31_60 > 0 ? formatINR(cust.days31_60, false) : '-'}
                    </td>
                    <td className="p-3.5 text-right text-orange-600">
                      {cust.days61_90 > 0 ? formatINR(cust.days61_90, false) : '-'}
                    </td>
                    <td className="p-3.5 text-right text-rose-600">
                      {cust.days91_180 > 0 ? formatINR(cust.days91_180, false) : '-'}
                    </td>
                    <td className="p-3.5 text-right text-rose-800 font-bold">
                      {(cust.days181_365 + cust.days365Plus) > 0 ? formatINR(cust.days181_365 + cust.days365Plus, false) : '-'}
                    </td>
                    <td className="p-3.5 text-right font-bold text-slate-900 bg-slate-50/50">
                      {formatINR(cust.totalOutstanding, false)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
          <div className="p-4 border-b border-slate-200 font-bold text-xs text-slate-800 flex justify-between items-center">
            <span>Invoice-Wise Ageing Breakdown</span>
            {selectedBucketFilter !== 'All' && (
              <button
                onClick={() => setSelectedBucketFilter('All')}
                className="text-[11px] font-semibold text-emerald-700 hover:underline"
              >
                Clear Filter ({selectedBucketFilter})
              </button>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                <tr>
                  <th className="p-3.5">Invoice No</th>
                  <th className="p-3.5">Customer</th>
                  <th className="p-3.5">Invoice Date</th>
                  <th className="p-3.5">Due Date</th>
                  <th className="p-3.5">Overdue Days</th>
                  <th className="p-3.5">Ageing Bucket</th>
                  <th className="p-3.5 text-right">Invoice Total</th>
                  <th className="p-3.5 text-right font-bold">Outstanding Balance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {openInvoicesWithAgeing.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-50">
                    <td className="p-3.5 font-mono font-bold text-slate-900">{inv.invoiceNumber}</td>
                    <td className="p-3.5 font-semibold text-slate-800">{inv.customerName}</td>
                    <td className="p-3.5 text-slate-600">{formatDate(inv.invoiceDate)}</td>
                    <td className="p-3.5 text-slate-600">{formatDate(inv.dueDate)}</td>
                    <td className="p-3.5">
                      {inv.daysOverdue <= 0 ? (
                        <span className="text-emerald-600 font-semibold">Not Due ({Math.abs(inv.daysOverdue)}d)</span>
                      ) : (
                        <span className="text-rose-600 font-bold">{inv.daysOverdue} days</span>
                      )}
                    </td>
                    <td className="p-3.5">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        inv.bucket === 'Not Due' ? 'bg-emerald-100 text-emerald-800' :
                        inv.bucket === '0–30 Days' ? 'bg-amber-100 text-amber-800' :
                        inv.bucket === '31–60 Days' ? 'bg-orange-100 text-orange-800' : 'bg-rose-100 text-rose-800'
                      }`}>
                        {inv.bucket}
                      </span>
                    </td>
                    <td className="p-3.5 text-right font-mono">{formatINR(inv.totalInvoiceValue, false)}</td>
                    <td className="p-3.5 text-right font-mono font-bold text-slate-900">{formatINR(inv.balance, false)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
