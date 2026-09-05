import React from 'react';
import { useApp } from '../context/AppContext';
import { Department } from '../types';
import {
  formatINR,
  formatAUD,
  convertInrToAud,
  formatIST,
  formatDate,
} from '../utils/formatters';
import { Printer, Download, CheckCircle2, ShieldCheck, X } from 'lucide-react';
import { exportConsolidatedToCSV } from '../utils/exportCsv';

interface ApprovalSummaryModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ApprovalSummaryModal: React.FC<ApprovalSummaryModalProps> = ({
  isOpen,
  onClose,
}) => {
  const { activeMonth, currentSubmissions } = useApp();

  if (!isOpen) return null;

  const departments: Department[] = ['HR', 'Admin', 'IT', 'Finance'];

  // Calculate department totals
  const deptData = departments.map((dept) => {
    const sub = currentSubmissions.find((s) => s.department === dept);
    const reqInr = sub?.lineItems.reduce((acc, i) => acc + i.amountInr, 0) || 0;
    const reqAud = convertInrToAud(reqInr, activeMonth.exchangeRate);
    const appInr = sub?.lineItems.reduce((acc, i) => acc + (i.approvedAmountInr !== undefined ? i.approvedAmountInr : i.amountInr), 0) || 0;
    const appAud = convertInrToAud(appInr, activeMonth.exchangeRate);
    const critInr = sub?.lineItems.filter((i) => i.priority === 'Critical').reduce((acc, i) => acc + i.amountInr, 0) || 0;

    return {
      department: dept,
      status: sub?.status || 'Not Started',
      submittedBy: sub?.submittedBy || '—',
      reqInr,
      reqAud,
      appInr,
      appAud,
      critInr,
      itemCount: sub?.lineItems.length || 0,
    };
  });

  const totalReqInr = deptData.reduce((acc, d) => acc + d.reqInr, 0);
  const totalReqAud = convertInrToAud(totalReqInr, activeMonth.exchangeRate);
  const totalAppInr = deptData.reduce((acc, d) => acc + d.appInr, 0);
  const totalAppAud = convertInrToAud(totalAppInr, activeMonth.exchangeRate);

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs overflow-y-auto print:p-0 print:bg-white print:static">
      <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-4xl w-full p-6 sm:p-8 space-y-6 my-auto print:shadow-none print:border-none print:max-w-none print:p-0">
        
        {/* Action Header (Hidden during print) */}
        <div className="flex items-center justify-between border-b border-slate-100 pb-3 print:hidden">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            Official Executive Sign-off Document
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg text-xs shadow-xs"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print / Save as PDF</span>
            </button>

            <button
              onClick={() => exportConsolidatedToCSV(activeMonth, currentSubmissions)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 font-semibold rounded-lg text-xs"
            >
              <Download className="w-3.5 h-3.5" />
              <span>CSV Data</span>
            </button>

            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg ml-2"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* PRINTABLE DOCUMENT BODY */}
        <div className="space-y-6 text-slate-800" id="printable-signoff-sheet">
          
          {/* Header */}
          <div className="flex justify-between items-start border-b-2 border-slate-900 pb-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-2xl font-black text-slate-900 tracking-tight">
                  MAROPOST INDIA
                </span>
                <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 bg-slate-100 text-slate-700 rounded border border-slate-300">
                  Treasury Remittance Pack
                </span>
              </div>
              <p className="text-sm font-semibold text-slate-600 mt-1">
                Monthly Operating Cash Requirements & Currency Authorization Sheet
              </p>
              <p className="text-xs text-slate-500">
                Entity: Maropost Technology India Pvt. Ltd. • Chandigarh & Bengaluru Hubs
              </p>
            </div>

            <div className="text-right">
              <div className="text-xs font-semibold text-slate-500">Target Operational Cycle</div>
              <div className="text-xl font-bold text-slate-900">{activeMonth.label}</div>
              <div className="text-xs text-emerald-800 font-mono font-bold mt-0.5">
                Locked FX: 1 INR = A${activeMonth.exchangeRate}
              </div>
            </div>
          </div>

          {/* Meta & FX Benchmark Details */}
          <div className="grid grid-cols-3 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs">
            <div>
              <span className="text-slate-500 block">Currency Benchmark Source:</span>
              <strong className="text-slate-800">{activeMonth.rateSource || 'RBI Reference Rate'}</strong>
            </div>
            <div>
              <span className="text-slate-500 block">Inverse Conversion:</span>
              <strong className="font-mono text-slate-800">1 AUD ≈ ₹{(1 / activeMonth.exchangeRate).toFixed(2)} INR</strong>
            </div>
            <div>
              <span className="text-slate-500 block">Sign-off Status:</span>
              <strong className="text-emerald-700">{activeMonth.status}</strong>
            </div>
          </div>

          {/* Department Breakdown Table */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
              Department Cash Requirements Summary
            </h4>

            <table className="w-full text-xs text-left border-collapse border border-slate-300">
              <thead>
                <tr className="bg-slate-100 border-b border-slate-300 font-bold text-slate-800">
                  <th className="py-2.5 px-3 border-r border-slate-300">Department</th>
                  <th className="py-2.5 px-3 border-r border-slate-300">Submitter</th>
                  <th className="py-2.5 px-3 border-r border-slate-300 text-right">Requested (₹ INR)</th>
                  <th className="py-2.5 px-3 border-r border-slate-300 text-right">Requested (A$ AUD)</th>
                  <th className="py-2.5 px-3 border-r border-slate-300 text-right">Approved (₹ INR)</th>
                  <th className="py-2.5 px-3 text-right">Approved (A$ AUD)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {deptData.map((d) => (
                  <tr key={d.department} className="border-b border-slate-200">
                    <td className="py-2.5 px-3 border-r border-slate-300 font-bold text-slate-900">
                      {d.department} Department
                    </td>
                    <td className="py-2.5 px-3 border-r border-slate-300 text-slate-600">
                      {d.submittedBy}
                    </td>
                    <td className="py-2.5 px-3 border-r border-slate-300 text-right font-mono">
                      {formatINR(d.reqInr)}
                    </td>
                    <td className="py-2.5 px-3 border-r border-slate-300 text-right font-mono text-slate-700">
                      {formatAUD(d.reqAud)}
                    </td>
                    <td className="py-2.5 px-3 border-r border-slate-300 text-right font-mono font-bold text-blue-900">
                      {formatINR(d.appInr)}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono font-bold text-emerald-800">
                      {formatAUD(d.appAud)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="bg-slate-100 font-black text-slate-900 border-t-2 border-slate-400">
                  <td colSpan={2} className="py-3 px-3 border-r border-slate-300 text-right uppercase">
                    Consolidated Grand Total:
                  </td>
                  <td className="py-3 px-3 border-r border-slate-300 text-right font-mono">
                    {formatINR(totalReqInr)}
                  </td>
                  <td className="py-3 px-3 border-r border-slate-300 text-right font-mono">
                    {formatAUD(totalReqAud)}
                  </td>
                  <td className="py-3 px-3 border-r border-slate-300 text-right font-mono text-blue-900 text-sm">
                    {formatINR(totalAppInr)}
                  </td>
                  <td className="py-3 px-3 text-right font-mono text-emerald-800 text-sm">
                    {formatAUD(totalAppAud)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>

          {/* Consolidation & Controller Comments */}
          {activeMonth.consolidationNotes && (
            <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-xs space-y-1">
              <span className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                Controller Consolidation Narrative:
              </span>
              <p className="text-slate-800 italic">
                "{activeMonth.consolidationNotes}"
              </p>
            </div>
          )}

          {/* Management Approval & Sign-off Stamp Block */}
          <div className="border-2 border-dashed border-slate-300 rounded-xl p-5 bg-slate-50/50 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-black text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                Executive Approval & Treasury Authorization Block
              </span>
              <span className="text-xs font-mono font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded">
                DECISION: {activeMonth.approvalRecord?.decision || (activeMonth.status === 'Approved' ? 'APPROVED' : 'PENDING SIGN-OFF')}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs pt-2">
              <div>
                <span className="text-slate-500 block">Approving Authority:</span>
                <strong className="text-slate-900 text-sm">
                  {activeMonth.approvalRecord?.approverName || 'Marcus Vance'}
                </strong>
                <div className="text-slate-500 text-[11px]">
                  {activeMonth.approvalRecord?.approverRole || 'Managing Director / Global VP Finance'}
                </div>
              </div>

              <div>
                <span className="text-slate-500 block">Sign-off Timestamp:</span>
                <strong className="text-slate-900 font-mono">
                  {activeMonth.approvalRecord?.decidedAt ? formatIST(activeMonth.approvalRecord.decidedAt) : 'Pending Final Authorization'}
                </strong>
              </div>

              <div>
                <span className="text-slate-500 block">Total Authorized Remittance:</span>
                <strong className="text-emerald-800 font-bold font-mono text-sm">
                  {formatAUD(totalAppAud)}
                </strong>
                <div className="text-slate-500 text-[11px]">
                  ({formatINR(totalAppInr)})
                </div>
              </div>
            </div>

            {activeMonth.approvalRecord?.comments && (
              <div className="pt-2 border-t border-slate-200 text-xs">
                <span className="text-slate-500 block">Executive Endorsement Notes:</span>
                <p className="text-slate-800 italic mt-0.5">
                  "{activeMonth.approvalRecord.comments}"
                </p>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="pt-4 border-t border-slate-200 text-[10px] text-slate-400 flex justify-between">
            <span>Maropost India • Financial FP&A Reporting System</span>
            <span>Generated on {formatIST(new Date().toISOString())}</span>
          </div>

        </div>

      </div>
    </div>
  );
};
