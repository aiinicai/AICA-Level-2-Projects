import React, { useState } from 'react';
import { 
  FileSpreadsheet, 
  FileText, 
  Copy, 
  Check, 
  ShieldCheck, 
  AlertCircle, 
  BookOpen,
  ArrowRight,
  Receipt
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { ChallanRecord, AssesseeDetails } from '../types';

interface Clause20bViewProps {
  records: ChallanRecord[];
  assessee: AssesseeDetails;
  onExportExcel: () => void;
  onExportPdf: () => void;
}

export const Clause20bView: React.FC<Clause20bViewProps> = ({
  records,
  assessee,
  onExportExcel,
  onExportPdf,
}) => {
  const [copied, setCopied] = useState(false);

  const totalReceived = records.reduce((s, r) => s + r.employeeContribution, 0);
  const totalPaid = records.reduce((s, r) => s + r.employeeContribution, 0);
  const totalDisallowed = records.reduce((s, r) => s + r.disallowableAmount, 0);

  const copyClause20bText = () => {
    let tsv = "Sl. No.\tNature of Fund\tSum received from employees\tDue date for payment\tActual date of payment\tActual amount paid\tAmount not paid by due date (Disallowed u/s 36(1)(va))\tRemarks / TRRN\n";
    
    records.forEach((rec, idx) => {
      const fund = rec.fundType === 'PF' ? `PF (${rec.wageMonth})` : `ESI (${rec.wageMonth})`;
      const remarks = rec.status === 'DELAYED' ? `Delayed by ${rec.delayDays} day(s) [${rec.challanReference}]` : `On time [${rec.challanReference}]`;
      tsv += `${idx + 1}\t${fund}\t${rec.employeeContribution}\t${rec.statutoryDueDate}\t${rec.actualPaymentDate}\t${rec.employeeContribution}\t${rec.disallowableAmount}\t${remarks}\n`;
    });

    tsv += `TOTAL\t\t${totalReceived}\t\t\t${totalPaid}\t${totalDisallowed}\tTotal Disallowance u/s 36(1)(va): Rs. ${totalDisallowed}\n`;

    navigator.clipboard.writeText(tsv);
    setCopied(true);
    confetti({ particleCount: 40, spread: 60, origin: { y: 0.8 } });
    setTimeout(() => setCopied(false), 3000);
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
      
      {/* Header Bar */}
      <div className="p-5 bg-slate-900 text-white flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="px-2.5 py-0.5 rounded-lg bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-[11px] font-bold uppercase tracking-wider">
              Form 3CD Clause 20(b)
            </span>
            <h2 className="text-base sm:text-lg font-bold text-white">
              Official Tax Audit Schedule
            </h2>
          </div>
          <p className="text-xs text-slate-300 mt-1">
            Statement of amounts received from employees as contribution to PF / ESI & deposited u/s 36(1)(va)
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={copyClause20bText}
            id="copy-clause-20b-btn"
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold border border-slate-700 transition cursor-pointer active:scale-95"
            title="Copy TSV for Excel/Tax Audit Utility"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-slate-300" />}
            <span>{copied ? "Copied Table!" : "Copy Table Data"}</span>
          </button>

          <button
            onClick={onExportExcel}
            id="clause20b-export-excel-btn"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold shadow-sm transition cursor-pointer active:scale-95"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>Download Excel</span>
          </button>

          <button
            onClick={onExportPdf}
            id="clause20b-export-pdf-btn"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold shadow-sm transition cursor-pointer active:scale-95"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Download PDF</span>
          </button>
        </div>
      </div>

      {/* Assessee Audit Meta Strip */}
      <div className="bg-slate-50 border-b border-slate-200 px-5 py-3 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div>
          <span className="text-slate-500 font-medium">Assessee: </span>
          <strong className="text-slate-900 font-bold">{assessee.name}</strong>
        </div>
        <div>
          <span className="text-slate-500 font-medium">PAN: </span>
          <strong className="text-slate-900 font-bold font-mono">{assessee.pan}</strong>
        </div>
        <div>
          <span className="text-slate-500 font-medium">A.Y. / F.Y.: </span>
          <strong className="text-slate-900 font-bold">{assessee.assessmentYear} / {assessee.financialYear}</strong>
        </div>
        <div>
          <span className="text-slate-500 font-medium">Auditor: </span>
          <strong className="text-indigo-800 font-bold">{assessee.auditorName}</strong>
        </div>
      </div>

      {/* Official 8-Column Clause 20(b) Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-100 text-slate-800 font-bold border-b border-slate-300 text-[11px] uppercase tracking-wider">
              <th className="py-3 px-3 w-12 text-center border-r border-slate-200">S.No.</th>
              <th className="py-3 px-4 border-r border-slate-200">Nature of fund</th>
              <th className="py-3 px-3 text-right border-r border-slate-200">Sum received from employees (₹)</th>
              <th className="py-3 px-3 text-center border-r border-slate-200">Due date for payment</th>
              <th className="py-3 px-3 text-center border-r border-slate-200">Actual date of payment</th>
              <th className="py-3 px-3 text-right border-r border-slate-200">The actual amount paid (₹)</th>
              <th className="py-3 px-3 text-right border-r border-slate-200 text-rose-800 bg-rose-50/70">
                Amount not paid by due date [Disallowed u/s 36(1)(va)] (₹)
              </th>
              <th className="py-3 px-4">Remarks / TRRN</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {records.map((rec, idx) => {
              const isDelayed = rec.status === 'DELAYED';

              return (
                <tr 
                  key={rec.id} 
                  className={`hover:bg-slate-50 transition ${
                    isDelayed ? 'bg-rose-50/40 font-medium' : ''
                  }`}
                >
                  <td className="py-2.5 px-3 text-center border-r border-slate-200 font-mono text-slate-500">
                    {idx + 1}
                  </td>
                  <td className="py-2.5 px-4 border-r border-slate-200">
                    <span className="font-bold text-slate-900">{rec.fundType}</span>
                    <span className="text-slate-500 ml-1">({rec.wageMonth})</span>
                    <span className="block text-[10px] text-slate-400 truncate max-w-[150px]">{rec.establishmentName}</span>
                  </td>
                  <td className="py-2.5 px-3 text-right border-r border-slate-200 font-mono font-bold text-slate-800">
                    ₹ {rec.employeeContribution.toLocaleString('en-IN')}
                  </td>
                  <td className="py-2.5 px-3 text-center border-r border-slate-200 font-mono text-slate-700">
                    <span className="bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                      {rec.statutoryDueDate}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-center border-r border-slate-200 font-mono">
                    <span className={`px-2 py-0.5 rounded font-bold ${
                      isDelayed 
                        ? 'bg-rose-100 text-rose-800 border border-rose-200' 
                        : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                    }`}>
                      {rec.actualPaymentDate}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-right border-r border-slate-200 font-mono font-bold text-slate-800">
                    ₹ {rec.employeeContribution.toLocaleString('en-IN')}
                  </td>
                  <td className={`py-2.5 px-3 text-right border-r border-slate-200 font-mono font-black ${
                    rec.disallowableAmount > 0 ? 'text-rose-700 bg-rose-50/70' : 'text-slate-400'
                  }`}>
                    {rec.disallowableAmount > 0 
                      ? `₹ ${rec.disallowableAmount.toLocaleString('en-IN')}` 
                      : 'NIL'}
                  </td>
                  <td className="py-2.5 px-4 text-[11px] text-slate-600 font-mono">
                    {isDelayed ? (
                      <span className="text-rose-700 font-semibold">
                        Delayed by {rec.delayDays} day(s) [{rec.challanReference}]
                      </span>
                    ) : (
                      <span className="text-emerald-700 font-medium">
                        On time [{rec.challanReference}]
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
          <tfoot className="bg-slate-100 border-t-2 border-slate-300 font-black text-slate-900 text-xs">
            <tr>
              <td colSpan={2} className="py-3 px-4 text-right uppercase tracking-wider border-r border-slate-200">
                TOTAL:
              </td>
              <td className="py-3 px-3 text-right font-mono border-r border-slate-200">
                ₹ {totalReceived.toLocaleString('en-IN')}
              </td>
              <td colSpan={2} className="border-r border-slate-200"></td>
              <td className="py-3 px-3 text-right font-mono border-r border-slate-200">
                ₹ {totalPaid.toLocaleString('en-IN')}
              </td>
              <td className="py-3 px-3 text-right text-rose-700 font-mono bg-rose-100/50 border-r border-slate-200">
                ₹ {totalDisallowed.toLocaleString('en-IN')}
              </td>
              <td className="py-3 px-4 text-xs font-semibold text-slate-700">
                {totalDisallowed > 0 
                  ? `Total Disallowance u/s 36(1)(va): ₹${totalDisallowed.toLocaleString('en-IN')}`
                  : '100% Complied'}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      {/* Tax Auditor's Legal Note under Section 36(1)(va) */}
      <div className="p-4 bg-slate-50 border-t border-slate-200 text-xs text-slate-600 space-y-2">
        <div className="flex items-start gap-2">
          <ShieldCheck className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
          <p>
            <strong>Auditor Note on Clause 20(b):</strong> In accordance with Explanation 2 to Section 36(1)(va) inserted by Finance Act 2021 and upheld by the Hon'ble Supreme Court of India in <em>Checkmate Services P. Ltd. v. CIT (2022) 448 ITR 518 (SC)</em>, the provisions of Section 43B do NOT apply to employee contributions. Any sum credited to the employee's account in the relevant fund after the statutory due date (15th of next month) is strictly disallowable.
          </p>
        </div>
      </div>

    </div>
  );
};
