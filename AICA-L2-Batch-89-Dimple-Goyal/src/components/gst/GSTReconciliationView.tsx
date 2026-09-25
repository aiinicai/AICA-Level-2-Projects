import React, { useState, useMemo } from 'react';
import {
  Receipt,
  Download,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  FileSpreadsheet,
  ArrowRight,
  Upload,
  ChevronDown,
  ChevronUp,
  Search,
  Filter,
  Users,
  ShieldAlert,
  Building2,
  FileText
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { GSTRecord, DebtorReconciliationSummary } from '../../types';
import { formatINR, formatDate } from '../../utils/formatters';
import { exportToCSV, exportToExcel } from '../../utils/excelEngine';
import { GSTR1ImportWizard } from './GSTR1ImportWizard';
import { ROLE_DEFINITIONS } from '../../utils/rbac';

export const GSTReconciliationView: React.FC = () => {
  const { gstRecords, invoices, customers, importGstRecordsBatch, currentUser } = useApp();
  
  const [viewMode, setViewMode] = useState<'debtor' | 'invoice'>('debtor');
  const [statusFilter, setStatusFilter] = useState<string>('All');
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedDebtors, setExpandedDebtors] = useState<Record<string, boolean>>({});
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);

  const rolePerms = ROLE_DEFINITIONS[currentUser.role];
  const canUpload = rolePerms?.canUploadGSTR1 ?? false;

  // Toggle expanded debtor drawer
  const toggleDebtor = (debtorKey: string) => {
    setExpandedDebtors(prev => ({
      ...prev,
      [debtorKey]: !prev[debtorKey]
    }));
  };

  // Group all invoices & GSTR-1 records Debtor-wise
  const debtorReconciliations: DebtorReconciliationSummary[] = useMemo(() => {
    const debtorMap = new Map<string, {
      customerName: string;
      customerGstin: string;
      customerId?: string;
      booksInvoices: any[];
      gstr1Invoices: GSTRecord[];
    }>();

    // 1. Group Books Invoices by Debtor
    invoices.forEach(inv => {
      const gstin = (inv.customerGstin || 'UNKNOWN-GSTIN').toUpperCase();
      const existing = debtorMap.get(gstin) || {
        customerName: inv.customerName,
        customerGstin: gstin,
        customerId: inv.customerId,
        booksInvoices: [],
        gstr1Invoices: []
      };
      existing.booksInvoices.push(inv);
      debtorMap.set(gstin, existing);
    });

    // 2. Group GSTR-1 Records by Debtor
    gstRecords.forEach(rec => {
      const gstin = (rec.customerGstin || rec.gstin || 'UNKNOWN-GSTIN').toUpperCase();
      const existing = debtorMap.get(gstin) || {
        customerName: rec.customerName || rec.tradeName || gstin,
        customerGstin: gstin,
        booksInvoices: [],
        gstr1Invoices: []
      };
      existing.gstr1Invoices.push(rec);
      debtorMap.set(gstin, existing);
    });

    // 3. Compute Debtor Summaries
    const summaries: DebtorReconciliationSummary[] = [];

    debtorMap.forEach((entry, gstin) => {
      const booksTaxable = entry.booksInvoices.reduce((sum, inv) => sum + (inv.taxableValue || 0), 0);
      const booksTax = entry.booksInvoices.reduce((sum, inv) => sum + (inv.cgst || 0) + (inv.sgst || 0) + (inv.igst || 0), 0);
      const booksTotal = entry.booksInvoices.reduce((sum, inv) => sum + (inv.totalInvoiceValue || 0), 0);

      const gstr1Taxable = entry.gstr1Invoices.reduce((sum, rec) => sum + (rec.taxableValue || 0), 0);
      const gstr1Tax = entry.gstr1Invoices.reduce((sum, rec) => sum + (rec.cgst || rec.cgstAmount || 0) + (rec.sgst || rec.sgstAmount || 0) + (rec.igst || rec.igstAmount || 0), 0);
      const gstr1Total = entry.gstr1Invoices.reduce((sum, rec) => sum + (rec.totalValue || rec.total || 0), 0);

      const taxableVariance = booksTaxable - gstr1Taxable;
      const taxVariance = booksTax - gstr1Tax;
      const totalVariance = booksTotal - gstr1Total;

      let status: DebtorReconciliationSummary['status'] = 'Fully Matched';
      if (entry.booksInvoices.length > 0 && entry.gstr1Invoices.length === 0) {
        status = 'Missing in GSTR-1';
      } else if (entry.booksInvoices.length === 0 && entry.gstr1Invoices.length > 0) {
        status = 'Only in GSTR-1';
      } else if (Math.abs(taxVariance) > 5 || Math.abs(taxableVariance) > 10) {
        status = 'Tax / Amount Variance';
      } else {
        status = 'Fully Matched';
      }

      // Compile detailed invoice comparison rows for this debtor
      const combinedInvoices: GSTRecord[] = [];
      
      // Match each books invoice
      entry.booksInvoices.forEach((bInv, idx) => {
        const matchingGstr = entry.gstr1Invoices.find(g =>
          g.invoiceNumber.toUpperCase() === bInv.invoiceNumber.toUpperCase() ||
          g.invoiceNumber.toUpperCase().replace(/[-/\s]/g, '') === bInv.invoiceNumber.toUpperCase().replace(/[-/\s]/g, '')
        );

        const bTax = (bInv.cgst || 0) + (bInv.sgst || 0) + (bInv.igst || 0);
        const gTax = matchingGstr ? (matchingGstr.cgst || matchingGstr.cgstAmount || 0) + (matchingGstr.sgst || matchingGstr.sgstAmount || 0) + (matchingGstr.igst || matchingGstr.igstAmount || 0) : 0;

        let invStatus: GSTRecord['status'] = 'Matched';
        let discrepancyRemarks: string | undefined;

        if (!matchingGstr) {
          invStatus = 'Invoice Missing in GST';
          discrepancyRemarks = 'Invoice in Sales Register but omitted from GSTR-1 filing';
        } else if (Math.abs(bTax - gTax) > 5 || Math.abs(bInv.totalInvoiceValue - (matchingGstr.totalValue || matchingGstr.total)) > 5) {
          invStatus = 'Tax Mismatch';
          discrepancyRemarks = `Tax/Value diff: Books ₹${bInv.totalInvoiceValue} vs GSTR-1 ₹${matchingGstr.totalValue || matchingGstr.total}`;
        }

        combinedInvoices.push({
          id: `comb-${bInv.id}-${idx}`,
          gstin,
          customerGstin: gstin,
          customerName: entry.customerName,
          tradeName: entry.customerName,
          invoiceNumber: bInv.invoiceNumber,
          invoiceDate: bInv.invoiceDate,
          taxableValue: bInv.taxableValue,
          cgst: bInv.cgst,
          sgst: bInv.sgst,
          igst: bInv.igst,
          total: bInv.totalInvoiceValue,
          totalValue: bInv.totalInvoiceValue,
          gstr1ReportedValue: matchingGstr ? (matchingGstr.totalValue || matchingGstr.total) : undefined,
          source: 'Sales Register (Books)',
          status: invStatus,
          discrepancyRemarks,
          discrepancyReason: discrepancyRemarks,
          differenceAmount: matchingGstr ? Math.abs(bInv.totalInvoiceValue - (matchingGstr.totalValue || matchingGstr.total)) : bInv.totalInvoiceValue
        });
      });

      // Any GSTR-1 record missing in books
      entry.gstr1Invoices.forEach(g => {
        const foundInBooks = entry.booksInvoices.some(b =>
          b.invoiceNumber.toUpperCase() === g.invoiceNumber.toUpperCase() ||
          b.invoiceNumber.toUpperCase().replace(/[-/\s]/g, '') === g.invoiceNumber.toUpperCase().replace(/[-/\s]/g, '')
        );
        if (!foundInBooks) {
          combinedInvoices.push({
            ...g,
            status: 'GST Data Missing in Books',
            discrepancyRemarks: 'Reported in GSTR-1 portal filing but missing in sales ledger'
          });
        }
      });

      summaries.push({
        customerId: entry.customerId,
        customerName: entry.customerName,
        customerGstin: gstin,
        booksInvoiceCount: entry.booksInvoices.length,
        gstr1InvoiceCount: entry.gstr1Invoices.length,
        booksTaxableValue: booksTaxable,
        gstr1TaxableValue: gstr1Taxable,
        booksTaxAmount: booksTax,
        gstr1TaxAmount: gstr1Tax,
        booksTotalValue: booksTotal,
        gstr1TotalValue: gstr1Total,
        taxableVariance,
        taxVariance,
        totalVariance,
        status,
        invoices: combinedInvoices
      });
    });

    return summaries;
  }, [invoices, gstRecords]);

  // Filtered Debtors
  const filteredDebtors = useMemo(() => {
    return debtorReconciliations.filter(d => {
      const matchSearch =
        d.customerName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        d.customerGstin.toLowerCase().includes(searchTerm.toLowerCase());
      const matchStatus = statusFilter === 'All' || d.status === statusFilter;
      return matchSearch && matchStatus;
    });
  }, [debtorReconciliations, searchTerm, statusFilter]);

  // Debtor Summary KPIs
  const totalDebtors = debtorReconciliations.length;
  const fullyMatchedDebtors = debtorReconciliations.filter(d => d.status === 'Fully Matched').length;
  const missingGstr1Debtors = debtorReconciliations.filter(d => d.status === 'Missing in GSTR-1').length;
  const varianceDebtors = debtorReconciliations.filter(d => d.status === 'Tax / Amount Variance').length;

  const handleExport = (type: 'csv' | 'excel') => {
    if (viewMode === 'debtor') {
      const exportData = filteredDebtors.map(d => ({
        'Debtor Name': d.customerName,
        'Debtor GSTIN': d.customerGstin,
        'Books Invoices': d.booksInvoiceCount,
        'GSTR-1 Invoices': d.gstr1InvoiceCount,
        'Books Turnover (₹)': d.booksTaxableValue,
        'GSTR-1 Turnover (₹)': d.gstr1TaxableValue,
        'Turnover Variance (₹)': d.taxableVariance,
        'Books Tax Amount (₹)': d.booksTaxAmount,
        'GSTR-1 Tax Amount (₹)': d.gstr1TaxAmount,
        'Tax Variance (₹)': d.taxVariance,
        'Reconciliation Status': d.status
      }));

      if (type === 'csv') exportToCSV(exportData, 'Debtor_Wise_GSTR1_Reconciliation');
      else exportToExcel(exportData, 'Debtor_Wise_GSTR1_Reconciliation', 'Debtor GSTR-1 Recon');
    } else {
      const allInvoices = filteredDebtors.flatMap(d => d.invoices);
      const exportData = allInvoices.map(g => ({
        'Debtor Name': g.customerName,
        'Customer GSTIN': g.customerGstin,
        'Invoice Number': g.invoiceNumber,
        'Invoice Date': g.invoiceDate,
        'Books Taxable (₹)': g.taxableValue,
        'Books Tax (₹)': (g.cgst || 0) + (g.sgst || 0) + (g.igst || 0),
        'Books Total (₹)': g.totalValue || g.total,
        'GSTR-1 Value (₹)': g.gstr1ReportedValue || 'N/A',
        'Status': g.status,
        'Remarks': g.discrepancyRemarks || 'Matched'
      }));

      if (type === 'csv') exportToCSV(exportData, 'Invoice_Wise_GST_Reconciliation');
      else exportToExcel(exportData, 'Invoice_Wise_GST_Reconciliation', 'Invoice GST Recon');
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">GST Reconciliation & Debtor Audit</h1>
            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-300">
              Debtor-Wise Engine
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Audit Books of Accounts against GSTR-1 filings grouped by debtor to protect customer ITC under Section 16(2)(aa).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`hidden sm:inline-flex px-2.5 py-1 text-[11px] font-bold rounded-lg border ${rolePerms.badgeClass}`}>
            {currentUser.role}
          </span>
          <button
            onClick={() => handleExport('excel')}
            className="px-3 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200/80 rounded-lg transition-colors flex items-center gap-1.5"
            title="Export Reconciliation"
          >
            <Download className="w-4 h-4 text-slate-500" />
            <span>Export</span>
          </button>
          {canUpload && (
            <button
              onClick={() => setIsImportModalOpen(true)}
              className="px-3.5 py-2 text-xs font-bold text-white bg-emerald-700 hover:bg-emerald-800 rounded-lg transition-colors flex items-center gap-1.5 shadow-xs"
            >
              <Upload className="w-4 h-4" />
              <span>Upload GSTR-1 (JSON, Excel, CSV)</span>
            </button>
          )}
        </div>
      </div>

      {/* Debtor-Wise KPI Highlights */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Total Debtors (Buyers)</span>
          <p className="text-xl font-bold text-slate-900 mt-1">{totalDebtors} Debtors</p>
          <span className="text-[11px] text-slate-500">{invoices.length} total sales bills</span>
        </div>

        <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-200 shadow-xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 block">Fully Reconciled Debtors</span>
          <p className="text-xl font-bold text-emerald-950 mt-1">{fullyMatchedDebtors} Debtors</p>
          <span className="text-[11px] text-emerald-700">100% Tax & Turnover match in GSTR-1</span>
        </div>

        <div className="p-4 bg-rose-50 rounded-xl border border-rose-200 shadow-xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-rose-800 block">Debtors with Missing Filings</span>
          <p className="text-xl font-bold text-rose-950 mt-1">{missingGstr1Debtors} Debtors</p>
          <span className="text-[11px] text-rose-700">Critical: Customer ITC denial risk u/s 16(2)(aa)</span>
        </div>

        <div className="p-4 bg-amber-50 rounded-xl border border-amber-200 shadow-xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-amber-800 block">Tax / Amount Variances</span>
          <p className="text-xl font-bold text-amber-950 mt-1">{varianceDebtors} Debtors</p>
          <span className="text-[11px] text-amber-700">Rate or rounding differences</span>
        </div>
      </div>

      {/* View Switcher & Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white p-4 rounded-xl border border-slate-200">
        <div className="flex items-center gap-2 w-full sm:w-auto">
          {/* View Mode Toggle */}
          <div className="flex bg-slate-100 p-1 rounded-lg">
            <button
              onClick={() => setViewMode('debtor')}
              className={`px-3 py-1.5 rounded-md text-xs font-bold transition-colors flex items-center gap-1.5 ${
                viewMode === 'debtor'
                  ? 'bg-white text-emerald-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Users className="w-3.5 h-3.5" />
              <span>Debtor-Wise Reconciliation</span>
            </button>
            <button
              onClick={() => setViewMode('invoice')}
              className={`px-3 py-1.5 rounded-md text-xs font-bold transition-colors flex items-center gap-1.5 ${
                viewMode === 'invoice'
                  ? 'bg-white text-emerald-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Invoice Detail View</span>
            </button>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search debtor name or GSTIN..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 bg-slate-50 focus:outline-hidden focus:border-emerald-600"
            />
          </div>

          <div className="flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs p-1.5 rounded-lg border border-slate-200 bg-slate-50 font-medium"
            >
              <option value="All">All Statuses</option>
              <option value="Fully Matched">Fully Matched</option>
              <option value="Missing in GSTR-1">Missing in GSTR-1</option>
              <option value="Tax / Amount Variance">Tax / Amount Variance</option>
              <option value="Only in GSTR-1">Only in GSTR-1</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Content Area: Debtor-Wise View vs Invoice Detail View */}
      {viewMode === 'debtor' ? (
        <div className="space-y-3">
          {filteredDebtors.length === 0 ? (
            <div className="p-12 text-center bg-white rounded-xl border border-slate-200 text-slate-500 text-xs">
              No debtor records match your search or filter criteria.
            </div>
          ) : (
            filteredDebtors.map((debtor) => {
              const isExpanded = !!expandedDebtors[debtor.customerGstin];
              const isFullyMatched = debtor.status === 'Fully Matched';
              const isMissingGstr1 = debtor.status === 'Missing in GSTR-1';
              const isVariance = debtor.status === 'Tax / Amount Variance';

              return (
                <div
                  key={debtor.customerGstin}
                  className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden transition-all"
                >
                  {/* Debtor Header Row */}
                  <div
                    onClick={() => toggleDebtor(debtor.customerGstin)}
                    className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer hover:bg-slate-50/70 transition-colors"
                  >
                    <div className="flex items-start gap-3">
                      <div className={`p-2.5 rounded-xl shrink-0 mt-0.5 ${
                        isFullyMatched
                          ? 'bg-emerald-100 text-emerald-700'
                          : isMissingGstr1
                          ? 'bg-rose-100 text-rose-700'
                          : 'bg-amber-100 text-amber-700'
                      }`}>
                        <Building2 className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-bold text-slate-900 text-sm">{debtor.customerName}</h3>
                          <span className={`px-2 py-0.5 text-[10px] font-bold rounded-full border ${
                            isFullyMatched
                              ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                              : isMissingGstr1
                              ? 'bg-rose-50 text-rose-800 border-rose-200 animate-pulse'
                              : 'bg-amber-50 text-amber-800 border-amber-200'
                          }`}>
                            {debtor.status}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
                          <span className="font-mono text-[11px] font-semibold text-slate-600">
                            GSTIN: {debtor.customerGstin}
                          </span>
                          <span>•</span>
                          <span>Books: {debtor.booksInvoiceCount} bills</span>
                          <span>•</span>
                          <span>GSTR-1: {debtor.gstr1InvoiceCount} reported</span>
                        </div>
                      </div>
                    </div>

                    {/* Financial Figures Comparison */}
                    <div className="flex items-center gap-6 text-xs justify-between md:justify-end">
                      <div>
                        <span className="text-[10px] uppercase font-bold text-slate-400 block">Books Turnover</span>
                        <p className="font-mono font-bold text-slate-900 text-sm mt-0.5">{formatINR(debtor.booksTaxableValue)}</p>
                      </div>

                      <div>
                        <span className="text-[10px] uppercase font-bold text-slate-400 block">GSTR-1 Filed</span>
                        <p className="font-mono font-bold text-slate-900 text-sm mt-0.5">{formatINR(debtor.gstr1TaxableValue)}</p>
                      </div>

                      <div>
                        <span className="text-[10px] uppercase font-bold text-slate-400 block">Tax Variance</span>
                        <p className={`font-mono font-bold text-sm mt-0.5 ${
                          Math.abs(debtor.taxVariance) <= 5 ? 'text-emerald-700' : 'text-rose-600'
                        }`}>
                          {Math.abs(debtor.taxVariance) <= 5 ? '₹0.00' : formatINR(debtor.taxVariance)}
                        </p>
                      </div>

                      <button
                        className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-200 transition-colors"
                        aria-label="Expand Debtor Details"
                      >
                        {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                      </button>
                    </div>
                  </div>

                  {/* Expanded Debtor Drawer (Invoice Breakdown) */}
                  {isExpanded && (
                    <div className="border-t border-slate-200 bg-slate-50/50 p-4 space-y-3">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-bold text-slate-700">
                          Invoice-Level Audit Trail for {debtor.customerName} ({debtor.invoices.length} records):
                        </span>
                        {isMissingGstr1 && (
                          <span className="text-[11px] font-semibold text-rose-700 flex items-center gap-1">
                            <AlertTriangle className="w-3.5 h-3.5" />
                            Action: Upload these bills in upcoming GSTR-1 or amendment Table 9
                          </span>
                        )}
                      </div>

                      <div className="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-2xs">
                        <table className="w-full text-left text-xs">
                          <thead className="bg-slate-50 border-b border-slate-200 text-[10px] uppercase font-bold text-slate-500">
                            <tr>
                              <th className="p-3">Invoice No</th>
                              <th className="p-3">Date</th>
                              <th className="p-3 text-right">Taxable (Books)</th>
                              <th className="p-3 text-right">Tax (Books)</th>
                              <th className="p-3 text-right">GSTR-1 Total</th>
                              <th className="p-3">Reconciliation Status</th>
                              <th className="p-3">Audit Discrepancy Note</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {debtor.invoices.map((inv) => (
                              <tr key={inv.id} className="hover:bg-slate-50">
                                <td className="p-3 font-mono font-bold text-slate-900">{inv.invoiceNumber}</td>
                                <td className="p-3 font-mono text-slate-500">{inv.invoiceDate}</td>
                                <td className="p-3 text-right font-mono">{formatINR(inv.taxableValue)}</td>
                                <td className="p-3 text-right font-mono">{formatINR((inv.cgst || 0) + (inv.sgst || 0) + (inv.igst || 0))}</td>
                                <td className="p-3 text-right font-mono font-bold text-slate-900">
                                  {inv.gstr1ReportedValue ? formatINR(inv.gstr1ReportedValue) : <span className="text-rose-600 italic">Not Reported</span>}
                                </td>
                                <td className="p-3">
                                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                    inv.status === 'Matched'
                                      ? 'bg-emerald-100 text-emerald-800'
                                      : inv.status === 'Invoice Missing in GST'
                                      ? 'bg-rose-100 text-rose-800'
                                      : 'bg-amber-100 text-amber-800'
                                  }`}>
                                    {inv.status}
                                  </span>
                                </td>
                                <td className="p-3 text-slate-600 text-[11px]">
                                  {inv.discrepancyRemarks || 'Matches filed portal record'}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      ) : (
        /* Invoice-Wise Detail View */
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-[10px] uppercase font-bold text-slate-500">
                <tr>
                  <th className="p-3.5">Invoice No</th>
                  <th className="p-3.5">Date</th>
                  <th className="p-3.5">Debtor Name & GSTIN</th>
                  <th className="p-3.5 text-right">Taxable (Books)</th>
                  <th className="p-3.5 text-right">Total (Books)</th>
                  <th className="p-3.5 text-right">GSTR-1 Filed</th>
                  <th className="p-3.5">Status</th>
                  <th className="p-3.5">Audit Note</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredDebtors.flatMap(d => d.invoices).map((g) => (
                  <tr key={g.id} className="hover:bg-slate-50">
                    <td className="p-3.5 font-mono font-bold text-slate-900">{g.invoiceNumber}</td>
                    <td className="p-3.5 font-mono text-slate-500">{g.invoiceDate}</td>
                    <td className="p-3.5">
                      <p className="font-semibold text-slate-900">{g.customerName}</p>
                      <span className="font-mono text-[10px] text-slate-400">{g.customerGstin}</span>
                    </td>
                    <td className="p-3.5 text-right font-mono">{formatINR(g.taxableValue)}</td>
                    <td className="p-3.5 text-right font-mono font-bold text-slate-900">{formatINR(g.totalValue || g.total)}</td>
                    <td className="p-3.5 text-right font-mono">
                      {g.gstr1ReportedValue ? formatINR(g.gstr1ReportedValue) : <span className="text-rose-600 italic">Missing</span>}
                    </td>
                    <td className="p-3.5">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        g.status === 'Matched'
                          ? 'bg-emerald-100 text-emerald-800'
                          : g.status === 'Invoice Missing in GST'
                          ? 'bg-rose-100 text-rose-800'
                          : 'bg-amber-100 text-amber-800'
                      }`}>
                        {g.status}
                      </span>
                    </td>
                    <td className="p-3.5 text-slate-600 text-[11px] max-w-xs truncate">
                      {g.discrepancyRemarks || 'Matches filed portal record'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* GSTR-1 Import Wizard Modal */}
      {isImportModalOpen && (
        <GSTR1ImportWizard
          isOpen={isImportModalOpen}
          customers={customers}
          existingInvoices={invoices}
          existingGstRecords={gstRecords}
          onClose={() => setIsImportModalOpen(false)}
          onImportComplete={(imported) => {
            importGstRecordsBatch(imported);
            setIsImportModalOpen(false);
          }}
        />
      )}
    </div>
  );
};
