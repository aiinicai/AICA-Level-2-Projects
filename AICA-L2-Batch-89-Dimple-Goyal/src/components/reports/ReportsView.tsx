import React, { useState } from 'react';
import {
  BarChart3,
  Download,
  FileSpreadsheet,
  FileText,
  Clock,
  ShieldCheck,
  Receipt,
  Users,
  CheckCircle2,
  Calendar
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { exportToCSV, exportToExcel } from '../../utils/excelEngine';
import { formatINR, formatDate } from '../../utils/formatters';
import { buildCustomerAgeingMatrix, computeBucketSummaries } from '../../utils/ageingEngine';

export const ReportsView: React.FC = () => {
  const { invoices, customers, bankTransactions, tdsRecords, gstRecords, allocations, kpis } = useApp();
  const [selectedReport, setSelectedReport] = useState<'sales' | 'customer_ledger' | 'outstanding' | 'ageing' | 'collections' | 'tds' | 'gst'>('outstanding');
  const [selectedCustomerFilter, setSelectedCustomerFilter] = useState<string>('All');

  const handleExport = (type: 'csv' | 'excel') => {
    let data: any[] = [];
    let filename = '';

    if (selectedReport === 'sales') {
      filename = 'Sales_Register_Report';
      data = invoices.map(i => ({
        'Invoice No': i.invoiceNumber,
        'Date': i.invoiceDate,
        'Due Date': i.dueDate,
        'Customer': i.customerName,
        'GSTIN': i.customerGstin,
        'Taxable Value': i.taxableValue,
        'GST Amount': i.gstAmount,
        'Total Value': i.totalInvoiceValue,
        'Expected TDS': i.expectedTds,
        'Received': i.amountReceived,
        'Balance': i.balance,
        'Status': i.status
      }));
    } else if (selectedReport === 'outstanding') {
      filename = 'Outstanding_Receivables_Report';
      data = invoices.filter(i => i.balance > 0).map(i => ({
        'Invoice No': i.invoiceNumber,
        'Customer': i.customerName,
        'Invoice Date': i.invoiceDate,
        'Due Date': i.dueDate,
        'Total Amount': i.totalInvoiceValue,
        'Received': i.amountReceived,
        'Outstanding Balance': i.balance,
        'Status': i.status
      }));
    } else if (selectedReport === 'ageing') {
      filename = 'Ageing_Summary_Report';
      data = buildCustomerAgeingMatrix(invoices, customers).map(c => ({
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
    } else if (selectedReport === 'collections') {
      filename = 'Collections_Summary_Report';
      data = bankTransactions.filter(t => t.isCredit).map(t => ({
        'Date': t.transactionDate,
        'Narration': t.narration,
        'Reference / UTR': t.referenceNumber,
        'Amount': t.amount,
        'Allocated': t.allocatedAmount,
        'Unallocated': t.unallocatedAmount,
        'Status': t.allocationStatus
      }));
    } else if (selectedReport === 'tds') {
      filename = 'TDS_26AS_Reconciliation_Report';
      data = tdsRecords.map(t => ({
        'TAN': t.tan,
        'Deductor': t.deductorName,
        'PAN': t.pan,
        'Section': t.section,
        'Amount Credited': t.amountPaidCredited,
        'TDS Deposited': t.tdsDeposited,
        'Matched Invoice': t.matchedInvoiceNumber || 'Unmatched',
        'Status': t.status
      }));
    } else if (selectedReport === 'gst') {
      filename = 'GST_Audit_Report';
      data = gstRecords.map(g => ({
        'Invoice No': g.invoiceNumber,
        'Customer': g.customerName,
        'GSTIN': g.customerGstin,
        'Books Value': g.totalValue,
        'GSTR-1 Value': g.gstr1ReportedValue || 'N/A',
        'Audit Status': g.status,
        'Remarks': g.discrepancyReason || 'None'
      }));
    } else if (selectedReport === 'customer_ledger') {
      filename = 'Customer_Ledger_Statement';
      const targetInvoices = selectedCustomerFilter === 'All' ? invoices : invoices.filter(i => i.customerId === selectedCustomerFilter);
      data = targetInvoices.map(i => ({
        'Customer': i.customerName,
        'Invoice No': i.invoiceNumber,
        'Date': i.invoiceDate,
        'Debit (Sales)': i.totalInvoiceValue,
        'Credit (Received)': i.amountReceived,
        'Closing Balance': i.balance
      }));
    }

    if (type === 'csv') exportToCSV(data, filename);
    else exportToExcel(data, filename, 'Report Data');
  };

  const reportsList = [
    { id: 'outstanding', name: 'Outstanding Receivables', desc: 'Detailed open customer balances with due dates', icon: Clock },
    { id: 'sales', name: 'Sales Register', desc: 'Chronological sales register with GST & TDS details', icon: FileText },
    { id: 'ageing', name: 'Ageing Summary Matrix', desc: 'Customer-wise 0-30, 31-60, 61-90, 90+ days matrix', icon: BarChart3 },
    { id: 'collections', name: 'Collections Summary', desc: 'Bank credits, UTR numbers, and receipt allocations', icon: FileSpreadsheet },
    { id: 'tds', name: 'TDS 26AS Audit Report', desc: 'Books TDS vs Income Tax Department 26AS/AIS deposits', icon: ShieldCheck },
    { id: 'gst', name: 'GST Audit Report', desc: 'Sales ledger vs GSTR-1 return filing discrepancies', icon: Receipt },
    { id: 'customer_ledger', name: 'Customer Ledger Statement', desc: 'Individual debtor running account statement', icon: Users }
  ];

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Financial Reports & Export Engine</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Generate compliant accounting statements, debtor ageings, TDS summaries, and GST reconciliation sheets.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleExport('csv')}
            className="px-3 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200/80 rounded-lg transition-colors flex items-center gap-1.5"
          >
            <Download className="w-4 h-4 text-slate-500" />
            <span>Export CSV</span>
          </button>
          <button
            onClick={() => handleExport('excel')}
            className="px-3.5 py-2 text-xs font-bold text-white bg-emerald-700 hover:bg-emerald-800 rounded-lg transition-colors flex items-center gap-1.5 shadow-xs"
          >
            <FileSpreadsheet className="w-4 h-4" />
            <span>Download Excel (.xlsx)</span>
          </button>
        </div>
      </div>

      {/* Report Selector Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {reportsList.map((r) => {
          const Icon = r.icon;
          const isSelected = selectedReport === r.id;
          return (
            <div
              key={r.id}
              onClick={() => setSelectedReport(r.id as any)}
              className={`p-4 rounded-xl border cursor-pointer transition-all ${
                isSelected
                  ? 'bg-slate-900 text-white border-slate-900 shadow-md'
                  : 'bg-white text-slate-800 border-slate-200 hover:border-slate-300 shadow-xs'
              }`}
            >
              <Icon className={`w-5 h-5 mb-2 ${isSelected ? 'text-emerald-400' : 'text-slate-500'}`} />
              <h4 className="font-bold text-xs">{r.name}</h4>
              <p className={`text-[11px] mt-1 line-clamp-2 ${isSelected ? 'text-slate-300' : 'text-slate-500'}`}>
                {r.desc}
              </p>
            </div>
          );
        })}
      </div>

      {/* Customer selector for Ledger */}
      {selectedReport === 'customer_ledger' && (
        <div className="bg-white p-4 rounded-xl border border-slate-200 flex items-center gap-3 text-xs">
          <label className="font-semibold text-slate-700">Select Customer:</label>
          <select
            value={selectedCustomerFilter}
            onChange={(e) => setSelectedCustomerFilter(e.target.value)}
            className="p-1.5 rounded-lg border border-slate-200 bg-slate-50 font-medium text-slate-800"
          >
            <option value="All">All Customers</option>
            {customers.map(c => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
      )}

      {/* Report Preview Section */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <h3 className="font-bold text-slate-900 text-sm">
              Live Preview: {reportsList.find(r => r.id === selectedReport)?.name}
            </h3>
            <p className="text-xs text-slate-500">First 5 records displayed. Click "Download Excel" for full file.</p>
          </div>
          <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-1 rounded border border-emerald-200">
            Form 26AS & GST Compatible
          </span>
        </div>

        <div className="overflow-x-auto text-xs">
          {selectedReport === 'outstanding' && (
            <table className="w-full text-left">
              <thead className="bg-slate-50 text-[10px] uppercase font-bold text-slate-500 border-b">
                <tr>
                  <th className="p-2.5">Invoice No</th>
                  <th className="p-2.5">Customer</th>
                  <th className="p-2.5">Due Date</th>
                  <th className="p-2.5 text-right">Invoice Value</th>
                  <th className="p-2.5 text-right">Received</th>
                  <th className="p-2.5 text-right font-bold">Outstanding</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {invoices.filter(i => i.balance > 0).slice(0, 5).map(i => (
                  <tr key={i.id}>
                    <td className="p-2.5 font-mono font-bold text-slate-900">{i.invoiceNumber}</td>
                    <td className="p-2.5 font-semibold text-slate-800">{i.customerName}</td>
                    <td className="p-2.5 text-slate-600">{formatDate(i.dueDate)}</td>
                    <td className="p-2.5 text-right font-mono">{formatINR(i.totalInvoiceValue)}</td>
                    <td className="p-2.5 text-right font-mono text-emerald-700">{formatINR(i.amountReceived)}</td>
                    <td className="p-2.5 text-right font-mono font-bold text-slate-900">{formatINR(i.balance)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {selectedReport === 'sales' && (
            <table className="w-full text-left">
              <thead className="bg-slate-50 text-[10px] uppercase font-bold text-slate-500 border-b">
                <tr>
                  <th className="p-2.5">Invoice No</th>
                  <th className="p-2.5">Customer</th>
                  <th className="p-2.5 text-right">Taxable</th>
                  <th className="p-2.5 text-right">GST</th>
                  <th className="p-2.5 text-right">Total</th>
                  <th className="p-2.5 text-right">Expected TDS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {invoices.slice(0, 5).map(i => (
                  <tr key={i.id}>
                    <td className="p-2.5 font-mono font-bold text-slate-900">{i.invoiceNumber}</td>
                    <td className="p-2.5 font-semibold text-slate-800">{i.customerName}</td>
                    <td className="p-2.5 text-right font-mono">{formatINR(i.taxableValue)}</td>
                    <td className="p-2.5 text-right font-mono">{formatINR(i.gstAmount)}</td>
                    <td className="p-2.5 text-right font-mono font-bold">{formatINR(i.totalInvoiceValue)}</td>
                    <td className="p-2.5 text-right font-mono text-purple-700">{formatINR(i.expectedTds)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {selectedReport === 'ageing' && (
            <table className="w-full text-left font-mono">
              <thead className="bg-slate-50 text-[10px] uppercase font-bold text-slate-500 border-b font-sans">
                <tr>
                  <th className="p-2.5">Customer</th>
                  <th className="p-2.5 text-right">Not Due</th>
                  <th className="p-2.5 text-right">0-30d</th>
                  <th className="p-2.5 text-right">31-60d</th>
                  <th className="p-2.5 text-right">61-90d</th>
                  <th className="p-2.5 text-right">&gt;90d</th>
                  <th className="p-2.5 text-right font-bold">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {buildCustomerAgeingMatrix(invoices, customers).slice(0, 5).map(c => (
                  <tr key={c.customerId}>
                    <td className="p-2.5 font-sans font-bold text-slate-900">{c.customerName}</td>
                    <td className="p-2.5 text-right">{formatINR(c.notDue, false)}</td>
                    <td className="p-2.5 text-right">{formatINR(c.days0_30 ?? c.days0to30 ?? 0, false)}</td>
                    <td className="p-2.5 text-right">{formatINR(c.days31_60 ?? c.days31to60 ?? 0, false)}</td>
                    <td className="p-2.5 text-right">{formatINR(c.days61_90 ?? c.days61to90 ?? 0, false)}</td>
                    <td className="p-2.5 text-right text-rose-600">
                      {formatINR((c.days91_180 ?? c.days91to180 ?? 0) + (c.days181_365 ?? c.days181to365 ?? 0) + (c.days365Plus ?? c.daysAbove365 ?? 0), false)}
                    </td>
                    <td className="p-2.5 text-right font-bold text-slate-900">{formatINR(c.totalOutstanding, false)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};
