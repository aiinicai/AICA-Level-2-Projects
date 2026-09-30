import React, { useState, useMemo } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  Download,
  Upload,
  AlertTriangle,
  FileSpreadsheet,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Filter,
  BookOpen,
  Sparkles
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { TDS26ASRecord } from '../../types';
import { formatINR, formatDate } from '../../utils/formatters';
import { exportToCSV, exportToExcel } from '../../utils/excelEngine';
import { TDS26ASImportWizard } from './TDS26ASImportWizard';
import { TDSSections2025Modal } from './TDSSections2025Modal';
import { ROLE_DEFINITIONS } from '../../utils/rbac';

export const TDSReconciliationView: React.FC = () => {
  const { tdsRecords, invoices, customers, importTdsRecordsBatch, kpis, currentUser } = useApp();
  const [selectedSection, setSelectedSection] = useState<string>('All');
  const [statusFilter, setStatusFilter] = useState<string>('All');
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [isSectionsGuideOpen, setIsSectionsGuideOpen] = useState(false);

  const rolePerms = ROLE_DEFINITIONS[currentUser.role];
  const canUpload = rolePerms?.canUpload26AS ?? false;

  // Invoices with expected TDS
  const invoicesWithExpectedTds = useMemo(() => {
    return invoices.filter(i => i.expectedTds > 0);
  }, [invoices]);

  const filteredTdsRecords = useMemo(() => {
    return tdsRecords.filter(t => {
      const matchSec = selectedSection === 'All' || t.section === selectedSection;
      const matchStatus = statusFilter === 'All' || t.status === statusFilter;
      return matchSec && matchStatus;
    });
  }, [tdsRecords, selectedSection, statusFilter]);

  const handleExport = (type: 'csv' | 'excel') => {
    const exportData = filteredTdsRecords.map(t => ({
      'TAN of Deductor': t.tan,
      'Deductor Name': t.deductorName,
      'PAN': t.pan,
      'Section': t.section,
      'Transaction Date': t.transactionDate,
      'Amount Paid / Credited': t.amountPaidCredited,
      'TDS Deposited': t.tdsDeposited,
      'Matched Invoice No': t.matchedInvoiceNumber || 'Unmatched',
      'Status': t.status,
      'Discrepancy Reason': t.discrepancyReason || 'None'
    }));

    if (type === 'csv') exportToCSV(exportData, 'TDS_26AS_Reconciliation');
    else exportToExcel(exportData, 'TDS_26AS_Reconciliation', 'TDS 26AS');
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">TDS / Form 26AS & AIS Verification</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Audit tax deducted at source by corporate clients against TRACES Form 26AS & AIS statements.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`hidden sm:inline-flex px-2.5 py-1 text-[11px] font-bold rounded-lg border ${rolePerms.badgeClass}`}>
            {currentUser.role}
          </span>
          <button
            onClick={() => setIsSectionsGuideOpen(true)}
            className="px-3 py-2 text-xs font-semibold text-emerald-900 bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 rounded-lg transition-colors flex items-center gap-1.5"
            title="Explore all TDS Sections under Income Tax (FY 2026-27)"
          >
            <BookOpen className="w-4 h-4 text-emerald-700" />
            <span>TDS Statutory Sections Guide</span>
          </button>
          <button
            onClick={() => handleExport('excel')}
            className="px-3 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200/80 rounded-lg transition-colors flex items-center gap-1.5"
          >
            <Download className="w-4 h-4 text-slate-500" />
            <span>Export Report</span>
          </button>
          {canUpload && (
            <button
              onClick={() => setIsImportModalOpen(true)}
              className="px-3.5 py-2 text-xs font-bold text-white bg-emerald-700 hover:bg-emerald-800 rounded-lg transition-colors flex items-center gap-1.5 shadow-xs"
            >
              <Upload className="w-4 h-4" />
              <span>Upload Form 26AS</span>
            </button>
          )}
        </div>
      </div>

      {/* KPI Cards for TDS */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Expected TDS</span>
          <p className="text-lg font-bold text-slate-900 mt-1">{formatINR(kpis.expectedTds)}</p>
          <span className="text-[11px] text-slate-500">{invoicesWithExpectedTds.length} eligible sales bills</span>
        </div>

        <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-200 shadow-xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 block">Reflected in 26AS</span>
          <p className="text-lg font-bold text-emerald-900 mt-1">{formatINR(kpis.reflectedTds)}</p>
          <span className="text-[11px] text-emerald-700">Deposited by customers</span>
        </div>

        <div className="p-4 bg-amber-50 rounded-xl border border-amber-200 shadow-xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-amber-800 block">TDS Pending in 26AS</span>
          <p className="text-lg font-bold text-amber-900 mt-1">{formatINR(kpis.pendingTds)}</p>
          <span className="text-[11px] text-amber-700">Deducted on payment, not deposited</span>
        </div>

        <div className="p-4 bg-rose-50 rounded-xl border border-rose-200 shadow-xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-rose-800 block">TDS Discrepancies</span>
          <p className="text-lg font-bold text-rose-900 mt-1">{formatINR(kpis.mismatchTds)}</p>
          <span className="text-[11px] text-rose-700">Rate / section mismatch</span>
        </div>
      </div>

      {/* CBDT Statutory Guidance Card */}
      <div className="bg-purple-50/70 border border-purple-200 rounded-xl p-4 text-xs text-purple-950 flex items-start gap-3 shadow-xs">
        <ShieldCheck className="w-5 h-5 text-purple-700 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <h4 className="font-bold">Statutory Compliance Note (CBDT Circular No. 23/2017 & Section 194C/J/Q)</h4>
          <p className="text-purple-900 leading-relaxed">
            In accordance with official CBDT rules, TDS must be deducted <strong>strictly on the Taxable Base Amount</strong>, excluding GST components. If a customer erroneously deducts TDS on the gross invoice amount inclusive of GST, FinRecon flags an <span className="font-bold">"Amount Mismatch"</span> exception so you can request an adjustment or revised TDS certificate.
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white p-4 rounded-xl border border-slate-200">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
            <Filter className="w-4 h-4 text-slate-400" />
            <span>TDS Section:</span>
          </div>
          <div className="flex flex-wrap gap-1">
            {['All', '194C', '194J', '194Q', '194I', '194H', '194T', '194R'].map(sec => (
              <button
                key={sec}
                onClick={() => setSelectedSection(sec)}
                className={`px-2.5 py-1 text-xs rounded-lg font-semibold transition-colors ${
                  selectedSection === sec
                    ? 'bg-slate-900 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {sec === 'All' ? 'All Sections' : `Sec ${sec}`}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <label className="text-slate-500 font-medium">Status:</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="p-1.5 rounded-lg border border-slate-200 bg-slate-50 text-slate-700 font-medium"
          >
            <option value="All">All Records</option>
            <option value="Matched">Matched</option>
            <option value="TDS Mismatch">Discrepancy / Mismatch</option>
            <option value="TDS Not Reflected">Not Reflected</option>
          </select>
        </div>
      </div>

      {/* Form 26AS Ledger Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-[10px] uppercase font-bold text-slate-500 tracking-wider">
              <tr>
                <th className="p-3.5">Deductor & TAN</th>
                <th className="p-3.5">Section</th>
                <th className="p-3.5">Credit Date</th>
                <th className="p-3.5 text-right">Gross Credited</th>
                <th className="p-3.5 text-right">TDS Deposited</th>
                <th className="p-3.5">Target Invoice</th>
                <th className="p-3.5">Verification Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredTdsRecords.map((t) => (
                <tr key={t.id} className="hover:bg-slate-50">
                  <td className="p-3.5">
                    <span className="font-bold text-slate-900 block">{t.deductorName}</span>
                    <span className="text-[10px] font-mono text-slate-400">TAN: {t.tan} • PAN: {t.pan}</span>
                  </td>

                  <td className="p-3.5 font-semibold text-slate-700">
                    <span className="px-2 py-0.5 bg-slate-100 rounded text-[11px] font-mono font-bold">
                      {t.section}
                    </span>
                  </td>

                  <td className="p-3.5 text-slate-600">{formatDate(t.transactionDate)}</td>

                  <td className="p-3.5 text-right font-mono text-slate-800">
                    {formatINR(t.amountPaidCredited, false)}
                  </td>

                  <td className="p-3.5 text-right font-mono font-bold text-purple-700">
                    {formatINR(t.tdsDeposited, false)}
                  </td>

                  <td className="p-3.5">
                    {t.matchedInvoiceNumber ? (
                      <span className="font-mono font-bold text-slate-800 text-xs">
                        {t.matchedInvoiceNumber}
                      </span>
                    ) : (
                      <span className="text-slate-400 italic text-[11px]">Unmatched</span>
                    )}
                  </td>

                  <td className="p-3.5">
                    <div>
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                          t.status === 'Matched'
                            ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-rose-100 text-rose-800'
                        }`}
                      >
                        {t.status}
                      </span>
                      {t.discrepancyReason && (
                        <p className="text-[10px] text-rose-600 font-medium mt-0.5">
                          {t.discrepancyReason}
                        </p>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 26AS Upload Wizard Modal */}
      {isImportModalOpen && (
        <TDS26ASImportWizard
          isOpen={isImportModalOpen}
          customers={customers}
          existingInvoices={invoices}
          existingTdsRecords={tdsRecords}
          onClose={() => setIsImportModalOpen(false)}
          onImportComplete={(imported) => {
            importTdsRecordsBatch(imported);
            setIsImportModalOpen(false);
          }}
        />
      )}

      {/* Income Tax 2025 TDS Sections Guide Modal */}
      {isSectionsGuideOpen && (
        <TDSSections2025Modal
          isOpen={isSectionsGuideOpen}
          onClose={() => setIsSectionsGuideOpen(false)}
        />
      )}
    </div>
  );
};
