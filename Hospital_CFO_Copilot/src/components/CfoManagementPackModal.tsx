import React from 'react';
import {
  Download,
  FileCheck2,
  FileSpreadsheet,
  Printer,
  ShieldAlert,
  Sparkles,
  X,
} from 'lucide-react';
import { DepartmentClearanceSummary } from '../engine/clearanceEngine';
import { DashboardMetrics, FinancialException, UserSession } from '../types';
import { formatIndianDate, formatINR } from '../utils/formatters';
import {
  exportManagementPackToPdf,
  exportManagementPackToExcel,
} from '../utils/reportExportUtils';

interface CfoManagementPackModalProps {
  isOpen: boolean;
  onClose: () => void;
  metrics: DashboardMetrics;
  exceptions: FinancialException[];
  clearanceSummary?: DepartmentClearanceSummary;
  currentUser: UserSession;
  runId: string;
  arSummary?: import('../utils/arCalculations').ArAgeingSummary;
  totalClaimsSubmitted?: number;
  totalApproved?: number;
  totalPending?: number;
}

export const CfoManagementPackModal: React.FC<CfoManagementPackModalProps> = ({
  isOpen,
  onClose,
  metrics,
  exceptions,
  clearanceSummary,
  currentUser,
  runId,
  arSummary,
  totalClaimsSubmitted,
  totalApproved,
  totalPending,
}) => {
  // Listen for Escape key to dismiss modal
  React.useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handlePrint = () => {
    window.print();
  };

  const todayStr = formatIndianDate(new Date().toISOString().split('T')[0]);

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs p-3 sm:p-6 flex justify-center items-start print:p-0 print:bg-white"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-4xl w-full my-4 sm:my-8 overflow-hidden animate-in fade-in zoom-in-95 duration-150 print:border-none print:shadow-none print:my-0 relative"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Sticky Modal Controls Header - Always visible regardless of scroll position */}
        <div className="sticky top-0 z-30 p-4 bg-slate-900 text-white flex items-center justify-between shadow-md print:hidden">
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5 text-teal-400" />
            <h2 className="text-sm font-bold tracking-tight">
              Hospital CFO Executive Management Pack
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() =>
                exportManagementPackToPdf(
                  metrics,
                  exceptions,
                  clearanceSummary,
                  arSummary,
                  currentUser,
                  runId,
                  totalClaimsSubmitted,
                  totalApproved,
                  totalPending
                )
              }
              className="flex items-center gap-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 px-3 py-1.5 text-xs font-semibold text-white transition cursor-pointer"
              title="Download officially formatted boardroom PDF dossier"
            >
              <Download className="h-3.5 w-3.5" />
              <span>Download PDF</span>
            </button>
            <button
              onClick={() =>
                exportManagementPackToExcel(
                  metrics,
                  exceptions,
                  clearanceSummary,
                  arSummary,
                  currentUser,
                  runId,
                  totalClaimsSubmitted,
                  totalApproved,
                  totalPending
                )
              }
              className="flex items-center gap-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white transition cursor-pointer"
              title="Export multi-sheet Excel spreadsheet (.xlsx)"
            >
              <FileSpreadsheet className="h-3.5 w-3.5" />
              <span>Export Excel</span>
            </button>
            <button
              onClick={handlePrint}
              className="hidden sm:flex items-center gap-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white px-2.5 py-1.5 text-xs font-medium transition cursor-pointer border border-slate-700"
            >
              <Printer className="h-3.5 w-3.5" />
              <span>Print</span>
            </button>
            <button
              onClick={onClose}
              aria-label="Close Management Pack"
              className="flex items-center gap-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white px-2.5 py-1.5 text-xs font-medium transition cursor-pointer border border-slate-700"
            >
              <X className="h-4 w-4" />
              <span>Close</span>
            </button>
          </div>
        </div>

        {/* PRINTABLE DOSSIER BODY */}
        <div className="p-8 space-y-6 text-slate-800 bg-white">
          {/* Institutional Header */}
          <div className="flex justify-between items-start border-b-2 border-teal-800 pb-4">
            <div>
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-lg bg-teal-800 text-white flex items-center justify-center font-bold text-sm">
                  HC
                </div>
                <h1 className="text-xl font-bold tracking-tight text-slate-900">
                  APEX MULTISPECIALTY HOSPITAL &amp; RESEARCH INSTITUTE
                </h1>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Office of the Chief Financial Officer &bull; Financial Governance &amp; Revenue Intelligence Pack
              </p>
            </div>
            <div className="text-right text-xs text-slate-600">
              <div className="font-semibold text-slate-900">Report Date: {todayStr}</div>
              <div>Run ID: <span className="font-mono text-teal-800 font-bold">{runId}</span></div>
              <div>Prepared for: <span className="font-medium text-slate-800">{currentUser.name} ({currentUser.role})</span></div>
            </div>
          </div>

          {/* 1. EXECUTIVE SUMMARY SECTION */}
          <section className="space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-teal-900 border-b border-slate-200 pb-1">
              1. Executive Financial Position &amp; Governance Snapshot
            </h3>
            {metrics.grossBilling > 0 || metrics.totalExpectedAmount > 0 ? (
              <>
                <p className="text-xs leading-relaxed text-slate-700">
                  The hospital recorded <strong>{formatINR(metrics.grossBilling)}</strong> in gross patient billing for the reporting audit period against an expected clinical tariff base of <strong>{formatINR(metrics.totalExpectedAmount)}</strong> (overall billing capture efficiency of {metrics.billingCaptureRate ?? (metrics.totalExpectedAmount > 0 ? ((metrics.grossBilling / metrics.totalExpectedAmount) * 100).toFixed(1) : 100)}%).
                  The deterministic control engine identified an institutional potential financial exposure of <strong>{formatINR(metrics.potentialFinancialExposure)}</strong> across <strong>{metrics.openExceptionsCount}</strong> open exceptions ({metrics.criticalExceptionsCount} critical, {metrics.highExceptionsCount} high). Outstanding accounts receivable stands at <strong>{formatINR(metrics.outstandingCollections)}</strong> with <strong>{formatINR(metrics.tpaPendingAmount)}</strong> pending adjudication across insurance payers.
                </p>

                <div className="grid grid-cols-4 gap-3 pt-2 text-xs">
                  <div className="p-2.5 rounded-lg border border-slate-200 bg-slate-50">
                    <div className="text-[10px] uppercase text-slate-500 font-semibold">Gross Billed</div>
                    <div className="text-base font-bold text-slate-900">{formatINR(metrics.grossBilling)}</div>
                  </div>
                  <div className="p-2.5 rounded-lg border border-amber-200 bg-amber-50">
                    <div className="text-[10px] uppercase text-amber-800 font-semibold">Identified Exposure</div>
                    <div className="text-base font-bold text-amber-900">{formatINR(metrics.potentialFinancialExposure)}</div>
                  </div>
                  <div className="p-2.5 rounded-lg border border-slate-200 bg-slate-50">
                    <div className="text-[10px] uppercase text-slate-500 font-semibold">Outstanding AR</div>
                    <div className="text-base font-bold text-slate-900">{formatINR(metrics.outstandingCollections)}</div>
                  </div>
                  <div className="p-2.5 rounded-lg border border-teal-200 bg-teal-50">
                    <div className="text-[10px] uppercase text-teal-800 font-semibold">Dept Clearance</div>
                    <div className="text-base font-bold text-teal-800">
                      {clearanceSummary ? `${clearanceSummary.clearancePercent}%` : 'Data not available'}
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <div className="p-4 text-center text-xs text-slate-500">
                Data not available for this reporting period.
              </div>
            )}
          </section>

          {/* 2. TOP PRIORITY FINANCIAL EXCEPTIONS TABLE */}
          <section className="space-y-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-teal-900 border-b border-slate-200 pb-1">
              2. Priority Financial Exceptions Requiring CFO Action
            </h3>
            {metrics.priorityExceptions && metrics.priorityExceptions.length > 0 ? (
              <table className="min-w-full text-left text-xs border border-slate-200">
                <thead className="bg-slate-100 text-[10px] font-bold text-slate-600 uppercase">
                  <tr>
                    <th className="p-2 border">Encounter</th>
                    <th className="p-2 border">Control</th>
                    <th className="p-2 border">Revenue Centre</th>
                    <th className="p-2 border">Exception Description</th>
                    <th className="p-2 border text-right">Exposure</th>
                    <th className="p-2 border">Severity</th>
                    <th className="p-2 border">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {metrics.priorityExceptions.slice(0, 6).map((exc, idx) => (
                    <tr key={`${exc.Exception_ID}-${idx}`} className="border-t">
                      <td className="p-2 border font-mono font-bold text-teal-800">{exc.Encounter_ID}</td>
                      <td className="p-2 border font-mono">{exc.Control_ID}</td>
                      <td className="p-2 border">{exc.Revenue_Centre}</td>
                      <td className="p-2 border text-slate-700">{exc.Description}</td>
                      <td className="p-2 border text-right font-bold text-amber-900">{formatINR(exc.Exposure_Amount)}</td>
                      <td className="p-2 border font-semibold">{exc.Severity}</td>
                      <td className="p-2 border">{exc.Status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="p-4 text-center text-xs text-slate-500 border border-slate-200 rounded">
                Data not available for this reporting period.
              </div>
            )}
          </section>

          {/* 3. DEPARTMENTAL EXPOSURE & CLEARANCE PERFORMANCE */}
          <section className="space-y-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-teal-900 border-b border-slate-200 pb-1">
              3. Departmental Exposure &amp; Clearance Breakdown
            </h3>
            <div className="grid grid-cols-2 gap-4">
              {metrics.exceptionsByDepartment && metrics.exceptionsByDepartment.length > 0 ? (
                <table className="min-w-full text-left text-xs border border-slate-200">
                  <thead className="bg-slate-100 text-[10px] font-bold text-slate-600 uppercase">
                    <tr>
                      <th className="p-2 border">Department</th>
                      <th className="p-2 border text-right">Exceptions</th>
                      <th className="p-2 border text-right">Financial Exposure</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metrics.exceptionsByDepartment.map((d) => (
                      <tr key={d.department} className="border-t">
                        <td className="p-2 border font-medium">{d.department}</td>
                        <td className="p-2 border text-right">{d.count}</td>
                        <td className="p-2 border text-right font-bold">{formatINR(d.exposure)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="p-4 text-center text-xs text-slate-500 border border-slate-200 rounded">
                  Data not available for this reporting period.
                </div>
              )}

              {metrics.exceptionsByControl && metrics.exceptionsByControl.length > 0 ? (
                <table className="min-w-full text-left text-xs border border-slate-200">
                  <thead className="bg-slate-100 text-[10px] font-bold text-slate-600 uppercase">
                    <tr>
                      <th className="p-2 border">Control Code &amp; Name</th>
                      <th className="p-2 border text-right">Count</th>
                      <th className="p-2 border text-right">Identified Leakage</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metrics.exceptionsByControl.map((c) => (
                      <tr key={c.controlId} className="border-t">
                        <td className="p-2 border font-medium">
                          <strong className="text-teal-800 mr-1 font-mono">{c.controlId}</strong>
                          {c.title}
                        </td>
                        <td className="p-2 border text-right">{c.count}</td>
                        <td className="p-2 border text-right font-bold">{formatINR(c.exposure)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="p-4 text-center text-xs text-slate-500 border border-slate-200 rounded">
                  Data not available for this reporting period.
                </div>
              )}
            </div>
          </section>

          {/* 4. AR AGEING SCHEDULE */}
          {arSummary && (
            <section className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-teal-900 border-b border-slate-200 pb-1">
                4. Accounts Receivable Ageing Schedule (As of {arSummary.asOfDateDisplay})
              </h3>
              <div className="grid grid-cols-4 gap-2 text-xs">
                {arSummary.ageingBuckets.map((bucket) => (
                  <div key={bucket.bucket} className="p-2 rounded border border-slate-200 bg-slate-50 text-center">
                    <div className="text-[10px] font-bold text-slate-500 uppercase">{bucket.label}</div>
                    <div className="text-sm font-bold text-slate-900 mt-0.5">
                      {new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(bucket.amount)}
                    </div>
                    <div className="text-[10px] text-slate-400">{bucket.count} accounts ({bucket.shareFormatted})</div>
                  </div>
                ))}
              </div>
              <div className="flex gap-4 text-xs pt-1">
                <span>Total AR: <strong>{new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(arSummary.totalAR)}</strong></span>
                <span>Collection Rate: <strong>{arSummary.collectionRate}%</strong></span>
                {totalClaimsSubmitted !== undefined && <span>TPA Submitted: <strong>{new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(totalClaimsSubmitted)}</strong></span>}
                {totalApproved !== undefined && <span>TPA Approved: <strong>{new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(totalApproved)}</strong></span>}
                {totalPending !== undefined && <span>TPA Pending: <strong>{new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(totalPending)}</strong></span>}
              </div>
            </section>
          )}

          {/* 5. GOVERNANCE & SIGN-OFF BLOCK (Dynamic User Identity) */}
          <div className="pt-6 border-t-2 border-slate-200 grid grid-cols-3 gap-6 text-xs text-slate-600">
            <div>
              <div className="border-b border-slate-400 pb-8 mb-1" />
              <div className="font-bold text-slate-900">{currentUser.name}</div>
              <div>{currentUser.role} &bull; Executing Officer</div>
            </div>
            <div>
              <div className="border-b border-slate-400 pb-8 mb-1" />
              <div className="font-bold text-slate-900">Finance &amp; Inpatient Billing Lead</div>
              <div>Operating Billing Clearance Authority</div>
            </div>
            <div>
              <div className="border-b border-slate-400 pb-8 mb-1" />
              <div className="font-bold text-slate-900">Revenue Assurance / Internal Audit</div>
              <div>Hospital Governance Sign-off</div>
            </div>
          </div>
        </div>

        {/* Footer Actions (Screen only) */}
        <div className="p-4 bg-slate-100 border-t border-slate-200 flex flex-wrap items-center justify-between gap-3 print:hidden">
          <div className="text-xs text-slate-500">
            Press <kbd className="px-1.5 py-0.5 bg-white border border-slate-300 rounded text-[11px] font-mono text-slate-700 font-semibold">Esc</kbd> or click outside to dismiss
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              className="flex items-center gap-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 px-3.5 py-1.5 text-xs font-semibold text-white transition cursor-pointer"
            >
              <Printer className="h-3.5 w-3.5" />
              <span>Print / Save as PDF</span>
            </button>
            <button
              onClick={onClose}
              className="px-4 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold transition cursor-pointer"
            >
              Close Document
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
